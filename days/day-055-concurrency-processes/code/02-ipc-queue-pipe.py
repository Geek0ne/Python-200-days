#!/usr/bin/env python3
"""
Day 055 - 进程间通信：Queue 和 Pipe

演示内容：
1. Queue 实现生产者-消费者模式
2. Pipe 实现点对点通信
3. 多生产者多消费者
4. 进程间传递复杂对象
"""

import multiprocessing as mp
import time
import os


# ============================================================
# 示例 1：Queue 基础 — 生产者-消费者
# ============================================================

def producer(queue, producer_id, count):
    """生产者：往队列里放数据"""
    for i in range(count):
        item = f"生产者{producer_id}-产品{i}"
        queue.put(item)
        print(f"  📦 {item}")
        time.sleep(0.1)  # 模拟生产耗时
    
    # 发送结束信号（哨兵值）
    queue.put(None)
    print(f"  📦 生产者{producer_id} 完成")


def consumer(queue, consumer_id):
    """消费者：从队列取数据"""
    while True:
        item = queue.get()
        if item is None:
            print(f"  📥 消费者{consumer_id} 收到结束信号")
            break
        print(f"  📥 消费者{consumer_id} 消费: {item}")
        time.sleep(0.2)  # 模拟处理耗时


def example_1_queue_basic():
    """基础 Queue 生产者-消费者"""
    print("=" * 60)
    print("示例 1：Queue 基础 — 单生产者单消费者")
    print("=" * 60)
    
    queue = mp.Queue()
    
    p = mp.Process(target=producer, args=(queue, 1, 5))
    c = mp.Process(target=consumer, args=(queue, 1))
    
    p.start()
    c.start()
    p.join()
    c.join()
    print()


# ============================================================
# 示例 2：多生产者多消费者
# ============================================================

def multi_producer(queue, producer_id, count):
    """多个生产者"""
    for i in range(count):
        item = f"P{producer_id}-Item{i}"
        queue.put(item)
        time.sleep(0.05)
    queue.put(None)  # 每个生产者发一个结束信号


def multi_consumer(queue, consumer_id, done_event):
    """多个消费者，通过 Event 判断是否全部结束"""
    while not done_event.is_set():
        try:
            item = queue.get(timeout=0.5)
            print(f"  📥 消费者{consumer_id}: {item}")
        except Exception:
            continue


def example_2_multi_producer_consumer():
    """多生产者多消费者"""
    print("=" * 60)
    print("示例 2：多生产者多消费者")
    print("=" * 60)
    
    queue = mp.Queue()
    done_event = mp.Event()
    
    num_producers = 3
    num_consumers = 2
    items_per_producer = 4
    
    # 启动生产者
    producers = []
    for i in range(num_producers):
        p = mp.Process(target=multi_producer, args=(queue, i, items_per_producer))
        producers.append(p)
        p.start()
    
    # 启动消费者
    consumers = []
    for i in range(num_consumers):
        c = mp.Process(target=multi_consumer, args=(queue, i, done_event))
        consumers.append(c)
        c.start()
    
    # 等待所有生产者完成
    for p in producers:
        p.join()
    
    # 通知消费者可以退出
    done_event.set()
    
    for c in consumers:
        c.join()
    
    print(f"  ✅ 总共生产 {num_producers * items_per_producer} 个产品\n")


# ============================================================
# 示例 3：Pipe 点对点通信
# ============================================================

def pipe_sender(conn):
    """通过管道发送数据"""
    messages = [
        {"type": "text", "content": "你好，我是子进程！"},
        {"type": "number", "content": 42},
        {"type": "list", "content": [1, 2, 3, 4, 5]},
    ]
    
    for msg in messages:
        conn.send(msg)
        print(f"  📤 发送: {msg}")
    
    conn.send(None)  # 结束信号
    conn.close()


def pipe_receiver(conn):
    """通过管道接收数据"""
    while True:
        data = conn.recv()
        if data is None:
            print(f"  📥 接收到结束信号")
            break
        print(f"  📥 接收: {data}")
    conn.close()


def example_3_pipe():
    """Pipe 点对点双向通信"""
    print("=" * 60)
    print("示例 3：Pipe 点对点通信")
    print("=" * 60)
    
    parent_conn, child_conn = mp.Pipe()
    
    sender = mp.Process(target=pipe_sender, args=(child_conn,))
    receiver = mp.Process(target=pipe_receiver, args=(parent_conn,))
    
    sender.start()
    receiver.start()
    
    # 父进程关闭子进程端的连接
    child_conn.close()
    
    sender.join()
    receiver.join()
    print()


# ============================================================
# 示例 4：Queue 传递复杂对象
# ============================================================

def complex_producer(queue):
    """发送复杂 Python 对象"""
    import json
    
    objects = [
        {"users": [{"name": "Alice", "scores": [90, 85, 92]},
                    {"name": "Bob", "scores": [78, 88, 95]}],
         "class": "Python 101"},
        [1, 2, 3, {"nested": True}],
        tuple(range(10)),
    ]
    
    for obj in objects:
        queue.put(obj)
        print(f"  📤 发送对象类型: {type(obj).__name__}")
    
    queue.put(None)


def complex_consumer(queue):
    """接收并处理复杂对象"""
    while True:
        obj = queue.get()
        if obj is None:
            break
        print(f"  📥 接收对象类型: {type(obj).__name__}, 内容: {obj}")


def example_4_complex_objects():
    """进程间传递复杂 Python 对象"""
    print("=" * 60)
    print("示例 4：传递复杂对象")
    print("=" * 60)
    
    queue = mp.Queue()
    
    p1 = mp.Process(target=complex_producer, args=(queue,))
    p2 = mp.Process(target=complex_consumer, args=(queue,))
    
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    print()


# ============================================================
# 示例 5：Queue 超时与非阻塞
# ============================================================

def example_5_queue_timeout():
    """Queue 的超时和非阻塞操作"""
    print("=" * 60)
    print("示例 5：Queue 超时与非阻塞")
    print("=" * 60)
    
    queue = mp.Queue(maxsize=3)
    
    # 放入数据
    for i in range(3):
        queue.put(f"item-{i}")
    
    # 检查队列状态
    print(f"  qsize: {queue.qsize()}")
    print(f"  empty: {queue.empty()}")
    print(f"  full: {queue.full()}")
    
    # 非阻塞取出
    item = queue.get_nowait()
    print(f"  get_nowait: {item}")
    
    # 阻塞取出（带超时）
    try:
        item = queue.get(timeout=1)
        print(f"  get(timeout=1): {item}")
    except Exception as e:
        print(f"  超时: {e}")
    
    # 非阻塞放入（队列满时）
    queue.put("extra-1")
    queue.put("extra-2")
    try:
        queue.put_nowait("overflow")
    except Exception as e:
        print(f"  put_nowait 满: {type(e).__name__}")
    
    print()


# ============================================================
# 主函数
# ============================================================

if __name__ == '__main__':
    print(f"🐍 Python 进程间通信示例")
    print()
    
    example_1_queue_basic()
    example_2_multi_producer_consumer()
    example_3_pipe()
    example_4_complex_objects()
    example_5_queue_timeout()
    
    print("✅ 所有 IPC 示例运行完毕")
