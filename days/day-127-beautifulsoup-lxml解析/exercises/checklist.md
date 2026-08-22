# Day 127 — BeautifulSoup / lxml 解析：练习与检查表

## ✅ 完成清单

- [ ] 掌握 BeautifulSoup 的核心查找方法
- [ ] 熟练使用 CSS 选择器
- [ ] 掌握 lxml 的 XPath 语法
- [ ] 能处理脏 HTML 和异常情况
- [ ] 完成至少 3 道练习题

---

## 📝 基础练习

### 练习 1：选择器练习

从以下 HTML 中提取指定数据：

```html
<div class="container">
    <div class="item" id="item-1">
        <h2 class="title">商品A</h2>
        <span class="price">¥99</span>
        <a href="/detail/1">详情</a>
    </div>
    <div class="item" id="item-2">
        <h2 class="title">商品B</h2>
        <span class="price">¥199</span>
        <a href="/detail/2">详情</a>
    </div>
</div>
```

要求：
1. 提取所有商品名
2. 提取第二个商品的价格
3. 提取所有链接的 href
4. 使用 CSS 选择器和 XPath 各实现一遍

### 练习 2：数据清洗

编写函数清洗以下脏数据：

```python
dirty_data = [
    "  ¥99.00  ",          # 多余空白
    "1,234条评价",          # 逗号分隔
    "4.8⭐",               # 混合字符
    "2024年1月15日",        # 日期格式
    "约500件",             # 带前缀
]

# 目标输出:
# [99.0, 1234, 4.8, "2024-01-15", 500]
```

### 练习 3：表格提取

从以下 HTML 提取表格数据并计算统计信息：

```html
<table>
    <tr><th>姓名</th><th>成绩</th></tr>
    <tr><td>张三</td><td>85</td></tr>
    <tr><td>李四</td><td>92</td></tr>
    <tr><td>王五</td><td>78</td></tr>
</table>
```

要求：
1. 提取为字典列表
2. 计算平均分、最高分、最低分
3. 按成绩排序输出

---

## 🚀 进阶挑战

### 挑战 1：多页爬虫

实现一个分页爬虫：
- 自动检测总页数
- 遍历所有页面提取数据
- 处理翻页的 URL 规律
- 进度显示
- 数据去重

### 挑战 2：嵌套数据提取

从以下 HTML 提取完整的嵌套结构：

```html
<div class="category">
    <h2>电子产品</h2>
    <div class="products">
        <div class="product">
            <h3>手机</h3>
            <ul class="specs">
                <li>屏幕: 6.1寸</li>
                <li>电池: 4500mAh</li>
            </ul>
        </div>
    </div>
</div>
```

要求提取为：
```json
{
    "category": "电子产品",
    "products": [
        {
            "name": "手机",
            "specs": {"屏幕": "6.1寸", "电池": "4500mAh"}
        }
    ]
}
```

### 挑战 3：构建爬虫框架

实现一个功能完整的爬虫框架：
- 支持 CSS 选择器和 XPath
- 自动重试和超时控制
- 请求频率限制
- 数据导出（JSON/CSV/数据库）
- 日志记录
- 配置文件驱动

---

## 💡 思考题

1. **BeautifulSoup vs lxml**：什么时候应该用 BeautifulSoup，什么时候应该用 lxml？

2. **JavaScript 渲染**：如果数据是通过 JavaScript 动态加载的，BeautifulSoup 能提取吗？应该用什么工具？

3. **编码问题**：遇到乱码时应该如何排查和解决？`resp.encoding` 和 `resp.apparent_encoding` 有什么区别？

4. **性能优化**：处理 100MB 的 HTML 文件时，有哪些优化策略？

5. **选择器性能**：`soup.select(".item .title")` 和 `soup.find("div", class_="item").find("h2", class_="title")` 哪个更快？为什么？
