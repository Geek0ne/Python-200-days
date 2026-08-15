"""
Day 113 - PyTorch 基础：手动实现线性回归
==========================================
使用 PyTorch Autograd 从零开始实现线性回归，不使用任何高级 API。

运行前请确保已安装 PyTorch:
    pip install torch
"""

import torch
import matplotlib.pyplot as plt


def main():
    print("=" * 60)
    print("Day 113 - 用 Autograd 手动实现线性回归")
    print("=" * 60)

    # =====================================================
    # 1. 生成模拟数据
    # =====================================================
    print("\n--- 1. 生成模拟数据 ---\n")

    torch.manual_seed(42)

    # 生成 100 个样本
    n_samples = 100
    x = 2 * torch.rand(n_samples, 1)  # 特征: [0, 2) 的均匀分布
    # 真实关系: y = 3x + 1 + noise
    y = 3.0 * x + 1.0 + 0.1 * torch.randn(n_samples, 1)

    print(f"数据集大小: {n_samples}")
    print(f"x 范围: [{x.min():.4f}, {x.max():.4f}]")
    print(f"y 范围: [{y.min():.4f}, {y.max():.4f}]")
    print(f"真实关系: y = 3.0x + 1.0")

    # =====================================================
    # 2. 初始化模型参数
    # =====================================================
    print("\n--- 2. 初始化模型参数 ---\n")

    # 随机初始化权重，偏置初始化为 0
    w = torch.randn(1, requires_grad=True)  # 权重
    b = torch.zeros(1, requires_grad=True)  # 偏置

    print(f"初始 w: {w.item():.4f} (真实值: 3.0)")
    print(f"初始 b: {b.item():.4f} (真实值: 1.0)")

    # =====================================================
    # 3. 定义损失函数和超参数
    # =====================================================
    print("\n--- 3. 定义损失函数和超参数 ---\n")

    learning_rate = 0.1
    num_epochs = 200
    print(f"学习率: {learning_rate}")
    print(f"训练轮数: {num_epochs}")

    # =====================================================
    # 4. 训练循环（手动实现）
    # =====================================================
    print("\n--- 4. 训练循环 ---\n")

    losses = []
    w_history = []
    b_history = []

    for epoch in range(num_epochs):
        # --- 前向传播 ---
        y_pred = x * w + b  # 线性模型: ŷ = wx + b

        # --- 计算损失 (MSE) ---
        loss = ((y_pred - y) ** 2).mean()

        # --- 反向传播 ---
        loss.backward()  # 自动计算 dw 和 db

        # --- 记录历史 ---
        losses.append(loss.item())
        w_history.append(w.item())
        b_history.append(b.item())

        # --- 参数更新 ---
        with torch.no_grad():  # 更新参数时不需要梯度跟踪
            w -= learning_rate * w.grad
            b -= learning_rate * b.grad

        # --- 梯度清零 ---
        w.grad.zero_()
        b.grad.zero_()

        # --- 打印进度 ---
        if (epoch + 1) % 40 == 0:
            print(f"Epoch [{epoch+1:3d}/{num_epochs}] | "
                  f"Loss: {loss.item():.6f} | "
                  f"w: {w.item():.4f} | b: {b.item():.4f}")

    # =====================================================
    # 5. 最终结果
    # =====================================================
    print("\n--- 5. 最终结果 ---\n")

    print(f"学到的模型: y = {w.item():.4f}x + {b.item():.4f}")
    print(f"真实模型:   y = 3.0000x + 1.0000")

    w_error = abs(w.item() - 3.0)
    b_error = abs(b.item() - 1.0)
    print(f"\n权重误差: {w_error:.4f}")
    print(f"偏置误差: {b_error:.4f}")

    # =====================================================
    # 6. 可视化
    # =====================================================
    print("\n--- 6. 生成可视化图表 ---\n")

    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # 图1: 数据与拟合直线
        ax1 = axes[0, 0]
        ax1.scatter(x.numpy(), y.numpy(), alpha=0.5, label="数据点", s=20)
        x_line = torch.linspace(0, 2, 100).unsqueeze(1)
        y_line = w.item() * x_line + b.item()
        y_true = 3.0 * x_line + 1.0
        ax1.plot(x_line.numpy(), y_line.numpy(), 'r-', linewidth=2, label=f"学到: y={w.item():.2f}x+{b.item():.2f}")
        ax1.plot(x_line.numpy(), y_true.numpy(), 'g--', linewidth=2, label="真实: y=3.0x+1.0")
        ax1.set_xlabel("x")
        ax1.set_ylabel("y")
        ax1.set_title("线性回归拟合结果")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 图2: 损失曲线
        ax2 = axes[0, 1]
        ax2.plot(losses, 'b-', linewidth=1)
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("MSE Loss")
        ax2.set_title("训练损失曲线")
        ax2.grid(True, alpha=0.3)

        # 图3: 权重变化
        ax3 = axes[1, 0]
        ax3.plot(w_history, 'r-', linewidth=1, label="w")
        ax3.axhline(y=3.0, color='g', linestyle='--', label="真实 w=3.0")
        ax3.set_xlabel("Epoch")
        ax3.set_ylabel("值")
        ax3.set_title("权重 w 的变化过程")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 图4: 偏置变化
        ax4 = axes[1, 1]
        ax4.plot(b_history, 'b-', linewidth=1, label="b")
        ax4.axhline(y=1.0, color='g', linestyle='--', label="真实 b=1.0")
        ax4.set_xlabel("Epoch")
        ax4.set_ylabel("值")
        ax4.set_title("偏置 b 的变化过程")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("linear_regression_result.png", dpi=150)
        print("图表已保存: linear_regression_result.png")
        plt.close()

    except ImportError:
        print("matplotlib 未安装，跳过可视化")

    # =====================================================
    # 7. 用学到的模型做预测
    # =====================================================
    print("\n--- 7. 模型预测 ---\n")

    test_x = torch.tensor([[0.0], [0.5], [1.0], [1.5], [2.0]])
    with torch.no_grad():
        test_y = test_x * w + b

    print("预测结果:")
    print(f"{'x':>6} | {'预测 y':>10} | {'真实 y':>10}")
    print("-" * 35)
    for i in range(len(test_x)):
        true_y = 3.0 * test_x[i].item() + 1.0
        print(f"{test_x[i].item():6.2f} | {test_y[i].item():10.4f} | {true_y:10.4f}")

    # =====================================================
    # 8. 批量梯度下降版本对比
    # =====================================================
    print("\n--- 8. 批量 vs 小批量 vs 随机梯度下降对比 ---\n")

    def train_gd(x, y, lr=0.1, epochs=200, batch_size=None):
        """通用训练函数"""
        w = torch.randn(1, requires_grad=True)
        b = torch.zeros(1, requires_grad=True)
        losses = []

        n = len(x)
        for epoch in range(epochs):
            if batch_size is None or batch_size >= n:
                # 批量梯度下降
                y_pred = x * w + b
                loss = ((y_pred - y) ** 2).mean()
            else:
                # 小批量梯度下降
                indices = torch.randperm(n)[:batch_size]
                x_batch = x[indices]
                y_batch = y[indices]
                y_pred = x_batch * w + b
                loss = ((y_pred - y_batch) ** 2).mean()

            loss.backward()
            losses.append(loss.item())

            with torch.no_grad():
                w -= lr * w.grad
                b -= lr * b.grad
            w.grad.zero_()
            b.grad.zero_()

        return w.item(), b.item(), losses

    # 批量梯度下降
    w_gd, b_gd, losses_gd = train_gd(x, y, lr=0.1, epochs=200)
    print(f"批量 GD: w={w_gd:.4f}, b={b_gd:.4f}, final_loss={losses_gd[-1]:.6f}")

    # 小批量梯度下降 (batch_size=32)
    w_sgd, b_sgd, losses_sgd = train_gd(x, y, lr=0.1, epochs=200, batch_size=32)
    print(f"小批量 GD: w={w_sgd:.4f}, b={b_sgd:.4f}, final_loss={losses_sgd[-1]:.6f}")

    # 随机梯度下降 (batch_size=1)
    w_sgd1, b_sgd1, losses_sgd1 = train_gd(x, y, lr=0.01, epochs=200, batch_size=1)
    print(f"随机 GD: w={w_sgd1:.4f}, b={b_sgd1:.4f}, final_loss={losses_sgd1[-1]:.6f}")

    print("\n" + "=" * 60)
    print("线性回归手动实现演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
