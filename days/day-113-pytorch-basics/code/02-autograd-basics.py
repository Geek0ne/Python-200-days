"""
Day 113 - PyTorch 基础：Autograd 自动求导
==========================================
本文件演示 PyTorch Autograd 自动微分引擎的工作原理和使用方法。

运行前请确保已安装 PyTorch:
    pip install torch
"""

import torch


def main():
    print("=" * 60)
    print("Day 113 - Autograd 自动求导基础")
    print("=" * 60)

    # =====================================================
    # 1. 基础：requires_grad 与 backward
    # =====================================================
    print("\n--- 1. 基础梯度计算 ---\n")

    # 创建需要梯度的 Tensor
    x = torch.tensor(3.0, requires_grad=True)
    print(f"x = {x}")
    print(f"requires_grad = {x.requires_grad}")

    # 前向传播
    y = x ** 2  # y = x^2
    print(f"y = x^2 = {y}")
    print(f"y.grad_fn = {y.grad_fn}")  # 记录了创建 y 的操作

    # 反向传播
    y.backward()
    print(f"dy/dx = 2x = {x.grad}")  # dy/dx = 2x = 6.0

    # =====================================================
    # 2. 多变量梯度
    # =====================================================
    print("\n--- 2. 多变量梯度 ---\n")

    x = torch.tensor([2.0, 3.0], requires_grad=True)
    print(f"x = {x}")

    # y = x1^2 + x2^3
    y = x[0] ** 2 + x[1] ** 3
    print(f"y = x1^2 + x2^3 = {y.item():.1f}")

    y.backward()
    print(f"dy/dx1 = 2*x1 = {x.grad[0].item():.1f} (应为 4.0)")
    print(f"dy/dx2 = 3*x2^2 = {x.grad[1].item():.1f} (应为 27.0)")

    # =====================================================
    # 3. 计算图与 grad_fn
    # =====================================================
    print("\n--- 3. 计算图与 grad_fn ---\n")

    x = torch.tensor(2.0, requires_grad=True)
    print(f"x: {x}, grad_fn: {x.grad_fn}")  # None，因为 x 是叶子节点

    y = x + 3
    print(f"y = x + 3: {y.item()}, grad_fn: {y.grad_fn}")

    z = y * 2
    print(f"z = y * 2: {z.item()}, grad_fn: {z.grad_fn}")

    w = z ** 2
    print(f"w = z^2: {w.item()}, grad_fn: {w.grad_fn}")

    # 反向传播
    w.backward()
    print(f"\n计算图: x → (+3) → y → (*2) → z → (^2) → w")
    print(f"dw/dx = 2*(z)*2 = {x.grad.item():.1f} (应为 32.0)")
    print(f"验证: 2 * (2*2 + 3) * 2 * 2 = {2 * (2*2 + 3) * 2 * 2}")

    # =====================================================
    # 4. 梯度累积
    # =====================================================
    print("\n--- 4. 梯度累积问题与清零 ---\n")

    x = torch.tensor(2.0, requires_grad=True)

    # 第一次反向传播
    y1 = x ** 2
    y1.backward()
    print(f"第一次: x.grad = {x.grad.item()}")  # 4.0

    # 第二次反向传播（梯度会累积！）
    y2 = x ** 3
    y2.backward()
    print(f"第二次（累积后）: x.grad = {x.grad.item()}")  # 4.0 + 12.0 = 16.0

    # 清零后重新计算
    x.grad.zero_()
    y3 = x ** 2
    y3.backward()
    print(f"清零后第三次: x.grad = {x.grad.item()}")  # 4.0

    # =====================================================
    # 5. retain_graph
    # =====================================================
    print("\n--- 5. retain_graph 参数 ---\n")

    x = torch.tensor(2.0, requires_grad=True)

    # 如果需要多次反向传播，需要 retain_graph=True
    y = x ** 2
    y.backward(retain_graph=True)  # 保留计算图
    print(f"第一次反向传播: {x.grad.item()}")

    y.backward()  # 再次反向传播
    print(f"第二次反向传播（累积）: {x.grad.item()}")

    # =====================================================
    # 6. torch.no_grad() 上下文管理器
    # =====================================================
    print("\n--- 6. torch.no_grad() ---\n")

    x = torch.tensor(2.0, requires_grad=True)
    print(f"x.requires_grad: {x.requires_grad}")

    # 默认情况下，所有操作都会被跟踪
    y = x * 2
    print(f"y.requires_grad: {y.requires_grad}")

    # 使用 no_grad 禁用跟踪
    with torch.no_grad():
        y = x * 2
        print(f"no_grad 内: y.requires_grad: {y.requires_grad}")
        print(f"no_grad 内: y.grad_fn: {y.grad_fn}")

    # no_grad 的用途：
    # 1. 推理时不需要梯度，节省内存
    # 2. 更新参数时不应该被记录到计算图中
    # 3. 某些操作不需要梯度
    print("\n用途：推理、参数更新、性能优化")

    # =====================================================
    # 7. detach() 方法
    # =====================================================
    print("\n--- 7. detach() 方法 ---\n")

    x = torch.tensor(2.0, requires_grad=True)
    y = x ** 2

    # detach 创建一个共享数据但不追踪梯度的新 Tensor
    z = y.detach()
    print(f"y: {y.item()}, requires_grad: {y.requires_grad}, grad_fn: {y.grad_fn}")
    print(f"z: {z.item()}, requires_grad: {z.requires_grad}, grad_fn: {z.grad_fn}")

    # z 和 y 共享底层数据
    y.data.fill_(100)
    print(f"\ny 修改为 100 后 z = {z.item()}")  # z 也变了，因为共享数据

    # =====================================================
    # 8. 梯度计算实例：复杂函数
    # =====================================================
    print("\n--- 8. 复杂函数梯度计算 ---\n")

    # 计算 f(x, y) = (x^2 + y^2) * sin(x*y) 的梯度
    x = torch.tensor(1.0, requires_grad=True)
    y = torch.tensor(2.0, requires_grad=True)

    f = (x ** 2 + y ** 2) * torch.sin(x * y)
    print(f"f(x, y) = (x² + y²) * sin(x*y)")
    print(f"f(1, 2) = {f.item():.4f}")

    f.backward()
    print(f"\n∂f/∂x = {x.grad.item():.4f}")
    print(f"∂f/∂y = {y.grad.item():.4f}")

    # 手动验证（数值梯度）
    eps = 1e-5
    x_val, y_val = 1.0, 2.0
    fx = ((x_val + eps) ** 2 + y_val ** 2) * torch.tensor((x_val + eps) * y_val).sin()
    fy = (x_val ** 2 + y_val ** 2) * torch.tensor(x_val * (y_val + eps)).sin()
    f0 = (x_val ** 2 + y_val ** 2) * torch.tensor(x_val * y_val).sin()
    numerical_df_dx = (fx - f0) / eps
    numerical_df_dy = (fy - f0) / eps
    print(f"\n数值验证: ∂f/∂x ≈ {numerical_df_dx.item():.4f}")
    print(f"数值验证: ∂f/∂y ≈ {numerical_df_dy.item():.4f}")

    # =====================================================
    # 9. 梯度裁剪
    # =====================================================
    print("\n--- 9. 梯度裁剪 ---\n")

    x = torch.tensor([10.0, 20.0], requires_grad=True)
    y = (x ** 2).sum()
    y.backward()

    print(f"原始梯度: {x.grad}")

    # 按范数裁剪
    torch.nn.utils.clip_grad_norm_(x, max_norm=5.0)
    print(f"裁剪后梯度 (max_norm=5): {x.grad}")
    print(f"梯度范数: {x.grad.norm().item():.4f}")

    # =====================================================
    # 10. 训练循环中的标准模式
    # =====================================================
    print("\n--- 10. 标准训练循环模式 ---\n")

    # 模拟一个简单的训练循环
    w = torch.randn(1, requires_grad=True)

    for i in range(3):
        # 前向传播
        x = torch.tensor(1.0)
        y_pred = w * x
        loss = (y_pred - 1.0) ** 2

        # 反向传播前清零梯度
        if w.grad is not None:
            w.grad.zero_()

        # 反向传播
        loss.backward()

        # 更新参数
        with torch.no_grad():
            w -= 0.1 * w.grad

        print(f"Step {i+1}: loss={loss.item():.4f}, w={w.item():.4f}")

    print(f"\n最终 w ≈ 1.0: {w.item():.4f}")

    print("\n" + "=" * 60)
    print("Autograd 自动求导演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
