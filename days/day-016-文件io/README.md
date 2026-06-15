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

---

## 四、文件指针与 seek/tell

### 4.1 文件指针概念

文件指针（文件位置指示器）记录当前读写位置。每次读写操作后，指针自动向后移动。

```
文件内容:  H e l l o   W o r l d  \n
字节位置:  0 1 2 3 4 5 6 7 8 9 10 11
                   ↑
               指针位置 (pos=5)
```

### 4.2 `tell()` — 获取当前位置

```python
with open("data.txt", "r") as f:
    print(f.tell())   # 0 — 在开头
    f.read(5)
    print(f.tell())   # 5 — 读了5个字符后
    f.read()
    print(f.tell())   # 文件总大小 — 读完了
```

### 4.3 `seek()` — 移动指针

```python
f.seek(offset, whence)

# whence 参数:
#   os.SEEK_SET (0) — 从文件开头计算 (默认)
#   os.SEEK_CUR (1) — 从当前位置计算
#   os.SEEK_END (2) — 从文件末尾计算
```

```python
with open("data.txt", "r") as f:
    f.seek(10)              # 移动到第10个字符
    print(f.read(5))        # 读取5个字符

    f.seek(0, os.SEEK_SET)  # 回到开头
    print(f.read(5))        # 重新读取前5个字符

    f.seek(-5, os.SEEK_END) # 移动到末尾前5个字符
    print(f.read())         # 读取最后5个字符
```

### 4.4 二进制文件中的 seek

二进制模式下，`seek` 可以自由使用 `SEEK_CUR` 和 `SEEK_END`：

```python
with open("data.bin", "rb") as f:
    # 末尾前10字节
    f.seek(-10, 2)        # 2 = SEEK_END
    print(f.read())

    # 当前位置后移20字节
    f.seek(20, 1)         # 1 = SEEK_CUR
```

**注意：文本模式下 `seek` 受限！**

文本模式下 `seek(offset, whence)` 只有在以下两种情况有效：
1. `seek(0, SEEK_SET)` — 回到开头
2. `seek(pos, SEEK_SET)` — 从开头移动到某个已知位置（`tell()` 返回值）

原因是 UTF-8 编码中字符长度可变，无法从字节偏移直接计算字符偏移。

---

## 五、编码问题与处理

### 5.1 常见编码

| 编码 | 说明 | 字节数/字符 |
|------|------|------------|
| ASCII | 仅支持英文/数字/符号 | 1 字节 |
| UTF-8 | 通用编码，兼容 ASCII | 1-4 字节 |
| UTF-16 | Unicode 编码 | 2-4 字节 |
| GBK | 中文编码（简体中文） | 1-2 字节 |
| ISO-8859-1 | 西欧语言 | 1 字节 |

### 5.2 编码问题典型案例

```python
# 编码不匹配 → UnicodeDecodeError
with open("chinese.txt", "r", encoding="ascii") as f:
    content = f.read()
# UnicodeDecodeError: 'ascii' codec can't decode byte 0xe4

# 指定正确编码 → 正常工作
with open("chinese.txt", "r", encoding="utf-8") as f:
    content = f.read()

# 读取未知编码的文件 → 尝试推断
import chardet
with open("unknown.txt", "rb") as f:
    raw = f.read()
    result = chardet.detect(raw)
    encoding = result["encoding"]
    content = raw.decode(encoding)
```

### 5.3 编码错误处理策略

```python
# 严格模式（默认）— 遇到非法编码抛出异常
with open("data.txt", "r", encoding="utf-8", errors="strict") as f:
    pass

# 忽略模式 — 跳过无法解码的字符（可能丢失数据！）
with open("data.txt", "r", encoding="utf-8", errors="ignore") as f:
    pass

# 替换模式 — 用 ? 替换无法解码的字符
with open("data.txt", "r", encoding="utf-8", errors="replace") as f:
    pass

# 编码时替代
with open("output.txt", "w", encoding="ascii", errors="xmlcharrefreplace") as f:
    f.write("你好")  # 写入 &#20320;&#22909;
```

### 5.4 BOM（字节顺序标记）

UTF-16 和 UTF-8 with BOM 编码的文件开头有 BOM 标记：

```
UTF-8 with BOM:    EF BB BF    (3 bytes)
UTF-16 LE:         FF FE       (2 bytes)
UTF-16 BE:         FE FF       (2 bytes)
```

```python
# 跳过 BOM 读取
import codecs
with open("bom_file.txt", "r", encoding="utf-8-sig") as f:
    content = f.read()  # BOM 自动被移除

---

## 六、常见文件操作陷阱与避坑

### 🚫 陷阱 1：大文件直接读取

```python
# ❌ 不要这样！内存会爆
with open("huge_file.txt") as f:
    content = f.read()  # 整个文件读入内存

# ✅ 逐行/逐块读取
with open("huge_file.txt") as f:
    for line in f:          # 迭代器方式，只存一行在内存
        process(line)

# 或分块读取
with open("huge_file.bin", "rb") as f:
    while chunk := f.read(8192):  # 每次读 8KB
        process(chunk)
```

### 🚫 陷阱 2：跨平台换行符

```python
# 在 Windows 上用二进制模式写入文本
with open("data.txt", "wb") as f:
    f.write("line1\nline2\n".encode())  # ❌ Windows 上可能显示为单行

# ✅ 用文本模式让 Python 处理换行符
with open("data.txt", "w") as f:
    f.write("line1\nline2\n")  # Windows → \r\n, Linux → \n
```

### 🚫 陷阱 3：忘记编码

```python
# ❌ 依赖默认编码（不同系统可能不同）
with open("data.txt") as f:     # Windows: gbk, Linux: utf-8
    ...

# ✅ 显式指定编码
with open("data.txt", encoding="utf-8") as f:
    ...
```

### 🚫 陷阱 4：写入后立即读取

```python
# ❌ 写入后指针在末尾，读取不到内容
with open("data.txt", "w+") as f:
    f.write("Hello")
    content = f.read()  # 空字符串！

# ✅ 写入后 seek 到开头
with open("data.txt", "w+") as f:
    f.write("Hello")
    f.seek(0)
    content = f.read()  # "Hello"
```

### 🚫 陷阱 5：多进程写冲突

```python
# 使用文件锁防止并发写入
import fcntl

with open("shared.log", "a") as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    f.write("important data\n")
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```
```
```
