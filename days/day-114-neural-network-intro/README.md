# Day 114 — 神经网络入门

> 🎯 今日目标：理解 PyTorch 神经网络的核心构建块，掌握 nn.Module、线性层、激活函数、损失函数和优化器，能手写一个完整的 2 层网络分类器。

---

## 1. nn.Module 与线性层

### 1.1 什么是 nn.Module？

`nn.Module` 是 PyTorch 中所有神经网络的**基类**。你自定义的任何网络都必须继承它。

```python
import torch
import torch.nn as nn

class SimpleNet(nn.Module):
    def __init__(self):
        super().__init__()          # 必须调用父类构造函数
        self.linear = nn.Linear(784, 10)  # 定义层

    def forward(self, x):           # 必须定义 forward 方法
        return self.linear(x)
```

**为什么需要继承 nn.Module？**
- 自动管理参数（`parameters()`、`state_dict()`）
- 支持 GPU 加速（`.to(device)`）
- 提供 `.train()` / `.eval()` 模式切换
- 支持模型保存与加载

### 1.2 nn.Linear — 全连接层

```python
# nn.Linear(in_features, out_features, bias=True)
linear = nn.Linear(784, 256)  # 784 → 256
```

**底层原理：**
```
输出 = 输入 × 权重转置 + 偏置
y = x @ W^T + b
```

其中：
- 权重 W 形状：`(out_features, in_features)` = `(256, 784)`
- 偏置 b 形状：`(out_features,)` = `(256,)`
- 参数由 Kaiming/Xavier 等方法**随机初始化**

### 1.3 参数查看

```python
net = SimpleNet()

# 查看所有参数
for name, param in net.named_parameters():
    print(f"{name}: {param.shape}")
# linear.weight: torch.Size([10, 784])
# linear.bias: torch.Size([10])
```

---

## 2. 激活函数

### 2.1 为什么需要激活函数？

如果没有激活函数，多层线性层的组合**等价于单层线性层**：

```
y = W2(W1·x + b1) + b2 = W'·x + b'
```

激活函数引入**非线性**，让网络能够学习复杂的模式。

### 2.2 三种常用激活函数对比

| 函数 | 公式 | 输出范围 | 特点 | 适用场景 |
|------|------|----------|------|----------|
| ReLU | max(0, x) | [0, +∞) | 计算快，缓解梯度消失 | **隐藏层首选** |
| Sigmoid | 1/(1+e^-x) | (0, 1) | 易饱和，梯度消失 | 二分类输出层 |
| Tanh | (e^x - e^-x)/(e^x + e^-x) | (-1, 1) | 零中心，仍有饱和问题 | RNN、GAN |

### 2.3 ReLU 详解（最常用）

```python
relu = nn.ReLU()
x = torch.tensor([-2.0, -1.0, 0.0, 1.0, 2.0])
print(relu(x))  # tensor([0., 0., 0., 1., 2.])
```

**ReLU 的设计原理：**
- 正区间梯度恒为 1 → 梯度不会消失
- 计算只需一次比较 → 极快
- 稀疏激活（负值归零）→ 类似生物神经元

**ReLU 的坑：**
- **Dying ReLU**：如果学习率太大，某个神经元可能永远输出 0
- 解决方案：使用 Leaky ReLU 或调整学习率

```python
# Leaky ReLU：负值给一个小斜率
leaky_relu = nn.LeakyReLU(negative_slope=0.01)
```

### 2.4 激活函数选择经验法则

```
隐藏层 → ReLU（默认）
输出层 → 根据任务选择：
  - 二分类 → Sigmoid
  - 多分类 → Softmax（通常内含在 CrossEntropyLoss 中）
  - 回归 → 无激活 / Linear
```

---

## 3. 损失函数

### 3.1 损失函数的作用

损失函数衡量**预测值与真实值的差距**，梯度通过损失函数反向传播，指导参数更新。

### 3.2 常用损失函数

#### MSELoss — 均方误差（回归任务）

```python
criterion = nn.MSELoss()
pred = torch.tensor([1.0, 2.0, 3.0])
target = torch.tensor([1.1, 1.9, 3.2])
loss = criterion(pred, target)  # tensor(0.02)
```

**公式：** `L = (1/n) Σ(pred - target)²`

#### CrossEntropyLoss — 交叉熵（分类任务）

```python
criterion = nn.CrossEntropyLoss()
# 注意：输入是未经过 Softmax 的 logits！
logits = torch.tensor([[2.0, 1.0, 0.1],   # 样本 1
                        [0.5, 2.0, 0.3]])   # 样本 2
labels = torch.tensor([0, 1])               # 样本 1 属于类 0，样本 2 属于类 1
loss = criterion(logits, labels)
```

**为什么不需要手动做 Softmax？**
- PyTorch 的 CrossEntropyLoss 内部已经包含了 Softmax
- 数值上更稳定（log-sum-exp 技巧避免溢出）
- 梯度计算更简洁

**CrossEntropyLoss 的底层原理：**
```
L = -Σ y_i · log(p_i)
```
其中 y 是 one-hot 标签，p 是预测概率。本质是衡量两个概率分布的差异。

---

## 4. 优化器

### 4.1 SGD — 随机梯度下降

```python
optimizer = torch.optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
```

**原理：**
```
v_t = momentum * v_{t-1} + lr * gradient
param = param - v_t
```
- **momentum（动量）**：累积历史梯度方向，加速收敛，减少震荡
- 直觉：像一个球从山上滚下来，动量让它冲过小坑

### 4.2 Adam — 自适应学习率优化器

```python
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
```

**为什么 Adam 更好用？**
- 为每个参数维护独立的学习率
- 结合了 Momentum（一阶矩）和 RMSProp（二阶矩）
- 自动调整学习率，对超参数不敏感
- **新手默认选 Adam 就对了**

### 4.3 优化器对比

| 特性 | SGD + Momentum | Adam |
|------|---------------|------|
| 学习率 | 需要手动调 | 自适应调整 |
| 收敛速度 | 较慢但稳定 | 快 |
| 泛化性能 | 通常更好 | 有时略差 |
| 适用场景 | 大数据集精细调优 | **通用首选** |

---

## 5. 完整训练流程图解

```
┌─────────────────────────────────────────────────────────────┐
│                    前向传播 (Forward)                         │
│                                                             │
│  输入 x ──→ [Linear] ──→ [ReLU] ──→ [Linear] ──→ 预测 y   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    计算损失 loss = criterion(y_pred, y_true)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    反向传播 (Backward)                        │
│                                                             │
│  loss.backward()  ← 自动计算所有参数的梯度                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    optimizer.step()  ← 根据梯度更新参数
                              │
                              ▼
                    optimizer.zero_grad()  ← 清空梯度
```

### 关键代码模式（每次训练迭代）

```python
for epoch in range(epochs):
    for x_batch, y_batch in dataloader:
        # 1. 前向传播
        y_pred = model(x_batch)

        # 2. 计算损失
        loss = criterion(y_pred, y_batch)

        # 3. 反向传播
        loss.backward()

        # 4. 更新参数
        optimizer.step()

        # 5. 清空梯度（重要！）
        optimizer.zero_grad()
```

⚠️ **常见错误：忘记 `zero_grad()`**，导致梯度累积，训练发散！

---

## 6. 实战：手写 2 层网络分类器

### 6.1 网络架构

```
输入 (784) ──→ Linear(784, 256) ──→ ReLU ──→ Linear(256, 10) ──→ 输出 (10)
     │              │                    │              │
     │         200,704 参数           无参数         2,570 参数
     │
  28×28 图像展平为 784 维向量
```

**总参数量：** 200,704 + 2,570 = 203,274 个可训练参数

### 6.2 完整代码

```python
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np

# ========== 1. 准备数据 ==========
digits = load_digits()
X = digits.data.astype(np.float32)    # (1797, 64)
y = digits.target.astype(np.int64)    # (1797,)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 标准化
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# 转为 PyTorch 张量
X_train_t = torch.tensor(X_train)
y_train_t = torch.tensor(y_train)
X_test_t = torch.tensor(X_test)
y_test_t = torch.tensor(y_test)

# ========== 2. 定义网络 ==========
class DigitNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = nn.Linear(64, 256)   # 第一层：64 → 256
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(256, 10)   # 第二层：256 → 10

    def forward(self, x):
        x = self.layer1(x)
        x = self.relu(x)
        x = self.layer2(x)
        return x

model = DigitNet()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# ========== 3. 训练 ==========
for epoch in range(100):
    # 前向传播
    outputs = model(X_train_t)
    loss = criterion(outputs, y_train_t)

    # 反向传播
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if (epoch + 1) % 20 == 0:
        # 计算准确率
        _, predicted = torch.max(outputs, 1)
        acc = (predicted == y_train_t).float().mean()
        print(f"Epoch [{epoch+1}/100], Loss: {loss.item():.4f}, Acc: {acc:.4f}")

# ========== 4. 测试 ==========
with torch.no_grad():
    test_outputs = model(X_test_t)
    _, predicted = torch.max(test_outputs, 1)
    test_acc = (predicted == y_test_t).float().mean()
    print(f"\n测试集准确率: {test_acc:.4f}")
```

### 6.3 代码逐行解析

| 步骤 | 代码 | 说明 |
|------|------|------|
| 数据准备 | `StandardScaler()` | 标准化让训练更稳定 |
| 网络定义 | `nn.Linear` × 2 | 两层全连接 |
| 损失函数 | `CrossEntropyLoss` | 多分类标准选择 |
| 优化器 | `Adam(lr=0.001)` | 通用默认配置 |
| 训练循环 | forward → loss → backward → step → zero_grad | **五步标准流程** |
| 测试 | `torch.no_grad()` | 关闭梯度计算，节省内存 |

---

## 7. API 速查表

### nn.Module 核心方法

| 方法 | 说明 |
|------|------|
| `model.parameters()` | 返回所有可训练参数的迭代器 |
| `model.named_parameters()` | 返回 (名字, 参数) 对 |
| `model.state_dict()` | 返回参数字典（用于保存） |
| `model.load_state_dict()` | 从字典加载参数 |
| `model.train()` | 设为训练模式（影响 Dropout/BN） |
| `model.eval()` | 设为评估模式 |
| `model.to(device)` | 移动到 GPU/CPU |

### 损失函数速查

| 损失函数 | 任务 | 输入 | 目标 |
|----------|------|------|------|
| `MSELoss` | 回归 | 任意实数 | 任意实数 |
| `CrossEntropyLoss` | 多分类 | logits (未 softmax) | 类别索引 |
| `BCEWithLogitsLoss` | 二分类 | logits (未 sigmoid) | 0 或 1 |
| `NLLLoss` | 多分类 | log softmax 后 | 类别索引 |

### 优化器速查

| 优化器 | 推荐学习率 | 特点 |
|--------|-----------|------|
| `SGD` | 0.01~0.1 | 需调参，泛化好 |
| `Adam` | 0.001 | 自适应，新手友好 |
| `AdamW` | 0.001 | Adam + 正确的权重衰减 |

---

## 8. 思考题

1. **为什么不把 ReLU 放在输出层？** 输出层的激活函数由任务决定，ReLU 会截断负值，对于分类/回归都不合适。

2. **如果把 2 层网络的所有 ReLU 去掉，会发生什么？** 两个线性层合并为一个，网络退化为线性模型，表达能力大幅下降。

3. **CrossEntropyLoss 和 NLLLoss 有什么区别？** CrossEntropyLoss = LogSoftmax + NLLLoss，前者更方便，后者需要手动做 log softmax。

4. **为什么 Adam 的默认学习率是 0.001，而 SGD 是 0.01？** Adam 有自适应机制，会自动缩放学习率，所以可以用更小的初始值；SGD 需要更大的学习率来保证收敛速度。

5. **训练时 loss 不下降可能是什么原因？** 学习率太大/太小、梯度未正确传播、数据未标准化、标签错误、网络结构问题等。

---

## 9. 关键总结

| 概念 | 核心要点 |
|------|---------|
| nn.Module | 所有网络的基类，必须继承 |
| nn.Linear | 全连接层，底层是矩阵乘法 |
| 激活函数 | 引入非线性，隐藏层用 ReLU |
| 损失函数 | 分类用 CrossEntropy，回归用 MSELoss |
| 优化器 | 新手用 Adam，调参用 SGD+Momentum |
| 训练循环 | forward → loss → backward → step → zero_grad |
