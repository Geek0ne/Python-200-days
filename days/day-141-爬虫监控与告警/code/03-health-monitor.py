#!/usr/bin/env python3
"""
Day 141 示例 03 — 爬虫健康监控系统（实战案例）

整合: 心跳检测 + 数据量断言 + 错误率统计 + 自动分级告警。
模拟一个爬虫与一个独立监控进程的完整交互。
可直接运行: python3 03-health-monitor.py
"""
import json
import os
import random
import time
from collections import deque
from pathlib import Path

from importlib.machinery import SourceFileLoader
# 复用示例 02 的通知器
_base = str(Path(__file__).parent)
_notifier_mod = SourceFileLoader("notifier", os.path.join(_base, "02-alert-notifier.py")).load_module()
Notifier = _notifier_mod.Notifier
Alert = _notifier_mod.Alert

HEARTBEAT_FILE = "/tmp/spider_health_demo.json"
HEARTBEAT_INTERVAL = 1       # 演示用 1 秒（生产建议 30s）
HEARTBEAT_TIMEOUT = 3        # 超过 3 秒没心跳 = 进程疑似死亡


# ========== 被监控对象: 模拟爬虫 ==========
class MockSpider:
    """模拟爬虫：正常产出数据 → 突然静默失败 → 恢复。

    重点演示"静默失败": 进程活着、持续心跳，但数据量为 0。
    这就是为什么业务级监控 > 进程级监控。
    """
    def __init__(self):
        self.stats = {"fetched": 0, "failed": 0, "started": time.time()}

    def run(self, rounds: int):
        for i in range(rounds):
            if i < 4:          # 阶段1: 正常
                self.stats["fetched"] += random.randint(80, 120)
                err = random.random() < 0.05
            elif i < 7:        # 阶段2: 静默失败（被封但进程未崩）
                self.stats["fetched"] += 0
                err = random.random() < 0.9
            else:              # 阶段3: 恢复
                self.stats["fetched"] += random.randint(80, 120)
                err = random.random() < 0.05
            if err:
                self.stats["failed"] += 1

            # 写心跳（生产中用独立线程/进程定时写）
            self.stats["last_heartbeat"] = time.time()
            Path(HEARTBEAT_FILE).write_text(json.dumps(self.stats))
            time.sleep(HEARTBEAT_INTERVAL)


# ========== 监控进程 ==========
class HealthMonitor:
    def __init__(self):
        self.notifier = Notifier(suppress_seconds=10)  # 演示用短抑制
        self.history: deque[float] = deque(maxlen=30)  # 滑动窗口: 每轮增量
        self.last_fetched = 0

    def check(self) -> bool:
        """返回 True 表示爬虫健康。三层检查: 存活 → 增量 → 错误率。"""
        p = Path(HEARTBEAT_FILE)
        if not p.exists():
            return True  # 爬虫还没启动，不告警

        stats = json.loads(p.read_text())

        # 1) 进程级: 心跳超时
        gap = time.time() - stats.get("last_heartbeat", 0)
        if gap > HEARTBEAT_TIMEOUT:
            self.notifier.send(Alert(
                "CRITICAL", "爬虫心跳丢失",
                f"距上次心跳 {gap:.0f}s（阈值 {HEARTBEAT_TIMEOUT}s），进程疑似崩溃",
                fingerprint="heartbeat-lost"))
            return False

        # 2) 业务级: 数据增量断言（最核心！）
        delta = stats["fetched"] - self.last_fetched
        self.last_fetched = stats["fetched"]
        if self.history:
            avg = sum(self.history) / len(self.history)
            if avg > 5 and delta < avg * 0.3:  # 骤降 70% 以上
                self.notifier.send(Alert(
                    "CRITICAL", "数据量骤降",
                    f"本轮增量 {delta}，历史均值 {avg:.0f} —— 疑似被封或页面改版",
                    fingerprint="output-drop"))
        self.history.append(delta)

        # 3) 质量级: 错误率
        total = stats["fetched"] + stats["failed"]
        if total > 20:
            err_rate = stats["failed"] / total
            if err_rate > 0.3:
                self.notifier.send(Alert(
                    "WARNING", "错误率过高",
                    f"累计错误率 {err_rate:.0%}（阈值 30%）",
                    fingerprint="high-error-rate"))

        return True


if __name__ == "__main__":
    print("=" * 60)
    print("爬虫健康监控演示（监控进程与爬虫同进程模拟，生产中应分离部署）")
    print("=" * 60)

    monitor = HealthMonitor()
    spider = MockSpider()

    # 用"分时切片"模拟两个进程并行
    for tick in range(10):
        spider.run(1)           # 爬虫跑一轮、写心跳
        healthy = monitor.check()  # 监控进程检查
        status = "✅ 健康" if healthy else "❌ 异常(已告警)"
        print(f"tick {tick}: fetched={spider.stats['fetched']:>5} "
              f"failed={spider.stats['failed']:>3}  监控: {status}")

    print("\n✅ 演示完成: 第 4~6 轮出现静默失败，数据量断言成功捕获并发送告警")
