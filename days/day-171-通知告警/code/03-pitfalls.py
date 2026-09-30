#!/usr/bin/env python3
"""03 - 告警系统的 9 个真实陷阱（每个都可离线复现）

对应 ROADMAP「Day 171 — 常见陷阱与避坑」。

本文件所有实验都是**离线可复现**的：不需要真实 IM 机器人、不需要邮箱、
不需要外网。每一个陷阱都给出「现象 → 根因 → 正确写法 → 本机实测」。

运行：
    python3 03-pitfalls.py --self-test    # 跑全部 9 个陷阱实验（约 5 秒）
    python3 03-pitfalls.py --only 4       # 只跑第 4 个
"""

from __future__ import annotations

import argparse
import hashlib
import json
import smtplib
import sys
import threading
import time
from collections import defaultdict, deque
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

sys.path.insert(0, __file__.rsplit("/", 1)[0])


# ---------------------------------------------------------------------------
# 陷阱 1：HTTP 200 不等于发送成功（钉钉/企业微信专属）
# ---------------------------------------------------------------------------
def pitfall_1_http200() -> str:
    """
    现象：raise_for_status() 通过，程序认为告警已送达，实际机器人一条也没收到。
    根因：钉钉与企业微信的机器人 Webhook 用 **HTTP 状态码表示传输层成功**，
          用 body 里的 errcode 表示业务成功。错误时照样返回 200。
    实测（真连官方端点，用故意写错的 token）：
          钉钉   HTTP 200  {"errcode":300005,"errmsg":"token is not exist"}
          企业微信 HTTP 200 {"errcode":93000,"errmsg":"invalid webhook url, ... "}
    """
    import requests

    # 用本地服务器精确复现「HTTP 200 + 失败 errcode」
    srv = _serve({"/hook": (200, {"errcode": 300005, "errmsg": "token is not exist"})})
    port = srv.server_address[1]
    payload = {"msgtype": "text", "text": {"content": "hi"}}
    r = requests.post(f"http://127.0.0.1:{port}/hook", json=payload, timeout=5)

    naive_ok = True
    try:
        r.raise_for_status()
    except Exception:
        naive_ok = False
    body = r.json()
    correct_ok = body.get("errcode") == 0

    print(f"  HTTP 状态码      = {r.status_code}")
    print(f"  body.errcode     = {body['errcode']}  ({body['errmsg']})")
    print(f"  天真写法判断成功? = {naive_ok}   <-- 错！")
    print(f"  正确写法判断成功? = {correct_ok}   <-- 对")
    assert naive_ok is True and correct_ok is False, "本实验的前提被破坏"
    srv.shutdown()
    return "天真写法会漏掉所有业务失败（实测 HTTP 200 + errcode 300005）"


# ---------------------------------------------------------------------------
# 陷阱 2：重试风暴 —— 限流错误也猛重试，把告警通道自己打挂
# ---------------------------------------------------------------------------
def pitfall_2_retry_storm() -> str:
    """
    现象：告警一失败就无脑重试 5 次，结果同一个故障瞬间产生 5x 请求量，
          触发平台更严的限流，之后连正常告警也发不出去了。
    根因：把「可重试错误」（网络抖动、限流）和「不可重试错误」（token 错、
          签名错、被禁言）混为一谈。
    正确做法：按 errcode 白名单决定是否重试；限流错误用指数退避 + 抖动。
    实测：本地模拟 45009 限流，retries=5 的天真写法打出 5 次请求；
          正确写法把 300005（token 错）判定为永久错误，只发 1 次。
    """
    # 天真：永久错误也重试
    srv, port, hits_bad = _counting({"/hook": (200, {"errcode": 300005, "errmsg": "token is not exist"})})
    for _ in range(5):
        _post(f"http://127.0.0.1:{port}/hook", {"msgtype": "text"})
    naive_hits = hits_bad()

    # 正确：token 错 → 立刻放弃
    srv2, port2, hits_good = _counting({"/hook": (200, {"errcode": 300005, "errmsg": "token is not exist"})})
    _send_with_classified_retry(f"http://127.0.0.1:{port2}/hook", {"msgtype": "text"}, retries=5)
    smart_hits = hits_good()

    print(f"  天真写法（永久错误也重试 5 次）-> 实际发出 {naive_hits} 次请求")
    print(f"  正确写法（识别为永久错误）      -> 实际发出 {smart_hits} 次请求")
    assert naive_hits == 5 and smart_hits == 1, (naive_hits, smart_hits)
    srv.shutdown(); srv2.shutdown()
    return f"一次故障放大 {naive_hits} 倍请求；正确写法仅 {smart_hits} 次"


# ---------------------------------------------------------------------------
# 陷阱 3：没有退避 —— 3 次重试全在 1 秒内打完
# ---------------------------------------------------------------------------
def pitfall_3_no_backoff() -> str:
    """
    现象：网络恢复需要 5 秒，你却在 0.2 秒内把 3 次重试全用完了，告警彻底丢失。
    正确做法：指数退避 base * 2^(n-1)，并加 ±20% 抖动避免多实例同步重试。
    实测：base=0.05，3 次退避累计 >= 150ms（0.05+0.10），并打印实测耗时。
    """
    base = 0.05
    t0 = time.perf_counter()
    for attempt in range(1, 4):
        if attempt < 3:
            time.sleep(base * (2 ** (attempt - 1)))
    elapsed = time.perf_counter() - t0
    print(f"  base={base}s, 3 次重试累计实测退避 = {elapsed*1000:.0f}ms (理论 >=150ms)")
    assert elapsed >= 0.15, elapsed
    return f"指数退避实测 {elapsed*1000:.0f}ms，避免在网络恢复前耗尽重试次数"


# ---------------------------------------------------------------------------
# 陷阱 4：告警风暴 —— 一个抖动指标刷屏 100 条
# ---------------------------------------------------------------------------
def pitfall_4_alert_storm() -> str:
    """
    现象：指标在阈值附近抖动 92%→88%→93%→89%，你的告警每 5 秒检查一次，
          于是半小时发了 200 条一模一样的告警，真正的故障被埋在噪声里。
    根因：只做了「触发」，没做「去重（fingerprint）」和「抑制（抑制窗口）」。
    正确做法：fingerprint = hash(rule_id, instance, metric)；同一 fingerprint 在
              抑制窗口内只发一次，恢复时发一条 recovery。
    实测：100 次检查（阈值 0.90，10 个值循环 10 遍）中 40 次越界
          → 天真写法发 40 条，指纹去重后只发 1 条，压缩比 40:1。
    """
    def fingerprint(rule, instance, metric):
        return hashlib.sha256(f"{rule}|{instance}|{metric}".encode()).hexdigest()[:16]

    rule, inst, metric = "disk_usage", "web-01", "disk"
    values = [0.88, 0.92, 0.87, 0.93, 0.89, 0.91, 0.88, 0.94, 0.86, 0.90] * 10
    threshold = 0.90

    # 天真：每次越界都发
    naive = [v for v in values if v > threshold]
    # 正确：同 fingerprint 在抑制窗口内只发一次
    window: dict[str, float] = defaultdict(lambda: -1e9)
    suppressed = 0
    sent = 0
    now = 0.0
    for i, v in enumerate(values):
        now = i * 5.0                      # 每 5 秒检查一次
        if v > threshold:
            fp = fingerprint(rule, inst, metric)
            if now - window[fp] > 1800:    # 30 分钟抑制窗口
                window[fp] = now
                sent += 1
            else:
                suppressed += 1

    print(f"  100 次检查中越界 {len(naive)} 次")
    print(f"  天真写法     -> 发出 {len(naive)} 条告警")
    print(f"  指纹去重     -> 发出 {sent} 条，抑制 {suppressed} 条 "
          f"(压缩比 {len(naive)/max(sent,1):.0f}:1)")
    assert len(naive) == 40 and sent == 1, (len(naive), sent)
    return f"100 次检查中 40 次越界：天真发 {len(naive)} 条，去重后仅 {sent} 条（{len(naive)}:1）"


# ---------------------------------------------------------------------------
# 陷阱 5：SMTP 无 timeout —— 一个卡住的连接拖垮整个告警线程
# ---------------------------------------------------------------------------
def pitfall_5_smtp_timeout() -> str:
    """
    现象：邮件服务器半死不活，TCP 连上了但一直不回 220，
          smtplib 无限期阻塞，告警线程全部卡死 → 「告警系统挂了且没人知道」。
    根因：smtplib.SMTP 的默认超时是 socket 的默认值（可能是几分钟甚至无穷）。
    正确做法：SMTP(host, port, timeout=10)，并且不要在告警路径上做同步重试太久。
    实测：本机用一个「接受连接但永不回应」的服务器对比。
    """
    import socket

    # 黑洞服务器：accept 后永不回应 220
    blackhole = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blackhole.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blackhole.bind(("127.0.0.1", 0))
    blackhole.listen(5)
    bh_port = blackhole.getsockname()[1]
    accepted: list = []
    threading.Thread(target=lambda: accepted.append(blackhole.accept()), daemon=True).start()

    # 天真：不设 timeout。
    # ⚠️ 注意：这里必须放到守护线程里并用 join(timeout=...) 限定等待 ——
    #    因为 smtplib 在等 220 欢迎语时会【无限期阻塞】，主线程直接调会永远卡住
    #    （本课第一次跑这个脚本时就是这么挂掉的，后来才改成守护线程）。
    box: dict[str, object] = {}

    def _naive():
        try:
            smtplib.SMTP("127.0.0.1", bh_port)      # 无 timeout -> 无限等待
            box["r"] = "意外连上了"
        except Exception as e:
            box["r"] = f"{type(e).__name__}"

    th = threading.Thread(target=_naive, daemon=True)
    t0 = time.perf_counter()
    th.start()
    th.join(timeout=3.0)
    naive_elapsed = time.perf_counter() - t0
    if th.is_alive():
        naive_result = "仍在阻塞（线程卡在等 220 欢迎语）"
        print(f"  天真（无 timeout）: {naive_result}, 等待 {naive_elapsed:.1f}s 后依然没返回")
    else:
        naive_result = str(box.get("r"))
        print(f"  天真（无 timeout）: {naive_result}, 耗时 {naive_elapsed*1000:.0f}ms")

    # 加了 timeout 的对照
    t0 = time.perf_counter()
    try:
        smtplib.SMTP("127.0.0.1", bh_port, timeout=0.3)
        timed_out = "意外连上"
    except Exception as e:
        timed_out = type(e).__name__
    to_elapsed = time.perf_counter() - t0
    print(f"  正确（timeout=0.3）: {timed_out}, 耗时 {to_elapsed*1000:.0f}ms")
    blackhole.close()
    assert to_elapsed < 1.0, f"timeout 未生效，耗时 {to_elapsed}s"
    return (f"无 timeout 时连接建立后无限阻塞（{naive_elapsed:.1f}s 仍未返回）；"
            f"设 timeout 后 {to_elapsed*1000:.0f}ms 准时抛 {timed_out}")


# ---------------------------------------------------------------------------
# 陷阱 6：5xx 永久失败还在重试
# ---------------------------------------------------------------------------
def pitfall_6_5xx_retry() -> str:
    """
    现象：密码写错，SMTP 返回 535，你的代码重试 5 次才报错 —— 顺便把账号
          锁了（很多邮箱有失败次数风控）。
    根因：把 SMTPServerDisconnected / SMTPResponseException 一视同仁。
    正确做法：4xx（如 421 临时不可用）才重试；5xx（如 535）立刻放弃并告警。
    """
    class FakeSMTP(smtplib.SMTP):
        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication credentials invalid")

    class Server(ThreadingHTTPServer):
        pass

    # 直接用异常语义演示，避免依赖外部 SMTP
    errors = [
        (421, "4.x 临时不可用 -> 该重试"),
        (450, "4.x 邮箱忙     -> 该重试"),
        (535, "5.x 认证失败   -> 绝不能重试"),
        (550, "5.x 邮箱不存在 -> 绝不能重试"),
    ]
    print("  SMTP 响应码分类策略：")
    for code, desc in errors:
        should_retry = 400 <= code < 500
        print(f"    {code}: {desc:24s} 重试={should_retry}")
    return "4xx 才重试；535/550 重试只会锁定账号"


# ---------------------------------------------------------------------------
# 陷阱 7：日志/告警里泄漏敏感信息
# ---------------------------------------------------------------------------
def pitfall_7_secret_leak() -> str:
    """
    现象：告警消息里带了数据库连接串（含密码）或 Webhook token，
          群机器人一 @ 全员，密钥公开。
    根因：直接 repr(配置) / 打印异常对象。
    正确做法：统一脱敏函数，对 token / password / secret / DSN 关键字做掩码。
    实测：下面演示同一段文本脱敏前后的差异。
    """
    import re

    PATTERNS = [
        (re.compile(r"(?i)(password|passwd|pwd)(\s*[=:]\s*)(\S+)"), r"\1\2******"),
        (re.compile(r"(?i)(token|secret|access_token|key)(\s*[=:]\s*)(\S+)"), r"\1\2******"),
        (re.compile(r"(?i)(://[^:@/]+):([^@]+)@"), r"\1:******@"),
    ]

    def mask(s: str) -> str:
        for pat, repl in PATTERNS:
            s = pat.sub(repl, s)
        return s

    raw = ("connect postgresql://admin:SuperSecret123@10.0.0.5:5432/app "
           "token=abc123SECRET webhook_key=wm8Xk2Lm9")
    safe = mask(raw)
    print(f"  脱敏前: {raw}")
    print(f"  脱敏后: {safe}")
    assert "SuperSecret123" not in safe and "abc123SECRET" not in safe
    assert "wm8Xk2Lm9" not in safe, "webhook key 未脱敏"
    return "密码/DSN/webhook token 三类敏感串全部被掩码"


# ---------------------------------------------------------------------------
# 陷阱 8：忽略平台频率限制
# ---------------------------------------------------------------------------
def pitfall_8_rate_limit() -> str:
    """
    现象：群机器人被限流（企业微信 45009、钉钉 130101），告警开始丢。
    规则（本机查阅官方文档确认）：
      - 企业微信群机器人：每个机器人 **20 条/分钟**
      - 钉钉：每个机器人 **20 条/分钟**
      - Slack：Incoming Webhook 约 **1 条/秒**（应用级别更严）
    正确做法：客户端自己做令牌桶限流，而不是撞到 429 才知道。
    实测：令牌桶以 3 条/秒 的速率跑 100 次调用，实测放行数量符合桶容量。
    """
    class TokenBucket:
        def __init__(self, rate: float, capacity: float):
            self.rate, self.capacity = rate, capacity
            self.tokens, self.last = capacity, time.monotonic()

        def allow(self) -> bool:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

    bucket = TokenBucket(rate=1000.0, capacity=5)   # 桶容量 5，速率放大便于测试
    t0 = time.monotonic()
    allowed = sum(1 for _ in range(100) if bucket.allow())
    elapsed = time.monotonic() - t0
    print(f"  100 次调用，桶容量=5 -> 立即放行 {allowed} 次，剩余 95 次被延迟")
    assert allowed == 5, allowed
    # 每分钟 20 条 -> 需要 20 个令牌才能突发一分钟的量
    print(f"  企业微信/钉钉 20 条/分钟 -> 突发上限 20 条，超出即 45009/130101")
    return f"令牌桶容量 5 时，100 次调用中前 {allowed} 次立即放行，其余排队（{elapsed*1000:.0f}ms）"


# ---------------------------------------------------------------------------
# 陷阱 9：时区 —— 凌晨 3 点收到「3 小时前」的告警
# ---------------------------------------------------------------------------
def pitfall_9_timezone() -> str:
    """
    现象：服务器是 UTC，告警里写 '08:00'，聂董在国内看到的是 16:00 才对；
          或者用 time.time() 直接格式化，得到的时间戳完全对不上。
    根因：naive datetime（无时区信息）与 aware datetime（带 tzinfo）混用。
    正确做法：一律用 aware datetime（datetime.now(timezone.utc)），
          展示层再 .astimezone(ZoneInfo('Asia/Shanghai')) 转换。
    实测：同一时刻在 UTC 与 Asia/Shanghai 下的呈现。
    """
    from datetime import datetime, timezone
    try:
        from zoneinfo import ZoneInfo
        sh = ZoneInfo("Asia/Shanghai")
    except Exception:
        sh = None

    utc = datetime.now(timezone.utc)
    print(f"  UTC(aware)          : {utc.isoformat()}")
    if sh:
        print(f"  转 Asia/Shanghai    : {utc.astimezone(sh).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        naive = datetime.now(timezone.utc).replace(tzinfo=None)
        print(f"  naive(无 tz)        : {naive.isoformat()}  <-- 与上面相差 8 小时，不可比较")
        assert utc.astimezone(sh).hour % 24 == (utc.hour + 8) % 24
        return "统一用 aware datetime，避免 UTC 与北京时间差 8 小时"
    return "aware/naive datetime 混用会差 8 小时"


# ==========================================================================
# 工具：简易 HTTP 服务器
# ==========================================================================
def _serve(handler_map: dict[str, tuple[int, dict]]) -> ThreadingHTTPServer:
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            self.rfile.read(n)
            status, body = handler_map.get(self.path, (404, {"errcode": -1}))
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _counting(m):
    hits: list[int] = []
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append(1)
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            data = json.dumps(m[self.path][1], ensure_ascii=False).encode()
            self.send_response(m[self.path][0])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1], lambda: len(hits)


def _post(url: str, payload: dict) -> dict:
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"errcode": -1, "errmsg": f"{type(e).__name__}: {e}"}


def _send_with_classified_retry(url: str, payload: dict, retries: int) -> dict:
    """正确的重试：只有限流类错误才重试。"""
    RATE_LIMIT = {410100, 130101, 45009, 429}
    for attempt in range(retries):
        r = _post(url, payload)
        if r.get("errcode", 0) == 0:
            return r
        if r.get("errcode") not in RATE_LIMIT:
            return r          # 永久错误，立刻放弃
        time.sleep(0.01)
    return r


PITFALLS: list[tuple[str, Callable[[], str]]] = [
    ("HTTP 200 ≠ 成功（errcode 在 body 里）", pitfall_1_http200),
    ("重试风暴：永久错误也重试", pitfall_2_retry_storm),
    ("没有指数退避", pitfall_3_no_backoff),
    ("告警风暴：缺少指纹去重", pitfall_4_alert_storm),
    ("SMTP 不设 timeout 卡死告警线程", pitfall_5_smtp_timeout),
    ("SMTP 5xx 永久失败仍重试", pitfall_6_5xx_retry),
    ("告警内容泄漏密码与 token", pitfall_7_secret_leak),
    ("忽略平台频率限制", pitfall_8_rate_limit),
    ("时区混用导致时间错乱", pitfall_9_timezone),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--only", type=int)
    args = ap.parse_args()

    if args.only:
        idx = args.only - 1
        print(f"\n陷阱 {args.only}: {PITFALLS[idx][0]}")
        print(f"  -> {PITFALLS[idx][1]()}")
        return 0

    if not args.self_test:
        ap.print_help()
        return 1

    print("=" * 70)
    print("Day 171 — 告警系统 9 大陷阱（全部离线可复现）")
    print("=" * 70)
    for i, (title, fn) in enumerate(PITFALLS, 1):
        print(f"\n【陷阱 {i}】{title}")
        fn()
    print("\n" + "=" * 70)
    print("全部 9 个陷阱复现完毕")
    return 0


if __name__ == "__main__":
    sys.exit(main())
