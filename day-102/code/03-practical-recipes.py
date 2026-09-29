#!/usr/bin/env python3
"""
Day 102 — Pandas 核心：实战案例 — CSV 数据探索
完整的数据加载 → 清洗 → 分析流程
"""

import pandas as pd
import numpy as np
import os

print("=" * 60)
print("实战：电商销售数据分析")
print("=" * 60)

# ══════════════════════════════════════════════════════
# 第一步：生成模拟数据并保存为 CSV
# ══════════════════════════════════════════════════════
print("\n--- 第一步：生成模拟数据 ---")

np.random.seed(42)
n = 2000

# 生成数据
products = np.random.choice(['iPhone', 'MacBook', 'iPad', 'AirPods', 'Apple Watch'], n,
                            p=[0.3, 0.15, 0.2, 0.25, 0.1])
base_prices = {'iPhone': 6999, 'MacBook': 12999, 'iPad': 4999, 'AirPods': 1299, 'Apple Watch': 3299}
prices = np.array([base_prices[p] * np.random.uniform(0.8, 1.2) for p in products]).round(2)
quantities = np.random.choice([1, 1, 1, 2, 2, 3], n)
discounts = np.random.choice([0, 0, 5, 10, 15, 20], n, p=[0.4, 0.2, 0.15, 0.1, 0.1, 0.05])
channels = np.random.choice(['线上', '线下', '直播'], n, p=[0.5, 0.3, 0.2])
cities = np.random.choice(['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安'], n)
# 故意制造一些缺失值
has_nan = np.random.random(n) < 0.05
ratings = np.where(has_nan, np.nan, np.random.choice([1, 2, 3, 4, 5], n, p=[0.05, 0.1, 0.2, 0.35, 0.3]))

dates = pd.date_range('2024-01-01', periods=n, freq='4H')

df = pd.DataFrame({
    '订单日期': dates,
    '产品': products,
    '单价': prices,
    '数量': quantities,
    '折扣率%': discounts,
    '渠道': channels,
    '城市': cities,
    '评分': ratings
})
df['实付金额'] = (df['单价'] * df['数量'] * (1 - df['折扣率%'] / 100)).round(2)

# 保存 CSV
os.makedirs('days/day-102-pandas-core/data', exist_ok=True)
csv_path = 'days/day-102-pandas-core/data/sales.csv'
df.to_csv(csv_path, index=False)
print(f"生成 {n} 条销售记录，已保存到 {csv_path}")
print(f"其中 {df['评分'].isna().sum()} 条评分缺失")

# ══════════════════════════════════════════════════════
# 第二步：加载与初步探索
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 第二步：加载与初步探索 ---")

df = pd.read_csv(csv_path, parse_dates=['订单日期'])

print(f"\n数据形状: {df.shape[0]} 行 × {df.shape[1]} 列")
print(f"\n数据类型:\n{df.dtypes}")
print(f"\n前5行:\n{df.head()}")
print(f"\n缺失值统计:\n{df.isnull().sum()}")

# ══════════════════════════════════════════════════════
# 第三步：数据清洗
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 第三步：数据清洗 ---")

# 填充缺失的评分为中位数
median_rating = df['评分'].median()
df['评分'] = df['评分'].fillna(median_rating)
print(f"用中位数 {median_rating} 填充了缺失的评分")

# 检查重复行
dup_count = df.duplicated().sum()
print(f"重复行数: {dup_count}")

# 数据验证
print(f"单价范围: {df['单价'].min():.2f} ~ {df['单价'].max():.2f}")
print(f"数量范围: {df['数量'].min()} ~ {df['数量'].max()}")
print(f"实付金额范围: {df['实付金额'].min():.2f} ~ {df['实付金额'].max():.2f}")

# ══════════════════════════════════════════════════════
# 第四步：数据分析
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 第四步：数据分析 ---")

# 4.1 总体概况
print("\n📊 总体销售概况:")
print(f"  总订单数: {len(df):,}")
print(f"  总销售额: ¥{df['实付金额'].sum():,.2f}")
print(f"  平均客单价: ¥{df['实付金额'].mean():.2f}")
print(f"  中位客单价: ¥{df['实付金额'].median():.2f}")

# 4.2 产品维度分析
print("\n📊 各产品销售情况:")
product_stats = df.groupby('产品').agg(
    订单数=('实付金额', 'count'),
    总销售额=('实付金额', 'sum'),
    平均单价=('单价', 'mean'),
    平均评分=('评分', 'mean')
).round(2).sort_values('总销售额', ascending=False)
print(product_stats)

# 4.3 渠道分析
print("\n📊 各渠道对比:")
channel_stats = df.groupby('渠道').agg(
    订单数=('实付金额', 'count'),
    总销售额=('实付金额', 'sum'),
    平均折扣=('折扣率%', 'mean'),
    平均评分=('评分', 'mean')
).round(2)
print(channel_stats)

# 4.4 城市分析
print("\n📊 Top 5 城市:")
city_sales = df.groupby('城市')['实付金额'].sum().sort_values(ascending=False).head()
print(city_sales.round(2))

# 4.5 月度趋势
df['月份'] = df['订单日期'].dt.to_period('M')
monthly = df.groupby('月份')['实付金额'].sum()
print("\n📊 月度销售趋势:")
print(monthly.round(2))

# ══════════════════════════════════════════════════════
# 第五步：高级筛选
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 第五步：高级筛选 ---")

# 高额订单
high_value = df[df['实付金额'] > 10000]
print(f"\n高额订单 (>¥10,000):")
print(f"  数量: {len(high_value)} 笔")
print(f"  占比: {len(high_value)/len(df)*100:.1f}%")
print(f"  贡献销售额: ¥{high_value['实付金额'].sum():,.2f} ({high_value['实付金额'].sum()/df['实付金额'].sum()*100:.1f}%)")

# 高评分产品
top_rated = df[df['评分'] >= 4.5]
print(f"\n高评分订单 (评分≥4.5):")
print(f"  数量: {len(top_rated)} 笔")
print(f"  平均实付金额: ¥{top_rated['实付金额'].mean():.2f}")

# 特定组合筛选
result = df.query('产品 == "iPhone" and 渠道 == "线上" and 城市 == "北京"')
print(f"\niPhone + 线上 + 北京: {len(result)} 笔")
print(f"  平均实付金额: ¥{result['实付金额'].mean():.2f}")

# ══════════════════════════════════════════════════════
# 第六步：导出分析结果
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 第六步：导出结果 ---")

# 保存分析结果
product_stats.to_csv('days/day-102-pandas-core/data/product_analysis.csv')
channel_stats.to_csv('days/day-102-pandas-core/data/channel_analysis.csv')
print("分析结果已保存到 data/ 目录")

print("\n✅ 实战案例完成！")
