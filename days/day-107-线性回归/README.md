# Day 107 — 线性回归

> 线性回归是机器学习中最基础、最经典的回归算法。理解它是掌握所有机器学习模型的第一步。

---

## 目录

1. [线性回归原理与假设](#1-线性回归原理与假设)
2. [Scikit-learn 中的 LinearRegression](#2-scikit-learn-中的-linearregression)
3. [评估指标：MSE 与 R²](#3-评估指标mse-与-r²)
4. [实战：房价预测](#4-实战房价预测)
5. [思考题](#5-思考题)

---

## 1. 线性回归原理与假设

### 1.1 什么是线性回归

线性回归（Linear Regression）是用一条直线（或超平面）来拟合数据的统计方法。它假设因变量 $y$ 与自变量 $x$ 之间存在线性关系。

**一元线性回归：**

$$y = w_0 + w_1 x + \epsilon$$

- $y$：因变量（要预测的目标）
- $x$：自变量（特征/输入）
- $w_0$：截距（intercept），当 $x=0$ 时 $y$ 的值
- $w_1$：斜率（coefficient），$x$ 每变化 1 单位 $y$ 的变化量
- $\epsilon$：误差项，模型无法解释的随机部分

**多元线性回归：**

$$y = w_0 + w_1 x_1 + w_2 x_2 + \cdots + w_n x_n + \epsilon$$

写成矩阵形式：

$$\mathbf{y} = \mathbf{X}\mathbf{w} + \epsilon$$

其中 $\mathbf{X}$ 是 $m \times (n+1)$ 的设计矩阵（第一列全为 1 用于截距项），$\mathbf{w}$ 是 $(n+1) \times 1$ 的权重向量。

### 1.2 四大假设

线性回归的有效性依赖于以下四个经典假设（线性回归的 Gauss-Markov 假设）：

| 假设 | 含义 | 违反后果 |
|------|------|----------|
| **线性性** | $y$ 与 $x$ 是线性关系 | 模型欠拟合，预测偏差大 |
| **独立性** | 残差之间相互独立 | 标准误估计不准，p 值不可靠 |
| **同方差性** | 残差方差恒定（不随 $x$ 变化） | 置信区间失效 |
| **正态性** | 残差服从正态分布 | 假设检验失效（但预测仍可用） |

> 💡 **实践建议**：实际项目中，后两个假设可以通过残差图检验。如果严重违反，考虑数据变换或使用非线性模型。

### 1.3 损失函数

线性回归通过**最小化残差平方和（RSS）**来求解参数：

$$J(w) = \frac{1}{2m} \sum_{i=1}^{m} (y_i - \hat{y}_i)^2 = \frac{1}{2m} \sum_{i=1}^{m} (y_i - \mathbf{x}_i^T \mathbf{w})^2$$

这里的 $\frac{1}{2}$ 是为了求导方便（消除导数中的系数 2）。

**两种求解方法：**

| 方法 | 公式 | 适用场景 |
|------|------|----------|
| **正规方程** | $\mathbf{w} = (\mathbf{X}^T \mathbf{X})^{-1} \mathbf{X}^T \mathbf{y}$ | 特征数 < 10,000 |
| **梯度下降** | $\mathbf{w} := \mathbf{w} - \alpha \nabla J(\mathbf{w})$ | 特征数很多时更快 |

Scikit-learn 的 `LinearRegression` 默认使用正规方程（基于 LAPACK 的奇异值分解）。

---

## 2. Scikit-learn 中的 LinearRegression

### 2.1 API 速查

```python
from sklearn.linear_model import LinearRegression

# 创建模型
model = LinearRegression(
    fit_intercept=True,    # 是否计算截距
    normalize=False,       # 已弃用，建议用 StandardScaler
    copy_X=True,           # 是否复制 X
    n_jobs=None            # 并行计算数（None=1，-1=全部 CPU）
)

# 训练
model.fit(X_train, y_train)

# 预测
y_pred = model.predict(X_test)

# 获取参数
model.coef_           # 各特征的系数 [n_features]
model.intercept_      # 截距 float
```

### 2.2 关键属性

| 属性 | 说明 |
|------|------|
| `coef_` | 各特征的回归系数 |
| `intercept_` | 截距项 |
| `rank_` | 矩阵 $\mathbf{X}$ 的秩 |
| `singular_` | $\mathbf{X}$ 的奇异值 |
| `n_features_in_` | 训练时看到的特征数（sklearn 1.0+） |

### 2.3 完整代码示例

```python
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# 生成模拟数据：y = 3x + 2 + noise
np.random.seed(42)
X = np.random.rand(100, 1) * 10
y = 3 * X.squeeze() + 2 + np.random.randn(100) * 2

# 拆分数据
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 训练
model = LinearRegression()
model.fit(X_train, y_train)

# 预测
y_pred = model.predict(X_test)

# 输出
print(f"截距: {model.intercept_:.4f}")
print(f"斜率: {model.coef_[0]:.4f}")
print(f"MSE:  {mean_squared_error(y_test, y_pred):.4f}")
print(f"R²:   {r2_score(y_test, y_pred):.4f}")
# 输出类似：
# 截距: 2.1234
# 斜率: 2.9876
# MSE:  3.4521
# R²:   0.9823
```

---

## 3. 评估指标：MSE 与 R²

### 3.1 MSE（均方误差）

$$\text{MSE} = \frac{1}{m} \sum_{i=1}^{m} (y_i - \hat{y}_i)^2$$

- 值越小越好
- 单位是 $y$ 的单位的平方（不好直接解释）
- 对大误差惩罚更重（平方效应）

### 3.2 RMSE（均方根误差）

$$\text{RMSE} = \sqrt{\frac{1}{m} \sum_{i=1}^{m} (y_i - \hat{y}_i)^2}$$

- 单位与 $y$ 一致，更直观
- "平均来说，预测值与真实值差多少"

### 3.3 MAE（平均绝对误差）

$$\text{MAE} = \frac{1}{m} \sum_{i=1}^{m} |y_i - \hat{y}_i|$$

- 对异常值更鲁棒
- 不会放大极端误差

### 3.4 R²（决定系数）

$$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2} = 1 - \frac{\text{SS}_{\text{res}}}{\text{SS}_{\text{tot}}}$$

- 范围：$(-\infty, 1]$
- $R^2 = 1$：完美拟合
- $R^2 = 0$：模型和直接用均值预测一样好
- $R^2 < 0$：模型比用均值还差

> ⚠️ **常见误区**：R² 高不代表模型一定好！可能存在过拟合，或者相关关系不代表因果关系。

### 3.5 指标选择指南

```
预测值 vs 真实值

场景                          推荐指标
─────────────────────────────────────────────
通用基准                       MSE / RMSE
需要直观解释                   RMSE / MAE
有异常值                       MAE
比较不同数据集的模型            R²
模型是否优于"猜均值"           R²
```

---

## 4. 实战：房价预测

### 4.1 场景描述

使用经典的 Boston Housing 数据集（sklearn 内置或用 California Housing），基于房屋特征（面积、房间数等）预测房价。

### 4.2 完整流程

```python
import numpy as np
import pandas as pd
from sklearn.datasets import fetch_california_housing
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

# 1. 加载数据
housing = fetch_california_housing()
X = pd.DataFrame(housing.data, columns=housing.feature_names)
y = pd.Series(housing.target, name='MedHouseVal')

print(f"数据集大小: {X.shape}")
print(f"特征: {list(X.columns)}")
print(f"目标: 房价中位数（单位: 10万美元）")

# 2. 数据探索
print(f"\n特征统计:\n{X.describe()}")

# 3. 拆分数据
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"\n训练集: {X_train.shape[0]} 条")
print(f"测试集: {X_test.shape[0]} 条")

# 4. 特征标准化（可选，但推荐）
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. 训练模型
model = LinearRegression()
model.fit(X_train_scaled, y_train)

# 6. 预测与评估
y_pred = model.predict(X_test_scaled)

print(f"\n=== 评估结果 ===")
print(f"MSE:  {mean_squared_error(y_test, y_pred):.4f}")
print(f"RMSE: {np.sqrt(mean_squared_error(y_test, y_pred)):.4f}")
print(f"MAE:  {mean_absolute_error(y_test, y_pred):.4f}")
print(f"R²:   {r2_score(y_test, y_pred):.4f}")

# 7. 特征重要性分析
coef_df = pd.DataFrame({
    '特征': housing.feature_names,
    '系数': model.coef_
}).sort_values('系数', key=abs, ascending=False)

print(f"\n特征重要性（按绝对值排序）:")
print(coef_df.to_string(index=False))
print(f"截距: {model.intercept_:.4f}")
```

---

## 5. 思考题

### Q1：为什么线性回归用 MSE 而不是 MAE 作为损失函数？

**提示**：从数学角度考虑——MSE 可导（梯度光滑），而 MAE 在零点不可导。此外，MSE 有闭式解（正规方程），MAE 没有。

**参考答案**

主要有三个原因：

- **数学上好求解**：MSE 是平方函数，处处可导、梯度光滑，且是凸函数，令导数为 0 就能推出**闭式解（正规方程）** `w = (XᵀX)⁻¹Xᵀy`，一步算出最优参数。MAE 含绝对值，在误差为 0 处不可导，没有闭式解，只能用迭代优化（如线性规划/次梯度），更麻烦。
- **优化性质好**：MSE 的梯度随误差线性增大，误差大时「拉力」大、收敛快；MAE 梯度恒为 ±1，接近最优时仍大步长，容易在最优点附近震荡。
- **统计意义**：假设噪声服从**高斯分布**时，最小化 MSE 等价于极大似然估计，有坚实的概率解释。

代价：MSE 对大误差平方放大，**对异常值敏感**（一个离群点会强烈拽动拟合线）。所以若数据异常值多、想要鲁棒性，反而会用 MAE（或 Huber 损失）作评估/损失——这正是 Q5 的思路。

💡 提示：「用 MSE 训练」和「用 MAE 评估」并不矛盾：训练要可导好优化，评估要直观抗异常，两者可以分开选。

### Q2：如果特征之间高度相关（多重共线性），线性回归会发生什么？

**提示**：考虑 $\mathbf{X}^T \mathbf{X}$ 是否可逆。现实中怎么检测和处理多重共线性？

**参考答案**

多重共线性指特征之间高度相关（如「房屋面积」和「房间数」几乎成正比）。后果：

- **矩阵接近奇异**：正规方程要求逆 `XᵀX`，特征高度相关时它接近不可逆（行列式趋近 0），数值上极不稳定。
- **系数方差爆炸、不可解释**：系数估计变得对数据微小扰动极其敏感，可能正负乱跳、绝对值巨大——「面积」和「房间数」的单独贡献无法区分，但它们的组合仍能预测。
- **预测未必变差**：若新数据的相关结构不变，整体预测可能仍准，受害的主要是「系数的可解释性」和稳定性。

**检测**：看特征相关系数矩阵（|r| 接近 1）；算 **VIF（方差膨胀因子）**，VIF > 5~10 通常认为共线性严重；观察 `XᵀX` 的条件数/奇异值。

**处理**：
- 删除冗余特征（保留一个即可）。
- **正则化**：Ridge（L2）给 `XᵀX` 加上 λI 使其可逆、压缩系数，是共线性的经典解药。
- **降维**：PCA 把相关特征合成无关主成分。
- 增加样本量、或改用对共线性不敏感的树模型。

⚠️ 注意：sklearn 的 `LinearRegression` 用 SVD 求解，即使奇异也能给出最小范数解而不报错，但系数依然不稳定——不要因「能跑通」就忽视共线性。

### Q3：R² = 0.95 就说明模型好吗？

**提示**：考虑以下情况——在训练集上 R²=0.99，在测试集上 R²=0.6；或者所有特征和目标都只是偶然相关。R² 高但模型过拟合，是否真的"好"？

**参考答案**

**不一定**。R² 高只说明「在这份数据上拟合得好」，不等于「模型好」。要警惕几种情况：

- **过拟合**：训练集 R²=0.99、测试集只有 0.6，说明模型把训练数据的噪声也背下来了，泛化差。真正要看的是**测试集/交叉验证**的 R²，而非训练集。
- **数据泄露**：若特征里混入了目标信息（如用「成交后才知道的字段」预测房价），R² 会虚高到接近 1，上线即崩。
- **伪相关**：特征与目标只是偶然相关（甚至纯属巧合），样本内 R² 高但没有因果/稳定关系，换个数据集就失效。
- **R² 的局限**：它衡量「相对均值预测的改进」，对异常值敏感；非线性关系下即使模型合适 R² 也可能不高；不同数据集的 R² 不能直接比。

正确姿势：看**测试集 R² + 残差图**（残差应随机分布、无趋势）、结合 RMSE/MAE、做交叉验证、排查泄露，并理解业务因果。

⚠️ 注意：R² 可以为负（模型比直接猜均值还差），所以「R²=0.95」务必先问一句——这是在训练集还是测试集上算的？

### Q4：线性回归能否处理非线性关系？如果能，怎么做？

**提示**：多项式回归（PolynomialFeatures）。思考为什么增加多项式项后仍然是"线性回归"（参数是线性的）。

**参考答案**

**能**。方法是**多项式回归**：先用 `PolynomialFeatures` 把原始特征 x 扩展出 x²、x³ 等项，再对这些新特征做普通线性回归，就能拟合曲线。

```python
import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline

# 非线性数据：y = x^2 + 噪声
rng = np.random.default_rng(42)
X = np.linspace(-3, 3, 60).reshape(-1, 1)
y = X.squeeze() ** 2 + rng.normal(0, 0.5, 60)

# 普通直线拟合抛物线 → 很差
linear = LinearRegression().fit(X, y)

# 加入 x^2 项后再做线性回归 → 很好
poly = make_pipeline(PolynomialFeatures(degree=2), LinearRegression()).fit(X, y)

print(f"直线模型 R²:     {linear.score(X, y):.3f}")
print(f"二次多项式 R²:   {poly.score(X, y):.3f}")
```

预期输出（数值因随机种子/版本略有差异）：

```
直线模型 R²:     0.000
二次多项式 R²:   0.980
```

直线完全拟合不了抛物线（R²≈0），加入 x² 项后 R² 跃升到 0.98。

**为什么仍叫「线性」回归**：这里的「线性」指**对参数 w 是线性的**，而非对 x。模型 `y = w0 + w1·x + w2·x²` 中，x² 只是一个「新特征」，y 仍是 w0、w1、w2 的线性组合——所以求解方法（正规方程/梯度下降）完全不变。换句话说，多项式回归 = 特征工程 + 线性回归。

⚠️ 注意：degree 越高越容易过拟合（曲线剧烈震荡），务必配合交叉验证选阶数，并做特征缩放（x² 量纲远大于 x）。

### Q5：在房价预测中，如果发现某个区域的房价特别高（异常值），应该怎么办？

**提示**：从数据预处理（异常值检测）、模型选择（鲁棒回归如 RANSAC）、评估指标（MAE vs MSE）三个角度思考。

**参考答案**

先判断「异常」的性质：某区域房价特别高，可能是**真实的豪宅成交**，也可能是录入错误（如把「万元」写成「元」）。**不要一上来就删**——先核实数据来源，真实的高价房本身就是有效信息，盲目删除会让模型系统性低估高端市场。

- **数据预处理（异常值检测）**：用箱线图的 IQR 法则（超出 `Q1−1.5×IQR` 或 `Q3+1.5×IQR` 视为离群）或 3σ 法则快速定位可疑点。对确认无误、只是「长尾偏高」的房价，可对目标 y 做 **log 变换**（`y' = log(y)`），压缩量纲、让分布更接近正态，预测后再 `exp` 还原；这比删数据更稳妥。
- **模型选择（鲁棒回归）**：普通最小二乘对异常值极敏感（一个离群点能把整条回归线「拽偏」）。改用 **RANSAC**（随机抽样一致性：反复用随机子集拟合，只信任「内点」）或 **Huber 回归**（小误差用平方、大误差用绝对值，降低离群点权重），让模型不被少数极端值带跑。sklearn 里对应 `RANSACRegressor`、`HuberRegressor`。
- **评估指标（MAE vs MSE）**：MSE 把误差平方，会被高价异常值放大（一个偏差 100 万的点贡献 10¹² 的惩罚），从而「掩盖」大多数普通样本的真实表现；**MAE（平均绝对误差）**对异常值更稳健，更能反映典型预测水平。建议两者都看，或分区域/分价位段分别评估。

💡 提示：一句话——先核实真伪，再用 log 变换或鲁棒回归「降低影响」而非「一删了之」，评估时优先看 MAE。

---

## 总结

| 要点 | 说明 |
|------|------|
| 核心思想 | 用线性组合拟合数据 |
| 损失函数 | 最小化残差平方和 |
| 求解方法 | 正规方程（小数据）/ 梯度下降（大数据） |
| 评估指标 | MSE/RMSE 衡量误差大小，R² 衡量拟合优度 |
| 适用场景 | 线性关系、基准模型、可解释性要求高 |
| 注意事项 | 检查假设、避免过拟合、处理多重共线性 |

> 🔗 **下一步**：Day 108 将学习逻辑回归与分类，从回归问题过渡到分类问题。
