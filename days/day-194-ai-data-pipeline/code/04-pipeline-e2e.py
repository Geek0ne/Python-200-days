#!/usr/bin/env python3
"""Day 194 · 端到端数据管道：清洗 → 抽取 → 去重 → 质量门禁 → 入库。

为什么要有"管道"而不是一堆脚本
----------------------------
单脚本的问题是**错误无法定位**：一条脏数据进来，可能是清洗没洗干净、
抽取正则写错、还是入库类型转换失败。管道把每一步的输入输出都量化，
出错时能直接看到"哪一步丢了多少、因为什么丢的"。

本脚本的五个阶段：
  S1 采集（合成 3000 个脏 HTML，含 6 类缺陷）
  S2 清洗（去脚本/标签/实体/零宽字符）
  S3 抽取（title / price / published_at / text）
  S4 去重（SimHash 粗筛 + Jaccard 精排）
  S5 质检 + 入库（SQLite，脏数据进 quarantine 表，不静默丢）

运行：
    python3 04-pipeline-e2e.py                 # 全量跑，写 /tmp/day194.db
    python3 04-pipeline-e2e.py --dry-run       # 不落库，只出统计
    python3 04-pipeline-e2e.py --rows 500
    python3 04-pipeline-e2e.py --self-test
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pipeline_lib import (
    SENTENCES,
    SimHashIndex,
    canon_url,
    check_record,
    clean_html,
    hash_to_signed,
    simhash,
    tokenize,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
    url_key      TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    price        REAL NOT NULL,
    published_at TEXT NOT NULL,
    content      TEXT NOT NULL,
    simhash      INTEGER NOT NULL,
    dup_of       TEXT,
    ingested_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quarantine (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url_key      TEXT,
    code         TEXT NOT NULL,
    field        TEXT NOT NULL,
    detail       TEXT,
    raw_snippet  TEXT
);
CREATE INDEX IF NOT EXISTS idx_pages_hash ON pages(simhash);
"""

GOOD_TEXT = [
    "国产新能源汽车在欧洲市场的接受度在两年内明显上升，价格与智能化是主要卖点。",
    "分布式数据库选型要先明确是 OLTP 还是 OLAP，两者的存储引擎完全不同。",
    "面团含水量决定口感，烤箱温差需要先用温度计校准再谈配方。",
]


def make_pages(n: int = 3000, seed: int = 194) -> list[dict]:
    """造脏数据：6 类缺陷按固定比例注入，保证每次跑出来的统计一致。"""
    rng = random.Random(seed)
    pages: list[dict] = []
    seen_bodies: list[str] = []
    kinds = ["clean"] * 62 + ["no_title"] * 5 + ["bad_price"] * 6 + \
            ["bad_date"] * 5 + ["mojibake"] * 4 + ["short_text"] * 5 + \
            ["dup"] * 8 + ["empty"] * 5
    for i in range(n):
        kind = rng.choice(kinds)
        pid = i
        title = f"商品 {pid:05d} 的详细说明"
        price = f"{rng.randint(9, 9999)}.{rng.randint(0, 99):02d}"
        date = f"2026-{rng.randint(1, 10):02d}-{rng.randint(1, 28):02d}"

        # 正文必须"每篇都不同"，否则去重阶段会把正常页面全判成重复 ——
        # 第一版这里用了同一个句子池，实测 94.9% 被误判为重复（见 README 翻车实验 3）。
        uniq = " ".join(f"SKU{pid}X{rng.randrange(10 ** 9):09d}" for _ in range(6))
        body = "".join(rng.sample(SENTENCES, 5)) + "规格明细：" + uniq + "。"

        if kind == "no_title":
            title = ""
        elif kind == "bad_price":
            price = rng.choice(["-1", "0", "面议", "99999999"])
        elif kind == "bad_date":
            date = rng.choice(["2026/10/24", "10-24-2026", "", "2026-13-40"])
        elif kind == "mojibake":
            title = "ä¸­æ–‡æ ‡é¢˜ " + title  # 典型 GBK 被当 UTF-8 解码的结果
        elif kind == "short_text":
            body = "太短"
        elif kind == "empty":
            body = ""
        elif kind == "dup" and seen_bodies:
            body = rng.choice(seen_bodies)  # 真正的转载：正文一字不差，URL 不同
        if kind != "short_text" and kind != "empty":
            seen_bodies.append(body)

        html = f"""<!doctype html><html><head><title>{title}</title>
<script>var _hmt=[];function track(){{return 'not content'}}</script>
<style>.x{{color:#fff}}</style></head>
<body><h1>{title}</h1>
<div class="meta"><span class="price">¥{price}</span>
<time datetime="{date}">发布日期</time></div>
<article>{body}</article>
<p>版权所有 © 2026 示例站点 扫码关注</p>
</body></html>"""
        pages.append({
            "url": f"https://shop.example.com/product/{pid}?utm_source=feed&sku=c{pid % 7}",
            "html": html,
            "kind": kind,
        })
    return pages


# ────────────────────────────── 各阶段 ──────────────────────────────

_RE_TITLE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
_RE_ARTICLE = re.compile(r"<article[^>]*>(.*?)</article>", re.S | re.I)
_RE_PRICE = re.compile(r'<span class="price">\s*¥?\s*([^<]*)</span>', re.I)
_RE_DATE = re.compile(r'<time[^>]*datetime="([^"]*)"', re.I)


def extract_body(html: str) -> str:
    """只取正文容器再清洗。

    这是本课最贵的一条经验：拿"整页清洗后的文本"去做去重，
    会把导航、价格、版权、模板句全算进相似度，正常页面互相撞车。
    必须先把正文抽出来，再去重。
    """
    m = _RE_ARTICLE.search(html)
    return clean_html(m.group(1)) if m else clean_html(html)


def extract(html: str) -> dict:
    """正则抽取。生产环境该用 lxml/cssselect，这里为了零依赖保持简单。"""
    def grab(rx, default=""):
        m = rx.search(html)
        return clean_html(m.group(1)) if m else default

    return {
        "title": grab(_RE_TITLE),
        "price": grab(_RE_PRICE, ""),
        "published_at": grab(_RE_DATE, ""),
    }


@dataclass
class Stats:
    stage_seconds: dict[str, float] = field(default_factory=dict)
    counts: Counter = field(default_factory=Counter)
    rejects: Counter = field(default_factory=Counter)
    dup_pairs: int = 0

    def as_dict(self) -> dict:
        return {
            "stages_ms": {k: round(v * 1000, 1) for k, v in self.stage_seconds.items()},
            "counts": dict(self.counts),
            "rejects": dict(self.rejects),
            "dup_pairs": self.dup_pairs,
        }


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def run(pages: list[dict], db_path: str | None, dry_run: bool = False,
        max_reject_rate: float = 0.40) -> Stats:
    st = Stats()

    # S1 采集：这里已经拿到 pages，统计一下缺陷分布（真实项目是网络耗时）
    t0 = time.perf_counter()
    st.counts["fetched"] = len(pages)
    st.stage_seconds["s1_fetch"] = time.perf_counter() - t0

    # S2 + S3 清洗与抽取
    t0 = time.perf_counter()
    records = []
    for p in pages:
        rec = extract(p["html"])
        rec["url"] = p["url"]
        rec["text"] = extract_body(p["html"])
        rec["kind"] = p["kind"]
        records.append(rec)
    st.stage_seconds["s2s3_clean_extract"] = time.perf_counter() - t0

    # S4 去重：粗筛（SimHash 8 段，k≤7）+ 精排（Jaccard ≥ 0.6）
    t0 = time.perf_counter()
    index = SimHashIndex(bands=8)
    shingles: dict[str, set[str]] = {}
    by_key: dict[str, dict] = {}
    accepted: list[dict] = []
    for rec in records:
        h = simhash(rec["text"])
        rec["simhash"] = h
        rec["dup_of"] = None
        key = canon_url(rec["url"])
        rec["url_key"] = key
        toks = set(tokenize(rec["text"]))
        dup = None
        for payload, _ in index.query(h, k=7):
            other = by_key[payload]  # 用字典查，不要每次线性扫 accepted
            a, b = toks, shingles[payload]
            if a and b and len(a & b) / len(a | b) >= 0.6:
                dup = payload
                break
        if dup:
            rec["dup_of"] = dup
            st.counts["duplicate"] += 1
            st.dup_pairs += 1
        else:
            index.add(h, key)
            shingles[key] = toks
            by_key[key] = rec
        accepted.append(rec)
    st.stage_seconds["s4_dedup"] = time.perf_counter() - t0

    # S5 质量门禁
    t0 = time.perf_counter()
    clean_rows, bad_rows = [], []
    for rec in accepted:
        issues = check_record(rec)
        if issues:
            for i in issues:
                st.rejects[i.code] += 1
            bad_rows.append((rec, issues))
        else:
            clean_rows.append(rec)
    st.counts["clean"] = len(clean_rows)
    st.counts["quarantined"] = len(bad_rows)
    st.stage_seconds["s5_gate"] = time.perf_counter() - t0

    # S6 入库
    t0 = time.perf_counter()
    reject_rate = len(bad_rows) / max(1, len(pages))
    if dry_run:
        st.counts["stored"] = 0
    else:
        conn = _connect(db_path)
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        with conn:
            for r in clean_rows:
                conn.execute(
                    "INSERT INTO pages(url_key,title,price,published_at,content,"
                    "simhash,dup_of,ingested_at) VALUES(?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(url_key) DO UPDATE SET "
                    "title=excluded.title, price=excluded.price, "
                    "published_at=excluded.published_at, content=excluded.content, "
                    "simhash=excluded.simhash, dup_of=excluded.dup_of, "
                    "ingested_at=excluded.ingested_at",
                    (r["url_key"], r["title"], float(r["price"]), r["published_at"],
                     r["text"], hash_to_signed(int(r["simhash"])), r["dup_of"], now),
                )
            for r, issues in bad_rows:
                for i in issues:
                    conn.execute(
                        "INSERT INTO quarantine(url_key,code,field,detail,raw_snippet) "
                        "VALUES(?,?,?,?,?)",
                        (r["url_key"], i.code, i.field, i.detail, r["title"][:80]),
                    )
        st.counts["stored"] = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        st.counts["rejected_rows_in_db"] = conn.execute(
            "SELECT COUNT(*) FROM quarantine").fetchone()[0]
        conn.close()
    st.stage_seconds["s6_store"] = time.perf_counter() - t0

    st.counts["reject_rate_pct"] = round(reject_rate * 100, 1)
    if reject_rate > max_reject_rate:
        st.counts["gate"] = "BLOCKED"
    return st


def report(st: Stats, pages: int, elapsed: float) -> None:
    total = sum(st.stage_seconds.values())
    print("\n── 阶段耗时 ──")
    for name, sec in st.stage_seconds.items():
        print(f"    {name:<20} {sec * 1000:8.1f} ms  ({sec / total * 100:5.1f}%)")
    print(f"    {'合计':<20} {total * 1000:8.1f} ms  "
          f"({pages / total:,.0f} 条/s)")

    print("\n── 数量漏斗 ──")
    print(f"    采集      {st.counts['fetched']:>6}")
    print(f"    去重丢弃  {st.counts['duplicate']:>6}  ({st.counts['duplicate'] / pages * 100:.1f}%)")
    print(f"    质检拦截  {st.counts['quarantined']:>6}  ({st.counts['reject_rate_pct']}%)")
    print(f"    入库      {st.counts['stored']:>6}")
    if st.counts.get("gate") == "BLOCKED":
        print("    ⚠️ 拦截率超过阈值，门禁判为 BLOCKED")

    print("\n── 拦截原因（按条计，一条可命中多个规则）──")
    for code, n in st.rejects.most_common():
        print(f"    {code:<20} {n:>6}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=3000)
    ap.add_argument("--db", default="/tmp/day194.db")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()

    pages = make_pages(args.rows)
    db = Path(args.db)
    for p in (db, Path(str(db) + "-journal")):
        p.unlink(missing_ok=True)

    print("=" * 72)
    print(f"Day 194 管道 | {len(pages)} 条输入 | dry_run={args.dry_run} | db={args.db}")
    print("=" * 72)

    t0 = time.perf_counter()
    st = run(pages, str(db), dry_run=args.dry_run)
    elapsed = time.perf_counter() - t0
    report(st, len(pages), elapsed)

    # 幂等性验证：再跑一次，行数必须完全一致
    if not args.dry_run:
        first = st.counts["stored"]
        st2 = run(pages, str(db), dry_run=False)
        second = st2.counts["stored"]
        print(f"\n── 幂等性 ──")
        print(f"    第一次入库 {first} 行 | 第二次重跑后 {second} 行 | "
              f"{'✅ 一致' if first == second else '❌ 重复写入'}")
        print(f"    隔离区行数 {st.counts['rejected_rows_in_db']} → "
              f"{st2.counts['rejected_rows_in_db']}（每轮都会追加，需按批次清理）")

    if args.report:
        Path(args.report).write_text(
            json.dumps(st.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n报告已写入 {args.report}")
    return 0


def _self_test() -> int:
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(("  ✅ " if cond else "  ❌ ") + name + ("" if cond else f" {extra}"))
        ok = ok and cond

    pages = make_pages(300, seed=5)
    st = run(pages, "/tmp/day194_selftest.db", dry_run=False)
    check("有数据入库", st.counts["stored"] > 0, str(st.counts["stored"]))
    check("有数据被拦截", st.counts["quarantined"] > 0)
    check("识别出重复", st.counts["duplicate"] > 0)
    check("入库数 = 干净数", st.counts["stored"] == st.counts["clean"])
    check("拦截原因里有坏价格", "PRICE_OUTLIER" in st.rejects or "PRICE_NOT_NUMBER" in st.rejects,
          str(st.rejects))
    check("拦截原因里有乱码", "MOJIBAKE" in st.rejects, str(st.rejects))

    st2 = run(pages, "/tmp/day194_selftest.db", dry_run=False)
    check("重跑幂等", st2.counts["stored"] == st.counts["stored"])

    st_dry = run(pages, None, dry_run=True)
    check("dry-run 不写库", st_dry.counts["stored"] == 0)

    Path("/tmp/day194_selftest.db").unlink(missing_ok=True)
    print("\n✅ 全部通过" if ok else "\n❌ 存在失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
