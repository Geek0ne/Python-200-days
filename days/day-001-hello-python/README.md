# Day 001 — Hello, Python! 🐍

> **目标**：了解 Python 是什么，搭建开发环境，编写第一个程序，理解代码执行过程。

---

## 1. Python 是什么？

### 概念解释

Python 是一种**高级、解释型、通用编程语言**，由 Guido van Rossum 于 1991 年首次发布。

```
┌─────────────────────────────────────────────────────────┐
│                     Python 的特点                        │
├──────────────┬──────────────────────────────────────────┤
│    特点      │                  说明                     │
├──────────────┼──────────────────────────────────────────┤
│  简洁易读    │ 语法接近自然语言，代码块用缩进表示        │
│  解释执行    │ 无需编译，逐行解释执行，开发效率高        │
│  动态类型    │ 变量类型在运行时确定，无需声明类型        │
│  自动内存    │ 有垃圾回收机制（GC），无需手动管理内存    │
│  胶水语言    │ 可以轻松调用 C/C++ 等语言写的库           │
│  跨平台      │ Windows/Linux/macOS 都能跑                │
└──────────────┴──────────────────────────────────────────┘
```

### 为什么选择 Python？

```
当前最热门应用领域：

  Web开发        ─── Django / Flask / FastAPI
  数据科学       ─── NumPy / Pandas / Matplotlib
  人工智能/ML    ─── PyTorch / TensorFlow / scikit-learn
  自动化运维     ─── Ansible / Fabric / Paramiko
  爬虫           ─── Scrapy / Requests / BeautifulSoup
  游戏开发       ─── Pygame
  嵌入式/RPA     ─── MicroPython / Automation
```

---

## 2. 环境搭建

### 安装 Python

**检查是否已安装：**

```bash
python3 --version
# 输出示例: Python 3.11.5
```

如果未安装，可以从 [python.org](https://python.org) 下载，或者使用包管理器：

```bash
# macOS (Homebrew)
brew install python3

# Ubuntu/Debian
sudo apt install python3 python3-pip

# Windows
# 从 python.org 下载安装包，安装时勾选 "Add Python to PATH"
```

### 🏠 你的开发环境

我们来体验三种运行 Python 的方式：

#### 方式一：交互式解释器（REPL）

```bash
python3
```

进入后：
```python
>>> print("Hello, Python!")
Hello, Python!
>>> 1 + 2 + 3
6
>>> exit()
```

**REPL 原理图解：**

```
┌─────────────────────────────────────────────────────┐
│                  Python REPL 流程                     │
│                                                      │
│  你输入代码                                           │
│      │                                                │
│      ▼                                                │
│  Python 解释器读取代码 (Read)                        │
│      │                                                │
│      ▼                                                │
│  解析为抽象语法树 (Parse)                             │
│      │                                                │
│      ▼                                                │
│  编译为字节码 (Compile)                               │
│      │                                                │
│      ▼                                                │
│  CPython 虚拟机执行 (Evaluate)                        │
│      │                                                │
│      ▼                                                │
│  打印结果 (Print) ──→ 回到 ">>>" 等待下一行           │
└─────────────────────────────────────────────────────┘
```

#### 方式二：脚本文件

创建 `hello.py`：
```python
print("Hello, Python!")
```

运行：
```bash
python3 hello.py
# 输出: Hello, Python!
```

#### 方式三：VS Code / IDE

推荐编辑器：
- **VS Code** + Python 扩展（免费、功能强）
- **PyCharm** Community/Professional
- **Thonny**（新手友好）

---

## 3. 你的第一个 Python 程序

### Hello World 的多种写法

```python
# 最简单版本
print("Hello, World!")

# 带变量的版本
message = "Hello, World!"
print(message)

# 多行字符串
print("""
╔══════════════════════╗
║   Hello, Python!     ║
║   欢迎来到 Python    ║
╚══════════════════════╝
""")

# 格式化输出
name = "Python"
print(f"Hello, {name}! 版本: 3.x")
```

---

## 4. 代码执行流程原理解析

### Python 程序的完整生命周期

```
┌─────────────────────────────────────────────────────────┐
│                 Python 执行全过程                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  源代码 (.py 文件)                                       │
│      │                                                   │
│      ▼                                                   │
│  ┌─────────────────────────────────────────┐             │
│  │           词法分析 (Lexer)               │             │
│  │  将源代码拆分成 Token 流                  │             │
│  │  "print(1+2)" → [NAME, LPAR, NUM,       │             │
│  │                  PLUS, NUM, RPAR]        │             │
│  └─────────────────────────────────────────┘             │
│      │                                                   │
│      ▼                                                   │
│  ┌─────────────────────────────────────────┐             │
│  │           语法分析 (Parser)               │             │
│  │  Token 流 → 抽象语法树 (AST)             │             │
│  │  检查语法是否正确                         │             │
│  └─────────────────────────────────────────┘             │
│      │                                                   │
│      ▼                                                   │
│  ┌─────────────────────────────────────────┐             │
│  │           编译 (Compiler)                │             │
│  │  AST → 字节码 (Bytecode)                 │             │
│  │  生成 .pyc 缓存文件 (__pycache__)       │             │
│  └─────────────────────────────────────────┘             │
│      │                                                   │
│      ▼                                                   │
│  ┌─────────────────────────────────────────┐             │
│  │        CPython 虚拟机 (V.M.)             │             │
│  │  逐条执行字节码指令                       │             │
│  │  管理栈帧、调用函数、分配对象              │             │
│  └─────────────────────────────────────────┘             │
│      │                                                   │
│      ▼                                                   │
│      输出结果                                              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 用代码验证这个过程

```python
# 查看字节码
import dis

def greet(name):
    msg = f"Hello, {name}!"
    print(msg)
    return len(msg)

# dis 模块反汇编函数，显示字节码指令
dis.dis(greet)
```

运行输出（你会在终端看到类似这样的指令）：
```
  2           0 LOAD_FAST                0 (name)
              2 FORMAT_VALUE          0
              4 LOAD_CONST               1 ('Hello, ')
              6 BUILD_STRING             2
              8 STORE_FAST               1 (msg)

  3          10 LOAD_GLOBAL              0 (print)
             12 LOAD_FAST                1 (msg)
             14 CALL_FUNCTION            1
             16 POP_TOP

  4          18 LOAD_FAST                1 (msg)
             20 LOAD_GLOBAL              1 (len)
             22 CALL_FUNCTION            1
             24 RETURN_VALUE
```

---

## 5. Python 语法速览（第一次预览）

```python
# ─── 这是注释（# 后面都是注释）───

# 变量：不需要声明类型
name = "Python"           # 字符串
version = 3.11            # 浮点数
year = 1991               # 整数
is_fun = True             # 布尔值

# 数据结构
numbers = [1, 2, 3, 4, 5]        # 列表
person = {"name": "Alice", "age": 30}  # 字典

# 条件判断
if year < 2000:
    print("上个世纪")
else:
    print("本世纪")

# 循环
for n in numbers:
    print(n, end=" ")     # 输出: 1 2 3 4 5

# 函数
def add(a, b):
    """返回两数之和"""
    return a + b

# 调用函数
result = add(3, 5)
print(f"3 + 5 = {result}")   # 输出: 3 + 5 = 8
```

---

## 6. print() 函数深入

`print()` 是 Python 最常用的内置函数之一。

```python
# ─── 基本用法 ───
print("Hello")                              # Hello
print(42)                                   # 42
print(3.14)                                 # 3.14

# ─── 多个参数（自动空格分隔）───
print("Hello", "World")                     # Hello World
print("答案", "是", 42)                     # 答案 是 42

# ─── sep 参数（自定义分隔符）───
print("2024", "01", "15", sep="-")          # 2024-01-15
print("A", "B", "C", sep=" | ")             # A | B | C

# ─── end 参数（不换行）───
print("正在下载", end="...")
print(" 完成!")                              # 正在下载... 完成!

# ─── 格式化输出 ───
name, score = "小明", 95.5
print(f"{name} 的分数是 {score} 分")         # f-string（推荐）
print("{} 的分数是 {} 分".format(name, score))  # format()
print("%s 的分数是 %.1f 分" % (name, score))     # % 格式化
```

---

## 7. 实战：完整的第一个程序

创建一个名为 `greeting.py` 的文件：

```python
#!/usr/bin/env python3
"""
我的第一个 Python 程序
功能：获取用户输入并生成个性化问候
"""

import datetime

def main():
    """程序入口"""
    # 获取用户信息
    name = input("你好！请问你叫什么名字？ ")
    
    # 获取当前时间
    now = datetime.datetime.now()
    hour = now.hour
    
    # 根据时间段判断问候语
    if 5 <= hour < 12:
        greeting = "早上好"
    elif 12 <= hour < 18:
        greeting = "下午好"
    else:
        greeting = "晚上好"
    
    # 计算今年年份
    year = now.year
    
    # 输出个性化问候
    print("\n" + "=" * 40)
    print(f"{greeting}，{name}！")
    print(f"欢迎来到 {year} 年的 Python 世界！")
    print(f"这是你的第一个 Python 程序，恭喜你迈出了第一步！")
    print("=" * 40)
    
    # 显示一些系统信息
    import sys
    print(f"\n📊 系统信息")
    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"平台: {sys.platform}")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# 当文件直接运行时执行
if __name__ == "__main__":
    main()
```

**运行结果示例：**
```
你好！请问你叫什么名字？ 聂生

========================================
下午好，聂生！
欢迎来到 2026 年的 Python 世界！
这是你的第一个 Python 程序，恭喜你迈出了第一步！
========================================

📊 系统信息
Python 版本: 3.11.5
平台: linux
当前时间: 2026-05-26 14:30:00
```

---

## 8. 这一天的核心概念卡片

```
┌─────────────────────────────────────────────────────────┐
│                    📝 核心概念速记                        │
├───────────────────┬─────────────────────────────────────┤
│  解释型语言       │ 代码无需编译，由解释器逐行执行        │
│  REPL             │ Read-Eval-Print Loop 交互式编程      │
│  字节码           │ Python 代码编译后的中间指令           │
│  CPython          │ 官方 Python 解释器实现               │
│  print()          │ 输出函数，最常用的调试工具            │
│  input()          │ 输入函数，从控制台读取用户输入        │
│  f-string         │ 格式化字符串，用 f"..." 语法         │
│  __name__         │ 模块名，等于 "__main__" 时表示直接运行 │
└───────────────────┴─────────────────────────────────────┘
```

---

## 9. 练习

### 基础练习

1. 编写一个程序，输出一个由 `*` 组成的三角形：
```
   *
  ***
 *****
*******
```

2. 使用 `print()` 的 `sep` 参数，输出以下格式的日期：`今日是 2026 年 05 月 26 日`

3. 编写程序询问用户的年龄，然后回答：`你出生于 20XX 年`

### 进阶练习

4. 使用 `dis` 模块反汇编一个包含 `if` 语句的函数，观察字节码的区别

5. 写一个 "记事本" 程序，让用户输入多条笔记，然后全部输出

---

## 10. 思考题

> 🤔 Python 为什么被称为"胶水语言"？这与其他编程语言的设计哲学有什么关系？
>
> 🤔 为什么 Python 使用缩进来表示代码块，而不是大括号 `{}`？这带来了什么优缺点？
>
> 🤔 查看 `sys.getsizeof(1)` 和 `sys.getsizeof("a")`，为什么一个整数占用这么多内存？

---

**📚 扩展阅读：**
- [Python 官方教程](https://docs.python.org/zh-cn/3/tutorial/)
- [PEP 8 — Python 代码风格指南](https://pep8.org/)
- [CPython 源码解析](https://github.com/python/cpython)

---

> **今日金句：** "Talk is cheap. Show me the code." — Linus Torvalds
