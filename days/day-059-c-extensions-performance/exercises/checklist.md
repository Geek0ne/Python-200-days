# Day 059 — C 扩展与性能优化 · 完成清单

## ✅ 学习检查表

- [ ] 理解 Python 慢的根本原因（GIL、动态类型、解释执行）
- [ ] 掌握 Cython 的类型声明和编译流程
- [ ] 掌握 ctypes 调用 C 标准库和自定义 C 函数
- [ ] 掌握 CFFI 的 ABI 模式和 API 模式
- [ ] 掌握 Numba 的 @jit 装饰器和 `parallel=True`
- [ ] 能根据场景选择合适的优化方案
- [ ] 运行过所有代码示例并观察性能差异

---

## 📝 基础练习题

### 练习 1：Numba 加速矩阵逐元素运算

用 Numba 加速以下函数，使其比纯 Python 快 10 倍以上：

```python
def matrix_relu(matrix):
    """对矩阵执行 ReLU 激活函数"""
    rows, cols = len(matrix), len(matrix[0])
    result = [[0.0] * cols for _ in range(rows)]
    for i in range(rows):
        for j in range(cols):
            result[i][j] = max(0, matrix[i][j])
    return result
```

要求：
- 使用 `@jit(nopython=True)` 装饰器
- 编写纯 Python 版本和 Numba 版本的性能对比
- 测试 1000×1000 矩阵

### 练习 2：ctypes 调用 math 库

用 ctypes 调用 C 标准库中的以下函数：
- `sqrt(double)` — 平方根
- `pow(double, double)` — 幂运算
- `log(double)` — 自然对数
- `sin(double)` — 正弦

编写测试代码验证每个函数的正确性。

### 练习 3：Numba 自动并行化

将以下串行求和改为并行版本，对比性能：

```python
import numpy as np
from numba import jit

@jit(nopython=True)
def serial_sum(arr):
    total = 0.0
    for i in range(len(arr)):
        total += arr[i]
    return total
```

提示：使用 `parallel=True` 和 `prange` 替代 `range`。

---

## 🚀 进阶挑战题

### 挑战 1：Cython 实现高性能排序

编写一个 Cython 函数实现快速排序（quicksort），要求：
- 使用 `cdef` 声明 C 级变量
- 对 100 万元素排序耗时 < 0.5 秒
- 与 Python 内置 `sorted()` 和 NumPy `np.sort()` 对比

### 挑战 2：ctypes 调用 BLAS

用 ctypes 加载系统 BLAS 库（`libblas.so`），调用 `dgemm` 函数执行矩阵乘法：
- `dgemm(transA, transB, M, N, K, alpha, A, lda, B, ldb, beta, C, ldc)`
- 计算 C = alpha * A × B + beta * C

### 挑战 3：性能分析报告

对以下场景进行性能分析，生成报告：
1. 创建 100 万随机浮点数的数组
2. 分别用纯 Python、NumPy、Numba、ctypes 计算平方和
3. 记录每种方式的耗时
4. 绘制柱状图对比（可以用 matplotlib）

要求报告包含：
- 各方案的执行时间
- 加速比表格
- 选型建议

---

## 💡 思考题答案提示

1. **图像处理选 Numba**：因为图像处理各步骤已经是 NumPy 数组操作，Numba 可以对单个函数做 JIT，且支持并行化。

2. **ctypes 调用开销**：ctypes 每次调用需要 Python 层面的类型转换和 FFI 调用，而 Cython 编译后直接是 C 函数调用。

3. **大文件处理**：都不太适合。应该用 `mmap` 或分块读取，ctypes/Cython 对 I密集型任务帮助有限。

4. **Numba parallel vs ThreadPool**：Numba 并行在编译时确定，直接操作内存无 GIL；ThreadPool 受 GIL 限制，适合 I/O 密集。

5. **Cython 余弦相似度**：使用 `cimport` 导入 NumPy C API，用 typed memoryview 操作数组，循环用 `nogil` 释放 GIL。
