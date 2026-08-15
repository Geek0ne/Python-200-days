# Day 113 图解 - PyTorch 基础

## 1. PyTorch 计算图

计算图是 PyTorch 实现自动微分的核心数据结构。当操作涉及 `requires_grad=True` 的 Tensor 时，PyTorch 自动构建此图。

```mermaid
graph LR
    A["x<br/>(requires_grad=True)<br/>值: 2.0"] -->|"+ 3"| B["y<br/>(grad_fn=AddBackward)<br/>值: 5.0"]
    B -->|"* 2"| C["z<br/>(grad_fn=MulBackward)<br/>值: 10.0"]
    C -->|"^ 2"| D["w<br/>(grad_fn=PowBackward)<br/>值: 100.0"]
    
    style A fill:#e1f5fe
    style B fill:#fff3e0
    style C fill:#fff3e0
    style D fill:#e8f5e9
```

**说明**：
- 绿色节点 = 叶子节点（输入 Tensor）
- 橙色节点 = 中间节点（由操作生成）
- 箭头 = 数据流向和梯度传播方向

---

## 2. 反向传播过程

反向传播从损失函数开始，沿计算图反向传播梯度。

```mermaid
graph TD
    A["Loss = 100.0"] -->|"∂Loss/∂z = 2z = 20.0"| B["z = 10.0"]
    B -->|"∂z/∂y = 2"| C["y = 5.0"]
    C -->|"∂y/∂x = 1"| D["x = 2.0"]
    
    A -.->|"backward()"| E["∂Loss/∂w<br/>= 20.0"]
    B -.->|"grad_fn 计算"| F["∂Loss/∂z"]
    C -.->|"grad_fn 计算"| G["∂Loss/∂y"]
    D -.->|"grad_fn 计算"| H["∂Loss/∂x"]
    
    style A fill:#ffcdd2
    style D fill:#c8e6c9
    style E fill:#ffcdd2
    style H fill:#c8e6c9
```

**反向传播公式**：
$$
\frac{\partial L}{\partial x} = \frac{\partial L}{\partial z} \cdot \frac{\partial z}{\partial y} \cdot \frac{\partial y}{\partial x}
$$

---

## 3. Autograd 自动求导流程

```mermaid
flowchart TD
    A["创建 Tensor<br/>requires_grad=True"] --> B["执行前向运算<br/>(构建计算图)"]
    B --> C["计算损失<br/>(Loss)"]
    C --> D["调用 loss.backward()<br/>(反向传播)"]
    D --> E["访问 .grad 属性<br/>(获取梯度)"]
    E --> F["更新参数<br/>(torch.no_grad)"]
    F --> G["清零梯度<br/>(grad.zero_())"]
    G --> B
    
    style A fill:#e1f5fe
    style C fill:#ffcdd2
    style D fill:#fff3e0
    style E fill:#e8f5e9
    style G fill:#f3e5f5
```

---

## 4. 梯度下降流程

```mermaid
flowchart LR
    A["初始化参数<br/>w, b"] --> B["前向传播<br/>y = wx + b"]
    B --> C["计算损失<br/>MSE = mean((y-y_true)²)"]
    C --> D["反向传播<br/>loss.backward()"]
    D --> E["获取梯度<br/>w.grad, b.grad"]
    E --> F["更新参数<br/>w = w - lr * w.grad"]
    F --> G["清零梯度<br/>grad.zero_()"]
    G --> B
    
    style A fill:#e1f5fe
    style C fill:#ffcdd2
    style D fill:#fff3e0
    style F fill:#e8f5e9
```

---

## 5. Tensor 设备迁移

```mermaid
flowchart TD
    A["创建 Tensor<br/>(默认 CPU)"] --> B{"有 GPU 可用?"}
    B -->|"是"| C["x.to('cuda')<br/>或<br/>x.cuda()"]
    B -->|"否"| D["留在 CPU<br/>x.to('cpu')"]
    C --> E["GPU 上计算<br/>(数千核心并行)"]
    D --> F["CPU 上计算<br/>(多核并行)"]
    E --> G["结果<br/>(仍在 GPU)"]
    F --> H["结果<br/>(仍在 CPU)"]
    
    style C fill:#e8f5e9
    style E fill:#e8f5e9
    style D fill:#fff3e0
    style F fill:#fff3e0
```

---

## 6. 线性回归模型结构

```mermaid
graph LR
    X["输入 x<br/>(特征)"] -->|"× w<br/>(权重)"| Y["中间结果<br/>wx"]
    B["偏置 b"] -->|"+"| Y
    Y -->|"预测值<br/>ŷ = wx + b"| YP["ŷ<br/>(预测输出)"]
    YT["y<br/>(真实值)"] --> LOSS["损失函数<br/>MSE = mean((ŷ-y)²)"]
    YP --> LOSS
    LOSS -->|"backward()"| G["梯度<br/>∂L/∂w, ∂L/∂b"]
    G -->|"更新"| W["w = w - lr·∂L/∂w"]
    G -->|"更新"| B2["b = b - lr·∂L/∂b"]
    W -.->|"下次迭代"| X
    B2 -.->|"下次迭代"| B
    
    style X fill:#e1f5fe
    style YP fill:#c8e6c9
    style LOSS fill:#ffcdd2
    style G fill:#fff3e0
```

---

## 7. 梯度累积与清零

```mermaid
sequenceDiagram
    participant Opt as 优化器
    participant Grad as 梯度 (w.grad)
    participant Model as 模型参数 (w)
    
    Note over Opt: 第1次迭代
    Opt->>Grad: loss.backward() → grad += Δ₁
    Note over Grad: w.grad = Δ₁
    Opt->>Model: w -= lr * w.grad
    
    Note over Opt: 第2次迭代 (不清零!)
    Opt->>Grad: loss.backward() → grad += Δ₂
    Note over Grad: w.grad = Δ₁ + Δ₂ ⚠️ 累积!
    Opt->>Model: w -= lr * (Δ₁ + Δ₂) ❌ 错误!
    
    Note over Opt: 第3次迭代 (正确: 先清零)
    Opt->>Grad: grad.zero_()
    Note over Grad: w.grad = 0 ✓
    Opt->>Grad: loss.backward() → grad = Δ₃
    Note over Grad: w.grad = Δ₃ ✓
    Opt->>Model: w -= lr * Δ₃ ✓ 正确!
```

---

## 8. 计算图 vs 命令式编程对比

```mermaid
graph TD
    subgraph "PyTorch (动态图/命令式)"
        A1["x = Tensor(...)"] --> B1["y = f(x)"]
        B1 --> C1["z = g(y)"]
        C1 --> D1["loss.backward()"]
        Note1["每次前向传播<br/>重新构建计算图"]
    end
    
    subgraph "TensorFlow 1.x (静态图/声明式)"
        A2["构建图: x → f → g → loss"] --> B2["session.run(loss)"]
        B2 --> C2["一次性执行整个图"]
        Note2["图只构建一次<br/>重复执行"]
    end
    
    style A1 fill:#e1f5fe
    style A2 fill:#f3e5f5
```

**PyTorch 优势**：动态图更灵活，便于调试，支持动态控制流（if/for）。
