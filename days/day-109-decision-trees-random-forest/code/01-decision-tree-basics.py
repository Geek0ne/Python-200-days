"""
Day 109 - 示例1：决策树基础用法
学习如何使用 sklearn 构建决策树分类器
"""

import numpy as np
from sklearn.tree import DecisionTreeClassifier, plot_tree, export_text
from sklearn.model_selection import train_test_split
from sklearn.datasets import load_iris
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt

# ========== 1. 加载经典数据集 ==========
print("=" * 60)
print("🌸 鸢尾花分类 — 决策树基础")
print("=" * 60)

iris = load_iris()
X, y = iris.data, iris.target
feature_names = iris.feature_names
class_names = iris.target_names

print(f"特征: {feature_names}")
print(f"类别: {class_names}")
print(f"样本数: {len(X)}")

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)
print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")

# ========== 2. 构建决策树 ==========
# max_depth=3 限制树深度，防止过拟合
dt = DecisionTreeClassifier(
    max_depth=3,           # 最大深度
    min_samples_split=5,   # 分裂所需最小样本数
    min_samples_leaf=2,    # 叶节点最小样本数
    criterion='gini',      # 分裂标准：基尼系数
    random_state=42
)

dt.fit(X_train, y_train)

# ========== 3. 模型评估 ==========
train_acc = accuracy_score(y_train, dt.predict(X_train))
test_acc = accuracy_score(y_test, dt.predict(X_test))

print(f"\n训练集准确率: {train_acc:.4f}")
print(f"测试集准确率: {test_acc:.4f}")
print(f"过拟合差距: {train_acc - test_acc:.4f}")

print("\n分类报告:")
print(classification_report(y_test, dt.predict(X_test),
                            target_names=class_names))

# ========== 4. 文本形式可视化 ==========
print("=" * 60)
print("📄 决策树文本表示")
print("=" * 60)

tree_text = export_text(dt, feature_names=feature_names)
print(tree_text)

# ========== 5. 图形化可视化 ==========
fig, ax = plt.subplots(figsize=(16, 8))
plot_tree(dt,
          feature_names=feature_names,
          class_names=class_names,
          filled=True,       # 用颜色表示类别
          rounded=True,      # 圆角矩形
          fontsize=10,
          ax=ax)
ax.set_title('决策树可视化 — 鸢尾花分类', fontsize=16)
plt.tight_layout()
plt.savefig('01-iris-tree.png', dpi=150, bbox_inches='tight')
print("✅ 决策树图已保存至 01-iris-tree.png")

# ========== 6. 查看树的结构信息 ==========
print("\n" + "=" * 60)
print("📊 树的结构信息")
print("=" * 60)

n_nodes = dt.tree_.node_count
n_leaves = dt.tree_.n_leaves
max_depth = dt.tree_.max_depth

print(f"节点总数: {n_nodes}")
print(f"叶节点数: {n_leaves}")
print(f"树深度: {max_depth}")
print(f"特征使用次数: {dict(zip(feature_names, dt.tree_.feature[:n_nodes]))}")

# ========== 7. 不同参数的影响 ==========
print("\n" + "=" * 60)
print("🔍 参数影响对比")
print("=" * 60)

depths = [1, 2, 3, 5, 10, None]
print(f"{'深度':<10} {'训练准确率':<12} {'测试准确率':<12} {'叶节点数':<10}")
print("-" * 50)

for depth in depths:
    dt_temp = DecisionTreeClassifier(max_depth=depth, random_state=42)
    dt_temp.fit(X_train, y_train)
    train_a = accuracy_score(y_train, dt_temp.predict(X_train))
    test_a = accuracy_score(y_test, dt_temp.predict(X_test))
    n_leaves = dt_temp.tree_.n_leaves
    label = str(depth) if depth else "不限制"
    print(f"{label:<10} {train_a:<12.4f} {test_a:<12.4f} {n_leaves:<10}")

print("\n💡 观察: 深度越大，训练准确率越高，但测试准确率可能下降（过拟合）")
print("💡 最佳深度需要通过交叉验证来确定")

plt.close()
print("\n✅ 示例1完成!")
