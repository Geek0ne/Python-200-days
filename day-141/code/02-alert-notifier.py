#!/usr/bin/env python3
"""
Day 141 示例 02 — 告警通知器（进阶用法 / 避坑）

支持: 钉钉(加签) / 企业微信 / 控制台降级。
进阶点:
  1. 告警分级 (WARNING / CRITICAL)
  2. 告警抑制 —— 同一指纹 1 小时内只发一次，防止告警风暴
可直接运行: python3 02-alert-notifier.py
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

# ====== 配置区：换成你自己的机器人 ======
DINGTALK_WEBHOOK = ""   # 如 https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET = ""    # 加签密钥 SEC 开头
WECOM_WEBHOOK = ""      # 如 https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx


# ========== 1. 钉钉加签（避坑：URL 泄露防护） ==========
def dingtalk_signed_url() -> str:
    """钉钉加签原理:
    string_to_sign = f"{timestamp}\\n{secret}"
    sign = base64(hmac_sha256(secret, string_to_sign))
    钉钉服务端用相同 secret 重新计算并比对，防止 webhook 被盗用。
    """
    if not DINGTALK_WEBHOOK or not DINGTALK_SECRET:
        return ""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{DINGTALK_SECRET}"
    sign = base64.b64encode(
        hmac.new(DINGTALK_SECRET.encode(), string_to_sign.encode(),
                 digestmod=hashlib.sha256).digest()
    )
    return (f"{DINGTALK_WEBHOOK}"
            f"&timestamp={timestamp}&sign={urllib.parse.quote_plus(sign)}")


# ========== 2. 通知器：多渠道 + 自动降级 ==========
@dataclass
class Alert:
    """告警对象：分级 + 指纹（用于抑制去重）。"""
    level: str            # WARNING / CRITICAL
    title: str
    detail: str
    fingerprint: str = ""  # 同一指纹的告警会被抑制
    ts: float = field(default_factory=time.time)

    def render(self) -> str:
        icon = {"WARNING": "⚠️", "CRITICAL": "🚨"}.get(self.level, "ℹ️")
        t = time.strftime("%H:%M:%S", time.localtime(self.ts))
        return f"{icon} [{self.level}] {self.title}\n{t}\n{self.detail}"


class Notifier:
    """多渠道通知器，带告警抑制（核心避坑点）。

    避坑: 不做抑制的话，爬虫一旦挂掉，每分钟发一条告警，
    一晚上 60 条消息会把群轰炸到没人看 —— "狼来了"效应，
    真正严重的事故反而被忽略。
    """

    def __init__(self, suppress_seconds: int = 3600):
        self.suppress_seconds = suppress_seconds
        self._recent: dict[str, float] = {}  # fingerprint -> last send time

    def _suppressed(self, fp: str) -> bool:
        now = time.time()
        last = self._recent.get(fp, 0)
        if now - last < self.suppress_seconds:
            return True
        self._recent[fp] = now
        return False

    def send(self, alert: Alert) -> bool:
        fp = alert.fingerprint or alert.title
        if self._suppressed(fp):
            print(f"[抑制] 告警 '{fp}' 在 {self.suppress_seconds}s 内已发过，跳过")
            return False

        sent = False
        # 渠道 1: 钉钉
        url = dingtalk_signed_url()
        if url:
            payload = {"msgtype": "text", "text": {"content": alert.render()}}
            sent |= self._post(url, payload)
        # 渠道 2: 企业微信
        if WECOM_WEBHOOK:
            payload = {"msgtype": "text", "text": {"content": alert.render()}}
            sent |= self._post(WECOM_WEBHOOK, payload)
        # 渠道 3: 控制台降级（没配置 webhook 时也能看到告警）
        if not sent:
            print("[降级->控制台]", alert.render())
        return sent

    @staticmethod
    def _post(url: str, payload: dict) -> bool:
        """发 POST。注意：告警发送本身也必须 try/except，
        通知渠道挂了不能把爬虫监控进程一起带崩（避坑）。"""
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            print(f"[通知失败] {e!r}")
            return False


if __name__ == "__main__":
    notifier = Notifier(suppress_seconds=3600)

    a1 = Alert("CRITICAL", "爬虫 spider-x 零产出",
               "最近 30 分钟新增数据 0 条（历史均值 1200 条/30min）",
               fingerprint="spider-x-zero-output")
    a2 = Alert("WARNING", "代理池不足",
               "可用代理 3 个（阈值 10）", fingerprint="proxy-pool-low")

    notifier.send(a1)
    notifier.send(a2)
    # 演示抑制：同一指纹再发会被拦截
    notifier.send(Alert("CRITICAL", "爬虫 spider-x 零产出",
                        "重复告警", fingerprint="spider-x-zero-output"))
    print("\n✅ 未配置 webhook 时自动降级到控制台输出，流程不中断")
