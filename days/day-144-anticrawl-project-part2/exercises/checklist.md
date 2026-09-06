# Day 144 — 完成清单与练习

## ✅ 今日清单

- [ ] 阅读 README.md：验证码策略、清洗管线、调度与告警
- [ ] 运行 `code/01-captcha-detector.py`，观察分级熔断触发
- [ ] 运行 `code/02-data-cleaner.py`（无输入文件时用内置脏数据），核对清洗报告
- [ ] 运行 `code/03-scheduler-alert.py`（先 `pip install apscheduler`），观察 30s 一轮与状态文件
- [ ] 回答 5 道思考题
- [ ] 回顾 Day 142–144 三日项目，画出完整系统架构图（自检）

## 📝 练习题

### 基础

1. 给 `detect_captcha` 增加一个"空响应体"信号（body 长度 < 50 视为可疑），并补充对应测试用例。
2. 给 `02-data-cleaner.py` 增加 `--dry-run` 参数：只输出报告不写文件。

### 进阶

3. **布隆过滤器**：用 `pybloom-live`（或手写 bitmap 版）替换 `seen` 字典做去重，测试 10 万条数据下的内存占用差异。
4. **告警去重**：同一域名 10 分钟内只告警一次，其余聚合为"已重复 N 次"——在 `send_alert` 外实现告警节流器。
5. **Compose 化**：把 Dockerfile 拆成两个服务（scheduler + 独立的 headless-browser 容器走 CDP），写出 `docker-compose.yml`。

## 🎯 里程碑

至此 Day 142–144「全栈反爬突破系统」阶段项目完成。下一阶段 Phase 10（Day 146 起）：网络安全开发。
