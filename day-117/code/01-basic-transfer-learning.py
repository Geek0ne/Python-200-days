"""
Day 117 - 迁移学习基础用法
使用 ResNet-50 进行特征提取（Feature Extraction）

运行方式: python3 01-basic-transfer-learning.py
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision.models as models
import torchvision.transforms as transforms
from torchvision.datasets import CIFAR10
import time
import os


def main():
    # ============================================================
    # 1. 设备配置
    # ============================================================
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"🖥️  使用设备: {device}")

    # ============================================================
    # 2. 数据预处理
    # ============================================================
    # 注意：预训练模型在 ImageNet 上训练时的预处理参数
    # mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    # 但 CIFAR-10 图像尺寸只有 32×32，需要 resize 到 224×224

    train_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])

    test_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])

    # 加载 CIFAR-10 数据集（自动下载）
    print("📥 加载 CIFAR-10 数据集...")
    train_dataset = CIFAR10(root='./data', train=True,
                            download=True, transform=train_transform)
    test_dataset = CIFAR10(root='./data', train=False,
                           download=True, transform=test_transform)

    # 取小子集演示（加速训练）
    train_subset = torch.utils.data.Subset(train_dataset, range(2000))
    test_subset = torch.utils.data.Subset(test_dataset, range(500))

    train_loader = DataLoader(train_subset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_subset, batch_size=32, shuffle=False)

    print(f"✅ 训练集: {len(train_subset)} 张, 测试集: {len(test_subset)} 张")

    # ============================================================
    # 3. 加载预训练模型（特征提取模式）
    # ============================================================
    print("🔄 加载预训练 ResNet-50...")
    model = models.resnet50(weights='IMAGENET1K_V2')

    # 冻结所有参数（特征提取模式）
    for param in model.parameters():
        param.requires_grad = False

    # 替换最后的全连接层（适配 CIFAR-10 的 10 个类别）
    num_features = model.fc.in_features  # 2048
    model.fc = nn.Linear(num_features, 10)

    model = model.to(device)
    print(f"✅ 模型已修改: 最后一层 {num_features} → 10")

    # ============================================================
    # 4. 统计参数量
    # ============================================================
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"📊 总参数量: {total_params:,}")
    print(f"📊 可训练参数: {trainable_params:,} ({100 * trainable_params / total_params:.1f}%)")

    # ============================================================
    # 5. 定义损失函数和优化器
    # ============================================================
    criterion = nn.CrossEntropyLoss()
    # 只优化可训练参数（冻结层不会参与梯度更新）
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=0.001
    )

    # ============================================================
    # 6. 训练函数
    # ============================================================
    def train_one_epoch(model, loader, criterion, optimizer, device):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (inputs, labels) in enumerate(loader):
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

            if (batch_idx + 1) % 20 == 0:
                print(f"  Batch {batch_idx + 1}/{len(loader)}: "
                      f"Loss={running_loss / (batch_idx + 1):.4f}, "
                      f"Acc={100. * correct / total:.1f}%")

        return running_loss / len(loader), 100. * correct / total

    def evaluate(model, loader, criterion, device):
        model.eval()
        running_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for inputs, labels in loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)

                running_loss += loss.item()
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()

        return running_loss / len(loader), 100. * correct / total

    # ============================================================
    # 7. 开始训练（只训练分类头，冻结卷积层）
    # ============================================================
    num_epochs = 3
    print(f"\n🚀 开始训练（特征提取模式）: {num_epochs} epochs")
    print("=" * 50)

    for epoch in range(num_epochs):
        start_time = time.time()
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = evaluate(
            model, test_loader, criterion, device)
        elapsed = time.time() - start_time

        print(f"Epoch {epoch + 1}/{num_epochs} ({elapsed:.1f}s):")
        print(f"  Train Loss={train_loss:.4f}, Acc={train_acc:.1f}%")
        print(f"  Val   Loss={val_loss:.4f}, Acc={val_acc:.1f}%")
        print()

    print("✅ 特征提取模式训练完成！")
    print("\n💡 注意：只训练了分类头（约 2 万个参数），卷积层全部冻结")
    print("   这就是迁移学习的威力：用很少的可训练参数，复用强大的预训练特征")


if __name__ == '__main__':
    main()
