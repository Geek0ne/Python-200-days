# Day 099 — 最佳实践与避坑指南

## 🚫 常见错误

### 1. Cython：忘记类型声明导致无加速

```cython
# ❌ 错误：没有类型声明，编译后和 Python 一样慢
def bad_fibonacci(n):
    a, b = 0, 1
    for i in range(n):
        a, b = b, a + b
    return a

# ✅ 正确：添加类型声明
cpdef long long good_fibonacci(int n):
    cdef long long a = 0, b = 1
    cdef int i
    for i in range(n):
        a, b = b, a + b
    return a
```

### 2. Pybind11：忘记 `py::init<>()`

```cpp
// ❌ 错误：无法在 Python 中创建实例
py::class_<MyClass>(m, "MyClass")
    .def("method", &MyClass::method);

// ✅ 正确：添加构造函数绑定
py::class_<MyClass>(m, "MyClass")
    .def(py::init<>())
    .def("method", &MyClass::method);
```

### 3. 嵌入 Python：引用计数泄漏

```cpp
// ❌ 错误：忘记 DECREF
PyObject *result = PyObject_CallObject(func, args);
// 使用 result 后直接继续...

// ✅ 正确：用完即 DECREF
PyObject *result = PyObject_CallObject(func, args);
if (result) {
    // 使用 result
    Py_DECREF(result);
}
```

### 4. 混合编程：忘记检查 NULL

```cpp
// ❌ 错误：直接使用可能为 NULL 的指针
PyObject *module = PyImport_ImportModule("math");
PyObject *func = PyObject_GetAttrString(module, "sqrt");

// ✅ 正确：每次调用后检查
PyObject *module = PyImport_ImportModule("math");
if (!module) { /* 错误处理 */ }
PyObject *func = PyObject_GetAttrString(module, "sqrt");
if (!func) { Py_DECREF(module); /* 错误处理 */ }
```

---

## ⚡ 性能优化技巧

### Cython

1. **用 `cpdef` 替代 `def`**：同时生成 Python 和 C 版本
2. **禁用边界检查**：`@cython.boundscheck(False)`
3. **使用 C 数组替代 Python list**：`cdef int[:] arr`
4. **避免 Python 对象创建**：在热循环中使用 C 类型
5. **使用 `nogil` 释放 GIL**：允许其他线程运行

### Pybind11

1. **使用 `py::array_t` 直接操作 NumPy 数组**：避免逐元素转换
2. **批量转换而非逐个转换**：传递整个容器而非逐个元素
3. **使用移动语义**：`std::move()` 传递大型对象
4. **启用编译优化**：`-O3 -march=native`

### 嵌入 Python

1. **只初始化一次**：`Py_Initialize()` 只调用一次
2. **复用模块引用**：缓存 `PyImport_ImportModule` 结果
3. **批量调用**：减少 Python/C 边界跨越次数

---

## 🔧 调试技巧

### Cython 调试

```bash
# 生成带调试信息的 C 代码
cython -g my_module.pyx

# 查看生成的 C 代码
less my_module.c
```

### Pybind11 调试

```python
# Python 端检查模块
import example
print(dir(example))         # 查看所有暴露的函数
print(example.__doc__)      # 查看模块文档
```

### 嵌入 Python 调试

```cpp
// 开启 Python 调试输出
PySys_SetArgvEx(0, NULL, 0);

// 检查 Python 异常
if (PyErr_Occurred()) {
    PyErr_Print();
}
```

---

## 📦 部署清单

- [ ] 确认目标平台的 Python 版本
- [ ] 提供多版本 wheel（pybind11 支持）
- [ ] 测试在目标平台的安装和导入
- [ ] 检查动态库依赖（`ldd` / `otool -L`）
- [ ] 编写 setup.py 或 pyproject.toml
- [ ] 添加 CI/CD 构建流水线
