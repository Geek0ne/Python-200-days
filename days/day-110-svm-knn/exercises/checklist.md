# Day 110 — SVM 与 KNN 练习清单

## ✅ 完成清单

- [ ] 理解 SVM 的最大间隔原理
- [ ] 理解核技巧的作用和常用核函数
- [ ] 掌握 SVM 的关键参数（C, gamma, kernel）
- [ ] 理解 KNN 的基本原理
- [ ] 掌握 K 值选择方法（交叉验证）
- [ ] 理解数据标准化对 KNN 的重要性
- [ ] 能够对比 SVM 和 KNN 的适用场景
- [ ] 完成手写数字识别实战
- [ ] 运行所有代码示例

---

## 📝 基础练习题

### 练习 1：SVM 参数调优

使用 sklearn 的乳腺癌数据集，尝试不同的 SVM 参数组合：

```python
from sklearn.datasets import load_breast_cancer
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# 加载数据
data = load_breast_cancer()
X, y = data.data, data.target

# 你的代码：
# 1. 划分训练/测试集
# 2. 标准化
# 3. 尝试 kernel='linear', 'rbf', 'poly'
# 4. 对每种核函数调参 C
# 5. 打印每种组合的准确率
```

**要求：** 找出最优的 kernel + C 组合

---

### 练习 2：KNN K 值分析

对鸢尾花数据集，绘制 K 值从 1 到 30 的准确率变化曲线：

```python
from sklearn.datasets import load_iris
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score
import matplotlib.pyplot as plt

# 你的代码：
# 1. 加载数据
# 2. 对 K=1 到 30，用 5 折交叉验证计算准确率
# 3. 绘制 K 值 vs 准确率 曲线
# 4. 标出最优 K 值
# 5. 分析曲线趋势
```

**思考：** 为什么 K 太小或太大都不好？

---

### 练习 3：距离度量实验

比较不同距离度量在 KNN 中的效果：

```python
from sklearn.datasets import load_wine
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score

# 你的代码：
# 1. 加载红酒数据集
# 2. 标准化
# 3. 分别用 euclidean, manhattan, chebyshev 距离
# 4. 打印每种距离的交叉验证准确率
# 5. 分析哪种距离最适合这个数据集
```

---

## 🚀 进阶挑战题

### 挑战 1：SVM 决策边界可视化

在 2D 数据上可视化 SVM 的决策边界和支持向量：

```python
# 你的代码：
# 1. 生成 2D 月亮数据（make_moons）
# 2. 用 SVM 训练
# 3. 创建网格点
# 4. 绘制决策边界（contourf）
# 5. 标记支持向量（用特殊标记）
# 6. 对比不同 C 值的边界变化
```

---

### 挑战 2：KNN 加速实验

KNN 在大数据集上很慢，尝试以下加速方法：

```python
# 你的代码：
# 1. 生成一个大数据集（10万样本，20特征）
# 2. 用 brute force KNN 训练和预测，记录时间
# 3. 用 ball_tree KNN，记录时间
# 4. 用 kd_tree KNN，记录时间
# 5. 对比三种算法的速度和准确率
# 6. 分析哪种算法最适合你的数据
```

**提示：** `algorithm` 参数可以设为 'ball_tree', 'kd_tree', 'brute', 'auto'

---

### 挑战 3：SVM vs KNN 综合对比

在多个数据集上对比 SVM 和 KNN：

```python
from sklearn.datasets import make_classification, make_circles, make_moons
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score

# 你的代码：
# 1. 生成 4 种不同特性的数据集：
#    - 线性可分
#    - 月亮形（非线性）
#    - 圆形（非线性）
#    - 高维稀疏
# 2. 对每个数据集，用 SVM 和 KNN 分别训练
# 3. 用交叉验证评估
# 4. 汇总成表格
# 5. 分析各算法的优势场景
```

**输出示例：**
```
数据集         | SVM 准确率 | KNN 准确率 | 更优算法
线性可分       | 0.95       | 0.93       | SVM
月亮形         | 0.97       | 0.98       | KNN
圆形           | 0.94       | 0.96       | KNN
高维稀疏       | 0.88       | 0.72       | SVM
```

---

### 挑战 4：KNN 回归实战

用 KNN 做回归任务：

```python
from sklearn.neighbors import KNeighborsRegressor
from sklearn.datasets import make_regression
from sklearn.metrics import mean_squared_error, r2_score

# 你的代码：
# 1. 生成回归数据
# 2. 尝试不同的 K 值
# 3. 尝试 weights='uniform' vs 'distance'
# 4. 绘制预测值 vs 真实值散点图
# 5. 计算 RMSE 和 R² 评分
```

---

## 📚 知识检查

1. SVM 中，参数 C 越大意味着什么？
2. 为什么 KNN 必须做数据标准化？
3. RBF 核的 gamma 参数控制什么？
4. KNN 的 weights='distance' 是什么意思？
5. 在什么场景下 SVM 比 KNN 更好？
