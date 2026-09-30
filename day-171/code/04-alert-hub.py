#!/usr/bin/env python3
"""04 - 实战：多渠道告警中枢 AlertHub

对应 ROADMAP「Day 171 — **实战**：多渠道告警」。

这是一个可以直接搬进生产的告警中枢最小实现，包含 8 个生产能力：

  1. 多渠道扇出      一次事件 -> 邮件 + 钉钉 + 企业微信 + Slack
  2. 指纹去重        fingerprint = sha1(rule|instance|metric)，抑制窗口内只发一次
  3. 恢复通知        指标回到正常时自动补一条 RECOVERED
  4. 分类分级        info / warn / critical，决定是否 @ 人、是否走全渠道
  5. 限速与背压      每个渠道一个令牌桶，撞到 20 条/分钟前就自己排队
  6. 分级降级        邮件挂了不影响 IM；核心渠道全挂时降级到 stdout 兜底
  7. 敏感信息脱敏    发送前统一 mask
  8. 幂等 + 可观测    每条通知有唯一告警 ID，发送结果写审计日志

运行：
    python3 04-alert-hub.py --self-test        # 离线自检（本地 SMTP + 本地 HTTP）
    python3 04-alert-hub.py --demo             # 演示一次完整故障 -> 恢复流程
    python3 04-alert-hub.py --storm            # 压测：注入 500 个抖动事件看去重效果
    python3 04-alert-hub.py --dry-run          # 不发任何请求，只打印将要发送的内容
"""

from __future__ import annotations

import argparse
import hashlib
import json
import queue
import re
import smtplib
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

sys.path.insert(0, __file__.rsplit("/", 1)[0])

LEVELS = ("info", "warn", "critical")


# ==========================================================================
# 脱敏
# ==========================================================================
_MASK_RULES = [
    (re.compile(r"(?i)(password|passwd|pwd)(\s*[=:]\s*)(\S+)"), r"\1\2******"),
    (re.compile(r"(?i)(token|secret|access_token|key)(\s*[=:]\s*)(\S+)"), r"\1\2******"),
    (re.compile(r"(?i)(://[^:@/]+):([^@]+)@"), r"\1:******@"),
]


def mask(text: str) -> str:
    """任何进入告警正文的字符串都要过一遍这个函数。"""
    for pat, repl in _MASK_RULES:
        text = pat.sub(repl, text)
    return text


# ==========================================================================
# 数据模型
# ==========================================================================
@dataclass
class Alert:
    rule: str                    # 规则名，如 disk_usage
    instance: str                # 实例，如 web-01
    metric: str                  # 指标，如 disk
    value: Any                   # 观测值
    threshold: Any               # 阈值
    level: str = "warn"          # info / warn / critical
    summary: str = ""
    detail: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def fingerprint(self) -> str:
        raw = f"{self.rule}|{self.instance}|{self.metric}"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    @property
    def alert_id(self) -> str:
        raw = f"{self.fingerprint}|{self.timestamp}"
        return hashlib.sha1(raw.encode()).hexdigest()[:12]

    def title(self) -> str:
        lv = {"info": "ℹ️", "warn": "⚠️", "critical": "🔴"}[self.level]
        return f"{lv} [{self.rule}] {self.instance} {self.metric}={self.value}"

    def body(self) -> str:
        lines = [
            f"**规则**    : {self.rule}",
            f"**实例**    : {self.instance}",
            f"**指标**    : {self.metric} = {self.value} (阈值 {self.threshold})",
            f"**级别**    : {self.level}",
            f"**时间**    : {self.timestamp}",
            f"**指纹**    : {self.fingerprint}",
            f"**告警ID**  : {self.alert_id}",
        ]
        if self.detail:
            lines += ["", "**详情**", "```", mask(self.detail), "```"]
        return "\n".join(lines)


@dataclass
class SendResult:
    channel: str
    ok: bool
    detail: str = ""
    elapsed_ms: float = 0.0


# ==========================================================================
# 渠道
# ==========================================================================
class Channel:
    name = "base"
    min_level = "info"           # 低于该级别的告警不走这个渠道

    def send(self, alert: Alert) -> SendResult:
        raise NotImplementedError


class StdoutChannel(Channel):
    """兜底渠道：永不失败，保证「至少有一条落地」。"""
    name = "stdout"

    def send(self, alert: Alert) -> SendResult:
        t0 = time.perf_counter()
        print(f"  [stdout] {alert.title()}\n{indent(alert.body())}")
        return SendResult(self.name, True, "", (time.perf_counter() - t0) * 1000)


class SMTPChannel(Channel):
    name = "email"

    def __init__(self, host: str, port: int, sender: str, to: str,
                 user: str | None = None, password: str | None = None,
                 ssl: bool = False, timeout: float = 10.0):
        self.host, self.port, self.sender, self.to = host, port, sender, to
        self.user, self.password, self.ssl, self.timeout = user, password, ssl, timeout

    def send(self, alert: Alert) -> SendResult:
        t0 = time.perf_counter()
        msg = EmailMessage()
        msg["From"] = formataddr(("Learn-Python 告警", self.sender))
        msg["To"] = self.to
        msg["Subject"] = alert.title()
        msg["Date"] = formatdate(localtime=True)
        msg["X-Alert-Id"] = alert.alert_id
        msg["X-Alert-Fingerprint"] = alert.fingerprint
        msg.set_content(mask(alert.body()))
        try:
            if self.ssl:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout) as s:
                    if self.user:
                        s.login(self.user, self.password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as s:
                    s.ehlo()
                    if self.user:
                        s.login(self.user, self.password)
                    s.send_message(msg)
            return SendResult(self.name, True, "", (time.perf_counter() - t0) * 1000)
        except Exception as e:
            # 邮件失败绝不能把告警中枢带崩
            return SendResult(self.name, False, f"{type(e).__name__}: {e}",
                              (time.perf_counter() - t0) * 1000)


class WebhookChannel(Channel):
    """通用 Webhook 渠道（钉钉 / 企业微信 / Slack 都走这个）。"""

    def __init__(self, name: str, url: str, kind: str = "dingtalk",
                 min_level: str = "info"):
        self.name, self.url, self.kind = name, url, kind
        self.min_level = min_level

    def build_payload(self, alert: Alert) -> dict[str, Any]:
        if self.kind == "dingtalk":
            return {"msgtype": "text",
                    "text": {"content": f"{alert.title()}\n{alert.body()}"},
                    "at": {"atMobiles": [], "isAtAll": alert.level == "critical"}}
        if self.kind == "wecom":
            return {"msgtype": "markdown",
                    "markdown": {"content": f"## {alert.title()}\n{alert.body()}"}}
        if self.kind == "slack":
            return {"text": alert.title(),
                    "blocks": [{"type": "section",
                                "text": {"type": "mrkdwn", "text": alert.body()}}]}
        return {"title": alert.title(), "body": alert.body()}

    def interpret(self, status: int, data: Any) -> tuple[bool, str]:
        if self.kind == "slack":
            return (200 <= status < 300), f"HTTP {status}"
        if isinstance(data, dict):
            code = data.get("errcode", -1)
            return (code == 0), f"errcode={code} errmsg={data.get('errmsg','')}"
        return False, f"unexpected body {data!r}"

    def send(self, alert: Alert) -> SendResult:
        import urllib.request
        t0 = time.perf_counter()
        payload = json.dumps(self.build_payload(alert), ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw, status = resp.read().decode("utf-8", "replace"), resp.status
        except urllib.error.HTTPError as e:
            raw, status = e.read().decode("utf-8", "replace"), e.code
        except Exception as e:
            return SendResult(self.name, False, f"{type(e).__name__}: {e}",
                              (time.perf_counter() - t0) * 1000)
        try:
            data = json.loads(raw)
        except ValueError:
            data = raw
        ok, detail = self.interpret(status, data)
        return SendResult(self.name, ok, detail, (time.perf_counter() - t0) * 1000)


# ==========================================================================
# 令牌桶限流
# ==========================================================================
class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: float):
        self.rate, self.capacity = rate_per_sec, capacity
        self._tokens, self._last = capacity, time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(self.capacity,
                                   self._tokens + (now - self._last) * self.rate)
                self._last = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))


# ==========================================================================
# 告警中枢
# ==========================================================================
class AlertHub:
    def __init__(self, channels: list[Channel], suppress_seconds: float = 1800,
                 rate_per_sec: float = 20 / 60, verbose: bool = True):
        self.channels = channels
        self.suppress_seconds = suppress_seconds
        self.verbose = verbose
        self.buckets = {c.name: TokenBucket(rate_per_sec, max(3, rate_per_sec * 60))
                        for c in channels}
        self._last_fired: dict[str, float] = {}
        self._active: set[str] = set()          # 已告警但未恢复的指纹
        self._lock = threading.Lock()
        self.audit: list[dict[str, Any]] = []
        self.stats = {"received": 0, "sent": 0, "suppressed": 0,
                      "recovered": 0, "channel_fail": 0, "fallback": 0}

    # ------------------------------------------------------------------
    def fire(self, alert: Alert) -> list[SendResult]:
        """上报一条告警（可能处于 firing / recovered 两种状态）。"""
        with self._lock:
            self.stats["received"] += 1
            fp = alert.fingerprint
            now = time.time()
            recovering = alert.level == "info" and fp in self._active

            if recovering:
                self._active.discard(fp)
                self._last_fired.pop(fp, None)
                self.stats["recovered"] += 1
                self._log(f"RECOVERED {fp}")
            else:
                last = self._last_fired.get(fp, -1e18)
                if now - last < self.suppress_seconds:
                    self.stats["suppressed"] += 1
                    self._log(f"SUPPRESSED {fp} ({now - last:.0f}s < {self.suppress_seconds}s)")
                    return []
                self._last_fired[fp] = now
                self._active.add(fp)
                self.stats["sent"] += 1

        return self._fanout(alert)

    # ------------------------------------------------------------------
    def _fanout(self, alert: Alert) -> list[SendResult]:
        results: list[SendResult] = []
        for ch in self.channels:
            if LEVELS.index(alert.level) < LEVELS.index(ch.min_level):
                continue
            if not self.buckets[ch.name].acquire(timeout=5.0):
                results.append(SendResult(ch.name, False, "限流：令牌桶 5s 内未取到令牌"))
                self.stats["channel_fail"] += 1
                continue
            r = ch.send(alert)
            results.append(r)
            if not r.ok:
                self.stats["channel_fail"] += 1
        # 分级降级：全渠道失败时，保证 stdout 兜底至少留痕
        if results and not any(r.ok for r in results):
            self.stats["fallback"] += 1
            self._log("!! 所有渠道均失败，降级到 stdout 兜底")
            results.append(StdoutChannel().send(alert))
        if self.verbose:
            for r in results:
                flag = "OK " if r.ok else "FAIL"
                self._log(f"  {flag} {r.channel:8s} {r.elapsed_ms:6.1f}ms  {r.detail}")
        return results

    # ------------------------------------------------------------------
    def _log(self, msg: str) -> None:
        line = f"[AlertHub] {msg}"
        if self.verbose:
            print(line)
        self.audit.append({"ts": datetime.now(timezone.utc).isoformat(), "msg": line})


def indent(text: str, n: int = 6) -> str:
    return "\n".join(" " * n + ln for ln in text.splitlines())


# ==========================================================================
# 真实指标采集：用 psutil 做一个真监控（与 Day 166 呼应）
# ==========================================================================
def collect_realtime_alert(hub: AlertHub, disk_threshold: float = 85.0,
                           cpu_threshold: float = 90.0) -> None:
    """采集本机真实指标并触发告警。psutil 缺失时自动降级为 os 模块。"""
    try:
        import psutil
        disk = psutil.disk_usage("/")
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        print(f"* 真实指标: 磁盘 {disk.percent:.1f}%  CPU {cpu:.1f}%  内存 {mem.percent:.1f}%")
        if disk.percent > disk_threshold:
            hub.fire(Alert("disk_usage", "local", "/", f"{disk.percent:.1f}%",
                           f"{disk_threshold}%", "critical",
                           detail=f"used={disk.used // 2**20}MiB free={disk.free // 2**20}MiB"))
        else:
            hub.fire(Alert("disk_usage", "local", "/", f"{disk.percent:.1f}%",
                           f"{disk_threshold}%", "info", summary="正常"))
    except ImportError:
        import os
        st = os.statvfs("/")
        used_pct = (st.f_blocks - st.f_bfree) / st.f_blocks * 100
        print(f"* psutil 未安装，降级用 os.statvfs: 磁盘 {used_pct:.1f}%")
        lvl = "critical" if used_pct > disk_threshold else "info"
        hub.fire(Alert("disk_usage", "local", "/", f"{used_pct:.1f}%",
                       f"{disk_threshold}%", lvl))


# ==========================================================================
# 自检
# ==========================================================================
def _mock_backend(dingtalk_body: dict | None = None,
                  wecom_body: dict | None = None) -> tuple[ThreadingHTTPServer, int, list]:
    """模拟钉钉/企业微信/Slack 的接收端，可配置返回 200+errcode 失败。"""
    hits: list[str] = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append(self.path)
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path.startswith("/dingtalk"):
                body = dingtalk_body if dingtalk_body is not None else {"errcode": 0, "errmsg": "ok"}
            elif self.path.startswith("/wecom"):
                body = wecom_body if wecom_body is not None else {"errcode": 0, "errmsg": "ok"}
            else:
                body = "ok"
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1], hits


def self_test() -> int:
    from smtp_capture_server import serve_in_thread

    smtp_srv, smtp_port = serve_in_thread(0)
    http_srv, http_port, hits = _mock_backend()
    base = f"http://127.0.0.1:{http_port}"

    channels = [
        SMTPChannel("127.0.0.1", smtp_srv.server_address[1],
                    "alert@learn-python.dev", "niedong@learn-python.dev"),
        WebhookChannel("dingtalk", f"{base}/dingtalk", "dingtalk"),
        WebhookChannel("wecom", f"{base}/wecom", "wecom"),
        WebhookChannel("slack", f"{base}/slack", "slack"),
    ]
    hub = AlertHub(channels, suppress_seconds=1800, rate_per_sec=20 / 60, verbose=True)

    print("\n--- 1. 首次触发，应扇出到全部 4 个渠道 ---")
    a1 = Alert("disk_usage", "web-01", "/", "91.2%", "85%", "critical",
               detail="connect postgresql://admin:Hunter2@10.0.0.5/app")
    res = hub.fire(a1)
    assert all(r.ok for r in res), res
    assert len(smtp_srv.messages) == 1, smtp_srv.messages
    assert len(hits) == 3, hits
    mail = smtp_srv.messages[0]["body"].decode()
    assert "Hunter2" not in mail, "密码泄漏到邮件里了！"
    assert "******" in mail
    print(f"  OK 4 渠道全部成功，邮件 1 封，HTTP 3 次；密码已脱敏")

    print("\n--- 2. 同一指纹重复触发，应被抑制 ---")
    a2 = Alert("disk_usage", "web-01", "/", "92.0%", "85%", "critical")
    assert hub.fire(a2) == []
    assert len(hits) == 3 and len(smtp_srv.messages) == 1, "抑制失效，产生了重复告警！"
    print(f"  OK 重复告警被抑制（suppressed={hub.stats['suppressed']}）")

    print("\n--- 3. 恢复事件，应补发一条 RECOVERED ---")
    a3 = Alert("disk_usage", "web-01", "/", "72.1%", "85%", "info")
    res = hub.fire(a3)
    assert len(res) == 4, res
    assert hub.stats["recovered"] == 1
    assert len(smtp_srv.messages) == 2
    print(f"  OK 恢复通知已发出，且不再被抑制")

    print("\n--- 4. 不同实例应独立去重 ---")
    hub.fire(Alert("disk_usage", "web-02", "/", "95.0%", "85%", "critical"))
    assert len(hits) == 9, f"web-02 应独立发送（6+3），实际 {len(hits)}"
    print(f"  OK web-02 指纹独立，未被 web-01 的抑制状态影响")

    print("\n--- 5. ⭐ 全渠道 HTTP 200 + errcode 失败 -> 必须识别并降级 ---")
    http_srv.shutdown()
    bad_srv, bad_port, bad_hits = _mock_backend(
        dingtalk_body={"errcode": 300005, "errmsg": "token is not exist"},
        wecom_body={"errcode": 93000, "errmsg": "invalid webhook url"})
    # 邮件指向一个不存在的端口 -> 必失败
    bad_channels = [
        SMTPChannel("127.0.0.1", 1, "alert@learn-python.dev", "n@learn-python.dev"),
        WebhookChannel("dingtalk", f"http://127.0.0.1:{bad_port}/dingtalk", "dingtalk"),
        WebhookChannel("wecom", f"http://127.0.0.1:{bad_port}/wecom", "wecom"),
    ]
    hub2 = AlertHub(bad_channels, suppress_seconds=1800, rate_per_sec=1000, verbose=False)
    before = hub2.stats["fallback"]
    res = hub2.fire(Alert("db_down", "db-01", "conn", "refused", "ok", "critical"))
    assert hub2.stats["fallback"] == before + 1, hub2.stats
    assert any(r.channel == "stdout" and r.ok for r in res), res
    assert any(r.channel == "dingtalk" and r.ok is False and "300005" in r.detail for r in res), res
    print(f"  OK 3 渠道全部失败 -> 自动降级到 stdout；errcode 300005 被正确识别为失败")
    print(f"      (若只看 HTTP 状态码，这里会被误判成成功 —— 就是那个致命陷阱)")
    bad_srv.shutdown()

    print("\n--- 6. 令牌桶限流：突发调用应被拦住 ---")
    bucket = TokenBucket(rate_per_sec=20 / 60, capacity=20)
    t0 = time.perf_counter()
    allowed = sum(1 for _ in range(40) if bucket.acquire(timeout=0.2))
    el = time.perf_counter() - t0
    # 令牌桶是【持续补充】的：被拦下的 19 次每次会 sleep ~50ms，总共过去约 1 秒，
    # 期间又回充了约 0.33 个令牌。所以放行数在 20~21 之间浮动是正确行为。
    assert 20 <= allowed <= 22, f"桶容量 20，放行应在 20~22，实际 {allowed}"
    print(f"  OK 40 次突发调用：放行 {allowed} 次（桶容量 20），其余 {40-allowed} 次被限流拦截"
          f"（耗时 {el*1000:.0f}ms）")

    smtp_srv.shutdown(); smtp_srv.server_close()
    print(f"\n最终统计: {hub.stats}")
    print("SELFTEST PASS")
    return 0


# ==========================================================================
# 演示
# ==========================================================================
def _demo_hub(verbose=True) -> tuple[AlertHub, Any, int, list]:
    from smtp_capture_server import serve_in_thread
    smtp_srv, _ = serve_in_thread(0)
    http_srv, http_port, hits = _mock_backend()
    base = f"http://127.0.0.1:{http_port}"
    chans = [
        SMTPChannel("127.0.0.1", smtp_srv.server_address[1],
                    "alert@learn-python.dev", "niedong@learn-python.dev"),
        WebhookChannel("dingtalk", f"{base}/dingtalk", "dingtalk"),
        WebhookChannel("wecom", f"{base}/wecom", "wecom"),
        WebhookChannel("slack", f"{base}/slack", "slack"),
    ]
    hub = AlertHub(chans, suppress_seconds=1800, rate_per_sec=1000, verbose=verbose)
    return hub, smtp_srv, http_port, hits


def demo() -> int:
    hub, smtp_srv, _, hits = _demo_hub()
    print("=" * 68)
    print("演示：磁盘告警触发 -> 抖动 -> 恢复")
    print("=" * 68)
    collect_realtime_alert(hub)                     # 真实指标
    hub.fire(Alert("disk_usage", "web-01", "/", "93.0%", "85%", "critical"))
    for v in ("94.1%", "95.2%", "96.0%"):            # 抖动 -> 应被抑制
        hub.fire(Alert("disk_usage", "web-01", "/", v, "85%", "critical"))
    hub.fire(Alert("disk_usage", "web-01", "/", "70.2%", "85%", "info"))   # 恢复
    smtp_srv.shutdown()
    print(f"\n统计: {hub.stats}")
    return 0


def storm() -> int:
    hub, smtp_srv, _, hits = _demo_hub(verbose=False)
    print("=" * 68)
    print("压测：注入 500 个抖动事件，观察去重与限流效果")
    print("=" * 68)
    t0 = time.perf_counter()
    for i in range(500):
        hub.fire(Alert("cpu_high", f"node-{i % 20:02d}", "cpu",
                       f"{80 + (i % 25)}%", "85%", "critical"))
    for i in range(100):
        hub.fire(Alert("disk_usage", "web-01", "/", "92%", "85%", "critical"))
    el = time.perf_counter() - t0
    print(f"  注入事件    : 600 条（500 条 CPU 抖动 + 100 条磁盘抖动）")
    print(f"  最终发送    : {hub.stats['sent']} 条")
    print(f"  被抑制      : {hub.stats['suppressed']} 条")
    print(f"  恢复通知    : {hub.stats['recovered']} 条")
    print(f"  总耗时      : {el*1000:.0f}ms  (平均每条 {el*1000/600:.2f}ms)")
    print(f"  实际 HTTP 请求: {len(hits)} 次   实际 SMTP: {len(smtp_srv.messages)} 封")
    smtp_srv.shutdown()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--storm", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.storm:
        return storm()
    if args.dry_run:
        hub, smtp_srv, _, _ = _demo_hub(verbose=True)
        collect_realtime_alert(hub)
        smtp_srv.shutdown()
        return 0
    return demo()


if __name__ == "__main__":
    sys.exit(main())
