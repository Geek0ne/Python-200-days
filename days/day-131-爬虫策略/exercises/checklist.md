# Day 131 - 爬虫策略 完成清单与练习

## ✅ 完成清单

- [ ] 理解环形链接导致的死循环问题与去重的必要性
- [ ] 会写 URL 归一化（fragment/跟踪参数/大小写/末尾斜杠）
- [ ] 会用 set + deque 搭建小规模去重爬虫
- [ ] 理解布隆过滤器原理（bit 数组 + k 哈希 + 假阳性/无假阴性）
- [ ] 会估算 set vs Bloom 的内存差距
- [ ] 会写原子 checkpoint（临时文件 + os.replace）
- [ ] 会实现断点续爬（队列/已访问/数据三态恢复）
- [ ] 会实现令牌桶限速（平均速率 + 突发容量）
- [ ] 会指数退避重试并尊重 Retry-After
- [ ] 知道礼貌爬取清单（robots.txt / 并发控制 / 错峰）

## 📝 练习题

### 练习 1（基础）
用 `urllib.robotparser` 检查 `http://books.toscrape.com/robots.txt` 是否允许爬取 `/catalogue/` 路径，写代码输出结论。

### 练习 2（进阶）
给 01 的 `SimpleBloomFilter` 增加 `false_positive_rate()` 方法：插入 N 个元素后，用一批"确定没插入过"的 URL 实测假阳性率，验证是否接近设计值 1%。

### 练习 3（避坑）
解释：为什么 `json.dump(state, open("ckpt.json","w"))` 这种写 checkpoint 的方式有数据损坏风险？写出正确的原子写法。

### 练习 4（进阶）
实现一个"带优先级的队列"：产品详情页 URL 优先级高于列表页 URL（用 `heapq` + (priority, url) 元组），说明这种策略为什么能更早拿到有价值数据。

### 练习 5（综合）
改造 `03-practical-crawler.py`：
1. 把令牌桶速率从 2/s 降到 0.5/s；
2. 增加失败 URL 的"补爬"功能：程序结束时若 fail_urls 非空，将其写回 checkpoint 的队列头部供下次重试；
3. 实测：运行中途 Ctrl+C，再启动验证续爬生效。
