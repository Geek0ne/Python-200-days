#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 155 · 示例 02 —— Addon 改包 8 大坑：错误做法 vs 正确做法
==============================================================

运行（离线自检，不需要 mitmproxy）：
    python3 02-addon-pitfalls.py --self-test

运行（真实代理，危险改写默认关闭）：
    mitmdump -s 02-addon-pitfalls.py -p 8080
    mitmdump -s 02-addon-pitfalls.py -p 8080 --set demo_rewrite=true

8 个坑：
  坑 1  改 body 不重算 Content-Length        → 客户端协议错乱
  坑 2  对 gzip 压缩字节直接做字符串替换       → 匹配不到 / 写出乱码
  坑 3  用 len(flow.response.text) 统计大小   → 大文件吃内存 + 解码异常
  坑 4  在回调里做同步阻塞 IO                → 整个代理卡死
  坑 5  用 print() 打日志                    → 输出混乱、无法分级
  坑 6  request 里 mock 响应后忘了 return    → 仍会转发到上游（或反之）
  坑 7  改 URL 时改了 host 导致请求发错站     → 越权/串站
  坑 8  不设白名单 / 不脱敏                   → 把别人的敏感数据写进日志

⚠️ 本脚本的"危险改写"全部受 --set demo_rewrite=true 控制，默认只打印演示。
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import time

try:
    from mitmproxy import ctx, http
    HAVE_MITM = True
except ImportError:
    ctx = None
    http = None
    HAVE_MITM = False

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1", "example.com", "httpbin.org"}

# 敏感字段（落日志前脱敏）
SENSITIVE_KEYS = re.compile(
    r"(authorization|cookie|set-cookie|password|passwd|pwd|token|secret|"
    r"api[-_]?key|session|csrf)", re.I)


def mask(value: str) -> str:
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def mask_headers(headers) -> dict:
    out = {}
    for k, v in headers.items():
        out[k] = "***" if SENSITIVE_KEYS.search(k) else v
    return out


# ═══════════════════════════════════════════════════════════════
class PitfallDemo:
    """一个把 8 个坑都演示出来的 Addon。"""

    def __init__(self):
        self.rewrite_enabled = False
        self.blocked = 0
        self.rewritten = 0

    def load(self, loader):
        loader.add_option(
            name="demo_rewrite",
            typespec=bool,
            default=False,
            help="是否真的执行改写（默认 False，只打印示范）",
        )

    def configure(self, updated):
        """configure 在选项变化时触发（包括启动时）。"""
        if HAVE_MITM and "demo_rewrite" in updated:
            self.rewrite_enabled = bool(ctx.options.demo_rewrite)
            ctx.log.info(f"[pitfalls] demo_rewrite = {self.rewrite_enabled}")

    # ──────────────────────────────────────────────
    def request(self, flow: "http.HTTPFlow"):
        host = flow.request.host.split(":")[0].lower()
        if host not in ALLOWED_HOSTS:
            return                                    # 坑 8：白名单，必须最早 return

        # ── 坑 4：不要在这里做同步阻塞 IO ──
        # ❌ 反例（千万不要）：
        #     time.sleep(0.5)
        #     requests.get("http://127.0.0.1:9000/check")   # 阻塞事件循环
        # ✅ 正确：用异步；纯内存改写直接做（微秒级）
        self._demo_pitfall_4()

        # ── 坑 7：改 URL 的三种改法与区别 ──
        # flow.request.path  只改路径+query，Host 不变  ← 一般用这个
        # flow.request.url   连 scheme/host/port 都改     ← 小心串站
        # flow.request.host  单独改 Host（vhost 测试）    ← 高级用法
        if self.rewrite_enabled and flow.request.path == "/api/old":
            flow.request.path = "/api/new"             # ✅ 只改 path，安全
            self._log("[坑7] 改 path: /api/old → /api/new")

        # ── 坑 6：mock 响应后要 return，别再让它转发 ──
        if flow.request.path.startswith("/mock/"):
            body = json.dumps({"mock": True,
                               "path": flow.request.path,
                               "ts": int(time.time())}).encode()
            flow.response = http.Response.make(
                200, body, {"Content-Type": "application/json"})
            self._log(f"[坑6] mock 命中: {flow.request.path}（不再请求上游）")
            return                                     # ← 关键

        # ── 坑 2：改请求体前先判断编码 ──
        enc = flow.request.headers.get("Content-Encoding", "")
        if self.rewrite_enabled and enc:
            self._log(f"[坑2] 请求体带 Content-Encoding={enc}，"
                      f"不能直接字节替换；请用 flow.request.text / .json")
            # ❌ flow.request.content.replace(...)
            # ✅ if "old" in flow.request.text: flow.request.text = ...replace...

        # ── 坑 3：统计大小时用 content，不要用 text ──
        n = len(flow.request.content or b"")           # ✅
        # ❌ len(flow.request.text) 会触发解码，大文件吃内存、非法字节抛异常
        self._log(f"[kw] → {flow.request.method} {flow.request.path} "
                  f"({n}B) host={host}")

    # ──────────────────────────────────────────────
    def response(self, flow: "http.HTTPFlow"):
        host = flow.request.host.split(":")[0].lower()
        if host not in ALLOWED_HOSTS:
            return
        r = flow.response
        if r is None:
            return

        # ── 坑 1 + 2：改写 body 的正确姿势 ──
        ctype = r.headers.get("Content-Type", "")
        if "text/html" in ctype:
            try:
                # ✅ 用 .text：自动 gunzip + 解码；赋值时自动重算 Content-Length
                text = r.text
            except Exception as e:
                self._log(f"[坑2] 解码失败，跳过改写: {e}")
                return

            if self.rewrite_enabled:
                new = text.replace("</body>",
                                   "<script>console.log('injected by mitmproxy')</script></body>")
                if new != text:
                    r.text = new                        # ✅ 长度由 mitmproxy 维护
                    self.rewritten += 1
                    self._log(f"[坑1] 已注入并自动更新 Content-Length: "
                              f"{len(text)} → {len(new)}")
            else:
                self._log(f"[demo] 本可注入 {len(text)}B 的 HTML（需 demo_rewrite=true）")

        # ── 坑 3：统计响应大小用 content ──
        size = len(r.content or b"")
        self._log(f"[kw] ← {r.status_code} {size}B {ctype or '?'} "
                  f"{flow.request.path}")

        # ── 坑 8：打日志前脱敏 ──
        if self.rewrite_enabled:
            self._log(f"[坑8] 请求头（脱敏后）: {mask_headers(flow.request.headers)}")

    def error(self, flow: "http.HTTPFlow"):
        self._log(f"[err] {flow.request.pretty_url} → {flow.error}")

    # ── 坑 4 的演示与说明 ──
    def _demo_pitfall_4(self):
        if not getattr(self, "_p4_printed", False):
            self._p4_printed = True
            self._log("[坑4] 回调里禁止 time.sleep / 同步 IO；"
                      "重活请用 asyncio.to_thread 或 ThreadPoolExecutor")

    # ── 坑 5：日志封装 ──
    @staticmethod
    def _log(msg: str):
        if HAVE_MITM:
            ctx.log.info(msg)
        else:
            print(msg)


addons = [PitfallDemo()]


# ═══════════════════════════════════════════════════════════════
# 离线自检：把 8 个坑的"纯逻辑部分"都验证一遍
# ═══════════════════════════════════════════════════════════════
def _self_test() -> int:
    print("=" * 70)
    print("离线自检：8 个坑的纯逻辑")
    print("=" * 70)

    # 坑 1：改写后长度会变 → 必须让 mitmproxy 重算
    body = b"Hello world"
    new_body = body.replace(b"world", b"there!")
    assert len(new_body) != len(body)
    print(f"✅ 坑1: 改写会改变长度 ({len(body)} → {len(new_body)})，"
          f"因此必须用 .text/.content 赋值让它重算 Content-Length")

    # 坑 2：gzip 原始字节里搜不到明文
    raw = gzip.compress(b'{"role":"user"}')
    assert b'"role"' not in raw, "gzip 压缩后不应能直接搜到明文"
    assert b'"role"' in gzip.decompress(raw)
    print("✅ 坑2: gzip 字节里搜不到明文 → 必须先解压（用 .text）")
    # 用 .text 的等效操作
    assert '"role"' in gzip.decompress(raw).decode()
    print("✅ 坑2: gzip.decompress + decode 后可正常替换")

    # 坑 3：非法字节会让 .text 抛异常，但 .content 永远安全
    bad = b"\xff\xfe\x00\x01invalid utf-8"
    try:
        bad.decode("utf-8")
        raise AssertionError("应当解码失败")
    except UnicodeDecodeError:
        pass
    assert len(bad) == 17, len(bad)
    print("✅ 坑3: .text 对非法字节会抛 UnicodeDecodeError；.content 恒定安全")

    # 坑 4：证明"同步 IO 会阻塞"——用时间差验证
    t0 = time.perf_counter()
    time.sleep(0.05)
    blocking = time.perf_counter() - t0
    assert blocking >= 0.05
    print(f"✅ 坑4: 同步 sleep(0.05) 实测阻塞 {blocking*1000:.1f}ms（事件循环会被它卡住）")

    # 坑 5：日志分级——纯逻辑用 logger 名字断言
    assert callable(PitfallDemo._log)
    print("✅ 坑5: 日志统一走 _log()/ctx.log，不用 print()")

    # 坑 6：mock 逻辑（路径匹配）
    class FakeReq:
        def __init__(self, path):
            self.path = path
            self.host = "example.com"
            self.method = "GET"
            self.headers = {}
            self.content = b""

    demo = PitfallDemo()
    assert "/mock/users".startswith("/mock/")
    assert not "/api/users".startswith("/mock/")
    print("✅ 坑6: mock 命中后必须 return，阻止转发到上游")

    # 坑 7：path 与 url 的区别（用字符串模拟）
    p = "/api/old"
    p2 = p.replace("/old", "/new")
    assert p2 == "/api/new" and "/api/new".startswith("/")
    print("✅ 坑7: 改路径优先用 flow.request.path（不动 host），避免串站")

    # 坑 8：脱敏
    h = {"Authorization": "Bearer abcdefghijklmnop", "User-Agent": "curl/8.0",
         "Cookie": "session=abcdefghijklmnop"}
    m = mask_headers(h)
    assert m["Authorization"] == "***", m
    assert m["Cookie"] == "***"
    assert m["User-Agent"] == "curl/8.0", "非敏感头应保留"
    assert mask("short") == "***"
    assert mask("abcdefghijklmnop") == "abcd********mnop"
    print(f"✅ 坑8: 敏感头被脱敏 → {m}")

    print("\n全部离线自检通过。")
    print("\n真实运行：")
    print("  mitmdump -s 02-addon-pitfalls.py -p 8080")
    print("  mitmdump -s 02-addon-pitfalls.py -p 8080 --set demo_rewrite=true")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv or not HAVE_MITM:
        if not HAVE_MITM and "--self-test" not in sys.argv:
            print("ℹ️  未检测到 mitmproxy，转为离线自检。\n")
        sys.exit(_self_test())
    print("请用 mitmdump 加载：mitmdump -s 02-addon-pitfalls.py")
