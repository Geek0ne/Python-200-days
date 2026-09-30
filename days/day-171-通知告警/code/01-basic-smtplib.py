#!/usr/bin/env python3
"""01 - 邮件告警基础：smtplib 的正确用法与 MIME 组装

对应 ROADMAP「Day 171 — 通知告警 / smtplib 邮件告警」。

运行：
    python3 01-basic-smtplib.py --self-test     # 离线自检（起本地抓包 SMTP）
    python3 01-basic-smtplib.py                 # 对本地抓包服务器发一封完整邮件
    python3 01-basic-smtplib.py --start-server  # 只启动抓包服务器，供另一个终端观察

本课要点（每一条都在后面有注释解释）：
  1. 用 EmailMessage 而不是手拼字符串 —— 手拼必踩编码/换行/中文的坑
  2. 用 with 上下文管理器 —— 保证 QUIT 与 socket 释放
  3. 一定要设 timeout —— 否则 SMTP 卡住时你的告警线程会被拖死
  4. 发信人(From)与发信账号要分离 —— 否则 QQ/163 会被直接拒收
  5. set_debuglevel(1) 是排查 SMTP 问题的唯一利器
"""

from __future__ import annotations

import argparse
import smtplib
import sys
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate

sys.path.insert(0, __file__.rsplit("/", 1)[0])


# --------------------------------------------------------------------------
# 1. 最基础：发一封纯文本告警
# --------------------------------------------------------------------------
def send_plain(host: str, port: int, sender: str, to: str, subject: str, body: str) -> dict:
    """发纯文本邮件。返回 smtplib 的结果字典。

    注意 SMTP 的两个「身份」：
      - MAIL FROM (envelope sender)：由 smtplib.login() 的账号决定，用于 SPF/退信
      - From 头 (header)：由你自己写，可以是任意显示名
    我们把两者解耦，这样可以用 noreply@ 之类的账号冒充任意 From。
    """
    msg = EmailMessage()
    # formataddr 会把中文名编码成 RFC 2047，例如
    # "=?utf-8?b?5pWw5o2u5bqT?= <alert@example.com>"
    msg["From"] = formataddr(("Learn-Python 告警", sender))
    msg["To"] = to
    msg["Subject"] = subject          # 中文主题会被自动编码，无需自己 base64
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = f"<{int(time.time())}@{host}>"
    msg.set_content(body)             # 7bit/8bit 自动选择

    with smtplib.SMTP(host, port, timeout=10) as s:
        s.set_debuglevel(0)
        s.ehlo()
        s.send_message(msg)
        # with 退出时自动 QUIT 并关闭连接
    return {"ok": True, "size": len(msg.as_bytes())}


# --------------------------------------------------------------------------
# 2. 带附件：add_attachment 的正确姿势（这里有真坑）
# --------------------------------------------------------------------------
def send_with_attachment(host: str, port: int, sender: str, to: str,
                         subject: str, body: str, log_text: str) -> dict:
    """带附件的邮件。

    ⚠️ 实测坑位（本机 Python 3.12.3 真实报错）：
        add_attachment 的 maintype/subtype 参数是否必填，取决于你传什么类型：

          传 str      →  不能传 maintype/subtype，否则
                        TypeError: set_text_content() got an unexpected keyword
                        argument 'maintype'
          传 bytes     →  必须传 maintype/subtype，否则
                        TypeError: set_bytes_content() missing 2 required
                        positional arguments: 'maintype' and 'subtype'
          传 BytesIO   →  直接 KeyError: '_io.BytesIO'（3.12 不支持）
          传 EmailMessage → OK（嵌套邮件）

        所以最省心的做法是：文本附件传 str，二进制附件传 bytes + 显式类型。
    """
    msg = EmailMessage()
    msg["From"] = formataddr(("Learn-Python 告警", sender))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    # ✅ 文本附件：str + 不传 maintype/subtype
    msg.add_attachment(log_text, filename="service.log")

    with smtplib.SMTP(host, port, timeout=10) as s:
        s.send_message(msg)
    return {"ok": True, "size": len(msg.as_bytes())}


# --------------------------------------------------------------------------
# 3. 生产环境：用真实的 SMTP 账号 + TLS
# --------------------------------------------------------------------------
def send_via_real_server(user: str, password: str, host: str, port: int,
                         to: str, subject: str, body: str,
                         sender: str | None = None) -> dict:
    """真实投递。QQ/163 邮箱的标准配置。

    两种加密方式，必须按服务商文档选：
      - 465 端口：隐式 TLS，用 SMTP_SSL，一上来就是加密连接
      - 587 端口：明文连接后 STARTTLS 升级

    ⚠️ 授权码：QQ/163 早就禁用了「登录密码」，必须去邮箱设置里开
       「POP3/SMTP/IMAP 服务」拿到一串 16 位授权码。
    """
    msg = EmailMessage()
    msg["From"] = formataddr(("Learn-Python 告警", sender or user))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if port == 465:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=15)
    else:
        server = smtplib.SMTP(host, port, timeout=15)
        server.ehlo()
        server.starttls()        # 升级为 TLS；服务器不支持会抛 SMTPNotSupportedError
        server.ehlo()           # TLS 后要重新 EHLO 一次，很多教程会漏

    with server as s:
        s.login(user, password)
        s.send_message(msg)
    return {"ok": True}


# --------------------------------------------------------------------------
# 4. 重试：告警系统必须自己扛住瞬时网络抖动
# --------------------------------------------------------------------------
def send_with_retry(host: str, port: int, sender: str, to: str,
                    subject: str, body: str, retries: int = 3,
                    backoff_base: float = 0.5) -> dict:
    """指数退避重试。注意：SMTP 永久性错误（如 550 认证失败）不该重试。"""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return send_plain(host, port, sender, to, subject, body)
        except (smtplib.SMTPResponseException, OSError) as e:
            last_exc = e
            code = getattr(e, "smtp_code", None)
            # 5xx = 永久失败，重试没意义，直接抛出
            if code is not None and 500 <= code < 600:
                raise
            if attempt == retries:
                break
            delay = backoff_base * (2 ** (attempt - 1))
            print(f"  第 {attempt} 次失败({e.__class__.__name__})，{delay:.1f}s 后重试")
            time.sleep(delay)
    return {"ok": False, "error": repr(last_exc)}


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def self_test() -> int:
    from smtp_capture_server import serve_in_thread

    srv, _ = serve_in_thread(0)
    port = srv.server_address[1]
    ok = True

    r = send_plain("127.0.0.1", port, "alert@learn-python.dev",
                   "niedong@learn-python.dev", "基础告警", "磁盘使用率 91%")
    m1 = srv.messages[0]
    assert m1["from"] == "alert@learn-python.dev", m1["from"]
    assert m1["to"] == ["niedong@learn-python.dev"], m1["to"]
    assert "磁盘使用率 91%" in m1["body"].decode()
    print(f"OK 基础邮件: envelope from={m1['from']} to={m1['to']} size={m1['size']}B")

    send_with_attachment("127.0.0.1", port, "alert@learn-python.dev",
                         "niedong@learn-python.dev", "带附件告警", "正文",
                         "ERROR: db timeout\nERROR: db timeout\n")
    m2 = srv.messages[1]
    body2 = m2["body"].decode()
    assert "multipart/mixed" in body2 and "service.log" in body2, "附件结构不对"
    print(f"OK 带附件邮件: multipart/mixed 生成成功 size={m2['size']}B")

    # 主题必须被 RFC2047 编码，否则非 ASCII 主题在真实 MTA 上会乱码/被拒
    raw = m1["body"].decode()
    assert "=?utf-8?b?" in raw or "=?utf-8?Q?" in raw, "主题未做 RFC2047 编码"
    print("OK 中文主题已做 RFC 2047 编码（=?utf-8?b?...?=&quot;）")

    # 重试逻辑：对一个没人监听的端口，必须重试耗尽后返回 ok=False 而不是抛异常
    closed = srv.server_address[1]
    srv.shutdown(); srv.server_close()
    r = send_with_retry("127.0.0.1", closed, "a@b.c", "d@e.f", "重试测试",
                        "body", retries=2, backoff_base=0.05)
    assert r["ok"] is False, f"重试耗尽应返回 ok=False，实际 {r}"
    print("OK 重试耗尽后优雅返回 ok=False（连接被拒），未抛出未捕获异常")

    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--start-server", action="store_true")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1025)
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.start_server:
        from smtp_capture_server import CaptureSMTPServer
        s = CaptureSMTPServer((args.host, args.port), verbose=True)
        print(f"* 抓包服务器运行于 {args.host}:{args.port}，Ctrl-C 停止")
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    from smtp_capture_server import serve_in_thread
    srv, _ = serve_in_thread(args.port, verbose=True)
    print(f"* 本地抓包 SMTP 服务器: {args.host}:{args.port}\n")
    send_plain(args.host, args.port, "alert@learn-python.dev",
               "niedong@learn-python.dev", "[P1] 磁盘告警", "磁盘使用率 91%")
    print("\n* 已发送，完整 SMTP 会话见上方")
    srv.shutdown(); srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
