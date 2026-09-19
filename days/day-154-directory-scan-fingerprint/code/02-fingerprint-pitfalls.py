#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 154 · 示例 02 —— 指纹识别与软 404：9 个必须踩过的坑
=========================================================

两种运行方式
------------
方式 A（联机演示：对着靶场/自有站点真发请求）:
    python3 code/00-local-lab.py --port 8080      # 另一个终端
    python3 code/02-fingerprint-pitfalls.py --url http://127.0.0.1:8080

方式 B（离线自检：完全离线、不装任何第三方库）:
    python3 code/02-fingerprint-pitfalls.py --self-test

本文件把目录扫描/指纹识别中最容易翻车的 9 个点，每个都写成"错误做法 vs 正确做法"，
并且能在**没有真实目标**的情况下完成全部验证（--self-test 会用同目录
`00-local-lab.py` 起一个回环靶场，全程 127.0.0.1，不联网）。

坑位清单：
  坑 1  allow_redirects=True  → 302 全部变成 200，信息丢失
  坑 2  只看状态码             → 软 404 造成 100% 误报
  坑 3  只比长度不归一化        → 动态页面（时间戳/计数）永远"命中"
  坑 4  headers 大小写        → 用 r.headers["Server"] 可能 KeyError
  坑 5  r.text 解码猜测        → 中文/二进制内容乱码，哈希不稳定
  坑 6  favicon 哈希口径不一致 → 自己算的哈希查不到 Shodan
  坑 7  无限并发无退避         → 触发 WAF 429，扫描中断 + IP 被封
  坑 8  r.headers.get_all()   → requests 根本没这个方法，线上直接 AttributeError
  坑 9  urljoin 吃掉 base 路径 → 子目录部署的站点会被整站扫错

⚠️ 法律边界：与示例 01 相同，非本机目标必须显式声明授权。

依赖说明
--------
· `requests` 可选（缺失时自动用 `00-local-lab.py` 里的标准库 urllib 实现）；
· `mmh3` 可选（缺失时自动用本文件内置的**纯 Python MurmurHash3 x86_32**，
  结果与 mmh3 逐位一致 —— self-test 里会做交叉校验）。
"""

import argparse
import base64
import hashlib
import importlib.util
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ── requests：可选 ──
try:
    import requests
    from requests.exceptions import RequestException

    HAVE_REQUESTS = True
    NET_ERRORS = (RequestException,)
except ImportError:                            # pragma: no cover
    requests = None                            # type: ignore[assignment]
    HAVE_REQUESTS = False
    NET_ERRORS = (OSError,)

# ── mmh3：可选（缺失时用下面自带的纯 Python 实现）──
try:
    import mmh3 as _mmh3

    HAVE_MMH3 = True
except ImportError:
    _mmh3 = None
    HAVE_MMH3 = False

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

_LAB_CACHE = None


def load_lab():
    """按路径加载同目录 `00-local-lab.py`（提供标准库 HTTP 客户端与回环靶场）。"""
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


def make_session():
    """返回一个可用的 HTTP 会话（requests 优先，标准库兜底）。"""
    if HAVE_REQUESTS:
        s = requests.Session()
        s.headers.update({"User-Agent": "OwnedSiteAudit/1.0 (+self-check)"})
        return s
    lab = load_lab()
    if lab is None:
        print("既没有 requests 也找不到 00-local-lab.py，无法建立连接。")
        sys.exit(3)
    s = lab.StdlibSession()
    s.headers.update({"User-Agent": "OwnedSiteAudit/1.0 (+stdlib-fallback)"})
    return s


def header_values(resp, name: str) -> list:
    """安全地取"可能出现多次"的响应头（Set-Cookie 最典型）。

    ⚠️ 坑 8 的核心：
      requests 的 `resp.headers` 是 `CaseInsensitiveDict`，**没有** `get_all()`。
      写成 `resp.headers.get_all("Set-Cookie")` 在真实运行时会直接
      AttributeError 崩掉（很多人的代码在"只跑单元测试"时看不出问题，
      因为单元测试用的是自己造的 dict）。
    正确做法：
      · 想拿全部同名头 → 走 `resp.raw.headers.getlist("Set-Cookie")`（urllib3）；
      · 只要一个字符串 → `resp.headers.get("Set-Cookie")`（多值会被 ", " 连接，
        但 Set-Cookie 用 ", " 连接后**无法安全拆分**，因为有 Expires=Wed, 21 Oct...）
      · 本函数把两种后端都包起来了，返回 list。
    """
    h = resp.headers
    if hasattr(h, "get_all"):                  # 本仓库 StdlibResponse 提供的方法
        return h.get_all(name)
    raw = getattr(resp, "raw", None)
    raw_headers = getattr(raw, "headers", None)
    if raw_headers is not None and hasattr(raw_headers, "getlist"):
        return raw_headers.getlist(name)
    v = h.get(name)
    return [v] if v else []


# ═══════════════════════════════════════════════════════════════
# 纯 Python MurmurHash3 x86_32 —— 没装 mmh3 时的离线降级路径
# ═══════════════════════════════════════════════════════════════
def murmur3_x86_32(data: bytes, seed: int = 0) -> int:
    """MurmurHash3 x86_32（Austin Appleby, 2011 公共领域算法），按规范实现。

    为什么值得自己实现一遍？
      · 环境里常常没有 mmh3（它是个 C 扩展，要编译）；
      · favicon 指纹查询要求哈希**与 Shodan/Fofa 完全一致**，
        所以必须严格照算法规范来，不能"近似"；
      · 32 位有符号整数的溢出/符号处理是最大的坑：
        所有乘法都要 & 0xFFFFFFFF，最后若 >= 0x80000000 要减去 2^32
        转成**有符号**（Shodan 页面上的 favicon hash 就是负数）。
    验证：self-test 用公开测试向量 foo → -156908512、hello → 613153351
    校验；若环境装了 mmh3，还会与 C 实现逐位对比。
    """
    c1 = 0xCC9E2D51
    c2 = 0x1B873593
    length = len(data)
    h1 = seed & 0xFFFFFFFF
    rounded_end = length & 0xFFFFFFFC           # 向下取整到 4 的倍数

    # 主体：每次处理 4 字节（小端序读取）
    for i in range(0, rounded_end, 4):
        k1 = (data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24))
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF        # rotl32(k1, 15)
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF        # rotl32(h1, 13)
        h1 = (h1 * 5 + 0xE6546B64) & 0xFFFFFFFF

    # 尾巴：剩下 1~3 字节
    k1 = 0
    tail = length & 0x03
    if tail == 3:
        k1 ^= data[rounded_end + 2] << 16
    if tail >= 2:
        k1 ^= data[rounded_end + 1] << 8
    if tail >= 1:
        k1 ^= data[rounded_end]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1

    # 收尾混合（fmix32）
    h1 ^= length
    h1 ^= h1 >> 16
    h1 = (h1 * 0x85EBCA6B) & 0xFFFFFFFF
    h1 ^= h1 >> 13
    h1 = (h1 * 0xC2B2AE35) & 0xFFFFFFFF
    h1 ^= h1 >> 16

    # 转有符号 32 位整数（这才是 Shodan/Fofa 显示的形式）
    return h1 - 0x100000000 if h1 >= 0x80000000 else h1


def mmh3_hash(data: bytes, seed: int = 0) -> int:
    """优先用 C 扩展 mmh3（快），没有就用纯 Python 实现（结果一致）。

    注意 mmh3.hash() 对 str 会先做 UTF-8 编码，对 bytes 直接算 ——
    为了跨工具一致，官方推荐先把 favicon 的原始字节 base64 成字符串再算。
    """
    if HAVE_MMH3:
        return _mmh3.hash(data, seed)
    return murmur3_x86_32(data, seed)


# ═══════════════════════════════════════════════════════════════
# 合规护栏
# ═══════════════════════════════════════════════════════════════
def guard(target_url: str, has_auth: bool) -> None:
    host = urlparse(target_url).hostname or ""
    if host in LOCAL_HOSTS:
        return
    if has_auth:
        print(f"⚠️  已声明对 {host} 的授权，继续。")
        return
    print("⛔ 拒绝执行：非本机目标且未声明授权。加 --i-have-authorization 表示你有书面授权。")
    sys.exit(2)


# ═══════════════════════════════════════════════════════════════
# 坑 1：allow_redirects 的默认值会毁掉你的扫描
# ═══════════════════════════════════════════════════════════════
def demo_pitfall_1(session, base):
    print("\n" + "─" * 70)
    print("坑 1｜allow_redirects=True：302 全被吞掉")
    print("─" * 70)
    path = "admin"
    url = urljoin(base.rstrip("/") + "/", path)

    # ❌ 错误做法
    try:
        r_bad = session.get(url, timeout=5)          # 默认 allow_redirects=True
        chain = "-" if not getattr(r_bad, "history", None) else " → ".join(
            str(h.status_code) for h in r_bad.history)
        print(f"  ❌ 默认跟随跳转: status={r_bad.status_code} "
              f"len={len(r_bad.content)} 重定向链={chain}")
        print("     解读：最终拿到 401/200，但**看不到**最初的 301/302 了。")
    except NET_ERRORS as e:
        print(f"  ❌ 默认跟随跳转: 请求失败 {type(e).__name__}")

    # ✅ 正确做法
    try:
        r_ok = session.get(url, timeout=5, allow_redirects=False)
        print(f"  ✅ 不跟随跳转:   status={r_ok.status_code} "
              f"len={len(r_ok.content)} Location={r_ok.headers.get('Location')}")
        print("     解读：301 → /admin/ 说明 /admin **确实存在**（只是目录要补斜杠）。")
    except NET_ERRORS as e:
        print(f"  ✅ 不跟随跳转: 请求失败 {type(e).__name__}")


# ═══════════════════════════════════════════════════════════════
# 坑 2 + 3：软 404 与内容归一化
# ═══════════════════════════════════════════════════════════════
DIGITS_RE = re.compile(rb"\d+")
WS_RE = re.compile(rb"\s+")
TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)
# 常见的"这个页面不存在"关键词（英文 + 中文），作为哈希/长度之外的第三道兜底
NOTFOUND_RE = re.compile(
    r"(not\s*found|does not exist|页面不存在|找不到|404)", re.I)


def normalize(content: bytes) -> bytes:
    """内容归一化：去掉一切"天然会变"的部分。

    为什么必须归一化？
    → 页脚的时间戳、访问计数、CSRF nonce 每次请求都不同，
      直接 sha256 会得到"每次都不一样"的哈希 → 软 404 过滤失效。
    这里做三件事：数字→#、连续空白→单空格、去首尾空白。
    ⚠️ 局限（务必知道）：只能压掉"纯数字/空白"的抖动。
      如果页面里有随机**字符串**（uuid、hex 串），归一化也没用 ——
      那种情况下要改用"结构性特征"（标题、状态码、关键 DOM 节点数）判定。
    """
    c = DIGITS_RE.sub(b"#", content)
    c = WS_RE.sub(b" ", c)
    return c.strip()


def fingerprint(content: bytes) -> tuple:
    """返回 (归一化哈希, 原始长度, 归一化长度, 页面标题)"""
    norm = normalize(content)
    title = ""
    m = TITLE_RE.search(content)
    if m:
        title = m.group(1).decode("utf-8", "ignore").strip()[:80]
    return (hashlib.sha256(norm).hexdigest()[:16], len(content), len(norm), title)


def looks_like_404(content: bytes, title: str = "") -> bool:
    """关键词判定：标题或正文里出现"不存在"的典型措辞。

    ⚠️ 这是三手段里最弱的一道（会被文案改动绕过），
       只能作为哈希/长度之外的补充提醒，不能作为主判据。
    """
    if title and NOTFOUND_RE.search(title):
        return True
    head = content[:4096]
    return bool(NOTFOUND_RE.search(head.decode("utf-8", "ignore")))


class Baseline:
    """软 404 基线：用随机路径确定"不存在的资源长什么样"。

    三种终局（self-test 会在靶场上逐一验证）：
      normal    —— 随机路径返回 404/其它非 200 → 站点规范，可按状态码 + 哈希判定
      soft404   —— 随机路径统一返回 200，但内容与首页不同（专用错误页）
      wildcard  —— 随机路径返回 200，且内容与首页**完全相同**（SPA try_files）
    区分 soft404 与 wildcard 很实用：
      · wildcard 站点**无法**用响应体判定存在性，只能靠状态码/头部差异，
        误报几乎不可避免，报告里必须标注"低置信度"；
      · soft404 站点只要哈希过滤做对，仍然能正常扫。
    """

    def __init__(self):
        self.entries = []          # [(status, fp_hash, raw_len, norm_len, title)]
        self.wildcard = False      # 兼容旧字段：是否检测到"任何路径都 200 且内容一致"
        self.kind = "unknown"      # normal / soft404 / wildcard / unknown

    def collect(self, session, base, n=3):
        print("\n" + "─" * 70)
        print("坑 2｜软 404：随机路径也能返回 200")
        print("─" * 70)
        for i in range(n):
            # 随机路径必须"绝对不可能存在"，且每次都不一样（防止打中被缓存的长尾）
            rnd = f"zz-not-exist-{int(time.time()) % 10**6}-{i}a9f3"
            url = urljoin(base.rstrip("/") + "/", rnd)
            try:
                r = session.get(url, timeout=5, allow_redirects=False)
            except NET_ERRORS as e:
                print(f"  基线 {i}: 请求失败 {type(e).__name__}")
                continue
            h, raw, norm, title = fingerprint(r.content)
            self.entries.append((r.status_code, h, raw, norm, title))
            print(f"  基线 {i}: status={r.status_code} raw_len={raw} "
                  f"norm_len={norm} hash={h} title={title!r}")

        if len(self.entries) >= 3:
            hashes = {e[1] for e in self.entries}
            statuses = {e[0] for e in self.entries}
            same_200 = (len(hashes) == 1 and 200 in statuses)
            self.wildcard = same_200
            if same_200:
                # 再取首页对比，区分"SPA 通配"和"自定义 404 页"
                self.kind = self._classify_catch_all(session, base, self.entries[0][1])
                if self.kind == "wildcard":
                    print("  ⚠️  检测到【通配路由】：随机路径返回 200，且内容与首页完全一致")
                    print("      → 这是 SPA 的 try_files $uri /index.html 配置。")
                    print("      → 状态码和响应长度完全失去判定能力，本工具只能按")
                    print("         '与首页哈希的差异' 判定，结果必须人工复核。")
                else:
                    print("  ⚠️  检测到【软 404】：随机路径返回 200，但内容是专用错误页")
                    print("      → 用「归一化哈希 + 长度容差」过滤即可正常扫描。")
            else:
                self.kind = "normal"
                print("  ✅ 未检测到通配响应，基线可用于比对。")

    def _classify_catch_all(self, session, base, baseline_hash) -> str:
        """catch-all 站点：首页哈希 == 基线哈希 → wildcard；否则 → soft404。"""
        try:
            r = session.get(base, timeout=5, allow_redirects=False)
        except NET_ERRORS:
            return "soft404"                   # 取不到首页就退化为保守判断
        home_hash = fingerprint(r.content)[0]
        return "wildcard" if home_hash == baseline_hash else "soft404"

    def is_soft404(self, status, fp_hash, norm_len, tolerance=0.05) -> bool:
        for (b_status, b_hash, _raw, b_norm, _t) in self.entries:
            if status != b_status:
                continue
            if fp_hash == b_hash:                       # 归一化后完全一致 → 铁定软404
                return True
            if b_norm and abs(norm_len - b_norm) / max(b_norm, 1) <= tolerance:
                return True                             # 长度在容差内 → 视为同一页面
        return False


def demo_pitfall_2_3(session, base, baseline: Baseline, words):
    print("\n" + "─" * 70)
    print("坑 3｜只比长度不比归一化内容：动态页面永远命中")
    print("─" * 70)

    # 纯函数演示：模拟两段"看起来不同、归一化后相同"的页面
    page_a = b"<html><title>Not Found</title><p>count: 1024</p></html>"
    page_b = b"<html><title>Not Found</title><p>count: 9987</p></html>"
    print(f"  raw sha256 相同?   {hashlib.sha256(page_a).hexdigest()[:12] == hashlib.sha256(page_b).hexdigest()[:12]}")
    print(f"  norm sha256 相同?  {hashlib.sha256(normalize(page_a)).hexdigest()[:12] == hashlib.sha256(normalize(page_b)).hexdigest()[:12]}")
    print("  ↑ 这就是为什么必须先归一化再哈希。")

    # 更细的一层：位数变化会让"严格等长比对"失效（1024 → 9987 长度不同）
    print(f"  额外提醒：严格等长比对会被『位数变化』击穿 —— "
          f"len(a)={len(page_a)} ≠ len(b)={len(page_b)}，"
          f"但归一化后都是 {len(normalize(page_a))} 字节。")

    print("\n  用基线过滤字典：")
    for w in words:
        url = urljoin(base.rstrip("/") + "/", w)
        try:
            r = session.get(url, timeout=5, allow_redirects=False)
        except NET_ERRORS as e:
            print(f"    {w:<20} 请求失败 {type(e).__name__}")
            continue
        h, raw, norm, title = fingerprint(r.content)
        soft = baseline.is_soft404(r.status_code, h, norm)
        if soft:
            verdict = "❌ 软404（丢弃）"
        elif r.status_code in (401, 403):
            verdict = "🔑 存在但受限"
        elif r.status_code in (301, 302, 307, 308):
            verdict = f"🔁 重定向 → {r.headers.get('Location')}"
        elif r.status_code == 404:
            verdict = "❌ 不存在"
        else:
            verdict = "✅ 命中"
            if looks_like_404(r.content, title):
                # 关键词是第三道兜底：命中但正文写着"不存在" → 高度可疑
                verdict = "🟡 命中但正文含『不存在』措辞，需人工确认"
        print(f"    {w:<20} status={r.status_code:<4} raw_len={raw:<7} → {verdict}")


# ═══════════════════════════════════════════════════════════════
# 坑 4：headers 大小写
# ═══════════════════════════════════════════════════════════════
def demo_pitfall_4(session, base):
    print("\n" + "─" * 70)
    print("坑 4｜响应头大小写：HTTP 头不区分大小写，字典取值区分")
    print("─" * 70)
    try:
        r = session.get(base, timeout=5, allow_redirects=False)
    except NET_ERRORS as e:
        print(f"  请求失败 {type(e).__name__}")
        return
    print(f"  r.headers 类型: {type(r.headers).__name__}")
    print(f"  r.headers['Server']            = {r.headers.get('Server')!r}")
    print(f"  r.headers.get('server')        = {r.headers.get('server')!r}  ← 小写也行")
    print(f"  r.headers.get('SERVER')        = {r.headers.get('SERVER')!r}  ← 全大写也行")
    print(f"  原始大小写: {[k for k in r.headers.keys() if k.lower() == 'server']}")
    print("  ✅ 结论：永远用 .get()，永远假设大小写任意。")
    print("     ⚠️ 若改用 http.client / 自己解析响应，原始 dict 是大小写敏感的，")
    print("        必须自行 lower() 归一化 —— 本仓库的 StdlibSession.CIHeaders 就是这么做的。")

    # 坑 8 的现场演示
    print("\n" + "─" * 70)
    print("坑 8｜r.headers.get_all() 在 requests 里并不存在")
    print("─" * 70)
    if HAVE_REQUESTS:
        print(f"  requests 版本 {requests.__version__}，"
              f"hasattr(r.headers, 'get_all') = {hasattr(r.headers, 'get_all')}")
        print("  ❌ 所以 `hdrs.get_all('Set-Cookie') or []` 会在真实运行时抛 AttributeError")
    print(f"  ✅ 用 header_values(r, 'Set-Cookie') 拿到 {len(header_values(r, 'Set-Cookie'))} 条："
          f" {header_values(r, 'Set-Cookie')}")
    print("     实现见本文件 header_values()："
          "优先 get_all()，其次 raw.headers.getlist()，最后退回 get()。")


# ═══════════════════════════════════════════════════════════════
# 坑 5：编码 —— 用 content 而不是 text
# ═══════════════════════════════════════════════════════════════
def demo_pitfall_5(session, base):
    print("\n" + "─" * 70)
    print("坑 5｜r.text 的编码猜测会让哈希不稳定")
    print("─" * 70)
    try:
        r = session.get(base, timeout=5, allow_redirects=False)
    except NET_ERRORS as e:
        print(f"  请求失败 {type(e).__name__}")
        return
    if HAVE_REQUESTS:
        print(f"  r.encoding（requests 猜测）: {r.encoding}")
        print(f"  r.apparent_encoding        : {r.apparent_encoding}")
        print(f"  len(r.content)={len(r.content)} bytes   len(r.text)={len(r.text)} chars")
    else:
        enc = r.headers.get("Content-Encoding")
        print(f"  Content-Encoding={enc!r}（标准库不会自动解压，本仓库的 .text 帮你做了）")
        print(f"  len(r.content)={len(r.content)} bytes   len(r.text)={len(r.text)} chars")
    print("  ⚠️ 中文站点常见坑：声明 GBK，requests 猜成 ISO-8859-1，")
    print("     text 里全是乱码；而 content 永远是原始字节，哈希稳定。")
    print("  ✅ 规则：算哈希/算长度/写文件 → 用 r.content；给人看 → r.text 但要指定编码。")


# ═══════════════════════════════════════════════════════════════
# 坑 6：favicon 哈希口径
# ═══════════════════════════════════════════════════════════════
def favicon_hash(data: bytes, style: str = "shodan") -> int:
    """按 Shodan/Fofa 社区口径计算 favicon 哈希。

    口径（重要，两派都有，必须先对齐再查库）：
      A. mmh3.hash(base64.encodebytes(data))    ← 带换行的 base64（Shodan 实际口径）
      B. mmh3.hash(base64.b64encode(data))      ← 标准 base64（无换行）
    Shodan 内部用的等价于 A（Python 的 encodebytes 会 76 字符换行）。
    查不到结果时，两个都试一遍 —— 这是最省事的工程解法。
    """
    if style == "shodan":
        return mmh3_hash(base64.encodebytes(data))
    return mmh3_hash(base64.b64encode(data))


def demo_pitfall_6(session, base):
    print("\n" + "─" * 70)
    print("坑 6｜favicon 哈希口径不一致 → 查不到指纹库")
    print("─" * 70)
    url = urljoin(base.rstrip("/") + "/", "favicon.ico")
    try:
        r = session.get(url, timeout=5, allow_redirects=False)
    except NET_ERRORS as e:
        print(f"  请求失败 {type(e).__name__}")
        return
    if r.status_code != 200 or not r.content:
        print(f"  目标没有可用 favicon（status={r.status_code}），跳过。")
        return
    print(f"  favicon 大小: {len(r.content)} bytes  content-type={r.headers.get('Content-Type')}")
    h_a = favicon_hash(r.content, "shodan")
    h_b = favicon_hash(r.content, "standard")
    print(f"  口径 A mmh3.hash(base64.encodebytes): {h_a}")
    print(f"  口径 B mmh3.hash(base64.b64encode)  : {h_b}")
    print(f"  （哈希引擎: {'C 扩展 mmh3' if HAVE_MMH3 else '内置纯 Python MurmurHash3'}）")
    print(f"  → 去 Shodan 搜 `http.favicon.hash:{h_a}`，或 Fofa 搜 `icon_hash=\"{h_a}\"`")
    print("  ⚠️ 注意：很多站点 favicon 是 302 到 CDN，务必 allow_redirects=False 先看状态。")


# ═══════════════════════════════════════════════════════════════
# 坑 7：限流与退避
# ═══════════════════════════════════════════════════════════════
def demo_pitfall_7(session, base):
    print("\n" + "─" * 70)
    print("坑 7｜无限并发无退避 → 429 后扫描全崩")
    print("─" * 70)
    print("  正确姿势（伪代码）：")
    print("""
    delay = 0.0
    for i in range(10000):
        r = get(urls[i])
        if r.status_code == 429 or r.status_code == 503:
            retry_after = float(r.headers.get("Retry-After", 5))
            delay = min(max(delay * 2, retry_after), 60)   # 指数退避，上限 60s
            time.sleep(delay)
            continue
        if delay > 0:
            delay = max(delay / 2 - 0.01, 0.0)             # 成功后缓慢恢复
        time.sleep(delay)
    """)
    try:
        r = session.get(urljoin(base.rstrip("/") + "/", "x-rate-probe"), timeout=5,
                        allow_redirects=False)
        print(f"  本次探测目标状态: {r.status_code}")
        print(f"  响应头里的限流线索: Retry-After={r.headers.get('Retry-After')!r} "
              f"X-RateLimit-Remaining={r.headers.get('X-RateLimit-Remaining')!r}")
    except NET_ERRORS as e:
        print(f"  请求失败 {type(e).__name__}")


# ═══════════════════════════════════════════════════════════════
# 坑 9：urljoin 会吃掉 base 的路径部分
# ═══════════════════════════════════════════════════════════════
def demo_pitfall_9():
    print("\n" + "─" * 70)
    print("坑 9｜urljoin(base, word) 把子目录部署的站点扫错")
    print("─" * 70)
    base = "http://127.0.0.1:8080/shop/"
    for w in ["admin", "/admin"]:
        print(f"  urljoin({base!r}, {w!r}) = {urljoin(base, w)!r}")
    print("  → 词条带前导斜杠时，urljoin 会**丢弃** base 的 /shop/ 前缀，")
    print("    你会把整个 /admin 从站点根开始扫 —— 既扫错目标，也越界探测。")
    print("  ✅ 正确做法：字典统一不含前导斜杠，或用 urlsplit 手动拼：")
    print("     base.rstrip('/') + '/' + word.lstrip('/')")


# ═══════════════════════════════════════════════════════════════
# 离线自检
# ═══════════════════════════════════════════════════════════════
class _FallbackSelfTest:
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
    if lab is not None:
        t = lab.SelfTest("day-154 示例02 指纹识别与软404")
    else:
        t = _FallbackSelfTest("day-154 示例02 指纹识别与软404")
        print("⚠️ 未找到 00-local-lab.py，只跑纯函数断言。")

    # ── 1. normalize ──
    # 两段页面只差"数字"和"空白"，归一化后必须完全一致
    a = b"<title>Not Found</title> count: 1024 \n\n\n"
    b = b"<title>Not Found</title>    count: 9987\t\n"
    t.check("normalize(): 数字↔#", normalize(b"count 1") , b"count #")
    t.check("normalize(): 数字/空白差异被消除", normalize(a), normalize(b))
    t.check("normalize(): 首尾空白被去掉", normalize(b"  x  "), b"x")
    # 局限性：随机字符串压不掉（必须知道这个边界）
    t.truthy("normalize(): 随机字符串仍会留下差异（已知局限）",
             normalize(b"csrf=ab12cd") != normalize(b"csrf=zz99yy"))

    # ── 2. fingerprint ──
    h, raw, norm, title = fingerprint(b"<HTML><head><TITLE>Hi</TITLE></head></HTML>")
    t.check("fingerprint(): 提取 <title>", title, "Hi")
    t.check("fingerprint(): 原始长度", raw, len(b"<HTML><head><TITLE>Hi</TITLE></head></HTML>"))
    t.check("fingerprint(): 哈希长度 16", len(h), 16)

    # ── 3. looks_like_404 ──
    t.check("looks_like_404(): 英文标题命中", looks_like_404(b"<title>404 Not Found</title>", "404 Not Found"), True)
    t.check("looks_like_404(): 中文正文命中", looks_like_404("页面不存在".encode(), ""), True)
    t.check("looks_like_404(): 正常页面不误报", looks_like_404(b"<title>Demo Shop</title>hello", "Demo Shop"), False)

    # ── 4. Baseline.is_soft404 ──
    bl = Baseline()
    bl.entries = [(200, "abc123", 100, 100, "Not Found")]
    t.check("is_soft404(): 哈希一致", bl.is_soft404(200, "abc123", 100), True)
    t.check("is_soft404(): 长度在容差内", bl.is_soft404(200, "different", 103), True)
    t.check("is_soft404(): 长度超容差且哈希不同", bl.is_soft404(200, "different", 900), False)
    t.check("is_soft404(): 状态码不同", bl.is_soft404(404, "abc123", 100), False)

    # ── 5. MurmurHash3：公开测试向量 ──
    # 这三个值是 mmh3 官方/社区广为引用的向量，用来锁住"纯 Python 实现是否等价"
    t.check("murmur3(\"\") = 0", murmur3_x86_32(b""), 0)
    t.check('murmur3("foo")', murmur3_x86_32(b"foo"), -156908512)
    t.check('murmur3("hello")', murmur3_x86_32(b"hello"), 613153351)
    if HAVE_MMH3:
        # 装了 C 扩展就逐位对比，确保降级实现与 mmh3 完全一致
        for sample in (b"", b"a", b"abc", bytes(range(256)),
                       base64.encodebytes(b"\x00\x01\x02" * 40)):
            t.check(f"纯 Python 与 mmh3 结果一致 (len={len(sample)})",
                    murmur3_x86_32(sample), _mmh3.hash(sample))
    else:
        print("ℹ️  未安装 mmh3，已用内置纯 Python MurmurHash3 实现（测试向量已校验）")

    # ── 6. favicon 两种口径 ──
    fake = b"\x00\x01\x02\x03" * 64
    h_a = favicon_hash(fake, "shodan")
    h_b = favicon_hash(fake, "standard")
    t.check("favicon 口径 A/B 都是 int", (isinstance(h_a, int), isinstance(h_b, int)),
            (True, True))
    t.truthy("favicon 口径 A/B 不同（所以必须统一口径）", h_a != h_b)
    # 同一份字节多次计算结果必须稳定（指纹库能命中的前提）
    t.check("favicon 哈希可复现", favicon_hash(fake, "shodan"), h_a)

    # ── 7. header_values（坑 8）──
    # 模拟 requests 的 CaseInsensitiveDict：可大小写不敏感取值，但**没有** get_all
    class DictLikeHeaders(dict):
        """模拟 requests 的 CaseInsensitiveDict：没有 get_all。"""

        def get(self, k, d=None):
            for kk, vv in self.items():
                if kk.lower() == k.lower():
                    return vv
            return d

    class FakeResp:
        headers = DictLikeHeaders({"Set-Cookie": "a=1, b=2"})

    t.check("header_values(): 无 get_all 时退回 get()",
            header_values(FakeResp(), "Set-Cookie"), ["a=1, b=2"])

    if lab is not None:
        ci = lab.CIHeaders([("Set-Cookie", "a=1"), ("Set-Cookie", "b=2"),
                            ("Server", "nginx/1.24.0")])

        class RealResp:
            headers = ci
            raw = None

        t.check("header_values(): 支持多次出现的头", header_values(RealResp(), "Set-Cookie"),
                ["a=1", "b=2"])
        t.check("header_values(): 大小写不敏感", header_values(RealResp(), "server"),
                ["nginx/1.24.0"])
        if HAVE_REQUESTS:
            t.check("坑8 证据：requests 的 headers 没有 get_all",
                    hasattr(requests.Response().headers, "get_all"), False)

    # ── 8. 端到端：靶场上验证基线分类与过滤 ──
    if lab is not None:
        words = ["robots.txt", "api/v1", "admin", "secret/", "no-such-xyz"]
        # 8.1 软 404 靶场
        srv = lab.start_lab(0, mode="soft404", slow_delay=0.01)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        s = lab.StdlibSession()
        try:
            bl = Baseline()
            bl.collect(s, base, n=3)
            t.check("软404靶场：判定为 catch-all（wildcard=True）", bl.wildcard, True)
            t.check("软404靶场：细分为 soft404（内容 ≠ 首页）", bl.kind, "soft404")
            # 三条基线的归一化哈希必须一致（计数器被归一化掉）
            t.check("软404靶场：3 条基线归一化哈希一致",
                    len({e[1] for e in bl.entries}), 1)
            # 关键实验：靶场的 hits 计数器会从个位数涨到两位数，
            #   · 归一化哈希：全程一致  → 能正确识别"同一个错误页"
            #   · 原始长度  ：9 → 10 时 +1 字节 → 严格等长比对会失效
            lens, hashes = set(), set()
            for _ in range(12):
                r = s.get(base.rstrip("/") + "/zz-counter-probe", timeout=5,
                        allow_redirects=False)
                h, raw, _n, _t = fingerprint(r.content)
                lens.add(len(r.content))
                hashes.add(h)
            t.check("软404靶场：多次基线采样，归一化哈希只有 1 种", len(hashes), 1)
            t.truthy(f"软404靶场：原始长度出现 {len(lens)} 种（计数器位数变化）",
                     len(lens) > 1)

            # 过滤效果：真实存在的路径保留，不存在的丢弃
            kept, dropped = [], []
            for w in words:
                r = s.get(urljoin(base.rstrip("/") + "/", w), timeout=5,
                          allow_redirects=False)
                h, _raw, norm, _title = fingerprint(r.content)
                if bl.is_soft404(r.status_code, h, norm):
                    dropped.append(w)
                elif r.status_code in (401, 403, 301, 302, 307, 308, 200, 201,
                                       204, 405, 500, 501):
                    kept.append(w)
            t.check("软404过滤：不存在的路径全部被丢弃", dropped, ["no-such-xyz"])
            t.check("软404过滤：存在的路径全部保留", sorted(kept),
                    sorted(["robots.txt", "api/v1", "admin", "secret/"]))
        finally:
            s.close()
            srv.shutdown()
            srv.server_close()

        # 8.2 通配路由靶场（SPA）
        srv = lab.start_lab(0, mode="wildcard", slow_delay=0.01)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        s = lab.StdlibSession()
        try:
            bl2 = Baseline()
            bl2.collect(s, base, n=3)
            t.check("通配靶场：判定为 wildcard（内容 == 首页）", bl2.kind, "wildcard")
            t.truthy("通配靶场：wildcard 标志为 True", bl2.wildcard)
        finally:
            s.close()
            srv.shutdown()
            srv.server_close()

        # 8.3 严格 404 靶场
        srv = lab.start_lab(0, mode="strict404", slow_delay=0.01)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        s = lab.StdlibSession()
        try:
            bl3 = Baseline()
            bl3.collect(s, base, n=3)
            t.check("严格404靶场：判定为 normal", bl3.kind, "normal")
            t.check("严格404靶场：不标记 wildcard", bl3.wildcard, False)
            t.check("严格404靶场：基线状态码都是 404",
                    sorted({e[0] for e in bl3.entries}), [404])
        finally:
            s.close()
            srv.shutdown()
            srv.server_close()

        # ── 9. favicon 哈希端到端：靶场的 favicon 必须稳定且可复现 ──
        srv = lab.start_lab(0, mode="strict404")
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        s = lab.StdlibSession()
        try:
            r1 = s.get(urljoin(base.rstrip("/") + "/", "favicon.ico"),
                       timeout=(3, 5), allow_redirects=False)
            r2 = s.get(urljoin(base.rstrip("/") + "/", "favicon.ico"),
                       timeout=(3, 5), allow_redirects=False)
            t.check("靶场 favicon 两次请求哈希一致",
                    favicon_hash(r1.content), favicon_hash(r2.content))
            t.check("靶场 favicon 长度符合预期", len(r1.content), len(lab.FAVICON))
            # gzip 正文：证明"压缩体里搜不到明文"这条坑确实存在
            rg = s.get(urljoin(base.rstrip("/") + "/", "gzip"),
                       timeout=(3, 5), allow_redirects=False)
            t.check("gzip 正文不能直接搜明文",
                    b"gzip body" in rg.content, False)
            t.truthy("gzip 解压后才能搜到明文（.text 帮我们做了）",
                     "gzip body" in rg.text)
        finally:
            s.close()
            srv.shutdown()
            srv.server_close()

    # ── 10. 坑 9：urljoin 行为（纯字符串，无需网络）──
    t.check("坑9: 词条带斜杠会丢掉 base 路径",
            urljoin("http://127.0.0.1:8080/shop/", "/admin"),
            "http://127.0.0.1:8080/admin")
    t.check("坑9: 不带斜杠才保留 base 路径",
            urljoin("http://127.0.0.1:8080/shop/", "admin"),
            "http://127.0.0.1:8080/shop/admin")

    return t.finish()


# ═══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="Day154 指纹识别避坑示例")
    ap.add_argument("--url", default="http://127.0.0.1/")
    ap.add_argument("--i-have-authorization", action="store_true")
    ap.add_argument("--self-test", action="store_true", help="只跑离线自检（含回环靶场）")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    guard(args.url, args.i_have_authorization)

    s = make_session()
    try:
        baseline = Baseline()
        baseline.collect(s, args.url, n=3)

        demo_pitfall_1(s, args.url)
        demo_pitfall_2_3(s, args.url, baseline,
                         ["admin", "login", "robots.txt", "zz-no-way-123",
                          "config", "api/v1", "backup.zip"])
        demo_pitfall_4(s, args.url)
        demo_pitfall_5(s, args.url)
        demo_pitfall_6(s, args.url)
        demo_pitfall_7(s, args.url)
        demo_pitfall_9()
    finally:
        s.close()

    print("\n" + "=" * 70)
    print("总结：把这 9 条做成检查表，你的扫描器误报率会下降一个数量级。")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
