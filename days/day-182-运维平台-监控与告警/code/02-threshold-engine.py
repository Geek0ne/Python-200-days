#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 182 - 自动化运维平台（一）：服务器监控 + 告警
02 - 阈值判定引擎：连续次数（for）、迟滞（hysteresis）、抖动（flapping）判定

要点：
- 「超阈值」不等于「该告警」。真正要回答的是三个问题：
    1) 超了几次？    -> 连续 N 次才升级（对应 Prometheus 的 for: 3m）
    2) 回落了吗？    -> 迟滞：跌回阈值下方不算恢复，得跌到「恢复线」以下
    3) 是不是在抖？  -> 抖动窗口内来回翻转太多次，就别再喊人了
- 本引擎是纯函数式状态机：调用者负责喂 (value, now)，引擎只负责吐事件。
  这样可以用「假时钟」把几小时的行为在毫秒内跑完（自检就是这么干的）。
- 事件类型：pending / firing / resolved / dropped（毛刺被过滤）。

用法：
    python3 02-threshold-engine.py --self-test
    python3 02-threshold-engine.py --demo --scenario spike
    python3 02-threshold-engine.py --demo --scenario sustained
    python3 02-threshold-engine.py --demo --scenario hysteresis
    python3 02-threshold-engine.py --demo --scenario flap
"""

import argparse
import sys


# --------------------------------------------------------------------------- #
# 指标取值：支持 "host_metrics.cpu_percent" / "app_metrics[0].latency_ms"
# 以及把探活状态 up/down 直接映射成 1.0/0.0，好让阈值规则统一处理。
# --------------------------------------------------------------------------- #
def extract(snap, path):
    cur = snap
    for raw in path.split("."):
        idx = None
        part = raw
        if raw.endswith("]") and "[" in raw:
            part, _, rest = raw.partition("[")
            idx = int(rest[:-1])
        if part:
            cur = cur[part]
        if idx is not None:
            cur = cur[idx]
    if cur == "up":
        return 1.0
    if cur == "down":
        return 0.0
    return float(cur)


# --------------------------------------------------------------------------- #
# 单条规则的状态机
# --------------------------------------------------------------------------- #
class ThresholdRule:
    """
    op=">"  : 指标 > threshold 算越界，恢复要等 <= release    （release <= threshold）
    op="<"  : 指标 < threshold 算越界，恢复要等 >= release    （release >= threshold）

    consecutive : 连续越界多少次才 firing（1 = 立刻告警）
    flap_window : 抖动统计窗口（秒）
    flap_limit  : 窗口内 firing/resolved 翻转达到这个次数，判定为抖动
    """

    def __init__(self, name, metric, op, threshold, release=None, consecutive=1,
                 flap_window=60.0, flap_limit=4, severity="warning"):
        if op not in (">", "<"):
            raise ValueError("op 只能是 > 或 <，收到 " + str(op))
        if consecutive < 1:
            raise ValueError("consecutive 至少为 1")
        if release is None:
            release = threshold
        if op == ">" and release > threshold:
            raise ValueError("op='>' 时 release 必须 <= threshold（否则永远恢复不了）")
        if op == "<" and release < threshold:
            raise ValueError("op='<' 时 release 必须 >= threshold（否则永远恢复不了）")
        self.name = name
        self.metric = metric
        self.op = op
        self.threshold = float(threshold)
        self.release = float(release)
        self.consecutive = int(consecutive)
        self.flap_window = float(flap_window)
        self.flap_limit = int(flap_limit)
        self.severity = severity

        self.state = "ok"
        self.flapping = False
        self._breach_run = 0
        self._transitions = []   # 最近的 firing/resolved 时间点

    # -- 判定原语 ---------------------------------------------------------- #
    def _is_breach(self, value):
        return value > self.threshold if self.op == ">" else value < self.threshold

    def _is_released(self, value):
        return value <= self.release if self.op == ">" else value >= self.release

    def _flap_check(self, now):
        cutoff = now - self.flap_window
        self._transitions = [t for t in self._transitions if t >= cutoff]
        self.flapping = len(self._transitions) >= self.flap_limit

    # -- 主循环 ------------------------------------------------------------ #
    def update(self, value, now):
        """喂一个样本；有状态变化时返回一个事件 dict，否则返回 None。"""
        prev = self.state
        event_type = None

        if self._is_breach(value):
            if prev == "firing":
                new = "firing"                     # 已在告警，保持
            else:
                self._breach_run += 1
                if self._breach_run >= self.consecutive:
                    new = "firing"
                    event_type = "firing"
                else:
                    new = "pending"
                    event_type = "pending"
        else:
            if prev == "firing":
                if self._is_released(value):
                    new = "ok"
                    self._breach_run = 0
                    event_type = "resolved"
                else:
                    new = "firing"                 # 迟滞：没到恢复线就继续告警
            else:
                if prev == "pending":
                    event_type = "dropped"         # 连续次数没凑够就回落 -> 过滤掉
                new = "ok"
                self._breach_run = 0

        if event_type in ("firing", "resolved"):
            self._transitions.append(now)

        self.state = new
        self._flap_check(now)

        if event_type is None:
            return None
        return {
            "rule": self.name,
            "metric": self.metric,
            "type": event_type,
            "state": new,
            "value": value,
            "threshold": self.threshold,
            "release": self.release,
            "consecutive": self.consecutive,
            "breach_run": self._breach_run,
            "severity": self.severity,
            "flapping": self.flapping,
            "ts": now,
        }


class RuleSet:
    def __init__(self, rules):
        self._by_metric = {}
        for rule in rules:
            self._by_metric.setdefault(rule.metric, []).append(rule)

    @property
    def rules(self):
        out = []
        for group in self._by_metric.values():
            out.extend(group)
        return out

    def evaluate(self, snap, now):
        events = []
        for metric, rules in self._by_metric.items():
            try:
                value = extract(snap, metric)
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            for rule in rules:
                ev = rule.update(value, now)
                if ev is not None:
                    events.append(ev)
        return events


def default_rules():
    return [
        ThresholdRule("host_cpu_high", "host_metrics.cpu_percent", ">", 90, 80,
                      consecutive=3, flap_window=300.0, flap_limit=4, severity="critical"),
        ThresholdRule("host_mem_high", "host_metrics.mem_percent", ">", 85, 75,
                      consecutive=3, flap_window=300.0, flap_limit=4),
        ThresholdRule("host_disk_high", "host_metrics.disk_percent", ">", 85, 80,
                      consecutive=1, flap_window=3600.0, flap_limit=4),
        ThresholdRule("app_down", "app_metrics[0].status", "<", 0.5, 0.5,
                      consecutive=2, flap_window=120.0, flap_limit=4, severity="critical"),
        ThresholdRule("app_latency_slow", "app_metrics[0].latency_ms", ">", 500, 300,
                      consecutive=3, flap_window=300.0, flap_limit=4),
    ]


# --------------------------------------------------------------------------- #
# 演示
# --------------------------------------------------------------------------- #
SCENARIOS = {
    "spike": [40, 40, 95, 41, 42, 40],
    "sustained": [40, 88, 91, 92, 93, 94, 95, 70, 65, 60, 40],
    "hysteresis": [40, 95, 95, 95, 88, 86, 84, 82, 81, 79, 60],
    "flap": [40, 95, 95, 95, 60, 95, 95, 95, 60, 95, 95, 95, 60, 95, 95, 95, 60],
    "disk": [50, 86, 87, 88, 88, 88],
}


def render_timeline(rule, values):
    print("scenario=%s  rule=%s  metric=%s  %s %s (release %s)  consecutive=%d"
          % ("(demo)", rule.name, rule.metric, rule.op, rule.threshold, rule.release, rule.consecutive))
    print("%-6s %-8s %-9s %-9s %s" % ("tick", "value", "state", "event", "note"))
    for tick, value in enumerate(values):
        ev = rule.update(value, float(tick))
        if rule.state == "pending" and ev and ev["type"] == "pending":
            note = "越界 %d/%d" % (ev["breach_run"], rule.consecutive)
        elif ev and ev["type"] == "dropped":
            note = "毛刺被过滤（未达连续次数）"
        elif rule.state == "firing" and not ev:
            note = "迟滞保持（未到恢复线 %s）" % rule.release
        elif ev and ev["type"] == "firing":
            note = "升级为告警" + ("（抖动中，将降级/抑制）" if ev["flapping"] else "")
        elif ev and ev["type"] == "resolved":
            note = "恢复通知" + ("（抖动中，将降级/抑制）" if ev["flapping"] else "")
        else:
            note = ""
        print("%-6d %-8s %-9s %-9s %s"
              % (tick, value, rule.state, ev["type"] if ev else "-", note))


# --------------------------------------------------------------------------- #
# 自检
# --------------------------------------------------------------------------- #
def self_test():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        print(("  PASS  " if cond else "  FAIL  ") + msg)

    print("== 02 阈值/抖动自检 ==")

    # 0) 参数校验：迟滞方向写反要直接报错，不能默默跑
    try:
        ThresholdRule("bad", "m", ">", 90, 95)
        check(False, "release > threshold（op='>'）应当报错")
    except ValueError:
        check(True, "release > threshold（op='>'）被拒绝")
    try:
        ThresholdRule("bad", "m", "<", 0.5, 0.1)
        check(False, "release < threshold（op='<'）应当报错")
    except ValueError:
        check(True, "release < threshold（op='<'）被拒绝")

    # 1) 单次尖峰不能触发告警
    r = ThresholdRule("cpu", "host_metrics.cpu_percent", ">", 90, 80, consecutive=3)
    seq = [40.0, 95.0, 41.0, 40.0]
    events = [r.update(v, float(i)) for i, v in enumerate(seq)]
    types = [e["type"] for e in events if e]
    check(types == ["pending", "dropped"], "单次尖峰：只出 pending + dropped，不出 firing（实测 %s）" % types)
    check(r.state == "ok", "单次尖峰后状态回到 ok（实测 %s）" % r.state)

    # 2) 连续 3 次越界 -> 恰好一次 firing
    r = ThresholdRule("cpu", "host_metrics.cpu_percent", ">", 90, 80, consecutive=3)
    seq = [40.0, 91.0, 92.0, 93.0, 94.0, 95.0]
    events = [e for e in (r.update(v, float(i)) for i, v in enumerate(seq)) if e]
    fires = [e for e in events if e["type"] == "firing"]
    check(len(fires) == 1, "连续 3 次越界只 firing 一次（实测 %d 次）" % len(fires))
    check(fires[0]["breach_run"] == 3, "升级发生在第 3 次越界（实测 breach_run=%d）" % fires[0]["breach_run"])

    # 3) 迟滞：跌到阈值下方但没到恢复线，仍然 firing、不发 resolved
    r = ThresholdRule("cpu", "host_metrics.cpu_percent", ">", 90, 80, consecutive=1)
    r.update(95.0, 0.0)
    ok_after = r.update(85.0, 1.0)
    check(r.state == "firing" and ok_after is None,
          "迟滞：85 在 (release=80, threshold=90] 之间，保持 firing 且无事件")
    res = r.update(79.0, 2.0)
    check(res is not None and res["type"] == "resolved", "跌破 release=80 -> resolved（实测 %s）" % (res and res["type"]))

    # 4) 恢复后能再次告警
    r = ThresholdRule("cpu", "host_metrics.cpu_percent", ">", 90, 80, consecutive=1)
    r.update(95.0, 0.0)
    r.update(60.0, 1.0)
    again = r.update(95.0, 2.0)
    check(again is not None and again["type"] == "firing", "恢复后再次越界 -> 再次 firing")

    # 5) 抖动判定：窗口内来回翻转 4 次即命中
    r = ThresholdRule("cpu", "host_metrics.cpu_percent", ">", 90, 80, consecutive=1,
                      flap_window=100.0, flap_limit=4)
    flips = 0
    for i, v in enumerate([95.0, 60.0, 95.0, 60.0, 95.0, 60.0, 95.0]):
        ev = r.update(v, float(i))
        if ev and ev["type"] in ("firing", "resolved"):
            flips += 1
            if ev["flapping"]:
                break
    check(r.flapping is True, "窗口内翻转 %d 次后判定为抖动（flapping=True）" % flips)

    # 6) 抖动判断用的是「时间窗口」，不是「总次数」：把窗口调小，翻转就不再算抖动
    r = ThresholdRule("cpu", "host_metrics.cpu_percent", ">", 90, 80, consecutive=1,
                      flap_window=2.0, flap_limit=4)
    seen_flap = False
    for i, v in enumerate([95.0, 60.0, 95.0, 60.0, 95.0, 60.0, 95.0]):
        ev = r.update(v, float(i) * 10.0)   # 每次间隔 10s，远超 2s 窗口
        if ev and ev.get("flapping"):
            seen_flap = True
    check(not seen_flap, "窗口 2s、采样间隔 10s 时不会误判抖动（时间窗口生效）")

    # 7) 从快照取值 + up/down 映射
    snap = {
        "host_metrics": {"cpu_percent": 91.0},
        "app_metrics": [{"status": "down", "latency_ms": 0.0}],
    }
    check(extract(snap, "host_metrics.cpu_percent") == 91.0, "extract 取字典路径")
    check(extract(snap, "app_metrics[0].status") == 0.0, "extract 把 down 映射成 0.0")

    rs = RuleSet(default_rules())
    evs = rs.evaluate(snap, 1.0)
    check(any(e["rule"] == "app_down" and e["type"] == "pending" for e in evs),
          "RuleSet 端到端：app down 进入 pending（consecutive=2）")

    if failures:
        print("self-test 失败 %d 项" % len(failures))
        return 1
    print("self-test 通过 | 参数校验 2 + 行为断言 9 全部成立")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Day 182 · 02 阈值与抖动判定引擎")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), default="sustained")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if args.demo:
        rule = default_rules()[0]
        render_timeline(rule, [float(v) for v in SCENARIOS[args.scenario]])
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
