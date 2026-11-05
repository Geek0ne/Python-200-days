#!/usr/bin/env python3
"""Day 194 · 内容去重：为什么用 SimHash 而不是 MD5，以及它什么时候会骗你。

四个问题，四组实测：
  1. 精确哈希（SHA256 + 标点归一化）在转载场景的召回是多少？
  2. SimHash 的阈值 k 怎么选？（扫一遍，看 precision/recall 曲线）
  3. 分桶索引和全量比对是否等价？几段最划算？（鸽巢原理的实证）
  4. 短文本为什么不适用 SimHash？（单 token 改动能顶掉多少位）

依赖：numpy（只用于 1200×1200 距离矩阵；纯 Python 版在库里，慢但结果一致）
运行：python3 02-simhash-dedup.py
      python3 02-simhash-dedup.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import string
import sys
import time
from collections import Counter

import numpy as np

from pipeline_lib import SimHashIndex, _token_hash, hamming, simhash, synth_corpus, tokenize

_PUNCT = str.maketrans("", "", string.punctuation + "，。、；：！？“”‘’（）【】《》 \n\t")


def normalize(text: str) -> str:
    """精确去重前的归一化：只处理标点/空白/大小写，不做任何语义近似。"""
    return text.translate(_PUNCT).lower()


def exact_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def pair_metrics(truth: np.ndarray, pred: np.ndarray) -> dict:
    """只统计上三角，避免把 (i,j) 和 (j,i) 算两次。"""
    iu = np.triu_indices(len(truth), 1)
    t, p = truth[iu], pred[iu]
    tp = int((t & p).sum())
    fp = int((~t & p).sum())
    fn = int((t & ~p).sum())
    tn = int((~t & ~p).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": prec, "recall": rec, "f1": f1}


def distance_matrix(hashes: list[int]) -> np.ndarray:
    h = np.array(hashes, dtype=np.uint64)
    xor = h[:, None] ^ h[None, :]
    try:
        return np.bitwise_count(xor).astype(np.uint8)  # numpy >= 2.0
    except AttributeError:  # 老版本兜底：按字节查表
        table = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)
        return table[xor.view(np.uint8)].reshape(xor.shape + (8,)).sum(-1).astype(np.uint8)


def simhash_np(text: str, bits: int = 64) -> int:
    """numpy 版 SimHash，只用于吞吐量测试；结果必须与纯 Python 版逐位一致。"""
    counts = Counter(tokenize(text))
    if not counts:
        return 0
    toks = list(counts)
    hashes = np.array([_token_hash(t) for t in toks], dtype=np.uint64)
    weights = np.array([1 + (c - 1) * 0.3 for c in counts.values()], dtype=np.float64)
    shifts = np.arange(bits, dtype=np.uint64)
    bits_mat = ((hashes[:, None] >> shifts) & np.uint64(1)).astype(np.float64)
    votes = ((bits_mat * 2 - 1) * weights[:, None]).sum(axis=0)
    out = 0
    for i, v in enumerate(votes):
        if v > 0:
            out |= 1 << i
    return out


def build_truth(base_ids: list[int]) -> np.ndarray:
    ids = np.array(base_ids)
    truth = ids[:, None] == ids[None, :]
    np.fill_diagonal(truth, False)
    return truth


def band_pairs(hashes: list[int], bands: int, k: int, out_stats: dict | None = None):
    """用 bands 段索引生成候选对，返回 (对集合, 平均候选数)。"""
    idx = SimHashIndex(bands=bands)
    for i, h in enumerate(hashes):
        idx.add(h, i)
    pairs: set[tuple[int, int]] = set()
    cand_total = 0
    for i, h in enumerate(hashes):
        hits = idx.query(h, k=k)
        cand_total += len(hits)
        for payload, _ in hits:
            if payload != i:
                pairs.add((min(i, payload), max(i, payload)))
    if out_stats is not None:
        out_stats["avg_candidates"] = cand_total / len(hashes)
        out_stats["buckets"] = len(idx.buckets)
    return pairs


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def throughput_report(n: int = 20_000) -> None:
    print(f"\n[5] 吞吐量：{n} 篇文档（合成语料，单进程无并发，numpy 版 SimHash）")
    docs = synth_corpus(n=n, dup_ratio=0.35, seed=7)
    texts = [d["text"] for d in docs]

    t0 = time.perf_counter()
    hashes = [simhash_np(t) for t in texts]
    t_hash = time.perf_counter() - t0

    t0 = time.perf_counter()
    idx = SimHashIndex(bands=8)
    for i, h in enumerate(hashes):
        idx.add(h, i)
    t_index = time.perf_counter() - t0

    t0 = time.perf_counter()
    cand = 0
    for h in hashes:
        cand += len(idx.query(h, k=7))
    t_query = time.perf_counter() - t0

    print(f"    生成哈希  {t_hash:6.2f} s  ({n / t_hash:,.0f} 篇/s)")
    print(f"    建索引    {t_index:6.2f} s  ({n / t_index:,.0f} 篇/s)")
    print(f"    全量查询  {t_query:6.2f} s  ({n / t_query:,.0f} 篇/s, 平均 {cand / n:.1f} 个候选/篇)")
    print(f"    桶数量    {len(idx.buckets):,}（8 段 × 2^8）")

    sample = texts[:200]
    same = all(simhash(t) == simhash_np(t) for t in sample)
    print(f"    纯 Python 与 numpy 实现逐位一致：{'✅ 是' if same else '❌ 否'}")


def short_text_report() -> None:
    """短文本是 SimHash 的死穴：token 少，单点改动就能翻掉很多位。"""
    print("\n[6] 短文本：200 条商品标题，仅把价格改掉（应判为同一商品）")
    rng = np.random.default_rng(7)
    models = list("ABCXZK")
    bases = [f"商品 {m}{rng.integers(100, 999)} 库存 {rng.integers(1, 50)} 件 价格 199 元"
             for m in rng.choice(models, 200)]
    variants = [t.replace("199 元", f"{rng.integers(9, 999)} 元") for t in bases]
    dists = [hamming(simhash(a), simhash(b)) for a, b in zip(bases, variants)]
    hist = Counter(dists)
    print(f"    平均 token 数 {np.mean([len(tokenize(t)) for t in bases]):.1f}")
    print("    汉明距离分布：" + ", ".join(f"{d}:{hist[d]}" for d in sorted(hist)[:8]) + " ...")
    for k in (3, 5, 8, 10):
        rec = np.mean([d <= k for d in dists])
        print(f"    k={k:<2} 召回 {rec * 100:5.1f}%")

    # 对照组：这些短标题彼此无关，看误判
    unrel = [f"商品 {m}{rng.integers(100, 999)} 库存 {rng.integers(1, 50)} 件 价格 {rng.integers(9, 999)} 元"
             for m in rng.choice(models, 600)]
    hs = [simhash(t) for t in unrel]
    d = distance_matrix(hs)
    iu = np.triu_indices(len(hs), 1)
    print(f"    对照组（600 条无关标题，{len(d[iu]):,} 对）："
          f"k=3 误判 {100 * float((d[iu] <= 3).mean()):.2f}% | "
          f"k=8 误判 {100 * float((d[iu] <= 8).mean()):.2f}%")
    print("    → 短文本的 k 必须放大才有召回，但放大后误判率同时上升：")
    print("      这就是为什么短文本该用集合相似度/规则，而不是 SimHash。")


def main() -> int:
    print("=" * 74)
    docs = synth_corpus(n=1200, dup_ratio=0.30, seed=194)
    texts = [d["text"] for d in docs]
    base_ids = [d["base_id"] for d in docs]
    n_dup_docs = sum(d["is_dup"] for d in docs)
    truth = build_truth(base_ids)
    n_truth_pairs = int(np.triu(truth, 1).sum())
    tok_counts = [len(tokenize(t)) for t in texts]
    print(f"语料：{len(docs)} 篇 | 转载/改写 {n_dup_docs} 篇 | 真实重复对 {n_truth_pairs:,}")
    print(f"文档长度：{min(tok_counts)} ~ {max(tok_counts)} token（中位 {int(np.median(tok_counts))}）")
    print("=" * 74)

    # ── 1. 精确哈希 ──
    by_hash: dict[str, list[int]] = {}
    for i, t in enumerate(texts):
        by_hash.setdefault(exact_hash(t), []).append(i)
    pred_exact = np.zeros_like(truth)
    for group in by_hash.values():
        for a in group:
            for b in group:
                if a != b:
                    pred_exact[a, b] = True
    m1 = pair_metrics(truth, pred_exact)
    print("\n[1] 精确哈希（SHA256 + 标点归一化）")
    print(f"    precision={m1['precision']:.3f} recall={m1['recall']:.3f} f1={m1['f1']:.3f}")
    print(f"    抓到 {m1['tp']} 对 / 漏 {m1['fn']} 对 —— 转载加个前缀就逃掉了")

    # ── 2. 阈值扫描（全量两两比对，不经过索引） ──
    hashes = [simhash(t) for t in texts]
    d = distance_matrix(hashes)
    print("\n[2] SimHash 阈值扫描（1200 篇全量两两比对）")
    print("    k     precision  recall     f1")
    best = (None, -1.0)
    for k in (3, 5, 6, 7, 8, 10, 12, 15):
        pred = d <= k
        np.fill_diagonal(pred, False)
        m = pair_metrics(truth, pred)
        if m["f1"] > best[1]:
            best = (k, m["f1"])
        print(f"    {k:<5} {m['precision']:<10.3f} {m['recall']:<10.3f} {m['f1']:.3f}")
    print(f"    → 本语料最优 k={best[0]}（f1={best[1]:.3f}）。k 没有普适值，必须在自己的样本上扫。")

    # ── 3. 分桶索引：段数怎么选 ──
    print("\n[3] 分桶索引：段数决定'保证召回的 k'与候选规模")
    print("    bands  保证k   平均候选/篇   候选对    与全量一致")
    d15 = d
    for bands in (4, 8):
        kk = bands - 1
        stats: dict = {}
        t0 = time.perf_counter()
        pairs = band_pairs(hashes, bands=bands, k=kk, out_stats=stats)
        dt = time.perf_counter() - t0
        full = {(int(i), int(j)) for i, j in zip(*np.where(np.triu(d15 <= kk, 1)))}
        print(f"    {bands:<7} {kk:<7} {stats['avg_candidates']:<13.1f} {len(pairs):<9} "
              f"{'✅' if pairs == full else '❌ 漏 %d' % len(full - pairs)}  ({dt * 1000:.0f} ms)")
    print("    bands=4 候选少但只能保证 k≤3；bands=8 把保证阈值抬到 7，代价是候选翻几倍。")

    # ── 4. 两阶段：粗筛 + 精排 ──
    print("\n[4] 两阶段去重：SimHash 粗筛（k≤7）+ Jaccard 精排（≥0.6）")
    stats = {}
    t0 = time.perf_counter()
    candidates = band_pairs(hashes, bands=8, k=7, out_stats=stats)
    shingles = [set(tokenize(t)) for t in texts]
    pred2 = np.zeros_like(truth)
    for i, j in candidates:
        if jaccard(shingles[i], shingles[j]) >= 0.6:
            pred2[i, j] = True
    dt = time.perf_counter() - t0
    m2 = pair_metrics(truth, pred2)
    total_pairs = len(texts) * (len(texts) - 1) // 2
    print(f"    候选对 {len(candidates):,} / 全量 {total_pairs:,}（{len(candidates) / total_pairs * 100:.2f}%）")
    print(f"    precision={m2['precision']:.3f} recall={m2['recall']:.3f} f1={m2['f1']:.3f}")
    print(f"    误报 {m2['fp']} 对 / 漏报 {m2['fn']} 对 | 耗时 {dt * 1000:.0f} ms")
    print("    → 单靠 SimHash 阈值无法同时拿到高精度和高召回，粗筛+精排才行。")

    throughput_report()
    short_text_report()

    print("\n" + "=" * 74)
    print("结论：精确哈希只能抓原样复制；SimHash 负责把 1200² 压到几千候选；")
    print("      最终判定交给集合相似度；短文本另走一条路。")
    print("=" * 74)
    return 0


def _self_test() -> int:
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(("  ✅ " if cond else "  ❌ ") + name + ("" if cond else f" {extra}"))
        ok = ok and cond

    check("归一化抹掉标点差异", normalize("你好，世界！") == normalize("你好世界"))

    t1 = "国产新能源汽车在欧洲市场的接受度明显上升"
    t2 = "国产新能源汽车在欧洲市场的接受度明显提高"
    check("改写文本精确哈希不同", exact_hash(t1) != exact_hash(t2))
    check("改写文本 SimHash 距离 ≤ 8", hamming(simhash(t1), simhash(t2)) <= 8)

    same = all(simhash(t) == simhash_np(t) for t in (t1, t2, "家庭烘焙面包时面团含水量决定最终口感"))
    check("numpy 版与纯 Python 版逐位一致", same)

    dm = distance_matrix([simhash(t1), simhash(t1)])
    check("距离矩阵对角为 0 且对称", dm[0, 0] == 0 and dm[0, 1] == dm[1, 0] == 0)

    hs = [simhash(t) for t in (t1, t2, "完全无关的第三篇文档内容，讲的是咖啡烘焙曲线")]
    band = band_pairs(hs, bands=8, k=7)
    full_d = distance_matrix(hs)
    full = {(int(i), int(j)) for i, j in zip(*np.where(np.triu(full_d <= 7, 1)))}
    check("8 段索引在 k=7 时与全量一致", band == full, f"{band} vs {full}")

    check("空集合 Jaccard 不炸", jaccard(set(), set()) == 0.0)

    print("\n✅ 全部通过" if ok else "\n❌ 存在失败")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    sys.exit(_self_test() if args.self_test else main())
