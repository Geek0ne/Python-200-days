# Day 107 — 线性回归 · 完成清单与练习

## ✅ 今日完成清单

- [ ] 理解线性回归的数学原理（y = w₀ + w₁x + ε）
- [ ] 知道四大经典假设（线性性/独立性/同方差性/正态性）
- [ ] 理解 MSE 与正规方程的关系
- [ ] 能用 Scikit-learn 的 LinearRegression 训练模型
- [ ] 理解 MSE/RMSE/MAE/R² 四个评估指标的区别
- [ ] 能用交叉验证评估模型
- [ ] 理解多重共线性对系数的影响
- [ ] 理解过拟合的信号（训练 R² >> 测试 R²）
- [ ] 能做基本的残差分析
- [ ] 完成代码示例运行

---

## 📝 练习题

### 基础题

#### 练习 1：手算线性回归

给定以下 5 个数据点：

| x | y |
|---|---|
| 1 | 2.1 |
| 2 | 3.9 |
| 3 | 6.2 |
| 4 | 7.8 |
| 5 | 10.1 |

1. 计算 $\bar{x}$ 和 $\bar{y}$
2. 用正规方程手动计算 $w_1$ 和 $w_0$
3. 用代码验证你的结果

**提示**：
$$w_1 = \frac{\sum(x_i - \bar{x})(y_i - \bar{y})}{\sum(x_i - \bar{x})^2}$$
$$w_0 = \bar{y} - w_1 \bar{x}$$

---

#### 练习 2：评估指标计算

用以下真实值和预测值计算四个指标：

```python
y_true = [10, 20, 30, 40, 50]
y_pred = [12, 18, 28, 42, 48]
```

手动计算：
1. MSE
2. RMSE
3. MAE
4. R²

然后用 `sklearn.metrics` 验证。

---

#### 练习 3：特征系数含义

训练完 California Housing 模型后：

1. 哪个特征的系数最大（绝对值）？这意味着什么？
2. 如果 `MedInc` 的系数是正数，说明收入越高房价越____？
3. 如果 `Population` 的系数接近 0，说明人口密度对房价____？

---

### 进阶题

#### 练习 4：多项式回归

对以下非线性数据，尝试用不同阶数的多项式回归拟合：

```python
np.random.seed(42)
X = np.sort(np.random.rand(50, 1) * 6, axis=0)
y = 0.5 * X.squeeze()**2 - 2 * X.squeeze() + 3 + np.random.randn(50) * 0.5
```

1. 用 `PolynomialFeatures(degree=1)` 拟合，观察 R²
2. 用 `PolynomialFeatures(degree=2)` 拟合，观察 R²
3. 用 `PolynomialFeatures(degree=10)` 拟合，观察训练和测试 R²
4. 画出三种情况的拟合曲线，解释过拟合现象

---

#### 练习 5：Ridge 正则化对比

用 California Housing 数据：

```python
alphas = [0.001, 0.01, 0.1, 1, 10, 100, 1000]
```

对每个 alpha：
1. 训练 Ridge 回归
2. 记录系数的 L2 范数 `np.linalg.norm(model.coef_)`
3. 画出 alpha vs L2范数 的图
4. 找到测试集 R² 最高的 alpha

---

#### 练习 6：异常值影响实验

```python
np.random.seed(42)
X = np.random.rand(100, 1) * 10
y = 2 * X.squeeze() + 1 + np.random.randn(100) * 0.5
```

1. 在训练集里人工加入 5 个异常值（y 值乘以 10）
2. 比较加入异常值前后：
   - 系数 w₁ 和截距 w₀ 的变化
   - MSE 和 MAE 的变化
   - 哪个指标变化更大？为什么？

---

## 🧠 思考题（口头/书面）

1. 为什么 MSE 有闭式解而 MAE 没有？
2. 线性回归的「线性」指的是什么的线性？
3. 在什么情况下，R² = 0 比 R² = 0.8 更有意义？
