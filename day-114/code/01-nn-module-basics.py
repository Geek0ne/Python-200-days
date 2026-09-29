"""
Day 114 - 01 基础：nn.Module 与线性层
====================================
学习 nn.Module 的基本用法和 nn.Linear 的创建与使用
"""

import torch
import torch.nn as nn

# ========== 1. 创建最简单的网络 ==========
class SimpleNet(nn.Module):
    """一个单层线性网络：输入 10 → 输出 3"""
    def __init__(self):
        super().__init__()  # 必须调用父类构造函数！
        self.linear = nn.Linear(10, 3)  # 线性层

    def forward(self, x):
        """定义前向传播：数据如何通过网络"""
        return self.linear(x)

# 创建模型实例
model = SimpleNet()
print("模型结构：")
print(model)

# ========== 2. 查看参数 ==========
print("\n--- 模型参数 ---")
for name, param in model.named_parameters():
    print(f"  {name}: shape={param.shape}, requires_grad={param.requires_grad}")

# ========== 3. 前向传播 ==========
x = torch.randn(1, 10)  # batch_size=1, features=10
output = model(x)
print(f"\n输入 shape: {x.shape}")
print(f"输出 shape: {output.shape}")
print(f"输出值: {output}")

# ========== 4. 多层网络 ==========
class MultiLayerNet(nn.Module):
    """两层网络：10 → 64 → 3"""
    def __init__(self):
        super().__init__()
        self.layer1 = nn.Linear(10, 64)
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(64, 3)

    def forward(self, x):
        x = self.layer1(x)
        x = self.relu(x)  # 激活函数
        x = self.layer2(x)
        return x

model2 = MultiLayerNet()
print("\n多层网络结构：")
print(model2)

# 批量输入
x_batch = torch.randn(5, 10)  # batch_size=5
output = model2(x_batch)
print(f"\n批量输入 shape: {x_batch.shape}")
print(f"批量输出 shape: {output.shape}")

# ========== 5. 参数总数统计 ==========
total_params = sum(p.numel() for p in model2.parameters())
trainable_params = sum(p.numel() for p in model2.parameters() if p.requires_grad)
print(f"\n总参数量: {total_params:,}")
print(f"可训练参数量: {trainable_params:,}")
