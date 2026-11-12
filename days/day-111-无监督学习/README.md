# Day 111 — 无监督学习：K-Means 聚类与 PCA 降维

## 📚 学习目标

1. 理解无监督学习的核心思想
2. 掌握 K-Means 聚类算法原理与实现
3. 掌握 PCA 降维原理与可视化
4. 实战：客户分群应用

---

## 一、概念解释

### 1.1 无监督学习定义

**无监督学习（Unsupervised Learning）** 是机器学习的一个重要分支，其核心特点是 **训练数据没有标签**。算法需要自行发现数据中的隐藏结构、模式和规律。

与监督学习对比：

| 特性 | 监督学习 | 无监督学习 |
|------|---------|-----------|
| 数据 | 有标签（X, y） | 无标签（仅 X） |
| 目标 | 预测已知输出 | 发现隐藏结构 |
| 评估 | 准确率、MSE 等 | 轮廓系数、SSE 等 |
| 典型任务 | 分类、回归 | 聚类、降维、异常检测 |

**无监督学习的主要应用场景：**

- **聚类（Clustering）**：将相似的数据点分组
- **降维（Dimensionality Reduction）**：减少特征数量，保留主要信息
- **异常检测（Anomaly Detection）**：发现异常数据点
- **关联规则（Association Rules）**：发现数据项之间的关联

### 1.2 K-Means 聚类

**K-Means** 是最经典的聚类算法之一，目标是将 n 个数据点划分为 K 个簇（cluster），使得每个数据点属于距其最近的簇中心（centroid）。

**核心思想：** 最小化簇内平方误差（Within-Cluster Sum of Squares, WCSS）：

$$
J = \sum_{k=1}^{K} \sum_{x_i \in C_k} \| x_i - \mu_k \|^2
$$

其中：
- $C_k$ 是第 k 个簇
- $\mu_k$ 是第 k 个簇的中心（均值）
- $\| x_i - \mu_k \|^2$ 是数据点到簇中心的欧氏距离平方

### 1.3 PCA 降维

**PCA（Principal Component Analysis，主成分分析）** 是最常用的线性降维方法。它通过正交变换，将原始高维数据投影到低维空间，同时最大化保留数据的方差。

**核心思想：**
- 找到数据方差最大的方向（主成分）
- 主成分之间相互正交（不相关）
- 第一主成分方差最大，第二主成分次之，依此类推

---

## 二、原理解释

### 2.1 K-Means 算法步骤

K-Means 算法采用迭代优化策略：

```
步骤 1：初始化
  - 随机选择 K 个数据点作为初始簇中心

步骤 2：分配（Assignment）
  - 对每个数据点，计算其到所有簇中心的距离
  - 将数据点分配到最近的簇中心所代表的簇

步骤 3：更新（Update）
  - 重新计算每个簇的中心（取簇内所有点的均值）

步骤 4：判断收敛
  - 如果簇中心不再变化（或变化小于阈值），则算法收敛
  - 否则，返回步骤 2 继续迭代
```

**K-Means 的变体：**

| 变体 | 特点 |
|------|------|
| K-Means++ | 更好的初始化策略，选择远离已有中心的点 |
| Mini-Batch K-Means | 每次用小批量数据更新，加速大数据集 |
| Bisecting K-Means | 二分层次聚类，自顶向下分裂 |

**K-Means 的优缺点：**

优点：
- 算法简单，易于实现
- 计算效率高，时间复杂度 O(n·K·t)
- 适合球形簇

缺点：
- 需要预先指定 K 值
- 对初始化敏感，可能陷入局部最优
- 对噪声和异常值敏感
- 只能发现凸形簇，无法处理复杂形状

### 2.2 PCA 数学原理

PCA 的核心是 **特征值分解（Eigendecomposition）**：

**步骤：**

1. **中心化数据**：减去均值，使数据均值为 0

2. **计算协方差矩阵**：

$$
C = \frac{1}{n-1} X^T X
$$

3. **特征值分解**：求解协方差矩阵的特征值和特征向量

$$
C v_i = \lambda_i v_i
$$

其中：
- $\lambda_i$ 是第 i 个特征值（代表方差大小）
- $v_i$ 是对应的特征向量（主成分方向）

4. **选择主成分**：按特征值从大到小排列，选择前 d 个特征向量

5. **投影**：将数据投影到选定的主成分上

$$
Z = X W_d
$$

其中 $W_d$ 是由前 d 个特征向量组成的矩阵。

### 2.3 肘部法则（Elbow Method）

肘部法则是选择最佳 K 值的常用方法：

**原理：**
- 计算不同 K 值下的 WCSS（簇内平方和）
- 随着 K 增大，WCSS 会减小（极端情况下 K=n 时 WCSS=0）
- 当 K 增大到某个值后，WCSS 的下降速度明显变缓，形成"肘部"
- 肘部对应的 K 值通常是最佳选择

**评估指标：**

| 指标 | 说明 | 范围 |
|------|------|------|
| SSE/Inertia | 簇内平方和 | 越小越好 |
| 轮廓系数 | 衡量簇内紧凑度与簇间分离度 | [-1, 1]，越大越好 |
| Calinski-Harabasz | 方差比准则 | 越大越好 |

---

## 三、API 速查

### 3.1 sklearn.cluster.KMeans

```python
from sklearn.cluster import KMeans

# 创建 KMeans 模型
kmeans = KMeans(
    n_clusters=3,           # 簇的数量 K
    init='k-means++',       # 初始化方法: 'k-means++', 'random', 或 ndarray
    n_init=10,              # 不同初始化运行次数，取最优
    max_iter=300,           # 最大迭代次数
    random_state=42,        # 随机种子
    algorithm='lloyd'       # 算法: 'lloyd', 'elkan'
)

# 训练模型（拟合数据）
kmeans.fit(X)

# 或一步完成拟合和预测
labels = kmeans.fit_predict(X)

# 预测新数据所属的簇
new_labels = kmeans.predict(X_new)

# 获取属性
centers = kmeans.cluster_centers_   # 簇中心坐标
inertia = kmeans.inertia_           # WCSS 值
n_iter = kmeans.n_iter_             # 实际迭代次数
labels = kmeans.labels_             # 每个样本的簇标签

# 评估
from sklearn.metrics import silhouette_score
score = silhouette_score(X, labels)  # 轮廓系数
```

### 3.2 sklearn.decomposition.PCA

```python
from sklearn.decomposition import PCA

# 创建 PCA 模型
pca = PCA(
    n_components=2,          # 保留的主成分数量
    copy=True,               # 是否复制数据
    whiten=False,            # 是否白化（归一化特征值）
    svd_solver='auto',       # SVD 求解器: 'auto', 'full', 'arpack', 'randomized'
    random_state=42
)

# 拟合并转换数据
X_pca = pca.fit_transform(X)

# 或分步操作
pca.fit(X)
X_pca = pca.transform(X)

# 获取属性
components = pca.components_        # 主成分方向（特征向量）
explained_var = pca.explained_variance_         # 各主成分的方差
explained_ratio = pca.explained_variance_ratio_ # 方差解释比例
cumsum = pca.explained_variance_ratio_.cumsum() # 累积方差比例

# 反向转换（从降维空间回到原始空间）
X_inverse = pca.inverse_transform(X_pca)

# 选择使累积方差达到阈值的 n_components
from sklearn.decomposition import PCA
pca = PCA(n_components=0.95)  # 保留 95% 的方差
```

---

## 四、图解

> 📊 详细的 Mermaid 流程图请查看 [diagrams/README.md](diagrams/README.md)

### K-Means 迭代过程（文字描述）

```
初始状态        →  第一次迭代      →  第二次迭代      →  收敛
随机3个中心       重新分配数据点      重新计算中心       中心不再变化
未分组数据        形成初始簇          优化簇边界        最终聚类结果
```

### PCA 降维原理（文字描述）

```
原始2D数据  →  计算协方差矩阵  →  特征值分解  →  选择主成分  →  投影到1D
(x1, x2)      2×2矩阵          特征值+特征向量   方差最大的方向   保留主要信息
```

---

## 五、实战代码案例：客户分群

### 场景说明

某电商平台拥有客户数据，包含：
- 年龄、收入、消费频率、平均消费金额等特征

目标：根据客户特征将客户分为不同群体，实施精准营销策略。

### 完整代码

```python
"""
客户分群实战 - 基于 K-Means 和 PCA 的客户细分
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# ========== 1. 生成模拟客户数据 ==========
np.random.seed(42)
n_customers = 500

# 生成 4 类客户
# 客户类型1: 年轻高收入高消费
group1 = np.random.randn(125, 4) * [5, 20, 2, 500] + [28, 80, 8, 2000]
# 客户类型2: 中年中收入中消费
group2 = np.random.randn(125, 4) * [8, 15, 3, 300] + [45, 50, 5, 1000]
# 客户类型3: 年轻低收入低消费
group3 = np.random.randn(125, 4) * [5, 10, 2, 200] + [25, 30, 3, 500]
# 客户类型4: 高龄高收入高消费
group4 = np.random.randn(125, 4) * [3, 25, 2, 400] + [58, 70, 6, 1500]

data = np.vstack([group1, group2, group3, group4])
np.random.shuffle(data)

df = pd.DataFrame(data, columns=['年龄', '年收入(万)', '月消费频次', '平均消费金额'])
print("=== 数据概览 ===")
print(df.describe().round(2))
print(f"\n数据维度: {df.shape}")

# ========== 2. 数据标准化 ==========
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df)

# ========== 3. 肘部法则选择最佳 K ==========
inertias = []
silhouette_scores = []
K_range = range(2, 11)

for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    inertias.append(kmeans.inertia_)
    silhouette_scores.append(silhouette_score(X_scaled, labels))
    print(f"K={k}: Inertia={kmeans.inertia_:.2f}, Silhouette={silhouette_scores[-1]:.4f}")

# 绘制肘部法则图
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
plt.savefig('elbow_method.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n已保存肘部法则图: elbow_method.png")

# ========== 4. 训练 K-Means 模型（K=4） ==========
best_k = 4
kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
df['客户分群'] = kmeans.fit_predict(X_scaled)

print(f"\n=== K-Means 聚类结果 (K={best_k}) ===")
print(f"轮廓系数: {silhouette_score(X_scaled, df['客户分群']):.4f}")
print(f"\n各簇客户数量:")
print(df['客户分群'].value_counts().sort_index())

# ========== 5. PCA 降维可视化 ==========
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

print(f"\n=== PCA 降维结果 ===")
print(f"第一主成分方差解释比例: {pca.explained_variance_ratio_[0]:.4f}")
print(f"第二主成分方差解释比例: {pca.explained_variance_ratio_[1]:.4f}")
print(f"累积方差解释比例: {pca.explained_variance_ratio_.sum():.4f}")

# 可视化
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 左图：按聚类结果着色
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
for i in range(best_k):
    mask = df['客户分群'] == i
    axes[0].scatter(X_pca[mask, 0], X_pca[mask, 1], 
                   c=colors[i], label=f'客户群 {i}', alpha=0.6, s=50, edgecolors='white')

axes[0].scatter(pca.transform(scaler.transform(kmeans.cluster_centers_))[:, 0],
               pca.transform(scaler.transform(kmeans.cluster_centers_))[:, 1],
               c='black', marker='X', s=200, label='簇中心', zorder=5)
axes[0].set_xlabel('第一主成分', fontsize=12)
axes[0].set_ylabel('第二主成分', fontsize=12)
axes[0].set_title('K-Means 客户分群结果 (PCA 降维)', fontsize=14)
axes[0].legend(fontsize=10)
axes[0].grid(True, alpha=0.3)

# 右图：各簇特征分析
cluster_stats = df.groupby('客户分群').mean()
cluster_stats.plot(kind='bar', ax=axes[1], width=0.8)
axes[1].set_title('各客户群特征对比', fontsize=14)
axes[1].set_xlabel('客户群', fontsize=12)
axes[1].set_ylabel('平均值', fontsize=12)
axes[1].legend(fontsize=9)
axes[1].grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('customer_segmentation.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n已保存分群结果图: customer_segmentation.png")

# ========== 6. 客户群分析报告 ==========
print("\n" + "=" * 60)
print("          客户分群分析报告")
print("=" * 60)

for i in range(best_k):
    cluster_data = df[df['客户分群'] == i]
    print(f"\n📊 客户群 {i} (共 {len(cluster_data)} 人)")
    print(f"   年龄: {cluster_data['年龄'].mean():.1f} ± {cluster_data['年龄'].std():.1f}")
    print(f"   年收入: {cluster_data['年收入(万)'].mean():.1f} ± {cluster_data['年收入(万)'].std():.1f} 万")
    print(f"   月消费频次: {cluster_data['月消费频次'].mean():.1f} ± {cluster_data['月消费频次'].std():.1f}")
    print(f"   平均消费金额: {cluster_data['平均消费金额'].mean():.0f} ± {cluster_data['平均消费金额'].std():.0f}")

print("\n" + "=" * 60)
```

---

## 六、思考题

### 思考题 1：K-Means 初始化的影响

> K-Means 对初始簇中心的选择很敏感。如果初始化不好，可能导致收敛到局部最优解。
> 请思考：
> - 为什么 K-Means++ 能缓解这个问题？
> - 除了 K-Means++，还有什么方法可以改善初始化？

**参考答案**

K-Means 随机选初始中心，若两个中心落在同一个真实簇里、或选到异常值，就会收敛到 WCSS 偏高的**局部最优**，分错簇。

**K-Means++** 让初始中心尽量分散：第一个随机选，之后每个新中心按「到已选中心的最近距离 D(x)²」为概率来选——离已有中心越远越可能被选中。于是种子更可能落进不同的真实簇，得到更好的局部最优、收敛更快更稳。

其他改善办法：
- **多次重启**（`n_init=10`，取 inertia 最小的一次）——sklearn 默认就这么做。
- **二分 K-Means**（自顶向下逐次分裂）、层次聚类或 canopy 聚类先给出种子。
- 先剔除异常值，或用领域知识指定初始中心。

小例子：3 个分得很开的团，随机初始化可能把 2 个中心放进同一团 → 合并了两类；K-Means++ 种子分散 → 正确分开。

### 思考题 2：K 值选择

> 假设你有一个包含 1000 个客户的数据集，你想做客户分群。
> - 肘部法则显示 K=3 和 K=5 都有"肘部"，该如何选择？
> - 如何结合业务目标来确定 K 值？

**参考答案**

肘部不明显（K=3 和 K=5 都像肘部）时，**别只靠肘部**：再看轮廓系数（取更高者）、Calinski-Harabasz、gap statistic，并检查分群在子采样下是否稳定。

更重要的是**结合业务**：K 要对应「能落地执行」的客群。如果营销只能跑 3 个活动，K=3 更有用，哪怕 K=5 拟合略好；如果确实存在 5 种行为迥异、各需一套策略的客群，就选 5。还要看可解释性和簇大小（避免出现没意义的极小簇）。

小例子：K=3 给出「高/中/低价值」三群，便于直接行动；K=5 进一步细分但其中两群人数极少、不值得单独运营 → 选 3。

💡 提示：肘部只是启发式，不是标准答案；让业务目标 + 轮廓系数 + 稳定性共同决定。

### 思考题 3：PCA 降维的信息损失

> PCA 降维会丢失一部分信息。假设原始数据有 10 个特征，PCA 保留了前 3 个主成分，累积方差解释比例为 85%。
> - 这意味着丢失了什么？
> - 在什么场景下，85% 的方差解释比例可能不够？

**参考答案**

保留 85% 方差，意味着丢掉的 7 个主成分承载了剩余 **15% 的方差**——也就是数据里「变化最小」的那些方向上的信息。重建误差约等于这 15%。

丢的是什么：可能是噪声，但也可能是**有意义的细微信号**。方差小 ≠ 不重要——某些区分类别的关键差异恰恰藏在低方差方向里。

85% 不够的场景：
- **异常/欺诈检测**：异常点往往体现在低方差方向，降维可能把它抹掉。
- **细粒度分类**：类别间差异细微，依赖被丢掉的成分。
- **医学/科学测量**等需要高精度的任务。
- 下游任务恰好依赖主要落在被丢成分里的特征。

小例子：欺诈只占 0.1%，其判别信号是个低方差方向 → PCA 保 85% 可能把它消除 → 检测器失效。

💡 提示：按下游任务选 `n_components`（精度任务常要 95%~99%），别套固定比例；PCA 是无监督的，高方差不等于对标签高相关。

### 思考题 4：K-Means 的局限性

> 以下哪种数据分布 K-Means 无法正确聚类？为什么？
> A. 同心圆环形分布
> B. 三个紧密的球形簇
> C. 密度均匀的矩形区域
> D. 所有数据均匀分布在一个圆内

**参考答案**

答案是 **A（同心圆环形分布）**。

K-Means 假设簇是**凸形、大致球形**、按「到中心的距离」可分。同心圆的内环和外环共享同一片中心区域，K-Means 只能按径向切成两块，把内外环混在一起，无法正确分开。B（三个紧密球形簇）正是 K-Means 的理想输入；C、D 是均匀分布、**本就没有真实簇结构**，K-Means 仍会切成凸块，但「正确聚类」无从谈起，不是本题的典型失败情形。

环形数据可改用 **DBSCAN（基于密度）、谱聚类或核 K-Means**。下面实测对比（需 `pip install scikit-learn`）：

```python
from sklearn.datasets import make_circles
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import adjusted_rand_score

# 同心圆环：内环一类、外环一类（非凸分布）
X, y_true = make_circles(n_samples=400, factor=0.4, noise=0.05, random_state=42)

km = KMeans(n_clusters=2, n_init=10, random_state=42).fit(X)
db = DBSCAN(eps=0.2, min_samples=5).fit(X)

# ARI（调整兰德指数）：衡量聚类与真实标签的吻合度，1 表示完全一致
print(f"KMeans ARI = {adjusted_rand_score(y_true, km.labels_):.3f}")
print(f"DBSCAN ARI = {adjusted_rand_score(y_true, db.labels_):.3f}")
```

预期输出（数值因机器/版本而异）：

```
KMeans ARI = -0.002
DBSCAN ARI = 1.000
```

KMeans 的 ARI≈0（和随机差不多，彻底失败），DBSCAN 的 ARI=1（完美分开内外环）。

### 思考题 5：降维与聚类的结合

> 在实战中，我们经常先用 PCA 降维再用 K-Means 聚类。请思考：
> - 先降维再聚类 vs 先聚类再降维，哪种更好？为什么？
> - PCA 降维后的特征失去了原始特征的可解释性，这会带来什么问题？

**参考答案**

通常**先降维再聚类**更好：PCA 先去噪、去掉冗余/相关维度，缓解维度灾难，让距离更有意义，K-Means 更容易找到干净的簇，还更快。反过来「先聚类再降维」是在原始高维噪声空间里聚类，可能一开始就分错，之后的 PCA 只是把（可能错误的）簇画出来而已。

但要留意：PCA 是无监督的（只保方差），有时会丢掉恰好能分开簇的方向，必要时对比原始空间聚类或用有监督降维，并做验证。

**可解释性问题**：主成分是原始特征的线性组合，「PC1 高、PC2 低」很难翻译成业务语言（如「高收入、年轻」），导致无法向业务方解释客群、也难以落回可操作的原始特征。缓解：在 PCA 空间聚完类后，**用原始特征给每个簇画像**（算各簇的年龄/收入均值），或用 `inverse_transform`、查看载荷（loadings）来解释主成分。

小例子：在 2 维 PCA 上聚类，再报告每簇的原始平均收入/年龄 → 重新获得可解释性。

---

## 📚 延伸阅读

1. [scikit-learn KMeans 文档](https://scikit-learn.org/stable/modules/clustering.html#k-means)
2. [scikit-learn PCA 文档](https://scikit-learn.org/stable/modules/decomposition.html#pca)
3. 《统计学习方法》李航 — 聚类算法章节
4. 《Python 机器学习》Sebastian Raschka — 无监督学习章节
