#!/usr/bin/env python3
"""captcha_lib.py — 合成验证码生成与图像预处理工具（无外部服务依赖）

为什么自己合成数据集：
    真实站点的验证码不能批量抓取（既有法律风险，也无法拿到标准答案）。
    要量化"识别率"，必须有一批**带 ground truth** 的样本。
    自己合成的好处是答案已知、噪声强度可控、可无限复现（固定 seed）。

用法：
    python3 captcha_lib.py --n 200 --noise hard --out /tmp/captcha-ds
"""
from __future__ import annotations

import argparse
import csv
import random
import string
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 去掉 0/O/1/I/l 这类人眼都容易混淆的字符：识别率的分母要干净
ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "O0I1L")
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def random_text(n: int = 4, rng: random.Random | None = None) -> str:
    rng = rng or random
    return "".join(rng.choice(ALPHABET) for _ in range(n))


def _warp(img: Image.Image, amp: float, rng: random.Random) -> Image.Image:
    """正弦波扭曲：模拟字符被拉伸，破坏 OCR 的"等宽切分"假设。"""
    import cv2

    arr = np.array(img)
    h, w = arr.shape[:2]
    phase = rng.uniform(0, 6.28)
    period = rng.uniform(28, 60)
    xs = np.arange(w, dtype=np.float32)
    dx = (amp * np.sin(2 * np.pi * xs / period + phase)).astype(np.float32)
    map_x = np.tile(xs, (h, 1)) + dx[None, :]
    map_y = np.tile(np.arange(h, dtype=np.float32)[:, None], (1, w))
    return Image.fromarray(cv2.remap(arr, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))


def render_captcha(text: str, noise: str = "medium", size=(160, 60), seed: int | None = None) -> Image.Image:
    """渲染一张验证码。

    noise 三档：
        clean  —— 只有字符，用于验证 OCR 上限
        medium —— 加点、线、轻微扭曲（多数站点的默认强度）
        hard   —— 强扭曲 + 多条干扰线 + 背景网格（模拟带风控的站点）
    """
    rng = random.Random(seed)
    w, h = size
    bg = rng.randint(235, 255)
    img = Image.new("RGB", size, (bg, bg, bg))
    d = ImageDraw.Draw(img)

    if noise == "hard":
        for x in range(0, w, 8):
            d.line([(x, 0), (x, h)], fill=(225, 225, 225))
        for y in range(0, h, 8):
            d.line([(0, y), (w, y)], fill=(225, 225, 225))

    # 字符：每个字独立旋转 + 上下抖动 + 深浅不同的颜色
    x = rng.randint(3, 8)
    for ch in text:
        fs = rng.randint(28, 36)
        f = _font(fs)
        color = tuple(rng.randint(10, 90) for _ in range(3))
        layer = Image.new("RGBA", (fs * 2, fs * 2), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((fs // 2, fs // 4), ch, font=f, fill=color + (255,))
        layer = layer.rotate(rng.uniform(-25, 25) if noise != "clean" else 0, expand=False, resample=Image.BICUBIC)
        img.paste(layer, (x, rng.randint(-3, 6)), layer)
        x += rng.randint(30, 34)

    if noise in ("medium", "hard"):
        # 干扰点
        for _ in range(120 if noise == "medium" else 260):
            d.point((rng.randrange(w), rng.randrange(h)), fill=tuple(rng.randint(0, 160) for _ in range(3)))
        # 干扰线
        for _ in range(2 if noise == "medium" else 5):
            d.line(
                [(rng.randrange(w), rng.randrange(h)), (rng.randrange(w), rng.randrange(h))],
                fill=tuple(rng.randint(60, 170) for _ in range(3)),
                width=1,
            )
        if noise == "hard":
            for _ in range(3):
                x0, y0 = rng.randrange(w), rng.randrange(h)
                d.arc([x0, y0, x0 + rng.randint(20, 60), y0 + rng.randint(15, 40)], 0, rng.randint(90, 330),
                      fill=tuple(rng.randint(80, 160) for _ in range(3)), width=1)

    if noise != "clean":
        img = _warp(img, 1.2 if noise == "medium" else 2.6, rng)
        img = img.filter(ImageFilter.SMOOTH if noise == "medium" else ImageFilter.GaussianBlur(0.4))
    return img


def preprocess(img: Image.Image, mode: str = "none") -> Image.Image:
    """图像预处理。mode: none / gray / otsu / denoise

    为什么需要预处理：OCR 模型吃的是"黑白分明的字符形状"，
    彩色背景、干扰线会把笔画和噪声混在一起。但预处理**不是越狠越好**——
    阈值太高会把细笔画一起干掉（见 Day 193 的翻车实验）。
    """
    if mode == "none":
        return img
    gray = img.convert("L")
    if mode == "gray":
        return gray
    arr = np.array(gray)
    arr = np.array(Image.fromarray(arr).filter(ImageFilter.MedianFilter(3)))
    # Otsu 阈值：最大化类间方差，自动找前景/背景分界
    hist = np.bincount(arr.ravel(), minlength=256).astype(np.float64)
    total = arr.size
    sum_all = np.dot(np.arange(256), hist)
    sum_b = w_b = 0.0
    best_t, best_var = 127, -1.0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best_var:
            best_var, best_t = var, t
    binary = ((arr > best_t) * 255).astype(np.uint8)
    out = Image.fromarray(binary)
    if mode == "denoise":
        import cv2

        m = cv2.morphologyEx(np.array(out), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        out = Image.fromarray(m)
    return out


def build_dataset(out_dir: str, n: int = 200, noise: str = "medium", length: int = 4, seed: int = 193) -> Path:
    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(n):
        s = seed * 100000 + i
        text = random_text(length, random.Random(s))
        img = render_captcha(text, noise=noise, seed=s)
        name = f"{i:04d}.png"
        img.save(out / "images" / name)
        rows.append({"file": name, "label": text, "noise": noise, "seed": s})
    with (out / "labels.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["file", "label", "noise", "seed"])
        wr.writeheader()
        wr.writerows(rows)
    return out


def load_dataset(ds_dir: str) -> list[dict]:
    ds = Path(ds_dir)
    with (ds / "labels.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["path"] = str(ds / "images" / r["file"])
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="合成验证码数据集")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--noise", choices=["clean", "medium", "hard"], default="medium")
    ap.add_argument("--out", default="/tmp/captcha-ds")
    a = ap.parse_args()
    p = build_dataset(a.out, a.n, a.noise)
    print(f"✅ 生成 {a.n} 张 {a.noise} 验证码 → {p}")
