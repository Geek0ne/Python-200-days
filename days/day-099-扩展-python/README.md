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

**参考答案**

三者决定了函数的「可见性」和「调用速度」：

- **`def`**：普通 Python 函数。参数和返回值都是 Python 对象，任何 Python 代码都能调用，但每次调用都有 Python 层的装箱/拆箱开销。适合做模块的对外接口。
- **`cdef`**：C 级别函数。参数可以是 C 类型（如 `int`、`double`），调用走 C 函数调用约定，几乎没有开销；但**只能被 Cython 代码调用**，Python 端 import 后看不到它。适合内部热点辅助函数。
- **`cpdef`**：两者兼得。Cython 同时生成 C 版本和 Python 包装版本：Cython 内部调用走快的 C 版本，Python 外部调用走包装版本。代价是参数/返回值必须能在 C 与 Python 类型间转换。

选择口诀：**对外接口用 `def`，纯内部热点用 `cdef`，既要内部快又要外部能调用用 `cpdef`**。例如斐波那契递归这种内部密集计算，用 `cdef long long fib(int n)` 最快；而模块入口 `def fibonacci(n)` 负责接收 Python 参数再委托给它。

⚠️ 注意：`cdef` 函数不支持 Python 的默认参数、`*args` 等特性（部分受限），写之前先确认语法支持。

2. Pybind11 如何处理 C++ 的 RAII 和智能指针？这与 Python 的 GC 有何关系？

**参考答案**

先解释两个术语：**RAII**（Resource Acquisition Is Initialization）是 C++ 的资源管理惯用法——资源的生命周期绑定在对象上，构造时获取、析构时释放；**智能指针**（如 `std::shared_ptr`）是自动管理内存的指针对象，引用计数归零时自动 delete。

Pybind11 的做法是**让两套生命周期系统对接**：

- 用 `py::class_<T>` 暴露类时，Python 对象内部持有一个 C++ 实例。Python 引用计数归零触发回收时，pybind11 会调用 C++ 析构函数——RAII 的「析构即释放」因此自动生效，文件句柄、锁等资源不会泄漏。
- 对 `std::shared_ptr<T>`，pybind11 提供内置持有者（holder）支持：Python 侧和 C++ 侧共享同一个引用计数，任何一方还持有引用，对象就不会被销毁，避免了「Python 已回收但 C++ 还在用」的悬空指针。
- 也支持 `std::unique_ptr` 转移所有权给 Python，由 Python 的回收时机决定 delete。

与 Python GC 的关系：Python 的引用计数/GC 决定「何时释放」，C++ 的析构/智能指针决定「释放时做什么」。pybind11 把前者的时机翻译成后者的动作，所以只要绑定写对了，C++ 资源就能像 Python 对象一样被自动管理。

⚠️ 注意：若 C++ 侧用裸指针返回对象且所有权约定不清，容易出现双重释放或泄漏——优先用智能指针做接口。

3. 嵌入 Python 到 C++ 时，如何正确管理 GIL？如果不管理会怎样？

**参考答案**

**GIL（全局解释器锁）**保证同一时刻只有一个线程执行 Python 字节码。嵌入场景下 C++ 是主程序，可能有多条 C++ 线程，规则是：**任何线程要调用 Python C API（执行 Python 代码），必须先持有 GIL**。

正确做法：

- 主线程 `Py_Initialize()` 后默认持有 GIL；在不需要 Python 的长计算前用 `PyEval_SaveThread()` 释放，让其他线程有机会运行。
- 其他 C++ 线程调用 Python 前，用 `PyGILState_Ensure()` 获取 GIL（它还会自动绑定线程状态），调用完用 `PyGILState_Release()` 归还。这一对 API 是嵌入场景的标准姿势。
- 纯 C++ 计算段主动释放 GIL，避免白白占着锁。

不管理的后果：

- 未持有 GIL 就调 Python API → 解释器内部状态被并发破坏，典型表现是**段错误（崩溃）**或引用计数错乱导致的内存泄漏/提前释放。
- 一直霸占 GIL 不放 → 其他线程的 Python 代码全部饿死，程序假死。

💡 提示：`PyGILState_Ensure/Release` 可重入、可嵌套，比老的 `PyEval_AcquireLock` 更安全，新代码一律用前者。

4. 在什么场景下你会选择 Cython 而不是 Pybind11？反过来呢？

**参考答案**

看「起点」和「目标」：

**选 Cython**：
- 起点是 **Python 代码**，目标是给它加速。把热点函数改写成 `.pyx`、加上 `cdef int` 类型声明就能编译提速，改动小、学习曲线低。
- 团队以 Python 工程师为主，不想碰 C++ 编译链。
- 需要快速迭代数值算法（循环密集、类型固定），典型如自定义距离计算、模拟循环。

**选 Pybind11**：
- 起点是**已有的 C++ 库**（自研或第三方），目标是把它暴露给 Python。pybind11 直接绑定现成的 C++ 函数/类，保留 C++ 的全部能力（模板、STL、智能指针）。
- 需要精细控制类型转换、所有权、异常映射，或要暴露复杂的 C++ 类层次。
- 团队有 C++ 工程师，追求极致性能和与 C++ 生态的无缝集成。

一句话：**「Python 要变快」用 Cython，「C++ 要被 Python 调用」用 Pybind11**。两者也可共存：Cython 负责胶水与加速，pybind11 负责封装重型 C++ 核心。

5. 如果你的 C++ 库使用了多线程，在暴露给 Python 时需要注意什么？

**参考答案**

核心矛盾：C++ 线程可以自由并行，但**凡是要回调 Python 或操作 Python 对象的线程，都必须先拿到 GIL**。注意四点：

- **回调 Python 前获取 GIL**：C++ 工作线程里若要调用 Python 回调函数，先 `PyGILState_Ensure()`，用完 `PyGILState_Release()`。否则直接崩溃。
- **纯 C++ 计算段释放 GIL**：进入密集计算前用 `py::gil_scoped_release`（pybind11）释放 GIL，让其他 Python 线程能运行；计算结束、要返回 Python 对象前再 `py::gil_scoped_acquire` 拿回来。这样多线程 C++ 才能真正并行，而不是被 GIL 串行化。
- **线程安全的数据交接**：C++ 线程与 Python 之间共享的数据结构要自己加锁（GIL 只保护 Python 对象，不保护你的 C++ 数据）。
- **异常与生命周期**：C++ 线程抛出的异常不能直接穿过 Python 栈，要捕获后转成 Python 异常；确保 Python 解释器 finalize 前所有 C++ 线程已退出，否则回调会访问已销毁的解释器。

⚠️ 注意：释放 GIL 期间**绝不能触碰任何 PyObject**（包括读引用计数），否则就是未定义行为。
