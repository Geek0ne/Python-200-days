#!/usr/bin/env python3
"""
Day 081 - 实战案例：股票数据分析仪表盘
使用 Matplotlib 创建完整的多面板可视化仪表盘
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ============ 生成模拟股票数据 ============
print("📊 生成模拟股票数据...")
np.random.seed(42)
days = 252  # 一年交易日
dates = pd.date_range('2024-01-01', periods=days, freq='B')

# 模拟股价（随机游走）
returns = np.random.randn(days) * 0.02
close = 100 * np.exp(np.cumsum(returns))
open_price = close * (1 + np.random.randn(days) * 0.005)
high = np.maximum(close, open_price) * (1 + np.abs(np.random.randn(days) * 0.01))
low = np.minimum(close, open_price) * (1 - np.abs(np.random.randn(days) * 0.01))
volume = np.random.randint(500000, 3000000, days)

df = pd.DataFrame({
    'date': dates, 'open': open_price, 'high': high,
    'low': low, 'close': close, 'volume': volume
})

# ============ 计算技术指标 ============
df['ma5'] = df['close'].rolling(5).mean()
df['ma20'] = df['close'].rolling(20).mean()
df['ma60'] = df['close'].rolling(60).mean()
df['daily_return'] = df['close'].pct_change()
df['volatility_20'] = df['daily_return'].rolling(20).std() * np.sqrt(252) * 100

# ============ 创建仪表盘 ============
print("🎨 创建可视化仪表盘...")
fig = plt.figure(figsize=(18, 12), facecolor='#1a1a2e')
gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.35, wspace=0.3,
                       left=0.06, right=0.94, top=0.92, bottom=0.06)

# 通用样式
title_style = {'fontsize': 11, 'fontweight': 'bold', 'color': '#e0e0e0'}
label_style = {'fontsize': 9, 'color': '#aaaaaa'}

# ============ 面板1：股价走势（跨4列） ============
ax_price = fig.add_subplot(gs[0, :])
ax_price.set_facecolor('#16213e')

ax_price.plot(df['date'], df['close'], color='#00d4ff', linewidth=1.5, label='收盘价')
ax_price.plot(df['date'], df['ma5'], color='#ff6b6b', linewidth=1, alpha=0.8, label='MA5')
ax_price.plot(df['date'], df['ma20'], color='#ffd93d', linewidth=1, alpha=0.8, label='MA20')
ax_price.plot(df['date'], df['ma60'], color='#6bcb77', linewidth=1, alpha=0.8, label='MA60')
ax_price.fill_between(df['date'], df['close'].min() * 0.98, df['close'], alpha=0.1, color='#00d4ff')

ax_price.set_title('📈 股价走势 — A股某科技公司', **title_style)
ax_price.set_ylabel('价格', **label_style)
ax_price.legend(loc='upper left', fontsize=9, facecolor='#16213e', edgecolor='#333')
ax_price.tick_params(colors='#aaaaaa')
ax_price.grid(True, alpha=0.15, color='#333')
ax_price.spines[:].set_color('#333')

# 标注关键点
max_idx = df['close'].idxmax()
min_idx = df['close'].idxmin()
ax_price.annotate(f'最高: {df["close"].iloc[max_idx]:.2f}',
                  xy=(df['date'].iloc[max_idx], df['close'].iloc[max_idx]),
                  xytext=(10, 15), textcoords='offset points',
                  color='#ff6b6b', fontsize=9,
                  arrowprops=dict(arrowstyle='->', color='#ff6b6b'))

# ============ 面板2：成交量 ============
ax_vol = fig.add_subplot(gs[1, :2])
ax_vol.set_facecolor('#16213e')

colors_vol = ['#4CAF50' if df['close'].iloc[i] >= df['close'].iloc[i-1] else '#F44336'
              for i in range(1, len(df))]
colors_vol.insert(0, '#4CAF50')
ax_vol.bar(df['date'], df['volume'], color=colors_vol, width=1.5, alpha=0.7)
ax_vol.set_title('📊 成交量', **title_style)
ax_vol.set_ylabel('成交量', **label_style)
ax_vol.tick_params(colors='#aaaaaa')
ax_vol.grid(True, alpha=0.15, color='#333')
ax_vol.spines[:].set_color('#333')

# ============ 面板3：收益率分布 ============
ax_ret = fig.add_subplot(gs[1, 2:])
ax_ret.set_facecolor('#16213e')

returns_pct = df['daily_return'].dropna() * 100
n, bins, patches = ax_ret.hist(returns_pct, bins=60, color='#4CAF50', edgecolor='#1a1a2e', alpha=0.8)
ax_ret.axvline(returns_pct.mean(), color='#ff6b6b', linestyle='--', linewidth=1.5,
               label=f'均值: {returns_pct.mean():.3f}%')
ax_ret.axvline(0, color='#ffd93d', linestyle='-', linewidth=1, alpha=0.5)
ax_ret.set_title('📈 日收益率分布', **title_style)
ax_ret.set_xlabel('收益率 (%)', **label_style)
ax_ret.set_ylabel('频次', **label_style)
ax_ret.legend(fontsize=9, facecolor='#16213e', edgecolor='#333')
ax_ret.tick_params(colors='#aaaaaa')
ax_ret.grid(True, alpha=0.15, color='#333')
ax_ret.spines[:].set_color('#333')

# ============ 面板4：波动率趋势 ============
ax_vol_trend = fig.add_subplot(gs[2, :2])
ax_vol_trend.set_facecolor('#16213e')

ax_vol_trend.fill_between(df['date'], 0, df['volatility_20'], alpha=0.3, color='#ff6b6b')
ax_vol_trend.plot(df['date'], df['volatility_20'], color='#ff6b6b', linewidth=1.5)
ax_vol_trend.set_title('📉 20日年化波动率', **title_style)
ax_vol_trend.set_ylabel('波动率 (%)', **label_style)
ax_vol_trend.tick_params(colors='#aaaaaa')
ax_vol_trend.grid(True, alpha=0.15, color='#333')
ax_vol_trend.spines[:].set_color('#333')

# ============ 面板5：关键指标卡片 ============
ax_info = fig.add_subplot(gs[2, 2:])
ax_info.set_facecolor('#16213e')
ax_info.axis('off')

# 统计指标
total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
max_drawdown = ((df['close'] / df['close'].cummax()) - 1).min() * 100
sharpe = returns_pct.mean() / returns_pct.std() * np.sqrt(252)
win_days = (df['daily_return'].dropna() > 0).sum()
lose_days = (df['daily_return'].dropna() < 0).sum()

metrics = [
    ('总收益率', f'{total_return:+.2f}%', '#4CAF50' if total_return > 0 else '#F44336'),
    ('最大回撤', f'{max_drawdown:.2f}%', '#F44336'),
    ('夏普比率', f'{sharpe:.2f}', '#00d4ff'),
    ('当前价格', f'{df["close"].iloc[-1]:.2f}', '#ffd93d'),
    ('平均成交量', f'{df["volume"].mean():,.0f}', '#e0e0e0'),
    ('上涨天数', f'{win_days} 天 ({win_days/len(df)*100:.1f}%)', '#4CAF50'),
    ('下跌天数', f'{lose_days} 天 ({lose_days/len(df)*100:.1f}%)', '#F44336'),
]

ax_info.set_title('📋 关键指标', **title_style)
for i, (name, value, color) in enumerate(metrics):
    y_pos = 0.88 - i * 0.12
    ax_info.text(0.05, y_pos, name, transform=ax_info.transAxes,
                 fontsize=10, color='#aaaaaa', va='center')
    ax_info.text(0.95, y_pos, value, transform=ax_info.transAxes,
                 fontsize=12, fontweight='bold', color=color,
                 ha='right', va='center')

# 分隔线
for i in range(len(metrics)):
    y_pos = 0.88 - i * 0.12
    ax_info.axhline(y=y_pos - 0.04, xmin=0.05, xmax=0.95,
                    color='#333', linewidth=0.5)

plt.suptitle('📊 股票数据分析仪表盘 — 2024年度报告',
             fontsize=18, fontweight='bold', color='#ffffff', y=0.97)
plt.savefig('stock_dashboard.png', dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
plt.show()
print("✅ 股票仪表盘已生成: stock_dashboard.png")
print(f"\n📋 关键数据:")
print(f"  总收益率: {total_return:+.2f}%")
print(f"  最大回撤: {max_drawdown:.2f}%")
print(f"  夏普比率: {sharpe:.2f}")
print(f"  当前价格: {df['close'].iloc[-1]:.2f}")
