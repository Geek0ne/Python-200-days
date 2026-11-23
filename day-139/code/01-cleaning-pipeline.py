# -*- coding: utf-8 -*-
"""
01 - 数据清洗与校验 Pipeline（基础用法）

演示：
1. CleaningPipeline：去空白、类型转换、默认值
2. ValidationPipeline：必填字段校验，不合格 DropItem
3. process_item 必须 return item（否则管道断裂）

可直接运行：python3 01-cleaning-pipeline.py
"""
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


# ===== 模拟一个爬虫产出的脏数据 =====
RAW_ITEMS = [
    {"title": "  三体  ", "price": "￥45.50", "url": "https://example.com/1"},   # 需清洗
    {"title": "", "price": "30", "url": "https://example.com/2"},                # 缺 title -> 丢弃
    {"title": "Python入门", "price": None, "url": "https://example.com/3"},      # price 缺省
    {"title": "干净的", "price": "12.0", "url": "https://example.com/4"},        # 直接合格
]


class CleaningPipeline:
    """第一层：把人类世界的脏格式转成标准类型"""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # 1) 字符串去空白
        for k, v in adapter.items():
            if isinstance(v, str):
                adapter[k] = v.strip()
        # 2) 价格 "￥45.50" -> 45.50
        price = adapter.get("price")
        if isinstance(price, str):
            adapter["price"] = float(price.replace("￥", "").replace("¥", "").replace(",", ""))
        # 3) 默认值
        if adapter.get("price") is None:
            adapter["price"] = 0.0
        return item          # ⚠️ 必须 return，否则下一层管道收不到数据


class ValidationPipeline:
    """第二层：业务校验，不合格直接丢弃并给出原因"""

    REQUIRED = ("title", "url")

    def __init__(self):
        self.dropped = 0

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        for field in self.REQUIRED:
            if not adapter.get(field):
                self.dropped += 1
                # DropItem 不会让爬虫崩溃，只是优雅丢弃 + 记录
                raise DropItem(f"缺少必填字段: {field}, item={item}")
        if adapter.get("price", 0) < 0:
            self.dropped += 1
            raise DropItem(f"价格非法: {adapter['price']}")
        return item


if __name__ == "__main__":
    cleaning = CleaningPipeline()
    validation = ValidationPipeline()

    class FakeSpider:
        name = "fake"

    ok = []
    for raw in RAW_ITEMS:
        try:
            item = cleaning.process_item(raw, FakeSpider)     # 第一层
            item = validation.process_item(item, FakeSpider)  # 第二层
            ok.append(item)
        except DropItem as e:
            print(f"🗑️  丢弃: {e}")

    print(f"\n✅ 合格数据 {len(ok)} 条 / 共 {len(RAW_ITEMS)} 条:")
    for it in ok:
        print("  ", it)
    assert ok[0]["title"] == "三体" and ok[0]["price"] == 45.5
    assert ok[1]["price"] == 0.0
    print("\n🎉 清洗与校验管道测试通过")
