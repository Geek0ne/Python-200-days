"""
Day 097 - DSL 基础：用装饰器和上下文管理器构建简单 DSL

学习要点：
1. 装饰器如何实现声明式语法
2. 上下文管理器如何创建 DSL 作用域
3. 动态属性如何实现魔法访问
"""

from functools import wraps
from contextlib import contextmanager
from datetime import datetime


# ============================================================
# 示例 1：装饰器 DSL —— 日志记录器
# ============================================================

def logged(prefix="LOG"):
    """装饰器 DSL：给函数添加日志"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{prefix}] [{timestamp}] 调用 {func.__name__}")
            result = func(*args, **kwargs)
            print(f"[{prefix}] [{timestamp}] 返回 {func.__name__}")
            return result
        return wrapper
    return decorator


# DSL 使用：像声明一样给函数添加日志
@logged(prefix="INFO")
def process_order(order_id, items):
    """处理订单"""
    print(f"  处理订单 #{order_id}: {items}")
    return {"order_id": order_id, "status": "done"}


@logged(prefix="DEBUG")
def validate_user(user_id):
    """验证用户"""
    print(f"  验证用户 {user_id}")
    return True


print("=" * 50)
print("示例 1：装饰器 DSL")
print("=" * 50)
result1 = process_order("A001", ["商品A", "商品B"])
result2 = validate_user("U001")
print()


# ============================================================
# 示例 2：上下文管理器 DSL —— 数据库事务
# ============================================================

class FakeDB:
    """模拟数据库"""
    def __init__(self):
        self.data = {}
        self._transaction = False
        self._buffer = {}

    def insert(self, table, record):
        if self._transaction:
            self._buffer.setdefault(table, []).append(record)
            print(f"  [事务中] 缓存插入 {table}: {record}")
        else:
            self.data.setdefault(table, []).append(record)
            print(f"  [直接] 插入 {table}: {record}")

    def query(self, table):
        return self.data.get(table, [])


@contextmanager
def transaction(db):
    """事务上下文管理器 DSL"""
    db._transaction = True
    db._buffer = {}
    print(">> 开始事务")
    try:
        yield db
        # 提交
        for table, records in db._buffer.items():
            db.data.setdefault(table, []).extend(records)
        print(">> 事务已提交")
    except Exception as e:
        # 回滚
        db._buffer = {}
        print(f">> 事务回滚: {e}")
    finally:
        db._transaction = False


print("=" * 50)
print("示例 2：上下文管理器 DSL")
print("=" * 50)
db = FakeDB()

# DSL 使用：用 with 语句管理事务
with transaction(db) as tx:
    tx.insert("users", {"name": "Alice", "age": 30})
    tx.insert("orders", {"user": "Alice", "amount": 99.9})

print(f"数据库状态: {db.data}")
print()


# ============================================================
# 示例 3：动态属性 DSL —— 链式调用
# ============================================================

class SQLBuilder:
    """SQL 构建器 DSL —— 动态属性 + 链式调用"""
    
    def __init__(self):
        self._parts = {
            "select": "*",
            "from": "",
            "where": [],
            "order": "",
            "limit": None,
        }
    
    def __getattr__(self, name):
        """支持 builder.select() 语法"""
        if name.startswith("_"):
            raise AttributeError(name)
        
        def method(*args, **kwargs):
            if name == "select":
                self._parts["select"] = ", ".join(args) if args else "*"
            elif name == "from_":
                self._parts["from"] = args[0]
            elif name == "where":
                self._parts["where"].append(args[0])
            elif name == "order_by":
                self._parts["order"] = ", ".join(args)
            elif name == "limit":
                self._parts["limit"] = args[0]
            return self  # 返回 self 支持链式调用
        
        return method
    
    def build(self):
        sql = f"SELECT {self._parts['select']} FROM {self._parts['from']}"
        if self._parts["where"]:
            sql += " WHERE " + " AND ".join(self._parts["where"])
        if self._parts["order"]:
            sql += f" ORDER BY {self._parts['order']}"
        if self._parts["limit"]:
            sql += f" LIMIT {self._parts['limit']}"
        return sql


print("=" * 50)
print("示例 3：动态属性 DSL —— SQL 构建器")
print("=" * 50)

# DSL 使用：链式调用构建 SQL
query = (SQLBuilder()
    .select("name", "age", "email")
    .from_("users")
    .where("age > 18")
    .where("active = true")
    .order_by("name")
    .limit(10))

print(query.build())
# 输出: SELECT name, age, email FROM users WHERE age > 18 AND active = true ORDER BY name LIMIT 10
print()


# ============================================================
# 总结
# ============================================================
print("=" * 50)
print("今日要点总结")
print("=" * 50)
print("""
1. 装饰器 → 声明式语法，用 @ 语法糖
2. 上下文管理器 → 用 with 语句定义作用域
3. 动态属性 → __getattr__ 实现魔法访问
4. 链式调用 → 方法返回 self 实现流畅接口

这些技巧组合起来，就能构建出既优雅又实用的 DSL！
""")
