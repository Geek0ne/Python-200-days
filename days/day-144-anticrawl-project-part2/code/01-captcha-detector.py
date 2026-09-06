#!/usr/bin/env python3
"""01-captcha-detector.py — 验证码信号检测 + 分级熔断

不绕过、只检测：把"遇到验证码"变成可观测信号并自动降级。
用法: python3 01-captcha-detector.py
"""
import time
import random

# ---------- 信号定义 ----------
CAPTCHA_TEXT_HINTS = ("captcha", "验证码", "请完成安全验证", "slider", "geetest")
CAPTCHA_PATH_HINTS = ("/captcha/", "/verify", "/challenge")
RATE_LIMIT_STATUS = {403, 412, 429}


class CircuitBreaker:
    """按域名分级熔断。"""

    def __init__(self, pause_seconds=1800):
        self.pause_seconds = pause_seconds
        self.level = {}        # domain -> 当前级别 1/2/3
        self.paused_until = {} # domain -> 时间戳

    def trip(self, domain: str, new_level: int):
        old = self.level.get(domain, 0)
        self.level[domain] = max(old, new_level)
        if new_level >= 2:
            self.paused_until[domain] = time.time() + self.pause_seconds
        print(f"  [熔断] {domain} -> Level {self.level[domain]}"
              + (f"，暂停至 {time.ctime(self.paused_until[domain])}" if new_level >= 2 else ""))

    def allowed(self, domain: str) -> bool:
        until = self.paused_until.get(domain)
        return not until or time.time() >= until

    def reset(self, domain: str):
        if domain in self.level:
            print(f"  [恢复] {domain} 熔断计数清零")
        self.level.pop(domain, None)
        self.paused_until.pop(domain, None)


def detect_captcha(status: int, url: str, body: str) -> tuple[bool, int]:
    """根据响应判断是否命中验证码/风控信号，返回 (是否命中, 熔断级别)。"""
    low = body.lower()
    if any(h in low for h in CAPTCHA_TEXT_HINTS):
        return True, 1                     # 出现验证码文案：轻 -> 换代理重试
    if any(h in url for h in CAPTCHA_PATH_HINTS):
        return True, 2                     # 被重定向到验证页：中 -> 暂停该域
    if status in RATE_LIMIT_STATUS:
        return True, 3 if status == 429 else 2  # 明确限频：重 -> 告警人工
    return False, 0


def fetch(url: str) -> tuple[int, str]:
    """模拟响应（真实场景换成 httpx/Playwright）。"""
    kind = random.random()
    if kind < 0.3:
        return 200, "<html>normal page</html>"
    if kind < 0.5:
        return 200, "<html>请完成安全验证 captcha</html>"
    if kind < 0.7:
        return 302, "redirect -> /captcha/step"
    if kind < 0.9:
        return 403, "forbidden"
    return 429, "too many requests"


def main():
    breaker = CircuitBreaker()
    domain = "example.com"

    for i in range(1, 13):
        if not breaker.allowed(domain):
            print(f"[{i:02d}] 域名处于熔断暂停期，跳过本轮")
            time.sleep(0.2)
            continue
        status, body = fetch(f"https://{domain}/list?page={i}")
        hit, level = detect_captcha(status, f"https://{domain}/list", body)
        if hit:
            print(f"[{i:02d}] 命中验证码信号 (status={status})")
            breaker.trip(domain, level)
            if level == 3:
                print("      -> 📢 推送告警：需要人工介入（此处接 Day 141 告警通道）")
        else:
            print(f"[{i:02d}] ✅ 正常抓取 (status={status})")
            breaker.reset(domain)
        time.sleep(0.2)

if __name__ == "__main__":
    main()
