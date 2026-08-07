# Day 101 — NumPy 核心：练习检查表

## ✅ 今日学习完成清单

- [ ] 理解 ndarray 的内存布局和为什么比 Python 列表快
- [ ] 掌握 ndarray 的核心属性：shape, dtype, ndim, size, strides
- [ ] 熟练使用各种数组创建函数：zeros, ones, eye, arange, linspace
- [ ] 理解 shape 操作：reshape, flatten, ravel 的区别
- [ ] 掌握 axis 概念和轴方向的判断
- [ ] 理解广播机制的 3 条规则
- [ ] 掌握 ufunc 数学函数和聚合函数
- [ ] 理解向量化计算的优势
- [ ] 能用 NumPy 进行线性代数运算
- [ ] 完成所有代码示例的运行和理解

---

## 练习题

### 基础题

**练习 1：创建与操作**

创建一个 5x5 的数组，元素为 0-24，然后：
1. 打印其 shape, dtype, ndim
2. 提取第 2 行
3. 提取所有大于 15 的元素
4. 将第 3 列的所有元素乘以 10

```python
import numpy as np
# 在这里编写代码
```

**练习 2：广播运算**

给定两个数组：
```python
a = np.array([1, 2, 3, 4, 5])  # 5 个学生的成绩
b = np.array([0.9, 1.0, 1.1])  # 3 次考试的权重
```
用广播计算加权平均分（需要正确 reshape）。期望结果：每个学生一个加权分数。

**练习 3：轴操作**

```python
data = np.random.rand(100, 5)  # 100 个样本，5 个特征
```
1. 计算每个特征的均值、标准差、最大值
2. 找出每个样本中最大的特征值及其索引
3. 对数据进行 Z-Score 标准化

---

### 进阶题

**练习 4：实现一个简化版的 K-Means 聚类**

```python
def kmeans(X, k, max_iters=100):
    """
    X: (n_samples, n_features) 数据矩阵
    k: 聚类数
    返回: (centroids, labels)
    """
    n = X.shape[0]
    # 随机初始化 k 个中心点
    indices = np.random.choice(n, k, replace=False)
    centroids = X[indices].copy()
    
    for _ in range(max_iters):
        # 1. 计算每个样本到各中心的距离（使用全向量化方法）
        # 2. 为每个样本分配最近的中心
        # 3. 重新计算各聚类的中心点
        # 4. 检查中心点是否收敛
        pass
    
    return centroids, labels

# 测试：在 3 个高斯簇上运行
from sklearn.datasets import make_blobs
X, _ = make_blobs(n_samples=300, centers=3, random_state=42)
centroids, labels = kmeans(X, 3)
```

**练习 5：图像马赛克效果**

使用 NumPy 实现一个简单的马赛克效果：
1. 把图像分成 block_size × block_size 的小块
2. 每个小块用均值填充
3. 不使用任何循环，只用切片和 reshape

```python
def mosaic(img, block_size=16):
    """实现图像马赛克效果"""
    h, w, c = img.shape
    # 提示：reshape → mean → reshape back
    pass
```

---

## 运行验证

完成后运行以下命令验证：
```bash
cd ~/code/Learn-Python
python3 days/day-101-numpy-core/code/01-numpy-basics.py
python3 days/day-101-numpy-core/code/02-broadcasting-advanced.py
python3 days/day-101-numpy-core/code/03-practical-recipes.py
```
