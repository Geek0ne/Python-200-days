"""
Day 112 — 01-cross-validation.py
交叉验证基础：从简单划分到 K-Fold，从 K-Fold 到分层交叉验证

运行方式：python 01-cross-validation.py
"""

import numpy as np
from sklearn.datasets import make_classification
from sklearn.model_selection import (
    train_test_split,
    KFold,
    StratifiedKFold,
    cross_val_score,
    LeaveOneOut,
)
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# ============================================================
# 1. 生成模拟数据
# ============================================================
print("=" * 60)
print("1. 生成模拟数据")
print("=" * 60)

X, y = make_classification(
    n_samples=500,
    n_features=10,
    n_informative=5,
    n_redundant=2,
    n_classes=2,
    random_state=42,
)

print(f"数据集大小: {X.shape}")
print(f"类别分布: {np.bincount(y)}")
print(f"正类比例: {y.mean():.2%}")

# ============================================================
# 2. 问题演示：单次划分的不稳定性
# ============================================================
print("\n" + "=" * 60)
print("2. 单次划分的不稳定性")
print("=" * 60)

# 多次随机划分，观察分数波动
scores_single = []
for seed in range(20):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed
    )
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_train, y_train)
    scores_single.append(model.score(X_test, y_test))

print(f"20次随机划分的测试分数:")
print(f"  平均值: {np.mean(scores_single):.4f}")
print(f"  标准差: {np.std(scores_single):.4f}")
print(f"  最小值: {np.min(scores_single):.4f}")
print(f"  最大值: {np.max(scores_single):.4f}")
print(f"  分数范围: {np.max(scores_single) - np.min(scores_single):.4f}")

# ============================================================
# 3. K-Fold 交叉验证
# ============================================================
print("\n" + "=" * 60)
print("3. K-Fold 交叉验证")
print("=" * 60)

# 基础 K-Fold
kf = KFold(n_splits=5, shuffle=True, random_state=42)

model = LogisticRegression(max_iter=1000, random_state=42)
scores_kfold = cross_val_score(model, X, y, cv=kf, scoring='accuracy')

print(f"K=5 的 K-Fold 交叉验证:")
print(f"  每折分数: {scores_kfold}")
print(f"  平均分数: {scores_kfold.mean():.4f} (+/- {scores_kfold.std() * 2:.4f})")

# 手动实现 K-Fold 验证（加深理解）
print("\n手动实现 K-Fold (K=5):")
kf_manual = KFold(n_splits=5, shuffle=True, random_state=42)
manual_scores = []

for fold, (train_idx, val_idx) in enumerate(kf_manual.split(X)):
    X_train_fold, X_val_fold = X[train_idx], X[val_idx]
    y_train_fold, y_val_fold = y[train_idx], y[val_idx]

    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_train_fold, y_train_fold)
    score = model.score(X_val_fold, y_val_fold)
    manual_scores.append(score)

    print(f"  折 {fold + 1}: 训练集 {len(train_idx)} 样本, "
          f"验证集 {len(val_idx)} 样本, 分数: {score:.4f}")

print(f"  手动平均分数: {np.mean(manual_scores):.4f}")

# ============================================================
# 4. Stratified K-Fold（分层交叉验证）
# ============================================================
print("\n" + "=" * 60)
print("4. Stratified K-Fold（分层交叉验证）")
print("=" * 60)

# 模拟类别不平衡数据
X_imbalanced, y_imbalanced = make_classification(
    n_samples=300,
    n_features=10,
    n_classes=2,
    weights=[0.9, 0.1],  # 90% vs 10%
    random_state=42,
)

print(f"不平衡数据集类别分布: {np.bincount(y_imbalanced)}")
print(f"少数类比例: {y_imbalanced.mean():.2%}")

# 普通 K-Fold vs Stratified K-Fold
kf_normal = KFold(n_splits=5, shuffle=True, random_state=42)
kf_stratified = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("\n普通 K-Fold 每折类别分布:")
for i, (_, val_idx) in enumerate(kf_normal.split(X_imbalanced)):
    fold_y = y_imbalanced[val_idx]
    print(f"  折{i+1}: 类别0={np.sum(fold_y==0)}, 类别1={np.sum(fold_y==1)} "
          f"(少数类比例: {fold_y.mean():.2%})")

print("\nStratified K-Fold 每折类别分布:")
for i, (_, val_idx) in enumerate(kf_stratified.split(X_imbalanced, y_imbalanced)):
    fold_y = y_imbalanced[val_idx]
    print(f"  折{i+1}: 类别0={np.sum(fold_y==0)}, 类别1={np.sum(fold_y==1)} "
          f"(少数类比例: {fold_y.mean():.2%})")

# 性能比较
model = LogisticRegression(max_iter=1000, random_state=42)
scores_normal = cross_val_score(model, X_imbalanced, y_imbalanced, cv=5, scoring='f1')
scores_stratified = cross_val_score(
    model, X_imbalanced, y_imbalanced,
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    scoring='f1'
)

print(f"\n性能比较 (F1 Score):")
print(f"  普通 K-Fold:    {scores_normal.mean():.4f} (+/- {scores_normal.std() * 2:.4f})")
print(f"  Stratified:     {scores_stratified.mean():.4f} (+/- {scores_stratified.std() * 2:.4f})")

# ============================================================
# 5. 不同模型的交叉验证比较
# ============================================================
print("\n" + "=" * 60)
print("5. 不同模型的交叉验证比较")
print("=" * 60)

# 构建不同模型的 Pipeline
models = {
    'Logistic Regression': Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(max_iter=1000, random_state=42))
    ]),
    'SVM (RBF)': Pipeline([
        ('scaler', StandardScaler()),
        ('clf', SVC(random_state=42))
    ]),
    'Random Forest': Pipeline([
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ]),
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print(f"{'模型':<25} {'平均分':>8} {'标准差':>8} {'每折分数'}")
print("-" * 75)

for name, pipeline in models.items():
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring='accuracy')
    fold_str = ' '.join([f'{s:.3f}' for s in scores])
    print(f"{name:<25} {scores.mean():>8.4f} {scores.std()*2:>8.4f} {fold_str}")

# ============================================================
# 6. 不同 K 值的比较
# ============================================================
print("\n" + "=" * 60)
print("6. 不同 K 值的交叉验证比较")
print("=" * 60)

model = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', LogisticRegression(max_iter=1000, random_state=42))
])

k_values = [3, 5, 7, 10, 15]

print(f"{'K值':>4} {'平均分':>8} {'标准差':>8} {'训练样本数/折':>14}")
print("-" * 40)

for k in k_values:
    cv_k = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=cv_k, scoring='accuracy')
    train_size = int(X.shape[0] * (k - 1) / k)
    print(f"{k:>4} {scores.mean():>8.4f} {scores.std()*2:>8.4f} {train_size:>14}")

# ============================================================
# 7. Leave-One-Out (LOO) 交叉验证
# ============================================================
print("\n" + "=" * 60)
print("7. Leave-One-Out (LOO) 交叉验证")
print("=" * 60)

# LOO 计算成本很高，只用小数据集演示
X_small, y_small = X[:50], y[:50]

loo = LeaveOneOut()
model = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', LogisticRegression(max_iter=1000, random_state=42))
])

scores_loo = cross_val_score(model, X_small, y_small, cv=loo, scoring='accuracy')

print(f"数据集大小: {len(X_small)}")
print(f"交叉验证折数: {len(scores_loo)} (每折1个样本)")
print(f"平均准确率: {scores_loo.mean():.4f}")
print(f"正确预测数: {int(scores_loo.sum())} / {len(scores_loo)}")

# ============================================================
# 8. cross_val_score 的 scoring 参数
# ============================================================
print("\n" + "=" * 60)
print("8. 不同评估指标")
print("=" * 60)

model = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', LogisticRegression(max_iter=1000, random_state=42))
])

scoring_metrics = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']

print(f"{'指标':<15} {'平均值':>8} {'标准差':>8}")
print("-" * 35)

for metric in scoring_metrics:
    try:
        scores = cross_val_score(model, X, y, cv=5, scoring=metric)
        print(f"{metric:<15} {scores.mean():>8.4f} {scores.std()*2:>8.4f}")
    except Exception as e:
        print(f"{metric:<15} 错误: {e}")

print("\n✅ 交叉验证基础完成！")
print("💡 关键要点:")
print("  1. 交叉验证提供比单次划分更可靠的模型评估")
print("  2. StratifiedKFold 在分类问题中应优先使用")
print("  3. K=5 或 K=10 是常用选择")
print("  4. 使用合适的评估指标（不平衡数据用 F1/AUC）")
