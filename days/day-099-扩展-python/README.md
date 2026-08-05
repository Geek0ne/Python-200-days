# Day 099 — 扩展 Python：Cython、Pybind11 与 C++ 混合编程

## 📌 今日目标

Python 虽然开发效率高，但在某些场景（数值计算、系统调用、高性能库）中，C/C++ 的执行速度远超 Python。今天我们将学习如何**将 Python 与 C/C++ 结合**，掌握三种主流扩展方式。

---

## 一、Cython 深入

### 1.1 什么是 Cython？

Cython 是一个**将 Python 代码编译为 C 代码**的编译器。它在 Python 语法基础上扩展了类型声明，生成的 C 代码可以直接编译为 CPython 扩展模块。

**核心价值**：
- 保留 Python 语法的简洁性
- 通过类型声明获得 C 级别性能
- 无缝调用 C/C++ 库
- 生成的 `.so`/`.pyd` 文件可直接被 Python import

### 1.2 Cython 的类型系统

```cython
# cdef: 声明 C 级别变量（不暴露给 Python）
cdef int x = 10
cdef double result = 0.0

# def: 声明 Python 可调用函数
def my_function(int a, int b):
    return a + b

# cpdef: 同时生成 C 和 Python 版本（性能最佳选择）
cpdef int fast_add(int a, int b):
    return a + b
```

### 1.3 .pyx 文件结构

```
my_module/
├── my_module.pyx      # Cython 源码
├── setup.py           # 构建配置
└── my_module.c        # 生成的 C 代码（可选查看）
```

### 1.4 性能对比：纯 Python vs Cython

```python
# 纯 Python
def fibonacci_py(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```

```cython
# Cython 版本
cpdef long long fibonacci_cy(int n):
    cdef long long a = 0, b = 1
    cdef int i
    for i in range(n):
        a, b = b, a + b
    return a
```

典型加速比：**10x ~ 100x**（取决于计算密集程度）

---

## 二、Pybind11

### 2.1 什么是 Pybind11？

Pybind11 是一个**轻量级头文件库**，用纯 C++ 代码暴露 C++ 函数/类给 Python。它的 API 设计灵感来自 Boost.Python，但无需 Boost 依赖。

**核心优势**：
- 纯头文件，无需预编译库
- 自动类型转换
- 支持 STL 容器、智能指针、NumPy 数组
- 支持 C++11/14/17 特性

### 2.2 基本用法

```cpp
#include <pybind11/pybind11.h>

namespace py = pybind11;

// 暴露一个普通函数
int add(int a, int b) {
    return a + b;
}

PYBIND11_MODULE(example, m) {
    m.doc() = "example module";   // 模块文档
    m.def("add", &add, "A function that adds two numbers");
}
```

### 2.3 暴露类

```cpp
#include <pybind11/pybind11.h>

class Calculator {
public:
    Calculator() : value(0) {}
    void add(int x) { value += x; }
    int get_value() const { return value; }
private:
    int value;
};

PYBIND11_MODULE(calculator, m) {
    py::class_<Calculator>(m, "Calculator")
        .def(py::init<>())
        .def("add", &Calculator::add)
        .def("get_value", &Calculator::get_value);
}
```

### 2.4 NumPy 集成

```cpp
#include <pybind11/numpy.h>

namespace py = pybind11;

py::array_t<double> multiply_array(py::array_t<double> input, double factor) {
    auto buf = input.mutable_unchecked<1>();
    auto result = py::array_t<double>(buf.shape(0));
    auto res_buf = result.mutable_unchecked<1>();

    for (py::ssize_t i = 0; i < buf.shape(0); i++) {
        res_buf(i) = buf(i) * factor;
    }
    return result;
}
```

---

## 三、嵌入 Python 到 C++

### 3.1 为什么要嵌入 Python？

有时候你需要在 **C++ 应用中调用 Python 代码**，比如：
- 利用 Python 生态做脚本/插件系统
- C++ 程序调用 Python 库（如 ML 模型）
- 测试框架中嵌入 Python 执行

### 3.2 嵌入步骤

```cpp
#include <Python.h>

int main() {
    Py_Initialize();                    // 初始化 Python 解释器

    PyRun_SimpleString("print('Hello from embedded Python!')");

    // 调用 Python 函数
    PyObject *module = PyImport_ImportModule("math");
    PyObject *func = PyObject_GetAttrString(module, "sqrt");
    PyObject *args = Py_BuildValue("(d)", 64.0);
    PyObject *result = PyObject_CallObject(func, args);

    double value = PyFloat_AsDouble(result);
    printf("sqrt(64) = %f\n", value);

    Py_DECREF(result);
    Py_DECREF(args);
    Py_DECREF(func);
    Py_DECREF(module);

    Py_Finalize();                     // 关闭 Python 解释器
    return 0;
}
```

### 3.3 关键注意事项

- **GIL 管理**：嵌入时需手动获取/释放 GIL
- **引用计数**：所有 PyObject* 都需要手动管理
- **Python 版本匹配**：编译和运行时的 Python 版本必须一致
- **错误处理**：检查 Python 调用返回值是否为 NULL

---

## 四、Python + C++ 混合编程实战

### 4.1 项目结构

```
hybrid_project/
├── CMakeLists.txt          # 构建配置
├── src/
│   ├── core.cpp            # C++ 核心计算
│   └── bindings.cpp        # pybind11 绑定
├── python/
│   ├── __init__.py
│   └── wrapper.py          # Python 包装层
└── tests/
    └── test_core.py        # 测试
```

### 4.2 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.15)
project(hybrid_project)

find_package(pybind11 REQUIRED)

pybind11_add_module(core src/core.cpp src/bindings.cpp)
target_compile_options(core PRIVATE -O3)
```

### 4.3 构建与使用

```bash
pip install pybind11 cmake
mkdir build && cd build
cmake .. -DPYTHON_EXECUTABLE=$(which python3)
make -j$(nproc)
cd .. && python3 -c "import core; print(core.fast_compute(1000000))"
```

---

## 五、三种方式对比

| 特性 | Cython | Pybind11 | 嵌入 Python |
|------|--------|----------|-------------|
| 输入语言 | Python + 类型注解 | C++ | C++ |
| 学习曲线 | 低 | 中 | 高 |
| 适用场景 | Python 加速 | C++ 库封装 | C++ 主程序调用 Python |
| 类型安全 | 编译时检查 | 编译时检查 | 运行时检查 |
| 性能 | 高 | 极高 | 取决于调用方式 |
| GIL 管理 | 自动 | 自动 | 手动 |
| 调试难度 | 低 | 中 | 高 |
| 部署复杂度 | 低 | 中 | 高 |

---

## 六、最佳实践与避坑

1. **先 profile 再优化**：不要盲目用 C++ 重写，先用 `cProfile` 找到瓶颈
2. **粒度控制**：只把计算密集的部分用 C++ 写，逻辑留在 Python
3. **错误传播**：C++ 异常要正确转换为 Python 异常
4. **内存安全**：C++ 分配的内存要确保有释放路径
5. **版本兼容**：发布时提供多版本 wheel（pybind11 支持）

---

## 🤔 思考题

1. Cython 中 `cdef`、`def`、`cpdef` 三者的区别是什么？什么时候该用哪个？
2. Pybind11 如何处理 C++ 的 RAII 和智能指针？这与 Python 的 GC 有何关系？
3. 嵌入 Python 到 C++ 时，如何正确管理 GIL？如果不管理会怎样？
4. 在什么场景下你会选择 Cython 而不是 Pybind11？反过来呢？
5. 如果你的 C++ 库使用了多线程，在暴露给 Python 时需要注意什么？
