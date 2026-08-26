# Day 128 - Scrapy 框架 完成清单与练习

## ✅ 完成清单

- [ ] 理解 Scrapy 与 requests+bs4 的本质区别（异步并发、组件化）
- [ ] 记住项目结构：items / middlewares / pipelines / settings / spiders
- [ ] 能手写一个包含 start_urls + parse + 翻页的 Spider
- [ ] 熟练使用 CSS 选择器（::text / ::attr()）和基本 XPath
- [ ] 理解 Item 的意义并会定义 Field
- [ ] 会写 Pipeline（process_item / open_spider / close_spider）
- [ ] 知道 Pipeline 数字顺序的重要性
- [ ] 理解 Middleware 的 process_request 返回值语义
- [ ] 会用 scrapy shell 调试选择器
- [ ] 知道 DOWNLOAD_DELAY / AUTOTHROTTLE 的作用

## 📝 练习题

### 练习 1（基础）
写一个 Spider 抓取 books.toscrape.com 首页，只提取所有图书标题和价格，导出为 CSV（提示：`-o books.csv` 或 FEEDS 配置）。

### 练习 2（进阶）
给练习 1 加一个 Pipeline：只保留价格 > £50 的书，并把价格转成 float。统计最终保留了几本。

### 练习 3（进阶）
用 XPath 实现两件事：
1. 找到页面上所有 class 包含 `price` 的元素文本；
2. 找到"链接文字是 next"的超链接的 href（CSS 做不到的那种写法）。

### 练习 4（避坑）
下面这段 Pipeline 代码有什么 bug？会导致什么现象？

```python
class MyPipeline:
    def process_item(self, item, spider):
        item["price"] = float(item["price"].replace("£", ""))
        # （没有 return）
```

### 练习 5（综合）
设计一个两级爬虫：列表页 `http://books.toscrape.com/catalogue/category/books/travel_2/index.html` 的每本书详情页，提取标题、描述、库存数量，并按 URL 去重后存为 JSON Lines 格式。（可参考 code/03，先自己写再看答案。）
