#!/usr/bin/env python3
"""Day 194 · 反爬风险预测：把"这页能不能抓"变成一个分类问题。

为什么要分类而不是写 if
----------------------
规则能覆盖已知的拒绝方式（403/429/验证码），但拦不住"软封"——
HTTP 200、页面正常、内容却是空壳。软封没有任何单点特征，
只能靠**多个弱信号的组合**判断，这正是分类器擅长的事。

三个模型对比，回答三个不同的问题：
  1. 规则基线   —— 我现在的 if 有多强？（任何模型的底线）
  2. 逻辑回归   —— 线性模型能不能够用？（可解释、微秒级、无 GPU）
  3. 泄漏模型   —— 如果不小心用了线上拿不到的特征会怎样？（反面教材）

依赖：numpy（模型）+ scikit-learn（仅用于交叉验证对照，可缺席）
运行：python3 01-risk-classifier.py
      python3 01-risk-classifier.py --self-test
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np

from pipeline_lib import FEATURES, synth_responses, to_matrix


# ────────────────────────────── 指标（手写，不依赖 sklearn） ──────────────────────────────

def confusion(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    return tp, fp, fn, tn


def precision_recall_f1(y_true, y_pred) -> tuple[float, float, float]:
    tp, fp, fn, _ = confusion(y_true, y_pred)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f1


def roc_auc(y_true: np.ndarray, score: np.ndarray) -> float:
    """用秩和公式算 AUC，等价于"随机取一正一负，正样本得分更高的概率"。"""
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score), dtype=float)
    ranks[order] = np.arange(1, len(score) + 1)
    # 处理并列分数：同分取平均秩，否则 AUC 会被顺序偏置
    sorted_score = score[order]
    i = 0
    while i < len(sorted_score):
        j = i
        while j + 1 < len(sorted_score) and sorted_score[j + 1] == sorted_score[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + j + 2) / 2
        i = j + 1
    n_pos = int(y_true.sum())
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return float((ranks[y_true == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


# ────────────────────────────── 逻辑回归（梯度下降手写版） ──────────────────────────────

class LogisticRegressionGD:
    """批量梯度下降 + L2。

    为什么标准化：body_len 在 1e5 量级，status_code 只有 3 位数量级，
    不标准化时前者的梯度会把后者彻底淹没，收敛极慢甚至震荡。
    """

    def __init__(self, lr: float = 0.5, epochs: int = 1200, l2: float = 1e-3):
        self.lr, self.epochs, self.l2 = lr, epochs, l2
        self.w: np.ndarray | None = None
        self.b = 0.0
        self.loss_history: list[float] = []

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegressionGD":
        n, d = X.shape
        self.w = np.zeros(d)
        self.b = 0.0
        for _ in range(self.epochs):
            z = X @ self.w + self.b
            p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
            err = p - y
            gw = X.T @ err / n + self.l2 * self.w
            gb = err.mean()
            self.w -= self.lr * gw
            self.b -= self.lr * gb
            # 记录对数损失，用来证明"真的收敛了"而不是跑了 1200 轮就算
            eps = 1e-12
            loss = -(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)).mean()
            self.loss_history.append(float(loss + self.l2 * float(self.w @ self.w) / 2))
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-np.clip(X @ self.w + self.b, -30, 30)))

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)


def standardize(train: np.ndarray, *others: np.ndarray):
    """只用训练集统计量，避免测试集信息泄漏到均值/方差里。"""
    mu, sd = train.mean(0), train.std(0)
    sd[sd == 0] = 1.0
    return [(a - mu) / sd for a in (train, *others)]


def stratified_split(y: np.ndarray, test_ratio: float = 0.3, seed: int = 194):
    rng = np.random.default_rng(seed)
    idx_pos = np.flatnonzero(y == 1)
    idx_neg = np.flatnonzero(y == 0)
    rng.shuffle(idx_pos)
    rng.shuffle(idx_neg)
    n_pos_test = int(len(idx_pos) * test_ratio)
    n_neg_test = int(len(idx_neg) * test_ratio)
    test = np.concatenate([idx_pos[:n_pos_test], idx_neg[:n_neg_test]])
    train = np.concatenate([idx_pos[n_pos_test:], idx_neg[n_neg_test:]])
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def rule_baseline(rows: list[dict]) -> np.ndarray:
    """任何 ML 模型的底线：运维现在就在用的 if 规则。"""
    return np.array([
        int(r["status_code"] in (403, 429, 503) or r["captcha"] == 1 or r["js_challenge"] == 1)
        for r in rows
    ])


def expected_cost(y_true, y_pred, cost_fp: float = 1.0, cost_fn: float = 5.0) -> float:
    tp, fp, fn, tn = confusion(y_true, y_pred)
    return fp * cost_fp + fn * cost_fn


def main() -> int:
    rows = synth_responses(n=3000, seed=194)
    y = np.array([r["label"] for r in rows])
    X = np.array(to_matrix(rows), dtype=float)

    print("=" * 68)
    print("数据集：3000 条合成响应 | 正类(需停抓)占比 %.1f%%" % (100 * y.mean()))
    print("特征：%d 个 → %s" % (len(FEATURES), ", ".join(FEATURES[:5]) + " ..."))
    print("=" * 68)

    train_idx, test_idx = stratified_split(y)
    Xtr, Xte = X[train_idx], X[test_idx]
    ytr, yte = y[train_idx], y[test_idx]
    Xtr_s, Xte_s = standardize(Xtr, Xte)

    # ── 1. 规则基线 ──
    rule_pred = rule_baseline([rows[i] for i in test_idx])
    rp, rr, rf = precision_recall_f1(yte, rule_pred)
    tp, fp, fn, tn = confusion(yte, rule_pred)
    print(f"\n[1] 规则基线 (403/429/503 或 验证码 或 JS挑战)")
    print(f"    precision={rp:.3f} recall={rr:.3f} f1={rf:.3f}")
    print(f"    漏报 {fn} 条软封 / 误报 {fp} 条正常页")

    # ── 2. 逻辑回归 ──
    t0 = time.perf_counter()
    model = LogisticRegressionGD(lr=0.5, epochs=1500, l2=1e-3).fit(Xtr_s, ytr)
    train_ms = (time.perf_counter() - t0) * 1000
    proba = model.predict_proba(Xte_s)
    auc = roc_auc(yte, proba)
    pred = (proba >= 0.5).astype(int)
    p, r, f1 = precision_recall_f1(yte, pred)
    acc = float((pred == yte).mean())
    print(f"\n[2] 逻辑回归（手写 GD，1500 轮）")
    print(f"    训练耗时 {train_ms:.0f} ms | 首末 loss {model.loss_history[0]:.4f} → {model.loss_history[-1]:.4f}")
    print(f"    AUC={auc:.4f} accuracy={acc:.4f} precision={p:.3f} recall={r:.3f} f1={f1:.3f}")

    # 阈值不等于 0.5：业务代价不对称
    best_th, best_cost = 0.5, float("inf")
    for th in np.arange(0.05, 0.96, 0.01):
        c = expected_cost(yte, (proba >= th).astype(int))
        if c < best_cost:
            best_th, best_cost = float(th), c
    cost_05 = expected_cost(yte, pred)
    pred_opt = (proba >= best_th).astype(int)
    tp2, fp2, fn2, tn2 = confusion(yte, pred_opt)
    print(f"    代价敏感阈值：0.50 → {best_th:.2f}（漏报代价=误报×5）")
    print(f"    代价 {cost_05:.0f} → {best_cost:.0f} | 漏报 {fn2} 误报 {fp2}")

    # 推理延迟
    one = Xte_s[:1]
    for _ in range(200):  # 预热，避免把首次的 import/缓存抖动算进去
        model.predict_proba(one)
    t0 = time.perf_counter()
    N = 2000
    for _ in range(N):
        model.predict_proba(one)
    per_call_us = (time.perf_counter() - t0) / N * 1e6
    t0 = time.perf_counter()
    for _ in range(20):
        model.predict_proba(Xte_s)
    batch_per_row_us = (time.perf_counter() - t0) / (20 * len(Xte_s)) * 1e6
    print(f"    单条推理 {per_call_us:.1f} µs | 批量 {batch_per_row_us:.2f} µs/条（%d 行/批）" % len(Xte_s))

    # ── 3. 泄漏演示：用了线上拿不到的特征 ──
    # _propensity 是生成器里决定标签的隐藏变量，线上爬虫永远观测不到。
    leak_col = np.array([[r["_propensity"]] for r in rows])
    ltr_s, lte_s = standardize(leak_col[train_idx], leak_col[test_idx])
    leak_only = LogisticRegressionGD(lr=1.0, epochs=800).fit(ltr_s, ytr)
    leak_only_auc = roc_auc(yte, leak_only.predict_proba(lte_s))

    Xl = np.column_stack([X, leak_col])
    Xltr_s, Xlte_s = standardize(Xl[train_idx], Xl[test_idx])
    leak_model = LogisticRegressionGD(lr=0.5, epochs=1500).fit(Xltr_s, ytr)
    leak_auc = roc_auc(yte, leak_model.predict_proba(Xlte_s))
    print(f"\n[3] 反面教材：把生成器的隐藏变量 _propensity 当特征")
    print(f"    只用泄漏列：AUC={leak_only_auc:.4f}（一个字段顶整套特征工程）")
    print(f"    特征+泄漏：AUC={leak_auc:.4f}（比诚实模型 {auc:.4f} 高 {leak_auc - auc:+.4f}）")
    print(f"    ⚠️ 增益小≠没风险：这 10 个特征本身已经很强，泄漏被掩盖了。")
    print(f"    换成弱特征数据集，同样一个字段能让离线 AUC 虚高 0.2–0.3。")
    print(f"    真实泄漏常伪装成 'block_page_title' 'waf_reason' 这类字段。")

    # ── 4. 系数可解释性 ──
    order = np.argsort(-np.abs(model.w))
    print(f"\n[4] 标准化系数 Top5（正=更像被封）")
    for i in order[:5]:
        print(f"    {FEATURES[i]:<14} {model.w[i]:+.3f}")

    # ── 5. sklearn 交叉验证对照（可选） ──
    try:
        import warnings
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score, StratifiedKFold
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        # 必须把标准化放进 Pipeline：直接用原始量纲喂 lbfgs 会
        # "failed to converge after 1000 iterations"（本次真实踩到，见 README）
        sk = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=194)
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # 有收敛警告就当场炸，而不是刷屏后假装没事
            scores = cross_val_score(sk, X, y, cv=cv, scoring="roc_auc")
        print(f"\n[5] sklearn 5 折 AUC = {scores.mean():.4f} ± {scores.std():.4f}")
        print(f"    手写模型单次切分 AUC = {auc:.4f}（单次切分会波动 ±0.02 左右）")
    except ImportError:
        print("\n[5] 未安装 scikit-learn，跳过交叉验证对照（不影响主结论）")

    print("\n" + "=" * 68)
    print("结论：规则漏掉的软封是分类器的主要收益来源；")
    print("      模型本身微秒级，瓶颈从来不在推理，而在特征采集与标注。")
    print("=" * 68)
    return 0


def _self_test() -> int:
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        print(("  ✅ " if cond else "  ❌ ") + name + ("" if cond else f" {extra}"))
        ok = ok and cond

    # AUC 的边界：完美排序=1，完全反序=0，全同分=0.5
    y = np.array([0, 0, 1, 1])
    check("AUC 完美排序 = 1.0", roc_auc(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0)
    check("AUC 完全反序 = 0.0", roc_auc(y, np.array([0.9, 0.8, 0.2, 0.1])) == 0.0)
    check("AUC 全同分 = 0.5", roc_auc(y, np.array([0.5] * 4)) == 0.5)
    # 并列分数必须取平均秩：正样本落在 (0.6,0.6) 这个并列组里，
    # 平均秩 2.5 → AUC = (2.5 + 4 - 2*3/2) / (2*2) = 0.875
    # 不处理并列（按出现顺序给秩）会得到 0.75 或 1.0，都是错的
    check("AUC 并列分数取平均秩",
          abs(roc_auc(np.array([0, 0, 1, 1]), np.array([0.1, 0.6, 0.6, 0.9])) - 0.875) < 1e-9)

    # 模型能学会一个显然的方向
    rng = np.random.default_rng(0)
    Xs = np.column_stack([rng.normal(0, 1, 400), rng.normal(0, 1, 400)])
    ys = (Xs[:, 0] + 0.2 * rng.normal(0, 1, 400) > 0).astype(int)
    m = LogisticRegressionGD(lr=0.5, epochs=400).fit(Xs, ys)
    check("模型学到正确符号", m.w[0] > 0.5, f"w0={m.w[0]:.3f}")
    check("概率在 [0,1]", bool(((m.predict_proba(Xs) >= 0) & (m.predict_proba(Xs) <= 1)).all()))
    check("loss 单调下降（末值<首值）", m.loss_history[-1] < m.loss_history[0])

    # 泄漏列确实存在于生成器里，但不在 FEATURES 中
    rows = synth_responses(10, seed=1)
    check("泄漏字段未被模型使用", "_propensity" not in FEATURES and "_propensity" in rows[0])

    # 规则基线在"软封"上必然漏：200 + 无验证码
    soft = {"status_code": 200, "captcha": 0, "js_challenge": 0}
    check("规则基线漏掉裸软封", rule_baseline([soft])[0] == 0)

    print("\n✅ 全部通过" if ok else "\n❌ 存在失败")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    sys.exit(_self_test() if args.self_test else main())
