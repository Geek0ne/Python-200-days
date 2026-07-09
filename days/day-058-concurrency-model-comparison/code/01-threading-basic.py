"""
01-threading-basic.py — 多线程基础用法
演示线程创建、同步、GIL 对 CPU 密集型的影响
"""

import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── 1. 基础线程创建 ──

def worker(name, delay):
    """线程工作函数"""
    print(f"[Thread-{name}] 开始工作 (PID: {os.getpid()}, TID: {threading.get_ident()})")
    time.sleep(delay)
    print(f"[Thread-{name}] 工作完成")


def demo_basic_thread():
    """演示基本线程创建与启动"""
    print("=" * 50)
    print("1. 基础线程创建")
    print("=" * 50)

    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(f"T{i}", 1), daemon=False)
        threads.append(t)
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join()

    print("所有线程完成\n")


# ── 2. 共享数据与锁 ──

counter = 0
lock = threading.Lock()


def increment_unsafe(n):
    """不安全的计数器（数据竞争）"""
    global counter
    for _ in range(n):
        counter += 1  # 非原子操作！


def increment_safe(n):
    """安全的计数器（加锁）"""
    global counter
    for _ in range(n):
        with lock:
            counter += 1


def demo_data_race():
    """演示数据竞争问题"""
    print("=" * 50)
    print("2. 数据竞争 vs 加锁保护")
    print("=" * 50)

    n = 100000

    # 无锁：数据竞争
    global counter
    counter = 0
    threads = [
        threading.Thread(target=increment_unsafe, args=(n,)),
        threading.Thread(target=increment_unsafe, args=(n,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"无锁结果: {counter} (期望: {n * 2})")

    # 有锁：正确
    counter = 0
    threads = [
        threading.Thread(target=increment_safe, args=(n,)),
        threading.Thread(target=increment_safe, args=(n,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"有锁结果: {counter} (期望: {n * 2})")
    print()


# ── 3. 线程池 ──

def fetch_page(url):
    """模拟网页请求"""
    time.sleep(0.1)  # 模拟 I/O 等待
    return f"页面内容 from {url}"


def demo_thread_pool():
    """演示线程池"""
    print("=" * 50)
    print("3. 线程池 (ThreadPoolExecutor)")
    print("=" * 50)

    urls = [f"http://example.com/page/{i}" for i in range(10)]

    start = time.time()

    with ThreadPoolExecutor(max_workers=4) as executor:
        # 方式1: submit + as_completed
        futures = {executor.submit(fetch_page, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            result = future.result()
            print(f"  完成: {url}")

    elapsed = time.time() - start
    print(f"总耗时: {elapsed:.2f}s (10 个任务, 4 线程池)")
    print()


# ── 4. GIL 对 CPU 密集型的影响 ──

def cpu_bound_task(n):
    """CPU 密集型任务：计算质数个数"""
    count = 0
    for i in range(2, n):
        if all(i % j != 0 for j in range(2, int(i**0.5) + 1)):
            count += 1
    return count


def demo_gil_impact():
    """演示 GIL 对 CPU 密集型任务的影响"""
    print("=" * 50)
    print("4. GIL 对 CPU 密集型的影响")
    print("=" * 50)

    n = 5000  # 质数范围
    rounds = 4  # 重复次数

    # 单线程
    start = time.time()
    for _ in range(rounds):
        cpu_bound_task(n)
    single_time = time.time() - start
    print(f"单线程 ({rounds}轮): {single_time:.2f}s")

    # 多线程
    start = time.time()
    threads = []
    for _ in range(rounds):
        t = threading.Thread(target=cpu_bound_task, args=(n,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    multi_time = time.time() - start
    print(f"多线程 ({rounds}线程): {multi_time:.2f}s")

    ratio = multi_time / single_time
    if ratio > 1:
        print(f"⚠️  多线程比单线程慢 {ratio:.1f}x (GIL 争抢导致)")
    else:
        print(f"多线程快 {1/ratio:.1f}x")
    print()


if __name__ == "__main__":
    demo_basic_thread()
    demo_data_race()
    demo_thread_pool()
    demo_gil_impact()
    print("✅ 所有线程示例执行完毕")
