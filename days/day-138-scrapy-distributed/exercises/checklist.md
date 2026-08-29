# Day 138 - Scrapy 分布式 完成清单与练习

## ✅ 今日完成清单

- [ ] 理解单机 Scrapy 无法分布式的根本原因（状态在内存）
- [ ] 掌握 Scrapy-Redis 三个替换组件：Scheduler / DupeFilter / 队列
- [ ] 会写 RedisSpider（redis_key 注入种子）和 RedisCrawlSpider
- [ ] 理解指纹去重原理（request_fingerprint + Redis SADD 原子性）
- [ ] 跑通 03-cluster-launcher.py 多进程集群模拟
- [ ] 知道 SCHEDULER_PERSIST 的取舍与调试技巧

## 📝 练习题

### 基础

**1.** 手写配置：把一个普通 Scrapy 项目改造成分布式需要改 settings.py 的哪几项？逐项说明作用。

**2.** 用 `redis-cli` 完成三件事：查看待处理队列长度、查看指纹集合大小、清空某个爬虫的全部状态 key。

### 进阶

**3.** 实现一个自定义去重组件 `BloomDupeFilter`：不使用 scrapy-redis 的 RFPDupeFilter，直接调用 RedisBloom 模块的 `BF.ADD`/`BF.EXISTS` 实现概率去重。要求：误判率 0.1%，预计插入 1 亿元素。（提示：`BF.RESERVE key 0.001 100000000`）

**4.** 生产事故排查：3 节点集群跑了一周后 Redis 内存告警（指纹 set 4GB）。给出至少 3 条治理方案，并分析各自的代价（换 Bloom / 定期过期 / 按业务分 key 分实例…）。

**5.** 设计题：如果要求"某个节点挂掉时它正在处理的那批请求不丢失"，你会怎么改？提示：研究 SpiderQueue 的 ZRANGE+ZREM 与"处理中"状态的转移，或考虑队列改用 `BLPOP` + 处理确认机制（类似消息队列的 ack）。

## 🎯 明日预告

Day 139 - 数据存储管道：爬虫数据清洗与结构化、MySQL/Redis/MongoDB 多后端存储、数据质量控制。
