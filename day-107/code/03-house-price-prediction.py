"""
Day 107 — 实战：房价预测
完整 ML 流程：数据探索 → 特征工程 → 模型训练 → 评估 → 分析

运行：python3 03-house-price-prediction.py
"""

import numpy as np
import pandas as pd
from sklearn.datasets import fetch_california_housing
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

# ============================================================
# 1. 加载数据
# ============================================================
print("=" * 60)
print("1. 数据加载与探索")
print("=" * 60)

housing = fetch_california_housing()
X = pd.DataFrame(housing.data, columns=housing.feature_names)
y = pd.Series(housing.target, name='MedHouseVal')

print(f"\n数据集形状: {X.shape}（20640 个样本，8 个特征）")
print(f"目标: 加州各区房价中位数（单位: 10 万美元）")
print(f"\n特征说明:")
print(f"  MedInc    - 收入中位数")
print(f"  HouseAge  - 房龄中位数")
print(f"  AveRooms  - 平均房间数")
print(f"  AveBedrms - 平均卧室数")
print(f"  Population - 人口")
print(f"  AveOccup  - 平均住户数")
print(f"  Latitude  - 纬度")
print(f"  Longitude - 经度")

print(f"\n目标统计:")
print(f"  均值: {y.mean():.3f}（即 {y.mean()*10:.1f} 万美元）")
print(f"  中位数: {y.median():.3f}")
print(f"  范围: [{y.min():.3f}, {y.max():.3f}]")

print(f"\n特征相关性（与目标）:")
corr_with_target = X.corrwith(y).sort_values(ascending=False)
for feat, corr in corr_with_target.items():
    bar = '█' * int(abs(corr) * 30)
    sign = '+' if corr > 0 else '-'
    print(f"  {feat:<12} {sign}{abs(corr):.3f} {bar}")

# ============================================================
# 2. 数据预处理
# ============================================================
print(f"\n{'=' * 60}")
print("2. 数据预处理")
print("=" * 60)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"训练集: {X_train.shape[0]} 条")
print(f"测试集: {X_test.shape[0]} 条")

# 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ============================================================
# 3. 训练多个模型
# ============================================================
print(f"\n{'=' * 60}")
print("3. 模型训练与对比")
print("=" * 60)

models = {
    'LinearRegression': LinearRegression(),
    'Ridge (α=1.0)': Ridge(alpha=1.0),
    'Ridge (α=10.0)': Ridge(alpha=10.0),
    'Lasso (α=0.01)': Lasso(alpha=0.01),
}

results = []

for name, model in models.items():
    # 交叉验证
    cv_scores = cross_val_score(
        model, X_train_scaled, y_train,
        cv=5, scoring='r2'
    )

    # 训练并预测
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)

    # 评估
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    results.append({
        '模型': name,
        'CV_R²_mean': cv_scores.mean(),
        'CV_R²_std': cv_scores.std(),
        'Test_MSE': mse,
        'Test_RMSE': rmse,
        'Test_MAE': mae,
        'Test_R²': r2
    })

# 打印结果表
results_df = pd.DataFrame(results)
print(f"\n模型对比:")
print(results_df.to_string(index=False))

# ============================================================
# 4. 特征重要性分析
# ============================================================
print(f"\n{'=' * 60}")
print("4. 特征重要性分析（LinearRegression）")
print("=" * 60)

best_model = LinearRegression()
best_model.fit(X_train_scaled, y_train)

coef_df = pd.DataFrame({
    '特征': housing.feature_names,
    '系数': best_model.coef_,
    'abs_系数': np.abs(best_model.coef_)
}).sort_values('abs_系数', ascending=False)

print(f"\n截距: {best_model.intercept_:.4f}")
print(f"\n特征系数（按重要性排序）:")
for _, row in coef_df.iterrows():
    bar = '█' * int(row['abs_系数'] * 10)
    direction = '↑' if row['系数'] > 0 else '↓'
    print(f"  {row['特征']:<12} {direction} {row['系数']:>+8.4f}  {bar}")

# ============================================================
# 5. 预测误差分析
# ============================================================
print(f"\n{'=' * 60}")
print("5. 预测误差分析")
print("=" * 60)

y_pred = best_model.predict(X_test_scaled)
errors = y_pred - y_test

# 按价格区间分析
price_bins = pd.cut(y_test, bins=5, labels=['极低', '低', '中', '高', '极高'])
error_by_price = pd.DataFrame({
    '价格区间': price_bins,
    'MAE': np.abs(errors),
    '误差': errors
}).groupby('价格区间', observed=True).agg({
    'MAE': 'mean',
    '误差': ['mean', 'std']
}).round(4)

print(f"\n按房价区间的预测误差:")
print(error_by_price.to_string())

# 最大误差案例
worst_idx = np.abs(errors).argsort()[-5:][::-1]
print(f"\n预测最差的 5 个样本:")
print(f"{'真实值':>10} {'预测值':>10} {'误差':>10}")
for i in worst_idx:
    print(f"  {y_test.iloc[i]:>8.3f}  {y_pred[i]:>8.3f}  {errors.iloc[i]:>+8.3f}")

# ============================================================
# 6. 总结
# ============================================================
print(f"\n{'=' * 60}")
print("6. 总结")
print("=" * 60)

best_r2 = results_df['Test_R²'].max()
best_rmse = results_df['Test_RMSE'].min()

print(f"""
📊 房价预测模型总结:

  最佳模型 R²:    {best_r2:.4f}
  最佳模型 RMSE:   {best_rmse:.4f}（即 {best_rmse*10:.1f} 万美元）

  关键发现:
  1. 收入中位数(MedInc)是最强预测因子（正相关）
  2. 地理位置(Latitude/Longitude)对房价影响显著
  3. Ridge 正则化对结果有微小改善
  4. 模型在中等价格区间预测最准
  5. 极端价格（极低/极高）预测误差更大

  线性回归局限:
  - 无法捕捉非线性关系（如经纬度的交互效应）
  - 对异常值敏感
  - 特征工程能显著提升效果
""")
