"""
Day 106 - 代码示例 3：实战案例 —— 手写数字识别（MNIST 简化版）

完整 ML 流程：
1. 数据加载与探索
2. 数据预处理
3. 多模型训练与对比
4. 混淆矩阵可视化（文本版）
5. 错误案例分析
"""

from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)

# 多个模型
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier

import numpy as np


def explore_data(X, y):
    """数据探索"""
    print("=" * 60)
    print("📊 手写数字数据集探索")
    print("=" * 60)
    print(f"  样本数: {X.shape[0]}")
    print(f"  特征数: {X.shape[1]} (8×8 像素)")
    print(f"  类别数: {len(np.unique(y))} (数字 0-9)")
    print(f"  特征范围: [{X.min():.1f}, {X.max():.1f}]")

    # 类别分布
    unique, counts = np.unique(y, return_counts=True)
    print(f"\n  类别分布:")
    for digit, count in zip(unique, counts):
        bar = "█" * (count // 10)
        print(f"    {digit}: {count:>4} ({count/len(y)*100:.1f}%) {bar}")


def visualize_digit(digit_data):
    """用文本方式可视化一个 8×8 数字"""
    pixels = digit_data.reshape(8, 8)
    print("  像素矩阵 (亮度 0-16):")
    for row in pixels:
        print("    ", end="")
        for pixel in row:
            if pixel == 0:
                print(" .", end="")
            elif pixel < 5:
                print(" ·", end="")
            elif pixel < 10:
                print(" o", end="")
            elif pixel < 14:
                print(" O", end="")
            else:
                print(" X", end="")
        print()


def compare_models_advanced(X_train, X_test, y_train, y_test):
    """多模型对比（使用 Pipeline 避免数据泄露）"""
    print("\n" + "=" * 60)
    print("🏆 多模型对比（Pipeline + Cross Validation）")
    print("=" * 60)

    models = {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]),
        "Decision Tree": Pipeline([
            ("clf", DecisionTreeClassifier(random_state=42)),
        ]),
        "Random Forest": Pipeline([
            ("clf", RandomForestClassifier(n_estimators=100, random_state=42)),
        ]),
        "SVM (RBF)": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="rbf", random_state=42)),
        ]),
        "KNN (k=5)": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", KNeighborsClassifier(n_neighbors=5)),
        ]),
    }

    print(f"\n{'模型':<25} {'CV 准确率':>10} {'测试准确率':>10}")
    print("-" * 48)

    best_score = 0
    best_name = ""
    best_model = None

    for name, pipeline in models.items():
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring="accuracy")
        pipeline.fit(X_train, y_train)
        test_score = pipeline.score(X_test, y_test)

        marker = ""
        if test_score > best_score:
            best_score = test_score
            best_name = name
            best_model = pipeline
            marker = " ⭐"

        print(f"{name:<25} {cv_scores.mean():.4f}±{cv_scores.std():.3f} {test_score:>10.4f}{marker}")

    return best_name, best_model


def error_analysis(model, X_test, y_test, target_names):
    """错误案例分析"""
    print("\n" + "=" * 60)
    print("🔍 错误案例分析")
    print("=" * 60)

    y_pred = model.predict(X_test)
    errors = np.where(y_pred != y_test)[0]

    print(f"  总测试样本: {len(y_test)}")
    print(f"  错误预测数: {len(errors)}")
    print(f"  错误率: {len(errors)/len(y_test)*100:.1f}%")

    if len(errors) > 0:
        print(f"\n  前 5 个错误案例:")
        for i, idx in enumerate(errors[:5]):
            print(f"\n  --- 错误 {i+1} ---")
            print(f"  真实标签: {target_names[y_test[idx]]}")
            print(f"  预测标签: {target_names[y_pred[idx]]}")
            visualize_digit(X_test[idx])


def confusion_matrix_text(y_true, y_pred, target_names):
    """文本版混淆矩阵可视化"""
    cm = confusion_matrix(y_true, y_pred)
    print("\n  混淆矩阵 (行=真实, 列=预测):")
    print(f"  {'':>5}", end="")
    for name in target_names:
        print(f"{name:>4}", end="")
    print()
    for i, name in enumerate(target_names):
        print(f"  {name:>5}", end="")
        for j in range(len(target_names)):
            val = cm[i][j]
            if i == j:
                print(f"\033[92m{val:>4}\033[0m", end="")  # 绿色=正确
            elif val > 0:
                print(f"\033[91m{val:>4}\033[0m", end="")  # 红色=错误
            else:
                print(f"{val:>4}", end="")
        print()


def main():
    # 1. 加载数据
    digits = load_digits()
    X, y = digits.data, digits.target
    explore_data(X, y)

    # 展示几个数字样本
    print("\n📝 数字样本展示:")
    for digit in range(5):
        idx = np.where(y == digit)[0][0]
        print(f"\n  数字 {digit}:")
        visualize_digit(X[idx])

    # 2. 数据拆分
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n📦 训练集: {X_train.shape[0]} | 测试集: {X_test.shape[0]}")

    # 3. 多模型对比
    best_name, best_model = compare_models_advanced(X_train, X_test, y_train, y_test)

    print(f"\n🏆 最终冠军: {best_name}")

    # 4. 最佳模型详细报告
    y_pred = best_model.predict(X_test)
    print(f"\n📊 {best_name} 详细分类报告:")
    print(classification_report(y_test, y_pred, target_names=[str(i) for i in range(10)]))

    # 5. 混淆矩阵
    confusion_matrix_text(y_test, y_pred, [str(i) for i in range(10)])

    # 6. 错误分析
    error_analysis(best_model, X_test, y_test, [str(i) for i in range(10)])


if __name__ == "__main__":
    main()
