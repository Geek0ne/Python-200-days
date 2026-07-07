"""
Day 056 - Task 与 Future 进阶用法
演示 Task 状态管理、错误处理、取消操作、超时控制
"""
import asyncio


# ============================================
# 1. Task 状态查询与回调
# ============================================
async def slow_operation():
    """一个耗时操作"""
    await asyncio.sleep(2)
    return 42


async def demo_task_states():
    """演示 Task 的各种状态"""
    print("=== Task 状态演示 ===\n")
    
    task = asyncio.create_task(slow_operation())
    
    # 创建后立即检查状态
    print(f"创建后 - done: {task.done()}, cancelled: {task.cancelled()}")
    
    # 添加完成回调
    def on_complete(t):
        print(f"  回调触发: done={t.done()}, result={t.result()}")
    
    task.add_done_callback(on_complete)
    
    # 等待完成
    result = await task
    print(f"完成后 - done: {task.done()}, result: {result}")
    print()


# ============================================
# 2. 错误处理 - try/except
# ============================================
async def failing_operation():
    """会失败的操作"""
    await asyncio.sleep(1)
    raise ValueError("操作失败了！")


async def demo_error_handling():
    """演示异常处理"""
    print("=== 异常处理演示 ===\n")
    
    # 方式 1：直接 try/except
    try:
        result = await failing_operation()
    except ValueError as e:
        print(f"捕获异常: {e}")
    
    # 方式 2：Task 中的异常
    task = asyncio.create_task(failing_operation())
    try:
        result = await task
    except ValueError as e:
        print(f"Task 异常: {e}")
    print()


# ============================================
# 3. gather 的错误处理
# ============================================
async def ok_task():
    await asyncio.sleep(0.5)
    return "成功"


async def fail_task():
    await asyncio.sleep(0.3)
    raise RuntimeError("失败了")


async def demo_gather_errors():
    """演示 gather 的错误处理"""
    print("=== gather 错误处理 ===\n")
    
    # 方式 1：默认行为（第一个异常会抛出）
    try:
        results = await asyncio.gather(ok_task(), fail_task())
    except RuntimeError as e:
        print(f"gather 默认: 捕获异常 - {e}")
    
    # 方式 2：return_exceptions=True（异常作为结果返回）
    results = await asyncio.gather(
        ok_task(), fail_task(),
        return_exceptions=True
    )
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"  结果 {i}: 异常 - {r}")
        else:
            print(f"  结果 {i}: {r}")
    print()


# ============================================
# 4. 取消 Task
# ============================================
async def long_running():
    """长时间运行的任务"""
    for i in range(10):
        print(f"  执行第 {i+1} 次...")
        await asyncio.sleep(1)
    return "完成"


async def demo_cancel():
    """演示取消 Task"""
    print("=== 取消 Task 演示 ===\n")
    
    task = asyncio.create_task(long_running())
    
    # 等待 3 秒后取消
    await asyncio.sleep(3)
    print("正在取消任务...")
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        print("任务已被取消!")
    
    print(f"取消后状态: cancelled={task.cancelled()}\n")


# ============================================
# 5. 超时控制
# ============================================
async def slow_task():
    """模拟慢速任务"""
    await asyncio.sleep(5)
    return "慢速任务完成"


async def demo_timeout():
    """演示超时控制"""
    print("=== 超时控制演示 ===\n")
    
    # 方式 1：wait_for
    try:
        result = await asyncio.wait_for(slow_task(), timeout=2.0)
        print(f"结果: {result}")
    except asyncio.TimeoutError:
        print("wait_for 超时!")
    
    # 方式 2：asyncio.timeout (Python 3.11+)
    try:
        async with asyncio.timeout(2.0):
            result = await slow_task()
            print(f"结果: {result}")
    except TimeoutError:
        print("asyncio.timeout 超时!")
    print()


# ============================================
# 主函数
# ============================================
async def main():
    await demo_task_states()
    await demo_error_handling()
    await demo_gather_errors()
    await demo_cancel()
    await demo_timeout()
    print("✅ 所有演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
