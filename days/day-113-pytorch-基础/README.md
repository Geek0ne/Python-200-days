# Day 113 — PyTorch 基础

## 📚 今日概览

今天我们进入深度学习框架的世界。PyTorch 是当今最流行的深度学习框架之一，以其动态计算图、Pythonic 设计和强大的 GPU 加速能力著称。我们将从 Tensor（张量）的基础操作开始，逐步学习 Autograd 自动求导机制，并最终用它们手动实现一个线性回归模型。

---

## 🔑 核心概念

### 1. PyTorch 概述

PyTorch 是由 Meta AI（原 Facebook AI Research）于 2016 年发布的开源深度学习框架。它的核心特点包括：

- **动态计算图（Dynamic Computational Graph）**：与 TensorFlow 1.x 的静态图不同，PyTorch 在运行时动态构建计算图，使得调试和修改网络结构更加灵活。
- **Pythonic 设计**：PyTorch 的 API 设计遵循 Python 习惯，使用起来自然直观。
- **原生 GPU 支持**：一行代码即可将计算迁移到 GPU，极大提升运算速度。
- **自动微分（Autograd）**：自动计算梯度，简化反向传播的实现。
- **丰富的生态系统**：包括 TorchVision（计算机视觉）、TorchText（自然语言处理）、TorchAudio（音频处理）等。

PyTorch 的核心数据结构是 **Tensor**，它本质上是一个多维数组，类似于 NumPy 的 ndarray，但拥有以下额外能力：

- 可以在 GPU 上运行
- 支持自动求导
- 与神经网络构建深度集成

### 2. Tensor（张量）概念

Tensor 是 PyTorch 中的基本数据单元。你可以把 Tensor 理解为：

| 维度 | 名称 | 例子 |
|------|------|------|
| 0 维 | 标量（Scalar） | `torch.tensor(5)` |
| 1 维 | 向量（Vector） | `torch.tensor([1, 2, 3])` |
| 2 维 | 矩阵（Matrix） | `torch.tensor([[1, 2], [3, 4]])` |
| 3+ 维 | 张量（Tensor） | `torch.rand(2, 3, 4)` |

Tensor 支持的数据类型（dtype）：

| dtype | 描述 |
|-------|------|
| `torch.float32` | 32位浮点数（默认） |
| `torch.float64` | 64位浮点数（双精度） |
| `torch.float16` | 16位浮点数（半精度，常用于GPU加速） |
| `torch.int32` | 32位整数 |
| `torch.int64` | 64位整数 |
| `torch.bool` | 布尔类型 |
| `torch.complex64` | 64位复数 |

### 3. Autograd 自动求导原理

Autograd 是 PyTorch 的自动微分引擎。它的工作原理基于 **反向传播（Backpropagation）** 算法：

1. **前向传播（Forward Pass）**：数据通过计算图，计算出输出结果
2. **构建计算图**：在前向传播过程中，PyTorch 自动记录所有操作，构建一个有向无环图（DAG）
3. **反向传播（Backward Pass）**：调用 `.backward()` 方法，从输出开始，沿计算图反向传播，计算每个叶子节点的梯度

关键属性：

- `requires_grad=True`：标记该 Tensor 需要计算梯度
- `.grad`：存储计算出的梯度值
- `.grad_fn`：记录创建该 Tensor 的操作（计算节点）
- `torch.no_grad()`：上下文管理器，用于临时禁用梯度计算（提高性能）

### 4. GPU 加速

现代深度学习严重依赖 GPU 加速。PyTorch 中 GPU 切换非常简单：

```python
# 检查是否有可用的 GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 将 Tensor 移动到 GPU
x = x.to(device)

# 创建 Tensor 时直接指定设备
x = torch.rand(3, 3, device=device)
```

GPU 加速的核心原因：
- GPU 拥有数千个核心，适合并行计算
- Tensor 运算（矩阵乘法、卷积等）天然是高度并行的
- 数据传输到 GPU 后，所有计算都在 GPU 上完成，避免反复传输

---

## 🧠 原理解释

### Tensor 计算图

计算图是 PyTorch 实现自动微分的核心数据结构。当一个操作涉及 `requires_grad=True` 的 Tensor 时，PyTorch 就会记录这个操作，构建计算图。

```
x (叶子节点, requires_grad=True)
|
| weight * x
v
y (中间节点, grad_fn=MulBackward)
|
| y + bias
v
loss (输出节点, grad_fn=AddBackward)
```

每个节点记录了：
- **操作类型**（加法、乘法、矩阵乘法等）
- **输入 Tensor**
- **梯度函数**（grad_fn）—— 用于计算梯度的函数

### 反向传播机制

反向传播基于链式法则（Chain Rule）：

$$
\frac{\partial L}{\partial x} = \frac{\partial L}{\partial y} \cdot \frac{\partial y}{\partial x}
$$

在 PyTorch 中：

1. 调用 `loss.backward()` 时，从 `loss` 节点开始
2. 每个节点调用其 `grad_fn` 计算相对于输入的梯度
3. 梯度沿着计算图传播到所有叶子节点
4. 结果存储在 `.grad` 属性中

### 梯度下降原理

梯度下降是优化算法的基础。其核心公式为：

$$
\theta_{new} = \theta_{old} - \eta \cdot \nabla L(\theta)
$$

其中：
- $\theta$ 是模型参数
- $\eta$ 是学习率（learning rate）
- $\nabla L(\theta)$ 是损失函数关于参数的梯度

PyTorch 中的手动梯度下降流程：

```python
# 1. 前向传播
y_pred = model(x)
loss = loss_fn(y_pred, y)

# 2. 反向传播（计算梯度）
optimizer.zero_grad()   # 清空之前的梯度
loss.backward()         # 计算梯度

# 3. 更新参数
optimizer.step()        # 根据梯度更新参数
```

---

## 📖 API 速查

### torch.Tensor 创建

| 方法 | 说明 | 示例 |
|------|------|------|
| `torch.tensor(data)` | 从数据创建 | `torch.tensor([1,2,3])` |
| `torch.zeros(rows, cols)` | 全零矩阵 | `torch.zeros(2,3)` |
| `torch.ones(rows, cols)` | 全一矩阵 | `torch.ones(2,3)` |
| `torch.randn(rows, cols)` | 标准正态分布 | `torch.randn(2,3)` |
| `torch.rand(rows, cols)` | [0,1) 均匀分布 | `torch.rand(2,3)` |
| `torch.arange(start, end)` | 等差数列 | `torch.arange(0,10,2)` |
| `torch.linspace(start, end, steps)` | 线性等距 | `torch.linspace(0,1,5)` |
| `torch.eye(n)` | 单位矩阵 | `torch.eye(3)` |

### Tensor 常用属性

| 属性 | 说明 |
|------|------|
| `.shape` / `.size()` | 形状 |
| `.dtype` | 数据类型 |
| `.device` | 所在设备（CPU/GPU） |
| `.ndim` | 维度数 |
| `.numel()` | 元素总数 |
| `.requires_grad` | 是否需要梯度 |

### Tensor 运算

| 运算 | 方法 | 说明 |
|------|------|------|
| 加法 | `a + b` 或 `torch.add(a, b)` | 逐元素加法 |
| 减法 | `a - b` 或 `torch.sub(a, b)` | 逐元素减法 |
| 乘法 | `a * b` 或 `torch.mul(a, b)` | 逐元素乘法 |
| 矩阵乘法 | `a @ b` 或 `torch.mm(a, b)` 或 `torch.matmul(a, b)` | 矩阵乘法 |
| 转置 | `a.t()` 或 `a.transpose(0,1)` | 转置 |
| 索引 | `a[i, j]` | 索引操作 |
| 切片 | `a[1:3, :]` | 切片操作 |
| 变形 | `a.reshape(m, n)` | 改变形状 |
| 拼接 | `torch.cat([a, b], dim=0)` | 拼接 |
| 求和 | `a.sum()` | 所有元素求和 |
| 均值 | `a.mean()` | 所有元素均值 |

### torch.autograd

| API | 说明 |
|-----|------|
| `Tensor.backward(gradient)` | 反向传播计算梯度 |
| `Tensor.grad` | 获取梯度值 |
| `Tensor.detach()` | 从计算图中分离 |
| `Tensor.requires_grad_(True/False)` | 原地设置梯度需求 |
| `torch.no_grad()` | 禁用梯度计算的上下文管理器 |
| `torch.enable_grad()` | 启用梯度计算的上下文管理器 |

### torch.optim

| 优化器 | 说明 |
|--------|------|
| `torch.optim.SGD` | 随机梯度下降 |
| `torch.optim.Adam` | Adam 优化器（自适应学习率） |
| `torch.optim.RMSprop` | RMSprop 优化器 |
| `torch.optim.Adagrad` | Adagrad 优化器 |
| `torch.optim.AdamW` | AdamW 优化器（权重衰减） |

---

## 🎯 实战代码案例：用 Autograd 实现线性回归

### 问题描述

我们用 PyTorch 从零开始实现线性回归，不使用任何高级 API（如 `nn.Linear` 或 `MSELoss`），完全基于 Autograd 手动计算。

### 完整代码

```python
import torch

# ====== 1. 生成模拟数据 ======
torch.manual_seed(42)
x = 2 * torch.rand(100, 1)          # 100 个样本，特征维度 1
y = 3.0 * x + 1.0 + 0.1 * torch.randn(100, 1)  # y = 3x + 1 + 噪声

# ====== 2. 初始化模型参数 ======
w = torch.randn(1, requires_grad=True)  # 权重
b = torch.zeros(1, requires_grad=True)  # 偏置

# ====== 3. 定义超参数 ======
learning_rate = 0.1
num_epochs = 100

# ====== 4. 训练循环 ======
for epoch in range(num_epochs):
    # --- 前向传播 ---
    y_pred = x * w + b                    # 预测值
    loss = ((y_pred - y) ** 2).mean()     # 均方误差

    # --- 反向传播 ---
    loss.backward()                        # 计算梯度

    # --- 更新参数（不用优化器，手动更新） ---
    with torch.no_grad():                  # 更新参数时不需要梯度
        w -= learning_rate * w.grad        # w = w - lr * dL/dw
        b -= learning_rate * b.grad        # b = b - lr * dL/db

    # --- 清空梯度 ---
    w.grad.zero_()                         # 重要！梯度会累积，必须清零
    b.grad.zero_()

    if (epoch + 1) % 20 == 0:
        print(f"Epoch [{epoch+1:3d}/100] | Loss: {loss.item():.6f} | w: {w.item():.4f} | b: {b.item():.4f}")

print(f"\n最终结果: y = {w.item():.4f}x + {b.item():.4f}")
print(f"真实关系: y = 3.0000x + 1.0000")
```

### 预期输出

```
Epoch [ 20/100] | Loss: 0.039125 | w: 2.8923 | b: 1.0512
Epoch [ 40/100] | Loss: 0.011580 | w: 2.9674 | b: 1.0150
Epoch [ 60/100] | Loss: 0.010205 | w: 2.9828 | b: 1.0098
Epoch [ 80/100] | Loss: 0.010030 | w: 2.9894 | b: 1.0067
Epoch [100/100] | Loss: 0.009996 | w: 2.9923 | b: 1.0051

最终结果: y = 2.9923x + 1.0051
真实关系: y = 3.0000x + 1.0000
```

### 代码解读

1. **数据生成**：使用 `torch.rand` 生成 100 个 [0, 1) 的随机样本，按 $y = 3x + 1 + noise$ 生成标签
2. **参数初始化**：`w` 和 `b` 都设置 `requires_grad=True`，PyTorch 会自动跟踪对它们的运算
3. **前向传播**：直接用数学运算 `x * w + b` 计算预测值
4. **计算损失**：手动实现 MSE：$L = \frac{1}{N}\sum(\hat{y} - y)^2$
5. **反向传播**：`loss.backward()` 自动计算 $\frac{\partial L}{\partial w}$ 和 $\frac{\partial L}{\partial b}$
6. **参数更新**：使用 `torch.no_grad()` 避免跟踪更新操作
7. **梯度清零**：`grad.zero_()` 必须手动调用，否则梯度会累积

---

## 💭 思考题

1. **为什么必须调用 `w.grad.zero_()`？如果不调用会发生什么？**
   - 提示：考虑梯度累积的机制

**参考答案**

PyTorch 的梯度默认是**累加**的：每次 `.backward()` 把新梯度**加到** `.grad` 上，而不是覆盖。如果不清零，上一批的旧梯度会一直堆积，参数更新用的是「历史梯度之和」而非当前梯度 → 方向错误、步长失控，训练震荡甚至发散。所以每步反向传播前要 `w.grad.zero_()`（或 `optimizer.zero_grad()`）清空。

为什么设计成累加？为了支持「梯度累积」（多个 micro-batch 累加后再更新，模拟大 batch）、RNN 等场景。但标准训练里必须每步清零。

小例子：两步梯度分别是 g1、g2，不清零时第二步用的是 g1+g2 而不是 g2 → 冲过头。

💡 提示：`optimizer.zero_grad()` 一次清所有参数；新版默认 `set_to_none=True` 更省内存。

2. **`torch.no_grad()` 的作用是什么？如果去掉会怎样？**
   - 提示：考虑内存和计算图的影响

**参考答案**

`torch.no_grad()` 是个上下文管理器，进入后**关闭梯度追踪**：里面的运算不再构建计算图，结果 `requires_grad=False`。常用于推理/评估和手动更新参数。

去掉它（在评估时）：PyTorch 仍会建图、保存中间结果 → 内存占用更大（可能近 2 倍）、速度更慢，还可能意外追踪本不需要的运算。在手动更新参数时去掉则会直接报错（见第 4 题）。

小例子：`with torch.no_grad(): y = model(x)` 得到的 y 没有 `grad_fn`；不加则保留整张图，而你其实不需要反向传播。

💡 提示：凡是不需要梯度的地方都用 `no_grad()`，省内存又加速。

3. **如果将学习率从 0.1 改为 1.0，训练会发生什么变化？尝试实验。**
   - 提示：考虑学习率过大导致的震荡和发散

**参考答案**

学习率过大会**越过最优点来回震荡，甚至发散**（损失爆炸到 inf/nan）。对这个线性回归，稳定要求 lr 小于约 `2/L`（L 是损失 Hessian 的最大特征值≈`2·mean(x²)`）；x∈[0,2] 时 lr 需小于约 0.75，所以 1.0 会发散。

下面实测对比（需 `pip install torch`）：

```python
import torch

def train(lr, num_epochs=100):
    torch.manual_seed(42)
    x = 2 * torch.rand(100, 1)
    y = 3.0 * x + 1.0 + 0.1 * torch.randn(100, 1)
    w = torch.randn(1, requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    for epoch in range(num_epochs):
        loss = ((x * w + b - y) ** 2).mean()
        loss.backward()
        with torch.no_grad():
            w -= lr * w.grad
            b -= lr * b.grad
        w.grad.zero_(); b.grad.zero_()
        if (epoch + 1) % 20 == 0:
            print(f"lr={lr} Epoch {epoch+1:3d} | loss={loss.item():.3e}")

train(0.1)
train(1.0)
```

预期输出（数值因机器/版本而异）：

```
lr=0.1 Epoch  20 | loss=1.790e-01
lr=0.1 Epoch  40 | loss=5.663e-02
lr=0.1 Epoch  60 | loss=2.114e-02
lr=0.1 Epoch  80 | loss=1.084e-02
lr=0.1 Epoch 100 | loss=7.852e-03
lr=1.0 Epoch  20 | loss=1.869e+22
lr=1.0 Epoch  40 | loss=inf
lr=1.0 Epoch  60 | loss=inf
lr=1.0 Epoch  80 | loss=nan
lr=1.0 Epoch 100 | loss=nan
```

lr=0.1 损失稳步降到 7.85e-3；lr=1.0 第 20 轮就爆到 1.87e22，随后 inf、nan——彻底发散。

💡 提示：用更小学习率、学习率调度、梯度裁剪，或自适应优化器（Adam）来避免发散。

4. **为什么在手动更新参数时需要 `torch.no_grad()`？**
   - 提示：参数更新本身不应该被记录到计算图中

**参考答案**

`w`、`b` 是 `requires_grad=True` 的**叶子张量**。更新 `w -= lr * w.grad` 是对它们的原地操作；若不放在 `no_grad()` 里，autograd 会试图追踪这次原地更新，直接抛出「a leaf Variable that requires grad is being used in an in-place operation」错误。而且从语义上，参数更新**不是损失的可微步骤**，本就不该进计算图。

`no_grad()` 告诉 autograd 跳过追踪，于是更新只改变数值、不建图，既避免报错，也防止图无限增长、内存膨胀和下一轮梯度算错。

小例子：不加 `no_grad` 时 `w -= lr*w.grad` 报 RuntimeError；加了就正常。

💡 提示：优化器内部也是在 `no_grad` 下做更新的，所以 `optimizer.step()` 不用你手动包裹。

5. **尝试将上述代码修改为批量梯度下降（每次使用全部数据）和小批量梯度下降（batch_size=32），比较训练效果。**
   - 提示：考虑随机性和收敛速度的差异

**参考答案**

- **全批量（batch_size=N）**：每次用全部数据算梯度，估计准、噪声小、收敛平滑；但每步开销大、每个 epoch 更新次数少，容易停在尖锐极小值。
- **小批量（batch_size=32）**：梯度是带噪估计，每 epoch 更新多次、更快，噪声有助于跳出尖锐极小/鞍点，泛化常更好；代价是轻微震荡。

下面实测（需 `pip install torch`）：

```python
import torch

torch.manual_seed(42)
x = 2 * torch.rand(100, 1)
y = 3.0 * x + 1.0 + 0.1 * torch.randn(100, 1)

def train(batch_size, lr=0.1, num_epochs=100):
    torch.manual_seed(0)
    w = torch.randn(1, requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    n = len(x)
    for epoch in range(num_epochs):
        perm = torch.randperm(n)            # 每个 epoch 打乱样本
        for start in range(0, n, batch_size):
            idx = perm[start:start + batch_size]
            xb, yb = x[idx], y[idx]
            loss = ((xb * w + b - yb) ** 2).mean()
            loss.backward()
            with torch.no_grad():
                w -= lr * w.grad
                b -= lr * b.grad
            w.grad.zero_(); b.grad.zero_()
    return w.item(), b.item()

w_full, b_full = train(batch_size=100)   # 批量梯度下降：每次用全部数据
w_mini, b_mini = train(batch_size=32)    # 小批量梯度下降
print(f"全批量:   y = {w_full:.4f}x + {b_full:.4f}")
print(f"小批量32: y = {w_mini:.4f}x + {b_mini:.4f}")
print("真实关系: y = 3.0000x + 1.0000")
```

预期输出（数值因机器/版本而异）：

```
全批量:   y = 2.9734x + 1.0273
小批量32: y = 2.9759x + 1.0271
真实关系: y = 3.0000x + 1.0000
```

两者都收敛到接近真实的 3x+1；小批量因每 epoch 更新更多次，这里略快一点点，差异不大。

💡 提示：小批量是实践默认（兼顾速度、稳定与泛化），batch_size 常取 32~256。

---

## 📚 延伸阅读

- [PyTorch 官方文档](https://pytorch.org/docs/stable/)
- [PyTorch 60 分钟入门](https://pytorch.org/tutorials/beginner/deep_learning_60min_blitz.html)
- [Autograd 机制详解](https://pytorch.org/docs/stable/autograd.html)
- [PyTorch 中文文档](https://pytorch.apachecn.org/)

---

> 💡 **明日预告**：Day 114 将学习 PyTorch 神经网络构建（nn.Module、损失函数、优化器）
