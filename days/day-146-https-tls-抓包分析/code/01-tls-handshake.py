#!/usr/bin/env python3
"""Day 146 - 用 Python 完成一次真实的 TLS 握手并观察结果.

相当于"代码级抓包": 打印协商出的 TLS 版本、密码套件、
对端证书的关键信息(主体/签发者/有效期/SAN), 以及握手耗时.

用法: python3 01-tls-handshake.py [host] [port]
"""
import socket
import ssl
import sys
import time

HOST = sys.argv[1] if len(sys.argv) > 1 else "www.baidu.com"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 443


def show_cert(cert: dict) -> None:
    """打印证书要点(域名、有效期、签发者)."""
    def field(key):
        return dict(x[0] for x in cert.get(key, []))
    subj, issuer = field("subject"), field("issuer")
    print("  主体(subject) :", subj.get("commonName", "?"))
    print("  签发者(issuer):", issuer.get("commonName", "?"),
          f"(O={issuer.get('organizationName', '?')})")
    print("  有效期        :", cert.get("notBefore"), "→", cert.get("notAfter"))
    san = cert.get("subjectAltName", ())
    print("  SAN           :", ", ".join(v for _, v in san[:4]),
          f"(共{len(san)}项)" if san else "")


def main() -> None:
    print(f"=== TLS 握手实验: {HOST}:{PORT} ===")
    # create_default_context(): 默认验证证书 + 加载系统 CA 信任库
    ctx = ssl.create_default_context()
    t0 = time.perf_counter()
    try:
        with socket.create_connection((HOST, PORT), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=HOST) as tls:
                cost = (time.perf_counter() - t0) * 1000
                print(f"握手成功, 耗时 {cost:.1f} ms")
                print("  协商版本    :", tls.version())
                cipher, proto, bits = tls.cipher()
                print(f"  密码套件    : {cipher} ({proto}, {bits} bits)")
                print("  对端证书    :")
                show_cert(tls.getpeercert())
                # 发一个真实 HTTP 请求, 验证通道可用
                tls.sendall(f"HEAD / HTTP/1.1\r\nHost: {HOST}\r\nConnection: close\r\n\r\n".encode())
                status = tls.recv(64).decode(errors="replace").splitlines()[0]
                print("  加密通道请求:", status)
                print("\n结论: 之后的报文都是对称加密的, 抓包只能看到密文.")
    except (socket.gaierror, ConnectionError, TimeoutError) as e:
        print(f"网络不可达({e}), 属于环境问题而非代码问题.")
        sys.exit(2)


if __name__ == "__main__":
    main()
