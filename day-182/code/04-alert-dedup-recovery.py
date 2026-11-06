#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 182 - 自动化运维平台（一）：服务器监控 + 告警
04 - 告警去重与恢复通知：指纹（fingerprint）+ 状态表

要点：
- 同一个故障在 5 分钟里会被采到 60 次。60 条告警 vs 1 条告警，区别就是值班的人
  还愿不愿意看手机。去重 = 给告警算一个稳定的「指纹」，同指纹只通知一次。
- 指纹必须由**稳定字段**构成：告警名 + 严重级别 + 关键标签（instance/job/disk 挂载点…）。
  绝不能把 value / 时间戳 / status 算进去，否则同一个故障每次值一变就是新告警。
- 恢复通知要求「同一指纹」：resolved 告警必须和当初的 firing 算出同一个指纹，
  否则永远匹配不上——下面自检里专门把这个坑钉住。
- 长时间不恢复的故障要周期性再提醒（resend_interval），不是彻底静音。

用法：
    python3 04-alert-dedup-recovery.py --self-test
    python3 04-alert-dedup-recovery.py --demo
"""

import argparse
import hashlib
import json
import sys

# 这些字段是「易变」的：绝不参与指纹计算，否则去重直接失效
VOLATILE_KEYS = ("value", "flapping", "ts", "summary", "status", "breach_run")


def fingerprint(alert, extra_keys=()):
    """
    稳定指纹 = sha256(告警名 + 严重级别 + labels [+ extra_keys]) 前 12 位十六进制。

    extra_keys 是给教学用的「反例开关」：传 ("status",) 就能复现
    「firing/resolved 指纹不同 -> 恢复通知永远发不出去」这个经典事故。
    """
    base = {"name": alert.get("name"), "severity": alert.get("severity")}
    base.update(alert.get("labels") or {})
    for key in extra_keys:
        base[key] = alert.get(key)
    raw = json.dumps(base, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


class AlertStore:
    """
    极简告警状态表：fp -> 记录。
    动作：
      notify    首次收到 firing -> 该通知
      suppress  同一指纹的重复告警 -> 不通知（但计数 +1）
      renotify  故障长时间不恢复，超过 resend_interval -> 再提醒一次
      recover   收到 resolved 且能匹配到活动告警 -> 发恢复通知，清状态
      drop      各种不该发的（无主恢复、被指纹搞错等）
    """

    def __init__(self, resend_interval=3600.0, extra_keys=(), verbose=False):
        self.resend_interval = float(resend_interval)
        self.extra_keys = tuple(extra_keys)
        self.verbose = verbose
        self.table = {}

    @property
    def open_count(self):
        return len(self.table)

    def process(self, alert, now):
        fp = fingerprint(alert, self.extra_keys)
        status = alert.get("status", "firing")
        rec = self.table.get(fp)

        if status == "firing":
            if rec is None:
                self.table[fp] = {"count": 1, "first": now, "last": now,
                                  "last_notify": now, "name": alert.get("name")}
                return {"fp": fp, "action": "notify", "count": 1, "reason": "首次越界",
                        "name": alert.get("name")}
            rec["count"] += 1
            rec["last"] = now
            if now - rec["last_notify"] >= self.resend_interval:
                rec["last_notify"] = now
                return {"fp": fp, "action": "renotify", "count": rec["count"],
                        "reason": "超过 %.0fs 未恢复，再提醒" % self.resend_interval,
                        "name": rec["name"]}
            return {"fp": fp, "action": "suppress", "count": rec["count"],
                    "reason": "重复告警，已去重", "name": rec["name"]}

        if rec is None:
            return {"fp": fp, "action": "drop", "count": 0,
                    "reason": "收到恢复通知但没有对应的活动告警", "name": alert.get("name")}
        del self.table[fp]
        return {"fp": fp, "action": "recover", "count": rec["count"],
                "reason": "恢复；活动时长 %.0fs" % (now - rec["first"]), "name": rec["name"]}


# --------------------------------------------------------------------------- #
# 造告警的小工具（让自检只关心「去重逻辑」，不关心上层）
# --------------------------------------------------------------------------- #
def make_alert(name="host_cpu_high", severity="critical", status="firing",
               instance="ace", value=95.0, metric="host_metrics.cpu_percent", ts=0.0):
    return {
        "name": name,
        "status": status,
        "severity": severity,
        "metric": metric,
        "value": value,
        "threshold": 90.0,
        "flapping": False,
        "summary": "[%s] %s 值=%s" % (severity, name, value),
        "labels": {"rule": name, "instance": instance},
        "ts": ts,
    }


# --------------------------------------------------------------------------- #
# 自检
# --------------------------------------------------------------------------- #
def self_test():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        print(("  PASS  " if cond else "  FAIL  ") + msg)

    print("== 04 去重/恢复自检 ==")

    # 1) 同一故障连来 3 次 -> 只通知 1 次
    store = AlertStore(resend_interval=3600.0)
    actions = [store.process(make_alert(value=v, ts=t), float(t))
               for t, v in enumerate([95.0, 96.0, 97.0])]
    kinds = [a["action"] for a in actions]
    check(kinds == ["notify", "suppress", "suppress"],
          "同一故障连来 3 次 -> 只通知 1 次（实测 %s）" % kinds)
    check(actions[-1]["count"] == 3, "被去重的告警仍然在计数（实测 count=%d）" % actions[-1]["count"])
    check(store.open_count == 1, "状态表里只有 1 条活动告警（实测 %d）" % store.open_count)

    # 2) value 变了不影响指纹（value 是易变字段）
    fa = fingerprint(make_alert(value=95.0))
    fb = fingerprint(make_alert(value=99.9))
    check(fa == fb, "value 不同但指纹相同（%s == %s）" % (fa, fb))

    # 3) instance 不同 -> 两条独立告警
    store = AlertStore()
    a1 = store.process(make_alert(instance="ace"), 0.0)
    a2 = store.process(make_alert(instance="node-b"), 0.0)
    check(a1["action"] == "notify" and a2["action"] == "notify",
          "不同 instance 各通知一次（实测 %s / %s）" % (a1["action"], a2["action"]))
    check(a1["fp"] != a2["fp"], "不同 instance 指纹不同（%s != %s）" % (a1["fp"], a2["fp"]))
    check(store.open_count == 2, "两条活动告警并存（实测 %d）" % store.open_count)

    # 4) 恢复通知：只发一次，且带活动时长
    store = AlertStore(resend_interval=100.0)
    store.process(make_alert(), 10.0)
    store.process(make_alert(value=98.0, ts=20.0), 20.0)
    rec = store.process(make_alert(status="resolved", value=40.0, ts=70.0), 70.0)
    check(rec["action"] == "recover", "resolved 触发恢复通知（实测 %s）" % rec["action"])
    check(rec["count"] == 2, "恢复通知带上被去重的次数（实测 count=%d）" % rec["count"])
    check("60s" in rec["reason"], "恢复通知带活动时长（实测 %s）" % rec["reason"])
    again = store.process(make_alert(status="resolved", value=40.0, ts=75.0), 75.0)
    check(again["action"] == "drop", "重复的恢复通知被丢弃（实测 %s）" % again["action"])
    check(store.open_count == 0, "恢复后状态表清空（实测 %d）" % store.open_count)

    # 5) 恢复后又故障 -> 重新通知（不是被历史去重掉）
    store = AlertStore()
    store.process(make_alert(), 0.0)
    store.process(make_alert(status="resolved", value=40.0), 10.0)
    re = store.process(make_alert(value=95.0), 20.0)
    check(re["action"] == "notify", "恢复后再次故障 -> 重新通知（实测 %s）" % re["action"])

    # 6) resend_interval：长时间不恢复要再提醒
    store = AlertStore(resend_interval=300.0)
    k1 = store.process(make_alert(), 0.0)["action"]
    k2 = store.process(make_alert(value=96.0), 100.0)["action"]
    k3 = store.process(make_alert(value=97.0), 400.0)["action"]
    check([k1, k2, k3] == ["notify", "suppress", "renotify"],
          "未恢复超过 resend_interval 再提醒一次（实测 %s）" % [k1, k2, k3])

    # 7) 反面：把 status 算进指纹 -> 恢复通知永远匹配不上（经典事故）
    store = AlertStore(extra_keys=("status",))
    fire = store.process(make_alert(), 0.0)
    resolved = store.process(make_alert(status="resolved", value=40.0), 60.0)
    check(resolved["action"] == "drop",
          "把 status 放进指纹后：恢复通知变成 drop（实测 %s）——这就是那个坑" % resolved["action"])
    check(fire["fp"] != resolved["fp"], "两种状态的指纹不同（%s != %s）" % (fire["fp"], resolved["fp"]))

    if failures:
        print("self-test 失败 %d 项" % len(failures))
        return 1
    print("self-test 通过 | 去重 3 + 恢复 5 + 再提醒/指纹陷阱 2 全部成立")
    return 0


# --------------------------------------------------------------------------- #
# 演示
# --------------------------------------------------------------------------- #
def demo():
    store = AlertStore(resend_interval=300.0)
    script = [
        (0.0, make_alert(value=95.0, ts=0.0)),
        (10.0, make_alert(value=96.0, ts=10.0)),
        (20.0, make_alert(value=97.0, ts=20.0)),
        (30.0, make_alert(instance="node-b", value=91.0, ts=30.0)),
        (330.0, make_alert(value=98.0, ts=330.0)),
        (400.0, make_alert(status="resolved", value=40.0, ts=400.0)),
        (410.0, make_alert(status="resolved", value=41.0, ts=410.0)),
    ]
    print("t(s)   告警                       动作        指纹       说明")
    for now, alert in script:
        rep = store.process(alert, now)
        print("%-6.0f %-26s %-11s %-10s %s"
              % (now, "%s/%s/%s" % (alert["name"], alert["status"], alert["labels"]["instance"]),
                 rep["action"], rep["fp"], rep["reason"]))
    print("演练结束：活动告警 %d 条" % store.open_count)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Day 182 · 04 告警去重与恢复通知")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.demo:
        return demo()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
