# Day 030 — 阶段项目：命令行工具：完成清单与练习题

## ✅ 完成清单

### 概念理解
- [ ] 理解 CLI 与 GUI 的区别与适用场景
- [ ] 理解 sys.argv 的局限性和手动解析方式
- [ ] 理解 argparse 的完整参数解析流程
- [ ] 理解位置参数、可选参数、标志参数的区别
- [ ] 理解子命令架构（Git 风格 CLI）
- [ ] 理解管道与重定向的工作原理
- [ ] 理解错误处理在 CLI 工具中的重要性

### Python 实现
- [ ] 能够使用 sys.argv 获取命令行参数
- [ ] 能够使用 argparse 构建多参数 CLI
- [ ] 能够使用 add_argument 的各种 action
- [ ] 能够使用 subparsers 构建多命令 CLI
- [ ] 能够使用 FileType 进行文件 I/O
- [ ] 能够实现自定义类型验证
- [ ] 能够检测管道输入

### 代码实践
- [ ] 运行 `01-basic-usage.py` 理解 CLI 基础
- [ ] 运行 `02-advanced-usage.py` 掌握子命令和高级特性
- [ ] 运行 `03-practical.py` 完成综合工具集
- [ ] 完成至少 3 道练习题

---

## 📝 练习题

### 练习 1：实现一个简单的计算器 CLI

```python
"""
使用 argparse 实现一个命令行计算器。
支持基本四则运算和幂运算。

用法:
  $ python calc.py 5 + 3      → 8.0
  $ python calc.py 10 / 3     → 3.333...
  $ python calc.py 2 ** 10    → 1024.0
"""
import argparse

def calc():
    # 你的代码
    pass

if __name__ == '__main__':
    calc()
```

### 练习 2：文件分割工具

```python
"""
实现一个文件分割工具，将大文件分割成指定大小的小文件。

用法:
  $ python file-split.py --file large.log --size 1M --output chunk_

参数:
  --file: 需要分割的文件
  --size: 每块的大小（支持 K, M, G 后缀）
  --output: 输出文件前缀
"""
def split_file(file_path, chunk_size, output_prefix):
    # 你的代码
    pass

# 测试
# split_file('bigfile.log', '1M', 'chunk_')
```

### 练习 3：Todo 管理器 CLI

```python
"""
实现一个简单的 Todo 命令行管理器。
数据存储到 JSON 文件。

用法:
  $ python todo.py add "学习 Python"          → 添加任务
  $ python todo.py list                        → 列出所有任务
  $ python todo.py done 1                      → 标记任务完成
  $ python todo.py delete 1                    → 删除任务
  $ python todo.py clear                       → 清空已完成
"""
# 你的代码
```

### 练习 4：密码生成器 CLI

```python
"""
实现一个密码生成器 CLI。

用法:
  $ python passgen.py --length 16 --no-symbols  → 生成不含符号的密码
  $ python passgen.py -l 12 -n 5               → 生成 5 个 12 位密码
  $ python passgen.py --no-digits              → 不含数字

参数:
  -l, --length: 密码长度（默认 16）
  -n, --count: 生成数量（默认 1）
  --no-digits: 不含数字
  --no-symbols: 不含符号
  --no-uppercase: 不含大写字母
"""
import argparse
import random
import string

def generate_password(length=16, use_digits=True, use_symbols=True,
                      use_uppercase=True):
    # 你的代码
    pass

# 测试
print(generate_password())
print(generate_password(8, use_symbols=False))
```

### 练习 5：日志监控器

```python
"""
实现一个实时日志监控器，检测文件变化并过滤指定级别的日志。

用法:
  $ python log-monitor.py app.log --level ERROR
  $ python log-monitor.py app.log --level WARNING --tail 50
  $ python log-monitor.py app.log --follow  # 持续监控

参数:
  logfile: 日志文件（位置参数）
  --level: 过滤级别（INFO/WARNING/ERROR）
  --tail: 显示末尾 N 行
  --follow: 持续监控文件写入
  --output: 输出到文件（可选）
"""
import time
import os

def tail_file(filepath, n=10):
    """类 tail 命令：显示文件末尾 N 行"""
    # 你的代码
    pass

def follow_file(filepath, callback):
    """类 tail -f 命令：持续监控文件变化"""
    # 你的代码
    pass

# 测试
# tail_file('app.log', 5)
```

---

## 📊 自评表

| 技能 | 初学者 | 理解 | 掌握 | 熟练 |
|------|--------|------|------|------|
| sys.argv 手动解析 | ☐ | ☐ | ☐ | ☐ |
| argparse 基础用法 | ☐ | ☐ | ☐ | ☐ |
| 子命令 (subparsers) | ☐ | ☐ | ☐ | ☐ |
| 自定义参数类型 | ☐ | ☐ | ☐ | ☐ |
| 文件 I/O 工具 | ☐ | ☐ | ☐ | ☐ |
| 管道输入检测 | ☐ | ☐ | ☐ | ☐ |
| CLI 错误处理 | ☐ | ☐ | ☐ | ☐ |
| setup.py 打包 | ☐ | ☐ | ☐ | ☐ |

---

## 🔗 参考资源

- [argparse 官方教程](https://docs.python.org/3/howto/argparse.html)
- [Python sys — 系统参数](https://docs.python.org/3/library/sys.html)
- [Click — 更优雅的 CLI 框架](https://click.palletsprojects.com/)
- [Typer — 类型提示 CLI](https://typer.tiangolo.com/)
- [Python Firebase CLI](https://github.com/google/python-fire)
