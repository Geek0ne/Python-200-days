"""
Day 114 - 03 实战：手写数字分类器
==================================
用 2 层网络在 digits 数据集上做分类
完整流程：数据准备 → 模型定义 → 训练 → 测试
"""

import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np

# ========== 1. 数据准备 ==========
print("=" * 60)
print("Step 1: 数据准备")
print("=" * 60)

digits = load_digits()
X = digits.data.astype(np.float32)    # (1797, 64) — 8×8 图像展平
y = digits.target.astype(np.int64)    # (1797,) — 0~9 的数字标签

print(f"数据集大小: {X.shape[0]} 个样本")
print(f"特征维度: {X.shape[1]} (8×8 像素)")
print(f"类别数: {len(np.unique(y))} (数字 0~9)")

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"训练集: {X_train.shape[0]} 个")
print(f"测试集: {X_test.shape[0]} 个")

# 标准化（重要！神经网络对输入尺度敏感）
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# 转为 PyTorch 张量
X_train_t = torch.tensor(X_train)
y_train_t = torch.tensor(y_train)
X_test_t = torch.tensor(X_test)
y_test_t = torch.tensor(y_test)

# ========== 2. 定义模型 ==========
print("\n" + "=" * 60)
print("Step 2: 定义模型")
print("=" * 60)

class DigitNet(nn.Module):
    """2 层全连接网络"""
    def __init__(self, input_dim=64, hidden_dim=256, output_dim=10):
        super().__init__()
        self.layer1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.layer1(x)
        x = self.relu(x)
        x = self.layer2(x)
        return x  # 注意：输出层不加 Softmax，CrossEntropyLoss 内含

model = DigitNet()
print(model)

# 统计参数
total = sum(p.numel() for p in model.parameters())
print(f"\n总参数量: {total:,}")

# ========== 3. 定义损失函数和优化器 ==========
print("\n" + "=" * 60)
print("Step 3: 损失函数 & 优化器")
print("=" * 60)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
print(f"损失函数: CrossEntropyLoss")
print(f"优化器: Adam (lr=0.001)")

# ========== 4. 训练循环 ==========
print("\n" + "=" * 60)
print("Step 4: 训练")
print("=" * 60)

epochs = 100
for epoch in range(epochs):
    # 设置为训练模式
    model.train()

    # 前向传播
    outputs = model(X_train_t)
    loss = criterion(outputs, y_train_t)

    # 反向传播
    optimizer.zero_grad()  # 清空梯度
    loss.backward()        # 计算梯度
    optimizer.step()       # 更新参数

    # 每 20 轮打印一次
    if (epoch + 1) % 20 == 0:
        model.eval()
        with torch.no_grad():
            _, predicted = torch.max(outputs, 1)
            acc = (predicted == y_train_t).float().mean()
        print(f"  Epoch [{epoch+1:3d}/{epochs}] | Loss: {loss.item():.4f} | Train Acc: {acc:.4f}")

# ========== 5. 测试评估 ==========
print("\n" + "=" * 60)
print("Step 5: 测试评估")
print("=" * 60)

model.eval()
with torch.no_grad():
    test_outputs = model(X_test_t)
    _, predicted = torch.max(test_outputs, 1)
    test_acc = (predicted == y_test_t).float().mean()

    # 每个类别的准确率
    print("\n各类别准确率:")
    for digit in range(10):
        mask = y_test_t == digit
        if mask.sum() > 0:
            class_acc = (predicted[mask] == digit).float().mean()
            print(f"  数字 {digit}: {class_acc:.4f} ({mask.sum()} 个样本)")

    print(f"\n🎯 测试集总体准确率: {test_acc:.4f}")

# ========== 6. 预测单个样本 ==========
print("\n" + "=" * 60)
print("Step 6: 单样本预测")
print("=" * 60)

# 取第一个测试样本
sample = X_test_t[0:1]
true_label = y_test_t[0].item()

with torch.no_grad():
    logits = model(sample)
    probs = torch.softmax(logits, dim=1)
    pred_label = torch.argmax(probs, dim=1).item()
    confidence = probs[0][pred_label].item()

print(f"真实标签: {true_label}")
print(f"预测标签: {pred_label}")
print(f"置信度: {confidence:.4f}")
print(f"概率分布: {probs[0].tolist()}")
print(f"{'✅ 预测正确！' if pred_label == true_label else '❌ 预测错误'}")
