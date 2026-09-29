"""
Day 108 - 02: 逻辑回归进阶 — 正则化对比与交叉验证
学习不同正则化强度对模型的影响，以及交叉验证的正确使用
"""
import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

# ==================== 1. 数据准备 ====================
data = load_breast_cancer()
X, y = data.data, data.target

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ==================== 2. 不同 C 值的对比实验 ====================
print("=" * 60)
print("📊 实验 1: 正则化强度对比")
print("=" * 60)

C_values = [0.001, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
results = []

for C in C_values:
    model = LogisticRegression(C=C, max_iter=5000, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    train_acc = model.score(X_train_scaled, y_train)
    test_acc = model.score(X_test_scaled, y_test)
    
    # 5 折交叉验证
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
    
    # AUC 评估
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    
    results.append({
        'C': C,
        'train_acc': train_acc,
        'test_acc': test_acc,
        'cv_mean': cv_scores.mean(),
        'cv_std': cv_scores.std(),
        'auc': auc,
        'n_params': np.sum(np.abs(model.coef_) > 0.01)  # 有效参数数量
    })

# 打印结果表格
print(f"\n{'C值':>10} {'训练集':>10} {'测试集':>10} {'CV均值±std':>16} {'AUC':>8}")
print("-" * 60)
for r in results:
    print(f"{r['C']:>10.3f} {r['train_acc']:>10.4f} {r['test_acc']:>10.4f} "
          f"{r['cv_mean']:>7.4f}±{r['cv_std']:.4f} {r['auc']:>8.4f}")

# ==================== 3. 分析过拟合与欠拟合 ====================
print("\n" + "=" * 60)
print("📊 分析: 过拟合与欠拟合")
print("=" * 60)

for r in results:
    gap = r['train_acc'] - r['test_acc']
    if gap > 0.05:
        status = "⚠️  过拟合"
    elif r['train_acc'] < 0.90:
        status = "⚠️  欠拟合"
    else:
        status = "✅ 良好"
    print(f"  C={r['C']:<8} 训练-测试差距={gap:.4f} → {status}")

# ==================== 4. 网格搜索最优参数 ====================
print("\n" + "=" * 60)
print("📊 实验 2: GridSearchCV 网格搜索")
print("=" * 60)

param_grid = {
    'C': [0.001, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0],
    'penalty': ['l1', 'l2'],
    'solver': ['liblinear']  # liblinear 支持 L1
}

grid_search = GridSearchCV(
    LogisticRegression(max_iter=5000, random_state=42),
    param_grid,
    cv=5,
    scoring='roc_auc',
    n_jobs=-1,
    verbose=0
)
grid_search.fit(X_train_scaled, y_train)

print(f"\n🏆 最优参数: {grid_search.best_params_}")
print(f"🏆 最优 CV AUC: {grid_search.best_score_:.4f}")

best_model = grid_search.best_estimator_
test_auc = roc_auc_score(y_test, best_model.predict_proba(X_test_scaled)[:, 1])
print(f"🏆 测试集 AUC: {test_auc:.4f}")

# ==================== 5. 可视化 ====================
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 图 1: 准确率 vs C
ax1 = axes[0, 0]
ax1.plot([r['C'] for r in results], [r['train_acc'] for r in results], 
         'o-', label='训练集', color='blue')
ax1.plot([r['C'] for r in results], [r['test_acc'] for r in results], 
         's-', label='测试集', color='red')
ax1.plot([r['C'] for r in results], [r['cv_mean'] for r in results], 
         '^-', label='CV 均值', color='green')
ax1.set_xscale('log')
ax1.set_xlabel('C (正则化强度倒数)')
ax1.set_ylabel('准确率')
ax1.set_title('正则化强度 vs 准确率')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 图 2: AUC vs C
ax2 = axes[0, 1]
ax2.plot([r['C'] for r in results], [r['auc'] for r in results], 
         'D-', color='purple', linewidth=2)
ax2.set_xscale('log')
ax2.set_xlabel('C (正则化强度倒数)')
ax2.set_ylabel('AUC')
ax2.set_title('正则化强度 vs AUC')
ax2.grid(True, alpha=0.3)

# 图 3: 训练-测试差距
ax3 = axes[1, 0]
gaps = [r['train_acc'] - r['test_acc'] for r in results]
colors = ['red' if g > 0.05 else 'green' for g in gaps]
ax3.bar(range(len(results)), gaps, color=colors, alpha=0.7)
ax3.set_xticks(range(len(results)))
ax3.set_xticklabels([str(r['C']) for r in results], rotation=45)
ax3.set_xlabel('C 值')
ax3.set_ylabel('训练集 - 测试集 准确率差')
ax3.set_title('过拟合指标 (差距 > 0.05 视为过拟合)')
ax3.axhline(y=0.05, color='red', linestyle='--', alpha=0.5)

# 图 4: 系数大小随 C 的变化
ax4 = axes[1, 1]
coef_norms = []
for C in C_values:
    model = LogisticRegression(C=C, max_iter=5000, random_state=42)
    model.fit(X_train_scaled, y_train)
    coef_norms.append(np.linalg.norm(model.coef_))

ax4.plot(C_values, coef_norms, 'o-', color='orange', linewidth=2)
ax4.set_xscale('log')
ax4.set_xlabel('C (正则化强度倒数)')
ax4.set_ylabel('权重 L2 范数')
ax4.set_title('权重大小随正则化强度变化')
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('day-108-regularization-analysis.png', dpi=150, bbox_inches='tight')
print("\n✅ 分析图表已保存")

# ==================== 6. 交叉验证详解 ====================
print("\n" + "=" * 60)
print("📊 交叉验证详解 (以最优模型为例)")
print("=" * 60)

cv_scores = cross_val_score(best_model, X_train_scaled, y_train, cv=5, scoring='accuracy')
print(f"\n5 折交叉验证结果:")
for i, score in enumerate(cv_scores):
    print(f"  Fold {i+1}: {score:.4f}")
print(f"  均值: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# 验证集 vs 测试集的区别
print(f"\n📌 交叉验证 vs 单次划分:")
print(f"  交叉验证 CV 均值: {cv_scores.mean():.4f}")
print(f"  单次测试集准确率: {best_model.score(X_test_scaled, y_test):.4f}")
print(f"  → CV 更稳定，因为它用了所有数据做评估")
