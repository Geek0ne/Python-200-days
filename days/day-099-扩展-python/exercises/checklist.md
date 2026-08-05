# Day 099 — 练习与检查表

## ✅ 今日完成清单

- [ ] 理解 Cython 的三种函数声明（cdef/def/cpdef）
- [ ] 掌握 Cython 类型声明与性能优化原理
- [ ] 了解 Pybind11 的基本用法和类型转换
- [ ] 理解嵌入 Python 到 C++ 的步骤和 GIL 管理
- [ ] 掌握 Python + C++ 混合编程的项目架构
- [ ] 完成至少 3 个练习题

---

## 📝 练习题

### 基础题

**1. Cython 类型声明**

将以下纯 Python 函数改写为 Cython 版本（.pyx 格式），添加类型声明：

```python
def matrix_multiply(a, b):
    n = len(a)
    m = len(b[0])
    k = len(b)
    result = [[0]*m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            for p in range(k):
                result[i][j] += a[i][p] * b[p][j]
    return result
```

要求：
- 所有循环变量声明为 `int`
- 矩阵元素声明为 `double`
- 函数声明为 `cpdef`
- 添加 `@cython.boundscheck(False)` 和 `@cython.wraparound(False)`

---

**2. Pybind11 类暴露**

写一段 pybind11 C++ 代码，暴露以下 Python 类给 Python：

```python
class Stats:
    def __init__(self):
        self.data = []
    
    def add(self, value):
        self.data.append(value)
    
    def mean(self):
        return sum(self.data) / len(self.data)
    
    def std(self):
        m = self.mean()
        return (sum((x - m) ** 2 for x in self.data) / len(self.data)) ** 0.5
```

要求：
- 使用 `std::vector<double>` 存储数据
- 暴露所有方法
- 处理空列表时的除零异常

---

**3. 嵌入 Python**

写一段 C++ 代码，在 C++ 程序中嵌入 Python 解释器，执行以下 Python 代码：

```python
import json
result = {"status": "ok", "data": [1, 2, 3, 4, 5]}
print(json.dumps(result))
```

并从 C++ 中读取打印结果。

---

### 进阶题

**4. 性能对比实验**

分别用纯 Python 和模拟 C++ 方式实现矩阵乘法，比较性能差异。

要求：
- 实现 100×100 矩阵的乘法
- 统计执行时间
- 分析性能差异的原因
- 思考 Cython 可以在哪里进一步优化

---

**5. 混合编程设计**

设计一个完整的项目架构，要求：
- C++ 负责：JSON 解析核心（使用 rapidjson）
- Python 负责：HTTP 服务器和路由
- 使用 pybind11 绑定
- 绘制项目结构图
- 说明构建流程（CMake + pip）
- 讨论如何处理错误和异常传播

---

## 💡 思考题

1. 为什么 Cython 的 `cpdef` 函数比纯 `def` 函数快？底层发生了什么？
2. Pybind11 如何处理 C++ 的移动语义（move semantics）？
3. 在混合编程项目中，如何平衡 C++ 的性能和 Python 的灵活性？
4. 如果 C++ 库使用了自定义内存分配器，暴露给 Python 时会遇到什么问题？
5. 嵌入 Python 时，如何在 C++ 线程中安全地调用 Python 函数？
