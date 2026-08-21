# Day 124 — 时间序列预测 — 练习清单

## ✅ 今日完成清单

- [ ] 理解时间序列的组成成分（趋势、季节性、周期性、残差）
- [ ] 掌握时间序列分解方法（加法/乘法）
- [ ] 理解平稳性概念与 ADF 检验
- [ ] 掌握 ARIMA 模型建模流程
- [ ] 了解 Prophet 模型及其优势
- [ ] 了解时间序列评估指标
- [ ] 完成 3 个代码示例的运行和理解
- [ ] 完成以下练习题

---

## 📝 基础练习题

### 练习 1：时间序列分解

给定以下月度销售额数据（12个月）：

```
月份:  1    2    3    4    5    6    7    8    9    10   11   12
销售: 100  110  120  130  140  150  160  155  145  135  125  115
```

**问题：**
1. 这个序列有趋势吗？趋势方向是什么？
2. 有季节性吗？周期是多少？
3. 用加法分解还是乘法分解更合适？为什么？
4. 计算季节性分量的值

---

### 练习 2：平稳性检验

判断以下序列是否平稳：

```
序列A: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
序列B: [5, 3, 7, 2, 8, 4, 6, 3, 7, 5]
序列C: [1, 10, 1, 10, 1, 10, 1, 10, 1, 10]
```

**问题：**
1. 哪个序列平稳？哪个不平稳？
2. 对不平稳的序列，需要几阶差分？
3. ADF 检验的 p-value 分别可能是多少？

---

### 练习 3：ARIMA 定阶

根据以下 ACF/PACF 图信息：

```
ACF:  滞后1=0.8, 滞后2=0.6, 滞后3=0.4, 滞后4=0.2, 滞后5=0.05
PACF: 滞后1=0.8, 滞后2=0.1, 滞后3=0.05, 滞后4=0.02, 滞后5=0.01
```

**问题：**
1. ACF 和 PACF 哪个截尾？哪个拖尾？
2. 应该选择 AR(p)、MA(q) 还是 ARIMA(p,q)？
3. p 和 q 的值分别是多少？
4. 写出完整的 ARIMA 模型表达式

---

## 🔥 进阶挑战题

### 挑战 1：股票预测

使用真实股票数据（可用 `yfinance` 库获取），实现：

1. 数据探索与可视化
2. 平稳性检验与差分
3. ARIMA 建模与预测
4. 与 Prophet 对比
5. 计算交易信号（预测上涨/下跌）

```python
# 提示: 获取股票数据
import yfinance as yf
df = yf.download('AAPL', start='2020-01-01', end='2026-01-01')
```

---

### 挑战 2：销量预测系统

构建一个完整的销量预测系统：

1. 数据清洗与异常值处理
2. 特征工程（滞后特征、滚动统计、时间特征）
3. 多模型对比（ARIMA、Prophet、LightGBM）
4. 模型融合（加权平均）
5. 预测结果可视化与报告生成

```python
# 特征工程示例
df['lag_1'] = df['sales'].shift(1)
df['lag_7'] = df['sales'].shift(7)
df['rolling_mean_7'] = df['sales'].rolling(7).mean()
df['day_of_week'] = df['date'].dt.dayofweek
```

---

### 挑战 3：异常检测

在时间序列中检测异常点：

1. 基于统计方法（3σ 原则）
2. 基于残差（ARIMA 残差超出阈值）
3. 基于 Prophet（trend 中的变化点）

```python
# 3σ 异常检测
mean = df['sales'].mean()
std = df['sales'].std()
anomalies = df[(df['sales'] > mean + 3*std) | (df['sales'] < mean - 3*std)]
```

---

## 📚 扩展阅读

- [Prophet 官方文档](https://facebook.github.io/prophet/)
- [Darts 时间序列库](https://unit8co.github.io/darts/) - 统一的时间序列预测框架
- [GluonTS](https://github.com/awslabs/gluonts) - 深度学习时间序列
- [Kaggle 时间序列竞赛](https://www.kaggle.com/competitions?search=time+series)
- [《Forecasting: Principles and Practice》](https://otexts.com/fpp3/) - 免费在线教材
