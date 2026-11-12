# Day 124 — 时间序列预测

> 时间序列数据无处不在：股票价格、天气温度、网站流量、销售额。掌握时间序列分析是数据科学家的必备技能。

---

## 1. 时间序列基础

### 1.1 什么是时间序列

时间序列（Time Series）是按时间顺序排列的数据点序列。与普通数据不同，时间序列具有 **时序依赖性**——当前值与过去值相关。

```
时间序列数据示例 (每日销售额):
日期        销售额
2026-01-01   100
2026-01-02   120
2026-01-03   115
2026-01-04   130
2026-01-05   125
    ...
```

### 1.2 时间序列的组成成分

```
时间序列 = 趋势 + 季节性 + 周期性 + 残差

Y(t) = T(t) + S(t) + C(t) + ε(t)

┌─────────────────────────────────────────────────┐
│ 原始序列                                         │
│   /\    /\    /\    /\                           │
│  /  \  /  \  /  \  /  \                         │
│ /    \/    \/    \/    \                        │
│ ────────────────────────  ← 趋势 (上升)         │
├─────────────────────────────────────────────────┤
│ 趋势分量 T(t)                                    │
│              ╱                                  │
│           ╱                                     │
│        ╱                                        │
│     ╱                                           │
├─────────────────────────────────────────────────┤
│ 季节性分量 S(t)                                  │
│  /\    /\    /\    /\                           │
│ /  \  /  \  /  \  /  \                         │
│/    \/    \/    \/    \                        │
├─────────────────────────────────────────────────┤
│ 残差 ε(t)                                       │
│  ~  ~   ~  ~    ~   ~  ~                       │
└─────────────────────────────────────────────────┘
```

### 1.3 时间序列的类型

| 类型 | 特征 | 示例 |
|------|------|------|
| 平稳序列 | 均值、方差恒定 | 白噪声 |
| 非平稳序列 | 均值或方差变化 | 股票价格 |
| 有季节性 | 固定周期重复模式 | 冬装销量 |
| 有趋势 | 长期上升或下降 | GDP增长 |

---

## 2. 时间序列分解

### 2.1 加法分解

```
Y(t) = T(t) + S(t) + ε(t)

适用: 季节性波动幅度恒定
示例: 每年固定增加100台销量
```

### 2.2 乘法分解

```
Y(t) = T(t) × S(t) × ε(t)

适用: 季节性波动随趋势增大
示例: 每年销量翻倍，季节性波动也翻倍
```

### 2.3 使用 statsmodels 分解

```python
from statsmodels.tsa.seasonal import seasonal_decompose
import pandas as pd

# 加法分解
result_add = seasonal_decompose(series, model='additive', period=12)

# 乘法分解
result_mul = seasonal_decompose(series, model='multiplicative', period=12)

# 访问分量
trend = result_add.trend       # 趋势
seasonal = result_add.seasonal # 季节性
residual = result_add.resid    # 残差
```

---

## 3. 平稳性检验

### 3.1 什么是平稳性

平稳时间序列的统计特性（均值、方差、自相关）不随时间变化。

```
平稳序列:                    非平稳序列:
  ~~~~波动恒定~~~~             / 逐渐上升 \
  均值恒定                    均值在变化
  方差恒定                    方差可能变化
```

### 3.2 ADF 检验（Augmented Dickey-Fuller）

```python
from statsmodels.tsa.stattools import adfuller

result = adfuller(series)
print(f'ADF Statistic: {result[0]:.4f}')
print(f'p-value: {result[1]:.4f}')

# 判断:
# p-value < 0.05 → 序列平稳
# p-value >= 0.05 → 序列非平稳，需要差分
```

### 3.3 差分（Differencing）

差分是将非平稳序列转化为平稳序列的常用方法：

```
一阶差分: Δy(t) = y(t) - y(t-1)
二阶差分: Δ²y(t) = Δy(t) - Δy(t-1)

示例:
原始:    [100, 110, 105, 120, 115]
一阶差分: [ 10,  -5,  15,  -5]
二阶差分: [-15,  20, -20]
```

---

## 4. ARIMA 模型

### 4.1 ARIMA 简介

ARIMA (AutoRegressive Integrated Moving Average) 是最经典的时间序列预测模型。

```
ARIMA(p, d, q)

p: 自回归阶数 (AR) - 用过去p个值预测
d: 差分阶数 (I) - 使序列平稳
q: 移动平均阶数 (MA) - 用过去q个误差预测
```

### 4.2 ARIMA 各部分

**AR (自回归):**
```
y(t) = c + φ₁y(t-1) + φ₂y(t-2) + ... + φₚy(t-p) + ε(t)

含义: 当前值是过去值的线性组合
```

**I (差分):**
```
Δy(t) = y(t) - y(t-1)

含义: 用差分使序列平稳
```

**MA (移动平均):**
```
y(t) = c + ε(t) + θ₁ε(t-1) + θ₂ε(t-2) + ... + θ_qε(t-q)

含义: 当前值受过去误差的影响
```

### 4.3 ARIMA 建模流程

```
Step 1: 平稳性检验
    │
    ▼
Step 2: 差分 (如果需要)
    │
    ▼
Step 3: 确定 p, q (ACF/PACF 图)
    │
    ├── ACF 拖尾, PACF 截尾 → AR(p)
    ├── ACF 截尾, PACF 拖尾 → MA(q)
    └── ACF 拖尾, PACF 拖尾 → ARIMA(p,q)
    │
    ▼
Step 4: 拟合模型
    │
    ▼
Step 5: 残差检验 (Ljung-Box 检验)
    │
    ▼
Step 6: 预测
```

### 4.4 使用 statsmodels 实现

```python
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# 拟合 ARIMA 模型
model = ARIMA(series, order=(1, 1, 1))
fitted = model.fit()
print(fitted.summary())

# 预测
forecast = fitted.forecast(steps=12)  # 预测未来12步
```

---

## 5. Prophet 模型

### 5.1 Prophet 简介

Prophet 是 Facebook 开源的时间序列预测工具，特别适合具有以下特征的数据：
- 强季节性
- 趋势变化点
- 缺失值
- 异常值

### 5.2 Prophet 核心思想

```
y(t) = g(t) + s(t) + h(t) + ε(t)

g(t): 趋势函数 (线性或逻辑增长)
s(t): 季节性函数 (傅里叶级数)
h(t): 节假日效应
ε(t): 误差项
```

### 5.3 使用 Prophet

```python
from prophet import Prophet
import pandas as pd

# 准备数据 (必须有 ds 和 y 列)
df = pd.DataFrame({
    'ds': pd.date_range('2026-01-01', periods=365),
    'y': sales_data  # 销售额
})

# 创建并训练模型
model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False,
    changepoint_prior_scale=0.05
)
model.fit(df)

# 创建未来日期
future = model.make_future_dataframe(periods=30)

# 预测
forecast = model.predict(future)

# 可视化
model.plot(forecast)
model.plot_components(forecast)
```

### 5.4 Prophet vs ARIMA 对比

| 对比维度 | ARIMA | Prophet |
|----------|-------|---------|
| 假设条件 | 严格（平稳性） | 宽松 |
| 季节性 | 需手动设置 | 自动检测 |
| 缺失值 | 需预处理 | 内置处理 |
| 异常值 | 敏感 | 鲁棒 |
| 可解释性 | 中等 | 高 |
| 调参难度 | 高 | 低 |
| 大规模数据 | 适合 | 适合 |

---

## 6. 评估指标

### 6.1 常用指标

| 指标 | 公式 | 说明 |
|------|------|------|
| MAE | Σ\|yₜ - ŷₜ\| / n | 平均绝对误差 |
| MSE | Σ(yₜ - ŷₜ)² / n | 均方误差 |
| RMSE | √MSE | 均方根误差 |
| MAPE | Σ\|yₜ - ŷₜ\|/\|yₜ\| × 100 / n | 平均绝对百分比误差 |
| SMAPE | Σ\|yₜ - ŷₜ\|/\|yₜ\|+\|ŷₜ\| × 100 / n | 对称MAPE |

### 6.2 MAPE 的陷阱

MAPE 在真实值接近0时会爆炸，且对低估和高估的惩罚不对称：

```python
# MAPE 的问题
真实值: 100, 预测值: 80  → MAPE = 20%
真实值: 100, 预测值: 120 → MAPE = 20%
但: 真实值: 1, 预测值: 101 → MAPE = 10000%!
```

---

## 7. 特征工程

### 7.1 时间特征

```python
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['day_of_week'] = df['date'].dt.dayofweek
df['quarter'] = df['date'].dt.quarter
df['is_weekend'] = df['date'].dt.dayofweek >= 5
```

### 7.2 滞后特征

```python
df['lag_1'] = df['y'].shift(1)   # 昨天的值
df['lag_7'] = df['y'].shift(7)   # 上周同天
df['lag_30'] = df['y'].shift(30) # 上月同天
```

### 7.3 滚动统计

```python
df['rolling_mean_7'] = df['y'].rolling(7).mean()   # 7天均值
df['rolling_std_7'] = df['y'].rolling(7).std()     # 7天标准差
df['rolling_max_30'] = df['y'].rolling(30).max()   # 30天最大值
```

---

## 8. 实战代码

- `01-time-series-decomposition.py`：时间序列分解与平稳性检验
- `02-arima-forecasting.py`：ARIMA 模型预测
- `03-prophet-forecasting.py`：Prophet 模型预测

---

## 9. 思考题

1. **什么情况下 ARIMA 比 Prophet 更好？** 从数据特征和假设条件的角度分析。

**参考答案**

ARIMA 更合适的情况：

- **数据量小、序列短**：Prophet 的趋势+季节+节假日模型较复杂，小数据容易过拟合；ARIMA 参数少、更稳。
- **接近平稳、无强季节性**：序列本身或差分后平稳、没有明显日历季节性和节假日效应时，ARIMA 的统计假设正好契合。
- **需要统计推断**：想要可解释的系数、显著性和置信区间。
- **高频无日历规律**：如传感器读数这类没有"周/年"周期的数据。

Prophet 则更适合强季节性、有趋势变化点、含缺失/异常值、有节假日效应的业务数据。

小例子：一段平稳的服务器 CPU 利用率序列，用 ARIMA(1,0,1) 就够了，Prophet 反而多余。

2. **如何判断时间序列是否需要差分？** ADF 检验的 p-value 为 0.06（接近但大于0.05），你会怎么做？

**参考答案**

判断流程：先看时序图有无趋势/均值漂移，再做 ADF 检验。ADF 的原假设是"存在单位根（非平稳）"，p<0.05 才拒绝原假设、认为平稳。

p=0.06 略大于 0.05，处于灰色地带，不能机械下结论。我会：

- **结合证据**：看 ACF（自相关图）是否衰减很慢、图形是否有明显趋势，综合判断。
- **试差分再检验**：做一阶差分后对差分序列再做 ADF，若 p 远小于 0.05 且 ACF 快速衰减，就取 d=1。
- **防止过度差分**：差分后方差反而变大、ACF 出现强负相关，说明差分过头。
- **用预测误差择优**：对比 d=0 与 d=1 的样本外预测误差来定。

核心：p=0.06 既不是"必须差分"也不是"绝不动"，要结合图形、差分后检验和验证误差综合决定。

3. **时间序列预测中的「数据泄露」是什么？** 如何在训练时避免看到未来数据？

**参考答案**

数据泄露（data leakage）指训练时不小心用到了"未来"的信息，导致离线评估虚高、一上线就崩。时间序列里常见三种：

- **随机切分**：打乱后划分训练/测试，使未来点混进训练集。
- **全局预处理**：用整段数据的均值/标准差做标准化，统计量里含未来信息。
- **特征越界**：滞后/滚动特征计算时跨越了预测时点。

避免方法：严格按时间切分（前段训练、后段测试）；所有预处理只在训练集上 `fit`，再 `transform` 测试集；滚动/滞后特征只用当前及过去值；用滚动原点交叉验证（walk-forward）。下面用纯标准库对比两种切分（可直接运行）：

```python
import random

random.seed(0)
# 构造带上升趋势的序列：值随时间增大
data = [100 + i * 2 + random.randint(-3, 3) for i in range(20)]

# ❌ 错误：随机打乱后切分，训练集里混进了"未来"的点
idx = list(range(len(data)))
random.shuffle(idx)
train_idx = idx[:14]
future_in_train = [i for i in train_idx if i >= 14]
print("随机切分：训练集里属于未来(下标>=14)的点数 =", len(future_in_train))

# ✅ 正确：严格按时间先后切分，前 14 个训练，后 6 个测试
train, test = data[:14], data[14:]
print("按时间切分：训练集最大下标 =", 13, "，测试集最小下标 =", 14)
print("训练集末尾值 =", train[-1], "，测试集开头值 =", test[0])
```

预期输出：

```
随机切分：训练集里属于未来(下标>=14)的点数 = 5
按时间切分：训练集最大下标 = 13 ，测试集最小下标 = 14
训练集末尾值 = 125 ，测试集开头值 = 129
```

随机切分把 5 个未来点泄露进了训练集；按时间切分则保证训练集永远在测试集之前。

4. **如何处理时间序列中的缺失值？** 前向填充、插值、模型预测各有什么优缺点？

**参考答案**

- **前向填充**（用最近一个已知值补）：简单、保持时序因果（只用过去），但会制造"平台"、低估波动，适合短缺口或状态量。
- **插值**（线性/样条，用两侧已知值）：平滑、利用前后信息，但用到了"未来"值，预测场景要小心泄露，更适合离线分析。
- **模型预测**（用其他特征/序列建模填补）：能利用复杂关系、精度高，但实现复杂、可能引入偏差。

选择看缺口长度、用途（分析还是预测）以及是否有辅助特征。下面用纯标准库演示前向填充与线性插值（可直接运行）：

```python
def forward_fill(values):
    """前向填充：用最近一个已知值补洞"""
    result, last = [], None
    for v in values:
        if v is not None:
            last = v
        result.append(last)
    return result

def linear_fill(values):
    """线性插值：用洞两侧已知值按距离加权补洞"""
    result = values[:]
    n = len(result)
    i = 0
    while i < n:
        if result[i] is None:
            left = i - 1                 # 洞左边最近的已知值下标
            right = i                    # 向右找第一个已知值
            while right < n and result[right] is None:
                right += 1
            if left >= 0 and right < n:  # 两侧都有已知值 -> 插值
                for j in range(i, right):
                    w = (j - left) / (right - left)
                    result[j] = result[left] + (result[right] - result[left]) * w
            elif left >= 0:              # 右边没有已知值 -> 只能前向填充
                for j in range(i, right):
                    result[j] = result[left]
            i = right
        else:
            i += 1
    return result

data = [100, None, None, 130, None, 150]
print("原始:    ", data)
print("前向填充:", forward_fill(data))
print("线性插值:", linear_fill(data))
```

预期输出：

```
原始:     [100, None, None, 130, None, 150]
前向填充: [100, 100, 100, 130, 130, 150]
线性插值: [100, 110.0, 120.0, 130, 140.0, 150]
```

前向填充把缺口填成"台阶"，线性插值则平滑过渡。

⚠️ 注意：做预测时，插值若用到未来值会造成数据泄露，应只用当前及过去的信息。

5. **在电商场景中，如何预测大促（如双11）期间的销量？** 常规时间序列模型可能失效，你会怎么处理？

**参考答案**

大促是极端事件，常规序列模型会把它当异常抹平或完全预测不到。处理思路：

- **事件/节假日建模**：用 Prophet 的 `holidays` 机制，或加入促销哑变量/特征（折扣力度、是否大促日、预热期），让模型显式学出尖峰。
- **单独建模**：用历年大促数据训练专门的促销模型，与日常模型分开。
- **分阶段预测**：预热期、爆发期、返场期分别建模。
- **引入外部特征**：流量投放、优惠券、竞品活动、库存。
- **业务校准兜底**：结合运营经验人工修正，并给出较宽的置信区间。

小例子：给 Prophet 传入双11的 holidays 表，它会学出当天销量的尖峰，而不是把它当异常值平滑掉。

---

## 参考资料

- [Prophet 官方文档](https://facebook.github.io/prophet/)
- [statsmodels 时间序列文档](https://www.statsmodels.org/stable/tsa.html)
- [《时间序列分析与预测》- Hyndman](https://otexts.com/fpp3/)
- [Kaggle 时间序列教程](https://www.kaggle.com/learn/time-series)
