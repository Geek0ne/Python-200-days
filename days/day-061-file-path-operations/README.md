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

2. **设计题**：设计一个自动清理工具：删除 30 天前的日志文件，压缩 7 天前的日志。需要用到哪些 API？

3. **对比题**：`shutil.copy` 和 `shutil.copy2` 的区别是什么？在什么场景下必须用 `copy2`？

4. **安全题**：编写一个安全的文件删除函数，要求：先检查文件是否存在、是否是符号链接、是否在允许删除的目录内。

5. **性能题**：比较 `os.listdir` 和 `Path.iterdir` 的性能差异。在什么场景下 `os.listdir` 更快？
