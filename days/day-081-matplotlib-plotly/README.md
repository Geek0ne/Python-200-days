# Day 081 — Matplotlib 与 Plotly 数据可视化

## 📋 今日目标
掌握 Matplotlib 和 Plotly 两大可视化库，能够创建从基础图表到交互式仪表盘的完整可视化方案。

---

## 一、Matplotlib 基础

### 1.1 什么是 Matplotlib？
Matplotlib 是 Python 最经典的 2D 绘图库，提供类似 MATLAB 的绘图接口。几乎所有 Python 数据可视化工具（Seaborn、Plotly 内部）都基于或兼容 Matplotlib。

### 1.2 架构原理
```
┌─────────────────────────────────────────────┐
│                  用户代码                     │
├─────────────────────────────────────────────┤
│           pyplot (MATLAB 风格接口)           │
├─────────────────────────────────────────────┤
│        Axes (坐标轴对象，核心绘图容器)         │
├─────────────────────────────────────────────┤
│       Figure (画布，管理所有 Axes)            │
├─────────────────────────────────────────────┤
│      Backend (渲染后端：Agg/PDF/SVG...)       │
└─────────────────────────────────────────────┘
```

**核心概念：**
- **Figure**：整个画布，可以包含多个子图
- **Axes**：每个子图/图表区域，绑定了 x/y 轴、标题、图例等
- **Axis**：坐标轴对象，控制刻度、标签、范围
- **Artist**：所有可见元素（线条、文字、矩形等）

### 1.3 两种编程风格

```python
# 面向对象风格（推荐，更灵活）
fig, ax = plt.subplots()
ax.plot(x, y)

# pyplot 脚本风格（简单快速）
plt.plot(x, y)
plt.show()
```

---

## 二、Matplotlib 核心图表类型

### 2.1 折线图 — 趋势展示
```python
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
fig, ax = plt.subplots()
ax.plot(x, np.sin(x), label='sin(x)', color='#2196F3', linewidth=2)
ax.plot(x, np.cos(x), label='cos(x)', color='#FF5722', linewidth=2, linestyle='--')
ax.set_xlabel('X 轴')
ax.set_ylabel('Y 轴')
ax.set_title('三角函数')
ax.legend()
ax.grid(True, alpha=0.3)
plt.show()
```

### 2.2 柱状图 — 对比展示
```python
categories = ['A', 'B', 'C', 'D', 'E']
values = [23, 45, 56, 78, 32]

fig, ax = plt.subplots()
bars = ax.bar(categories, values, color=['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336'])
# 在柱子上方显示数值
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            str(val), ha='center', va='bottom', fontweight='bold')
ax.set_title('分类对比')
plt.show()
```

### 2.3 散点图 — 相关性分析
```python
np.random.seed(42)
x = np.random.randn(100)
y = 2 * x + np.random.randn(100) * 0.5
colors = np.random.rand(100)
sizes = np.random.rand(100) * 200

fig, ax = plt.subplots()
scatter = ax.scatter(x, y, c=colors, s=sizes, alpha=0.6, cmap='viridis')
plt.colorbar(scatter, label='颜色值')
ax.set_title('散点图：相关性分析')
plt.show()
```

### 2.4 饼图与环形图 — 占比展示
```python
labels = ['Python', 'Java', 'Go', 'Rust', '其他']
sizes = [45, 25, 15, 10, 5]
colors = ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0', '#FFC107']
explode = (0.05, 0, 0, 0, 0)  # 突出第一块

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.pie(sizes, labels=labels, colors=colors, explode=explode,
        autopct='%1.1f%%', shadow=True, startangle=90)
ax1.set_title('饼图')

# 环形图（用 wedges 实现）
wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90, pctdistance=0.85)
# 画中间的白色圆
centre_circle = plt.Circle((0, 0), 0.60, fc='white')
ax2.add_artist(centre_circle)
ax2.set_title('环形图')
plt.show()
```

### 2.5 箱线图 — 分布展示
```python
np.random.seed(42)
data = [np.random.normal(0, std, 100) for std in range(1, 5)]

fig, ax = plt.subplots()
bp = ax.boxplot(data, labels=['组A', '组B', '组C', '组D'],
                patch_artist=True, notch=True)
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
ax.set_title('箱线图：数据分布')
plt.show()
```

### 2.6 热力图 — 矩阵展示
```python
np.random.seed(42)
data = np.random.rand(10, 10)
fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(data, cmap='YlOrRd', aspect='auto')
plt.colorbar(im)
ax.set_xticks(range(10))
ax.set_yticks(range(10))
ax.set_title('热力图')
plt.show()
```

---

## 三、子图布局

### 3.1 subplot 布局
```python
# 2x2 网格
fig, axes = plt.subplots(2, 2, figsize=(10, 8))

axes[0, 0].plot([1, 2, 3], [1, 4, 9])
axes[0, 0].set_title('平方')

axes[0, 1].bar(['a', 'b', 'c'], [3, 7, 2])
axes[0, 1].set_title('柱状图')

axes[1, 0].scatter([1, 2, 3, 4], [4, 3, 2, 1])
axes[1, 0].set_title('散点图')

axes[1, 1].pie([30, 20, 50], labels=['A', 'B', 'C'])
axes[1, 1].set_title('饼图')

plt.tight_layout()
plt.show()
```

### 3.2 GridSpec 复杂布局
```python
import matplotlib.gridspec as gridspec

fig = plt.figure(figsize=(12, 8))
gs = gridspec.GridSpec(2, 3, figure=fig)

# 大图占 2 行
ax_main = fig.add_subplot(gs[:, 0:2])
ax_main.plot(np.linspace(0, 10, 100), np.sin(np.linspace(0, 10, 100)))
ax_main.set_title('主图')

# 右侧两个小图
ax_right1 = fig.add_subplot(gs[0, 2])
ax_right1.bar(['A', 'B', 'C'], [1, 2, 3])

ax_right2 = fig.add_subplot(gs[1, 2])
ax_right2.pie([40, 60], labels=['Yes', 'No'])

plt.tight_layout()
plt.show()
```

---

## 四、样式与美化

### 4.1 内置样式
```python
# 查看所有可用样式
print(plt.style.available)

# 使用样式
plt.style.use('seaborn-v0_8')   # seaborn 风格
plt.style.use('ggplot')         # ggplot 风格
plt.style.use('dark_background') # 暗色主题

# 临时使用
with plt.style.context('seaborn-v0_8'):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    plt.show()
```

### 4.2 自定义样式表
创建 `my_style.mplstyle` 文件：
```ini
axes.prop_cycle: cycler('color', ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0'])
axes.grid: True
grid.alpha: 0.3
axes.spines.top: False
axes.spines.right: False
figure.figsize: 12, 6
font.size: 12
```
```python
plt.style.use('./my_style.mplstyle')
```

### 4.3 中文显示
```python
# 方法1：指定字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 方法2：使用 font_manager
from matplotlib import font_manager
font_path = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
prop = font_manager.FontProperties(fname=font_path)
ax.set_title('中文标题', fontproperties=prop)
```

---

## 五、Plotly 交互式可视化

### 5.1 Plotly 简介
Plotly 是基于 JavaScript 的交互式可视化库，生成的图表支持：
- 鼠标悬停显示详情
- 缩放、平移、选择
- 动态切换图例
- 导出为 PNG/SVG

### 5.2 Plotly 基础图表

```python
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 折线图
fig = px.line(x=[1, 2, 3, 4], y=[10, 20, 15, 30],
              title='折线图', labels={'x': 'X', 'y': 'Y'})
fig.show()

# 散点图（带 hover 信息）
df = px.data.iris()
fig = px.scatter(df, x='sepal_width', y='sepal_length',
                 color='species', size='petal_length',
                 hover_data=['petal_width'],
                 title='鸢尾花数据')
fig.show()

# 柱状图
fig = px.bar(x=['A', 'B', 'C', 'D'], y=[23, 45, 56, 78],
             color=['A', 'B', 'C', 'D'], title='柱状图')
fig.show()

# 热力图
import numpy as np
z = np.random.rand(10, 10)
fig = px.imshow(z, title='热力图', color_continuous_scale='Viridis')
fig.show()
```

### 5.3 子图

```python
from plotly.subplots import make_subplots
import plotly.graph_objects as go

fig = make_subplots(rows=2, cols=2,
                    subplot_titles=('折线图', '柱状图', '散点图', '饼图'))

fig.add_trace(go.Scatter(x=[1,2,3], y=[1,4,9], name='折线'), row=1, col=1)
fig.add_trace(go.Bar(x=['A','B','C'], y=[3,7,2], name='柱'), row=1, col=2)
fig.add_trace(go.Scatter(x=[1,2,3,4], y=[4,3,2,1], mode='markers', name='散点'), row=2, col=1)
fig.add_trace(go.Pie(labels=['A','B','C'], values=[30,20,50], name='饼'), row=2, col=2)

fig.update_layout(height=600, showlegend=False)
fig.show()
```

### 5.4 动画

```python
import plotly.express as px

df = px.data.gapminder()
fig = px.scatter(df, x="gdpPercap", y="lifeExp",
                 animation_frame="year", animation_group="country",
                 size="pop", color="continent", hover_name="country",
                 log_x=True, size_max=55,
                 range_x=[100, 100000], range_y=[25, 90])
fig.show()
```

---

## 六、Matplotlib vs Plotly 对比

| 特性 | Matplotlib | Plotly |
|------|-----------|--------|
| 交互性 | 静态（需 mpld3） | 原生交互 |
| 输出格式 | PNG/PDF/SVG | HTML/图片 |
| 学习曲线 | 较陡 | 平缓 |
| 生态整合 | Seaborn/Pandas | Dash/Streamlit |
| 适合场景 | 论文/报告 | Web 应用/仪表盘 |
| 文件大小 | 小 | 大（含 JS） |
| 自定义程度 | 极高 | 中等 |

---

## 七、实战：股票数据可视化仪表盘

```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 生成模拟股票数据
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=252)
close = 100 + np.cumsum(np.random.randn(252) * 2)
volume = np.random.randint(1000000, 5000000, 252)

df = pd.DataFrame({'date': dates, 'close': close, 'volume': volume})

# 创建 2x2 仪表盘
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

# 1. 股价走势
ax1 = fig.add_subplot(gs[0, :])  # 跨两列
ax1.plot(df['date'], df['close'], color='#2196F3', linewidth=1.5)
ax1.fill_between(df['date'], df['close'].min(), df['close'],
                 alpha=0.2, color='#2196F3')
# 20 日均线
ma20 = df['close'].rolling(20).mean()
ax1.plot(df['date'], ma20, color='#FF5722', linewidth=1, linestyle='--', label='MA20')
ax1.set_title('股价走势', fontsize=14, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. 日收益率分布
returns = df['close'].pct_change().dropna() * 100
ax2 = fig.add_subplot(gs[1, 0])
ax2.hist(returns, bins=50, color='#4CAF50', edgecolor='white', alpha=0.8)
ax2.axvline(returns.mean(), color='red', linestyle='--', label=f'均值: {returns.mean():.2f}%')
ax2.set_title('日收益率分布')
ax2.legend()

# 3. 成交量柱状图
ax3 = fig.add_subplot(gs[1, 1])
colors = ['#4CAF50' if df['close'].iloc[i] >= df['close'].iloc[i-1] else '#F44336'
          for i in range(1, len(df))]
ax3.bar(df['date'][1:], df['volume'][1:], color=colors, width=1)
ax3.set_title('成交量（红跌绿涨）')

plt.suptitle('📊 股票数据分析仪表盘', fontsize=16, fontweight='bold', y=1.02)
plt.savefig('stock_dashboard.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

## 八、思考题

1. **为什么 Matplotlib 选择 Figure → Axes → Artist 的三层架构？** 这种设计有什么优势？
2. **Plotly 的动画系统（animation_frame）底层是如何工作的？** 它与 Matplotlib 的 FuncAnimation 有什么区别？
3. **在生产环境中，你会选择哪种方式存储可视化结果？** PNG/PDF（Matplotlib）vs HTML（Plotly），各有什么取舍？
4. **如何为大量时间序列数据创建高效的可视化？** 提示：考虑降采样、LOD（Level of Detail）策略。
5. **Seaborn 与 Matplotlib 的关系是什么？** Seaborn 做了哪些 Matplotlib 做不到的事情？
