#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 150 · 示例 01：OAuth2 授权码流程 + PKCE 完整模拟（基础用法）
=================================================================

目标
----
用**纯标准库**搭一个"迷你授权服务器 + 客户端 + 资源服务器"，
把 RFC 6749（授权码流程）和 RFC 7636（PKCE）的关键步骤真实地走一遍，
让你在调试真实 OAuth2 时，知道每一步到底在发生什么、哪里可能出错。

为什么不用 requests / authlib？
------------------------------
因为我们要"看清楚机制"。第三方库把这些步骤封装了，反而看不见
state 怎么比、code_challenge 怎么算、code_verifier 怎么校验。

运行
----
    python3 01-oauth2-auth-code-flow.py            # 完整流程演示（含 4 秒真实 sleep）
    python3 01-oauth2-auth-code-flow.py --self-test # 离线自检（不联网、不 sleep，秒出结果）

⚠️ 为什么要有 --self-test？
    演示模式为了证明"令牌真的会过期"，必须真的 sleep 4 秒；
    但 CI / 教学验证需要**确定性、快速、可重复**的结果。
    self-test 用"手动把 expires_at 拨到过去"替代 sleep，
    用断言把每个安全属性钉死，失败时打印实际值 vs 期望值。

阅读顺序
--------
    ① MiniAuthServer   —— 授权服务器（/authorize、/token、/userinfo）
    ② OAuthClient      —— 客户端（生成 state / PKCE、换令牌、调接口）
    ③ main()           —— 把一次完整授权走完，并演示令牌过期与刷新
"""

import base64
import hashlib
import json
import secrets
import sys
import time
import urllib.parse
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════

def b64url(data: bytes) -> str:
    """Base64URL 编码，**去掉填充等号**（PKCE / JWT 都用这种编码）。

    为什么必须用 URL-Safe 变体？
    因为标准 Base64 里的 '+' '/' '=' 在 URL 查询串中需要转义，
    各语言转义行为不一致会导致"明明一样的值却算不出同样的 challenge"。
    """
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def s256(verifier: str) -> str:
    """PKCE 的 S256 变换：challenge = BASE64URL(SHA256(ASCII(verifier)))。

    注意：编码前必须是 **ASCII 字节**，不能是 UTF-8 的多字节内容
    （verifier 由 urlsafe 随机串构成，本来就是 ASCII，这里显式编码防手滑）。
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return b64url(digest)


def banner(title: str) -> None:
    print("\n" + "═" * 68)
    print(f"  {title}")
    print("═" * 68)


# ══════════════════════════════════════════════════════════════════
# ① 授权服务器（Authorization Server + Resource Server 合体）
# ══════════════════════════════════════════════════════════════════

@dataclass
class AuthCode:
    """授权码的"服务端记录"。授权码本身就是一把一次性钥匙。"""
    client_id: str
    redirect_uri: str
    scope: str
    user: str
    code_challenge: str
    code_challenge_method: str
    expires_at: float
    used: bool = False


@dataclass
class TokenRecord:
    """已签发令牌的"服务端记录"（真实实现里会入库 / Redis）。"""
    user: str
    scope: str
    expires_at: float
    revoked: bool = False


class MiniAuthServer:
    """迷你授权服务器。真实实现在这里会做：登录页、同意页、HTTPS、限流等。"""

    CODE_TTL = 60          # 授权码 60 秒就作废（真实实现 30~60s）
    ACCESS_TTL = 3         # 演示用 3 秒；真实是 300~3600 秒
    REFRESH_TTL = 3600

    def __init__(self):
        # 注册的客户端：生产环境这些信息存在数据库里
        self.clients = {
            "webapp": {
                "client_secret": "s3cr3t-keep-it-on-server",
                "redirect_uris": ["https://app.example.com/callback"],  # 精确匹配
                "public": False,   # 有后端 → 机密客户端
            },
            "mobileapp": {
                "client_secret": None,          # 拿不到 secret → 公开客户端
                "redirect_uris": ["myapp://cb"],
                "public": True,                 # 必须用 PKCE
            },
        }
        self.codes: dict[str, AuthCode] = {}
        self.access_tokens: dict[str, TokenRecord] = {}
        self.refresh_tokens: dict[str, str] = {}   # refresh -> user
        self.audit_log: list[str] = []

    # ── 内部：审计日志（安全系统最重要的"证据链"）──────────────
    def _log(self, msg: str) -> None:
        # ⚠️ 生产环境：绝不把 token / code / secret 原文写进日志
        self.audit_log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    # ── 端点 1：GET /authorize ────────────────────────────────
    def authorize(self, params: dict) -> str:
        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")

        client = self.clients.get(client_id)
        if client is None:
            return f"error: unknown client_id={client_id!r}"

        # 【关键校验 A】redirect_uri 必须**精确匹配**注册值。
        # 用 startswith() / 通配符匹配是经典漏洞：攻击者可用
        # https://app.example.com/callback.evil.com 或 /callback/../evil 绕过。
        if redirect_uri not in client["redirect_uris"]:
            self._log(f"authorize REJECT: redirect_uri mismatch {redirect_uri!r}")
            return "error: redirect_uri is not exactly registered"

        # 【关键校验 B】response_type 只允许 code（隐式模式已废弃）
        if params.get("response_type") != "code":
            return "error: only response_type=code is supported"

        # 【关键校验 C】公开客户端必须带 PKCE，且 method 必须是 S256
        if client["public"]:
            if not params.get("code_challenge"):
                self._log("authorize REJECT: public client without PKCE")
                return "error: PKCE required for public clients"
            if params.get("code_challenge_method") != "S256":
                # 'plain' 等于明文传 verifier，PKCE 形同虚设
                return "error: code_challenge_method must be S256"

        # 真实场景：这里会把用户带到登录页 + 同意页
        user = params.get("_simulated_user", "alice")

        code = b64url(secrets.token_bytes(32))
        self.codes[code] = AuthCode(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=params.get("scope", ""),
            user=user,
            code_challenge=params.get("code_challenge", ""),
            code_challenge_method=params.get("code_challenge_method", ""),
            expires_at=time.time() + self.CODE_TTL,
        )
        self._log(f"authorize OK user={user} client={client_id}")

        # 授权服务器把 state **原样回传**（它自己不做任何校验，
        # 校验是客户端的责任！这是很多人搞混的点）
        qs = urllib.parse.urlencode({
            "code": code,
            "state": params.get("state", ""),
        })
        return f"{redirect_uri}?{qs}"

    # ── 端点 2：POST /token ───────────────────────────────────
    def token(self, form: dict) -> dict:
        grant = form.get("grant_type")
        if grant == "authorization_code":
            return self._token_from_code(form)
        if grant == "refresh_token":
            return self._token_from_refresh(form)
        return {"error": "unsupported_grant_type"}

    def _token_from_code(self, form: dict) -> dict:
        code = form.get("code", "")
        rec = self.codes.get(code)

        # 【校验】授权码必须存在、未使用、未过期、且绑定同一客户端
        if rec is None:
            self._log(f"token REJECT: invalid code")
            return {"error": "invalid_grant", "detail": "unknown code"}
        if rec.used:
            # ⚠️ 真实生产：授权码被重复使用应该**吊销该用户全部令牌**，
            # 因为这通常意味着授权码泄漏（RFC 6749 §4.1.2）
            self._log("token REJECT: code replay detected!")
            return {"error": "invalid_grant", "detail": "code already used"}
        if time.time() > rec.expires_at:
            return {"error": "invalid_grant", "detail": "code expired"}
        if form.get("client_id") != rec.client_id:
            return {"error": "invalid_grant", "detail": "client mismatch"}
        if form.get("redirect_uri") != rec.redirect_uri:
            return {"error": "invalid_grant", "detail": "redirect_uri mismatch"}

        client = self.clients[rec.client_id]

        # 【校验】机密客户端必须提供正确的 client_secret
        if not client["public"]:
            if form.get("client_secret") != client["client_secret"]:
                self._log("token REJECT: bad client_secret")
                return {"error": "invalid_client"}

        # 【校验】PKCE：重新算 SHA256(verifier) 与授权时存下的 challenge 比对
        if rec.code_challenge:
            verifier = form.get("code_verifier", "")
            if not verifier:
                return {"error": "invalid_grant", "detail": "code_verifier missing"}
            if s256(verifier) != rec.code_challenge:
                self._log("token REJECT: PKCE verification failed")
                return {"error": "invalid_grant", "detail": "PKCE mismatch"}

        rec.used = True   # 一次性：用后即焚

        return self._issue(rec.user, rec.scope)

    def _token_from_refresh(self, form: dict) -> dict:
        rt = form.get("refresh_token", "")
        user = self.refresh_tokens.pop(rt, None)   # 轮转：旧的立刻作废
        if user is None:
            self._log("token REJECT: invalid/rotated refresh_token")
            return {"error": "invalid_grant"}

        # 真实实现要校验 client_id 与最初授权时一致
        return self._issue(user, form.get("scope", ""))

    def _issue(self, user: str, scope: str) -> dict:
        at = b64url(secrets.token_bytes(24))
        rt = b64url(secrets.token_bytes(24))
        self.access_tokens[at] = TokenRecord(
            user=user, scope=scope, expires_at=time.time() + self.ACCESS_TTL
        )
        self.refresh_tokens[rt] = user
        self._log(f"issue tokens for user={user} scope={scope!r}")
        return {
            "access_token": at,
            "refresh_token": rt,
            "token_type": "Bearer",
            "expires_in": self.ACCESS_TTL,
            "scope": scope,
        }

    # ── 端点 3：GET /userinfo（资源服务器）────────────────────
    def userinfo(self, authorization: str) -> dict:
        if not authorization.startswith("Bearer "):
            return {"error": "invalid_token", "detail": "missing bearer"}
        at = authorization[7:]
        rec = self.access_tokens.get(at)
        if rec is None or rec.revoked:
            return {"error": "invalid_token"}
        if time.time() > rec.expires_at:
            return {"error": "invalid_token", "detail": "expired"}
        return {"sub": rec.user, "email": f"{rec.user}@example.com", "scope": rec.scope}

    def revoke(self, at: str) -> None:
        if at in self.access_tokens:
            self.access_tokens[at].revoked = True
            self._log("token revoked")


# ══════════════════════════════════════════════════════════════════
# ② 客户端（Browser / App / 后端）
# ══════════════════════════════════════════════════════════════════

class OAuthClient:
    def __init__(self, server: MiniAuthServer, client_id: str,
                 redirect_uri: str, use_pkce: bool):
        self.server = server
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.use_pkce = use_pkce
        secret = server.clients[client_id]["client_secret"]
        self.client_secret = secret

        # 会话级状态：真实实现里 state 存在服务端 session 或加密 Cookie 里
        self.session = {}

    # ── 步骤 1：构造授权请求 ─────────────────────────────────
    def build_authorize_url(self, scope: str) -> str:
        # state：防 CSRF 的随机串，高熵、一次性
        self.session["state"] = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "state": self.session["state"],
        }

        if self.use_pkce:
            # code_verifier 只存在于客户端内存，永远不经过浏览器 URL
            self.session["code_verifier"] = b64url(secrets.token_bytes(48))
            params["code_challenge"] = s256(self.session["code_verifier"])
            params["code_challenge_method"] = "S256"

        return "https://auth.example.com/authorize?" + urllib.parse.urlencode(params)

    # ── 步骤 2：处理回调，校验 state ─────────────────────────
    def handle_callback(self, callback_url: str) -> str | None:
        parsed = urllib.parse.urlparse(callback_url)
        q = urllib.parse.parse_qs(parsed.query)

        # ⚠️ 必须校验 state：不校验 = 任何人都能拿自己的 code 绑你的账号
        got_state = q.get("state", [""])[0]
        if not secrets.compare_digest(got_state, self.session.get("state", "")):
            print("  ❌ state 校验失败，拒绝这次授权（可能是 CSRF 攻击）")
            return None

        # state 用后即焚，防止重放
        del self.session["state"]

        if "error" in q:
            print(f"  ❌ 授权被拒绝: {q['error']}")
            return None
        return q.get("code", [None])[0]

    # ── 步骤 3：用 code 换 token ─────────────────────────────
    def exchange_code(self, code: str) -> dict:
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
        }
        if self.client_secret:
            form["client_secret"] = self.client_secret
        if self.use_pkce:
            form["code_verifier"] = self.session.pop("code_verifier")

        tokens = self.server.token(form)
        if "access_token" in tokens:
            self.session["tokens"] = tokens  # 真实实现：放服务端 session 或 HttpOnly Cookie
        return tokens

    def call_api(self, path: str) -> dict:
        tokens = self.session.get("tokens", {})
        return self.server.userinfo(f"Bearer {tokens.get('access_token', '')}")

    def refresh(self) -> dict:
        tokens = self.session.get("tokens", {})
        new = self.server.token({
            "grant_type": "refresh_token",
            "refresh_token": tokens.get("refresh_token", ""),
            "client_id": self.client_id,
            "client_secret": self.client_secret or "",
        })
        if "access_token" in new:
            self.session["tokens"] = new
        return new


# ══════════════════════════════════════════════════════════════════
# ③ 主流程
# ══════════════════════════════════════════════════════════════════

def run_flow(use_pkce: bool) -> None:
    server = MiniAuthServer()
    client = OAuthClient(
        server,
        client_id="webapp" if not use_pkce else "mobileapp",
        redirect_uri="https://app.example.com/callback" if not use_pkce else "myapp://cb",
        use_pkce=use_pkce,
    )

    mode = "授权码 + PKCE（公开客户端）" if use_pkce else "授权码（机密客户端）"
    banner(f"流程演示：{mode}")

    url = client.build_authorize_url(scope="profile email")
    print(f"1. 客户端生成授权 URL:\n   {url[:120]}...")

    # 模拟：用户点了"同意授权"（真实场景这里会先跳登录页 + 同意页）
    server_params = {
        "response_type": "code",
        "client_id": client.client_id,
        "redirect_uri": client.redirect_uri,
        "scope": "profile email",
        "state": client.session["state"],
    }
    if use_pkce:
        server_params["code_challenge"] = s256(client.session["code_verifier"])
        server_params["code_challenge_method"] = "S256"
    callback = server.authorize(server_params)
    print(f"2. 授权服务器回调（浏览器只看到 code）:\n   {callback[:90]}...")

    code = client.handle_callback(callback)
    if code is None:
        return
    print(f"3. ✅ state 校验通过，拿到授权码: {code[:16]}...")

    tokens = client.exchange_code(code)
    if "error" in tokens:
        print(f"4. ❌ 换令牌失败: {tokens}")
        return
    print(f"4. ✅ 拿到令牌: access_token={tokens['access_token'][:16]}... "
          f"expires_in={tokens['expires_in']}s")

    info = client.call_api("/userinfo")
    print(f"5. ✅ 调用受保护接口: {info}")

    # ── 演示授权码一次性：重放同一个 code 会失败 ──
    print("\n6. 攻击者重放刚才那个授权码（应被拒绝）:")
    print(f"   → {server.token({'grant_type': 'authorization_code', 'code': code, 'client_id': client.client_id, 'redirect_uri': client.redirect_uri, 'client_secret': client.client_secret or '', 'code_verifier': ''})}")

    # ── 演示 access_token 过期 + refresh ──
    print(f"\n7. 等 {MiniAuthServer.ACCESS_TTL + 1} 秒让 access_token 过期……")
    time.sleep(MiniAuthServer.ACCESS_TTL + 1)
    print(f"   过期后调用接口: {client.call_api('/userinfo')}")
    new = client.refresh()
    print(f"8. ✅ 用 refresh_token 换新令牌: "
          f"access_token={new['access_token'][:16]}...（旧 refresh 已作废/轮转）")
    print(f"   现在调用接口: {client.call_api('/userinfo')}")

    # ── 撤销演示 ──
    at = client.session["tokens"]["access_token"]
    server.revoke(at)
    print(f"9. 主动撤销令牌后调用接口: {client.call_api('/userinfo')}")

    print("\n📋 服务端审计日志（真实系统里这就是安全事件溯源）:")
    for line in server.audit_log:
        print("   " + line)


def main() -> None:
    run_flow(use_pkce=False)
    run_flow(use_pkce=True)

    banner("小结")
    print("""
• 授权码只经过浏览器，且一次性、60 秒过期 → 泄漏了也换不到令牌
• access_token 只在"服务器↔服务器"之间传输 → 浏览器永远看不到
• state 由**客户端**校验，防 CSRF；PKCE 由**授权服务器**校验，防 code 劫持
• 授权码被重放 = 强危险信号，生产环境应吊销该用户所有令牌
• 令牌要能过期、能刷新（轮转）、能撤销，这才叫"可控凭证"
""")


# ══════════════════════════════════════════════════════════════════
# ④ 离线自检（--self-test）
# ══════════════════════════════════════════════════════════════════

def self_test() -> None:
    """离线自检：不联网 / 不用第三方库 / 不 sleep，重复运行结果完全一致。

    自检覆盖的安全属性（每一条都是本文件想教的东西）：
      1) PKCE 的 S256 变换与 **RFC 7636 附录 B 官方向量**逐字节一致
         —— 这是"我的实现没写反"的最硬证据（比自说自话强得多）；
      2) 授权端点的四道关卡：client_id / redirect_uri 精确匹配 /
         response_type / 公开客户端强制 PKCE(S256)；
      3) 授权码一次性：重放同一个 code 必须被拒；
      4) state 必须与会话中一致，否则回调直接返回 None；
      5) PKCE：verifier 对不上 → 拒；且**拒一次不会把 code 烧掉**
         （授权服务器在校验通过前不能置 used，否则就是自己制造 DoS 漏洞）；
      6) 令牌生命周期：过期 / 刷新轮转 / 撤销，三件事都能被验证；
      7) 审计日志里**不能出现**令牌或授权码原文。
    """
    checks: list[tuple[str, object, object]] = []

    def eq(name: str, actual: object, expected: object) -> None:
        checks.append((name, actual, expected))

    # ── 1) 算法正确性：对照 RFC 7636 附录 B 的官方测试向量 ──────────
    # 这两行常量来自 RFC 7636 Appendix B，任何实现都必须算出同一个 challenge。
    # 踩坑点：如果你用了标准 base64（带 '+' '/' '='）或忘了 rstrip('=')，
    #        这一条会立刻红 —— 而这正是"和第三方服务器对不上"的常见原因。
    RFC7636_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    RFC7636_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    eq("S256 与 RFC 7636 官方向量一致", s256(RFC7636_VERIFIER), RFC7636_CHALLENGE)
    eq("b64url 去掉了填充等号", b64url(b"a"), "YQ")

    # ── 2) 授权端点的四道关卡 ────────────────────────────────
    srv = MiniAuthServer()
    base = {
        "client_id": "webapp",
        "redirect_uri": "https://app.example.com/callback",
        "response_type": "code",
    }
    eq("未知 client_id 被拒",
       srv.authorize({**base, "client_id": "nope"}),
       "error: unknown client_id='nope'")
    eq("redirect_uri 追加后缀被拒（前缀匹配是漏洞，精确匹配才拦得住）",
       srv.authorize({**base, "redirect_uri": "https://app.example.com/callback.evil.com"}),
       "error: redirect_uri is not exactly registered")
    eq("response_type=token（隐式模式）被拒",
       srv.authorize({**base, "response_type": "token"}),
       "error: only response_type=code is supported")
    eq("公开客户端缺 PKCE 被拒",
       srv.authorize({"client_id": "mobileapp", "redirect_uri": "myapp://cb",
                      "response_type": "code"}),
       "error: PKCE required for public clients")
    eq("PKCE plain 模式被拒",
       srv.authorize({"client_id": "mobileapp", "redirect_uri": "myapp://cb",
                      "response_type": "code", "code_challenge": "abc",
                      "code_challenge_method": "plain"}),
       "error: code_challenge_method must be S256")

    # ── 3) 机密客户端完整流程（无 PKCE）─────────────────────
    srv = MiniAuthServer()
    web = OAuthClient(srv, "webapp", "https://app.example.com/callback", use_pkce=False)
    url = web.build_authorize_url("profile email")
    eq("授权 URL 使用 response_type=code", "response_type=code" in url, True)
    eq("授权 URL 带回注册的 redirect_uri",
       "redirect_uri=https%3A%2F%2Fapp.example.com%2Fcallback" in url, True)

    cb = srv.authorize({"response_type": "code", "client_id": web.client_id,
                        "redirect_uri": web.redirect_uri, "scope": "profile email",
                        "state": web.session["state"]})
    code = web.handle_callback(cb)
    eq("回调拿到授权码（长度足够，非空）", isinstance(code, str) and len(code) >= 32, True)
    tokens = web.exchange_code(code)
    eq("拿到 access_token", "access_token" in tokens, True)
    eq("access_token 只经由后端通道发放（token_type=Bearer）", tokens["token_type"], "Bearer")
    at, rt = tokens["access_token"], tokens["refresh_token"]
    eq("用令牌访问 /userinfo 成功",
       srv.userinfo("Bearer " + at), {"sub": "alice", "email": "alice@example.com",
                                      "scope": "profile email"})
    eq("授权码重放被拒（一次性）",
       srv.token({"grant_type": "authorization_code", "code": code,
                  "client_id": web.client_id, "redirect_uri": web.redirect_uri,
                  "client_secret": web.client_secret})["detail"],
       "code already used")
    eq("服务端审计日志记下了重放事件",
       any("code replay" in line for line in srv.audit_log), True)

    # ── 4) state 校验失败必须拒绝回调 ────────────────────────
    web2 = OAuthClient(srv, "webapp", "https://app.example.com/callback", use_pkce=False)
    web2.build_authorize_url("profile")
    # ⚠️ 这里的回调**故意**用错的 state，handle_callback 会往 stdout 打印一行
    #    "❌ state 校验失败"。自检要的是干净的 PASS/FAIL 列表，所以临时把它
    #    的输出吞掉；断言本身照旧（这行 ❌ 在演示模式下才是给人看的）。
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        state_result = web2.handle_callback(
            "https://app.example.com/callback?code=x&state=ATTACKER_STATE")
    eq("state 不匹配 → 回调返回 None（拦下 CSRF）", state_result, None)

    # ── 5) PKCE 公开客户端流程 ───────────────────────────────
    srv3 = MiniAuthServer()
    mob = OAuthClient(srv3, "mobileapp", "myapp://cb", use_pkce=True)
    mob.build_authorize_url("profile")
    verifier = mob.session["code_verifier"]
    cb = srv3.authorize({"response_type": "code", "client_id": "mobileapp",
                         "redirect_uri": "myapp://cb",
                         "code_challenge": s256(verifier),
                         "code_challenge_method": "S256",
                         "state": mob.session["state"]})
    pcode = mob.handle_callback(cb)
    eq("PKCE 流程也能拿到授权码", isinstance(pcode, str) and len(pcode) >= 32, True)

    # 攻击者拿着 code 但不知道 verifier → 换不到令牌
    eq("PKCE verifier 对不上 → 拒绝",
       srv3.token({"grant_type": "authorization_code", "code": pcode,
                   "client_id": "mobileapp", "redirect_uri": "myapp://cb",
                   "code_verifier": "attacker-guess"})["detail"],
       "PKCE mismatch")
    eq("PKCE 缺 verifier → 拒绝",
       srv3.token({"grant_type": "authorization_code", "code": pcode,
                   "client_id": "mobileapp", "redirect_uri": "myapp://cb"})["detail"],
       "code_verifier missing")
    # ⚠️ 关键细节：上面两次失败**不能**把 code 烧掉（否则攻击者可以故意
    #    用错 verifier 来 DoS 合法用户）。正确实现只在全部校验通过后才置 used。
    mob_tokens = mob.exchange_code(pcode)
    eq("校验失败的尝试不会烧掉授权码（防 DoS）", "access_token" in mob_tokens, True)

    # ── 6) 令牌生命周期：过期 / 刷新轮转 / 撤销（不 sleep）────
    m_at = mob_tokens["access_token"]
    m_rt = mob_tokens["refresh_token"]
    srv3.access_tokens[m_at].expires_at = time.time() - 1     # 手动拨到过去 = 等价于睡了 3 秒
    eq("过期 access_token 被拒",
       srv3.userinfo("Bearer " + m_at)["detail"], "expired")
    fresh = mob.refresh()
    eq("refresh_token 换到新 access_token", "access_token" in fresh, True)
    eq("refresh_token 轮转：旧的立刻失效",
       srv3.token({"grant_type": "refresh_token", "refresh_token": m_rt})["error"],
       "invalid_grant")
    eq("新 access_token 可用", srv3.userinfo("Bearer " + fresh["access_token"])["sub"], "alice")
    srv3.revoke(fresh["access_token"])
    eq("撤销后 access_token 立刻不可用",
       srv3.userinfo("Bearer " + fresh["access_token"]), {"error": "invalid_token"})

    # ── 7) 日志卫生：审计日志不得泄漏令牌/授权码原文 ──────────
    log_text = "\n".join(srv3.audit_log)
    eq("审计日志不含 access_token 原文", m_at in log_text, False)
    eq("审计日志不含授权码原文", pcode in log_text, False)

    # ── 汇总输出 ────────────────────────────────────────────
    bad = 0
    for name, actual, expected in checks:
        if actual == expected:
            print(f"  [PASS] {name}")
        else:
            bad += 1
            print(f"  [FAIL] {name}\n         实际值 = {actual!r}\n         期望值 = {expected!r}")
    if bad:
        print(f"\n自检失败：{bad}/{len(checks)} 项与期望不符")
        sys.exit(1)
    print(f"\n共 {len(checks)} 项断言全部通过")
    print("SELF-TEST OK")
    sys.exit(0)


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        self_test()
    else:
        main()
