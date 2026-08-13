"""
Day 110 - SVM 基础用法
=====================
学习 SVM 的基本使用方法，包括：
1. 线性 SVM 分类
2. RBF 核 SVM 分类
3. 参数 C 和 gamma 的影响
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 无头模式
import matplotlib.pyplot as plt
from sklearn.svm import SVC, LinearSVC
from sklearn.datasets import make_moons, make_circles, make_classification
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# ============================================================
# 1. 生成示例数据
# ============================================================
print("=" * 60)
print("1. 生成示例数据")
print("=" * 60)

# 生成线性可分数据
X_linear, y_linear = make_classification(
    n_samples=200, n_features=2, n_redundant=0, n_informative=2,
    random_state=1, n_clusters_per_class=1, class_sep=2.0
)

# 生成月亮形数据（非线性可分）
X_moons, y_moons = make_moons(n_samples=200, noise=0.1, random_state=42)

print(f"线性数据: {X_linear.shape}, 类别分布: {np.bincount(y_linear)}")
print(f"月亮数据: {X_moons.shape}, 类别分布: {np.bincount(y_moons)}")

# ============================================================
# 2. 线性 SVM
# ============================================================
print("\n" + "=" * 60)
print("2. 线性 SVM")
print("=" * 60)

# 数据标准化（SVM 必须！）
scaler = StandardScaler()
X_linear_scaled = scaler.fit_transform(X_linear)

# 划分训练/测试集
X_train, X_test, y_train, y_test = train_test_split(
    X_linear_scaled, y_linear, test_size=0.3, random_state=42
)

# 线性 SVM
svm_linear = SVC(kernel='linear', C=1.0)
svm_linear.fit(X_train, y_train)
y_pred = svm_linear.predict(X_test)

print(f"准确率: {accuracy_score(y_test, y_pred):.4f}")
print(f"支持向量数量: {svm_linear.n_support_}")
print(f"支持向量总数: {sum(svm_linear.n_support_)}")

# ============================================================
# 3. RBF 核 SVM（处理非线性数据）
# ============================================================
print("\n" + "=" * 60)
print("3. RBF 核 SVM")
print("=" * 60)

X_moons_scaled = scaler.fit_transform(X_moons)
X_train_m, X_test_m, y_train_m, y_test_m = train_test_split(
    X_moons_scaled, y_moons, test_size=0.3, random_state=42
)

# RBF 核
svm_rbf = SVC(kernel='rbf', C=1.0, gamma='scale')
svm_rbf.fit(X_train_m, y_train_m)
y_pred_m = svm_rbf.predict(X_test_m)

print(f"准确率: {accuracy_score(y_test_m, y_pred_m):.4f}")
print(f"支持向量数量: {svm_rbf.n_support_}")

# ============================================================
# 4. 参数 C 的影响
# ============================================================
print("\n" + "=" * 60)
print("4. 参数 C 的影响对比")
print("=" * 60)

C_values = [0.01, 0.1, 1, 10, 100]
for C in C_values:
    svm = SVC(kernel='rbf', C=C, gamma='scale')
    svm.fit(X_train_m, y_train_m)
    train_acc = accuracy_score(y_train_m, svm.predict(X_train_m))
    test_acc = accuracy_score(y_test_m, svm.predict(X_test_m))
    n_sv = sum(svm.n_support_)
    print(f"C={C:>6} | 训练准确率: {train_acc:.4f} | 测试准确率: {test_acc:.4f} | 支持向量: {n_sv}")

# ============================================================
# 5. 参数 gamma 的影响
# ============================================================
print("\n" + "=" * 60)
print("5. 参数 gamma 的影响对比")
print("=" * 60)

gamma_values = ['scale', 'auto', 0.01, 0.1, 1, 10]
for gamma in gamma_values:
    svm = SVC(kernel='rbf', C=1.0, gamma=gamma)
    svm.fit(X_train_m, y_train_m)
    train_acc = accuracy_score(y_train_m, svm.predict(X_train_m))
    test_acc = accuracy_score(y_test_m, svm.predict(X_test_m))
    n_sv = sum(svm.n_support_)
    print(f"gamma={str(gamma):>6} | 训练准确率: {train_acc:.4f} | 测试准确率: {test_acc:.4f} | 支持向量: {n_sv}")

# ============================================================
# 6. 决策边界可视化
# ============================================================
print("\n" + "=" * 60)
print("6. 保存决策边界图")
print("=" * 60)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for idx, (kernel, title) in enumerate([
    ('linear', '线性核'),
    ('rbf', 'RBF 核 (gamma=scale)'),
    ('poly', '多项式核 (degree=3)')
]):
    svm = SVC(kernel=kernel, C=1.0, gamma='scale', degree=3)
    svm.fit(X_train_m, y_train_m)

    # 创建网格
    h = 0.02
    x_min, x_max = X_train_m[:, 0].min() - 1, X_train_m[:, 0].max() + 1
    y_min, y_max = X_train_m[:, 1].min() - 1, X_train_m[:, 1].max() + 1
    xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))

    Z = svm.predict(np.c_[xx.ravel(), yy.ravel()])
    Z = Z.reshape(xx.shape)

    axes[idx].contourf(xx, yy, Z, alpha=0.3, cmap=plt.cm.RdYlBu)
    axes[idx].scatter(X_train_m[:, 0], X_train_m[:, 1], c=y_train_m,
                      cmap=plt.cm.RdYlBu, edgecolors='black', s=30)
    axes[idx].set_title(f'{title}\n准确率: {accuracy_score(y_test_m, svm.predict(X_test_m)):.3f}')
    axes[idx].set_xlabel('特征 1')
    axes[idx].set_ylabel('特征 2')

plt.tight_layout()
plt.savefig('/root/code/Learn-Python/days/day-110-svm-knn/svm_boundaries.png', dpi=100)
print("✅ 决策边界图已保存到 svm_boundaries.png")

# ============================================================
# 7. 多分类：One-vs-Rest
# ============================================================
print("\n" + "=" * 60)
print("7. 多分类示例")
print("=" * 60)

# 使用手写数字数据集
from sklearn.datasets import load_digits
digits = load_digits()
X_d, y_d = digits.data, digits.target

X_train_d, X_test_d, y_train_d, y_test_d = train_test_split(
    X_d, y_d, test_size=0.3, random_state=42
)

scaler_d = StandardScaler()
X_train_d = scaler_d.fit_transform(X_train_d)
X_test_d = scaler_d.transform(X_test_d)

# SVM 多分类（默认使用 OvO）
svm_multi = SVC(kernel='rbf', C=10, gamma='scale')
svm_multi.fit(X_train_d, y_train_d)
y_pred_d = svm_multi.predict(X_test_d)

print(f"手写数字识别准确率: {accuracy_score(y_test_d, y_pred_d):.4f}")
print(f"每个类别的支持向量数: {svm_multi.n_support_}")

print("\n✅ SVM 基础用法学习完成！")
