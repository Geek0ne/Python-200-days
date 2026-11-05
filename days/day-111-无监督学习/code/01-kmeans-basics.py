"""
Day 111 - K-Means 基础用法
学习 K-Means 聚类算法的基本操作
"""
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score

# ========== 1. 生成模拟数据 ==========
print("=" * 50)
print("1. 生成模拟数据（4个簇）")
print("=" * 50)

X, y_true = make_blobs(
    n_samples=300,
    centers=4,
    cluster_std=1.0,
    random_state=42
)

print(f"数据形状: {X.shape}")
print(f"真实簇标签: {np.unique(y_true)}")

# 可视化原始数据
plt.figure(figsize=(10, 5))
plt.subplot(1, 2, 1)
plt.scatter(X[:, 0], X[:, 1], c=y_true, cmap='viridis', s=50, alpha=0.7, edgecolors='white')
plt.title('原始数据（真实标签）', fontsize=14)
plt.xlabel('特征 1', fontsize=12)
plt.ylabel('特征 2', fontsize=12)
plt.grid(True, alpha=0.3)

# ========== 2. K-Means 基本用法 ==========
print("\n" + "=" * 50)
print("2. K-Means 基本用法")
print("=" * 50)

# 创建并训练模型
kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
y_pred = kmeans.fit_predict(X)

print(f"预测标签: {np.unique(y_pred)}")
print(f"簇中心:\n{kmeans.cluster_centers_}")
print(f"WCSS (Inertia): {kmeans.inertia_:.4f}")
print(f"迭代次数: {kmeans.n_iter_}")

# 可视化聚类结果
plt.subplot(1, 2, 2)
scatter = plt.scatter(X[:, 0], X[:, 1], c=y_pred, cmap='viridis', s=50, alpha=0.7, edgecolors='white')
plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1],
           c='red', marker='X', s=200, label='簇中心', zorder=5)
plt.title('K-Means 聚类结果', fontsize=14)
plt.xlabel('特征 1', fontsize=12)
plt.ylabel('特征 2', fontsize=12)
plt.legend(fontsize=10)
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('kmeans_basic.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n已保存图片: kmeans_basic.png")

# ========== 3. K-Means++ 初始化 ==========
print("\n" + "=" * 50)
print("3. K-Means++ vs 随机初始化")
print("=" * 50)

# 随机初始化
kmeans_random = KMeans(n_clusters=4, init='random', random_state=42, n_init=10)
kmeans_random.fit(X)

# K-Means++ 初始化（默认）
kmeans_pp = KMeans(n_clusters=4, init='k-means++', random_state=42, n_init=10)
kmeans_pp.fit(X)

print(f"随机初始化 WCSS: {kmeans_random.inertia_:.4f}")
print(f"K-Means++  WCSS: {kmeans_pp.inertia_:.4f}")

# ========== 4. 预测新数据 ==========
print("\n" + "=" * 50)
print("4. 预测新数据")
print("=" * 50)

# 创建新数据点
new_points = np.array([[0, 0], [3, 3], [-3, -3]])
predictions = kmeans.predict(new_points)

print("新数据点:")
for i, (point, pred) in enumerate(zip(new_points, predictions)):
    print(f"  点 {point} → 簇 {pred}")

# ========== 5. 评估聚类质量 ==========
print("\n" + "=" * 50)
print("5. 评估聚类质量")
print("=" * 50)

sil_score = silhouette_score(X, y_pred)
print(f"轮廓系数 (Silhouette Score): {sil_score:.4f}")
print("轮廓系数范围: [-1, 1]")
print("  - 接近 1: 样本远离其他簇")
print("  - 接近 0: 样本在簇边界上")
print("  - 接近 -1: 样本被错误分到当前簇")

# ========== 6. 不同 K 值的比较 ==========
print("\n" + "=" * 50)
print("6. 不同 K 值的比较")
print("=" * 50)

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
K_values = [2, 3, 4, 5, 6, 7]

for idx, k in enumerate(K_values):
    ax = axes[idx // 3, idx % 3]
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    
    ax.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis', s=30, alpha=0.7)
    ax.scatter(km.cluster_centers_[:, 0], km.cluster_centers_[:, 1],
              c='red', marker='X', s=100, zorder=5)
    
    sil = silhouette_score(X, labels)
    ax.set_title(f'K={k}, Silhouette={sil:.3f}', fontsize=12)
    ax.grid(True, alpha=0.3)

plt.suptitle('不同 K 值的聚类效果对比', fontsize=16, y=1.02)
plt.tight_layout()
plt.savefig('kmeans_k_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存图片: kmeans_k_comparison.png")

# ========== 7. 物理模型的惯性解释 ==========
print("\n" + "=" * 50)
print("7. 簇标签重映射（与真实标签对齐）")
print("=" * 50)

# 使用匈牙利算法对齐标签
from scipy.optimize import linear_sum_assignment

def align_labels(true_labels, pred_labels):
    """将预测标签与真实标签对齐"""
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(true_labels, pred_labels)
    row_ind, col_ind = linear_sum_assignment(-cm)
    mapping = {col_ind[i]: row_ind[i] for i in range(len(row_ind))}
    aligned = np.array([mapping[label] for label in pred_labels])
    return aligned

y_pred_aligned = align_labels(y_true, y_pred)
accuracy = np.mean(y_true == y_pred_aligned)
print(f"标签对齐后的准确率: {accuracy:.4f}")

print("\n✅ Day 111 K-Means 基础用法练习完成！")
