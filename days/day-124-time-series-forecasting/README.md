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

2. **如何判断时间序列是否需要差分？** ADF 检验的 p-value 为 0.06（接近但大于0.05），你会怎么做？

3. **时间序列预测中的「数据泄露」是什么？** 如何在训练时避免看到未来数据？

4. **如何处理时间序列中的缺失值？** 前向填充、插值、模型预测各有什么优缺点？

5. **在电商场景中，如何预测大促（如双11）期间的销量？** 常规时间序列模型可能失效，你会怎么处理？

---

## 参考资料

- [Prophet 官方文档](https://facebook.github.io/prophet/)
- [statsmodels 时间序列文档](https://www.statsmodels.org/stable/tsa.html)
- [《时间序列分析与预测》- Hyndman](https://otexts.com/fpp3/)
- [Kaggle 时间序列教程](https://www.kaggle.com/learn/time-series)
