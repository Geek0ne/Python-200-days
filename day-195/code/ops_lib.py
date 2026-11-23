#!/usr/bin/env python3
"""
Day 195 · 运维三件套的最小实现：重试、结构化日志、告警收敛。

只用标准库，Python 3.9+。设计原则：

1. **一切可注入**（sleep / clock / random），否则写不出确定性测试；
2. **先分类再重试** —— 对 401 重试 5 次只是浪费钱，还会把账号刷进风控；
3. **日志是给人查的 JSON**，不是给机器看的散文，键名要稳定；
4. **告警必须收敛** —— 一次故障发一千条通知，等于没有通知。

这个库被 01/04/05 三个脚本复用，也是容器里 app.py 的运行时依赖。
"""

from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


# ─────────────────────────────────────────────────────────────
# 1. 错误分类：决定"要不要再试一次"
# ─────────────────────────────────────────────────────────────

class Failure(str, Enum):
    RETRYABLE = "retryable"      # 超时、连接重置、5xx
    RATE_LIMIT = "rate_limit"    # 429，能重试但必须听 Retry-After
    AUTH = "auth"                # 401/403，重试只会更糟
    FATAL = "fatal"              # 400/404/422，参数错了，重试没意义


class TransientError(Exception):
    """可重试：网络抖动、上游 5xx、限流。"""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class PermanentError(Exception):
    """不可重试：请求本身是错的。"""


class AuthError(Exception):
    """凭证问题：重试不会让密码变对。"""


def classify(exc: BaseException) -> Failure:
    """把异常映射成四类。未知异常默认 FATAL —— 宁可少试，不要放大事故。"""
    if isinstance(exc, TransientError):
        return Failure.RATE_LIMIT if exc.retry_after is not None else Failure.RETRYABLE
    if isinstance(exc, AuthError):
        return Failure.AUTH
    return Failure.FATAL


# ─────────────────────────────────────────────────────────────
# 2. 退避策略：指数 + 抖动 + 预算
# ─────────────────────────────────────────────────────────────

@dataclass
class RetryPolicy:
    attempts: int = 5
    base_delay: float = 0.2
    factor: float = 2.0
    max_delay: float = 5.0
    jitter: str = "full"          # full | equal | none
    deadline: float | None = None  # 总时长预算（秒），None = 不限制


@dataclass
class RetryReport:
    attempts: int = 0
    delays: list[float] = field(default_factory=list)
    elapsed: float = 0.0
    last_error: str | None = None


def compute_delay(policy: RetryPolicy, attempt: int,
                  retry_after: float | None = None) -> float:
    """第 attempt 次失败后该睡多久（attempt 从 1 开始）。

    - 指数：base * factor**(attempt-1)，封顶 max_delay
    - Retry-After 优先：服务端说 3 秒就至少 3 秒，但仍然封顶
    - full jitter：在 [0, delay] 均匀取值，打散重试风暴
    - equal jitter：delay/2 + U(0, delay/2)，保底一半等待
    """
    exp = min(policy.max_delay, policy.base_delay * (policy.factor ** (attempt - 1)))
    if retry_after is not None:
        return min(policy.max_delay, max(exp, float(retry_after)))
    if policy.jitter == "full":
        return random.uniform(0, exp)
    if policy.jitter == "equal":
        return exp / 2 + random.uniform(0, exp / 2)
    return exp


def retry_call(
    fn: Callable[[int], Any],
    policy: RetryPolicy | None = None,
    *,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[Any, RetryReport]:
    """执行 fn(attempt)，失败按策略重试。

    返回 (结果, 报告)。耗尽次数或遇到不可重试错误时原样抛出最后一个异常。
    """
    policy = policy or RetryPolicy()
    report = RetryReport()
    start = clock()

    for attempt in range(1, policy.attempts + 1):
        report.attempts = attempt
        try:
            value = fn(attempt)
            report.elapsed = clock() - start
            return value, report
        except Exception as exc:  # noqa: BLE001 —— 这里就是要把所有异常分类
            kind = classify(exc)
            report.last_error = f"{type(exc).__name__}: {exc}"
            report.elapsed = clock() - start

            # 重试无意义的错误：立刻上抛，不要浪费预算
            if kind in (Failure.AUTH, Failure.FATAL):
                raise

            if attempt >= policy.attempts:
                raise

            delay = compute_delay(policy, attempt, getattr(exc, "retry_after", None))
            if policy.deadline is not None and (clock() - start) + delay > policy.deadline:
                raise TimeoutError(
                    f"retry deadline {policy.deadline}s exceeded after {attempt} attempt(s)"
                ) from exc

            report.delays.append(round(delay, 3))
            if on_retry is not None:
                on_retry(attempt, delay, exc)
            sleep(delay)

    raise AssertionError("unreachable")


# ─────────────────────────────────────────────────────────────
# 3. 结构化日志：JSON 行 + 密钥脱敏 + 请求绑定
# ─────────────────────────────────────────────────────────────

_SECRET_KEYS = {
    "password", "passwd", "pwd", "token", "access_token", "refresh_token",
    "secret", "api_secret", "api_key", "apikey", "authorization",
    "x-api-key", "cookie", "set-cookie", "session", "master_key",
}

_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


def redact(value: Any) -> Any:
    """递归把敏感键的值替换成 ***。键名大小写不敏感。"""
    if isinstance(value, dict):
        return {
            key: ("***" if str(key).lower() in _SECRET_KEYS else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class JsonLogger:
    """输出一行一个 JSON 对象，便于 Loki / ES / jq 直接消费。"""

    def __init__(self, service: str, level: str = "INFO",
                 stream=None, _base: dict[str, Any] | None = None) -> None:
        self.service = service
        self.level = level.upper()
        self.stream = stream if stream is not None else sys.stdout
        self._base = dict(_base or {})

    def bind(self, **fields: Any) -> "JsonLogger":
        """返回带固定字段的新 logger，例如 bind(request_id=...)。"""
        base = dict(self._base)
        base.update(fields)
        return JsonLogger(self.service, self.level, self.stream, base)

    def _emit(self, level: str, event: str, fields: dict[str, Any]) -> None:
        if _LEVELS[level] < _LEVELS.get(self.level, 20):
            return
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": level,
            "service": self.service,
            "event": event,
        }
        record.update(self._base)
        record.update(redact(fields))
        self.stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self.stream.flush()

    def debug(self, event: str, **fields: Any) -> None: self._emit("DEBUG", event, fields)
    def info(self, event: str, **fields: Any) -> None: self._emit("INFO", event, fields)
    def warning(self, event: str, **fields: Any) -> None: self._emit("WARNING", event, fields)
    def error(self, event: str, **fields: Any) -> None: self._emit("ERROR", event, fields)
    def critical(self, event: str, **fields: Any) -> None: self._emit("CRITICAL", event, fields)


# ─────────────────────────────────────────────────────────────
# 4. 告警收敛：冷却窗口 + 抑制计数
# ─────────────────────────────────────────────────────────────

@dataclass
class Alert:
    key: str
    severity: str
    message: str
    suppressed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "severity": self.severity,
            "message": self.message,
            "suppressed": self.suppressed,
        }


class AlertSink:
    """同一个 key 在 cooldown 秒内只放行一条，其余累计为 suppressed。

    为什么不是简单的"去重"？因为完全静音会让人以为问题消失了。
    正确做法：一条"发生了 N 次"的汇总告警，比一千条原始告警有用。
    """

    def __init__(self, cooldown: float = 60.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.cooldown = cooldown
        self.clock = clock
        self._state: dict[str, dict[str, float]] = {}
        self.sent: list[Alert] = []

    def emit(self, key: str, severity: str, message: str) -> Alert | None:
        now = self.clock()
        state = self._state.setdefault(key, {"last_sent": float("-inf"), "suppressed": 0})
        if now - state["last_sent"] >= self.cooldown:
            alert = Alert(key, severity, message, suppressed=int(state["suppressed"]))
            state["last_sent"] = now
            state["suppressed"] = 0
            self.sent.append(alert)
            return alert
        state["suppressed"] += 1
        return None

    def reset(self, key: str) -> None:
        """故障恢复时调用：清掉状态，下次再出问题可以立刻告警。"""
        self._state.pop(key, None)


# ─────────────────────────────────────────────────────────────
# 5. 自检：不联网、不 sleep，纯逻辑验证
# ─────────────────────────────────────────────────────────────

def _self_test() -> None:
    # 4xx 类错误不重试
    calls: list[int] = []

    def unauthorized(attempt: int) -> None:
        calls.append(attempt)
        raise AuthError("401")

    try:
        retry_call(unauthorized, RetryPolicy(attempts=5), sleep=lambda _: None)
    except AuthError:
        pass
    else:
        raise AssertionError("AuthError should propagate")
    assert calls == [1], calls

    # 可重试错误：前两次失败，第三次成功
    attempts: list[int] = []
    sleeps: list[float] = []
    fake_now = [0.0]

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        fake_now[0] += seconds

    def flaky(attempt: int) -> str:
        attempts.append(attempt)
        if attempt < 3:
            raise TransientError("503")
        return "ok"

    value, report = retry_call(
        flaky, RetryPolicy(attempts=5, base_delay=1.0, factor=2.0, jitter="none"),
        sleep=fake_sleep, clock=lambda: fake_now[0],
    )
    assert value == "ok" and report.attempts == 3
    assert sleeps == [1.0, 2.0], sleeps

    # 预算限制：deadline 到了就不再等
    fake_now[0] = 0.0
    try:
        retry_call(
            flaky, RetryPolicy(attempts=5, base_delay=1.0, factor=2.0,
                               jitter="none", deadline=2.5),
            sleep=fake_sleep, clock=lambda: fake_now[0],
        )
    except TimeoutError:
        pass
    else:
        raise AssertionError("deadline should stop retries")

    # Retry-After 优先于指数退避
    assert compute_delay(RetryPolicy(base_delay=0.1), 1, retry_after=3.0) == 3.0
    # 封顶
    assert compute_delay(RetryPolicy(base_delay=1, factor=10, max_delay=5,
                                     jitter="none"), 5) == 5.0

    # 日志脱敏
    redacted = redact({"user": "bob", "password": "p@ss", "nested": {"token": "t"}})
    assert redacted == {"user": "bob", "password": "***", "nested": {"token": "***"}}, redacted

    # 告警冷却
    fake_now[0] = 0.0
    sink = AlertSink(cooldown=60, clock=lambda: fake_now[0])
    assert sink.emit("db_down", "critical", "db down") is not None
    assert sink.emit("db_down", "critical", "db down") is None
    assert sink.emit("db_down", "critical", "db down") is None
    fake_now[0] = 61.0
    alert = sink.emit("db_down", "critical", "db down")
    assert alert is not None and alert.suppressed == 2, alert

    print("✅ ops_lib.py self-test passed (4 groups)")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
    else:
        print(__doc__)
