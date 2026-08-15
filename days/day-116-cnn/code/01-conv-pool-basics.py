"""
Day 116 - 01 基础：卷积层与池化层
====================================
理解 Conv2d 和 MaxPool2d 的工作原理
"""

import torch
import torch.nn as nn

# ========== 1. 卷积层基础 ==========
print("=" * 60)
print("卷积层基础")
print("=" * 60)

# 创建一个卷积层
conv = nn.Conv2d(
    in_channels=1,     # 输入通道（灰度图）
    out_channels=1,    # 输出通道（1 个卷积核）
    kernel_size=3,     # 3×3 卷积核
    stride=1,
    padding=0          # 不填充
)

print(f"卷积层结构: {conv}")
print(f"权重形状: {conv.weight.shape}")  # (1, 1, 3, 3)
print(f"偏置形状: {conv.bias.shape}")    # (1,)

# 手动设置卷积核权重（方便理解）
with torch.no_grad():
    conv.weight.copy_(torch.tensor([
        [[[1, 0, 1],
          [0, 1, 0],
          [1, 0, 1]]]
    ]).float())
    conv.bias.zero_()

# 创建输入 (batch=1, channel=1, height=5, width=5)
x = torch.tensor([[
    [[1, 0, 1, 0, 1],
     [0, 1, 0, 1, 0],
     [1, 0, 1, 0, 1],
     [0, 1, 0, 1, 0],
     [1, 0, 1, 0, 1]]
]]).float()

print(f"\n输入形状: {x.shape}")  # (1, 1, 5, 5)

# 前向传播
output = conv(x)
print(f"输出形状: {output.shape}")  # (1, 1, 3, 3)
print(f"输出值:\n{output.squeeze()}")

# ========== 2. 输出尺寸计算 ==========
print("\n" + "=" * 60)
print("输出尺寸计算")
print("=" * 60)

def calc_output_size(input_size, kernel_size, stride=1, padding=0):
    """计算卷积/池化后的输出尺寸"""
    return (input_size - kernel_size + 2 * padding) // stride + 1

# 不同配置的输出尺寸
configs = [
    (32, 3, 1, 0),   # 32→30
    (32, 3, 1, 1),   # 32→32（保持）
    (32, 3, 2, 0),   # 32→15
    (32, 5, 1, 2),   # 32→32（保持）
]

for in_size, k, s, p in configs:
    out = calc_output_size(in_size, k, s, p)
    print(f"  输入={in_size}, kernel={k}, stride={s}, padding={p} → 输出={out}")

# ========== 3. 多通道卷积 ==========
print("\n" + "=" * 60)
print("多通道卷积（RGB 图像）")
print("=" * 60)

# RGB 图像 → 32 个卷积核
conv_multi = nn.Conv2d(3, 32, kernel_size=3, padding=1)
x_rgb = torch.randn(1, 3, 32, 32)  # batch=1, RGB, 32×32

output = conv_multi(x_rgb)
print(f"输入: {x_rgb.shape}")   # (1, 3, 32, 32)
print(f"输出: {output.shape}")  # (1, 32, 32, 32)
print(f"参数量: {sum(p.numel() for p in conv_multi.parameters()):,}")
# 3×3×3×32 + 32 = 864 + 32 = 896

# ========== 4. 池化层 ==========
print("\n" + "=" * 60)
print("池化层")
print("=" * 60)

# MaxPool2d
maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
x_pool = torch.tensor([[
    [[1, 3, 2, 4],
     [5, 6, 1, 2],
     [3, 2, 8, 7],
     [1, 4, 3, 5]]
]]).float()

print(f"输入 (4×4):\n{x_pool.squeeze()}")
output = maxpool(x_pool)
print(f"\nMaxPool2d(2,2) 输出 (2×2):\n{output.squeeze()}")

# AdaptiveAvgPool2d
gap = nn.AdaptiveAvgPool2d(1)  # 输出 1×1
x_feat = torch.randn(1, 64, 8, 8)
output = gap(x_feat)
print(f"\n全局平均池化:")
print(f"  输入: {x_feat.shape}")
print(f"  输出: {output.shape}")  # (1, 64, 1, 1)

# ========== 5. 卷积 + 池化组合 ==========
print("\n" + "=" * 60)
print("卷积 + 池化组合")
print("=" * 60)

block = nn.Sequential(
    nn.Conv2d(3, 16, 3, padding=1),  # 32×32 → 32×32
    nn.ReLU(),
    nn.MaxPool2d(2, 2),              # 32×32 → 16×16
    nn.Conv2d(16, 32, 3, padding=1), # 16×16 → 16×16
    nn.ReLU(),
    nn.MaxPool2d(2, 2),              # 16×16 → 8×8
)

x = torch.randn(1, 3, 32, 32)
output = block(x)
print(f"输入: {x.shape}")
print(f"输出: {output.shape}")
print(f"参数量: {sum(p.numel() for p in block.parameters()):,}")
