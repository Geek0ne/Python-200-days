#!/usr/bin/env python3
"""
Day 079 - 实战案例：股票数据分析
用 NumPy 分析模拟股票数据，生成统计报告
"""

import numpy as np
from datetime import datetime, timedelta

print("=" * 60)
print("实战案例：股票数据分析")
print("=" * 60)

# ─── 1. 生成模拟股票数据 ──────────────────────────────
print("\n【1】生成模拟股票数据")

np.random.seed(42)  # 固定随机种子，保证结果可复现

# 生成 120 个交易日的股票价格（约 6 个月）
n_days = 120
# 每日收益率：正态分布，均值 0.05%，标准差 2%
daily_returns = np.random.normal(0.0005, 0.02, n_days)

# 初始价格 100 元
initial_price = 100
# 价格 = 初始价格 × (1 + 收益率) 的累积乘积
prices = initial_price * np.cumprod(1 + daily_returns)

# 生成日期序列
start_date = datetime(2026, 1, 5)  # 周一开始
dates = []
current = start_date
for _ in range(n_days):
    if current.weekday() >= 5:  # 跳过周末
        current += timedelta(days=(7 - current.weekday()))
    dates.append(current)
    current += timedelta(days=1)

print(f"股票代码: FAKE-001")
print(f"数据区间: {dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}")
print(f"交易天数: {n_days}")
print(f"初始价格: {initial_price:.2f}")
print(f"最终价格: {prices[-1]:.2f}")

# ─── 2. 基本统计 ──────────────────────────────────────
print("\n【2】基本统计")

total_return = (prices[-1] / prices[0] - 1) * 100
max_price = np.max(prices)
min_price = np.min(prices)
max_day_idx = np.argmax(prices)
min_day_idx = np.argmin(prices)
avg_price = np.mean(prices)
median_price = np.median(prices)

print(f"总收益率: {total_return:.2f}%")
print(f"最高价: {max_price:.2f} ({dates[max_day_idx].strftime('%Y-%m-%d')})")
print(f"最低价: {min_price:.2f} ({dates[min_day_idx].strftime('%Y-%m-%d')})")
print(f"平均价: {avg_price:.2f}")
print(f"中位价: {median_price:.2f}")

# ─── 3. 收益率分析 ────────────────────────────────────
print("\n【3】收益率分析")

returns = np.diff(prices) / prices[:-1]  # 日收益率
returns_pct = returns * 100

print(f"日均收益率: {np.mean(returns_pct):.4f}%")
print(f"日收益率标准差: {np.std(returns_pct):.4f}%")
print(f"最大单日涨幅: {np.max(returns_pct):.2f}% (第{np.argmax(returns_pct)}天)")
print(f"最大单日跌幅: {np.min(returns_pct):.2f}% (第{np.argmin(returns_pct)}天)")

# 上涨/下跌天数
up_days = np.sum(returns > 0)
down_days = np.sum(returns < 0)
flat_days = np.sum(returns == 0)
print(f"上涨天数: {up_days} ({up_days/len(returns)*100:.1f}%)")
print(f"下跌天数: {down_days} ({down_days/len(returns)*100:.1f}%)")
print(f"持平天数: {flat_days}")

# ─── 4. 移动均线 ──────────────────────────────────────
print("\n【4】移动均线")

def moving_average(data, window):
    """计算移动平均线"""
    cumsum = np.cumsum(data)
    cumsum[window:] = cumsum[window:] - cumsum[:-window]
    return cumsum[window - 1:] / window

ma5 = moving_average(prices, 5)
ma20 = moving_average(prices, 20)
ma60 = moving_average(prices, 60)

print(f"5日均线 (最后值): {ma5[-1]:.2f}")
print(f"20日均线 (最后值): {ma20[-1]:.2f}")
print(f"60日均线 (最后值): {ma60[-1]:.2f}")

# 金叉/死叉信号
ma5_short = moving_average(prices[:-5], 5)[-20:]
ma20_short = moving_average(prices[:-5], 20)[-20:]
crosses = np.diff(np.sign(ma5_short - ma20_short))
golden_crosses = np.where(crosses > 0)[0]
death_crosses = np.where(crosses < 0)[0]
print(f"金叉次数: {len(golden_crosses)}")
print(f"死叉次数: {len(death_crosses)}")

# ─── 5. 波动率分析 ────────────────────────────────────
print("\n【5】波动率分析")

# 年化波动率（假设 252 个交易日）
annual_volatility = np.std(returns) * np.sqrt(252) * 100
print(f"年化波动率: {annual_volatility:.2f}%")

# 30日滚动波动率
rolling_vol = np.std(returns[-30:]) * np.sqrt(252) * 100
print(f"最近30日年化波动率: {rolling_vol:.2f}%")

# 最大回撤
cummax = np.maximum.accumulate(prices)
drawdown = (cummax - prices) / cummax * 100
max_drawdown = np.max(drawdown)
max_dd_idx = np.argmax(drawdown)
print(f"最大回撤: {max_drawdown:.2f}% (在第{max_dd_idx}天达到)")

# ─── 6. 收益分布 ──────────────────────────────────────
print("\n【6】收益分布")

# 将收益分成 10 个区间
hist, bin_edges = np.histogram(returns_pct, bins=10)
print("收益分布直方图:")
for i in range(len(hist)):
    bar = "█" * (hist[i] // 2)
    print(f"  [{bin_edges[i]:6.2f}%, {bin_edges[i+1]:6.2f}%): {bar} ({hist[i]})")

# ─── 7. 相关性分析（模拟两只股票） ─────────────────────
print("\n【7】相关性分析（模拟两只股票）")

# 第二只股票（与第一只有一定相关性）
prices_b = initial_price * np.cumprod(1 + daily_returns * 0.8 + np.random.normal(0, 0.01, n_days))
returns_b = np.diff(prices_b) / prices_b[:-1]

# 计算相关系数
correlation = np.corrcoef(returns, returns_b)[0, 1]
print(f"两只股票收益率相关系数: {correlation:.4f}")

# ─── 8. 生成报告 ──────────────────────────────────────
print("\n" + "=" * 60)
print("📊 股票分析报告")
print("=" * 60)
print(f"""
股票代码:   FAKE-001
分析区间:   {dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}
交易天数:   {n_days}

价格统计:
  最高价:   {max_price:.2f} ({dates[max_day_idx].strftime('%m/%d')})
  最低价:   {min_price:.2f} ({dates[min_day_idx].strftime('%m/%d')})
  平均价:   {avg_price:.2f}
  中位价:   {median_price:.2f}

收益统计:
  总收益率: {total_return:+.2f}%
  日均收益: {np.mean(returns_pct):+.4f}%
  年化波动: {annual_volatility:.2f}%
  最大回撤: {max_drawdown:.2f}%

交易统计:
  上涨天数: {up_days} ({up_days/n_days*100:.1f}%)
  下跌天数: {down_days} ({down_days/n_days*100:.1f}%)

均线信号:
  MA5:  {ma5[-1]:.2f}
  MA20: {ma20[-1]:.2f}
  MA60: {ma60[-1]:.2f}
""")

print("✅ 分析完成！")
print("=" * 60)
