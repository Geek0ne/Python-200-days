"""
Day 067 — FastAPI 异步支持
运行方式：uvicorn 05-async-fastapi:app --reload
"""
import asyncio
import time
from fastapi import FastAPI

app = FastAPI(title="异步 FastAPI 示例")


@app.get("/sync/")
def sync_handler():
    """
    同步路由——运行在线程池中
    
    FastAPI 会把同步路由放到线程池执行，
    不会阻塞事件循环，但会占用一个线程。
    """
    start = time.time()
    time.sleep(1)  # 模拟耗时操作
    elapsed = time.time() - start
    return {"message": "同步完成", "耗时": f"{elapsed:.2f}秒"}


@app.get("/async/")
async def async_handler():
    """
    异步路由——不阻塞事件循环
    
    async/await 让出控制权，事件循环可以处理其他请求。
    适合 I/O 密集型操作（网络请求、文件读写、数据库查询）。
    """
    start = time.time()
    await asyncio.sleep(1)  # 异步等待，不阻塞
    elapsed = time.time() - start
    return {"message": "异步完成", "耗时": f"{elapsed:.2f}秒"}


async def fetch_data(url: str) -> dict:
    """模拟异步数据获取"""
    await asyncio.sleep(1)  # 模拟网络延迟
    return {"url": url, "status": "ok", "data": f"来自 {url} 的数据"}


@app.get("/concurrent/")
async def concurrent_handler():
    """
    并发执行——同时发起多个异步任务
    
    asyncio.gather 同时执行多个协程：
    - 3 个任务各需 1 秒
    - 总耗时约 1 秒（不是 3 秒！）
    """
    start = time.time()

    # 同时执行 3 个异步任务
    results = await asyncio.gather(
        fetch_data("api/users"),
        fetch_data("api/orders"),
        fetch_data("api/products"),
    )

    elapsed = time.time() - start
    return {
        "message": "并发完成",
        "耗时": f"{elapsed:.2f}秒",
        "results": results,
    }


@app.get("/sequential/")
async def sequential_handler():
    """
    顺序执行——逐个等待（对比用）
    
    和 concurrent 对比：
    - 3 个任务各需 1 秒
    - 总耗时约 3 秒（因为是顺序执行）
    """
    start = time.time()

    # 逐个等待
    r1 = await fetch_data("api/users")
    r2 = await fetch_data("api/orders")
    r3 = await fetch_data("api/products")

    elapsed = time.time() - start
    return {
        "message": "顺序完成",
        "耗时": f"{elapsed:.2f}秒",
        "results": [r1, r2, r3],
    }


# ========== 运行 ==========
# uvicorn 05-async-fastapi:app --reload
#
# 测试：
# curl http://127.0.0.1:8000/concurrent/   → ~1秒
# curl http://127.0.0.1:8000/sequential/    → ~3秒
#
# ⚠️ 避坑：不要在 async def 中使用 time.sleep()
# ❌ async def bad(): time.sleep(1)  → 阻塞整个事件循环！
# ✅ async def good(): await asyncio.sleep(1)
