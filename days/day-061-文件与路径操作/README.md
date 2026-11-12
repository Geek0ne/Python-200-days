# Day 061 — 文件与路径操作

> 从 `os.path` 到 `pathlib`，Python 文件操作的现代方式

## 📋 今日学习目标

1. 掌握 `os` 模块的文件和目录操作
2. 理解 `pathlib` 的面向对象路径操作（现代推荐方式）
3. 掌握 `shutil` 的高级文件操作（复制、移动、压缩）
4. 实战：构建一个文件同步工具

---

## 一、为什么需要 pathlib？

### 传统方式的问题

```python
import os

# 路径拼接 — 可读性差，容易出错
path = os.path.join("home", "user", "documents", "file.txt")

# 路径判断 — 需要记住函数名
if os.path.exists(path) and os.path.isfile(path):
    size = os.path.getsize(path)
    ext = os.path.splitext(path)[1]
    name = os.path.basename(path)
    dir_name = os.path.dirname(path)
```

### pathlib 的优势

```python
from pathlib import Path

# 路径拼接 — 用 / 运算符，直觉自然
path = Path("home") / "user" / "documents" / "file.txt"

# 路径判断 — 属性访问，一目了然
if path.exists() and path.is_file():
    size = path.stat().st_size
    ext = path.suffix
    name = path.name
    dir_name = path.parent
```

### 对比总结

```
os.path                    pathlib.Path
─────────────────────────────────────────
os.path.join(a, b)    →    Path(a) / b
os.path.exists(p)     →    p.exists()
os.path.isfile(p)     →    p.is_file()
os.path.isdir(p)      →    p.is_dir()
os.path.getsize(p)    →    p.stat().st_size
os.path.basename(p)   →    p.name
os.path.dirname(p)    →    p.parent
os.path.splitext(p)   →    (p.stem, p.suffix)
os.path.abspath(p)    →    p.resolve()
os.listdir(d)         →    list(d.iterdir())
```

---

## 二、os 模块 — 基础文件操作

### 2.1 文件读写

```python
import os

# 打开文件的底层方式
fd = os.open("test.txt", os.O_WRONLY | os.O_CREAT, 0o644)
os.write(fd, b"Hello, os module!\n")
os.close(fd)

# 读取
fd = os.open("test.txt", os.O_RDONLY)
data = os.read(fd, 1024)
os.close(fd)
print(data)  # b'Hello, os module!\n'

# 更常用：用 open() 而不是 os.open()
with open("test.txt", "w") as f:
    f.write("Hello, world!\n")
```

### 2.2 目录操作

```python
import os

# 创建目录
os.makedirs("a/b/c", exist_ok=True)  # 递归创建
os.mkdir("test_dir")                   # 创建单级

# 列出目录
entries = os.listdir(".")
print(entries)  # ['file1.txt', 'dir1', ...]

# 遍历目录树
for root, dirs, files in os.walk("."):
    print(f"📁 {root}")
    for f in files:
        print(f"  📄 {os.path.join(root, f)}")

# 删除
os.rmdir("test_dir")           # 删除空目录
os.remove("test.txt")          # 删除文件
# os.removedirs("a/b/c")       # 递归删除空目录
```

### 2.3 文件信息

```python
import os
import time

stat_info = os.stat("test.txt")

print(f"大小:     {stat_info.st_size} bytes")
print(f"权限:     {oct(stat_info.st_mode)}")
print(f"所有者:   UID={stat_info.st_uid}")
print(f"修改时间: {time.ctime(stat_info.st_mtime)}")
print(f"访问时间: {time.ctime(stat_info.st_atime)}")
```

### 2.4 环境变量与路径

```python
import os

# 环境变量
home = os.environ.get("HOME", "/tmp")
path_var = os.environ.get("PATH", "")

# 路径相关
print(os.getcwd())           # 当前工作目录
print(os.path.expanduser("~"))  # ~ 展开为 home 目录
print(os.path.expandvars("$HOME"))  # 环境变量展开
```

---

## 三、pathlib — 现代路径操作

### 3.1 Path 对象创建

```python
from pathlib import Path, PurePath

# 多种创建方式
p1 = Path("home/user/file.txt")       # 字符串
p2 = Path.home() / "file.txt"         # home 目录
p3 = Path.cwd()                       # 当前目录
p4 = Path("/etc/hosts")               # 绝对路径
p5 = Path(".", "subdir", "file.txt")  # 多段拼接

# 跨平台
p6 = Path("folder", "subfolder", "file.txt")  # 自动处理分隔符
```

### 3.2 路径属性

```python
from pathlib import Path

p = Path("/home/user/documents/report.pdf")

# 路径各部分
print(p.name)       # 'report.pdf'    文件名
print(p.stem)       # 'report'        不含后缀的文件名
print(p.suffix)     # '.pdf'          后缀
print(p.suffixes)   # ['.pdf']        所有后缀
print(p.parent)     # '/home/user/documents'  父目录
print(p.parent.parent)  # '/home/user'
print(p.root)       # '/'             根目录
print(p.parts)      # ('/', 'home', 'user', 'documents', 'report.pdf')

# 路径转换
print(p.as_posix())  # '/home/user/documents/report.pdf'
print(p.as_uri())    # 'file:///home/user/documents/report.pdf'
print(p.absolute())  # 绝对路径
print(p.resolve())   # 绝对路径 + 解析符号链接
```

### 3.3 路径判断与查询

```python
from pathlib import Path

p = Path("test_file.txt")

# 创建测试文件
p.write_text("hello")

# 判断
print(p.exists())     # True
print(p.is_file())    # True
print(p.is_dir())     # False
print(p.is_symlink()) # False
print(p.is_absolute())# False

# 文件信息
stat = p.stat()
print(f"大小: {stat.st_size}")
print(f"修改: {stat.st_mtime}")

# 快捷属性（Python 3.10+）
print(p.stat().st_size)  # 文件大小
```

### 3.4 读写文件

```python
from pathlib import Path

p = Path("demo.txt")

# 写入
p.write_text("Hello, pathlib!\n第二行", encoding="utf-8")

# 写入字节
p.write_bytes(b"Binary content\n")

# 读取文本
content = p.read_text(encoding="utf-8")
print(content)

# 读取字节
data = p.read_bytes()
print(data)

# 追加写入（Python 3.10+）
p.write_text("追加内容\n", encoding="utf-8", append=True)
```

### 3.5 目录操作

```python
from pathlib import Path

# 创建目录
p = Path("test_dir/sub1/sub2")
p.mkdir(parents=True, exist_ok=True)  # parents=True 递归创建

# 列出目录
for item in Path(".").iterdir():
    if item.is_file():
        print(f"📄 {item.name}")
    elif item.is_dir():
        print(f"📁 {item.name}")

# 遍历目录树
for f in Path(".").rglob("*.py"):  # 递归匹配
    print(f"🐍 {f}")

# glob 模式匹配
for f in Path(".").glob("**/*.txt"):  # ** 递归
    print(f"📝 {f}")

# 删除
Path("demo.txt").unlink(missing_ok=True)  # missing_ok 避免报错
```

### 3.6 重命名与移动

```python
from pathlib import Path

p = Path("old_name.txt")

# 重命名
p.rename("new_name.txt")

# 移动
Path("new_name.txt").rename("archive/old_name.txt")

# 批量重命名
for f in Path("photos").glob("IMG_*.jpg"):
    new_name = f.parent / f"photo_{f.stem.split('_')[1]}{f.suffix}"
    f.rename(new_name)
```

---

## 四、shutil — 高级文件操作

### 4.1 文件复制

```python
import shutil
from pathlib import Path

src = Path("source.txt")
dst = Path("backup/source_backup.txt")

# 基础复制
shutil.copy(src, dst)              # 复制文件 + 权限
shutil.copy2(src, dst)             # 复制文件 + 权限 + 元数据
shutil.copyfile(src, dst)          # 只复制内容
shutil.copytree("src_dir", "dst_dir")  # 复制整个目录树
```

### 4.2 文件移动与删除

```python
import shutil
from pathlib import Path

# 移动文件/目录
shutil.move("old/path", "new/path")

# 删除目录树（⚠️ 慎用！）
shutil.rmtree("directory_to_delete")

# 磁盘使用统计
total, used, free = shutil.disk_usage("/")
print(f"总计: {total // (1024**3)} GB")
print(f"已用: {used // (1024**3)} GB")
print(f"可用: {free // (1024**3)} GB")
```

### 4.3 压缩与解压

```python
import shutil
from pathlib import Path

# 创建压缩包
shutil.make_archive("backup", "zip", "source_dir")
# → backup.zip

# 解压
shutil.unpack_archive("backup.zip", "extract_dir")

# 支持格式：zip, tar, gztar, bztar, xztar
```

### 4.4 文件查找

```python
import shutil

# 查找可执行文件
which_python = shutil.which("python3")
print(which_python)  # /usr/bin/python3

# 查找不存在的程序
missing = shutil.which("nonexistent_program")
print(missing)  # None
```

### 4.5 文件锁（高级）

```python
import fcntl
import os

def locked_operation(filepath):
    """文件锁，防止并发写入冲突"""
    with open(filepath, "r+") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # 临界区：安全操作文件
            data = f.read()
            f.seek(0)
            f.write(data + "\n新内容")
            f.truncate()
        except BlockingIOError:
            print("文件被其他进程锁定")
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

---

## 五、实战：文件同步工具

```python
"""
文件同步工具 — 比较两个目录并同步差异
使用 pathlib + shutil 实现
"""

import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import List, Set
from datetime import datetime


@dataclass
class SyncAction:
    """同步操作"""
    action: str  # "copy", "update", "delete", "skip"
    src: Path
    dst: Path
    reason: str

    def __str__(self):
        icons = {"copy": "📄", "update": "🔄", "delete": "🗑️", "skip": "✅"}
        return f"{icons.get(self.action, '?')} [{self.action.upper()}] {self.src.name} → {self.dst} ({self.reason})"


def compare_dirs(src_dir: Path, dst_dir: Path) -> List[SyncAction]:
    """比较两个目录的差异"""
    actions = []

    src_files = {f.relative_to(src_dir): f for f in src_dir.rglob("*") if f.is_file()}
    dst_files = {f.relative_to(dst_dir): f for f in dst_dir.rglob("*") if f.is_file()}

    # 新文件：在 src 中有，dst 中没有
    for rel_path, src_file in src_files.items():
        if rel_path not in dst_files:
            actions.append(SyncAction("copy", src_file, dst_dir / rel_path, "新文件"))
        else:
            # 比较修改时间
            src_mtime = src_file.stat().st_mtime
            dst_mtime = dst_files[rel_path].stat().st_mtime
            if src_mtime > dst_mtime:
                actions.append(SyncAction("update", src_file, dst_files[rel_path], "源文件更新"))
            else:
                actions.append(SyncAction("skip", src_file, dst_files[rel_path], "已同步"))

    # 删除：在 dst 中有，src 中没有
    for rel_path, dst_file in dst_files.items():
        if rel_path not in src_files:
            actions.append(SyncAction("delete", dst_file, dst_file, "源中不存在"))

    return actions


def sync_dirs(src_dir: Path, dst_dir: Path, dry_run: bool = True) -> List[SyncAction]:
    """执行同步"""
    print(f"📂 比较: {src_dir} → {dst_dir}")
    print(f"   模式: {'预览 (dry-run)' if dry_run else '执行'}\n")

    actions = compare_dirs(src_dir, dst_dir)

    if not actions:
        print("✅ 两个目录已同步，无需操作")
        return []

    # 按操作类型分组显示
    for action_type in ["copy", "update", "delete", "skip"]:
        filtered = [a for a in actions if a.action == action_type]
        if filtered:
            print(f"\n{'─' * 40}")
            print(f"  {action_type.upper()} ({len(filtered)} 个)")
            print(f"{'─' * 40}")
            for a in filtered:
                print(f"  {a}")

    # 执行操作
    if not dry_run:
        print(f"\n{'═' * 40}")
        print("  执行同步...")
        print(f"{'═' * 40}")

        for action in actions:
            if action.action == "copy":
                action.dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(action.src, action.dst)
                print(f"  ✅ 复制: {action.src.name}")
            elif action.action == "update":
                shutil.copy2(action.src, action.dst)
                print(f"  ✅ 更新: {action.src.name}")
            elif action.action == "delete":
                action.dst.unlink()
                print(f"  🗑️ 删除: {action.dst.name}")

        print(f"\n✅ 同步完成！操作 {len([a for a in actions if a.action != 'skip'])} 个文件")

    return actions


# ─── 演示 ───

def demo():
    import tempfile
    import os

    # 创建临时目录结构
    with tempfile.TemporaryDirectory(prefix="sync_demo_") as tmp:
        src = Path(tmp) / "source"
        dst = Path(tmp) / "dest"

        # 创建源目录
        (src / "file1.txt").write_text("File 1 content")
        (src / "file2.txt").write_text("File 2 content")
        (src / "subdir").mkdir()
        (src / "subdir" / "file3.txt").write_text("File 3 in subdir")

        # 创建目标目录（部分同步）
        (dst / "file1.txt").write_text("File 1 old content")
        (dst / "old_file.txt").write_text("This file is outdated")

        print("=" * 50)
        print("文件同步工具演示")
        print("=" * 50)

        # Dry-run 预览
        actions = sync_dirs(src, dst, dry_run=True)

        # 实际执行
        print("\n" + "=" * 50)
        sync_dirs(src, dst, dry_run=False)

        # 验证结果
        print("\n同步后的目标目录:")
        for f in sorted(dst.rglob("*")):
            if f.is_file():
                print(f"  📄 {f.relative_to(dst)}: {f.read_text()[:30]}...")


if __name__ == "__main__":
    demo()
```

---

## 六、常见陷阱与避坑

### 1. 路径分隔符

```python
# ❌ 硬编码分隔符（跨平台出问题）
path = "folder/subfolder/file.txt"  # Linux OK，Windows 可能有问题

# ✅ 用 Path 或 os.path.join
path = Path("folder") / "subfolder" / "file.txt"  # 自动适配
```

### 2. 编码问题

```python
# ❌ 默认编码可能不是 UTF-8
with open("file.txt") as f:
    content = f.read()  # 可能用系统默认编码

# ✅ 显式指定编码
with open("file.txt", encoding="utf-8") as f:
    content = f.read()

# pathlib 也需要指定
Path("file.txt").read_text(encoding="utf-8")
```

### 3. 相对路径陷阱

```python
# ❌ 相对路径基于当前工作目录
file = Path("data.csv")  # 在哪个目录执行，就找哪个目录

# ✅ 用 resolve() 获取绝对路径
file = Path(__file__).parent / "data.csv"  # 基于脚本位置
```

### 4. shutil.rmtree 危险操作

```python
# ❌ 慎用！会递归删除整个目录
shutil.rmtree("/important/directory")

# ✅ 先检查，再删除
target = Path("/important/directory")
if target.exists() and target.is_dir():
    # 先列出将要删除的内容
    files = list(target.rglob("*"))
    print(f"将删除 {len(files)} 个文件")
    confirm = input("确认删除？(y/n)")
    if confirm == "y":
        shutil.rmtree(target)
```

### 5. 并发文件操作

```python
# ❌ 多进程同时写入同一文件可能损坏
from multiprocessing import Pool

def write_to_file(data):
    with open("shared.txt", "a") as f:
        f.write(data)

# ✅ 每个进程写入不同文件，或用锁
import fcntl

def safe_write(data, filepath):
    with open(filepath, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(data)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

---

## 七、API 速查表

### os 模块

| 函数 | 说明 |
|------|------|
| `os.listdir(path)` | 列出目录内容 |
| `os.walk(path)` | 递归遍历目录树 |
| `os.makedirs(path)` | 递归创建目录 |
| `os.remove(path)` | 删除文件 |
| `os.rmdir(path)` | 删除空目录 |
| `os.rename(src, dst)` | 重命名/移动 |
| `os.stat(path)` | 获取文件信息 |
| `os.path.join(a, b)` | 拼接路径 |
| `os.path.exists(path)` | 判断是否存在 |
| `os.path.getsize(path)` | 获取文件大小 |

### pathlib.Path

| 属性/方法 | 说明 |
|----------|------|
| `.name` | 文件名 |
| `.stem` | 不含后缀的文件名 |
| `.suffix` | 后缀 |
| `.parent` | 父目录 |
| `.parts` | 路径各部分 |
| `.exists()` | 是否存在 |
| `.is_file()` | 是否是文件 |
| `.is_dir()` | 是否是目录 |
| `.read_text()` | 读取文本 |
| `.write_text()` | 写入文本 |
| `.mkdir()` | 创建目录 |
| `.unlink()` | 删除文件 |
| `.rename()` | 重命名 |
| `.glob(pattern)` | 模式匹配 |
| `.rglob(pattern)` | 递归模式匹配 |
| `.resolve()` | 解析为绝对路径 |

### shutil

| 函数 | 说明 |
|------|------|
| `shutil.copy(src, dst)` | 复制文件 |
| `shutil.copy2(src, dst)` | 复制文件+元数据 |
| `shutil.copytree(src, dst)` | 复制目录树 |
| `shutil.move(src, dst)` | 移动文件/目录 |
| `shutil.rmtree(path)` | 删除目录树 |
| `shutil.make_archive(name, fmt, dir)` | 创建压缩包 |
| `shutil.unpack_archive(file, dir)` | 解压 |
| `shutil.which(cmd)` | 查找可执行文件 |
| `shutil.disk_usage(path)` | 磁盘使用统计 |

---

## 八、思考题

1. **选型题**：你需要处理一个包含 100 万个文件的目录，统计所有 `.log` 文件的总大小。用 `os.walk` + `os.path.getsize` 还是 `Path.rglob` + `.stat().st_size`？为什么？

**参考答案**

两种方案的渐进复杂度一样：都要遍历全部目录项，并对每个 `.log` 文件做一次 `stat`（获取文件元数据的系统调用）。100 万个文件时差别只在常数因子，瓶颈通常是磁盘 IO 而不是 Python 本身。

差别在每个条目的开销：`os.walk` 内部使用 `os.scandir`，全程操作字符串，更轻；`Path.rglob` 会为每个条目创建 `Path` 对象，对象创建和方法调用让它略慢一点。但 `rglob("*.log")` 自带过滤，代码可读性更好。

如果真要榨性能，推荐第三种写法 `os.scandir`：它返回的 `DirEntry`（目录条目对象）自带文件名和类型信息，且**在 Windows 上 stat 结果已缓存在目录条目里**，`entry.stat()` 不必再发一次系统调用，明显快于前两者。

结论：日常脚本用 `Path.rglob`（可读性优先）；大规模纯统计用 `os.walk` 或 `os.scandir`。下面用 3000 个小文件实测对比（临时目录，跑完自动清理）：

```python
import os
import tempfile
import time
from pathlib import Path


def make_files(root: Path, n_log: int = 2000, n_txt: int = 1000) -> None:
    """造测试文件：2000 个 100 字节的 .log + 1000 个 50 字节的 .txt"""
    for i in range(n_log):
        (root / f"app_{i}.log").write_bytes(b"x" * 100)
    for i in range(n_txt):
        (root / f"data_{i}.txt").write_bytes(b"y" * 50)


def total_by_walk(root: str) -> int:
    """方案一：os.walk + os.path.getsize"""
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".log"):
                total += os.path.getsize(os.path.join(dirpath, name))
    return total


def total_by_rglob(root: str) -> int:
    """方案二：Path.rglob + stat().st_size"""
    return sum(p.stat().st_size for p in Path(root).rglob("*.log"))


def total_by_scandir(root: str) -> int:
    """方案三（推荐）：os.scandir，DirEntry 自带名字/类型信息（单层目录）"""
    total = 0
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.name.endswith(".log") and entry.is_file():
                total += entry.stat().st_size
    return total


with tempfile.TemporaryDirectory() as tmp:
    make_files(Path(tmp))
    for func in (total_by_walk, total_by_rglob, total_by_scandir):
        start = time.perf_counter()
        total = func(tmp)
        cost = time.perf_counter() - start
        print(f"{func.__name__:16s} total={total} bytes  time={cost:.3f}s")
```

预期输出（耗时因机器而异，下面是作者 Windows 机器上的结果）：

```text
total_by_walk    total=200000 bytes  time=0.011s
total_by_rglob   total=200000 bytes  time=0.013s
total_by_scandir total=200000 bytes  time=0.002s
```

三种方案统计结果必然一致（2000 × 100 字节 = 200000）；速度上 `scandir` 最快，`walk` 与 `rglob` 接近。

⚠️ 注意：`os.scandir` 只遍历单层目录，递归遍历要自己写递归（或改用 `os.walk`）；Linux 上 `DirEntry` 不缓存 stat 结果，`scandir` 的优势会缩小。

2. **设计题**：设计一个自动清理工具：删除 30 天前的日志文件，压缩 7 天前的日志。需要用到哪些 API？

**参考答案**

需要的 API（全部来自标准库）：

- **遍历筛选**：`Path.rglob("*.log")` —— 递归找出所有日志文件；
- **判断年龄**：`Path.stat().st_mtime`（最后修改时间戳），用 `time.time()` 减去它再除以 86400，得到「多少天前」；
- **压缩**：`gzip.open` + `shutil.copyfileobj` 流式压缩单个文件；若想把整个目录打成 zip 包，用 `shutil.make_archive`；
- **删除**：`Path.unlink()`；
- **辅助**：`Path.mkdir(parents=True, exist_ok=True)`（建归档目录）、`os.utime`（测试时伪造文件时间戳）。

设计要点：① 一次遍历中按年龄分档处理（>30 天删除、7~30 天压缩），避免「先压缩再删除」两步走互相打架；② 跳过符号链接和非普通文件；③ 生产工具建议先加 dry-run（只预览不执行）模式。完整实现：

```python
import gzip
import os
import shutil
import tempfile
import time
from pathlib import Path

DAY = 24 * 3600  # 一天的秒数


def cleanup_logs(log_dir: Path, now: float | None = None):
    """删除 30 天前的 .log；把 7~30 天前的 .log 压缩成 .log.gz"""
    now = time.time() if now is None else now
    deleted, compressed = [], []
    for f in sorted(log_dir.rglob("*.log")):
        if not f.is_file() or f.is_symlink():   # 只处理普通文件，跳过符号链接
            continue
        age_days = (now - f.stat().st_mtime) / DAY
        if age_days > 30:
            f.unlink()                          # 超过 30 天：直接删除
            deleted.append(f.name)
        elif age_days > 7:
            target = f.with_suffix(".log.gz")
            with open(f, "rb") as src, gzip.open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)    # 流式压缩，大文件也不吃内存
            f.unlink()                          # 压缩成功后删除原文件
            compressed.append(target.name)
    return deleted, compressed


# ─── 演示：造 3 个不同「年龄」的日志 ───
with tempfile.TemporaryDirectory() as tmp:
    log_dir = Path(tmp)
    now = time.time()
    for name, days in {"fresh.log": 1, "week.log": 10, "ancient.log": 40}.items():
        p = log_dir / name
        p.write_text("log line\n" * 3, encoding="utf-8")
        old = now - days * DAY
        os.utime(p, (old, old))   # 把修改时间伪造成 days 天前

    deleted, compressed = cleanup_logs(log_dir)
    print("删除:", deleted)
    print("压缩:", compressed)
    print("剩余:", sorted(p.name for p in log_dir.iterdir()))
```

预期输出：

```text
删除: ['ancient.log']
压缩: ['week.log.gz']
剩余: ['fresh.log', 'week.log.gz']
```

40 天前的 `ancient.log` 被删除，10 天前的 `week.log` 被压缩成 `.log.gz`，1 天前的 `fresh.log` 保持原样。演示里用 `os.utime` 把新建文件「做旧」，真实场景直接读 `st_mtime` 即可。

3. **对比题**：`shutil.copy` 和 `shutil.copy2` 的区别是什么？在什么场景下必须用 `copy2`？

**参考答案**

区别在于「复制多少元数据」：

- `shutil.copy` = `copyfile`（文件内容）+ `copymode`（权限位）。目标文件的修改时间是**复制那一刻**；
- `shutil.copy2` = `copyfile` + `copystat`（权限位 + 修改时间 mtime、访问时间 atime 等时间戳）。目标文件的时间戳**与源文件保持一致**。

必须用 `copy2` 的场景：一切依赖时间戳做判断的逻辑。最典型的是**增量备份/同步**——本章的文件同步工具靠比较 `st_mtime` 判断「源文件更新」，如果用 `copy` 做备份，所有备份文件的修改时间都变成「刚刚」，下一轮比较就会彻底失灵。归档照片、文档这类需要保留原始拍摄/修改时间的场景，也必须用 `copy2`。

小实验验证：

```python
import os
import shutil
import tempfile
import time
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    src = tmp / "src.txt"
    src.write_text("hello", encoding="utf-8")
    old = time.time() - 86400            # 把源文件修改时间设为 1 天前
    os.utime(src, (old, old))

    shutil.copy(src, tmp / "copy.txt")   # 只复制内容 + 权限位
    shutil.copy2(src, tmp / "copy2.txt") # 复制内容 + 权限位 + 时间戳等元数据

    src_mtime = src.stat().st_mtime
    same = lambda p: abs(p.stat().st_mtime - src_mtime) < 1
    print("copy  保留修改时间:", same(tmp / "copy.txt"))
    print("copy2 保留修改时间:", same(tmp / "copy2.txt"))
```

预期输出：

```text
copy  保留修改时间: False
copy2 保留修改时间: True
```

💡 提示：两者默认都跟随符号链接（复制的是链接指向的文件内容），想复制链接本身要传 `follow_symlinks=False`；`copy2` 保留时间戳但不保留属主/属组，完整快照需要专门的备份工具。

4. **安全题**：编写一个安全的文件删除函数，要求：先检查文件是否存在、是否是符号链接、是否在允许删除的目录内。

**参考答案**

核心思路是「先检查、后删除」，设四道关卡：① 存在性——用 `os.path.lexists`，它不跟随链接，连「悬空链接」（指向不存在目标的符号链接）也能发现；② 拒绝符号链接——否则攻击者可以在允许目录里放一个指向系统文件的链接，骗你删掉目录外的东西；③ 只处理普通文件，目录一律不动；④ 用 `resolve()` 把路径解析成真实绝对路径（消掉 `../`），再检查是否仍落在允许目录内。

```python
import os
import tempfile
from pathlib import Path


def safe_delete(target, allowed_dir):
    """只删除「存在、不是符号链接、位于允许目录内」的普通文件。

    返回 (是否删除成功, 原因说明)。
    """
    target = Path(target)
    allowed_dir = Path(allowed_dir).resolve()

    # 1. 存在性检查：lexists 不跟随符号链接，连「悬空链接」也能发现
    if not os.path.lexists(target):
        return False, "不存在"
    # 2. 拒绝符号链接：防止借助链接骗我们删掉目录外的真实文件
    if target.is_symlink():
        return False, "是符号链接"
    # 3. 只处理普通文件，目录一律不动（避免误递归删除）
    if not target.is_file():
        return False, "不是普通文件"
    # 4. 包含性检查：resolve() 消掉 ../ 和链接后，必须仍在允许目录内
    resolved = target.resolve()
    if not resolved.is_relative_to(allowed_dir):   # Python 3.9+
        return False, "越出允许目录"

    resolved.unlink()
    return True, "已删除"


# ─── 演示 ───
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    allowed = root / "allowed"
    allowed.mkdir()
    (allowed / "ok.txt").write_text("可以删", encoding="utf-8")
    outside = root / "outside.txt"
    outside.write_text("不能删", encoding="utf-8")

    cases = [
        ("目录内普通文件", allowed / "ok.txt"),
        ("不存在的文件", allowed / "missing.txt"),
        ("../ 越界文件", allowed / ".." / "outside.txt"),
        ("目录本身", allowed),
    ]
    for label, path in cases:
        ok, reason = safe_delete(path, allowed)
        print(f"{label}: 删除={ok}（{reason}）")

    try:
        link = allowed / "link.txt"
        link.symlink_to(outside)          # 指向目录外文件的符号链接
        ok, reason = safe_delete(link, allowed)
        print(f"指向外部的符号链接: 删除={ok}（{reason}）")
        print("outside.txt 仍然存在:", outside.exists())
    except OSError:
        print("（当前系统不允许创建符号链接，跳过该用例）")
```

预期输出：

```text
目录内普通文件: 删除=True（已删除）
不存在的文件: 删除=False（不存在）
../ 越界文件: 删除=False（越出允许目录）
目录本身: 删除=False（不是普通文件）
指向外部的符号链接: 删除=False（是符号链接）
outside.txt 仍然存在: True
```

四类危险输入全部被拒绝，只有目录内的普通文件被真正删除。

⚠️ 注意：`is_relative_to()` 需要 Python 3.9+；Windows 上创建符号链接需要开发者模式或管理员权限，所以演示用 `try/except` 兜底。高安全场景下「检查」和「删除」之间仍有时间窗口（TOCTOU：检查后文件可能被调包），更严格的做法是用 `os.unlink(path, dir_fd=...)` 把操作锚定在已打开的目录句柄上。

5. **性能题**：比较 `os.listdir` 和 `Path.iterdir` 的性能差异。在什么场景下 `os.listdir` 更快？

**参考答案**

两者底层都基于 `os.scandir`，读取的是同一份目录数据，差别在「包装」方式：`os.listdir` 一次性返回**全部文件名的列表（纯字符串）**；`Path.iterdir` 是**生成器**，逐个懒创建 `Path` 对象。

`os.listdir` 更快的场景：**只需要名字**的时候。比如按扩展名过滤（`endswith`）、排序、做集合运算、取 `len()`、或者要多次遍历——它省去了为每个条目创建 `Path` 对象的开销，实测能快 2~4 倍。

`Path.iterdir` 更合适的场景：目录巨大但只处理前几个条目（惰性求值，随时 `break`，不会一次性建百万元素的大列表）；或者后续要链式调用 `.is_file()`、`.stat()` 等 `Path` 方法，代码更顺手。如果两者都要对每个文件 `stat`，系统调用次数相同，差距会缩小。

实测对比（5000 个空文件）：

```python
import os
import tempfile
import time
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    for i in range(5000):                 # 造 5000 个空文件
        Path(tmp, f"f{i}.txt").touch()

    start = time.perf_counter()
    names1 = os.listdir(tmp)              # 一次性返回全部文件名（str 列表）
    t1 = time.perf_counter() - start

    start = time.perf_counter()
    names2 = [p.name for p in Path(tmp).iterdir()]  # 逐个生成 Path 对象再取名字
    t2 = time.perf_counter() - start

    print("结果一致:", sorted(names1) == sorted(names2))
    print(f"os.listdir: {t1:.4f}s   Path.iterdir: {t2:.4f}s")
```

预期输出（耗时因机器而异）：

```text
结果一致: True
os.listdir: 0.0014s   Path.iterdir: 0.0048s
```

结果完全一致，但只取名字时 `os.listdir` 快了约 3 倍——省下的正是创建 5000 个 `Path` 对象的成本。
