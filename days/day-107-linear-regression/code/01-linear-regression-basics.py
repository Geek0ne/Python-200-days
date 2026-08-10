"""
Day 107 — 线性回归基础用法
从零理解线性回归：生成数据 → 训练模型 → 可视化结果

运行：python3 01-linear-regression-basics.py
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 无 GUI 环境
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# ============================================================
# 1. 生成模拟数据：y = 2.5x + 3 + 噪声
# ============================================================
np.random.seed(42)

X = np.random.rand(200, 1) * 10  # 200 个样本，特征范围 [0, 10)
noise = np.random.randn(200) * 1.5  # 噪声
y = 2.5 * X.squeeze() + 3 + noise  # 真实关系

print(f"数据集大小: {X.shape}")
print(f"y 范围: [{y.min():.2f}, {y.max():.2f}]")

# ============================================================
# 2. 拆分训练集和测试集
# ============================================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"训练集: {len(X_train)} 条 | 测试集: {len(X_test)} 条")

# ============================================================
# 3. 训练线性回归模型
# ============================================================
model = LinearRegression()
model.fit(X_train, y_train)

print(f"\n=== 模型参数 ===")
print(f"截距 (w0): {model.intercept_:.4f}  (真实值: 3.0)")
print(f"斜率 (w1): {model.coef_[0]:.4f}  (真实值: 2.5)")

# ============================================================
# 4. 预测与评估
# ============================================================
y_pred = model.predict(X_test)

mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print(f"\n=== 评估指标 ===")
print(f"MSE:  {mse:.4f}")
print(f"RMSE: {rmse:.4f}  (平均预测误差约 {rmse:.2f})")
print(f"R²:   {r2:.4f}  (解释了 {r2*100:.1f}% 的方差)")

# ============================================================
# 5. 可视化
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 左图：拟合效果
ax1 = axes[0]
ax1.scatter(X_train, y_train, alpha=0.5, s=20, label='训练数据', color='steelblue')
ax1.scatter(X_test, y_test, alpha=0.5, s=20, label='测试数据', color='orange')
x_line = np.linspace(0, 10, 100).reshape(-1, 1)
y_line = model.predict(x_line)
ax1.plot(x_line, y_line, 'r-', linewidth=2, label=f'拟合线: y={model.coef_[0]:.2f}x+{model.intercept_:.2f}')
ax1.set_xlabel('特征 X')
ax1.set_ylabel('目标 y')
ax1.set_title('线性回归拟合效果')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 右图：预测 vs 真实
ax2 = axes[1]
ax2.scatter(y_test, y_pred, alpha=0.5, s=20, color='steelblue')
min_val = min(y_test.min(), y_pred.min())
max_val = max(y_test.max(), y_pred.max())
ax2.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='完美预测线')
ax2.set_xlabel('真实值')
ax2.set_ylabel('预测值')
ax2.set_title(f'预测 vs 真实 (R²={r2:.4f})')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('day-107-basics.png', dpi=150, bbox_inches='tight')
print(f"\n📊 图表已保存: day-107-basics.png")

# ============================================================
# 6. 关键点总结
# ============================================================
print(f"\n=== 关键点 ===")
print(f"1. 线性回归拟合 y = w1*x + w0")
print(f"2. 截距 {model.intercept_:.2f} ≈ 真实值 3.0")
print(f"3. 斜率 {model.coef_[0]:.2f} ≈ 真实值 2.5")
print(f"4. R²={r2:.4f} 说明模型解释了大部分方差")
print(f"5. RMSE={rmse:.2f} 说明平均预测误差较小")
