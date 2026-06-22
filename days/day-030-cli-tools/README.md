# Day 030 — 阶段项目：命令行工具

> Phase 2 综合项目：构建实用的 Python 命令行工具集

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| sys.argv | ⭐ | 最基础的命令行参数获取 |
| argparse | ⭐⭐⭐ | 官方推荐的命令行参数解析库 |
| 文件处理工具 | ⭐⭐ | 文件统计/搜索/转换 CLI |
| 数据处理工具 | ⭐⭐⭐ | CSV/JSON 处理 CLI |
| 网络工具 | ⭐⭐ | HTTP 请求/URL 解析 CLI |
| 安装与打包 | ⭐⭐ | setup.py 与可执行脚本 |

---

## 一、为什么需要命令行工具？

### 1.1 图形界面 vs 命令行

```
图形界面 (GUI)              命令行 (CLI)
─────────────               ─────────────
• 鼠标点击操作              • 键盘输入命令
• 学习成本较低              • 学习曲线较陡
• 适合简单操作              • 适合批量/自动化
• 难以组合复用              • 便于管道组合
• 资源占用大                • 资源占用极小
• 交互友好                  • 脚本友好
```

Python 命令行工具的优势：
- 零依赖（stdlib 即可）
- 跨平台运行
- 易于分发部署
- 可嵌入脚本/工作流

### 1.2 命令行参数的基本概念

```
command [optional_args] positional_args

$ cat file.txt              # 位置参数: file.txt
$ ls -l /tmp                # 可选参数: -l, 位置: /tmp
$ python script.py --name Alice --verbose  # 长选项
$ grep -i "hello" file.txt  # 短选项: -i, 模式: hello
```

---

## 二、sys.argv — 最基础的参数获取

### 2.1 基本用法

```python
import sys

# sys.argv[0] = 脚本名称
# sys.argv[1:] = 传入的参数列表
print(f"脚本名: {sys.argv[0]}")
print(f"参数: {sys.argv[1:]}")
```

```
$ python script.py hello world 42
脚本名: script.py
参数: ['hello', 'world', '42']
```

### 2.2 手动解析示例

```python
import sys

def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python script.py <name> [--verbose]")
        sys.exit(1)
    
    verbose = False
    names = []
    
    i = 0
    while i < len(args):
        if args[i] == '--verbose' or args[i] == '-v':
            verbose = True
        elif args[i].startswith('--'):
            print(f"未知选项: {args[i]}")
            sys.exit(1)
        else:
            names.append(args[i])
        i += 1
    
    print(f"Hello, {', '.join(names)}!")
    if verbose:
        print("Verbose 模式已开启")

if __name__ == '__main__':
    main()
```

### 2.3 sys.argv 的局限性

| 问题 | 说明 |
|------|------|
| 无类型转换 | 所有参数都是字符串 |
| 无帮助信息 | 需要手动实现 `--help` |
| 无错误提示 | 参数错误需要自己抛出 |
| 不支持子命令 | 需要自己实现路由 |

---

## 三、argparse — 官方参数解析库

### 3.1 快速入门

```python
import argparse

parser = argparse.ArgumentParser(
    description='一个简单的命令行工具',
    epilog='示例: python app.py --name Alice --count 3'
)

parser.add_argument('name', help='你的名字')           # 位置参数
parser.add_argument('-c', '--count', type=int, default=1, help='重复次数')
parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')

args = parser.parse_args()

for i in range(args.count):
    print(f"Hello, {args.name}!")
    if args.verbose:
        print(f"  (第 {i+1} 次)")
```

```
$ python hello.py Alice -c 3 -v
Hello, Alice!
  (第 1 次)
Hello, Alice!
  (第 2 次)
Hello, Alice!
  (第 3 次)

$ python hello.py --help
usage: hello.py [-h] [-c COUNT] [-v] name

一个简单的命令行工具

positional arguments:
  name                  你的名字

optional arguments:
  -h, --help            show this help message and exit
  -c, --count COUNT     重复次数
  -v, --verbose         详细输出
```

### 3.2 argparse 的 Action 类型

| Action | 说明 | 示例 |
|--------|------|------|
| `store` | 存储值（默认） | 保存参数值 |
| `store_true` | 存储 True/False | 标志开关 |
| `store_const` | 存储常量值 | 特定模式 |
| `append` | 追加到列表 | `-f a -f b` |
| `count` | 计数 | `-v` → 1, `-vv` → 2 |
| `extend` | 扩展列表 | 3.8+ 新特性 |

### 3.3 高级参数类型

```python
# 可选值列表
parser.add_argument('--mode', choices=['read', 'write', 'append'],
                    default='read', help='操作模式')

# 文件类型
parser.add_argument('--input', type=argparse.FileType('r'),
                    help='输入文件')
parser.add_argument('--output', type=argparse.FileType('w'),
                    help='输出文件')

# 可选参数
parser.add_argument('--config', nargs='?', const='default.conf',
                    default=None, help='配置文件')

# 不定数量参数
parser.add_argument('files', nargs='+', help='文件列表')

# 剩余参数
parser.add_argument('rest', nargs=argparse.REMAINDER,
                    help='剩余参数')
```

### 3.4 子命令（Subparsers）

```python
parser = argparse.ArgumentParser(description='文件操作工具')
subparsers = parser.add_subparsers(dest='command', help='可用命令')

# cat 子命令
cat_parser = subparsers.add_parser('cat', help='显示文件内容')
cat_parser.add_argument('file', help='文件名')

# grep 子命令
grep_parser = subparsers.add_parser('grep', help='搜索文本')
grep_parser.add_argument('pattern', help='搜索模式')
grep_parser.add_argument('file', help='文件名')
grep_parser.add_argument('-i', '--ignore-case', action='store_true', help='忽略大小写')

args = parser.parse_args()
```

---

## 四、文件处理工具实战

### 4.1 文件统计工具 (wc)

统计文件的行数、单词数、字符数：

```python
def wc(filename, lines=True, words=True, chars=True):
    """类似 Unix wc 命令"""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = {}
    if lines:
        result['lines'] = content.count('\n')
    if words:
        result['words'] = len(content.split())
    if chars:
        result['chars'] = len(content)
    return result
```

### 4.2 文件搜索工具 (grep)

```python
def grep(pattern, filename, ignore_case=False, show_line_num=False):
    """类似 Unix grep 命令"""
    matches = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if ignore_case:
                found = pattern.lower() in line.lower()
            else:
                found = pattern in line
            if found:
                if show_line_num:
                    matches.append((line_num, line.rstrip()))
                else:
                    matches.append(line.rstrip())
    return matches
```

### 4.3 文件查找工具 (find)

```python
import os
from pathlib import Path

def find_files(root_dir, pattern=None, file_type=None, 
               min_size=None, max_size=None):
    """
    查找文件（类似 Unix find 命令）
    
    Args:
        root_dir: 根目录
        pattern: 文件名模式
        file_type: 'f' 文件, 'd' 目录
        min_size: 最小文件大小（字节）
        max_size: 最大文件大小（字节）
    """
    results = []
    root = Path(root_dir)
    
    for path in root.rglob('*'):
        if pattern and pattern not in path.name:
            continue
        if file_type == 'f' and not path.is_file():
            continue
        if file_type == 'd' and not path.is_dir():
            continue
        if min_size is not None and path.stat().st_size < min_size:
            continue
        if max_size is not None and path.stat().st_size > max_size:
            continue
        results.append(path)
    
    return results
```

---

## 五、数据处理工具实战

### 5.1 CSV 查看器

```python
import csv
import sys

def csv_view(filename, delimiter=',', header=True, 
             max_rows=10, columns=None):
    """查看 CSV 文件内容"""
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        
        rows = list(reader)
        if not rows:
            return
        
        # 处理表头
        start_idx = 0
        headers = None
        if header:
            headers = rows[0]
            start_idx = 1
        
        # 选择列
        if columns and headers:
            col_idx = []
            for col in columns:
                if isinstance(col, str):
                    try:
                        col_idx.append(headers.index(col))
                    except ValueError:
                        print(f"错误: 找不到列 '{col}'", file=sys.stderr)
                        return
                else:
                    col_idx.append(col)
        else:
            col_idx = None
        
        # 打印
        def get_cols(row):
            if col_idx:
                return [row[i] if i < len(row) else '' for i in col_idx]
            return row
        
        if headers:
            print('\t'.join(get_cols(headers)))
            print('-' * 40)
        
        for row in rows[start_idx:start_idx + max_rows]:
            print('\t'.join(get_cols(row)))
        
        if len(rows) - start_idx > max_rows:
            print(f"... (还有 {len(rows) - start_idx - max_rows} 行)")
```

### 5.2 JSON 格式化工具

```python
import json
import sys

def json_format(input_data, indent=2, sort_keys=False):
    """JSON 格式化/美化输出"""
    try:
        data = json.loads(input_data)
        return json.dumps(data, indent=indent, 
                         sort_keys=sort_keys, 
                         ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"JSON 解析错误: {e}"
```

---

## 六、综合工具实现

### 6.1 工具集架构

```
mytools/
├── __init__.py         ← 包初始化
├── __main__.py         ← python -m mytools 入口
├── cli.py              ← 主 CLI 入口
├── utils/
│   ├── __init__.py
│   ├── file_utils.py   ← 文件操作工具
│   ├── data_utils.py   ← 数据处理工具
│   └── net_utils.py    ← 网络工具
└── setup.py            ← 安装配置
```

### 6.2 模块化设计原则

```
用户调用                 内部实现
─────────               ────────
$ mytools wc file.txt   →  cli.py → file_utils.wc()
$ mytools grep pattern  →  cli.py → file_utils.grep()
$ mytools csv-view      →  cli.py → data_utils.csv_view()
$ mytools json-fmt      →  cli.py → data_utils.json_format()
```

### 6.3 错误处理策略

```python
import sys
import traceback

class ToolError(Exception):
    """工具自定义异常"""
    pass

def handle_error(func):
    """错误处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ToolError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError as e:
            print(f"文件未找到: {e.filename}", file=sys.stderr)
            sys.exit(1)
        except PermissionError as e:
            print(f"权限不足: {e.filename}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n操作已取消", file=sys.stderr)
            sys.exit(130)
        except Exception as e:
            if '--debug' in sys.argv:
                traceback.print_exc()
            print(f"未知错误: {e}", file=sys.stderr)
            sys.exit(1)
    return wrapper
```

---

## 七、安装与分发

### 7.1 setup.py 配置

```python
from setuptools import setup, find_packages

setup(
    name='mytools',
    version='1.0.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'mytools=mytools.cli:main',
        ],
    },
    python_requires='>=3.8',
)
```

### 7.2 安装到系统

```bash
# 开发模式安装
$ pip install -e .

# 或直接运行
$ python -m mytools

# 安装到用户目录
$ pip install --user .
```

### 7.3 shebang 与可执行脚本

```python
#!/usr/bin/env python3
"""可执行脚本 — 添加 shebang 后 chmod +x"""

import sys
# ... 工具实现 ...

if __name__ == '__main__':
    main()
```

```bash
$ chmod +x mytool.py
$ ./mytool.py --help
```

---

## 💡 思考题

1. `argparse` 的 `add_subparsers` 可以实现 git 风格的子命令（`git commit`, `git push`）。如果要实现 `tool init`, `tool config`, `tool run` 三个子命令，如何组织代码？
2. 如何实现一个交互式命令行工具（类似 `redis-cli` 那种可以输入命令的 REPL）？提示：使用 `cmd` 模块或 `prompt_toolkit`。
3. 大量的文件 I/O 操作如何优化？考虑使用缓冲区、mmap 还是多线程？
4. 如果要支持色输出（彩色文本），如何实现跨平台兼容？（提示：`colorama` 库）
5. 设计一个支持管道操作的 CLI 工具（从 stdin 读取输入，输出到 stdout），如何检测是否有管道输入？

---

## 📚 参考资源

- [argparse 官方文档](https://docs.python.org/3/library/argparse.html)
- [Click 库 — 更简洁的 CLI 框架](https://click.palletsprojects.com/)
- [Typer — 基于类型提示的 CLI 框架](https://typer.tiangolo.com/)
- [Python 打包用户指南](https://packaging.python.org/)
- [Fire 库 — 自动生成 CLI](https://github.com/google/python-fire)
