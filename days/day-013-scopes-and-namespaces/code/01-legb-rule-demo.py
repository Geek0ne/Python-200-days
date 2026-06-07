"""
Day 013 - 01: LEGB 规则实战演示
===============================
展示 Python 的变量查找规则和各作用域层级的交互。
可直接运行：python3 01-legb-rule-demo.py
"""

import sys


# ============================================================
# 1. 最基本的 LEGB 查找
# ============================================================
print("=" * 60)
print("1. LEGB 基本查找")
print("=" * 60)

# B：内置命名空间（Built-in）
# print, len, range 等都在内置命名空间中，不需要定义

# G：全局命名空间（Global）
global_var = "🌍 全局变量"
builtin_demo = "🔧 演示内置变量遮蔽"  # 注意：这会影响下面查找 builtins 中的某些同名对象


def outer_function():
    """演示 LEGB 嵌套查找"""
    # E：封闭作用域（Enclosing）
    enclosing_var = "📦 封闭变量（outer 函数的局部变量）"

    def inner_function():
        # L：局部作用域（Local）
        local_var = "📍 局部变量（inner 函数的局部变量）"

        # LEGB 查找顺序演示
        print(f"[L] 局部变量:     {local_var}")       # Local
        print(f"[E] 封闭变量:     {enclosing_var}")    # Enclosing
        print(f"[G] 全局变量:     {global_var}")       # Global
        print(f"[B] 内置函数 len: {len([1, 2, 3])}")   # Built-in

    inner_function()


outer_function()


# ============================================================
# 2. 遮蔽现象（Shadowing）
# ============================================================
print("\n" + "=" * 60)
print("2. 变量遮蔽（Shadowing）演示")
print("=" * 60)

value = "🌓 初始全局值"


def demonstrate_shadowing():
    """演示变量遮蔽：内层变量覆盖外层同名变量"""
    value = "🌑 遮蔽值（局部变量）"  # 创建新的局部变量，和全局变量同名
    print(f"函数内部: {value}")


demonstrate_shadowing()
print(f"函数外部: {value}")  # 全局变量不受影响

# 嵌套遮蔽
x = "全局 X"


def level1():
    x = "第一层 X"

    def level2():
        x = "第二层 X"

        def level3():
            x = "第三层 X"
            print(f"最深嵌套层: {x}")

        level3()
        print(f"第二层:     {x}")

    level2()
    print(f"第一层:     {x}")


level1()
print(f"全局层:     {x}")


# ============================================================
# 3. 读取 vs 赋值（重要区别！）
# ============================================================
print("\n" + "=" * 60)
print("3. 读取 vs 赋值的不同行为")
print("=" * 60)

items = [10, 20, 30]


def modify_via_method():
    """通过方法修改：先读取（LEGB 查找）再修改"""
    items.append(40)  # ✅ LEGB 找到全局 items，然后 append
    print(f"方法修改后: {items}")


def modify_via_reassign():
    """通过赋值修改：在局部创建新变量！"""
    items = [100, 200, 300]  # ⚠️ 这不是修改全局 items，而是创建局部变量
    print(f"赋值修改内: {items}")


modify_via_method()
modify_via_reassign()
print(f"全局 items: {items}")  # [10, 20, 30, 40] — 方法修改生效了，赋值没有


# ============================================================
# 4. 错误案例：UnboundLocalError
# ============================================================
print("\n" + "=" * 60)
print("4. UnboundLocalError 演示")
print("=" * 60)


def will_cause_error():
    """演示 UnboundLocalError"""
    # 请取消下面两行的注释来观察错误
    # print(value)   # 这行没问题，因为此时 value 还是全局的
    # value = "局部"  # ⚡ 这一行让 Python 把 value 标记为局部变量！
    pass


def safe_way():
    """安全地使用局部变量"""
    # 要么：先赋值再使用
    value = "全新局部"
    print(f"安全的局部使用: {value}")


safe_way()

# 不能在局部读写混用同名的全局→局部变量
# 下面演示这个问题
message = "你好"


def problematic():
    # Python 在编译时发现 message 在函数中有赋值操作
    # 所以把 message 标记为"局部变量"
    # print(message)  # ← 如果取消注释，这里会报 UnboundLocalError
    message = "再见"   # ← 这行导致上面的 print 出错


# ============================================================
# 5. __closure__ 和 __code__ 检查函数作用域
# ============================================================
print("\n" + "=" * 60)
print("5. 检查函数的作用域属性")
print("=" * 60)


def example_func():
    """一个示例函数"""
    local_x = 1
    local_y = 2
    return local_x + local_y


# 函数对象的 __code__ 属性
print(f"局部变量名:   {example_func.__code__.co_varnames}")
print(f"自由变量名:   {example_func.__code__.co_free_vars}")
print(f"是否是生成器: {example_func.__code__.co_flags & 0x0020 != 0}")


# 闭包示例
def make_closure():
    captured = [1, 2, 3]  # 这个会被闭包捕获

    def inner():
        return sum(captured)

    print(f"inner 的自由变量: {inner.__code__.co_free_vars}")
    print(f"inner 的闭包内容: {inner.__closure__}")
    return inner


closure_func = make_closure()
print(f"调用闭包: {closure_func()}")


# ============================================================
# 6. dir() 和 locals()/globals() 查看作用域
# ============================================================
print("\n" + "=" * 60)
print("6. 使用 locals() / globals() 查看作用域")
print("=" * 60)

# 查看全局作用域
print(f"全局作用域中的变量（部分）：")
global_keys = list(globals().keys())
print(f"  共有 {len(global_keys)} 个符号")
print(f"  包含: {[k for k in global_keys if 'var' in k or 'func' in k]}")


def scope_inspector():
    """检查局部作用域"""
    a = 10
    b = "hello"
    c = [1, 2, 3]

    print(f"\n局部变量: {list(locals().keys())}")
    print(f"局部 a: {locals()['a']}")

    # 动态创建局部变量（不推荐，仅演示）
    locals()["d"] = "动态创建的变量"
    # ⚠️ 注意：通过 locals() 字典不总是能成功创建变量
    # 在函数内，编译器已经决定了哪些是局部变量
    # print(d)  # 可能会报 NameError！


scope_inspector()

# 使用 vars() 查看当前作用域
print(f"\nvars() 当前作用域部分键: {[k for k in vars().keys() if not k.startswith('__')][:5]}")
