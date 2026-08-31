# Day 141 — 爬虫监控与告警 · 练习与清单

## ✅ 完成清单

- [ ] 理解为什么"业务级监控 > 进程级监控"（静默失败）
- [ ] 能手写指数退避 + 抖动的重试装饰器
- [ ] 掌握 requests Retry 的 `status_forcelist` / `allowed_methods` 含义
- [ ] 理解钉钉加签的 HMAC-SHA256 原理
- [ ] 实现带告警抑制的多渠道通知器
- [ ] 跑通 03-health-monitor.py，观察静默失败被捕获
- [ ] 回答全部思考题

## 📝 练习题

### 基础

**1.** 写一个 `@retry(times=5, delay=2)` 装饰器（固定间隔即可），并说明固定间隔相比指数退避的缺陷。

**2.** 给下面的函数加上 urllib3 Retry：对 502/503/504 重试最多 3 次，退避因子 2。
```python
import requests
def fetch(session, url):
    return session.get(url, timeout=10).json()
```

### 进阶

**3.** 实现一个"告警升级"机制：WARNING 级别的同一指纹告警，如果 10 分钟内出现 3 次仍存在，自动升级为 CRITICAL 并 @ 所有人。（提示：在 `Notifier` 中为每个指纹维护计数器和首次时间）

**4.** 分布式场景下（10 台机器各跑爬虫），心跳存在 Redis：请写出爬虫端写心跳和监控端批量检查的伪代码（用 `SET key ts EX 120` 与 `SCAN`）。思考：为什么用 Redis 的 TTL 而不是自己比对时间戳？

### 挑战

**5.** 为你的 03-health-monitor.py 增加一个"监控者守护"：每 5 分钟向另一个 webhook 发送 `I'm alive` 心跳；如果外部（如 UptimeRobot 免费服务）连续 2 个周期收不到该心跳，说明监控进程自己挂了，会通过外部渠道通知你。实现这个自报告函数并解释这解决了什么问题。
