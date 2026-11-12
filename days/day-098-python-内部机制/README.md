# Day 098 — Python 内部机制

> **阶段 7：进阶与性能优化** | **主题：Python 内部机制** | **难度：⭐⭐⭐⭐⭐**

---

## 📋 今日学习目标

1. 理解 Python 字节码的生成与执行原理
2. 掌握 `dis` 模块分析字节码的方法
3. 深入理解 CPython 虚拟机的执行模型
4. 理解 PyObject 与 Python 类型系统的底层实现
5. 实战：构建一个字节码分析器

---

## 1. Python 字节码（dis 模块）

### 1.1 什么是字节码？

Python 是一种**解释型语言**，但并不是逐行解释执行的。Python 源代码首先被编译为**字节码（Bytecode）**，然后由 Python 虚拟机（PVM）执行字节码。

```
源代码 (.py)
    ↓  编译（compile）
字节码 (.pyc / 内存)
    ↓  执行
CPython 虚拟机 (PVM)
```

**为什么需要字节码？**

- **性能优化**：字节码比源代码更紧凑，执行更快
- **跨平台**：字节码是平台无关的（在同版本 Python 内）
- **缓存机制**：`.pyc` 文件缓存编译结果，避免重复编译
- **安全性**：字节码比源代码更难逆向工程

### 1.2 什么是 pyc 文件？

`.pyc` 文件是 Python 编译后的字节码缓存文件，存储在 `__pycache__/` 目录下：

```
my_module.py
__pycache__/
    my_module.cpython-312.pyc   ← Python 3.12 编译的字节码
```

**pyc 文件结构：**

```
┌─────────────────────────────┐
│  Magic Number (4 bytes)     │  ← 标识 Python 版本
│  Flags (4 bytes)            │  ← 编译标志
│  Source timestamp (4 bytes) │  ← 源文件修改时间
│  Source size (4 bytes)      │  ← 源文件大小
│  Code Object                │  ← 实际的字节码
└─────────────────────────────┘
```

### 1.3 使用 dis 模块反汇编

`dis`（disassembler）模块是 Python 内置的字节码反汇编工具：

```python
import dis

def add(a, b):
    return a + b

# 反汇编函数
dis.dis(add)
```

输出示例：

```
  2           0 LOAD_FAST                0 (a)
              2 LOAD_FAST                1 (b)
              4 BINARY_ADD
              6 RETURN_VALUE
```

**每条指令的含义：**

| 字段 | 说明 |
|------|------|
| 行号 | 源代码行号（2） |
| 偏移量 | 字节码中的位置（0, 2, 4, 6） |
| 操作码 | 指令名称（LOAD_FAST, BINARY_ADD 等） |
| 操作数 | 指令参数（0, 1 等） |
| 注释 | 可读的名称（a, b 等） |

### 1.4 字节码指令详解

Python 字节码有数百条指令，以下是最常用的几类：

**加载/存储指令：**

| 指令 | 说明 | 示例 |
|------|------|------|
| `LOAD_CONST` | 加载常量 | `x = 1` → 加载 1 |
| `LOAD_FAST` | 加载局部变量 | 函数参数、局部变量 |
| `STORE_FAST` | 存储局部变量 | `x = 1` → 存储到 x |
| `LOAD_GLOBAL` | 加载全局变量 | 访问全局变量或内置函数 |
| `LOAD_ATTR` | 加载属性 | `obj.attr` |
| `LOAD_METHOD` | 加载方法 | `obj.method()` |

**运算指令：**

| 指令 | 说明 |
|------|------|
| `BINARY_ADD` | 加法 `a + b` |
| `BINARY_SUBTRACT` | 减法 `a - b` |
| `BINARY_MULTIPLY` | 乘法 `a * b` |
| `BINARY_TRUE_DIVIDE` | 真除法 `a / b` |
| `BINARY_FLOOR_DIVIDE` | 整除 `a // b` |
| `BINARY_MODULO` | 取模 `a % b` |
| `BINARY_POWER` | 幂运算 `a ** b` |

**控制流指令：**

| 指令 | 说明 |
|------|------|
| `POP_JUMP_IF_FALSE` | 条件为假时跳转 |
| `POP_JUMP_IF_TRUE` | 条件为真时跳转 |
| `JUMP_ABSOLUTE` | 无条件绝对跳转 |
| `FOR_ITER` | for 循环迭代 |
| `GET_ITER` | 获取迭代器 |
| `CALL_FUNCTION` | 调用函数 |

**Python 3.11+ 的新指令：**

| 指令 | 说明 |
|------|------|
| `RESUME` | 恢复执行（替代 NOP） |
| `PRECALL` | 预调用（3.11） |
| `CALL` | 统一调用指令（3.11+） |
| `PUSH_NULL` | 推送 NULL（3.11+） |

### 1.5 实战：分析 if-else 的字节码

```python
import dis

def check_positive(x):
    if x > 0:
        return "正数"
    elif x == 0:
        return "零"
    else:
        return "负数"

dis.dis(check_positive)
```

输出：

```
  2           0 LOAD_FAST                0 (x)
              2 LOAD_CONST               1 (0)
              4 COMPARE_OP               4 (>)
              6 POP_JUMP_IF_FALSE       12

  3           8 LOAD_CONST               2 ('正数')
             10 RETURN_VALUE

  4     >>   12 LOAD_FAST                0 (x)
             14 LOAD_CONST               1 (0)
             16 COMPARE_OP               2 (==)
             18 POP_JUMP_IF_FALSE       24

  5          20 LOAD_CONST               3 ('零')
             22 RETURN_VALUE

  7     >>   24 LOAD_CONST               4 ('负数')
             26 RETURN_VALUE
```

**分析流程：**

```
开始
  ↓
LOAD_FAST x → LOAD_CONST 0 → COMPARE_OP >
  ↓
POP_JUMP_IF_FALSE → 跳到偏移 12（elif 检查）
  ↓ (如果 x > 0)
LOAD_CONST '正数' → RETURN_VALUE
```

### 1.6 实战：分析 for 循环的字节码

```python
import dis

def sum_list(lst):
    total = 0
    for item in lst:
        total += item
    return total

dis.dis(sum_list)
```

**for 循环的字节码结构：**

```
GET_ITER          ← 获取迭代器
>> FOR_ITER       ← 取下一个元素（失败则跳转到循环后）
  STORE_FAST      ← 存储循环变量
  [循环体字节码]    ← 循环体操作
  JUMP_ABSOLUTE   ← 跳回 FOR_ITER
>> [循环后的代码]   ← 循环结束
```

### 1.7 实战：分析列表推导式的字节码

```python
import dis

def list_comprehension(n):
    return [x**2 for x in range(n) if x % 2 == 0]

dis.dis(list_comprehension)
```

**列表推导式的字节码特点：**

- 使用 `LIST_APPEND` 指令而非 `append()` 方法调用
- 比普通 for 循环 + append 更高效
- 内部仍然是迭代器模式

---

## 2. CPython 虚拟机结构

### 2.1 CPython 执行模型

CPython 的执行过程可以分为三个阶段：

```
┌──────────────────────────────────────────────┐
│                    CPython                    │
│                                              │
│  源代码 ──→ 编译器 ──→ 字节码 ──→ PVM 执行   │
│  (.py)     (Parser)   (.pyc)    (PyEval_Eval │
│                                  _Frame)     │
└──────────────────────────────────────────────┘
```

**三个核心组件：**

1. **编译器（Compiler）**：将源代码转换为字节码
2. **字节码（Bytecode）**：紧凑的指令序列
3. **虚拟机（PVM）**：解释执行字节码

### 2.2 栈帧（Frame）结构

每次函数调用都会创建一个**栈帧（Frame）**，它是执行的上下文：

```
┌─────────────────────────────────┐
│           Frame Object          │
├─────────────────────────────────┤
│ f_code        → Code Object     │  ← 要执行的代码
│ f_back        → 上一级 Frame    │  ← 调用栈链接
│ f_locals      → 局部变量字典    │  ← locals() 返回的
│ f_lineno      → 当前行号       │  ← 当前执行到哪行
│ f_lasti       → 最后执行指令    │  ← 字节码偏移量
│ f_valuestack  → 值栈           │  ← 运算操作数
│ f_blockstack  → 块栈           │  ← try/with 块
└─────────────────────────────────┘
```

### 2.3 Code Object（代码对象）

每个函数、模块、类的编译结果都是一个 Code Object：

```python
import dis

def example():
    x = 1
    y = 2
    return x + y

code = example.__code__

print(f"代码对象: {code}")
print(f"常量池: {code.co_consts}")
print(f"变量名: {code.co_varnames}")
print(f"字节码: {code.co_code}")
print(f"行号表: {code.co_lnotab}")
```

**Code Object 的关键属性：**

| 属性 | 说明 |
|------|------|
| `co_code` | 字节码指令（字节串） |
| `co_consts` | 常量池（元组） |
| `co_varnames` | 局部变量名（元组） |
| `co_names` | 全局/属性名（元组） |
| `co_stacksize` | 栈大小 |
| `co_argcount` | 参数个数 |
| `co_kwonlyargcount` | 关键字参数个数 |
| `co_nlocals` | 局部变量数 |
| `co_flags` | 标志位 |
| `co_filename` | 源文件名 |
| `co_firstlineno` | 第一行行号 |
| `co_lnotab` | 行号与字节码偏移的映射表 |

### 2.4 值栈（Value Stack）执行模型

CPython 使用**基于栈的虚拟机**，所有操作都在栈上进行：

```python
import dis

def compute():
    x = 3 + 4 * 5  # 运算符优先级
    
dis.dis(compute)
```

输出：

```
  2           0 LOAD_CONST               0 (3)
              2 LOAD_CONST               1 (4)
              4 LOAD_CONST               2 (5)
              6 BINARY_MULTIPLY
              8 BINARY_ADD
             10 STORE_FAST               0 (x)
```

**值栈执行过程：**

```
指令           栈状态
─────────────────────────
LOAD_CONST 3   [3]
LOAD_CONST 4   [3, 4]
LOAD_CONST 5   [3, 4, 5]
BINARY_MULTIPLY [3, 20]     ← 4 * 5 = 20
BINARY_ADD     [23]          ← 3 + 20 = 23
STORE_FAST x   []            ← x = 23
```

### 2.5 Python 3.11+ 的自适应解释器

Python 3.11 引入了**自适应解释器（Adaptive Interpreter）**，也叫 **Faster CPython** 项目：

```
┌─────────────────────────────────────────────┐
│         自适应解释器工作流程                   │
│                                             │
│  字节码 ──→ 普通执行 ──→ 热点检测            │
│                           ↓                  │
│                    特化（Specialize）         │
│                           ↓                  │
│                    特化指令执行               │
│                    (更快的版本)              │
└─────────────────────────────────────────────┘
```

**特化指令示例：**

| 原始指令 | 特化指令 | 说明 |
|----------|----------|------|
| `LOAD_ATTR` | `LOAD_ATTR_INSTANCE_VALUE` | 从实例 __dict__ 加载 |
| `LOAD_ATTR` | `LOAD_ATTR_SLOT` | 从 slot 加载 |
| `BINARY_OP` | `BINARY_OP_ADD_INT` | 整数加法专用 |
| `CALL` | `CALL_PY_EXACT_ARGS` | Python 函数精确调用 |

### 2.6 GIL 与线程执行

**全局解释器锁（GIL）**确保同一时刻只有一个线程执行 Python 字节码：

```
┌──────────┬──────────┬──────────┐
│ 线程 A   │ 线程 B   │ 线程 C   │
├──────────┼──────────┼──────────┤
│ 执行中   │ 等待     │ 等待     │  ← 时间片 1
│ 等待     │ 执行中   │ 等待     │  ← 时间片 2
│ 等待     │ 等待     │ 执行中   │  ← 时间片 3
└──────────┴──────────┴──────────┘
              ↓
    通过 time-slicing 模拟并发
```

**GIL 的影响：**

- CPU 密集型任务无法利用多核
- I/O 操作时会释放 GIL（文件读写、网络请求等）
- Python 3.12+ 开始逐步移除 GIL（PEP 703）

---

## 3. PyObject 与类型系统

### 3.1 万物皆对象

在 CPython 中，**所有数据都是对象**，包括整数、函数、类、模块等。每个对象在 C 层面都是一个 `PyObject`：

```c
// CPython 源码 (object.h)
typedef struct _object {
    Py_ssize_t ob_refcnt;    // 引用计数
    PyTypeObject *ob_type;    // 类型指针
} PyObject;
```

**内存布局：**

```
┌──────────────────────┐
│     PyObject         │
├──────────────────────┤
│  ob_refcnt (8 bytes) │  ← 引用计数
│  ob_type (8 bytes)   │  ← 指向类型对象
├──────────────────────┤
│     对象数据          │  ← 类型特定的数据
└──────────────────────┘
```

### 3.2 引用计数机制

CPython 使用**引用计数**作为主要的内存管理机制：

```python
import sys

a = []              # 引用计数 = 1
print(sys.getrefcount(a))  # 引用计数 = 2（参数本身也引用了一次）

b = a               # 引用计数 = 3
c = a               # 引用计数 = 4

del b               # 引用计数 = 3
del c               # 引用计数 = 2
```

**引用计数增减规则：**

| 操作 | 引用计数变化 |
|------|-------------|
| `a = b` | +1（b 的引用计数） |
| `del a` | -1（a 的引用计数） |
| 函数传参 | +1 |
| 函数返回 | -1 |
| 加入容器 | +1 |
| 从容器移除 | -1 |

**引用计数为 0 时，对象立即被回收：**

```python
import sys

class Tracker:
    def __init__(self, name):
        self.name = name
        print(f"创建: {name}")
    def __del__(self):
        print(f"销毁: {self.name}")

t1 = Tracker("A")  # 创建: A
t2 = Tracker("B")  # 创建: B
del t1              # 销毁: A（引用计数为 0）
del t2              # 销毁: B（引用计数为 0）
```

### 3.3 循环引用与垃圾回收

引用计数无法处理**循环引用**：

```python
import gc

class Node:
    def __init__(self):
        self.ref = None

a = Node()
b = Node()
a.ref = b   # a → b
b.ref = a   # b → a  （循环引用）

del a
del b
# 对象仍然存在！引用计数不为 0，但已经无法访问
```

**分代垃圾回收（Generational GC）：**

```
┌─────────────────────────────────────────┐
│            分代垃圾回收                   │
├─────────┬──────────┬──────────┬─────────┤
│  Generation 0 │ Generation 1 │ Generation 2 │
│  新创建的对象  │  存活一次的   │  长期存活的   │
│  频繁回收      │  较少回收     │  很少回收     │
└─────────┴──────────┴──────────┴─────────┘
```

```python
import gc

# 查看 GC 统计
print(gc.get_stats())

# 手动触发 GC
gc.collect()

# 查看不可回收的对象
print(gc.garbage)
```

### 3.4 类型对象与类型层次

在 CPython 中，类型本身也是对象：

```python
# 所有类型都是 type 的实例
print(type(int))      # <class 'type'>
print(type(str))      # <class 'type'>
print(type(list))     # <class 'type'>
print(type(type))     # <class 'type'>  ← type 是自身的实例！

# 类型层次
print(int.__bases__)    # (<class 'object'>,)
print(str.__bases__)    # (<class 'object'>,)
print(type.__bases__)   # (<class 'object'>,)
```

**类型层次图：**

```
                    object
                      ↑
          ┌───────────┼───────────┐
          ↑           ↑           ↑
       type        int          str
         ↑
    ┌────┼────┐
    ↑    ↑    ↑
  bool  int  float
```

### 3.5 内存分配器

CPython 使用三级内存分配器：

```
┌─────────────────────────────────────┐
│  第三层：Python 内存分配器           │
│  (pymalloc)                         │
│  管理小于 512 字节的对象            │
├─────────────────────────────────────┤
│  第二层：通用内存分配器              │
│  (pymalloc raw)                     │
│  管理 512B ~ 1MB 的分配             │
├─────────────────────────────────────┤
│  第一层：系统内存分配器              │
│  (malloc/free)                      │
│  管理大于 1MB 的分配                │
└─────────────────────────────────────┘
```

**pymalloc 的内存池：**

```
Arena (256 KB)
├── Pool 1 (4 KB)
│   ├── Block (8 bytes) × N
│   ├── Block (16 bytes) × N
│   ├── Block (32 bytes) × N
│   └── Block (64 bytes) × N
├── Pool 2 (4 KB)
│   └── ...
└── Pool 64 (4 KB)
    └── ...
```

### 3.6 内置类型实现

不同内置类型的内存布局各不相同：

```python
import sys

# 整数的内存
x = 42
print(sys.getsizeof(x))  # 28 bytes (Python 3.12)

# 列表的内存
lst = [1, 2, 3]
print(sys.getsizeof(lst))  # 88 bytes（列表对象本身）
print(sys.getsizeof(lst) + sum(sys.getsizeof(i) for i in lst))  # 包含元素

# 字典的内存
d = {"a": 1, "b": 2}
print(sys.getsizeof(d))  # 232 bytes

# 字符串的内存
s = "hello"
print(sys.getsizeof(s))  # 54 bytes
```

**整数的内存布局（小整数缓存）：**

```
Python 缓存了 -5 到 256 的整数对象：
┌──────────────────────┐
│   小整数缓存池        │
│   [-5, -4, ..., 255] │
│   同一个对象被复用！   │
└──────────────────────┘

a = 256
b = 256
print(a is b)  # True ← 同一个对象

a = 257
b = 257
print(a is b)  # False ← 不同对象（在交互式环境中）
```

---

## 4. 实战：字节码分析器

### 4.1 项目结构

```
day-098-python-内部机制/
├── README.md
├── code/
│   ├── 01-bytecode-basics.py
│   ├── 02-vm-internals.py
│   └── 03-bytecode-analyzer.py
├── diagrams/
│   └── README.md
└── exercises/
    └── checklist.md
```

### 4.2 字节码分析器功能

完整的字节码分析器将包含以下功能：

1. **反汇编函数**：显示字节码指令和注释
2. **统计分析**：指令频率、操作数分布
3. **调用图分析**：函数调用关系
4. **常量池分析**：常量的类型和值
5. **性能评估**：识别潜在的性能问题

---

## 5. 思考题

### 基础题

1. **为什么 Python 使用字节码而不是直接解释源代码？**
   - 提示：考虑编译时间、执行效率、缓存机制

**参考答案**

直接解释源代码意味着每次执行都要重新做词法分析、语法分析、生成语法树——这些「理解代码」的工作非常昂贵，而且每次结果都一样。字节码把这部分工作**一次性做完并固化**：

- **执行效率**：字节码是紧凑的指令序列，虚拟机只需「取指令 → 执行」的简单循环，不用再解析文本。比如 `a + b` 已经变成 `LOAD_FAST a / LOAD_FAST b / BINARY_OP +` 三条指令，省去了所有语法分析开销。
- **缓存机制**：编译结果可以存成 `.pyc` 文件。下次导入同一模块时，只要源文件没改（对比时间戳和大小），直接加载字节码，跳过整个编译阶段，显著加快启动速度。
- **编译与执行解耦**：编译只做一次，执行可以无数次；还便于在执行层做优化（如 3.11 的指令特化），而不用动编译器。

打个比方：源代码是「菜谱原文」，字节码是「备好的半成品菜」——厨师（虚拟机）直接下锅翻炒，不必每次从洗菜切菜开始。

2. **引用计数和垃圾回收各有什么优缺点？**
   - 提示：考虑实时性、循环引用、性能开销

**参考答案**

两者是互补关系，CPython 以引用计数为主、分代 GC 为辅。

**引用计数**：每个对象记录「有多少引用指向我」，计数归零立即回收。
- 优点：**实时性好**——对象一没人用就马上释放，内存占用平稳，回收时机可预测；实现简单，不需要暂停整个程序去扫描。
- 缺点：**无法处理循环引用**（a 引用 b、b 引用 a，即使外部都不用了，计数也不为 0）；每次赋值、传参、容器操作都要维护计数，有持续的运行时开销，多线程下还需加锁保护。

**分代垃圾回收（追踪式 GC）**：定期从根对象出发扫描，找出「不可达」的对象回收。
- 优点：能发现循环引用这类「计数不为 0 但实际已死」的对象；按代分层（新对象频繁查、老对象很少查），利用了「大多数对象朝生夕死」的规律，摊薄成本。
- 缺点：回收时机不确定，触发时可能产生停顿；扫描本身有开销，且无法像引用计数那样即时释放。

小例子：两个互相引用的 Node 对象 `del` 之后，引用计数各剩 1 不会释放，只有 `gc.collect()` 扫描发现它们不可达才回收——这就是为什么需要两套机制配合。

3. **`.pyc` 文件的 Magic Number 有什么作用？**
   - 提示：考虑版本兼容性

**参考答案**

Magic Number（魔数）是 `.pyc` 文件开头的 4 个字节，本质是**字节码格式的版本号**。不同 Python 版本的字节码指令集不同（比如 3.11 新增了 `RESUME`、`CALL`，删除了旧指令），同一份字节码在别的版本上可能根本无法执行。

加载 `.pyc` 时，解释器先比对文件里的魔数和自己当前的魔数：

- **一致** → 字节码格式兼容，继续检查源文件时间戳/大小，决定是否直接加载缓存；
- **不一致** → 缓存作废，忽略该 `.pyc`，重新从 `.py` 源码编译。

这就是为什么升级 Python 后旧的 `__pycache__` 不会导致崩溃——魔数让解释器能一眼识别「这是别的版本编译的，不能用」。例如 Python 3.11 和 3.12 的魔数不同；甚至同一小版本的不同补丁版本之间，魔数也可能更新（可用 `importlib.util.MAGIC_NUMBER` 查看当前解释器的魔数）。

💡 提示：魔数只保证「字节码格式」兼容，不保证业务逻辑兼容；`.pyc` 也容易被反编译，不要把它当作代码保护手段。

### 进阶题

4. **如何在不修改源代码的情况下，给函数添加性能监控？**
   - 提示：考虑字节码修改、sys.settrace

**参考答案**

最实用的方案是 **`sys.settrace`**：它允许注册一个回调函数，解释器在每次函数调用（`call`）、每行执行（`line`）、返回（`return`）时都会通知你——完全不用改业务代码。下面是一个统计「调用次数 + 累计耗时」的监控器：

```python
import sys
import time
from collections import defaultdict

call_count = defaultdict(int)      # 函数名 -> 调用次数
total_time = defaultdict(float)    # 函数名 -> 累计耗时（秒）
_start_stack = []                  # 记录每层调用的开始时间


def profiler(frame, event, arg):
    name = frame.f_code.co_name
    if event == 'call':
        call_count[name] += 1
        _start_stack.append((name, time.perf_counter()))
    elif event == 'return':
        if _start_stack:
            key, t0 = _start_stack.pop()
            total_time[key] += time.perf_counter() - t0
    return profiler                # 返回自身，继续跟踪函数内部的行事件


def slow_add(n):
    s = 0
    for i in range(n):
        s += i
    return s


def work():
    slow_add(10000)
    slow_add(20000)


sys.settrace(profiler)   # 开启跟踪（不改任何业务代码）
work()
sys.settrace(None)       # 关闭跟踪

for name in call_count:
    print(f"{name}: 调用 {call_count[name]} 次, "
          f"累计耗时 {total_time[name] * 1000:.2f} ms")
```

预期输出（耗时因机器/版本而异）：

```
work: 调用 1 次, 累计耗时 7.32 ms
slow_add: 调用 2 次, 累计耗时 7.31 ms
```

原理：`call` 事件时把开始时间压栈，`return` 事件时弹栈并累加时间差，栈结构天然支持嵌套调用。其他不改源码的思路还有：外部用装饰器包一层（`work = monitor(work)`）、用 `cProfile` 直接跑、或在字节码层面插桩（改写 Code Object，难度高，一般不推荐）。

⚠️ 注意：`sys.settrace` 本身开销很大（每行都回调），测出的耗时包含跟踪开销，只适合定位相对热点，不适合精确计时；且它只跟踪当前线程。

5. **Python 3.11 的自适应解释器是如何提升性能的？**
   - 提示：考虑热点检测、特化指令

**参考答案**

核心思想是「**让常用路径走捷径**」，分三步：

1. **热点检测**：解释器给指令附带计数器，统计每条指令被执行了多少次。反复执行的「热点」指令会被标记出来。
2. **特化（Specialization）**：把通用指令替换成针对具体类型的专用版本。例如 `BINARY_OP` 发现两边总是 int，就换成 `BINARY_OP_ADD_INT`——跳过类型判断、直接做整数加法；`LOAD_ATTR` 发现属性总在实例 `__dict__` 的固定位置，就换成 `LOAD_ATTR_INSTANCE_VALUE`，跳过完整的属性查找流程。
3. **去优化（Deoptimization）**：特化版本附带「守卫条件」，一旦类型假设被打破（比如突然传进来一个字符串），自动退回通用指令，保证正确性。

打个比方：通用指令像「人工收费站」，每辆车都要停车问车型；特化指令像「ETC 专用道」，识别过车型后直接抬杆放行。

效果：官方基准测试中 3.11 比 3.10 平均快约 25%（因 workload 和机器而异）。这一切发生在运行时、对开发者完全透明——你不需要改任何代码。

6. **为什么 `a = 257; b = 257; a is b` 在交互式环境中为 False，但在脚本中为 True？**
   - 提示：考虑编译器优化、常量折叠

**参考答案**

关键在**编译单位**不同，导致常量能否被合并：

- **脚本中**：整个文件被一次性编译成一个 Code Object。编译器做常量折叠/合并时发现两个 `257` 是相等的常量，就让它们共用常量池里的**同一个对象**——两条 `LOAD_CONST` 指向同一地址，所以 `a is b` 为 True。
- **交互式环境中**：每输入一行就单独编译一次。`a = 257` 和 `b = 257` 属于两个不同的 Code Object，各自创建了一个新的 257 对象（257 超出 -5~256 的小整数缓存范围），所以 `a is b` 为 False。

用 `compile()` 可以精确复现这两种情况：

```python
import dis

# 场景 1：整段脚本一次编译（相当于 .py 文件）
src = "a = 257; b = 257; result = a is b"
ns = {}
exec(compile(src, "<script>", "exec"), ns)
print("脚本中 a is b:", ns["result"])

# 查看字节码：两条 LOAD_CONST 指向常量池里的同一个对象
print("--- 脚本字节码 ---")
dis.dis(compile(src, "<script>", "exec"))

# 场景 2：模拟交互式环境，每条语句单独编译
g = {}
exec(compile("a = 257", "<stdin>", "exec"), g)
exec(compile("b = 257", "<stdin>", "exec"), g)
print("逐条编译 a is b:", g["a"] is g["b"])
```

预期输出（字节码细节因版本而异，此处为 3.12）：

```
脚本中 a is b: True
--- 脚本字节码 ---
  0           0 RESUME                   0
  1           2 LOAD_CONST               0 (257)
              4 STORE_NAME               0 (a)
              6 LOAD_CONST               0 (257)
              ...
逐条编译 a is b: False
```

注意两条 `LOAD_CONST` 的参数都是 `0 (257)`——同一个常量池条目，这就是 True 的直接证据。

⚠️ 注意：这是 CPython 的实现细节，不是语言保证。比较整数的值永远用 `==`，`is` 只用于判断「是否同一个对象」（如 `x is None`）。

### 挑战题

7. **设计一个字节码级别的性能分析工具，能检测函数中的性能热点。**
   - 提示：考虑指令频率、循环深度、函数调用开销

**参考答案**

设计思路是「**静态 + 动态**」两条腿走路：

- **静态**：用 `dis.get_instructions()` 分析字节码——统计指令频率（`LOAD_GLOBAL`/`LOAD_ATTR` 多说明查找开销大）、找向后跳转（跳转目标偏移小于当前偏移 = 循环体）。
- **动态**：用 `sys.settrace` 统计每行的实际执行次数——执行次数最多的行就是热点，再结合静态信息判断它是否在循环里。

完整实现（仅标准库）：

```python
import dis
import sys
from collections import Counter, defaultdict


def hotspots(func, *args, **kwargs):
    """静态字节码分析 + 动态行计数，找出函数热点"""
    code = func.__code__

    # ── 静态分析：统计指令频率、检测循环 ──
    instructions = list(dis.get_instructions(code))
    freq = Counter(ins.opname for ins in instructions)
    # 跳转目标偏移 < 当前偏移 → 向后跳转 → 说明存在循环
    loops = [ins for ins in instructions
             if 'JUMP' in ins.opname
             and isinstance(ins.argval, int)
             and ins.argval < ins.offset]

    # ── 动态分析：用 sys.settrace 统计每行执行次数 ──
    hits = defaultdict(int)

    def tracer(frame, event, arg):
        if frame.f_code is code and event == 'line':
            hits[frame.f_lineno] += 1
        return tracer

    old_trace = sys.gettrace()
    sys.settrace(tracer)
    try:
        result = func(*args, **kwargs)
    finally:
        sys.settrace(old_trace)   # 恢复原跟踪器，避免影响其他代码

    print(f"函数 {func.__name__} 指令频率 TOP5: {freq.most_common(5)}")
    print(f"检测到 {len(loops)} 处向后跳转（循环体）")
    print("热点行（执行次数最多）:")
    for lineno, n in sorted(hits.items(), key=lambda kv: -kv[1])[:3]:
        print(f"  第 {lineno} 行: 执行 {n} 次")
    return result


def sum_squares(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


hotspots(sum_squares, 10000)
```

预期输出（行号取决于代码在文件中的位置，指令名因 Python 版本而异）：

```
函数 sum_squares 指令频率 TOP5: [('LOAD_FAST', 5), ('STORE_FAST', 3), ('BINARY_OP', 2), ('RESUME', 1), ('LOAD_CONST', 1)]
检测到 1 处向后跳转（循环体）
热点行（执行次数最多）:
  第 45 行: 执行 10001 次
  第 46 行: 执行 10000 次
  第 44 行: 执行 1 次
```

解释：`for` 行执行 n+1 次（最后一次判断迭代结束）、循环体行执行 n 次、初始化行 1 次——执行次数与循环深度直接对应，最热的行就是优化目标（比如把循环换成 `sum(i * i for i in range(n))` 或向量化计算）。

💡 提示：这是教学版工具。生产环境请用 `cProfile`（函数级）或 `py-spy`/`scalene`（行级、低开销），它们基于采样而非逐行回调，开销小得多。

8. **如何用 `sys.settrace` 实现一个简单的代码覆盖率工具？**
   - 提示：跟踪行号执行情况

**参考答案**

原理分两步：**记录执行过的行**（trace 回调里收集 `frame.f_lineno`）+ **求出所有可执行的行**（用 `dis.findlinestarts` 从字节码反推行号），两者相除就是覆盖率。

```python
import sys
import dis


def classify(x):
    if x > 0:
        return "正数"
    elif x == 0:
        return "零"
    else:
        return "负数"


class LineCoverage:
    """基于 sys.settrace 的行覆盖率工具"""

    def __init__(self):
        self.hit = set()          # 记录 (文件名, 行号)

    def _tracer(self, frame, event, arg):
        if event == 'line':       # 每执行一行就触发一次
            self.hit.add((frame.f_code.co_filename, frame.f_lineno))
        return self._tracer

    def run(self, func, *args):
        sys.settrace(self._tracer)
        try:
            func(*args)
        finally:
            sys.settrace(None)    # 用完必须关闭，否则严重拖慢程序

    def report(self, func):
        code = func.__code__
        # findlinestarts 给出字节码对应的所有可执行行号
        # 排除 def 所在行（函数定义在导入时执行，不属于函数体）
        all_lines = {ln for _, ln in dis.findlinestarts(code)
                     if ln != code.co_firstlineno}
        hit_lines = {ln for fn, ln in self.hit if fn == code.co_filename}
        covered = all_lines & hit_lines
        missed = sorted(all_lines - hit_lines)
        print(f"{func.__name__}: 覆盖 {len(covered)}/{len(all_lines)} 行"
              f" = {len(covered) / len(all_lines):.0%}")
        print(f"未覆盖的行号: {missed}")


cov = LineCoverage()
cov.run(classify, 5)     # 只走「正数」分支
cov.run(classify, -3)    # 只走「负数」分支
cov.report(classify)     # 「零」分支没测到 → 覆盖率不是 100%
```

预期输出（行号以本段代码为准，`return "零"` 在第 9 行）：

```
classify: 覆盖 4/5 行 = 80%
未覆盖的行号: [9]
```

解释：函数体共 5 个可执行行（`if`、正数 `return`、`elif`、零 `return`、负数 `return`），测试只走了正数和负数分支，`return "零"` 没执行到，所以覆盖率 80%，工具准确指出了遗漏的行。这正是 `coverage.py` 的核心原理（它额外处理了分支覆盖、多文件汇总等）。

⚠️ 注意：`else:` 这类纯跳转行没有对应字节码，不计入可执行行；`sys.settrace` 只跟踪当前线程，多线程程序需要给每个线程单独设置。

---

## 6. 本日小结

| 主题 | 关键要点 |
|------|---------|
| 字节码 | Python 编译的中间表示，比源代码更紧凑高效 |
| dis 模块 | 内置的字节码反汇编工具 |
| Code Object | 存储编译结果的数据结构 |
| 栈帧 | 函数调用的执行上下文 |
| PyObject | 所有对象的 C 层基础结构 |
| 引用计数 | 主要的内存管理机制 |
| 分代 GC | 处理循环引用的补充机制 |
| pymalloc | 高效的内存分配器 |

---

> **明日预告**：Day 099 — 扩展 Python（Cython、Pybind11、混合编程）
