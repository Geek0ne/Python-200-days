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
    python3 01-oauth2-auth-code-flow.py

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


if __name__ == "__main__":
    main()
