# 逻辑回归 API 速查表

## LogisticRegression 核心参数

| 参数 | 默认值 | 说明 | 推荐值 |
|------|--------|------|--------|
| `penalty` | 'l2' | 正则化类型: 'l1', 'l2', 'elasticnet', None | 'l2' |
| `C` | 1.0 | 正则化强度倒数，越小正则化越强 | 0.1~10 (交叉验证) |
| `solver` | 'lbfgs' | 优化算法 | 小数据: lbfgs, 大数据: saga |
| `max_iter` | 100 | 最大迭代次数 | 1000+ |
| `multi_class` | 'auto' | 多分类策略 | 'auto' 或 'multinomial' |
| `class_weight` | None | 类别权重 | 'balanced' 处理不平衡 |
| `random_state` | None | 随机种子 | 42 |
| `tol` | 1e-4 | 收敛阈值 | 1e-4 |
| `intercept_scaling` | 1 | 截距缩放 | 1 |

## solver 选择指南

| solver | 适用场景 | 支持的 penalty | 特点 |
|--------|----------|---------------|------|
| `lbfgs` | 小数据集 (<10k) | l2, None | 默认推荐，收敛快 |
| `liblinear` | 小数据集 | l1, l2 | 支持 L1，适合特征选择 |
| `saga` | 大数据集 | l1, l2, elasticnet, None | 支持弹性网络 |
| `newton-cg` | 中等数据集 | l2, None | 二阶优化 |

## 核心方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `fit(X, y)` | 训练模型 | self |
| `predict(X)` | 预测类别 | ndarray (n_samples,) |
| `predict_proba(X)` | 预测概率 | ndarray (n_samples, n_classes) |
| `decision_function(X)` | 决策函数值 | ndarray (n_samples,) |
| `score(X, y)` | 准确率 | float |
| `get_params()` | 获取参数 | dict |
| `set_params(**params)` | 设置参数 | self |

## 常用属性

| 属性 | 说明 | shape |
|------|------|-------|
| `coef_` | 权重系数 | (n_classes, n_features) |
| `intercept_` | 偏置项 | (n_classes,) |
| `classes_` | 类别标签 | (n_classes,) |
| `n_iter_` | 实际迭代次数 | (n_classes,) |

## 评估指标速查

| 指标 | sklearn 函数 | 适用场景 |
|------|-------------|----------|
| 准确率 | `accuracy_score(y_true, y_pred)` | 类别均衡 |
| 精确率 | `precision_score(y_true, y_pred)` | 关注误报 |
| 召回率 | `recall_score(y_true, y_pred)` | 关注漏报 |
| F1 | `f1_score(y_true, y_pred)` | 平衡 P 和 R |
| 混淆矩阵 | `confusion_matrix(y_true, y_pred)` | 全面分析 |
| 分类报告 | `classification_report(y_true, y_pred)` | 一键输出所有指标 |
| ROC 曲线 | `roc_curve(y_true, y_score)` | 不同阈值表现 |
| AUC | `roc_auc_score(y_true, y_score)` | 综合评估 |
| PR 曲线 | `precision_recall_curve(y_true, y_score)` | 不平衡数据 |

## 常用代码模板

```python
# 基础训练流程
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
model.fit(X_train_scaled, y_train)

# 预测
y_pred = model.predict(X_test_scaled)
y_prob = model.predict_proba(X_test_scaled)[:, 1]

# 交叉验证
from sklearn.model_selection import cross_val_score
cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
```
