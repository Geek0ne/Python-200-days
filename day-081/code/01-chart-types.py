#!/usr/bin/env python3
"""
Day 081 - 基础用法：Matplotlib 图表类型大全
演示折线图、柱状图、散点图、饼图、箱线图等核心图表
"""

import matplotlib.pyplot as plt
import numpy as np

# ============ 设置中文显示 ============
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============ 1. 折线图 ============
print("1. 绘制折线图...")
x = np.linspace(0, 10, 100)
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# 折线图
axes[0, 0].plot(x, np.sin(x), label='sin(x)', color='#2196F3', linewidth=2)
axes[0, 0].plot(x, np.cos(x), label='cos(x)', color='#FF5722', linewidth=2, linestyle='--')
axes[0, 0].set_title('折线图：三角函数', fontsize=12)
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# ============ 2. 柱状图 ============
print("2. 绘制柱状图...")
categories = ['Python', 'Java', 'Go', 'Rust', 'JS']
values = [45, 25, 15, 10, 5]
colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336']
bars = axes[0, 1].bar(categories, values, color=colors)
for bar, val in zip(bars, values):
    axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    str(val) + '%', ha='center', va='bottom', fontweight='bold')
axes[0, 1].set_title('柱状图：语言占比', fontsize=12)

# ============ 3. 散点图 ============
print("3. 绘制散点图...")
np.random.seed(42)
x_scatter = np.random.randn(50)
y_scatter = 2 * x_scatter + np.random.randn(50) * 0.5
colors_scatter = np.random.rand(50)
sizes_scatter = np.random.rand(50) * 200 + 20
scatter = axes[0, 2].scatter(x_scatter, y_scatter, c=colors_scatter,
                              s=sizes_scatter, alpha=0.7, cmap='viridis')
plt.colorbar(scatter, ax=axes[0, 2], label='颜色值')
axes[0, 2].set_title('散点图：相关性分析', fontsize=12)

# ============ 4. 饼图 ============
print("4. 绘制饼图...")
labels_pie = ['Python', 'Java', 'Go', 'Rust', '其他']
sizes_pie = [45, 25, 15, 10, 5]
explode = (0.05, 0, 0, 0, 0)
axes[1, 0].pie(sizes_pie, labels=labels_pie, colors=colors[:5],
               explode=explode, autopct='%1.1f%%', shadow=True, startangle=90)
axes[1, 0].set_title('饼图：语言分布', fontsize=12)

# ============ 5. 箱线图 ============
print("5. 绘制箱线图...")
np.random.seed(42)
data_box = [np.random.normal(0, std, 100) for std in range(1, 5)]
bp = axes[1, 1].boxplot(data_box, labels=['组A', '组B', '组C', '组D'],
                         patch_artist=True, notch=True)
box_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
for patch, color in zip(bp['boxes'], box_colors):
    patch.set_facecolor(color)
axes[1, 1].set_title('箱线图：数据分布', fontsize=12)

# ============ 6. 热力图 ============
print("6. 绘制热力图...")
data_heatmap = np.random.rand(8, 8)
im = axes[1, 2].imshow(data_heatmap, cmap='YlOrRd', aspect='auto')
plt.colorbar(im, ax=axes[1, 2])
axes[1, 2].set_title('热力图：相关矩阵', fontsize=12)

plt.suptitle('Day 081 — Matplotlib 图表类型大全', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig('chart_types.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ 图表类型大全已生成")
