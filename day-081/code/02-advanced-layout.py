#!/usr/bin/env python3
"""
Day 081 - 进阶用法：子图布局与样式美化
演示 GridSpec 复杂布局、样式定制、中文支持
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

# ============ 1. GridSpec 复杂布局 ============
print("1. GridSpec 复杂布局...")
fig = plt.figure(figsize=(14, 10))
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.3)

# 大图占 2 行 2 列
ax_main = fig.add_subplot(gs[0:2, 0:2])
x = np.linspace(0, 10, 200)
ax_main.plot(x, np.sin(x) * np.exp(-x/5), color='#2196F3', linewidth=2)
ax_main.fill_between(x, 0, np.sin(x) * np.exp(-x/5), alpha=0.2, color='#2196F3')
ax_main.set_title('主图：衰减正弦波', fontsize=14, fontweight='bold')
ax_main.grid(True, alpha=0.3)

# 右上
ax_r1 = fig.add_subplot(gs[0, 2])
categories = ['A', 'B', 'C', 'D']
values = [23, 45, 56, 78]
ax_r1.barh(categories, values, color=['#4CAF50', '#2196F3', '#FF9800', '#9C27B0'])
ax_r1.set_title('水平柱状图', fontsize=12)

# 右中
ax_r2 = fig.add_subplot(gs[1, 2])
theta = np.linspace(0, 2*np.pi, 100)
ax_r2.plot(np.cos(theta), np.sin(theta), color='#FF5722', linewidth=2)
ax_r2.set_aspect('equal')
ax_r2.set_title('单位圆', fontsize=12)
ax_r2.grid(True, alpha=0.3)

# 左下
ax_bl = fig.add_subplot(gs[2, 0])
x_hist = np.random.randn(1000)
ax_bl.hist(x_hist, bins=50, color='#4CAF50', edgecolor='white', alpha=0.8)
ax_bl.set_title('正态分布直方图', fontsize=12)

# 中下
ax_bm = fig.add_subplot(gs[2, 1])
x_polar = np.linspace(0, 2*np.pi, 8)
for i in range(8):
    angle = np.linspace(0, 2*np.pi, 50)
    r = 1 + 0.5 * np.sin(3 * angle + i * np.pi/4)
    ax_bm.plot(r * np.cos(angle), r * np.sin(angle), alpha=0.7)
ax_bm.set_aspect('equal')
ax_bm.set_title('花瓣图案', fontsize=12)

# 右下
ax_br = fig.add_subplot(gs[2, 2])
sizes = [30, 20, 25, 15, 10]
labels = ['Python', 'Java', 'Go', 'Rust', 'JS']
ax_br.pie(sizes, labels=labels, autopct='%1.0f%%',
          colors=['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336'])
ax_br.set_title('环形图', fontsize=12)

plt.suptitle('Day 081 — GridSpec 复杂布局', fontsize=16, fontweight='bold')
plt.savefig('gridspec_layout.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ GridSpec 布局已生成")

# ============ 2. 样式对比 ============
print("\n2. 样式对比...")
styles = ['ggplot', 'seaborn-v0_8', 'dark_background', 'Solarized_Light2']
fig, axes = plt.subplots(1, 4, figsize=(16, 4))

np.random.seed(42)
x = np.linspace(0, 10, 50)

for ax, style in zip(axes, styles):
    try:
        with plt.style.context(style):
            ax.plot(x, np.sin(x) + x/10, linewidth=2)
            ax.fill_between(x, 0, np.sin(x) + x/10, alpha=0.3)
            ax.set_title(style, fontsize=11)
            ax.grid(True, alpha=0.3)
    except OSError:
        # 某些样式可能不可用
        ax.plot(x, np.sin(x), linewidth=2)
        ax.set_title(f'{style} (fallback)', fontsize=11)

plt.suptitle('Day 081 — 内置样式对比', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('style_comparison.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 样式对比已生成")

# ============ 3. 避坑：常见问题演示 ============
print("\n3. 常见避坑...")

# 坑1：坐标轴范围问题
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
x = np.linspace(0, 10, 100)
y = np.sin(x)

ax1.plot(x, y)
ax1.set_title('❌ 没设置坐标范围')
# 自动范围可能不好看

ax2.plot(x, y)
ax2.set_xlim(0, 10)
ax2.set_ylim(-1.2, 1.2)
ax2.set_title('✅ 手动设置坐标范围')

plt.tight_layout()
plt.savefig('pitfall_xlim.png', dpi=150, bbox_inches='tight')
plt.show()

# 坑2：颜色循环用完后重复
fig, ax = plt.subplots(figsize=(8, 5))
for i in range(15):
    ax.plot(np.random.randn(50).cumsum(), label=f'Line {i+1}')
ax.set_title('超过10条线时颜色会循环重复')
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
plt.tight_layout()
plt.savefig('pitfall_colors.png', dpi=150, bbox_inches='tight')
plt.show()

print("✅ 避坑演示已生成")
print("\n🎉 所有进阶用法演示完成！")
