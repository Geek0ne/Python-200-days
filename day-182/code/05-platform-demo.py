#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 182 - 自动化运维平台（一）：服务器监控 + 告警
05 - 平台串联：采集(01) -> 阈值(02) -> 去重(04) -> 路由(03) 一条链路跑通

要点：
- 四个脚本不是四份练习，是一条流水线的四段：
      collect -> evaluate -> dedup -> route
- 本脚本用 importlib 把 01~04 当模块加载（文件名带中划线/数字，不能直接 import），
  证明「平台」真的是把这些件拼起来的，而不是又抄了一遍。
- --self-test 用「假时钟 + 假快照」把 32 个采样点毫秒级跑完，断言的是
  「32 个样本 -> 几条通知」，也就是告警系统真正的价值：降噪比例。
- --once / --serve 用真机数据跑同一条链路。

用法：
    python3 05-platform-demo.py --self-test
    python3 05-platform-demo.py --once
    python3 05-platform-demo.py --once --probe http://127.0.0.1:8000/ --probe http://127.0.0.1:9999/
    python3 05-platform-demo.py --serve --count 3 --interval 2 --probe http://127.0.0.1:8000/
"""

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))

MODULE_FILES = {
    "collect": "01-collect-metrics.py",
    "threshold": "02-threshold-engine.py",
    "routing": "03-alert-routing.py",
    "dedup": "04-alert-dedup-recovery.py",
}


def load_modules():
    """把同目录的 01~04 当模块加载。文件名不是合法标识符，所以走 spec_from_file_location。"""
    mods = {}
    for key, filename in MODULE_FILES.items():
        path = os.path.join(HERE, filename)
        if not os.path.exists(path):
            raise RuntimeError("缺少同目录模块：%s" % path)
        spec = importlib.util.spec_from_file_location("day182_" + key, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        mods[key] = module
    return mods


# --------------------------------------------------------------------------- #
# 流水线：把四段拼起来
# --------------------------------------------------------------------------- #
class Pipeline:
    """collect -> evaluate -> dedup -> route，每一步都可以被假数据驱动。"""

    def __init__(self, mods, rules, webhook_url, file_path, resend_interval=300.0,
                 attempts=2, dry_run=False, verbose=True):
        self.mods = mods
        self.rules = mods["threshold"].RuleSet(rules)
        self.store = mods["dedup"].AlertStore(resend_interval=resend_interval)
        channels = mods["routing"].make_channels(webhook_url, file_path, dry_run=dry_run)
        self.router = mods["routing"].Router(channels, attempts=attempts, verbose=verbose)
        self.verbose = verbose
        self.stats = {"samples": 0, "events": 0, "notify": 0, "renotify": 0,
                      "suppress": 0, "recover": 0, "drop": 0, "filtered": 0,
                      "delivered": 0, "by_channel": {}, "routes": {}}

    def step(self, snap, now, label=""):
        """喂一个快照，返回本步产生并投递出去的告警报告列表。"""
        self.stats["samples"] += 1
        out = []
        for event in self.rules.evaluate(snap, now):
            self.stats["events"] += 1
            if event["type"] not in ("firing", "resolved"):
                # pending / dropped 是「还没到该喊人的程度」，不进告警通道
                self.stats["filtered"] += 1
                if self.verbose:
                    print("      %-8s %-10s %s" % (event["type"], "-", event["rule"]))
                continue
            alert = self.mods["routing"].to_alert(event)
            decision = self.store.process(alert, now)
            action = decision["action"]
            self.stats[action] = self.stats.get(action, 0) + 1
            if action not in ("notify", "renotify", "recover"):
                if self.verbose and action in ("renotify", "drop"):
                    print("      %-7s %-10s %s" % (action, decision["fp"], decision["reason"]))
                continue
            tag = "恢复" if action == "recover" else "告警"
            report = self.router.deliver(alert)
            self.stats["delivered"] += 1 if report["delivered_by"] else 0
            self.stats["by_channel"][report["delivered_by"] or "FAILED"] =                 self.stats["by_channel"].get(report["delivered_by"] or "FAILED", 0) + 1
            self.stats["routes"][report["route"]] = self.stats["routes"].get(report["route"], 0) + 1
            if self.verbose:
                print("   %-4s %-8s %s | 路由=%-13s %s->%s"
                      % ("t=%.0f" % now, tag, alert["summary"], report["route"],
                         "+".join(report["chain"]), report["delivered_by"] or "全部失败"))
            out.append(report)
        return out


# --------------------------------------------------------------------------- #
# 场景（自检用，假时钟）
# --------------------------------------------------------------------------- #
def scenario_rules(mods):
    T = mods["threshold"]
    return [
        T.ThresholdRule("host_cpu_high", "host_metrics.cpu_percent", ">", 90, 80,
                        consecutive=3, flap_window=600.0, flap_limit=4, severity="critical"),
        T.ThresholdRule("app_latency_slow", "app_metrics[0].latency_ms", ">", 500, 300,
                        consecutive=1, flap_window=600.0, flap_limit=4, severity="warning"),
    ]


def scenario_timeline():
    """32 个采样点：正常 -> 连续越界 -> 持续越界 -> 恢复 -> 应用延迟抖动。"""
    tl = []
    for _ in range(10):
        tl.append((40.0, 50.0))            # 0-9   正常
    tl.append((92.0, 50.0))                # 10    pending 1
    tl.append((93.0, 50.0))                # 11    pending 2
    tl.append((94.0, 50.0))                # 12    firing (critical)
    for _ in range(7):
        tl.append((95.0, 50.0))            # 13-19 持续越界 -> 去重
    tl.append((70.0, 50.0))                # 20    恢复
    for i in range(11):
        tl.append((40.0, 900.0 if i % 2 == 0 else 100.0))   # 21-31 延迟抖动
    return tl


def fake_snapshot(cpu, latency):
    return {
        "ts": 0.0,
        "host": "fake-node",
        "host_metrics": {"backend": "fake", "cpu_percent": cpu, "mem_percent": 50.0,
                         "disk_percent": 40.0, "load1": 1.0, "load5": 1.0, "load15": 1.0,
                         "cpu_count": 4, "uptime_seconds": 100},
        "app_metrics": [{"target": "http://fake-app/", "status": "up", "http_code": 200,
                         "latency_ms": latency, "error": None}],
    }


def run_scenario(mods, webhook_url, file_path, verbose=False):
    pipe = Pipeline(mods, scenario_rules(mods), webhook_url, file_path,
                    resend_interval=300.0, attempts=1, dry_run=False, verbose=verbose)
    for tick, (cpu, latency) in enumerate(scenario_timeline()):
        pipe.step(fake_snapshot(cpu, latency), float(tick))
    return pipe.stats


# --------------------------------------------------------------------------- #
# 自检用的 webhook 桩
# --------------------------------------------------------------------------- #
class _HookHandler(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            _HookHandler.received.append(json.loads(self.rfile.read(length).decode("utf-8")))
        except ValueError:
            _HookHandler.received.append({"_raw": True})
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def self_test():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        print(("  PASS  " if cond else "  FAIL  ") + msg)

    print("== 05 平台串联自检 ==")

    mods = load_modules()
    check(hasattr(mods["collect"], "build_snapshot") and hasattr(mods["threshold"], "RuleSet")
          and hasattr(mods["routing"], "Router") and hasattr(mods["dedup"], "AlertStore"),
          "四个同目录模块都从真实文件加载成功")

    tmpdir = tempfile.mkdtemp(prefix="day182-platform-")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _HookHandler)
    hook_url = "http://127.0.0.1:%d/hook" % srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    try:
        # --- 场景 A：webhook 健在 ---
        _HookHandler.received.clear()
        f_a = os.path.join(tmpdir, "a.jsonl")
        stats = run_scenario(mods, hook_url, f_a, verbose=False)
        check(stats["samples"] == 32, "跑完整条时间线，共 32 个采样点（实测 %d）" % stats["samples"])
        check(stats["filtered"] == 2, "cpu 前两次越界只到 pending，被挡在告警通道之外（实测 %d）" % stats["filtered"])
        check(stats["notify"] == 7, "首次告警 7 条：cpu 1 + 延迟抖动 6（实测 %d）" % stats["notify"])
        check(stats["recover"] == 6, "恢复通知 6 条：cpu 1 + 延迟 5（实测 %d）" % stats["recover"])
        check(stats["suppress"] == 0 and stats["renotify"] == 0,
              "阈值引擎只在状态变化时吐事件，这一轮没有重复告警要去重（实测 suppress=%d renotify=%d）"
              % (stats["suppress"], stats["renotify"]))
        check(stats["routes"].get("flap-silenced", 0) == 8,
              "抖动判定生效后 8 条通知改走静默路由（实测 routes=%s）" % stats["routes"])
        check(stats["by_channel"].get("webhook", 0) == 2,
              "critical 的 1 告警 + 1 恢复走 webhook（实测 %s）" % stats["by_channel"])
        check(len(_HookHandler.received) == 2, "收数桩实测收到 2 条 payload（故障 + 恢复）")
        names = sorted(a.get("name") for a in _HookHandler.received)
        check(names == ["host_cpu_high", "host_cpu_high"], "payload 名字是 host_cpu_high（%s）" % names)
        statuses = sorted(a.get("status") for a in _HookHandler.received)
        check(statuses == ["firing", "resolved"], "payload 一条 firing 一条 resolved（%s）" % statuses)
        # 降噪比：通知条数 vs 采样条数
        notified = stats["notify"] + stats["recover"] + stats["renotify"]
        check(notified < stats["samples"], "通知数（%d）远少于采样数（%d）——这就是降噪" % (notified, stats["samples"]))

        # --- 场景 B：webhook 挂了（端口没人听），critical 必须降级到 file ---
        dead = free_port()
        f_b = os.path.join(tmpdir, "b.jsonl")
        stats_b = run_scenario(mods, "http://127.0.0.1:%d/hook" % dead, f_b, verbose=False)
        check(stats_b["by_channel"].get("file", 0) >= 4,
              "webhook 全挂时，所有通知降级到 file（实测 %s）" % stats_b["by_channel"])
        check(stats_b["by_channel"].get("webhook", 0) == 0, "降级场景下 webhook 一次也没成功")
        check(os.path.exists(f_b) and os.path.getsize(f_b) > 0,
              "降级通道的落盘文件非空（%d 字节）" % (os.path.getsize(f_b) if os.path.exists(f_b) else 0))
        first = json.loads(open(f_b, encoding="utf-8").readline())
        check(first["name"] == "host_cpu_high" and first["status"] == "firing",
              "降级落盘的第一条是 cpu 告警（实测 %s/%s）" % (first["name"], first["status"]))

        # --- 场景 C：--dry-run 不落任何盘 ---
        f_c = os.path.join(tmpdir, "c.jsonl")
        pipe = Pipeline(mods, scenario_rules(mods), "http://127.0.0.1:1/hook", f_c,
                        resend_interval=300.0, attempts=1, dry_run=True, verbose=False)
        for tick, (cpu, latency) in enumerate(scenario_timeline()):
            pipe.step(fake_snapshot(cpu, latency), float(tick))
        check(not os.path.exists(f_c), "dry-run 模式全程没写盘")
        check(pipe.stats["delivered"] == pipe.stats["notify"] + pipe.stats["recover"] + pipe.stats["renotify"],
              "dry-run 也如实汇报「本应投递」的条数（%d）" % pipe.stats["delivered"])

        # --- 场景 D：上游是「无状态告警源」（每轮都发同一条），去重才是主角 ---
        store = mods["dedup"].AlertStore(resend_interval=1000.0)
        stateless = mods["routing"].to_alert({
            "rule": "host_cpu_high", "type": "firing", "severity": "critical",
            "metric": "host_metrics.cpu_percent", "value": 95.0, "threshold": 90,
            "flapping": False, "ts": 0.0})
        kinds = [store.process(stateless, float(t))["action"] for t in range(10)]
        check(kinds[0] == "notify" and kinds.count("suppress") == 9,
              "无状态源连发 10 条同指纹告警 -> 压成 1 条通知（实测 %s）" % kinds)
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmpdir, ignore_errors=True)

    if failures:
        print("self-test 失败 %d 项" % len(failures))
        return 1
    print("self-test 通过 | 场景 A/B/C/D 全部断言成立（采样 32 -> 通知 13，抖动静默 8，去重 10->1）")
    return 0


# --------------------------------------------------------------------------- #
# 真机模式
# --------------------------------------------------------------------------- #
def real_run(probes, count, interval, webhook_url, file_path, dry_run, backend="auto"):
    mods = load_modules()
    pipe = Pipeline(mods, mods["threshold"].default_rules(), webhook_url, file_path,
                    resend_interval=300.0, attempts=2, dry_run=dry_run, verbose=True)
    print("真机模式：采集 %d 次，间隔 %.1fs，probe=%s，dry-run=%s"
          % (count, interval, probes or "（无）", dry_run))
    for idx in range(count):
        if idx:
            time.sleep(interval)
        snap = mods["collect"].build_snapshot(probes, backend)
        print("  [%s] cpu=%.1f%% mem=%.1f%% disk=%.1f%% probe=%s"
              % (snap["ts"], snap["host_metrics"]["cpu_percent"], snap["host_metrics"]["mem_percent"],
                 snap["host_metrics"]["disk_percent"],
                 [(a["target"], a["status"]) for a in snap["app_metrics"]] or "-"))
        pipe.step(snap, time.time())
    print("汇总：样本 %d | 事件 %d | 通知 %d | 去重 %d | 恢复 %d | 投递 %s"
          % (pipe.stats["samples"], pipe.stats["events"], pipe.stats["notify"] + pipe.stats["renotify"],
             pipe.stats["suppress"], pipe.stats["recover"], pipe.stats["by_channel"] or "{}"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Day 182 · 05 平台串联（采集->阈值->去重->路由）")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--probe", action="append", default=[])
    ap.add_argument("--backend", choices=["auto", "psutil", "proc"], default="auto")
    ap.add_argument("--dry-run", action="store_true", default=False)
    ap.add_argument("--live", action="store_true", help="真的发 webhook / 写文件（默认 dry-run）")
    ap.add_argument("--webhook", default="http://127.0.0.1:9999/hook")
    ap.add_argument("--file", default=os.path.join(tempfile.gettempdir(), "day182", "platform.jsonl"))
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.once or args.serve:
        count = args.count if args.serve else 1
        return real_run(args.probe, count, args.interval, args.webhook, args.file,
                        dry_run=not args.live, backend=args.backend)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
