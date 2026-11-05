#!/usr/bin/env python3
"""
Day 190 · 05 — 端到端验收：从扫描差异到告警送达，一次跑通并自证

串起三块：快照差异（00） → 幂等任务队列（02） → 告警漏斗（03） → 真实 HTTP 接收端。
验收不靠肉眼，靠断言 + 退出码；CI 里失败就是失败。

  python3 05-e2e-acceptance.py --self-test   # 离线
  python3 05-e2e-acceptance.py --e2e         # 本地起接收端，真发 HTTP
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # 必须先注册到 sys.modules：dataclasses 会反查 cls.__module__ 对应的模块对象，
    # 不注册就抛 AttributeError: 'NoneType' object has no attribute '__dict__'
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fixture = load("d190_fixture", "00-fixture.py")
jobs = load("d190_jobs", "02-retry-idempotency.py")
alerts = load("d190_alerts", "03-alert-dedup.py")


def run_pipeline(sender, db_path: str, diff: dict, workers: int = 4) -> dict:
    """把差异变成任务，4 个 worker 并发处理，全部汇入告警漏斗。"""
    conn = jobs.connect(db_path)
    jobs.init_db(conn)

    day = "2026-10-20"
    entries = [("port-appeared", a, "warning" if a["severity"] == "warning" else "critical")
               for a in diff["appeared"]]
    entries += [("port-missing", a, "info") for a in diff["missing"]]

    # 故意入队两遍：模拟 cron 重叠触发
    for _ in range(2):
        for rule, asset, sev in entries:
            key = f"{rule}:{day}:{asset['ip']}:{asset['port']}"
            jobs.enqueue(conn, "alert", key, {"rule": rule, "asset": asset, "severity": sev}, now=time.time())

    pipe = alerts.AlertPipeline(sender, group_window_s=0.05, batch_size=20,
                                bucket_capacity=20, refill_per_s=100.0)
    lock = threading.Lock()

    def worker(wid: int) -> None:
        c = jobs.connect(db_path)
        while True:
            def task(job: dict) -> None:
                p = job["payload"]
                a = p["asset"]
                alert = alerts.Alert(p["rule"], f"{a['ip']}:{a['port']}", p["severity"],
                                     f"{a['service']} {p['rule']}", detail="由 Day 190 流水线生成")
                with lock:
                    pipe.submit(alert)
            out = jobs.run_worker(c, f"w{wid}", time.time(), 30, task)
            if out is None:
                break
        c.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    pipe.close()

    row = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    eff = conn.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
    dup_effects = conn.execute(
        "SELECT COUNT(*) FROM (SELECT idem_key FROM effects GROUP BY idem_key HAVING COUNT(*)>1)"
    ).fetchone()[0]
    conn.close()
    return {"jobs": row, "effects": eff, "duplicate_effects": dup_effects,
            "pipeline": pipe.stats, "queued_entries": len(entries)}


def main(e2e: bool) -> int:
    tmp = tempfile.mkdtemp(prefix="d190-e2e-")
    db_path = os.path.join(tmp, "jobs.db")
    payload = fixture.emit(os.path.join(tmp, "fixtures"))
    diff = payload["diff"]

    if e2e:
        rx = alerts._Receiver()
        rx.__enter__()
        sender = alerts.HttpSender(f"http://127.0.0.1:{rx.port}/hook")
        print(f"接收端: 127.0.0.1:{rx.port}")
    else:
        rx = None
        sender = alerts.MemorySender()

    result = run_pipeline(sender, db_path, diff)
    p = result["pipeline"]

    if e2e:
        received = rx.payloads
        rx.__exit__()
        delivered_critical = sum(m["counts"]["critical"] for m in received)
        delivered_total = sum(m["total"] for m in received)
        items = [i for m in received for i in m["items"]]
        dup_items = len(items) - len({(i["rule"], i["asset"]) for i in items})
    else:
        received = sender.messages
        delivered_critical = sum(m["counts"]["critical"] for m in received)
        delivered_total = sum(m["total"] for m in received)
        items = [i for m in received for i in m["items"]]
        dup_items = len(items) - len({(i["rule"], i["asset"]) for i in items})

    checks = [
        ("任务数等于差异数（重复入队被去重）", result["jobs"] == result["queued_entries"],
         f"jobs={result['jobs']} entries={result['queued_entries']}"),
        ("每个任务只产生一次副作用", result["effects"] == result["jobs"] and result["duplicate_effects"] == 0,
         f"effects={result['effects']} dup={result['duplicate_effects']}"),
        ("严重事件全部送达", delivered_critical >= 2, f"critical={delivered_critical}"),
        ("消息条数受控", len(received) <= 5, f"messages={len(received)}"),
        ("消息内无重复条目", dup_items == 0, f"dup_items={dup_items}"),
        ("送达总数与漏斗统计一致", delivered_total <= p.received, f"delivered={delivered_total} received={p.received}"),
    ]

    print("\n验收清单")
    print("-" * 70)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<28} {detail}")
    print("-" * 70)
    print(f"漏斗: 收到 {p.received} / 去重 {p.deduped} / 消息 {p.messages} / "
          f"服务端收到 {len(received)}")
    print(f"队列: jobs={result['jobs']} effects={result['effects']}")

    ok = all(c[1] for c in checks)
    report = {"ok": ok, "checks": [{"name": n, "pass": o, "detail": d} for n, o, d in checks],
              "pipeline": vars(p), "delivered": delivered_total}
    print("\n" + json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n总体: {'ACCEPTED' if ok else 'REJECTED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--e2e", action="store_true")
    a = ap.parse_args()
    sys.exit(main(a.e2e))
