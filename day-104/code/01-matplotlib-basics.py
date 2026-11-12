"""
Day 104 - 数据可视化
01 - Matplotlib 基础图表：折线图、柱状图、散点图

运行方式：python3 01-matplotlib-basics.py
输出文件：line_chart.png, bar_chart.png, scatter_chart.png
"""
import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# 中文字体配置（避免中文显示为方块）
# ============================================================
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# ============================================================
# 1. 折线图 — 展示月度营收趋势
# ============================================================
print("📊 绘制折线图...")

months = np.arange(1, 13)
revenue_2023 = [120, 135, 148, 162, 155, 170, 185, 200, 192, 210, 225, 240]
revenue_2024 = [130, 150, 165, 175, 168, 190, 210, 230, 220, 245, 260, 280]

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(months, revenue_2023, marker='o', linewidth=2, label='2023', color='#3498db')
ax.plot(months, revenue_2024, marker='s', linewidth=2, label='2024', color='#e74c3c')

# 填充两线之间的区域
ax.fill_between(months, revenue_2023, revenue_2024, alpha=0.15, color='green')

ax.set_title('Monthly Revenue Trend', fontsize=14, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('Revenue (10K)')
ax.set_xticks(months)
ax.set_xticklabels([f'M{i}' for i in months])
ax.legend(loc='upper left', fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('line_chart.png', dpi=150)
print("✅ line_chart.png saved")
plt.close()

# ============================================================
# 2. 柱状图 — 编程语言流行度对比
# ============================================================
print("\n📊 绘制柱状图...")

languages = ['Python', 'Java', 'JavaScript', 'C/C++', 'Go', 'Rust']
popularity = [28.5, 17.2, 13.8, 12.1, 8.5, 6.3]
colors = ['#3776AB', '#F89820', '#F7DF1E', '#00599C', '#00ADD8', '#DEA584']

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(languages, popularity, color=colors, edgecolor='black', linewidth=0.5)

# 在柱子上方标注数值
for bar, val in zip(bars, popularity):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
            f'{val}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.set_title('Programming Language Popularity (TIOBE 2024)', fontsize=14, fontweight='bold')
ax.set_ylabel('Market Share (%)')
ax.set_ylim(0, 35)
ax.grid(True, axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('bar_chart.png', dpi=150)
print("✅ bar_chart.png saved")
plt.close()

# ============================================================
# 3. 散点图 — 学习时长 vs 考试成绩（带趋势线）
# ============================================================
print("\n📊 绘制散点图...")

np.random.seed(42)
study_hours = np.random.uniform(1, 10, 50)
scores = study_hours * 8.5 + np.random.normal(0, 4, 50)  # 线性关系 + 噪声

fig, ax = plt.subplots(figsize=(9, 7))
scatter = ax.scatter(study_hours, scores, c=study_hours, cmap='coolwarm',
                     s=120, alpha=0.7, edgecolors='black', linewidth=0.5)

# 颜色条
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Study Hours', fontsize=11)

# 拟合趋势线（一次多项式）
z = np.polyfit(study_hours, scores, 1)
p = np.poly1d(z)
x_line = np.linspace(study_hours.min(), study_hours.max(), 100)
ax.plot(x_line, p(x_line), 'r--', linewidth=2, alpha=0.8,
        label=f'Trend: y={z[0]:.1f}x+{z[1]:.1f}')

# 计算相关系数
correlation = np.corrcoef(study_hours, scores)[0, 1]
ax.text(0.05, 0.92, f'r = {correlation:.3f}', transform=ax.transAxes,
        fontsize=12, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

ax.set_title('Study Hours vs Exam Score', fontsize=14, fontweight='bold')
ax.set_xlabel('Study Hours')
ax.set_ylabel('Exam Score')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('scatter_chart.png', dpi=150)
print("✅ scatter_chart.png saved")
plt.close()

print("\n🎉 All charts generated successfully!")
