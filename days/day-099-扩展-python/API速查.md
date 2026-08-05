# Day 099 — API 速查与对比

## Cython API 速查

### 函数声明

| 语法 | Python 可见 | C 级别 | 用途 |
|------|------------|--------|------|
| `def func(...)` | ✅ | ❌ | 纯 Python 函数 |
| `cdef func(...)` | ❌ | ✅ | 纯 C 内部函数 |
| `cpdef func(...)` | ✅ | ✅ | 双版本（推荐） |

### 类型声明

```cython
cdef int x = 0           # C int
cdef double y = 0.0      # C double
cdef str name = ""       # Python str（C 级别）
cdef list items = []     # Python list（C 级别）
cdef dict mapping = {}   # Python dict（C 级别）
cdef object obj = None   # 通用 Python 对象
```

### 编译指令

```cython
@cython.boundscheck(False)     # 禁用边界检查
@cython.wraparound(False)      # 禁用负索引
@cython.cdivision(True)        # 使用 C 除法（不检查除零）
@cython.overflowcheck(True)    # 启用整数溢出检查
```

### 外部 C 函数

```cython
cdef extern from "math.h":
    double sqrt(double x)
    double sin(double x)

cdef extern from "stdlib.h":
    int rand()
```

---

## Pybind11 API 速查

### 模块定义

```cpp
PYBIND11_MODULE(name, m) {
    m.doc() = "module docstring";
    m.def("func", &func, "docstring");
}
```

### 类绑定

```cpp
py::class_<MyClass>(m, "MyClass")
    .def(py::init<>())                      // 默认构造
    .def(py::init<int, std::string>())       // 参数化构造
    .def("method", &MyClass::method)         // 方法
    .def_readwrite("attr", &MyClass::attr)   // 可读写属性
    .def_readonly("attr", &MyClass::attr)    // 只读属性
    .def_static("static_method", ...)        // 静态方法
    .def("__repr__", &MyClass::repr);        // 自定义 repr
```

### 类型转换

| C++ 类型 | Python 类型 | 需要头文件 |
|----------|------------|-----------|
| `int/long` | `int` | pybind11/pybind11.h |
| `float/double` | `float` | pybind11/pybind11.h |
| `std::string` | `str` | pybind11/stl.h |
| `std::vector<T>` | `list` | pybind11/stl.h |
| `std::map<K,V>` | `dict` | pybind11/stl.h |
| `std::optional<T>` | `Optional[T]` | pybind11/stl.h |
| `py::array_t<T>` | `numpy.ndarray` | pybind11/numpy.h |

### NumPy 操作

```cpp
// 一维数组
auto buf = input.unchecked<1>();       // 只读
auto buf = input.mutable_unchecked<1>(); // 可写
double val = buf(i);                    // 读取
buf(i) = 42.0;                          // 写入

// 二维数组
auto buf2d = input.unchecked<2>();
double val = buf2d(row, col);
```

---

## 嵌入 Python API 速查

### 初始化与关闭

```cpp
Py_Initialize();        // 初始化
Py_Finalize();          // 关闭
```

### 执行代码

```cpp
PyRun_SimpleString("code");
PyRun_SimpleStringFlags("code", &flags);
```

### 导入模块

```cpp
PyObject *module = PyImport_ImportModule("module_name");
PyObject *func = PyObject_GetAttrString(module, "func_name");
```

### 调用函数

```cpp
PyObject *args = Py_BuildValue("(id)", 42, 3.14);  // int, double
PyObject *result = PyObject_CallObject(func, args);
```

### 获取结果

```cpp
long val = PyLong_AsLong(result);        // Python int -> C long
double val = PyFloat_AsDouble(result);   // Python float -> C double
const char *str = PyUnicode_AsUTF8(result); // Python str -> C string
```

### 引用计数

```cpp
Py_INCREF(obj);    // 增加引用
Py_DECREF(obj);    // 减少引用（为 0 时释放）
```

### GIL 管理

```cpp
PyGILState_Ensure();     // 获取 GIL
PyGILState_Release(s);   // 释放 GIL
```

---

## 三种方式选择指南

```
需要加速 Python 代码？
├── 只是计算密集型循环 → Cython
├── 已有 C++ 库要封装 → Pybind11
├── C++ 主程序需要 Python 能力 → 嵌入 Python
└── 不确定 → 先 profile，再决定
```
