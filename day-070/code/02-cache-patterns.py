"""
Day 070 — 缓存模式：Cache-Aside / 穿透 / 击穿 / 雪崩
运行方式：
  python 02-cache-patterns.py --self-test   # MiniRedis 离线自检
  python 02-cache-patterns.py               # 真实 Redis 环境
"""
import json
import random
import sys
import time
import uuid


class MiniRedis:
    """带 TTL 的极简模拟（用逻辑时钟模拟过期）"""

    def __init__(self):
        self.kv = {}
        self.now = 0.0
        self.db_hits = 0  # 观测用：缓存未命中导致的回源次数

    def setex(self, k, ttl, v):
        self.kv[k] = (str(v), self.now + ttl)

    def setnx(self, k, v):
        if self._alive(k):
            return False
        self.kv[k] = (str(v), None)
        return True

    def get(self, k):
        return self._alive(k)

    def delete(self, k):
        self.kv.pop(k, None)

    def _alive(self, k):
        item = self.kv.get(k)
        if item is None:
            return None
        v, expire = item
        if expire is not None and self.now >= expire:
            self.kv.pop(k, None)
            return None
        return v


# ========== 模拟"数据库" ==========

DB = {"u1": {"name": "alice"}, "u2": {"name": "bob"}}   # u3 不存在


def query_db(user_id):
    time.sleep(0.001)  # 模拟回源开销
    if isinstance(MINIR, MiniRedis):
        MINIR.db_hits += 1
    return DB.get(user_id)


# ========== Cache-Aside ==========

def get_user_without_cache(user_id):
    return query_db(user_id)


def get_user_cache_aside(r, user_id, ttl=300):
    key = f"user:{user_id}"
    cached = r.get(key)
    if cached is not None:
        return None if cached == "null" else json.loads(cached)
    user = query_db(user_id)
    if user is None:
        r.setex(key, 60, "null")                              # 空值缓存 → 防穿透
    else:
        r.setex(key, ttl + random.randint(0, 60), json.dumps(user))  # TTL 抖动 → 防雪崩
    return user


def update_user(r, user_id, user):
    DB[user_id] = user
    r.delete(f"user:{user_id}")   # 删除式失效，而不是更新缓存


def self_test():
    global MINIR
    MINIR = r = MiniRedis()

    # 1. 未命中 → 回源 → 第二次命中
    assert get_user_cache_aside(r, "u1") == {"name": "alice"}
    assert MINIR.db_hits == 1
    assert get_user_cache_aside(r, "u1") == {"name": "alice"}
    assert MINIR.db_hits == 1, "第二次应命中缓存"

    # 2. 空值缓存防穿透：u3 不存在，连续查 5 次只回源 1 次
    hits_before = MINIR.db_hits
    for _ in range(5):
        assert get_user_cache_aside(r, "u3") is None
    assert MINIR.db_hits == hits_before + 1, f"穿透了: {MINIR.db_hits - hits_before} 次回源"

    # 3. 删除式失效：更新后能读到新值
    update_user(r, "u1", {"name": "alice-v2"})
    assert get_user_cache_aside(r, "u1") == {"name": "alice-v2"}

    # 4. TTL 抖动：100 个 key 的过期时间不应完全相同（防雪崩）
    ttls = set()
    for i in range(100):
        r2 = MiniRedis()
        get_user_cache_aside(r2, "u1")
        expire = r2.kv["user:u1"][1]
        ttls.add(expire)
    assert len(ttls) > 1, "TTL 应带随机抖动"

    # 5. 击穿现象：热点 key 过期瞬间，多个并发读者都“读到 miss”再回源
    r3 = MiniRedis()
    r3.setex("user:u1", 1, json.dumps({"name": "alice"}))   # 热点 key，TTL 1s
    r3.now = 10   # key 过期
    misses = 0
    for _ in range(10):
        if r3.get("user:u1") is None:     # 模拟 10 个并发请求同时读到 miss
            query_db("u1")                 # 缓存还没来得及重建，各自回源
            misses += 1
    assert misses == 10, f"应复现击穿: {misses} 次回源"
    print("（击穿现象已复现：10 个并发 miss 全部回源；生产用互斥锁/逻辑过期挡住，见 README）")

    print("✅ self-test 全部通过")


MINIR = None


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        try:
            import redis
            r = redis.Redis(host="127.0.0.1", decode_responses=True)
        except ImportError:
            r = MiniRedis()
        print("冷查询:", get_user_without_cache("u1"))
        t0 = time.perf_counter(); get_user_cache_aside(r, "u1"); print(f"首次: {time.perf_counter()-t0:.4f}s")
        t0 = time.perf_counter(); get_user_cache_aside(r, "u1"); print(f"缓存: {time.perf_counter()-t0:.4f}s")
