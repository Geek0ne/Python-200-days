"""
Day 114 - 02 进阶：激活函数与损失函数对比
==========================================
理解不同激活函数和损失函数的行为差异
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

# ========== 1. 激活函数对比 ==========
print("=" * 60)
print("激活函数对比")
print("=" * 60)

x = torch.linspace(-5, 5, 11)  # -5 到 5，11 个点
print(f"\n输入: {x.tolist()}\n")

# ReLU
relu_out = F.relu(x)
print(f"ReLU 输出:      {relu_out.tolist()}")
print(f"  特点: 负值变0，正值不变")

# Leaky ReLU
leaky_relu_out = F.leaky_relu(x, negative_slope=0.01)
print(f"\nLeaky ReLU 输出: {leaky_relu_out.tolist()}")
print(f"  特点: 负值乘以0.01，避免神经元死亡")

# Sigmoid
sigmoid_out = torch.sigmoid(x)
print(f"\nSigmoid 输出:   {sigmoid_out.tolist()}")
print(f"  特点: 压缩到 (0,1)，容易梯度消失")

# Tanh
tanh_out = torch.tanh(x)
print(f"\nTanh 输出:      {tanh_out.tolist()}")
print(f"  特点: 压缩到 (-1,1)，零中心")

# ========== 2. 梯度对比（核心！） ==========
print("\n" + "=" * 60)
print("梯度对比（为什么 ReLU 更好）")
print("=" * 60)

# 创建带梯度的张量
x_grad = torch.tensor([2.0, -2.0], requires_grad=True)

# ReLU 梯度
relu_y = F.relu(x_grad)
relu_y.sum().backward()
print(f"\nReLU 输入:  {x_grad.tolist()}")
print(f"ReLU 输出:  {relu_y.tolist()}")
print(f"ReLU 梯度:  {x_grad.grad.tolist()}")
# 正值梯度=1，负值梯度=0

# Sigmoid 梯度
x_grad2 = torch.tensor([2.0, -2.0], requires_grad=True)
sig_y = torch.sigmoid(x_grad2)
sig_y.sum().backward()
print(f"\nSigmoid 输入:  {x_grad2.tolist()}")
print(f"Sigmoid 输出:  {sig_y.tolist()}")
print(f"Sigmoid 梯度:  {x_grad2.grad.tolist()}")
# 梯度很小 → 梯度消失

# ========== 3. 损失函数对比 ==========
print("\n" + "=" * 60)
print("损失函数对比")
print("=" * 60)

# MSE Loss（回归）
mse = nn.MSELoss()
pred = torch.tensor([3.0, 5.0, 2.0])
target = torch.tensor([3.5, 4.0, 2.5])
mse_loss = mse(pred, target)
print(f"\nMSE Loss:")
print(f"  预测: {pred.tolist()}")
print(f"  目标: {target.tolist()}")
print(f"  损失: {mse_loss.item():.4f}")

# CrossEntropyLoss（分类）
ce = nn.CrossEntropyLoss()
# logits: 未经过 Softmax 的原始输出
logits = torch.tensor([
    [2.0, 1.0, 0.1],   # 样本1: 类0的概率最高
    [0.5, 2.0, 0.3],   # 样本2: 类1的概率最高
])
labels = torch.tensor([0, 1])  # 真实标签
ce_loss = ce(logits, labels)
print(f"\nCrossEntropyLoss:")
print(f"  Logits:\n{logits}")
print(f"  标签: {labels.tolist()}")
print(f"  损失: {ce_loss.item():.4f}")

# 注意：CrossEntropyLoss 内部已包含 Softmax
probs = F.softmax(logits, dim=1)
print(f"  Softmax 概率:\n{probs}")

# ========== 4. Dying ReLU 问题演示 ==========
print("\n" + "=" * 60)
print("Dying ReLU 问题")
print("=" * 60)

# 模拟：如果权重全是负的，ReLU 永远输出 0
bad_weight = torch.tensor([[-1.0, -1.0]], requires_grad=True)
x_input = torch.tensor([1.0, 1.0])
output = F.relu(x_input @ bad_weight.T)
print(f"\n输入: {x_input.tolist()}")
print(f"权重: {bad_weight.tolist()}")
print(f"ReLU 输出: {output.item()}")
print(f"梯度: {bad_weight.grad}")
print("→ 输出为 0，梯度也为 0，参数永远无法更新！")
print("→ 解决方案：用 LeakyReLU 或减小学习率")

# ========== 5. 实际网络中的激活函数选择 ==========
print("\n" + "=" * 60)
print("实战：正确的网络结构")
print("=" * 60)

class ProperNet(nn.Module):
    """隐藏层用 ReLU，输出层不加激活函数"""
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(10, 64),
            nn.ReLU(),           # 隐藏层 → ReLU
            nn.Linear(64, 32),
            nn.ReLU(),           # 隐藏层 → ReLU
            nn.Linear(32, 1)     # 输出层 → 无激活（回归任务）
        )

    def forward(self, x):
        return self.net(x)

model = ProperNet()
print(model)
x = torch.randn(1, 10)
print(f"\n输入: {x.shape}")
print(f"输出: {model(x).shape}")
print(f"输出值: {model(x).item():.4f}")
