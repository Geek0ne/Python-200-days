"""
02-multiprocessing-basic.py — 多进程基础用法
演示进程创建、进程间通信、共享内存
"""

import multiprocessing
import time
import os
from multiprocessing import Process, Queue, Pool, Value, Array, Manager


# ── 1. 基础进程创建 ──

def process_worker(name):
    """进程工作函数"""
    print(f"[Process-{name}] 开始工作 (PID: {os.getpid()}, PPID: {os.getppid()})")
    time.sleep(0.5)
    print(f"[Process-{name}] 工作完成")


def demo_basic_process():
    """演示基本进程创建"""
    print("=" * 50)
    print("1. 基础进程创建")
    print("=" * 50)

    processes = []
    for i in range(3):
        p = Process(target=process_worker, args=(f"P{i}",))
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=5)
        if p.is_alive():
            p.terminate()

    print("所有进程完成\n")


# ── 2. 进程间通信 (Queue) ──

def producer(queue, n):
    """生产者：往队列放数据"""
    for i in range(n):
        item = f"item-{i}"
        queue.put(item)
        print(f"[Producer] 放入: {item}")
        time.sleep(0.1)
    queue.put(None)  # 结束信号


def consumer(queue):
    """消费者：从队列取数据"""
    while True:
        item = queue.get()
        if item is None:
            break
        print(f"[Consumer] 取出: {item}")
        time.sleep(0.2)  # 模拟处理


def demo_queue():
    """演示 Queue 进程间通信"""
    print("=" * 50)
    print("2. 进程间通信 (Queue)")
    print("=" * 50)

    queue = Queue()

    p1 = Process(target=producer, args=(queue, 5))
    p2 = Process(target=consumer, args=(queue,))

    p1.start()
    p2.start()

    p1.join()
    p2.join()
    print()


# ── 3. 进程池 ──

def heavy_compute(n):
    """CPU 密集型计算"""
    total = 0
    for i in range(n):
        total += i * i
    return total


def demo_pool():
    """演示进程池"""
    print("=" * 50)
    print("3. 进程池 (Pool)")
    print("=" * 50)

    numbers = [500000] * 4

    # 串行
    start = time.time()
    results_serial = [heavy_compute(n) for n in numbers]
    serial_time = time.time() - start
    print(f"串行耗时: {serial_time:.2f}s")

    # 进程池
    start = time.time()
    with Pool(processes=4) as pool:
        results_parallel = pool.map(heavy_compute, numbers)
    parallel_time = time.time() - start
    print(f"进程池耗时: {parallel_time:.2f}s")

    print(f"加速比: {serial_time / parallel_time:.1f}x")
    print(f"结果一致: {results_serial == results_parallel}")
    print()


# ── 4. 共享内存 ──

def increment_shared(counter, n):
    """在共享计数器上递增"""
    for _ in range(n):
        with counter.get_lock():
            counter.value += 1


def demo_shared_memory():
    """演示共享内存"""
    print("=" * 50)
    print("4. 共享内存 (Value)")
    print("=" * 50)

    counter = Value('i', 0)  # 共享整数
    n = 100000

    processes = []
    for _ in range(4):
        p = Process(target=increment_shared, args=(counter, n))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    print(f"共享计数器: {counter.value} (期望: {n * 4})")
    print()


# ── 5. Manager 共享复杂对象 ──

def worker_append(shared_list, shared_dict, worker_id):
    """向共享列表和字典添加数据"""
    for i in range(3):
        shared_list.append(f"worker-{worker_id}-item-{i}")
        shared_dict[f"worker-{worker_id}-{i}"] = time.time()


def demo_manager():
    """演示 Manager 共享复杂对象"""
    print("=" * 50)
    print("5. Manager 共享复杂对象")
    print("=" * 50)

    with Manager() as manager:
        shared_list = manager.list()
        shared_dict = manager.dict()

        processes = []
        for i in range(3):
            p = Process(target=worker_append, args=(shared_list, shared_dict, i))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        print(f"共享列表长度: {len(shared_list)} (期望: 9)")
        print(f"共享字典长度: {len(shared_dict)} (期望: 9)")
        print(f"列表内容: {list(shared_list)[:5]}...")
    print()


if __name__ == "__main__":
    demo_basic_process()
    demo_queue()
    demo_pool()
    demo_shared_memory()
    demo_manager()
    print("✅ 所有进程示例执行完毕")
