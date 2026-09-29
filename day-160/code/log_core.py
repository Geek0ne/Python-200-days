"""日志安全分析核心模块（Day 160 — 日志安全分析）。

先读这一节：日志分析翻车，几乎都不是"算法不对"，而是下面五个坑。

1. **格式异构**：sshd(syslog)、nginx(combined)、应用(JSON) 三种日志混在一起，
   必须先**标准化**成统一事件，检测逻辑才可能只写一遍。
   标准化 = 解析 + 归一（时间统一到 UTC、字段名统一、动作词表统一）。

2. **时间戳缺失/不可解析**：窗口类检测（暴力破解）**必须有时间**。
   缺失时间戳的事件不猜、不填 now()，而是计入 `no_timestamp` 并在报告里声明
   "这部分无法参与判定"——猜时间等于编造证据。

3. **日志乱序 / 多主机合并**：合并多台机器的日志后，文件顺序毫无意义。
   所以检测前一律 `sort(key=ts)`，并统计乱序条数（信息来源需要被检查）。

4. **跨主机混淆**：同名的 `admin` 在两台机器上是两个可能完全不同的人。
   统计键必须是 `(host, user)` / `(host, src_ip)`，不能只用 user 或 ip。

5. **报告泄露 IP/用户名**：报告会流转。对外版本把 IP 末段掩码（`203.0.113.x`），
   并给出 `subject_sha` 指纹用于跨报告关联同一对象。

另外：**阈值不是真理**。所有检测器都暴露 window/threshold 参数，
报告里必须回显用了什么参数——否则"没告警"和"参数太宽"无法区分。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator, Sequence

# ─────────────────────────── 严重度 / 置信度 ───────────────────────────
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}
TRIAGE_BANDS = ((12, "P0"), (8, "P1"), (4, "P2"), (0, "P3"))

DEFAULT_TZ = timezone(timedelta(hours=8), "CST")  # 日志无时区时按此假设计算


def priority(severity: str, confidence: str) -> int:
    return (SEVERITY_ORDER[severity] + 1) * (CONFIDENCE_ORDER[confidence] + 1)


def triage_band(severity: str, confidence: str) -> str:
    score = priority(severity, confidence)
    for threshold, band in TRIAGE_BANDS:
        if score >= threshold:
            return band
    return "P3"


def subject_sha(value: str) -> str:
    """主体指纹（IP/用户名）：用于跨报告关联，不可逆。"""
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:12]


def mask_ip(ip: str | None) -> str:
    """IPv4 末段掩码，IPv6 保留前两组。报告里默认用这个而不是真实 IP。"""
    if not ip:
        return "-"
    if ":" in ip:
        parts = ip.split(":")
        return ":".join(parts[:2]) + "::x"
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3]) + ".x"
    return ip


# ─────────────────────────────── 事件模型 ───────────────────────────────
@dataclass(frozen=True)
class LogEvent:
    """标准化后的日志事件。

    注意没有 `raw` 字段：原始行可能包含口令片段、Token、Cookie、个人数据，
    复制进结果对象就等于把它们带进报告和 CI 日志。
    需要溯源时用 `ref`（`文件名:行号`）回原文件看。
    """

    ts: datetime | None          # None = 日志里没有可用时间戳（不猜）
    host: str
    source: str                  # sshd / nginx / app
    kind: str                    # auth / http
    action: str                  # login_failed / login_success / request / ...
    user: str | None = None
    src_ip: str | None = None
    status: int | None = None
    path: str | None = None
    ref: str = ""

    @property
    def subject(self) -> tuple:
        """检测统计用的主体键：必须含 host，避免跨主机混淆。"""
        return (self.host, self.src_ip or "-", self.user or "-")


@dataclass
class LogCoverage:
    """覆盖与可判定性统计。任何一项缺口都要如实进报告。"""

    lines_total: int = 0
    parsed: int = 0
    unparsed: int = 0
    no_timestamp: int = 0
    deduped: int = 0
    out_of_order: int = 0
    hosts: list = field(default_factory=list)
    time_start: datetime | None = None
    time_end: datetime | None = None

    @property
    def complete(self) -> bool:
        return self.unparsed == 0 and self.no_timestamp == 0

    @property
    def gaps(self) -> list:
        gaps = []
        if self.unparsed:
            gaps.append(f"unparsed={self.unparsed} 行无法识别格式（未参与判定）")
        if self.no_timestamp:
            gaps.append(f"no_timestamp={self.no_timestamp} 条缺少时间戳（窗口类检测不可用）")
        return gaps

    def to_dict(self) -> dict:
        data = asdict(self)
        data["complete"] = self.complete
        data["gaps"] = self.gaps
        data["time_start"] = self.time_start.isoformat() if self.time_start else None
        data["time_end"] = self.time_end.isoformat() if self.time_end else None
        return data


# ─────────────────────────────── 解析层 ───────────────────────────────
SYSLOG_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

SYSLOG_RE = re.compile(
    r"^(?P<ts>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<proc>[\w\-/]+)\[(?P<pid>\d+)\]:\s*(?P<msg>.*)$"
)
NGINX_RE = re.compile(
    r"^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+"
    r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)(?:\s+[^"]*)?"\s+'
    r"(?P<status>\d{3})\s+(?P<size>\S+)"
)
SSHD_MSG = (
    ("login_failed", re.compile(r"^Failed (?:password|publickey) for (?:invalid user )?(?P<user>\S+) from (?P<ip>\S+) port")),
    ("login_success", re.compile(r"^Accepted (?:password|publickey|keyboard-interactive/pam) for (?P<user>\S+) from (?P<ip>\S+) port")),
    ("invalid_user", re.compile(r"^Invalid user (?P<user>\S+) from (?P<ip>\S+)")),
    ("conn_closed", re.compile(r"^(?:Connection closed|Disconnected) by (?:authenticating user (?P<user>\S+) )?(?P<ip>\S+) port")),
)

JSON_ACTIONS = {
    "login_failed": ("auth", "login_failed"),
    "login.success": ("auth", "login_success"),
    "login_success": ("auth", "login_success"),
    "request": ("http", "request"),
}


def parse_timestamp(text: str, *, assume_tz: timezone = DEFAULT_TZ, year: int = 2026) -> datetime | None:
    """把各格式时间戳解析成**带时区**的 datetime。支持不了就返回 None（不猜）。"""
    text = text.strip()
    if not text:
        return None
    # 1) ISO8601（含 Z 与 ±hh:mm）
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=assume_tz)
    except ValueError:
        pass
    # 2) nginx: 19/Sep/2026:06:12:01 +0800
    for fmt in ("%d/%b/%Y:%H:%M:%S %z", "%d/%b/%Y:%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=assume_tz)
        except ValueError:
            continue
    # 3) syslog: Sep 19 06:12:01（无年份，用上下文年份补齐）
    m = re.match(r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<clock>\d{2}:\d{2}:\d{2})$", text)
    if m:
        month = SYSLOG_MONTHS.get(m.group("mon"))
        if month:
            hh, mm, ss = (int(x) for x in m.group("clock").split(":"))
            return datetime(year, month, int(m.group("day")), hh, mm, ss, tzinfo=assume_tz)
    # 4) 朴素格式
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=assume_tz)
        except ValueError:
            continue
    return None


def detect_source(line: str) -> str:
    """按形态猜日志来源。解析顺序：JSON → nginx → sshd → unknown。"""
    stripped = line.strip()
    if stripped.startswith("{"):
        return "app"
    if NGINX_RE.match(stripped):
        return "nginx"
    if SYSLOG_RE.match(stripped) and re.search(r"sshd|sudo|systemd-logind", stripped):
        return "sshd"
    return "unknown"


def parse_sshd(line: str, fallback_host: str, *, assume_tz, year: int, ref: str) -> LogEvent | None:
    m = SYSLOG_RE.match(line.strip())
    if not m:
        return None
    ts = parse_timestamp(m.group("ts"), assume_tz=assume_tz, year=year)
    msg = m.group("msg")
    for action, pattern in SSHD_MSG:
        hit = pattern.search(msg)
        if not hit:
            continue
        groups = hit.groupdict()
        return LogEvent(
            ts=ts, host=m.group("host") or fallback_host, source="sshd", kind="auth",
            action=action, user=groups.get("user"), src_ip=groups.get("ip"), ref=ref,
        )
    # 是 sshd 行但没有我们关心的动作：不算解析失败，返回 None 由调用方计入"跳过"
    return None


def parse_nginx(line: str, fallback_host: str, *, assume_tz, year: int, ref: str) -> LogEvent | None:
    m = NGINX_RE.match(line.strip())
    if not m:
        return None
    return LogEvent(
        ts=parse_timestamp(m.group("ts"), assume_tz=assume_tz, year=year),
        host=fallback_host, source="nginx", kind="http", action="request",
        src_ip=m.group("ip"), status=int(m.group("status")), path=m.group("path"), ref=ref,
    )


def parse_json_log(line: str, fallback_host: str, *, assume_tz, year: int, ref: str) -> LogEvent | None:
    try:
        data = json.loads(line)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    event_key = str(data.get("event") or data.get("action") or "").lower()
    kind, action = JSON_ACTIONS.get(event_key, ("app", event_key or "unknown"))
    return LogEvent(
        ts=parse_timestamp(str(data.get("time") or data.get("@timestamp") or ""),
                           assume_tz=assume_tz, year=year),
        host=str(data.get("host") or fallback_host), source="app", kind=kind, action=action,
        user=data.get("user"), src_ip=data.get("src_ip") or data.get("ip"),
        status=int(data["status"]) if str(data.get("status", "")).isdigit() else None,
        path=data.get("path"), ref=ref,
    )


PARSERS = {"sshd": parse_sshd, "nginx": parse_nginx, "app": parse_json_log}


def parse_line(line: str, fallback_host: str, *, assume_tz=DEFAULT_TZ, year: int = 2026,
               ref: str = "") -> LogEvent | None:
    source = detect_source(line)
    parser = PARSERS.get(source)
    if parser is None:
        return None
    return parser(line, fallback_host, assume_tz=assume_tz, year=year, ref=ref)


def parse_lines(lines: Iterable[str], *, fallback_host: str = "unknown-host",
                assume_tz: timezone = DEFAULT_TZ, year: int = 2026,
                source_name: str = "stdin") -> tuple:
    """解析并标准化一批日志行，返回 (events, coverage)。events 已按时间排序。"""
    coverage = LogCoverage()
    events: list[LogEvent] = []
    seen: set = set()
    previous_ts: datetime | None = None

    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        coverage.lines_total += 1
        event = parse_line(line, fallback_host, assume_tz=assume_tz, year=year,
                           ref=f"{source_name}:{lineno}")
        if event is None:
            coverage.unparsed += 1
            continue
        key = (event.ts, event.host, event.action, event.user, event.src_ip, event.status, event.path)
        if key in seen:
            coverage.deduped += 1
            continue
        seen.add(key)
        if event.ts is None:
            coverage.no_timestamp += 1
        else:
            if previous_ts is not None and event.ts < previous_ts:
                coverage.out_of_order += 1
            previous_ts = event.ts
        events.append(event)

    events.sort(key=lambda e: (e.ts is None, e.ts or datetime.min.replace(tzinfo=timezone.utc)))
    coverage.parsed = len(events)
    if events:
        coverage.hosts = sorted({e.host for e in events})
        timed = [e.ts for e in events if e.ts]
        if timed:
            coverage.time_start, coverage.time_end = min(timed), max(timed)
    return events, coverage


# ─────────────────────────────── 告警模型 ───────────────────────────────
@dataclass
class Alert:
    detector: str
    title: str
    severity: str
    confidence: str
    subject: str            # 已掩码的主体（IP / user@host）
    subject_sha: str
    count: int
    window_seconds: int
    first_ts: datetime | None
    last_ts: datetime | None
    evidence: str
    why: str
    remediation: str
    parameters: dict = field(default_factory=dict)   # 回显实际使用的阈值

    @property
    def band(self) -> str:
        return triage_band(self.severity, self.confidence)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["priority"] = priority(self.severity, self.confidence)
        data["triage_band"] = self.band
        data["first_ts"] = self.first_ts.isoformat() if self.first_ts else None
        data["last_ts"] = self.last_ts.isoformat() if self.last_ts else None
        return data


@dataclass
class AlertReport:
    alerts: list = field(default_factory=list)
    coverage: LogCoverage = field(default_factory=LogCoverage)
    detectors_run: list = field(default_factory=list)
    parameters: dict = field(default_factory=dict)

    def by_severity(self) -> dict:
        counts = {name: 0 for name in SEVERITY_ORDER}
        for alert in self.alerts:
            counts[alert.severity] += 1
        return counts

    def at_or_above(self, threshold: str = "high") -> list:
        limit = SEVERITY_ORDER[threshold]
        return [a for a in self.alerts if SEVERITY_ORDER[a.severity] >= limit]

    def to_dict(self) -> dict:
        return {
            "summary": {
                "alerts": len(self.alerts),
                "by_severity": self.by_severity(),
                "by_triage_band": {band: sum(1 for a in self.alerts if a.band == band)
                                   for band in ("P0", "P1", "P2", "P3")},
            },
            "parameters": self.parameters,
            "coverage": self.coverage.to_dict(),
            "detectors_run": list(self.detectors_run),
            "alerts": [a.to_dict() for a in self.alerts],
        }


# ─────────────────────────────── 检测器 ───────────────────────────────
def _timed(events: Iterable[LogEvent]) -> list:
    """只保留有时间戳的事件——窗口类检测的前提。"""
    return [e for e in events if e.ts is not None]


def _sliding_windows(items: Sequence, window_seconds: int) -> Iterator[list]:
    """按时间滑窗切分（items 必须已按时间升序且都有 ts）。"""
    buffer: deque = deque()
    for item in items:
        buffer.append(item)
        while buffer and (item.ts - buffer[0].ts).total_seconds() > window_seconds:
            buffer.popleft()
        yield list(buffer)


def detect_brute_force(events: Iterable[LogEvent], *, window_seconds: int = 300,
                       threshold: int = 8, host: str | None = None) -> list:
    """单源暴力破解：同一 (host, src_ip) 在窗口内失败次数 >= threshold。"""
    failures = [e for e in _timed(events)
                if e.action == "login_failed" and (host is None or e.host == host)]
    grouped: dict = defaultdict(list)
    for event in failures:
        grouped[(event.host, event.src_ip)].append(event)

    alerts = []
    for (ev_host, ip), items in sorted(grouped.items(), key=lambda kv: str(kv[0])):
        items.sort(key=lambda e: e.ts)
        best: list = []
        for window in _sliding_windows(items, window_seconds):
            if len(window) > len(best):
                best = window
        if len(best) >= threshold:
            users = sorted({e.user for e in best if e.user})
            alerts.append(Alert(
                detector="brute_force_single_source",
                title="单一来源暴力破解尝试",
                severity="high" if len(best) < threshold * 3 else "critical",
                confidence="high",
                subject=f"{mask_ip(ip)}@{ev_host}",
                subject_sha=subject_sha(f"{ev_host}|{ip}"),
                count=len(best),
                window_seconds=window_seconds,
                first_ts=best[0].ts, last_ts=best[-1].ts,
                evidence=f"{window_seconds}s 内失败 {len(best)} 次；涉及账号数 {len(users)}",
                why="短窗口内高频认证失败是口令猜测的直接特征，成功一次即可能失陷。",
                remediation="对该来源限速/封禁或改用密钥认证；检查是否已有成功登录。",
                parameters={"window_seconds": window_seconds, "threshold": threshold},
            ))
    return alerts


def detect_distributed_bruteforce(events: Iterable[LogEvent], *, window_seconds: int = 600,
                                  threshold: int = 10, min_sources: int = 3) -> list:
    """分布式爆破：同一 (host, user) 在窗口内被多个来源尝试。

    单 IP 都可能低于阈值，所以 per-IP 规则抓不到——这是真实存在的规避方式。
    """
    failures = [e for e in _timed(events) if e.action == "login_failed" and e.user]
    grouped: dict = defaultdict(list)
    for event in failures:
        grouped[(event.host, event.user)].append(event)

    alerts = []
    for (ev_host, user), items in sorted(grouped.items(), key=lambda kv: str(kv[0])):
        items.sort(key=lambda e: e.ts)
        best: list = []
        for window in _sliding_windows(items, window_seconds):
            if len(window) > len(best):
                best = window
        sources = {e.src_ip for e in best}
        if len(best) >= threshold and len(sources) >= min_sources:
            alerts.append(Alert(
                detector="brute_force_distributed",
                title="分布式口令猜测（多来源同一账号）",
                severity="medium",
                confidence="medium",   # 多来源也可能来自共享出口 IP/NAT，需要人工确认
                subject=f"{user}@{ev_host}",
                subject_sha=subject_sha(f"{ev_host}|{user}"),
                count=len(best),
                window_seconds=window_seconds,
                first_ts=best[0].ts, last_ts=best[-1].ts,
                evidence=f"{window_seconds}s 内失败 {len(best)} 次，来源 IP {len(sources)} 个",
                why="每个来源都低于单源阈值，只有按账号聚合才看得出被集中攻击。",
                remediation="锁定/加固该账号（MFA、密钥认证），并结合来源情报判断是否共享出口。",
                parameters={"window_seconds": window_seconds, "threshold": threshold,
                            "min_sources": min_sources},
            ))
    return alerts


def detect_failed_then_success(events: Iterable[LogEvent], *, window_seconds: int = 900,
                               min_failures: int = 3) -> list:
    """失败后成功：同一 (host, user, ip) 先失败若干次、随后登录成功。

    这是最需要人工介入的模式：可能是同事记错口令，也可能是爆破得手。
    必须同 host + 同 user + 同来源 IP 才算同一链路。
    """
    items = [e for e in _timed(events) if e.kind == "auth" and e.user and e.src_ip]
    grouped: dict = defaultdict(list)
    for event in items:
        grouped[(event.host, event.user, event.src_ip)].append(event)

    alerts = []
    for (ev_host, user, ip), seq in sorted(grouped.items(), key=lambda kv: str(kv[0])):
        seq.sort(key=lambda e: e.ts)
        failures: deque = deque()
        for event in seq:
            if event.action == "login_failed":
                failures.append(event)
                continue
            if event.action != "login_success":
                continue
            while failures and (event.ts - failures[0].ts).total_seconds() > window_seconds:
                failures.popleft()
            if len(failures) >= min_failures:
                alerts.append(Alert(
                    detector="failed_then_success",
                    title="多次失败后登录成功",
                    severity="high",
                    confidence="medium",   # 也可能是本人连续输错后输对
                    subject=f"{user}@{ev_host}",
                    subject_sha=subject_sha(f"{ev_host}|{user}|{ip}"),
                    count=len(failures),
                    window_seconds=window_seconds,
                    first_ts=failures[0].ts, last_ts=event.ts,
                    evidence=f"失败 {len(failures)} 次后成功，来源 {mask_ip(ip)}",
                    why="失败堆积后的成功登录是账户可能已被攻破的最直接线索。",
                    remediation="确认该登录是否为本人；必要时强制改密、撤销会话、开启 MFA。",
                    parameters={"window_seconds": window_seconds, "min_failures": min_failures},
                ))
                failures.clear()
    return alerts


def detect_new_source(events: Iterable[LogEvent], baseline: dict | None = None) -> list:
    """新来源登录：某 (host, user) 出现了历史上没见过的来源 IP。

    baseline 形如 {"host|user": {"1.2.3.4", ...}}；无 baseline 时退回
    "在本次日志范围内只出现过一次（且成功）"的启发式，置信度低。
    """
    baseline = baseline or {}
    successes = [e for e in _timed(events)
                 if e.action == "login_success" and e.user and e.src_ip]
    known: dict = defaultdict(set)
    for event in events:
        if event.src_ip:
            known[f"{event.host}|{event.user}"].add(event.src_ip)

    alerts = []
    for event in successes:
        key = f"{event.host}|{event.user}"
        allowed = set(baseline.get(key, ()))
        if allowed and event.src_ip not in allowed:
            alerts.append(Alert(
                detector="login_from_unexpected_source",
                title="登录来自基线之外的来源",
                severity="medium",
                confidence="medium",
                subject=f"{event.user}@{event.host}",
                subject_sha=subject_sha(key),
                count=1, window_seconds=0,
                first_ts=event.ts, last_ts=event.ts,
                evidence=f"来源 {mask_ip(event.src_ip)} 不在该账号基线来源中",
                why="账号通常从固定网段/跳板机登录；来源漂移常先于失陷被观察到。",
                remediation="与本人确认（出差/VPN 变更），否则按可疑登录处置。",
                parameters={"baseline_accounts": len(baseline)},
            ))
        elif not allowed and len({e.src_ip for e in events
                                  if e.user == event.user and e.host == event.host}) == 1:
            alerts.append(Alert(
                detector="login_from_single_source",
                title="本次范围内仅出现单一来源的成功登录",
                severity="low",
                confidence="low",
                subject=f"{event.user}@{event.host}",
                subject_sha=subject_sha(key),
                count=1, window_seconds=0,
                first_ts=event.ts, last_ts=event.ts,
                evidence=f"来源 {mask_ip(event.src_ip)}（无基线，仅启发式）",
                why="无基线时只能说'没见过'，不能断言异常——这是低置信度的原因。",
                remediation="建立并维护账号来源基线，之后该检测才能给出可信结论。",
                parameters={"baseline_accounts": 0},
            ))
    return alerts


def detect_off_hours_success(events: Iterable[LogEvent], *, start_hour: int = 8,
                             end_hour: int = 20) -> list:
    """非工作时段成功登录（按事件本地时区的小时判断；跨时区需先统一）。"""
    alerts = []
    for event in _timed(events):
        if event.action != "login_success" or not event.user:
            continue
        hour = event.ts.astimezone(DEFAULT_TZ).hour
        if start_hour <= hour < end_hour:
            continue
        alerts.append(Alert(
            detector="off_hours_success",
            title="非工作时段成功登录",
            severity="low",
            confidence="low",
            subject=f"{event.user}@{event.host}",
            subject_sha=subject_sha(f"{event.host}|{event.user}|{event.src_ip}"),
            count=1, window_seconds=0,
            first_ts=event.ts, last_ts=event.ts,
            evidence=f"本地时间 {event.ts.astimezone(DEFAULT_TZ):%H:%M}（工作时段 {start_hour}:00-{end_hour}:00）",
            why="运维/值班会产生大量正常夜间登录，所以这是低置信度线索，需结合值班表。",
            remediation="对照排班与变更记录；无常班表就无法降低这类误报。",
            parameters={"start_hour": start_hour, "end_hour": end_hour},
        ))
    return alerts


def detect_web_auth_abuse(events: Iterable[LogEvent], *, window_seconds: int = 600,
                          threshold: int = 20) -> list:
    """Web 侧撞库：同一来源在窗口内大量 401/403 响应。"""
    items = [e for e in _timed(events)
             if e.kind == "http" and e.status in (401, 403) and e.src_ip]
    grouped: dict = defaultdict(list)
    for event in items:
        grouped[(event.host, event.src_ip)].append(event)

    alerts = []
    for (ev_host, ip), seq in sorted(grouped.items(), key=lambda kv: str(kv[0])):
        seq.sort(key=lambda e: e.ts)
        best: list = []
        for window in _sliding_windows(seq, window_seconds):
            if len(window) > len(best):
                best = window
        if len(best) >= threshold:
            paths = Counter(e.path for e in best).most_common(3)
            alerts.append(Alert(
                detector="web_auth_abuse",
                title="Web 认证接口高频失败（疑似撞库）",
                severity="medium",
                confidence="medium",
                subject=f"{mask_ip(ip)}@{ev_host}",
                subject_sha=subject_sha(f"{ev_host}|{ip}"),
                count=len(best),
                window_seconds=window_seconds,
                first_ts=best[0].ts, last_ts=best[-1].ts,
                evidence=f"{window_seconds}s 内 401/403 共 {len(best)} 次；热点路径 {[p for p, _ in paths]}",
                why="撞库用大量已知账号口令尝试登录接口，表现为短时间密集的鉴权失败。",
                remediation="对该来源限速、加验证码与 MFA；排查是否有成功登录伴随出现。",
                parameters={"window_seconds": window_seconds, "threshold": threshold},
            ))
    return alerts


def detect_path_traversal_probe(events: Iterable[LogEvent]) -> list:
    """目录穿越探测：请求路径含 ../ 或 %2e%2e 且未被正常化。"""
    pattern = re.compile(r"(\.\./|%2e%2e|%252e)", re.IGNORECASE)
    alerts = []
    for event in _timed(events):
        if event.kind != "http" or not event.path or not pattern.search(event.path):
            continue
        alerts.append(Alert(
            detector="path_traversal_probe",
            title="请求路径包含目录穿越特征",
            severity="medium",
            confidence="high",
            subject=f"{mask_ip(event.src_ip)}@{event.host}",
            subject_sha=subject_sha(f"{event.host}|{event.src_ip}"),
            count=1, window_seconds=0,
            first_ts=event.ts, last_ts=event.ts,
            evidence=f"路径含穿越特征，响应码 {event.status}（仅记录，未构造请求验证）",
            why="路径遍历是文件读取类漏洞的典型探测手法；本工具只做日志侧识别，不发起请求。",
            remediation="确认应用是否做了路径规范化与白名单；结合 WAF 阻断该来源。",
            parameters={"pattern": "../ | %2e%2e | %252e"},
        ))
    return alerts


DETECTORS = {
    "brute_force_single_source": detect_brute_force,
    "brute_force_distributed": detect_distributed_bruteforce,
    "failed_then_success": detect_failed_then_success,
    "login_from_unexpected_source": detect_new_source,
    "off_hours_success": detect_off_hours_success,
    "web_auth_abuse": detect_web_auth_abuse,
    "path_traversal_probe": detect_path_traversal_probe,
}


def analyze(events: Sequence[LogEvent], coverage: LogCoverage | None = None, *,
            baseline: dict | None = None, parameters: dict | None = None) -> AlertReport:
    """跑全部检测器并汇总。每个检测器的阈值都通过 parameters 回显。"""
    params = parameters or {}
    alerts: list = []
    alerts += detect_brute_force(events, window_seconds=params.get("brute_window", 300),
                                 threshold=params.get("brute_threshold", 8))
    alerts += detect_distributed_bruteforce(events, window_seconds=params.get("dist_window", 600),
                                            threshold=params.get("dist_threshold", 10),
                                            min_sources=params.get("dist_min_sources", 3))
    alerts += detect_failed_then_success(events, window_seconds=params.get("fts_window", 900),
                                         min_failures=params.get("fts_min_failures", 3))
    alerts += detect_new_source(events, baseline=baseline)
    alerts += detect_off_hours_success(events, start_hour=params.get("work_start", 8),
                                       end_hour=params.get("work_end", 20))
    alerts += detect_web_auth_abuse(events, window_seconds=params.get("web_window", 600),
                                    threshold=params.get("web_threshold", 20))
    alerts += detect_path_traversal_probe(events)

    alerts.sort(key=lambda a: (-priority(a.severity, a.confidence), a.detector, a.subject))
    return AlertReport(
        alerts=alerts,
        coverage=coverage or LogCoverage(),
        detectors_run=sorted(DETECTORS),
        parameters=params,
    )


def summarize(report: AlertReport) -> str:
    sev = report.by_severity()
    parts = " ".join(f"{k}={v}" for k, v in sev.items() if v)
    state = "覆盖完整" if report.coverage.complete else "覆盖不全"
    return (f"alerts={len(report.alerts)} [{parts or '无'}] "
            f"lines={report.coverage.lines_total} parsed={report.coverage.parsed} {state}")
