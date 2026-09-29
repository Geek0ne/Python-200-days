"""
Day 076 - Scrapy Pipeline 数据处理示例
演示数据管道的完整工作流：验证→清洗→去重→存储

运行方式（在 Scrapy 项目中使用）：
    将以下类复制到 pipelines.py 并启用

独立运行演示：
    python 02-pipeline数据处理.py
"""
import json
import hashlib
from datetime import datetime


# ============================================================
# 1. 数据模型定义（对应 Scrapy 的 Item）
# ============================================================

class ProductItem:
    """商品数据模型"""
    fields = ["name", "price", "url", "category", "timestamp"]
    
    def __init__(self, **kwargs):
        for field in self.fields:
            setattr(self, field, kwargs.get(field))
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def get(self, key, default=None):
        return getattr(self, key, default)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)
    
    def to_dict(self):
        return {field: getattr(self, field) for field in self.fields}


# ============================================================
# 2. Pipeline 1: 数据验证管道
# ============================================================

class ValidationPipeline:
    """
    验证管道 - 检查数据完整性和合法性
    
    Scrapy 中的 DropItem 异常用于丢弃不合格的数据。
    """
    def __init__(self):
        self.stats = {"passed": 0, "dropped": 0}
    
    def process_item(self, item, spider):
        """
        处理每条数据
        
        在 Scrapy 中，这个方法会在每条 Item 经过时被调用。
        返回 Item 继续传递，或抛出 DropItem 异常丢弃。
        """
        # 检查必填字段
        required_fields = ["name", "price", "url"]
        for field in required_fields:
            if not item.get(field):
                print(f"  ❌ 丢弃: 缺少字段 {field} | {item.get('name', '未知')}")
                self.stats["dropped"] += 1
                return None  # Scrapy 中应该 raise DropItem
        
        # 验证价格格式
        price = item.get("price")
        try:
            price_float = float(price)
            if price_float <= 0:
                print(f"  ❌ 丢弃: 价格无效 ({price}) | {item['name']}")
                self.stats["dropped"] += 1
                return None
        except (ValueError, TypeError):
            print(f"  ❌ 丢弃: 价格格式错误 ({price}) | {item['name']}")
            self.stats["dropped"] += 1
            return None
        
        self.stats["passed"] += 1
        return item


# ============================================================
# 3. Pipeline 2: 数据清洗管道
# ============================================================

class CleanPipeline:
    """
    清洗管道 - 标准化和清理数据
    
    常见清洗操作：
    - 去除首尾空白
    - 标准化格式
    - 统一编码
    """
    def process_item(self, item, spider):
        # 清洗商品名
        name = item.get("name", "")
        name = name.strip()
        name = " ".join(name.split())  # 合并多余空格
        item["name"] = name
        
        # 清洗价格 - 确保是浮点数
        price = item.get("price", 0)
        item["price"] = round(float(price), 2)
        
        # 清洗 URL
        url = item.get("url", "")
        if not url.startswith("http"):
            url = "https://" + url
        item["url"] = url
        
        # 添加时间戳
        item["timestamp"] = datetime.now().isoformat()
        
        print(f"  🧹 清洗完成: {name[:30]} | ¥{item['price']}")
        return item


# ============================================================
# 4. Pipeline 3: 去重管道
# ============================================================

class DuplicateFilterPipeline:
    """
    去重管道 - 基于内容指纹去重
    
    Scrapy 内置的去重是基于 URL 的，
    但有时需要按内容去重（比如同一商品不同 URL）。
    """
    def __init__(self):
        self.seen_fingerprints = set()
        self.stats = {"total": 0, "duplicates": 0}
    
    def get_fingerprint(self, item):
        """生成内容指纹"""
        content = f"{item.get('name', '')}:{item.get('price', 0)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def process_item(self, item, spider):
        self.stats["total"] += 1
        fingerprint = self.get_fingerprint(item)
        
        if fingerprint in self.seen_fingerprints:
            print(f"  🔁 重复跳过: {item['name'][:30]}")
            self.stats["duplicates"] += 1
            return None
        
        self.seen_fingerprints.add(fingerprint)
        return item
    
    def get_stats(self):
        return {
            "总数据": self.stats["total"],
            "去重数": self.stats["duplicates"],
            "保留数": self.stats["total"] - self.stats["duplicates"]
        }


# ============================================================
# 5. Pipeline 4: JSON 存储管道
# ============================================================

class JsonWriterPipeline:
    """
    JSON 存储管道 - 将数据写入 JSON Lines 文件
    
    JSON Lines 格式：每行一个 JSON 对象
    优点：逐行写入，不需要加载全部数据；方便追加。
    """
    def __init__(self, filename="products.jl"):
        self.filename = filename
        self.file = None
        self.count = 0
    
    def open(self):
        """管道启动（Scrapy 中是 open_spider）"""
        self.file = open(self.filename, "w", encoding="utf-8")
        print(f"📁 打开输出文件: {self.filename}")
    
    def close(self):
        """管道关闭（Scrapy 中是 close_spider）"""
        if self.file:
            self.file.close()
            print(f"📁 关闭输出文件，共写入 {self.count} 条数据")
    
    def process_item(self, item, spider):
        """处理每条数据"""
        line = json.dumps(item.to_dict(), ensure_ascii=False) + "\n"
        self.file.write(line)
        self.count += 1
        return item


# ============================================================
# 6. Pipeline 编排器（模拟 Scrapy 的 Pipeline 调度）
# ============================================================

class PipelineRunner:
    """
    模拟 Scrapy 的 Pipeline 执行流程
    
    实际 Scrapy 中，Engine 会按 settings.py 中定义的顺序
    依次调用每个 Pipeline 的 process_item 方法。
    """
    def __init__(self, pipelines):
        self.pipelines = pipelines
    
    def run(self, items):
        """对一组 Item 执行 Pipeline 链"""
        print("=" * 50)
        print("🚀 开始执行 Pipeline 链")
        print("=" * 50)
        
        results = []
        for i, item in enumerate(items, 1):
            print(f"\n--- 处理第 {i} 条数据: {item.get('name', '未知')[:40]} ---")
            
            current_item = item
            for pipeline in self.pipelines:
                current_item = pipeline.process_item(current_item, None)
                if current_item is None:
                    print(f"  ⛔ 被 {pipeline.__class__.__name__} 丢弃")
                    break
            
            if current_item is not None:
                results.append(current_item)
        
        print(f"\n{'=' * 50}")
        print(f"✅ Pipeline 执行完成: {len(items)} 条输入 → {len(results)} 条输出")
        print(f"{'=' * 50}")
        
        return results


# ============================================================
# 7. 模拟数据 + 运行演示
# ============================================================

def main():
    # 模拟爬取到的原始数据（包含脏数据）
    raw_items = [
        ProductItem(name="  Python编程从入门到实践  ", price="79.00", url="example.com/py-book"),
        ProductItem(name="流畅的Python", price="108.00", url="https://example.com/fluent-py"),
        ProductItem(name="", price="59.00", url="example.com/no-name"),           # 缺少名称
        ProductItem(name="算法导论", price="-10", url="example.com/algo"),          # 负价格
        ProductItem(name="  深入理解计算机系统  ", price="139.00", url="csapp.com"),
        ProductItem(name="流畅的Python", price="108.00", url="other.com/fluent"),  # 重复
        ProductItem(name="代码大全", price="not_a_number", url="example.com"),      # 价格格式错误
        ProductItem(name="设计模式", price="69.00", url="example.com/design"),
    ]
    
    # 按顺序执行 Pipeline 链
    pipelines = [
        ValidationPipeline(),    # 100: 先验证
        CleanPipeline(),         # 200: 再清洗
        DuplicateFilterPipeline(),  # 300: 然后去重
    ]
    
    runner = PipelineRunner(pipelines)
    results = runner.run(raw_items)
    
    # 最后用存储管道保存
    writer = JsonWriterPipeline("cleaned_products.jl")
    writer.open()
    for item in results:
        writer.process_item(item, None)
    writer.close()
    
    # 显示最终结果
    print("\n📊 最终结果:")
    for i, item in enumerate(results, 1):
        print(f"  {i}. {item['name']} | ¥{item['price']} | {item['url']}")


if __name__ == "__main__":
    main()
