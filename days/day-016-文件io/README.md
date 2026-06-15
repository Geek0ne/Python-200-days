# Day 016 — 文件 I/O

> **Phase 2: 核心编程概念** | 文件输入输出是编程中最基础也最重要的操作之一。Python 提供了简洁而强大的文件操作接口，从简单的文本读取到复杂的二进制文件处理，都能优雅地完成。

---

## 📖 学习目标

- 掌握 Python 文件操作的核心 API
- 理解不同打开模式的适用场景
- 熟练使用 `with` 语句进行安全的文件操作
- 区分文本模式与二进制模式
- 理解文件指针与编码处理
- 能够编写实用的文件处理工具

---

## 一、文件打开模式详解

### 1.1 基本模式

Python 的 `open()` 函数支持不同的模式标志，决定了文件的打开方式和行为：

| 模式 | 含义 | 文件指针位置 | 文件不存在时 | 覆盖写入 |
|------|------|-------------|-------------|---------|
| `r` | 只读（文本） | 开头 | 抛出 `FileNotFoundError` | ❌ |
| `w` | 只写（文本） | 开头（清空） | 创建新文件 | ✅ |
| `a` | 追加（文本） | 末尾 | 创建新文件 | ❌（追加） |
| `x` | 排他性创建 | 开头 | 创建新文件 | ❌ |
| `b` | 二进制模式 | — | — | — |
| `t` | 文本模式（默认） | — | — | — |
| `+` | 读写模式 | — | — | — |

### 1.2 组合模式详解

| 组合模式 | 含义 | 指针位置 | 典型场景 |
|---------|------|---------|---------|
| `rb` | 二进制只读 | 开头 | 读取图片、音频等 |
| `wb` | 二进制只写 | 开头（清空） | 写入二进制数据 |
| `ab` | 二进制追加 | 末尾 | 追加二进制数据 |
| `r+` | 文本读写 | 开头 | 读取并修改文件 |
| `w+` | 文本读写（清空） | 开头 | 读写新文件 |
| `a+` | 文本读写（追加） | 末尾 | 读取并追加 |
| `rb+` | 二进制读写 | 开头 | 修改二进制文件 |

### 1.3 深入理解打开模式

```
打开模式 = 基本操作 + 附加标志

基本操作:     r    w    a    x
文件类型:          t (文本,默认)    b (二进制)
附加操作:               + (读写)
示例:       rb, wb, r+, w+b, a+b


open() 底层调用流程:

Python 代码
  │
  ▼
open(file, mode, ...)
  │
  ├─► 模式解析器解析 mode 字符串
  │     "r+b"  →  O_RDWR | O_BINARY
  │
  ├─► 系统调用 os.open()
  │     根据标志打开文件描述符 (fd)
  │
  └─► 根据是否带 b 包装文件对象
        ┌─ 文本模式: TextIOWrapper (处理编码/换行)
        └─ 二进制模式: BufferedReader/BufferedWriter
```

### 1.4 `x` 模式详解

`x` 模式（排他性创建）非常适合**避免文件覆盖**的场景：

```python
try:
    with open("output.txt", "x") as f:
        f.write("新内容")
except FileExistsError:
    print("文件已存在，不会覆盖")
```

---

## 二、上下文管理器与 `with` 语句

### 2.1 为什么需要 `with`

传统的文件操作需要手动管理资源：

```python
# ❌ 不推荐 — 容易忘记关闭文件
f = open("data.txt", "r")
content = f.read()
f.close()  # 如果中间发生异常，这行不会执行！
```

使用 `with` 语句自动管理资源：

```python
# ✅ 推荐 — 自动关闭
with open("data.txt", "r") as f:
    content = f.read()
# 离开缩进块后自动调用 f.close()
```

### 2.2 `with` 语句的工作原理

`with` 语句依赖于**上下文管理协议**，即 `__enter__` 和 `__exit__` 方法：

```python
# with 语句的等价实现
f = open("data.txt", "r")  # __init__
try:
    f.__enter__()           # 进入上下文
    content = f.read()
finally:
    f.__exit__(...)         # 发生异常也会执行
```

执行流程：

```
with open(...) as f:     ← 调用 f.__enter__()
    ┌─────────────────────┐
    │   执行代码块        │
    │   正常或发生异常    │
    └──────┬──────────────┘
           ▼
    f.__exit__(exc_type, exc_val, exc_tb)
           │
      ├─ 如果无异常: ⭐ 返回 True 或 None
      ├─ 如果有异常: 返回 True → 吞掉异常
      │                返回 False → 继续传播异常
      └─ 无论如何: 都会调用 f.close()
```

### 2.3 自定义上下文管理器

```python
class FileManager:
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode

    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        return False

with FileManager("data.txt", "r") as f:
    print(f.read())
```

### 2.4 使用 `contextlib` 简化

```python
from contextlib import contextmanager

@contextmanager
def open_file(filename, mode):
    f = open(filename, mode)
    try:
        yield f
    finally:
        f.close()

with open_file("data.txt", "r") as f:
    content = f.read()
```

---

## 三、文本文件 vs 二进制文件

### 3.1 核心区别

| 特性 | 文本模式 (`t`) | 二进制模式 (`b`) |
|------|---------------|-----------------|
| 数据类型 | `str` | `bytes` |
| 编码处理 | 自动编码/解码 | 原始字节 |
| 换行符 | 平台自动转换<br>`\n` ↔ `\r\n` | 不转换 |
| 适用场景 | TXT, CSV, JSON, HTML | 图片, 音频, 视频, 压缩包 |
| 读取单元 | 字符（可能多字节） | 字节 |

### 3.2 换行符在不同平台的处理

```
写入文本时:
  Python:   "hello\nworld"
  Windows:  "hello\r\nworld"   ← 自动转换 \n → \r\n
  Linux:    "hello\nworld"     ← 不变

读取文本时:
  Windows:  "hello\r\nworld" → "hello\nworld"  ← 自动转换 \r\n → \n
  Linux:    "hello\nworld"   → "hello\nworld"  ← 不变

二进制模式:
  任何平台: bytes 原样读写，不处理换行符
```

### 3.3 什么时候用二进制

```python
# 读取图片 → 必须用二进制
with open("photo.jpg", "rb") as f:
    data = f.read()  # bytes 对象

# 读取 JSON → 用文本（默认）
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)  # str 对象

# 处理压缩文件 → 二进制
import gzip
with gzip.open("archive.gz", "rb") as f:
    content = f.read()
```
