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

**参考答案**

这是典型的**关注点分离**：每一层只管一件事。

- **Figure（画布）**：管"整张图"——尺寸、背景、包含哪些子图、最终导出成什么文件。
- **Axes（绘图区）**：管"一个带坐标系的图表"——数据到图形的映射、标题、图例、坐标轴范围。一个 Figure 可以放多个 Axes。
- **Artist（图元）**：所有可见元素的基类——线条、文字、矩形、刻度都是 Artist 的子类，统一实现 `draw()` 接口。

这样设计的优势：

1. **组合灵活**：子图数量、布局（GridSpec）随意拼，互不干扰。
2. **后端无关**：Artist 只描述"画什么"，具体"怎么画"交给后端（Agg 画 PNG、PDF/SVG 后端画矢量）——同一份代码换后端就能输出不同格式。
3. **细粒度控制**：任何元素都是对象，拿到就能改属性（颜色、字号、位置），不用推倒重来。
4. **易扩展**：自定义图表只需实现一个 Artist 子类，自动融入整个体系。

小例子（已验证，Agg 无界面后端）：

```python
import matplotlib
matplotlib.use("Agg")  # 无界面后端，不弹窗
import matplotlib.pyplot as plt
from matplotlib.artist import Artist

fig, axes = plt.subplots(1, 2)   # 一个 Figure 里放两个 Axes
axes[0].plot([1, 2, 3], [1, 4, 9])
line = axes[0].get_lines()[0]    # 每条线是一个 Artist
title = axes[0].set_title("示例")

print("fig 是:", type(fig).__name__)
print("axes[0] 是:", type(axes[0]).__name__)
print("line 是:", type(line).__name__)
print("title 是:", type(title).__name__)
print("Line2D 是 Artist 子类:", isinstance(line, Artist))
print("Text 是 Artist 子类:", isinstance(title, Artist))
plt.close(fig)
```

预期输出：

```
fig 是: Figure
axes[0] 是: Axes
line 是: Line2D
title 是: Text
Line2D 是 Artist 子类: True
Text 是 Artist 子类: True
```

💡 提示：日常推荐"面向对象风格"（`fig, ax = plt.subplots()` 然后 `ax.plot(...)`），就是在显式操作这三层；`plt.plot()` 脚本风格只是帮你隐式管理当前 Figure/Axes，图一复杂就容易乱。

2. **Plotly 的动画系统（animation_frame）底层是如何工作的？** 它与 Matplotlib 的 FuncAnimation 有什么区别？

**参考答案**

核心区别一句话：**Plotly 是"预先算好所有帧、打包成数据交给浏览器播放"，Matplotlib 的 FuncAnimation 是"运行时反复回调 Python 函数、一帧一帧现画"。**

Plotly 的 `animation_frame` 底层流程：

1. 你指定按哪一列分组（比如 `year`），Plotly 在**导出时就把每一帧的数据、坐标、样式全部算好**，存进 `fig.frames`（一个 `Frame` 对象列表）。
2. `fig.to_html()` / `write_html()` 把这些帧连同播放按钮、滑块一起**序列化成 JSON**，内嵌进 HTML。
3. 浏览器里的 **plotly.js** 读取 JSON，靠 JS 定时器在帧之间切换、做补间过渡——**播放阶段完全不需要 Python**。

Matplotlib 的 `FuncAnimation(fig, update, frames=N)`：

- 你提供一个 `update(frame_index)` 回调，动画播放时**每一帧都要回到 Python 执行这个函数**，重新设置 Artist 数据再重绘。
- 它依赖一个活着的 GUI 事件循环（或存成 GIF/MP4 时逐帧渲染），**离开 Python 进程就动不起来**。

小例子（已验证，用 Plotly 内置数据，无需联网）：

```python
import plotly.express as px

df = px.data.gapminder()   # 内置示例数据，无需联网
fig = px.scatter(df, x="gdpPercap", y="lifeExp",
                 animation_frame="year", animation_group="country",
                 size="pop", color="continent", hover_name="country")
print("动画帧数:", len(fig.frames))
print("数据中的年份数:", df["year"].nunique())
print("每一帧的类型:", type(fig.frames[0]).__name__)
```

预期输出：

```
动画帧数: 12
数据中的年份数: 12
每一帧的类型: Frame
```

可以看到：帧数正好等于年份数，说明每个 `year` 都被**提前展开成一个独立的 Frame**，这就是"预计算"的证据。

💡 提示：因此 Plotly 动画适合做成**可分享的交互网页/仪表盘**（对方没装 Python 也能看、能拖动滑块）；FuncAnimation 适合**科学计算里边算边看**或导出成视频，帧内容依赖复杂实时计算时更灵活。

3. **在生产环境中，你会选择哪种方式存储可视化结果？** PNG/PDF（Matplotlib）vs HTML（Plotly），各有什么取舍？

**参考答案**

没有绝对的赢家，**按"给谁看、要不要交互、存在哪"来选**。可以这样对比：

| 维度 | PNG（位图） | PDF/SVG（矢量） | HTML（Plotly） |
|---|---|---|---|
| 交互 | 无，纯静态 | 无（PDF 可缩放） | 有：悬停、缩放、动画、筛选 |
| 体积 | 小～中 | 小 | 大（内嵌数据+JS，常几百 KB 起） |
| 清晰度 | 放大会糊，看 DPI | 无限缩放不糊 | 矢量渲染，任意缩放清晰 |
| 通用性 | 任何地方都能贴（邮件/PPT/微信） | 打印、论文、报告首选 | 需浏览器，离线也能开 |
| 生成成本 | 快、依赖少 | 快 | 需打包数据，重数据时慢 |
| 可复现 | 只是像素，数据丢了 | 同左 | 数据内嵌，可再提取 |

生产中的常见选择：

- **定时报表、邮件推送、大屏截图、聊天工具分享** → PNG（Matplotlib + Agg 后端），简单、体积小、哪都能显示。
- **论文、正式文档、需要印刷或无限放大** → PDF/SVG 矢量。
- **交互式仪表盘、给业务方自助探索、需要动画/悬停看明细** → HTML（Plotly），或直接托管到 Dash/Web 服务。
- **海量数据的图** → 优先矢量或"降采样后的 PNG"，别把百万点原样塞进 HTML（会卡爆浏览器，见第 4 题）。

💡 提示：很多团队是**组合用**——后台 Matplotlib 批量出 PNG 存档/发报表，前端 Plotly 出 HTML 供交互探索。另外 HTML 内嵌了原始数据，**分享前注意脱敏**，别把敏感明细一起发出去。

4. **如何为大量时间序列数据创建高效的可视化？** 提示：考虑降采样、LOD（Level of Detail）策略。

**参考答案**

关键认知：**屏幕横向就几千个像素，画一百万个点纯属浪费**——大部分点落在同一像素列里，既看不出区别，又拖慢渲染、撑大文件。所以核心思路是"**只画看得出来的点**"。

常用手段：

1. **降采样（Downsampling）**：把海量点压缩成几千个代表点。
   - 简单等间隔抽样：快，但**会漏掉尖峰/异常**，危险。
   - **min-max 分桶**：把数据分成 N 桶，每桶只保留最小值和最大值——**尖峰一定不丢**，最适合监控曲线。
   - **LTTB（Largest-Triangle-Three-Buckets）**：在保留视觉形状的前提下选点，曲线更"像原图"，是很多图表库的默认算法。
2. **LOD（Level of Detail，细节层次）**：按当前缩放级别给不同精度的数据。
   - 看全年 → 用"按天/按小时聚合"的粗数据；放大到某一天 → 再加载分钟级原始数据。
   - 类似地图：缩得越远加载越粗的瓦片，放大才拉高清细节。
3. **聚合预计算**：入库时就算好 1 分钟/1 小时/1 天的均值、最值，查询直接取聚合表。
4. **渲染层优化**：用 WebGL（Plotly 的 `scattergl`）、矢量输出、服务端出图，避免把原始大数组塞进前端。

小例子（已验证，min-max 分桶降采样，尖峰不丢）：

```python
import numpy as np

np.random.seed(42)
n = 100_000
y = np.cumsum(np.random.randn(n))   # 模拟时间序列

def downsample_minmax(y, buckets=1000):
    """min-max 降采样：每桶保留最小值和最大值，尖峰不丢"""
    kept = []
    for bucket in np.array_split(y, buckets):
        kept.append(bucket.min())
        kept.append(bucket.max())
    return np.array(kept)

small = downsample_minmax(y, buckets=1000)
print("原始点数:", len(y))
print("降采样后:", len(small))
print("全局最大值保留:", np.isclose(small.max(), y.max()))
print("全局最小值保留:", np.isclose(small.min(), y.min()))
```

预期输出：

```
原始点数: 100000
降采样后: 2000
全局最大值保留: True
全局最小值保留: True
```

10 万点压到 2000 点（缩到 1/50），但**全局最高/最低点都还在**——这就是 min-max 相比"随便抽点"的价值：异常尖峰不会被抹掉。

💡 提示：降采样是"有损"的，务必按场景选算法——**监控/告警看异常用 min-max，看整体趋势用 LTTB**；需要精确数值时仍要回原始数据查询，别拿降采样后的图当数据源。

5. **Seaborn 与 Matplotlib 的关系是什么？** Seaborn 做了哪些 Matplotlib 做不到的事情？

**参考答案**

关系一句话：**Seaborn 是建立在 Matplotlib 之上的高层封装，不是替代品。** 它底层调用的还是 Matplotlib 的 Figure/Axes/Artist，画出来的每个元素仍然是 Matplotlib 对象，你可以继续用 `ax.set_title()` 之类去微调。

分工：

- **Matplotlib**：底层、通用、什么都能画，但要自己处理数据分组、配色、统计计算，代码啰嗦。
- **Seaborn**：面向**统计数据可视化**，把常见统计图型做成"一行搞定"，并自带更美观的默认主题和调色板。

Seaborn 帮你做了哪些"Matplotlib 要手写一大堆"的事（严格说不是"做不到"，而是"做起来很费劲"）：

1. **直接吃 DataFrame + 语义映射**：`sns.scatterplot(data=df, x="身高", y="体重", hue="性别", style="城市")`——按列自动分组、上色、换标记，Matplotlib 得自己循环分组。
2. **统计图型开箱即用**：`histplot`（带 KDE 核密度估计）、`boxplot`/`violinplot`（分布）、`regplot`（自动拟合回归线+置信区间）、`heatmap`（相关矩阵）等，统计计算内置。
3. **分面（Faceting）**：`FacetGrid` / `catplot` 按类别自动拆成多个子图网格，一句 `col=`/`row=` 就行。
4. **更漂亮的默认样式与调色板**：`set_theme()`、分类/连续/发散色板，默认就比 Matplotlib 好看，且对色盲友好。
5. **自动处理图例、置信区间、聚合**：少写很多样板代码。

一句话总结：**Matplotlib 给你"画笔和画布"，Seaborn 给你"统计图表模板"**；探索数据、画统计图用 Seaborn 更快更美，需要极致定制或特殊图型时再落到 Matplotlib。

💡 提示：因为 Seaborn 返回的就是 Matplotlib 的 Axes，两者可以无缝混用——先 `sns.xxx()` 画主体，再用返回的 `ax` 做 Matplotlib 级别的精修，是实践中最常见的组合。
