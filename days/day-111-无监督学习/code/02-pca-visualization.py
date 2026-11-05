"""
Day 111 - PCA 降维可视化
学习 PCA 降维原理与可视化
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.datasets import load_iris, make_friedman1
from sklearn.preprocessing import StandardScaler

# ========== 1. PCA 基本用法（Iris 数据集） ==========
print("=" * 50)
print("1. PCA 基本用法 - Iris 数据集")
print("=" * 50)

# 加载数据
iris = load_iris()
X = iris.data
y = iris.target
feature_names = iris.feature_names
target_names = iris.target_names

print(f"原始数据维度: {X.shape}")
print(f"特征名称: {feature_names}")
print(f"目标类别: {target_names}")

# 标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 创建 PCA 模型
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

print(f"\n降维后数据维度: {X_pca.shape}")
print(f"各主成分方差: {pca.explained_variance_}")
print(f"方差解释比例: {pca.explained_variance_ratio_}")
print(f"累积方差解释比例: {pca.explained_variance_ratio_.cumsum()}")

# 可视化
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 左图：PCA 降维结果
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
for i, name in enumerate(target_names):
    mask = y == i
    axes[0].scatter(X_pca[mask, 0], X_pca[mask, 1], 
                   c=colors[i], label=name, alpha=0.7, s=50, edgecolors='white')
axes[0].set_xlabel('第一主成分', fontsize=12)
axes[0].set_ylabel('第二主成分', fontsize=12)
axes[0].set_title('Iris 数据集 PCA 降维', fontsize=14)
axes[0].legend(fontsize=10)
axes[0].grid(True, alpha=0.3)

# 右图：方差解释比例
n_components = len(pca.explained_variance_ratio_)
x = np.arange(1, n_components + 1)
axes[1].bar(x, pca.explained_variance_ratio_, alpha=0.7, color='steelblue', label='单独解释比例')
axes[1].plot(x, pca.explained_variance_ratio_.cumsum(), 'ro-', linewidth=2, markersize=8, label='累积解释比例')
axes[1].set_xlabel('主成分', fontsize=12)
axes[1].set_ylabel('方差解释比例', fontsize=12)
axes[1].set_title('方差解释比例', fontsize=14)
axes[1].legend(fontsize=10)
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('pca_basic.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n已保存图片: pca_basic.png")

# ========== 2. PCA 数学原理可视化 ==========
print("\n" + "=" * 50)
print("2. PCA 数学原理可视化")
print("=" * 50)

# 生成有相关性的2D数据
np.random.seed(42)
mean = [0, 0]
cov = [[2, 1.5], [1.5, 1]]  # 有相关性
X_2d = np.random.multivariate_normal(mean, cov, 200)

# PCA 分析
pca_2d = PCA(n_components=2)
X_2d_pca = pca_2d.fit_transform(X_2d)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 左图：原始数据 + 主成分方向
axes[0].scatter(X_2d[:, 0], X_2d[:, 1], alpha=0.5, s=30, color='steelblue')

# 绘制主成分方向（特征向量）
for i, (comp, var) in enumerate(zip(pca_2d.components_, pca_2d.explained_variance_)):
    axes[0].quiver(0, 0, comp[0] * 2, comp[1] * 2,
                   angles='xy', scale_units='xy', scale=1, 
                   color=['red', 'green'][i],
                   label=f'PC{i+1} (方差={var:.2f})', width=0.02)
axes[0].set_xlim(-4, 4)
axes[0].set_ylim(-4, 4)
axes[0].set_aspect('equal')
axes[0].set_title('原始数据与主成分方向', fontsize=14)
axes[0].legend(fontsize=10)
axes[0].grid(True, alpha=0.3)

# 右图：PCA 投影结果
axes[1].scatter(X_2d_pca[:, 0], X_2d_pca[:, 1], alpha=0.5, s=30, color='steelblue')
axes[1].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
axes[1].axvline(x=0, color='gray', linestyle='--', alpha=0.5)
axes[1].set_xlabel('第一主成分', fontsize=12)
axes[1].set_ylabel('第二主成分', fontsize=12)
axes[1].set_title('PCA 投影后数据', fontsize=14)
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('pca_principle.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存图片: pca_principle.png")

# ========== 3. 选择主成分数量 ==========
print("\n" + "=" * 50)
print("3. 选择主成分数量（累积方差法）")
print("=" * 50)

# 使用更高维数据
X_high, _ = make_friedman1(n_samples=200, n_features=10, random_state=42)
X_high_scaled = StandardScaler().fit_transform(X_high)

# 计算所有主成分
pca_full = PCA()
pca_full.fit(X_high_scaled)

print("各主成分的方差解释比例:")
for i, ratio in enumerate(pca_full.explained_variance_ratio_):
    print(f"  PC{i+1}: {ratio:.4f}")

# 可视化
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 碎石图 (Scree Plot)
axes[0].plot(range(1, len(pca_full.explained_variance_ratio_) + 1),
            pca_full.explained_variance_ratio_, 'bo-', linewidth=2, markersize=8)
axes[0].axhline(y=0.1, color='red', linestyle='--', alpha=0.5, label='10% 阈值')
axes[0].set_xlabel('主成分编号', fontsize=12)
axes[0].set_ylabel('方差解释比例', fontsize=12)
axes[0].set_title('碎石图 (Scree Plot)', fontsize=14)
axes[0].legend(fontsize=10)
axes[0].grid(True, alpha=0.3)

# 累积方差
cumsum = pca_full.explained_variance_ratio_.cumsum()
axes[1].plot(range(1, len(cumsum) + 1), cumsum, 'ro-', linewidth=2, markersize=8)
axes[1].axhline(y=0.9, color='green', linestyle='--', alpha=0.5, label='90% 阈值')
axes[1].axhline(y=0.95, color='orange', linestyle='--', alpha=0.5, label='95% 阈值')
axes[1].set_xlabel('主成分数量', fontsize=12)
axes[1].set_ylabel('累积方差解释比例', fontsize=12)
axes[1].set_title('累积方差解释比例', fontsize=14)
axes[1].legend(fontsize=10)
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('pca_variance.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n已保存图片: pca_variance.png")

# 自动选择主成分数量
for threshold in [0.90, 0.95]:
    n = np.argmax(cumsum >= threshold) + 1
    print(f"保留 {threshold*100:.0f}% 方差需要 {n} 个主成分")

# ========== 4. PCA 热力图（特征载荷） ==========
print("\n" + "=" * 50)
print("4. PCA 特征载荷热力图")
print("=" * 50)

# Iris 数据集的载荷
pca_iris = PCA()
X_iris_scaled = StandardScaler().fit_transform(iris.data)
pca_iris.fit(X_iris_scaled)

loadings = pd.DataFrame(
    pca_iris.components_.T,
    columns=[f'PC{i+1}' for i in range(len(iris.feature_names))],
    index=iris.feature_names
)
print(f"\n特征载荷:\n{loadings}")

# 使用 matplotlib 直接绘制
loadings_data = pca_iris.components_.T
fig, ax = plt.subplots(figsize=(8, 5))
im = ax.imshow(loadings_data[:2, :], cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
ax.set_xticks(range(len(iris.feature_names)))
ax.set_xticklabels([f'PC{i+1}' for i in range(2)], fontsize=12)
ax.set_yticks(range(len(iris.feature_names)))
ax.set_yticklabels(iris.feature_names, fontsize=12)
plt.colorbar(im, ax=ax)
ax.set_title('PCA 特征载荷热力图', fontsize=14)

# 添加数值标注
for i in range(2):
    for j in range(len(iris.feature_names)):
        ax.text(j, i, f'{loadings_data[i, j]:.2f}', ha='center', va='center', fontsize=10)

plt.tight_layout()
plt.savefig('pca_loadings.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存图片: pca_loadings.png")

# ========== 5. 降维与可视化对比 ==========
print("\n" + "=" * 50)
print("5. PCA vs 原始特征可视化对比")
print("=" * 50)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 原始特征的两两组合
feature_pairs = [(0, 1), (0, 2), (0, 3), (1, 2)]
for idx, (i, j) in enumerate(feature_pairs):
    ax = axes[idx // 2, idx % 2]
    for k, name in enumerate(target_names):
        mask = y == k
        ax.scatter(X[mask, i], X[mask, j], c=colors[k], label=name, alpha=0.6, s=30)
    ax.set_xlabel(feature_names[i], fontsize=10)
    ax.set_ylabel(feature_names[j], fontsize=10)
    ax.set_title(f'{feature_names[i]} vs {feature_names[j]}', fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

plt.suptitle('原始特征可视化', fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig('pca_vs_original.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存图片: pvs_vs_original.png")

print("\n✅ Day 111 PCA 降维可视化练习完成！")
