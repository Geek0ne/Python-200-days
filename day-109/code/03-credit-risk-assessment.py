"""
Day 109 - 示例3：实战 — 信用风险评估
完整项目：数据生成 → 特征工程 → 模型训练 → 评估 → 部署准备
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, roc_curve, precision_recall_curve
)
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 第一部分：数据准备
# ==========================================
print("=" * 60)
print("🏦 信用风险评估系统")
print("=" * 60)

def generate_credit_data(n_samples=2000, random_state=42):
    """生成模拟信用数据"""
    np.random.seed(random_state)

    data = pd.DataFrame({
        'age': np.random.randint(22, 65, n_samples),
        'income': np.random.lognormal(mean=3.5, sigma=0.7, size=n_samples).round(2),
        'debt_ratio': np.random.beta(2, 5, n_samples).round(3),
        'credit_score': np.random.normal(650, 120, n_samples).clip(300, 850).astype(int),
        'employment_years': np.random.poisson(5, n_samples),
        'loan_amount': np.random.lognormal(mean=2.5, sigma=0.8, size=n_samples).round(2),
        'num_credit_cards': np.random.poisson(2, n_samples),
        'recent_inquiries': np.random.poisson(1, n_samples),
        'has_mortgage': np.random.choice(['yes', 'no'], n_samples, p=[0.3, 0.7]),
        'education': np.random.choice(
            ['high_school', 'bachelor', 'master', 'phd'],
            n_samples, p=[0.3, 0.4, 0.2, 0.1]
        ),
    })

    # 基于业务逻辑生成违约标签
    risk_score = (
        -0.25 * (data['income'] / data['income'].max())
        + 0.35 * data['debt_ratio']
        - 0.30 * (data['credit_score'] / 850)
        - 0.10 * np.minimum(data['employment_years'], 10) / 10
        + 0.20 * (data['loan_amount'] / data['loan_amount'].max())
        + 0.10 * data['recent_inquiries'] / 5
        + 0.05 * data['num_credit_cards'] / 5
        + np.random.normal(0, 0.12, n_samples)
    )

    # 按风险分位数划分违约（约 25% 违约率）
    threshold = np.percentile(risk_score, 75)
    data['default'] = (risk_score > threshold).astype(int)

    return data

data = generate_credit_data(2000)

print(f"\n📊 数据集概况:")
print(f"  样本数: {len(data)}")
print(f"  特征数: {len(data.columns) - 1}")
print(f"  违约率: {data['default'].mean():.2%}")
print(f"\n  缺失值: {data.isnull().sum().sum()}")

# ==========================================
# 第二部分：特征工程
# ==========================================
print("\n" + "=" * 60)
print("🔧 特征工程")
print("=" * 60)

# 编码类别变量
label_encoders = {}
categorical_cols = ['has_mortgage', 'education']

for col in categorical_cols:
    le = LabelEncoder()
    data[f'{col}_encoded'] = le.fit_transform(data[col])
    label_encoders[col] = le
    print(f"  {col}: {dict(zip(le.classes_, le.transform(le.classes_)))}")

# 特征列
feature_cols = [
    'age', 'income', 'debt_ratio', 'credit_score',
    'employment_years', 'loan_amount', 'num_credit_cards',
    'recent_inquiries', 'has_mortgage_encoded', 'education_encoded'
]

X = data[feature_cols]
y = data['default']

# 划分数据集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n  训练集: {len(X_train)} 样本 (违约率 {y_train.mean():.2%})")
print(f"  测试集: {len(X_test)} 样本 (违约率 {y_test.mean():.2%})")

# ==========================================
# 第三部分：模型训练与对比
# ==========================================
print("\n" + "=" * 60)
print("🤖 模型训练与对比")
print("=" * 60)

models = {
    '决策树 (depth=5)': DecisionTreeClassifier(
        max_depth=5, min_samples_split=20, random_state=42
    ),
    '决策树 (depth=10)': DecisionTreeClassifier(
        max_depth=10, min_samples_split=10, random_state=42
    ),
    '随机森林 (100树)': RandomForestClassifier(
        n_estimators=100, max_features='sqrt', random_state=42, n_jobs=-1
    ),
    '随机森林 (300树)': RandomForestClassifier(
        n_estimators=300, max_features='sqrt', random_state=42, n_jobs=-1
    ),
}

results = {}
for name, model in models.items():
    model.fit(X_train, y_train)

    # 交叉验证
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='f1')

    # 测试集评估
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    test_f1 = classification_report(y_test, y_pred, output_dict=True)['1']['f1-score']
    auc = roc_auc_score(y_test, y_proba)

    results[name] = {
        'cv_f1_mean': cv_scores.mean(),
        'cv_f1_std': cv_scores.std(),
        'test_f1': test_f1,
        'auc': auc,
        'model': model
    }

    print(f"\n  {name}:")
    print(f"    CV F1: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"    测试 F1: {test_f1:.4f}")
    print(f"    AUC: {auc:.4f}")

# ==========================================
# 第四部分：最佳模型详细分析
# ==========================================
print("\n" + "=" * 60)
print("🏆 最佳模型分析")
print("=" * 60)

best_name = max(results, key=lambda x: results[x]['auc'])
best_model = results[best_name]['model']
print(f"最佳模型: {best_name}")

y_pred_best = best_model.predict(X_test)
y_proba_best = best_model.predict_proba(X_test)[:, 1]

print("\n分类报告:")
print(classification_report(y_test, y_pred_best,
                            target_names=['正常', '违约'],
                            digits=4))

# 混淆矩阵分析
cm = confusion_matrix(y_test, y_pred_best)
tn, fp, fn, tp = cm.ravel()
print("混淆矩阵:")
print(f"  预测正常, 实际正常 (TN): {tn}")
print(f"  预测违约, 实际正常 (FP): {fp} → 误伤好客户")
print(f"  预测正常, 实际违约 (FN): {fn} → 漏判坏客户 ⚠️")
print(f"  预测违约, 实际违约 (TP): {tp}")

# ==========================================
# 第五部分：特征重要性
# ==========================================
print("\n" + "=" * 60)
print("🔍 特征重要性")
print("=" * 60)

if hasattr(best_model, 'feature_importances_'):
    importances = best_model.feature_importances_
    indices = np.argsort(importances)[::-1]

    print(f"\n  {'排名':<6} {'特征':<25} {'重要性':<10} {'柱状图'}")
    print("  " + "-" * 60)
    for rank, idx in enumerate(indices, 1):
        bar = "█" * int(importances[idx] * 50)
        print(f"  {rank:<6} {feature_cols[idx]:<25} {importances[idx]:<10.4f} {bar}")

# ==========================================
# 第六部分：可视化
# ==========================================
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 图1: ROC 曲线对比
for name, res in results.items():
    model = res['model']
    y_proba = model.predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    axes[0, 0].plot(fpr, tpr, label=f"{name} (AUC={res['auc']:.3f})")

axes[0, 0].plot([0, 1], [0, 1], 'k--', alpha=0.3)
axes[0, 0].set_xlabel('假正率 (FPR)')
axes[0, 0].set_ylabel('真正率 (TPR)')
axes[0, 0].set_title('ROC 曲线对比')
axes[0, 0].legend(fontsize=8)
axes[0, 0].grid(True, alpha=0.3)

# 图2: 精确率-召回率曲线
for name, res in results.items():
    model = res['model']
    y_proba = model.predict_proba(X_test)[:, 1]
    precision, recall, _ = precision_recall_curve(y_test, y_proba)
    axes[0, 1].plot(recall, precision, label=name)

axes[0, 1].set_xlabel('召回率 (Recall)')
axes[0, 1].set_ylabel('精确率 (Precision)')
axes[0, 1].set_title('精确率-召回率曲线')
axes[0, 1].legend(fontsize=8)
axes[0, 1].grid(True, alpha=0.3)

# 图3: 混淆矩阵热力图
im = axes[1, 0].imshow(cm, interpolation='nearest', cmap='Blues')
axes[1, 0].set_title(f'混淆矩阵 ({best_name})')
axes[1, 0].set_xlabel('预测值')
axes[1, 0].set_ylabel('真实值')
axes[1, 0].set_xticks([0, 1])
axes[1, 0].set_yticks([0, 1])
axes[1, 0].set_xticklabels(['正常', '违约'])
axes[1, 0].set_yticklabels(['正常', '违约'])

for i in range(2):
    for j in range(2):
        color = 'white' if cm[i, j] > cm.max() / 2 else 'black'
        axes[1, 0].text(j, i, str(cm[i, j]), ha='center', va='center',
                        color=color, fontsize=14, fontweight='bold')

# 图4: 特征重要性
if hasattr(best_model, 'feature_importances_'):
    colors = ['#F44336' if i < 3 else '#4CAF50' for i in range(len(feature_cols))]
    axes[1, 1].barh(range(len(feature_cols)),
                     importances[indices[::-1]], color=[colors[indices[::-1][i]] for i in range(len(feature_cols))])
    axes[1, 1].set_yticks(range(len(feature_cols)))
    axes[1, 1].set_yticklabels([feature_cols[i] for i in indices[::-1]])
    axes[1, 1].set_xlabel('重要性')
    axes[1, 1].set_title('特征重要性 (红色=前3重要)')
    axes[1, 1].axvline(x=importances.mean(), color='gray', linestyle='--', alpha=0.5)

plt.suptitle('信用风险评估模型分析', fontsize=16, y=1.02)
plt.tight_layout()
plt.savefig('03-credit-risk-analysis.png', dpi=150, bbox_inches='tight')
print("\n✅ 分析图已保存至 03-credit-risk-analysis.png")

# ==========================================
# 第七部分：业务建议
# ==========================================
print("\n" + "=" * 60)
print("💼 业务建议")
print("=" * 60)

print(f"""
基于模型分析结果:

1. 关键风险指标 (按重要性排序):
   - {feature_cols[indices[0]]}: 最重要的预测因子
   - {feature_cols[indices[1]]}: 第二重要
   - {feature_cols[indices[2]]}: 第三重要

2. 模型性能:
   - AUC: {results[best_name]['auc']:.4f}
   - F1 (违约类): {results[best_name]['test_f1']:.4f}
   - 该模型区分好坏客户的能力{'优秀' if results[best_name]['auc'] > 0.8 else '良好'}

3. 业务优化方向:
   - 漏判坏客户 (FN={fn}) 会导致坏账损失 → 可降低分类阈值提高召回率
   - 误伤好客户 (FP={fp}) 会损失利息收入 → 权衡业务成本后调整阈值
   - 建议定期用新数据重新训练模型
""")

plt.close()
print("🎉 信用风险评估实战完成!")
