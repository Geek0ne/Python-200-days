"""
Day 057 - 异步迭代器与生成器（进阶用法 + 避坑）

学习要点：
1. 异步迭代器的实现
2. 异步生成器的使用
3. 常见陷阱与解决方案
"""

import asyncio
from typing import AsyncGenerator


# ============================================
# 示例 1：异步迭代器完整实现
# ============================================

class AsyncCursor:
    """模拟数据库游标 — 异步迭代器"""

    def __init__(self, data: list, page_size: int = 3):
        self.data = data
        self.page_size = page_size
        self.offset = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.offset >= len(self.data):
            raise StopAsyncIteration

        # 模拟异步获取下一批数据
        await asyncio.sleep(0.05)
        chunk = self.data[self.offset:self.offset + self.page_size]
        self.offset += self.page_size
        return chunk


# ============================================
# 示例 2：异步生成器 — 数据流处理
# ============================================

async def fetch_user(user_id: int) -> dict:
    """模拟异步 API 请求"""
    await asyncio.sleep(0.1)
    return {"id": user_id, "name": f"用户{user_id}", "score": user_id * 10}


async def user_stream(user_ids: list[int]) -> AsyncGenerator[dict, None]:
    """异步用户数据流"""
    for uid in user_ids:
        user = await fetch_user(uid)
        yield user


async def filtered_users(
    min_score: int,
) -> AsyncGenerator[dict, None]:
    """过滤后的异步数据流"""
    all_ids = list(range(1, 21))  # 模拟 1~20 用户
    async for user in user_stream(all_ids):
        if user["score"] >= min_score:
            yield user


# ============================================
# 示例 3：异步生成器表达式与推导式
# ============================================

async def square(n: int) -> int:
    """模拟异步计算"""
    await asyncio.sleep(0.01)
    return n * n


# ============================================
# 示例 4：常见陷阱演示
# ============================================

# ❌ 陷阱 1：在异步迭代中使用同步 I/O
async def bad_example():
    """不要这样做！"""
    import time
    # time.sleep(0.1)  # 会阻塞事件循环！
    # 应该用 await asyncio.sleep(0.1)
    pass


# ❌ 陷阱 2：忘记 StopAsyncIteration
# 异步迭代器必须抛出 StopAsyncIteration（不是 StopIteration）
# 如果用 raise StopIteration 会变成 RuntimeError

# ❌ 陷阱 3：在 async for 中修改迭代器
# async for 会调用 __anext__，如果在循环中修改迭代器内部状态可能出问题


async def main():
    print("=" * 50)
    print("示例 1：异步游标分页获取")
    print("=" * 50)

    data = [f"记录{i}" for i in range(10)]
    cursor = AsyncCursor(data, page_size=3)

    page_num = 1
    async for page in cursor:
        print(f"  第 {page_num} 页: {page}")
        page_num += 1

    print("\n" + "=" * 50)
    print("示例 2：异步生成器过滤数据")
    print("=" * 50)

    print("  过滤 score >= 100 的用户:")
    count = 0
    async for user in filtered_users(min_score=100):
        print(f"    {user}")
        count += 1
        if count >= 5:
            print("    ... (最多显示 5 条)")
            break

    print("\n" + "=" * 50)
    print("示例 3：异步推导式")
    print("=" * 50)

    # 列表推导式（同步方式，但每个元素需要 await）
    results = [await square(i) for i in range(6)]
    print(f"  列表推导式: {results}")

    # 异步生成器函数
    async def gen():
        for i in range(6):
            yield await square(i)

    print("  异步生成器遍历: ", end="")
    async for val in gen():
        print(val, end=" ")
    print()

    # 异步生成器表达式
    gen_expr = (await square(i) for i in range(6))
    # 注意：异步生成器表达式在 Python 3.6+ 需要用 async for 遍历
    # 但 (await x for ...) 语法在某些版本有限制
    # 推荐使用 async def 函数

    print("\n" + "=" * 50)
    print("示例 4：异步迭代器实现累加器")
    print("=" * 50)

    async def async_counter(start: int, end: int, step: int = 1):
        """异步计数器生成器"""
        current = start
        while current < end:
            await asyncio.sleep(0.05)
            yield current
            current += step

    total = 0
    async for num in async_counter(1, 11):
        total += num
        print(f"  累加 {num}, 当前总和: {total}")

    print(f"\n  最终总和: {total}")

    print("\n" + "=" * 50)
    print("示例 5：异常处理")
    print("=" * 50)

    async def risky_generator():
        """可能出错的异步生成器"""
        for i in range(5):
            await asyncio.sleep(0.05)
            if i == 3:
                raise ValueError(f"在 {i} 时出错")
            yield i

    try:
        async for val in risky_generator():
            print(f"  获取: {val}")
    except ValueError as e:
        print(f"  ❌ 捕获异常: {e}")

    print("\n✅ 所有示例运行完毕")


if __name__ == "__main__":
    asyncio.run(main())
