"""
Day 115 - 01 基础：DataLoader 与 Dataset
==========================================
学习如何创建自定义 Dataset 和使用 DataLoader
"""

import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np

# ========== 1. 自定义 Dataset ==========
class SimpleDataset(Dataset):
    """一个简单的数据集：生成随机数据"""
    def __init__(self, n_samples=100, n_features=10):
        super().__init__()
        # 随机生成数据
        self.X = torch.randn(n_samples, n_features)
        # 简单的线性关系 + 噪声
        self.y = (self.X[:, 0] * 2 + self.X[:, 1] * 3 + 
                  torch.randn(n_samples) * 0.1)

    def __len__(self):
        """返回数据集大小"""
        return len(self.X)

    def __getitem__(self, idx):
        """返回第 idx 个样本"""
        return self.X[idx], self.y[idx]

# 创建数据集
dataset = SimpleDataset(n_samples=200, n_features=10)
print(f"数据集大小: {len(dataset)}")
print(f"单个样本: X={dataset[0][0].shape}, y={dataset[0][1].shape}")

# ========== 2. DataLoader 基础用法 ==========
print("\n--- DataLoader ---")
loader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=0  # Windows 上建议设为 0
)

print(f"批次数量: {len(loader)}")  # 200/32 ≈ 7 批
print(f"每批大小: {loader.batch_size}")

# 遍历一个 epoch
for batch_idx, (batch_x, batch_y) in enumerate(loader):
    print(f"  Batch {batch_idx}: x={batch_x.shape}, y={batch_y.shape}")
    if batch_idx >= 2:  # 只打印前 3 批
        break

# ========== 3. 训练/验证集划分 ==========
print("\n--- 训练/验证集划分 ---")
from torch.utils.data import random_split

train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size

train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
print(f"训练集: {len(train_dataset)} 样本")
print(f"验证集: {len(val_dataset)} 样本")

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

# ========== 4. 带变换的 Dataset ==========
print("\n--- 数据增强示例 ---")
from torchvision import transforms

# 图像变换管道
transform = transforms.Compose([
    transforms.Resize((32, 32)),           # 调整大小
    transforms.RandomHorizontalFlip(),     # 随机水平翻转
    transforms.RandomRotation(10),         # 随机旋转 ±10°
    transforms.ToTensor(),                 # 转为 tensor
    transforms.Normalize((0.5,), (0.5,))   # 归一化到 [-1, 1]
])

print("变换管道:")
for t in transform.transforms:
    print(f"  → {t}")

# ========== 5. DataLoader 高级参数 ==========
print("\n--- DataLoader 高级参数 ---")

advanced_loader = DataLoader(
    dataset,
    batch_size=64,
    shuffle=True,
    num_workers=0,        # 多进程加载（Windows 建议 0）
    pin_memory=True,      # 锁页内存，加速 GPU 传输
    drop_last=True,       # 丢弃最后不完整的 batch
    persistent_workers=False  # 是否保持 worker 进程
)

print(f"批次数量（drop_last=True）: {len(advanced_loader)}")
print(f"  原始: 200/64 = 3.125 → 3 批（丢弃最后不完整的）")
