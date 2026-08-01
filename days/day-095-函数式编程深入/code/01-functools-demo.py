"""
Day 095 - 函数式编程深入
01-functools-demo.py: functools 模块详解

知识点:
  - reduce 归约操作
  - partial 偏函数
  - lru_cache 函数缓存
  - singledispatch 单分派泛型
  - total_ordering 自动比较
"""

from functools import reduce, partial, lru_cache, singledispatch, total_ordering
import time
import inspect

# ============================================================
# 第一部分：reduce 归约操作
# ============================================================

def reduce_demo():
    """演示 reduce 的各种用法"""
    print("=" * 50)
    print("reduce 归约操作")
    print("=" * 50)
    
    numbers = [1, 2, 3, 4, 5]
    
    # 1. 基本求和
    total = reduce(lambda acc, x: acc + x, numbers)
    print(f"求和: {total}")
    
    # 2. 带初始值
    total_with_init = reduce(lambda acc, x: acc + x, numbers, 100)
    print(f"带初始值求和: {total_with_init}")
    
    # 3. 求最大值
    max_val = reduce(lambda a, b: a if a > b else b, numbers)
    print(f"最大值: {max_val}")
    
    # 4. 扁平化嵌套列表
    nested = [[1, 2], [3, 4], [5, 6]]
    flat = reduce(lambda acc, x: acc + x, nested, [])
    print(f"扁平化: {flat}")
    
    # 5. 字符串连接
    words = ["Hello", " ", "World", "!"]
    sentence = reduce(lambda acc, w: acc + w, words)
    print(f"连接: {sentence}")
    
    # 6. 计算阶乘
    factorial = reduce(lambda acc, x: acc * x, range(1, 6))
    print(f"5! = {factorial}")
    
    # 7. 嵌套字典合并
    dicts = [
        {"a": 1, "b": 2},
        {"b": 3, "c": 4},
        {"d": 5}
    ]
    merged = reduce(lambda acc, d: {**acc, **d}, dicts)
    print(f"合并字典: {merged}")
    
    # 8. 管道执行
    def pipe(*funcs):
        return reduce(lambda acc, f: f(acc), funcs)
    
    result = pipe(
        5,
        lambda x: x * 2,
        lambda x: x + 10,
        lambda x: x ** 2
    )
    print(f"管道: ((((5 * 2) + 10) ** 2)) = {result}")


# ============================================================
# 第二部分：partial 偏函数
# ============================================================

def partial_demo():
    """演示 partial 的用法"""
    print("\n" + "=" * 50)
    print("partial 偏函数")
    print("=" * 50)
    
    # 1. 基本用法
    def power(base, exponent):
        return base ** exponent
    
    square = partial(power, exponent=2)
    cube = partial(power, exponent=3)
    
    print(f"平方(5): {square(5)}")
    print(f"立方(5): {cube(5)}")
    
    # 2. 实际应用：API 请求
    def api_request(url, method="GET", timeout=30, headers=None):
        return {"url": url, "method": method, "timeout": timeout}
    
    get = partial(api_request, method="GET", timeout=10)
    post = partial(api_request, method="POST", timeout=30)
    
    print(f"GET 请求: {get('https://api.example.com/users')}")
    print(f"POST 请求: {post('https://api.example.com/users')}")
    
    # 3. 排序偏函数
    from operator import itemgetter
    
    users = [
        {"name": "Alice", "age": 30, "score": 85},
        {"name": "Bob", "age": 25, "score": 92},
        {"name": "Charlie", "age": 35, "score": 78},
    ]
    
    sort_by_age = partial(sorted, key=itemgetter("age"))
    sort_by_score = partial(sorted, key=itemgetter("score"), reverse=True)
    
    print(f"按年龄排序: {[u['name'] for u in sort_by_age(users)]}")
    print(f"按分数排序: {[u['name'] for u in sort_by_score(users)]}")
    
    # 4. 带默认参数的日志
    def log(level, module, message):
        print(f"  [{level}] [{module}] {message}")
    
    error = partial(log, "ERROR")
    info = partial(log, "INFO")
    db_error = partial(error, "Database")
    
    db_error("连接超时")
    info("请求处理完成")
    db_error("查询失败")


# ============================================================
# 第三部分：lru_cache 函数缓存
# ============================================================

def lru_cache_demo():
    """演示 lru_cache 的用法"""
    print("\n" + "=" * 50)
    print("lru_cache 函数缓存")
    print("=" * 50)
    
    # 1. 斐波那契数列
    @lru_cache(maxsize=128)
    def fibonacci(n):
        if n < 2:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    
    # 性能测试
    start = time.time()
    result = fibonacci(100)
    cached_time = time.time() - start
    
    print(f"fib(100) = {result}")
    print(f"有缓存耗时: {cached_time:.6f}s")
    print(f"缓存信息: {fibonacci.cache_info()}")
    
    # 清除缓存
    fibonacci.cache_clear()
    
    # 2. 实际应用：数据库查询缓存
    @lru_cache(maxsize=256)
    def get_user(user_id):
        """模拟数据库查询"""
        time.sleep(0.01)  # 模拟 I/O 延迟
        return {"id": user_id, "name": f"User_{user_id}"}
    
    # 第一次查询（慢）
    start = time.time()
    user1 = get_user(1)
    first_time = time.time() - start
    
    # 第二次查询（快，命中缓存）
    start = time.time()
    user1_cached = get_user(1)
    cached_time = time.time() - start
    
    print(f"\n首次查询: {first_time:.4f}s")
    print(f"缓存查询: {cached_time:.6f}s")
    print(f"加速比: {first_time/cached_time:.0f}x")
    
    # 3. 注意事项
    print("\n--- 注意事项 ---")
    
    # 可哈希的参数可以缓存
    @lru_cache(maxsize=10)
    def process(key, value):
        return f"{key}: {value}"
    
    print(f"可缓存: {process('name', 'Alice')}")
    
    # 不可哈希的参数会报错
    try:
        process("data", [1, 2, 3])  # TypeError
    except TypeError as e:
        print(f"不可缓存: {e}")
    
    # 4. typed 参数
    @lru_cache(maxsize=10, typed=True)
    def typed_process(x):
        return x * 2
    
    # int 和 float 被视为不同参数
    typed_process(1)
    typed_process(1.0)
    print(f"typed 缓存: {typed_process.cache_info()}")


# ============================================================
# 第四部分：singledispatch 泛型函数
# ============================================================

def singledispatch_demo():
    """演示 singledispatch 的用法"""
    print("\n" + "=" * 50)
    print("singledispatch 泛型函数")
    print("=" * 50)
    
    @singledispatch
    def serialize(value):
        """序列化（根据类型分派）"""
        raise TypeError(f"不支持的类型: {type(value)}")
    
    @serialize.register(int)
    def _(value):
        return f"int:{value}"
    
    @serialize.register(float)
    def _(value):
        return f"float:{value:.2f}"
    
    @serialize.register(str)
    def _(value):
        return f"str:{value}"
    
    @serialize.register(list)
    def _(value):
        return f"list:[{','.join(str(x) for x in value)}]"
    
    @serialize.register(dict)
    def _(value):
        items = ','.join(f"{k}={v}" for k, v in value.items())
        return f"dict:{{{items}}}"
    
    # 使用
    print(f"serialize(42): {serialize(42)}")
    print(f"serialize(3.14): {serialize(3.14)}")
    print(f"serialize('hello'): {serialize('hello')}")
    print(f"serialize([1,2,3]): {serialize([1,2,3])}")
    print(f"serialize({{'a':1}}): {serialize({'a':1})}")
    
    # 实际应用：格式化输出
    @singledispatch
    def format_value(value):
        return str(value)
    
    @format_value.register(int)
    def _(value):
        return f"{value:,}"
    
    @format_value.register(float)
    def _(value):
        return f"{value:,.2f}"
    
    @format_value.register(list)
    def _(value):
        return f"[{', '.join(str(x) for x in value)}]"
    
    print(f"\nformat_value(1234567): {format_value(1234567)}")
    print(f"format_value(3.14159): {format_value(3.14159)}")


# ============================================================
# 第五部分：total_ordering 自动比较
# ============================================================

def total_ordering_demo():
    """演示 total_ordering 的用法"""
    print("\n" + "=" * 50)
    print("total_ordering 自动比较")
    print("=" * 50)
    
    @total_ordering
    class Version:
        """版本号比较"""
        
        def __init__(self, major, minor=0, patch=0):
            self.major = major
            self.minor = minor
            self.patch = patch
        
        def __eq__(self, other):
            if not isinstance(other, Version):
                return NotImplemented
            return (self.major, self.minor, self.patch) == \
                   (other.major, other.minor, other.patch)
        
        def __lt__(self, other):
            if not isinstance(other, Version):
                return NotImplemented
            return (self.major, self.minor, self.patch) < \
                   (other.major, other.minor, other.patch)
        
        def __repr__(self):
            return f"Version({self.major}.{self.minor}.{self.patch})"
    
    # 自动获得 __le__, __gt__, __ge__
    v1 = Version(1, 0, 0)
    v2 = Version(1, 2, 3)
    v3 = Version(2, 0, 0)
    
    print(f"{v1} < {v2}: {v1 < v2}")
    print(f"{v1} > {v2}: {v1 > v2}")
    print(f"{v2} <= {v2}: {v2 <= v2}")
    print(f"{v3} >= {v1}: {v3 >= v1}")
    
    # 可以用于排序
    versions = [Version(2, 1), Version(1, 0), Version(1, 5), Version(2, 0)]
    sorted_versions = sorted(versions)
    print(f"排序: {sorted_versions}")


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    reduce_demo()
    partial_demo()
    lru_cache_demo()
    singledispatch_demo()
    total_ordering_demo()
    
    print("\n" + "=" * 50)
    print("✅ functools 演示完成")
    print("=" * 50)
