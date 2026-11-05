"""
Day 108 - 01: 逻辑回归基础用法
学习 LogisticRegression 的基本使用流程
"""
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

# ==================== 1. 加载数据 ====================
# 乳腺癌数据集：30 个特征，二分类（恶性/良性）
data = load_breast_cancer()
X, y = data.data, data.target

print(f"📊 数据集信息:")
print(f"  样本数: {X.shape[0]}")
print(f"  特征数: {X.shape[1]}")
print(f"  类别: {list(data.target_names)}")
print(f"  类别分布: 恶性={sum(y==0)}, 良性={sum(y==1)}")

# ==================== 2. 划分数据集 ====================
# stratify=y 确保训练集和测试集类别比例一致
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n数据划分:")
print(f"  训练集: {X_train.shape[0]} 样本")
print(f"  测试集: {X_test.shape[0]} 样本")

# ==================== 3. 特征标准化 ====================
# ⚠️ 逻辑回归对特征尺度非常敏感，必须标准化！
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)  # fit 只在训练集上
X_test_scaled = scaler.transform(X_test)        # transform 应用到测试集

print(f"\n标准化前 - 特征均值范围: [{X_train.mean(axis=0).min():.2f}, {X_train.mean(axis=0).max():.2f}]")
print(f"标准化后 - 特征均值范围: [{X_train_scaled.mean(axis=0).min():.4f}, {X_train_scaled.mean(axis=0).max():.4f}]")

# ==================== 4. 创建并训练模型 ====================
model = LogisticRegression(
    penalty='l2',      # L2 正则化（默认）
    C=1.0,             # 正则化强度倒数
    solver='lbfgs',    # 优化算法
    max_iter=1000,     # 最大迭代次数
    random_state=42
)

model.fit(X_train_scaled, y_train)
print(f"\n✅ 模型训练完成")
print(f"  实际迭代次数: {model.n_iter_[0]}")

# ==================== 5. 预测 ====================
y_pred = model.predict(X_test_scaled)         # 类别预测
y_prob = model.predict_proba(X_test_scaled)   # 概率预测

# 展示前 5 个样本的预测结果
print(f"\n📋 预测结果示例 (前 5 个):")
print(f"{'样本':>6} {'真实':>6} {'预测':>6} {'概率(恶性)':>12} {'概率(良性)':>12}")
print("-" * 50)
for i in range(5):
    print(f"  {i+1:>4} {y_test[i]:>6} {y_pred[i]:>6} {y_prob[i][0]:>12.4f} {y_prob[i][1]:>12.4f}")

# ==================== 6. 评估 ====================
accuracy = accuracy_score(y_test, y_pred)
print(f"\n📊 模型评估:")
print(f"  准确率: {accuracy:.4f} ({accuracy*100:.2f}%)")
print(f"\n分类报告:")
print(classification_report(y_test, y_pred, target_names=data.target_names))

# ==================== 7. 查看模型参数 ====================
print(f"📊 模型参数:")
print(f"  权重系数 shape: {model.coef_.shape}")
print(f"  偏置项: {model.intercept_[0]:.4f}")

# 找出最重要的 5 个特征
importance = np.abs(model.coef_[0])
top5_idx = np.argsort(importance)[::-1][:5]
print(f"\nTop 5 重要特征:")
for i, idx in enumerate(top5_idx):
    print(f"  {i+1}. {data.feature_names[idx]}: {importance[idx]:.4f}")
