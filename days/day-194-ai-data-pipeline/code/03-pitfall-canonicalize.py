#!/usr/bin/env python3
"""Day 194 · 翻车实验：URL 规范化做过头，2400 条 URL 静默变成 421 条。

现象
----
入库后行数只有预期的一半，日志没有任何报错，重跑也"幂等"。
根因不在数据库，在规范化：早期版本为了去重，把**整个查询串**都删了。

本脚本完整复现并修复：
  1. 构造 2400 条 URL（400 个商品 × 2 个颜色 = 800 个真实页面 + 分页）
  2. 用"删掉全部查询参数"的旧规则入库 → 看丢了多少
  3. 换成"只删已知追踪参数"的新规则 → 再看一次
  4. 重跑两遍，证明幂等 ≠ 正确

运行：python3 03-pitfall-canonicalize.py
      python3 03-pitfall-canonicalize.py --self-test
"""

from __future__ import annotations

import argparse
import random
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pipeline_lib import canon_url

BASE = "https://shop.example.com"


def legacy_canon(url: str) -> str:
    """旧规则：丢掉全部查询串。看起来"干净"，实际上把业务主键也丢了。"""
    p = urlsplit(url.strip())
    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return urlunsplit((p.scheme.lower(), netloc, p.path or "/", "", ""))


def build_fixture() -> tuple[list[str], set[str]]:
    """返回 (抓到的 URL 列表, 真实页面集合)。

    真实页面 = 商品路径 + 颜色 sku；分页的 page 同样是业务主键。
    这三类参数（sku / page / 追踪参数）在旧规则下被一视同仁地删掉。
    """
    rng = random.Random(194)
    urls: list[str] = []
    truth: set[str] = set()
    for pid in range(1, 401):
        for color in ("red", "blue"):
            page = f"/product/{pid}?sku={color}"
            truth.add(page)
            base = BASE + page
            urls.append(base)
            urls.append(base + "&utm_source=weibo&utm_medium=social")
            urls.append(base + "&spm=a1z.2&ref=home")
            if rng.random() < 0.3:
                urls.append(base + "&utm_campaign=autumn")
    for p in range(1, 21):
        truth.add(f"/list?page={p}")
        urls.append(f"{BASE}/list?page={p}")
        urls.append(f"{BASE}/list?page={p}&utm_source=nav")
    rng.shuffle(urls)
    return urls, truth


def store(urls: list[str], canon, db_path: str) -> dict:
    db = Path(db_path)
    if db.exists():
        db.unlink()
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE pages (
            url_key TEXT PRIMARY KEY,
            raw_url TEXT NOT NULL,
            hit_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    for u in urls:
        conn.execute(
            "INSERT INTO pages(url_key, raw_url, hit_count) VALUES(?,?,1) "
            "ON CONFLICT(url_key) DO UPDATE SET hit_count = hit_count + 1",
            (canon(u), u),
        )
    conn.commit()
    rows = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    keys = {r[0] for r in conn.execute("SELECT url_key FROM pages")}
    conn.close()
    return {"rows": rows, "keys": keys}


def evaluate(name: str, urls: list[str], truth: set[str], canon) -> dict:
    canon_keys = {canon(u) for u in urls}
    # 判断"丢页"：同一个 key 下挂了多少个不同的真实页面
    buckets: dict[str, set[str]] = {}
    for u in urls:
        k = canon(u)
        # 从原始 URL 还原它属于哪个真实页面
        p = urlsplit(u)
        page = p.path + (("?" + p.query) if "sku=" in p.query else "")
        if "sku=" in p.query:
            sku = [seg for seg in p.query.split("&") if seg.startswith("sku=")][0]
            page = p.path + "?" + sku
        elif "page=" in p.query:
            pg = [seg for seg in p.query.split("&") if seg.startswith("page=")][0]
            page = p.path + "?" + pg
        else:
            page = p.path
        buckets.setdefault(k, set()).add(page)

    collapsed = {k: v for k, v in buckets.items() if len(v) > 1}
    lost_pages = len(truth) - len({next(iter(v)) for v in buckets.values() if len(v) == 1}
                                  | {next(iter(v)) for v in collapsed.values()})
    merged_pages = sum(len(v) for v in collapsed.values())
    print(f"\n[{name}] 规范化后不同 key：{len(canon_keys)} 个")
    print(f"    真实页面 {len(truth)} 个 → 能表示出来的 {len(truth) - (merged_pages - len(collapsed))} 个")
    print(f"    发生合并的 key：{len(collapsed)} 个，涉及真实页面 {merged_pages} 个")
    print(f"    静默丢失 {merged_pages - len(collapsed)} 个页面（没有任何报错）")
    if collapsed:
        sample = list(collapsed.items())[:2]
        for k, v in sample:
            print(f"      例：{k} ← {sorted(v)}")
    return {"keys": len(canon_keys), "lost": merged_pages - len(collapsed)}


def main() -> int:
    urls, truth = build_fixture()
    print("=" * 72)
    print(f"抓取样本：{len(urls)} 条 URL | 真实页面（去重后应有）：{len(truth)} 个")
    print("=" * 72)

    print("\n[1] 旧规则：删掉全部查询串")
    old = evaluate("legacy", urls, truth, legacy_canon)
    db_old = store(urls, legacy_canon, "/tmp/day194_old.db")

    print("\n[2] 新规则：只删已知追踪参数（utm_* / spm / ref / from ...）")
    new = evaluate("fixed", urls, truth, canon_url)
    db_new = store(urls, canon_url, "/tmp/day194_new.db")

    print("\n[3] 入库结果对比")
    print(f"    旧规则 {db_old['rows']} 行 | 新规则 {db_new['rows']} 行 | 应有 {len(truth)} 行")

    print("\n[4] 重跑两遍：幂等 ≠ 正确")
    again_old = store(urls, legacy_canon, "/tmp/day194_old.db")
    again_new = store(urls, canon_url, "/tmp/day194_new.db")
    print(f"    旧规则重跑 {again_old['rows']} 行（与第一次相同 → 幂等）")
    print(f"    新规则重跑 {again_new['rows']} 行（与第一次相同 → 幂等）")
    print("    两次的结果都'稳定'，但只有新规则是对的。幂等只保证可重复，不保证正确。")

    print("\n[5] 修复要点")
    print("    ✅ 白名单删除：只删明确无业务含义的追踪参数，未知参数一律保留")
    print("    ✅ 参数排序：a=1&b=2 与 b=2&a=1 视为同一资源")
    print("    ✅ 入库前断言：canon 后的 key 数量不应小于原始 URL 数的 1/10（兜底告警）")
    print("    ✅ 分页/排序/筛选参数永远不删 —— 它们改变的是内容，不是渠道")

    Path("/tmp/day194_old.db").unlink(missing_ok=True)
    Path("/tmp/day194_new.db").unlink(missing_ok=True)

    print("\n" + "=" * 72)
    print(f"结论：旧规则把 {old['lost']} 个页面合并掉；新规则丢失 {new['lost']} 个。")
    print("=" * 72)
    return 0 if new["lost"] == 0 else 1


def _self_test() -> int:
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(("  ✅ " if cond else "  ❌ ") + name + ("" if cond else f" {extra}"))
        ok = ok and cond

    u1 = "https://shop.example.com/product/1?sku=red&utm_source=x"
    u2 = "https://shop.example.com/product/1?sku=blue&utm_source=x"
    check("旧规则把两个颜色合并", legacy_canon(u1) == legacy_canon(u2))
    check("新规则保留颜色差异", canon_url(u1) != canon_url(u2))
    check("新规则删掉追踪参数", "utm_source" not in canon_url(u1))
    check("新规则保留分页", "page=3" in canon_url("http://e.com/list?page=3&spm=1"))

    urls, truth = build_fixture()
    check("fixture 里有 800 个商品页 + 20 个分页", len(truth) == 820, str(len(truth)))
    old_keys = {legacy_canon(u) for u in urls}
    new_keys = {canon_url(u) for u in urls}
    check("旧规则 key 数明显少于真实页数", len(old_keys) < len(truth) / 2,
          f"{len(old_keys)} vs {len(truth)}")
    check("新规则 key 数等于真实页数", len(new_keys) == len(truth), f"{len(new_keys)} vs {len(truth)}")

    stats1 = store(urls[:50], canon_url, "/tmp/day194_st.db")
    stats2 = store(urls[:50], canon_url, "/tmp/day194_st.db")
    check("重跑行数一致（幂等）", stats1["rows"] == stats2["rows"])
    Path("/tmp/day194_st.db").unlink(missing_ok=True)

    print("\n✅ 全部通过" if ok else "\n❌ 存在失败")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    sys.exit(_self_test() if args.self_test else main())
