"""
03-ecommerce-monitor.py
实战案例：电商价格监控系统（完整可运行版本）

本脚本模拟一个完整的电商价格监控系统，包含：
- 多商品并发监控
- 价格历史追踪
- 降价提醒
- 数据持久化
- 统计报表

运行方式：python3 03-ecommerce-monitor.py
无需 Scrapy 环境，纯 Python 实现
"""

import json
import hashlib
import random
import time
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# ============================================================
# 1. 数据结构定义
# ============================================================

@dataclass
class Product:
    """商品数据"""
    name: str
    price: float
    original_price: float = 0.0
    url: str = ''
    shop: str = ''
    category: str = ''
    rating: float = 0.0
    reviews: int = 0
    crawled_at: str = ''
    alert: str = '首次记录'
    discount_pct: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PriceRecord:
    """价格记录"""
    price: float
    timestamp: str
    alert: str = ''


# ============================================================
# 2. 调度器：管理爬取请求
# ============================================================

class CrawlScheduler:
    """
    爬取调度器
    - 优先级队列
    - 去重过滤
    - 请求计数
    """

    def __init__(self):
        self.queue = []       # (priority, url, callback_name)
        self.seen_fps = set() # 已见指纹
        self.stats = {
            'enqueued': 0,
            'filtered': 0,
            'dequeued': 0,
        }

    def _fingerprint(self, url: str, ignore_params: list = None) -> str:
        """生成请求指纹"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        if ignore_params:
            for p in ignore_params:
                params.pop(p, None)

        sorted_query = urlencode(sorted(params.items()), doseq=True)
        clean_url = urlunparse(parsed._replace(query=sorted_query))

        return hashlib.sha1(clean_url.encode()).hexdigest()

    def enqueue(self, url: str, priority: int = 0,
                callback: str = 'parse',
                dont_filter: bool = False,
                ignore_params: list = None) -> bool:
        """入队请求"""
        fp = self._fingerprint(url, ignore_params)

        if not dont_filter and fp in self.seen_fps:
            self.stats['filtered'] += 1
            return False

        self.seen_fps.add(fp)
        self.queue.append((priority, url, callback))
        self.queue.sort(key=lambda x: -x[0])  # 降序，大的优先
        self.stats['enqueued'] += 1
        return True

    def next_request(self) -> Optional[tuple]:
        """取出下一个请求"""
        if not self.queue:
            return None
        item = self.queue.pop(0)
        self.stats['dequeued'] += 1
        return item

    @property
    def size(self) -> int:
        return len(self.queue)


# ============================================================
# 3. 数据管道
# ============================================================

class CleanPipeline:
    """数据清洗"""

    def process(self, item: Product) -> Product:
        # 清洗名称
        item.name = ' '.join(item.name.split())

        # 标准化价格
        if isinstance(item.price, str):
            item.price = float(
                item.price.replace('¥', '').replace('$', '').replace(',', '')
            )
        item.price = round(item.price, 2)

        # 标准化评分
        if item.rating:
            item.rating = round(float(item.rating), 1)

        # 添加爬取时间
        item.crawled_at = datetime.now().isoformat()

        return item


class ValidatePipeline:
    """数据验证"""

    def process(self, item: Product) -> Optional[Product]:
        # 必填检查
        if not item.name or not item.price or not item.url:
            return None  # 丢弃

        # 价格合理性
        if item.price <= 0 or item.price > 999999:
            return None

        # URL 格式
        if not item.url.startswith('http'):
            return None

        return item


class PriceAlertPipeline:
    """价格预警"""

    def __init__(self):
        self.history = {}  # {url: [PriceRecord, ...]}

    def process(self, item: Product) -> Product:
        url = item.url
        price = item.price

        if url in self.history:
            records = self.history[url]
            last_price = records[-1].price

            if price < last_price:
                discount = (last_price - price) / last_price * 100
                item.alert = f"降价 {discount:.1f}%"
                item.discount_pct = round(discount, 1)
            elif price > last_price:
                item.alert = "涨价"
                item.discount_pct = -round(
                    (price - last_price) / last_price * 100, 1
                )
            else:
                item.alert = "持平"
                item.discount_pct = 0
        else:
            item.alert = "首次记录"
            item.discount_pct = 0

        self.history.setdefault(url, []).append(
            PriceRecord(price=price, timestamp=item.crawled_at, alert=item.alert)
        )
        return item


class StoragePipeline:
    """数据存储"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.file = None
        self.count = 0

    def open(self):
        self.file = open(self.filepath, 'a', encoding='utf-8')
        self.count = 0

    def close(self):
        if self.file:
            self.file.close()

    def process(self, item: Product) -> Product:
        if self.file:
            line = json.dumps(item.to_dict(), ensure_ascii=False)
            self.file.write(line + '\n')
            self.file.flush()
            self.count += 1
        return item


# ============================================================
# 4. 模拟数据源（替代真实爬虫）
# ============================================================

MOCK_PRODUCTS = [
    {
        'name': 'iPhone 15 Pro 256GB',
        'base_price': 8999,
        'url': 'https://shop.example.com/p/iphone15pro',
        'shop': 'Apple 官方旗舰店',
        'category': '手机',
        'rating': 4.8,
        'reviews': 12580,
    },
    {
        'name': 'MacBook Pro 14 M3',
        'base_price': 16999,
        'url': 'https://shop.example.com/p/macbookpro14',
        'shop': 'Apple 官方旗舰店',
        'category': '电脑',
        'rating': 4.9,
        'reviews': 8920,
    },
    {
        'name': 'AirPods Pro 2',
        'base_price': 1899,
        'url': 'https://shop.example.com/p/airpodspro2',
        'shop': 'Apple 官方旗舰店',
        'category': '配件',
        'rating': 4.7,
        'reviews': 25600,
    },
    {
        'name': 'iPad Air M2',
        'base_price': 4799,
        'url': 'https://shop.example.com/p/ipadairm2',
        'shop': 'Apple 官方旗舰店',
        'category': '平板',
        'rating': 4.6,
        'reviews': 6780,
    },
    {
        'name': 'Samsung Galaxy S24 Ultra',
        'base_price': 9999,
        'url': 'https://shop.example.com/p/galaxys24ultra',
        'shop': '三星官方旗舰店',
        'category': '手机',
        'rating': 4.5,
        'reviews': 5430,
    },
]


def simulate_crawl_round(round_num: int) -> list[Product]:
    """模拟一轮爬取，返回商品列表（模拟价格波动）"""
    products = []
    for data in MOCK_PRODUCTS:
        # 模拟价格波动：-15% ~ +5%
        fluctuation = random.uniform(-0.15, 0.05)
        current_price = round(data['base_price'] * (1 + fluctuation), 2)

        product = Product(
            name=data['name'],
            price=current_price,
            original_price=data['base_price'],
            url=data['url'],
            shop=data['shop'],
            category=data['category'],
            rating=data['rating'],
            reviews=data['reviews'],
        )
        products.append(product)

    return products


# ============================================================
# 5. 统计分析
# ============================================================

class StatsAnalyzer:
    """爬取统计分析"""

    def __init__(self):
        self.price_history = defaultdict(list)  # {url: [(price, time), ...]}
        self.alerts = []

    def record(self, product: Product):
        self.price_history[product.url].append(
            (product.price, product.crawled_at)
        )
        if product.alert not in ('首次记录', '持平'):
            self.alerts.append({
                'name': product.name,
                'alert': product.alert,
                'price': product.price,
                'time': product.crawled_at,
            })

    def summary(self) -> dict:
        total_alerts = len(self.alerts)
        price_drops = sum(1 for a in self.alerts if '降价' in a['alert'])
        price_rises = sum(1 for a in self.alerts if '涨价' in a['alert'])

        # 找出最大降幅
        max_drop = None
        for a in self.alerts:
            if '降价' in a['alert']:
                pct = float(a['alert'].split()[1].rstrip('%'))
                if max_drop is None or pct > max_drop['pct']:
                    max_drop = {'name': a['name'], 'pct': pct}

        return {
            'total_products': len(self.price_history),
            'total_records': sum(len(v) for v in self.price_history.values()),
            'total_alerts': total_alerts,
            'price_drops': price_drops,
            'price_rises': price_rises,
            'max_drop': max_drop,
        }


# ============================================================
# 6. 主程序
# ============================================================

def main():
    print("🛒 电商价格监控系统 v1.0")
    print("=" * 60)

    # 初始化组件
    scheduler = CrawlScheduler()
    clean = CleanPipeline()
    validate = ValidatePipeline()
    alert_pipeline = PriceAlertPipeline()
    storage = StoragePipeline('monitor_output.jsonl')
    analyzer = StatsAnalyzer()

    storage.open()

    # 入队所有商品页面
    print("\n📥 初始化爬取队列...")
    for product in MOCK_PRODUCTS:
        priority = 10 if product['category'] == '手机' else 5
        scheduler.enqueue(
            product['url'],
            priority=priority,
            callback='parse_product',
            ignore_params=['timestamp', 'session_id'],
        )
    print(f"  队列大小: {scheduler.size}")

    # 模拟多轮爬取
    NUM_ROUNDS = 3
    for round_num in range(1, NUM_ROUNDS + 1):
        print(f"\n{'─' * 60}")
        print(f"📡 第 {round_num} 轮爬取")
        print(f"{'─' * 60}")

        # 从调度器取出请求并模拟爬取
        items = []
        while True:
            req = scheduler.next_request()
            if req is None:
                break
            priority, url, callback = req
            items.append(url)

        print(f"  爬取 {len(items)} 个商品页面")

        # 模拟获取数据
        products = simulate_crawl_round(round_num)

        # 通过 Pipeline 处理
        processed = 0
        dropped = 0
        for product in products:
            try:
                # 清洗
                product = clean.process(product)
                # 验证
                product = validate.process(product)
                if product is None:
                    dropped += 1
                    continue
                # 价格预警
                product = alert_pipeline.process(product)
                # 存储
                storage.process(product)
                # 统计
                analyzer.record(product)
                processed += 1

                # 显示结果
                alert_icon = '🔔' if '降价' in product.alert else '📈' if '涨价' in product.alert else '➖'
                print(f"  {alert_icon} {product.name}: ¥{product.price} [{product.alert}]")

            except Exception as e:
                dropped += 1
                print(f"  ❌ 处理失败: {e}")

        print(f"  ✅ 本轮: {processed} 条处理, {dropped} 条丢弃")

        # 爬取间隔
        if round_num < NUM_ROUNDS:
            print(f"\n  ⏳ 等待 1 秒后开始下一轮...")
            time.sleep(1)

    # 关闭存储
    storage.close()

    # 生成统计报告
    print(f"\n{'=' * 60}")
    print("📊 监控统计报告")
    print(f"{'=' * 60}")

    stats = analyzer.summary()
    print(f"  监控商品数: {stats['total_products']}")
    print(f"  累计记录数: {stats['total_records']}")
    print(f"  价格提醒数: {stats['total_alerts']}")
    print(f"  降价次数:   {stats['price_drops']}")
    print(f"  涨价次数:   {stats['price_rises']}")

    if stats['max_drop']:
        print(f"  最大降幅:   {stats['max_drop']['name']} "
              f"({stats['max_drop']['pct']}%)")

    # 显示调度器统计
    print(f"\n📡 调度器统计:")
    print(f"  入队请求数: {scheduler.stats['enqueued']}")
    print(f"  去重过滤数: {scheduler.stats['filtered']}")
    print(f"  出队请求数: {scheduler.stats['dequeued']}")

    # 显示导出文件
    print(f"\n📄 导出文件 (monitor_output.jsonl):")
    try:
        with open('monitor_output.jsonl', 'r') as f:
            lines = f.readlines()
            print(f"  共 {len(lines)} 条记录")
            for line in lines[:3]:
                data = json.loads(line)
                print(f"  {data['name']}: ¥{data['price']} [{data['alert']}]")
            if len(lines) > 3:
                print(f"  ... 还有 {len(lines) - 3} 条")
    except FileNotFoundError:
        print("  (文件不存在)")

    print(f"\n{'=' * 60}")
    print("✅ 监控完成！")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
