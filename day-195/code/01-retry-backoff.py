#!/usr/bin/env python3
"""
Day 195 · 01 重试与退避：从 for 循环到可用的重试策略

运行：
    python3 01-retry-backoff.py              # 全部演示（约 2 秒）
    python3 01-retry-backoff.py --self-test  # 离线自检，不开端口

本脚本回答四个问题：
1. 为什么"失败就 sleep 1 秒再试"在生产里是灾难？（重试风暴）
2. 抖动（jitter）到底解决了什么？用数字看。
3. 哪些错误根本不该重试？401 重试五次只会把账号送进风控。
4. 重试 POST 为什么会重复下单？Idempotency-Key 怎么救。
"""

from __future__ import annotations

import json
import random
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ops_lib import (  # noqa: E402
    AuthError, PermanentError, RetryPolicy, TransientError, classify, retry_call,
)


# ─────────────────────────────────────────────────────────────
# 一个会捣乱的本地上游：前两次 GET 返回 503，第一次 POST 写成功但丢响应
# ─────────────────────────────────────────────────────────────

class State:
    lock = threading.Lock()
    get_calls = 0
    post_calls = 0
    rows: list[bytes] = []
    idempotency: dict[str, str] = {}
    first_post_fails = True

    @classmethod
    def reset(cls) -> None:
        with cls.lock:
            cls.get_calls = 0
            cls.post_calls = 0
            cls.rows = []
            cls.idempotency = {}
            cls.first_post_fails = True


class FlakyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # 静音默认访问日志
        pass

    def _send(self, code: int, payload: dict, headers: dict | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        with State.lock:
            State.get_calls += 1
            call_no = State.get_calls
        if call_no <= 2:
            # 第二次带 Retry-After，演示"服务端让你等多久就等多久"
            self._send(503, {"error": "upstream warming up"},
                       {"Retry-After": "0.1"} if call_no == 2 else None)
            return
        self._send(200, {"ok": True, "call": call_no})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        key = self.headers.get("Idempotency-Key")
        with State.lock:
            State.post_calls += 1
            if key and key in State.idempotency:
                self._send(200, {"id": State.idempotency[key], "duplicate": True})
                return
            record_id = f"rec-{len(State.rows) + 1}"
            State.rows.append(body)
            if key:
                State.idempotency[key] = record_id
            fail_now = State.first_post_fails
            State.first_post_fails = False
        # 第一次：数据已经落库，但响应"丢"了（超时/网关 502 的真实形态）
        if fail_now:
            self._send(503, {"error": "response lost after commit"})
        else:
            self._send(201, {"id": record_id})


def http_call(method: str, url: str, body: bytes | None = None,
              headers: dict | None = None) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, method=method,
                                     headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        retry_after = exc.headers.get("Retry-After")
        if exc.code == 429 or 500 <= exc.code < 600:
            raise TransientError(f"HTTP {exc.code}", 
                                 retry_after=float(retry_after) if retry_after else None)
        if exc.code in (401, 403):
            raise AuthError(f"HTTP {exc.code}")
        raise PermanentError(f"HTTP {exc.code}: {raw[:120]!r}")


# ─────────────────────────────────────────────────────────────
# 演示 1：指数退避 + Retry-After
# ─────────────────────────────────────────────────────────────

def demo_backoff(base_url: str) -> None:
    State.reset()
    print("\n" + "=" * 68)
    print("演示 1：两次 503 之后成功 —— 看时间线")
    print("=" * 68)

    def call(attempt: int) -> tuple[int, bytes]:
        print(f"  attempt {attempt}: GET /flaky")
        return http_call("GET", f"{base_url}/flaky")

    started = time.perf_counter()
    (status, body), report = retry_call(
        call,
        RetryPolicy(attempts=5, base_delay=0.1, factor=2.0, max_delay=2.0,
                    jitter="full", deadline=10),
        on_retry=lambda attempt, delay, exc: print(
            f"    ↳ {type(exc).__name__}({exc}) → sleep {delay:.3f}s"),
    )
    elapsed = time.perf_counter() - started
    print(f"  ✅ HTTP {status} {body.decode()}")
    print(f"  总尝试 {report.attempts} 次，实际耗时 {elapsed:.3f}s，"
          f"退避序列 {report.delays}")
    print("  注意：base=0.1 理论等待 0.1+0.2=0.3s；实际因为有抖动会小于它。")
    print("  第二次 503 带 Retry-After: 0.1，所以第二次等待不会低于 0.1s。")


# ─────────────────────────────────────────────────────────────
# 演示 2：错误分类 —— 不是所有错误都值得重试
# ─────────────────────────────────────────────────────────────

def demo_classification() -> None:
    print("\n" + "=" * 68)
    print("演示 2：错误分类决定重试次数")
    print("=" * 68)

    cases = [
        ("401 凭证过期", AuthError("401 Unauthorized")),
        ("404 资源不存在", PermanentError("404 Not Found")),
        ("503 上游过载", TransientError("503 Service Unavailable")),
        ("429 被限流", TransientError("429 Too Many Requests", retry_after=0.2)),
    ]

    for label, exc in cases:
        calls = []

        def boom(attempt: int, error=exc) -> None:
            calls.append(attempt)
            raise error

        started = time.perf_counter()
        try:
            retry_call(boom, RetryPolicy(attempts=4, base_delay=0.01, factor=2,
                                         jitter="none"))
        except Exception:  # noqa: BLE001
            pass
        spent = (time.perf_counter() - started) * 1000
        print(f"  {label:<14} 分类={classify(exc).value:<10} "
              f"调用 {len(calls)} 次  耗时 {spent:.1f}ms")

    print("  结论：401/404 一次就停；5xx/429 才值得指数退避。")
    print("  未知异常默认 FATAL —— 宁可少试，也不要把事故放大。")


# ─────────────────────────────────────────────────────────────
# 演示 3：抖动与重试风暴（纯模拟，不发请求）
# ─────────────────────────────────────────────────────────────

def _storm(max_clients: int = 500, retries: int = 5,
           jitter: str = "none") -> tuple[int, float]:
    """模拟 N 个客户端同时失败，统计 10ms 时间桶里的最大撞车数。"""
    random.seed(20261025)
    buckets: dict[int, int] = {}
    total_wait = 0.0
    for _ in range(max_clients):
        t = 0.0
        for attempt in range(1, retries + 1):
            exp = min(30.0, 0.5 * (2 ** (attempt - 1)))
            if jitter == "none":
                delay = exp
            elif jitter == "equal":
                delay = exp / 2 + random.uniform(0, exp / 2)
            else:
                delay = random.uniform(0, exp)
            t += delay
        total_wait += t
        buckets[int(t * 100)] = buckets.get(int(t * 100), 0) + 1
    peak = max(buckets.values())
    return peak, total_wait / max_clients


def demo_jitter() -> None:
    print("\n" + "=" * 68)
    print("演示 3：500 个客户端同时重试，抖动把洪峰削平多少？")
    print("=" * 68)
    print(f"  {'策略':<12}{'同一 10ms 桶最大并发':>22}{'平均总等待(s)':>16}")
    for jitter, name in (("none", "无抖动"), ("equal", "equal"), ("full", "full")):
        peak, avg_wait = _storm(jitter=jitter)
        print(f"  {name:<12}{peak:>20}{avg_wait:>18.2f}")
    print("  说明：无抖动时所有客户端在同一毫秒醒来，第二波直接把上游再打挂；")
    print("  full jitter 的代价是平均等待略长，换来的是上游不会被自己人压死。")


# ─────────────────────────────────────────────────────────────
# 演示 4：重试 POST 的重复写入灾难
# ─────────────────────────────────────────────────────────────

def demo_idempotency(base_url: str) -> None:
    print("\n" + "=" * 68)
    print("演示 4：重试 POST —— 没有 Idempotency-Key 会写几条？")
    print("=" * 68)
    payload = json.dumps({"amount": 100, "to": "alice"}).encode()

    # 4a. 朴素重试
    State.reset()
    try:
        retry_call(
            lambda attempt: http_call("POST", f"{base_url}/orders", payload,
                                      {"Content-Type": "application/json"}),
            RetryPolicy(attempts=3, base_delay=0.01, jitter="none"),
        )
    except TransientError as exc:
        print(f"  朴素重试最终失败：{exc}")
    print(f"  服务端实际落库 {len(State.rows)} 条（客户端只看到 1 次成功）")
    print(f"  服务端收到 {State.post_calls} 次 POST")

    # 4b. 幂等键
    State.reset()
    key = "order-20261025-0001"
    try:
        retry_call(
            lambda attempt: http_call("POST", f"{base_url}/orders", payload,
                                      {"Content-Type": "application/json",
                                       "Idempotency-Key": key}),
            RetryPolicy(attempts=3, base_delay=0.01, jitter="none"),
        )
    except TransientError as exc:
        print(f"  幂等键重试最终失败：{exc}")
    print(f"  带幂等键后实际落库 {len(State.rows)} 条")
    print(f"  服务端收到 {State.post_calls} 次 POST（第二次命中幂等表，返回 duplicate）")
    print("  关键：幂等键必须由客户端生成并在重试间保持不变，服务端要持久化它。")


# ─────────────────────────────────────────────────────────────
# 自检
# ─────────────────────────────────────────────────────────────

def self_test() -> None:
    # 分类
    assert classify(TransientError("x")) is not None
    assert classify(AuthError("x")).value == "auth"

    # 固定退避序列 + 假的 clock，零等待
    now = [0.0]
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    def always_503(attempt: int) -> None:
        raise TransientError("503")

    try:
        retry_call(always_503, RetryPolicy(attempts=3, base_delay=1, factor=2,
                                           jitter="none"),
                   sleep=fake_sleep, clock=lambda: now[0])
    except TransientError:
        pass
    else:
        raise AssertionError("should exhaust attempts")
    assert sleeps == [1.0, 2.0], sleeps

    # full jitter 落在 [0, exp] 内
    from ops_lib import compute_delay
    for attempt in range(1, 6):
        delay = compute_delay(RetryPolicy(base_delay=1, factor=2, max_delay=8), attempt)
        assert 0 <= delay <= 8, (attempt, delay)

    # 抖动确实打散了时间桶
    no_jitter_peak, _ = _storm(max_clients=100, jitter="none")
    full_jitter_peak, _ = _storm(max_clients=100, jitter="full")
    assert no_jitter_peak == 100, no_jitter_peak
    assert full_jitter_peak < 40, full_jitter_peak

    print(f"✅ 01 self-test passed (no jitter peak={no_jitter_peak}, "
          f"full jitter peak={full_jitter_peak})")


def main() -> None:
    if "--self-test" in sys.argv:
        self_test()
        return

    server = ThreadingHTTPServer(("127.0.0.1", 0), FlakyHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    print(f"本地假冒上游已启动：{base_url}")

    try:
        demo_backoff(base_url)
        demo_classification()
        demo_jitter()
        demo_idempotency(base_url)
    finally:
        server.shutdown()
        server.server_close()
        print("\n本地上游已停止。")


if __name__ == "__main__":
    main()
