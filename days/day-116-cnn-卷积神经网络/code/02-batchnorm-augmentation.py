"""
Day 116 - 02 进阶：BatchNorm 与数据增强
==========================================
理解 BatchNorm 的作用和数据增强技巧
"""

import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np

# ========== 1. BatchNorm 原理 ==========
print("=" * 60)
print("BatchNorm 原理")
print("=" * 60)

# 模拟一个特征图
batch_size = 4
channels = 3
height, width = 8, 8

x = torch.randn(batch_size, channels, height, width)

# BatchNorm2d
bn = nn.BatchNorm2d(channels)
bn.train()  # 训练模式

output = bn(x)

print(f"输入: {x.shape}")
print(f"输出: {output.shape}")

# 查看 BN 的参数
print(f"\nBN 参数:")
for name, param in bn.named_parameters():
    print(f"  {name}: shape={param.shape}, value={param.data}")

# 查看 BN 的 running stats
print(f"\nBN 运行统计量:")
print(f"  running_mean: {bn.running_mean}")
print(f"  running_var: {bn.running_var}")

# 训练 vs 评估模式的区别
bn.eval()  # 评估模式
output_eval = bn(x)
print(f"\n评估模式输出: 均值={output_eval.mean():.4f}, 方差={output_eval.var():.4f}")

# ========== 2. BatchNorm 的作用演示 ==========
print("\n" + "=" * 60)
print("BatchNorm 的作用")
print("=" * 60)

# 无 BN 的网络
class NetWithoutBN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(10, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
    def forward(self, x):
        return self.net(x)

# 有 BN 的网络
class NetWithBN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(10, 64),
            nn.BatchNorm1d(64),  # BN 层
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
    def forward(self, x):
        return self.net(x)

net_no_bn = NetWithoutBN()
net_with_bn = NetWithBN()

x = torch.randn(32, 10)  # batch=32

# 比较各层输出的分布
def check_layer_outputs(model, x, name):
    activations = []
    hooks = []
    def hook(module, input, output):
        activations.append(output.detach())
    for layer in model.net:
        if isinstance(layer, (nn.Linear, nn.BatchNorm1d)):
            hooks.append(layer.register_forward_hook(hook))
    model(x)
    for h in hooks:
        h.remove()
    print(f"\n{name} 各层输出统计:")
    for i, act in enumerate(activations):
        print(f"  Layer {i}: mean={act.mean():.4f}, std={act.std():.4f}")

check_layer_outputs(net_no_bn, x, "无 BN")
check_layer_outputs(net_with_bn, x, "有 BN")

# ========== 3. 数据增强 ==========
print("\n" + "=" * 60)
print("数据增强技巧")
print("=" * 60)

# 创建一个模拟图像
img_array = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
img = Image.fromarray(img_array)

# 训练时的数据增强
train_transform = transforms.Compose([
    transforms.RandomCrop(32, padding=4),          # 随机裁剪
    transforms.RandomHorizontalFlip(p=0.5),        # 随机水平翻转
    transforms.RandomRotation(15),                  # 随机旋转 ±15°
    transforms.ColorJitter(                        # 颜色抖动
        brightness=0.2,
        contrast=0.2,
        saturation=0.2,
        hue=0.1
    ),
    transforms.RandomAffine(                       # 随机仿射变换
        degrees=0,
        translate=(0.1, 0.1)
    ),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), 
                         (0.2470, 0.2435, 0.2616))
])

# 测试时不做增强（保持确定性）
test_transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), 
                         (0.2470, 0.2435, 0.2616))
])

print("训练增强管道:")
for t in train_transform.transforms:
    print(f"  → {t}")

# 生成增强后的样本
print("\n增强样本（同一张图生成 5 个不同版本）:")
for i in range(5):
    augmented = train_transform(img)
    print(f"  样本 {i+1}: shape={augmented.shape}, "
          f"range=[{augmented.min():.2f}, {augmented.max():.2f}]")

# ========== 4. 数据增强策略 ==========
print("\n" + "=" * 60)
print("数据增强策略")
print("=" * 60)

strategies = {
    "图像分类": [
        "RandomCrop + RandomHorizontalFlip（基础）",
        "ColorJitter（颜色抖动）",
        "RandAugment（自动增强）",
        "CutOut / RandomErasing（随机遮挡）"
    ],
    "目标检测": [
        "只能用不改变框位置的增强",
        "RandomHorizontalFlip",
        "颜色增强"
    ],
    "NLP": [
        "同义词替换",
        "随机插入/删除",
        "回译"
    ]
}

for task, aug_list in strategies.items():
    print(f"\n{task}:")
    for aug in aug_list:
        print(f"  • {aug}")
