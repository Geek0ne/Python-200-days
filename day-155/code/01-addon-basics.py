#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 155 · 示例 01 —— mitmproxy Addon 基础：最小可用的流量观察器
================================================================

三种运行方式
------------
方式 A（真 mitmproxy，推荐先跑通这个）：
    pip install mitmproxy
    mitmdump -s 01-addon-basics.py -p 8080
    # 另开一个终端：
    curl -x http://127.0.0.1:8080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem \
         https://example.com/

方式 B（没装 mitmproxy 也能把这些逻辑跑起来：仓库自带的本地实验台，纯标准库）：
    python3 00-local-lab.py --addon 01-addon-basics.py
    # 再另开终端（走代理，目标是本地上游站点）：
    curl -x http://127.0.0.1:<代理端口> http://127.0.0.1:<上游端口>/api/users

方式 C（离线自检：不联网、不装任何第三方库）：
    python3 01-addon-basics.py --self-test

本文件教你 Addon 的 4 个最小要点：
    1) addons = [...]           ← mitmdump 靠这个列表发现你的类
    2) def request(self, flow)  ← 按事件名命名方法，不需要继承/装饰器
    3) flow.request.* 的属性    ← 能读到什么
    4) ctx.log.*                ← 怎么打日志（不要用 print！）

⚠️ 只处理白名单域，其它域一律透传，不打印、不记录。
   白名单不是"礼貌"，是**最小权限原则**在工具层落地：
   一个抓包工具默认抓全网，等于把一个"全量监听器"放在你机器上，
   一旦日志落盘就是一堆别人的凭据。
"""

from __future__ import annotations

import sys
import time

# ── mitmproxy 的导入：装在不在都能 import 本模块 ──────────────
# 这样设计的意义：同一个文件既能被真 mitmdump 加载，
# 也能在"没装 mitmproxy"的机器上被 --self-test 用来验证逻辑。
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

# 不记录的静态资源后缀（减少噪音）。
# ⚠️ 注意这里**故意不含 .js**：很多接口会把数据塞在 .js/.json 里，
#    一律跳过会漏掉你想看的东西。要跳过就按项目实际情况显式加。
SKIP_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2",
               ".ttf", ".svg", ".css", ".mp4", ".webp")


def host_allowed(host: str) -> bool:
    """域名白名单判定。

    三个必须处理的细节：
      · 端口：`flow.request.host` 一般不含端口，但 curl/httpx 某些模式下会带；
        统一 split(":")[0] 再比较，避免 "127.0.0.1:8080" 被判为不在白名单；
      · 大小写：DNS 名字不区分大小写（RFC 4343），必须 lower()；
      · 空值：host 可能是 None（畸形请求），不能让判定函数抛异常。
    """
    return (host or "").lower().split(":")[0] in ALLOWED_HOSTS


def is_static(path: str) -> bool:
    """静态资源判定：先剥 query 再比后缀。

    为什么要剥 query？`/static/app.css?v=20240101` 的 endswith 判断会失败，
    这是"过滤器看起来写了却不生效"的最常见原因。
    """
    return path.lower().split("?")[0].endswith(SKIP_SUFFIX)


# ─────────────────────────────────────────────────────────────
# Addon 主体
# ─────────────────────────────────────────────────────────────
class ObserveAddon:
    """最小观察器：只读、不改、不落盘敏感数据。

    "只读"是一个可验证的性质：本类的 request()/response() 不会写
    flow.request / flow.response 的任何字段（只写 flow.metadata，
    那是 mitmproxy 专门给 addon 之间传值用的"私有口袋"）。
    """

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
            return                                # 白名单外一律透传（不打印、不记录）
        if is_static(flow.request.path):
            return

        self.seq += 1
        # flow.metadata 是 mitmproxy 给 addon 用的字典：在这里放一个序号，
        # response 事件里就能把"请求"和"响应"配对（mitmproxy 不保证两者相邻）。
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
                    # ⚠️ json() 是**方法**，忘写括号会拿到一个函数对象
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
        if r is None:
            return
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
# 离线自检
# ─────────────────────────────────────────────────────────────
class _Checker:
    """20 行断言器：累计失败，最后统一输出 SELF-TEST OK 或失败详情。

    为什么不用 assert？
    → assert 在 python -O 下会被优化掉；而且它只抛第一个错，
      看不出"到底几项不对"。测试要看**全部**差异。
    """

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
        print("-" * 66)
        if self.fail:
            print(f"❌ {self.fail}/{self.n} 项断言失败")
            return 1
        print(f"✅ 全部 {self.n} 项断言通过")
        print("SELF-TEST OK")
        return 0


class _FakeHeaders(dict):
    """鸭子类型的 headers：够 addon 用即可。

    为什么用鸭子类型（fake flow）而不是真 mitmproxy 对象？
    → 自检要能在**没装 mitmproxy**的机器上跑；而且单元测试只关心
      "我的代码有没有正确使用这些属性"，用最小替身反而更清晰。
      集成层面的真实验证由 00-local-lab.py 负责（它会真的起代理发请求）。
    """

    def get(self, k, d=None):
        return dict.get(self, k, d)

    def items(self):
        return dict.items(self)


class _FakeReq:
    def __init__(self, method="GET", host="example.com",
                 path="/api/users?page=1", headers=None, content=b""):
        self.method = method
        self.host = host
        self.path = path
        self.pretty_url = f"https://{host}{path}"
        self.headers = _FakeHeaders(headers or {})
        self.content = content
        self.scheme = "https"
        self.port = 443
        self.url = self.pretty_url

    def json(self):
        import json as _j
        return _j.loads(self.content.decode())


class _FakeResp:
    def __init__(self, status_code=200, content=b'{"ok": true}', headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = _FakeHeaders(headers or {"Content-Type": "application/json"})


class _FakeFlow:
    def __init__(self, req=None, resp=None):
        self.request = req or _FakeReq()
        self.response = resp
        self.metadata = {}
        self.error = None
        self.id = "fake-flow-1"
        self.type = "http"


def _self_test() -> int:
    c = _Checker()
    print("=" * 66)
    print("离线自检（不需要安装 mitmproxy，也不联网）")
    print("=" * 66)
    print(f"mitmproxy 可用: {HAVE_MITM}"
          f"{'' if HAVE_MITM else '（当前环境没装，用鸭子类型对象验证逻辑）'}")

    # ── 1. 白名单判定 ──
    c.eq("host_allowed('127.0.0.1:8080') 剥端口", host_allowed("127.0.0.1:8080"), True)
    c.eq("host_allowed('example.com')", host_allowed("example.com"), True)
    c.eq("host_allowed('EXAMPLE.COM') 忽略大小写", host_allowed("EXAMPLE.COM"), True)
    c.eq("host_allowed('evil.example.org') 拒绝", host_allowed("evil.example.org"), False)
    c.eq("host_allowed('') 空串安全", host_allowed(""), False)
    c.eq("host_allowed(None) 不抛异常", host_allowed(None), False)
    # ⚠️ 子域必须**显式**加入白名单：不能写 endswith(".example.com")，
    #    否则 attacker.example.com.evil.com 这类域名会被绕过
    c.eq("host_allowed('sub.example.com') 不在白名单", host_allowed("sub.example.com"), False)

    # ── 2. 静态资源判定 ──
    c.eq("is_static('/static/a.png')", is_static("/static/a.png"), True)
    c.eq("is_static('/a.png?v=1') 剥掉 query", is_static("/a.png?v=1"), True)
    c.eq("is_static('/API/USERS') 大小写无关", is_static("/API/USERS"), False)
    c.eq("is_static('/static/app.js?ver=1') — .js 不在跳过列表",
         is_static("/static/app.js?ver=1"), False)
    c.eq("is_static('/api/users')", is_static("/api/users"), False)

    # ── 3. 实例状态 ──
    a = ObserveAddon()
    c.eq("ObserveAddon: seq 初始值", a.seq, 0)
    c.ok("ObserveAddon: started 已初始化", a.started > 0)

    # ── 4. 事件回调逻辑（鸭子类型 flow）──
    f = _FakeFlow(resp=_FakeResp())
    a.request(f)
    c.eq("request(): seq 递增", a.seq, 1)
    c.eq("request(): 序号写入 metadata", f.metadata.get("observe_seq"), 1)
    a.response(f)
    c.eq("response(): 不改变 seq", a.seq, 1)

    # 静态资源不计数
    f2 = _FakeFlow(req=_FakeReq(path="/static/a.css"), resp=_FakeResp())
    a.request(f2)
    a.response(f2)
    c.eq("静态资源不计数", a.seq, 1)

    # 非白名单主机不计数
    f3 = _FakeFlow(req=_FakeReq(host="evil.example.org"), resp=_FakeResp())
    a.request(f3)
    a.response(f3)
    c.eq("非白名单主机不计数", a.seq, 1)

    # 只读性质：回调不得改动请求/响应
    f4 = _FakeFlow(req=_FakeReq(path="/api/users?page=1",
                                headers={"Content-Type": "application/json"},
                                content=b'{"a": 1}'),
                   resp=_FakeResp(201, b'{"ok": true}',
                                  {"Content-Type": "application/json"}))
    before = (f4.request.path, f4.request.method, dict(f4.request.headers),
              f4.request.content, f4.response.status_code, f4.response.content)
    a.request(f4)
    a.response(f4)
    after = (f4.request.path, f4.request.method, dict(f4.request.headers),
             f4.request.content, f4.response.status_code, f4.response.content)
    c.eq("只读保证：请求/响应完全未被修改", after, before)
    c.eq("只读保证：seq 仍然递增（记录行为发生）", a.seq, 2)

    # JSON body 解析路径（含非法 JSON 不能抛出去）
    f5 = _FakeFlow(req=_FakeReq(headers={"Content-Type": "application/json"},
                                content=b'{"x": 1}'))
    a.request(f5)
    c.eq("JSON body 解析不抛异常", a.seq, 3)
    f6 = _FakeFlow(req=_FakeReq(headers={"Content-Type": "application/json"},
                                content=b'{bad json'))
    try:
        a.request(f6)
        c.ok("非法 JSON 被就地捕获（不中断代理）", True)
    except Exception as e:                     # pragma: no cover
        c.ok("非法 JSON 被就地捕获（不中断代理）", False, repr(e))

    # error / websocket_start / done 事件不能抛异常
    f7 = _FakeFlow(req=_FakeReq())
    f7.error = "ConnectionReset"
    try:
        a.error(f7)
        a.websocket_start(f7)
        a.done()
        c.ok("error()/websocket_start()/done() 均可安全调用", True)
    except Exception as e:                     # pragma: no cover
        c.ok("error()/websocket_start()/done() 均可安全调用", False, repr(e))

    # ── 5. 模块契约 ──
    c.eq("模块级 addons 列表存在", isinstance(addons, list), True)
    c.eq("addons 里有 1 个实例", len(addons), 1)
    c.ok("addons[0] 是 ObserveAddon", isinstance(addons[0], ObserveAddon))
    c.ok("提供了 request/response/error/load 四个必备回调",
         all(hasattr(ObserveAddon, m) for m in
             ("request", "response", "error", "load")))

    print("\n启动方式：")
    print("  A) mitmdump -s 01-addon-basics.py -p 8080")
    print("     mitmdump -s 01-addon-basics.py -p 8080 --set obs_verbose=true")
    print("  B) python3 00-local-lab.py --addon 01-addon-basics.py   ← 不需要 mitmproxy")
    return c.done()


if __name__ == "__main__":
    if "--self-test" in sys.argv or not HAVE_MITM:
        if not HAVE_MITM and "--self-test" not in sys.argv:
            print("ℹ️  未检测到 mitmproxy（pip install mitmproxy），转为离线自检。\n")
        sys.exit(_self_test())
    print("本文件请用 mitmdump 加载：mitmdump -s 01-addon-basics.py")
    print("或运行：python3 01-addon-basics.py --self-test")
