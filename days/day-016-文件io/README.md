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

---

## 七、性能对比：不同读取方式

```python
import time

# 测试文件：100MB 文本
filename = "test_100mb.txt"

# 方法 1：read() 全量读取
start = time.time()
with open(filename) as f:
    data = f.read()
print(f"read() 全量: {time.time()-start:.3f}s")

# 方法 2：readlines()
start = time.time()
with open(filename) as f:
    lines = f.readlines()
print(f"readlines(): {time.time()-start:.3f}s")

# 方法 3：逐行迭代
start = time.time()
with open(filename) as f:
    for line in f:
        pass
print(f"迭代器: {time.time()-start:.3f}s")

# 方法 4：分块读取
start = time.time()
with open(filename) as f:
    while chunk := f.read(65536):
        pass
print(f"64KB 块: {time.time()-start:.3f}s")
```

**典型结果：**

| 方式 | 内存 | 速度 | 推荐场景 |
|------|------|------|---------|
| `read()` | ❌ 高 | ⭐ 快 | 小文件 (<100MB) |
| `readlines()` | ❌ 更高 | ⭐⭐ 更快 | 需要索引访问行 |
| `for line in f` | ✅ 低 | ⭐ 快 | 大文件逐行处理 |
| `read(chunk_size)` | ✅ 可控 | ⭐⭐⭐ 最快 | 二进制大文件 |

---

## 八、文件对象方法与属性速查

### 8.1 读取方法

| 方法 | 说明 | 示例 |
|------|------|------|
| `read(n)` | 读取 n 个字符/字节 | `f.read(100)` |
| `read()` | 读取全部内容 | `content = f.read()` |
| `readline()` | 读取一行（含换行符） | `line = f.readline()` |
| `readlines()` | 读取所有行，返回列表 | `lines = f.readlines()` |
| 迭代 | 逐行迭代（推荐大文件） | `for line in f:` |

### 8.2 写入方法

| 方法 | 说明 | 示例 |
|------|------|------|
| `write(s)` | 写入字符串/字节 | `f.write("Hello")` |
| `writelines(lines)` | 写入字符串列表 | `f.writelines(["a\n", "b\n"])` |
| `flush()` | 强制刷新缓冲区 | `f.flush()` |

### 8.3 属性与方法

| 属性/方法 | 说明 | 示例 |
|----------|------|------|
| `name` | 文件名 | `f.name → "data.txt"` |
| `mode` | 打开模式 | `f.mode → "r"` |
| `encoding` | 编码 | `f.encoding → "utf-8"` |
| `closed` | 是否已关闭 | `f.closed → True/False` |
| `fileno()` | 文件描述符 | `fd = f.fileno()` |
| `isatty()` | 是否终端设备 | `f.isatty()` |
| `truncate(size)` | 截断文件 | `f.truncate(100)` |
| `seekable()` | 是否支持随机访问 | `f.seekable()` |
| `readable()` | 是否可读 | `f.readable()` |
| `writable()` | 是否可写 | `f.writable()` |
| `detach()` | 分离底层二进制流 | `binary = f.detach()` |
```
```

---

## 九、思考题

1. **`with` 与写入模式的选择**：为什么推荐 `with open(...)` 而不是手动 `f.close()`？`w`、`a`、`x` 三种写入模式在「文件已存在」时分别会发生什么？如果要生成一份**绝不能覆盖已有结果**的报告，该选哪个？

**参考答案**

手动 `close()` 的问题是：一旦读写过程中抛异常，`close()` 那一行就被跳过了，文件句柄泄漏、缓冲区里的数据也可能没落盘。`with` 依赖**上下文管理协议**（`__enter__` / `__exit__`），离开代码块时无论正常结束还是异常退出都会调用 `__exit__`，等价于把 `close()` 放进 `finally`，所以更安全也更简洁。

三种写入模式对「已存在的文件」态度完全不同：

- `w`：**先清空**再写，原内容全部丢失（最危险的误操作来源）。
- `a`：保留原内容，指针固定在末尾，写入总是追加。
- `x`：**排他性创建**，文件已存在就抛 `FileExistsError`，一个字节都不动。

所以「绝不覆盖」的场景选 `x`，并捕获异常：`with open("report.txt", "x", encoding="utf-8") as f: ...`，外面套 `try/except FileExistsError` 提示用户改文件名。

⚠️ 注意：`r` 模式打开不存在的文件会抛 `FileNotFoundError`，而 `w`/`a`/`x` 会自动创建；`with` 只保证「关闭」，不保证「写对了内容」，模式选错照样丢数据。

2. **写完读不到内容（代码）**：`with open("demo.txt", "w+") as f: f.write("Hello"); print(f.read())` 为什么打印空字符串？请用代码演示文件指针的变化，并给出处理大文件时的安全读取写法。

**参考答案**

```python
import os
import tempfile

# 在系统临时目录里做实验，不会污染项目目录
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "demo.txt")

    # 陷阱：w+ 写完指针停在末尾，直接 read() 得到空字符串
    with open(path, "w+", encoding="utf-8") as f:
        f.write("Hello")
        print(repr(f.read()))       # '' —— 指针已在末尾
        f.seek(0)                   # 回到开头再读
        print(repr(f.read()))       # 'Hello'
        print(f.tell())             # 5 —— 读完指针又走到末尾

    # 追加模式 a：不清空原内容，写入永远落在末尾
    with open(path, "a", encoding="utf-8") as f:
        f.write("\nWorld")

    # 逐行迭代：内存里只留一行，适合大文件
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            print(i, repr(line))    # 行尾的 \n 会被保留
```

预期输出：

```
''
'Hello'
5
1 'Hello\n'
2 'World'
```

文件对象内部有个**文件指针**，记录「下一次读写从哪个位置开始」。`write("Hello")` 之后指针停在 5，`read()` 从 5 读到末尾自然什么都没有；`seek(0)` 把指针拨回开头才读得到内容，`tell()` 则随时报告当前位置。

大文件不要用 `read()`（一次性全进内存）或 `readlines()`（还要额外建列表），直接 `for line in f` 逐行迭代，内存占用与文件大小无关；二进制大文件用 `while chunk := f.read(65536)` 分块读。

⚠️ 注意：文本模式下 `seek` 受限，只能用 `seek(0)` 或 `seek(tell() 返回的位置)`；`seek(-5, 2)` 这种「从末尾倒数」的写法只在二进制模式（`rb`）下合法，因为 UTF-8 字符长度可变，无法按字节倒推字符位置。

3. **编码与 BOM（代码）**：同一个中文文件，用 `utf-8` 写、用 `ascii` 读会发生什么？`errors="ignore"` 和 `errors="replace"` 各付出什么代价？为什么处理 Excel 导出的 CSV 经常要用 `utf-8-sig`？

**参考答案**

```python
import os
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "cn.txt")

    # 用 UTF-8 写入中文
    with open(path, "w", encoding="utf-8") as f:
        f.write("你好，Python")

    # 用 ASCII 读同一份字节 → 解码失败
    try:
        with open(path, "r", encoding="ascii") as f:
            f.read()
    except UnicodeDecodeError as e:
        print("解码失败:", e.reason)

    # errors="ignore"：丢掉无法解码的字节（会丢数据，慎用）
    with open(path, "r", encoding="ascii", errors="ignore") as f:
        print(repr(f.read()))       # 'Python'，中文全被丢掉

    # 带 BOM 的 UTF-8：utf-8-sig 读取时自动去掉 BOM
    bom_path = os.path.join(tmp, "bom.txt")
    with open(bom_path, "w", encoding="utf-8-sig") as f:
        f.write("标题")
    with open(bom_path, "rb") as f:
        print(f.read(3))            # b'\xef\xbb\xbf' —— BOM 三字节
    with open(bom_path, "r", encoding="utf-8-sig") as f:
        print(repr(f.read()))       # '标题'
    with open(bom_path, "r", encoding="utf-8") as f:
        print(repr(f.read()))       # '\ufeff标题'，BOM 变成了一个字符
```

预期输出：

```
解码失败: ordinal not in range(128)
'Python'
b'\xef\xbb\xbf'
'标题'
'\ufeff标题'
```

磁盘上存的永远是**字节**，编码就是「字节 ↔ 字符」的翻译规则。写入用 UTF-8、读取用 ASCII，等于拿错字典翻译，遇到 `0xe4` 这类超出 ASCII 范围的字节就抛 `UnicodeDecodeError`。`errors="ignore"` 让程序不崩，但代价是**静默丢数据**（中文全没了）；`errors="replace"` 把每个坏字节换成 ``（U+FFFD），本例会得到 9 个 `` 加 `Python`，同样不可逆。二者都只适合「尽力抢救」，正确做法始终是指定对的编码。

**BOM**（字节顺序标记）是文件开头的 `EF BB BF` 三字节，Excel 导出 UTF-8 CSV 时经常带上它。用 `utf-8-sig` 读取会自动剥离；若用普通 `utf-8`，BOM 会变成字符 `\ufeff` 粘在第一个字段上，于是表头 `姓名` 变成 `\ufeff姓名`，后续按列名取值全部失败。

💡 提示：读写文本一律显式写 `encoding="utf-8"`，别依赖系统默认（Windows 中文环境常是 GBK）；图片、音频、压缩包必须用 `rb`/`wb`，二进制模式不做任何编码与换行转换。
