"""
Day 108 - 03: 实战 — 完整二分类 Pipeline
从数据探索到模型部署的完整流程
场景：信用卡欺诈检测（模拟数据）
"""
import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    confusion_matrix, classification_report,
    roc_curve, auc, precision_recall_curve,
    average_precision_score
)

# ==================== 1. 生成模拟数据（模拟欺诈检测场景） ====================
# 正常交易: 95%, 欺诈交易: 5% (类别不平衡)
X, y = make_classification(
    n_samples=10000,
    n_features=20,
    n_informative=10,
    n_redundant=5,
    n_classes=2,
    weights=[0.95, 0.05],  # 类别不平衡
    flip_y=0.01,            # 1% 标签噪声
    random_state=42
)

print("=" * 60)
print("📊 数据探索")
print("=" * 60)
print(f"总样本: {len(y)}")
print(f"正常交易: {sum(y==0)} ({sum(y==0)/len(y)*100:.1f}%)")
print(f"欺诈交易: {sum(y==1)} ({sum(y==1)/len(y)*100:.1f}%)")

# ==================== 2. 数据划分 ====================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n训练集: {len(y_train)} (欺诈: {sum(y_train==1)})")
print(f"测试集: {len(y_test)} (欺诈: {sum(y_test==1)})")

# ==================== 3. 特征标准化 ====================
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ==================== 4. 训练模型（处理类别不平衡） ====================
print("\n" + "=" * 60)
print("📊 训练模型")
print("=" * 60)

# 方案 1: 不处理不平衡
model_naive = LogisticRegression(max_iter=1000, random_state=42)
model_naive.fit(X_train_scaled, y_train)

# 方案 2: class_weight='balanced' 自动调整权重
model_balanced = LogisticRegression(
    class_weight='balanced',  # ⭐ 关键参数
    max_iter=1000,
    random_state=42
)
model_balanced.fit(X_train_scaled, y_train)

# 方案 3: 手动设置权重（欺诈样本权重更高）
model_custom = LogisticRegression(
    class_weight={0: 1, 1: 10},  # 欺诈样本权重 10 倍
    max_iter=1000,
    random_state=42
)
model_custom.fit(X_train_scaled, y_train)

# ==================== 5. 评估对比 ====================
print("\n" + "=" * 60)
print("📊 三种方案评估对比")
print("=" * 60)

models = {
    '不处理不平衡': model_naive,
    'balanced 权重': model_balanced,
    '手动权重 {0:1, 1:10}': model_custom
}

results = {}
for name, model in models.items():
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    
    cm = confusion_matrix(y_test, y_pred)
    auc_score = auc(*roc_curve(y_test, y_prob)[:2])
    
    # 关注欺诈类（正类）的 recall
    from sklearn.metrics import recall_score, precision_score, f1_score
    recall = recall_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    results[name] = {
        'accuracy': model.score(X_test_scaled, y_test),
        'recall': recall,
        'precision': precision,
        'f1': f1,
        'auc': auc_score,
        'cm': cm
    }
    
    print(f"\n📌 {name}:")
    print(f"  准确率: {results[name]['accuracy']:.4f}")
    print(f"  召回率 (欺诈检出率): {results[name]['recall']:.4f}")
    print(f"  精确率: {results[name]['precision']:.4f}")
    print(f"  F1: {results[name]['f1']:.4f}")
    print(f"  AUC: {results[name]['auc']:.4f}")
    print(f"  混淆矩阵:\n    {cm}")

# ==================== 6. 阈值调优 ====================
print("\n" + "=" * 60)
print("📊 阈值调优 (基于 balanced 模型)")
print("=" * 60)

y_prob_balanced = model_balanced.predict_proba(X_test_scaled)[:, 1]

# 不同阈值的效果
thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
print(f"\n{'阈值':>8} {'精确率':>10} {'召回率':>10} {'F1':>10}")
print("-" * 45)

for thresh in thresholds:
    y_pred_thresh = (y_prob_balanced >= thresh).astype(int)
    p = precision_score(y_test, y_pred_thresh)
    r = recall_score(y_test, y_pred_thresh)
    f = f1_score(y_test, y_pred_thresh)
    print(f"{thresh:>8.1f} {p:>10.4f} {r:>10.4f} {f:>10.4f}")

# ==================== 7. 可视化 ====================
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 图 1: ROC 曲线对比
ax1 = axes[0, 0]
for name, model in models.items():
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    roc_auc = auc(fpr, tpr)
    ax1.plot(fpr, tpr, label=f'{name} (AUC={roc_auc:.3f})', linewidth=2)

ax1.plot([0, 1], [0, 1], 'k--', alpha=0.5)
ax1.set_xlabel('假正例率 (FPR)')
ax1.set_ylabel('真正例率 (TPR)')
ax1.set_title('ROC 曲线对比')
ax1.legend(loc='lower right')
ax1.grid(True, alpha=0.3)

# 图 2: Precision-Recall 曲线
ax2 = axes[0, 1]
for name, model in models.items():
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    precision, recall, _ = precision_recall_curve(y_test, y_prob)
    ap = average_precision_score(y_test, y_prob)
    ax2.plot(recall, precision, label=f'{name} (AP={ap:.3f})', linewidth=2)

ax2.set_xlabel('召回率 (Recall)')
ax2.set_ylabel('精确率 (Precision)')
ax2.set_title('Precision-Recall 曲线')
ax2.legend(loc='lower left')
ax2.grid(True, alpha=0.3)

# 图 3: 阈值 vs 指标
ax3 = axes[1, 0]
thresh_range = np.arange(0.1, 0.9, 0.01)
precisions, recalls, f1s = [], [], []
for t in thresh_range:
    y_pred_t = (y_prob_balanced >= t).astype(int)
    precisions.append(precision_score(y_test, y_pred_t, zero_division=0))
    recalls.append(recall_score(y_test, y_pred_t))
    f1s.append(f1_score(y_test, y_pred_t))

ax3.plot(thresh_range, precisions, label='精确率', linewidth=2)
ax3.plot(thresh_range, recalls, label='召回率', linewidth=2)
ax3.plot(thresh_range, f1s, label='F1', linewidth=2)
ax3.axvline(x=0.5, color='gray', linestyle='--', alpha=0.5, label='默认阈值=0.5')
ax3.set_xlabel('阈值')
ax3.set_ylabel('分数')
ax3.set_title('阈值 vs 分类指标')
ax3.legend()
ax3.grid(True, alpha=0.3)

# 图 4: 混淆矩阵
ax4 = axes[1, 1]
cm = results['balanced 权重']['cm']
im = ax4.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
ax4.set_title('混淆矩阵 (balanced)')
ax4.set_xlabel('预测标签')
ax4.set_ylabel('真实标签')
tick_marks = np.arange(2)
ax4.set_xticks(tick_marks)
ax4.set_xticklabels(['正常', '欺诈'])
ax4.set_yticks(tick_marks)
ax4.set_yticklabels(['正常', '欺诈'])
for i in range(2):
    for j in range(2):
        ax4.text(j, i, format(cm[i, j], 'd'),
                ha="center", va="center",
                color="white" if cm[i, j] > cm.max()/2 else "black")
plt.colorbar(im, ax=ax4)

plt.tight_layout()
plt.savefig('day-108-fraud-detection.png', dpi=150, bbox_inches='tight')
print("\n✅ 可视化图表已保存")

# ==================== 8. 实用建议总结 ====================
print("\n" + "=" * 60)
print("📋 实用建议总结")
print("=" * 60)
print("""
1. 类别不平衡时:
   - 用 class_weight='balanced' 而不是手动调权重
   - 评估指标看 F1/AUC，不要只看 Accuracy
   - Precision-Recall 曲线比 ROC 更适合不平衡场景

2. 阈值选择:
   - 默认 0.5 不一定最优
   - 根据业务需求调整：高召回（宁可误报）→ 降低阈值
                      高精确（不能误报）→ 提高阈值

3. 特征工程:
   - 标准化是必须的
   - 逻辑回归对特征尺度敏感

4. 模型解释:
   - coef_ 可以看出每个特征的影响方向和大小
   - 正系数 → 特征值越大越可能属于正类
   - 适合需要可解释性的场景（如金融风控）
""")
