"""
Day 100 - 知识体系梳理：综合回顾示例 1
将 100 天中多个概念融合到一个实际场景中
"""

import time
import functools
import contextlib
from dataclasses import dataclass, field
from typing import Generator, Any


# ============================================================
# 概念融合：装饰器 + 上下文管理器 + dataclass + 生成器
# ============================================================

# 1. 装饰器：用于性能计时（Day 23-24）
def timer(func):
    """计时装饰器 - 综合运用装饰器知识"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  ⏱ {func.__name__} 耗时: {elapsed:.4f}s")
        return result
    return wrapper


# 2. 上下文管理器：用于资源管理（Day 25）
@contextlib.contextmanager
def database_connection(name: str):
    """模拟数据库连接 - 综合运用上下文管理器知识"""
    print(f"  📡 连接到数据库: {name}")
    conn = {"name": name, "connected": True}
    try:
        yield conn
    finally:
        conn["connected"] = False
        print(f"  📡 断开数据库连接: {name}")


# 3. dataclass：用于数据建模（Day 43）
@dataclass
class QueryResult:
    """查询结果 - 综合运用 dataclass 知识"""
    query: str
    rows: list = field(default_factory=list)
    execution_time: float = 0.0
    
    @property
    def row_count(self) -> int:
        return len(self.rows)


# 4. 生成器：用于数据流处理（Day 22）
def process_stream(data: list, batch_size: int = 3) -> Generator:
    """分批处理数据 - 综合运用生成器知识"""
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        print(f"  📦 处理批次 {i // batch_size + 1}: {batch}")
        yield batch


# ============================================================
# 综合实战：数据处理管道
# ============================================================

@timer
def data_pipeline():
    """
    一个综合了多种概念的数据处理管道：
    - 装饰器监控性能
    - 上下文管理器管理数据库连接
    - dataclass 存储结果
    - 生成器实现流式处理
    - 异常处理保障健壮性
    """
    # 模拟数据
    raw_data = [
        {"name": "Alice", "score": 85},
        {"name": "Bob", "score": 92},
        {"name": "Charlie", "score": 78},
        {"name": "David", "score": 95},
        {"name": "Eve", "score": 88},
    ]
    
    results = []
    
    # 使用上下文管理器管理数据库
    with database_connection("student_db") as conn:
        print(f"  ✅ 数据库已连接: {conn['name']}")
        
        # 使用生成器流式处理数据
        for batch in process_stream(raw_data, batch_size=2):
            for item in batch:
                # 异常处理
                try:
                    processed = {
                        "name": item["name"],
                        "score": item["score"],
                        "grade": "A" if item["score"] >= 90 else "B" if item["score"] >= 80 else "C",
                    }
                    results.append(processed)
                except KeyError as e:
                    print(f"  ⚠️ 数据错误: {e}")
    
    # 使用 dataclass 存储结果
    qr = QueryResult(
        query="SELECT * FROM students",
        rows=results,
        execution_time=0.1,
    )
    
    print(f"\n  📊 查询结果: {qr.row_count} 条记录")
    for row in qr.rows:
        print(f"     {row['name']}: {row['score']}分 → {row['grade']}")
    
    return qr


# ============================================================
# 概念关联：展示知识间的内在联系
# ============================================================

def demonstrate_knowledge_links():
    """展示 100 天知识间的关联"""
    print("\n" + "=" * 60)
    print("🔗 知识关联演示")
    print("=" * 60)
    
    # 关联 1: 装饰器 + 闭包 + 高阶函数
    print("\n📌 关联 1: 装饰器 = 闭包 + 高阶函数")
    print("   闭包提供数据捕获，高阶函数提供函数包装")
    
    # 关联 2: 迭代器 + 生成器 + for 循环
    print("\n📌 关联 2: for 循环底层 = iter() + __next__() + StopIteration")
    print("   生成器是迭代器的语法糖，让代码更简洁")
    
    # 关联 3: 上下文管理器 + 异常处理 + with 语句
    print("\n📌 关联 3: with 语句 = __enter__ + __exit__ + 异常处理")
    print("   上下文管理器保证资源释放，无论是否发生异常")
    
    # 关联 4: 类型提示 + dataclass + 描述符
    print("\n📌 关联 4: dataclass = 类型提示 + __init__ 自动生成 + 描述符")
    print("   类型提示让 dataclass 更强大，IDE 支持更好")
    
    # 关联 5: 装饰器 + 类方法 + staticmethod
    print("\n📌 关联 5: @staticmethod 本质是装饰器应用")
    print("   装饰器是一种通用的元编程工具")


if __name__ == "__main__":
    print("=" * 60)
    print("🎓 Day 100 - 综合回顾示例 1")
    print("   装饰器 + 上下文管理器 + dataclass + 生成器")
    print("=" * 60)
    
    # 运行数据管道
    result = data_pipeline()
    
    # 展示知识关联
    demonstrate_knowledge_links()
    
    print("\n" + "=" * 60)
    print("✅ 综合回顾完成！")
    print("   这个示例融合了 Day 22, 23, 25, 43 的核心概念")
    print("=" * 60)
