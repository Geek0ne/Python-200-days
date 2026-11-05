# Day 122 — 推荐系统基础

> 推荐系统是信息过载时代的核心技术，让用户从海量内容中快速找到感兴趣的内容。

---

## 1. 推荐系统概述

### 1.1 什么是推荐系统

推荐系统（Recommendation System）是一种信息过滤系统，通过分析用户行为和物品特征，预测用户可能感兴趣的物品并进行推荐。

### 1.2 推荐系统的应用场景

| 场景 | 示例 | 核心目标 |
|------|------|----------|
| 电商 | 淘宝、京东「猜你喜欢」 | 提升购买转化率 |
| 视频 | B站、YouTube 推荐流 | 增加观看时长 |
| 音乐 | Spotify、网易云音乐 | 发现新音乐 |
| 社交 | 微博、抖音推荐 | 增加用户留存 |
| 新闻 | 今日头条、即刻 | 提升阅读量 |

### 1.3 推荐系统分类

```
推荐系统
├── 基于内容的推荐 (Content-Based)
│   └── 利用物品属性特征进行推荐
├── 协同过滤推荐 (Collaborative Filtering)
│   ├── 基于用户的协同过滤 (User-Based CF)
│   ├── 基于物品的协同过滤 (Item-Based CF)
│   └── 矩阵分解 (Matrix Factorization)
├── 混合推荐 (Hybrid)
│   └── 结合多种方法
└── 深度学习推荐
    ├── Wide & Deep
    ├── DeepFM
    └── 双塔模型
```

---

## 2. 基于内容的推荐（Content-Based Filtering）

### 2.1 原理

核心思想：**「你喜欢这个，那你应该也喜欢和它相似的物品」**

工作流程：
1. 提取物品的内容特征（如电影的类型、导演、演员）
2. 构建用户画像（用户喜欢过的物品的特征聚合）
3. 计算用户画像与候选物品的相似度
4. 推荐相似度最高的物品

### 2.2 优缺点

**优点：**
- 不需要其他用户的数据
- 可以推荐新物品（冷启动友好）
- 推荐结果可解释性强

**缺点：**
- 特征工程成本高
- 推荐结果多样性差（信息茧房）
- 无法发现用户潜在兴趣

---

## 3. 协同过滤（Collaborative Filtering）

### 3.1 核心思想

**「和你品味相似的人喜欢的，你也可能喜欢」**

协同过滤不依赖物品的内容信息，纯粹基于用户的历史行为数据（评分、点击、购买等）进行推荐。

### 3.2 基于用户的协同过滤（User-Based CF）

#### 原理
1. 找到与目标用户行为相似的用户群（邻居）
2. 用邻居的评分预测目标用户对未见过物品的评分
3. 推荐预测评分最高的物品

#### 相似度计算

**余弦相似度（Cosine Similarity）：**

```
sim(u, v) = cos(⃗u, ⃗v) = (Σ uᵢ × vᵢ) / (√Σuᵢ² × √Σvᵢ²)
```

**皮尔逊相关系数（Pearson Correlation）：**

```
sim(u, v) = Σ(uᵢ - ū)(vᵢ - v̄) / (√Σ(uᵢ-ū)² × √Σ(vᵢ-v̄)²)
```

#### 预测评分

```
pred(u, i) = r̄ᵤ + Σ sim(u, v) × (rᵥᵢ - r̄ᵥ) / Σ |sim(u, v)|
```

其中：
- `r̄ᵤ` 是用户 u 的平均评分
- `sim(u, v)` 是用户 u 和 v 的相似度
- `rᵥᵢ` 是用户 v 对物品 i 的评分
- `r̄ᵥ` 是用户 v 的平均评分

### 3.3 基于物品的协同过滤（Item-Based CF）

#### 原理
1. 计算物品之间的相似度（基于所有用户对它们的评分）
2. 根据用户历史评分过的物品，推荐最相似的物品

#### 为什么 Item-Based 通常比 User-Based 好？

| 对比维度 | User-Based CF | Item-Based CF |
|----------|---------------|---------------|
| 稳定性 | 用户兴趣变化快，邻居不稳定 | 物品属性相对稳定 |
| 可扩展性 | 用户数量通常远大于物品数 | 物品数相对较少 |
| 可解释性 | "和你相似的人喜欢" | "因为你喜欢A，所以推荐B" |
| 时效性 | 实时性要求高 | 可离线预计算 |

### 3.4 评分矩阵

推荐系统的核心数据结构是 **用户-物品评分矩阵**：

```
          电影A  电影B  电影C  电影D  电影E
用户1       5      3      4      4      ?
用户2       3      1      2      3      3
用户3       4      3      4      3      5
用户4       3      3      1      5      4
用户5       1      5      5      2      1

问题：用户1 对电影E 的评分是多少？
```

这个矩阵通常是 **非常稀疏** 的（大部分用户只看过少量物品），这也是推荐系统面临的核心挑战之一。

---

## 4. 矩阵分解（Matrix Factorization）

### 4.1 原理

矩阵分解将稀疏的用户-物品评分矩阵分解为两个低维矩阵的乘积：

```
R ≈ P × Qᵀ

其中：
R: m×n 评分矩阵（m个用户，n个物品）
P: m×k 用户特征矩阵（k为隐因子数）
Q: n×k 物品特征矩阵
```

### 4.2 直觉理解

假设 k=2（两个隐因子），对于电影推荐：
- 隐因子1 可能代表「动作程度」
- 隐因子2 可能代表「浪漫程度」

```
用户特征矩阵 P:
          动作  浪漫
用户1     0.9   0.1    ← 喜欢动作片
用户2     0.2   0.8    ← 喜欢浪漫片

物品特征矩阵 Q:
          动作  浪漫
电影A     0.8   0.2    ← 动作片
电影B     0.3   0.9    ← 浪漫片

预测评分 = P × Qᵀ
用户1对电影A = 0.9×0.8 + 0.1×0.2 = 0.74 (高分)
用户1对电影B = 0.9×0.3 + 0.1×0.9 = 0.36 (低分)
```

### 4.3 SVD（奇异值分解）

SVD 是矩阵分解的经典方法：

```
R = U × Σ × Vᵀ

U: 用户奇异向量矩阵
Σ: 奇异值对角矩阵（表示每个隐因子的重要性）
V: 物品奇异向量矩阵
```

实际应用中，通常使用 **截断SVD**（只保留前k个最大的奇异值）来降维。

### 4.4 ALS（交替最小二乘法）

ALS 是训练矩阵分解模型的常用算法：

```
目标：min Σ (rᵤᵢ - pᵤ·qᵢ)² + λ(||pᵤ||² + ||qᵢ||²)

交替优化：
1. 固定 Q，优化 P
2. 固定 P，优化 Q
3. 重复直到收敛
```

**优点：** 可以并行化，适合大规模数据
**缺点：** 需要调参（隐因子数k、正则化λ）

---

## 5. 评估指标

### 5.1 准确性指标

| 指标 | 公式 | 说明 |
|------|------|------|
| MAE | Σ\|rᵤᵢ - r̂ᵤᵢ\| / n | 平均绝对误差 |
| RMSE | √(Σ(rᵤᵢ - r̂ᵤᵢ)² / n) | 均方根误差 |
| Precision@K | 推荐列表中相关物品数 / K | 前K个推荐的准确率 |
| Recall@K | 推荐列表中相关物品数 / 相关物品总数 | 前K个推荐的召回率 |

### 5.2 排序指标

| 指标 | 说明 |
|------|------|
| MAP | 平均精度均值 |
| NDCG | 归一化折扣累积增益 |
| MRR | 平均倒数排名 |

### 5.3 覆盖率与多样性

- **覆盖率**：推荐系统能够推荐的物品占总物品库的比例
- **多样性**：推荐列表中物品之间的差异程度
- **新颖度**：推荐不那么流行的物品的能力

---

## 6. 冷启动问题

### 6.1 新用户冷启动

新用户没有历史行为数据，无法进行协同过滤。

**解决方案：**
- 收集用户注册时的兴趣标签
- 利用人口统计学信息（年龄、性别、地区）
- 使用基于内容的推荐
- 推荐热门/流行物品
- 使用 Bandit 算法探索

### 6.2 新物品冷启动

新物品没有被任何用户评分/交互过。

**解决方案：**
- 利用物品的内容特征
- 利用物品的元数据（标题、标签、描述）
- 编辑推荐/人工运营

### 6.3 系统冷启动

新系统没有任何用户和交互数据。

**解决方案：**
- 从简单规则开始（热门推荐）
- 收集反馈数据后逐步引入复杂算法
- 利用第三方数据

---

## 7. 使用 Surprise 库实战

### 7.1 安装

```bash
pip install scikit-surprise
```

### 7.2 API 速查

```python
from surprise import Dataset, Reader, SVD, KNNBasic
from surprise.model_selection import cross_validate, train_test_split

# 1. 加载数据
reader = Reader(rating_scale=(1, 5))
data = Dataset.load_from_df(df[['user_id', 'item_id', 'rating']], reader)

# 2. 划分训练集/测试集
trainset, testset = train_test_split(data, test_size=0.2)

# 3. 选择算法
algo = SVD(n_factors=100, n_epochs=20, lr_all=0.005, reg_all=0.02)

# 4. 训练
algo.fit(trainset)

# 5. 预测
prediction = algo.predict(uid='user1', iid='movie1')

# 6. 评估
cross_validate(algo, data, measures=['RMSE', 'MAE'], cv=5, verbose=True)

# 7. 获取推荐
def get_top_n(algo, trainset, user_id, n=10):
    """为指定用户推荐 top-n 物品"""
    # 获取用户未评分的物品
    user_items = set(trainset.ur[trainset.to_inner_uid(user_id)])
    all_items = set(trainset.all_items())
    candidate_items = all_items - user_items
    
    # 预测评分
    predictions = []
    for item_inner in candidate_items:
        item_raw = trainset.to_raw_iid(item_inner)
        pred = algo.predict(user_id, item_raw)
        predictions.append((item_raw, pred.est))
    
    # 按预测评分排序
    predictions.sort(key=lambda x: x[1], reverse=True)
    return predictions[:n]
```

---

## 8. 实战：电影推荐系统

下面的代码示例实现了一个完整的电影推荐系统：
- `01-collaborative-filtering-basics.py`：协同过滤基础
- `02-matrix-factorization-svd.py`：矩阵分解 SVD
- `03-movie-recommender.py`：完整电影推荐系统

---

## 9. 思考题

1. **为什么协同过滤在实际应用中往往比基于内容的推荐效果更好？** 从数据利用和用户行为的角度思考。

2. **矩阵分解中的隐因子（latent factor）有什么实际含义？** 能否举例说明在音乐推荐中，隐因子可能代表什么？

3. **如何解决推荐系统中的「马太效应」？** 即热门物品越来越热，冷门物品越来越冷的问题。

4. **Item-Based CF 和 User-Based CF 各适合什么场景？** 如果是一个新上线的短视频平台，你会选择哪种？为什么？

5. **冷启动问题在实际产品中是如何解决的？** 结合你使用过的 App，举例说明它们是如何处理新用户推荐的。

---

## 参考资料

- [Surprise 官方文档](http://surpriselib.com/)
- [《推荐系统实践》- 项亮](https://book.douban.com/subject/10765214/)
- [Netflix Prize 经典论文](https://datajobs.com/data-science-repo/Recommender-Systems-%5BNetflix%5D.pdf)
- [RecBole 推荐系统框架](https://recbole.io/)
