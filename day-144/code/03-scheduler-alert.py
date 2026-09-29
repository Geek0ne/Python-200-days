#!/usr/bin/env python3
"""03-scheduler-alert.py — APScheduler 定时调度 + Webhook 告警 + Docker 化

整合 Day 142-144：定时跑"取数+清洗"迷你任务，失败率超阈值时
通过钉钉/企微 Webhook 告警（WEBHOOK_URL 未配置时打印到控制台）。

依赖: pip install apscheduler httpx
用法: python3 03-scheduler-alert.py   (Ctrl+C 退出)
"""
import json
import os
import random
import time

import httpx

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    sys_exit = __import__("sys").exit
    sys_exit("请先安装: pip install apscheduler")

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # 钉钉/企微机器人 Webhook
FAIL_RATE_THRESHOLD = 0.3  # 清洗失败率超过 30% 触发告警
STATE_FILE = "pipeline_state.json"


# ---------- 告警（复用 Day 141 思路，兼容钉钉/企微） ----------
def send_alert(text: str):
    if not WEBHOOK_URL:
        print(f"📢 [告警-未配置Webhook] {text}")
        return
    # 钉钉与企微的 text 消息格式恰好兼容
    payload = {"msgtype": "text", "text": {"content": f"[爬虫系统] {text}"}}
    try:
        r = httpx.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"📢 告警已发送: {r.status_code}")
    except Exception as e:
        print(f"📢 告警发送失败: {e}")


# ---------- 模拟一轮"取数+清洗"任务 ----------
def run_pipeline_job():
    print(f"\n[{time.strftime('%H:%M:%S')}] 定时任务触发：取数+清洗")
    fetched = random.randint(8, 20)
    failed = random.randint(0, fetched)
    fail_rate = failed / fetched
    stats = {"time": time.strftime("%F %T"), "fetched": fetched,
             "failed": failed, "fail_rate": round(fail_rate, 2)}

    print(f"  抓取 {fetched} 条，失败 {failed} 条，失败率 {fail_rate:.0%}")
    if fail_rate > FAIL_RATE_THRESHOLD:
        send_alert(f"失败率超阈值: {fail_rate:.0%} > {FAIL_RATE_THRESHOLD:.0%}，请检查代理池/目标站点状态")

    # 状态持久化（Docker volume 挂这个目录）
    state = []
    if os.path.exists(STATE_FILE):
        try:
            state = json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            state = []
    state.append(stats)
    json.dump(state[-50:], open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    sched = BackgroundScheduler(timezone="Asia/Shanghai")
    # 每 30 秒演示一次；生产环境改为 cron 凌晨低峰: hour=3, minute=0
    sched.add_job(run_pipeline_job, "interval", seconds=30,
                  max_instances=1,          # 上一轮没跑完不许再起一轮
                  misfire_grace_time=60)    # 错过触发的宽限期
    sched.start()
    print("调度器已启动（每 30s 一轮，Ctrl+C 退出）")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        sched.shutdown()
        print("调度器已停止")


# ---------- Docker 化（本文件配套的 Dockerfile 内容见下） ----------
DOCKERFILE = '''
FROM python:3.12-slim
RUN pip install --no-cache-dir httpx apscheduler playwright \
    && playwright install --with-deps chromium
WORKDIR /app
COPY . .
VOLUME ["/app/data"]
ENV TZ=Asia/Shanghai
CMD ["python3", "03-scheduler-alert.py"]
'''

if __name__ == "__main__":
    main()
