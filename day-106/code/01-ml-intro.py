"""
Day 106 - 代码示例 1：机器学习入门 —— 第一个 ML 模型

演示完整的 ML 工作流：加载数据 → 拆分 → 训练 → 预测 → 评估
使用经典的鸢尾花（Iris）数据集
"""

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
import numpy as np


def main():
    # ===== 1. 加载内置数据集 =====
    iris = load_iris()
    X, y = iris.data, iris.target

    print("=" * 50)
    print("🌸 鸢尾花分类 —— 第一个 ML 模型")
    print("=" * 50)
    print(f"\n📊 数据集概览:")
    print(f"  样本数: {X.shape[0]}")
    print(f"  特征数: {X.shape[1]}")
    print(f"  类别数: {len(np.unique(y))}")
    print(f"  特征名: {iris.feature_names}")
    print(f"  类别名: {list(iris.target_names)}")

    # 查看前 5 条数据
    print(f"\n前 5 条数据:")
    for i in range(5):
        print(f"  样本{i}: {X[i]} → 类别: {iris.target_names[y[i]]}")

    # ===== 2. 数据拆分 =====
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n📦 数据拆分:")
    print(f"  训练集: {X_train.shape[0]} 条")
    print(f"  测试集: {X_test.shape[0]} 条")

    # ===== 3. 特征缩放 =====
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)  # fit + transform
    X_test_scaled = scaler.transform(X_test)         # 只 transform！

    print(f"\n📐 特征缩放 (StandardScaler):")
    print(f"  训练集均值: {scaler.mean_.round(2)}")
    print(f"  训练集方差: {scaler.scale_.round(2)}")

    # ===== 4. 训练 KNN 模型 =====
    model = KNeighborsClassifier(n_neighbors=5)
    model.fit(X_train_scaled, y_train)

    print(f"\n🤖 模型训练完成: KNeighborsClassifier(k=5)")

    # ===== 5. 预测 =====
    y_pred = model.predict(X_test_scaled)

    # 查看前几个预测结果
    print(f"\n🔮 预测结果（前 10 条）:")
    print(f"  {'真实':>6} → {'预测':>6}")
    correct = 0
    for i in range(min(10, len(y_test))):
        real = iris.target_names[y_test[i]]
        pred = iris.target_names[y_pred[i]]
        mark = "✅" if y_test[i] == y_pred[i] else "❌"
        if y_test[i] == y_pred[i]:
            correct += 1
        print(f"  {real:>6} → {pred:>6}  {mark}")
    print(f"  前 10 条准确率: {correct}/{min(10, len(y_test))}")

    # ===== 6. 评估 =====
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n📈 评估结果:")
    print(f"  准确率: {accuracy:.2%}")

    print(f"\n分类报告:")
    print(classification_report(y_test, y_pred, target_names=iris.target_names))

    print(f"混淆矩阵:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  {'':>10}", end="")
    for name in iris.target_names:
        print(f"{name:>10}", end="")
    print()
    for i, name in enumerate(iris.target_names):
        print(f"  {name:>10}", end="")
        for j in range(len(iris.target_names)):
            print(f"{cm[i][j]:>10}", end="")
        print()

    # ===== 7. 预测新数据 =====
    print(f"\n🆕 预测新样本:")
    new_flower = np.array([[5.1, 3.5, 1.4, 0.2]])  # 一朵花的特征
    new_scaled = scaler.transform(new_flower)
    prediction = model.predict(new_scaled)
    probability = model.predict_proba(new_scaled)

    print(f"  输入: {new_flower[0]}")
    print(f"  预测类别: {iris.target_names[prediction[0]]}")
    print(f"  各类别概率: {dict(zip(iris.target_names, probability[0].round(3)))}")


if __name__ == "__main__":
    main()
