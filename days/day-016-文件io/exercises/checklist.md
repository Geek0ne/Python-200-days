# Day 016 — 文件 I/O 检查清单与练习题

---

## ✅ 知识掌握检查清单

### 基础概念
- [ ] 理解文件操作的三个基本步骤：打开 → 读写 → 关闭
- [ ] 理解 `open()` 函数的完整签名与参数
- [ ] 能区分 `r/w/a/x` 四种基本模式的差异
- [ ] 理解 `+` 修饰符的作用
- [ ] 理解 `t` 和 `b` 模式的区别
- [ ] 知道各种组合模式的适用场景（r+, w+, a+, rb, wb 等）

### with 语句
- [ ] 理解 `with` 语句为什么能自动管理资源
- [ ] 理解上下文管理协议（`__enter__` / `__exit__`）
- [ ] 能自己实现上下文管理器（类方式）
- [ ] 能用 `@contextmanager` 装饰器简化实现
- [ ] 理解 `__exit__` 的返回值对异常传播的影响

### 文件读写方法
- [ ] 掌握 `read()`, `readline()`, `readlines()` 的区别和使用场景
- [ ] 掌握 `write()`, `writelines()` 的用法
- [ ] 理解为什么大文件需要用 `for line in f` 或分块读取
- [ ] 知道 `flush()` 的作用和何时需要调用

### 文件指针
- [ ] 理解文件指针的概念
- [ ] 能正确使用 `tell()` 获取当前指针位置
- [ ] 掌握 `seek(offset, whence)` 的三种模式
- [ ] 知道文本模式下 seek 的局限性

### 编码处理
- [ ] 了解常见编码（UTF-8, GBK, ASCII, Latin-1）
- [ ] 知道 `encoding` 参数的重要性
- [ ] 理解 `UnicodeDecodeError` 的产生原因
- [ ] 掌握 errors 参数的五种处理策略
- [ ] 了解什么是 BOM 以及如何处理
- [ ] 知道如何使用 chardet 检测编码

### 文件对象
- [ ] 知道文件对象的常用属性（name, mode, encoding, closed）
- [ ] 知道 `fileno()`, `truncate()`, `seekable()` 等方法的用途

### 陷阱与最佳实践
- [ ] 知道大文件不能直接用 `read()` 读取
- [ ] 知道跨平台换行符的处理方式
- [ ] 知道 w+ 模式下写入后需要 `seek(0)` 才能读取
- [ ] 知道 x 模式用于排他性创建
- [ ] 知道需要显式指定 encoding 参数

---

## 📝 快速回顾题

### 选择题

**1.** 下列哪个模式会清空已存在的文件内容？
- A. `r`
- B. `w`
- C. `a`
- D. `x`

**2.** `with open("file.txt", "r+") as f:` 打开文件后，文件指针在什么位置？
- A. 文件开头
- B. 文件末尾
- C. 取决于文件大小
- D. 文件中间

**3.** 二进制模式下，`f.read()` 返回什么类型？
- A. `str`
- B. `bytes`
- C. `bytearray`
- D. `list`

**4.** `with` 语句在退出时一定会执行文件对象的哪个方法？
- A. `__del__`
- B. `__exit__`
- C. `flush`
- D. `truncate`

**5.** 以下哪种方式最适合读取 5GB 的大日志文件？
- A. `content = f.read()`
- B. `lines = f.readlines()`
- C. `for line in f:`
- D. `content = f.read(1024*1024*1024)`

### 判断题

- [ ] `w+` 模式可以读取文件，但需要先 `seek()` 到合适位置
- [ ] 文本模式下 `seek(-5, 2)` 永远有效
- [ ] `encoding="utf-8"` 是 Python 3 的默认编码，可以不指定
- [ ] 二进制模式下读取文件不会自动处理换行符
- [ ] `x` 模式如果文件已存在，会抛出 `FileExistsError`

---

## 🛠️ 动手练习题

### 基础题

**练习 1：文件复制工具**
编写一个函数 `copy_file(src, dst)`，将源文件完整复制到目标文件。要求：
- 使用 `with` 语句
- 支持任意文件类型（文本和二进制）
- 对大文件使用分块读取
- 返回复制的字节数

<details>
<summary>参考思路</summary>

```python
def copy_file(src, dst, chunk_size=65536):
    with open(src, "rb") as s, open(dst, "wb") as d:
        total = 0
        while chunk := s.read(chunk_size):
            d.write(chunk)
            total += len(chunk)
    return total
```
</details>

---

**练习 2：行号阅读器**
编写一个函数 `print_with_line_numbers(filename)`，读取文件并在每行前加上行号输出：

```
    1 | Hello, World!
    2 | 这是第二行。
    3 | 第三行内容。
```

<details>
<summary>参考思路</summary>

```python
def print_with_line_numbers(filename):
    with open(filename, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            print(f"{i:>5} | {line}", end="")
```
</details>

---

**练习 3：文件统计器**
编写一个函数 `file_stats(filename)`，返回文件的基本统计信息：
- 文件大小（字节）
- 行数（文本文件）
- 字符数（文本文件）
- 单词数（粗略统计，按空格分割）
- 最长行的长度

<details>
<summary>参考思路</summary>

```python
def file_stats(filename):
    stats = {"size": 0, "lines": 0, "chars": 0, "words": 0, "max_line_length": 0}
    stats["size"] = os.path.getsize(filename)
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            stats["lines"] += 1
            stats["chars"] += len(line)
            stats["words"] += len(line.split())
            stats["max_line_length"] = max(stats["max_line_length"], len(line))
    return stats
```
</details>

---

### 进阶题

**练习 4：简易 CSV 解析器**
实现一个简单的 CSV 读取器（不使用 csv 模块），支持：
- 按行读取
- 根据逗号分隔字段
- 处理带引号的字段（字段内的逗号不应作为分隔符）
- 返回列表的列表

示例 CSV 内容：
```csv
Name,Age,City
Alice,28,"New York, NY"
Bob,35,Shanghai
```

<details>
<summary>参考思路</summary>

```python
def parse_csv(filename):
    rows = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fields = []
            current = ""
            in_quotes = False
            for ch in line:
                if ch == '"':
                    in_quotes = not in_quotes
                elif ch == "," and not in_quotes:
                    fields.append(current.strip())
                    current = ""
                else:
                    current += ch
            fields.append(current.strip())
            rows.append(fields)
    return rows
```
</details>

---

**练习 5：文件差异比较器**
实现一个简单的文件差异比较工具 `diff_files(file1, file2)`，逐行比较两个文本文件，输出：
- 相同的行数
- 不同的行数
- 仅存在于文件 1 的行
- 仅存在于文件 2 的行
- 内容不同但行号相同的行

<details>
<summary>参考思路</summary>
逐行读取两个文件，使用 `difflib` 模块或手动比较。
</details>

---

**练习 6：断点续传下载器（模拟）**
设计一个支持断点续传的下载器模拟程序：
- `start_download(url, filepath)` — 开始下载
- `resume_download(filepath)` — 从中断处续传
- 使用 `seek()` 和文件大小记录已下载进度
- 模拟下载进度输出

<details>
<summary>参考思路</summary>
用文件大小模拟已下载进度，利用 `seek()` 定位续传位置。
</details>

---

### 挑战题

**练习 7：INI 配置文件解析器**
实现一个完整的 INI 配置解析器（不使用 configparser 模块），支持：
- `[section]` 段落
- `key = value` 配置项
- `;` 和 `#` 注释
- 空格忽略
- 引用值（带引号的字符串）
- 保存/写入修改后的配置

<details>
<summary>参考思路</summary>
逐行解析，维护一个嵌套字典 `{section: {key: value}}`。
</details>

---

**练习 8：日志文件轮转器**
实现一个日志轮转工具 `rotate_log(filename, max_size, backup_count)`：
- 当日志文件超过 `max_size` 时自动轮转
- 保留 `backup_count` 个历史备份
- 命名规则：`app.log` → `app.log.1` → `app.log.2` → ...
- 自动检测文件大小和编码

<details>
<summary>参考思路</summary>
检查文件大小 → 将已存在的备份文件重命名（序号递增）→ 创建新日志文件。
</details>

---

## 🚀 实战项目

### 项目 1：文件整理工具
创建一个命令行工具，根据以下规则整理指定目录中的文件：

```bash
python organize.py /path/to/downloads --sort-by-type --move
```

功能要求：
- 按文件类型（图片、文档、视频、压缩包等）分类移动
- 支持规则可配置（通过 JSON 配置文件）
- 支持预览模式（--dry-run，只显示要移动的文件，不实际执行）
- 输出操作摘要报告

### 项目 2：文本日志浏览器
创建一个终端交互式日志浏览器：

```bash
python log_browser.py app.log --interactive
```

功能要求：
- 分页显示（上一页/下一页）
- 按级别过滤
- 搜索（/ 开启搜索模式）
- 统计视图（显示图表）
- 实时模式（跟踪文件末尾追加的内容）

---

## 📚 扩展阅读

- [Python 官方文档: 文件对象](https://docs.python.org/3/library/io.html)
- [PEP 343: The "with" Statement](https://peps.python.org/pep-0343/)
- [Python Unicode 指南](https://docs.python.org/3/howto/unicode.html)
- [chardet: 字符编码检测库](https://github.com/chaoshui/chardet)
- [Real Python: Reading and Writing Files in Python](https://realpython.com/read-write-files-python/)
