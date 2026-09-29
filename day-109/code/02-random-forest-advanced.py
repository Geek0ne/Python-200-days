"""
Day 109 - 示例2：随机森林进阶用法
学习随机森林的超参数调优、OOB评估、特征重要性分析
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.datasets import make_classification
from sklearn.metrics import accuracy_score, classification_report
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt

# ========== 1. 创建模拟数据集 ==========
print("=" * 60)
print("🌲 随机森林进阶 — 超参数调优与特征分析")
print("=" * 60)

X, y = make_classification(
    n_samples=1000,
    n_features=10,
    n_informative=5,      # 真正有用的特征数
    n_redundant=2,         # 冗余特征数
    n_classes=2,
    random_state=42,
    flip_y=0.1             # 加入10%标签噪声
)

feature_names = [f'feature_{i}' for i in range(10)]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"样本数: {len(X)}, 特征数: 10")
print(f"有用特征: 5, 冗余特征: 2, 噪声特征: 3")
print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")

# ========== 2. 基础随机森林 ==========
print("\n" + "=" * 60)
print("🌲 Step 1: 基础随机森林")
print("=" * 60)

rf_base = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    n_jobs=-1,
    oob_score=True
)
rf_base.fit(X_train, y_train)

print(f"训练准确率: {rf_base.score(X_train, y_train):.4f}")
print(f"测试准确率: {rf_base.score(X_test, y_test):.4f}")
print(f"OOB 评分: {rf_base.oob_score_:.4f}")

# ========== 3. 超参数调优 ==========
print("\n" + "=" * 60)
print("🔧 Step 2: 超参数调优 (GridSearch)")
print("=" * 60)

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [5, 10, 15, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'max_features': ['sqrt', 'log2', 0.3]
}

# 使用随机搜索代替网格搜索（更快）
from sklearn.model_selection import RandomizedSearchCV

random_search = RandomizedSearchCV(
    RandomForestClassifier(random_state=42, n_jobs=-1),
    param_distributions=param_grid,
    n_iter=30,           # 随机尝试30个组合
    cv=5,
    scoring='f1',
    random_state=42,
    n_jobs=-1
)

random_search.fit(X_train, y_train)

print(f"最佳参数: {random_search.best_params_}")
print(f"最佳 CV F1: {random_search.best_score_:.4f}")

best_rf = random_search.best_estimator_
print(f"测试集准确率: {best_rf.score(X_test, y_test):.4f}")

# ========== 4. n_estimators 学习曲线 ==========
print("\n" + "=" * 60)
print("📈 Step 3: 树数量 vs 性能")
print("=" * 60)

n_estimators_range = [10, 25, 50, 100, 200, 300, 500]
train_scores = []
test_scores = []

for n in n_estimators_range:
    rf_temp = RandomForestClassifier(n_estimators=n, random_state=42, n_jobs=-1)
    rf_temp.fit(X_train, y_train)
    train_scores.append(accuracy_score(y_train, rf_temp.predict(X_train)))
    test_scores.append(accuracy_score(y_test, rf_temp.predict(X_test)))

print(f"{'树数量':<10} {'训练准确率':<12} {'测试准确率':<12}")
print("-" * 40)
for n, tr, te in zip(n_estimators_range, train_scores, test_scores):
    print(f"{n:<10} {tr:<12.4f} {te:<12.4f}")

# ========== 5. 特征重要性分析 ==========
print("\n" + "=" * 60)
print("🔍 Step 4: 特征重要性分析")
print("=" * 60)

# MDI 重要性
print("\n--- 基于不纯度的重要性 (MDI) ---")
importances_mdi = best_rf.feature_importances_
indices = np.argsort(importances_mdi)[::-1]

for i, idx in enumerate(indices):
    bar = "█" * int(importances_mdi[idx] * 50)
    print(f"  {i+1}. feature_{idx}: {importances_mdi[idx]:.4f} {bar}")

# Permutation 重要性
print("\n--- 基于排列的重要性 (Permutation) ---")
perm_result = permutation_importance(best_rf, X_test, y_test,
                                      n_repeats=10, random_state=42, n_jobs=-1)
perm_indices = np.argsort(perm_result.importances_mean)[::-1]

for i, idx in enumerate(perm_indices):
    bar = "█" * int(perm_result.importances_mean[idx] * 50)
    print(f"  {i+1}. feature_{idx}: {perm_result.importances_mean[idx]:.4f} ± "
          f"{perm_result.importances_std[idx]:.4f} {bar}")

# ========== 6. 可视化 ==========
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 图1: 树数量 vs 性能
axes[0, 0].plot(n_estimators_range, train_scores, 'o-', label='训练集', color='#2196F3')
axes[0, 0].plot(n_estimators_range, test_scores, 's-', label='测试集', color='#F44336')
axes[0, 0].set_xlabel('树数量 (n_estimators)')
axes[0, 0].set_ylabel('准确率')
axes[0, 0].set_title('树数量 vs 模型性能')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# 图2: MDI 特征重要性
axes[0, 1].barh(range(10), importances_mdi[indices[::-1]], color='#4CAF50', alpha=0.7)
axes[0, 1].set_yticks(range(10))
axes[0, 1].set_yticklabels([f'feature_{i}' for i in indices[::-1]])
axes[0, 1].set_xlabel('重要性')
axes[0, 1].set_title('特征重要性 (MDI)')

# 图3: Permutation 特征重要性
axes[1, 0].barh(range(10), perm_result.importances_mean[perm_indices[::-1]],
                xerr=perm_result.importances_std[perm_indices[::-1]],
                color='#FF9800', alpha=0.7)
axes[1, 0].set_yticks(range(10))
axes[1, 0].set_yticklabels([f'feature_{i}' for i in perm_indices[::-1]])
axes[1, 0].set_xlabel('重要性')
axes[1, 0].set_title('特征重要性 (Permutation)')

# 图4: 两种重要性对比
x_pos = np.arange(10)
width = 0.35
axes[1, 1].bar(x_pos - width/2, importances_mdi, width, label='MDI', color='#2196F3', alpha=0.7)
axes[1, 1].bar(x_pos + width/2, perm_result.importances_mean, width, label='Permutation', color='#F44336', alpha=0.7)
axes[1, 1].set_xticks(x_pos)
axes[1, 1].set_xticklabels([f'f{i}' for i in range(10)], rotation=45)
axes[1, 1].set_ylabel('重要性')
axes[1, 1].set_title('MDI vs Permutation 重要性对比')
axes[1, 1].legend()

plt.suptitle('随机森林进阶分析', fontsize=16, y=1.02)
plt.tight_layout()
plt.savefig('02-random-forest-analysis.png', dpi=150, bbox_inches='tight')
print("\n✅ 分析图已保存至 02-random-forest-analysis.png")

plt.close()
print("\n✅ 示例2完成!")
