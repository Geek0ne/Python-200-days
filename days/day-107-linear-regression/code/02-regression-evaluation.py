"""
Day 107 — 回归评估指标详解与常见陷阱
理解 MSE/RMSE/MAE/R² 的区别，以及线性回归的常见陷阱

运行：python3 02-regression-evaluation.py
"""

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline

# ============================================================
# 1. 各指标的直觉理解
# ============================================================
print("=" * 60)
print("1. 各指标对比")
print("=" * 60)

# 三组预测结果
y_true = np.array([3.0, 5.0, 2.5, 7.0, 4.0])
pred_a = np.array([3.1, 4.8, 2.6, 6.9, 3.9])  # 很准
pred_b = np.array([3.0, 5.0, 2.5, 7.0, 10.0])  # 一个大误差
pred_c = np.array([4.0, 6.0, 3.5, 8.0, 5.0])  # 一致偏高

for name, pred in [("预测A（很准）", pred_a), ("预测B（一个大误差）", pred_b), ("预测C（一致偏高）", pred_c)]:
    mse = mean_squared_error(y_true, pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, pred)
    r2 = r2_score(y_true, pred)
    print(f"\n{name}:")
    print(f"  MSE={mse:.4f}  RMSE={rmse:.4f}  MAE={mae:.4f}  R²={r2:.4f}")

# 观察要点：
# - 预测B 的 MSE 和 RMSE 因一个异常值被拉高（平方效应）
# - 预测C 的 MAE 最小但 R² 可能不好（系统偏差）
# - R² 可以为负数（比均值预测还差）

# ============================================================
# 2. 多重共线性陷阱
# ============================================================
print(f"\n{'=' * 60}")
print("2. 多重共线性陷阱")
print("=" * 60)

np.random.seed(42)
n = 200

x1 = np.random.randn(n)
x2 = x1 + np.random.randn(n) * 0.01  # x2 ≈ x1，高度共线
x3 = np.random.randn(n)
y = 2 * x1 + 3 * x3 + np.random.randn(n) * 0.1

X_collinear = np.column_stack([x1, x2, x3])
X_train, X_test, y_train, y_test = train_test_split(
    X_collinear, y, test_size=0.2, random_state=42
)

model = LinearRegression()
model.fit(X_train, y_train)

print(f"\n真实系数: x1=2, x2=0, x3=3")
print(f"学习到的系数: x1={model.coef_[0]:.2f}, x2={model.coef_[1]:.2f}, x3={model.coef_[2]:.2f}")
print(f"⚠️ x1 和 x2 高度相关，系数被「分摊」了！")
print(f"   单独看 x1 或 x2 的系数没有意义，但预测仍然准确")

y_pred = model.predict(X_test)
print(f"R²: {r2_score(y_test, y_pred):.4f}（预测能力不受影响）")

# ============================================================
# 3. 过拟合演示
# ============================================================
print(f"\n{'=' * 60}")
print("3. 过拟合演示")
print("=" * 60)

np.random.seed(42)
X = np.sort(np.random.rand(30, 1) * 10, axis=0)
y = np.sin(X.squeeze()) * 3 + np.random.randn(30) * 0.5

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# 不同阶数的多项式回归
for degree in [1, 3, 10]:
    pipe = Pipeline([
        ('poly', PolynomialFeatures(degree=degree, include_bias=False)),
        ('lr', LinearRegression())
    ])
    pipe.fit(X_train, y_train)

    train_r2 = r2_score(y_train, pipe.predict(X_train))
    test_r2 = r2_score(y_test, pipe.predict(X_test))

    print(f"\n多项式阶数={degree}:")
    print(f"  训练集 R²: {train_r2:.4f}")
    print(f"  测试集 R²: {test_r2:.4f}")
    if degree == 1:
        print(f"  → 欠拟合：模型太简单")
    elif degree == 3:
        print(f"  → 合适：训练和测试 R² 都不错")
    else:
        print(f"  → 过拟合：训练 R² 很高，测试 R² 很差")

# ============================================================
# 4. Ridge 回归应对过拟合
# ============================================================
print(f"\n{'=' * 60}")
print("4. Ridge 回归（L2 正则化）应对过拟合")
print("=" * 60)

for alpha in [0, 0.1, 1.0, 10.0, 100.0]:
    pipe = Pipeline([
        ('poly', PolynomialFeatures(degree=10, include_bias=False)),
        ('ridge', Ridge(alpha=alpha))
    ])
    pipe.fit(X_train, y_train)

    train_r2 = r2_score(y_train, pipe.predict(X_train))
    test_r2 = r2_score(y_test, pipe.predict(X_test))

    print(f"  alpha={alpha:<6} → 训练R²={train_r2:.4f}  测试R²={test_r2:.4f}")

print(f"\n💡 Ridge 通过惩罚大系数来防止过拟合")
print(f"   alpha 越大，系数被压缩得越厉害，模型越简单")

# ============================================================
# 5. 残差分析
# ============================================================
print(f"\n{'=' * 60}")
print("5. 残差分析（模型诊断）")
print("=" * 60)

# 用线性模型拟合
model = LinearRegression()
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
residuals = y_test - y_pred

print(f"残差统计:")
print(f"  均值: {residuals.mean():.4f}  (应接近 0)")
print(f"  标准差: {residuals.std():.4f}")
print(f"  最大绝对值: {np.abs(residuals).max():.4f}")

# 简单正态性检验（D'Agostino 检验）
from scipy import stats
if len(residuals) >= 8:
    stat, p_value = stats.normaltest(residuals)
    print(f"  正态性检验 p-value: {p_value:.4f}")
    if p_value > 0.05:
        print(f"  → 残差近似正态（p > 0.05）✅")
    else:
        print(f"  → 残差偏离正态（p <= 0.05）⚠️")

print(f"\n✅ 总结：")
print(f"  - MSE/RMSE 衡量误差大小，对异常值敏感")
print(f"  - MAE 对异常值鲁棒")
print(f"  - R² 衡量拟合优度，-∞ 到 1")
print(f"  - 多重共线性不影响预测但影响系数解释")
print(f"  - 过拟合看训练集和测试集的 R² 差距")
print(f"  - 残差应近似正态、无明显模式")
