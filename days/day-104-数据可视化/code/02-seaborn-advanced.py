"""
Day 104 - 数据可视化
02 - Seaborn 统计图表：boxplot / violin / heatmap / pairplot

运行方式：python3 02-seaborn-advanced.py
输出文件：seaborn_boxplot.png, seaborn_heatmap.png, seaborn_pairplot.png
"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# ============================================================
# 中文字体配置
# ============================================================
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 使用 Seaborn 默认主题（更美观）
sns.set_theme(style="whitegrid", palette="muted")

# ============================================================
# 1. Boxplot — Tips 数据集：性别 × 星期 × 消费金额
# ============================================================
print("📊 绘制箱线图...")
tips = sns.load_dataset('tips')

fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(data=tips, x='day', y='total_bill', hue='sex',
            palette='Set2', linewidth=1.2, ax=ax)

# 标注每个箱线图的中位数
medians = tips.groupby(['day', 'sex'])['total_bill'].median()
for i, day in enumerate(['Thur', 'Fri', 'Sat', 'Sun']):
    for j, sex in enumerate(['Male', 'Female']):
        med = medians.loc[(day, sex)]
        ax.text(i + (j - 0.5) * 0.25, med + 0.5, f'{med:.0f}',
                ha='center', va='bottom', fontsize=9, color='red')

ax.set_title('Total Bill by Day and Gender', fontsize=14, fontweight='bold')
ax.set_xlabel('Day of Week')
ax.set_ylabel('Total Bill ($)')
ax.legend(title='Gender')
plt.tight_layout()
plt.savefig('seaborn_boxplot.png', dpi=150)
print("✅ seaborn_boxplot.png saved")
plt.close()

# ============================================================
# 2. Heatmap — 特征相关性矩阵
# ============================================================
print("\n📊 绘制热力图...")

# 加载 iris 数据集
iris = sns.load_dataset('iris')
numeric_cols = iris.select_dtypes(include=[np.number])
corr = numeric_cols.corr()

fig, ax = plt.subplots(figsize=(8, 6))
mask = np.triu(np.ones_like(corr, dtype=bool))  # 上三角遮罩

sns.heatmap(corr, mask=mask, annot=True, cmap='coolwarm', center=0,
            fmt='.2f', linewidths=0.8, square=True,
            cbar_kws={'shrink': 0.8}, ax=ax)

ax.set_title('Iris Feature Correlation Matrix', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('seaborn_heatmap.png', dpi=100)
print("✅ seaborn_heatmap.png saved")
plt.close()

# ============================================================
# 3. Pairplot — 多变量关系（散点矩阵 + 分布）
# ============================================================
print("\n📊 绘制 pairplot...")

g = sns.pairplot(iris, hue='species', palette='husl',
                 diag_kind='kde',  # 对角线用 KDE 密度图
                 plot_kws={'alpha': 0.6, 's': 40},
                 diag_kws={'linewidth': 2})
g.figure.suptitle('Iris Feature Relationships', y=1.02, fontsize=14, fontweight='bold')
plt.savefig('seaborn_pairplot.png', dpi=100, bbox_inches='tight')
print("✅ seaborn_pairplot.png saved")
plt.close()

# ============================================================
# 4. Violin Plot — 分布形状（split=True 比较两组）
# ============================================================
print("\n📊 绘制小提琴图...")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 左图：基础 violin
sns.violinplot(data=tips, x='day', y='total_bill', palette='Set3',
               inner='quartile', ax=axes[0])  # inner='quartile' 显示四分位线
axes[0].set_title('Violin Plot (Basic)', fontsize=13, fontweight='bold')

# 右图：split violin（按性别拆分）
sns.violinplot(data=tips, x='day', y='total_bill', hue='sex',
               split=True, palette='muted', inner='box', ax=axes[1])
axes[1].set_title('Split Violin (by Gender)', fontsize=13, fontweight='bold')

plt.tight_layout()
plt.savefig('seaborn_violin.png', dpi=100)
print("✅ seaborn_violin.png saved")
plt.close()

print("\n🎉 All Seaborn charts generated!")
