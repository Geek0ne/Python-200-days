# Day 096 — AST 与代码分析

> 抽象语法树是 Python 理解代码的"骨架"。掌握 AST，你就能让程序"读懂"并"改造"自身。

---

## 一、抽象语法树（ast 模块）

### 1.1 什么是 AST？

**抽象语法树**（Abstract Syntax Tree）是源代码的树状结构化表示。Python 解释器在执行代码前，会先把源码解析成 AST，再编译成字节码。

```
源代码 → AST → 字节码 → 执行
         ↑
      我们要操作这一层
```

**为什么需要 AST？**

| 需求 | 说明 |
|------|------|
| 静态分析 | 不运行代码就能检查语法和结构 |
| 代码变换 | 自动修改/生成代码 |
| Lint 工具 | 实现自定义代码规范检查 |
| 代码生成 | 从数据或 DSL 生成 Python 代码 |

### 1.2 ast 模块核心概念

**Node 类型层级**（继承关系）：

```
AST (base)
├── stmt (语句)
│   ├── FunctionDef    # def foo():
│   ├── ClassDef       # class Foo:
│   ├── Return         # return x
│   ├── Assign         # x = 1
│   ├── If             # if ...:
│   ├── For            # for x in ...:
│   ├── While          # while ...:
│   ├── Import         # import os
│   ├── With           # with open(...) as f:
│   └── Expr           # expression as statement
├── expr (表达式)
│   ├── Name           # 变量名
│   ├── Constant       # 字面量（3.8+）
│   ├── BinOp          # a + b
│   ├── Call           # func()
│   ├── Attribute      # obj.attr
│   ├── IfExp          # a if cond else b
│   ├── ListComp       # [x for x in ...]
│   └── Lambda         # lambda x: ...
├── operator (运算符)
│   ├── Add, Sub, Mult, Div, Mod, Pow
│   └── LShift, RShift, BitOr, BitXor, BitAnd
└── keyword (关键字参数)
```

### 1.3 基本操作

```python
import ast

# 解析源代码为 AST
tree = ast.parse("x = 1 + 2")

# 将 AST 转回源代码
print(ast.unparse(tree))  # "x = 1 + 2"（Python 3.9+）

# 查看 AST 结构
print(ast.dump(tree, indent=2))
```

**ast.dump 输出解读**：

```
Module(
  body=[
    Assign(
      targets=[Name(id='x', ctx=Store())],
      value=BinOp(
        left=Constant(value=1),
        op=Add(),
        right=Constant(value=2)
      )
    )
  ]
)
```

**关键字段含义**：

| 字段 | 含义 |
|------|------|
| `ctx` | 上下文：`Load()`=读取，`Store()`=赋值，`Del()`=删除 |
| `op` | 运算符类型（`Add()`, `Sub()`, `Mult()` 等） |
| `id` | 标识符名称 |
| `value` | 字面量的值 |

### 1.4 遍历 AST 的三种方式

#### 方式一：ast.NodeVisitor（推荐）

```python
import ast

class NameFinder(ast.NodeVisitor):
    """收集所有变量名"""
    def __init__(self):
        self.names = []

    def visit_Name(self, node):
        self.names.append(node.id)
        self.generic_visit(node)  # 继续遍历子节点

tree = ast.parse("x = a + b; print(x)")
finder = NameFinder()
finder.visit(tree)
print(finder.names)  # ['x', 'a', 'b', 'x']
```

#### 方式二：ast.walk（递归遍历）

```python
import ast

tree = ast.parse("x = 1 + 2")
for node in ast.walk(tree):
    print(type(node).__name__, end=" ")
# Module Assign Name Constant BinOp Add Constant
```

#### 方式三：ast.NodeTransformer（修改 AST）

```python
import ast

class NumAdder(ast.NodeTransformer):
    """把所有数字加 1"""
    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            return ast.Constant(value=node.value + 1)
        return node

tree = ast.parse("x = 10 + 20")
new_tree = ast.NodeTransformer().visit(tree)
ast.fix_missing_locations(new_tree)  # 补全行号信息
print(ast.unparse(new_tree))  # "x = 11 + 21"
```

---

## 二、代码生成与变换

### 2.1 ast.parse 与 ast.unparse

```python
import ast

# 解析
source = "result = sum([i**2 for i in range(10)])"
tree = ast.parse(source)

# 代码变换（在 AST 上操作）
# ...（中间变换逻辑）...

# 还原为代码
print(ast.unparse(tree))  # Python 3.9+
```

**⚠️ Python 版本注意**：
- `ast.unparse()` 需要 **Python 3.9+**
- 3.8 可用 `astor` 库：`pip install astor` → `astor.to_source(tree)`
- 3.7 可用 `astunparse`：`pip install astunparse`

### 2.2 手动构建 AST 节点

```python
import ast

# 构建：print("Hello, AST!")
node = ast.Expr(
    value=ast.Call(
        func=ast.Name(id='print', ctx=ast.Load()),
        args=[ast.Constant(value='Hello, AST!')],
        keywords=[]
    )
)
tree = ast.Module(body=[node], type_ignores=[])
ast.fix_missing_locations(tree)
code = compile(tree, '<ast>', 'exec')
exec(code)  # 输出: Hello, AST!
```

**构建节点的速查表**：

| 目标代码 | AST 构造 |
|---------|---------|
| `x = 1` | `Assign(targets=[Name('x', Store())], value=Constant(1))` |
| `return x` | `Return(value=Name('x', Load()))` |
| `if x: pass` | `If(test=Name('x', Load()), body=[Pass()], orelse=[])` |
| `def f(): pass` | `FunctionDef(name='f', args=arguments(...), body=[Pass()])` |
| `import os` | `Import(names=[alias(name='os')])` |
| `a + b` | `BinOp(left=Name('a'), op=Add(), right=Name('b'))` |

### 2.3 代码变换实战：自动添加类型注解

```python
import ast

class TypeAnnotator(ast.NodeTransformer):
    """给函数参数添加类型注解"""
    def __init__(self, annotations: dict):
        # annotations: {"x": "int", "y": "str"}
        self.annotations = annotations

    def visit_FunctionDef(self, node):
        for arg in node.args.args:
            if arg.arg in self.annotations and arg.annotation is None:
                arg.annotation = ast.Name(
                    id=self.annotations[arg.arg],
                    ctx=ast.Load()
                )
        return node

source = """
def greet(name, age):
    return f"Hello {name}, you are {age}"
"""
tree = ast.parse(source)
annotator = TypeAnnotator({"name": "str", "age": "int"})
new_tree = annotator.visit(tree)
ast.fix_missing_locations(new_tree)
print(ast.unparse(new_tree))
```

---

## 三、静态分析工具实现

### 3.1 什么是静态分析？

**静态分析**是指**不运行程序**的情况下，通过分析源代码的结构和内容来发现潜在问题。

```
源代码 → 解析器 → AST → 分析器 → 报告
                            ↑
                        规则在这里执行
```

### 3.2 常见分析维度

| 分析类型 | 检查内容 | 典型工具 |
|---------|---------|---------|
| 语法检查 | 代码是否合法 | ast.parse 直接报错 |
| 命名规范 | 变量/函数命名风格 | pylint, flake8 |
| 复杂度分析 | 函数复杂度、嵌套深度 | radon |
| 安全检查 | 危险函数调用、SQL 注入 | bandit |
| 类型检查 | 类型注解一致性 | mypy |
| 死代码检测 | 未使用的变量/导入 | vulture |
| 依赖分析 | 函数间调用关系 | 自定义 |

### 3.3 实现一个函数复杂度分析器

```python
import ast

class ComplexityAnalyzer(ast.NodeVisitor):
    """计算函数的圈复杂度（Cyclomatic Complexity）"""
    # 复杂度 = 分支数 + 1

    def __init__(self):
        self.results = []

    def _calc(self, node):
        """计算单个函数的复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For,
                                  ast.ExceptHandler, ast.With)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or 每个操作数 +1
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Assert):
                complexity += 1

        return complexity

    def visit_FunctionDef(self, node):
        cc = self._calc(node)
        self.results.append((node.name, cc, node.lineno))
        self.generic_visit(node)

source = """
def risky_function(a, b):
    if a > 0:
        if b > 0:
            return a + b
    elif a < 0:
        for i in range(b):
            if i % 2 == 0:
                print(i)
    else:
        try:
            result = a / b
        except ZeroDivisionError:
            result = 0
    return result
"""

tree = ast.parse(source)
analyzer = ComplexityAnalyzer()
analyzer.visit(tree)

for name, cc, line in analyzer.results:
    level = "🟢 简单" if cc <= 5 else "🟡 中等" if cc <= 10 else "🔴 复杂"
    print(f"函数 {name}（第{line}行）: 圈复杂度 = {cc} {level}")
```

### 3.4 实现变量作用域分析器

```python
import ast

class ScopeAnalyzer(ast.NodeVisitor):
    """分析函数内变量的定义和使用"""

    def __init__(self):
        self.definitions = {}  # name -> [line]
        self.usages = {}       # name -> [line]

    def visit_FunctionDef(self, node):
        # 分析函数体
        self._analyze_body(node)
        self.generic_visit(node)

    def _analyze_body(self, func_node):
        """分析函数体中的变量"""
        for node in ast.walk(func_node):
            # 赋值 = 定义
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self._add_def(target.id, node.lineno)
                # 右侧是使用
                self._check_value(node.value)

            # For 循环变量 = 定义
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    self._add_def(node.target.id, node.lineno)

            # 名称引用 = 使用
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                self._add_use(node.id, node.lineno)

    def _add_def(self, name, line):
        self.definitions.setdefault(name, []).append(line)

    def _add_use(self, name, line):
        self.usages.setdefault(name, []).append(line)

    def _check_value(self, node):
        """检查表达式中的名称引用"""
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                self._add_use(child.id, child.lineno)

    def report(self):
        # 未使用的变量
        unused = set(self.definitions) - set(self.usages)
        # 未定义的变量（可能是全局变量）
        undefined = set(self.usages) - set(self.definitions)

        print("=== 变量分析报告 ===")
        if unused:
            print(f"未使用的变量: {', '.join(sorted(unused))}")
        else:
            print("所有变量均被使用 ✓")
        if undefined:
            print(f"可能的外部变量: {', '.join(sorted(undefined))}")

source = """
def analyze(x, y):
    temp = x + y
    unused_var = 42
    result = temp * 2
    print(result)
    return result
"""
tree = ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        analyzer = ScopeAnalyzer()
        analyzer.visit(node)
        analyzer.report()
```

---

## 四、实战：自定义 Linter

### 4.1 Linter 的工作流程

```
┌─────────────────────────────────────────────┐
│              自定义 Linter                    │
├─────────────────────────────────────────────┤
│                                             │
│  1. 读取源文件                               │
│     ↓                                       │
│  2. ast.parse() 解析为 AST                  │
│     ↓                                       │
│  3. 遍历 AST，运行规则检查器                  │
│     ↓                                       │
│  4. 收集所有告警                              │
│     ↓                                       │
│  5. 格式化输出报告                            │
│                                             │
└─────────────────────────────────────────────┘
```

### 4.2 实现一个迷你 Linter

```python
import ast
import sys
from dataclasses import dataclass, field
from typing import List

@dataclass
class LintWarning:
    """一条 Lint 告警"""
    line: int
    col: int
    code: str       # e.g. "W001"
    message: str
    severity: str   # "warning" | "error"

    def __str__(self):
        return f"  L{self.line}:{self.col} [{self.severity.upper()}] {self.code}: {self.message}"


class Linter(ast.NodeVisitor):
    """自定义 Linter：检查常见代码问题"""

    def __init__(self):
        self.warnings: List[LintWarning] = []

    # ===== 规则集合 =====

    def visit_FunctionDef(self, node):
        self._check_func_name(node)
        self._check_func_length(node)
        self._check_func_args(node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        self._check_var_name(node)
        self.generic_visit(node)

    def visit_Call(self, node):
        self._check_bare_except(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self._check_class_name(node)
        self.generic_visit(node)

    # ===== 具体规则 =====

    def _check_func_name(self, node):
        """规则 W001：函数名应使用 snake_case"""
        import re
        if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
            self.warnings.append(LintWarning(
                line=node.lineno,
                col=node.col_offset,
                code="W001",
                message=f"函数名 '{node.name}' 应使用 snake_case 命名",
                severity="warning"
            ))

    def _check_func_length(self, node):
        """规则 W002：函数不应超过 50 行"""
        end = getattr(node, 'end_lineno', None)
        if end:
            length = end - node.lineno + 1
            if length > 50:
                self.warnings.append(LintWarning(
                    line=node.lineno,
                    col=node.col_offset,
                    code="W002",
                    message=f"函数 '{node.name}' 有 {length} 行，建议不超过 50 行",
                    severity="warning"
                ))

    def _check_func_args(self, node):
        """规则 W003：函数参数不应超过 5 个"""
        arg_count = len(node.args.args)
        if arg_count > 5:
            self.warnings.append(LintWarning(
                line=node.lineno,
                col=node.col_offset,
                code="W003",
                message=f"函数 '{node.name}' 有 {arg_count} 个参数，建议不超过 5 个",
                severity="warning"
            ))

    def _check_var_name(self, node):
        """规则 W004：变量名应使用 snake_case"""
        import re
        for target in node.targets:
            if isinstance(target, ast.Name) and not re.match(r'^[a-z_][a-z0-9_]*$', target.id):
                if not target.id.startswith('_'):
                    self.warnings.append(LintWarning(
                        line=node.lineno,
                        col=node.col_offset,
                        code="W004",
                        message=f"变量名 '{target.id}' 应使用 snake_case",
                        severity="warning"
                    ))

    def _check_class_name(self, node):
        """规则 W005：类名应使用 PascalCase"""
        import re
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
            self.warnings.append(LintWarning(
                line=node.lineno,
                col=node.col_offset,
                code="W005",
                message=f"类名 '{node.name}' 应使用 PascalCase",
                severity="warning"
            ))

    def _check_bare_except(self, node):
        """规则 E001：不应使用裸 except"""
        if isinstance(node.func, ast.Name) and node.func.id == 'raise':
            pass  # skip raise
        # 注意：bare except 检查在 ExceptionHandler 节点

    def report(self) -> str:
        if not self.warnings:
            return "✅ 未发现问题！"
        lines = [f"发现 {len(self.warnings)} 个问题：\n"]
        for w in sorted(self.warnings, key=lambda x: x.line):
            lines.append(str(w))
        return "\n".join(lines)


def lint_file(filepath: str):
    """对单个文件运行 Linter"""
    with open(filepath, 'r') as f:
        source = f.read()

    tree = ast.parse(source, filename=filepath)
    linter = Linter()
    linter.visit(tree)
    print(f"📄 {filepath}")
    print(linter.report())
    return linter.warnings


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python linter.py <file.py>")
        sys.exit(1)

    all_warnings = []
    for path in sys.argv[1:]:
        all_warnings.extend(lint_file(path))

    sys.exit(1 if any(w.severity == "error" for w in all_warnings) else 0)
```

### 4.3 进阶：实现多文件分析

```python
import ast
import os
import sys
from pathlib import Path

class ProjectLinter:
    """项目级别的 Linter"""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.results = {}

    def find_python_files(self) -> list:
        """递归查找所有 .py 文件"""
        files = []
        for path in self.root_dir.rglob("*.py"):
            # 跳过常见的不需要检查的目录
            parts = path.parts
            if any(skip in parts for skip in ['venv', '.venv', 'node_modules', '__pycache__']):
                continue
            files.append(path)
        return sorted(files)

    def lint_file(self, filepath: Path) -> list:
        """分析单个文件"""
        try:
            source = filepath.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(filepath))

            # 自定义分析器
            linter = Linter()
            linter.visit(tree)

            return linter.warnings
        except SyntaxError as e:
            return [LintWarning(
                line=e.lineno or 1,
                col=e.offset or 0,
                code="E999",
                message=f"语法错误: {e.msg}",
                severity="error"
            )]

    def lint_project(self):
        """分析整个项目"""
        files = self.find_python_files()
        print(f"🔍 扫描 {len(files)} 个 Python 文件...\n")

        total_warnings = 0
        total_errors = 0

        for filepath in files:
            warnings = self.lint_file(filepath)
            if warnings:
                rel = filepath.relative_to(self.root_dir)
                print(f"📄 {rel}")
                for w in warnings:
                    print(f"   L{w.line} [{w.severity.upper()}] {w.code}: {w.message}")
                print()
                total_warnings += sum(1 for w in warnings if w.severity == "warning")
                total_errors += sum(1 for w in warnings if w.severity == "error")

        print("=" * 50)
        print(f"📊 总计: {total_errors} 个错误, {total_warnings} 个警告")
        return total_errors, total_warnings
```

---

## 五、AST 高级技巧

### 5.1 exec 与 compile 配合 AST

```python
import ast

# 从 AST 生成可执行代码
tree = ast.parse("""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
""")

# 编译
code = compile(tree, '<fib>', 'exec')

# 执行
exec(code)  # 输出: 55
```

### 5.2 ast.literal_eval 的安全求值

```python
import ast

# 安全地解析 Python 字面量（不执行任意代码）
data = ast.literal_eval("{'name': '聂董', 'age': 30, 'scores': [95, 88, 72]}")
print(data)
# {'name': '聂董', 'age': 30, 'scores': [95, 88, 72]}

# 对比 eval（危险！不要用）
# eval("__import__('os').system('rm -rf /')")  # ❌ 绝对不要
```

**为什么 `ast.literal_eval` 安全？**

```
eval()     → 可执行任意代码（函数调用、导入等）
ast.literal_eval() → 只接受字面量：
  ✓ 数字、字符串、布尔、None
  ✓ 列表、元组、字典、集合
  ✗ 函数调用、变量引用、import
```

### 5.3 代码格式化的 AST 实现

```python
import ast

class CodeFormatter:
    """基于 AST 的简单代码格式化器"""

    @staticmethod
    def indent_code(source: str, indent_size: int = 4) -> str:
        """规范化缩进"""
        tree = ast.parse(source)
        lines = source.splitlines()
        result = []

        for node in ast.walk(tree):
            if hasattr(node, 'lineno'):
                # 简单的缩进规范化
                line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                if line:
                    # 去掉前导空格，按层级重新缩进
                    stripped = line.lstrip()
                    indent = " " * (node.col_offset)
                    result.append(indent + stripped)

        return "\n".join(result) if result else source
```

### 5.4 安全的动态代码执行流程

```
用户输入 → ast.literal_eval / ast.parse
              ↓
         是否安全？
         ├─ 是 → compile() → exec() / eval()
         └─ 否 → 拒绝执行，返回错误
```

---

## 六、Mermaid 图解

### AST 解析流程

```mermaid
graph TD
    A[Python 源代码] --> B[Tokenizer 词法分析]
    B --> C[Tokens 流]
    C --> D[Parser 语法分析]
    D --> E[AST 抽象语法树]
    E --> F[Compiler 编译器]
    F --> G[字节码 .pyc]
    G --> H[Python 虚拟机执行]
    
    style E fill:#ff9,stroke:#333,stroke-width:2px
    style A fill:#9f9,stroke:#333
```

### Linter 分析流程

```mermaid
flowchart LR
    A[源文件] --> B[ast.parse]
    B --> C[AST]
    C --> D[规则 1: 命名检查]
    C --> E[规则 2: 复杂度检查]
    C --> F[规则 3: 安全检查]
    D --> G[告警收集]
    E --> G
    F --> G
    G --> H[格式化输出]
```

---

## 七、思考题

1. **AST 与正则表达式的区别**：为什么不能用正则表达式来解析 Python 代码？用 AST 做代码分析相比正则有什么优势？

**参考答案**

根本原因是 **Python 不是「正则语言」，而是上下文无关文法**：它有任意深度的嵌套（括号、缩进块、推导式里再套推导式），而正则表达式没有「配对计数」能力，无法可靠匹配嵌套结构。

用正则解析 Python 会踩的坑：

- **字符串和注释里的假代码**：`s = "def foo():"`、`# import os` 会被当成真的定义/导入。
- **上下文歧义**：跨行括号续行、`\` 续行、三引号跨行字符串、`f(a, b)` 与 `f (a)(b)`，正则每遇到一种就要打一个补丁。
- **同名不同义**：`x = 1` 里的 `x` 是赋值（Store），`y = x` 里的 `x` 是读取（Load）；正则看不出区别，AST 的 `ctx` 字段直接告诉你。
- **缩进即语法**：Python 用缩进划分代码块，正则很难还原「这个 return 属于哪个 if」。

AST 的优势是**结构化 + 语义化**：`ast.parse` 用的是 Python 官方解析器，缩进、续行、转义全部正确处理；节点自带 `lineno`/`col_offset` 可精确定位；`isinstance(node, ast.Call)` 判类型比字符串匹配可靠；改完还能用 `ast.unparse` 还原成代码，或用 `compile` 直接执行。

小例子：想统计「所有对 eval 的调用」，正则 `eval\(` 会把 `my_eval(`、`"eval("`、`# eval(` 全算进去；AST 里只需判断 `isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "eval"`，零误报。

⚠️ 注意：AST 也不万能——它丢掉了注释和原始排版（`ast.unparse` 会重排引号与空格），需要保留格式时用 `tokenize` 或 `libcst`；而且 AST 只做语法分析，不做类型推断和跨模块符号解析，那些要交给 mypy/pyright。

2. **安全执行**：`ast.literal_eval` 为什么比 `eval` 安全？如果要设计一个安全的在线 Python 执行环境，需要做哪些防护措施？

**参考答案**

`eval` 会**编译并执行任意表达式**：能调函数、能 `__import__`、能通过属性访问一路摸到 `os`/`subprocess`。`ast.literal_eval` 则先把字符串解析成 AST，再**只放行白名单节点**（Constant、List、Tuple、Dict、Set，以及数字前的正负号和复数加减），遇到 Call / Name / Attribute / Import 一律抛 `ValueError`——代码根本没被执行。

下面用一个带副作用的函数直观对比（`eval` 的参数是写死的字面量，仅用于演示差异）：

```python
import ast

# ✅ literal_eval 只接受字面量：数字/字符串/布尔/None/列表/元组/字典/集合
print("字典:", ast.literal_eval("{'name': '张三', 'scores': [95, 88]}"))
print("集合:", ast.literal_eval("{1, 2, 3}"))
print("负数:", ast.literal_eval("-42"))

# 用一个带副作用的函数，直观看出「代码有没有真的被执行」
counter = {"n": 0}


def ping():
    counter["n"] += 1
    return "pong"


# ❌ eval 会真的调用函数，副作用发生了
print("eval 调用 :", eval("ping()"), "| 副作用计数:", counter["n"])

# ✅ literal_eval 直接拒绝，函数根本不会被调用
for bad in ["ping()", "__import__('os').getcwd()", "x + 1", "[i for i in range(3)]"]:
    try:
        ast.literal_eval(bad)
        print("竟然通过了:", bad)
    except (ValueError, SyntaxError) as e:
        print("拒绝:", bad, "->", type(e).__name__, "| 副作用计数:", counter["n"])
```

运行输出（已验证）：

```
字典: {'name': '张三', 'scores': [95, 88]}
集合: {1, 2, 3}
负数: -42
eval 调用 : pong | 副作用计数: 1
拒绝: ping() -> ValueError | 副作用计数: 1
拒绝: __import__('os').getcwd() -> ValueError | 副作用计数: 1
拒绝: x + 1 -> ValueError | 副作用计数: 1
拒绝: [i for i in range(3)] -> ValueError | 副作用计数: 1
```

`eval("ping()")` 让计数从 0 变成 1（真的执行了），而 `literal_eval` 对同样的字符串直接拒绝，计数不再增长。但要注意 `literal_eval` **不是沙箱**：它仍要解析整个字符串，超深嵌套或超大字面量能撑爆内存/递归栈，所以还得限制输入长度。

设计在线 Python 执行环境需要多层防护，缺一不可：

1. **进程隔离**：每次执行起独立子进程，绝不在主服务进程里 `exec`。
2. **操作系统级沙箱**：容器 / gVisor / Firecracker + seccomp 过滤系统调用，只读根文件系统，非 root 用户，禁网或只放行白名单。
3. **资源上限**：`resource.setrlimit` 限制 CPU 时间、内存、文件大小、进程数；外层再加 wall-clock 超时并强杀，防死循环和 fork 炸弹。
4. **输入输出限制**：限制源码长度和 stdout 大小；AST 预检黑名单（`import os`、`open`、`__` 开头的属性访问）只能作为**额外**一层，不能当唯一防线。
5. **清理与审计**：执行完销毁临时目录和容器，记录源码与结果供审计。

⚠️ 注意：「清空 `__builtins__`」或「删掉 `__import__`」这类纯 Python 沙箱**都能被绕过**（通过 `().__class__.__mro__` 摸到 `object` 再枚举子类），pysandbox 项目就是因此被作者宣布失败。真正的隔离必须落到操作系统层。

3. **代码变换的局限性**：使用 `ast.NodeTransformer` 修改 AST 时，为什么需要调用 `ast.fix_missing_locations()`？如果省略会发生什么？

**参考答案**

`compile()` 要求每个语句/表达式节点都带 `lineno`、`col_offset`（3.8+ 还有 `end_lineno`、`end_col_offset`），因为字节码要附带行号表，供 traceback 和调试器使用。`ast.parse` 出来的节点自带这些字段，但**手工 `ast.Expr(...)` 新建的、或 `NodeTransformer` 里替换出来的节点没有**，于是编译时直接抛 `TypeError: required field "lineno" missing from stmt`。

`ast.fix_missing_locations(tree)` 做的事就是**自顶向下把父节点的位置信息「继承」给缺失的子节点**（就地修改并返回同一棵树）。它只补缺失的，已有行号的节点保持原值。

```python
import ast

# 手工造一个 print("Hello, AST!") 节点，故意不带行号/列号
node = ast.Expr(
    value=ast.Call(
        func=ast.Name(id="print", ctx=ast.Load()),
        args=[ast.Constant(value="Hello, AST!")],
        keywords=[],
    )
)
tree = ast.Module(body=[node], type_ignores=[])

# unparse 只是「拼字符串」，不需要位置信息
print("unparse 不需要行号:", ast.unparse(tree))

# ❌ 省略 fix_missing_locations：compile 直接报错
try:
    compile(tree, "<ast>", "exec")
    print("竟然编译成功了")
except (TypeError, ValueError) as e:
    print("省略 fix_missing_locations ->", type(e).__name__, ":", e)

# ✅ 补全位置信息后就能编译执行
ast.fix_missing_locations(tree)
exec(compile(tree, "<ast>", "exec"))
print("补全后的行号/列号:", node.lineno, node.col_offset)
```

运行输出（已验证，Python 3.12）：

```
unparse 不需要行号: print('Hello, AST!')
省略 fix_missing_locations -> TypeError : required field "lineno" missing from stmt
Hello, AST!
补全后的行号/列号: 1 0
```

第三行的 `Hello, AST!` 是补全位置后 `exec` 真正执行出来的。注意 `ast.unparse` 不需要行号（它只是拼字符串），所以「能 unparse」不代表「能 compile」——这正是这个坑容易被忽略的原因。

💡 提示：更精确的做法是用 `ast.copy_location(new_node, old_node)` 从被替换的旧节点拷贝真实位置，整棵树变换完再统一调一次 `fix_missing_locations` 兜底。另外 `NodeTransformer` 的 `visit_*` 返回 `None` 表示删除该节点、返回新节点表示替换，所以别忘了 `return node`，否则整棵子树会被静默删掉。

4. **性能考虑**：在一个大型项目（10万行代码）中运行自定义 Linter，你会选择哪种遍历方式（NodeVisitor / walk / 手动递归）？为什么？

**参考答案**

选 **`ast.NodeVisitor`**（需要改写代码时用它的子类 `NodeTransformer`），核心理由是「一次遍历 + 按类型分派」，代码量和运行开销都最小。

三种方式的实际差别：

- **`NodeVisitor`**：`visit_FunctionDef`、`visit_Call` 这样的方法名直接对应节点类型，分派是一次属性查找；只为你关心的类型写逻辑，其余靠 `generic_visit` 自动下沉。一次遍历就能同时跑十几条规则。
- **`ast.walk`**：广度优先把所有节点摊平成序列，写法最简单，但**每条规则都要重新 walk 一遍整棵树**，N 条规则就是 N 次全量遍历；而且它丢掉了父子关系，做「函数内变量作用域」「嵌套深度」这类需要上下文的检查很别扭。
- **手动递归**：最灵活，但要自己处理所有节点类型和字段，容易漏掉 `ast.arguments`、`ast.comprehension` 这些非 stmt/expr 的中间节点，维护成本高。

10 万行项目的工程做法：**每个文件只 `ast.parse` 一次**，把 tree 传给所有规则共享；用 `ProcessPoolExecutor` 按文件并行（AST 分析是 CPU 密集型，多进程才吃得到多核并绕开 GIL）；「函数长度」「圈复杂度」这类需要子树统计的规则，在 `visit_FunctionDef` 里只对**该子树**做一次局部 walk，而不是对全树反复 walk；再按「文件 mtime + 内容哈希」缓存结果，跳过未改动的文件。

小例子：20 条规则用 `walk` 就是 20 次全树遍历；用 `NodeVisitor` 把 20 条规则按节点类型挂进同一个 visitor 只需 1 次遍历，差距通常是数倍（因机器/规则数量而异）。

⚠️ 注意：`NodeVisitor` 重写了 `visit_Xxx` 后**不会**自动递归，必须显式调用 `self.generic_visit(node)`，否则该节点内部的告警全部漏掉——这是自定义 Linter 最常见的 bug。

5. **扩展性**：如何让自定义 Linter 支持通过配置文件（如 `.lintrc`）来启用/禁用规则？设计一个简单的插件机制。

**参考答案**

思路是把「规则」和「引擎」解耦：**规则用装饰器注册进一张表，引擎只负责读配置、按节点类型分派、收集告警**。这样新增规则不用改引擎，启用/禁用/调阈值全靠配置文件。

三个组成部分：

1. **注册表 + 装饰器**：`@rule("W001", ast.FunctionDef, "函数名应使用 snake_case")` 把处理函数、关心的节点类型、提示语和默认开关一起存进 `RULES`。
2. **配置合并**：优先级为 `disable` > `rules` 里的显式开关 > 插件默认值；`options` 提供阈值等参数（如 `max_args`）。配置用 JSON/TOML 都行，`.lintrc` 读进来 `json.loads` 即可。
3. **引擎**：构造时把启用的规则按 `node_type` 分桶，`visit` 里查桶执行——整棵树只遍历一次，规则再多也不增加遍历次数。

```python
import ast
import json

# ---------- 1. 规则注册表：用装饰器把规则「插」进来 ----------
RULES = {}


def rule(code, node_type, message, enabled=True):
    """插件注册装饰器：新增规则只需写一个函数，不用改 Linter 主体"""
    def deco(func):
        RULES[code] = {"func": func, "node_type": node_type,
                       "message": message, "enabled": enabled}
        return func
    return deco


# ---------- 2. 三个示例规则，编号沿用本课的 Linter ----------
@rule("W001", ast.FunctionDef, "函数名应使用 snake_case")
def check_func_name(node, opts):
    name = node.name.lstrip("_")        # 允许下划线开头的私有函数
    return node.name if name and not name.islower() else None


@rule("W003", ast.FunctionDef, "函数参数过多")
def check_args(node, opts):
    limit = opts.get("max_args", 5)     # 阈值可由配置调整
    n = len(node.args.args)
    return f"{n} 个参数 > {limit}" if n > limit else None


@rule("E001", ast.ExceptHandler, "不应使用裸 except")
def check_bare_except(node, opts):
    return "未指定异常类型" if node.type is None else None


# ---------- 3. Linter 主体：按配置决定启用哪些规则 ----------
class Linter(ast.NodeVisitor):
    def __init__(self, config):
        self.config = config
        self.warnings = []
        self.active = {}                # 节点类型 -> [规则编号]
        for code, meta in RULES.items():
            on = config.get("rules", {}).get(code, meta["enabled"])
            if code in config.get("disable", []):
                on = False              # disable 优先级最高
            if on:
                self.active.setdefault(meta["node_type"], []).append(code)

    def visit(self, node):
        for code in self.active.get(type(node), []):
            meta = RULES[code]
            detail = meta["func"](node, self.config.get("options", {}))
            if detail is not None:
                sev = "ERROR" if code.startswith("E") else "WARNING"
                self.warnings.append(
                    f"L{node.lineno} [{sev}] {code}: {meta['message']}（{detail}）")
        return super().visit(node)      # 继续遍历子节点


# ---------- 4. 配置：真实项目里就是 .lintrc 的内容 ----------
# 读取方式: config = json.loads(Path(".lintrc").read_text(encoding="utf-8"))
cfg_a = json.loads('{"disable": ["W001"], "options": {"max_args": 5}}')
cfg_b = json.loads('{"rules": {"W001": true}, "options": {"max_args": 3}}')

source = """
def BadName(a, b, c, d, e, f):
    try:
        return a / b
    except:
        return 0
"""

for label, cfg in (("配置A：禁用 W001", cfg_a), ("配置B：启用 W001 且阈值改为 3", cfg_b)):
    print(label)
    linter = Linter(cfg)
    linter.visit(ast.parse(source))
    for w in linter.warnings:
        print("   ", w)
```

运行输出（已验证）：

```
配置A：禁用 W001
    L2 [WARNING] W003: 函数参数过多（6 个参数 > 5）
    L5 [ERROR] E001: 不应使用裸 except（未指定异常类型）
配置B：启用 W001 且阈值改为 3
    L2 [WARNING] W001: 函数名应使用 snake_case（BadName）
    L2 [WARNING] W003: 函数参数过多（6 个参数 > 3）
    L5 [ERROR] E001: 不应使用裸 except（未指定异常类型）
```

同一份被检查代码：配置 A 禁用了 W001，就只报「参数过多」和「裸 except」；配置 B 打开 W001 并把阈值从 5 改成 3，告警多了一条、W003 的文案也跟着变——**引擎代码一行没改**。

再往前一步就是真正的插件系统：把每条规则放进独立模块，用 `importlib.import_module` 按配置里的 `plugins = ["rules.naming", "rules.security"]` 动态导入（导入即触发装饰器注册），或用 `importlib.metadata.entry_points(group="mylinter.rules")` 让第三方 pip 包也能把规则挂进来。

💡 提示：配置里的规则编号要做校验，未知编号应报错而不是静默忽略，否则用户把 `W001` 写成 `W01` 会误以为规则生效了；`severity` 也建议可配置，让团队把「裸 except」从 warning 提升为 error，从而卡住 CI。

---

## 八、总结

| 概念 | 核心要点 |
|------|---------|
| AST 结构 | 语句(stmt) + 表达式(expr) + 运算符(operator) |
| 遍历方式 | NodeVisitor（安全）、walk（简单）、NodeTransformer（可修改） |
| 代码变换 | parse → 修改 AST → fix_missing_locations → unparse/compile |
| 静态分析 | 不运行代码就能发现问题 |
| 安全执行 | `ast.literal_eval` 只解析字面量，`eval/exec` 有安全风险 |

> **明日预告**：Day 097 — 领域特定语言（DSL），用 Python 元编程构建自己的 DSL！
