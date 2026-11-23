"""
Day 115 - 03 实战：MNIST 手写数字识别
======================================
完整的 MNIST 训练流程：数据加载 → 模型定义 → 训练 → 测试 → 保存
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# ========== 1. 设备配置 ==========
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")

# ========== 2. 数据加载与预处理 ==========
# MNIST 像素值 0~255，Normalize 后变为均值 0、标准差 1
transform = transforms.Compose([
    transforms.ToTensor(),                          # 转为 tensor，范围 [0, 1]
    transforms.Normalize((0.1307,), (0.3081,))      # MNIST 的均值和标准差
])

train_dataset = datasets.MNIST(
    root='./data', train=True, download=True, transform=transform
)
test_dataset = datasets.MNIST(
    root='./data', train=False, transform=transform
)

train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True, num_workers=2)
test_loader = DataLoader(test_dataset, batch_size=1000, shuffle=False)

print(f"训练集: {len(train_dataset)} 样本")
print(f"测试集: {len(test_dataset)} 样本")

# 查看一个样本
sample_x, sample_y = train_dataset[0]
print(f"\n样本形状: {sample_x.shape}")  # (1, 28, 28)
print(f"标签: {sample_y}")

# ========== 3. 定义模型 ==========
class MNISTNet(nn.Module):
    """3 层全连接网络 + Dropout"""
    def __init__(self):
        super().__init__()
        self.flatten = nn.Flatten()  # (1, 28, 28) → (784,)
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
        x = self.flatten(x)
        return self.net(x)

model = MNISTNet().to(device)
print(f"\n模型参数量: {sum(p.numel() for p in model.parameters()):,}")

# ========== 4. 损失函数和优化器 ==========
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# ========== 5. 训练循环 ==========
best_acc = 0
epochs = 10

for epoch in range(epochs):
    # ---- 训练 ----
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

    # ---- 测试 ----
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

    print(f"Epoch [{epoch+1:2d}/{epochs}] "
          f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
          f"Test Loss: {test_loss:.4f} Acc: {test_acc:.4f}")

    # 保存最佳模型
    if test_acc > best_acc:
        best_acc = test_acc
        torch.save(model.state_dict(), 'mnist_best.pth')

print(f"\n🎯 最佳测试准确率: {best_acc:.4f}")

# ========== 6. 加载最佳模型验证 ==========
print("\n--- 加载最佳模型 ---")
loaded_model = MNISTNet().to(device)
loaded_model.load_state_dict(torch.load('mnist_best.pth'))
loaded_model.eval()

with torch.no_grad():
    # 取前 5 个测试样本做预测
    sample_x, sample_y = test_dataset[:5]
    sample_x = sample_x.to(device)
    outputs = loaded_model(sample_x)
    _, predictions = outputs.max(1)

    for i in range(5):
        print(f"  样本 {i+1}: 真实={sample_y[i]}, 预测={predictions[i].item()}", 
              "✅" if sample_y[i] == predictions[i].item() else "❌")
