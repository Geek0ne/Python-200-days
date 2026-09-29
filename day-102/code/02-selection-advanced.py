#!/usr/bin/env python3
"""
Day 102 — Pandas 核心：数据选择进阶
演示 loc/iloc 的高级用法、布尔索引、query 方法
"""

import pandas as pd
import numpy as np

print("=" * 60)
print("数据选择进阶：loc / iloc / 布尔索引 / query")
print("=" * 60)

# 创建示例数据
np.random.seed(42)
df = pd.DataFrame({
    '产品': np.random.choice(['手机', '电脑', '耳机', '平板'], 20),
    '品牌': np.random.choice(['华为', '苹果', '小米', '联想'], 20),
    '价格': np.random.randint(100, 8000, 20),
    '销量': np.random.randint(10, 500, 20),
    '评分': np.round(np.random.uniform(3.0, 5.0, 20), 1),
    '地区': np.random.choice(['华北', '华东', '华南', '西南'], 20)
})

print("原始数据:")
print(df)

# ── 1. loc 高级用法 ──
print("\n--- 1. loc 高级用法 ---")

# 行标签 + 列标签
print(f"\n选择第 0 行的 产品 和 价格:")
print(df.loc[0, ['产品', '价格']])

# 范围选择
print(f"\n选择第 2-5 行:")
print(df.loc[2:5])

# 条件 + 列选择
print(f"\n价格 > 3000 的产品和品牌:")
print(df.loc[df['价格'] > 3000, ['产品', '品牌']])

# 多条件 + 列选择
print(f"\n华为 + 价格 > 2000 的记录:")
print(df.loc[(df['品牌'] == '华为') & (df['价格'] > 2000)])

# ── 2. iloc 高级用法 ──
print("\n--- 2. iloc 高级用法 ---")

# 行列同时指定
print(f"\niloc: 前5行，第1-3列:")
print(df.iloc[:5, 1:4])

# 花式索引
print(f"\niloc: 第0, 5, 10行，第0, 2列:")
print(df.iloc[[0, 5, 10], [0, 2]])

# ── 3. 布尔索引详解 ──
print("\n--- 3. 布尔索引详解 ---")

# 单条件
mask1 = df['价格'] > 3000
print(f"\n价格 > 3000 的行数: {mask1.sum()}")

# 多条件（注意括号！）
mask2 = (df['品牌'] == '华为') & (df['评分'] > 4.0)
print(f"华为且评分>4.0的行数: {mask2.sum()}")

# OR 条件
mask3 = (df['产品'] == '手机') | (df['产品'] == '电脑')
print(f"手机或电脑的行数: {mask3.sum()}")

# NOT 条件
mask4 = ~(df['地区'] == '华北')
print(f"非华北地区的行数: {mask4.sum()}")

# isin 筛选
print(f"\n华为或苹果的产品:")
print(df[df['品牌'].isin(['华为', '苹果'])][['产品', '品牌', '价格']])

# between 范围筛选
print(f"\n价格在 1000-5000 之间:")
print(df[df['价格'].between(1000, 5000)][['产品', '价格']])

# ── 4. query 方法 ──
print("\n--- 4. query 方法 ---")

# 基本查询
print(f"\nquery: 价格 > 3000:")
print(df.query('价格 > 3000'))

# 使用变量
min_price = 2000
max_price = 5000
print(f"\nquery: 价格在 {min_price}-{max_price} 之间:")
print(df.query('@min_price <= 价格 <= @max_price'))

# 复杂查询
print(f"\nquery: 华为手机且评分>4:")
print(df.query('品牌 == "华为" and 产品 == "手机" and 评分 > 4'))

# ── 5. 字符串筛选 ──
print("\n--- 5. 字符串筛选 ---")

print(f"\n品牌以 '华' 开头:")
print(df[df['品牌'].str.startswith('华')][['品牌']])

print(f"\n品牌包含 '联':")
print(df[df['品牌'].str.contains('联')][['品牌']])

# ── 6. 性能对比 ──
print("\n--- 6. 性能对比 ---")

import time

# 大数据
big_df = pd.DataFrame({
    'A': np.random.rand(100000),
    'B': np.random.rand(100000),
    'C': np.random.choice(['X', 'Y', 'Z'], 100000)
})

# loc 方式
start = time.time()
_ = big_df.loc[big_df['A'] > 0.5]
t_loc = time.time() - start

# 布尔索引方式
start = time.time()
_ = big_df[big_df['A'] > 0.5]
t_bool = time.time() - start

# query 方式
start = time.time()
_ = big_df.query('A > 0.5')
t_query = time.time() - start

print(f"loc 布尔筛选:   {t_loc:.4f}s")
print(f"[] 布尔索引:    {t_bool:.4f}s")
print(f"query 方法:     {t_query:.4f}s")

print("\n✅ 数据选择进阶演示完成！")
