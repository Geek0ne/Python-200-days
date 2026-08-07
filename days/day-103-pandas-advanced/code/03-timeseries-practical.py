#!/usr/bin/env python3
"""
Day 103 — Pandas 进阶：时间序列与实战案例
演示时间序列处理和完整的电商数据分析流程
"""

import pandas as pd
import numpy as np
import os

print("=" * 60)
print("Pandas 进阶：时间序列处理")
print("=" * 60)

# ══════════════════════════════════════════════════════
# 1. 时间序列基础
# ══════════════════════════════════════════════════════
print("\n--- 1. 日期时间基础 ---")

# 创建日期范围
dates = pd.date_range('2024-01-01', periods=12, freq='M')
print(f"月度日期:\n{dates}")

# 提取日期组件
df_dates = pd.DataFrame({'日期': dates})
df_dates['年'] = df_dates['日期'].dt.year
df_dates['月'] = df_dates['日期'].dt.month
df_dates['季度'] = df_dates['日期'].dt.quarter
df_dates['星期'] = df_dates['日期'].dt.day_name()
print(f"\n日期组件:\n{df_dates}")

# ══════════════════════════════════════════════════════
# 2. 时间序列聚合
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 2. 时间序列聚合 ---")

# 模拟每日销售数据
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=365, freq='D')
sales = pd.DataFrame({
    '日期': dates,
    '销售额': np.random.lognormal(10, 0.5, 365).round(2),
    '订单数': np.random.randint(50, 200, 365),
    '客户数': np.random.randint(30, 150, 365)
})
sales.set_index('日期', inplace=True)

# 按周汇总
weekly = sales.resample('W').agg({
    '销售额': 'sum',
    '订单数': 'sum',
    '客户数': 'sum'
})
print("周度汇总 (前4周):")
print(weekly.head(4))

# 按月汇总
monthly = sales.resample('M').agg({
    '销售额': 'sum',
    '订单数': 'sum',
    '客户数': 'sum'
})
print(f"\n月度汇总:")
print(monthly)

# 按季度汇总
quarterly = sales.resample('Q').sum()
print(f"\n季度汇总:")
print(quarterly)

# ══════════════════════════════════════════════════════
# 3. 滚动窗口
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 3. 滚动窗口 ---")

sales['7日移动平均'] = sales['销售额'].rolling(7).mean()
sales['30日移动平均'] = sales['销售额'].rolling(30).mean()
sales['7日移动标准差'] = sales['销售额'].rolling(7).std()
sales['EMA_7'] = sales['销售额'].ewm(span=7).mean()

print("滚动窗口结果 (最后10天):")
print(sales[['销售额', '7日移动平均', '30日移动平均', 'EMA_7']].tail(10).round(2))

# ══════════════════════════════════════════════════════
# 4. 实战：电商数据分析
# ══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("--- 实战：电商销售数据分析 ---")

np.random.seed(42)
n = 3000
dates = pd.date_range('2023-01-01', periods=n, freq='6H')

df = pd.DataFrame({
    '日期': np.random.choice(dates, n),
    '产品': np.random.choice(['iPhone', 'MacBook', 'iPad', 'AirPods'], n, p=[0.3, 0.15, 0.3, 0.25]),
    '渠道': np.random.choice(['线上', '线下', '直播'], n, p=[0.5, 0.3, 0.2]),
    '城市': np.random.choice(['北京', '上海', '广州', '深圳'], n),
    '数量': np.random.choice([1, 1, 1, 2, 2, 3], n),
    '折扣': np.random.choice([0, 5, 10, 15], n, p=[0.4, 0.3, 0.2, 0.1])
})

base_prices = {'iPhone': 6999, 'MacBook': 12999, 'iPad': 4999, 'AirPods': 1299}
df['单价'] = df['产品'].map(base_prices) * np.random.uniform(0.85, 1.15, n)
df['实付金额'] = (df['单价'] * df['数量'] * (1 - df['折扣'] / 100)).round(2)

# 数据清洗
df['日期'] = pd.to_datetime(df['日期'])
df['月'] = df['日期'].dt.to_period('M')
df['季度'] = df['日期'].dt.to_period('Q')

# 产品维度分析
print("\n📊 产品销售统计:")
product_stats = df.groupby('产品').agg(
    订单数=('实付金额', 'count'),
    总销售额=('实付金额', 'sum'),
    平均客单价=('实付金额', 'mean'),
    平均折扣=('折扣', 'mean')
).round(2).sort_values('总销售额', ascending=False)
print(product_stats)

# 渠道对比
print("\n📊 渠道对比:")
channel_stats = df.groupby('渠道').agg(
    订单数=('实付金额', 'count'),
    总销售额=('实付金额', 'sum'),
    平均折扣=('折扣', 'mean')
).round(2)
print(channel_stats)

# 城市排名
print("\n📊 城市销售排名:")
city_stats = df.groupby('城市')['实付金额'].agg(['count', 'sum', 'mean']).round(2)
city_stats.columns = ['订单数', '总销售额', '平均客单价']
print(city_stats.sort_values('总销售额', ascending=False))

# 月度趋势
print("\n📊 月度销售趋势:")
monthly_sales = df.groupby('月').agg({
    '实付金额': 'sum',
    '数量': 'sum'
}).round(2)
print(monthly_sales)

# 交叉分析
print("\n📊 产品 × 渠道 销售额:")
cross = pd.pivot_table(df, values='实付金额', index='产品', columns='渠道',
                       aggfunc='sum', fill_value=0).round(2)
print(cross)

print("\n✅ 时间序列与实战案例完成！")
