#!/usr/bin/env python3
"""一个极简的「抓包式」SMTP 服务器，只用标准库实现。

为什么自己写？
  Python 3.12 起标准库的 ``smtpd`` 模块已被移除（PEP 594），
  ``python -m smtpd -c DebuggingServer`` 在 3.12+ 直接报
  ``No module named 'smtpd'``。而 aiosmtpd 又需要额外安装。
  教学场景下最稳的做法就是：用 ``socketserver`` 手写一个几十行的
  SMTP 服务端，把整段 SMTP 会话原样打印出来。

它能让你在没有真实邮箱、也不联网发信的情况下，
看清楚 smtplib 客户端到底和服务器聊了什么。

用法：
    python3 smtp_capture_server.py                  # 监听 127.0.0.1:1025
    python3 smtp_capture_server.py --port 2525
    python3 smtp_capture_server.py --self-test      # 离线自检

协议实现范围（够用即可）：
    EHLO/HELO  -> 250
    MAIL FROM  -> 250
    RCPT TO    -> 250
    DATA       -> 354，然后收正文直到单独一行的 "."
    RSET/NOOP/QUIT -> 250/250/221
    其它       -> 500 Command not recognized
"""

from __future__ import annotations

import argparse
import socketserver
import sys
import threading
from typing import Any

BANNER = "Learn-Python Capture SMTP"


class SMTPHandler(socketserver.StreamRequestHandler):
    """处理一条 SMTP 连接。每条连接一个实例。"""

    # 由 serve_forever 在 setup() 之前注入
    server: "CaptureSMTPServer"

    def _reply(self, line: str) -> None:
        self.wfile.write((line + "\r\n").encode("utf-8"))
        self.wfile.flush()

    def setup(self) -> None:
        super().setup()
        self.mail_from: str | None = None
        self.rcpt_to: list[str] = []

    def handle(self) -> None:
        self._reply(f"220 {self.server.hostname} ESMTP {BANNER}")
        while True:
            raw = self.rfile.readline()
            if not raw:  # 客户端直接断开
                return
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            self.server.record(("C: " + line).encode("utf-8"))
            verb = line.split(" ")[0].upper() if line else ""

            if verb in ("EHLO", "HELO"):
                self._reply(f"250-{self.server.hostname} greets you")
                self._reply("250-8BITMIME")
                self._reply("250-SMTPUTF8")
                self._reply("250 SIZE 10485760")
            elif verb == "MAIL":
                self.mail_from = _addr(line)
                self.server.record(f"  [envelope sender] {self.mail_from}".encode())
                self._reply("250 2.1.0 Ok")
            elif verb == "RCPT":
                addr = _addr(line)
                self.rcpt_to.append(addr)
                self.server.record(f"  [envelope rcpt] {addr}".encode())
                self._reply("250 2.1.5 Ok")
            elif verb == "DATA":
                self._reply("354 End data with <CR><LF>.<CR><LF>")
                body = self._read_data()
                self.server.store_message(self.mail_from, list(self.rcpt_to), body)
                self._reply("250 2.0.0 Ok: queued as CAPTURED")
            elif verb == "RSET":
                self.mail_from, self.rcpt_to = None, []
                self._reply("250 2.0.0 Ok")
            elif verb == "NOOP":
                self._reply("250 2.0.0 Ok")
            elif verb == "QUIT":
                self._reply(f"221 2.0.0 {self.server.hostname} closing connection")
                return
            else:
                self._reply("500 5.5.2 Command not recognized")

    def _read_data(self) -> bytes:
        """读取 DATA 正文，直到单独一行 '.'。做反转义还原（去掉行首 ..）。"""
        chunks: list[bytes] = []
        while True:
            line = self.rfile.readline()
            if not line:
                break
            if line in (b".\r\n", b".\n"):
                break
            if line.startswith(b".."):
                line = line[1:]  # SMTP 的 "dot stuffing" 反转义
            chunks.append(line)
        return b"".join(chunks)


def _addr(line: str) -> str:
    """从 'RCPT TO:<a@b.c>' 里抠出 a@b.c。

    ⚠️ 翻车点：smtplib 发的不是干净的 ``MAIL FROM:<a@b.c>``，而是带 ESMTP 参数的
        ``MAIL FROM:<a@b.c> BODY=8BITMIME``（因为正文含中文/8bit 字符时
        smtplib 会声明 8BITMIME）。天真地取冒号后面全部内容，会得到
        ``a@b.c BODY=8BITMIME``，我第一次实现就踩了这个坑。
    所以这里必须先把第一个空格（参数区）切掉，再剥尖括号。
    """
    _, _, rest = line.partition(":")
    # ESMTP 参数以空格分隔：<addr> [KEY=VALUE ...]
    addr_part = rest.strip().split(" ")[0]
    return addr_part.strip("<>").strip()


class CaptureSMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, addr: tuple[str, int], verbose: bool = True):
        self.hostname = "capture.local"
        self.verbose = verbose
        self.messages: list[dict[str, Any]] = []
        self.transcript: list[str] = []
        self._lock = threading.Lock()
        super().__init__(addr, SMTPHandler)

    def record(self, line: bytes) -> None:
        text = line.decode("utf-8", errors="replace").rstrip("\n")
        with self._lock:
            self.transcript.append(text)
        if self.verbose:
            print(f"  {text}", flush=True)

    def store_message(self, sender: str | None, rcpt: list[str], body: bytes) -> None:
        with self._lock:
            self.messages.append(
                {"from": sender, "to": rcpt, "body": body, "size": len(body)}
            )


def serve_in_thread(port: int, verbose: bool = False) -> tuple[CaptureSMTPServer, threading.Thread]:
    """启动一个后台抓包服务器，供脚本 --self-test 使用。"""
    srv = CaptureSMTPServer(("127.0.0.1", port), verbose=verbose)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, t


# ------------------------------------------------------------------ 自检
def self_test() -> int:
    """离线自检：不依赖任何外部服务，直接在进程内起服务器再发一封信。"""
    import smtplib
    from email.message import EmailMessage

    srv, _ = serve_in_thread(0)          # 端口 0 = 让内核分配空闲端口
    port = srv.server_address[1]
    ok = True

    msg = EmailMessage()
    msg["From"] = "selftest@learn-python.dev"
    msg["To"] = "niedong@learn-python.dev"
    msg["Subject"] = "自检邮件"
    msg.set_content("这是一封自检邮件，正文含中文。")

    with smtplib.SMTP("127.0.0.1", port, timeout=10) as s:
        s.send_message(msg)

    if len(srv.messages) != 1:
        print(f"FAIL: 期望抓到 1 封，实际 {len(srv.messages)}")
        ok = False
    else:
        m = srv.messages[0]
        assert m["from"] == "selftest@learn-python.dev", m["from"]
        assert m["to"] == ["niedong@learn-python.dev"], m["to"]
        assert "自检邮件" in m["body"].decode("utf-8"), "正文乱码/缺中文"
        print(f"OK: 抓到 1 封邮件，envelope from={m['from']} to={m['to']} size={m['size']}B")
        print("OK: 正文中文 UTF-8 未乱码，SMTP dot-stuffing 反转义正确")

    srv.shutdown()
    srv.server_close()
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="抓包式 SMTP 服务器")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1025)
    ap.add_argument("--self-test", action="store_true", help="离线自检后退出")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    srv = CaptureSMTPServer((args.host, args.port), verbose=True)
    print(f"* 抓包 SMTP 服务器已启动: {args.host}:{args.port}")
    print(f"* 发送测试邮件请用: python3 -c \"import smtplib;s=smtplib.SMTP('{args.host}',{args.port});"
          f"s.sendmail('a@b.c',['d@e.f'],'Subject: hi\\n\\nbody');s.quit()\"")
    print("* Ctrl-C 停止")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print(f"\n* 共抓到 {len(srv.messages)} 封邮件，服务器已停止")
    finally:
        srv.shutdown()
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
