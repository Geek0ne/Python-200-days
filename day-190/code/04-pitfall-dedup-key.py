#!/usr/bin/env python3
"""
Day 190 · 04 — 翻车实验：去重键设计错了，比不去重更危险

同一个事件流，三种指纹设计，真实跑出三种结局：

  v1  指纹 = rule            → 太粗：所有端口变化是一件事，高危被低危按在地上
  v2  指纹 = rule + 标题(含次数) → 太细：每次抖动都是一个新问题，121 条全发
  v3  指纹 = rule + asset，且高危升级穿透冷却 → 12+5 条，零丢失

这个脚本不是示意，是把三套逻辑都跑一遍再数消息。

  python3 04-pitfall-dedup-key.py
  python3 04-pitfall-dedup-key.py --self-test
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass

SEV_RANK = {"info": 0, "warning": 1, "critical": 2}


@dataclass(frozen=True)
class Event:
    rule: str
    asset: str
    severity: str
    title: str


def build_stream() -> list[Event]:
    """12 个资产各抖动 10 次（120 条 info），最后来 5 条真高危。

    其中 10.0.0.9 正是刚抖过的资产——这就是 v1 会把高危一起吞掉的现场。
    """
    events: list[Event] = []
    for i in range(12):
        asset = f"10.0.0.{i + 1}"
        for n in range(1, 11):
            events.append(Event("port-changed", f"{asset}:8080", "info", f"第 {n} 次抖动"))
    for i in range(4):
        events.append(Event("high-risk-port", f"10.0.0.{i + 1}:3389", "critical", "RDP 暴露"))
    events.append(Event("high-risk-port", "10.0.0.9:3389", "critical", "RDP 暴露"))
    return events


def send_v1(events: list[Event], cooldown_s: float = 600.0) -> tuple[int, int]:
    """太粗：只看 rule。第一次 info 把 rule 的冷却打满，后面的 critical 全被挡。"""
    seen: dict[str, float] = {}
    sent = lost_critical = 0
    for idx, e in enumerate(events):
        now = float(idx)
        last = seen.get(e.rule)
        if last is not None and now - last < cooldown_s:
            if e.severity == "critical":
                lost_critical += 1
            continue
        seen[e.rule] = now
        sent += 1
    return sent, lost_critical


def send_v2(events: list[Event], cooldown_s: float = 600.0) -> tuple[int, int]:
    """太细：标题里带"第 N 次"，同一次故障每次都是新指纹，冷却完全失效。"""
    seen: dict[str, float] = {}
    sent = lost_critical = 0
    for idx, e in enumerate(events):
        now = float(idx)
        # 真实写法往往是"规则 + 资产 + 标题"，标题里还带计数 → 每次都独一无二
        fp = f"{e.rule}|{e.asset}|{e.title}"
        last = seen.get(fp)
        if last is not None and now - last < cooldown_s:
            if e.severity == "critical":
                lost_critical += 1
            continue
        seen[fp] = now
        sent += 1
    return sent, lost_critical


def send_v3(events: list[Event], cooldown_s: float = 600.0) -> tuple[int, int]:
    """正确：按 (rule, asset) 聚合，严重级升高立即放行，critical 不走冷却。"""
    state: dict[str, tuple[float, str]] = {}
    sent = lost_critical = 0
    for idx, e in enumerate(events):
        now = float(idx)
        fp = f"{e.rule}|{e.asset}"
        prev = state.get(fp)
        if prev is None:
            state[fp] = (now, e.severity)
            sent += 1
            continue
        last, last_sev = prev
        escalated = SEV_RANK[e.severity] > SEV_RANK[last_sev]
        if e.severity == "critical" or escalated or now - last >= cooldown_s:
            state[fp] = (now, e.severity)
            sent += 1
        elif e.severity == "critical":
            lost_critical += 1
    return sent, lost_critical


def main() -> int:
    events = build_stream()
    total_critical = sum(1 for e in events if e.severity == "critical")
    print(f"事件流: {len(events)} 条，其中 critical {total_critical} 条")
    print(f"分布: {dict(Counter(e.severity for e in events))}\n")

    results = []
    for name, fn, desc in (
        ("v1 rule", send_v1, "指纹=规则，冷却 600s"),
        ("v2 rule+asset+title", send_v2, "指纹=规则+资产+标题(含次数)"),
        ("v3 rule+asset", send_v3, "指纹=规则+资产，高危放行"),
    ):
        sent, lost = fn(events)
        results.append((name, sent, lost, desc))

    print(f"{'方案':<16}{'消息数':>8}{'丢失 critical':>15}  说明")
    print("-" * 78)
    for name, sent, lost, desc in results:
        print(f"{name:<16}{sent:>8}{lost:>15}  {desc}")
    print("-" * 78)

    v1, v2, v3 = results
    print(f"\nv1 的问题：消息少，但把 {v1[2]} 条高危一起吞了——比不降噪更危险。")
    print(f"v2 的问题：一条没丢，但发了 {v2[1]} 条消息，等于把收件人训练成盲点。")
    print(f"v3 的结果：{v3[1]} 条消息（12 个资产各 1 条 + 5 条高危），丢失 {v3[2]}。")
    return 0


def self_test() -> int:
    events = build_stream()
    v1 = send_v1(events)
    v2 = send_v2(events)
    v3 = send_v3(events)
    checks = [
        ("v1 确实会吞高危", v1[1] >= 3, f"lost={v1[1]}"),
        ("v2 消息爆炸", v2[0] > 100, f"messages={v2[0]}"),
        ("v3 零丢失", v3[1] == 0, f"lost={v3[1]}"),
        ("v3 消息量可控", v3[0] <= 20, f"messages={v3[0]}"),
        ("v3 覆盖全部高危", v3[0] >= 5, f"messages={v3[0]}"),
    ]
    ok = all(c[1] for c in checks)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    print(f"\n{'全部通过' if ok else '存在失败项'}（{len(checks)} 项）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
