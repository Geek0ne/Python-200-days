# Day 115 — 训练流程

> 🎯 今日目标：掌握 DataLoader/Dataset 数据加载、完整的训练循环、模型保存与加载，最终完成 MNIST 手写数字识别实战。

---

## 1. DataLoader 与 Dataset

### 1.1 为什么需要 DataLoader？

Day 114 中我们直接把全部数据一次性传入模型。这在小数据集上没问题，但实际场景中：
- 数据集可能有**百万级**样本，内存装不下
- 一次性计算梯度太慢，**小批量**训练效果更好
- DataLoader 自动处理**打乱、并行加载、多进程**

### 1.2 Dataset — 数据的容器

```python
from torch.utils.data import Dataset, DataLoader

class MyDataset(Dataset):
    def __init__(self, features, labels):
        self.features = features  # numpy array 或 tensor
        self.labels = labels

    def __len__(self):
        """返回数据集大小"""
        return len(self.features)

    def __getitem__(self, idx):
        """返回第 idx 个样本"""
        return self.features[idx], self.labels[idx]

# 使用
dataset = MyDataset(X_train, y_train)
print(len(dataset))       # 数据集大小
print(dataset[0])         # 第一个样本 (feature, label)
```

**为什么继承 Dataset？**
- PyTorch 的 DataLoader 需要 Dataset 接口
- `__getitem__` 让 DataLoader 能按索引取数据
- `__len__` 让 DataLoader 知道数据集大小

### 1.3 DataLoader — 自动批处理

```python
loader = DataLoader(
    dataset,
    batch_size=32,       # 每批 32 个样本
    shuffle=True,        # 每个 epoch 打乱顺序
    num_workers=2,       # 2 个进程并行加载
    drop_last=False      # 最后一批不满 batch_size 时是否丢弃
)

# 遍历 DataLoader
for batch_features, batch_labels in loader:
    # batch_features: (32, 64) — 32 个样本，64 个特征
    # batch_labels: (32,) — 32 个标签
    pass
```

### 1.4 Batch Size 选择指南

| Batch Size | 优点 | 缺点 | 适用场景 |
|-----------|------|------|---------|
| 1（SGD） | 梯度噪声大，跳出局部最优 | 训练不稳定，速度慢 | 在线学习 |
| 32~256 | **常用范围**，收敛稳定 | — | 通用 |
| 大（1024+） | GPU 利用率高，速度快 | 泛化可能略差 | 大数据集 |

**经验值：** 从 32 开始，GPU 显存够就加大到 64、128。

### 1.5 常见内置 Dataset

```python
from torchvision import datasets, transforms

# MNIST 手写数字
mnist = datasets.MNIST(root='./data', train=True, download=True)

# CIFAR-10 图像分类
cifar = datasets.CIFAR10(root='./data', train=True, download=True)

# ImageFolder — 按文件夹组织的图像数据
# data/train/dog/xxx.jpg → 自动标注为 "dog"
folder = datasets.ImageFolder(root='./data/train')
```

---

## 2. 完整训练循环

### 2.1 标准训练模板

```python
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

def train(model, train_loader, criterion, optimizer, device):
    """训练一个 epoch"""
    model.train()  # 设为训练模式
    total_loss = 0
    correct = 0
    total = 0

    for batch_x, batch_y in train_loader:
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)

        # 1. 前向传播
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)

        # 2. 反向传播
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # 3. 统计
        total_loss += loss.item() * batch_x.size(0)
        _, predicted = outputs.max(1)
        correct += predicted.eq(batch_y).sum().item()
        total += batch_y.size(0)

    avg_loss = total_loss / total
    accuracy = correct / total
    return avg_loss, accuracy

def evaluate(model, test_loader, criterion, device):
    """评估模型"""
    model.eval()  # 设为评估模式
    total_loss = 0
    correct = 0
    total = 0

    with torch.no_grad():  # 关闭梯度计算
        for batch_x, batch_y in test_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)

            total_loss += loss.item() * batch_x.size(0)
            _, predicted = outputs.max(1)
            correct += predicted.eq(batch_y).sum().item()
            total += batch_y.size(0)

    avg_loss = total_loss / total
    accuracy = correct / total
    return avg_loss, accuracy
```

### 2.2 train() vs eval() 的区别

| 模式 | Dropout | BatchNorm | 用途 |
|------|---------|-----------|------|
| `model.train()` | 随机丢弃神经元 | 用当前 batch 统计量 | 训练 |
| `model.eval()` | 不丢弃 | 用全局统计量 | 评估/推理 |

⚠️ **忘记切换模式是常见 bug！** 评估时用 train() 会导致结果不稳定。

### 2.3 torch.no_grad() 的作用

```python
# 训练时：需要梯度
outputs = model(x)      # 计算图被记录
loss.backward()         # 计算梯度

# 评估时：不需要梯度
with torch.no_grad():   # 关闭计算图
    outputs = model(x)  # 不记录，节省内存
```

**为什么评估时要关？**
- 节省约 50% 显存
- 加速推理（不计算梯度）
- 防止意外修改参数

---

## 3. 模型保存与加载

### 3.1 保存/加载 state_dict（推荐）

```python
# 保存
torch.save(model.state_dict(), 'model.pth')

# 加载
model = MyModel()  # 先创建模型结构
model.load_state_dict(torch.load('model.pth'))
model.eval()
```

**为什么保存 state_dict 而不是整个模型？**
- state_dict 只包含参数，体积小
- 不依赖代码结构，更灵活
- 方便断点续训

### 3.2 保存/加载完整 checkpoint

```python
# 保存训练状态
checkpoint = {
    'epoch': epoch,
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'loss': loss,
}
torch.save(checkpoint, 'checkpoint.pth')

# 加载
checkpoint = torch.load('checkpoint.pth')
model.load_state_dict(checkpoint['model_state_dict'])
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
start_epoch = checkpoint['epoch']
```

### 3.3 模型文件大小参考

| 模型 | 参数量 | state_dict 大小 |
|------|--------|----------------|
| 2 层网络 (10→256→10) | ~27K | ~108 KB |
| 3 层网络 (784→256→128→10) | ~235K | ~940 KB |
| ResNet-18 | ~11M | ~44 MB |

---

## 4. 图解：完整训练流程

```
┌──────────────────────────────────────────────────────────────┐
│                    完整训练流程                                │
│                                                              │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐               │
│  │  原始数据 │ →  │ Dataset  │ →  │DataLoader│               │
│  └─────────┘    └──────────┘    └────┬─────┘               │
│                                      │                       │
│                                      ▼                       │
│                              ┌──────────────┐                │
│                              │  for batch in │                │
│                              │    loader:    │                │
│                              └──────┬───────┘                │
│                                     │                         │
│              ┌──────────────────────┼──────────────────────┐ │
│              ▼                      ▼                      ▼ │
│    ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐│
│    │   前向传播        │  │   反向传播        │  │  参数更新   ││
│    │ model(batch_x)  │  │ loss.backward() │  │ optim.step ││
│    └────────┬────────┘  └────────┬────────┘  └─────┬──────┘│
│             │                    │                   │       │
│             ▼                    ▼                   ▼       │
│    ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐│
│    │   计算损失        │  │   累计梯度        │  │ 清空梯度    ││
│    │ criterion(out,y)│  │   自动求导        │  │ zero_grad  ││
│    └─────────────────┘  └─────────────────┘  └────────────┘│
│                                                              │
│  Epoch 结束 → 打印 Loss/Acc → 检查是否保存最佳模型           │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. 实战：MNIST 手写数字识别

### 5.1 网络架构

```
输入: 28×28 = 784 维
  │
  ▼
Linear(784, 512) → ReLU → Dropout(0.2)
  │
  ▼
Linear(512, 256) → ReLU → Dropout(0.2)
  │
  ▼
Linear(256, 10) → 输出（10 个数字类别）
```

### 5.2 完整代码

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import os

# ========== 1. 配置 ==========
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")

# ========== 2. 数据加载 ==========
transform = transforms.Compose([
    transforms.ToTensor(),                # 转为 tensor，像素值 0~1
    transforms.Normalize((0.1307,), (0.3081,))  # MNIST 的均值和标准差
])

train_dataset = datasets.MNIST('./data', train=True, download=True, transform=transform)
test_dataset = datasets.MNIST('./data', train=False, transform=transform)

train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True, num_workers=2)
test_loader = DataLoader(test_dataset, batch_size=1000, shuffle=False)

# ========== 3. 定义模型 ==========
class MNISTNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.flatten = nn.Flatten()
        self.net = nn.Sequential(
            nn.Linear(784, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 10)
        )

    def forward(self, x):
        x = self.flatten(x)  # (batch, 1, 28, 28) → (batch, 784)
        return self.net(x)

model = MNISTNet().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# ========== 4. 训练循环 ==========
best_acc = 0
for epoch in range(10):
    # 训练
    model.train()
    train_loss = 0
    correct = 0
    total = 0

    for batch_x, batch_y in train_loader:
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)

        optimizer.zero_grad()
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()

        train_loss += loss.item() * batch_x.size(0)
        _, predicted = outputs.max(1)
        correct += predicted.eq(batch_y).sum().item()
        total += batch_y.size(0)

    train_loss /= total
    train_acc = correct / total

    # 测试
    model.eval()
    test_loss = 0
    test_correct = 0
    test_total = 0

    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            test_loss += loss.item() * batch_x.size(0)
            _, predicted = outputs.max(1)
            test_correct += predicted.eq(batch_y).sum().item()
            test_total += batch_y.size(0)

    test_loss /= test_total
    test_acc = test_correct / test_total

    print(f"Epoch [{epoch+1}/10] "
          f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
          f"Test Loss: {test_loss:.4f} Acc: {test_acc:.4f}")

    # 保存最佳模型
    if test_acc > best_acc:
        best_acc = test_acc
        torch.save(model.state_dict(), 'best_mnist.pth')
        print(f"  → 保存最佳模型 (acc={test_acc:.4f})")

print(f"\n🎯 最佳测试准确率: {best_acc:.4f}")
```

### 5.3 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| Batch size | 64 | 平衡速度与稳定性 |
| 优化器 | Adam | 自适应学习率，调参少 |
| Dropout | 0.2 | 防止过拟合 |
| 数据增强 | 无 | MNIST 太简单，不需要 |
| 标准化 | Normalize | 加速收敛 |

---

## 6. API 速查表

### DataLoader 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `batch_size` | 1 | 每批样本数 |
| `shuffle` | False | 是否打乱顺序 |
| `num_workers` | 0 | 并行加载进程数 |
| `drop_last` | False | 是否丢弃不完整的最后一批 |
| `pin_memory` | False | 锁页内存，加速 GPU 传输 |

### 模型模式切换

| 方法 | 说明 |
|------|------|
| `model.train()` | 训练模式 |
| `model.eval()` | 评估模式 |
| `torch.no_grad()` | 关闭梯度计算 |

### 保存/加载

| 操作 | 代码 |
|------|------|
| 保存参数 | `torch.save(model.state_dict(), 'path.pth')` |
| 加载参数 | `model.load_state_dict(torch.load('path.pth'))` |
| 保存 checkpoint | `torch.save({'model': ..., 'optim': ..., 'epoch': ...}, 'ckpt.pth')` |

---

## 7. 思考题

1. **为什么训练时要 shuffle 数据？** 打乱顺序防止模型记住数据顺序，减少梯度估计的偏差。

2. **num_workers 设为 0 和 4 有什么区别？** 0 表示主进程加载（慢），4 表示 4 个子进程并行加载（快，但增加内存开销）。

3. **Dropout 为什么只在训练时启用？** Dropout 是一种正则化，训练时随机丢弃让网络更鲁棒；推理时所有神经元都参与才能得到稳定输出。

4. **为什么 Adam 的默认学习率比 SGD 小？** Adam 有自适应机制，会自动缩放梯度，所以用更小的初始学习率；SGD 需要更大步长保证收敛。

5. **checkpoint 和 state_dict 有什么区别？** state_dict 只含模型参数；checkpoint 还包含优化器状态、epoch 等训练信息，适合断点续训。
