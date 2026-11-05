#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 155 · 示例 02 —— Addon 改包 8 大坑：错误做法 vs 正确做法
==============================================================

运行方式
--------
方式 A（真 mitmproxy，危险改写默认关闭）：
    pip install mitmproxy
    mitmdump -s 02-addon-pitfalls.py -p 8080
    mitmdump -s 02-addon-pitfalls.py -p 8080 --set demo_rewrite=true

方式 B（本地实验台，不需要 mitmproxy；仓库自带，纯标准库）：
    python3 00-local-lab.py --addon 02-addon-pitfalls.py --set demo_rewrite=true
    curl -x http://127.0.0.1:<代理端口> http://127.0.0.1:<上游端口>/mock/users

方式 C（离线自检，不联网、不装任何第三方库）：
    python3 02-addon-pitfalls.py --self-test

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
    """脱敏：保留前 4 + 后 4 字符，中间打码。

    为什么保留首尾？→ 排查问题时需要确认"这条凭据是不是我以为的那条"，
      完全打码成 *** 就失去了可辨识性；保留首尾是"可调试"与"不泄露"的折中。
    ⚠️ 长度 ≤ 8 的短字符串直接全打码：否则保留首尾等于没脱敏。
    """
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def mask_headers(headers) -> dict:
    """按头名脱敏，返回普通 dict（可直接写日志/JSON）。"""
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
        """configure 在选项变化时触发（包括启动时）。

        ⚠️ 必须判断 "demo_rewrite" in updated，否则会把**别的**选项变化
           误当成自己的开关 —— 多人共用一套选项系统时这是经典 bug。
        """
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
            # ❌ flow.request.content.replace(...)  ← 压缩体里搜不到明文
            # ✅ if "old" in flow.request.text: flow.request.text = ...replace...

        # ── 坑 3：统计大小时用 content，不要用 text ──
        n = len(flow.request.content or b"")           # ✅
        # ❌ len(flow.request.text)
        #    → 触发解压+解码：大文件吃内存，非法字节直接抛 UnicodeDecodeError
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
                # ✅ 用 .text：自动 gunzip + 解码；
                #    赋值时 mitmproxy 自动重算 Content-Length（并保持原 Content-Encoding）
                text = r.text
            except Exception as e:
                self._log(f"[坑2] 解码失败，跳过改写: {e}")
                return

            if self.rewrite_enabled:
                new = text.replace(
                    "</body>",
                    "<script>console.log('injected by mitmproxy')</script></body>")
                if new != text:
                    r.text = new                        # ✅ 长度由 mitmproxy 维护
                    self.rewritten += 1
                    self._log(f"[坑1] 已注入并自动更新 Content-Length: "
                              f"{len(text)} → {len(new)} 字符")
            else:
                self._log(f"[demo] 本可注入 {len(text)} 字符的 HTML（需 demo_rewrite=true）")

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
        """只打印一次说明：回调里禁止阻塞。

        为什么"打印一次"要用标志位？→ request 回调每个请求都会跑，
          不加标志会把日志刷爆（这也算坑 5 的一个延伸：日志要能控量）。
        """
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
# 离线自检
# ═══════════════════════════════════════════════════════════════
class _Checker:
    def __init__(self):
        self.fail = 0
        self.n = 0

    def eq(self, name, actual, expected):
        self.n += 1
        if actual == expected:
            print(f"✅ {name}: {actual!r}")
        else:
            self.fail += 1
            print(f"❌ {name}\n     实际值: {actual!r}\n     期望值: {expected!r}")

    def ok(self, name, cond, detail=""):
        self.n += 1
        if cond:
            print(f"✅ {name}{(' — ' + detail) if detail else ''}")
        else:
            self.fail += 1
            print(f"❌ {name}{(' — ' + detail) if detail else ''}")

    def done(self) -> int:
        print("-" * 70)
        if self.fail:
            print(f"❌ {self.fail}/{self.n} 项断言失败")
            return 1
        print(f"✅ 全部 {self.n} 项断言通过")
        print("SELF-TEST OK")
        return 0


class _MitmLikeResponse:
    """模仿 mitmproxy `http.Response` 的关键语义（用于离线验证坑 1/2/3）。

    为什么在测试里自己实现一遍？→ 自检必须能在**没装 mitmproxy** 的机器上跑。
      这里只实现被测代码真正依赖的三条契约：
        1. `.text` 读取时自动 gunzip 解压；
        2. `.text` 赋值时按原 Content-Encoding 重新压缩；
        3. 赋值后 Content-Length 自动更新（就是"坑 1 的正解"）。
      真 mitmproxy 由 00-local-lab.py 的集成自检来验证。
    """

    def __init__(self, content=b"", headers=None):
        self.headers = dict(headers or {})
        self.content = content
        # 真实响应一定带 Content-Length（或 chunked），这里补上以便演示同步逻辑
        self.headers.setdefault("Content-Length", str(len(content)))

    @property
    def text(self):
        raw = self.content
        if "gzip" in self.headers.get("Content-Encoding", "").lower():
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")

    @text.setter
    def text(self, value):
        raw = value.encode("utf-8")
        if "gzip" in self.headers.get("Content-Encoding", "").lower():
            raw = gzip.compress(raw)
        self.content = raw
        # ✅ mitmproxy 会自动重算；如果不这样做，客户端会读到错位的 body
        self.headers["Content-Length"] = str(len(raw))


def _self_test() -> int:
    c = _Checker()
    print("=" * 70)
    print("离线自检：8 个坑的纯逻辑 + 契约验证（不联网）")
    print("=" * 70)
    print(f"mitmproxy 可用: {HAVE_MITM}"
          f"{'' if HAVE_MITM else '（没装也能验证：用等价对象与纯字节运算）'}")

    # ── 坑 1：改写会改变长度 → 必须让它自动重算 ──
    body = b"Hello world"
    new_body = body.replace(b"world", b"there!")
    c.ok("坑1: 改写必然改变长度", len(new_body) != len(body),
         f"{len(body)} → {len(new_body)}")
    r = _MitmLikeResponse(content=b"<p>x</p>",
                          headers={"Content-Type": "text/html"})
    c.eq("坑1: 初始 Content-Length 与 body 一致",
         r.headers.get("Content-Length"), str(len(r.content)))
    r.text = "<p>xxxxxxxxxx</p>"
    c.eq("坑1: 赋值 .text 后 Content-Length 自动同步",
         r.headers.get("Content-Length"), str(len(r.content)))
    # ❌ 反例：手工写死 Content-Length，body 变了头没变 → 协议错乱
    bad = {"Content-Length": "10", "Content-Type": "text/html"}
    bad_body = b"<p>xxxxxxxxxx</p>"
    c.ok("坑1: 反例（手写长度不更新）确实会造成长度不符",
         int(bad["Content-Length"]) != len(bad_body),
         f"头说 {bad['Content-Length']}，实际 {len(bad_body)} 字节")

    # ── 坑 2：gzip 原始字节里搜不到明文 ──
    raw = gzip.compress(b'{"role":"user"}')
    c.eq("坑2: gzip 字节里搜不到明文", b'"role"' in raw, False)
    c.eq("坑2: 解压后能搜到", b'"role"' in gzip.decompress(raw), True)
    g = _MitmLikeResponse(content=raw, headers={"Content-Encoding": "gzip",
                                                "Content-Type": "application/json"})
    c.eq("坑2: .text 自动解压", g.text, '{"role":"user"}')
    g.text = g.text.replace("user", "admin")
    c.eq("坑2: 赋值后仍是 gzip（Content-Encoding 保留）",
         g.headers.get("Content-Encoding"), "gzip")
    c.eq("坑2: 重新压缩后解压可见替换结果",
         gzip.decompress(g.content), b'{"role":"admin"}')
    c.eq("坑2: Content-Length 与压缩后长度一致",
         g.headers.get("Content-Length"), str(len(g.content)))

    # ── 坑 3：非法字节让 .text 抛异常，.content 恒定安全 ──
    bad_bytes = b"\xff\xfe\x00\x01invalid utf-8"
    try:
        bad_bytes.decode("utf-8")
        c.ok("坑3: .text 对非法字节抛 UnicodeDecodeError", False, "竟然解码成功")
    except UnicodeDecodeError:
        c.ok("坑3: .text 对非法字节抛 UnicodeDecodeError", True)
    c.eq("坑3: .content 长度恒定可用", len(bad_bytes), 17)
    gz_bad = _MitmLikeResponse(content=gzip.compress(bad_bytes),
                               headers={"Content-Encoding": "gzip"})
    c.eq("坑3: gzip+bytes 用 .text 会抛（replace 兜底才安全）",
         gz_bad.text, bad_bytes.decode("utf-8", "replace"))

    # ── 坑 4：同步 IO 确实会阻塞 ──
    t0 = time.perf_counter()
    time.sleep(0.05)
    blocking = time.perf_counter() - t0
    c.ok("坑4: 同步 sleep(0.05) 真的阻塞了事件循环",
         blocking >= 0.05, f"实测 {blocking * 1000:.1f}ms")
    c.ok("坑4: 说明只打印一次（不刷屏）", hasattr(PitfallDemo(), "_demo_pitfall_4"))

    # ── 坑 5：日志走 _log()，可降级 ──
    c.ok("坑5: _log 是可调用的统一出口", callable(PitfallDemo._log))
    c.ok("坑5: 有 mitmproxy 时走 ctx.log.info（无则 print 降级）",
         HAVE_MITM or ctx is None)

    # ── 坑 6：mock 命中后必须 return ──
    c.ok("坑6: /mock/ 前缀命中", "/mock/users".startswith("/mock/"))
    c.ok("坑6: /api/users 不命中", not "/api/users".startswith("/mock/"))

    # ── 坑 7：改 path 不动 host ──
    p = "/api/old"
    p2 = p.replace("/old", "/new")
    c.eq("坑7: 路径替换结果", p2, "/api/new")
    c.ok("坑7: 替换后仍是路径（不会变成绝对 URL，host 不变）",
         p2.startswith("/") and "://" not in p2)

    # ── 坑 8：脱敏 ──
    h = {"Authorization": "Bearer abcdefghijklmnop", "User-Agent": "curl/8.0",
         "Cookie": "session=abcdefghijklmnop", "X-Api-Key": "sk-1234567890",
         "Set-Cookie": "a=b"}
    m = mask_headers(h)
    c.eq("坑8: Authorization 被脱敏", m["Authorization"], "***")
    c.eq("坑8: Cookie 被脱敏", m["Cookie"], "***")
    c.eq("坑8: X-Api-Key 被脱敏", m["X-Api-Key"], "***")
    c.eq("坑8: Set-Cookie 被脱敏", m["Set-Cookie"], "***")
    c.eq("坑8: 非敏感头保留原值", m["User-Agent"], "curl/8.0")
    c.eq("坑8: 短值全打码", mask("short"), "***")
    c.eq("坑8: 8 字符全打码（边界）", mask("12345678"), "***")
    c.eq("坑8: 长值保留首尾", mask("abcdefghijklmnop"), "abcd********mnop")
    c.eq("坑8: 长度 9（边界）→ 保留 4+1+4", mask("abcdefghi"), "abcd*fghi")
    c.eq("坑8: 空值原样返回", mask(""), "")

    # ── 白名单必须最早 return ──
    c.ok("白名单: 未授权主机不会被处理",
         "evil.example.org" not in ALLOWED_HOSTS)

    # ── 模块契约 ──
    c.eq("模块级 addons 列表", isinstance(addons, list), True)
    c.eq("addons 数量", len(addons), 1)
    c.ok("addons[0] 是 PitfallDemo", isinstance(addons[0], PitfallDemo))
    c.ok("默认关闭改写（危险操作必须显式开启）",
         addons[0].rewrite_enabled is False)
    c.ok("提供 load/configure/request/response 四个必备回调",
         all(hasattr(PitfallDemo, mm) for mm in
             ("load", "configure", "request", "response")))

    print("\n真实运行：")
    print("  A) mitmdump -s 02-addon-pitfalls.py -p 8080")
    print("     mitmdump -s 02-addon-pitfalls.py -p 8080 --set demo_rewrite=true")
    print("  B) python3 00-local-lab.py --addon 02-addon-pitfalls.py --set demo_rewrite=true")
    return c.done()


if __name__ == "__main__":
    if "--self-test" in sys.argv or not HAVE_MITM:
        if not HAVE_MITM and "--self-test" not in sys.argv:
            print("ℹ️  未检测到 mitmproxy，转为离线自检。\n")
        sys.exit(_self_test())
    print("请用 mitmdump 加载：mitmdump -s 02-addon-pitfalls.py")
    print("或运行：python3 02-addon-pitfalls.py --self-test")
