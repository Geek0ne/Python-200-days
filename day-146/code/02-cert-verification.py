#!/usr/bin/env python3
"""Day 146 - 证书验证实验: 三种场景对比.

场景1: 正常站点 → 验证通过
场景2: self-signed.badssl.com(自签证书) → 验证失败(信任链断裂)
场景3: 用 unverified context 强行连上 → 演示"关掉验证=接受任意MITM"

用法: python3 02-cert-verification.py
"""
import socket
import ssl

CASES = [
    ("www.baidu.com", "正常站点(受信CA签发)"),
    ("self-signed.badssl.com", "自签证书站点"),
]


def try_handshake(host: str, ctx: ssl.SSLContext) -> tuple[bool, str]:
    """返回 (是否成功, 说明)."""
    try:
        with socket.create_connection((host, 443), timeout=10) as s:
            with ctx.wrap_socket(s, server_hostname=host) as tls:
                cert = tls.getpeercert()  # CERT_NONE 时为空 dict
                if not cert:
                    return True, "连接成功(但拿不到证书信息 — 验证已关闭)"
                return True, f"连接成功, {tls.version()}, 证书主体: " + dict(
                    x[0] for x in cert["subject"]
                ).get("commonName", "?")
    except ssl.SSLCertVerificationError as e:
        return False, f"证书验证失败! {e.verify_message}"
    except (socket.gaierror, ConnectionError, TimeoutError) as e:
        return False, f"网络不可达({e}) — 环境问题"


def main() -> None:
    print("=== 场景1/2: 默认严格验证 ===")
    for host, desc in CASES:
        ok, msg = try_handshake(host, ssl.create_default_context())
        print(f"[{'通过' if ok else '拒绝'}] {host} ({desc})\n       {msg}\n")

    print("=== 场景3: 关闭验证(unverified context) ===")
    # 仅演示用! 生产代码严禁这样写
    bad_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    bad_ctx.check_hostname = False
    bad_ctx.verify_mode = ssl.CERT_NONE
    ok, msg = try_handshake("self-signed.badssl.com", bad_ctx)
    print(f"[{'通过' if ok else '拒绝'}] self-signed.badssl.com\n       {msg}")
    print("\n结论: 关掉验证后自签证书也能连上 — 这正是 MITM 攻击的土壤,")
    print("      所以教程里的 _create_unverified_context() 用完必须删.")


if __name__ == "__main__":
    main()
