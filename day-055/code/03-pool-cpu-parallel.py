#!/usr/bin/env python3
"""
Day 055 - 实战：进程池加速 CPU 密集型任务

演示内容：
1. Pool.map 基础用法
2. Pool.apply_async 异步提交
3. 多种 Pool 方法对比
4. 实战：素数计数加速
5. 实战：并行数据处理流水线
"""

import multiprocessing as mp
import time
import math
import os


# ============================================================
# 示例 1：Pool.map 基础用法
# ============================================================

def square(n):
    """计算平方"""
    pid = mp.current_process().pid
    time.sleep(0.1)  # 模拟耗时
    return {"input": n, "output": n ** 2, "pid": pid}


def example_1_pool_map():
    """Pool.map 基本用法"""
    print("=" * 60)
    print("示例 1：Pool.map 基础用法")
    print("=" * 60)
    
    numbers = list(range(10))
    
    start = time.perf_counter()
    with mp.Pool(processes=4) as pool:
        results = pool.map(square, numbers)
    elapsed = time.perf_counter() - start
    
    # 统计各进程处理数量
    pid_counts = {}
    for r in results:
        pid = r["pid"]
        pid_counts[pid] = pid_counts.get(pid, 0) + 1
    
    print(f"  输入: {numbers}")
    print(f"  输出: {[r['output'] for r in results]}")
    print(f"  耗时: {elapsed:.2f}s")
    print(f"  使用进程:")
    for pid, count in sorted(pid_counts.items()):
        print(f"    PID {pid}: 处理 {count} 个任务")
    print()


# ============================================================
# 示例 2：Pool.apply_async 异步提交
# ============================================================

def heavy_task(seconds):
    """模拟耗时任务"""
    time.sleep(seconds)
    return {"pid": mp.current_process().pid, "slept": seconds}


def example_2_apply_async():
    """apply_async 异步提交单个任务"""
    print("=" * 60)
    print("示例 2：Pool.apply_async 异步提交")
    print("=" * 60)
    
    with mp.Pool(3) as pool:
        # 异步提交多个任务
        results = []
        for i, secs in enumerate([1, 0.5, 1.5, 0.8, 1.2]):
            r = pool.apply_async(heavy_task, args=(secs,))
            results.append((i, r))
        
        # 收集结果
        for idx, r in results:
            value = r.get()
            print(f"  任务{idx}: pid={value['pid']}, 耗时={value['slept']}s")
    
    print()


# ============================================================
# 示例 3：Pool 方法对比
# ============================================================

def process_item(item):
    """演示用：处理单个元素"""
    time.sleep(0.1)
    return item * 10


def example_3_pool_methods():
    """对比 map / imap / imap_unordered"""
    print("=" * 60)
    print("示例 3：Pool 方法对比")
    print("=" * 60)
    
    items = [1, 2, 3, 4, 5]
    
    with mp.Pool(3) as pool:
        # map - 同步，阻塞，保序
        start = time.perf_counter()
        result_map = pool.map(process_item, items)
        t_map = time.perf_counter() - start
        print(f"  map 结果: {result_map} ({t_map:.2f}s)")
        
        # imap - 惰性，保序
        start = time.perf_counter()
        result_imap = list(pool.imap(process_item, items))
        t_imap = time.perf_counter() - start
        print(f"  imap 结果: {result_imap} ({t_imap:.2f}s)")
        
        # imap_unordered - 惰性，不保序
        start = time.perf_counter()
        result_imap_u = list(pool.imap_unordered(process_item, items))
        t_imap_u = time.perf_counter() - start
        print(f"  imap_unordered 结果: {result_imap_u} ({t_imap_u:.2f}s)")
    
    print()


# ============================================================
# 示例 4：实战 — 素数计数加速
# ============================================================

def is_prime(n):
    """高效素数判断"""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def count_primes(args):
    """计算范围内的素数个数"""
    start, end = args
    return sum(1 for n in range(start, end) if is_prime(n))


def example_4_prime_counting():
    """多进程加速素数计算"""
    print("=" * 60)
    print("示例 4：多进程素数计数加速")
    print("=" * 60)
    
    total = 2_000_000
    num_workers = mp.cpu_count()
    chunk_size = total // num_workers
    ranges = [
        (i * chunk_size, min((i + 1) * chunk_size, total))
        for i in range(num_workers)
    ]
    
    # 单进程
    start = time.perf_counter()
    single_count = sum(1 for n in range(total) if is_prime(n))
    single_time = time.perf_counter() - start
    
    # 多进程
    start = time.perf_counter()
    with mp.Pool(num_workers) as pool:
        results = pool.map(count_primes, ranges)
    multi_count = sum(results)
    multi_time = time.perf_counter() - start
    
    print(f"  范围: 0 ~ {total:,}")
    print(f"  CPU 核心数: {num_workers}")
    print(f"  单进程: {single_count:,} 个素数, {single_time:.2f}s")
    print(f"  多进程: {multi_count:,} 个素数, {multi_time:.2f}s")
    print(f"  加速比: {single_time / multi_time:.2f}x")
    print()


# ============================================================
# 示例 5：实战 — 并行数据处理流水线
# ============================================================

def read_chunk(args):
    """模拟读取数据块"""
    chunk_id, chunk_size = args
    time.sleep(0.1)
    return {"chunk_id": chunk_id, "data": list(range(chunk_id * chunk_size, (chunk_id + 1) * chunk_size))}


def transform_chunk(data):
    """模拟数据转换（CPU 密集）"""
    result = []
    for x in data["data"]:
        # 模拟复杂计算
        val = sum(i * i for i in range(min(x + 1, 1000)))
        result.append(val)
    return {"chunk_id": data["chunk_id"], "transformed": result, "pid": mp.current_process().pid}


def example_5_pipeline():
    """多进程数据处理流水线"""
    print("=" * 60)
    print("示例 5：并行数据处理流水线")
    print("=" * 60)
    
    num_chunks = 8
    chunk_size = 100
    
    start = time.perf_counter()
    
    with mp.Pool(4) as pool:
        # 第一阶段：并行读取数据
        chunks = pool.map(read_chunk, [(i, chunk_size) for i in range(num_chunks)])
        
        # 第二阶段：并行转换数据
        transformed = pool.map(transform_chunk, chunks)
    
    elapsed = time.perf_counter() - start
    
    total_records = sum(len(t["transformed"]) for t in transformed)
    pids_used = set(t["pid"] for t in transformed)
    
    print(f"  处理了 {num_chunks} 个数据块, 共 {total_records} 条记录")
    print(f"  使用进程: {len(pids_used)} 个")
    print(f"  总耗时: {elapsed:.2f}s")
    print()


# ============================================================
# 主函数
# ============================================================

if __name__ == '__main__':
    print(f"🐍 Python 进程池实战示例")
    print(f"   CPU 核心数: {mp.cpu_count()}")
    print()
    
    example_1_pool_map()
    example_2_apply_async()
    example_3_pool_methods()
    example_4_prime_counting()
    example_5_pipeline()
    
    print("✅ 所有进程池示例运行完毕")
