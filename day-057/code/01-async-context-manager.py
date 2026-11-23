"""
Day 057 - 异步上下文管理器基础用法

学习要点：
1. __aenter__ / __aexit__ 的实现
2. asynccontextmanager 装饰器
3. 资源生命周期管理
"""

import asyncio
from contextlib import asynccontextmanager


# ============================================
# 示例 1：基于类的异步上下文管理器
# ============================================

class AsyncResource:
    """模拟异步资源（如数据库连接、文件句柄）"""

    def __init__(self, name: str):
        self.name = name
        self._is_open = False
        self._data = {}

    async def __aenter__(self):
        """进入上下文：建立连接/获取资源"""
        print(f"🔌 [{self.name}] 正在建立连接...")
        await asyncio.sleep(0.3)  # 模拟异步操作
        self._is_open = True
        print(f"✅ [{self.name}] 连接已建立")
        return self  # 返回值绑定到 as 变量

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文：释放资源"""
        print(f"🔌 [{self.name}] 正在释放连接...")
        await asyncio.sleep(0.1)  # 模拟异步清理
        self._is_open = False
        print(f"✅ [{self.name}] 连接已释放")
        # 返回 False = 不抑制异常
        # 返回 True  = 吞掉异常（慎用！）
        return False

    async def execute(self, key: str, value: str):
        """模拟资源操作"""
        if not self._is_open:
            raise RuntimeError(f"资源 {self.name} 未打开")
        await asyncio.sleep(0.05)
        self._data[key] = value
        return f"[{self.name}] 写入 {key}={value}"


# ============================================
# 示例 2：基于装饰器的异步上下文管理器
# ============================================

@asynccontextmanager
async def async_timer(label: str):
    """异步计时器上下文管理器"""
    print(f"⏱️  [{label}] 计时开始")
    start = asyncio.get_event_loop().time()

    try:
        yield  # 执行 async with 块内的代码
    except Exception as e:
        print(f"⚠️  [{label}] 发生异常: {e}")
        raise
    finally:
        elapsed = asyncio.get_event_loop().time() - start
        print(f"⏱️  [{label}] 耗时: {elapsed:.3f}s")


# ============================================
# 示例 3：嵌套异步上下文管理器
# ============================================

@asynccontextmanager
async def database_connection(db_name: str):
    """模拟数据库连接"""
    print(f"📊 连接数据库 {db_name}")
    await asyncio.sleep(0.1)
    conn = {"name": db_name, "status": "connected"}
    try:
        yield conn
    finally:
        conn["status"] = "disconnected"
        print(f"📊 断开数据库 {db_name}")


@asynccontextmanager
async def transaction(conn: dict):
    """模拟数据库事务"""
    print(f"🔄 开始事务")
    await asyncio.sleep(0.05)
    try:
        yield conn
        print(f"🔄 事务提交")
    except Exception:
        print(f"🔄 事务回滚")
        raise


# ============================================
# 主函数
# ============================================

async def main():
    print("=" * 50)
    print("示例 1：基于类的异步上下文管理器")
    print("=" * 50)

    async with AsyncResource("数据库A") as res:
        result = await res.execute("user", "聂董")
        print(f"  操作结果: {result}")
    # __aexit__ 在这里自动调用，即使发生异常也会释放资源

    print("\n" + "=" * 50)
    print("示例 2：计时器上下文管理器")
    print("=" * 50)

    async with async_timer("模拟任务"):
        await asyncio.sleep(0.5)
        print("  执行模拟任务中...")

    print("\n" + "=" * 50)
    print("示例 3：嵌套上下文管理器")
    print("=" * 50)

    async with database_connection("mydb") as conn:
        async with transaction(conn):
            print(f"  连接状态: {conn['status']}")
            await asyncio.sleep(0.1)
            print("  执行 SQL 操作...")

    print("\n" + "=" * 50)
    print("示例 4：异常场景")
    print("=" * 50)

    async with AsyncResource("数据库B") as res:
        try:
            await res.execute("key", "value")
            raise ValueError("模拟业务异常！")
        except ValueError as e:
            print(f"  捕获异常: {e}")
        # 即使有异常，__aexit__ 也会执行释放资源

    print("\n✅ 所有示例运行完毕")


if __name__ == "__main__":
    asyncio.run(main())
