"""
Day 110 - KNN 基础用法
=====================
学习 KNN 的基本使用方法，包括：
1. KNN 分类
2. K 值选择与交叉验证
3. 距离度量对比
4. 数据标准化的重要性
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsClassifier
from sklearn.datasets import load_iris, make_classification
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score

# ============================================================
# 1. 加载数据
# ============================================================
print("=" * 60)
print("1. 加载鸢尾花数据集")
print("=" * 60)

iris = load_iris()
X, y = iris.data, iris.target
print(f"数据形状: {X.shape}")
print(f"类别: {iris.target_names}")
print(f"特征: {iris.feature_names}")

# 划分数据集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# ============================================================
# 2. 基本 KNN 分类
# ============================================================
print("\n" + "=" * 60)
print("2. 基本 KNN 分类")
print("=" * 60)

knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train, y_train)
y_pred = knn.predict(X_test)

print(f"K=5 准确率: {accuracy_score(y_test, y_pred):.4f}")
print(f"预测概率（前5个样本）:\n{knn.predict_proba(X_test[:5])}")

# ============================================================
# 3. K 值选择
# ============================================================
print("\n" + "=" * 60)
print("3. K 值选择 - 交叉验证")
print("=" * 60)

k_range = range(1, 31)
cv_scores = []
train_scores = []

for k in k_range:
    knn = KNeighborsClassifier(n_neighbors=k)
    # 交叉验证
    scores = cross_val_score(knn, X_train, y_train, cv=5, scoring='accuracy')
    cv_scores.append(scores.mean())
    # 训练集准确率
    knn.fit(X_train, y_train)
    train_scores.append(accuracy_score(y_train, knn.predict(X_train)))

# 找最优 K
best_k = k_range[np.argmax(cv_scores)]
print(f"最优 K 值: {best_k}")
print(f"最高交叉验证准确率: {max(cv_scores):.4f}")

# 打印部分结果
print("\nK值 | 训练准确率 | 验证准确率")
print("-" * 40)
for k in [1, 3, 5, 7, 10, 15, 20, 25, 30]:
    idx = k - 1
    print(f"K={k:>2} | {train_scores[idx]:.4f}     | {cv_scores[idx]:.4f}")

# 可视化 K 值影响
plt.figure(figsize=(10, 5))
plt.plot(k_range, train_scores, 'o-', label='训练集准确率', color='blue')
plt.plot(k_range, cv_scores, 's-', label='交叉验证准确率', color='red')
plt.axvline(x=best_k, linestyle='--', color='green', label=f'最优 K={best_k}')
plt.xlabel('K 值')
plt.ylabel('准确率')
plt.title('K 值对 KNN 性能的影响')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('/root/code/Learn-Python/days/day-110-svm-knn/knn_k_selection.png', dpi=100)
print("\n✅ K 值选择图已保存")

# ============================================================
# 4. 距离度量对比
# ============================================================
print("\n" + "=" * 60)
print("4. 距离度量对比")
print("=" * 60)

metrics = ['euclidean', 'manhattan', 'chebyshev', 'minkowski']
p_values = [1, 2, 3, 5]

print(f"{'度量方式':<20} | {'准确率':<10} | 说明")
print("-" * 60)

for metric in metrics:
    if metric == 'minkowski':
        for p in p_values:
            knn = KNeighborsClassifier(n_neighbors=5, metric=metric, p=p)
            knn.fit(X_train, y_train)
            acc = accuracy_score(y_test, knn.predict(X_test))
            print(f"minkowski (p={p}){'':<10} | {acc:.4f}     | p=1曼哈顿, p=2欧氏")
    else:
        knn = KNeighborsClassifier(n_neighbors=5, metric=metric)
        knn.fit(X_train, y_train)
        acc = accuracy_score(y_test, knn.predict(X_test))
        desc = {
            'euclidean': '欧氏距离',
            'manhattan': '曼哈顿距离',
            'chebyshev': '切比雪夫距离'
        }.get(metric, '')
        print(f"{metric:<20} | {acc:.4f}     | {desc}")

# ============================================================
# 5. 数据标准化的重要性
# ============================================================
print("\n" + "=" * 60)
print("5. 数据标准化的重要性")
print("=" * 60)

# 生成特征尺度差异大的数据
X_special, y_special = make_classification(
    n_samples=300, n_features=5, n_informative=3,
    n_redundant=0, random_state=42
)
# 让第一个特征的尺度远大于其他特征
X_special[:, 0] *= 1000

X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(
    X_special, y_special, test_size=0.3, random_state=42
)

# 不做标准化
knn_no_scale = KNeighborsClassifier(n_neighbors=5)
knn_no_scale.fit(X_train_s, y_train_s)
acc_no_scale = accuracy_score(y_test_s, knn_no_scale.predict(X_test_s))

# 做标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_s)
X_test_scaled = scaler.transform(X_test_s)

knn_scaled = KNeighborsClassifier(n_neighbors=5)
knn_scaled.fit(X_train_scaled, y_train_s)
acc_scaled = accuracy_score(y_test_s, knn_scaled.predict(X_test_scaled))

print(f"不做标准化: {acc_no_scale:.4f}")
print(f"做标准化:   {acc_scaled:.4f}")
print(f"提升:       {acc_scaled - acc_no_scale:.4f}")

# ============================================================
# 6. weights 参数的影响
# ============================================================
print("\n" + "=" * 60)
print("6. weights 参数对比")
print("=" * 60)

for weights in ['uniform', 'distance']:
    knn = KNeighborsClassifier(n_neighbors=5, weights=weights)
    knn.fit(X_train, y_train)
    acc = accuracy_score(y_test, knn.predict(X_test))
    print(f"weights='{weights}': {acc:.4f}")

# ============================================================
# 7. KNN 的预测概率
# ============================================================
print("\n" + "=" * 60)
print("7. KNN 预测概率详解")
print("=" * 60)

knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train, y_train)

# 预测前5个测试样本
proba = knn.predict_proba(X_test[:5])
pred = knn.predict(X_test[:5])
true = y_test[:5]

print(f"{'样本':<6} | {'真实类别':<10} | {'预测类别':<10} | {'概率分布'}")
print("-" * 60)
for i in range(5):
    proba_str = " | ".join([f"{p:.3f}" for p in proba[i]])
    print(f"{i+1:<6} | {iris.target_names[true[i]]:<10} | {iris.target_names[pred[i]]:<10} | [{proba_str}]")

print("\n✅ KNN 基础用法学习完成！")
