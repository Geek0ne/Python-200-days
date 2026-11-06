#!/usr/bin/env python3
"""02 - IM 机器人 Webhook 告警：钉钉 / 企业微信 / Slack 统一封装

对应 ROADMAP「Day 171 — 企业微信/钉钉机器人、Slack Webhook」。

⭐ 本课最重要的一个认知（本机真机实测得出）：
   **HTTP 200 不代表发送成功！**
   钉钉和企业微信的失败也返回 HTTP 200，真正的错误在 body 的 errcode 里。
   如果你只写 requests.post(url, json=payload).raise_for_status()，
   告警会在「token 写错」「被限流」「被拉黑」时全部静默丢失 —— 而你永远不知道。
   详见 --probe 参数，它会真连官方端点把这件事演示给你看。

运行：
    python3 02-webhook-notify.py --self-test     # 离线自检（本地 HTTP 模拟各种故障）
    python3 02-webhook-notify.py --probe         # 真连官方端点（需外网），演示 200+errcode
    python3 02-webhook-notify.py --demo          # 用本地模拟服务器演示正常发送
    python3 02-webhook-notify.py --dry-run       # 只打印 payload，不发任何请求
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore  # --self-test 会用 stdlib 兜底

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:  # pragma: no cover
    pass


# ==========================================================================
# 通道抽象
# ==========================================================================
@dataclass
class NotifyResult:
    """统一的发送结果。无论哪个渠道，都归一化成这个结构。"""
    ok: bool
    channel: str
    status_code: int = 0
    errcode: int = 0
    errmsg: str = ""
    elapsed_ms: float = 0.0
    attempts: int = 1
    payload: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return (f"[{self.channel}] ok={self.ok} http={self.status_code} "
                f"errcode={self.errcode} errmsg={self.errmsg!r} "
                f"elapsed={self.elapsed_ms:.0f}ms attempts={self.attempts}")


class WebhookChannel:
    """所有 IM 机器人的抽象基类。子类只需实现 build_payload 与 interpret。"""

    name = "base"
    #: 该平台是否把失败编码在 HTTP 200 的 body 里（钉钉/企业微信：True）
    errcode_in_body = True

    def build_payload(self, title: str, body: str, level: str = "info",
                      at_mobiles: list[str] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def interpret(self, status: int, data: Any) -> tuple[bool, int, str]:
        """把 (HTTP 状态, body) 归一化成 (是否成功, errcode, errmsg)。"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 统一发送逻辑（含重试与退避）
    # ------------------------------------------------------------------
    def send(self, url: str, title: str, body: str, level: str = "info",
             retries: int = 3, backoff_base: float = 1.0,
             timeout: float = 10.0,
             dry_run: bool = False) -> NotifyResult:
        payload = self.build_payload(title, body, level)
        if dry_run:
            print(f"[DRY-RUN] {self.name} payload = "
                  f"{json.dumps(payload, ensure_ascii=False)[:300]}")
            return NotifyResult(True, self.name, payload=payload)

        headers = {"Content-Type": "application/json; charset=utf-8"}
        last = NotifyResult(False, self.name, payload=payload)
        for attempt in range(1, retries + 1):
            t0 = time.perf_counter()
            try:
                status, data = self._post(url, json.dumps(payload).encode("utf-8"), headers, timeout)
                ok, code, msg = self.interpret(status, data)
                last = NotifyResult(ok, self.name, status, code, msg,
                                    (time.perf_counter() - t0) * 1000, attempt, payload)
                if ok:
                    return last
                # 限流（钉钉 410100 / 企业微信 45009）值得退避重试
                if not self._is_rate_limited(code):
                    return last          # token 错误这类，重试也没用，立刻返回
            except Exception as e:                                   # 网络层异常
                last = NotifyResult(False, self.name, 0, 0, f"{type(e).__name__}: {e}",
                                    (time.perf_counter() - t0) * 1000, attempt, payload)
            if attempt < retries:
                time.sleep(backoff_base * (2 ** (attempt - 1)))
        return last

    @staticmethod
    def _is_rate_limited(code: int) -> bool:
        # 钉钉 130101/410100、企业微信 45009、Slack 429
        return code in (410100, 130101, 45009, 429)

    def _post(self, url: str, body: bytes, headers: dict[str, str],
              timeout: float) -> tuple[int, Any]:
        if requests is not None:
            r = requests.post(url, data=body, headers=headers, timeout=timeout)
            try:
                return r.status_code, r.json()
            except ValueError:
                return r.status_code, r.text
        # 无 requests 时的 stdlib 兜底（保证 --self-test 零依赖可跑）
        req = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                status = resp.status
        except HTTPError as e:
            raw, status = e.read().decode("utf-8", errors="replace"), e.code
        try:
            return status, json.loads(raw)
        except ValueError:
            return status, raw


# ==========================================================================
# 钉钉
# ==========================================================================
class DingTalk(WebhookChannel):
    """
    端点： https://oapi.dingtalk.com/robot/send?access_token=xxx
    安全设置可勾选「加签」（sign）或「自定义关键词」（keyword）。
    加签 = HMAC-SHA256(timestamp + "\n" + secret)，结果 URL-encode 后作为
           &timestamp= &sign= 传参。本实现两种都支持。

    实测错误码（真连官方端点得出）：
      300005  token is not exist        ← token 写错/机器人被删
      310000  keywords not in content   ← 没勾关键词时消息里必须含关键词
      130101  send too fast             ← 限流
      400013  不在白名单的 IP / 签名错误等
    注意：以上错误全部返回 HTTP 200！
    """
    name = "dingtalk"

    def __init__(self, secret: str | None = None, keywords: list[str] | None = None):
        self.secret = secret
        self.keywords = keywords or []

    @staticmethod
    def sign(secret: str, timestamp_ms: int) -> tuple[str, str]:
        """加签：返回 (timestamp_str, urlencoded_sign)。"""
        import base64
        import hashlib
        import hmac
        from urllib.parse import quote

        ts = str(timestamp_ms)
        payload = f"{ts}\n{secret}"
        digest = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
        sign_b64 = base64.b64encode(digest).decode()
        return ts, quote(sign_b64)

    def build_payload(self, title: str, body: str, level: str = "info",
                      at_mobiles: list[str] | None = None) -> dict[str, Any]:
        # 自定义关键词模式：把关键词塞进正文，否则机器人直接拒收
        text = f"{title}\n{body}"
        for kw in self.keywords:
            if kw not in text:
                text = f"{kw}\n{text}"
        payload: dict[str, Any] = {
            "msgtype": "text",
            "text": {"content": text},
            "at": {"atMobiles": at_mobiles or [], "isAtAll": level == "critical"},
        }
        if level == "critical":          # 加签模式可以不带关键词
            text = f"{title}\n{body}"
            payload["text"]["content"] = text
        return payload

    def url(self, access_token: str) -> str:
        base = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"
        if self.secret:
            ts, sign = self.sign(self.secret, int(time.time() * 1000))
            return f"{base}&timestamp={ts}&sign={sign}"
        return base

    def interpret(self, status: int, data: Any) -> tuple[bool, int, str]:
        if not isinstance(data, dict):
            return False, -1, f"非 JSON 响应: {data!r}"
        code = int(data.get("errcode", -1))
        msg = str(data.get("errmsg", ""))
        return (code == 0), code, msg


# ==========================================================================
# 企业微信（群机器人）
# ==========================================================================
class WeCom(WebhookChannel):
    """
    端点： https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
    实测错误码（真连官方端点得出）：
      93000   invalid webhook url       ← key 写错
      40001   不合法
      45009   接口调用超过限制          ← 限流，每机器人 20 条/分钟
    ⚠️ 同样全部返回 HTTP 200。
    """
    name = "wecom"

    def build_payload(self, title: str, body: str, level: str = "info",
                      at_mobiles: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "msgtype": "markdown",
            "markdown": {"content": f"## {title}\n{body}"},
        }
        if at_mobiles:
            payload["at"] = {"atMobiles": at_mobiles, "isAtAll": False}
        elif level == "critical":
            # 企业微信群机器人要真正 @ 人，必须写进 markdown 内容的 mentioned_list
            payload["markdown"]["content"] += '\n<font color="warning">请立即处理</font>'
        return payload

    def interpret(self, status: int, data: Any) -> tuple[bool, int, str]:
        if not isinstance(data, dict):
            return False, -1, f"非 JSON 响应: {data!r}"
        code = int(data.get("errcode", -1))
        return (code == 0), code, str(data.get("errmsg", ""))


# ==========================================================================
# Slack Incoming Webhook
# ==========================================================================
class Slack(WebhookChannel):
    """
    端点： https://hooks.slack.com/services/T000/B000/xxxx
    Slack 的失败语义与前两家相反：
      - 200 + "ok"        → 成功
      - 4xx / 5xx / 302  → 失败（body 是纯文本 human-readable 错误，不是 JSON）
    所以这里的 errcode_in_body = False。
    实测：随便打一个假路径返回 HTTP 302。
    """
    name = "slack"
    errcode_in_body = False

    def build_payload(self, title: str, body: str, level: str = "info",
                      at_mobiles: list[str] | None = None) -> dict[str, Any]:
        icon = {"critical": ":rotating_light:", "warn": ":warning:"}.get(level, ":information_source:")
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"{icon} {title}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": body}},
            {"type": "context",
             "elements": [{"type": "mrkdwn", "text": f"level={level}"}]},
        ]
        return {"text": f"{title}: {body[:100]}", "blocks": blocks}  # text 是降级文本

    def interpret(self, status: int, data: Any) -> tuple[bool, int, str]:
        if 200 <= status < 300:
            return True, 0, str(data)
        return False, status, str(data)


# ==========================================================================
# 自检：本地 HTTP 服务器模拟各种真实故障
# ==========================================================================
def _mock_server(behaviors: dict[str, Any]):
    """起一个本地 HTTP 服务器，按 URL 路径返回预设行为。返回 (srv, port, hits)。"""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    hits: list[str] = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append(self.path)
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n).decode("utf-8")
            resp = behaviors.get(self.path, {"status": 200, "body": {"errcode": 0, "errmsg": "ok"}})
            body = json.dumps(resp["body"], ensure_ascii=False).encode()
            self.send_response(resp["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1], hits


def self_test() -> int:
    ok = True
    base = "http://127.0.0.1:"

    # --- 1. 正常路径 ---
    srv, port, hits = _mock_server({})
    dt = DingTalk()
    r = dt.send(f"{base}{port}/ok", "磁盘告警", "使用率 91%", retries=1)
    assert r.ok and r.errcode == 0, r
    print(f"OK 正常发送: {r}")
    srv.shutdown(); srv.server_close()

    # --- 2. ⭐ HTTP 200 + errcode!=0（钉钉 token 错误的真实形态）---
    srv, port, hits = _mock_server({
        "/bad": {"status": 200, "body": {"errcode": 300005, "errmsg": "token is not exist"}}
    })
    r = DingTalk().send(f"{base}{port}/bad", "x", "y", retries=1)
    assert r.status_code == 200, r
    assert r.ok is False and r.errcode == 300005, f"200 被误判为成功！{r}"
    print(f"OK 核心陷阱: HTTP 200 但 errcode=300005 被正确识别为失败 -> {r}")

    # 3. 限流：应该重试，而且要退避
    srv, port, hits = _mock_server({
        "/rl": {"status": 200, "body": {"errcode": 45009, "errmsg": "接口调用超过限制"}}
    })
    t0 = time.perf_counter()
    r = WeCom().send(f"{base}{port}/rl", "x", "y", retries=3, backoff_base=0.1)
    el = time.perf_counter() - t0
    assert len(hits) == 3, f"限流应重试 3 次，实际 {len(hits)}"
    assert r.ok is False and r.errcode == 45009, r
    assert el >= 0.1 + 0.2, f"退避未生效，耗时 {el:.3f}s"
    print(f"OK 限流退避: 重试 {len(hits)} 次，总耗时 {el*1000:.0f}ms（>=300ms）-> {r}")

    # 4. token 错误不该重试（重试无意义，会加剧限流）
    srv, port, hits = _mock_server({
        "/tok": {"status": 200, "body": {"errcode": 300005, "errmsg": "token is not exist"}}
    })
    DingTalk().send(f"{base}{port}/tok", "x", "y", retries=5, backoff_base=0.01)
    assert len(hits) == 1, f"永久错误应只发 1 次，实际 {len(hits)} 次（重试风暴！）"
    print(f"OK 永久错误不重试: 5 次 retries 配置下实际只发 {len(hits)} 次")
    srv.shutdown(); srv.server_close()

    # --- 5. Slack：失败是 4xx + 纯文本，不是 JSON ---
    srv, port, hits = _mock_server({"/s": {"status": 404, "body": "no_service"}})
    r = Slack().send(f"{base}{port}/s", "x", "y", retries=1)
    assert r.ok is False and r.errcode == 404, r
    print(f"OK Slack 语义不同: 4xx 判失败且不解析 JSON -> {r}")
    srv.shutdown(); srv.server_close()

    # --- 6. 签名算法确定性 ---
    ts, sign = DingTalk.sign("SECRET", 1700000000000)
    ts2, sign2 = DingTalk.sign("SECRET", 1700000000000)
    assert ts == ts2 and sign == sign2, "签名不确定"
    print(f"OK 钉钉加签确定性: timestamp={ts} sign={sign[:20]}...")

    # --- 7. 关键词注入 ---
    p = DingTalk(keywords=["报警"]).build_payload("t", "b")
    assert p["text"]["content"].startswith("报警"), p
    print("OK 钉钉自定义关键词自动注入正文（否则 errcode=310000 拒收）")

    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


# ==========================================================================
# 真机探测：连官方端点（需要外网），证明 200+errcode 现象
# ==========================================================================
def probe() -> int:
    print("说明：下面用的是【故意写错的 token】，不会打扰任何人，")
    print("      目的只是真实演示「HTTP 200 但业务失败」。\n")
    targets = [
        ("钉钉", DingTalk(), "https://oapi.dingtalk.com/robot/send?access_token=DUMMY_TOKEN_FOR_PROBE"),
        ("企业微信", WeCom(), "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=DUMMY_KEY_FOR_PROBE"),
        ("Slack", Slack(), "https://hooks.slack.com/services/DUMMY/PROBE/PROBE"),
    ]
    for label, ch, url in targets:
        try:
            r = ch.send(url, "探测", "这是一次无害的连通性探测", retries=1, timeout=15)
            print(f"{label:6s} -> {r}")
            if label in ("钉钉", "企业微信") and r.status_code == 200 and not r.ok:
                print(f"         ^^^ 铁证：HTTP {r.status_code} 却是失败，errcode={r.errcode}")
        except Exception as e:
            print(f"{label:6s} -> 网络不可达: {type(e).__name__}: {e}")
        print()
    return 0


def demo() -> int:
    srv, port, hits = _mock_server({})
    for ch in (DingTalk(), WeCom(), Slack()):
        ch.send(f"http://127.0.0.1:{port}/{ch.name}", "P1 磁盘告警",
                "web-01 磁盘使用率 **91%**，阈值 85%", level="critical")
    print(f"\n* 本地模拟服务器收到 {len(hits)} 个请求: {hits}")
    srv.shutdown(); srv.server_close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.probe:
        return probe()
    if args.dry_run:
        for ch in (DingTalk(), WeCom(), Slack()):
            ch.send("", "[P1] 磁盘告警", "web-01 磁盘使用率 91%", level="critical", dry_run=True)
        return 0
    return demo()


if __name__ == "__main__":
    sys.exit(main())
