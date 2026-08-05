# Day 099 — 扩展 Python 架构图解

## 1. Python 扩展方式总览

```mermaid
graph TB
    subgraph "Python 扩展三种方式"
        A["🐍 Python 代码"]
        B["🔧 Cython<br/>Python + 类型注解"]
        C["⚙️ Pybind11<br/>C++ 头文件库"]
        D["🔗 嵌入 Python<br/>C++ 主程序"]
    end

    subgraph "输出产物"
        E[".so / .pyd<br/>CPython 扩展模块"]
        F[".so / .pyd<br/>CPython 扩展模块"]
        G["可执行文件<br/>内置 Python 解释器"]
    end

    A -->|编译| B
    A -->|绑定| C
    A -->|嵌入| D

    B -->|cythonize| E
    C -->|cmake| F
    D -->|链接 libpython| G
```

## 2. Cython 编译流程

```mermaid
flowchart LR
    A[".pyx 源码<br/>(Python + 类型)"] -->|cythonize| B[".c 文件<br/>(纯 C 代码)"]
    B -->|gcc/clang| C[".so/.pyd<br/>(共享库)"]
    C -->|import| D["Python 代码"]

    style A fill:#4CAF50,color:#fff
    style B fill:#2196F3,color:#fff
    style C fill:#FF9800,color:#fff
    style D fill:#9C27B0,color:#fff
```

## 3. Pybind11 绑定架构

```mermaid
graph TB
    subgraph "C++ 层"
        A["C++ 类/函数"]
        B["pybind11 绑定代码"]
        C["编译为 .so/.pyd"]
    end

    subgraph "Python 层"
        D["import module"]
        E["调用 C++ 功能"]
        F["自动类型转换"]
    end

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F -->|返回| A
```

## 4. 嵌入 Python 架构

```mermaid
sequenceDiagram
    participant C++ as C++ 主程序
    participant PY as Python 解释器
    participant Code as Python 脚本

    C++->>C++: Py_Initialize()
    C++->>PY: PyRun_SimpleString()
    PY->>Code: 执行 Python 代码
    Code-->>PY: 返回结果
    PY-->>C++: PyObject* 结果
    C++->>C++: 解析 PyObject
    C++->>C++: Py_Finalize()
```

## 5. 混合编程项目结构

```
hybrid_project/
├── CMakeLists.txt              # 构建入口
├── setup.py                    # pip 安装入口
│
├── src/                        # C++ 源码
│   ├── core.cpp               # 核心计算逻辑
│   ├── bindings.cpp           # pybind11 绑定
│   └── utils.h                # C++ 工具函数
│
├── python/                     # Python 高层接口
│   ├── __init__.py
│   ├── wrapper.py             # Python 包装层
│   └── pipeline.py            # 业务流程
│
├── tests/                      # 测试
│   ├── test_core.py
│   └── test_wrapper.py
│
└── examples/                   # 使用示例
    └── demo.py
```

## 6. 类型转换映射表

```mermaid
graph LR
    subgraph "C++ 类型"
        A1["int"]
        A2["double"]
        A3["std::string"]
        A4["std::vector&lt;T&gt;"]
        A5["std::map&lt;K,V&gt;"]
        A6["std::optional&lt;T&gt;"]
        A7["std::shared_ptr&lt;T&gt;"]
    end

    subgraph "Python 类型"
        B1["int"]
        B2["float"]
        B3["str"]
        B4["list"]
        B5["dict"]
        B6["Optional[T]"]
        B7["T (GC 管理)"]
    end

    A1 --- B1
    A2 --- B2
    A3 --- B3
    A4 --- B4
    A5 --- B5
    A6 --- B6
    A7 --- B7
```

## 7. 性能对比图

```
基准测试：斐波那契(500000)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

纯 Python     ████████████████████████████  100%
Cython (无类型) ████████████████             55%
Cython (全类型) ██                           8%
C++ 原生       █                            5%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 8. GIL 管理对比

```mermaid
graph TB
    subgraph "Cython"
        A["自动管理 GIL<br/>无需手动操作"]
    end

    subgraph "Pybind11"
        B["默认持有 GIL<br/>py::gil_scoped_release 可释放"]
    end

    subgraph "嵌入 Python"
        C["必须手动管理<br/>PyGILState_Ensure/Release"]
    end

    style A fill:#4CAF50,color:#fff
    style B fill:#2196F3,color:#fff
    style C fill:#f44336,color:#fff
```
