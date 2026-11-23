"""
Day 112 — 02-grid-search.py
网格搜索调参：从手动调参到 GridSearchCV，结合 Pipeline 进行超参数搜索

运行方式：python 02-grid-search.py
"""

import numpy as np
import warnings
warnings.filterwarnings('ignore')

from sklearn.datasets import make_classification, load_breast_cancer
from sklearn.model_selection import (
    train_test_split,
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.decomposition import PCA
from scipy.stats import randint, uniform

# ============================================================
# 1. 生成数据
# ============================================================
print("=" * 60)
print("1. 加载数据")
print("=" * 60)

# 使用乳腺癌数据集（更接近真实场景）
data = load_breast_cancer()
X, y = data.data, data.target

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"训练集: {X_train.shape}, 测试集: {X_test.shape}")
print(f"特征数: {X.shape[1]}")
print(f"类别分布: {np.bincount(y)}")

# ============================================================
# 2. 手动调参 vs 网格搜索
# ============================================================
print("\n" + "=" * 60)
print("2. 手动调参的问题")
print("=" * 60)

# 手动尝试不同参数
print("手动尝试 SVM 的 C 参数:")
for C in [0.01, 0.1, 1, 10, 100]:
    model = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', SVC(C=C, random_state=42))
    ])
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
    print(f"  C={C:<8} 得分: {scores.mean():.4f} (+/- {scores.std()*2:.4f})")

print("\n⚠️  手动调参的问题:")
print("  1. 需要逐个尝试，效率低下")
print("  2. 难以考虑参数之间的交互作用")
print("  3. 结果分散，难以比较")

# ============================================================
# 3. GridSearchCV 基础
# ============================================================
print("\n" + "=" * 60)
print("3. GridSearchCV 基础用法")
print("=" * 60)

# 定义简单搜索空间
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', SVC(random_state=42))
])

param_grid = {
    'clf__C': [0.01, 0.1, 1, 10, 100],
    'clf__kernel': ['linear', 'rbf'],
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

grid_search = GridSearchCV(
    estimator=pipeline,
    param_grid=param_grid,
    cv=cv,
    scoring='accuracy',
    n_jobs=-1,
    verbose=0,
    return_train_score=True,
)

grid_search.fit(X_train, y_train)

print(f"搜索空间大小: {np.prod([len(v) for v in param_grid.values()])} 种组合")
print(f"交叉验证折数: 5")
print(f"总训练次数: {np.prod([len(v) for v in param_grid.values()]) * 5}")
print(f"\n最佳参数: {grid_search.best_params_}")
print(f"最佳交叉验证得分: {grid_search.best_score_:.4f}")
print(f"测试集得分: {grid_search.score(X_test, y_test):.4f}")

# ============================================================
# 4. 查看搜索结果详情
# ============================================================
print("\n" + "=" * 60)
print("4. 搜索结果详情")
print("=" * 60)

# 将结果整理成 DataFrame 风格
import pandas as pd
results = pd.DataFrame(grid_search.cv_results_)

# 显示关键列
cols = ['params', 'mean_test_score', 'std_test_score', 'rank_test_score']
print(results[cols].sort_values('rank_test_score').to_string(index=False))

# ============================================================
# 5. 多参数组合搜索
# ============================================================
print("\n" + "=" * 60)
print("5. 多参数组合搜索（带 PCA）")
print("=" * 60)

pipeline_pca = Pipeline([
    ('scaler', StandardScaler()),
    ('pca', PCA(random_state=42)),
    ('clf', SVC(random_state=42))
])

param_grid_pca = {
    'pca__n_components': [5, 10, 15, 20],
    'clf__C': [0.1, 1, 10],
    'clf__kernel': ['linear', 'rbf'],
    'clf__gamma': ['scale', 'auto'],
}

search_space = np.prod([len(v) for v in param_grid_pca.values()])
print(f"搜索空间: {search_space} 种组合 × 5折 = {search_space * 5} 次训练")

grid_search_pca = GridSearchCV(
    estimator=pipeline_pca,
    param_grid=param_grid_pca,
    cv=5,
    scoring='accuracy',
    n_jobs=-1,
    verbose=0,
)

grid_search_pca.fit(X_train, y_train)

print(f"\n最佳参数: {grid_search_pca.best_params_}")
print(f"最佳CV得分: {grid_search_pca.best_score_:.4f}")
print(f"测试集得分: {grid_search_pca.score(X_test, y_test):.4f}")

# ============================================================
# 6. Pipeline + GridSearchCV 综合示例
# ============================================================
print("\n" + "=" * 60)
print("6. 综合示例：比较多个模型")
print("=" * 60)

# 定义多个模型的搜索空间
search_spaces = {
    'LogisticRegression': {
        'pipeline': Pipeline([
            ('scaler', StandardScaler()),
            ('clf', LogisticRegression(max_iter=1000, random_state=42))
        ]),
        'params': {
            'clf__C': [0.01, 0.1, 1, 10],
            'clf__penalty': ['l1', 'l2'],
            'clf__solver': ['liblinear'],
        }
    },
    'SVM': {
        'pipeline': Pipeline([
            ('scaler', StandardScaler()),
            ('clf', SVC(random_state=42))
        ]),
        'params': {
            'clf__C': [0.1, 1, 10],
            'clf__kernel': ['linear', 'rbf'],
        }
    },
    'RandomForest': {
        'pipeline': Pipeline([
            ('clf', RandomForestClassifier(random_state=42))
        ]),
        'params': {
            'clf__n_estimators': [50, 100, 200],
            'clf__max_depth': [5, 10, 20, None],
            'clf__min_samples_split': [2, 5, 10],
        }
    },
}

print(f"{'模型':<22} {'最佳CV得分':>10} {'测试得分':>10} {'最佳参数'}")
print("-" * 80)

best_score = 0
best_name = ""

for name, config in search_spaces.items():
    gs = GridSearchCV(
        estimator=config['pipeline'],
        param_grid=config['params'],
        cv=5,
        scoring='accuracy',
        n_jobs=-1,
        verbose=0,
    )
    gs.fit(X_train, y_train)
    test_score = gs.score(X_test, y_test)

    # 简化显示最佳参数
    best_params_str = str(gs.best_params_)
    if len(best_params_str) > 35:
        best_params_str = best_params_str[:35] + "..."

    print(f"{name:<22} {gs.best_score_:>10.4f} {test_score:>10.4f} {best_params_str}")

    if gs.best_score_ > best_score:
        best_score = gs.best_score_
        best_name = name

print(f"\n🏆 最佳模型: {best_name} (CV得分: {best_score:.4f})")

# ============================================================
# 7. RandomizedSearchCV（随机搜索）
# ============================================================
print("\n" + "=" * 60)
print("7. RandomizedSearchCV（随机搜索）")
print("=" * 60)

# 当搜索空间大时，随机搜索更高效
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', RandomForestClassifier(random_state=42))
])

# 定义连续分布的参数空间
param_distributions = {
    'clf__n_estimators': randint(50, 300),
    'clf__max_depth': randint(3, 30),
    'clf__min_samples_split': randint(2, 20),
    'clf__min_samples_leaf': randint(1, 10),
    'clf__max_features': uniform(0.1, 0.9),
}

print("搜索空间:")
for name, dist in param_distributions.items():
    if hasattr(dist, 'args'):
        print(f"  {name}: 均匀分布 [{dist.args[0]}, {dist.args[0] + dist.args[1]}]")
    else:
        print(f"  {name}: {dist}")

# GridSearch 需要尝试的组合数
grid_space = 10 * 27 * 18 * 9  # 离散化的近似
print(f"\nGridSearch 近似组合数: ~{grid_space}")
print(f"RandomizedSearch 运行次数: 50")

random_search = RandomizedSearchCV(
    estimator=pipeline,
    param_distributions=param_distributions,
    n_iter=50,
    cv=5,
    scoring='accuracy',
    n_jobs=-1,
    random_state=42,
    verbose=0,
)

random_search.fit(X_train, y_train)

print(f"\n最佳参数:")
for k, v in random_search.best_params_.items():
    print(f"  {k}: {v}")
print(f"最佳CV得分: {random_search.best_score_:.4f}")
print(f"测试集得分: {random_search.score(X_test, y_test):.4f}")

# ============================================================
# 8. 使用 GridSearchCV 的 best_estimator_
# ============================================================
print("\n" + "=" * 60)
print("8. 使用最佳模型")
print("=" * 60)

# GridSearchCV 的 best_estimator_ 就是用最佳参数重新训练的完整 Pipeline
best_model = grid_search.best_estimator_

print("最佳 Pipeline 结构:")
for name, step in best_model.steps:
    print(f"  {name}: {step.__class__.__name__}")

# 可以直接用 best_model 进行预测
from sklearn.metrics import classification_report

y_pred = best_model.predict(X_test)
print(f"\n分类报告:")
print(classification_report(y_test, y_pred, target_names=data.target_names))

# ============================================================
# 9. 网格搜索的最佳实践
# ============================================================
print("\n" + "=" * 60)
print("9. 网格搜索最佳实践总结")
print("=" * 60)

print("""
✅ 推荐做法:
  1. 先用 RandomizedSearchCV 粗调，再用 GridSearchCV 精调
  2. 搜索空间从大到小逐步缩小
  3. 使用 StratifiedKFold 保证每折类别比例
  4. 设置 return_train_score=True 检查过拟合
  5. 使用 n_jobs=-1 并行加速
  6. 关注 mean_test_score 而非单次得分

⚠️  常见陷阱:
  1. 搜索空间太大 → 计算成本爆炸
  2. 忘记对测试集只做 transform（应使用 Pipeline）
  3. 过度调参 → 在测试集上过拟合
  4. 只看准确率 → 不平衡数据应看 F1/AUC
""")

print("✅ 网格搜索调参完成！")
