"""
Day 054 — 线程安全与锁
演示竞态条件、死锁以及各种同步原语的使用
"""

import threading
import time
import random
from collections import deque


# ============================================================
# 1. 竞态条件演示 — 没有锁的后果
# ============================================================

print("=== 竞态条件演示 ===")

counter_unsafe = 0
counter_safe = 0
lock = threading.Lock()


def increment_unsafe():
    global counter_unsafe
    for _ in range(100_000):
        counter_unsafe += 1  # 不安全：读-改-写不是原子操作


def increment_safe():
    global counter_safe
    for _ in range(100_000):
        with lock:
            counter_safe += 1  # 安全：加锁保护


t_unsafe_1 = threading.Thread(target=increment_unsafe)
t_unsafe_2 = threading.Thread(target=increment_unsafe)
t_safe_1 = threading.Thread(target=increment_safe)
t_safe_2 = threading.Thread(target=increment_safe)

# 无锁版本
t_unsafe_1.start(); t_unsafe_2.start()
t_unsafe_1.join(); t_unsafe_2.join()
print(f"  无锁: 期望 200000, 实际 {counter_unsafe}")

# 有锁版本
t_safe_1.start(); t_safe_2.start()
t_safe_1.join(); t_safe_2.join()
print(f"  有锁: 期望 200000, 实际 {counter_safe}")
print()


# ============================================================
# 2. 信号量 — 限制并发数量
# ============================================================

print("=== 信号量 (Semaphore) — 限制并发数 ===")

semaphore = threading.Semaphore(2)  # 最多 2 个线程同时执行
active_count = 0
active_lock = threading.Lock()


def limited_task(name):
    global active_count
    with semaphore:
        with active_lock:
            active_count += 1
            print(f"  {name} 进入 (当前并发: {active_count})")
        
        time.sleep(random.uniform(0.1, 0.3))
        
        with active_lock:
            active_count -= 1
            print(f"  {name} 离开 (当前并发: {active_count})")


threads = [threading.Thread(target=limited_task, args=(f"T{i}",)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()
print()


# ============================================================
# 3. 条件变量 — 生产者-消费者模式
# ============================================================

print("=== 条件变量 (Condition) — 生产者-消费者 ===")

buffer = deque()
condition = threading.Condition()
BUFFER_SIZE = 3
produced = 0
consumed = 0


def producer(name):
    global produced
    for i in range(4):
        with condition:
            # 缓冲区满时等待
            while len(buffer) >= BUFFER_SIZE:
                print(f"  {name}: 缓冲区已满，等待...")
                condition.wait()
            
            item = f"产品-{i}"
            buffer.append(item)
            produced += 1
            print(f"  {name}: 生产了 {item} (缓冲区: {len(buffer)}/{BUFFER_SIZE})")
            condition.notify()
        
        time.sleep(random.uniform(0.05, 0.15))


def consumer(name):
    global consumed
    for i in range(4):
        with condition:
            # 缓冲区空时等待
            while not buffer:
                print(f"  {name}: 缓冲区为空，等待...")
                condition.wait()
            
            item = buffer.popleft()
            consumed += 1
            print(f"  {name}: 消费了 {item} (缓冲区: {len(buffer)}/{BUFFER_SIZE})")
            condition.notify()
        
        time.sleep(random.uniform(0.05, 0.15))


p = threading.Thread(target=producer, args=("生产者",))
c = threading.Thread(target=consumer, args=("消费者",))
p.start(); c.start()
p.join(); c.join()
print(f"  生产: {produced}, 消费: {consumed}\n")


# ============================================================
# 4. 事件 (Event) — 线程间信号通知
# ============================================================

print("=== 事件 (Event) — 一次性信号 ===")

event = threading.Event()


def waiter_thread(name):
    print(f"  {name}: 等待信号...")
    event.wait()
    print(f"  {name}: 收到信号！开始工作")


def signaler_thread():
    time.sleep(0.5)
    print("  [信号发送者]: 发送信号！")
    event.set()


waiters = [threading.Thread(target=waiter_thread, args=(f"W{i}",)) for i in range(3)]
signaler = threading.Thread(target=signaler_thread)

for w in waiters: w.start()
signaler.start()
for w in waiters: w.join()
signaler.join()
print()


# ============================================================
# 5. 死锁演示与避免
# ============================================================

print("=== 死锁演示 ===")

lock_x = threading.Lock()
lock_y = threading.Lock()


def deadlock_risk_a():
    """危险：先获取 lock_x，再获取 lock_y"""
    with lock_x:
        time.sleep(0.01)  # 给另一个线程机会
        with lock_y:
            print("  任务 A 完成")


def deadlock_risk_b():
    """危险：先获取 lock_y，再获取 lock_x"""
    with lock_y:
        time.sleep(0.01)
        with lock_x:
            print("  任务 B 完成")


# 注意：这段代码可能死锁！
# 在实际使用中，应该始终以相同顺序获取锁
# 这里加了超时来避免无限等待

def safe_with_timeout(lock, timeout=0.5):
    """尝试获取锁，超时返回 False"""
    return lock.acquire(timeout=timeout)


def safe_task_a():
    if safe_with_timeout(lock_x):
        try:
            time.sleep(0.001)
            if safe_with_timeout(lock_y):
                try:
                    print("  任务 A 完成（安全）")
                finally:
                    lock_y.release()
            else:
                print("  任务 A: 获取 lock_y 超时")
        finally:
            lock_x.release()


def safe_task_b():
    # 以相同顺序获取锁：先 x 后 y
    if safe_with_timeout(lock_x):
        try:
            if safe_with_timeout(lock_y):
                try:
                    print("  任务 B 完成（安全）")
                finally:
                    lock_y.release()
            else:
                print("  任务 B: 获取 lock_y 超时")
        finally:
            lock_x.release()


t_a = threading.Thread(target=safe_task_a)
t_b = threading.Thread(target=safe_task_b)
t_a.start(); t_b.start()
t_a.join(); t_b.join()
print("  死锁避免策略演示完成\n")


# ============================================================
# 6. 线程安全的计数器（封装）
# ============================================================

print("=== 线程安全的计数器 ===")


class ThreadSafeCounter:
    """线程安全的计数器"""
    
    def __init__(self, initial=0):
        self._value = initial
        self._lock = threading.Lock()
    
    def increment(self, amount=1):
        with self._lock:
            self._value += amount
    
    def decrement(self, amount=1):
        with self._lock:
            self._value -= amount
    
    @property
    def value(self):
        with self._lock:
            return self._value


counter = ThreadSafeCounter()


def bump():
    for _ in range(50_000):
        counter.increment()


threads = [threading.Thread(target=bump) for _ in range(4)]
for t in threads: t.start()
for t in threads: t.join()
print(f"  期望: 200000, 实际: {counter.value}")
