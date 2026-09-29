"""
Day 111 - 客户分群实战
基于 K-Means 和 PCA 的完整客户细分流程
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ========== 1. 生成模拟客户数据 ==========
print("=" * 60)
print("1. 生成模拟客户数据")
print("=" * 60)

np.random.seed(42)
n_customers = 500

# 4类客户画像：
# 类型A: 年轻高收入高消费（职场新人/科技行业）
# 类型B: 中年中收入稳定消费（家庭型）
# 类型C: 年轻低收入低消费（学生群体）
# 类型D: 中老年高收入高消费（成熟高管）

# 年龄, 年收入(万), 月消费频次, 平均消费金额, 在线时长(小时)
group_a = np.random.randn(125, 5) * [5, 20, 2, 500, 3] + [28, 80, 8, 2000, 15]
group_b = np.random.randn(125, 5) * [8, 15, 3, 300, 2] + [45, 50, 5, 1000, 5]
group_c = np.random.randn(125, 5) * [5, 10, 2, 200, 4] + [25, 30, 3, 500, 12]
group_d = np.random.randn(125, 5) * [3, 25, 2, 400, 2] + [58, 70, 6, 1500, 4]

data = np.vstack([group_a, group_b, group_c, group_d])
np.random.shuffle(data)

columns = ['年龄', '年收入(万)', '月消费频次', '平均消费金额', '在线时长(h)']
df = pd.DataFrame(data, columns=columns)

# 修正异常值（年龄、频次等不能为负）
df['年龄'] = df['年龄'].clip(lower=18, upper=70)
df['月消费频次'] = df['月消费频次'].clip(lower=1, upper=30)
df['平均消费金额'] = df['平均消费金额'].clip(lower=50, upper=10000)
df['在线时长(h)'] = df['在线时长(h)'].clip(lower=0.5, upper=24)

print(f"数据维度: {df.shape}")
print(f"\n数据统计摘要:")
print(df.describe().round(2))
print(f"\n前5条数据:")
print(df.head())

# ========== 2. 探索性数据分析 (EDA) ==========
print("\n" + "=" * 60)
print("2. 探索性数据分析")
print("=" * 60)

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
for i, col in enumerate(columns):
    ax = axes[i // 3, i % 3]
    ax.hist(df[col], bins=30, color='steelblue', alpha=0.7, edgecolor='white')
    ax.set_title(col, fontsize=12)
    ax.grid(True, alpha=0.3)

# 添加相关性热力图
ax = axes[1, 2]
corr = df.corr()
im = ax.imshow(corr, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
ax.set_xticks(range(len(columns)))
ax.set_xticklabels(columns, rotation=45, ha='right', fontsize=8)
ax.set_yticks(range(len(columns)))
ax.set_yticklabels(columns, fontsize=8)
plt.colorbar(im, ax=ax)
ax.set_title('特征相关性', fontsize=12)

plt.suptitle('客户数据探索性分析', fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig('customer_eda.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存 EDA 图: customer_eda.png")

# ========== 3. 数据预处理 ==========
print("\n" + "=" * 60)
print("3. 数据预处理（标准化）")
print("=" * 60)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(df)
print(f"标准化后数据均值: {X_scaled.mean(axis=0).round(4)}")
print(f"标准化后数据标准差: {X_scaled.std(axis=0).round(4)}")

# ========== 4. PCA 降维 ==========
print("\n" + "=" * 60)
print("4. PCA 降维分析")
print("=" * 60)

# 分析所有主成分
pca_full = PCA()
pca_full.fit(X_scaled)

print("各主成分方差解释比例:")
cumsum = 0
for i, ratio in enumerate(pca_full.explained_variance_ratio_):
    cumsum += ratio
    print(f"  PC{i+1}: {ratio:.4f} (累积: {cumsum:.4f})")

# 选择保留 95% 方差的主成分数量
n_components_95 = np.argmax(pca_full.explained_variance_ratio_.cumsum() >= 0.95) + 1
print(f"\n保留 95% 方差需要 {n_components_95} 个主成分")

# 使用 2 个主成分用于可视化
pca_2d = PCA(n_components=2)
X_pca = pca_2d.fit_transform(X_scaled)
print(f"\n2D PCA 方差解释比例: {pca_2d.explained_variance_ratio_.round(4)}")
print(f"2D PCA 累积方差解释比例: {pca_2d.explained_variance_ratio_.sum():.4f}")

# ========== 5. 肘部法则选择 K ==========
print("\n" + "=" * 60)
print("5. 肘部法则 + 轮廓系数选择最佳 K")
print("=" * 60)

K_range = range(2, 11)
inertias = []
silhouette_scores = []

for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    inertias.append(kmeans.inertia_)
    sil = silhouette_score(X_scaled, labels)
    silhouette_scores.append(sil)
    print(f"K={k:2d}: WCSS={kmeans.inertia_:10.2f}, 轮廓系数={sil:.4f}")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

axes[0].plot(K_range, inertias, 'bo-', linewidth=2, markersize=8)
axes[0].set_xlabel('K 值', fontsize=12)
axes[0].set_ylabel('WCSS (簇内平方和)', fontsize=12)
axes[0].set_title('肘部法则', fontsize=14)
axes[0].grid(True, alpha=0.3)

axes[1].plot(K_range, silhouette_scores, 'rs-', linewidth=2, markersize=8)
axes[1].set_xlabel('K 值', fontsize=12)
axes[1].set_ylabel('轮廓系数', fontsize=12)
axes[1].set_title('轮廓系数法', fontsize=14)
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('elbow_silhouette.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n已保存图片: elbow_silhouette.png")

# ========== 6. 训练最终模型 ==========
print("\n" + "=" * 60)
print("6. 训练 K-Means 模型 (K=4)")
print("=" * 60)

best_k = 4
kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
df['客户分群'] = kmeans.fit_predict(X_scaled)

final_sil = silhouette_score(X_scaled, df['客户分群'])
print(f"最终轮廓系数: {final_sil:.4f}")

# ========== 7. 客户群可视化 ==========
print("\n" + "=" * 60)
print("7. 客户群可视化")
print("=" * 60)

fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 7.1 PCA 降维散点图
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
for i in range(best_k):
    mask = df['客户分群'] == i
    axes[0, 0].scatter(X_pca[mask, 0], X_pca[mask, 1],
                      c=colors[i], label=f'客户群 {i}', alpha=0.6, s=50, edgecolors='white')
centers_pca = pca_2d.transform(scaler.transform(kmeans.cluster_centers_))
axes[0, 0].scatter(centers_pca[:, 0], centers_pca[:, 1],
                  c='black', marker='X', s=200, label='簇中心', zorder=5)
axes[0, 0].set_xlabel('第一主成分', fontsize=12)
axes[0, 0].set_ylabel('第二主成分', fontsize=12)
axes[0, 0].set_title('PCA 降维客户分群', fontsize=14)
axes[0, 0].legend(fontsize=10)
axes[0, 0].grid(True, alpha=0.3)

# 7.2 各群特征雷达图（使用柱状图替代）
cluster_means = df.groupby('客户分群')[columns].mean()
cluster_means.plot(kind='bar', ax=axes[0, 1], width=0.8)
axes[0, 1].set_title('各客户群特征对比', fontsize=14)
axes[0, 1].set_xlabel('客户群', fontsize=12)
axes[0, 1].set_ylabel('平均值', fontsize=12)
axes[0, 1].legend(fontsize=9, loc='upper right')
axes[0, 1].grid(True, alpha=0.3, axis='y')

# 7.3 各群客户数量
cluster_counts = df['客户分群'].value_counts().sort_index()
axes[1, 0].bar(cluster_counts.index.astype(str), cluster_counts.values, 
              color=colors, edgecolor='white', linewidth=2)
for i, v in enumerate(cluster_counts.values):
    axes[1, 0].text(i, v + 5, str(v), ha='center', fontsize=12, fontweight='bold')
axes[1, 0].set_title('各客户群数量', fontsize=14)
axes[1, 0].set_xlabel('客户群', fontsize=12)
axes[1, 0].set_ylabel('客户数量', fontsize=12)
axes[1, 0].grid(True, alpha=0.3, axis='y')

# 7.4 年龄 vs 收入散点图
for i in range(best_k):
    mask = df['客户分群'] == i
    axes[1, 1].scatter(df[mask]['年龄'], df[mask]['年收入(万)'],
                      c=colors[i], label=f'客户群 {i}', alpha=0.6, s=50)
axes[1, 1].set_xlabel('年龄', fontsize=12)
axes[1, 1].set_ylabel('年收入(万)', fontsize=12)
axes[1, 1].set_title('年龄 vs 收入', fontsize=14)
axes[1, 1].legend(fontsize=10)
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('customer_segmentation.png', dpi=150, bbox_inches='tight')
plt.close()
print("已保存图片: customer_segmentation.png")

# ========== 8. 详细分析报告 ==========
print("\n" + "=" * 60)
print("          客户分群详细分析报告")
print("=" * 60)

for i in range(best_k):
    cluster_data = df[df['客户分群'] == i]
    print(f"\n{'─' * 50}")
    print(f"📊 客户群 {i} (共 {len(cluster_data)} 人, 占比 {len(cluster_data)/len(df)*100:.1f}%)")
    print(f"{'─' * 50}")
    for col in columns:
        mean_val = cluster_data[col].mean()
        std_val = cluster_data[col].std()
        print(f"  {col:12s}: {mean_val:8.2f} ± {std_val:.2f}")
    
    # 自动分析客户特征
    print(f"\n  🏷️  客户画像:")
    if cluster_data['年龄'].mean() < 35:
        print(f"     → 年轻群体 (平均年龄 {cluster_data['年龄'].mean():.0f} 岁)")
    elif cluster_data['年龄'].mean() > 50:
        print(f"     → 中老年群体 (平均年龄 {cluster_data['年龄'].mean():.0f} 岁)")
    else:
        print(f"     → 中年群体 (平均年龄 {cluster_data['年龄'].mean():.0f} 岁)")
    
    if cluster_data['年收入(万)'].mean() > 60:
        print(f"     → 高收入群体 (平均年收入 {cluster_data['年收入(万)'].mean():.0f} 万)")
    elif cluster_data['年收入(万)'].mean() < 40:
        print(f"     → 低收入群体 (平均年收入 {cluster_data['年收入(万)'].mean():.0f} 万)")
    
    if cluster_data['平均消费金额'].mean() > 1500:
        print(f"     → 高消费群体 (平均消费 {cluster_data['平均消费金额'].mean():.0f} 元)")
    elif cluster_data['平均消费金额'].mean() < 800:
        print(f"     → 低消费群体 (平均消费 {cluster_data['平均消费金额'].mean():.0f} 元)")

# ========== 9. 营销策略建议 ==========
print("\n" + "=" * 60)
print("          营销策略建议")
print("=" * 60)

strategies = {
    0: "高频互动 + 专属折扣",
    1: "家庭套餐 + 会员积分",
    2: "新人优惠 + 社交分享",
    3: "高端服务 + 专属客服"
}

for i in range(best_k):
    print(f"\n🎯 客户群 {i}: {strategies.get(i, '待制定策略')}")

print("\n✅ Day 111 客户分群实战完成！")
