#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 154 · 示例 01 —— 目录扫描基础：从单线程到线程池
=========================================================

两种运行方式
------------
方式 A（联机演示：需要一个真实/靶场 HTTP 服务）:
    # 先起本地靶场（仓库自带，纯标准库）
    python3 code/00-local-lab.py --port 8080
    # 再另一个终端跑扫描
    python3 code/01-dir-brute-basics.py --url http://127.0.0.1:8080
    python3 code/01-dir-brute-basics.py --url http://127.0.0.1:8080 --wordlist common.txt

方式 B（离线自检：完全离线，不联网、不装任何第三方库）:
    python3 code/01-dir-brute-basics.py --self-test

目标：把"目录扫描"拆成 4 个可理解的步骤
    1) 构造 URL            2) 发请求（allow_redirects=False）
    3) 判定状态码语义       4) 并发化 + 汇总

⚠️ 法律边界：本脚本默认只允许 127.0.0.1 / localhost / ::1。
   扫描任何其它目标都需要书面授权，并且必须显式加 --i-have-authorization。
   这不是形式主义：把边界写进代码，是"安全工程师"和"脚本小子"的分水岭。

⚠️ 本脚本**没有**实现软 404 过滤（那是示例 02 的内容），
   故意保留这个缺陷，让你亲眼看到误报长什么样。

依赖说明（重要）
----------------
本文件优先用 `requests`；如果环境里没有装 requests，会**自动降级**到
同目录 `00-local-lab.py` 提供的 `StdlibSession`（纯标准库 urllib 实现，
接口与 requests 对齐）。两条路径的扫描逻辑完全一致，所以你可以放心地
在"没网、没装库"的机器上学习。
"""

import argparse
import concurrent.futures as cf
import importlib.util
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ── 依赖探测：requests 是"可选的"，没有也能跑 ──────────────────
try:
    import requests
    from requests.exceptions import RequestException

    HAVE_REQUESTS = True
    NET_ERRORS = (RequestException,)          # requests 的异常体系（含超时/连接错误）
except ImportError:                            # pragma: no cover
    requests = None                            # type: ignore[assignment]
    HAVE_REQUESTS = False
    # 标准库路径下，网络错误都是 OSError 的子类：
    #   URLError（DNS 失败/连接被拒）、socket.timeout / TimeoutError（超时）
    NET_ERRORS = (OSError,)

# ─────────────────────────────────────────────────────────────
# 0. 合规护栏
# ─────────────────────────────────────────────────────────────
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

# 内置小字典（约 60 条）。真实场景请用 SecLists 的 common.txt。
BUILTIN_WORDLIST = [
    "", "admin", "administrator", "login", "logout", "register", "signup",
    "api", "api/v1", "api/v2", "v1", "v2", "graphql", "swagger", "swagger.json",
    "openapi.json", "docs", "documentation", "help",
    "static", "assets", "public", "uploads", "files", "media", "images", "img",
    "css", "js", "fonts",
    "backup", "backups", "backup.zip", "www.zip", "site.tar.gz", "db.sql",
    "config", "config.php", "settings.py", "settings.json", ".env", ".git",
    ".git/HEAD", ".git/config", ".svn", ".DS_Store",
    "test", "tests", "dev", "develop", "staging", "stage", "demo", "old", "new",
    "tmp", "temp", "cache", "log", "logs", "debug", "debug.log", "error.log",
    "phpinfo.php", "info.php", "robots.txt", "sitemap.xml", "favicon.ico",
    "server-status", "server-info", "status", "health", "healthz", "metrics",
    "console", "manager", "manager/html", "dashboard", "panel", "cpanel",
    "user", "users", "profile", "account", "settings",
    "wp-admin", "wp-login.php", "wp-content", "xmlrpc.php",
    "actuator", "actuator/health", "actuator/env",
]

# 后缀变体：真实事故里大量敏感文件是"主文件 + 备份后缀"，
# 例如 index.php.bak / config.php~ / db.sql.zip（编辑器自动备份、运维手工打包）
SUFFIXES = [".bak", ".old", "~", ".swp", ".zip", ".tar.gz", ".1"]


def guard(target_url: str, has_auth: bool) -> None:
    """合规检查：非本机目标必须显式声明授权。"""
    host = urlparse(target_url).hostname or ""
    if host in LOCAL_HOSTS:
        return
    if has_auth:
        print(f"⚠️  你声明了对 {host} 的授权。请确认授权书覆盖该域名/时间窗/速率上限。")
        return
    print("=" * 68)
    print("⛔ 拒绝执行：目标不是本机，且未声明授权。")
    print(f"   目标主机: {host}")
    print("   合法使用场景：自有资产 / 持有书面授权的资产 / 授权靶场。")
    print("   中国大陆相关法条：《刑法》285、286 条，《网络安全法》27 条。")
    print("   如确有授权，请追加参数：--i-have-authorization")
    print("=" * 68)
    sys.exit(2)


# ─────────────────────────────────────────────────────────────
# 0.5 可选依赖：本地靶场模块（提供纯标准库 HTTP 客户端）
# ─────────────────────────────────────────────────────────────
_LAB_CACHE = None


def load_lab():
    """按路径加载同目录的 `00-local-lab.py`。

    为什么不能直接 `import 00-local-lab`？
    → 模块名不能以数字开头，也不是合法标识符。标准姿势是用 importlib
      按**文件路径**加载（`spec_from_file_location`），返回一个模块对象。
      这也是加载插件的通用做法（mitmproxy 的 `-s` 也类似）。
    """
    global _LAB_CACHE
    if _LAB_CACHE is not None:
        return _LAB_CACHE
    path = Path(__file__).resolve().parent / "00-local-lab.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("day154_lab", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)               # type: ignore[union-attr]
    _LAB_CACHE = mod
    return mod


# ─────────────────────────────────────────────────────────────
# 1. 单次探测
# ─────────────────────────────────────────────────────────────
# 状态码 → (语义, 是否值得记录) 映射表。
# 注意 401/403/302 都算"存在"的证据，这是初学者最容易漏的点。
INTERESTING = {200, 201, 204, 301, 302, 307, 308, 401, 403, 405, 500, 501}
# 为什么 429/503 不在里面？因为它们是"限流信号"，与资源是否存在无关，
# 应当触发退避而不是被当成命中（示例 03 里专门处理）。
THROTTLE_CODES = {429, 503}


def make_session():
    """构造一个带连接复用的 Session。

    为什么要 Session（而不是每次 requests.get）？
    → Session 内部维护连接池，keep-alive 复用 TCP 连接，
      1 万次请求可以省掉 ~99% 的三次握手开销。扫描场景必须用。
    → 没有 requests 时退化为 StdlibSession（每次新建连接，慢，但功能一致）。
    """
    if HAVE_REQUESTS:
        s = requests.Session()
        s.headers.update({
            # 标识自己是谁。礼貌 + 出事时对方能联系到你。
            "User-Agent": "OwnedSiteAudit/1.0 (+self-check; contact: admin@example.com)",
            "Accept": "*/*",
            "Connection": "keep-alive",
        })
        # 把连接池放大到与线程数匹配，否则多线程会互相等连接
        adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        return s
    lab = load_lab()
    if lab is None:
        print("既没有 requests，也找不到同目录的 00-local-lab.py，无法建立连接。")
        sys.exit(3)
    s = lab.StdlibSession()
    s.headers.update({
        "User-Agent": "OwnedSiteAudit/1.0 (+stdlib-fallback)",
        "Accept": "*/*",
    })
    return s


def probe(session, base: str, word: str, timeout=5.0) -> dict:
    """请求一个路径，返回结构化结果。异常一律吞掉并标记，绝不让单点失败打断整体。"""
    # urljoin 的坑：base 必须以 "/" 结尾，否则 "/api" + "v1" 会得到 "/api/v1"？
    # 不一定 —— 会得到 "/v1"（把 api 当成文件名替换掉）。所以先 rstrip("/") 再补 "/"。
    url = urljoin(base.rstrip("/") + "/", word)
    rec = {"path": "/" + word.lstrip("/"), "url": url, "status": None,
           "length": None, "location": None, "error": None, "elapsed": None}
    t0 = time.time()
    try:
        # 关键参数：allow_redirects=False —— 我们要自己看 301/302 的 Location！
        # 若跟随跳转，"存在但需登录"的路径会返回登录页 200，信息全丢。
        r = session.get(url, timeout=(3, timeout), allow_redirects=False)
        rec["status"] = r.status_code
        rec["length"] = len(r.content)
        rec["location"] = r.headers.get("Location")
    except NET_ERRORS as e:
        # 单点失败绝不能炸掉整个扫描：记为 error 继续下一个
        rec["error"] = type(e).__name__
    rec["elapsed"] = round((time.time() - t0) * 1000)  # ms
    return rec


def expand_suffixes(words, suffixes=SUFFIXES):
    """给字典追加备份后缀变体，并保持顺序、去重。

    为什么必须去重？→ 字典里本来就有 "backup.zip"，再扩展一次会重复请求。
    为什么必须同时提高延迟？→ 字典膨胀 8 倍 = 请求量膨胀 8 倍，
      不降速就从"扫描"变成"DDoS 练习"（合规红线）。
    """
    out = []
    seen = set()
    for w in words:
        for cand in [w] + [w + s for s in suffixes]:
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
    return out


# ─────────────────────────────────────────────────────────────
# 2. 单线程版（慢，但便于理解）与线程池版（快）
# ─────────────────────────────────────────────────────────────
def scan_single(base: str, words: list, session=None) -> list:
    print("\n[单线程] 逐个请求，观察耗时增长 …")
    out = []
    s = session or make_session()
    try:
        t0 = time.time()
        for w in words:
            out.append(probe(s, base, w))
        print(f"[单线程] {len(words)} 个路径耗时 {time.time() - t0:.2f}s")
    finally:
        if session is None:
            s.close()
    return out


def scan_threaded(base: str, words: list, workers: int = 20, session=None) -> list:
    """线程池版：I/O 密集场景下收益接近线性。

    为什么用线程而不是协程？
    → requests 是同步阻塞库；扫描瓶颈在网络等待，线程在等 I/O 时会释放 GIL，
      所以线程池足够，改动成本最低。追求极限可换 httpx.AsyncClient。
    """
    print(f"\n[线程池 x{workers}] 并发请求 …")
    out = []
    t0 = time.time()
    s = session or make_session()
    try:
        # 每个线程一个 Session 也可以，但共享一个 Session 更省连接。
        # ⚠️ requests.Session 官方文档说它线程"基本安全"，但连接池是共享的；
        #    在极高并发下仍可能因为 pool_maxsize 不够而排队（见 README 2.7）。
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(probe, s, base, w): w for w in words}
            for fut in cf.as_completed(futures):
                try:
                    out.append(fut.result())
                except Exception as e:            # 兜底：绝不让一个任务炸掉整个扫描
                    out.append({"path": futures[fut], "status": None, "error": repr(e),
                                "length": None, "location": None, "elapsed": None})
        print(f"[线程池] {len(words)} 个路径耗时 {time.time() - t0:.2f}s")
    finally:
        if session is None:
            s.close()
    return out


# ─────────────────────────────────────────────────────────────
# 3. 结果展示
# ─────────────────────────────────────────────────────────────
def interesting_of(results: list) -> list:
    """挑出"值得看"的记录：命中状态码，或发生了网络错误。

    抽成独立函数是为了**可测试**：报告的输出格式会变，但"哪些算命中"
    的判定逻辑必须稳定 —— 这正是 --self-test 要锁住的东西。
    """
    hits = [r for r in results
            if r.get("status") in INTERESTING or r.get("error")]
    # 排序键：(是否没有状态码, 路径)。让输出稳定，便于 diff 两次扫描结果。
    hits.sort(key=lambda r: (r.get("status") is None, r.get("path") or ""))
    return hits


def report(results: list) -> None:
    """按"是否有价值"分类打印。"""
    interesting = interesting_of(results)

    print("\n" + "=" * 78)
    print(f"命中/异常共 {len(interesting)} 条（总请求 {len(results)} 条）")
    print("=" * 78)
    print(f"{'状态':>6}  {'长度':>8}  {'耗时(ms)':>8}  路径 / 重定向")
    print("-" * 78)
    for r in interesting:
        st = r.get("status")
        st_s = str(st) if st is not None else (r.get("error") or "ERR")[:6]
        ln = r.get("length")
        ln_s = str(ln) if ln is not None else "-"
        extra = ""
        if r.get("location"):
            extra = f"  →  {r['location']}"
        print(f"{st_s:>6}  {ln_s:>8}  {str(r.get('elapsed') or '-'):>8}  {r['path']}{extra}")

    # 按状态码统计，帮助理解"为什么 200 不一定是命中"
    c = Counter(str(r.get("status")) for r in results)
    print("\n状态码分布：", dict(sorted(c.items(), key=lambda kv: kv[0])))


# ─────────────────────────────────────────────────────────────
# 4. CLI
# ─────────────────────────────────────────────────────────────
def load_words(path):
    if not path:
        return BUILTIN_WORDLIST
    with open(path, encoding="utf-8", errors="ignore") as f:
        words = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    print(f"从 {path} 载入 {len(words)} 个词")
    return words


def main() -> int:
    ap = argparse.ArgumentParser(description="Day154 目录扫描基础示例（仅限授权目标）")
    ap.add_argument("--url", default="http://127.0.0.1/", help="目标根 URL")
    ap.add_argument("--wordlist", default=None, help="字典文件，一行一个路径")
    ap.add_argument("--workers", type=int, default=20, help="线程数（默认 20，建议 ≤50）")
    ap.add_argument("--suffixes", action="store_true",
                    help="启用备份后缀变体（字典膨胀 %d 倍，请同步降速）" % (len(SUFFIXES) + 1))
    ap.add_argument("--self-test", action="store_true", help="离线自检（不联网）")
    ap.add_argument("--i-have-authorization", action="store_true",
                    help="声明已获得对非本机目标的书面授权")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    guard(args.url, args.i_have_authorization)

    words = load_words(args.wordlist)
    if args.suffixes:
        before = len(words)
        words = expand_suffixes(words)
        print(f"后缀变体已启用：{before} → {len(words)} 条")
        args.workers = max(1, min(args.workers, 5))   # 自动降并发，别把自己变成 DDoS
        print(f"为控制请求速率，线程数自动降为 {args.workers}")

    print(f"目标: {args.url}")
    print(f"字典: {len(words)} 条 | 线程: {args.workers}")
    print(f"HTTP 后端: {'requests' if HAVE_REQUESTS else '标准库 urllib（未安装 requests）'}")
    print("提示：单线程版只跑前 30 条，避免演示太慢。")

    # 先跑一小段单线程，让你看到"串行有多慢"
    single = scan_single(args.url, words[:30])
    # 再跑全量线程池
    threaded = scan_threaded(args.url, words, workers=args.workers)

    report(threaded)
    # 单线程那一段的结果也打出来，方便对比"同样的请求，只是慢"
    print(f"\n（单线程 30 条里命中 {len(interesting_of(single))} 条）")

    print("\n📌 观察任务：")
    print("  1. 上面有没有 200 但其实不存在的路径？（提示：如果目标返回自定义 404 页，会有一大片）")
    print("  2. 有没有 302 但 Location 都相同的？它们的真实含义是什么？")
    print("  3. 单线程 30 条 vs 线程池全量，耗时差多少倍？")
    print("  → 这些问题的答案，都在 02-fingerprint-pitfalls.py 里。")
    return 0


# ═══════════════════════════════════════════════════════════════
# 5. 离线自检
# ═══════════════════════════════════════════════════════════════
class _FallbackSelfTest:
    """万一 00-local-lab.py 不在，用这个极简断言器保证自检仍可运行。"""

    def __init__(self, title):
        self.failures = 0
        self.total = 0
        print("=" * 70)
        print(f"{title}（离线自检，不联网）")
        print("=" * 70)

    def check(self, name, actual, expected):
        self.total += 1
        if actual == expected:
            print(f"✅ {name}: {actual!r}")
        else:
            self.failures += 1
            print(f"❌ {name}\n     实际值: {actual!r}\n     期望值: {expected!r}")

    def truthy(self, name, actual):
        self.total += 1
        if actual:
            print(f"✅ {name}")
        else:
            self.failures += 1
            print(f"❌ {name} → 期望真值，实际 {actual!r}")

    def finish(self):
        print("-" * 70)
        if self.failures:
            print(f"❌ {self.failures}/{self.total} 项断言失败")
            return 1
        print(f"✅ 全部 {self.total} 项断言通过")
        print("SELF-TEST OK")
        return 0


def self_test() -> int:
    lab = load_lab()
    t = lab.SelfTest("day-154 示例01 目录扫描基础") if lab else _FallbackSelfTest(
        "day-154 示例01 目录扫描基础")
    if lab is None:
        print("⚠️ 未找到 00-local-lab.py，将只跑纯函数断言。")

    # ── A. 纯函数：URL 构造 ──
    # 用鸭子类型的假 Session，直接验证 probe() 的路径拼接逻辑（不需要网络）
    class FakeResp:
        def __init__(self, status=200, body=b"x", headers=None):
            self.status_code = status
            self.content = body
            self.headers = headers or {}

    class FakeSession:
        def __init__(self, resp):
            self.resp = resp
            self.calls = []

        def get(self, url, timeout=None, allow_redirects=False, **kw):
            self.calls.append((url, allow_redirects))
            return self.resp

    fs = FakeSession(FakeResp(200, b"hello", {"Location": "/admin/"}))
    r = probe(fs, "http://127.0.0.1:8080", "admin")
    t.check("probe(): 路径字段", r["path"], "/admin")
    t.check("probe(): 请求 URL", r["url"], "http://127.0.0.1:8080/admin")
    t.check("probe(): 状态码", r["status"], 200)
    t.check("probe(): 正文长度", r["length"], 5)
    t.check("probe(): 取到 Location", r["location"], "/admin/")
    t.check("probe(): 明确要求不跟随重定向", fs.calls[0][1], False)

    # base 带/不带结尾斜杠，结果必须一致（urljoin 的经典坑）
    r1 = probe(FakeSession(FakeResp()), "http://127.0.0.1:8080/", "api/v1")
    r2 = probe(FakeSession(FakeResp()), "http://127.0.0.1:8080", "api/v1")
    t.check("probe(): base 结尾斜杠不影响结果", r1["url"], r2["url"])

    # 字典里写 "/admin" 或 "" 也不能拼出错误 URL
    t.check("probe(): 词带前导斜杠", probe(FakeSession(FakeResp()),
                                          "http://127.0.0.1:8080", "/admin")["path"], "/admin")
    t.check("probe(): 空词=根路径", probe(FakeSession(FakeResp()),
                                         "http://127.0.0.1:8080", "")["url"],
            "http://127.0.0.1:8080/")

    # ── B. 纯函数：异常隔离 ──
    # 用「当前后端真正会抛的异常基类」来构造异常，保证 requests / urllib
    # 两种环境下断言都成立（requests 把所有网络问题包成 RequestException）。
    _Boom = type("BoomError", (NET_ERRORS[0],), {})

    class BoomSession:
        def get(self, *a, **kw):
            raise _Boom("connection refused")

    rb = probe(BoomSession(), "http://127.0.0.1:8080", "admin")
    t.check("probe(): 网络异常被吞掉并标记", (rb["status"], rb["error"]),
            (None, "BoomError"))

    # ── C. 纯函数：状态码语义 ──
    for code in (301, 302, 401, 403):
        t.truthy(f"{code} 属于「值得记录」（存在性证据）", code in INTERESTING)
    t.check("404 不值得记录", 404 in INTERESTING, False)
    t.check("429/503 归入限流集合（不是命中）",
            (429 in INTERESTING, 503 in INTERESTING), (False, False))
    t.truthy("429 在 THROTTLE_CODES 里", 429 in THROTTLE_CODES)

    # ── D. 纯函数：结果筛选与排序 ──
    fake = [
        {"status": 404, "path": "/a", "error": None, "length": 1, "location": None,
         "elapsed": 1},
        {"status": 403, "path": "/b", "error": None, "length": 1, "location": None,
         "elapsed": 1},
        {"status": None, "path": "/c", "error": "Timeout", "length": None,
         "location": None, "elapsed": 1},
        {"status": 200, "path": "/d", "error": None, "length": 1, "location": None,
         "elapsed": 1},
    ]
    got = interesting_of(fake)
    t.check("interesting_of(): 过滤掉 404", [x["path"] for x in got], ["/b", "/d", "/c"])
    t.check("interesting_of(): 有状态码的排前面", got[0]["status"], 403)

    # ── E. 纯函数：后缀变体 ──
    exp = expand_suffixes(["admin", "admin.bak"])
    # 精确期望：admin 本身 + admin 的 7 种变体 + admin.bak 的 7 种变体
    # （"admin.bak" 本身在第二轮已经出现过，被去重掉）
    want = (["admin"] + ["admin" + sx for sx in SUFFIXES]
            + ["admin.bak" + sx for sx in SUFFIXES])
    t.check("expand_suffixes(): 展开结果逐项正确", exp, want)
    t.check("expand_suffixes(): 无重复", len(exp), len(set(exp)))
    t.check("expand_suffixes(): 原字典条目被保留", "admin" in exp, True)

    # ── F. 端到端：对着本地靶场真发请求（纯标准库，离线）──
    if lab is not None:
        srv = lab.start_lab(0, mode="soft404", slow_delay=0.05)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"
        try:
            s = lab.StdlibSession()
            words = ["admin", "admin/", "secret/", "login", "robots.txt",
                     "api/v1", "no-such-path-xyz"]
            got = {w: probe(s, base, w) for w in words}
            t.check("/admin → 301", got["admin"]["status"], 301)
            t.check("/admin Location → /admin/", got["admin"]["location"], "/admin/")
            t.check("/admin/ → 401（存在但需登录）", got["admin/"]["status"], 401)
            t.check("/secret/ → 403（存在但被拒）", got["secret/"]["status"], 403)
            t.check("/login → 302", got["login"]["status"], 302)
            t.check("/robots.txt → 200", got["robots.txt"]["status"], 200)
            t.check("/api/v1 → 200", got["api/v1"]["status"], 200)

            # 这一段是本示例的"故意缺陷"演示：软 404 让不存在也变 200
            t.check("不存在路径也返回 200（软404，本示例故意不处理）",
                    got["no-such-path-xyz"]["status"], 200)
            hits = interesting_of(list(got.values()))
            t.check("条条都算命中 → 包含误报", len(hits), len(words))

            # 同一批词在"严格 404"靶场上：误报消失
            srv2 = lab.start_lab(0, mode="strict404", slow_delay=0.05)
            try:
                base2 = f"http://127.0.0.1:{srv2.server_address[1]}"
                got2 = [probe(s, base2, w) for w in words]
                t.check("严格404靶场：未命中数", len(interesting_of(got2)), len(words) - 1)
                t.check("严格404靶场：不存在路径 → 404",
                        [r["status"] for r in got2 if r["path"] == "/no-such-path-xyz"], [404])
            finally:
                srv2.shutdown()
                srv2.server_close()

            # ── G. 并发收益：/slow 延迟 0.2s，6 次请求 ──
            srv3 = lab.start_lab(0, mode="strict404", slow_delay=0.2)
            try:
                base3 = f"http://127.0.0.1:{srv3.server_address[1]}"
                slow_words = ["slow"] * 6
                t0 = time.time()
                for w in slow_words:
                    probe(s, base3, w)
                single_ms = (time.time() - t0) * 1000
                t0 = time.time()
                scan_threaded(base3, slow_words, workers=6, session=s)
                threaded_ms = (time.time() - t0) * 1000
                t.truthy(
                    f"并发收益：单线程 {single_ms:.0f}ms vs 6线程 {threaded_ms:.0f}ms "
                    f"（提速 {single_ms / max(threaded_ms, 1):.1f}x）",
                    threaded_ms < single_ms * 0.8)
            finally:
                srv3.shutdown()
                srv3.server_close()
            s.close()
        finally:
            srv.shutdown()
            srv.server_close()

    return t.finish()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
