# Day 115 — 训练流程 · 图解

## DataLoader 工作原理

```
原始数据集 (1000 样本)
    │
    ▼ shuffle=True（打乱索引）
索引序列: [847, 123, 56, 901, ...]
    │
    ▼ 按 batch_size=32 分批
┌─────────────────────────────────┐
│  Batch 0: [847, 123, ..., 56]  │  32 个样本
├─────────────────────────────────┤
│  Batch 1: [901, 45, ..., 234]  │  32 个样本
├─────────────────────────────────┤
│  ...                           │
├─────────────────────────────────┤
│  Batch 31: [678, 12, ..., 89]  │  16 个样本 ← 不满一批
└─────────────────────────────────┘
    │
    ▼ drop_last=True → 丢弃最后一批
实际训练: 31 批 × 32 = 992 个样本
```

## 训练 vs 评估模式

```
┌──────────────────────┬──────────────────────────────┐
│      model.train()   │       model.eval()            │
├──────────────────────┼──────────────────────────────┤
│  Dropout: 随机丢弃   │  Dropout: 全部保留            │
│  BatchNorm: 用 batch │  BatchNorm: 用全局均值/方差   │
│  梯度: 正常计算       │  需配合 torch.no_grad()       │
│  用途: 训练阶段       │  用途: 验证/测试/推理          │
└──────────────────────┴──────────────────────────────┘
```

## 模型保存流程

```
训练过程中:
  ┌──────────┐
  │ Epoch 1  │ → val_acc=95.2% → 保存 checkpoint
  │ Epoch 2  │ → val_acc=96.1% → 保存 checkpoint（更好）
  │ Epoch 3  │ → val_acc=95.8% → 不保存（没更好）
  │ Epoch 4  │ → val_acc=96.5% → 保存 checkpoint（最好）
  └──────────┘

保存内容 (state_dict):
┌─────────────────────────────────┐
│  model.pth                      │
│  ├── layer1.weight (512×784)    │
│  ├── layer1.bias (512)          │
│  ├── layer2.weight (256×512)    │
│  ├── layer2.bias (256)          │
│  ├── layer3.weight (10×256)     │
│  └── layer3.bias (10)           │
└─────────────────────────────────┘

加载:
  1. 创建模型结构 → model = MNISTNet()
  2. 加载参数 → model.load_state_dict(torch.load('model.pth'))
  3. 设为评估模式 → model.eval()
```

## MNIST 数据流

```
MNIST 原始图像 (28×28 像素，0~255)
    │
    ▼ transforms.ToTensor()
Tensor (1, 28, 28)，值 [0, 1]
    │
    ▼ transforms.Normalize((0.1307,), (0.3081,))
Tensor (1, 28, 28)，均值≈0，标准差≈1
    │
    ▼ nn.Flatten()
Tensor (784,) — 展平为一维向量
    │
    ▼ Linear(784, 512) → ReLU → Dropout
Tensor (512,)
    │
    ▼ Linear(512, 256) → ReLU → Dropout
Tensor (256,)
    │
    ▼ Linear(256, 10)
Tensor (10,) — 10 个类别的 logits
    │
    ▼ torch.argmax()
预测数字 (0~9)
```
