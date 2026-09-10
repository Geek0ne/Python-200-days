#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 150 · 示例 03：认证系统安全审计脚本（实战案例）
====================================================

把今天 README 里的"安全基线检查表"变成一个**可自动运行、可接 CI** 的审计器。

它做四件事：
  1. 审计 OAuth2 客户端配置（state / PKCE / redirect_uri / 弃用模式 / 令牌有效期）
  2. 审计会话 Cookie 标志（HttpOnly / Secure / SameSite / Path）
  3. 审计 CSRF 防护（是否启用 Token、是否只保护 POST、GET 是否有副作用）
  4. **SSRF 检测**：对"用户可控 URL"做协议/主机/IP 白名单校验

输出 PASS / WARN / FAIL 分级报告，并返回退出码：
  0 = 全部通过（允许 WARN）   1 = 存在 FAIL（CI 里应阻断发布）

运行：
    python3 03-auth-security-audit.py
    python3 03-auth-security-audit.py --json      # 机器可读输出

⚠️ 本脚本只做**静态配置审计 + 本地 URL 校验**，不会主动去请求任何目标地址。
   真实渗透测试请务必先取得书面授权！
"""

from __future__ import annotations

import ipaddress
import json
import socket
import sys
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import Any


# ══════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════

@dataclass
class Finding:
    level: str        # PASS | WARN | FAIL
    check: str        # 检查项 ID
    title: str
    detail: str = ""
    fix: str = ""


@dataclass
class Report:
    target: str
    findings: list = field(default_factory=list)

    def add(self, level: str, check: str, title: str,
            detail: str = "", fix: str = "") -> None:
        self.findings.append(Finding(level, check, title, detail, fix))

    @property
    def counts(self) -> dict:
        c = {"PASS": 0, "WARN": 0, "FAIL": 0}
        for f in self.findings:
            c[f.level] += 1
        return c

    @property
    def has_failure(self) -> bool:
        return self.counts["FAIL"] > 0

    def render(self) -> str:
        icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}
        out = ["", "═" * 74, f"  认证系统安全审计报告 — {self.target}", "═" * 74]
        for f in self.findings:
            out.append(f"{icon[f.level]} [{f.level}] {f.check} {f.title}")
            if f.detail:
                out.append(f"        · 现状: {f.detail}")
            if f.fix and f.level != "PASS":
                out.append(f"        · 建议: {f.fix}")
        c = self.counts
        out += ["─" * 74,
                f"  合计: ✅ {c['PASS']} 个通过 / ⚠️  {c['WARN']} 个警告 / "
                f"❌ {c['FAIL']} 个失败",
                "═" * 74]
        return "\n".join(out)


# ══════════════════════════════════════════════════════════════════
# ① OAuth2 配置审计
# ══════════════════════════════════════════════════════════════════

DEPRECATED_METHODS = {"plain"}          # 只允许 S256
DEPRECATED_GRANTS = {"implicit", "password", "token"}


def audit_oauth2(cfg: dict, rpt: Report) -> None:
    """cfg 形如：
    {
      "response_type": "code",
      "uses_state": true,
      "state_length": 43,
      "state_stored_in_session": true,
      "pkce": {"enabled": true, "method": "S256"},
      "redirect_uris": ["https://app.example.com/callback"],
      "registered_redirect_uris": ["https://app.example.com/callback"],
      "enabled_grants": ["authorization_code", "refresh_token"],
      "access_token_ttl": 900,
      "refresh_token_rotation": true,
      "https_everywhere": true,
      "revocation_endpoint": true,
    }
    """
    # 1) response_type
    if cfg.get("response_type") in DEPRECATED_GRANTS:
        rpt.add("FAIL", "OAUTH-01", "使用了已废弃的隐式/密码模式",
                f"response_type={cfg.get('response_type')}",
                "改用 response_type=code + PKCE（RFC 9700 建议）")
    else:
        rpt.add("PASS", "OAUTH-01", f"授权模式为 {cfg.get('response_type')}")

    # 2) state 防护
    if not cfg.get("uses_state"):
        rpt.add("FAIL", "OAUTH-02", "授权请求缺少 state 参数",
                "回调无法防 CSRF，攻击者可用自己的 code 绑定受害者账号",
                "生成 secrets.token_urlsafe(32) 存入会话，回调中比对并立即删除")
    elif not cfg.get("state_length", 0) >= 32:
        rpt.add("WARN", "OAUTH-02", "state 熵可能不足",
                f"长度 {cfg.get('state_length')}",
                "建议 >= 32 字符，且来自密码学安全随机源（secrets，不是 random）")
    elif not cfg.get("state_stored_in_session", False):
        rpt.add("FAIL", "OAUTH-02", "state 未绑定到用户会话",
                "state 若可被攻击者预知/复用，等于没有防护",
                "state 必须存在服务端 session 或加密 Cookie，且一次性")
    else:
        rpt.add("PASS", "OAUTH-02", "state 存在、长度充足、绑定会话")

    # 3) PKCE
    pkce = cfg.get("pkce", {})
    if not pkce.get("enabled"):
        rpt.add("WARN", "OAUTH-03", "未启用 PKCE",
                "公开客户端（SPA / 移动 App）必须启用",
                "使用 code_challenge_method=S256")
    elif pkce.get("method") in DEPRECATED_METHODS:
        rpt.add("FAIL", "OAUTH-03", "PKCE 使用了 plain 模式",
                f"method={pkce.get('method')}",
                "必须用 S256：challenge=Base64URL(SHA256(verifier))")
    else:
        rpt.add("PASS", "OAUTH-03", f"PKCE 已启用，method={pkce.get('method')}")

    # 4) redirect_uri 精确匹配
    used = cfg.get("redirect_uris", [])
    registered = cfg.get("registered_redirect_uris", [])
    bad = [u for u in used if u not in registered]
    if bad:
        rpt.add("FAIL", "OAUTH-04", "存在未精确注册的 redirect_uri",
                f"未注册: {bad}",
                "redirect_uri 必须与注册值**完全一致**，禁止前缀/通配/正则匹配")
    else:
        rpt.add("PASS", "OAUTH-04", "redirect_uri 全部精确匹配注册值")

    # 5) 全链路 HTTPS
    if not cfg.get("https_everywhere", False):
        rpt.add("FAIL", "OAUTH-05", "存在非 HTTPS 链路", "redirect_uri 含 http://",
                "授权/令牌/回调/资源全部强制 HTTPS，并启用 HSTS")
    else:
        rpt.add("PASS", "OAUTH-05", "全链路 HTTPS")

    # 6) 令牌生命周期
    ttl = cfg.get("access_token_ttl", 0)
    if ttl == 0:
        rpt.add("FAIL", "OAUTH-06", "access_token 永不过期", "TTL=0",
                "设置 5~60 分钟有效期，并配合 refresh token")
    elif ttl > 3600:
        rpt.add("WARN", "OAUTH-06", "access_token 有效期偏长", f"{ttl}s (>1h)",
                "缩短到 5~60 分钟，用 refresh token 续期")
    else:
        rpt.add("PASS", "OAUTH-06", f"access_token 有效期合理（{ttl}s）")

    if not cfg.get("refresh_token_rotation", False):
        rpt.add("WARN", "OAUTH-07", "refresh_token 未轮转",
                "刷新后旧 refresh_token 仍有效",
                "启用 Rotation：每次刷新作废旧 token，检测到重放即吊销整条链")
    else:
        rpt.add("PASS", "OAUTH-07", "refresh_token 已启用轮转")

    if not cfg.get("revocation_endpoint", False):
        rpt.add("WARN", "OAUTH-08", "未提供令牌撤销端点",
                "用户登出/改密后旧令牌仍可用",
                "实现 RFC 7009 revocation 端点，并在改密/登出时吊销")
    else:
        rpt.add("PASS", "OAUTH-08", "支持令牌撤销")

    # 7) 启用的 grant 类型
    deprecated_enabled = DEPRECATED_GRANTS & set(cfg.get("enabled_grants", []))
    if deprecated_enabled:
        rpt.add("FAIL", "OAUTH-09", "仍启用了废弃的 grant",
                f"{sorted(deprecated_enabled)}",
                "关闭 implicit / password grant")
    else:
        rpt.add("PASS", "OAUTH-09", "未启用废弃 grant 类型")


# ══════════════════════════════════════════════════════════════════
# ② Cookie / 会话审计
# ══════════════════════════════════════════════════════════════════

def audit_cookie(cookie: dict, rpt: Report) -> None:
    """cookie 形如 {"name": "session", "httponly": True, "secure": True,
    "samesite": "Lax", "path": "/", "max_age": 3600, "domain": None}"""
    name = cookie.get("name", "?")
    if not cookie.get("httponly"):
        rpt.add("FAIL", "COOKIE-01", f"Cookie `{name}` 缺少 HttpOnly",
                "JS 可读 → 一次 XSS 即可窃取会话",
                "加上 HttpOnly；如必须 JS 读取请重新评估方案")
    else:
        rpt.add("PASS", "COOKIE-01", f"Cookie `{name}` 有 HttpOnly")

    if not cookie.get("secure"):
        rpt.add("FAIL", "COOKIE-02", f"Cookie `{name}` 缺少 Secure",
                "明文 HTTP 下会被中间人窃听",
                "加上 Secure（同时确保全站 HTTPS）")
    else:
        rpt.add("PASS", "COOKIE-02", f"Cookie `{name}` 有 Secure")

    samesite = (cookie.get("samesite") or "unset").lower()
    if samesite in ("unset", "none"):
        rpt.add("FAIL", "COOKIE-03", f"Cookie `{name}` SameSite={samesite}",
                "跨站请求会携带该 Cookie，CSRF 风险高",
                "改为 SameSite=Lax（默认推荐）或 Strict；"
                "若必须 None，必须同时设置 Secure 并配合 CSRF Token")
    elif samesite == "lax":
        rpt.add("PASS", "COOKIE-03", f"Cookie `{name}` SameSite=Lax")
    else:
        rpt.add("PASS", "COOKIE-03", f"Cookie `{name}` SameSite=Strict")

    # 会话 Cookie 不应设置过宽的 Domain
    if cookie.get("domain"):
        rpt.add("WARN", "COOKIE-04", f"Cookie `{name}` 设置了 Domain",
                f"domain={cookie['domain']}",
                "尽量不设置 Domain（Host-Only），缩小作用范围，降低子域被攻陷的影响")
    else:
        rpt.add("PASS", "COOKIE-04", f"Cookie `{name}` 为 Host-Only")

    if cookie.get("max_age", 0) > 30 * 24 * 3600:
        rpt.add("WARN", "COOKIE-05", f"Cookie `{name}` 有效期过长",
                f"{cookie['max_age']}s (>30 天)",
                "会话 Cookie 建议不超过 7 天，配合滑动续期")


# ══════════════════════════════════════════════════════════════════
# ③ CSRF 防护审计
# ══════════════════════════════════════════════════════════════════

def audit_csrf(csrf: dict, rpt: Report) -> None:
    if not csrf.get("token_enabled"):
        rpt.add("FAIL", "CSRF-01", "未启用 CSRF Token",
                "仅依赖 Cookie 的会话无法区分攻击者伪造的请求",
                "对状态改变请求使用 Synchronizer Token 或 Double Submit Cookie")
    else:
        rpt.add("PASS", "CSRF-01", "已启用 CSRF Token")

    if not csrf.get("token_verified_server_side", False):
        rpt.add("FAIL", "CSRF-02", "CSRF Token 未在服务端比对",
                "前端生成但不校验 = 没有防护",
                "服务端用 secrets.compare_digest 比对（常量时间，防时序攻击）")
    else:
        rpt.add("PASS", "CSRF-02", "CSRF Token 服务端比对")

    if csrf.get("tokens_reused"):
        rpt.add("WARN", "CSRF-03", "CSRF Token 长期复用",
                "同一个 token 反复使用会降低防护强度",
                "考虑每个会话一个 + 定期轮换；敏感操作可一次性 token")

    mutating_get = csrf.get("get_has_side_effects", False)
    if mutating_get:
        rpt.add("FAIL", "CSRF-04", "存在有副作用的 GET 请求",
                "GET 应幂等，浏览器可直接通过 <img>/<a> 触发 → SameSite=Lax 也防不住",
                "所有状态改变操作改为 POST/PUT/DELETE + CSRF Token")
    else:
        rpt.add("PASS", "CSRF-04", "GET 请求无副作用")

    if not csrf.get("origin_checked", False):
        rpt.add("WARN", "CSRF-05", "未校验 Origin/Referer",
                "缺少一层补充防护",
                "校验 Origin 是否在严格白名单（精确匹配，勿用后缀匹配）")
    else:
        rpt.add("PASS", "CSRF-05", "已校验 Origin/Referer")

    if csrf.get("json_only_relied", False):
        rpt.add("WARN", "CSRF-06", "仅靠 Content-Type 判断防护 CSRF",
                "把 Content-Type 当 CSRF 防护是不可靠的隐式假设",
                "显式加上 CSRF Token / SameSite")


# ══════════════════════════════════════════════════════════════════
# ④ SSRF 检测（核心实战部分）
# ══════════════════════════════════════════════════════════════════

# 云元数据服务地址（SSRF 最想打的目标：能换云凭证）
METADATA_HOSTS = {
    "169.254.169.254",          # AWS / Azure / GCP / OpenStack
    "metadata.google.internal",  # GCP
    "100.100.100.200",           # 阿里云
    "169.254.170.2",             # AWS ECS task metadata
    "fd00:ec2::254",             # AWS IMDS IPv6
}

ALLOWED_SCHEMES = {"http", "https"}
DANGEROUS_SCHEMES = {"file", "gopher", "dict", "ftp", "ldap", "tftp", "jar"}

# 私有/保留网段（IPv4 + IPv6）
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> tuple[bool, str]:
    for net in BLOCKED_NETWORKS:
        if ip.version == net.version and ip in net:
            return True, str(net)
    return False, ""


def check_url_ssrf(raw_url: str, allowed_hosts: set[str] | None = None,
                   resolve_dns: bool = True) -> list[Finding]:
    """对**一个**用户可控 URL 做 SSRF 风险检测。

    返回 Finding 列表。注意这里只做**检测/判定**，不发起任何网络请求。

    检测顺序（也就是正确防护的顺序）：
      1) 协议白名单
      2) 禁用凭据（user:pass@）
      3) 域名白名单（若有）
      4) 主机名解析为 IP → 检查私有段/元数据地址
      5) 检测十进制/十六进制/IPv6 映射等混淆写法
      6) 重定向风险提示
    """
    findings: list[Finding] = []

    if not raw_url:
        return findings

    # ── 混淆写法检测（解析前先做文本级嗅探）──────────────────
    lowered = raw_url.strip().lower()
    obfuscation_hits = []
    # http://2130706433/  十进制 IP == 127.0.0.1
    if any(s in lowered for s in ("2130706433", "017700000001", "0x7f000001", "0x7f.0.0.1")):
        obfuscation_hits.append("疑似十进制/十六进制/八进制编码的 127.0.0.1")
    # http://expected.com@evil.com/
    if "@" in urllib.parse.urlparse(raw_url).netloc:
        obfuscation_hits.append("netloc 含 '@'，可能存在 userinfo 混淆")
    if "%00" in lowered:
        obfuscation_hits.append("含 %00 空字节，可能用于绕过校验")
    if obfuscation_hits:
        findings.append(Finding(
            "FAIL", "SSRF-06", "URL 中存在混淆/绕过特征",
            "; ".join(obfuscation_hits),
            "对 URL 先规范化再做校验；拒绝含 userinfo/空字节/异常编码的输入"))

    parsed = urllib.parse.urlparse(raw_url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()

    # ── 1) 协议 ───────────────────────────────────────────
    if scheme in DANGEROUS_SCHEMES:
        findings.append(Finding(
            "FAIL", "SSRF-01", f"危险协议 `{scheme}://`",
            "可用于读取本地文件或攻击内网服务（gopher 甚至能发原始 TCP）",
            "协议白名单只允许 http/https"))
    elif scheme not in ALLOWED_SCHEMES:
        findings.append(Finding(
            "FAIL", "SSRF-01", f"协议不在白名单: `{scheme or '(空)'}`",
            "", "只允许 http / https"))
    else:
        findings.append(Finding("PASS", "SSRF-01", f"协议 {scheme}:// 在白名单内"))

    if not host:
        findings.append(Finding("FAIL", "SSRF-02", "URL 缺少主机名", "",
                                "校验失败直接拒绝，不要兜底成默认地址"))
        return findings

    # ── 2) 凭据 ───────────────────────────────────────────
    if parsed.username or parsed.password:
        findings.append(Finding(
            "FAIL", "SSRF-02", "URL 中携带凭据（user:pass@host）",
            "常用于混淆真实主机，且会把凭据泄漏给目标",
            "拒绝含 userinfo 的 URL"))

    # ── 3) 主机白名单 ─────────────────────────────────────
    if allowed_hosts is not None:
        exact = host in allowed_hosts
        # 后缀匹配是常见错误：evil.com 的域名可以写成 "expected.com.evil.com"
        if exact:
            findings.append(Finding("PASS", "SSRF-03", f"主机 {host} 命中白名单"))
        else:
            findings.append(Finding(
                "FAIL", "SSRF-03", f"主机 {host} 不在白名单",
                f"白名单: {sorted(allowed_hosts)}",
                "使用精确匹配；不要用 endswith/后缀匹配（可被 evil.com 绕过）。"
                "更好的做法：用 `id -> URL` 映射表，根本不接收任意 URL"))

    # ── 4) 元数据 & IP 检查 ───────────────────────────────
    if host in METADATA_HOSTS:
        findings.append(Finding(
            "FAIL", "SSRF-04", f"目标是云元数据地址 `{host}`",
            "元数据服务可换取云临时凭证 → 可能直接接管云主机/云账号",
            "永久封禁该地址；启用 IMDSv2（需要 token 头）等云侧加固"))

    # 直接是 IP 字面量 → 无需 DNS 即可判定
    literal_ip: ipaddress._BaseAddress | None = None
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        blocked, net = _is_blocked_ip(literal_ip)
        if blocked:
            findings.append(Finding(
                "FAIL", "SSRF-05", f"IP 字面量命中受限网段: {literal_ip} (in {net})",
                "内网/回环/保留地址，SSRF 高危目标",
                "解析后校验 IP，禁止私有段/回环/链路本地/组播"))
        else:
            findings.append(Finding("PASS", "SSRF-05", f"IP 字面量 {literal_ip} 为公网地址"))
    elif resolve_dns:
        # 域名 → 解析 → 校验。⚠️ 真实防护中必须在**发起连接时**用同一个 IP，
        # 否则中间可能发生 DNS Rebinding（校验时公网、连接时内网）。
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            ips = sorted({i[4][0] for i in infos})
        except socket.gaierror as e:
            findings.append(Finding("WARN", "SSRF-05", f"域名 {host} 解析失败",
                                    str(e), "无法判定；生产环境应**解析失败即拒绝**"))
            return findings

        bad_ips = []
        for ip_str in ips:
            ip_obj = ipaddress.ip_address(ip_str.split("%")[0])
            blocked, net = _is_blocked_ip(ip_obj)
            if blocked:
                bad_ips.append(f"{ip_str} (in {net})")

        if bad_ips:
            findings.append(Finding(
                "FAIL", "SSRF-05", f"域名 {host} 解析到受限地址",
                f"{bad_ips}",
                "解析后校验 IP；且校验与连接必须使用**同一个已解析 IP**，防 DNS Rebinding"))
        else:
            findings.append(Finding(
                "PASS", "SSRF-05", f"域名 {host} 解析到 {ips}，均为公网地址",
                "注意：仍需在连接时复用该 IP，防 Rebinding"))

    # ── 5) 重定向风险 ─────────────────────────────────────
    findings.append(Finding(
        "WARN", "SSRF-07", "重定向风险需人工确认",
        "攻击者可用 302 把已通过校验的公网 URL 跳转到内网地址",
        "禁用自动跟随重定向；若必须跟随，每次跳转都重新执行本检测"))

    return findings


def audit_ssrf(urls: list[str], allowed_hosts: set[str] | None, rpt: Report) -> None:
    for u in urls:
        print(f"    · 检测 URL: {u}")
        for f in check_url_ssrf(u, allowed_hosts):
            rpt.findings.append(f)


# ══════════════════════════════════════════════════════════════════
# ⑤ 演示入口
# ══════════════════════════════════════════════════════════════════

def demo_config() -> dict[str, Any]:
    """一个**故意做错**的示例配置，用来展示审计器能抓出什么。"""
    return {
        "oauth2": {
            "response_type": "code",
            "uses_state": True,
            "state_length": 43,
            "state_stored_in_session": True,
            "pkce": {"enabled": True, "method": "S256"},
            "redirect_uris": ["https://app.example.com/callback"],
            "registered_redirect_uris": ["https://app.example.com/callback"],
            "enabled_grants": ["authorization_code", "refresh_token"],
            "access_token_ttl": 86400,          # ⚠️ 24 小时，偏长
            "refresh_token_rotation": False,    # ⚠️ 未轮转
            "https_everywhere": True,
            "revocation_endpoint": False,       # ⚠️ 无撤销
        },
        "cookies": [
            {"name": "session", "httponly": True, "secure": True,
             "samesite": "Lax", "path": "/", "max_age": 3600, "domain": None},
            {"name": "csrf_token", "httponly": True, "secure": True,
             "samesite": "Lax", "path": "/", "max_age": 3600, "domain": None},
        ],
        "csrf": {
            "token_enabled": True,
            "token_verified_server_side": True,
            "tokens_reused": True,              # ⚠️ 长期复用
            "get_has_side_effects": False,
            "origin_checked": True,
            "json_only_relied": False,
        },
        # 用户可控 URL（比如"从链接导入头像"功能收到的输入）
        "user_supplied_urls": [
            "https://cdn.example.com/avatar.png",      # 正常
            "http://169.254.169.254/latest/meta-data/",  # 云元数据 SSRF 💀
            "http://2130706433:6379/",                 # 十进制 IP 混淆 → 127.0.0.1
            "file:///etc/passwd",                      # 危险协议
            "http://expected.com@evil.com/x",          # userinfo 混淆
            "http://192.168.1.1/admin",                # 内网
        ],
        "ssrf_allowed_hosts": {"cdn.example.com"},
    }


def main() -> int:
    as_json = "--json" in sys.argv
    cfg = demo_config()
    rpt = Report(target="demo-app（示例配置，故意做错若干项）")

    print("🔍 开始审计……（本节只做静态判定，不发起任何网络请求）\n")
    print("  [1/4] OAuth2 配置");       audit_oauth2(cfg["oauth2"], rpt)
    print("  [2/4] Cookie / 会话");     [audit_cookie(c, rpt) for c in cfg["cookies"]]
    print("  [3/4] CSRF 防护");         audit_csrf(cfg["csrf"], rpt)
    print("  [4/4] SSRF 检测");         audit_ssrf(cfg["user_supplied_urls"],
                                                  cfg["ssrf_allowed_hosts"], rpt)

    if as_json:
        print(json.dumps(
            {"target": rpt.target, "counts": rpt.counts,
             "findings": [asdict(f) for f in rpt.findings]},
            ensure_ascii=False, indent=2))
    else:
        print(rpt.render())
        print("""
  🎯 使用建议：
     • 把 `audit_*` 换成从你自己的配置文件/数据库读取，即可变成真实审计器
     • `check_url_ssrf()` 可直接放在"用户提交 URL"的入口做前置校验
     • 校验通过后**不要重新解析域名**：用已解析并校验过的 IP 去连接，
       同时手动设置 Host 头，才能同时防住 DNS Rebinding 与 302 绕过
""")

    return 1 if rpt.has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
