#!/usr/bin/env python3
"""
Day 189 · 03 — 趋势统计与静态看板

输入：01/02 生成的库（scans / scan_assets / events / assets）
输出：
  1) 终端 ASCII 趋势（▁▂▃▄▅▆▇█）
  2) 单文件 HTML 看板（内联 CSS + SVG，零依赖、可直接扔到任意静态服务器）

口径必须固定，否则趋势会"说谎"：
  - 某天的开放端口数 = 当天**最后一次**扫描的观测数（不是当天所有扫描之和）
  - 新增资产 = first_seen 落在当天的资产数
  - 变更数 = 当天 events 表条数（appeared 另算，避免重复计数）

用法：
    python3 03-trend-dashboard.py --db /tmp/day189.db --out /tmp/day189.html
    python3 03-trend-dashboard.py --self-test
"""
from __future__ import annotations

import argparse
import html
import random
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    label TEXT
);
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    proto TEXT NOT NULL DEFAULT 'tcp',
    service TEXT,
    banner TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'active',
    miss_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ip, port, proto)
);
CREATE TABLE IF NOT EXISTS scan_assets (
    scan_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    seen_at TEXT NOT NULL,
    PRIMARY KEY (scan_id, asset_id)
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    seen_at TEXT NOT NULL,
    event TEXT NOT NULL,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    proto TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT
);
CREATE INDEX IF NOT EXISTS idx_scans_started ON scans(started_at);
CREATE INDEX IF NOT EXISTS idx_events_seen ON events(seen_at);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def collect_daily(conn: sqlite3.Connection) -> list[dict]:
    """按天聚合。只取每天最后一次扫描，避免"扫得越勤数字越大"的假趋势。"""
    days = conn.execute(
        """SELECT date(started_at) AS d, MAX(id) AS last_scan
             FROM scans GROUP BY date(started_at) ORDER BY d"""
    ).fetchall()
    rows = []
    for day in days:
        d, scan_id = day["d"], day["last_scan"]
        open_ports = conn.execute(
            "SELECT COUNT(*) FROM scan_assets WHERE scan_id=?", (scan_id,)
        ).fetchone()[0]
        new_assets = conn.execute(
            "SELECT COUNT(*) FROM assets WHERE date(first_seen)=?", (d,)
        ).fetchone()[0]
        ev = dict(conn.execute(
            """SELECT event, COUNT(*) AS n FROM events
                WHERE date(seen_at)=? GROUP BY event""", (d,)
        ).fetchall())
        rows.append({
            "date": d,
            "open_ports": open_ports,
            "new_assets": new_assets,
            "appeared": ev.get("appeared", 0),
            "gone": ev.get("gone", 0),
            "changed": ev.get("changed", 0),
            "missing": ev.get("missing", 0),
        })
    return rows


BLOCKS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[int]) -> str:
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return BLOCKS[3] * len(values)
    return "".join(BLOCKS[round((v - lo) / (hi - lo) * (len(BLOCKS) - 1))] for v in values)


def print_ascii(rows: list[dict]) -> None:
    if not rows:
        print("没有数据")
        return
    print(f"开放端口趋势  {rows[0]['date']} → {rows[-1]['date']}")
    print("  " + sparkline([r["open_ports"] for r in rows]))
    print(f"  min={min(r['open_ports'] for r in rows)}  "
          f"max={max(r['open_ports'] for r in rows)}  "
          f"latest={rows[-1]['open_ports']}")
    print()
    print(f"{'日期':<12}{'端口':>6}{'新增':>6}{'下线':>6}{'变更':>6}")
    for r in rows[-10:]:
        print(f"{r['date']:<12}{r['open_ports']:>6}{r['new_assets']:>6}"
              f"{r['gone']:>6}{r['changed']:>6}")


def _svg(rows: list[dict]) -> str:
    w, h, pad = 900, 260, 44
    if len(rows) < 2:
        return "<p>数据点不足，无法绘制趋势</p>"
    vals = [r["open_ports"] for r in rows]
    lo, hi = min(vals), max(vals)
    span = max(1, hi - lo)
    step = (w - 2 * pad) / (len(rows) - 1)

    def x(i: int) -> float:
        return pad + i * step

    def y(v: int) -> float:
        return h - pad - (v - lo) / span * (h - 2 * pad)

    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    area = f"{pad},{h - pad} " + points + f" {w - pad},{h - pad}"
    grid = []
    for g in range(5):
        gv = lo + span * g / 4
        gy = y(gv)
        grid.append(
            f'<line x1="{pad}" y1="{gy:.1f}" x2="{w - pad}" y2="{gy:.1f}" '
            f'stroke="#e5e7eb" stroke-width="1"/>'
            f'<text x="8" y="{gy + 4:.1f}" font-size="11" fill="#6b7280">{gv:.0f}</text>'
        )
    labels = (
        f'<text x="{pad}" y="{h - 14}" font-size="12" fill="#6b7280">{rows[0]["date"]}</text>'
        f'<text x="{w - pad}" y="{h - 14}" font-size="12" fill="#6b7280" text-anchor="end">'
        f'{rows[-1]["date"]}</text>'
    )
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="开放端口趋势">'
        + "".join(grid)
        + f'<polygon points="{area}" fill="#3b82f6" opacity="0.12"/>'
        + f'<polyline points="{points}" fill="none" stroke="#2563eb" stroke-width="2.5"/>'
        + labels + "</svg>"
    )


def render_html(rows: list[dict], conn: sqlite3.Connection, db_path: str) -> str:
    latest = rows[-1] if rows else {"open_ports": 0, "date": "-", "new_assets": 0}
    total_assets = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM assets WHERE state='active'").fetchone()[0]
    recent = conn.execute(
        """SELECT seen_at, event, ip, port, old_value, new_value
             FROM events ORDER BY id DESC LIMIT 15"""
    ).fetchall()

    cards = [
        ("当前资产", total_assets, "库中全部自然键"),
        ("活跃端口", active, "state = active"),
        ("最新快照端口", latest["open_ports"], latest["date"]),
        ("数据天数", len(rows), "覆盖的日历天"),
    ]
    card_html = "".join(
        f'<div class="card"><div class="k">{html.escape(k)}</div>'
        f'<div class="v">{v}</div><div class="s">{html.escape(s)}</div></div>'
        for k, v, s in cards
    )

    trs = "".join(
        f"<tr><td>{html.escape(r['seen_at'])}</td>"
        f"<td><span class='tag {html.escape(r['event'])}'>{html.escape(r['event'])}</span></td>"
        f"<td>{html.escape(r['ip'])}:{r['port']}</td>"
        f"<td>{html.escape(r['old_value'] or '-')} → {html.escape(r['new_value'] or '-')}</td></tr>"
        for r in recent
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>资产趋势看板 · Day 189</title>
<style>
  :root {{ --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --bg:#f9fafb; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: -apple-system, "Segoe UI", "PingFang SC", sans-serif;
         color:var(--ink); background:var(--bg); }}
  main {{ max-width: 1000px; margin: 0 auto; padding: 32px 20px 60px; }}
  h1 {{ font-size: 24px; margin: 0 0 4px; }}
  .meta {{ color: var(--muted); font-size: 13px; margin-bottom: 24px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:24px; }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:16px; }}
  .card .k {{ color:var(--muted); font-size:12px; }}
  .card .v {{ font-size:28px; font-weight:650; margin:4px 0; }}
  .card .s {{ color:var(--muted); font-size:11px; }}
  section {{ background:#fff; border:1px solid var(--line); border-radius:10px;
            padding:18px; margin-bottom:20px; }}
  h2 {{ font-size:15px; margin:0 0 12px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th, td {{ text-align:left; padding:7px 8px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--muted); font-weight:500; }}
  .tag {{ padding:1px 7px; border-radius:999px; font-size:11px; background:#eef2ff; color:#3730a3; }}
  .tag.gone {{ background:#fef2f2; color:#991b1b; }}
  .tag.changed {{ background:#fffbeb; color:#92400e; }}
  .tag.revived {{ background:#ecfdf5; color:#065f46; }}
  footer {{ color:var(--muted); font-size:11px; margin-top:24px; }}
</style>
</head>
<body>
<main>
  <h1>企业资产趋势看板</h1>
  <div class="meta">数据源：{html.escape(db_path)} · 生成于 {datetime.now(timezone.utc).isoformat(timespec="seconds")}</div>
  <div class="cards">{card_html}</div>
  <section><h2>开放端口趋势（每天最后一次快照）</h2>{_svg(rows)}</section>
  <section><h2>最近变更</h2>
    <table><thead><tr><th>时间</th><th>事件</th><th>资产</th><th>变化</th></tr></thead>
    <tbody>{trs or '<tr><td colspan="4">暂无事件</td></tr>'}</tbody></table>
  </section>
  <footer>纯静态单文件 · 无 JS 依赖 · 由 03-trend-dashboard.py 生成</footer>
</main>
</body>
</html>
"""


def seed_demo(conn: sqlite3.Connection, days: int = 30, seed: int = 42) -> None:
    """造 30 天真实形状的演示数据（固定随机种子，可复现）。"""
    rnd = random.Random(seed)
    start = datetime(2026, 9, 20, 2, 0, tzinfo=timezone.utc)
    services = [("ssh", 22), ("http", 80), ("https", 443), ("redis", 6379), ("mysql", 3306)]
    assets: dict[tuple[str, int], dict] = {}
    next_host = 5

    for d in range(days):
        at = (start + timedelta(days=d)).isoformat(timespec="seconds")
        cur = conn.execute("INSERT INTO scans(started_at, label) VALUES (?, ?)",
                           (at, f"day-{d+1}"))
        scan_id = int(cur.lastrowid)

        # 新暴露：每天 0~2 个
        for _ in range(rnd.choice([0, 0, 1, 1, 2])):
            ip = f"10.0.{next_host // 200}.{next_host % 200}"
            next_host += 1
            svc, port = rnd.choice(services)
            row = conn.execute(
                """INSERT INTO assets(ip, port, proto, service, banner, first_seen, last_seen, state)
                   VALUES (?, ?, 'tcp', ?, ?, ?, ?, 'active')""",
                (ip, port, svc, f"{svc}/demo", at, at),
            )
            assets[(ip, port)] = {"id": int(row.lastrowid), "ip": ip, "port": port,
                                  "service": svc}
            conn.execute(
                """INSERT INTO events(scan_id, seen_at, event, ip, port, proto, new_value)
                   VALUES (?, ?, 'appeared', ?, ?, 'tcp', ?)""",
                (scan_id, at, ip, port, svc),
            )

        # 下线：每天 0~1 个，至少保留 4 个
        if len(assets) > 4 and rnd.random() < 0.35:
            key = rnd.choice(list(assets))
            info = assets.pop(key)
            conn.execute("UPDATE assets SET state='gone' WHERE id=?", (info["id"],))
            conn.execute(
                """INSERT INTO events(scan_id, seen_at, event, ip, port, proto, old_value)
                   VALUES (?, ?, 'gone', ?, ?, 'tcp', ?)""",
                (scan_id, at, info["ip"], info["port"], info["service"]),
            )

        # 服务变化：低频
        if assets and rnd.random() < 0.2:
            info = rnd.choice(list(assets.values()))
            new = rnd.choice(["http", "https", "ssh"])
            if new != info["service"]:
                conn.execute("UPDATE assets SET service=? WHERE id=?", (new, info["id"]))
                conn.execute(
                    """INSERT INTO events(scan_id, seen_at, event, ip, port, proto,
                                          old_value, new_value)
                       VALUES (?, ?, 'changed', ?, ?, 'tcp', ?, ?)""",
                    (scan_id, at, info["ip"], info["port"], info["service"], new),
                )
                info["service"] = new

        # 当天快照：写入全部活跃资产
        for info in assets.values():
            conn.execute(
                "INSERT INTO scan_assets(scan_id, asset_id, seen_at) VALUES (?, ?, ?)",
                (scan_id, info["id"], at),
            )
            conn.execute("UPDATE assets SET last_seen=?, state='active', miss_count=0 WHERE id=?",
                         (at, info["id"]))
    conn.commit()


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "demo.db"
        out = Path(td) / "dashboard.html"
        conn = connect(db)
        seed_demo(conn, days=14, seed=7)
        rows = collect_daily(conn)
        assert len(rows) == 14, len(rows)
        assert all(r["open_ports"] > 0 for r in rows)
        assert sum(r["new_assets"] for r in rows) >= 5
        assert any(r["gone"] for r in rows)

        page = render_html(rows, conn, str(db))
        out.write_text(page, encoding="utf-8")
        assert "<svg" in page and "开放端口趋势" in page
        assert rows[-1]["date"] in page
        assert "appeared" in page
        size = out.stat().st_size
        assert size > 3000, size
        conn.close()
    print(f"✅ 03 self-test 通过：14 天趋势聚合 + SVG/HTML 渲染（{size} bytes）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="资产趋势看板")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--db", default=str(Path(tempfile.gettempdir()) / "day189-dashboard.db"))
    ap.add_argument("--out", default="out/day-189-dashboard.html")
    ap.add_argument("--seed-days", type=int, default=0,
                    help="库为空时生成 N 天演示数据（0 = 不生成）")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    conn = connect(args.db)
    if args.seed_days and conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0] == 0:
        seed_demo(conn, args.seed_days)

    rows = collect_daily(conn)
    print_ascii(rows)
    page = render_html(rows, conn, args.db)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"\n看板已写入 {out}（{out.stat().st_size} bytes）")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
