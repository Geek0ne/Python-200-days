#!/usr/bin/env python3
"""
Day 189 · 05 — 端到端流水线：扫描 JSON → 入库 → 变更 → 看板

这一课把前四天的零件串起来：
    scans/*.json  ──parse──▶  02 的 run_scan（UPSERT + 差集 + 事件）
                              │
                              ├──▶ SQLite（assets / events）
                              └──▶ 03 的看板（子进程，CLI 即接口）

为什么用子进程调 03，而不是 import？
  03 带 --self-test 和 CLI，本身就是一个可独立部署的工具；
  用命令行组合，任何语言都能替换其中一环，流水线不绑死 Python 内部结构。

用法：
    python3 00-fixture.py --out /tmp/day189-scans --days 5
    python3 05-ingest-pipeline.py --scan-dir /tmp/day189-scans \
        --db /tmp/day189-pipeline.db --out /tmp/day189-pipeline.html

    python3 05-ingest-pipeline.py --self-test
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_sibling(filename: str, modname: str):
    """按文件路径加载同级脚本（文件名带连字符，不能直接 import）。"""
    spec = importlib.util.spec_from_file_location(modname, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


diff = load_sibling("02-incremental-snapshot.py", "day189_diff")


def read_scan(path: Path) -> tuple[list[dict], str, str | None]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    observations = []
    for host in doc.get("hosts", []):
        for p in host.get("ports", []):
            observations.append({
                "ip": host["ip"],
                "port": int(p["port"]),
                "proto": p.get("proto", "tcp"),
                "service": p.get("service"),
                "banner": p.get("banner"),
            })
    return observations, doc.get("label") or path.stem, doc.get("scanned_at")


def run_pipeline(scan_dir: Path, db: Path, out_html: Path, grace: int = 2) -> dict:
    conn = diff.connect(db)
    report = []
    for path in sorted(scan_dir.glob("*.json")):
        obs, label, scanned_at = read_scan(path)
        events = diff.run_scan(conn, obs, label=label, seen_at=scanned_at, grace=grace)
        counts: dict[str, int] = {}
        for e in events:
            counts[e["event"]] = counts.get(e["event"], 0) + 1
        report.append({"file": path.name, "label": label, "observed": len(obs),
                       "events": counts})
    conn.close()

    subprocess.run(
        [sys.executable, str(HERE / "03-trend-dashboard.py"), "--db", str(db),
         "--out", str(out_html)],
        check=True,
    )
    return {"scans": report, "db": str(db), "dashboard": str(out_html)}


def demo(scan_dir: Path, db: Path, out_html: Path) -> None:
    if not scan_dir.exists():
        raise SystemExit(f"扫描目录不存在：{scan_dir}\n先跑 00-fixture.py 生成夹具")
    result = run_pipeline(scan_dir, db, out_html)
    print("\n入库结果：")
    for s in result["scans"]:
        ev = ", ".join(f"{k}={v}" for k, v in sorted(s["events"].items())) or "无变化"
        print(f"  {s['file']:<14} observed={s['observed']:<3} {ev}")
    print(f"\n数据库：{result['db']}")
    print(f"看板：  {result['dashboard']}")


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        scan_dir = root / "scans"
        scan_dir.mkdir()
        fixture = load_sibling("00-fixture.py", "day189_fixture")
        docs = fixture.scan_docs(5)
        for i, doc in enumerate(docs):
            (scan_dir / f"scan-{i+1}.json").write_text(
                json.dumps(doc, ensure_ascii=False), encoding="utf-8")

        db = root / "pipe.db"
        page = root / "dash.html"
        result = run_pipeline(scan_dir, db, page, grace=2)

        assert len(result["scans"]) == 5
        assert page.exists() and page.stat().st_size > 3000
        assert "开放端口趋势" in page.read_text(encoding="utf-8")

        # 第 4 天 6379 第一次消失 -> missing；第 5 天仍消失 -> gone
        conn = diff.connect(db)
        row = conn.execute("SELECT state, miss_count FROM assets WHERE port=6379").fetchone()
        assert row["state"] == "gone" and row["miss_count"] == 2, dict(row)
        # 22 端口 SSH 版本变化应记录 changed
        n_changed = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event='changed' AND port=22").fetchone()[0]
        assert n_changed >= 1, n_changed
        # 8080 新增一次
        n_appeared = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event='appeared' AND port=8080").fetchone()[0]
        assert n_appeared == 1, n_appeared
        conn.close()

        print("\n流水线自检：")
        for s in result["scans"]:
            print(f"  {s['file']} observed={s['observed']} events={s['events']}")
    print("✅ 05 self-test 通过：5 份扫描 → 入库 → 变更事件 → HTML 看板")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="扫描结果端到端流水线")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--scan-dir", default="out/day189-scans")
    ap.add_argument("--db", default="out/day189-pipeline.db")
    ap.add_argument("--out", default="out/day189-pipeline.html")
    ap.add_argument("--grace", type=int, default=2)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    db = Path(args.db)
    out = Path(args.out)
    db.parent.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    demo(Path(args.scan_dir), db, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
