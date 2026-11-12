#!/usr/bin/env python3
"""03-captcha-ocr.py — 验证码识别基准：ddddocr × 预处理 × 噪声强度

为什么要有基准：
    "加个预处理能提高识别率"是常见直觉，但直觉经常是错的。
    本脚本在固定 seed 的合成数据集上，对 4 种预处理 × 3 种噪声强度做全组合测量，
    给出**准确率 / 字符准确率 / 单张耗时**三列真实数字。

指标定义：
    exact     4 个字符全对才算对（业务上唯一有意义的指标：验证码错一个字符也是错）
    char_acc  按字符位置统计，用来看"错得多离谱"
    ms/img    单张推理耗时（含预处理）

用法：
    python3 03-captcha-ocr.py --n 100
    python3 03-captcha-ocr.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from captcha_lib import build_dataset, load_dataset, preprocess  # noqa: E402

MODES = ("none", "gray", "otsu", "denoise")
NOISES = ("clean", "medium", "hard")


def char_accuracy(pred: str, truth: str) -> float:
    """按位置比较（不做对齐编辑距离）：验证码长度固定，位置错就是错。"""
    if not truth:
        return 0.0
    n = min(len(pred), len(truth))
    hit = sum(1 for i in range(n) if pred[i] == truth[i])
    return hit / len(truth)


def evaluate(rows: list[dict], mode: str, ocr) -> dict:
    from PIL import Image

    exact = 0
    char_sum = 0.0
    t_sum = 0.0
    bad_examples = []
    for r in rows:
        img = Image.open(r["path"])
        t0 = time.perf_counter()
        processed = preprocess(img, mode)
        pred = ocr.classification(processed)
        t_sum += time.perf_counter() - t0
        pred = (pred or "").upper()
        if pred == r["label"]:
            exact += 1
        else:
            if len(bad_examples) < 3:
                bad_examples.append(f"{r['label']}→{pred or '∅'}")
        char_sum += char_accuracy(pred, r["label"])
    n = len(rows)
    return {
        "mode": mode,
        "n": n,
        "exact": exact,
        "exact_rate": exact / n,
        "char_acc": char_sum / n,
        "ms_per_img": t_sum / n * 1000,
        "bad_examples": bad_examples,
    }


def run(n: int, datasets_root: str) -> int:
    try:
        import ddddocr
    except ImportError:
        print("❌ 未安装 ddddocr：pip install ddddocr")
        return 2
    ocr = ddddocr.DdddOcr(show_ad=False)

    root = Path(datasets_root)
    results = {}
    for noise in NOISES:
        ds = root / noise
        if not (ds / "labels.csv").exists():
            print(f"生成 {noise} 数据集（{n} 张）…")
            build_dataset(str(ds), n=n, noise=noise, seed={"clean": 11, "medium": 22, "hard": 33}[noise])
        rows = load_dataset(str(ds))
        results[noise] = []
        print(f"\n=== 噪声强度: {noise} ({len(rows)} 张) ===")
        print(f"{'预处理':<10}{'全对':>6}{'准确率':>9}{'字符准确率':>11}{'ms/张':>8}   错例")
        for mode in MODES:
            r = evaluate(rows, mode, ocr)
            results[noise].append(r)
            print(f"{mode:<10}{r['exact']:>6}{r['exact_rate']*100:>8.1f}%"
                  f"{r['char_acc']*100:>10.1f}%{r['ms_per_img']:>8.1f}   {' '.join(r['bad_examples'])}")

    print("\n=== 横向对比：每种噪声下的最佳预处理 ===")
    for noise, rs in results.items():
        best = max(rs, key=lambda x: x["exact_rate"])
        worst = min(rs, key=lambda x: x["exact_rate"])
        delta = (best["exact_rate"] - worst["exact_rate"]) * 100
        print(f"  {noise:<8} 最佳={best['mode']:<8}{best['exact_rate']*100:5.1f}%  "
              f"最差={worst['mode']:<8}{worst['exact_rate']*100:5.1f}%  差距 {delta:+.1f}pp")

    out = Path(tempfile.gettempdir()) / "day193-captcha.json"
    out.write_text(json.dumps({"n": n, "results": results}, ensure_ascii=False, indent=2))
    print(f"\n结果已写入 {out}")
    return 0


def self_test() -> int:
    fails = 0

    def check(name, cond, extra=""):
        nonlocal fails
        print(("  ✅ " if cond else "  ❌ ") + name + (f"  {extra}" if extra else ""))
        fails += 0 if cond else 1

    from PIL import Image
    import numpy as np
    from captcha_lib import render_captcha, random_text

    img = render_captcha("AB3D", noise="hard", seed=7)
    check("生成图为 RGB 160x60", img.size == (160, 60) and img.mode == "RGB")
    gray = preprocess(img, "gray")
    check("gray 模式转单通道", gray.mode == "L")
    binimg = preprocess(img, "otsu")
    vals = set(np.array(binimg).ravel().tolist())
    check("otsu 输出只有 0/255", vals <= {0, 255}, str(sorted(vals))[:40])
    check("denoise 不崩且尺寸不变", preprocess(img, "denoise").size == (160, 60))
    check("同一 seed 可复现", list(img.getdata()) == list(render_captcha("AB3D", noise="hard", seed=7).getdata()))

    # 指标函数自身的正确性：错一个字符时 exact=0 但 char_acc=75%
    check("字符准确率计算正确", abs(char_accuracy("AB3X", "AB3D") - 0.75) < 1e-9)
    check("空预测得 0", char_accuracy("", "AB3D") == 0.0)
    check("长度不符不越界", char_accuracy("AB", "AB3D") == 0.5)
    print(f"\n自检结果：{'全部通过' if fails == 0 else f'{fails} 项失败'}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--datasets", default="/tmp/captcha-ds")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    raise SystemExit(self_test() if a.self_test else run(a.n, a.datasets))
