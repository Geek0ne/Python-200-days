# Day 106 — 机器学习基础

> 🎯 **今日目标**：理解机器学习的核心概念，掌握 Scikit-learn 基本工作流，完成第一个完整的 ML 流程体验。

---

## 1. 什么是机器学习？

机器学习（Machine Learning）是让计算机从数据中**自动学习规律**，而不是通过显式编程来完成任务。

### 为什么需要机器学习？

| 传统编程 | 机器学习 |
|---------|---------|
| 人写规则 → 计算机执行 | 人给数据 → 计算机学习规则 |
| 适合逻辑明确的任务 | 适合规则难以描述的任务 |
| 例：if-else 判断年龄 | 例：识别图片中的猫 |

**核心公式**：
```
传统编程:  Input + Rules  → Output
机器学习:  Input + Output → Rules (Model)
```

---

## 2. 三大学习范式

### 2.1 监督学习（Supervised Learning）

给模型**带标签的数据**，让它学习输入到输出的映射。

```
训练数据: [(图片1, "猫"), (图片2, "狗"), ...]
         ↓ 模型学习
新图片 → 模型 → 预测 "猫"/"狗"
```

**典型任务**：
- **分类**：邮件是否是垃圾邮件？肿瘤是良性还是恶性？
- **回归**：预测房价、预测温度

### 2.2 无监督学习（Unsupervised Learning）

数据**没有标签**，让模型自己发现数据中的结构。

```
训练数据: [客户A的消费数据, 客户B的消费数据, ...]
         ↓ 模型发现
结果: 客户被分成 3 个群体（高消费、中等、低消费）
```

**典型任务**：
- **聚类**：客户分群、文档分组
- **降维**：数据可视化、特征压缩
- **异常检测**：欺诈识别

### 2.3 强化学习（Reinforcement Learning）

模型通过**与环境交互**，根据奖励信号学习最优策略。

```
Agent(智能体) → 执行动作 → 环境反馈奖励/惩罚
     ↑                              ↓
     ←←←←←←← 学习最优策略 ←←←←←←←←←
```

**典型应用**：游戏 AI（AlphaGo）、机器人控制、自动驾驶

### 学习范式对比

```
┌─────────────┬──────────────────┬──────────────────┐
│   范式       │  数据特点         │  学习目标         │
├─────────────┼──────────────────┼──────────────────┤
│ 监督学习     │  有标签           │  预测输出         │
│ 无监督学习   │  无标签           │  发现结构         │
│ 强化学习     │  奖励信号         │  最优策略         │
└─────────────┴──────────────────┴──────────────────┘
```

---

## 3. Scikit-learn 概览

Scikit-learn（sklearn）是 Python 最流行的机器学习库，提供统一、简洁的 API。

### 3.1 安装

```bash
pip install scikit-learn
```

### 3.2 统一 API 设计

Scikit-learn 所有模型都遵循相同的 API 模式：

```python
from sklearn.xxx import XxxModel

# 1. 创建模型
model = XxxModel(hyperparameter=value)

# 2. 训练（拟合）
model.fit(X_train, y_train)

# 3. 预测
y_pred = model.predict(X_test)

# 4. 评估
score = model.score(X_test, y_test)
```

### 3.3 核心模块

```
sklearn
├── datasets        # 内置数据集（鸢尾花、手写数字等）
├── model_selection # 数据拆分、交叉验证、网格搜索
├── preprocessing   # 数据预处理（标准化、编码等）
├── linear_model    # 线性模型（线性回归、逻辑回归等）
├── tree            # 决策树
├── ensemble        # 集成方法（随机森林、GBDT）
├── svm             # 支持向量机
├── neighbors       # K 近邻
├── cluster         # 聚类算法
├── metrics         # 评估指标
└── pipeline        # 管道（串联预处理和模型）
```

---

## 4. 数据集拆分 — train_test_split

### 为什么要拆分？

防止**过拟合**——模型在训练集上表现好，但在新数据上表现差。

```
完整数据集
├── 训练集 (80%) → 用于训练模型
└── 测试集 (20%) → 用于评估模型泛化能力
```

### 使用方法

```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y,                # 特征和标签
    test_size=0.2,       # 测试集比例
    random_state=42,     # 随机种子（保证可复现）
    stratify=y           # 分层抽样（保持类别比例一致）
)
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `test_size` | 测试集比例（0~1） | 0.25 |
| `train_size` | 训练集比例（0~1） | None |
| `random_state` | 随机种子 | None |
| `stratify` | 按该标签分层抽样 | None |

---

## 5. 评估指标详解

### 5.1 分类指标

#### 混淆矩阵（Confusion Matrix）

```
                    预测值
                正例(P)   负例(N)
实际  正例(P)    TP        FN
值    负例(N)    FP        TN
```

- **TP**（True Positive）：真正例，实际正，预测正 ✅
- **TN**（True Negative）：真负例，实际负，预测负 ✅
- **FP**（False Positive）：假正例，实际负，预测正 ❌（误报）
- **FN**（False Negative）：假负例，实际正，预测负 ❌（漏报）

#### 四大指标

| 指标 | 公式 | 含义 | 适用场景 |
|------|------|------|----------|
| **准确率** Accuracy | (TP+TN)/(TP+TN+FP+FN) | 所有样本中预测正确的比例 | 类别平衡时 |
| **精确率** Precision | TP/(TP+FP) | 预测为正的样本中真正为正的比例 | 关注误报（如垃圾邮件） |
| **召回率** Recall | TP/(TP+FN) | 实际为正的样本中被正确预测的比例 | 关注漏报（如癌症检测） |
| **F1 分数** | 2×P×R/(P+R) | 精确率和召回率的调和平均 | 综合考虑两者 |

#### 何时用哪个？

```
垃圾邮件检测 → 高精确率（宁可漏掉，不可误判正常邮件为垃圾）
癌症筛查     → 高召回率（宁可误判，不可漏掉真正的患者）
一般分类     → F1 分数（综合考虑）
```

### 5.2 回归指标

| 指标 | 公式 | 含义 |
|------|------|------|
| **MSE** | mean((y-y_pred)²) | 均方误差，对大误差敏感 |
| **RMSE** | √MSE | 均方根误差，与原始单位一致 |
| **MAE** | mean(|y-y_pred|) | 平均绝对误差 |
| **R²** | 1 - SS_res/SS_tot | 决定系数，1=完美，0=等同于均值 |

---

## 6. 完整 ML 工作流图解

```
┌─────────────────────────────────────────────────┐
│              机器学习工作流                        │
├─────────────────────────────────────────────────┤
│                                                   │
│  ① 数据收集                                       │
│      ↓                                            │
│  ② 数据探索 (EDA)                                  │
│      ↓                                            │
│  ③ 数据预处理                                     │
│      ├── 缺失值处理                                │
│      ├── 特征编码                                  │
│      ├── 特征缩放                                  │
│      └── 特征选择                                  │
│      ↓                                            │
│  ④ 数据拆分 (train_test_split)                    │
│      ↓                                            │
│  ⑤ 模型选择 & 训练                                │
│      ↓                                            │
│  ⑥ 模型评估                                       │
│      ├── 准确率/精确率/召回率/F1                    │
│      ├── 交叉验证                                  │
│      └── 学习曲线                                  │
│      ↓                                            │
│  ⑦ 超参数调优 (GridSearchCV)                      │
│      ↓                                            │
│  ⑧ 部署 & 预测                                    │
│                                                   │
└─────────────────────────────────────────────────┘
```

### Scikit-learn Pipeline 流程图

```mermaid
graph LR
    A[原始数据] --> B[预处理器]
    B --> C[特征缩放]
    C --> D[模型训练]
    D --> E[预测输出]
    D --> F[评估指标]
    F -->|不满意| G[调参]
    G --> D
```

---

## 7. 实战代码案例

### 案例：鸢尾花分类（Iris Classification）

这是 ML 界的 "Hello World"，用 4 个特征（花萼/花瓣长宽）预测鸢尾花品种。

```python
"""
Day 106 实战：鸢尾花分类完整流程
"""
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np

# ===== 1. 加载数据 =====
iris = load_iris()
X, y = iris.data, iris.target
print(f"数据集大小: {X.shape}")
print(f"特征名: {iris.feature_names}")
print(f"类别名: {list(iris.target_names)}")

# ===== 2. 数据拆分 =====
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")

# ===== 3. 特征缩放 =====
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)  # fit + transform
X_test_scaled = scaler.transform(X_test)         # 只 transform!

# ===== 4. 训练模型 =====
model = KNeighborsClassifier(n_neighbors=5)
model.fit(X_train_scaled, y_train)

# ===== 5. 评估 =====
y_pred = model.predict(X_test_scaled)
accuracy = np.mean(y_pred == y_test)
print(f"\n准确率: {accuracy:.2%}")
print("\n分类报告:")
print(classification_report(y_test, y_pred, target_names=iris.target_names))
print("混淆矩阵:")
print(confusion_matrix(y_test, y_pred))
```

---

## 8. 常见陷阱与避坑

### ❌ 陷阱 1：数据泄露（Data Leakage）

```python
# ❌ 错误：先缩放再拆分 → 测试集信息泄露到训练集
scaler.fit_transform(X)  # 用所有数据算均值/方差
X_train, X_test, y_train, y_test = train_test_split(X, y)

# ✅ 正确：先拆分再缩放
X_train, X_test, y_train, y_test = train_test_split(X, y)
scaler.fit_transform(X_train)  # 只用训练集算
scaler.transform(X_test)       # 测试集用训练集的参数
```

### ❌ 陷阱 2：在测试集上训练

```python
# ❌ 错误
model.fit(X_test, y_test)  # 绝对不要这样做！

# ✅ 正确
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
```

### ❌ 陷阱 3：忽略类别不平衡

```python
# 如果 95% 是 A 类，5% 是 B 类
# 模型全预测 A 就有 95% 准确率，但毫无意义！
# 解决方案：
# 1. 用 F1 分数替代准确率
# 2. 使用 class_weight='balanced'
# 3. 过采样 (SMOTE) 或欠采样
# 4. 使用 precision-recall 曲线而非 ROC
```

### ❌ 陷阱 4：特征工程中使用测试集信息

```python
# ❌ 错误：用全体数据计算均值填充缺失值
mean_val = df['age'].mean()  # 包含了测试集的统计信息
df['age'].fillna(mean_val)

# ✅ 正确：只用训练集计算
mean_val = X_train['age'].mean()
X_train['age'].fillna(mean_val, inplace=True)
X_test['age'].fillna(mean_val, inplace=True)  # 用训练集的均值
```

---

## 9. API 速查表

### 模型通用 API

| 方法 | 说明 |
|------|------|
| `model.fit(X, y)` | 训练模型 |
| `model.predict(X)` | 预测 |
| `model.predict_proba(X)` | 预测概率（分类） |
| `model.score(X, y)` | 评估（默认准确率） |
| `model.get_params()` | 获取超参数 |
| `model.set_params(**params)` | 设置超参数 |

### 数据拆分

| 函数 | 说明 |
|------|------|
| `train_test_split(X, y, ...)` | 拆分训练/测试集 |
| `cross_val_score(model, X, y, cv=5)` | 交叉验证 |
| `StratifiedKFold(n_splits=5)` | 分层 K 折 |

### 预处理

| 类 | 说明 |
|-----|------|
| `StandardScaler()` | 标准化（均值0，方差1） |
| `MinMaxScaler()` | 归一化（0~1） |
| `LabelEncoder()` | 标签编码 |
| `OneHotEncoder()` | 独热编码 |

### 评估指标

| 函数 | 说明 |
|------|------|
| `accuracy_score(y_true, y_pred)` | 准确率 |
| `precision_score(y_true, y_pred)` | 精确率 |
| `recall_score(y_true, y_pred)` | 召回率 |
| `f1_score(y_true, y_pred)` | F1 分数 |
| `classification_report(y_true, y_pred)` | 完整报告 |
| `confusion_matrix(y_true, y_pred)` | 混淆矩阵 |

---

## 10. 思考题

1. **数据泄露**：为什么不能在拆分之前做特征缩放？用一个简单的数值例子说明后果。

**参考答案**

因为缩放要算**均值和标准差**，如果在拆分前对全体数据做，这两个统计量就**混入了测试集的信息**——相当于让模型在训练时「偷看」了测试集的分布，评估结果会虚高，上线后才发现没那么好。这就是数据泄露（data leakage）。

数值例子：设某特征只有 4 个值 `[1, 2, 3, 100]`，拆成训练集 `[1,2,3]`、测试集 `[100]`。

- **错误（先缩放再拆）**：用全体算，均值 = 26.5、标准差 ≈ 42.4。缩放后 `1 → (1-26.5)/42.4 ≈ -0.60`，`100 → 1.73`。注意测试点 100 把均值狠狠拉高，导致训练值全被压缩到 0 附近——缩放参数里已经「藏」了测试点的信息。
- **正确（先拆再缩放）**：只用训练集 `[1,2,3]` 算，均值 = 2、标准差 ≈ 0.816。训练值缩放为 `-1.22, 0, 1.22`；测试点 `100 → (100-2)/0.816 ≈ 120`，远远超出训练范围。

对比可见：正确做法下测试点是个「模型从没见过的极端值」，评估能真实反映模型的泛化（外推）能力；错误做法却把它的影响提前抹平，制造了「模型很稳」的假象。

⚠️ 注意：同理，缺失值填充、特征选择、归一化等任何「要从数据学统计量」的步骤，都必须只在训练集上 fit，再 transform 测试集。用 `Pipeline` 把预处理和模型串起来能自动避免这类泄露。

2. **评估指标选择**：假设你在构建一个欺诈检测系统（欺诈交易仅占 0.1%），准确率、精确率、召回率哪个最重要？为什么？

**参考答案**

**召回率（Recall）最重要**，准确率几乎没用。

- **准确率失效**：欺诈只占 0.1%，模型只要「全部预测为正常」就有 99.9% 准确率，却一笔欺诈都抓不到——高准确率毫无意义。这是类别不平衡的典型陷阱。
- **召回率优先**：召回率 = 抓到的欺诈 / 全部真实欺诈。漏掉一笔欺诈（FN）往往意味着直接的资金损失，代价极高；所以首要目标是「尽量别漏」，即高召回。
- **精确率也要兼顾**：精确率 = 判为欺诈里真欺诈的比例。太低意味着大量正常交易被误报（FP），人工审核成本爆炸、用户体验差。所以不能为了召回把一切都判成欺诈。

实践做法：以召回为主、用 **F1 或 PR-AUC（精确率-召回率曲线下面积）** 综合衡量；通过调分类阈值、`class_weight='balanced'`、过采样（SMOTE）在「漏报」和「误报」之间按业务成本找平衡。

💡 提示：到底偏召回还是偏精确，取决于两类错误的代价。若误报代价更高（如误冻结用户账户），则要向精确率倾斜——指标选择本质是业务成本权衡。

3. **K 值选择**：KNN 中 K=1 和 K=100 分别会导致什么问题？如何选择合适的 K 值？

**参考答案**

KNN 靠「最近的 K 个邻居投票」分类，K 控制模型的复杂度：

- **K=1 → 过拟合**：完全由最近的一个点决定，对噪声和异常值极度敏感，决策边界支离破碎。训练误差为 0（每个点最近的就是自己），但泛化差。
- **K=100 → 欠拟合**：投票范围太大，局部结构被抹平，边界过于平滑；若类别不平衡，大 K 还会被多数类「淹没」，少数类几乎预测不出来。

**如何选 K**：
- 用**交叉验证**（如 5 折）在一组候选 K（1,3,5,…,31）上比较准确率/F1，选验证表现最好的。
- 通常取**奇数**避免二分类平票；经验起点可试 `K ≈ sqrt(样本数)`。
- 配合**距离加权**（`weights='distance'`，近邻话语权更大）缓解大 K 的平滑问题。
- 先做**特征缩放**——KNN 基于距离，量纲大的特征会主导结果。

一句话：K 小→高方差（过拟合），K 大→高偏差（欠拟合），用交叉验证找偏差-方差的平衡点。

4. **模型选择**：面对一个新问题，你会如何选择机器学习算法？请列出你的决策流程。

**参考答案**

一个实用的决策流程：

1. **界定问题类型**：有标签吗？→ 有：分类（离散）还是回归（连续）；无：聚类/降维/异常检测。这一步决定大方向。
2. **看数据规模与特征**：样本量、特征数、是否结构化（表格）、文本/图像、是否高维稀疏、有无缺失。小表格数据优先树模型/线性模型；图像/文本优先深度学习。
3. **明确约束**：要不要可解释性（金融/医疗→线性模型、决策树）？要不要概率输出（逻辑回归）？延迟/算力限制？类别是否不平衡？
4. **先建简单基线**：从逻辑回归/线性回归、单棵决策树、KNN 起步，快速拿到一个基准分数，别一上来就上复杂模型。
5. **逐步升级 + 交叉验证**：试随机森林/GBDT（XGBoost、LightGBM）、SVM 等，用同一套交叉验证公平比较，看是否显著超过基线。
6. **评估与迭代**：用对指标（不平衡看 F1/PR-AUC，回归看 RMSE/MAE），分析错误样本，做特征工程，再调参（GridSearchCV）。
7. **权衡落地**：在精度、可解释性、训练/推理成本、维护难度间取舍，选「够用且可维护」的，而非最炫的。

核心原则：**没有万能算法（No Free Lunch），先简单后复杂、用验证数据说话、让业务约束驱动选择**。

5. **实际应用**：想一个你生活中的场景，它适合用监督学习还是无监督学习？为什么？需要什么数据？

**参考答案**

（开放题，以下为示例）场景：**预测二手房成交价**——适合**监督学习（回归）**。

- **为什么监督**：我们有明确的「输入→输出」对应关系：房屋特征（面积、地段、房龄、楼层、朝向）对应一个已知的成交价。目标是学出这个映射来预测新房子价格，属于带标签的回归任务。
- **需要的数据**：历史成交记录，每行包含房屋特征（数值/类别）+ 真实成交价（标签）；还可补充周边配套、学区、距地铁距离等特征。数据要清洗（缺失、异常高价）、做特征编码与缩放。
- **可选模型**：线性回归做基线，随机森林/GBDT 捕捉非线性，用 RMSE/MAE 评估。

对比：如果是「把小区房源自动分成几档（刚需/改善/豪宅）且没有现成标签」，那就是**无监督聚类**——只有特征、没有答案，让算法自己发现分群结构。

💡 提示：判断监督/无监督的关键就一句话——**有没有「标准答案」（标签）**。有标签学映射是监督，没标签找结构是无监督。
