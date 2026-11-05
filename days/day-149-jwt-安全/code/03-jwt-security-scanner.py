#!/usr/bin/env python3
"""
Day 149 · 示例 03 —— 实战：JWT 安全检测脚本（audit_jwt）

依赖：
    pip install pyjwt cryptography

这是一个「离线静态审计器」：只拿到一个 JWT 字符串，不访问目标服务，
就能给出安全体检报告。它可以发现：

    [严重] alg=none —— 未签名 token 可伪造
    [严重] HS256 弱密钥 —— 用内置字典离线爆破
    [严重] payload 含敏感字段（password/id_card/手机号等）
    [高危] 缺少 exp —— token 永不过期
    [高危] exp 过长（> 24h）—— 重放窗口过大
    [中危] 缺少 aud —— 存在跨服务 token 混用风险
    [中危] 缺少 iss —— 无法验证签发者
    [中危] iat > exp 或时间戳单位疑似写成了毫秒
    [提示] 使用 HS256 —— 多方验证场景建议改用 RS256/ES256
    [提示] 使用 deprecated 算法（HS256/RS256 之外的弱算法、无 kid 等）

用法：
    python3 03-jwt-security-scanner.py                 # 跑内置演示样本
    python3 03-jwt-security-scanner.py "<token>"       # 审计指定 token

⚠️ 仅供对自有系统做安全自查，请勿用于未授权目标。
"""

import base64
import hashlib
import hmac
import json
import re
import secrets
import sys
import time

import jwt

# ────────────────────────────────────────────────────────────────
# 内置弱密钥字典（真实审计时应换成 rockyou / jwt-secrets 等大字典）
# ────────────────────────────────────────────────────────────────
COMMON_SECRETS = [
    b"secret", b"password", b"123456", b"12345678", b"jwt_secret",
    b"changeme", b"admin", b"key", b"token", b"your-256-bit-secret",
    b"supersecret", b"jwt", b"test", b"dev", b"default",
]

SENSITIVE_KEYS = re.compile(
    r"(pass(word|wd)?|pwd|secret|token|id_?card|credit|card_?no|"
    r"phone|mobile|ssn|bank|private_?key|api_?key)",
    re.IGNORECASE,
)

SAFE_ALGS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512",
             "PS256", "PS384", "PS512", "EdDSA"}
WEAK_ALGS = {"HS256", "HS384", "HS512"}


# ────────────────────────────────────────────────────────────────
# Base64URL 工具
# ────────────────────────────────────────────────────────────────
def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ────────────────────────────────────────────────────────────────
# 报告收集器
# ────────────────────────────────────────────────────────────────
class Report:
    def __init__(self, token: str):
        self.token = token
        self.findings: list[tuple[str, str, str]] = []  # (级别, 标题, 说明)

    def add(self, level: str, title: str, detail: str) -> None:
        self.findings.append((level, title, detail))

    def render(self) -> str:
        icon = {"严重": "🔴", "高危": "🟠", "中危": "🟡", "提示": "🔵", "通过": "🟢"}
        lines = ["", "─" * 64, "JWT 安全审计报告", "─" * 64]
        lines.append(f"Token(截断): {self.token[:48]}...")
        if not self.findings:
            lines.append("🟢 未发现明显问题")
        for level, title, detail in self.findings:
            lines.append(f"{icon.get(level, '•')} [{level}] {title}")
            lines.append(f"      {detail}")
        lines.append("─" * 64)
        return "\n".join(lines)


# ────────────────────────────────────────────────────────────────
# 核心：审计一个 token
# ────────────────────────────────────────────────────────────────
def audit_jwt(token: str, wordlist: list[bytes] | None = None) -> Report:
    """对单个 JWT 做离线安全审计，返回 Report 对象"""
    wordlist = wordlist if wordlist is not None else COMMON_SECRETS
    rep = Report(token)

    # ① 结构检查：3 段（JWS）还是 5 段（JWE）
    parts = token.split(".")
    if len(parts) == 5:
        rep.add("提示", "这是一个 JWE（加密 JWT）",
                "5 段结构，payload 已加密，安全性高于普通 JWS")
        return rep
    if len(parts) != 3:
        rep.add("严重", "结构非法", f"期望 3 段，实际 {len(parts)} 段")
        return rep

    h_b64, p_b64, s_b64 = parts

    # ② 解析 Header / Payload（不验签，纯解码）
    try:
        header = json.loads(b64url_decode(h_b64))
        payload = json.loads(b64url_decode(p_b64))
    except Exception as e:
        rep.add("严重", "Header/Payload 无法解析",
                f"不是合法 JSON：{e}")
        return rep

    alg = header.get("alg", "<缺失>")

    # ③ alg 检查
    if alg == "none":
        rep.add("严重", "alg=none（未签名）",
                "任何人都能伪造身份，必须立即修复：验证端白名单禁止 none")
    elif alg in SAFE_ALGS:
        rep.add("通过", f"使用非对称算法 {alg}",
                "验证方只需要公钥，无法反推出签名能力")
    elif alg in WEAK_ALGS:
        rep.add("提示", f"使用对称算法 {alg}",
                "单方自用可接受；多服务/第三方场景建议改 RS256/ES256（公钥可分发给验证方）")
    else:
        rep.add("高危", f"未知/过时算法 {alg}",
                "请确认该算法未被禁用（如 MD5 系、无签名 none），并升级库版本")

    # ④ {alg, kid, jku, x5u} 危险字段
    if "jku" in header or "x5u" in header:
        rep.add("高危", "Header 含 jku/x5u",
                "若服务端盲信该 URL 拉取公钥，攻击者可注入自己的密钥；"
                "必须将取值限制在服务端白名单")
    if "kid" in header:
        kid = str(header["kid"])
        if any(x in kid for x in ("..", "/", "\\", "'", '"', ";")):
            rep.add("高危", "kid 含可疑字符",
                    f"kid={kid!r} 可能触发路径穿越 / SQL 注入 / 命令注入")

    # ⑤ 弱密钥离线爆破（仅对 HMAC 系列有意义）
    if alg in WEAK_ALGS:
        signing_input = f"{h_b64}.{p_b64}".encode()
        target = b64url_decode(s_b64)
        found = None
        for cand in wordlist:
            if hmac.compare_digest(
                hmac.new(cand, signing_input, hashlib.sha256).digest(), target
            ):
                found = cand
                break
        if found:
            rep.add("严重", "HS256 弱密钥可离线爆破",
                    f"密钥 = {found!r}；攻击者可任意签发/篡改 token，必须立即轮换为 32B 随机密钥")
        else:
            rep.add("通过", "内置字典未命中弱密钥",
                    f"已尝试 {len(wordlist)} 个候选（大字典请用 hashcat -m 16500）")

    # ⑥ 时间类 claim
    now = int(time.time())
    exp, iat, nbf = payload.get("exp"), payload.get("iat"), payload.get("nbf")

    if exp is None:
        rep.add("高危", "缺少 exp（永不过期）",
                "token 一旦泄露即长期有效，必须设置短有效期（建议 5~30 分钟）")
    else:
        if exp > now and exp - now > 86400:
            rep.add("高危", "有效期过长",
                    f"距过期还有 {(exp - now) / 3600:.1f} 小时，建议 ≤ 24h（access token 建议分钟级）")
        if exp < now:
            rep.add("提示", "token 已过期",
                    f"exp={exp} 早于当前 {now}，此 token 已不可用")
        # 毫秒单位误用检测
        if exp > 10 ** 12:
            rep.add("中危", "exp 疑似毫秒单位",
                    "JWT 规范要求 Unix 秒；毫秒会让有效期变成数万年")

    if iat and exp and iat > exp:
        rep.add("中危", "iat 晚于 exp", f"iat={iat} > exp={exp}，签发时间异常")

    if nbf and nbf > now + 3600:
        rep.add("中危", "nbf 远超当前时间", f"nbf={nbf}，token 将在很久之后才生效")

    # ⑦ 受众 / 签发者
    if "aud" not in payload:
        rep.add("中危", "缺少 aud",
                "未限定接收方，存在跨服务 token 混用风险（A 服务的 token 可能被 B 服务接受）")
    if "iss" not in payload:
        rep.add("中危", "缺少 iss",
                "验证方无法确认签发者，异地签发者的 token 可能被误信")
    if "jti" not in payload:
        rep.add("提示", "缺少 jti",
                "无法做黑名单/防重放；主动注销场景建议加 jti")

    # ⑧ payload 敏感信息
    leaks = [k for k in payload if SENSITIVE_KEYS.search(str(k))]
    # 手机号 / 身份证号 / 邮箱等模式匹配
    flat = json.dumps(payload, ensure_ascii=False)
    if re.search(r"\b1[3-9]\d{9}\b", flat):
        leaks.append("<疑似手机号>")
    if re.search(r"\b\d{17}[\dXx]\b", flat):
        leaks.append("<疑似身份证号>")
    if leaks:
        rep.add("严重", "payload 含敏感信息",
                f"字段 {leaks}；payload 仅 Base64 编码，任何人可解码读取，"
                "应改为服务端按 sub 查库，或用 JWE 加密")

    return rep


# ────────────────────────────────────────────────────────────────
# 演示：构造几个有代表性的「问题 token」送进审计器
# ────────────────────────────────────────────────────────────────
def build_samples() -> list[tuple[str, str]]:
    now = int(time.time())
    samples: list[tuple[str, str]] = []

    # 样本 1：弱密钥 + 缺 aud/iss + 敏感信息
    weak = jwt.encode(
        {"sub": "10086", "role": "admin", "password": "hunter2",
         "phone": "13800138000", "exp": now + 3600},
        b"secret", algorithm="HS256",
    )
    samples.append(("弱密钥 + 敏感信息", weak))

    # 样本 2：alg=none
    h = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(
        json.dumps({"sub": "1", "role": "admin", "exp": now + 3600},
                   separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    samples.append(("alg=none", f"{h}.{p}."))

    # 样本 3：超长有效期（30 天）
    long_lived = jwt.encode(
        {"sub": "1", "iss": "auth", "aud": "api", "exp": now + 30 * 86400},
        secrets.token_bytes(32), algorithm="HS256",
    )
    samples.append(("超长有效期", long_lived))

    # 样本 4：kid 路径穿越
    h2 = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "kid": "../../etc/passwd"},
                   separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    p2 = base64.urlsafe_b64encode(
        json.dumps({"sub": "1", "exp": now + 600}, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()
    sig = hmac.new(b"secret", f"{h2}.{p2}".encode(), hashlib.sha256).digest()
    samples.append(("kid 注入", f"{h2}.{p2}."
                    + base64.urlsafe_b64encode(sig).rstrip(b"=").decode()))

    # 样本 5：健康配置（用 RS256 需要密钥对，这里用强随机 HS256 + 全套 claim 作对照）
    good = jwt.encode(
        {"sub": "10086", "iss": "https://auth.example.com", "aud": "api.example.com",
         "iat": now, "nbf": now, "exp": now + 900, "jti": secrets.token_hex(8),
         "role": "user"},
        secrets.token_bytes(32), algorithm="HS256",
    )
    samples.append(("健康样本（对照）", good))

    return samples


def main() -> None:
    if len(sys.argv) > 1:
        for tok in sys.argv[1:]:
            print(audit_jwt(tok).render())
        return

    print("Day 149 · JWT 安全检测脚本演示")
    for name, tok in build_samples():
        print(f"\n\n########## 样本：{name} ##########")
        print(audit_jwt(tok).render())

    print("\n提示：也可以对真实 token 直接审计 ——")
    print("  python3 03-jwt-security-scanner.py '<token>'")


if __name__ == "__main__":
    main()
