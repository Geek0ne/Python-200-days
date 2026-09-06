# Day 142 — 完成清单与练习

## ✅ 今日清单

- [ ] 阅读 README.md：robots.txt 语法、法律红线、职业道德
- [ ] 运行 `code/01-robots-parser.py`，观察最长前缀匹配结果
- [ ] 运行 `code/02-compliance-checker.py https://www.python.org commercial`
- [ ] 运行 `code/03-polite-crawler.py`，查看 polite_audit.log 审计日志
- [ ] 回答 5 道思考题（至少口头过一遍）

## 📝 练习题

### 基础

1. 写一个函数 `load_robots(url)`，返回该站的 `RobotFileParser`，并对以下路径批量输出允许/禁止：`/`, `/search`, `/static/js/app.js`（自选一个真实网站验证）。
2. 给 `03-polite-crawler.py` 的 `RobotsCache` 增加单测：mock 掉 `rp.read()`，验证 TTL 过期后会重新加载。

### 进阶

3. **合规中间件设计**：把 `PoliteCrawler` 的 robots 检查 + 限速逻辑改写成 Scrapy downloader middleware 的骨架（写出 `process_request` 方法即可，不必跑通 Scrapy）。
4. **断案练习**：某公司 A 爬取公司 B 的公开商品数据并在自己的 App 中展示（含 B 的图片与描述，未标注来源），B 起诉。请从 robots.txt、反不正当竞争、版权三个角度分析 A 的法律风险点。
5. **PII 检测器**：写一个正则集合，检测 HTML 文本中是否含手机号/身份证号/邮箱+姓名组合，命中即拒绝入库——作为爬虫入库前的最后一道合规闸门。

## 🎯 明日预告

Day 143–144 — 阶段项目：全栈反爬突破系统（代理池 + 浏览器模拟 + JS 解析 → 验证码处理 + 数据清洗 → 调度 + 告警 + 容器化）。
