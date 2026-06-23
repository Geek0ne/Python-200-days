"""
Day 39 — 设计模式（结构型）
03-cache-proxy.py
实战案例：缓存代理 — 模拟多级缓存 + 数据库查询优化

场景：高并发 API 服务，每次查询数据库开销大。
使用缓存代理减少数据库查询次数，支持 TTL 过期和 LRU 淘汰。

┌──────────┐    ┌───────────────────┐    ┌──────────────┐
│ 客户端   │───▶│  CacheProxy        │───▶│  DBService   │
│ (高并发) │    │                    │    │ (模拟数据库) │
└──────────┘    │  ┌───────────┐    │    └──────────────┘
                │  │  缓存 LRU  │    │
                │  │  + TTL    │    │    查 user_001
                │  └───────────┘    │──────────────┐
                │  ┌───────────┐    │              ▼
                │  │  统计信息  │    │    查询数据库 50ms
                │  │  命中率    │    │
                │  └───────────┘    │    再查 user_001
                │                   │────── ✅ 缓存 0ms
                └───────────────────┘
"""

from abc import ABC, abstractmethod
import time
import threading
from collections import OrderedDict


# ══════════════════════════════════════════════════════════
# 1. 抽象主题
# ══════════════════════════════════════════════════════════

class UserService(ABC):
    """抽象用户服务接口"""
    
    @abstractmethod
    def get_user(self, user_id: str) -> dict:
        """查询用户信息"""
        pass
    
    @abstractmethod
    def update_user(self, user_id: str, data: dict) -> bool:
        """更新用户信息"""
        pass


# ══════════════════════════════════════════════════════════
# 2. 真实主题：数据库服务
# ══════════════════════════════════════════════════════════

class DBUserService(UserService):
    """
    真实数据库服务（模拟）
    
    模拟 MySQL / Redis 等数据库操作，每次查询需要 50ms。
    在真实系统中，这里会执行 SQL 查询。
    """
    
    def __init__(self):
        # 模拟数据库中的用户数据
        self._database = {
            "user_001": {"name": "张三", "age": 28, "email": "zhangsan@example.com", "level": "VIP"},
            "user_002": {"name": "李四", "age": 32, "email": "lisi@example.com", "level": "普通"},
            "user_003": {"name": "王五", "age": 25, "email": "wangwu@example.com", "level": "VIP"},
            "user_004": {"name": "赵六", "age": 35, "email": "zhaoliu@example.com", "level": "普通"},
        }
        self._query_count = 0
    
    def _simulate_db_query(self) -> None:
        """模拟数据库查询延迟"""
        time.sleep(0.05)  # 50ms 数据库查询
    
    def get_user(self, user_id: str) -> dict | None:
        self._query_count += 1
        self._simulate_db_query()
        
        if user_id not in self._database:
            return None
        
        user = self._database[user_id].copy()
        print(f"      [DB] 📡 查询数据库: {user_id} → {user['name']} (第{self._query_count}次查询)")
        return user
    
    def update_user(self, user_id: str, data: dict) -> bool:
        if user_id not in self._database:
            return False
        
        self._database[user_id].update(data)
        print(f"      [DB] 📝 更新数据库: {user_id} → {data}")
        return True
    
    def get_query_count(self) -> int:
        """获取总查询次数"""
        return self._query_count


# ══════════════════════════════════════════════════════════
# 3. 代理：多级缓存代理
# ══════════════════════════════════════════════════════════

class CacheEntry:
    """缓存条目：包含数据和过期时间"""
    
    def __init__(self, data: dict, ttl_seconds: int = 60):
        self.data = data
        self.expire_at = time.time() + ttl_seconds
    
    def is_expired(self) -> bool:
        return time.time() > self.expire_at
    
    def __repr__(self):
        return f"CacheEntry(expire_in={int(self.expire_at - time.time())}s)"


class CacheProxy(UserService):
    """
    缓存代理（LRU + TTL）
    
    功能特性：
    1. LRU 淘汰：超过缓存容量时淘汰最久未使用的条目
    2. TTL 过期：缓存在指定时间后自动失效
    3. 统计监控：记录缓存命中率
    4. 缓存失效：数据更新时自动清除相关缓存
    5. 线程安全：支持并发访问
    """
    
    def __init__(self, service: UserService, max_size: int = 100, default_ttl: int = 60):
        """
        初始化缓存代理
        
        Args:
            service: 被代理的真实服务
            max_size: 缓存最大条目数
            default_ttl: 默认缓存过期时间（秒）
        """
        self._service = service
        self._max_size = max_size
        self._default_ttl = default_ttl
        
        # OrderedDict 实现 LRU：迭代顺序 = 访问顺序
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()  # 线程安全
        
        # 统计信息
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
        
        print(f"  [CacheProxy] 🚀 缓存代理启动 | 容量={max_size} | TTL={default_ttl}s")
    
    def get_user(self, user_id: str) -> dict | None:
        """
        获取用户信息（优先从缓存返回）
        """
        with self._lock:
            # 检查缓存
            if user_id in self._cache:
                entry = self._cache[user_id]
                
                # 检查是否过期
                if entry.is_expired():
                    # 过期了，移除
                    del self._cache[user_id]
                    self._stats["expirations"] += 1
                    print(f"      [Cache] ⏰ 缓存过期: {user_id}")
                else:
                    # 缓存命中！
                    # 把该条目移到末尾（表示最近使用）
                    self._cache.move_to_end(user_id)
                    self._stats["hits"] += 1
                    print(f"      [Cache] ✅ 缓存命中: {user_id}")
                    return entry.data.copy()
        
        # 缓存未命中，查询真实服务
        self._stats["misses"] += 1
        print(f"      [Cache] ❌ 缓存未命中: {user_id} → 查询数据库")
        
        data = self._service.get_user(user_id)
        
        if data is not None:
            # 存到缓存
            with self._lock:
                self._evict_if_needed()
                self._cache[user_id] = CacheEntry(data, self._default_ttl)
                self._cache.move_to_end(user_id)
        
        return data
    
    def update_user(self, user_id: str, data: dict) -> bool:
        """
        更新用户信息（同时失效缓存）
        """
        result = self._service.update_user(user_id, data)
        
        if result:
            # 数据变更，清除相关缓存
            with self._lock:
                if user_id in self._cache:
                    del self._cache[user_id]
                    print(f"      [Cache] 🧹 缓存失效: {user_id}（数据已更新）")
        
        return result
    
    def _evict_if_needed(self) -> None:
        """如果缓存满了，淘汰最久未使用的条目"""
        while len(self._cache) >= self._max_size:
            # 从头弹出（最久未使用）
            oldest_key, _ = self._cache.popitem(last=False)
            self._stats["evictions"] += 1
            print(f"      [Cache] 🗑️ 淘汰: {oldest_key}（缓存已满）")
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        with self._lock:
            cache_size = len(self._cache)
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": cache_size,
            "max_size": self._max_size,
            "evictions": self._stats["evictions"],
            "expirations": self._stats["expirations"],
        }
    
    def clear_cache(self) -> None:
        """清除所有缓存"""
        with self._lock:
            self._cache.clear()
        print(f"      [Cache] 🧹 已清除全部缓存")


# ══════════════════════════════════════════════════════════
# 4. 扩展：统计代理（装饰器模式与代理组合）
# ══════════════════════════════════════════════════════════

class StatsProxy(UserService):
    """
    统计代理：记录每个用户的查询频率和响应时间
    可以和缓存代理链式使用
    """
    
    def __init__(self, service: UserService):
        self._service = service
        self._stats: dict[str, dict] = {}
    
    def get_user(self, user_id: str) -> dict | None:
        start = time.time()
        result = self._service.get_user(user_id)
        elapsed = (time.time() - start) * 1000  # ms
        
        if user_id not in self._stats:
            self._stats[user_id] = {"count": 0, "total_ms": 0, "avg_ms": 0}
        
        self._stats[user_id]["count"] += 1
        self._stats[user_id]["total_ms"] += elapsed
        self._stats[user_id]["avg_ms"] = (
            self._stats[user_id]["total_ms"] / self._stats[user_id]["count"]
        )
        
        print(f"      [Stats] ⏱️  {user_id} 查询耗时 {elapsed:.1f}ms (平均 {self._stats[user_id]['avg_ms']:.1f}ms)")
        return result
    
    def update_user(self, user_id: str, data: dict) -> bool:
        start = time.time()
        result = self._service.update_user(user_id, data)
        elapsed = (time.time() - start) * 1000
        print(f"      [Stats] ⏱️  更新 {user_id} 耗时 {elapsed:.1f}ms")
        return result
    
    def get_stats_report(self) -> str:
        """生成统计报告"""
        lines = ["\n📊 用户查询统计报告", "-" * 30]
        for uid, s in sorted(self._stats.items()):
            lines.append(f"  {uid}: {s['count']}次, 平均{s['avg_ms']:.0f}ms")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# 5. 测试
# ══════════════════════════════════════════════════════════

def demo_cache_basics():
    """演示缓存代理基础功能"""
    
    print("=" * 70)
    print("实战：缓存代理 — 基础功能演示")
    print("=" * 70)
    
    # 创建服务链：真实数据库 → 缓存代理
    db = DBUserService()
    cache = CacheProxy(db, max_size=3, default_ttl=10)  # 容量3，TTL 10秒
    
    print("\n📥 第一次查询（缓存未命中 → 查数据库）:")
    user = cache.get_user("user_001")
    print(f"    结果: {user['name']}, {user['email']}")
    
    print("\n📥 第二次查询（缓存命中 → 无需查库）:")
    user = cache.get_user("user_001")
    print(f"    结果: {user['name']}, {user['email']}")
    
    print("\n📥 查询其他用户:")
    cache.get_user("user_002")
    cache.get_user("user_003")
    
    print(f"\n📊 缓存统计:")
    for k, v in cache.get_stats().items():
        print(f"    {k}: {v}")
    
    print(f"\n📡 数据库总查询次数: {db.get_query_count()} 次")
    print("   （如果有 3 次查询但只命中 1 次缓存，说明另外 2 次也是查库）")


def demo_lru_eviction():
    """演示 LRU 淘汰"""
    
    print("\n" + "=" * 70)
    print("实战：LRU 淘汰策略演示（容量=3）")
    print("=" * 70)
    
    db = DBUserService()
    cache = CacheProxy(db, max_size=3, default_ttl=60)
    
    # 先查入 3 个用户，填满缓存
    print("\n📥 填充缓存（3个用户）:")
    for uid in ["user_001", "user_002", "user_003"]:
        cache.get_user(uid)
    
    print("\n📥 查询 user_001（把它移到最近使用）:")
    cache.get_user("user_001")
    
    print("\n📥 查询 user_004（缓存已满 → 淘汰最久未使用的 user_002）:")
    cache.get_user("user_004")
    
    print("\n📥 再查 user_002（已被淘汰，需要重新查库）:")
    cache.get_user("user_002")
    
    print(f"\n📊 缓存统计:")
    for k, v in cache.get_stats().items():
        print(f"    {k}: {v}")


def demo_cache_invalidation():
    """演示缓存失效"""
    
    print("\n" + "=" * 70)
    print("实战：缓存失效 — 更新数据时清除缓存")
    print("=" * 70)
    
    db = DBUserService()
    cache = CacheProxy(db, max_size=10, default_ttl=60)
    
    # 查询缓存
    print("\n📥 查询 user_001:")
    cache.get_user("user_001")
    
    print("\n📥 再次查询（缓存命中）:")
    cache.get_user("user_001")
    
    print("\n📝 更新 user_001 信息（缓存应失效）:")
    cache.update_user("user_001", {"level": "SVIP"})
    
    print("\n📥 查询 user_001（缓存已失效 → 重新查库）:")
    cache.get_user("user_001")
    
    print(f"\n📊 最终缓存统计:")
    for k, v in cache.get_stats().items():
        print(f"    {k}: {v}")


def demo_proxy_chain():
    """演示代理链：统计代理 → 缓存代理 → 数据库"""
    
    print("\n" + "=" * 70)
    print("实战：代理链 — 组合多个代理")
    print("=" * 70)
    
    db = DBUserService()
    cache = CacheProxy(db, max_size=100, default_ttl=30)
    stats = StatsProxy(cache)  # 统计代理包裹缓存代理
    
    # 客户端只和 stats 代理交互
    print("\n📥 通过代理链查询:")
    for _ in range(3):
        stats.get_user("user_001")
        stats.get_user("user_002")
    
    print(stats.get_stats_report())
    
    print(f"\n📊 缓存命中率:")
    print(cache.get_stats())


def benchmark():
    """性能对比：有缓存 vs 无缓存"""
    
    print("\n" + "=" * 70)
    print("性能基准测试：有缓存 vs 无缓存")
    print("=" * 70)
    
    db = DBUserService()
    cache = CacheProxy(db, max_size=100, default_ttl=60)
    
    # 模拟 20 次查询（只有 5 个不同用户）
    users = ["user_001", "user_002", "user_003", "user_004", "user_001",
             "user_002", "user_003", "user_001", "user_002", "user_003",
             "user_004", "user_001", "user_002", "user_003", "user_001",
             "user_002", "user_003", "user_001", "user_004", "user_002"]
    
    start = time.time()
    for uid in users:
        cache.get_user(uid)
    elapsed = time.time() - start
    
    stats = cache.get_stats()
    print(f"\n📊 20 次查询结果:")
    print(f"    总耗时: {elapsed:.2f}s")
    print(f"    缓存命中: {stats['hits']} 次")
    print(f"    缓存未命中: {stats['misses']} 次")
    print(f"    命中率: {stats['hit_rate']}")
    print(f"    数据库查询: {db.get_query_count()} 次")
    
    estimated_without_cache = len(users) * 0.05  # 每次 50ms
    print(f"\n📈 性能对比:")
    print(f"    无缓存: ~{estimated_without_cache:.1f}s")
    print(f"    有缓存: ~{elapsed:.2f}s")
    print(f"    提升: ~{estimated_without_cache/elapsed:.0f}x 速度")


if __name__ == "__main__":
    demo_cache_basics()
    demo_lru_eviction()
    demo_cache_invalidation()
    demo_proxy_chain()
    benchmark()

"""
运行结果要点：

20 次查询（5 个不同用户）：
  无缓存：20 × 50ms = 1.0s
  有缓存：5 × 50ms + 15 × 0ms = 0.25s（命中第一波后都是缓存）
  速度提升约 4x！

LRU 淘汰策略：
  容量 3，查 4 个不同用户 → 最早使用的被自动淘汰
  淘汰策略确保热数据保留在缓存中

缓存失效：
  更新数据时自动清除缓存 → 下次查询读到最新数据
  保证数据一致性
"""
