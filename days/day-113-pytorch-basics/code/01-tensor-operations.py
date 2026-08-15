"""
Day 113 - PyTorch 基础：Tensor 创建与运算
==========================================
本文件演示 PyTorch Tensor 的各种创建方式和基本运算操作。

运行前请确保已安装 PyTorch:
    pip install torch
"""

import torch

def main():
    print("=" * 60)
    print("Day 113 - Tensor 基础操作")
    print("=" * 60)

    # =====================================================
    # 1. Tensor 创建
    # =====================================================
    print("\n--- 1. Tensor 创建 ---\n")

    # 从 Python 列表创建
    t1 = torch.tensor([1, 2, 3, 4, 5])
    print(f"从列表创建: {t1}")
    print(f"  形状: {t1.shape}, 数据类型: {t1.dtype}, 维度: {t1.ndim}")

    # 二维 Tensor
    t2 = torch.tensor([[1, 2, 3], [4, 5, 6]])
    print(f"\n二维 Tensor:\n{t2}")
    print(f"  形状: {t2.shape}, 元素总数: {t2.numel()}")

    # 指定数据类型
    t3 = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32)
    t4 = torch.tensor([1, 2, 3], dtype=torch.float64)
    print(f"\nfloat32 类型: {t3}, dtype={t3.dtype}")
    print(f"float64 类型: {t4}, dtype={t4.dtype}")

    # 特殊创建方法
    print("\n--- 特殊创建方法 ---")
    zeros = torch.zeros(2, 3)
    print(f"全零矩阵 (2x3):\n{zeros}")

    ones = torch.ones(3, 2)
    print(f"\n全一矩阵 (3x2):\n{ones}")

    rand_normal = torch.randn(2, 3)  # 标准正态分布
    print(f"\n标准正态随机数 (2x3):\n{rand_normal}")

    rand_uniform = torch.rand(2, 3)  # [0, 1) 均匀分布
    print(f"\n均匀分布随机数 (2x3):\n{rand_uniform}")

    arange = torch.arange(0, 10, 2)
    print(f"\narange(0, 10, 2): {arange}")

    linspace = torch.linspace(0, 1, 5)
    print(f"linspace(0, 1, 5): {linspace}")

    eye = torch.eye(3)
    print(f"\n单位矩阵 (3x3):\n{eye}")

    # 常量 Tensor
    full = torch.full((2, 3), fill_value=3.14)
    print(f"\n常量 Tensor (填充值 3.14):\n{full}")

    # =====================================================
    # 2. Tensor 属性
    # =====================================================
    print("\n--- 2. Tensor 属性 ---\n")

    x = torch.tensor([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    print(f"Tensor:\n{x}")
    print(f"  形状 (shape): {x.shape}")
    print(f"  数据类型 (dtype): {x.dtype}")
    print(f"  设备 (device): {x.device}")
    print(f"  维度数 (ndim): {x.ndim}")
    print(f"  元素总数 (numel): {x.numel()}")
    print(f"  是否需要梯度 (requires_grad): {x.requires_grad}")

    # =====================================================
    # 3. 索引与切片
    # =====================================================
    print("\n--- 3. 索引与切片 ---\n")

    t = torch.arange(12).reshape(3, 4)
    print(f"原始 Tensor (3x4):\n{t}")
    print(f"\n  t[0] = {t[0]}          # 第0行")
    print(f"  t[:, 1] = {t[:, 1]}      # 第1列")
    print(f"  t[1:3] =\n{t[1:3]}    # 第1-2行")
    print(f"  t[0, 1:3] = {t[0, 1:3]}  # 第0行, 第1-2列")
    print(f"  t[t > 5] = {t[t > 5]}  # 条件索引")

    # =====================================================
    # 4. 基本运算
    # =====================================================
    print("\n--- 4. 基本运算 ---\n")

    a = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    b = torch.tensor([[5.0, 6.0], [7.0, 8.0]])

    print(f"Tensor a:\n{a}")
    print(f"\nTensor b:\n{b}")

    # 加法
    print(f"\n逐元素加法: a + b =\n{a + b}")
    print(f"函数加法: torch.add(a, b) =\n{torch.add(a, b)}")

    # 减法
    print(f"\n逐元素减法: a - b =\n{a - b}")

    # 逐元素乘法（注意不是矩阵乘法）
    print(f"\n逐元素乘法: a * b =\n{a * b}")

    # 矩阵乘法
    print(f"\n矩阵乘法: a @ b =\n{a @ b}")
    print(f"函数矩阵乘法: torch.mm(a, b) =\n{torch.mm(a, b)}")
    print(f"torch.matmul(a, b) =\n{torch.matmul(a, b)}")

    # 转置
    print(f"\na 的转置:\n{a.t()}")
    print(f"a.transpose(0,1):\n{a.transpose(0, 1)}")

    # 广播机制
    print("\n--- 广播机制 ---")
    c = torch.tensor([10.0, 20.0])
    print(f"Tensor a:\n{a}")
    print(f"Tensor c: {c}")
    print(f"a + c (广播加法):\n{a + c}")

    # =====================================================
    # 5. 聚合运算
    # =====================================================
    print("\n--- 5. 聚合运算 ---\n")

    t = torch.tensor([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    print(f"Tensor:\n{t}")
    print(f"\n  总和 (sum): {t.sum().item()}")
    print(f"  均值 (mean): {t.mean().item():.4f}")
    print(f"  最大值 (max): {t.max().item()}")
    print(f"  最小值 (min): {t.min().item()}")
    print(f"  标准差 (std): {t.std().item():.4f}")

    # 按维度聚合
    print(f"\n  按行求和 (dim=1): {t.sum(dim=1)}")
    print(f"  按列求和 (dim=0): {t.sum(dim=0)}")
    print(f"  按行求均值 (dim=1): {t.mean(dim=1)}")

    # =====================================================
    # 6. 变形操作
    # =====================================================
    print("\n--- 6. 变形操作 ---\n")

    t = torch.arange(12)
    print(f"原始 (1D): {t}")
    print(f"reshape(3, 4):\n{t.reshape(3, 4)}")
    print(f"reshape(4, 3):\n{t.reshape(4, 3)}")
    print(f"view(2, 6):\n{t.view(2, 6)}")
    print(f"flatten(): {t.flatten()}")

    # 拼接
    print("\n--- 拼接与拆分 ---")
    a = torch.tensor([[1, 2], [3, 4]])
    b = torch.tensor([[5, 6], [7, 8]])
    print(f"a:\n{a}")
    print(f"b:\n{b}")
    print(f"\ntorch.cat([a, b], dim=0) (纵向拼接):\n{torch.cat([a, b], dim=0)}")
    print(f"torch.cat([a, b], dim=1) (横向拼接):\n{torch.cat([a, b], dim=1)}")
    print(f"torch.stack([a, b]) (堆叠):\n{torch.stack([a, b])}")

    # =====================================================
    # 7. 设备相关操作
    # =====================================================
    print("\n--- 7. 设备相关操作 ---\n")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"当前设备: {device}")

    x = torch.rand(3, 3)
    print(f"Tensor 默认设备: {x.device}")

    # 如果有 GPU，演示迁移
    if torch.cuda.is_available():
        x_gpu = x.to(device)
        print(f"迁移到 GPU 后: {x_gpu.device}")
        print(f"GPU Tensor 示例:\n{x_gpu}")
    else:
        print("当前环境无 GPU，跳过 GPU 演示")

    # =====================================================
    # 8. Tensor 与 NumPy 互转
    # =====================================================
    print("\n--- 8. Tensor 与 NumPy 互转 ---\n")

    import numpy as np

    # Tensor -> NumPy
    t = torch.tensor([1.0, 2.0, 3.0])
    arr = t.numpy()
    print(f"Tensor: {t}")
    print(f"NumPy 数组: {arr}")
    print(f"类型: {type(arr)}")

    # NumPy -> Tensor
    arr2 = np.array([4.0, 5.0, 6.0])
    t2 = torch.from_numpy(arr2)
    print(f"\nNumPy 数组: {arr2}")
    print(f"Tensor: {t2}")

    # 共享内存（重要！）
    print("\n⚠️  注意：Tensor 和 NumPy 数组共享内存！")
    arr[0] = 999
    print(f"修改 NumPy 数组后 Tensor: {t}")  # t 也会变！

    # =====================================================
    # 9. 自动广播
    # =====================================================
    print("\n--- 9. 自动广播 (Broadcasting) ---\n")

    a = torch.zeros(3, 4, 5)
    b = torch.zeros(4, 1)
    # a + b 会自动广播 b 到 (3, 4, 5)
    c = a + b
    print(f"a shape: {a.shape}")
    print(f"b shape: {b.shape}")
    print(f"a + b shape: {c.shape} (自动广播)")

    a = torch.zeros(3, 1)
    b = torch.zeros(1, 4)
    c = a + b
    print(f"\na shape: {a.shape}")
    print(f"b shape: {b.shape}")
    print(f"a + b shape: {c.shape} (自动广播)")

    print("\n" + "=" * 60)
    print("Tensor 基础操作演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
