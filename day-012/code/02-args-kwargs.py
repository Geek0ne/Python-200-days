#!/usr/bin/env python3
"""
02-args-kwargs.py — *args 和 **kwargs 详解

演示 Python 可变参数的打包与解包机制，
以及在实际开发中的各种使用模式。

运行: python3 02-args-kwargs.py
"""

print("=" * 60)
print("1️⃣  位置参数 vs 关键字参数基础")
print("=" * 60)


def greet(name, greeting, punctuation):
    return f"{greeting}, {name}{punctuation}"


print("\n--- 位置参数传递 ---")
print(greet("张三", "你好", "!"))            # 按顺序

print("\n--- 关键字参数传递 ---")
print(greet(name="李四", greeting="Hello", punctuation="!!"))

print("\n--- 混合传递（位置在前，关键字在后） ---")
print(greet("王五", greeting="Hi", punctuation="?"))  # ✅


# ============================================================
# 2. *args — 可变位置参数
# ============================================================
print("\n" + "=" * 60)
print("2️⃣  *args — 可变位置参数（打包/解包机制）")
print("=" * 60)


def sum_all(*args):
    """
    接收任意多个位置参数，*args 将所有参数打包成元组

    原理: *args 在函数定义中表示「收集剩余的位置参数到 args 元组」
    """
    print(f"  args 类型: {type(args).__name__}")
    print(f"  args 内容: {args}")
    total = 0
    for num in args:
        total += num
    return total


print("\n--- sum_all 演示 ---")
print(f"  sum_all(1, 2) = {sum_all(1, 2)}")
print(f"  sum_all(1, 2, 3, 4, 5) = {sum_all(1, 2, 3, 4, 5)}")
print(f"  sum_all() = {sum_all()}")  # 空元组


def log_message(level, *messages):
    """
    固定的 level 参数 + 可变数量的消息

    *args 只在「多余」的位置参数上起作用
    """
    print(f"[{level.upper()}]", end=" ")
    for msg in messages:
        print(msg, end=" | ")
    print()


print("\n--- 固定参数 + *args ---")
log_message("info", "系统启动成功")
log_message("warn", "磁盘空间不足", "建议清理缓存", "当前使用率 85%")


# ============================================================
# 3. **kwargs — 可变关键字参数
# ============================================================
print("\n" + "=" * 60)
print("3️⃣  **kwargs — 可变关键字参数（打包/解包机制）")
print("=" * 60)


def create_profile(name, **kwargs):
    """
    接收任意多个关键字参数，**kwargs 将所有参数打包成字典

    原理: **kwargs 在函数定义中表示「收集剩余的关键字参数到 kwargs 字典」
    """
    print(f"  kwargs 类型: {type(kwargs).__name__}")
    print(f"  kwargs 内容: {kwargs}")

    profile = {"name": name}
    profile.update(kwargs)
    return profile


print("\n--- 创建用户档案 ---")
p1 = create_profile("张三", age=25, city="北京", job="工程师")
print(f"  {p1}")

p2 = create_profile("李四", age=30, city="上海", job="设计师", hobby="摄影")
print(f"  {p2}")


def configure(**settings):
    """
    通用配置函数 — 默认值 + 用户覆盖
    """
    defaults = {
        "host": "localhost",
        "port": 8080,
        "debug": False,
        "timeout": 30,
    }
    defaults.update(settings)  # 用户配置覆盖默认
    return defaults


print("\n--- 配置管理 ---")
print(f"  默认配置: {configure()}")
print(f"  自定义: {configure(host='example.com', port=443, debug=True)}")


# ============================================================
# 4. 解包（Unpacking）— 调用时使用 * 和 **
# ============================================================
print("\n" + "=" * 60)
print("4️⃣  解包操作符（调用时 * 和 **）")
print("=" * 60)


def introduce(name, age, city):
    print(f"  我叫{name}, {age}岁, 来自{city}")


print("\n--- 列表/元组解包 * ---")
person_list = ["张三", 25, "北京"]
introduce(*person_list)  # 相当于 introduce("张三", 25, "北京")

person_tuple = ("李四", 30, "上海")
introduce(*person_tuple)

print("\n--- 字典解包 ** ---")
person_dict = {"name": "王五", "age": 28, "city": "广州"}
introduce(**person_dict)  # 相当于 introduce(name="王五", age=28, city="广州")

print("\n--- 实用技巧：合并字典 ---")
dict1 = {"a": 1, "b": 2}
dict2 = {"c": 3, "d": 4}
merged = {**dict1, **dict2}
print(f"  {dict1} + {dict2} = {merged}")


# ============================================================
# 5. 同时使用 *args 和 **kwargs
# ============================================================
print("\n" + "=" * 60)
print("5️⃣  同时使用 *args 和 **kwargs")
print("=" * 60)


def flexible_function(a, b, *args, c=10, **kwargs):
    """
    完整参数顺序（从左到右）:
    1. a, b       — 普通位置参数
    2. *args      — 可变位置参数
    3. c=10       — 默认关键字参数（仅限关键字形式）
    4. **kwargs   — 可变关键字参数
    """
    print(f"  a = {a}")
    print(f"  b = {b}")
    print(f"  *args = {args}")
    print(f"  c = {c}")
    print(f"  **kwargs = {kwargs}")


print("\n--- 完整参数示例 ---")
flexible_function(1, 2, 3, 4, 5, c=100, x="hello", y="world")
"""
输出:
  a = 1
  b = 2
  *args = (3, 4, 5)
  c = 100
  **kwargs = {'x': 'hello', 'y': 'world'}
"""


# ============================================================
# 6. 常见使用模式：参数转发（装饰器基础）
# ============================================================
print("\n" + "=" * 60)
print("6️⃣  参数转发模式（装饰器的基础）")
print("=" * 60)


def logger(func):
    """简单的日志装饰器：原封不动转发参数"""
    def wrapper(*args, **kwargs):
        print(f"  ▶ 调用 {func.__name__}{args} {kwargs}")
        result = func(*args, **kwargs)
        print(f"  ◀ 返回 {result!r}")
        return result
    return wrapper


@logger
def add(x, y):
    return x + y


@logger
def greet_user(name, greeting="你好"):
    return f"{greeting}, {name}!"


print("\n--- 带日志的函数调用 ---")
add(3, 5)
greet_user("张三")
greet_user("李四", greeting="Hello")


# ============================================================
# 7. 鸭子类型：统一接口适配不同数据源
# ============================================================
print("\n" + "=" * 60)
print("7️⃣  统一接口适配不同数据源")
print("=" * 60)


def fetch_data(source_type, **params):
    """
    同一接口，不同数据源

    **params 让不同类型的数据源传入各自需要的参数
    """
    if source_type == "api":
        url = params.get("url", "unknown")
        timeout = params.get("timeout", 30)
        return f"[API] GET {url} (timeout={timeout}s)"

    elif source_type == "database":
        table = params.get("table", "unknown")
        where = params.get("where", "")
        limit = params.get("limit", 100)
        return f"[DB] SELECT * FROM {table} WHERE {where} LIMIT {limit}"

    elif source_type == "file":
        path = params.get("path", "unknown")
        encoding = params.get("encoding", "utf-8")
        return f"[FILE] 正在读取 {path} (编码: {encoding})"

    else:
        raise ValueError(f"未知数据源: {source_type}")


print("\n--- 同一函数处理不同数据源 ---")
print(f"  {fetch_data('api', url='https://api.example.com/users', timeout=10)}")
print(f"  {fetch_data('database', table='users', where='age > 18', limit=50)}")
print(f"  {fetch_data('file', path='/data/input.csv', encoding='gbk')}")


# ============================================================
# 8. 仅限关键字参数（Keyword-only Arguments）
# ============================================================
print("\n" + "=" * 60)
print("8️⃣  仅限关键字参数（Python 3 特性）")
print("=" * 60)


def create_user(name, age, *, city, phone):
    """
    * 之后的参数是「仅限关键字参数」

    调用时必须用 keyword=value 形式，不能使用位置参数
    """
    return f"{name}({age}岁) — {city}, 电话: {phone}"


print("\n--- 仅限关键字参数 ---")
print(f"  {create_user('张三', 25, city='北京', phone='13800138000')}")

# 下面这行会报错，取消注释试试：
# print(create_user("张三", 25, "北京", "13800138000"))
# TypeError: create_user() takes 2 positional arguments but 4 were given


def send_message(recipient, subject, *, urgency="normal", attachments=None):
    """
    第一个参数是位置参数，后面是仅限关键字参数
    """
    msg = f"收件人: {recipient}\n主题: {subject}"
    msg += f"\n紧急程度: {urgency}"

    if attachments:
        attach_str = ", ".join(attachments) if isinstance(attachments, list) else attachments
        msg += f"\n附件: {attach_str}"

    return msg


print("\n--- 发送消息 ---")
print(f"  \n{send_message('alice@example.com', '会议通知', urgency='high', attachments=['议程.pdf'])}")


# ============================================================
# 9. 综合练习：通用格式化输出函数
# ============================================================
print("\n" + "=" * 60)
print("9️⃣  综合练习：通用格式化输出")
print("=" * 60)


def format_output(title, *items, sep="-", numbered=False, **styles):
    """
    通用格式化输出函数

    Args:
        title: 标题（位置参数）
        *items: 要输出的项目列表（可变位置参数）
        sep: 分隔符（关键字参数）
        numbered: 是否编号（关键字参数）
        **styles: 样式设置（对齐方式、填充字符等）
    """
    width = styles.get("width", 40)
    align = styles.get("align", "center")

    print("=" * width)
    if align == "center":
        print(f"{title:^{width}}")
    elif align == "left":
        print(f"{title:<{width}}")
    elif align == "right":
        print(f"{title:>{width}}")
    print("=" * width)

    for i, item in enumerate(items, 1):
        if numbered:
            print(f"  {i}. {item}")
        else:
            print(f"  {item}")

    print("-" * width)
    print(f"  共 {len(items)} 项")
    print()


print("--- 基本用法 ---")
format_output("购物清单", "苹果", "香蕉", "牛奶", "面包")

print("--- 带编号 ---")
format_output("TODO", "写报告", "开会", "健身", "读书", numbered=True, width=30)

print("--- 自定义样式 ---")
format_output("行程安排", "09:00 起床", "10:00 健身", "14:00 阅读",
              sep="|", numbered=True, width=50, align="left")


# ============================================================
# 10. 总结
# ============================================================
print("\n" + "=" * 60)
print("📋  *args/**kwargs 核心理解")
print("=" * 60)

summary = """
┌──────────────────────────────────────────────────────────────┐
│  *args 与 **kwargs 的本质                                      │
│                                                              │
│  定义时（打包/Packing）:                                        │
│    def f(*args):     → args 接收所有多余位置参数 → 元组          │
│    def f(**kwargs):  → kwargs 接收所有关键字参数  → 字典          │
│                                                              │
│  调用时（解包/Unpacking）:                                      │
│    f(*lst)          → 把列表/元组展开为位置参数                  │
│    f(**dct)         → 把字典展开为关键字参数                     │
│                                                              │
│  参数顺序（从左到右）:                                           │
│    普通位置参数 → *args(打包) → 默认参数 → 仅限关键字参数 → **kwargs│
│    a, b, c       *args      d=10       *, e, f      **kwargs  │
│                                                              │
│  注意:                                                        │
│    *args 必须是 tuple（不可变），但你可以转换成 list               │
│    **kwargs 中的键必须是字符串                                   │
│    参数名 args/kwargs 只是约定，*pos 和 **named 也一样有效       │
└──────────────────────────────────────────────────────────────┘
"""
print(summary)
