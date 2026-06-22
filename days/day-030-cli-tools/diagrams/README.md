# Day 030 — 阶段项目：命令行工具：图解

> argparse 架构、CLI 工作流、数据流图

---

## 1️⃣ 命令行参数解析流程

```
用户输入
    │
    ▼
┌─────────────────────────────┐
│  shell 解析                  │
│  $ mytool subcommand --opt   │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  argparse 解析               │
│                             │
│  sys.argv = [mytool,        │
│    subcommand, --opt]       │
│                             │
│  subparsers → 路由子命令     │
│  add_argument → 绑定参数    │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  参数验证                    │
│  • 类型转换 (type=int)      │
│  • 值验证 (choices=[...])   │
│  • 文件验证 (FileType)      │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  业务逻辑处理                │
│  • args.command 分发        │
│  • 调用对应工具函数          │
│  • 输出结果                  │
└─────────────────────────────┘
```

## 2️⃣ 子命令架构（Git 风格）

```
mytools
  │
  ├── wc             文件统计
  │   ├── file                  位置参数
  │   ├── -l, --lines           只统计行数
  │   ├── -w, --words           只统计单词数
  │   └── -c, --chars           只统计字符数
  │
  ├── grep           文本搜索
  │   ├── pattern               搜索模式
  │   ├── file                  文件名
  │   ├── -i, --ignore-case     忽略大小写
  │   └── -n, --line-number     显示行号
  │
  ├── find           文件查找
  │   ├── root                  根目录
  │   ├── --name                文件名模式
  │   └── --type                类型 (f/d)
  │
  └── json-fmt       JSON 格式化
      ├── input                 JSON 字符串
      ├── --indent              缩进空格
      └── --sort                按键排序
```

### Python 实现架构

```python
# cli.py — 主入口
def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    
    # 注册各个子命令
    register_wc(subparsers)
    register_grep(subparsers)
    register_find(subparsers)
    register_json_fmt(subparsers)
    
    args = parser.parse_args()
    
    # 路由到对应处理函数
    if args.command == 'wc':
        return wc_handler(args)
    elif args.command == 'grep':
        return grep_handler(args)
    # ...
```

## 3️⃣ 管道与重定向

```
stdin 重定向:
  $ cat data.txt | python mytool.py parse
                                    ↑
        ┌───────────────────────────┘
        ▼
    sys.stdin.read()
    
标准输出到文件:
  $ python mytool.py stats > report.txt
                              ↓
                         写入文件

管道组合:
  $ python mytool.py scan . | python mytool.py json-fmt
       ↑               ↑                   ↑
   扫描目录树     输出 JSON 列表       美化 JSON
```

### Python 中检测管道输入

```python
import sys

def has_pipe_input():
    """检测 stdin 是否来自管道"""
    return not sys.stdin.isatty()

if has_pipe_input():
    data = sys.stdin.read()
    # 处理管道输入
else:
    # 交互式模式
    pass
```

## 4️⃣ 工具集数据流

```
数据输入                  处理管道                 输出
─────────────────    ──────────────────    ─────────────
文件系统  ─────────→  FileInfoTool.get_info  ───────→ 终端文本
                      CodeStatsTool.count   ───────→ 表格/汇总
日志文件  ─────────→  LogAnalyzer.analyze   ───────→ 统计 + 图表
目录树    ─────────→  TreeTool.generate     ───────→ 树形文本
JSON 串   ─────────→  json_format_tool      ───────→ 格式化 JSON
```

## 5️⃣ argparse 参数类型对比

```
参数类型        语法示例                值类型          说明
────────────────────────────────────────────────────────────
positional     parser.add_argument     字符串          必须提供
               ('file')
optional       parser.add_argument     根据 type       用 -- 指定
               ('--output')
flag           parser.add_argument      bool           无需参数
               ('-v', action='store_true')
list           parser.add_argument      list           可重复
               ('-f', action='append')
choice         parser.add_argument      str            限定值范围
               ('--mode', choices=['a','b'])
count          parser.add_argument      int            计数
               ('-v', action='count')
file           parser.add_argument      file object    自动打开/关闭
               ('--log', type=FileType('w'))
```

## 6️⃣ 错误处理流程

```
用户输入错误
    │
    ▼
参数解析失败 ───→ argparse 自动生成错误信息
    │                 $ ./tool --unknown-opt
    │                 usage: tool [-h] ...
    │                 tool: error: unrecognized arguments: --unknown-opt
    │
    ▼
文件不存在 ──────→ 自定义错误处理
    │                 try:
    │                     open(file)
    │                 except FileNotFoundError:
    │                     print(f"错误: 文件 '{file}' 不存在", file=sys.stderr)
    │                     sys.exit(1)
    │
    ▼
业务逻辑错误 ────→ 自定义异常装饰器
    │                 @handle_error
    │                 def safe_main():
    │                     # ...
    │
    ▼
未捕获异常 ──────→ 全局异常处理
                    try:
                        main()
                    except Exception as e:
                        if '--debug' in sys.argv:
                            traceback.print_exc()
                        else:
                            print(f"错误: {e}", file=sys.stderr)
                        sys.exit(1)
```

## 7️⃣ Phase 2 学习路径总览

```
Phase 2: 核心编程概念 (Day 16–30)

Day 16-18: 数据结构基础
  ┌─────────────────────────────────────┐
  │ 列表 │ 元组 │ 集合 │ 字典            │
  └─────────────────────────────────────┘

Day 19: 字符串处理
  ┌─────────────────────────────────────┐
  │ 字符串方法 │ 正则 │ 格式化           │
  └─────────────────────────────────────┘

Day 20-23: 函数与函数式编程
  ┌─────────────────────────────────────┐
  │ 函数进阶 │ 迭代器 │ 生成器           │
  │ 装饰器   │ 高阶函数 │ lambda         │
  │ 映射/过滤/归约                       │
  └─────────────────────────────────────┘

Day 24-26: 进阶特性
  ┌─────────────────────────────────────┐
  │ 装饰器进阶 │ 上下文管理器            │
  │ 字符串进阶 │ datetime                │
  └─────────────────────────────────────┘

Day 27-29: 数据结构与算法
  ┌─────────────────────────────────────┐
  │ datetime │ 数据结构综合 │ 算法入门    │
  └─────────────────────────────────────┘

Day 30: 命令行工具 🏆
  ┌─────────────────────────────────────┐
  │ sys.argv │ argparse │ 文件工具       │
  │ 搜索工具 │ JSON工具 │ 输出格式化     │
  │ 安装打包 │ 综合项目                  │
  └─────────────────────────────────────┘

下一站: Phase 3 — 面向对象编程 🚀
```
