"""
Day 121 - Isolation Forest 基础用法
====================================
演示 Isolation Forest 的核心 API：训练、预测、异常分数分析
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 无显示器环境
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.datasets import make_blobs

# ============================================================
# 1. 生成模拟数据：正常簇 + 异常点
# ============================================================

# 正常数据：3个簇，共300个样本
X_normal, _ = make_blobs(
    n_samples=300,
    centers=3,
    cluster_std=0.8,
    random_state=42
)

# 注入异常点：随机散布在正常数据之外
np.random.seed(42)
n_anomalies = 20
X_anomalies = np.random.uniform(
    low=-10, high=10,
    size=(n_anomalies, 2)
)

# 合并数据
X = np.vstack([X_normal, X_anomalies])
print(f"总样本数: {len(X)}")
print(f"  正常样本: {len(X_normal)}")
print(f"  异常样本: {len(X_anomalies)}")

# ============================================================
# 2. 训练 Isolation Forest
# ============================================================

# contamination=0.06 表示预期约6%的异常（20/333 ≈ 6%）
clf = IsolationForest(
    n_estimators=100,       # 100棵隔离树
    max_samples=256,        # 每棵树采样256个点（推荐值）
    contamination=0.06,     # 预期异常比例
    random_state=42,
    n_jobs=-1               # 使用所有CPU核
)

clf.fit(X)

print(f"\n模型训练完成！")
print(f"  树数量: {clf.n_estimators}")
print(f"  采样大小: {clf.max_samples}")

# ============================================================
# 3. 预测异常
# ============================================================

# predict: 1=正常, -1=异常
predictions = clf.predict(X)

# decision_function: 异常分数（负值=异常）
scores = clf.decision_function(X)

# score_samples: 每个样本的异常分数
sample_scores = clf.score_samples(X)

print(f"\n预测结果统计:")
print(f"  预测正常 (1): {np.sum(predictions == 1)}")
print(f"  预测异常 (-1): {np.sum(predictions == -1)}")

# 找出被标记为异常的样本
anomaly_mask = predictions == -1
print(f"\n异常分数范围:")
print(f"  最小: {scores.min():.4f}")
print(f"  最大: {scores.max():.4f}")
print(f"  均值: {scores.mean():.4f}")
print(f"  异常样本均分: {scores[anomaly_mask].mean():.4f}")
print(f"  正常样本均分: {scores[~anomaly_mask].mean():.4f}")

# ============================================================
# 4. 可视化结果
# ============================================================

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# 左图：真实标签
ax1 = axes[0]
ax1.scatter(X_normal[:, 0], X_normal[:, 1],
           c='blue', s=20, alpha=0.6, label='正常样本')
ax1.scatter(X_anomalies[:, 0], X_anomalies[:, 1],
           c='red', s=60, marker='x', label='真实异常')
ax1.set_title('真实标签', fontsize=14)
ax1.legend()
ax1.set_xlabel('Feature 1')
ax1.set_ylabel('Feature 2')

# 右图：Isolation Forest 检测结果
ax2 = axes[1]
normal_pred = predictions == 1
anomaly_pred = predictions == -1
ax2.scatter(X[normal_pred, 0], X[normal_pred, 1],
           c='blue', s=20, alpha=0.6, label='预测正常')
ax2.scatter(X[anomaly_pred, 0], X[anomaly_pred, 1],
           c='red', s=60, marker='x', label='预测异常')

# 标注被错误分类的点
false_positives = (anomaly_pred) & (np.isin(X, X_normal).all(axis=1))
false_negatives = (normal_pred) & (np.isin(X, X_anomalies).all(axis=1))

ax2.set_title('Isolation Forest 检测结果', fontsize=14)
ax2.legend()
ax2.set_xlabel('Feature 1')
ax2.set_ylabel('Feature 2')

plt.tight_layout()
plt.savefig('days/day-121-异常检测与安全交叉/diagrams/isolation_forest_basic.png',
            dpi=150, bbox_inches='tight')
print("\n✅ 可视化已保存到 diagrams/isolation_forest_basic.png")

# ============================================================
# 5. 异常分数分布直方图
# ============================================================

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(scores[~anomaly_mask], bins=50, alpha=0.7, label='正常样本', color='blue')
ax.hist(scores[anomaly_mask], bins=20, alpha=0.7, label='异常样本', color='red')
ax.axvline(x=clf.offset_, color='green', linestyle='--', label=f'决策边界: {clf.offset_:.4f}')
ax.set_xlabel('异常分数 (decision_function)')
ax.set_ylabel('样本数量')
ax.set_title('异常分数分布')
ax.legend()
plt.tight_layout()
plt.savefig('days/day-121-异常检测与安全交叉/diagrams/score_distribution.png',
            dpi=150, bbox_inches='tight')
print("✅ 异常分数分布图已保存")

# ============================================================
# 6. contamination 调优实验
# ============================================================

print("\n--- contamination 调优实验 ---")
for c in [0.01, 0.05, 0.1, 0.2, 0.3]:
    clf_temp = IsolationForest(contamination=c, random_state=42)
    clf_temp.fit(X)
    pred_temp = clf_temp.predict(X)
    n_anomaly = np.sum(pred_temp == -1)
    print(f"  contamination={c:.2f} → 检测出 {n_anomaly} 个异常")

print("\n💡 关键要点：")
print("  1. contamination 控制异常检测的敏感度")
print("  2. 值越大，检测出的异常越多（可能误报）")
print("  3. 值越小，检测越保守（可能漏报）")
print("  4. 建议：先用 'auto'，再根据业务调整")
