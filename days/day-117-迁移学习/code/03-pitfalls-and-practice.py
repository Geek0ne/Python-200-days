"""
Day 117 - 迁移学习常见陷阱与实战场景
演示过拟合、灾难性遗忘等常见问题及解决方案

运行方式: python3 03-pitfalls-and-practice.py
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision.models as models
import torchvision.transforms as transforms
from torchvision.datasets import CIFAR10
import copy


def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"🖥️  使用设备: {device}")

    # ============================================================
    # 数据准备
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

    train_dataset = CIFAR10(root='./data', train=True,
                            download=True, transform=train_transform)
    test_dataset = CIFAR10(root='./data', train=False,
                           download=True, transform=test_transform)

    # 用非常小的数据集演示过拟合问题
    train_subset = torch.utils.data.Subset(train_dataset, range(200))
    test_subset = torch.utils.data.Subset(test_dataset, range(200))

    train_loader = DataLoader(train_subset, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_subset, batch_size=16, shuffle=False)

    # ============================================================
    # 陷阱 1：灾难性遗忘（Catastrophic Forgetting）
    # ============================================================
    print("=" * 60)
    print("⚠️  陷阱 1: 灾难性遗忘")
    print("=" * 60)
    print("问题：微调时如果学习率太大，会'忘记'预训练模型学到的知识")
    print()

    model_forget = models.resnet50(weights='IMAGENET1K_V2')
    model_forget.fc = nn.Linear(model_forget.fc.in_features, 10)
    model_forget = model_forget.to(device)

    # ❌ 错误做法：大学习率全量微调
    # 这会破坏预训练权重，导致"灾难性遗忘"
    print("❌ 错误做法: lr=0.01 全量微调（会破坏预训练权重）")
    print("  学习率太大 → 梯度更新过猛 → 预训练特征被破坏")
    print()

    # ✅ 正确做法：小学习率 + 冻结底层
    print("✅ 正确做法: lr=0.0001 + 冻结底层（保护预训练特征）")
    print("  1. 冻结 layer1-3（通用特征层）")
    print("  2. 只解冻 layer4 和分类头")
    print("  3. 使用小学习率 (1e-4 ~ 1e-5)")
    print()

    # ============================================================
    # 陷阱 2：数据预处理不一致
    # ============================================================
    print("=" * 60)
    print("⚠️  陷阱 2: 数据预处理不一致")
    print("=" * 60)
    print("问题：训练和推理时使用不同的预处理，导致性能下降")
    print()

    # 正确的预处理流程
    correct_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],  # ImageNet 均值
                             [0.229, 0.224, 0.225])   # ImageNet 标准差
    ])

    print("✅ 正确的预处理:")
    print("  1. Resize → 256")
    print("  2. CenterCrop → 224")
    print("  3. ToTensor → [0, 1]")
    print("  4. Normalize → ImageNet 均值和标准差")
    print()
    print("❌ 常见错误:")
    print("  - 用 CIFAR-10 自己的均值/标准差（应该用 ImageNet 的）")
    print("  - 训练时 resize 到 224，推理时 resize 到 299")
    print("  - 遗漏归一化步骤")
    print()

    # ============================================================
    # 陷阱 3：不保存预处理参数
    # ============================================================
    print("=" * 60)
    print("⚠️  陷阱 3: 不保存预处理参数")
    print("=" * 60)
    print("问题：部署时忘记保存预处理参数，导致推理结果错误")
    print()

    # 推荐：将预处理参数和模型一起保存
    class ModelWithPreprocessing(nn.Module):
        """封装模型 + 预处理，确保一致性"""
        def __init__(self, model, mean, std):
            super().__init__()
            self.model = model
            # 注册为 buffer（不参与训练，但会随模型保存）
            self.register_buffer('mean', torch.tensor(mean).view(1, 3, 1, 1))
            self.register_buffer('std', torch.tensor(std).view(1, 3, 1, 1))

        def forward(self, x):
            # 自动归一化
            x = (x - self.mean) / self.std
            return self.model(x)

    # 使用示例
    base_model = models.resnet50(weights='IMAGENET1K_V2')
    base_model.fc = nn.Linear(base_model.fc.in_features, 10)

    wrapped_model = ModelWithPreprocessing(
        base_model,
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )

    print("✅ 推荐做法: 将预处理封装到模型中")
    print("  - 预处理参数注册为 buffer，随模型一起保存")
    print("  - 推理时自动处理，不会遗漏")
    print("  - 使用 torch.save(wrapped_model, 'model.pt') 即可")
    print()

    # ============================================================
    # 陷阱 4：过拟合小数据集
    # ============================================================
    print("=" * 60)
    print("⚠️  陷阱 4: 过拟合小数据集")
    print("=" * 60)
    print("问题：数据量太小时，微调容易过拟合")
    print()

    # 解决方案 1: 数据增强
    augmentation_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])

    print("✅ 解决方案:")
    print("  1. 数据增强（Data Augmentation）")
    print("     - RandomHorizontalFlip, RandomRotation, ColorJitter")
    print("     - 可以增加数据多样性")
    print()
    print("  2. 正则化")
    print("     - Dropout: 在分类头添加 Dropout(0.5)")
    print("     - Weight Decay: optimizer 中设置 weight_decay=1e-4")
    print()
    print("  3. 早停（Early Stopping）")
    print("     - 监控验证集 loss，不再下降时停止训练")
    print()

    # ============================================================
    # 实战场景：完整的迁移学习 pipeline
    # ============================================================
    print("=" * 60)
    print("🎯 实战场景: 完整的迁移学习 Pipeline")
    print("=" * 60)
    print()

    # Step 1: 加载模型
    model = models.resnet50(weights='IMAGENET1K_V2')

    # Step 2: 修改分类头
    model.fc = nn.Sequential(
        nn.Dropout(0.5),  # 正则化
        nn.Linear(model.fc.in_features, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, 10)
    )
    model = model.to(device)

    # Step 3: 冻结 + 分阶段解冻
    for param in model.parameters():
        param.requires_grad = False

    # Step 4: 只训练分类头
    trainable = filter(lambda p: p.requires_grad, model.parameters())
    optimizer = optim.Adam(trainable, lr=1e-3, weight_decay=1e-4)

    # Step 5: 训练（省略具体循环）
    print("Pipeline 步骤:")
    print("  1. 加载预训练模型")
    print("  2. 修改分类头（加 Dropout）")
    print("  3. 冻结卷积层")
    print("  4. 训练分类头（lr=1e-3）")
    print("  5. 解冻 layer4（lr=1e-4）")
    print("  6. 解冻 layer3-4（lr=1e-5）")
    print("  7. 保存完整模型（含预处理）")
    print()

    # ============================================================
    # 保存模型示例
    # ============================================================
    print("=" * 60)
    print("💾 保存模型示例")
    print("=" * 60)

    # 方式 1: 保存整个模型
    torch.save(model, 'model_full.pt')
    print("  torch.save(model, 'model_full.pt')  # 保存整个模型")

    # 方式 2: 保存 state_dict（推荐）
    torch.save(model.state_dict(), 'model_state.pt')
    print("  torch.save(model.state_dict(), 'model_state.pt')  # 推荐")

    # 方式 3: 保存 checkpoint（含训练状态）
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'epoch': 0,
        'loss': 0.0,
        'config': {
            'num_classes': 10,
            'backbone': 'resnet50',
            'dropout': 0.5,
        }
    }
    torch.save(checkpoint, 'checkpoint.pt')
    print("  torch.save(checkpoint, 'checkpoint.pt')  # 完整 checkpoint")
    print()

    print("✅ 全部陷阱与实战场景演示完成！")
    print("\n📝 总结:")
    print("  1. 灾难性遗忘 → 小学习率 + 冻结底层")
    print("  2. 预处理不一致 → 统一 ImageNet 预处理")
    print("  3. 忘记保存参数 → 封装到模型中")
    print("  4. 过拟合小数据 → 数据增强 + 正则化 + 早停")


if __name__ == '__main__':
    main()
