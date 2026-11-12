# Day 104 — 数据可视化

> 📅 日期：Day 104 / 200 | 🏷️ 阶段：Phase 7 — 进阶与性能优化 | 📌 子主题：实战

---

## 目录

1. [概念总览](#1-概念总览)
2. [Matplotlib 深入](#2-matplotlib-深入)
3. [Seaborn 数据可视化](#3-seaborn-数据可视化)
4. [图表类型速查](#4-图表类型速查)
5. [数据探索性分析报告实战](#5-数据探索性分析报告实战)
6. [思考题](#6-思考题)

---

## 1. 概念总览

### 1.1 为什么需要数据可视化？

数据可视化是将数据转化为图形/图表的过程。人类大脑处理图像的速度比文字快 **60,000 倍**，可视化能帮助我们：

- **快速发现数据模式**：趋势、异常值、分布特征
- **沟通分析结果**：让非技术人员也能理解
- **验证假设**：用视觉方式检验数据是否符合预期
- **讲故事**：数据 + 叙事 = 有力的说服

### 1.2 Python 可视化生态

```
┌─────────────────────────────────────────────┐
│              Python 可视化生态              │
├─────────────────────────────────────────────┤
│                                             │
│  基础层：Matplotlib（最底层、最灵活）       │
│    ├── Seaborn（统计图表，基于 Matplotlib）  │
│    ├── Pandas .plot()（快速绑定 DataFrame） │
│    └── Axes 级别定制                        │
│                                             │
│  交互层：Plotly / Bokeh（Web 交互式图表）   │
│                                             │
│  专用层：                                    │
│    ├── Folium（地理地图）                   │
│    ├── NetworkX（网络图）                   │
│    └── WordCloud（词云）                    │
│                                             │
└─────────────────────────────────────────────┘
```

### 1.3 Matplotlib vs Seaborn vs Plotly

| 特性 | Matplotlib | Seaborn | Plotly |
|------|-----------|---------|--------|
| **定位** | 底层引擎 | 统计可视化 | 交互式可视化 |
| **学习曲线** | 陡峭 | 平缓 | 中等 |
| **定制性** | 极高 | 中等 | 中等 |
| **交互性** | ❌ | ❌ | ✅ |
| **适合场景** | 论文/报告 | EDA 分析 | Web 展示 |
| **依赖** | 无 | Matplotlib | 无 |

---

## 2. Matplotlib 深入

### 2.1 Figure 与 Axes 架构

Matplotlib 的核心是 **双层对象模型**：

```
Figure（画布）
 └── Axes（子图/坐标系）—— 我们实际绑图的地方
      ├── xaxis（X 轴）
      └── yaxis（Y 轴）
```

**两种创建方式对比：**

| 方式 | 语法 | 适用场景 |
|------|------|---------|
| 面向对象（推荐） | `fig, ax = plt.subplots()` | 复杂图形、多子图 |
| pyplot 接口 | `plt.plot()` | 快速绘图、简单场景 |

### 2.2 常用图表类型

#### 2.2.1 折线图 — 趋势分析

```python
import matplotlib.pyplot as plt
import numpy as np

x = np.arange(1, 13)
revenue = [120, 135, 148, 162, 155, 170, 185, 200, 192, 210, 225, 240]

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x, revenue, marker='o', linewidth=2, label='月度营收')
ax.set_title('2024 年月度营收趋势', fontsize=14, fontweight='bold')
ax.set_xlabel('月份')
ax.set_ylabel('营收（万元）')
ax.set_xticks(x)
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('line_chart.png', dpi=150)
```

#### 2.2.2 柱状图 — 分类对比

```python
categories = ['Python', 'Java', 'JavaScript', 'Go', 'Rust']
popularity = [30.5, 18.2, 15.8, 10.5, 8.3]

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(categories, popularity, color=['#3776AB', '#F89820', '#F7DF1E', '#00ADD8', '#DEA584'])
ax.set_title('编程语言流行度（TIOBE 2024）', fontsize=13)
ax.set_ylabel('市场份额 (%)')

# 在柱子上方标注数值
for bar, val in zip(bars, popularity):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{val}%', ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig('bar_chart.png', dpi=150)
```

#### 2.2.3 散点图 — 相关性分析

```python
import numpy as np

np.random.seed(42)
study_hours = np.random.uniform(1, 10, 50)
scores = study_hours * 8 + np.random.normal(0, 5, 50)
colors = np.random.choice(['red', 'blue', 'green'], 50)

fig, ax = plt.subplots(figsize=(8, 6))
scatter = ax.scatter(study_hours, scores, c=study_hours, cmap='coolwarm',
                     s=100, alpha=0.7, edgecolors='black')
plt.colorbar(scatter, label='学习时长')
ax.set_title('学习时长 vs 考试成绩', fontsize=13)
ax.set_xlabel('学习时长（小时）')
ax.set_ylabel('考试成绩')

# 添加趋势线
z = np.polyfit(study_hours, scores, 1)
p = np.poly1d(z)
ax.plot(sorted(study_hours), p(sorted(study_hours)), 'r--', alpha=0.8, label='趋势线')
ax.legend()
plt.tight_layout()
plt.savefig('scatter_chart.png', dpi=150)
```

#### 2.2.4 饼图 — 占比分析

```python
labels = ['产品 A', '产品 B', '产品 C', '产品 D', '其他']
sizes = [35, 25, 20, 12, 8]
colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0']
explode = (0.05, 0, 0, 0, 0)  # 突出第一块

fig, ax = plt.subplots(figsize=(8, 6))
wedges, texts, autotexts = ax.pie(
    sizes, explode=explode, labels=labels, colors=colors,
    autopct='%1.1f%%', shadow=True, startangle=90
)
ax.set_title('产品市场份额', fontsize=13)
plt.tight_layout()
plt.savefig('pie_chart.png', dpi=150)
```

#### 2.2.5 直方图 — 分布分析

```python
data = np.random.normal(170, 10, 1000)  # 身高数据

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(data, bins=30, edgecolor='black', alpha=0.7, color='steelblue')
ax.axvline(data.mean(), color='red', linestyle='--', linewidth=2, label=f'均值={data.mean():.1f}')
ax.axvline(data.median(), color='green', linestyle='-.', linewidth=2, label=f'中位数={np.median(data):.1f}')
ax.set_title('成年男性身高分布', fontsize=13)
ax.set_xlabel('身高（cm）')
ax.set_ylabel('频数')
ax.legend()
plt.tight_layout()
plt.savefig('histogram_chart.png', dpi=150)
```

#### 2.2.6 箱线图 — 异常值检测

```python
data_groups = [np.random.normal(loc, 5, 200) for loc in [160, 170, 175]]

fig, ax = plt.subplots(figsize=(8, 5))
bp = ax.boxplot(data_groups, labels=['女性', '男性（年轻）', '男性（年长）'],
                patch_artist=True, notch=True)
colors_box = ['#FFB6C1', '#87CEEB', '#98FB98']
for patch, color in zip(bp['boxes'], colors_box):
    patch.set_facecolor(color)
ax.set_title('不同群体身高分布', fontsize=13)
ax.set_ylabel('身高（cm）')
ax.grid(True, axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('boxplot_chart.png', dpi=150)
```

### 2.3 多子图布局

```python
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
# axes 是 2x3 的 ndarray，axes[0,0] 到 axes[1,2]

axes[0, 0].plot([1, 2, 3], [1, 4, 9])
axes[0, 0].set_title('子图 1')

# ... 为每个子图绑图

plt.tight_layout()
plt.savefig('subplots.png', dpi=150)
```

**布局技巧：**

| 方法 | 用途 |
|------|------|
| `plt.subplots(nrows, ncols)` | 规则网格 |
| `fig.add_subplot(211)` | 灵活添加 |
| `GridSpec` | 不规则布局 |
| `plt.tight_layout()` | 自动调整间距 |
| `constrained_layout=True` | 更好的布局控制 |

### 2.4 样式与美化

```python
# 查看可用样式
print(plt.style.available)

# 使用预设样式
plt.style.use('seaborn-v0_8')  # 或 'ggplot', 'dark_background' 等

# 全局字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
```

---

## 3. Seaborn 数据可视化

### 3.1 Seaborn 核心优势

Seaborn 是 Matplotlib 的上层封装，专门用于**统计可视化**：

- **默认美观**：自动应用主题，无需手动美化
- **数据绑定**：直接绑定 DataFrame，无需手动提取列
- **内置统计**：自动计算均值、置信区间等
- **分面绘图**：轻松创建分组对比图

### 3.2 统计图表

#### 3.2.1 Boxplot — 分布与异常值

```python
import seaborn as sns
import pandas as pd

tips = sns.load_dataset('tips')

fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(data=tips, x='day', y='total_bill', hue='sex', palette='Set2', ax=ax)
ax.set_title('不同日期的消费分布', fontsize=13)
plt.tight_layout()
plt.savefig('seaborn_boxplot.png', dpi=150)
```

#### 3.2.2 Violin Plot — 分布形状

```python
fig, ax = plt.subplots(figsize=(10, 6))
sns.violinplot(data=tips, x='day', y='total_bill', hue='sex',
               split=True, palette='muted', ax=ax)
ax.set_title('消费分布（小提琴图）', fontsize=13)
plt.tight_layout()
plt.savefig('seaborn_violin.png', dpi=150)
```

#### 3.2.3 Heatmap — 相关性矩阵

```python
fig, ax = plt.subplots(figsize=(8, 6))
corr = tips[['total_bill', 'tip', 'size']].corr()
sns.heatmap(corr, annot=True, cmap='coolwarm', center=0,
            fmt='.2f', linewidths=0.5, ax=ax)
ax.set_title('数值特征相关性矩阵', fontsize=13)
plt.tight_layout()
plt.savefig('seaborn_heatmap.png', dpi=150)
```

#### 3.2.4 Pairplot — 多变量关系

```python
iris = sns.load_dataset('iris')
sns.pairplot(iris, hue='species', palette='husl', diag_kind='kde')
plt.suptitle('鸢尾花特征关系矩阵', y=1.02, fontsize=13)
plt.savefig('seaborn_pairplot.png', dpi=150)
```

#### 3.2.5 Countplot — 分类计数

```python
fig, ax = plt.subplots(figsize=(8, 5))
sns.countplot(data=tips, x='day', hue='time', palette='pastel', ax=ax)
ax.set_title('不同日期的用餐次数', fontsize=13)
plt.tight_layout()
plt.savefig('seaborn_countplot.png', dpi=150)
```

#### 3.2.6 Regression Plot — 回归趋势

```python
fig, ax = plt.subplots(figsize=(8, 6))
sns.regplot(data=tips, x='total_bill', y='tip', scatter_kws={'alpha': 0.5}, ax=ax)
ax.set_title('消费金额 vs 小费', fontsize=13)
plt.tight_layout()
plt.savefig('seaborn_regplot.png', dpi=150)
```

### 3.3 Seaborn 图表选择指南

```
你想展示什么？
│
├── 分布 → histplot / kdeplot / displot
├── 分类对比 → barplot / countplot / boxplot
├── 关系 → scatterplot / lineplot / regplot
├── 多变量 → pairplot / heatmap
└── 分面 → FacetGrid / catplot / relplot
```

---

## 4. 图表类型速查

| 场景 | 推荐图表 | Matplotlib | Seaborn |
|------|---------|-----------|---------|
| 趋势变化 | 折线图 | `ax.plot()` | `sns.lineplot()` |
| 分类对比 | 柱状图 | `ax.bar()` | `sns.barplot()` |
| 占比构成 | 饼图 | `ax.pie()` | — |
| 数据分布 | 直方图 | `ax.hist()` | `sns.histplot()` |
| 分布形状 | 箱线图 | `ax.boxplot()` | `sns.boxplot()` |
| 相关性 | 散点图 | `ax.scatter()` | `sns.scatterplot()` |
| 热力图 | 相关矩阵 | `ax.imshow()` | `sns.heatmap()` |
| 多变量 | 散点矩阵 | — | `sns.pairplot()` |
| 时间序列 | 折线图 | `ax.plot()` | `sns.lineplot()` |

---

## 5. 数据探索性分析报告实战

下面是一个完整的 EDA（探索性分析）工作流：

```python
"""
完整 EDA 流程：使用 Titanic 数据集
"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# ========== 1. 加载数据 ==========
titanic = sns.load_dataset('titanic')

# ========== 2. 基本信息 ==========
print("=" * 50)
print("📊 数据集概览")
print("=" * 50)
print(f"形状: {titanic.shape}")
print(f"\n数据类型:\n{titanic.dtypes}")
print(f"\n缺失值:\n{titanic.isnull().sum()}")
print(f"\n基本统计:\n{titanic.describe()}")

# ========== 3. 可视化分析 ==========
plt.style.use('seaborn-v0_8')
fig = plt.figure(figsize=(16, 14))

# 图1: 生存率分布
ax1 = fig.add_subplot(3, 2, 1)
survival = titanic['survived'].value_counts()
ax1.pie(survival, labels=['遇难', '存活'], autopct='%1.1f%%',
        colors=['#ff6b6b', '#51cf66'], startangle=90)
ax1.set_title('生存率分布')

# 图2: 性别与生存率
ax2 = fig.add_subplot(3, 2, 2)
sns.countplot(data=titanic, x='sex', hue='survived', palette='Set2', ax=ax2)
ax2.set_title('性别与生存率')
ax2.legend(['遇难', '存活'])

# 图3: 船舱等级与生存率
ax3 = fig.add_subplot(3, 2, 3)
sns.countplot(data=titanic, x='class', hue='survived', palette='coolwarm', ax=ax3)
ax3.set_title('船舱等级与生存率')
ax3.legend(['遇难', '存活'])

# 图4: 年龄分布
ax4 = fig.add_subplot(3, 2, 4)
sns.histplot(data=titanic, x='age', hue='survived', kde=True,
             palette='RdYlGn', ax=ax4, bins=30)
ax4.set_title('年龄分布与生存率')

# 图5: 船票价格分布
ax5 = fig.add_subplot(3, 2, 5)
sns.boxplot(data=titanic, x='class', y='fare', hue='survived',
            palette='Set3', ax=ax5)
ax5.set_title('船票价格与生存率')

# 图6: 登船港口
ax6 = fig.add_subplot(3, 2, 6)
sns.countplot(data=titanic, x='embarked', hue='survived', palette='muted', ax=ax6)
ax6.set_title('登船港口与生存率')

plt.suptitle('🚢 Titanic 数据探索性分析报告', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('titanic_eda_report.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 6. 思考题

### 🤔 思考题

1. **为什么折线图通常比柱状图更适合展示时间序列数据？** 柱状图在什么情况下可以用作时间序列？

**参考答案**

折线图用「点 + 连线」强调**连续变化的趋势与方向**——线的斜率直观告诉读者「在涨还是在跌、变化快不快」，而且时间点很多时（如 365 天）依然清爽。柱状图每根柱子是独立的矩形，强调的是**单个时间点的量值大小**，点一多就挤成一片「栅栏」，趋势反而被淹没。

从视觉编码看：折线把注意力引向「相邻点之间的关系」（变化），柱状把注意力引向「每根柱子的高度」（绝对量）。时间序列分析通常关心前者，所以折线更合适。

**柱状图适合的时间序列场景**：
- 时间点**少且离散**，重点是比较各期数值，如「四个季度的营收对比」。
- 强调**每期独立总量**而非连续走势，如「每月新增用户数」。
- 需要突出**正负对比**（柱子在零轴上下），如「每月净利润盈亏」。

💡 提示：即便用柱状图展示时间，也应保持时间顺序排列、等宽等距，不要随意排序，否则会破坏时间语义。

2. **箱线图中的"须"（whiskers）代表什么？** 超出须范围的点一定是异常值吗？如何调整异常值判定标准？

**参考答案**

箱体本身是 **Q1（25%分位）到 Q3（75%分位）**，中间的线是中位数。**须**默认从箱体两端延伸到「1.5 倍 IQR 范围内的最远数据点」，其中 IQR = Q3 - Q1（四分位距，即中间 50% 数据的跨度）。须外的点被单独画成圆点，标记为「疑似异常值」。

**超出须的点不一定是真异常值**：1.5×IQR 只是一个经验约定（约对应正态分布的 ±2.7σ），在重尾分布（如收入、房价）里，很多完全合理的极端值也会被标出来。它只是「统计上偏离主体」，是否真异常要结合业务判断。

**调整判定标准**：
- Matplotlib `ax.boxplot(data, whis=3.0)`：把倍数从默认 1.5 改成 3，须更长、标出的点更少；`whis=(5,95)` 则直接用百分位定须。
- Seaborn `sns.boxplot(..., whis=3.0)` 同理。
- 也可改用 Z-score、IQR 自定义阈值或业务规则来判定，而非依赖默认倍数。

⚠️ 注意：箱线图假设数据大致单峰；多峰分布时箱体可能误导，配合小提琴图/直方图看形状更稳妥。

3. **热力图中的颜色映射（colormap）选择有什么讲究？** `coolwarm` 和 `viridis` 分别适合什么场景？

**参考答案**

选 colormap 的核心是**匹配数据的语义**，并保证「感知均匀」（颜色变化幅度与人眼感受到的数值变化成正比，不误导）。

- **`coolwarm`（发散型 diverging）**：蓝—白—红，有一个**中性中点**。适合「有正负、有中心基准」的数据，最典型是**相关系数矩阵**（-1 蓝、0 白、+1 红），配合 `center=0` 让零点对齐白色，一眼看出正相关/负相关。也适合温差、盈亏等。
- **`viridis`（顺序型 sequential）**：紫—绿—黄，单调递增、感知均匀、对色盲友好。适合「从低到高、无负值」的数据，如人口密度、销售额、概率值。它不会像 jet/rainbow 那样制造虚假的边界。

讲究总结：**有中心基准用发散型（coolwarm/RdBu），单调量值用顺序型（viridis/magma），分类用定性型（tab10）**；避免用 jet 这类感知不均匀的彩虹色。

💡 提示：相关矩阵务必 `center=0` 并设 `vmin=-1, vmax=1`，否则不同图之间颜色不可比；发表论文优先选色盲友好的 viridis 系。

4. **当你有 10 个以上分类变量需要对比时，柱状图会变得拥挤。** 你会如何处理？列出至少 3 种方案。

**参考答案**

至少三种方案：

1. **改用水平柱状图 `barh`**：分类标签横排放在左侧，纵向空间充裕，10~30 个类别也能从容显示长标签，是最省事的改造。
2. **Top-N + 其他**：按数值排序，只展示前 8~10 名，其余合并成「其他」一类。突出主要矛盾，避免长尾噪声（电商品类、城市销售常用）。
3. **分面（faceting）拆图**：用 `sns.catplot(col=...)` 或 `plt.subplots` 按某个维度把类别拆成多个小图，每图只放几个类别，化整为零。

其他可选：
- **换图型**：类别多且要看占比 → 树状图（treemap）；要看两个维度交叉 → 热力图。
- **交互化**：用 Plotly 做可缩放/悬停的图，或加滚动条。
- **降维分组**：先把细类别聚成大类（如把几十个城市归到「华东/华南…」），再对比。

💡 提示：无论哪种，先排序再画（按值降序）能大幅提升可读性；饼图在类别 >5 时几乎不可读，应避免。

5. **Seaborn 的 `pairplot` 在特征数量超过 10 时会变得非常慢且难以阅读。** 在实际项目中你会如何优化这个过程？

**参考答案**

pairplot 会画 n×n 个子图，特征一多就是「组合爆炸」（10 个特征 = 100 格，20 个 = 400 格），既慢又看不清。优化思路：

1. **先筛特征再画**：用相关性热力图、方差阈值、或模型特征重要性挑出最相关的 5~8 个，再 `sns.pairplot(df[cols])`。或用 `vars=[...]` 只指定关心的列。
2. **采样数据**：`df.sample(2000)` 取子集画散点，几万行降到几千行，速度大幅提升且分布形状基本不变。
3. **只画一半 / 换对角线**：`corner=True` 去掉重复的上三角；`diag_kind='kde'` 或 `'hist'` 让对角线更轻量。
4. **分而治之**：按业务把特征分组，分别画几张小 pairplot；或改用 `sns.PairGrid` 自定义每格图型（上三角放相关系数、下三角放散点）。
5. **换工具**：高维探索用降维（PCA/t-SNE/UMAP）降到 2~3 维再散点，或用 Plotly 的交互式散点矩阵按需查看。

核心原则：**pairplot 是「少量关键特征」的探索工具，不是高维数据的通用方案**——先降维/筛选，再可视化。

⚠️ 注意：采样会丢失稀有类别/异常点，若目标是找异常值，采样要谨慎或保留全量但减少特征数。

---

## 📚 延伸阅读

- [Matplotlib 官方图库](https://matplotlib.org/stable/gallery/)
- [Seaborn 示例库](https://seaborn.pydata.org/examples/)
- [Python 数据可视化最佳实践](https://clauswilke.com/dataviz/)
- [Python Graph Gallery](https://www.python-graph-gallery.com/)

---

## 附录：Matplotlib API 速查表

| 方法 | 功能 | 常用参数 |
|------|------|----------|
| `plt.subplots()` | 创建画布+子图 | `nrows, ncols, figsize, dpi` |
| `ax.plot()` | 折线图 | `marker, linewidth, label, color` |
| `ax.bar()` | 柱状图 | `color, edgecolor, width` |
| `ax.barh()` | 水平柱状图 | `height, color, edgecolor` |
| `ax.scatter()` | 散点图 | `c, cmap, s, alpha, edgecolors` |
| `ax.hist()` | 直方图 | `bins, edgecolor, alpha, density` |
| `ax.boxplot()` | 箱线图 | `patch_artist, notch, labels` |
| `ax.pie()` | 饼图 | `labels, autopct, explode, colors` |
| `ax.imshow()` | 热力图 | `cmap, aspect, interpolation` |
| `ax.text()` | 添加文本 | `x, y, s, fontsize, ha, va` |
| `ax.legend()` | 图例 | `loc, fontsize, title` |
| `ax.grid()` | 网格线 | `alpha, linestyle, which` |
| `ax.set_title()` | 标题 | `fontsize, fontweight, pad` |
| `ax.set_xlabel()` | X 轴标签 | `fontsize, labelpad` |
| `ax.set_ylabel()` | Y 轴标签 | `fontsize, labelpad` |
| `ax.set_xticks()` | X 轴刻度 | `ticks, labels` |
| `ax.set_xlim()` | X 轴范围 | `left, right` |
| `ax.set_ylim()` | Y 轴范围 | `bottom, top` |
| `plt.tight_layout()` | 自动调整布局 | `pad, h_pad, w_pad` |
| `plt.savefig()` | 保存图片 | `dpi, bbox_inches, facecolor` |
| `plt.close()` | 关闭画布 | — |

## 附录：Seaborn API 速查表

| 方法 | 功能 | 常用参数 |
|------|------|----------|
| `sns.histplot()` | 直方图 | `data, x, hue, kde, bins` |
| `sns.kdeplot()` | 密度图 | `data, x, hue, fill, shade` |
| `sns.boxplot()` | 箱线图 | `data, x, y, hue, palette` |
| `sns.violinplot()` | 小提琴图 | `data, x, y, hue, split, inner` |
| `sns.barplot()` | 柱状图 | `data, x, y, hue, ci` |
| `sns.countplot()` | 计数图 | `data, x, hue, order` |
| `sns.stripplot()` | 散点图 | `data, x, y, hue, jitter` |
| `sns.swarmplot()` | 蜂群图 | `data, x, y, hue, size` |
| `sns.scatterplot()` | 散点图 | `data, x, y, hue, style, size` |
| `sns.lineplot()` | 折线图 | `data, x, y, hue, style` |
| `sns.regplot()` | 回归图 | `data, x, y, scatter_kws` |
| `sns.heatmap()` | 热力图 | `data, annot, cmap, center, fmt` |
| `sns.pairplot()` | 散点矩阵 | `data, hue, diag_kind, palette` |
| `sns.catplot()` | 分类图 | `data, x, y, hue, kind, col` |
| `sns.set_theme()` | 全局主题 | `style, palette, font_scale` |

## 附录：图表选择决策指南

| 你想回答的问题 | 推荐图表 | 示例场景 |
|---------------|---------|----------|
| 某指标随时间如何变化？ | 折线图 | 月度销售额趋势 |
| 不同类别之间如何对比？ | 柱状图 | 产品销量对比 |
| 各部分占总体的比例？ | 饼图 | 市场份额分布 |
| 数据的分布形状？ | 直方图 | 用户年龄分布 |
| 是否存在异常值？ | 箱线图 | 测试成绩异常检测 |
| 两变量之间有关系吗？ | 散点图 | 广告投入 vs 收入 |
| 哪些特征高度相关？ | 热力图 | 特征相关性分析 |
| 多个变量之间的关系？ | pairplot | 多维数据探索 |
| 分组数据的分布对比？ | violin/box | 不同实验组效果 |
| 分类变量的计数？ | countplot | 各状态工单数量 |

**选图口诀：**
- 看趋势 → 折线
- 看对比 → 柱状
- 看构成 → 饼/环
- 看分布 → 直方/密度
- 看关系 → 散点/热力
- 看异常 → 箱线
