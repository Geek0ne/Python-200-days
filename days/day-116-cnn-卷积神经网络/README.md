# Day 116 — CNN 卷积神经网络

> 🎯 今日目标：理解卷积层和池化层的原理，掌握 CNN 结构设计，完成 CIFAR-10 图像分类实战。

---

## 1. 卷积层原理

### 1.1 为什么用卷积？

全连接网络处理图像有两个致命问题：
- **参数爆炸**：224×224×3 的图像 → 展平后 150,528 维，第一个全连接层就有几亿参数
- **丢失空间信息**：展平后像素之间的位置关系全部丢失

**卷积层的三大优势：**
1. **局部连接**：每个神经元只看一个小区域（感受野），参数少
2. **权值共享**：同一个卷积核在整张图上滑动，大幅减少参数
3. **平移不变性**：猫在图片左上角还是右下角，都能识别

### 1.2 卷积运算过程

```
输入图像 (5×5)          卷积核 (3×3)         输出特征图 (3×3)
┌───────────────┐     ┌───────────┐      ┌───────────────┐
│ 1  0  1  0  1 │     │ 1  0  1   │      │ 4  3  4       │
│ 0  1  0  1  0 │  ⊗  │ 0  1  0   │  =   │ 2  4  3       │
│ 1  0  1  0  1 │     │ 1  0  1   │      │ 4  3  4       │
│ 0  1  0  1  0 │     └───────────┘      └───────────────┘
│ 1  0  1  0  1 │
└───────────────┘

运算过程（以左上角为例）：
  输入左上 3×3 区域:        卷积核:
  ┌───────────┐            ┌───────────┐
  │ 1  0  1   │            │ 1  0  1   │
  │ 0  1  0   │     ×      │ 0  1  0   │     = 1×1+0×0+1×1 + 0×0+1×1+0×0 + 1×1+0×0+1×1 = 4
  │ 1  0  1   │            │ 1  0  1   │
  └───────────┘            └───────────┘
```

### 1.3 关键参数

```python
nn.Conv2d(
    in_channels=3,      # 输入通道数（RGB=3，灰度=1）
    out_channels=16,    # 输出通道数（卷积核数量）
    kernel_size=3,      # 卷积核大小（3×3）
    stride=1,           # 步幅（每次滑动几格）
    padding=1           # 填充（周围补几圈 0）
)
```

### 1.4 输出尺寸计算公式

```
输出尺寸 = (输入尺寸 - 卷积核大小 + 2×填充) / 步幅 + 1

例如：
  输入: 32×32, 卷积核: 3×3, padding=1, stride=1
  输出: (32 - 3 + 2×1) / 1 + 1 = 32×32  ← 尺寸不变！

  输入: 32×32, 卷积核: 3×3, padding=0, stride=1
  输出: (32 - 3 + 0) / 1 + 1 = 30×30  ← 尺寸缩小
```

**保持尺寸不变的秘诀：** `padding = kernel_size // 2`（3×3 卷积用 padding=1）

### 1.5 卷积核的作用

每个卷积核学习检测一种**特征模式**：

| 卷积核类型 | 检测内容 | 示例 |
|-----------|---------|------|
| 水平边缘 | 横向线条 | 检测地平线 |
| 垂直边缘 | 纵向线条 | 检测柱子 |
| 对角边缘 | 斜向线条 | 检测屋顶 |
| 纹理 | 重复图案 | 检测毛发、布料 |

**网络越深，检测的特征越高级：**
```
浅层卷积 → 边缘、颜色
中间卷积 → 纹理、形状
深层卷积 → 眼睛、鼻子（物体部件）
最后层   → 完整物体（人脸、猫）
```

---

## 2. 池化层

### 2.1 Max Pooling — 最大池化

```python
nn.MaxPool2d(kernel_size=2, stride=2)
```

```
输入 (4×4):                输出 (2×2):
┌───────────────────┐      ┌───────────┐
│ 1  3  2  4        │      │ 3     4   │
│ 5  6  1  2   →    │  →   │           │
│ 3  2  8  7        │      │ 3     8   │
│ 1  4  3  5        │      └───────────┘
└───────────────────┘
每个 2×2 区域取最大值
```

### 2.2 池化的作用

1. **降维**：特征图尺寸减半，减少计算量
2. **不变性**：小幅平移不影响最大值
3. **扩大感受野**：后续层能"看到"更大区域

### 2.3 池化 vs 步幅

| 方式 | 优点 | 缺点 |
|------|------|------|
| MaxPool2d | 保留最强特征 | 丢失部分信息 |
| stride=2 卷积 | 可学习的下采样 | 参数更多 |
| AveragePool | 保留平均信息 | 可能模糊特征 |

---

## 3. CNN 结构设计

### 3.1 经典 CNN 结构

```
┌─────────────────────────────────────────────────────────┐
│                    CNN 典型结构                           │
│                                                         │
│  输入图像                                               │
│    ↓                                                    │
│  [Conv → ReLU → Pool] × N 层     ← 特征提取             │
│    ↓                                                    │
│  Flatten                                                │
│    ↓                                                    │
│  [Linear → ReLU] × M 层          ← 分类器               │
│    ↓                                                    │
│  Linear → 输出                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.2 CNN 设计经验法则

| 规则 | 说明 |
|------|------|
| 卷积核用 3×3 | 小卷积核堆叠比大卷积核更高效 |
| 通道数递增 | 64→128→256，特征越来越丰富 |
| 空间尺寸递减 | 32→16→8，特征越来越抽象 |
| 每次池化后加通道 | 尺寸减半，通道翻倍 |
| Padding 保持尺寸 | 用 `padding=1` 保持空间大小 |

### 3.3 参数量对比

```
全连接网络 (28×28→10):
  输入: 784 维
  参数: 784 × 10 = 7,840

CNN (3×3 卷积核, 32 个):
  参数: 3 × 3 × 1 × 32 = 288  ← 少 27 倍！
```

---

## 4. 图解：卷积神经网络

```
输入: 3×32×32 (RGB 图像)
    │
    ▼ Conv2d(3, 32, 3×3) + ReLU + MaxPool(2×2)
特征图: 32×16×16
    │
    ▼ Conv2d(32, 64, 3×3) + ReLU + MaxPool(2×2)
特征图: 64×8×8
    │
    ▼ Conv2d(64, 128, 3×3) + ReLU + MaxPool(2×2)
特征图: 128×4×4
    │
    ▼ Flatten: 128×4×4 = 2048
    │
    ▼ Linear(2048, 256) + ReLU + Dropout
    │
    ▼ Linear(256, 10) → 输出
```

---

## 5. 实战：CIFAR-10 图像分类

### 5.1 CIFAR-10 数据集

- 60,000 张 32×32 彩色图像
- 10 个类别：飞机、汽车、鸟、猫、鹿、狗、青蛙、马、船、卡车
- 训练集 50,000，测试集 10,000

### 5.2 完整代码

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# ========== 1. 设备与配置 ==========
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"设备: {device}")

# ========== 2. 数据加载 ==========
# CIFAR-10 的均值和标准差（提前计算好的）
mean = (0.4914, 0.4822, 0.4465)
std = (0.2470, 0.2435, 0.2616)

train_transform = transforms.Compose([
    transforms.RandomCrop(32, padding=4),     # 随机裁剪
    transforms.RandomHorizontalFlip(),        # 随机水平翻转
    transforms.ColorJitter(brightness=0.2),   # 颜色抖动
    transforms.ToTensor(),
    transforms.Normalize(mean, std)
])

test_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean, std)
])

train_dataset = datasets.CIFAR10('./data', train=True, download=True, transform=train_transform)
test_dataset = datasets.CIFAR10('./data', train=False, transform=test_transform)

train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True, num_workers=2)
test_loader = DataLoader(test_dataset, batch_size=1000, shuffle=False)

classes = ('plane', 'car', 'bird', 'cat', 'deer',
           'dog', 'frog', 'horse', 'ship', 'truck')

# ========== 3. 定义 CNN 模型 ==========
class CIFARNet(nn.Module):
    """3 层 CNN + 全连接分类器"""
    def __init__(self, num_classes=10):
        super().__init__()

        # 特征提取
        self.features = nn.Sequential(
            # Block 1: 3 → 32 通道
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),      # 32×32 → 16×16

            # Block 2: 32 → 64 通道
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),      # 16×16 → 8×8

            # Block 3: 64 → 128 通道
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),      # 8×8 → 4×4
        )

        # 分类器
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

model = CIFARNet().to(device)
print(f"参数量: {sum(p.numel() for p in model.parameters()):,}")

# ========== 4. 损失函数与优化器 ==========
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)

# ========== 5. 训练循环 ==========
def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    for batch_x, batch_y in loader:
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)

        optimizer.zero_grad()
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * batch_x.size(0)
        _, predicted = outputs.max(1)
        correct += predicted.eq(batch_y).sum().item()
        total += batch_y.size(0)

    return total_loss / total, correct / total

def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0
    correct = 0
    total = 0

    with torch.no_grad():
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)

            total_loss += loss.item() * batch_x.size(0)
            _, predicted = outputs.max(1)
            correct += predicted.eq(batch_y).sum().item()
            total += batch_y.size(0)

    return total_loss / total, correct / total

# 训练
best_acc = 0
for epoch in range(50):
    train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
    val_loss, val_acc = evaluate(model, test_loader, criterion, device)
    scheduler.step()

    if (epoch + 1) % 10 == 0:
        print(f"Epoch [{epoch+1}/50] "
              f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
              f"Test Loss: {val_loss:.4f} Acc: {val_acc:.4f}")

    if val_acc > best_acc:
        best_acc = val_acc
        torch.save(model.state_dict(), 'best_cifar.pth')

print(f"\n🎯 最佳测试准确率: {best_acc:.4f}")
```

### 5.3 数据增强的作用

```
原始图像 ──→ RandomCrop ──→ RandomHorizontalFlip ──→ ColorJitter
  32×32       32×32（有填充）      水平翻转              颜色微调
    │              │                  │                    │
    └──────────────┴──────────────────┴────────────────────┘
                        ↓
              每个 epoch 看到不同的图像版本
              相当于扩充了训练集
              提高泛化能力，减少过拟合
```

### 5.4 BatchNorm 的作用

```python
nn.BatchNorm2d(32)  # 对 32 个通道分别做归一化
```

**原理：** 对每个通道的特征图做归一化（均值 0，方差 1），然后学习缩放和偏移。

**好处：**
1. 加速训练收敛
2. 允许使用更大学习率
3. 有轻微正则化效果
4. 减少对参数初始化的敏感性

---

## 6. API 速查表

### 卷积层参数

| 参数 | 说明 | 常用值 |
|------|------|--------|
| `in_channels` | 输入通道数 | RGB=3, 上一层 out_channels |
| `out_channels` | 输出通道数（卷积核数） | 32, 64, 128, 256 |
| `kernel_size` | 卷积核大小 | 3, 5 |
| `stride` | 步幅 | 1（保持尺寸）, 2（下采样） |
| `padding` | 填充 | 0（不填充）, 1（3×3 保持尺寸） |

### 池化层参数

| 类型 | 参数 | 说明 |
|------|------|------|
| `MaxPool2d` | kernel_size=2, stride=2 | 最常用，尺寸减半 |
| `AvgPool2d` | kernel_size=2, stride=2 | 保留平均信息 |
| `AdaptiveAvgPool2d` | output_size=(1,1) | 全局平均池化 |

### 输出尺寸公式

```
输出 = (输入 - kernel_size + 2×padding) / stride + 1
```

---

## 7. 思考题

1. **为什么卷积核通常用 3×3 而不是 5×5 或 7×7？** 两个 3×3 卷积堆叠的感受野等于一个 5×5，但参数更少（2×9=18 vs 25），非线性更强。

**参考答案**

两个 3×3 卷积堆叠的**感受野**等于一个 5×5（每个输出像素能「看到」5×5 区域），但参数更少：每对通道 2×(3×3)=18 vs 5×5=25（少约 28%），而且中间多了一次 ReLU → **非线性更强、表达力更好**。同理三个 3×3 ≈ 一个 7×7 的感受野，参数 27 vs 49。小核还更省计算、等效网络更深。这正是 VGG 的核心思想。

小例子：覆盖 5×5 区域用两个 3×3，参数 18<25，还多一层非线性。

💡 提示：首层有时用较大核（如 ResNet conv1 的 7×7）快速抓粗结构，但主体仍是 3×3 堆叠。

2. **MaxPool 和 AveragePool 什么时候用哪个？** 特征提取阶段用 MaxPool（保留最强特征），分类前用全局 AveragePool（保留整体信息）。

**参考答案**

- **MaxPool**：取区域最强激活，保留显著边缘/纹理，带来一定平移不变性，适合**卷积特征提取阶段**的下采样。
- **AveragePool**：取平均，保留整体/背景信息、更平滑。**全局平均池化（GAP）** 用在分类前：把每个通道平均成 1 个值，替代庞大的全连接层 → 参数骤减、过拟合更轻，保留通道级整体信息（如 ResNet 结尾）。

小例子：特征图用 MaxPool 下采样保显著特征；末尾 7×7×512 → GAP → 512 维 → FC，而不是展平成 25088 维接巨型 FC。

💡 提示：下采样特征用 MaxPool，分类前汇总用 GAP。

3. **BatchNorm 放在 ReLU 前还是后？** 原始论文建议 BN → ReLU，但实践中两种都可以。现代网络常用 BN → ReLU。

**参考答案**

原始 BN 论文把 BN 放在激活**前**（Conv → BN → ReLU），先归一化再让非线性拿到尺度合适的输入。实践中两种顺序都能用，现代网络常见 Conv → BN → ReLU；也有「预激活」结构（如 pre-activation ResNet）用 BN → ReLU → Conv。没有绝对赢家，BN→ReLU 是稳妥默认。另外加了 BN 后卷积的 bias 是冗余的（被 BN 的 β 吸收），常设 `bias=False`。

小例子：`nn.Conv2d(..., bias=False)` → `nn.BatchNorm2d` → `nn.ReLU`。

💡 提示：两种顺序都有人用，跟随具体架构的约定即可；BN→ReLU 是安全默认。

4. **如果输入图像是 224×224，经过 3 次 MaxPool2d(2,2) 后尺寸是多少？** 224→112→56→28，每次减半。

**参考答案**

每次 `MaxPool2d(2,2)` 把空间尺寸减半：224→112→56→28，通道数不变。公式 `输出=(输入-核)/步幅+1`，即 (224-2)/2+1=112，依此类推。

下面实测（需 `pip install torch`）：

```python
import torch
import torch.nn as nn

x = torch.randn(1, 3, 224, 224)   # 一张 224×224 的 RGB 图
pool = nn.MaxPool2d(kernel_size=2, stride=2)
for i in range(3):
    x = pool(x)
    print(f"第{i+1}次 MaxPool2d(2,2) 后: {tuple(x.shape)}")
```

预期输出：

```
第1次 MaxPool2d(2,2) 后: (1, 3, 112, 112)
第2次 MaxPool2d(2,2) 后: (1, 3, 56, 56)
第3次 MaxPool2d(2,2) 后: (1, 3, 28, 28)
```

💡 提示：尺寸为奇数时向下取整；池化不改变通道数。

5. **CNN 的参数量主要由什么决定？** 卷积层参数 = kernel_size × kernel_size × in_channels × out_channels × 层数。全连接层通常参数更多但更容易过拟合。

**参考答案**

- **卷积层**参数 = `kernel_h × kernel_w × in_channels × out_channels`（再加 out_channels 个 bias，若启用），乘以层数。由核大小、输入/输出通道数、深度决定，**与输入图像空间尺寸无关**（权值共享）。
- **全连接层**参数 = `in_features × out_features`（+bias）。因为展平后 in_features 很大，FC 往往参数最多、也最容易过拟合。

小例子：`Conv2d(3,32,3)` 参数 = 3×3×3×32 + 32 = 896；`Linear(2048,256)` = 2048×256 + 256 = 524544——FC 远多于卷积。

💡 提示：用 GAP 压缩 FC；通道数和核大小决定卷积参数，空间尺寸不影响卷积参数量。
