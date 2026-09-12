#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 154 · 示例 01 —— 目录扫描基础：从单线程到线程池
=========================================================

运行：
    python3 01-dir-brute-basics.py                     # 用内置小字典扫 127.0.0.1:80
    python3 01-dir-brute-basics.py --url http://127.0.0.1:8080
    python3 01-dir-brute-basics.py --wordlist /path/to/common.txt

目标：把"目录扫描"拆成 4 个可理解的步骤
    1) 构造 URL            2) 发请求（allow_redirects=False）
    3) 判定状态码语义       4) 并发化 + 汇总

⚠️ 法律边界：本脚本默认只允许 127.0.0.1 / localhost / ::1。
   扫描任何其它目标都需要书面授权，并且必须显式加 --i-have-authorization。
   这不是形式主义：把边界写进代码，是"安全工程师"和"脚本小子"的分水岭。

⚠️ 本脚本**没有**实现软 404 过滤（那是示例 02 的内容），
   故意保留这个缺陷，让你亲眼看到误报长什么样。
"""

import argparse
import concurrent.futures as cf
import sys
import time
from urllib.parse import urljoin, urlparse

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:  # pragma: no cover
    print("需要 requests：pip install requests")
    sys.exit(1)

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
# 1. 单次探测
# ─────────────────────────────────────────────────────────────
# 状态码 → (语义, 是否值得记录) 映射表。
# 注意 401/403/302 都算"存在"的证据，这是初学者最容易漏的点。
INTERESTING = {200, 201, 204, 301, 302, 307, 308, 401, 403, 405, 500, 501}


def make_session() -> "requests.Session":
    """构造一个带连接复用的 Session。

    为什么要 Session（而不是每次 requests.get）？
    → Session 内部维护连接池，keep-alive 复用 TCP 连接，
      1 万次请求可以省掉 ~99% 的三次握手开销。扫描场景必须用。
    """
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


def probe(session: "requests.Session", base: str, word: str, timeout=5.0) -> dict:
    """请求一个路径，返回结构化结果。异常一律吞掉并标记，绝不让单点失败打断整体。"""
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
    except RequestException as e:
        rec["error"] = type(e).__name__
    rec["elapsed"] = round((time.time() - t0) * 1000)  # ms
    return rec


# ─────────────────────────────────────────────────────────────
# 2. 单线程版（慢，但便于理解）与线程池版（快）
# ─────────────────────────────────────────────────────────────
def scan_single(base: str, words: list) -> list:
    print("\n[单线程] 逐个请求，观察耗时增长 …")
    out = []
    with make_session() as s:
        t0 = time.time()
        for w in words:
            out.append(probe(s, base, w))
        print(f"[单线程] {len(words)} 个路径耗时 {time.time() - t0:.2f}s")
    return out


def scan_threaded(base: str, words: list, workers: int = 20) -> list:
    """线程池版：I/O 密集场景下收益接近线性。

    为什么用线程而不是协程？
    → requests 是同步阻塞库；扫描瓶颈在网络等待，线程在等 I/O 时会释放 GIL，
      所以线程池足够，改动成本最低。追求极限可换 httpx.AsyncClient。
    """
    print(f"\n[线程池 x{workers}] 并发请求 …")
    out = []
    t0 = time.time()
    # 每个线程一个 Session 也可以，但共享一个 Session 更省连接（requests.Session 线程安全）
    with make_session() as s, cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(probe, s, base, w): w for w in words}
        for fut in cf.as_completed(futures):
            try:
                out.append(fut.result())
            except Exception as e:            # 兜底：绝不让一个任务炸掉整个扫描
                out.append({"path": futures[fut], "status": None, "error": repr(e),
                            "length": None, "location": None, "elapsed": None})
    print(f"[线程池] {len(words)} 个路径耗时 {time.time() - t0:.2f}s")
    return out


# ─────────────────────────────────────────────────────────────
# 3. 结果展示
# ─────────────────────────────────────────────────────────────
def report(results: list) -> None:
    """按"是否有价值"分类打印。"""
    interesting = [r for r in results
                   if r.get("status") in INTERESTING or r.get("error")]
    interesting.sort(key=lambda r: (r.get("status") is None, r.get("path") or ""))

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
    from collections import Counter
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
    ap.add_argument("--i-have-authorization", action="store_true",
                    help="声明已获得对非本机目标的书面授权")
    args = ap.parse_args()

    guard(args.url, args.i_have_authorization)

    words = load_words(args.wordlist)
    print(f"目标: {args.url}")
    print(f"字典: {len(words)} 条 | 线程: {args.workers}")
    print("提示：单线程版只跑前 30 条，避免演示太慢。")

    # 先跑一小段单线程，让你看到"串行有多慢"
    single = scan_single(args.url, words[:30])
    # 再跑全量线程池
    threaded = scan_threaded(args.url, words, workers=args.workers)

    report(threaded)

    print("\n📌 观察任务：")
    print("  1. 上面有没有 200 但其实不存在的路径？（提示：如果目标返回自定义 404 页，会有一大片）")
    print("  2. 有没有 302 但 Location 都相同的？它们的真实含义是什么？")
    print("  3. 单线程 30 条 vs 线程池全量，耗时差多少倍？")
    print("  → 这些问题的答案，都在 02-fingerprint-pitfalls.py 里。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
