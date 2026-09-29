"""
Day 110 - 实战：手写数字识别
===========================
使用 SVM 和 KNN 对比完成手写数字识别任务

数据集：sklearn 内置 digits（8x8 像素手写数字图片）
目标：对比 SVM 和 KNN 的分类效果
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.datasets import load_digits
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, ConfusionMatrixDisplay)

# ============================================================
# 1. 加载数据
# ============================================================
print("=" * 60)
print("1. 加载手写数字数据集")
print("=" * 60)

digits = load_digits()
X, y = digits.data, digits.target

print(f"数据形状: {X.shape}")
print(f"每张图片: 8x8 = 64 个像素特征")
print(f"类别数量: {len(np.unique(y))}")
print(f"类别分布: {dict(zip(*np.unique(y, return_counts=True)))}")

# 可视化部分样本
fig, axes = plt.subplots(2, 5, figsize=(12, 5))
for i, ax in enumerate(axes.flat):
    ax.imshow(digits.images[i], cmap='gray_r')
    ax.set_title(f'标签: {digits.target[i]}', fontsize=10)
    ax.axis('off')
plt.suptitle('手写数字样本', fontsize=14)
plt.tight_layout()
plt.savefig('/root/code/Learn-Python/days/day-110-svm-knn/digit_samples.png', dpi=100)
print("✅ 样本可视化已保存")

# ============================================================
# 2. 数据预处理
# ============================================================
print("\n" + "=" * 60)
print("2. 数据预处理")
print("=" * 60)

# 划分训练/测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"训练集: {X_train.shape[0]} 样本")
print(f"测试集: {X_test.shape[0]} 样本")

# 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ============================================================
# 3. SVM 模型
# ============================================================
print("\n" + "=" * 60)
print("3. SVM 模型训练")
print("=" * 60)

# 基础 SVM
svm_basic = SVC(kernel='rbf', C=10, gamma='scale', random_state=42)
svm_basic.fit(X_train_scaled, y_train)
y_pred_svm = svm_basic.predict(X_test_scaled)

print(f"SVM (基础) 准确率: {accuracy_score(y_test, y_pred_svm):.4f}")
print(f"支持向量数: {svm_basic.n_support_}")

# 网格搜索优化 SVM
print("\n🔍 SVM 网格搜索优化...")
param_grid_svm = {
    'C': [1, 10, 100],
    'gamma': ['scale', 'auto', 0.01, 0.1],
    'kernel': ['rbf']
}

grid_svm = GridSearchCV(SVC(random_state=42), param_grid_svm, cv=5, scoring='accuracy', n_jobs=-1)
grid_svm.fit(X_train_scaled, y_train)

print(f"最优参数: {grid_svm.best_params_}")
print(f"最优交叉验证准确率: {grid_svm.best_score_:.4f}")

y_pred_svm_opt = grid_svm.predict(X_test_scaled)
print(f"优化后测试集准确率: {accuracy_score(y_test, y_pred_svm_opt):.4f}")

# ============================================================
# 4. KNN 模型
# ============================================================
print("\n" + "=" * 60)
print("4. KNN 模型训练")
print("=" * 60)

# 基础 KNN
knn_basic = KNeighborsClassifier(n_neighbors=5)
knn_basic.fit(X_train_scaled, y_train)
y_pred_knn = knn_basic.predict(X_test_scaled)

print(f"KNN (K=5) 准确率: {accuracy_score(y_test, y_pred_knn):.4f}")

# 网格搜索优化 KNN
print("\n🔍 KNN 网格搜索优化...")
param_grid_knn = {
    'n_neighbors': [3, 5, 7, 9, 11],
    'weights': ['uniform', 'distance'],
    'metric': ['euclidean', 'manhattan']
}

grid_knn = GridSearchCV(KNeighborsClassifier(), param_grid_knn, cv=5, scoring='accuracy', n_jobs=-1)
grid_knn.fit(X_train_scaled, y_train)

print(f"最优参数: {grid_knn.best_params_}")
print(f"最优交叉验证准确率: {grid_knn.best_score_:.4f}")

y_pred_knn_opt = grid_knn.predict(X_test_scaled)
print(f"优化后测试集准确率: {accuracy_score(y_test, y_pred_knn_opt):.4f}")

# ============================================================
# 5. 算法对比
# ============================================================
print("\n" + "=" * 60)
print("5. 算法对比总结")
print("=" * 60)

print(f"{'算法':<25} | {'测试准确率':<12} | {'交叉验证准确率'}")
print("-" * 60)
print(f"{'SVM (基础)':<25} | {accuracy_score(y_test, y_pred_svm):.4f}      | -")
print(f"{'SVM (优化)':<25} | {accuracy_score(y_test, y_pred_svm_opt):.4f}      | {grid_svm.best_score_:.4f}")
print(f"{'KNN (K=5)':<25} | {accuracy_score(y_test, y_pred_knn):.4f}      | -")
print(f"{'KNN (优化)':<25} | {accuracy_score(y_test, y_pred_knn_opt):.4f}      | {grid_knn.best_score_:.4f}")

# ============================================================
# 6. 分类报告
# ============================================================
print("\n" + "=" * 60)
print("6. 最优模型分类报告")
print("=" * 60)

best_name = "SVM" if accuracy_score(y_test, y_pred_svm_opt) > accuracy_score(y_test, y_pred_knn_opt) else "KNN"
best_pred = y_pred_svm_opt if best_name == "SVM" else y_pred_knn_opt

print(f"\n🏆 最优模型: {best_name}")
print(f"\n分类报告:")
print(classification_report(y_test, best_pred, target_names=[str(i) for i in range(10)]))

# ============================================================
# 7. 混淆矩阵可视化
# ============================================================
print("\n" + "=" * 60)
print("7. 混淆矩阵")
print("=" * 60)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# SVM 混淆矩阵
cm_svm = confusion_matrix(y_test, y_pred_svm_opt)
disp_svm = ConfusionMatrixDisplay(cm_svm, display_labels=digits.target_names)
disp_svm.plot(ax=axes[0], cmap='Blues', values_format='d')
axes[0].set_title(f'SVM 混淆矩阵\n准确率: {accuracy_score(y_test, y_pred_svm_opt):.4f}')

# KNN 混淆矩阵
cm_knn = confusion_matrix(y_test, y_pred_knn_opt)
disp_knn = ConfusionMatrixDisplay(cm_knn, display_labels=digits.target_names)
disp_knn.plot(ax=axes[1], cmap='Greens', values_format='d')
axes[1].set_title(f'KNN 混淆矩阵\n准确率: {accuracy_score(y_test, y_pred_knn_opt):.4f}')

plt.suptitle('手写数字识别 - 混淆矩阵对比', fontsize=14)
plt.tight_layout()
plt.savefig('/root/code/Learn-Python/days/day-110-svm-knn/confusion_matrices.png', dpi=100)
print("✅ 混淆矩阵已保存")

# ============================================================
# 8. 预测可视化
# ============================================================
print("\n" + "=" * 60)
print("8. 预测结果可视化")
print("=" * 60)

fig, axes = plt.subplots(2, 5, figsize=(14, 6))
for i, ax in enumerate(axes.flat):
    idx = i
    ax.imshow(X_test[idx].reshape(8, 8), cmap='gray_r')
    color = 'green' if best_pred[idx] == y_test[idx] else 'red'
    ax.set_title(f'预测: {best_pred[idx]}\n真实: {y_test[idx]}', color=color, fontsize=10)
    ax.axis('off')
plt.suptitle(f'{best_name} 预测结果（绿色=正确，红色=错误）', fontsize=14)
plt.tight_layout()
plt.savefig('/root/code/Learn-Python/days/day-110-svm-knn/predictions.png', dpi=100)
print("✅ 预测可视化已保存")

# ============================================================
# 9. 速度对比
# ============================================================
print("\n" + "=" * 60)
print("9. 训练速度对比")
print("=" * 60)

import time

# SVM 训练时间
start = time.time()
svm_speed = SVC(kernel='rbf', C=10, gamma='scale')
svm_speed.fit(X_train_scaled, y_train)
svm_train_time = time.time() - start

start = time.time()
svm_speed.predict(X_test_scaled)
svm_predict_time = time.time() - start

# KNN 训练时间（KNN 几乎没有训练时间）
start = time.time()
knn_speed = KNeighborsClassifier(n_neighbors=5)
knn_speed.fit(X_train_scaled, y_train)
knn_train_time = time.time() - start

start = time.time()
knn_speed.predict(X_test_scaled)
knn_predict_time = time.time() - start

print(f"{'算法':<10} | {'训练时间':<15} | {'预测时间'}")
print("-" * 50)
print(f"{'SVM':<10} | {svm_train_time*1000:.2f} ms       | {svm_predict_time*1000:.2f} ms")
print(f"{'KNN':<10} | {knn_train_time*1000:.2f} ms       | {knn_predict_time*1000:.2f} ms")

print("\n" + "=" * 60)
print("✅ 手写数字识别实战完成！")
print("=" * 60)
print(f"""
📊 总结:
- SVM (优化后) 准确率: {accuracy_score(y_test, y_pred_svm_opt):.4f}
- KNN (优化后) 准确率: {accuracy_score(y_test, y_pred_knn_opt):.4f}
- 最优模型: {best_name}
- 两个模型都表现优秀，SVM 在此数据集上略胜一筹
""")
