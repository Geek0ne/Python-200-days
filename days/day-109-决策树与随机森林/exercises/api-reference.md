# Day 109 — API 速查与对比

## sklearn.tree.DecisionTreeClassifier

```python
from sklearn.tree import DecisionTreeClassifier

dt = DecisionTreeClassifier(
    criterion='gini',       # 'gini' | 'entropy' | 'log_loss'
    max_depth=None,         # 最大深度 (None=不限制)
    min_samples_split=2,    # 分裂所需最小样本数
    min_samples_leaf=1,     # 叶节点最小样本数
    max_features=None,      # 分裂时考虑的最大特征数
    max_leaf_nodes=None,    # 最大叶节点数
    class_weight=None,      # 类别权重 (None | 'balanced')
    random_state=None,      # 随机种子
)
dt.fit(X_train, y_train)
dt.predict(X_test)
dt.score(X_test, y_test)
dt.feature_importances_    # 特征重要性
dt.tree_                   # 底层树结构
```

## sklearn.tree.DecisionTreeRegressor

```python
from sklearn.tree import DecisionTreeRegressor

dt_reg = DecisionTreeRegressor(
    criterion='squared_error',  # 'squared_error' | 'friedman_mse' | 'absolute_error'
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    random_state=None,
)
dt_reg.fit(X_train, y_train)
dt_reg.predict(X_test)
```

## sklearn.ensemble.RandomForestClassifier

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(
    n_estimators=100,       # 树的数量
    criterion='gini',       # 分裂标准
    max_depth=None,         # 最大深度
    min_samples_split=2,    # 分裂最小样本数
    min_samples_leaf=1,     # 叶节点最小样本数
    max_features='sqrt',    # 特征子集大小 (分类默认 sqrt(p))
    bootstrap=True,         # 是否 Bootstrap 抽样
    oob_score=False,        # 是否计算 OOB 评分
    n_jobs=None,            # 并行数 (-1=全部CPU)
    random_state=None,
    class_weight=None,      # 类别权重
    warm_start=False,       # 是否复用上次训练结果
)
rf.fit(X_train, y_train)
rf.predict(X_test)
rf.score(X_test, y_test)
rf.feature_importances_    # 特征重要性
rf.oob_score_              # OOB 评分 (需 oob_score=True)
rf.estimators_             # 所有子树列表
```

## sklearn.ensemble.RandomForestRegressor

```python
from sklearn.ensemble import RandomForestRegressor

rf_reg = RandomForestRegressor(
    n_estimators=100,
    criterion='squared_error',
    max_features=1.0,      # 回归默认考虑所有特征
    bootstrap=True,
    n_jobs=None,
    random_state=None,
)
rf_reg.fit(X_train, y_train)
```

## 关键参数速查表

| 参数 | 决策树 | 随机森林 | 推荐值 |
|------|--------|----------|--------|
| `max_depth` | ✅ | ✅ | 5-15 (树) / None (森林) |
| `min_samples_split` | ✅ | ✅ | 2-20 |
| `min_samples_leaf` | ✅ | ✅ | 1-10 |
| `max_features` | ✅ | ✅ | None (树) / sqrt (森林) |
| `n_estimators` | ❌ | ✅ | 100-500 |
| `bootstrap` | ❌ | ✅ | True |
| `oob_score` | ❌ | ✅ | True (调试时) |
| `class_weight` | ✅ | ✅ | 'balanced' (不平衡时) |
| `n_jobs` | ❌ | ✅ | -1 |

## 可视化工具

```python
from sklearn.tree import plot_tree, export_text, export_graphviz

# 图形化
plot_tree(model, feature_names=..., class_names=...,
          filled=True, rounded=True, max_depth=3)

# 文本
export_text(model, feature_names=...)

# Graphviz
export_graphviz(model, out_file='tree.dot', feature_names=...,
                class_names=..., filled=True, rounded=True)
```

## 评估工具

```python
from sklearn.model_selection import cross_val_score, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.inspection import permutation_importance

# 交叉验证
cross_val_score(model, X, y, cv=5, scoring='f1')

# 超参数搜索
RandomizedSearchCV(model, param_distributions, n_iter=30, cv=5, scoring='f1')

# 排列重要性
permutation_importance(model, X_test, y_test, n_repeats=10)
```
