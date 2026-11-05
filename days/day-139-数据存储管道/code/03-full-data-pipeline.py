# -*- coding: utf-8 -*-
"""
03 - 实战：完整数据管道（清洗 -> 去重 -> 双库 -> 质量报表）

一个可以独立运行的"迷你版生产管道"：
- 用内存版去重（无 Redis 依赖，逻辑与 SADD 完全同构）
- 批量缓冲 + 定量 flush
- 结束时输出数据质量报表（完整性/唯一性/吞吐）

python3 03-full-data-pipeline.py
"""
import time
from collections import Counter

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class QualityReport:
    """第四层：监控统计。生产上对接 Prometheus / 日志平台"""

    def __init__(self):
        self.stats = Counter()
        self.t0 = time.time()
        self.seen_urls = set()

    def count(self, key):
        self.stats[key] += 1

    def emit(self):
        total = self.stats["input"]
        dt = time.time() - self.t0
        print("\n" + "=" * 46)
        print("📊 数据质量报表")
        print("=" * 46)
        print(f"输入总量     : {total}")
        print(f"清洗不合格   : {self.stats['drop_invalid']}")
        print(f"重复丢弃     : {self.stats['drop_dupe']}")
        print(f"成功入库     : {self.stats['stored']}")
        if total:
            print(f"完整率       : {self.stats['stored'] / total:.1%}")
        print(f"唯一 URL 数  : {len(self.seen_urls)}")
        print(f"耗时/吞吐    : {dt:.2f}s ({self.stats['stored'] / max(dt, 1e-9):.0f} 条/秒)")


class FullPipeline:
    """把四层管道串成一个可独立运行的类"""

    BATCH = 4  # 演示用小批量

    def __init__(self):
        self.report = QualityReport()
        self.buffer = []
        self.db = []          # 模拟数据库表

    # ---------- 第一层：清洗 ----------
    def _clean(self, item):
        a = ItemAdapter(item)
        for k, v in list(a.items()):
            if isinstance(v, str):
                a[k] = v.strip()
        if a.get("price") is None:
            a["price"] = 0.0
        if isinstance(a.get("price"), str):
            a["price"] = float(a["price"].replace("¥", ""))
        if not a.get("title") or not a.get("url"):
            self.report.count("drop_invalid")
            raise DropItem(f"缺必填字段: {item}")
        return a.asdict()

    # ---------- 第二层：去重（与 Redis SADD 同构） ----------
    def _dedupe(self, item):
        if item["url"] in self.report.seen_urls:
            self.report.count("drop_dupe")
            raise DropItem(f"重复: {item['url']}")
        self.report.seen_urls.add(item["url"])
        return item

    # ---------- 第三层：缓冲入库 ----------
    def process(self, raw_items):
        for raw in raw_items:
            self.report.count("input")
            try:
                item = self._clean(raw)
                item = self._dedupe(item)
                item["crawled_at"] = time.strftime("%Y-%m-%d %H:%M:%S")  # 溯源字段
                self.buffer.append(item)
                if len(self.buffer) >= self.BATCH:
                    self._flush()
            except DropItem as e:
                print(f"  🗑️ {e}")
        self._flush()  # 收尾 flush，防丢尾批

    def _flush(self):
        if not self.buffer:
            return
        self.db.extend(self.buffer)   # 真实场景: executemany / insert_many
        self.report.stats["stored"] += len(self.buffer)
        print(f"  💾 批量写入 {len(self.buffer)} 条")
        self.buffer = []


if __name__ == "__main__":
    raw = [
        {"title": " 三体 ", "price": "¥45.5", "url": "https://e.com/1"},
        {"title": "", "price": "10", "url": "https://e.com/2"},          # invalid
        {"title": "Python", "price": 89.0, "url": "https://e.com/3"},
        {"title": "算法", "price": "¥55", "url": "https://e.com/4"},
        {"title": "三体", "price": "¥45.5", "url": "https://e.com/1"},   # dupe
        {"title": "数据库", "price": None, "url": "https://e.com/5"},    # price 缺省->0.0
        {"title": "网络", "price": "¥40", "url": "https://e.com/6"},
    ]
    pipe = FullPipeline()
    pipe.process(raw)
    assert len(pipe.db) == 5 and pipe.db[0]["title"] == "三体" and pipe.db[3]["price"] == 0.0
    pipe.report.emit()
    print("\n🎉 完整管道运行通过，db 表如下：")
    for row in pipe.db:
        print("  ", row)
