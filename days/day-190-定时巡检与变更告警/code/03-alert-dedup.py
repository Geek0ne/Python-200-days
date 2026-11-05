#!/usr/bin/env python3
"""
Day 190 · 03 — 告警降噪：去重、分组、限流、静默、升级

一个 30 台主机的资产库，端口抖动一小时能产生几百条"变化"。
原样推给人 = 三分钟后被静音 = 真出事时没人看。

本脚本实现一条五级漏斗，并用真实 HTTP 接收端验证投递：
  归一化 → 去重（指纹 + 冷却） → 分组（时间窗聚合） → 限流（令牌桶） → 投递

设计要点：
  - 指纹不含严重级：同一资产的同一问题反复出现是"同一个问题"
  - 严重级升高必须穿透冷却：低危先报过，不能把后来的高危吞掉
  - 限流不丢数据：被限的条目合并进下一条消息的"另有 N 条"
  - 静默窗口按资产标签匹配：维护窗口内只计数不打扰

用法：
  python3 03-alert-dedup.py --self-test            # 离线，不起网络
  python3 03-alert-dedup.py --e2e                  # 真起本地 HTTP 接收端
  python3 03-alert-dedup.py --e2e --flaky-receiver # 接收端前 2 次返回 500，验证重试
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEV_RANK = {"info": 0, "warning": 1, "critical": 2}


@dataclass(frozen=True)
class Alert:
    rule: str
    asset: str
    severity: str
    title: str
    detail: str = ""
    ts: float = 0.0
    tag: str = ""

    def fingerprint(self) -> str:
        # 故意不含 severity：同资产同规则 = 同一个待处理问题
        return f"{self.rule}|{self.asset}"


class MemorySender:
    """离线发送端：只记录，不发网络。self-test 用它。"""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    def send(self, payload: dict) -> bool:
        self.messages.append(payload)
        return True


class HttpSender:
    """真实 HTTP 发送端。失败重试，指数退避。"""

    def __init__(self, url: str, attempts: int = 3, timeout: float = 2.0) -> None:
        self.url = url
        self.attempts = attempts
        self.timeout = timeout
        self.posts = 0
        self.failures = 0

    def send(self, payload: dict) -> bool:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        for attempt in range(1, self.attempts + 1):
            req = urllib.request.Request(self.url, data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if 200 <= resp.status < 300:
                        self.posts += 1
                        return True
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                self.failures += 1
                if attempt == self.attempts:
                    print(f"  [send] 放弃投递: {exc}")
                    return False
                time.sleep(0.05 * (2 ** (attempt - 1)))
        return False


@dataclass
class PipelineStats:
    received: int = 0
    deduped: int = 0
    silenced: int = 0
    escalated: int = 0
    rate_limited: int = 0
    messages: int = 0
    send_failed: int = 0
    per_severity: dict = field(default_factory=lambda: {"info": 0, "warning": 0, "critical": 0})


class AlertPipeline:
    def __init__(self, sender, cooldown_s: dict | None = None, group_window_s: float = 0.5,
                 batch_size: int = 5, bucket_capacity: int = 5, refill_per_s: float = 2.0,
                 silence: dict | None = None, max_items_per_message: int = 8) -> None:
        self.sender = sender
        self.cooldown = cooldown_s or {"critical": 0.0, "warning": 1800.0, "info": 3600.0}
        self.group_window_s = group_window_s
        self.batch_size = batch_size
        self.capacity = bucket_capacity
        self.refill_per_s = refill_per_s
        self.silence = silence or {}      # {"tag": until_ts}
        self.max_items = max_items_per_message
        self.state: dict[str, dict] = {}  # fingerprint -> {last_ts, last_sev}
        self.buffer: list[Alert] = []
        self.buffer_start = 0.0
        self.tokens = float(bucket_capacity)
        self.last_refill = 0.0
        self.overflow: list[Alert] = []
        self.stats = PipelineStats()

    # --- 漏斗第 1 级：去重 ---
    def _dedupe(self, alert: Alert, now: float) -> bool:
        fp = alert.fingerprint()
        prev = self.state.get(fp)
        if prev is None:
            self.state[fp] = {"last_ts": now, "last_sev": alert.severity}
            return True
        fresh = now - prev["last_ts"]
        escalated = SEV_RANK[alert.severity] > SEV_RANK[prev["last_sev"]]
        if escalated:
            self.stats.escalated += 1
            self.state[fp] = {"last_ts": now, "last_sev": alert.severity}
            return True
        if alert.severity == "critical":
            # 高危即使同级也按 cooldown=0 处理：允许重复提醒
            self.state[fp] = {"last_ts": now, "last_sev": alert.severity}
            return True
        if fresh < self.cooldown.get(alert.severity, 3600.0):
            self.stats.deduped += 1
            return False
        self.state[fp] = {"last_ts": now, "last_sev": alert.severity}
        return True

    # --- 漏斗第 2 级：静默 ---
    def _silenced(self, alert: Alert, now: float) -> bool:
        until = self.silence.get(alert.tag)
        if until is not None and now < until:
            self.stats.silenced += 1
            return True
        return False

    # --- 漏斗第 3 级：令牌桶 ---
    def _take_token(self, now: float) -> bool:
        if self.last_refill == 0.0:
            self.last_refill = now
        elapsed = max(0.0, now - self.last_refill)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_s)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def submit(self, alert: Alert, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.stats.received += 1
        if self._silenced(alert, now):
            return
        if not self._dedupe(alert, now):
            return
        if not self.buffer:
            self.buffer_start = now
        self.buffer.append(alert)
        self.stats.per_severity[alert.severity] += 1
        if len(self.buffer) >= self.batch_size or now - self.buffer_start >= self.group_window_s:
            self.flush(now)

    def flush(self, now: float | None = None, force: bool = False) -> None:
        now = time.monotonic() if now is None else now
        if not self.buffer:
            return
        if not force and now - self.buffer_start < self.group_window_s and len(self.buffer) < self.batch_size:
            return
        batch, self.buffer = self.buffer, []
        if not self._take_token(now):
            # 限流：不丢弃，转入 overflow，等下一次有令牌时合并上报
            self.stats.rate_limited += len(batch)
            self.overflow.extend(batch)
            return
        merged = batch + self.overflow
        self.overflow = []
        self._deliver(merged, now)

    def _deliver(self, batch: list[Alert], now: float) -> None:
        batch.sort(key=lambda a: (-SEV_RANK[a.severity], a.asset))
        top = batch[: self.max_items]
        counts = {"info": 0, "warning": 0, "critical": 0}
        for a in batch:
            counts[a.severity] += 1
        payload = {
            "title": f"资产变更 {len(batch)} 条（严重 {counts['critical']} / 警告 {counts['warning']} / 提示 {counts['info']}）",
            "counts": counts,
            "total": len(batch),
            "items": [
                {"rule": a.rule, "asset": a.asset, "severity": a.severity, "title": a.title, "detail": a.detail}
                for a in top
            ],
            "truncated": max(0, len(batch) - len(top)),
            "sent_at": round(now, 3),
        }
        self.stats.messages += 1
        if not self.sender.send(payload):
            self.stats.send_failed += 1

    def close(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.flush(now, force=True)
        while self.overflow:
            batch, self.overflow = self.overflow, []
            self._deliver(batch, now)


class _Receiver:
    """真本地 HTTP 接收端：记录 POST，可注入前 N 次 500。"""

    def __init__(self, fail_first: int = 0) -> None:
        self.payloads: list[dict] = []
        self.fail_first = fail_first
        self.hits = 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                outer.hits += 1
                if outer.hits <= outer.fail_first:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b"boom")
                    return
                try:
                    outer.payloads.append(json.loads(raw))
                except json.JSONDecodeError:
                    outer.payloads.append({"raw": raw.decode("utf-8", "replace")})
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def do_GET(self):  # noqa: N802
                body = json.dumps({"count": len(outer.payloads), "hits": outer.hits}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):  # 静音默认访问日志
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def make_events(n: int = 500, seed: int = 20261020) -> list[Alert]:
    """造 500 条变化：大量同资产重复抖动 + 少量真高危。"""
    rng = random.Random(seed)
    assets = [f"10.0.1.{i}" for i in range(10, 22)]
    events = []
    for i in range(n - 20):
        asset = assets[i % len(assets)]
        port = rng.choice([80, 443, 8080])
        events.append(Alert("port-appeared", f"{asset}:{port}", "info",
                            f"{port} 端口抖动重开", "扫描确认 SYN-ACK", ts=float(i), tag="prod"))
    for i in range(20):
        asset = f"10.0.2.{i}"
        events.append(Alert("high-risk-port", f"{asset}:3389", "critical",
                            "RDP 暴露到网络", "3389/tcp 可直连，存在爆破风险", ts=float(i), tag="prod"))
    rng.shuffle(events)
    return events


def e2e(flaky: bool) -> int:
    events = make_events(500)
    fail_first = 2 if flaky else 0
    with _Receiver(fail_first=fail_first) as rx:
        sender = HttpSender(f"http://127.0.0.1:{rx.port}/hook")
        pipe = AlertPipeline(sender, group_window_s=0.05, batch_size=40,
                             bucket_capacity=5, refill_per_s=50.0)
        t0 = time.perf_counter()
        for a in events:
            pipe.submit(a)
        pipe.close()
        elapsed = time.perf_counter() - t0
        print(f"接收端: 127.0.0.1:{rx.port}  (前 {fail_first} 次故意 500)")
        print(f"输入事件           : {len(events)}")
        print(f"去重拦截           : {pipe.stats.deduped}")
        print(f"静默拦截           : {pipe.stats.silenced}")
        print(f"严重级升级放行     : {pipe.stats.escalated}")
        print(f"限流合并           : {pipe.stats.rate_limited}")
        print(f"发出的消息         : {pipe.stats.messages}")
        print(f"HTTP 成功 POST     : {sender.posts}  失败次数: {sender.failures}")
        print(f"接收端收到         : {len(rx.payloads)}  总请求: {rx.hits}")
        print(f"耗时               : {elapsed*1000:.1f} ms")
        crit_sent = sum(p["counts"]["critical"] for p in rx.payloads)
        total_sent = sum(p["total"] for p in rx.payloads)
        print(f"送达的 critical 条 : {crit_sent} / 20")
        print(f"送达总条数         : {total_sent} (含合并的限流条目)")
        ok = (crit_sent == 20 and len(rx.payloads) <= 10
              and (sender.failures == 2 if flaky else sender.failures == 0))
        print(f"验收: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1


def self_test() -> int:
    checks = []
    events = make_events(500)
    sender = MemorySender()
    pipe = AlertPipeline(sender, group_window_s=0.1, batch_size=50, bucket_capacity=10, refill_per_s=100.0)
    now = 1000.0
    for a in events:
        pipe.submit(a, now=now)
        now += 0.001
    pipe.close(now)
    crit = sum(m["counts"]["critical"] for m in sender.messages)
    checks.append(("500 条事件压缩到少量消息", len(sender.messages) <= 10, f"messages={len(sender.messages)}"))
    checks.append(("高危一条不丢", crit == 20, f"critical={crit}/20"))
    checks.append(("去重确实生效", pipe.stats.deduped > 300, f"deduped={pipe.stats.deduped}"))
    checks.append(("消息含截断说明", all("truncated" in m for m in sender.messages), "字段存在"))

    # 静默窗口
    s2 = MemorySender()
    p2 = AlertPipeline(s2, silence={"prod": 2000.0})
    p2.submit(Alert("r", "a:1", "critical", "t", tag="prod"), now=1500.0)
    p2.close(1500.0)
    checks.append(("静默窗口内不打扰", p2.stats.silenced == 1 and not s2.messages, f"silenced={p2.stats.silenced}"))

    # 严重级升级穿透冷却
    s3 = MemorySender()
    p3 = AlertPipeline(s3, batch_size=10, group_window_s=100.0)
    p3.submit(Alert("r", "a:1", "info", "低危"), now=3000.0)
    p3.submit(Alert("r", "a:1", "critical", "高危"), now=3001.0)
    p3.close(3002.0)
    sevs = [i["severity"] for m in s3.messages for i in m["items"]]
    checks.append(("升级穿透冷却", "critical" in sevs and p3.stats.escalated == 1, f"sevs={sevs}"))

    # 限流：令牌不足时进入 overflow，最终仍合并上报
    s4 = MemorySender()
    p4 = AlertPipeline(s4, batch_size=1, group_window_s=0.0, bucket_capacity=1, refill_per_s=0.0001)
    for i in range(5):
        p4.submit(Alert("r", f"a:{i}", "info", "x"), now=5000.0 + i)
    p4.close(5001.0)
    delivered = sum(m["total"] for m in s4.messages)
    checks.append(("限流不丢条目", delivered == 5 and p4.stats.rate_limited >= 3,
                   f"delivered={delivered} rate_limited={p4.stats.rate_limited}"))

    ok = all(c[1] for c in checks)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    print(f"\n{'全部通过' if ok else '存在失败项'}（{len(checks)} 项）")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="告警降噪漏斗")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--e2e", action="store_true")
    ap.add_argument("--flaky-receiver", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.e2e:
        return e2e(args.flaky_receiver)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
