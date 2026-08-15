# Day 112 — 模型调优与 Pipeline

> 交叉验证、网格搜索、特征工程 Pipeline 与模型持久化——构建完整的机器学习工作流

---

## 📋 今日学习目标

1. 理解交叉验证原理，掌握 K-Fold 交叉验证的使用
2. 掌握网格搜索（GridSearchCV）进行超参数调优
3. 理解 Pipeline 概念，将特征工程与模型训练串联
4. 学会使用 joblib 保存与加载训练好的模型
5. 实战：构建一个完整的 ML Pipeline（数据预处理→特征工程→模型训练→评估→部署）

---

## 一、交叉验证（Cross Validation）

### 1.1 为什么需要交叉验证？

在之前的课程中，我们用 `train_test_split` 将数据分为训练集和测试集。但这种划分方式有一个问题：

- **单次划分的随机性**：不同的随机种子会产生不同的划分，导致评估结果不稳定
- **数据浪费**：只用一部分数据训练，另一部分只用于评估
- **评估偏差**：如果测试集恰好包含"容易"或"困难"的样本，评估结果会失真

交叉验证通过**多次划分、多次训练、多次评估**来解决这些问题。

### 1.2 交叉验证的原理

交叉验证的核心思想是：**将数据集分成 K 份，每次用 K-1 份训练，1 份验证，重复 K 次，取平均值作为最终评估指标。**

#### K-Fold 交叉验证步骤

1. 将训练数据随机分为 K 个大小相似的子集（fold）
2. 对于每个 fold：
   - 用其余 K-1 个 fold 作为训练集
   - 用当前 fold 作为验证集
   - 记录模型在验证集上的性能
3. 计算 K 次评估结果的平均值作为最终性能指标

```
数据划分示例（K=5）：
轮次1: [验证] [训练] [训练] [训练] [训练] → 得分1
轮次2: [训练] [验证] [训练] [训练] [训练] → 得分2
轮次3: [训练] [训练] [验证] [训练] [训练] → 得分3
轮次4: [训练] [训练] [训练] [验证] [训练] → 得分4
轮次5: [训练] [训练] [训练] [训练] [验证] → 得分5

最终得分 = (得分1 + 得分2 + ... + 得分5) / 5
```

#### 交叉验证的优势

| 方面 | train_test_split | K-Fold 交叉验证 |
|------|-----------------|-----------------|
| 数据利用率 | 约 75%/25% | 100%（每条数据都参与过训练和验证） |
| 稳定性 | 依赖单次划分 | 多次划分取平均，结果更稳定 |
| 计算成本 | 1次训练 | K次训练 |
| 适用场景 | 快速验证 | 正式评估模型性能 |

### 1.3 常见的交叉验证策略

#### K-Fold

最基础的交叉验证方法，数据被等分为 K 份。

**K 值选择建议：**
- K=5 或 K=10 是最常用的选择
- K 太小（如 K=2）：训练数据太少，评估偏差大
- K 太大（如 K=N）：每次只留1个样本验证（留一法），计算成本高
- K 越大，偏差越小但方差越大

#### Stratified K-Fold

分层 K 折交叉验证，确保每个 fold 中各类别的比例与整体数据集一致。

**适用场景：** 分类问题，尤其是类别不平衡时。

```
原始数据类别分布：正类 30%，负类 70%
Stratified K-Fold 后每个 fold：正类 ~30%，负类 ~70%
```

#### Leave-One-Out (LOO)

K = N（样本总数），每次只留1个样本做验证。

**特点：**
- 无偏估计（几乎用了所有数据训练）
- 计算成本极高（N次训练）
- 方差较大

#### Repeated K-Fold

重复 K-Fold 多次，每次重新随机划分。

**特点：**
- 更稳定的评估结果
- 计算成本 = 重复次数 × K

---

## 二、网格搜索（Grid Search）

### 2.1 为什么需要超参数调优？

机器学习模型通常有**超参数**（hyperparameters），它们在训练之前设定，不能通过训练自动学习。例如：

- SVM 的 `C`（正则化强度）和 `gamma`（核函数参数）
- 随机森林的 `n_estimators`（树的数量）和 `max_depth`（最大深度）
- KNN 的 `n_neighbors`（近邻数）

选择合适的超参数对模型性能影响巨大。网格搜索是一种系统化的超参数调优方法。

### 2.2 网格搜索的原理

网格搜索的工作方式非常直观：

1. **定义搜索空间**：为每个超参数指定一组候选值
2. **穷举组合**：生成所有超参数值的组合
3. **逐个尝试**：对每种组合训练并评估模型
4. **选择最优**：返回性能最好的超参数组合

```
假设搜索空间：
  C = [0.1, 1, 10]
  gamma = [0.01, 0.1, 1]

组合数 = 3 × 3 = 9 种
每种组合用 K-Fold 交叉验证评估
共训练 9 × 5 = 45 次
```

### 2.3 网格搜索的优缺点

**优点：**
- 系统性：不遗漏任何组合
- 并行化：不同组合之间独立，可以并行计算
- 结合交叉验证：结果更可靠

**缺点：**
- 计算成本随超参数数量**指数级增长**
- 只能搜索预定义的离散值
- 不适合高维超参数空间

### 2.4 其他搜索策略

| 方法 | 特点 | 适用场景 |
|------|------|---------|
| GridSearchCV | 穷举所有组合 | 超参数空间小 |
| RandomizedSearchCV | 随机采样固定次数 | 超参数空间大 |
| HalvingGridSearchCV | 逐轮淘汰，加速搜索 | 大规模数据集 |

---

## 三、Pipeline — 管道

### 3.1 为什么需要 Pipeline？

在实际项目中，数据预处理和模型训练通常是分开的：

```python
# 分开的做法
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)  # ⚠️ 必须用 transform，不能 fit_transform！

model = LogisticRegression()
model.fit(X_train_scaled, y_train)
```

这种做法有几个问题：

1. **容易犯错**：忘记对测试集只做 `transform` 而误用 `fit_transform`，导致**数据泄露**
2. **代码冗余**：每个预处理步骤都要单独调用
3. **部署困难**：保存模型时需要同时保存多个预处理器
4. **难以复现**：步骤多了容易遗漏

Pipeline 将所有步骤串联成一个整体，解决上述所有问题。

### 3.2 Pipeline 的概念

Pipeline 是一个**按顺序执行的处理链**，每个步骤可以是一个预处理器（transformer）或一个模型（estimator）。

```
数据输入 → [步骤1: 预处理] → [步骤2: 特征工程] → [步骤3: 模型] → 预测输出
```

**Pipeline 的关键特性：**

- **统一接口**：对外表现为一个 estimator，支持 `fit()`、`predict()`、`score()` 等方法
- **自动数据流**：前一步的输出自动作为下一步的输入
- **防数据泄露**：在交叉验证中，每个 fold 的预处理只在训练数据上 fit
- **便于部署**：一个 `joblib.dump()` 就能保存整个 Pipeline

### 3.3 Pipeline 的执行流程

```
Pipeline([('scaler', StandardScaler()), ('pca', PCA(n_components=5)), ('clf', SVC())])

fit(X, y) 执行过程：
  1. scaler.fit_transform(X) → X_scaled
  2. pca.fit_transform(X_scaled) → X_pca
  3. clf.fit(X_pca, y)

predict(X_new) 执行过程：
  1. scaler.transform(X_new) → X_scaled
  2. pca.transform(X_scaled) → X_pca
  3. clf.predict(X_pca)
```

**注意：** Pipeline 中只有最后一步是 estimator，其余都是 transformer。

### 3.4 ColumnTransformer — 处理不同类型特征

实际数据中通常包含数值型和类别型特征，需要不同的处理方式。`ColumnTransformer` 可以对不同列应用不同的预处理器。

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

preprocessor = ColumnTransformer([
    ('num', StandardScaler(), ['age', 'income']),
    ('cat', OneHotEncoder(), ['city', 'gender'])
])
```

### 3.5 嵌套 Pipeline 与 GridSearchCV

Pipeline 中的超参数可以通过 `__` 语法访问：

```python
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', SVC())
])

# 访问 SVC 的 C 参数
param_grid = {'clf__C': [0.1, 1, 10]}
```

结合 GridSearchCV，可以同时搜索多个步骤的超参数。

---

## 四、模型持久化（Model Persistence）

### 4.1 为什么需要保存模型？

训练一个模型可能花费数小时甚至数天。保存模型意味着：

- 不需要每次使用都重新训练
- 可以在不同环境中部署
- 可以进行 A/B 测试
- 可以回滚到之前的版本

### 4.2 joblib — 推荐方式

joblib 是 scikit-learn 官方推荐的模型保存方式，特别适合处理包含大量 NumPy 数组的模型。

**核心 API：**

| 函数 | 作用 |
|------|------|
| `joblib.dump(model, filename)` | 将模型保存到文件 |
| `joblib.load(filename)` | 从文件加载模型 |

**为什么不用 pickle？**

- pickle 也可以保存模型，但对大型 NumPy 数组效率低
- joblib 使用更高效的压缩，文件更小
- joblib 是 scikit-learn 的官方推荐

### 4.3 保存与加载最佳实践

```python
import joblib

# 保存
joblib.dump(pipeline, 'model_pipeline.pkl')

# 加载
loaded_pipeline = joblib.load('model_pipeline.pkl')

# 使用加载的模型预测
predictions = loaded_pipeline.predict(X_new)
```

**注意事项：**
- 保存的文件包含模型结构和参数，不包含训练数据
- 版本兼容性：加载时的 scikit-learn 版本应与保存时兼容
- 文件安全：pickle/joblib 文件可以执行代码，不要加载不可信来源的模型

---

## 五、完整 ML Pipeline 实战

### 5.1 项目概述

我们将构建一个完整的机器学习 Pipeline，用于预测客户是否流失（Churn Prediction）。这模拟了真实的工业级 ML 项目流程。

**数据集：** 使用合成数据模拟电信客户流失数据

**Pipeline 步骤：**
1. 数据加载与探索
2. 数据预处理（缺失值处理、编码、缩放）
3. 特征工程
4. 模型选择与超参数调优
5. 评估与比较
6. 模型保存与部署

### 5.2 完整代码

请查看 `code/03-full-pipeline.py` 获取完整的可运行代码。

### 5.3 关键点总结

| 环节 | 工具/方法 | 要点 |
|------|----------|------|
| 交叉验证 | `cross_val_score`, `StratifiedKFold` | 确保每折类别比例一致 |
| 超参数调优 | `GridSearchCV` | 结合交叉验证，避免过拟合 |
| 数据预处理 | `ColumnTransformer`, `Pipeline` | 统一处理流程 |
| 模型保存 | `joblib.dump/load` | 保存完整 Pipeline |
| 评估指标 | `classification_report`, `confusion_matrix` | 多维度评估 |

---

## 六、API 速查

### cross_val_score

```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(estimator, X, y, cv=5, scoring='accuracy')
print(f"平均得分: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")
```

**参数说明：**
- `estimator`：模型对象
- `X, y`：特征和标签
- `cv`：交叉验证折数（默认5）
- `scoring`：评估指标

### GridSearchCV

```python
from sklearn.model_selection import GridSearchCV

grid_search = GridSearchCV(
    estimator=pipeline,
    param_grid=param_grid,
    cv=5,
    scoring='accuracy',
    n_jobs=-1,
    verbose=1
)
grid_search.fit(X_train, y_train)
print(f"最佳参数: {grid_search.best_params_}")
print(f"最佳得分: {grid_search.best_score_:.4f}")
```

**参数说明：**
- `estimator`：模型或 Pipeline
- `param_grid`：超参数搜索空间（字典）
- `cv`：交叉验证折数
- `scoring`：评估指标
- `n_jobs`：并行数（-1 表示使用所有 CPU）
- `verbose`：日志详细程度

### Pipeline

```python
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('pca', PCA(n_components=10)),
    ('clf', SVC())
])

# 统一接口
pipeline.fit(X_train, y_train)
score = pipeline.score(X_test, y_test)
predictions = pipeline.predict(X_test)
```

### joblib

```python
import joblib

# 保存模型
joblib.dump(pipeline, 'model.pkl', compress=3)

# 加载模型
loaded = joblib.load('model.pkl')
```

---

## 七、思考题

### 思考题 1：交叉验证 vs 保留验证集

> 如果你的数据集非常小（只有 100 条样本），你会选择哪种验证方式？为什么？

**提示：** 考虑数据利用率、评估偏差、计算成本之间的权衡。

### 思考题 2：GridSearchCV 的计算成本

> 一个 Pipeline 有 3 个步骤，每个步骤有 4 个超参数选择，使用 5 折交叉验证。总共需要训练多少次模型？

**提示：** 总组合数 = 各步骤参数数量的乘积。

### 思考题 3：数据泄露

> 在不使用 Pipeline 的情况下，以下代码有什么问题？如何修复？

```python
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.fit_transform(X_test)  # 注意是 fit_transform
model = LogisticRegression()
model.fit(X_train_scaled, y_train)
```

**提示：** 思考 "fit" 操作在训练集和测试集上的含义。

### 思考题 4：Pipeline 的局限性

> Pipeline 能否处理以下场景？如果不能，你会如何解决？
> - 训练数据中需要做文本清洗，但清洗规则需要人工定义
> - 特征选择需要根据标签信息动态调整
> - 需要并行运行多个模型然后融合预测结果

### 思考题 5：模型持久化的安全隐患

> `joblib.load()` 本质上执行 pickle 反序列化，这可能带来什么安全风险？在生产环境中如何安全地加载模型？

**提示：** 考虑 pickle 反序列化漏洞、模型来源验证、沙箱加载等。

---

## 📚 今日总结

今天学习了构建完整机器学习工作流所需的四个关键技能：

1. **交叉验证**：通过多次划分数据获得可靠的模型评估
2. **网格搜索**：系统化地搜索最优超参数组合
3. **Pipeline**：将数据预处理和模型训练串联成一个整体，防止数据泄露，简化部署
4. **模型持久化**：使用 joblib 保存训练好的 Pipeline，便于重复使用

这四个工具组合使用，构成了工业级机器学习项目的基础框架。明天我们将进入深度学习的世界！

---

> 📅 昨天 Day 111: 无监督学习 | 明天 Day 113: PyTorch 基础
