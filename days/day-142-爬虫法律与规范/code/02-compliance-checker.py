#!/usr/bin/env python3
"""02-compliance-checker.py — 抓取前合规自检（避坑清单代码化）

把 Day 142 的法律红线与职业道德落成可执行的检查项。
用法: python3 02-compliance-checker.py <目标URL> [用途: research|commercial]
"""
import sys
import time
from urllib import robotparser
from urllib.parse import urlparse

# 避坑清单：
# 1. URL 必须是 http/https
# 2. 目标不能要求登录/绕过验证码（这里以人工声明为准）
# 3. robots.txt 必须允许
# 4. 必须配置真实可联系的 User-Agent
# 5. 必须限速（Crawl-delay 或默认 2 秒）
# 6. 商业用途需额外评估"实质性替代"风险

DEFAULT_DELAY = 2.0  # 秒

def check_scheme(url: str) -> list:
    issues = []
    o = urlparse(url)
    if o.scheme not in ("http", "https"):
        issues.append("BLOCK: URL 必须是 http/https")
    if not o.netloc:
        issues.append("BLOCK: URL 缺少主机名")
    return issues

def check_robots(url: str, ua: str) -> tuple:
    o = urlparse(url)
    base = f"{o.scheme}://{o.netloc}"
    rp = robotparser.RobotFileParser()
    rp.set_url(base + "/robots.txt")
    try:
        rp.read()
    except Exception as e:
        return None, f"WARN: robots.txt 读取失败({e})，按惯例视为允许，但请人工确认"
    allowed = rp.can_fetch(ua, url)
    delay = rp.crawl_delay(ua) or DEFAULT_DELAY
    issues = []
    if not allowed:
        issues.append("BLOCK: robots.txt 禁止抓取该路径")
    else:
        issues.append(f"OK: robots.txt 允许，Crawl-delay={delay}s")
    return allowed, issues

class ComplianceReport:
    def __init__(self, url):
        self.url = url
        self.blocks, self.warns, self.oks = [], [], []

    def add(self, msgs):
        for m in msgs or []:
            if m.startswith("BLOCK"):
                self.blocks.append(m)
            elif m.startswith("WARN"):
                self.warns.append(m)
            else:
                self.oks.append(m)

    def summary(self) -> str:
        lines = [f"📋 合规自检报告 — {self.url}"]
        lines += [f"  ✅ {m[3:]}" for m in self.oks]
        lines += [f"  ⚠️  {m[5:]}" for m in self.warns]
        lines += [f"  ⛔ {m[6:]}" for m in self.blocks]
        verdict = "❌ 不建议抓取" if self.blocks else ("⚠️ 谨慎评估" if self.warns else "✅ 可礼貌抓取")
        lines.append(f"结论: {verdict}")
        return "\n".join(lines)

def run(url: str, purpose: str = "research") -> ComplianceReport:
    rep = ComplianceReport(url)

    # 检查 1：URL 合法性
    rep.add(check_scheme(url))

    # 检查 2：UA 规范（职业道德）
    ua = "MyPoliteBot/1.0 (+https://example.com/bot; contact@example.com)"
    rep.add([f"OK: User-Agent 已包含联系方式: {ua.split('(')[0]}"])

    # 检查 3：robots.txt
    allowed, msg = check_robots(url, ua)
    rep.add(msg if isinstance(msg, list) else [msg])

    # 检查 4：用途风险评估
    if purpose == "commercial":
        rep.add(["WARN: 商业用途 —— 评估是否'实质性替代'原站服务（反不正当竞争风险）"])
    else:
        rep.add(["OK: 个人研究用途，非商业、不传播"])

    # 检查 5：PII 提醒（无法程序化判断，仅提醒）
    rep.add(["WARN: 请人工确认目标数据不含个人信息（手机号/身份证/住址等）"])

    return rep

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    target = sys.argv[1]
    purpose = sys.argv[2] if len(sys.argv) > 2 else "research"
    report = run(target, purpose)
    print(report.summary())
