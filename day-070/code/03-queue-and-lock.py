"""
Day 070 — 任务队列与分布式锁
运行方式：
  python 03-queue-and-lock.py --self-test   # MiniRedis 离线自检
  python 03-queue-and-lock.py               # 真实 Redis 环境
"""
import sys
import threading
import time
import uuid


class MiniRedis:
    """list 队列 + SET NX EX 锁的内存模拟（阻塞版 brpop 用轮询近似）"""

    def __init__(self):
        self.lst = {}
        self.kv = {}
        self.lock = threading.Lock()

    def lpush(self, k, v):
        with self.lock:
            self.lst.setdefault(k, []).insert(0, str(v))
            return len(self.lst[k])

    def brpop(self, k, timeout=1):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self.lock:
                data = self.lst.get(k, [])
                if data:
                    return (k, data.pop())
            time.sleep(0.005)
        return None

    def set(self, k, v, nx=False, ex=None):
        with self.lock:
            if nx:
                item = self.kv.get(k)
                if item is not None:
                    _, expire = item
                    if expire is None or time.time() < expire:
                        return False   # 过期的锁不挡路
            self.kv[k] = (str(v), time.time() + ex if ex is not None else None)
            return True

    def get(self, k):
        with self.lock:
            item = self.kv.get(k)
            if item is None:
                return None
            v, expire = item
            if expire and time.time() >= expire:
                self.kv.pop(k, None)
                return None
            return v

    def eval(self, script, numkeys, key, token):
        # 仅实现 README 中的 compare-and-del 锁释放脚本语义
        with self.lock:
            item = self.kv.get(key)
            if item and item[0] == str(token):
                self.kv.pop(key, None)
                return 1
            return 0


def connect():
    try:
        import redis
        return redis.Redis(host="127.0.0.1", decode_responses=True)
    except ImportError:
        return MiniRedis()


# ========== 任务队列 ==========

def produce(r, queue_name, tasks):
    for t in tasks:
        r.lpush(queue_name, t)


def consume(r, queue_name, results, timeout=1):
    got = r.brpop(queue_name, timeout=timeout)
    if got:
        results.append(got[1])


# ========== 分布式锁 ==========

RELEASE_SCRIPT = ('if redis.call("get", KEYS[1]) == ARGV[1] '
                  'then return redis.call("del", KEYS[1]) end')


def acquire_lock(r, name, ttl=10):
    token = uuid.uuid4().hex
    ok = r.set(f"lock:{name}", token, nx=True, ex=ttl)
    return token if ok else None


def release_lock(r, name, token):
    return r.eval(RELEASE_SCRIPT, 1, f"lock:{name}", token)


def self_test():
    r = MiniRedis()

    # 队列：FIFO（lpush 头插 + brpop 尾取）
    produce(r, "tasks", ["t1", "t2", "t3"])
    results = []
    consume(r, "tasks", results)
    consume(r, "tasks", results)
    assert results == ["t1", "t2"], f"FIFO 语义错误: {results}"
    consume(r, "tasks", results)   # 清掉剩余的 t3

    # 并发消费：3 个 worker 抢 10 个任务，不重不漏
    produce(r, "tasks", [f"job{i}" for i in range(10)])
    got = []
    lock = threading.Lock()

    def worker():
        while True:
            item = r.brpop("tasks", timeout=0.2)
            if item is None:
                return
            with lock:
                got.append(item[1])

    threads = [threading.Thread(target=worker) for _ in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(got) == sorted(f"job{i}" for i in range(10)), f"不重不漏被打破: {got}"

    # 锁：互斥
    t1 = acquire_lock(r, "demo")
    t2 = acquire_lock(r, "demo")
    assert t1 is not None and t2 is None, "第二把锁必须失败"
    assert release_lock(r, "demo", t1) == 1, "释放自己的锁应成功"

    # 锁：token 校验，删不掉别人的锁
    t3 = acquire_lock(r, "demo")
    assert release_lock(r, "demo", "wrong-token") == 0, "不能删别人的锁"
    assert r.get("lock:demo") == t3, "锁应还在"
    release_lock(r, "demo", t3)

    # 锁：TTL 自动过期（防死锁）
    t4 = acquire_lock(r, "ttl-demo", ttl=0)
    time.sleep(0.01)
    assert acquire_lock(r, "ttl-demo", ttl=1) is not None, "过期后应可重新加锁"

    print("✅ self-test 全部通过")


def demo(r):
    produce(r, "tasks", ["send-email:alice", "send-email:bob"])
    results = []
    consume(r, "tasks", results)
    print("消费到:", results)

    token = acquire_lock(r, "nightly-report")
    print("加锁成功:", bool(token))
    print("释放:", release_lock(r, "nightly-report", token) in (1, True))


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        demo(connect())
