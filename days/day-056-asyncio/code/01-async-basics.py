"""
Day 056 - asyncio 基础用法
演示 async/await 关键字、协程函数 vs 协程对象、顺序执行 vs 并发执行
"""
import asyncio
import time


# ============================================
# 1. 协程函数 vs 协程对象
# ============================================
async def say_hello():
    """这是一个协程函数"""
    print("Hello")
    await asyncio.sleep(1)  # 挂起 1 秒
    print("World")
    return "完成"


# 注意：直接调用协程函数不会执行它，只是返回协程对象
coro = say_hello()
print(f"协程对象类型: {type(coro)}")  # <class 'coroutine'>
print(f"协程对象: {coro}")

# 必须通过事件循环来执行
result = asyncio.run(coro)
print(f"返回值: {result}")


# ============================================
# 2. 顺序执行 vs 并发执行
# ============================================
async def fetch_data(name, delay):
    """模拟异步数据获取"""
    print(f"[{name}] 开始获取数据...")
    await asyncio.sleep(delay)  # 模拟 I/O 等待
    print(f"[{name}] 数据获取完成!")
    return f"{name} 的数据"


async def sequential():
    """顺序执行：一个接一个"""
    print("\n--- 顺序执行 ---")
    start = time.time()
    
    # 顺序 await：必须等前一个完成
    result1 = await fetch_data("A", 2)
    result2 = await fetch_data("B", 2)
    result3 = await fetch_data("C", 2)
    
    elapsed = time.time() - start
    print(f"顺序执行总耗时: {elapsed:.1f}s")  # 约 6 秒
    return [result1, result2, result3]


async def concurrent():
    """并发执行：同时发起"""
    print("\n--- 并发执行 ---")
    start = time.time()
    
    # 使用 gather 并发执行
    results = await asyncio.gather(
        fetch_data("A", 2),
        fetch_data("B", 2),
        fetch_data("C", 2),
    )
    
    elapsed = time.time() - start
    print(f"并发执行总耗时: {elapsed:.1f}s")  # 约 2 秒
    return results


# ============================================
# 3. 创建 Task 进行并发
# ============================================
async def worker(name, delay):
    """工作协程"""
    print(f"[{name}] 开始工作 (延迟 {delay}s)")
    await asyncio.sleep(delay)
    print(f"[{name}] 工作完成!")
    return f"{name} 完成"


async def demo_tasks():
    """使用 create_task 进行并发"""
    print("\n--- Task 并发 ---")
    start = time.time()
    
    # 创建 Task（立即调度执行）
    task_a = asyncio.create_task(worker("A", 3))
    task_b = asyncio.create_task(worker("B", 1))
    task_c = asyncio.create_task(worker("C", 2))
    
    # 等待所有任务完成
    result_a = await task_a
    result_b = await task_b
    result_c = await task_c
    
    elapsed = time.time() - start
    print(f"Task 并发总耗时: {elapsed:.1f}s")  # 约 3 秒（取最长的）
    print(f"结果: {result_a}, {result_b}, {result_c}")


# ============================================
# 主函数
# ============================================
async def main():
    """主函数：演示各种异步模式"""
    
    # 演示顺序执行
    seq_results = await sequential()
    print(f"顺序结果: {seq_results}")
    
    # 演示并发执行
    con_results = await concurrent()
    print(f"并发结果: {con_results}")
    
    # 演示 Task 并发
    await demo_tasks()
    
    print("\n✅ 所有演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
