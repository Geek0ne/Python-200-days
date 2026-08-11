# Day 108 — 逻辑回归与分类 · 练习清单

## ✅ 今日完成清单

- [ ] 理解 Sigmoid 函数的数学原理和作用
- [ ] 掌握 LogisticRegression 的基本使用流程
- [ ] 理解混淆矩阵四个指标的含义
- [ ] 掌握 ROC 曲线和 AUC 的解读
- [ ] 理解 OvR 和 Softmax 两种多分类策略
- [ ] 理解特征标准化对逻辑回归的重要性
- [ ] 掌握正则化参数 C 的调优方法
- [ ] 完成所有练习题

---

## 📝 基础练习题

### 练习 1：手写 Sigmoid 计算

不使用 sklearn，用纯 Python 实现 Sigmoid 函数，并计算以下输入的输出：

```python
# 请实现
def sigmoid(z):
    """实现 Sigmoid 函数"""
    pass

# 测试用例
assert abs(sigmoid(0) - 0.5) < 1e-6
assert abs(sigmoid(100) - 1.0) < 1e-6
assert abs(sigmoid(-100) - 0.0) < 1e-6
```

**思考**：为什么 sigmoid(100) 不完全等于 1.0？（浮点数精度问题）

---

### 练习 2：手动计算混淆矩阵指标

给定以下数据：
- TP = 80, TN = 850, FP = 30, FN = 40

请手动计算：
1. Accuracy（准确率）
2. Precision（精确率）
3. Recall（召回率）
4. F1-Score

**验证**：用 sklearn 的 confusion_matrix 和 classification_report 检查你的结果。

---

### 练习 3：逻辑回归二分类

使用 sklearn 的 `load_wine()` 数据集，完成以下任务：

```python
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# 1. 加载数据
# 2. 只保留前两个类别（二分类）
# 3. 标准化特征
# 4. 划分训练集/测试集
# 5. 训练 LogisticRegression
# 6. 输出准确率和分类报告
```

**要求**：
- 必须做特征标准化
- 设置 max_iter=1000
- 输出完整的分类报告

---

## 🔥 进阶挑战题

### 练习 4：阈值调优

在练习 3 的基础上：

1. 用 `predict_proba` 获取概率预测
2. 尝试不同的分类阈值（0.3, 0.4, 0.5, 0.6, 0.7）
3. 计算每个阈值下的 Precision、Recall、F1
4. 绘制阈值 vs 指标的折线图
5. 找出 F1 最高的阈值

**思考**：为什么默认的 0.5 不一定是最优阈值？

---

### 练习 5：不平衡数据处理

生成一个类别严重不平衡的数据集：

```python
from sklearn.datasets import make_classification

X, y = make_classification(
    n_samples=5000,
    n_features=15,
    weights=[0.98, 0.02],  # 98% vs 2%
    random_state=42
)
```

分别用以下方式训练逻辑回归，对比性能：
1. 不处理不平衡（默认参数）
2. `class_weight='balanced'`
3. `class_weight={0: 1, 1: 50}`（手动权重）

**评估指标**：
- Accuracy
- Precision（正类）
- Recall（正类）
- F1（正类）
- AUC

**思考**：为什么 Accuracy 在不平衡数据上会误导？哪个指标最能反映模型对少数类的识别能力？

---

### 练习 6：特征选择对逻辑回归的影响

使用乳腺癌数据集：

1. 训练完整特征的逻辑回归，记录 AUC
2. 只用 `coef_` 绝对值最大的 5 个特征，再训练一次
3. 只用 `coef_` 绝对值最小的 5 个特征，再训练一次
4. 对比三次的 AUC

**思考**：逻辑回归的 coef_ 可以用来做特征选择吗？有什么局限性？

---

## 📊 自评表

| 知识点 | 掌握程度 | 备注 |
|--------|----------|------|
| Sigmoid 函数原理 | ⬜ 掌握 / ⬜ 需复习 | |
| LogisticRegression 使用 | ⬜ 掌握 / ⬜ 需复习 | |
| 混淆矩阵指标 | ⬜ 掌握 / ⬜ 需复习 | |
| ROC/AUC | ⬜ 掌握 / ⬜ 需复习 | |
| 多分类策略 | ⬜ 掌握 / ⬜ 需复习 | |
| 特征标准化 | ⬜ 掌握 / ⬜ 需复习 | |
| 正则化调优 | ⬜ 掌握 / ⬜ 需复习 | |
| 不平衡数据处理 | ⬜ 掌握 / ⬜ 需复习 | |
