# Day 109 — 决策树与随机森林

> **阶段**: Phase 7 — 进阶与性能优化
> **子主题**: 机器学习实战
> **预计时长**: 2-3 小时

---

## 📚 目录

1. [决策树原理](#1-决策树原理)
2. [信息增益与基尼系数](#2-信息增益与基尼系数)
3. [可视化决策树](#3-可视化决策树)
4. [随机森林 Bagging 集成](#4-随机森林-bagging-集成)
5. [特征重要性分析](#5-特征重要性分析)
6. [实战：信用风险评估](#6-实战信用风险评估)
7. [思考题](#7-思考题)

---

## 1. 决策树原理

### 1.1 什么是决策树

决策树（Decision Tree）是一种**非参数的监督学习算法**，可用于分类和回归任务。它的核心思想非常直观：通过一系列 if-else 规则将数据逐步分割，最终形成一棵树状结构。

```
                    ┌─────────────────┐
                    │   年收入 > 5万?  │
                    └────────┬────────┘
                   是 ↙            ↘ 否
              ┌──────────┐    ┌──────────┐
              │ 负债 < 2万? │    │ 信用评分? │
              └─────┬────┘    └─────┬────┘
             是 ↙       ↘      优/良    差
        ┌──────┐  ┌──────┐  ┌──────┐ ┌──────┐
        │ 通过 │  │ 拒绝 │  │ 通过 │ │ 拒绝 │
        └──────┘  └──────┘  └──────┘ └──────┘
```

### 1.2 为什么决策树有效

**人类天然的决策方式**：决策树模拟了人类做决策的过程——逐步排除不确定因素，直到得出结论。

**三大优势**：
- **可解释性强**：每一步决策都清晰可见，不像神经网络是"黑箱"
- **无需特征缩放**：不受量纲影响，不需要标准化
- **处理混合类型**：天然支持数值特征和类别特征

**设计原理**：
- 每次分裂都选择**最优特征**和**最优切分点**，使得分裂后的子节点纯度最高
- 这是一个**贪心算法**——每一步都做局部最优选择，但不保证全局最优

### 1.3 决策树的构建过程

```
数据集 D
  │
  ├── 1. 选择最优分裂特征 F 和切分点 S
  │     （基于信息增益 / 基尼系数）
  │
  ├── 2. 将 D 分为 D_left 和 D_right
  │
  ├── 3. 对 D_left 和 D_right 递归执行 1-2
  │
  └── 4. 满足停止条件时，生成叶节点
        （节点样本数 < min_samples_split
         或 树深度 >= max_depth
         或 纯度足够高）
```

### 1.4 决策树的关键概念

| 概念 | 说明 |
|------|------|
| **根节点 (Root)** | 树的第一个分裂点，包含所有样本 |
| **内部节点 (Internal)** | 有子节点的决策点 |
| **叶节点 (Leaf)** | 最终预测结果 |
| **分裂 (Split)** | 选择特征和阈值将数据分成两部分 |
| **深度 (Depth)** | 从根到叶的最大层数 |
| **纯度 (Purity)** | 节点中样本属于同一类的比例 |

---

## 2. 信息增益与基尼系数

决策树的核心问题是：**如何选择最优的分裂特征？**

### 2.1 信息增益（ID3 算法）

**信息熵（Entropy）**衡量数据集的"混乱程度"：

$$
H(D) = -\sum_{k=1}^{K} p_k \log_2(p_k)
$$

其中 $p_k$ 是第 $k$ 类样本的比例。

**信息增益（Information Gain）**：

$$
IG(D, A) = H(D) - \sum_{v \in Values(A)} \frac{|D_v|}{|D|} H(D_v)
$$

**直观理解**：信息增益越大，说明用特征 A 分裂后，子节点越"纯净"。

**例子**：
```
原始数据: 10个样本, 5个A类, 5个B类 → H(D) = 1.0 (最大混乱)

按特征X分裂后:
  左子节点: 8个样本, 全是A类 → H(左) = 0 (完全纯净!)
  右子节点: 2个样本, 全是B类 → H(右) = 0 (完全纯净!)

信息增益 = 1.0 - (8/10 × 0 + 2/10 × 0) = 1.0 ✅ 完美分裂
```

### 2.2 基尼系数（CART 算法）

CART（分类与回归树）使用基尼系数作为分裂标准：

$$
Gini(D) = 1 - \sum_{k=1}^{K} p_k^2
$$

**基尼系数的范围**：
- **最小值 0**：所有样本属于同一类（完全纯净）
- **最大值**：所有类等概率分布（最混乱）
  - 二分类: 0.5
  - K 类: 1 - 1/K

### 2.3 信息增益 vs 基尼系数

| 特性 | 信息增益 | 基尼系数 |
|------|---------|---------|
| **计算** | 需要 log 运算 | 只需平方运算 |
| **速度** | 较慢 | 较快 |
| **偏好多数类** | 是（C4.5 修正） | 轻微 |
| **默认使用** | ID3/C4.5 | CART (sklearn) |
| **实际差异** | 通常很小 | 通常很小 |

> 💡 **实际经验**：两者差异很小，sklearn 默认使用基尼系数，实际项目中无需纠结选择哪个。

### 2.4 回归树的分裂标准

对于回归任务，决策树使用**均方误差（MSE）**或**平均绝对误差（MAE）**：

$$
MSE = \frac{1}{n} \sum_{i=1}^{n} (y_i - \bar{y})^2
$$

分裂目标：找到使左右子节点 MSE 加权和最小的切分点。

---

## 3. 可视化决策树

### 3.1 为什么可视化很重要

决策树最大的优势就是**可解释性**。可视化让我们能：
- 理解模型的决策逻辑
- 向非技术人员解释模型
- 发现数据中的规律
- 排查模型异常

### 3.2 sklearn 的两种可视化方式

```python
from sklearn.tree import export_graphviz, plot_tree

# 方式1：plot_tree（推荐，直接在 matplotlib 中显示）
plot_tree(model, feature_names=feature_names, class_names=class_names,
          filled=True, rounded=True)

# 方式2：导出为 Graphviz 格式（更美观，但需要安装 graphviz）
export_graphviz(model, out_file='tree.dot', feature_names=feature_names,
                class_names=class_names, filled=True, rounded=True)
```

### 3.3 可视化参数速查

| 参数 | 作用 | 推荐值 |
|------|------|--------|
| `filled=True` | 用颜色表示类别 | ✅ 始终开启 |
| `rounded=True` | 圆角矩形 | ✅ 始终开启 |
| `feature_names` | 显示特征名 | ✅ 始终传入 |
| `class_names` | 显示类别名 | ✅ 分类任务必传 |
| `max_depth` | 限制显示深度 | 3-5（避免太深） |
| `fontsize` | 字体大小 | 8-12 |

---

## 4. 随机森林 Bagging 集成

### 4.1 从单棵树到森林

**单棵决策树的问题**：
- 容易过拟合（记住了训练数据的噪声）
- 对数据微小变化敏感（不稳定）
- 方差大

**解决方案**：集成多棵树，取平均/投票结果。

### 4.2 Bagging 原理

Bagging（Bootstrap Aggregating）的核心思想：

```
原始训练集 D (N个样本)
  │
  ├── 第1次: 有放回抽样 N 个样本 → 训练树1
  ├── 第2次: 有放回抽样 N 个样本 → 训练树2
  ├── 第3次: 有放回抽样 N 个样本 → 训练树3
  └── ...
  │
  最终预测 = 多数投票(树1, 树2, 树3, ...)  [分类]
           = 平均值(树1, 树2, 树3, ...)    [回归]
```

**为什么 Bagging 有效？**

每棵树约使用 **63.2%** 的原始样本（因为有放回抽样，约 36.8% 是 out-of-bag 样本）。

关键洞察：
- 每棵树是"弱学习器"（可能过拟合自己的子集）
- 但树之间**相关性低**（训练数据不同）
- 集成后**方差显著降低**，而偏差基本不变

### 4.3 随机森林的双重随机性

随机森林在 Bagging 基础上增加了一层随机性：

| 随机性 | 描述 | 效果 |
|--------|------|------|
| **数据随机** | Bootstrap 抽样（63.2% 样本） | 每棵树看到不同的数据 |
| **特征随机** | 每次分裂只考虑 √p 个特征（p 为总特征数） | 降低树之间的相关性 |

> 💡 **为什么需要特征随机？** 如果不加特征随机，所有树都会优先选择最强特征，导致树之间高度相关，集成效果大打折扣。

### 4.4 随机森林超参数

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(
    n_estimators=100,       # 树的数量（越多越好，但有收益递减）
    max_depth=None,         # 树的最大深度（None=不限制）
    min_samples_split=2,    # 分裂所需最小样本数
    min_samples_leaf=1,     # 叶节点最小样本数
    max_features='sqrt',    # 每次分裂考虑的特征数（分类默认 √p）
    bootstrap=True,         # 是否使用 Bootstrap 抽样
    oob_score=False,        # 是否计算 OOB 评分
    random_state=42,        # 随机种子
    n_jobs=-1,              # 并行训练的 CPU 核数
)
```

### 4.5 Out-of-Bag（OOB）评估

OOB 是 Bagging 的"免费午餐"——无需额外的验证集即可评估模型：

- 每棵树约有 36.8% 的样本未参与训练（OOB 样本）
- 用这些 OOB 样本对每棵树进行预测
- 汇总所有树的 OOB 预测，得到 OOB 评分

```python
rf = RandomForestClassifier(oob_score=True, random_state=42)
rf.fit(X_train, y_train)
print(f"OOB 评分: {rf.oob_score_:.4f}")
# OOB 评分 ≈ 交叉验证评分，无需额外划分验证集
```

### 4.6 Bagging vs Boosting 对比

| 特性 | Bagging（随机森林） | Boosting（GBDT/XGBoost） |
|------|-------------------|-------------------------|
| **训练方式** | 并行（独立训练） | 串行（依赖前序模型） |
| **降低的误差** | 方差 | 偏差 |
| **过拟合风险** | 较低 | 较高（需调参） |
| **训练速度** | 快（可并行） | 慢（串行） |
| **可解释性** | 一般 | 较差 |
| **典型代表** | 随机森林 | XGBoost, LightGBM |

---

## 5. 特征重要性分析

### 5.1 基于不纯度的重要性（MDI）

sklearn 默认使用**平均不纯度减少**（Mean Decrease in Impurity）：

```
特征重要性 = Σ (该特征参与的分裂带来的不纯度减少) / 树的总数
```

```python
importances = rf.feature_importances_
for name, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1]):
    print(f"{name}: {imp:.4f}")
```

**优点**：计算快，训练时顺便完成
**缺点**：对高基数特征有偏好（如 ID 列会得到高重要性）

### 5.2 基于排列的重要性（Permutation Importance）

更可靠的方法——通过打乱特征值观察模型性能下降：

```python
from sklearn.inspection import permutation_importance

result = permutation_importance(rf, X_test, y_test, n_repeats=10, random_state=42)
for name, imp in sorted(zip(feature_names, result.importances_mean), key=lambda x: -x[1]):
    print(f"{name}: {imp:.4f}")
```

**原理**：如果某个特征很重要，打乱它的值应该让模型性能大幅下降。

### 5.3 两种方法对比

| 特性 | MDI（不纯度） | Permutation |
|------|-------------|-------------|
| **计算时机** | 训练时 | 需要单独计算 |
| **计算速度** | 快 | 慢 |
| **偏差** | 偏向高基数特征 | 更客观 |
| **推荐场景** | 快速筛选 | 正式评估 |

---

## 6. 实战：信用风险评估

### 6.1 业务背景

银行需要根据客户的个人信息和财务数据，预测其是否会违约（信用风险评估）。

**特征说明**：
| 特征 | 类型 | 说明 |
|------|------|------|
| age | 数值 | 年龄 |
| income | 数值 | 年收入（万元） |
| debt_ratio | 数值 | 负债比率 |
| credit_score | 数值 | 信用评分 |
| employment_years | 数值 | 工作年限 |
| loan_amount | 数值 | 贷款金额（万元） |
| has_mortgage | 类别 | 是否有房贷 |
| education | 类别 | 教育程度 |

### 6.2 完整代码

```python
"""
Day 109 实战：信用风险评估
使用决策树和随机森林构建信用风险评估模型
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt

# ========== 1. 生成模拟数据 ==========
np.random.seed(42)
n_samples = 1000

data = pd.DataFrame({
    'age': np.random.randint(22, 65, n_samples),
    'income': np.random.lognormal(mean=3, sigma=0.6, size=n_samples).round(2),
    'debt_ratio': np.random.beta(2, 5, n_samples).round(3),
    'credit_score': np.random.randint(300, 850, n_samples),
    'employment_years': np.random.poisson(5, n_samples),
    'loan_amount': np.random.lognormal(mean=2, sigma=0.8, size=n_samples).round(2),
    'has_mortgage': np.random.choice(['yes', 'no'], n_samples, p=[0.3, 0.7]),
    'education': np.random.choice(['high_school', 'bachelor', 'master', 'phd'],
                                   n_samples, p=[0.3, 0.4, 0.2, 0.1]),
})

# 生成标签（基于业务逻辑 + 噪声）
risk_score = (
    -0.3 * (data['income'] / data['income'].max())
    + 0.4 * data['debt_ratio']
    - 0.2 * (data['credit_score'] / data['credit_score'].max())
    - 0.1 * (data['employment_years'] / data['employment_years'].max())
    + 0.2 * (data['loan_amount'] / data['loan_amount'].max())
    + np.random.normal(0, 0.15, n_samples)
)
data['default'] = (risk_score > np.percentile(risk_score, 70)).astype(int)

print("=" * 60)
print("📊 信用风险评估数据集")
print("=" * 60)
print(f"样本数: {len(data)}")
print(f"违约率: {data['default'].mean():.2%}")
print(f"\n特征统计:")
print(data.describe().round(2))

# ========== 2. 特征工程 ==========
# 编码类别特征
le_mortgage = LabelEncoder()
data['has_mortgage_encoded'] = le_mortgage.fit_transform(data['has_mortgage'])

le_education = LabelEncoder()
data['education_encoded'] = le_education.fit_transform(data['education'])

feature_names = ['age', 'income', 'debt_ratio', 'credit_score',
                 'employment_years', 'loan_amount', 'has_mortgage', 'education']
X = data[['age', 'income', 'debt_ratio', 'credit_score',
          'employment_years', 'loan_amount', 'has_mortgage_encoded', 'education_encoded']]
y = data['default']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n训练集: {len(X_train)} 样本")
print(f"测试集: {len(X_test)} 样本")

# ========== 3. 单棵决策树 ==========
print("\n" + "=" * 60)
print("🌳 单棵决策树")
print("=" * 60)

dt = DecisionTreeClassifier(max_depth=5, min_samples_split=20, random_state=42)
dt.fit(X_train, y_train)

train_score = dt.score(X_train, y_train)
test_score = dt.score(X_test, y_test)
print(f"训练集准确率: {train_score:.4f}")
print(f"测试集准确率: {test_score:.4f}")
print(f"过拟合差距: {train_score - test_score:.4f}")

print("\n分类报告:")
y_pred_dt = dt.predict(X_test)
print(classification_report(y_test, y_pred_dt, target_names=['正常', '违约']))

# ========== 4. 随机森林 ==========
print("=" * 60)
print("🌲 随机森林")
print("=" * 60)

rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=None,
    min_samples_split=5,
    min_samples_leaf=2,
    max_features='sqrt',
    random_state=42,
    n_jobs=-1,
    oob_score=True
)
rf.fit(X_train, y_train)

train_score_rf = rf.score(X_train, X_train)
test_score_rf = rf.score(X_test, y_test)
print(f"训练集准确率: {train_score_rf:.4f}")
print(f"测试集准确率: {test_score_rf:.4f}")
print(f"OOB 评分: {rf.oob_score_:.4f}")

print("\n分类报告:")
y_pred_rf = rf.predict(X_test)
print(classification_report(y_test, y_pred_rf, target_names=['正常', '违约']))

# ========== 5. 交叉验证对比 ==========
print("=" * 60)
print("📊 交叉验证对比")
print("=" * 60)

cv_scores_dt = cross_val_score(dt, X, y, cv=5, scoring='f1')
cv_scores_rf = cross_val_score(rf, X, y, cv=5, scoring='f1')

print(f"决策树 F1: {cv_scores_dt.mean():.4f} ± {cv_scores_dt.std():.4f}")
print(f"随机森林 F1: {cv_scores_rf.mean():.4f} ± {cv_scores_rf.std():.4f}")

# ========== 6. 特征重要性 ==========
print("\n" + "=" * 60)
print("🔍 特征重要性 (随机森林)")
print("=" * 60)

importances = rf.feature_importances_
indices = np.argsort(importances)[::-1]

for i, idx in enumerate(indices):
    bar = "█" * int(importances[idx] * 50)
    print(f"{i+1}. {feature_names[idx]:20s} {importances[idx]:.4f} {bar}")

# ========== 7. 可视化 ==========
fig, axes = plt.subplots(1, 2, figsize=(16, 8))

# 决策树可视化
plot_tree(dt, feature_names=feature_names, class_names=['正常', '违约'],
          filled=True, rounded=True, ax=axes[0], max_depth=3, fontsize=8)
axes[0].set_title('决策树 (前3层)', fontsize=14)

# 特征重要性
axes[1].barh(range(len(feature_names)),
             importances[indices[::-1]], align='center')
axes[1].set_yticks(range(len(feature_names)))
axes[1].set_yticklabels([feature_names[i] for i in indices[::-1]])
axes[1].set_xlabel('重要性')
axes[1].set_title('特征重要性 (随机森林)', fontsize=14)

plt.tight_layout()
plt.savefig('day-109-visualization.png', dpi=150, bbox_inches='tight')
print("\n✅ 可视化已保存至 day-109-visualization.png")

# ========== 8. 混淆矩阵 ==========
from sklearn.metrics import ConfusionMatrixDisplay

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

ConfusionMatrixDisplay.from_estimator(dt, X_test, y_test,
    display_labels=['正常', '违约'], ax=axes[0], cmap='Blues')
axes[0].set_title('决策树 混淆矩阵')

ConfusionMatrixDisplay.from_estimator(rf, X_test, y_test,
    display_labels=['正常', '违约'], ax=axes[1], cmap='Greens')
axes[1].set_title('随机森林 混淆矩阵')

plt.tight_layout()
plt.savefig('day-109-confusion.png', dpi=150, bbox_inches='tight')
print("✅ 混淆矩阵已保存至 day-109-confusion.png")

print("\n🎉 信用风险评估实战完成!")
```

### 6.3 模型评估要点

| 指标 | 说明 | 信用场景意义 |
|------|------|-------------|
| **Precision** | 预测为违约中实际违约的比例 | 误判好客户为坏客户 → 损失业务 |
| **Recall** | 实际违约中被预测出的比例 | 漏判坏客户 → 坏账损失 |
| **F1** | Precision 和 Recall 的调和平均 | 平衡两类错误 |
| **AUC** | ROC 曲线下面积 | 综合评估排序能力 |

> 💡 **业务场景下，Recall 通常比 Precision 更重要**——漏掉一个坏客户（高坏账）比误判一个好客户（损失利息）代价更大。

---

## 7. 思考题

### 基础题

1. **决策树的分裂过程是贪心的，这意味着什么？它可能错过全局最优解吗？**

2. **如果一个特征有 1000 个不同值（如用户 ID），决策树会怎样处理它？信息增益会偏高吗？**

3. **随机森林中 `n_estimators=10` 和 `n_estimators=1000`，模型性能一定会提升吗？为什么？**

### 进阶题

4. **在信用风险评估中，为什么更关注 Recall 而不是 Precision？如果银行的成本结构变了（如获客成本极高），应该如何调整阈值？**

5. **比较决策树、随机森林和 XGBoost：它们各自适合什么场景？如果数据量只有 100 条，你会选哪个？如果数据量有 1000 万条呢？**

---

## 📝 本日小结

| 概念 | 要点 |
|------|------|
| 决策树 | 通过 if-else 规则递归分割数据，可解释性强 |
| 信息增益 | 基于熵减少选择分裂特征 |
| 基尼系数 | CART 默认标准，计算更快 |
| 随机森林 | Bagging + 特征随机，降低方差 |
| OOB | 免费的验证集评估方法 |
| 特征重要性 | MDI（快）vs Permutation（准） |

**下一步**: Day 110 — SVM 与 KNN，继续机器学习算法之旅！

---

> 📅 **日期**: 2026-08-13
> 🏷️ **标签**: `机器学习` `决策树` `随机森林` `集成学习` `分类`
