# Day 139 - 数据存储管道 完成清单与练习

## ✅ 今日完成清单

- [ ] 理解 Item Pipeline 四个钩子的时机与用途
- [ ] 掌握清洗 -> 校验 -> 去重 -> 入库 四层分层设计
- [ ] 跑通 03-full-data-pipeline.py 并看懂质量报表
- [ ] 理解批量缓冲的意义与崩溃窗口风险
- [ ] 掌握三种幂等写法：ON DUPLICATE KEY UPDATE / upsert / SET
- [ ] 能为爬虫项目做存储选型（Redis/Mongo/MySQL 分工）

## 📝 练习题

### 基础

**1.** 手写一个 `PriceCleaningPipeline`：把 "1,299.00元"、"USD 59.9"、"免费" 分别转成 1299.0、59.9、0.0，非法值 DropItem。

**2.** 解释 `process_item` 不写 `return item` 会发生什么，并用实验验证。

### 进阶

**3.** 给 03 的管道加"定时 flush"：即使不满 BATCH，每 10 秒也强制写库（提示：`threading.Timer` 或 `twisted` 的 `LoopingCall`，注意线程安全）。

**4.** 用 pydantic 重写校验层：定义 `BookModel(title: str, price: float = Field(ge=0), url: HttpUrl)`，统计 ValidationError 的字段级错误分布，输出"哪个字段脏数据最多"。

**5.** 设计题：一天 500 万条数据的爬虫，要求去重且 Redis 内存有限。设计"Redis 近期去重 + MySQL 历史兜底"的两级去重方案，说明两级各自拦截什么。

## 🎯 明日预告

Day 140 - App 爬虫基础：mitmproxy 抓包、反编译 APK 基础、协议模拟。
