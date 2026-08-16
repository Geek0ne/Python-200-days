"""
Day 117 - 迁移学习进阶用法
微调（Fine-tuning）：解冻部分层 + 差分学习率

运行方式: python3 02-fine-tuning.py
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision.models as models
import torchvision.transforms as transforms
from torchvision.datasets import CIFAR10
import time


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"🖥️  使用设备: {device}")

    # ============================================================
    # 1. 数据预处理（与基础示例相同）
    # ============================================================
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

    print("📥 加载 CIFAR-10 数据集...")
    train_dataset = CIFAR10(root='./data', train=True,
                            download=True, transform=train_transform)
    test_dataset = CIFAR10(root='./data', train=False,
                           download=True, transform=test_transform)

    train_subset = torch.utils.data.Subset(train_dataset, range(2000))
    test_subset = torch.utils.data.Subset(test_dataset, range(500))

    train_loader = DataLoader(train_subset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_subset, batch_size=32, shuffle=False)

    print(f"✅ 训练集: {len(train_subset)} 张, 测试集: {len(test_subset)} 张")

    # ============================================================
    # 2. 加载预训练模型
    # ============================================================
    print("🔄 加载预训练 ResNet-50...")
    model = models.resnet50(weights='IMAGENET1K_V2')

    # 替换分类头
    model.fc = nn.Linear(model.fc.in_features, 10)
    model = model.to(device)

    # ============================================================
    # 3. 渐进式解冻策略
    # ============================================================
    print("\n📋 渐进式解冻策略:")
    print("  阶段 1: 只训练分类头 (epoch 1-2)")
    print("  阶段 2: 解冻 layer4 + 分类头 (epoch 3-4)")
    print("  阶段 3: 解冻 layer3-4 + 分类头 (epoch 5+)")

    # --- 阶段 1：冻结所有层，只训练分类头 ---
    for param in model.parameters():
        param.requires_grad = False
    for param in model.fc.parameters():
        param.requires_grad = True

    criterion = nn.CrossEntropyLoss()

    # ============================================================
    # 4. 差分学习率（Discriminative Learning Rates）
    # ============================================================
    def get_optimizer_stage1(model):
        """阶段 1: 只有分类头"""
        return optim.Adam(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=0.001
        )

    def get_optimizer_stage2(model):
        """阶段 2: layer4 + 分类头，差分学习率"""
        return optim.Adam([
            {'params': model.layer4.parameters(), 'lr': 1e-4},  # 10x 小于分类头
            {'params': model.fc.parameters(), 'lr': 1e-3},
        ])

    def get_optimizer_stage3(model):
        """阶段 3: layer3-4 + 分类头，三层差分学习率"""
        return optim.Adam([
            {'params': model.layer3.parameters(), 'lr': 1e-5},  # 最小
            {'params': model.layer4.parameters(), 'lr': 1e-4},  # 中等
            {'params': model.fc.parameters(), 'lr': 1e-3},      # 最大
        ])

    # ============================================================
    # 5. 训练函数
    # ============================================================
    def train_one_epoch(model, loader, criterion, optimizer, device):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for inputs, labels in loader:
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
    # 6. 分阶段训练
    # ============================================================
    stages = [
        {"name": "阶段1: 训练分类头", "epochs": 2, "unfreeze": [], "optimizer_fn": get_optimizer_stage1},
        {"name": "阶段2: 解冻 layer4", "epochs": 2, "unfreeze": ["layer4"], "optimizer_fn": get_optimizer_stage2},
        {"name": "阶段3: 解冻 layer3-4", "epochs": 2, "unfreeze": ["layer3", "layer4"], "optimizer_fn": get_optimizer_stage3},
    ]

    global_epoch = 0
    for stage in stages:
        print(f"\n{'='*50}")
        print(f"🔄 {stage['name']}")
        print(f"{'='*50}")

        # 解冻指定层
        for layer_name in stage['unfreeze']:
            layer = getattr(model, layer_name)
            for param in layer.parameters():
                param.requires_grad = True

        # 统计可训练参数
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"  可训练参数: {trainable:,}")

        # 创建优化器
        optimizer = stage['optimizer_fn'](model)

        for epoch in range(stage['epochs']):
            global_epoch += 1
            start_time = time.time()
            train_loss, train_acc = train_one_epoch(
                model, train_loader, criterion, optimizer, device)
            val_loss, val_acc = evaluate(
                model, test_loader, criterion, device)
            elapsed = time.time() - start_time

            print(f"  Epoch {global_epoch} ({elapsed:.1f}s): "
                  f"Train Acc={train_acc:.1f}%, Val Acc={val_acc:.1f}%")

    # ============================================================
    # 7. 总结
    # ============================================================
    print(f"\n{'='*50}")
    print("✅ 微调训练完成！")
    print("\n📊 差分学习率设置:")
    print("  layer3: lr=1e-5 (最深层，变化最小)")
    print("  layer4: lr=1e-4 (中间层)")
    print("  fc:     lr=1e-3 (分类头，变化最大)")
    print("\n💡 关键点:")
    print("  1. 底层特征更通用，学习率要小")
    print("  2. 高层特征更任务相关，学习率要大")
    print("  3. 渐进式解冻可以稳定训练过程")
    print("  4. 避免一步全量微调导致灾难性遗忘")


if __name__ == '__main__':
    main()
