# Day 116 — CNN 卷积神经网络 · 练习清单

## ✅ 今日完成清单

- [ ] 理解卷积运算过程（滑动窗口、逐元素相乘求和）
- [ ] 掌握 Conv2d 的关键参数（in/out channels, kernel_size, stride, padding）
- [ ] 能手动计算卷积输出尺寸
- [ ] 理解池化层的作用（降维、不变性）
- [ ] 理解 BatchNorm 的作用和使用位置
- [ ] 掌握数据增强的基本技巧
- [ ] 完成 CIFAR-10 图像分类实战

---

## 基础练习题

### 练习 1：输出尺寸计算
计算以下配置的输出尺寸：
1. Conv2d(3, 16, 3, padding=1)，输入 32×32
2. Conv2d(16, 32, 3, stride=2)，输入 32×32
3. MaxPool2d(2, 2)，输入 16×16
4. AdaptiveAvgPool2d(1)，输入 8×8

### 练习 2：参数量计算
一个卷积层 Conv2d(3, 64, 3, padding=1)：
1. 权重参数量是多少？
2. 加上偏置后总参数量是多少？

### 练习 3：数据增强选择
为以下场景选择合适的数据增强：
1. 医学图像分类（不能翻转）
2. 自然场景分类（可以增强）
3. 文字 OCR（不能旋转）

---

## 进阶挑战题

### 挑战 1：实现 ResNet 基本块
实现一个残差连接（skip connection）：
```python
class ResidualBlock(nn.Module):
    # 输入 → Conv → BN → ReLU → Conv → BN → (+输入) → ReLU
```

### 挑战 2：可视化卷积核
加载训练好的模型，提取第一层卷积核权重并可视化。

### 挑战 3：对比不同网络结构
比较以下配置的 CIFAR-10 准确率：
- 基线 CNN（3 层）
- 加 BatchNorm
- 加数据增强
- 两者都加

---

## 💡 自测要点

1. Conv2d 的 in_channels 和 out_channels 分别代表什么？
2. 为什么卷积层通常不用 padding=0（不填充）？
3. MaxPool 和 AvgPool 各自适用于什么场景？
4. BatchNorm 为什么放在 Linear 前而不是后？
