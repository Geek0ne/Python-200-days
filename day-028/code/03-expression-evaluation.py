"""
Day 028 — 数据结构综合：表达式求值实战
======================================================================
使用栈实现中缀表达式求值计算器
  1. 中缀转后缀（调度场算法）
  2. 后缀表达式求值
  3. 整合为完整计算器
======================================================================
"""

import re
from collections import deque


# ====================================================================
# 第一部分：后缀表达式求值（逆波兰表示法）
# ====================================================================
print("=" * 60)
print("1️⃣  后缀表达式（逆波兰表示法）求值")
print("=" * 60)

def eval_rpn(tokens):
    """
    计算逆波兰表达式
    输入: ["2", "1", "+", "3", "*"]  →  9
    """
    stack = []
    operators = {'+', '-', '*', '/'}

    for token in tokens:
        if token not in operators:
            stack.append(float(token))
        else:
            b = stack.pop()
            a = stack.pop()
            if token == '+':
                stack.append(a + b)
            elif token == '-':
                stack.append(a - b)
            elif token == '*':
                stack.append(a * b)
            elif token == '/':
                if b == 0:
                    raise ZeroDivisionError("division by zero")
                stack.append(a / b)

    return stack[0]

# 测试后缀表达式
test_rpns = [
    (["3", "4", "+"], "3 + 4", 7),
    (["3", "4", "2", "1", "-", "*", "+"],
     "3 + 4 * (2 - 1)", 7),
    (["2", "1", "+", "3", "*"],
     "(2 + 1) * 3", 9),
    (["5", "1", "2", "+", "4", "*", "+", "3", "-"],
     "5 + ((1 + 2) * 4) - 3", 14),
    (["10", "3", "/"],
     "10 / 3", 10 / 3),
]

print("后缀表达式求值测试:")
for tokens, expr, expected in test_rpns:
    result = eval_rpn(tokens)
    status = "✅" if abs(result - expected) < 1e-9 else "❌"
    print(f"  {status} {expr:25s} = {result:8.2f} (期望 {expected:8.2f})")


# ====================================================================
# 第二部分：中缀表达式 → 后缀表达式（调度场算法）
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  中缀表达式 → 后缀表达式（调度场算法）")
print("=" * 60)

def infix_to_rpn(expression):
    """
    调度场算法 (Shunting-yard algorithm)
    将中缀表达式转换为后缀表达式
    """
    # 定义运算符优先级
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3}
    # 定义运算符结合性（True = 右结合，False = 左结合）
    right_assoc = {'^': True}
    operators = set(precedence.keys())

    output = []
    op_stack = []

    # 分词
    tokens = tokenize(expression)

    for token in tokens:
        if token.isdigit() or '.' in token:  # 数字
            output.append(token)
        elif token == '(':
            op_stack.append(token)
        elif token == ')':
            # 弹出直到匹配左括号
            while op_stack and op_stack[-1] != '(':
                output.append(op_stack.pop())
            if not op_stack:
                raise ValueError("括号不匹配")
            op_stack.pop()  # 移除左括号
        elif token in operators:
            # 处理运算符优先级
            while (op_stack and op_stack[-1] != '(' and
                   (precedence.get(op_stack[-1], 0) > precedence[token] or
                    (precedence.get(op_stack[-1], 0) == precedence[token] and
                     not right_assoc.get(token, False)))):
                output.append(op_stack.pop())
            op_stack.append(token)
        else:
            raise ValueError(f"未知 token: {token}")

    # 弹出剩余运算符
    while op_stack:
        if op_stack[-1] == '(':
            raise ValueError("括号不匹配")
        output.append(op_stack.pop())

    return output


def tokenize(expression):
    """
    将表达式字符串分词
    "3 + 4 * (2 - 1)" → ["3", "+", "4", "*", "(", "2", "-", "1", ")"]
    """
    # 去除所有空格
    expr = expression.replace(' ', '')
    # 用正则分词：匹配数字（包括小数）或单个字符
    pattern = r'\d+\.?\d*|.'
    tokens = re.findall(pattern, expr)

    # 处理一元负号：如果 '-' 是第一个 token 或前一个是 '('
    result = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t == '-' and (i == 0 or tokens[i-1] == '('):
            # 一元负号：将下一个数字取负
            if i + 1 < len(tokens):
                result.append('-' + tokens[i+1])
                i += 2
                continue
        result.append(t)
        i += 1

    return result


# 测试中缀转后缀
test_expressions = [
    ("3 + 4", ["3", "4", "+"]),
    ("3 + 4 * 2", ["3", "4", "2", "*", "+"]),
    ("(3 + 4) * 2", ["3", "4", "+", "2", "*"]),
    ("3 + 4 * (2 - 1)",
     ["3", "4", "2", "1", "-", "*", "+"]),
    ("10 / 3", ["10", "3", "/"]),
]

print("中缀转后缀测试:")
for expr, expected in test_expressions:
    try:
        rpn = infix_to_rpn(expr)
        status = "✅" if rpn == expected else "❌"
        print(f"  {status} {expr:25s} → {' '.join(rpn):30s}")
        if rpn != expected:
            print(f"       期望: {' '.join(expected):30s}")
    except Exception as e:
        print(f"  ❌ {expr:25s} → 错误: {e}")


# ====================================================================
# 第三部分：完整计算器
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  完整计算器（中缀 → 后缀 → 求值）")
print("=" * 60)

class Calculator:
    """支持 +, -, *, /, ^, () 的表达式计算器"""

    def calc(self, expression: str) -> float:
        """计算表达式的值"""
        rpn = infix_to_rpn(expression)
        result = eval_rpn(rpn)
        return result

    def calc_with_steps(self, expression: str):
        """计算并显示中间步骤"""
        print(f"\n📝 计算: {expression}")

        # 分词
        tokens = tokenize(expression)
        print(f"  分词: {tokens}")

        # 转后缀
        rpn = infix_to_rpn(expression)
        print(f"  后缀: {' '.join(rpn)}")

        # 逐步求值
        stack = []
        operators = {'+', '-', '*', '/', '^'}
        print(f"  求值过程:")
        for token in rpn:
            if token not in operators:
                stack.append(float(token))
            else:
                b = stack.pop()
                a = stack.pop()
                step = f"{a:.2f} {token} {b:.2f}"
                if token == '+':   val = a + b
                elif token == '-': val = a - b
                elif token == '*': val = a * b
                elif token == '/': val = a / b if b != 0 else float('inf')
                elif token == '^': val = a ** b
                stack.append(val)
                print(f"    {step:15s} = {val:.2f}, 栈: {[f'{x:.2f}' for x in stack]}")

        result = stack[0]
        print(f"  ▶ 结果: {result:.10f}")
        return result


# 测试计算器
calc = Calculator()
test_cases = [
    ("3 + 4", 7),
    ("3 + 4 * 2", 11),
    ("(3 + 4) * 2", 14),
    ("3 + 4 * (2 - 1)", 7),
    ("10 / 3", 10 / 3),
    ("5 + ((1 + 2) * 4) - 3", 14),
    ("(2 + 3) * (4 - 1)", 15),
]

print("\n计算器测试:")
all_passed = True
for expr, expected in test_cases:
    try:
        result = calc.calc(expr)
        passed = abs(result - expected) < 1e-9
        status = "✅" if passed else "❌"
        print(f"  {status} {expr:30s} = {result:15.10f} (期望 {expected:15.10f})")
        if not passed:
            all_passed = False
    except Exception as e:
        print(f"  ❌ {expr:30s} → 错误: {e}")
        all_passed = False

print(f"\n{'✅ 全部测试通过!' if all_passed else '❌ 存在失败测试'}")


# ====================================================================
# 第四部分：交互式计算器
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  交互式计算器（逐步展示）")
print("=" * 60)

# 运行几个示例的逐步推演
calc.calc_with_steps("(3 + 4) * 2")
calc.calc_with_steps("3 + 4 * (2 - 1)")
calc.calc_with_steps("5 + ((1 + 2) * 4) - 3")


# ====================================================================
# 第五部分：附加 — 中缀转后缀图解
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  中缀转后缀工作原理图解")
print("=" * 60)

def visualize_infix_to_rpn(expression):
    """可视化展示调度场算法"""
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '^': 3}
    operators = set(precedence.keys())
    tokens = tokenize(expression)

    print(f"\n表达式: {expression}")
    print(f"{'Token':8s} {'操作':20s} {'输出':20s} {'运算符栈':20s}")
    print("-" * 68)

    output = []
    op_stack = []

    for token in tokens:
        if token.isdigit() or '.' in token:
            output.append(token)
            print(f"{token:8s} {'入队':20s} {' '.join(output):20s} {' '.join(op_stack[::-1]):20s}")
        elif token == '(':
            op_stack.append(token)
            print(f"{token:8s} {'入栈':20s} {' '.join(output):20s} {' '.join(op_stack[::-1]):20s}")
        elif token == ')':
            while op_stack and op_stack[-1] != '(':
                output.append(op_stack.pop())
            op_stack.pop()  # 移除 '('
            print(f"{token:8s} {'弹栈直到 (':20s} {' '.join(output):20s} {' '.join(op_stack[::-1]):20s}")
        elif token in operators:
            while (op_stack and op_stack[-1] != '(' and
                   precedence.get(op_stack[-1], 0) >= precedence[token]):
                output.append(op_stack.pop())
            op_stack.append(token)
            print(f"{token:8s} {'处理优先级后入栈':20s} {' '.join(output):20s} {' '.join(op_stack[::-1]):20s}")

    while op_stack:
        output.append(op_stack.pop())

    print(f"{'':8s} {'清空栈':20s} {' '.join(output):20s} {'':20s}")
    print(f"\n结果: {' '.join(output)}")

visualize_infix_to_rpn("3 + 4 * (2 - 1)")


# ====================================================================
# 总结
# ====================================================================
print("\n" + "=" * 60)
print("📌  表达式求值总结")
print("=" * 60)
print("""
核心要点:
  • 中缀表达式是人类易读的，但不便于计算机直接求值
  • 后缀表达式（RPN）消除了括号，可以用栈轻松求值
  • 调度场算法用两个栈实现中缀→后缀的转换
  • 运算符优先级和结合性决定转换规则

复杂度分析:
  • 时间复杂度: O(n) — 每个 token 只处理一次
  • 空间复杂度: O(n) — 需要栈存储运算符

扩展方向:
  • 支持函数: sin, cos, sqrt, log
  • 支持变量: 如 x + 2
  • 支持负数: 一元负号处理
  • 浮点数精度优化
""")

print("✅ 表达式求值实战演示完毕！")
