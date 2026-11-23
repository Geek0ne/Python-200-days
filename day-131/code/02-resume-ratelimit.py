# -*- coding: utf-8 -*-
"""
Day 131 - 爬虫策略进阶：断点续爬 + 令牌桶限速 + 指数退避
==========================================================
运行：python 02-resume-ratelimit.py
（限速/退避演示纯本地模拟，不发真实请求；断点续爬逻辑可直接套用到真实爬虫）

核心思想：
- 断点续爬 = 把"队列 + 已访问集合"定期原子落盘，重启时恢复
- 令牌桶   = 平均速率受限，允许短时突发（比死板 sleep 更高效自然）
- 指数退避 = 失败后间隔翻倍重试，绝不硬撞
"""
import json
import os
import time


# ===============================================================
# 1. 断点续爬：原子写 checkpoint + 恢复
# ===============================================================
class Checkpoint:
    """
    ⚠️ 避坑：直接 open(path, 'w') 写 checkpoint，写一半进程崩了
    -> 文件损坏 -> 恢复失败 -> 全部进度丢失。
    正确姿势：写临时文件，再 os.replace() 原子替换（同分区 rename 是原子的）。
    """
    def __init__(self, path="checkpoint.json"):
        self.path = path
        self.data = {"queue": [], "visited": [], "item_count": 0}

    def save(self, queue, visited, item_count):
        self.data = {"queue": list(queue), "visited": list(visited),
                     "item_count": item_count}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False)
        os.replace(tmp, self.path)          # 原子替换！
        print(f"[checkpoint] 已保存: 队列 {len(queue)} | 已访问 {len(visited)} | 数据 {item_count} 条")

    def load(self):
        """存在则恢复，返回 True；不存在返回 False（全新开始）"""
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
            print(f"[checkpoint] 恢复成功: 从 {self.data['item_count']} 条数据处继续")
            return True
        print("[checkpoint] 无存档，全新开始")
        return False

    def clear(self):
        if os.path.exists(self.path):
            os.remove(self.path)


def demo_checkpoint():
    """模拟：跑一半"崩溃"，重启后接着跑"""
    cp = Checkpoint("demo_checkpoint.json")
    cp.clear()

    # ---- 第一次运行：处理到第 6 个 URL 时"崩溃" ----
    urls = [f"http://site.com/p{i}" for i in range(20)]
    queue, visited = list(urls), set()
    item_count = 0
    for i in range(6):
        url = queue.pop(0)
        visited.add(url)
        item_count += 1
    cp.save(queue, visited, item_count)      # 崩溃前恰好在最后一次保存成功
    print("[模拟] 进程崩溃!\n")

    # ---- 第二次运行：从 checkpoint 恢复 ----
    cp2 = Checkpoint("demo_checkpoint.json")
    if cp2.load():
        queue = cp2.data["queue"]
        visited = set(cp2.data["visited"])
        item_count = cp2.data["item_count"]
        # 继续处理剩余 URL
        while queue:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            item_count += 1
        print(f"[续爬完成] 总处理 {item_count} 条（应为 20，且无重复）")
    cp2.clear()


# ===============================================================
# 2. 令牌桶限速
# ===============================================================
class TokenBucket:
    """
    rate     = 每秒生成令牌数（平均速率上限）
    capacity = 桶容量（允许的最大突发量）
    例：rate=2, capacity=5 -> 空闲很久后可连发 5 个请求，
        之后平均每秒最多 2 个。比"每 0.5s 死等一次"吞吐更高、更像真人。
    """
    def __init__(self, rate=2.0, capacity=5):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last = time.monotonic()

    def acquire(self, n=1):
        """拿 n 个令牌；不够就睡到攒够为止"""
        while True:
            now = time.monotonic()
            # 按流逝时间补令牌（不超容量）
            self.tokens = min(self.capacity,
                              self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= n:
                self.tokens -= n
                return
            time.sleep((n - self.tokens) / self.rate)

    def try_acquire(self, n=1):
        """非阻塞版：拿不到立即返回 False（爬虫可先去做别的）"""
        now = time.monotonic()
        self.tokens = min(self.capacity,
                          self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


def demo_token_bucket():
    bucket = TokenBucket(rate=5.0, capacity=3)  # 平均 5 个/秒，最多突发 3 个
    t0 = time.monotonic()
    stamps = []
    for i in range(10):
        bucket.acquire()
        stamps.append(round(time.monotonic() - t0, 2))
    print("10 次请求时间点:", stamps)
    print("解读：前 3 个立即放行(突发)，之后约每 0.2s 一个(速率限制)")


# ===============================================================
# 3. 指数退避重试
# ===============================================================
def fetch_with_backoff(url, fetch, max_retries=5, base=1.0):
    """
    fetch: 传入的下载函数（返回 None 表示失败）
    429/5xx 时：等 base * 2**retry 秒再试，并尊重 Retry-After 头
    """
    for attempt in range(max_retries):
        result = fetch(url)
        if result is not None:
            return result
        delay = base * (2 ** attempt)      # 1, 2, 4, 8, 16...
        print(f"  第 {attempt+1} 次失败，退避 {delay}s 后重试")
        time.sleep(delay)
    print(f"  {url} 重试 {max_retries} 次仍失败，放弃并记录")
    return None


def demo_backoff():
    # 模拟一个前 3 次"挂掉"、第 4 次成功的接口（演示用，缩短等待时间）
    state = {"n": 0}
    def fake_fetch(url):
        state["n"] += 1
        return f"<html>{url}</html>" if state["n"] >= 3 else None

    r = fetch_with_backoff("http://site.com/x", fake_fetch,
                           max_retries=5, base=0.01)
    print("最终结果:", r)


def main():
    print("== 1. 断点续爬 ==")
    demo_checkpoint()
    print("\n== 2. 令牌桶限速 ==")
    demo_token_bucket()
    print("\n== 3. 指数退避 ==")
    demo_backoff()


if __name__ == "__main__":
    main()
