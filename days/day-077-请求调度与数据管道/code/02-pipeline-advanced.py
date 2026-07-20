"""
02-pipeline-advanced.py
数据管道进阶用法与常见陷阱

运行方式：python3 02-pipeline-advanced.py
无需 Scrapy 环境，用纯 Python 模拟 Pipeline 行为
"""

import json
import time
import logging
from datetime import datetime
from typing import Any, Generator

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# 1. Pipeline 基础框架
# ============================================================

class Pipeline:
    """模拟 Scrapy Pipeline 的基类"""

    def open_spider(self, spider_name: str):
        """爬虫启动时调用"""
        pass

    def close_spider(self, spider_name: str):
        """爬虫关闭时调用"""
        pass

    def process_item(self, item: dict, spider_name: str) -> dict:
        """
        处理每个 Item
        必须返回 item（或抛出 DropItem 丢弃）
        """
        return item


class DropItem(Exception):
    """丢弃数据的异常"""
    pass


class PipelineRunner:
    """模拟 Scrapy 引擎的 Pipeline 执行器"""

    def __init__(self, pipelines: list[tuple[int, Pipeline]]):
        """
        pipelines: [(priority, pipeline_instance), ...]
        数字越小越先执行
        """
        self.pipelines = sorted(pipelines, key=lambda x: x[0])

    def run(self, spider_name: str, items: list[dict]) -> list[dict]:
        """运行所有 Pipeline 处理一批 Item"""
        # 1. open_spider
        for _, pipeline in self.pipelines:
            pipeline.open_spider(spider_name)

        # 2. 处理每个 Item
        results = []
        dropped = 0
        for item in items:
            try:
                current = item
                for _, pipeline in self.pipelines:
                    current = pipeline.process_item(current, spider_name)
                results.append(current)
            except DropItem as e:
                dropped += 1
                logger.warning(f"⚠️ DropItem: {e}")

        # 3. close_spider
        for _, pipeline in self.pipelines:
            pipeline.close_spider(spider_name)

        logger.info(f"✅ 处理完成: {len(results)} 条保留, {dropped} 条丢弃")
        return results


# ============================================================
# 2. 实战 Pipeline：电商数据处理
# ============================================================

class CleanPipeline(Pipeline):
    """数据清洗管道"""

    def process_item(self, item: dict, spider: str) -> dict:
        # 清洗名称
        if 'name' in item and item['name']:
            item['name'] = ' '.join(item['name'].split())

        # 标准化价格
        if 'price' in item:
            try:
                price_str = str(item['price'])
                price_str = price_str.replace('¥', '').replace('$', '').replace(',', '')
                item['price'] = round(float(price_str), 2)
            except ValueError:
                raise DropItem(f"价格格式无效: {item.get('price')}")

        # 标准化评分
        if 'rating' in item and item['rating'] is not None:
            try:
                item['rating'] = round(float(item['rating']), 1)
            except (ValueError, TypeError):
                item['rating'] = None

        return item


class ValidatePipeline(Pipeline):
    """数据验证管道"""

    REQUIRED_FIELDS = ['name', 'price', 'url']

    def process_item(self, item: dict, spider: str) -> dict:
        # 必填字段
        for field in self.REQUIRED_FIELDS:
            if not item.get(field):
                raise DropItem(f"缺少必填字段 '{field}'")

        # 业务规则
        if item['price'] <= 0:
            raise DropItem(f"价格必须大于 0: {item['price']}")
        if item['price'] > 999999:
            raise DropItem(f"价格异常: {item['price']}")

        # URL 格式
        if not item['url'].startswith('http'):
            raise DropItem(f"URL 无效: {item['url']}")

        return item


class PriceAlertPipeline(Pipeline):
    """价格预警管道：记录历史价格，检测降价"""

    def __init__(self):
        self.history = {}

    def process_item(self, item: dict, spider: str) -> dict:
        url = item['url']
        price = item['price']

        if url in self.history:
            last_price = self.history[url][-1]
            if price < last_price:
                discount = (last_price - price) / last_price * 100
                item['alert'] = f"降价 {discount:.1f}%"
                item['discount_pct'] = round(discount, 1)
            elif price > last_price:
                item['alert'] = "涨价"
                item['discount_pct'] = -round(
                    (price - last_price) / last_price * 100, 1
                )
            else:
                item['alert'] = "持平"
                item['discount_pct'] = 0
        else:
            item['alert'] = "首次记录"
            item['discount_pct'] = 0

        self.history.setdefault(url, []).append(price)
        return item


class JsonLinesExportPipeline(Pipeline):
    """JSON Lines 导出管道"""

    def __init__(self, filepath: str = 'output.jsonl'):
        self.filepath = filepath
        self.file = None
        self.count = 0

    def open_spider(self, spider: str):
        self.file = open(self.filepath, 'w', encoding='utf-8')
        self.count = 0
        logger.info(f"📂 打开输出文件: {self.filepath}")

    def close_spider(self, spider: str):
        if self.file:
            self.file.close()
        logger.info(f"📊 共导出 {self.count} 条数据")

    def process_item(self, item: dict, spider: str) -> dict:
        if self.file:
            # 写入前记录时间戳
            item['exported_at'] = datetime.now().isoformat()
            line = json.dumps(item, ensure_ascii=False)
            self.file.write(line + '\n')
            self.file.flush()
            self.count += 1
        return item


# ============================================================
# 3. 常见陷阱演示
# ============================================================

def demo_trap_forget_return():
    """陷阱 1: 忘记 return item"""
    print("\n" + "=" * 60)
    print("⚠️ 陷阱 1: 忘记 return item")
    print("=" * 60)

    class BadPipeline(Pipeline):
        def process_item(self, item, spider):
            item['processed'] = True
            # 忘记 return item！后续管道收不到数据

    class NextPipeline(Pipeline):
        def process_item(self, item, spider):
            print(f"  NextPipeline 收到: {item}")
            return item

    runner = PipelineRunner([
        (100, BadPipeline()),
        (200, NextPipeline()),
    ])

    items = [{'name': 'Test', 'price': 10}]
    results = runner.run('spider', items)
    print(f"  结果: {results}  ← 如果是空列表，说明数据丢失了！")


def demo_trap_wrong_order():
    """陷阱 2: Pipeline 执行顺序错误"""
    print("\n" + "=" * 60)
    print("⚠️ 陷阱 2: Pipeline 执行顺序")
    print("=" * 60)

    class StorePipeline(Pipeline):
        def process_item(self, item, spider):
            print(f"  📦 StorePipeline: 保存 {item}")
            return item

    class CleanPipelineDemo(Pipeline):
        def process_item(self, item, spider):
            item['name'] = item['name'].strip()
            print(f"  🧹 CleanPipeline: 清洗完成")
            return item

    # 错误顺序：存储在前，清洗在后
    print("\n  ❌ 错误顺序 (Store=100, Clean=200):")
    runner_wrong = PipelineRunner([
        (100, StorePipeline()),
        (200, CleanPipelineDemo()),
    ])
    runner_wrong.run('spider', [{'name': '  dirty name  '}])

    # 正确顺序：清洗在前，存储在后
    print("\n  ✅ 正确顺序 (Clean=100, Store=200):")
    runner_right = PipelineRunner([
        (100, CleanPipelineDemo()),
        (200, StorePipeline()),
    ])
    runner_right.run('spider', [{'name': '  dirty name  '}])


def demo_trap_memory_leak():
    """陷阱 3: 内存泄漏"""
    print("\n" + "=" * 60)
    print("⚠️ 陷阱 3: Pipeline 内存泄漏风险")
    print("=" * 60)

    class LeakyPipeline(Pipeline):
        """反面教材：缓存无限增长"""
        def __init__(self):
            self.cache = []  # 无限增长！

        def process_item(self, item, spider):
            self.cache.append(item)  # 每条数据都缓存，永不释放
            return item

    leaky = LeakyPipeline()
    print("  LeakyPipeline 每条 item 都 append 到 self.cache")
    print("  爬取 10 万条数据 → cache 占用大量内存")
    print("  ✅ 解决方案：用数据库存储，或定期清理缓存")


# ============================================================
# 4. 完整 Pipeline 链演示
# ============================================================

def demo_full_pipeline():
    """演示完整的数据处理流程"""
    print("\n" + "=" * 60)
    print("📊 完整 Pipeline 链演示")
    print("=" * 60)

    # 创建 Pipeline 链
    runner = PipelineRunner([
        (100, CleanPipeline()),
        (200, ValidatePipeline()),
        (300, PriceAlertPipeline()),
        (400, JsonLinesExportPipeline('demo_output.jsonl')),
    ])

    # 模拟商品数据（包含脏数据）
    items = [
        # 正常数据
        {
            'name': '  iPhone 15 Pro  ',
            'price': '¥7999',
            'url': 'https://shop.com/p/iphone15',
            'rating': 4.8,
            'shop': 'Apple 官方店',
        },
        # 缺少必填字段
        {
            'name': 'Test Product',
            'price': 999,
            # 缺少 url
        },
        # 价格为 0
        {
            'name': 'Free Product',
            'price': 0,
            'url': 'https://shop.com/p/free',
        },
        # 正常数据（第二次，触发降价检测）
        {
            'name': '  iPhone 15 Pro  ',
            'price': '6999',
            'url': 'https://shop.com/p/iphone15',
            'rating': 4.8,
            'shop': 'Apple 官方店',
        },
        # 正常数据
        {
            'name': 'MacBook Pro 14',
            'price': '14999',
            'url': 'https://shop.com/p/macbook14',
            'rating': 4.9,
            'shop': 'Apple 官方店',
        },
    ]

    print(f"\n📥 输入 {len(items)} 条数据:")
    for i, item in enumerate(items):
        print(f"  {i+1}. {item.get('name', '(无名)')} - {item.get('price', '?')}")

    # 运行 Pipeline
    results = runner.run('ecommerce_spider', items)

    print(f"\n📤 输出 {len(results)} 条数据:")
    for i, item in enumerate(results):
        alert = item.get('alert', '')
        print(f"  {i+1}. {item['name']} - ¥{item['price']} [{alert}]")

    # 读取导出文件
    print(f"\n📄 导出文件内容 (demo_output.jsonl):")
    try:
        with open('demo_output.jsonl', 'r') as f:
            for line in f:
                data = json.loads(line)
                print(f"  {data['name']} ¥{data['price']} [{data['alert']}]")
    except FileNotFoundError:
        print("  (文件不存在)")


# ============================================================
# 主函数
# ============================================================

if __name__ == '__main__':
    print("🐍 Scrapy 数据管道进阶用法演示")
    print("=" * 60)

    demo_full_pipeline()
    demo_trap_forget_return()
    demo_trap_wrong_order()
    demo_trap_memory_leak()

    print("\n" + "=" * 60)
    print("✅ 所有演示完成！")
    print("=" * 60)
