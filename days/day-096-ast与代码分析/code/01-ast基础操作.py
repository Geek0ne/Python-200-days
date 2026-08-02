"""
Day 096 - 代码分析 - 01: AST 基础操作
演示：解析、遍历、dump AST
"""
import ast

# ===== 1. 解析源代码 =====
source = """
x = 10
y = 20
result = x + y
print(result)
"""
print("=== 源代码 ===")
print(source)

tree = ast.parse(source)

print("=== ast.dump 输出 ===")
print(ast.dump(tree, indent=2))

print("\n=== ast.unparse 还原 ===")
print(ast.unparse(tree))

# ===== 2. AST 节点类型 =====
print("\n=== AST 节点类型 ===")
for node in ast.walk(tree):
    indent = "  " * getattr(node, 'lineno', 0)
    print(f"{type(node).__name__}", end="")

    if isinstance(node, ast.Name):
        print(f" (id='{node.id}', ctx={type(node.ctx).__name__})", end="")
    elif isinstance(node, ast.Constant):
        print(f" (value={node.value!r})", end="")
    elif isinstance(node, ast.BinOp):
        print(f" (op={type(node.op).__name__})", end="")
    elif isinstance(node, ast.Assign):
        print(f" (targets={len(node.targets)})", end="")
    print()

# ===== 3. 遍历 AST 查找所有函数 =====
print("\n=== 查找所有函数定义 ===")

source2 = """
def greet(name):
    return f"Hello, {name}!"

def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
"""
tree2 = ast.parse(source2)

for node in ast.walk(tree2):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = [a.arg for a in node.args.args]
        print(f"  函数: {node.name}({', '.join(args)}) @ 行 {node.lineno}")
    elif isinstance(node, ast.ClassDef):
        print(f"  类: {node.name} @ 行 {node.lineno}")

# ===== 4. 自定义 NodeVisitor =====
print("\n=== 自定义 Visitor：收集所有字符串常量 ===")

class StringCollector(ast.NodeVisitor):
    def __init__(self):
        self.strings = []

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            self.strings.append((node.value, node.lineno))
        self.generic_visit(node)

source3 = """
msg = "Hello"
print("World")
config = {"key": "value", "debug": True}
"""
tree3 = ast.parse(source3)
collector = StringCollector()
collector.visit(tree3)

for s, line in collector.strings:
    print(f"  第 {line} 行: '{s}'")

print("\n✅ 基础操作完成！")
