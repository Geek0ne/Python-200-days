#!/usr/bin/env python3
"""
Day 101 — NumPy 核心：实战案例
场景：图像处理与数据分析中的 NumPy 应用
"""

import numpy as np
import time

print("=" * 60)
print("实战：图像处理与数据分析")
print("=" * 60)

# ══════════════════════════════════════════════════════
# 场景 1：模拟图像处理流水线
# ══════════════════════════════════════════════════════
print("\n--- 场景 1：图像灰度转换与亮度调整 ---")

# 模拟一张 800x600 RGB 图片
np.random.seed(42)
img = np.random.randint(0, 256, (600, 800, 3), dtype=np.uint8)

# 灰度转换：加权平均法
weights = np.array([0.299, 0.587, 0.114])
start = time.time()
gray = np.dot(img.astype(np.float32), weights).astype(np.uint8)
t_gray = time.time() - start
print(f"灰度转换耗时: {t_gray*1000:.2f}ms")
print(f"灰度图 shape: {gray.shape}, dtype: {gray.dtype}")

# 亮度调整：提升 50% 亮度
bright = np.clip(gray.astype(np.float32) * 1.5, 0, 255).astype(np.uint8)
print(f"亮度调整后均值: {gray.mean():.1f} → {bright.mean():.1f}")

# 直方图统计
hist, bins = np.histogram(gray, bins=256, range=(0, 255))
print(f"最暗像素 (0-31): {hist[:32].sum()} 个")
print(f"最亮像素 (224-255): {hist[224:].sum()} 个")
print(f"中灰度 (96-159): {hist[96:160].sum()} 个")

# 对比度增强（直方图均衡化）
def histogram_equalization(img_gray):
    """直方图均衡化"""
    hist, bins = np.histogram(img_gray, bins=256, range=(0, 256))
    cdf = hist.cumsum()  # 累积分布函数
    cdf_min = cdf[cdf > 0].min()
    n = img_gray.size
    lut = np.round((cdf - cdf_min) / (n - cdf_min) * 255).astype(np.uint8)
    return lut[img_gray]

enhanced = histogram_equalization(gray)
print(f"均衡化后标准差: {gray.std():.1f} → {enhanced.std():.1f}")

# ══════════════════════════════════════════════════════
# 场景 2：销售数据分析
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 场景 2：销售数据分析 ---")

# 模拟 1000 笔交易
np.random.seed(42)
n = 1000

# 交易数据
amounts = np.random.lognormal(mean=4.5, sigma=1.0, size=n).round(2)
categories = np.random.choice(["电子产品", "服装", "食品", "图书", "家居"], size=n)
quantities = np.random.randint(1, 10, size=n)
discounts = np.random.choice([0, 0.05, 0.1, 0.15, 0.2], size=n, p=[0.3, 0.3, 0.2, 0.15, 0.05])

# 计算实付金额（广播运算）
final_prices = (amounts * quantities * (1 - discounts)).round(2)
print(f"总交易数: {n}")
print(f"总销售额: ¥{final_prices.sum():,.2f}")
print(f"平均客单价: ¥{final_prices.mean():.2f}")
print(f"中位客单价: ¥{np.median(final_prices):.2f}")

# 分类统计
print(f"\n--- 分类分析 ---")
unique_cats = np.unique(categories)
for cat in unique_cats:
    mask = categories == cat
    cat_total = final_prices[mask].sum()
    cat_count = mask.sum()
    cat_avg = final_prices[mask].mean()
    print(f"  {cat}: {cat_count}笔, 总额 ¥{cat_total:,.2f}, 均价 ¥{cat_avg:.2f}")

# 折扣对销售额的影响
print(f"\n--- 折扣分析 ---")
for disc in np.unique(discounts):
    mask = discounts == disc
    avg_sale = final_prices[mask].mean()
    count = mask.sum()
    print(f"  折扣 {disc*100:.0f}%: {count}笔, 平均销售额 ¥{avg_sale:.2f}")

# 高额交易筛选
threshold = np.percentile(final_prices, 90)
high_value = final_prices[final_prices > threshold]
print(f"\n--- 高额交易 (Top 10%) ---")
print(f"  阈值: ¥{threshold:.2f}")
print(f"  数量: {len(high_value)} 笔")
print(f"  总额: ¥{high_value.sum():,.2f}")
print(f"  占比: {high_value.sum() / final_prices.sum() * 100:.1f}%")

# ══════════════════════════════════════════════════════
# 场景 3：性能对比 — 矩阵距离计算
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 场景 3：三种距离计算方法性能对比 ---")

np.random.seed(42)
points = np.random.rand(5000, 5)

# 方法 1: 双重循环
def dist_loop(pts):
    n = len(pts)
    d = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d[i, j] = np.sqrt(np.sum((pts[i] - pts[j]) ** 2))
            d[j, i] = d[i, j]
    return d

# 方法 2: 向量化循环
def dist_vectorized_loop(pts):
    n = len(pts)
    d = np.zeros((n, n))
    for i in range(n):
        diff = pts - pts[i]
        d[i] = np.sqrt(np.sum(diff ** 2, axis=1))
    return d

# 方法 3: 全向量化 (广播)
def dist_broadcast(pts):
    sq = np.sum(pts ** 2, axis=1)
    d_sq = sq[:, None] + sq[None, :] - 2 * pts @ pts.T
    np.maximum(d_sq, 0, out=d_sq)
    return np.sqrt(d_sq)

# 测试向量化循环
start = time.time()
d2 = dist_vectorized_loop(points)
t2 = time.time() - start
print(f"向量化循环 (5000点): {t2:.3f}s")

# 测试全向量化
start = time.time()
d3 = dist_broadcast(points)
t3 = time.time() - start
print(f"全向量化广播 (5000点): {t3:.3f}s")
print(f"加速比: {t2/t3:.1f}x")
print(f"结果一致性: {np.allclose(d2, d3, atol=1e-10)}")

# ══════════════════════════════════════════════════════
# 场景 4：NumPy 保存与加载
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 场景 4：NumPy 文件操作 ---")

import os
import tempfile

data = np.random.rand(1000, 10)

# 保存为 .npy 格式（二进制）
with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f:
    npy_path = f.name
np.save(npy_path, data)
print(f"npy 文件大小: {os.path.getsize(npy_path) / 1024:.1f} KB")

# 加载
loaded = np.load(npy_path)
print(f"加载后 shape: {loaded.shape}, 数据一致: {np.array_equal(data, loaded)}")

# 保存为文本格式（对比大小）
with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
    txt_path = f.name
np.savetxt(txt_path, data)
print(f"txt 文件大小: {os.path.getsize(txt_path) / 1024:.1f} KB")
print(f"二进制比文本小 {os.path.getsize(txt_path) / os.path.getsize(npy_path):.1f} 倍")

# 清理临时文件
os.remove(npy_path)
os.remove(txt_path)

print("\n✅ 实战案例演示完成！")
