#!/usr/bin/env python3
"""
Day 055 - 进程基础：multiprocessing.Process 基本用法

演示内容：
1. 创建和启动子进程
2. 获取进程 PID
3. daemon 守护进程
4. 进程退出码
"""

import multiprocessing as mp
import time
import os


# ============================================================
# 示例 1：最简单的子进程
# ============================================================

def worker_basic(name):
    """子进程执行的函数"""
    pid = mp.current_process().pid
    ppid = os.getppid()
    print(f"  🔵 子进程 [{name}] 启动 | PID={pid}, 父PID={ppid}")
    time.sleep(1)
    print(f"  🔵 子进程 [{name}] 完成")


def example_1_basic():
    """创建一个子进程并等待它完成"""
    print("=" * 60)
    print("示例 1：创建子进程")
    print("=" * 60)
    
    print(f"🟢 主进程启动 | PID={os.getpid()}")
    
    p = mp.Process(target=worker_basic, args=("A",))
    p.start()   # 启动子进程（非阻塞）
    print(f"  主进程: 子进程已启动, PID={p.pid}")
    
    p.join()    # 等待子进程结束（阻塞）
    print(f"  主进程: 子进程退出码={p.exitcode}")
    
    print(f"🟢 主进程结束\n")


# ============================================================
# 示例 2：多个子进程并行
# ============================================================

def worker_parallel(task_id):
    """模拟耗时任务"""
    pid = mp.current_process().pid
    print(f"  🔵 任务 {task_id} 开始 (PID={pid})")
    time.sleep(0.5)  # 模拟工作
    print(f"  🔵 任务 {task_id} 完成 (PID={pid})")
    return task_id


def example_2_parallel():
    """启动多个子进程并行执行"""
    print("=" * 60)
    print("示例 2：多进程并行执行")
    print("=" * 60)
    
    start = time.perf_counter()
    
    processes = []
    for i in range(4):
        p = mp.Process(target=worker_parallel, args=(i,))
        processes.append(p)
        p.start()
    
    # 等待所有子进程完成
    for p in processes:
        p.join()
    
    elapsed = time.perf_counter() - start
    print(f"  ⏱️  4 个任务并行耗时: {elapsed:.2f}s (理想值约 0.5s)\n")


# ============================================================
# 示例 3：daemon 守护进程
# ============================================================

def worker_daemon():
    """守护进程：主进程退出时自动终止"""
    while True:
        print(f"  🔵 守护进程运行中 (PID={os.getpid()})")
        time.sleep(1)


def example_3_daemon():
    """守护进程在主进程退出时自动终止"""
    print("=" * 60)
    print("示例 3：daemon 守护进程")
    print("=" * 60)
    
    p = mp.Process(target=worker_daemon, daemon=True)
    p.start()
    
    time.sleep(2.5)
    print("  🟢 主进程即将退出（守护进程会被自动终止）")
    # 主进程退出时，守护进程自动终止，无需 join
    # 如果不设 daemon=True，join() 会永远阻塞


# ============================================================
# 示例 4：进程退出码与异常
# ============================================================

def worker_success():
    """正常退出"""
    print("  🔵 工作进程: 正常完成")
    return 42


def worker_error():
    """异常退出"""
    raise ValueError("模拟错误！")


def example_4_exitcode():
    """通过 exitcode 判断子进程状态"""
    print("=" * 60)
    print("示例 4：进程退出码")
    print("=" * 60)
    
    # 正常退出
    p1 = mp.Process(target=worker_success)
    p1.start()
    p1.join()
    print(f"  正常进程 exitcode={p1.exitcode} (0=正常)")
    
    # 异常退出
    p2 = mp.Process(target=worker_error)
    p2.start()
    p2.join()
    print(f"  异常进程 exitcode={p2.exitcode} (非0=异常)")
    
    # 被终止
    p3 = mp.Process(target=worker_daemon)
    p3.start()
    time.sleep(0.1)
    p3.terminate()
    p3.join()
    print(f"  被终止进程 exitcode={p3.exitcode} (负数=被信号终止)")
    print()


# ============================================================
# 主函数
# ============================================================

if __name__ == '__main__':
    print(f"🐍 Python 进程基础示例")
    print(f"   CPU 核心数: {mp.cpu_count()}")
    print()
    
    example_1_basic()
    example_2_parallel()
    example_3_daemon()
    example_4_exitcode()
    
    print("✅ 所有示例运行完毕")
