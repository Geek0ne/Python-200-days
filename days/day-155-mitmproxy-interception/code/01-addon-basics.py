#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 155 · 示例 01 —— mitmproxy Addon 基础：最小可用的流量观察器
================================================================

运行方式 A（推荐，用 mitmdump 加载）：
    pip install mitmproxy
    mitmdump -s 01-addon-basics.py -p 8080
    # 另开一个终端：
    curl -x http://127.0.0.1:8080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem \
         https://example.com/

运行方式 B（不装 mitmproxy 也能跑，看离线自检）：
    python3 01-addon-basics.py --self-test

本文件教你 Addon 的 4 个最小要点：
    1) addons = [...]           ← mitmdump 靠这个列表发现你的类
    2) def request(self, flow)  ← 按事件名命名方法，不需要继承/装饰器
    3) flow.request.* 的属性    ← 能读到什么
    4) ctx.log.*                ← 怎么打日志（不要用 print！）

⚠️ 只处理白名单域，其它域一律透传，不打印、不记录。
"""

from __future__ import annotations

import sys
import time

# ── mitmproxy 的导入：装在不在都能 import 本模块 ──────────────
try:
    from mitmproxy import ctx, http          # type: ignore
    HAVE_MITM = True
except ImportError:                           # pragma: no cover
    ctx = None
    http = None
    HAVE_MITM = False

# ─────────────────────────────────────────────────────────────
# 配置：白名单（护栏）
# ─────────────────────────────────────────────────────────────
ALLOWED_HOSTS = {
    "127.0.0.1", "localhost", "::1",
    "example.com", "www.example.com",
    "httpbin.org",                            # 公开无害的测试服务
}

# 不记录的静态资源后缀（减少噪音）
SKIP_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2",
               ".ttf", ".svg", ".css", ".mp4", ".webp")


def host_allowed(host: str) -> bool:
    return (host or "").lower().split(":")[0] in ALLOWED_HOSTS


def is_static(path: str) -> bool:
    return path.lower().split("?")[0].endswith(SKIP_SUFFIX)


# ─────────────────────────────────────────────────────────────
# Addon 主体
# ─────────────────────────────────────────────────────────────
class ObserveAddon:
    """最小观察器：只读、不改、不落盘敏感数据。"""

    def __init__(self):
        self.seq = 0
        self.started = time.time()

    # ── 生命周期：load 里注册自定义 --set 选项 ──
    def load(self, loader):
        """load 事件在启动时触发一次，用来声明自定义选项。

        为什么用 ctx.options 而不是全局变量？
        → mitmdump 以多进程/子进程方式工作时，全局变量不可靠；
          选项系统是官方推荐的配置入口。
        """
        loader.add_option(
            name="obs_verbose",
            typespec=bool,
            default=False,
            help="是否打印每个请求的完整头",
        )
        if HAVE_MITM:
            ctx.log.info("[observe] addon 已加载，白名单 = %s" % sorted(ALLOWED_HOSTS))

    def running(self):
        """代理完全启动后触发。适合打印 banner。"""
        if HAVE_MITM:
            ctx.log.info("[observe] 代理就绪，开始记录。Ctrl-C 退出。")

    # ── 核心：请求事件 ──
    def request(self, flow: "http.HTTPFlow"):
        host = flow.request.host
        if not host_allowed(host):
            return
        if is_static(flow.request.path):
            return

        self.seq += 1
        flow.metadata["observe_seq"] = self.seq

        # ⚠️ 不要用 print()：mitmdump 的 stdout 会和流量输出混在一起，
        #    而且支持 --set termlog_verbosity 的日志系统才是正确姿势。
        self._log(
            f"[#{self.seq}] → {flow.request.method} {flow.request.pretty_url}"
        )
        if HAVE_MITM and ctx.options.obs_verbose:
            for k, v in flow.request.headers.items():
                self._log(f"      {k}: {v}")

        # 演示：读 body 的三种方式（这里只读，不改）
        if flow.request.content:
            ctype = flow.request.headers.get("Content-Type", "")
            if "json" in ctype:
                try:
                    self._log(f"      JSON body: {flow.request.json()}")
                except Exception as e:
                    self._log(f"      JSON 解析失败: {e}")

    # ── 响应事件：只统计，不改写 ──
    def response(self, flow: "http.HTTPFlow"):
        if not host_allowed(flow.request.host):
            return
        if is_static(flow.request.path):
            return
        seq = flow.metadata.get("observe_seq", "-")
        r = flow.response
        # 注意：这里用 len(r.content) 而不是 len(r.text)
        #   理由见示例 02 的坑 5：content 是原始字节，稳定且不触发解码
        self._log(
            f"[{seq}] ← {r.status_code} {len(r.content)}B "
            f"{r.headers.get('Content-Type', '?')} "
            f"({flow.request.host}{flow.request.path})"
        )

    # ── 错误事件：上游挂了要能看见 ──
    def error(self, flow: "http.HTTPFlow"):
        if host_allowed(flow.request.host):
            self._log(f"[!] 请求出错: {flow.error} ({flow.request.pretty_url})")

    # ── 流开始 / 结束（WebSocket 等也走这里）──
    def websocket_start(self, flow):
        if host_allowed(flow.request.host):
            self._log(f"[ws] WebSocket 建立: {flow.request.pretty_url}")

    def done(self):
        if HAVE_MITM:
            ctx.log.info(f"[observe] 结束，共记录 {self.seq} 个请求，"
                         f"运行 {time.time() - self.started:.1f}s")

    # ── 内部日志封装 ──
    @staticmethod
    def _log(msg: str):
        if HAVE_MITM:
            ctx.log.info(msg)
        else:                                  # 离线自检时降级为 print
            print(msg)


# ─────────────────────────────────────────────────────────────
# mitmdump 通过模块级 addons 列表发现插件（必须！）
# ─────────────────────────────────────────────────────────────
addons = [ObserveAddon()]


# ─────────────────────────────────────────────────────────────
# 离线自检：不依赖 mitmproxy，验证纯逻辑
# ─────────────────────────────────────────────────────────────
def _self_test() -> int:
    print("=" * 66)
    print("离线自检（不需要安装 mitmproxy）")
    print("=" * 66)

    assert host_allowed("127.0.0.1:8080") is True
    assert host_allowed("example.com") is True
    assert host_allowed("evil.example.org") is False
    assert host_allowed("EXAMPLE.COM") is True, "域名比较必须忽略大小写"
    print("✅ host_allowed(): 白名单判定 + 大小写无关")

    assert is_static("/static/a.png") is True
    assert is_static("/static/app.js?ver=1") is False   # .js 不在跳过列表
    assert is_static("/api/users") is False
    print("✅ is_static(): 静态资源识别（含 query 剥离）")

    a = ObserveAddon()
    assert isinstance(a.seq, int) and a.started > 0
    print("✅ ObserveAddon(): 可实例化，seq 初始为", a.seq)

    # 模拟 flow 的鸭子类型，验证 request/response 逻辑不依赖真 mitmproxy
    class FakeHeaders(dict):
        def get(self, k, d=None):
            return dict.get(self, k, d)

    class FakeReq:
        def __init__(self):
            self.method = "GET"
            self.host = "example.com"
            self.path = "/api/users?page=1"
            self.pretty_url = "https://example.com/api/users?page=1"
            self.headers = FakeHeaders({"Content-Type": "application/json"})
            self.content = b'{"a": 1}'
            self.json = lambda: {"a": 1}

    class FakeResp:
        status_code = 200
        headers = FakeHeaders({"Content-Type": "application/json"})
        content = b'{"ok": true}'

    class FakeFlow:
        def __init__(self):
            self.request = FakeReq()
            self.response = FakeResp()
            self.metadata = {}
            self.error = None

    f = FakeFlow()
    a.request(f)
    assert f.metadata.get("observe_seq") == 1, "request 应写入 seq"
    a.response(f)
    print("✅ request()/response(): 用鸭子类型 flow 验证通过，seq =", a.seq)

    print("\n全部离线自检通过。")
    print("\n启动方式：")
    print("  mitmdump -s 01-addon-basics.py -p 8080")
    print("  mitmdump -s 01-addon-basics.py -p 8080 --set obs_verbose=true")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv or not HAVE_MITM:
        if not HAVE_MITM and "--self-test" not in sys.argv:
            print("ℹ️  未检测到 mitmproxy（pip install mitmproxy），转为离线自检。\n")
        sys.exit(_self_test())
    print("本文件请用 mitmdump 加载：mitmdump -s 01-addon-basics.py")
    print("或运行：python3 01-addon-basics.py --self-test")
