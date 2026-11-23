"""
Day 095 - 函数式编程深入
02-currying-immutability.py: 柯里化与不可变数据结构

知识点:
  - 柯里化实现与应用
  - partial vs currying 对比
  - 不可变数据结构（tuple, frozenset, namedtuple）
  - 线程安全与不可变性
"""

import inspect
import threading
from collections import namedtuple
from typing import NamedTuple, Tuple, FrozenSet
from functools import partial

# ============================================================
# 第一部分：柯里化实现
# ============================================================

def curry_manual(func):
    """手动实现柯里化"""
    sig = inspect.signature(func)
    num_params = len(sig.parameters)
    
    def curried(*args, **kwargs):
        if len(args) + len(kwargs) >= num_params:
            return func(*args, **kwargs)
        else:
            def wrapper(*more_args, **more_kwargs):
                all_args = args + more_args
                all_kwargs = {**kwargs, **more_kwargs}
                return curried(*all_args, **all_kwargs)
            return wrapper
    
    return curried


def auto_curry(func):
    """自动柯里化装饰器（更智能的版本）"""
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    
    def curried(*args, **kwargs):
        # 构建已知参数映射
        bound = {}
        for i, arg in enumerate(args):
            if i < len(params):
                bound[params[i]] = arg
        bound.update(kwargs)
        
        # 检查是否所有参数都已提供
        missing = [p for p in params if p not in bound]
        if not missing:
            return func(**bound)
        
        # 返回新函数继续接收参数
        def wrapper(*more_args, **more_kwargs):
            new_bound = dict(bound)
            offset = len(args)
            for i, arg in enumerate(more_args):
                if offset + i < len(params):
                    new_bound[params[offset + i]] = arg
            new_bound.update(more_kwargs)
            return curried(**new_bound)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    curried.__name__ = func.__name__
    curried.__doc__ = func.__doc__
    return curried


def currying_demo():
    """演示柯里化"""
    print("=" * 50)
    print("柯里化实现与应用")
    print("=" * 50)
    
    # 1. 手动柯里化
    @curry_manual
    def add(a, b, c):
        return a + b + c
    
    print(f"add(1)(2)(3) = {add(1)(2)(3)}")
    print(f"add(1, 2)(3) = {add(1, 2)(3)}")
    print(f"add(1, 2, 3) = {add(1, 2, 3)}")
    
    # 2. 创建专用函数
    @curry_manual
    def multiply(a, b):
        return a * b
    
    double = multiply(2)
    triple = multiply(3)
    
    print(f"\ndouble(5) = {double(5)}")
    print(f"triple(5) = {triple(5)}")
    
    # 3. 实际应用：日志函数
    @curry_manual
    def log(level, module, message):
        return f"[{level}] [{module}] {message}"
    
    error = log("ERROR")
    db_error = error("Database")
    
    print(f"\n{db_error('连接超时')}")
    print(f"{db_error('查询失败')}")
    print(f"{error('Auth')('登录失败')}")
    
    # 4. 与 partial 对比
    print("\n--- partial vs currying ---")
    
    def greet(greeting, name, punctuation):
        return f"{greeting}, {name}{punctuation}"
    
    # partial 方式
    hello = partial(greet, "Hello")
    hello_alice = partial(greet, "Hello", "Alice")
    
    print(f"partial: {hello('Alice', '!')}")
    print(f"partial: {hello_alice('!')}")
    
    # currying 方式
    @curry_manual
    def greet_curried(greeting, name, punctuation):
        return f"{greeting}, {name}{punctuation}"
    
    hello_curried = greet_curried("Hello")
    
    print(f"currying: {hello_curried('Alice')('!')}")
    print(f"currying: {hello_curried('Bob', '.')}")
    
    # 5. 管道构建
    @curry_manual
    def pipe_step(func, data):
        return func(data)
    
    @curry_manual
    def pipe(*funcs):
        from functools import reduce
        return reduce(lambda acc, f: f(acc), funcs)
    
    transform = pipe(
        str.strip,
        str.lower,
        lambda s: s.replace(" ", "_"),
    )
    
    print(f"\n管道: '{transform('  Hello World  ')}'")
    
    # 6. 条件过滤
    @curry_manual
    def filter_by(key, value, items):
        return [item for item in items if item.get(key) == value]
    
    users = [
        {"name": "Alice", "role": "admin"},
        {"name": "Bob", "role": "user"},
        {"name": "Charlie", "role": "admin"},
    ]
    
    admins = filter_by("role", "admin")(users)
    print(f"\n管理员: {[u['name'] for u in admins]}")


# ============================================================
# 第二部分：不可变数据结构
# ============================================================

def immutability_demo():
    """演示不可变数据结构"""
    print("\n" + "=" * 50)
    print("不可变数据结构")
    print("=" * 50)
    
    # 1. tuple 基础
    print("--- tuple 基础 ---")
    point = (10, 20)
    print(f"点: {point}")
    print(f"x={point[0]}, y={point[1]}")
    
    # 解包
    x, y = point
    print(f"解包: x={x}, y={y}")
    
    # 嵌套
    matrix = ((1, 2), (3, 4), (5, 6))
    print(f"矩阵: {matrix}")
    print(f"访问: matrix[1][0] = {matrix[1][0]}")
    
    # 2. namedtuple
    print("\n--- namedtuple ---")
    
    # 基本用法
    Point = namedtuple('Point', ['x', 'y'])
    p = Point(10, 20)
    print(f"点: {p}")
    print(f"通过名称: x={p.x}, y={p.y}")
    print(f"通过索引: x={p[0]}, y={p[1]}")
    
    # 替换字段（返回新对象）
    p2 = p._replace(x=50)
    print(f"替换后: {p2}")
    print(f"原对象: {p} (不变)")
    
    # 转换为字典
    d = p._asdict()
    print(f"字典: {d}")
    
    # 带默认值
    Color = namedtuple('Color', ['r', 'g', 'b', 'alpha'], defaults=[255])
    red = Color(255, 0, 0)
    print(f"颜色: {red}")
    
    # 3. Typed NamedTuple (Python 3.6+)
    print("\n--- Typed NamedTuple ---")
    
    class Point3D(NamedTuple):
        x: float
        y: float
        z: float
        label: str = "origin"
    
    p3d = Point3D(1.0, 2.0, 3.0)
    print(f"3D点: {p3d}")
    print(f"类型注解: {Point3D.__annotations__}")
    
    # 4. frozenset
    print("\n--- frozenset ---")
    
    fs1 = frozenset([1, 2, 3, 4])
    fs2 = frozenset([3, 4, 5, 6])
    
    print(f"fs1: {fs1}")
    print(f"fs2: {fs2}")
    print(f"交集: {fs1 & fs2}")
    print(f"并集: {fs1 | fs2}")
    print(f"差集: {fs1 - fs2}")
    print(f"对称差: {fs1 ^ fs2}")
    
    # 可以作为字典键
    cache = {}
    cache[frozenset([1, 2])] = "cached"
    print(f"缓存: {cache[frozenset([1, 2])]}")
    
    # 5. 不可变字典操作
    print("\n--- 不可变字典操作 ---")
    
    original = {"a": 1, "b": 2, "c": 3}
    
    # 添加（返回新字典）
    added = {**original, "d": 4}
    print(f"添加: {added}")
    print(f"原字典: {original} (不变)")
    
    # 更新
    updated = {**original, "b": 99}
    print(f"更新: {updated}")
    
    # 删除
    removed = {k: v for k, v in original.items() if k != "a"}
    print(f"删除: {removed}")
    
    # 6. 不可变列表操作
    print("\n--- 不可变列表操作 ---")
    
    original_list = [1, 2, 3, 4, 5]
    
    # 添加
    appended = (*original_list, 6)
    print(f"添加: {appended}")
    
    # 删除
    removed = original_list[:2] + original_list[3:]
    print(f"删除索引2: {removed}")
    
    # 替换
    replaced = original_list[:2] + [99] + original_list[3:]
    print(f"替换索引2: {replaced}")


# ============================================================
# 第三部分：不可变性与线程安全
# ============================================================

def thread_safety_demo():
    """演示不可变数据的线程安全性"""
    print("\n" + "=" * 50)
    print("不可变性与线程安全")
    print("=" * 50)
    
    # 1. 可变数据的竞态条件
    print("--- 可变数据的竞态条件 ---")
    
    counter = {"value": 0}
    lock = threading.Lock()
    
    def increment_safe(n):
        for _ in range(n):
            with lock:
                counter["value"] += 1
    
    # 并发修改
    threads = [threading.Thread(target=increment_safe, args=(10000,)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    print(f"加锁后: {counter['value']} (应该是 50000)")
    
    # 2. 不可变数据无需加锁
    print("\n--- 不可变数据无需加锁 ---")
    
    # 不可变数据可以安全地在线程间共享
    shared_config = ({"host": "localhost", "port": 8080},)  # 元组包装
    
    def read_config():
        # 读取不需要锁
        config = shared_config[0]
        return f"Config: {config}"
    
    # 多个线程可以安全读取
    threads = [threading.Thread(target=read_config) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    print("多线程读取不可变数据: ✅ 安全")
    
    # 3. 函数式更新模式
    print("\n--- 函数式更新模式 ---")
    
    def immutable_update(data, **updates):
        """不可变更新：返回新字典"""
        return {**data, **updates}
    
    state = {"count": 0, "items": [], "loading": False}
    
    # 模拟状态更新
    state = immutable_update(state, count=1)
    state = immutable_update(state, loading=True)
    state = immutable_update(state, items=["item1"], loading=False)
    
    print(f"状态更新: {state}")
    print("每次更新都返回新对象，原对象不变")


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    currying_demo()
    immutability_demo()
    thread_safety_demo()
    
    print("\n" + "=" * 50)
    print("✅ 柯里化与不可变性演示完成")
    print("=" * 50)
