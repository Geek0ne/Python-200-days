#!/usr/bin/env python3
"""Day 146 - 实战: HTTPS 站点安全体检工具(纯标准库).

对一组站点做 TLS "抓包级" 侦察, 输出体检报告:
  - 协商出的 TLS 版本(是否 1.3 / 是否淘汰协议)
  - 密码套件(是否 AEAD 加密)
  - 证书链深度、剩余有效期(过期预警)
  - 握手耗时(粗略反映 RTT 与服务器性能)

用法: python3 03-tls-audit.py [host1 host2 ...]
不传参数时使用内置站点列表。
"""
import socket
import ssl
import sys
import time
from datetime import datetime, timezone

DEFAULT_TARGETS = ["www.baidu.com", "www.python.org", "github.com"]

# 认为已"淘汰/不安全"的协议
BAD_PROTOCOLS = {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}


def parse_time(s: str) -> datetime:
    """把证书里的 notAfter (如 'Nov  5 05:12:12 2027 GMT') 解析成 datetime."""
    return datetime.strptime(s, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)


def audit(host: str) -> dict:
    """对单个站点做一次 TLS 体检, 返回结果 dict."""
    report = {"host": host, "ok": False}
    ctx = ssl.create_default_context()
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, 443), timeout=10) as s:
            with ctx.wrap_socket(s, server_hostname=host) as tls:
                report["ok"] = True
                report["handshake_ms"] = (time.perf_counter() - t0) * 1000
                report["version"] = tls.version()
                cipher, proto, bits = tls.cipher()
                report["cipher"] = cipher
                report["aead"] = any(
                    a in cipher for a in ("GCM", "POLY1305", "CCM")
                )  # AEAD = 认证加密, 老 CBC 套件不具备
                cert = tls.getpeercert()
                not_after = parse_time(cert["notAfter"])
                days_left = (not_after - datetime.now(timezone.utc)).days
                report["days_left"] = days_left
                report["issuer"] = dict(
                    x[0] for x in cert["issuer"]
                ).get("organizationName", "?")
    except ssl.SSLCertVerificationError as e:
        report["error"] = f"证书验证失败: {e.verify_message}"
    except (socket.gaierror, ConnectionError, TimeoutError) as e:
        report["error"] = f"网络不可达: {e}"
    return report


def verdict(r: dict) -> list[str]:
    """根据体检结果生成结论列表."""
    notes = []
    if not r["ok"]:
        return [f"❌ 无法建立可信连接: {r.get('error')}"]
    if r["version"] in BAD_PROTOCOLS:
        notes.append(f"❌ 协议 {r['version']} 已淘汰, 存在安全漏洞")
    elif r["version"] == "TLSv1.3":
        notes.append("✅ TLS 1.3, 最新协议")
    else:
        notes.append(f"⚠️ 协议 {r['version']}, 可用但建议升级 1.3")
    notes.append(
        "✅ AEAD 认证加密套件" if r["aead"] else "⚠️ 非 AEAD 套件(可能为老式 CBC)"
    )
    if r["days_left"] < 0:
        notes.append("❌ 证书已过期!")
    elif r["days_left"] < 30:
        notes.append(f"⚠️ 证书仅剩 {r['days_left']} 天, 尽快续期")
    else:
        notes.append(f"✅ 证书剩余 {r['days_left']} 天")
    notes.append(f"握手耗时 {r['handshake_ms']:.0f} ms, 签发机构 {r['issuer']}")
    return notes


def main() -> None:
    targets = sys.argv[1:] or DEFAULT_TARGETS
    print("=" * 56)
    print("HTTPS 站点 TLS 安全体检报告")
    print("=" * 56)
    for host in targets:
        r = audit(host)
        print(f"\n▶ {host}")
        if r["ok"]:
            print(f"  版本: {r['version']} | 套件: {r['cipher']}")
        for line in verdict(r):
            print(" ", line)
    print("\n说明: 这就是'分析 HTTPS 流量'的代码化做法 ——")
    print("  Wireshark 看的是握手报文本身, 这里看的是握手协商出的结果.")


if __name__ == "__main__":
    main()
