"""
Day 104 - 数据可视化
03 - 实战案例：完整 EDA 报告（Titanic 数据探索性分析）

运行方式：python3 03-eda-report.py
输出文件：titanic_eda_report.png
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
sns.set_theme(style="whitegrid")

# ============================================================
# 1. 加载并预处理数据
# ============================================================
print("🚢 Loading Titanic dataset...")
titanic = sns.load_dataset('titanic')

# 用中位数填充年龄缺失值
median_age = titanic['age'].median()
titanic['age'] = titanic['age'].fillna(median_age)

# 创建年龄段
titanic['age_group'] = pd.cut(titanic['age'], bins=[0, 12, 18, 35, 55, 80],
                               labels=['Child', 'Teen', 'Young', 'Middle', 'Senior'])

# 创建家庭规模
titanic['family_size'] = titanic['sibsp'] + titanic['parch'] + 1

print(f"✅ 数据集形状: {titanic.shape}")
print(f"✅ 缺失值处理: age 列用中位数 {median_age} 填充")

# ============================================================
# 2. 生成 6 子图 EDA 报告
# ============================================================
print("\n📊 Generating EDA report...")

fig = plt.figure(figsize=(18, 14))
fig.suptitle('🚢 Titanic Survival Analysis - EDA Report',
             fontsize=18, fontweight='bold', y=0.98)

# --- 图1: 总体生存率 ---
ax1 = fig.add_subplot(3, 3, 1)
survival_counts = titanic['survived'].value_counts()
colors = ['#e74c3c', '#2ecc71']
wedges, texts, autotexts = ax1.pie(
    survival_counts,
    labels=['Died', 'Survived'],
    autopct='%1.1f%%',
    colors=colors,
    startangle=90,
    explode=(0, 0.05),
    textprops={'fontsize': 11}
)
ax1.set_title('Overall Survival Rate', fontsize=13, fontweight='bold')

# --- 图2: 性别 vs 生存率 ---
ax2 = fig.add_subplot(3, 3, 2)
sex_survival = titanic.groupby('sex')['survived'].mean() * 100
bars = ax2.bar(sex_survival.index, sex_survival.values,
               color=['#3498db', '#e91e63'], edgecolor='black')
for bar, val in zip(bars, sex_survival.values):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
             f'{val:.1f}%', ha='center', fontweight='bold', fontsize=12)
ax2.set_title('Survival Rate by Gender', fontsize=13, fontweight='bold')
ax2.set_ylabel('Survival Rate (%)')
ax2.set_ylim(0, 100)

# --- 图3: 船舱等级 vs 生存率 ---
ax3 = fig.add_subplot(3, 3, 3)
class_survival = titanic.groupby('class')['survived'].mean() * 100
colors_class = ['#f39c12', '#3498db', '#e74c3c']
bars = ax3.bar(class_survival.index, class_survival.values,
               color=colors_class, edgecolor='black')
for bar, val in zip(bars, class_survival.values):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
             f'{val:.1f}%', ha='center', fontweight='bold', fontsize=12)
ax3.set_title('Survival Rate by Class', fontsize=13, fontweight='bold')
ax3.set_ylabel('Survival Rate (%)')
ax3.set_ylim(0, 100)

# --- 图4: 年龄分布（分组） ---
ax4 = fig.add_subplot(3, 3, 4)
age_survival = titanic.groupby(['age_group', 'survived']).size().unstack(fill_value=0)
age_survival.plot(kind='bar', stacked=True, ax=ax4, color=colors, edgecolor='black')
ax4.set_title('Survival by Age Group', fontsize=13, fontweight='bold')
ax4.set_xlabel('Age Group')
ax4.set_ylabel('Count')
ax4.legend(['Died', 'Survived'], loc='upper left')
ax4.tick_params(axis='x', rotation=0)

# --- 图5: 票价分布 vs 生存 ---
ax5 = fig.add_subplot(3, 3, 5)
sns.histplot(data=titanic, x='fare', hue='survived', kde=True,
             palette={0: '#e74c3c', 1: '#2ecc71'}, ax=ax5, bins=30, alpha=0.6)
ax5.set_title('Fare Distribution by Survival', fontsize=13, fontweight='bold')
ax5.set_xlabel('Fare ($)')
ax5.set_xlim(0, 300)

# --- 图6: 相关性热力图 ---
ax6 = fig.add_subplot(3, 3, 6)
features = ['survived', 'pclass', 'age', 'sibsp', 'parch', 'fare', 'family_size']
corr_matrix = titanic[features].corr()
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='RdYlBu_r',
            center=0, fmt='.2f', linewidths=0.5, ax=ax6, cbar_kws={'shrink': 0.8})
ax6.set_title('Feature Correlation', fontsize=13, fontweight='bold')

# --- 图7: 登船港口 ---
ax7 = fig.add_subplot(3, 3, 7)
embarked_survival = titanic.groupby('embarked')['survived'].mean() * 100
bars = ax7.bar(embarked_survival.index, embarked_survival.values,
               color=['#9b59b6', '#1abc9c', '#e67e22'], edgecolor='black')
for bar, val in zip(bars, embarked_survival.values):
    ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
             f'{val:.1f}%', ha='center', fontweight='bold')
ax7.set_title('Survival by Embarkation', fontsize=13, fontweight='bold')
ax7.set_ylabel('Survival Rate (%)')

# --- 图8: 家庭规模 ---
ax8 = fig.add_subplot(3, 3, 8)
family_survival = titanic.groupby('family_size')['survived'].mean() * 100
ax8.plot(family_survival.index, family_survival.values, marker='o',
         linewidth=2, markersize=8, color='#2c3e50')
ax8.fill_between(family_survival.index, family_survival.values, alpha=0.2, color='#3498db')
ax8.set_title('Survival by Family Size', fontsize=13, fontweight='bold')
ax8.set_xlabel('Family Size')
ax8.set_ylabel('Survival Rate (%)')
ax8.set_xticks(range(1, titanic['family_size'].max() + 1))
ax8.grid(True, alpha=0.3)

# --- 图9: 关键发现文本 ---
ax9 = fig.add_subplot(3, 3, 9)
ax9.axis('off')
findings = """
🔑 KEY FINDINGS

1. Gender: Women survived at
   74.2% vs Men at 18.9%

2. Class: 1st class had 63%
   survival vs 3rd class 24%

3. Age: Children (0-12) had
   higher survival rates

4. Fare: Higher fare = higher
   survival probability

5. Family: Size 2-4 had best
   survival, solo had worst
"""
ax9.text(0.05, 0.95, findings, transform=ax9.transAxes,
         fontsize=11, verticalalignment='top',
         fontfamily='monospace',
         bbox=dict(boxstyle='round,pad=0.8', facecolor='lightyellow',
                   edgecolor='orange', alpha=0.9))

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('titanic_eda_report.png', dpi=150, bbox_inches='tight')
print("✅ titanic_eda_report.png saved")

# ============================================================
# 3. 输出分析摘要
# ============================================================
print("\n" + "=" * 50)
print("📋 ANALYSIS SUMMARY")
print("=" * 50)
print(f"Total passengers: {len(titanic)}")
print(f"Overall survival rate: {titanic['survived'].mean()*100:.1f}%")
print(f"\nBy Gender:")
print(titanic.groupby('sex')['survived'].mean().map(lambda x: f"{x*100:.1f}%"))
print(f"\nBy Class:")
print(titanic.groupby('class')['survived'].mean().map(lambda x: f"{x*100:.1f}%"))
print(f"\nBy Age Group:")
print(titanic.groupby('age_group')['survived'].mean().map(lambda x: f"{x*100:.1f}%"))
print("\n🎉 EDA Report Complete!")
