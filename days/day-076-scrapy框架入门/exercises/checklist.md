# Day 076 — 练习清单

## ✅ 今日完成清单

- [ ] 阅读 README.md，理解 Scrapy 架构
- [ ] 运行 01-基础爬虫.py，爬取名言数据
- [ ] 运行 02-pipeline数据处理.py，理解 Pipeline 工作流
- [ ] 运行 03-反爬策略与实战.py，了解反爬应对
- [ ] 完成练习题

---

## 📝 练习题

### 基础题

**1. Scrapy 架构题**
> 画出 Scrapy 的数据流图，标注每个组件的职责。说明 Engine 在其中起到什么作用。

参考要点：
- Spider → Engine → Scheduler → Downloader → Engine → Spider → Pipeline
- Engine 是中枢，协调所有组件之间的数据传递

**2. Selector 练习**
> 给定以下 HTML，用 CSS 选择器提取所有商品名称和价格：
```html
<div class="product">
  <h2 class="name">Python编程</h2>
  <span class="price">79.00</span>
</div>
<div class="product">
  <h2 class="name">算法导论</h2>
  <span class="price">108.00</span>
</div>
```

参考答案：
```python
response.css("h2.name::text").getall()  # ['Python编程', '算法导论']
response.css("span.price::text").getall()  # ['79.00', '108.00']
```

**3. Pipeline 顺序题**
> 如果有三个 Pipeline：A（优先级 300）、B（优先级 100）、C（优先级 200），它们的执行顺序是什么？为什么这样设计？

参考答案：
- 执行顺序：B(100) → C(200) → A(300)
- 数字越小越先执行，这样可以在早期过滤无效数据，减少后续 Pipeline 的处理量

### 进阶题

**4. 去重机制设计**
> Scrapy 默认按 URL 去重。如果需要按「商品ID + 价格」维度去重（同一商品不同 URL），你会如何实现？写出代码思路。

参考思路：
```python
class PriceBasedFilter:
    def __init__(self):
        self.seen = set()
    
    def process_item(self, item, spider):
        key = f"{item['product_id']}:{item['price']}"
        if key in self.seen:
            raise DropItem(f"重复: {key}")
        self.seen.add(key)
        return item
```

**5. 反爬策略设计**
> 某网站同时使用了以下反爬手段：
> - User-Agent 检测
> - 同一 IP 每分钟最多 60 次请求
> - 需要登录才能查看价格
> - 数据通过 JavaScript 动态加载
>
> 设计一个爬虫架构来应对，说明每个问题的解决方案。

参考方案：
1. **UA 检测** → RandomUserAgentMiddleware 轮换
2. **IP 限速** → 自动限速 + 代理池（如 IPIDEA）
3. **登录态** → SessionManager 管理 Cookie，或用 Selenium 模拟登录
4. **JS 渲染** → Splash 或 Playwright 渲染页面后再解析
5. 整体架构：Scrapy + Splash + 代理中间件 + Cookie 中间件

---

## 🏋️ 挑战题

**6. 性能分析**
> 如果要爬取 10000 个页面，分别用以下方案，估算所需时间：
> - A: requests + BeautifulSoup（同步，每页 1 秒）
> - B: Scrapy（16 并发，下载延迟 1 秒）
> - C: Scrapy + AutoThrottle（自动调整）
>
> 哪种方案最快？为什么？

**7. 增量爬取**
> 设计一个增量爬取方案：每天只爬取新增/更新的数据，而不是全量爬取。说明用什么技术手段判断数据是否有更新。
