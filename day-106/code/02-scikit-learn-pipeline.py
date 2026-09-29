"""
Day 106 - 代码示例 2：进阶用法 —— 交叉验证与多模型对比

演示：
1. 交叉验证避免单次拆分的偶然性
2. 多个模型对比
3. 超参数调优基础
"""

from sklearn.datasets import load_iris
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

# 引入多个模型
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression

import numpy as np


def compare_models(X, y):
    """对比多个模型的交叉验证表现"""
    print("=" * 60)
    print("📊 多模型交叉验证对比 (5-fold)")
    print("=" * 60)

    # 定义候选模型
    models = {
        "KNN (k=5)": KNeighborsClassifier(n_neighbors=5),
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "SVM (RBF)": SVC(kernel="rbf", random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=200, random_state=42),
    }

    results = {}
    print(f"\n{'模型':<25} {'平均准确率':>10} {'标准差':>8}")
    print("-" * 45)

    for name, model in models.items():
        # 5 折交叉验证
        scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
        mean_score = scores.mean()
        std_score = scores.std()
        results[name] = (mean_score, std_score)
        print(f"{name:<25} {mean_score:>10.4f} {std_score:>8.4f}")

    # 找出最佳模型
    best_name = max(results, key=lambda k: results[k][0])
    print(f"\n🏆 最佳模型: {best_name} (准确率: {results[best_name][0]:.4f})")

    return best_name


def pipeline_example(X_train, X_test, y_train, y_test):
    """使用 Pipeline 避免数据泄露"""
    print("\n" + "=" * 60)
    print("🔧 Pipeline 示例：预处理 + 模型 一步到位")
    print("=" * 60)

    # Pipeline 将预处理和模型串联
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", KNeighborsClassifier(n_neighbors=5)),
    ])

    # fit 时自动先缩放再训练
    pipe.fit(X_train, y_train)

    # predict 时自动先缩放再预测
    y_pred = pipe.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"  Pipeline 步骤: StandardScaler → KNeighborsClassifier")
    print(f"  测试集准确率: {accuracy:.4f}")

    # 注意：不能在 Pipeline 里用已经缩放的数据！
    print(f"\n⚠️  Pipeline 自动处理缩放，无需手动 fit_transform")


def hyperparameter_search(X, y):
    """超参数调优基础"""
    print("\n" + "=" * 60)
    print("🎯 超参数调优：GridSearchCV")
    print("=" * 60)

    from sklearn.model_selection import GridSearchCV

    # 定义参数网格
    param_grid = {
        "n_neighbors": [1, 3, 5, 7, 9, 11, 15],
        "weights": ["uniform", "distance"],
        "metric": ["euclidean", "manhattan"],
    }

    model = KNeighborsClassifier()
    grid_search = GridSearchCV(
        model, param_grid, cv=5, scoring="accuracy", n_jobs=-1, verbose=0
    )

    grid_search.fit(X, y)

    print(f"  最佳参数: {grid_search.best_params_}")
    print(f"  最佳交叉验证准确率: {grid_search.best_score_:.4f}")
    print(f"  评估了 {len(grid_search.cv_results_['params'])} 种参数组合")

    # 展示 Top 5
    results = grid_search.cv_results_
    indices = np.argsort(results["rank_test_score"])[:5]
    print(f"\n  Top 5 参数组合:")
    for i, idx in enumerate(indices):
        print(f"    {i+1}. {results['params'][idx]} → {results['mean_test_score'][idx]:.4f}")


def main():
    # 加载数据
    iris = load_iris()
    X, y = iris.data, iris.target

    # 数据拆分
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 1. 多模型对比
    compare_models(X, y)

    # 2. Pipeline 示例
    pipeline_example(X_train, X_test, y_train, y_test)

    # 3. 超参数调优
    hyperparameter_search(X, y)


if __name__ == "__main__":
    main()
