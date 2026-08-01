"""
Day 095 - 函数式编程深入
03-functional-pipeline.py: 函数式数据处理管道实战

知识点:
  - 管道模式实现
  - 函数组合
  - 惰性求值
  - 实战：日志分析、数据清洗、文本处理管道
"""

from functools import reduce
from collections import Counter, defaultdict
from typing import Callable, Any, Iterator
import re

# ============================================================
# 第一部分：管道基础
# ============================================================

def pipe_forward(*functions):
    """从左到右执行的管道"""
    def pipeline(data):
        result = data
        for f in functions:
            result = f(result)
        return result
    return pipeline

def compose(*functions):
    """从右到左组合的函数"""
    def composed(data):
        result = data
        for f in reversed(functions):
            result = f(result)
        return result
    return composed

def pipe_demo():
    """演示管道基础"""
    print("=" * 50)
    print("管道基础")
    print("=" * 50)
    
    # 1. 基本管道
    process = pipe_forward(
        str.strip,
        str.lower,
        lambda s: s.replace(" ", "_"),
        lambda s: f"[{s}]"
    )
    
    result = process("  Hello World  ")
    print(f"基本管道: '{result}'")
    
    # 2. 数值管道
    calculate = pipe_forward(
        lambda x: x * 2,
        lambda x: x + 10,
        lambda x: x ** 2
    )
    
    result = calculate(5)
    print(f"数值管道: {result} (5*2+10)^2 = 400")
    
    # 3. 条件管道
    def when(predicate, func):
        """条件执行"""
        def wrapper(data):
            if predicate(data):
                return func(data)
            return data
        return wrapper
    
    process = pipe_forward(
        when(lambda x: x > 0, lambda x: x * 2),
        when(lambda x: x > 20, lambda x: x - 5)
    )
    
    print(f"条件管道(10): {process(10)}")  # 10*2=20, 20-5=15
    print(f"条件管道(-5): {process(-5)}")   # -5不变(不大于0)


# ============================================================
# 第二部分：惰性求值
# ============================================================

class LazyPipeline:
    """惰性求值管道：只在需要时才执行"""
    
    def __init__(self, data):
        self._data = data
        self._operations = []
    
    def map(self, func):
        """添加 map 操作"""
        self._operations.append(('map', func))
        return self
    
    def filter(self, predicate):
        """添加 filter 操作"""
        self._operations.append(('filter', predicate))
        return self
    
    def flat_map(self, func):
        """添加 flat_map 操作"""
        self._operations.append(('flat_map', func))
        return self
    
    def take(self, n):
        """取前 n 个元素"""
        self._operations.append(('take', n))
        return self
    
    def execute(self):
        """执行所有操作"""
        result = self._data
        for op_type, op_func in self._operations:
            if op_type == 'map':
                result = map(op_func, result)
            elif op_type == 'filter':
                result = filter(op_func, result)
            elif op_type == 'flat_map':
                result = (item for sub in map(op_func, result) for item in sub)
            elif op_type == 'take':
                result = (x for i, x in enumerate(result) if i < op_func)
        return list(result)
    
    def __iter__(self):
        return iter(self.execute())


def lazy_pipeline_demo():
    """演示惰性求值管道"""
    print("\n" + "=" * 50)
    print("惰性求值管道")
    print("=" * 50)
    
    # 1. 大数据处理
    data = range(1_000_000)
    
    # 惰性管道：只处理需要的元素
    lazy_result = (
        LazyPipeline(data)
        .filter(lambda x: x % 2 == 0)     # 过滤偶数
        .map(lambda x: x * 2)             # 乘以2
        .filter(lambda x: x > 100)        # 大于100
        .take(10)                          # 只取前10个
        .execute()
    )
    
    print(f"惰性管道结果: {lazy_result}")
    
    # 2. 比较性能
    import time
    
    # 惰性管道
    start = time.time()
    lazy = list(
        LazyPipeline(range(1_000_000))
        .filter(lambda x: x % 3 == 0)
        .map(lambda x: x // 3)
        .take(100)
    )
    lazy_time = time.time() - start
    
    # 普通列表操作
    start = time.time()
    normal = [x // 3 for x in range(1_000_000) if x % 3 == 0][:100]
    normal_time = time.time() - start
    
    print(f"\n惰性管道: {lazy_time:.6f}s")
    print(f"列表推导: {normal_time:.6f}s")
    print(f"结果相同: {lazy == normal}")
    
    # 3. 无限序列
    def count_from(n=0):
        """无限计数器"""
        while True:
            yield n
            n += 1
    
    # 从无限序列中取前10个满足条件的
    result = list(
        LazyPipeline(count_from(1))
        .filter(lambda x: x % 7 == 0)  # 7的倍数
        .take(10)
    )
    
    print(f"\n无限序列中的7的倍数: {result}")


# ============================================================
# 第三部分：函数组合
# ============================================================

def compose_demo():
    """演示函数组合"""
    print("\n" + "=" * 50)
    print("函数组合")
    print("=" * 50)
    
    import math
    
    # 从右到左组合
    process = compose(
        math.sqrt,           # 3. 开方
        lambda x: x + 1,    # 2. 加1
        lambda x: x * 2,    # 1. 乘2
    )
    
    print(f"compose: process(4) = sqrt(4*2+1) = {process(4)}")
    
    # 从左到右管道
    process = pipe_forward(
        lambda x: x * 2,    # 1. 乘2
        lambda x: x + 1,    # 2. 加1
        math.sqrt,           # 3. 开方
    )
    
    print(f"pipe: process(4) = sqrt(4*2+1) = {process(4)}")
    
    # 1. 数学运算组合
    print("\n--- 数学运算组合 ---")
    
    # 创建可复用的变换
    scale = lambda factor: lambda x: x * factor
    offset = lambda amount: lambda x: x + amount
    
    # 组合变换
    transform = pipe_forward(
        scale(2),           # 乘2
        offset(10),         # 加10
        scale(0.5),         # 乘0.5
    )
    
    print(f"transform(5) = {transform(5)}")  # (5*2+10)*0.5 = 10
    
    # 2. 字符串处理组合
    print("\n--- 字符串处理组合 ---")
    
    clean = pipe_forward(
        str.strip,
        str.lower,
        lambda s: re.sub(r'\s+', ' ', s),  # 多个空格合并
    )
    
    title = pipe_forward(
        clean,
        str.title,
    )
    
    slug = pipe_forward(
        clean,
        lambda s: re.sub(r'[^a-z0-9]+', '-', s),
        lambda s: s.strip('-'),
    )
    
    text = "  Hello   World   from   Python  "
    print(f"clean: '{clean(text)}'")
    print(f"title: '{title(text)}'")
    print(f"slug: '{slug(text)}'")
    
    # 3. 数据验证组合
    print("\n--- 数据验证组合 ---")
    
    def validate(rule, error_msg):
        """创建验证器"""
        def validator(data):
            if rule(data):
                return {"valid": True, "data": data}
            return {"valid": False, "error": error_msg}
        return validator
    
    def all_valid(*validators):
        """组合多个验证器"""
        def combined(data):
            for v in validators:
                result = v(data)
                if not result["valid"]:
                    return result
            return {"valid": True, "data": data}
        return combined
    
    user_validator = all_valid(
        validate(lambda d: "username" in d, "缺少用户名"),
        validate(lambda d: len(d.get("username", "")) >= 3, "用户名太短"),
        validate(lambda d: "email" in d, "缺少邮箱"),
        validate(lambda d: "@" in d.get("email", ""), "邮箱格式错误"),
    )
    
    # 测试验证
    test_cases = [
        {"username": "alice", "email": "alice@example.com"},
        {"username": "ab", "email": "alice@example.com"},
        {"username": "alice", "email": "invalid"},
    ]
    
    for case in test_cases:
        result = user_validator(case)
        status = "✅" if result["valid"] else f"❌ {result.get('error')}"
        print(f"  {case} → {status}")


# ============================================================
# 第四部分：实战管道
# ============================================================

def log_analysis_pipeline():
    """实战：日志分析管道"""
    print("\n" + "=" * 50)
    print("实战：日志分析管道")
    print("=" * 50)
    
    # 模拟日志数据
    logs = [
        "2024-01-15 10:30:15 ERROR Database connection failed timeout=30s",
        "2024-01-15 10:30:16 INFO Request processed user=alice status=200",
        "2024-01-15 10:30:17 WARNING Slow query detected duration=2.5s",
        "2024-01-15 10:30:18 ERROR Timeout exceeded request_id=abc123",
        "2024-01-15 10:30:19 INFO Request processed user=bob status=200",
        "2024-01-15 10:30:20 ERROR Database connection failed retry=1",
        "2024-01-15 10:30:21 INFO Request processed user=alice status=404",
        "2024-01-15 10:30:22 WARNING Memory usage high usage=85%",
    ]
    
    # 定义处理步骤
    def parse_log(log):
        """解析日志行"""
        parts = log.split(" ", 4)
        return {
            "date": parts[0],
            "time": parts[1],
            "level": parts[2],
            "message": parts[3] if len(parts) > 3 else "",
            "detail": parts[4] if len(parts) > 4 else "",
        }
    
    def extract_field(detail, field):
        """从详情中提取字段"""
        match = re.search(f'{field}=([^\\s]+)', detail)
        return match.group(1) if match else None
    
    # 管道1：统计各级别数量
    level_stats = pipe_forward(
        list,
        lambda logs: [parse_log(l) for l in logs],
        lambda logs: Counter(l["level"] for l in logs),
        dict
    )
    
    stats = level_stats(logs)
    print(f"级别统计: {stats}")
    
    # 管道2：提取错误信息
    error_analysis = pipe_forward(
        list,
        lambda logs: [parse_log(l) for l in logs],
        lambda logs: [l for l in logs if l["level"] == "ERROR"],
        lambda errors: [
            {"message": e["message"], "time": e["time"]}
            for e in errors
        ]
    )
    
    errors = error_analysis(logs)
    print(f"\n错误分析:")
    for e in errors:
        print(f"  [{e['time']}] {e['message']}")
    
    # 管道3：用户活跃度分析
    user_activity = pipe_forward(
        list,
        lambda logs: [parse_log(l) for l in logs],
        lambda logs: [l for l in logs if "user=" in l.get("detail", "")],
        lambda logs: [
            {"user": extract_field(l["detail"], "user"), "status": extract_field(l["detail"], "status")}
            for l in logs
        ],
        lambda records: Counter(r["user"] for r in records)
    )
    
    activity = user_activity(logs)
    print(f"\n用户活跃度: {dict(activity)}")
    
    # 管道4：时间窗口分析
    time_window_analysis = pipe_forward(
        list,
        lambda logs: [parse_log(l) for l in logs],
        lambda logs: defaultdict(int, Counter(l["time"][:7] for l in logs)),  # 按秒统计
        dict
    )
    
    time_stats = time_window_analysis(logs)
    print(f"\n时间窗口(每秒): {dict(time_stats)}")


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    pipe_demo()
    lazy_pipeline_demo()
    compose_demo()
    log_analysis_pipeline()
    
    print("\n" + "=" * 50)
    print("✅ 函数式管道实战演示完成")
    print("=" * 50)
