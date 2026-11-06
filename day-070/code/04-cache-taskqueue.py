"""
Day 070 — 实战：缓存加速 + 任务队列（数据管道）
运行方式：
  python 04-cache-taskqueue.py --self-test   # MiniRedis 离线跑全流程
  python 04-cache-taskqueue.py               # 真实 Redis 环境
"""
import json
import sys
import threading
import time


class MiniRedis:
    def __init__(self):
        self.kv, self.lst = {}, {}
        self.lock = threading.Lock()

    def get(self, k):
        with self.lock:
            return self.kv.get(k)

    def setex(self, k, ttl, v):
        with self.lock:
            self.kv[k] = str(v)

    def setnx(self, k, v):
        with self.lock:
            if k in self.kv:
                return False
            self.kv[k] = str(v)
            return True

    def delete(self, k):
        with self.lock:
            self.kv.pop(k, None)

    def lpush(self, k, v):
        with self.lock:
            self.lst.setdefault(k, []).insert(0, str(v))

    def brpop(self, k, timeout=1):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self.lock:
                data = self.lst.get(k, [])
                if data:
                    return (k, data.pop())
            time.sleep(0.005)
        return None


def connect():
    try:
        import redis
        return redis.Redis(host="127.0.0.1", decode_responses=True)
    except ImportError:
        return MiniRedis()


# ========== 1. 慢查询模拟：报表聚合 ==========

SALES = {"2026-10": [120, 340, 89, 450], "2026-11": [230, 110, 560]}


def slow_report(month):
    time.sleep(0.005)   # 真实场景这里可能是几十毫秒的聚合查询
    values = SALES.get(month, [])
    return {"month": month, "total": sum(values), "count": len(values)}


# ========== 2. Cache-Aside 包一层 ==========

REPORT_KEY = "report:{month}"


def get_report_cached(r, month):
    key = REPORT_KEY.format(month=month)
    cached = r.get(key)
    if cached:
        return json.loads(cached)
    report = slow_report(month)
    r.setex(key, 300, json.dumps(report))
    return report


# ========== 3. 数据变更 → 失效任务 → worker 重建 ==========

def on_sales_updated(r, month):
    """写路径：数据变了，删缓存 + 发失效任务（删除式失效）"""
    r.delete(REPORT_KEY.format(month=month))
    r.lpush("tasks:invalidate", json.dumps({"key": REPORT_KEY.format(month=month)}))


def worker_loop(r, processed, n_expected, timeout=1):
    """消费失效任务：幂等重建缓存（SET NX 做防重放）"""
    while len(processed) < n_expected:
        got = r.brpop("tasks:invalidate", timeout=timeout)
        if got is None:
            return
        task = json.loads(got[1])
        key = task["key"]
        guard = f"rebuilding:{key}"
        if not r.setnx(guard, "1"):     # 同一任务并发投递时只处理一次
            continue
        r.delete(key)                    # 删掉旧缓存，下次读自动回填
        processed.append(key)
        r.delete(guard)


def self_test():
    r = connect()

    # 冷 → 热：第二次走缓存
    rep = get_report_cached(r, "2026-10")
    assert rep["total"] == 999, rep
    assert r.get(REPORT_KEY.format(month="2026-10")), "应已回填缓存"

    # 变更：删缓存 + 发任务
    on_sales_updated(r, "2026-10")
    assert r.get(REPORT_KEY.format(month="2026-10")) is None, "缓存应已删除"

    # worker 消费重建
    processed = []
    worker_loop(r, processed, n_expected=1)
    assert processed == ["report:2026-10"], processed

    # 幂等：同一任务重复投递只处理一次
    r.lpush("tasks:invalidate", json.dumps({"key": "report:2026-10"}))
    r.lpush("tasks:invalidate", json.dumps({"key": "report:2026-10"}))
    processed2 = []
    t = threading.Thread(target=worker_loop, args=(r, processed2, 1))
    t.start(); t.join()
    assert len(processed2) == 1, f"防重放失效: {processed2}"

    print("✅ self-test 全部通过（缓存加速 → 变更失效 → 幂等重建）")


def demo(r):
    t0 = time.perf_counter(); get_report_cached(r, "2026-11"); t_cold = time.perf_counter() - t0
    t0 = time.perf_counter(); get_report_cached(r, "2026-11"); t_hot = time.perf_counter() - t0
    print(f"冷查询 {t_cold * 1000:.1f}ms → 热查询 {t_hot * 1000:.1f}ms")
    on_sales_updated(r, "2026-11")
    processed = []
    worker_loop(r, processed, 1)
    print("worker 处理:", processed)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        demo(connect())
