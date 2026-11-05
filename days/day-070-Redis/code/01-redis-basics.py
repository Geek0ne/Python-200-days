"""
Day 070 — Redis 基础：五大结构操作
运行方式：
  python 01-redis-basics.py --self-test   # MiniRedis 离线自检
  python 01-redis-basics.py               # 真实 Redis 环境
"""
import sys


# ========== MiniRedis：仅供离线自检的内存模拟 ==========

class MiniRedis:
    def __init__(self):
        self.kv, self.hash, self.lst, self.st, self.zs = {}, {}, {}, {}, {}

    def set(self, k, v): self.kv[k] = str(v); return True
    def get(self, k): return self.kv.get(k)
    def incr(self, k): self.kv[k] = str(int(self.kv.get(k, "0")) + 1); return int(self.kv[k])
    def hset(self, k, f, v): self.hash.setdefault(k, {})[f] = str(v); return 1
    def hgetall(self, k): return dict(self.hash.get(k, {}))
    def lpush(self, k, v): self.lst.setdefault(k, []).insert(0, str(v)); return len(self.lst[k])
    def lrange(self, k, a, b):
        data = self.lst.get(k, [])
        b = len(data) if b == -1 else b + 1
        return data[a:b]
    def sadd(self, k, v):
        s = self.st.setdefault(k, set()); before = len(s); s.add(str(v)); return int(len(s) > before)
    def smembers(self, k): return set(self.st.get(k, set()))
    def zadd(self, k, mapping):
        z = self.zs.setdefault(k, {}); z.update({str(m): float(s) for m, s in mapping.items()}); return len(mapping)
    def zrevrange(self, k, a, b):
        ranked = [m for m, _ in sorted(self.zs.get(k, {}).items(), key=lambda x: -x[1])]
        b = len(ranked) if b == -1 else b + 1
        return ranked[a:b]


def connect():
    try:
        import redis
        return redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
    except ImportError:
        print("未安装 redis 包，使用 MiniRedis")
        return MiniRedis()


def demo(r):
    print("--- string：计数器 ---")
    r.set("article:1001:views", 0)
    for _ in range(3):
        r.incr("article:1001:views")
    print("阅读量 =", r.get("article:1001:views"))

    print("--- hash：用户资料 ---")
    r.hset("user:1", "name", "alice")
    r.hset("user:1", "city", "BJ")
    print(r.hgetall("user:1"))

    print("--- list：最新动态 ---")
    r.lpush("feed", "msg-1")
    r.lpush("feed", "msg-2")
    print("最新:", r.lrange("feed", 0, -1))

    print("--- set：去重 ---")
    for tag in ["python", "redis", "python"]:
        r.sadd("tags", tag)
    print("标签:", r.smembers("tags"))

    print("--- zset：排行榜 ---")
    r.zadd("board", {"alice": 95, "bob": 87, "carol": 92})
    print("Top2:", r.zrevrange("board", 0, 1))


def self_test():
    r = MiniRedis()
    demo(r)
    assert r.get("article:1001:views") == "3"
    assert r.hgetall("user:1") == {"name": "alice", "city": "BJ"}
    assert r.lrange("feed", 0, -1) == ["msg-2", "msg-1"], "lpush 头插语义"
    assert r.smembers("tags") == {"python", "redis"}
    assert r.zrevrange("board", 0, 1) == ["alice", "carol"]
    print("✅ self-test 全部通过")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        demo(connect())
