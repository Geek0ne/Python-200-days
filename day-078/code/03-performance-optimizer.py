"""
性能优化工具集 - 批量写入 + 布隆过滤器 + 异步IO
功能：提升爬虫系统性能的核心工具
"""

import asyncio
import time
import random
import hashlib
from typing import List, Dict, Optional, Any
from collections import OrderedDict
from functools import lru_cache


# ==================== 批量写入器 ====================

class BatchWriter:
    """
    批量写入优化器
    
    解决问题：频繁的单条数据库写入会造成性能瓶颈
    解决方案：缓冲数据，批量写入数据库
    """
    
    def __init__(self, name: str = "default", batch_size: int = 100, flush_interval: float = 5.0):
        """
        初始化批量写入器
        
        Args:
            name: 写入器名称（用于日志）
            batch_size: 批量大小（达到此数量时自动刷新）
            flush_interval: 刷新间隔（秒）
        """
        self.name = name
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer: List[Dict] = []
        self.last_flush = time.time()
        self.total_written = 0
        self.flush_count = 0
    
    def add(self, item: Dict):
        """
        添加数据到缓冲区
        
        当缓冲区达到 batch_size 或超过 flush_interval 时自动刷新
        """
        self.buffer.append(item)
        
        # 检查是否需要刷新
        should_flush = (
            len(self.buffer) >= self.batch_size or
            time.time() - self.last_flush >= self.flush_interval
        )
        
        if should_flush:
            self.flush()
    
    def flush(self):
        """刷新缓冲区到数据库（模拟）"""
        if not self.buffer:
            return
        
        # 这里模拟数据库写入
        # 实际项目中替换为真实的数据库操作
        items_to_write = self.buffer.copy()
        self.buffer.clear()
        self.last_flush = time.time()
        self.flush_count += 1
        self.total_written += len(items_to_write)
        
        # 模拟写入耗时
        time.sleep(0.01)
        
        print(f"[{self.name}] ✅ 批量写入 {len(items_to_write)} 条数据 (总计: {self.total_written})")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "buffer_size": len(self.buffer),
            "total_written": self.total_written,
            "flush_count": self.flush_count,
            "avg_batch_size": self.total_written / self.flush_count if self.flush_count else 0
        }
    
    def __del__(self):
        """析构时刷新剩余数据"""
        if self.buffer:
            self.flush()


# ==================== 布隆过滤器 ====================

class BloomFilter:
    """
    布隆过滤器 - 高效概率型数据结构
    
    特点：
    - 空间效率极高
    - 查询时间 O(k)，k为哈希函数数量
    - 可能有假阳性（误判），但绝无假阴性（漏判）
    
    适用场景：
    - 大规模 URL 去重
    - 缓存穿透防护
    - 垃圾邮件过滤
    """
    
    def __init__(self, expected_elements: int = 1000000, false_positive_rate: float = 0.001):
        """
        初始化布隆过滤器
        
        Args:
            expected_elements: 预期存储元素数量
            false_positive_rate: 允许的假阳性率（误判率）
        """
        import math
        
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate
        
        # 计算最优参数
        self.size = self._optimal_size(expected_elements, false_positive_rate)
        self.hash_count = self._optimal_hash_count(self.size, expected_elements)
        
        # 使用整数数组模拟位数组（Python没有原生bitarray）
        self.bit_array = [0] * ((self.size + 63) // 64)  # 每个int存储64位
        self.count = 0
        
        print(f"🔧 布隆过滤器初始化:")
        print(f"   位数组大小: {self.size} bits ({self.size / 8 / 1024:.1f} KB)")
        print(f"   哈希函数数: {self.hash_count}")
    
    def _optimal_size(self, n: int, p: float) -> int:
        """计算最优位数组大小"""
        import math
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(m)
    
    def _optimal_hash_count(self, m: int, n: int) -> int:
        """计算最优哈希函数数量"""
        import math
        k = (m / n) * math.log(2)
        return max(1, int(k))
    
    def _hash(self, item: str, seed: int) -> int:
        """计算哈希值"""
        # 使用不同种子模拟多个哈希函数
        return int(hashlib.md5(f"{seed}:{item}".encode()).hexdigest(), 16) % self.size
    
    def _set_bit(self, position: int):
        """设置位"""
        array_index = position // 64
        bit_index = position % 64
        self.bit_array[array_index] |= (1 << bit_index)
    
    def _get_bit(self, position: int) -> bool:
        """获取位"""
        array_index = position // 64
        bit_index = position % 64
        return bool(self.bit_array[array_index] & (1 << bit_index))
    
    def add(self, item: str):
        """添加元素"""
        for i in range(self.hash_count):
            position = self._hash(item, i)
            self._set_bit(position)
        self.count += 1
    
    def contains(self, item: str) -> bool:
        """
        检查元素是否可能存在
        
        Returns:
            True: 元素可能存在（有小概率是误判）
            False: 元素一定不存在
        """
        for i in range(self.hash_count):
            position = self._hash(item, i)
            if not self._get_bit(position):
                return False
        return True
    
    def __contains__(self, item: str) -> bool:
        """支持 in 操作符"""
        return self.contains(item)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        # 计算实际使用的位数
        used_bits = sum(bin(x).count('1') for x in self.bit_array)
        return {
            "total_bits": self.size,
            "used_bits": used_bits,
            "usage_rate": f"{used_bits / self.size * 100:.2f}%",
            "element_count": self.count,
            "hash_count": self.hash_count,
            "memory_kb": self.size / 8 / 1024
        }


# ==================== LRU 缓存 ====================

class LRUCache:
    """
    LRU（最近最少使用）缓存
    
    适用场景：
    - 缓存已爬取的页面摘要
    - 缓存解析结果
    - 限制内存使用
    """
    
    def __init__(self, capacity: int = 1000):
        """
        初始化 LRU 缓存
        
        Args:
            capacity: 缓存容量
        """
        self.capacity = capacity
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def put(self, key: str, value: Any):
        """设置缓存值"""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        
        # 超出容量时删除最旧的
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def contains(self, key: str) -> bool:
        """检查 key 是否存在"""
        return key in self.cache
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hits / total * 100:.1f}%" if total else "0%"
        }


# ==================== 异步批量请求器 ====================

class AsyncBatchFetcher:
    """
    异步批量请求器
    
    使用 asyncio + aiohttp 实现高并发请求
    """
    
    def __init__(self, max_concurrent: int = 20, timeout: float = 10.0):
        """
        初始化异步请求器
        
        Args:
            max_concurrent: 最大并发数
            timeout: 请求超时时间（秒）
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.results = []
    
    async def fetch_one(self, url: str, delay: float = 0) -> Dict:
        """
        获取单个 URL（模拟）
        
        实际项目中替换为 aiohttp 请求
        """
        async with self.semaphore:
            if delay > 0:
                await asyncio.sleep(delay)
            
            # 模拟请求
            success = random.random() > 0.1
            duration = random.uniform(0.1, 2.0)
            
            return {
                "url": url,
                "success": success,
                "status": 200 if success else random.choice([404, 500, 503]),
                "duration": round(duration, 2),
                "size": random.randint(1000, 100000) if success else 0
            }
    
    async def fetch_batch(self, urls: List[str]) -> List[Dict]:
        """批量异步获取"""
        tasks = [self.fetch_one(url) for url in urls]
        self.results = await asyncio.gather(*tasks)
        return self.results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self.results:
            return {"total": 0}
        
        successful = sum(1 for r in self.results if r["success"])
        total_duration = sum(r["duration"] for r in self.results)
        
        return {
            "total": len(self.results),
            "successful": successful,
            "failed": len(self.results) - successful,
            "success_rate": f"{successful / len(self.results) * 100:.1f}%",
            "total_duration": round(total_duration, 2),
            "avg_duration": round(total_duration / len(self.results), 2),
            "requests_per_second": round(len(self.results) / total_duration, 2) if total_duration > 0 else 0
        }


# ==================== 性能基准测试 ====================

def benchmark_batch_writer():
    """基准测试：批量写入 vs 单条写入"""
    print("\n📊 基准测试：批量写入 vs 单条写入")
    print("-" * 40)
    
    test_data = [{"id": i, "data": f"item_{i}"} for i in range(1000)]
    
    # 单条写入
    start = time.time()
    for item in test_data:
        # 模拟单条写入
        time.sleep(0.001)
    single_time = time.time() - start
    
    # 批量写入
    writer = BatchWriter(name="benchmark", batch_size=100)
    start = time.time()
    for item in test_data:
        writer.add(item)
    writer.flush()
    batch_time = time.time() - start
    
    print(f"单条写入: {single_time:.2f}s")
    print(f"批量写入: {batch_time:.2f}s")
    print(f"性能提升: {single_time / batch_time:.1f}x")


def benchmark_bloom_filter():
    """基准测试：布隆过滤器 vs 集合"""
    print("\n📊 基准测试：布隆过滤器 vs 集合")
    print("-" * 40)
    
    test_count = 100000
    
    # 生成测试数据
    test_urls = [f"https://example.com/page/{i}" for i in range(test_count)]
    query_urls = test_urls[:10000] + [f"https://example.com/new/{i}" for i in range(10000)]
    
    # 集合测试
    start = time.time()
    url_set = set(test_urls)
    results_set = [url in url_set for url in query_urls]
    set_time = time.time() - start
    set_memory = len(url_set) * 100  # 估算内存
    
    # 布隆过滤器测试
    start = time.time()
    bloom = BloomFilter(expected_elements=test_count)
    for url in test_urls:
        bloom.add(url)
    results_bloom = [url in bloom for url in query_urls]
    bloom_time = time.time() - start
    
    # 统计内存
    bloom_stats = bloom.get_stats()
    
    print(f"集合 - 时间: {set_time:.3f}s, 内存: ~{set_memory / 1024:.1f} KB")
    print(f"布隆 - 时间: {bloom_time:.3f}s, 内存: {bloom_stats['memory_kb']:.1f} KB")
    print(f"内存节省: {set_memory / 1024 / bloom_stats['memory_kb']:.1f}x")


# ==================== 演示 ====================

def demo():
    """完整演示"""
    print("🎯 性能优化工具演示")
    print("=" * 40)
    
    # 1. 批量写入演示
    print("\n📦 1. 批量写入演示")
    writer = BatchWriter(name="demo", batch_size=20, flush_interval=2.0)
    
    for i in range(50):
        writer.add({"id": i, "value": f"item_{i}"})
        time.sleep(0.05)
    
    writer.flush()
    print(f"统计: {writer.get_stats()}")
    
    # 2. 布隆过滤器演示
    print("\n🔍 2. 布隆过滤器演示")
    bloom = BloomFilter(expected_elements=1000)
    
    # 添加 URL
    for i in range(500):
        bloom.add(f"https://example.com/page/{i}")
    
    # 测试查询
    test_urls = [
        "https://example.com/page/100",     # 存在
        "https://example.com/page/999",     # 不存在
        "https://example.com/new/123",      # 不存在
    ]
    
    for url in test_urls:
        result = "可能存在" if url in bloom else "一定不存在"
        print(f"   {url}: {result}")
    
    print(f"统计: {bloom.get_stats()}")
    
    # 3. LRU 缓存演示
    print("\n💾 3. LRU 缓存演示")
    cache = LRUCache(capacity=5)
    
    for i in range(8):
        cache.put(f"key_{i}", f"value_{i}")
        print(f"   添加 key_{i}, 缓存大小: {len(cache.cache)}")
    
    # 访问已存在的 key
    cache.get("key_5")
    print(f"   访问 key_5 (应存在)")
    print(f"   统计: {cache.get_stats()}")
    
    # 4. 性能基准测试
    print("\n📊 4. 性能基准测试")
    benchmark_batch_writer()
    benchmark_bloom_filter()
    
    print("\n✅ 演示完成!")


if __name__ == "__main__":
    demo()
