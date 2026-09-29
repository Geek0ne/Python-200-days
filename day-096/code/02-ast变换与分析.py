"""
Day 096 - 代码分析 - 02: AST 代码变换与静态分析
演示：NodeTransformer 变换 + 函数复杂度分析 + 变量作用域分析
"""
import ast
import re

# =============================================
# 第一部分：AST 变换 — 自动添加类型注解
# =============================================
print("=" * 60)
print("第一部分：AST 代码变换 — 自动添加类型注解")
print("=" * 60)

class TypeAnnotator(ast.NodeTransformer):
    """
    给函数参数添加类型注解
    使用方法：TypeAnnotator({"参数名": "类型名"})
    """

    def __init__(self, annotations: dict):
        self.annotations = annotations  # {"name": "str", "age": "int"}

    def visit_FunctionDef(self, node):
        for arg in node.args.args:
            # 跳过 'self' 参数
            if arg.arg == 'self':
                continue
            # 如果参数有注解则跳过，没有注解且在映射表中则添加
            if arg.arg in self.annotations and arg.annotation is None:
                arg.annotation = ast.Name(
                    id=self.annotations[arg.arg],
                    ctx=ast.Load()
                )
        return node


source = """
def greet(name, age):
    return f"Hello {name}, you are {age}"

def calculate(x, y):
    result = x + y
    return result

def already_annotated(x: int, y):
    return x + y
"""

tree = ast.parse(source)
annotator = TypeAnnotator({"name": "str", "age": "int", "x": "float", "y": "float"})
new_tree = annotator.visit(tree)
ast.fix_missing_locations(new_tree)

print("变换前:")
print(source)
print("\n变换后:")
print(ast.unparse(new_tree))


# =============================================
# 第二部分：函数圈复杂度分析
# =============================================
print("\n" + "=" * 60)
print("第二部分：函数圈复杂度分析")
print("=" * 60)

class ComplexityAnalyzer(ast.NodeVisitor):
    """
    计算函数的圈复杂度（Cyclomatic Complexity）
    复杂度 = 分支数 + 1
    分支包括：if/elif/else/for/while/except/and/or/assert/三元运算符
    """

    def __init__(self):
        self.results = []

    def _calc_complexity(self, node):
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            # 条件分支
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            # 异常处理
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            # 上下文管理器（with 语句）
            elif isinstance(child, ast.With):
                complexity += 1
            # 断言
            elif isinstance(child, ast.Assert):
                complexity += 1
            # 布尔运算（and/or 每增加一个操作数 +1）
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            # 三元表达式
            elif isinstance(child, ast.IfExp):
                complexity += 1

        return complexity

    def visit_FunctionDef(self, node):
        cc = self._calc_complexity(node)
        end_line = getattr(node, 'end_lineno', node.lineno)
        length = end_line - node.lineno + 1
        self.results.append({
            'name': node.name,
            'complexity': cc,
            'length': length,
            'line': node.lineno,
        })
        self.generic_visit(node)


source = """
def simple_function(x):
    return x + 1

def moderate_function(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item)
        elif item == 0:
            continue
        else:
            result.append(-item)
    return result

def complex_function(a, b, c, d):
    if a > 0:
        if b > 0:
            if c > 0:
                return a + b + c
            else:
                return a + b - c
        elif d:
            for i in range(a):
                if i % 2 == 0:
                    print(i)
        else:
            try:
                result = a / b
            except ZeroDivisionError:
                result = 0
    else:
        result = -a
    return result
"""
tree = ast.parse(source)
analyzer = ComplexityAnalyzer()
analyzer.visit(tree)

print(f"{'函数名':<25} {'复杂度':>6} {'行数':>6} {'评级'}")
print("-" * 55)
for r in analyzer.results:
    level = "🟢 简单" if r['complexity'] <= 5 else "🟡 中等" if r['complexity'] <= 10 else "🔴 复杂"
    print(f"{r['name']:<25} {r['complexity']:>6} {r['length']:>6}   {level}")


# =============================================
# 第三部分：变量作用域分析
# =============================================
print("\n" + "=" * 60)
print("第三部分：变量作用域分析")
print("=" * 60)

class ScopeAnalyzer(ast.NodeVisitor):
    """分析函数内变量的定义和使用情况"""

    def __init__(self):
        self.definitions = {}  # 变量名 -> [行号]
        self.usages = {}       # 变量名 -> [行号]

    def visit_FunctionDef(self, node):
        self._analyze_scope(node)
        self.generic_visit(node)

    def _analyze_scope(self, func_node):
        for node in ast.walk(func_node):
            # 赋值 = 定义
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self._add_def(target.id, node.lineno)
                # 检查右侧表达式
                self._scan_expr(node.value)

            # For 循环变量 = 定义
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    self._add_def(node.target.id, node.lineno)
                # 也要检查 iterable
                self._scan_expr(node.iter)

            # 带注解的赋值
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    self._add_def(node.target.id, node.lineno)
                if node.value:
                    self._scan_expr(node.value)

            # 名称引用 = 使用（Load 模式）
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                self._add_use(node.id, node.lineno)

    def _add_def(self, name, line):
        self.definitions.setdefault(name, []).append(line)

    def _add_use(self, name, line):
        self.usages.setdefault(name, []).append(line)

    def _scan_expr(self, expr):
        """扫描表达式中的名称引用"""
        for child in ast.walk(expr):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                self._add_use(child.id, child.lineno)

    def report(self):
        defined = set(self.definitions.keys())
        used = set(self.usages.keys())

        unused = defined - used         # 定义了但没用
        possibly_external = used - defined  # 用了但没在函数内定义

        print(f"\n  定义的变量: {defined or '无'}")
        print(f"  使用的变量: {used or '无'}")

        if unused:
            print(f"  ⚠️  未使用的变量: {', '.join(sorted(unused))}")
        else:
            print("  ✅ 所有变量均被使用")

        if possibly_external:
            print(f"  📎 可能的外部变量: {', '.join(sorted(possibly_external))}")

        # 显示每个变量的定义和使用位置
        print("\n  变量明细:")
        for name in sorted(defined | used):
            defs = self.definitions.get(name, [])
            uses = self.usages.get(name, [])
            def_str = f"定义@行{defs}" if defs else ""
            use_str = f"使用@行{uses}" if uses else ""
            print(f"    {name}: {def_str} {use_str}")


source = """
def analyze_data(values):
    total = 0
    count = len(values)
    unused_var = "我不会被使用"
    threshold = 10

    for v in values:
        if v > threshold:
            total += v
            print(v)

    average = total / count if count > 0 else 0
    return average
"""
tree = ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        analyzer = ScopeAnalyzer()
        analyzer.visit(node)
        analyzer.report()

print("\n✅ 进阶分析完成！")
