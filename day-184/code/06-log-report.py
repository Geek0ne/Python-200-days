#!/usr/bin/env python3
"""
Day 184 · 示例 06 —— 日志平台的可视化：ASCII 看板 + 单文件 HTML 报告

为什么要有这个文件？
    「可视化」在运维平台里有两个受众：
        ① 值班的人：要一个刷新就能看的**看板**（本文件打印 ASCII 看板，
           不需要浏览器、不需要 HTTP，ssh 上去就能看）；
        ② 要交差的人：要一个能发出去的**报告文件**（本文件生成单文件 HTML，
           用内联 CSS + 内联柱状图，无 CDN、无 JS 依赖，邮件附件也能看）。

    两者吃的是同一份 SQL：按时间分桶的聚合。所以本文件把「查询」和「渲染」分开：
        query_timeseries() → 返回数据结构（可复用、可单测）
        render_ascii() / render_html() → 只负责把数据画出来

运行方式：
    # 先有库（02 号服务写的 /tmp/day184/logs.db）
    python3 06-log-report.py --db /tmp/day184/logs.db --bucket 60
    python3 06-log-report.py --db /tmp/day184/logs.db --html /tmp/day184/report.html
    python3 06-log-report.py --self-test      # 离线自证（临时库造数据→断言渲染结果）
"""

from __future__ import annotations

import argparse
import html
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BLOCKS = "▁▂▃▄▅▆▇█"


def query_summary(conn: sqlite3.Connection, window_seconds: int) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat(
        timespec="milliseconds"
    )
    by_level = conn.execute(
        "SELECT level, COUNT(*) FROM logs WHERE received_at >= ? GROUP BY level ORDER BY 2 DESC",
        (cutoff,),
    ).fetchall()
    top_msgs = conn.execute(
        "SELECT msg, COUNT(*) c FROM logs WHERE received_at >= ? GROUP BY msg ORDER BY c DESC LIMIT 5",
        (cutoff,),
    ).fetchall()
    total, first, last = conn.execute(
        "SELECT COUNT(*), MIN(received_at), MAX(received_at) FROM logs WHERE received_at >= ?",
        (cutoff,),
    ).fetchone()
    return {
        "window_seconds": window_seconds,
        "total": total or 0,
        "first": first,
        "last": last,
        "by_level": by_level,
        "top_msgs": top_msgs,
    }


def query_timeseries(conn: sqlite3.Connection, bucket_seconds: int, window_seconds: int) -> list:
    """把日志按 bucket_seconds 分桶计数。

    为什么在 SQL 里分桶而不是取全量到 Python 再算？
        日志表几百万行时，把行搬进 Python 再聚合会把内存吃光；
        分桶这件事数据库做（GROUP BY + 整数除法）比应用层快得多。
        received_at 是 ISO8601 字符串，SQLite 的 substr 能直接切出秒 —— 这就是
        「时间戳存字符串但保持可排序」这个设计的好处。
    """
    rows = conn.execute(
        """
        SELECT CAST(strftime('%s', substr(received_at, 1, 19)) AS INTEGER) / ? AS bucket,
               COUNT(*)
        FROM logs
        WHERE received_at >= ?
        GROUP BY bucket ORDER BY bucket
        """,
        (bucket_seconds, (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat(
            timespec="milliseconds")),
    ).fetchall()
    return [(int(b), c) for b, c in rows]


def sparkline(values: list[int]) -> str:
    if not values:
        return "(无数据)"
    lo, hi = min(values), max(values)
    if hi == lo:
        return BLOCKS[0] * len(values)
    return "".join(BLOCKS[min(len(BLOCKS) - 1, (v - lo) * (len(BLOCKS) - 1) // (hi - lo))]
            for v in values)


def render_ascii(summary: dict, series: list, bucket: int) -> str:
    lines = []
    lines.append("┌─ 日志看板 ─────────────────────────────────────────────")
    lines.append(f"│ 窗口        : 最近 {summary['window_seconds']}s")
    lines.append(f"│ 总条数      : {summary['total']}")
    lines.append(f"│ 首/末时间   : {summary['first']} → {summary['last']}")
    lines.append("├─ 按级别 ───────────────────────────────────────────────")
    if summary["by_level"]:
        widest = max(len(lv) for lv, _ in summary["by_level"])
        peak = max(c for _, c in summary["by_level"]) or 1
        for level, count in summary["by_level"]:
            bar = "█" * max(1, round(count / peak * 30))
            lines.append(f"│ {level:<{widest}}  {count:>7}  {bar}")
    else:
        lines.append("│ (空)")
    lines.append("├─ 时间序列 ─────────────────────────────────────────────")
    counts = [c for _, c in series]
    lines.append(f"│ 每 {bucket}s 一桶  {sparkline(counts)}  峰值={max(counts) if counts else 0}")
    lines.append("├─ TOP 消息 ─────────────────────────────────────────────")
    for msg, count in summary["top_msgs"]:
        lines.append(f"│ {count:>5}  {msg[:60]}")
    lines.append("└────────────────────────────────────────────────────────")
    return "\n".join(lines)


def render_html(summary: dict, series: list, bucket: int, title: str = "Day 184 日志报告") -> str:
    peak = max([c for _, c in series], default=1) or 1
    bars = "".join(
        f'<div class="bar" style="height:{max(2, round(c / peak * 120))}px" '
        f'title="{datetime.fromtimestamp(b * bucket, timezone.utc).isoformat()} ← {c} 条"></div>'
        for b, c in series
    )
    rows = "".join(
        f"<tr><td>{html.escape(str(level))}</td><td>{count}</td></tr>"
        for level, count in summary["by_level"]
    )
    msgs = "".join(
        f"<tr><td>{count}</td><td>{html.escape(str(msg))}</td></tr>"
        for msg, count in summary["top_msgs"]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
 body{{font-family:-apple-system,"Segoe UI",Roboto,sans-serif;margin:24px;color:#222}}
 h1{{font-size:20px}} .card{{border:1px solid #e3e3e3;border-radius:8px;padding:16px;margin:16px 0}}
 .chart{{display:flex;align-items:flex-end;gap:2px;height:130px}}
 .bar{{background:#4b8bbe;width:6px;border-radius:2px 2px 0 0}}
 table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #eee;padding:6px 10px;text-align:left}}
 .muted{{color:#888;font-size:12px}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<p class="muted">窗口 {summary['window_seconds']}s · 总条数 {summary['total']} ·
 {summary['first']} → {summary['last']} · 每桶 {bucket}s（桶高按峰值 {peak} 归一化）</p>
<div class="card"><h2>时间序列</h2><div class="chart">{bars}</div></div>
<div class="card"><h2>按级别</h2><table><tr><th>level</th><th>count</th></tr>{rows}</table></div>
<div class="card"><h2>TOP 消息</h2><table><tr><th>count</th><th>msg</th></tr>{msgs}</table></div>
<p class="muted">本报告由 code/06-log-report.py 生成，零第三方依赖、无 CDN、无 JS。</p>
</body></html>
"""


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="day184-report-") as tmp:
        db = str(Path(tmp) / "r.db")
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE logs(id INTEGER PRIMARY KEY, ts TEXT, received_at TEXT, "
            "level TEXT, service TEXT, msg TEXT, raw TEXT)"
        )
        now = datetime.now(timezone.utc)
        rows = []
        for i in range(6):
            rows.append((now.isoformat(timespec="milliseconds"), "INFO", f"ok-{i}"))
        for i in range(2):
            rows.append((now.isoformat(timespec="milliseconds"), "ERROR", "boom"))
        conn.executemany(
            "INSERT INTO logs(ts, received_at, level, service, msg, raw) VALUES(?,?,?,?,?,?)",
            [(r[0], r[0], r[1], "svc", r[2], "{}") for r in rows],
        )
        conn.commit()

        summary = query_summary(conn, 3600)
        assert summary["total"] == 8, summary
        assert dict(summary["by_level"]) == {"INFO": 6, "ERROR": 2}, summary["by_level"]

        series = query_timeseries(conn, 60, 3600)
        assert len(series) == 1 and series[0][1] == 8, series

        ascii_dash = render_ascii(summary, series, 60)
        assert "ERROR" in ascii_dash and "boom" in ascii_dash

        page = render_html(summary, series, 60)
        assert page.startswith("<!DOCTYPE html>") and "boom" in page
        assert "<script" not in page.lower(), "报告不该带 JS"
        print("✅ self-test 通过：聚合/分桶/sparkline/HTML 渲染都对，8 条数据（6 INFO + 2 ERROR）")
        conn.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="日志看板与报告生成")
    parser.add_argument("--db", default="/tmp/day184/logs.db")
    parser.add_argument("--window", type=int, default=3600)
    parser.add_argument("--bucket", type=int, default=60)
    parser.add_argument("--html", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if not Path(args.db).exists():
        print(f"❌ 数据库不存在：{args.db}（先跑 02 号服务收日志）", file=sys.stderr)
        return 2

    conn = sqlite3.connect(args.db)
    summary = query_summary(conn, args.window)
    series = query_timeseries(conn, args.bucket, args.window)
    print(render_ascii(summary, series, args.bucket))
    if args.html:
        Path(args.html).write_text(render_html(summary, series, args.bucket), encoding="utf-8")
        print(f"📄 HTML 报告已写入 {args.html}（{Path(args.html).stat().st_size} 字节）")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
