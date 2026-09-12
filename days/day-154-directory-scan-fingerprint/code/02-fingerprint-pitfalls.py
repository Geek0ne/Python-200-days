#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 154 · 示例 02 —— 指纹识别与软 404：7 个必须踩过的坑
=========================================================

运行：
    python3 02-fingerprint-pitfalls.py                     # 打 127.0.0.1:80
    python3 02-fingerprint-pitfalls.py --url http://127.0.0.1:8080
    python3 02-fingerprint-pitfalls.py --self-test          # 不联网，只跑纯函数自检

本文件把目录扫描/指纹识别中最容易翻车的 7 个点，每个都写成"错误做法 vs 正确做法"，
并且能在**没有真实目标**的情况下完成大多数验证（--self-test）。

坑位清单：
  坑 1  allow_redirects=True  → 302 全部变成 200，信息丢失
  坑 2  只看状态码             → 软 404 造成 100% 误报
  坑 3  只比长度不归一化        → 动态页面（时间戳/计数）永远"命中"
  坑 4  headers 大小写        → 用 r.headers["Server"] 可能 KeyError
  坑 5  r.text 解码猜测        → 中文/二进制内容乱码，哈希不稳定
  坑 6  favicon 哈希口径不一致 → 自己算的哈希查不到 Shodan
  坑 7  无限并发无退避         → 触发 WAF 429，扫描中断 + IP 被封

⚠️ 法律边界：与示例 01 相同，非本机目标必须显式声明授权。
"""

import argparse
import base64
import hashlib
import re
import sys
import time
from urllib.parse import urljoin, urlparse

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:
    print("需要 requests：pip install requests")
    sys.exit(1)

try:
    import mmh3 as _mmh3            # pip install mmh3
except ImportError:
    _mmh3 = None                    # 没装也能跑，只是跳过 favicon 哈希

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


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
        print(f"  ❌ 默认跟随跳转: status={r_bad.status_code} "
              f"len={len(r_bad.content)} history={[h.status_code for h in r_bad.history]}")
    except RequestException as e:
        print(f"  ❌ 默认跟随跳转: 请求失败 {type(e).__name__}")

    # ✅ 正确做法
    try:
        r_ok = session.get(url, timeout=5, allow_redirects=False)
        print(f"  ✅ 不跟随跳转:   status={r_ok.status_code} "
              f"len={len(r_ok.content)} Location={r_ok.headers.get('Location')}")
        print("     解读：302 到 /login 说明 /admin **确实存在**，只是需要登录。")
    except RequestException as e:
        print(f"  ✅ 不跟随跳转: 请求失败 {type(e).__name__}")


# ═══════════════════════════════════════════════════════════════
# 坑 2 + 3：软 404 与内容归一化
# ═══════════════════════════════════════════════════════════════
DIGITS_RE = re.compile(rb"\d+")
WS_RE = re.compile(rb"\s+")
TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)


def normalize(content: bytes) -> bytes:
    """内容归一化：去掉一切"天然会变"的部分。

    为什么必须归一化？
    → 页脚的时间戳、访问计数、CSRF nonce 每次请求都不同，
      直接 sha256 会得到"每次都不一样"的哈希 → 软 404 过滤失效。
    这里做三件事：数字→#、连续空白→单空格、去首尾空白。
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


class Baseline:
    """软 404 基线：用随机路径确定"不存在的资源长什么样"。"""

    def __init__(self):
        self.entries = []          # [(status, fp_hash, raw_len, norm_len, title)]
        self.wildcard = False      # 是否检测到通配响应

    def collect(self, session, base, n=3):
        print("\n" + "─" * 70)
        print("坑 2｜软 404：随机路径也能返回 200")
        print("─" * 70)
        for i in range(n):
            rnd = f"zz-not-exist-{int(time.time()) % 10**6}-{i}a9f3"
            url = urljoin(base.rstrip("/") + "/", rnd)
            try:
                r = session.get(url, timeout=5, allow_redirects=False)
            except RequestException as e:
                print(f"  基线 {i}: 请求失败 {type(e).__name__}")
                continue
            h, raw, norm, title = fingerprint(r.content)
            self.entries.append((r.status_code, h, raw, norm, title))
            print(f"  基线 {i}: status={r.status_code} raw_len={raw} "
                  f"norm_len={norm} hash={h} title={title!r}")

        if len(self.entries) >= 3:
            hashes = {e[1] for e in self.entries}
            statuses = {e[0] for e in self.entries}
            self.wildcard = len(hashes) == 1 and 200 in statuses
            if self.wildcard:
                print("  ⚠️  检测到【通配响应】：随机路径也返回 200 且内容一致。")
                print("      → 如果你只看状态码，字典里每一条都会'命中'。")
            else:
                print("  ✅ 未检测到通配响应，基线可用于比对。")

    def is_soft404(self, status, fp_hash, norm_len, tolerance=0.05):
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

    print("\n  用基线过滤字典：")
    for w in words:
        url = urljoin(base.rstrip("/") + "/", w)
        try:
            r = session.get(url, timeout=5, allow_redirects=False)
        except RequestException as e:
            print(f"    {w:<20} 请求失败 {type(e).__name__}")
            continue
        h, raw, norm, _t = fingerprint(r.content)
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
    except RequestException as e:
        print(f"  请求失败 {type(e).__name__}")
        return
    print(f"  r.headers 类型: {type(r.headers).__name__}")
    # requests 的 headers 是 CaseInsensitiveDict，三种写法都能取到
    print(f"  r.headers['Server']            = {r.headers.get('Server')!r}")
    print(f"  r.headers.get('server')        = {r.headers.get('server')!r}  ← 小写也行")
    print(f"  r.headers.get('SERVER')        = {r.headers.get('SERVER')!r}  ← 全大写也行")
    print(f"  原始大小写: {[k for k in r.headers.keys() if k.lower() == 'server']}")
    print("  ✅ 结论：永远用 .get()，永远假设大小写任意。")
    print("     ⚠️ 若改用 aiohttp/http.client，原始 dict 是大小写敏感的，必须自行 lower()。")


# ═══════════════════════════════════════════════════════════════
# 坑 5：编码 —— 用 content 而不是 text
# ═══════════════════════════════════════════════════════════════
def demo_pitfall_5(session, base):
    print("\n" + "─" * 70)
    print("坑 5｜r.text 的编码猜测会让哈希不稳定")
    print("─" * 70)
    try:
        r = session.get(base, timeout=5, allow_redirects=False)
    except RequestException as e:
        print(f"  请求失败 {type(e).__name__}")
        return
    print(f"  r.encoding（requests 猜测）: {r.encoding}")
    print(f"  r.apparent_encoding        : {r.apparent_encoding}")
    print(f"  len(r.content)={len(r.content)} bytes   len(r.text)={len(r.text)} chars")
    print("  ⚠️ 中文站点常见坑：声明 GBK，requests 猜成 ISO-8859-1，" )
    print("     text 里全是乱码；而 content 永远是原始字节，哈希稳定。")
    print("  ✅ 规则：算哈希/算长度/写文件 → 用 r.content；给人看 → r.text 但要指定编码。")


# ═══════════════════════════════════════════════════════════════
# 坑 6：favicon 哈希口径
# ═══════════════════════════════════════════════════════════════
def favicon_hash(data: bytes) -> int:
    """按 Shodan/Fofa 社区口径计算 favicon 哈希。

    口径（重要，两派都有）：
      A. mmh3.hash(base64.encodebytes(data))    ← 带换行的 base64
      B. mmh3.hash(base64.b64encode(data))      ← 标准 base64（无换行）
    Shodan 实际使用的是 A（因为它内部用了 Python 的 encodebytes）。
    查不到结果时，两个都试一遍。
    """
    if _mmh3 is None:
        raise RuntimeError("未安装 mmh3，无法计算 favicon 哈希（pip install mmh3）")
    return _mmh3.hash(base64.encodebytes(data))


def demo_pitfall_6(session, base):
    print("\n" + "─" * 70)
    print("坑 6｜favicon 哈希口径不一致 → 查不到指纹库")
    print("─" * 70)
    url = urljoin(base.rstrip("/") + "/", "favicon.ico")
    try:
        r = session.get(url, timeout=5, allow_redirects=False)
    except RequestException as e:
        print(f"  请求失败 {type(e).__name__}")
        return
    if r.status_code != 200 or not r.content:
        print(f"  目标没有可用 favicon（status={r.status_code}），跳过。")
        return
    print(f"  favicon 大小: {len(r.content)} bytes  content-type={r.headers.get('Content-Type')}")
    if _mmh3 is None:
        print("  ⚠️ 未安装 mmh3，跳过哈希计算。pip install mmh3")
        return
    h_a = _mmh3.hash(base64.encodebytes(r.content))   # 口径 A（Shodan）
    h_b = _mmh3.hash(base64.b64encode(r.content))     # 口径 B
    print(f"  口径 A mmh3.hash(base64.encodebytes): {h_a}")
    print(f"  口径 B mmh3.hash(base64.b64encode)  : {h_b}")
    print("  → 去 Shodan 搜 `http.favicon.hash:{值}`，或 Fofa 搜 `icon_hash=\"{值}\"`")
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
        r = session.get(base, timeout=5, allow_redirects=False)
        print(f"  本次探测目标状态: {r.status_code}")
        print(f"  响应头里的限流线索: Retry-After={r.headers.get('Retry-After')!r} "
              f"X-RateLimit-Remaining={r.headers.get('X-RateLimit-Remaining')!r}")
    except RequestException as e:
        print(f"  请求失败 {type(e).__name__}")


# ═══════════════════════════════════════════════════════════════
# 纯函数自检（不需要网络）
# ═══════════════════════════════════════════════════════════════
def self_test() -> int:
    print("=" * 70)
    print("离线自检（不联网）")
    print("=" * 70)

    # normalize
    # 两段页面只差"数字"和"空白"，归一化后必须完全一致
    a = b"<title>Not Found</title> count: 1024 \n\n\n"
    b = b"<title>Not Found</title>    count: 9987\t\n"
    assert normalize(a) == normalize(b), "normalize 应消除数字与空白差异"
    print("✅ normalize(): 数字/空白差异被消除")

    # fingerprint 提取标题
    h, raw, norm, title = fingerprint(b"<HTML><head><TITLE>Hi</TITLE></head></HTML>")
    assert title == "Hi", title
    print("✅ fingerprint(): 可提取 <title>")

    # Baseline 判定
    bl = Baseline()
    bl.entries = [(200, "abc123", 100, 100, "Not Found")]
    assert bl.is_soft404(200, "abc123", 100) is True
    assert bl.is_soft404(200, "different", 900) is False
    assert bl.is_soft404(404, "abc123", 100) is False
    print("✅ Baseline.is_soft404(): 哈希一致/长度容差/状态码不同 三种情形正确")

    # favicon 口径
    if _mmh3 is not None:
        fake = b"\x00\x01\x02\x03" * 64
        ha = _mmh3.hash(base64.encodebytes(fake))
        hb = _mmh3.hash(base64.b64encode(fake))
        assert isinstance(ha, int) and isinstance(hb, int)
        print(f"✅ favicon 哈希可计算: A={ha} B={hb}（两者不同，说明口径必须统一）")
    else:
        print("ℹ️  未安装 mmh3，跳过 favicon 自检")

    print("\n全部离线自检通过。")
    return 0


# ═══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="Day154 指纹识别避坑示例")
    ap.add_argument("--url", default="http://127.0.0.1/")
    ap.add_argument("--i-have-authorization", action="store_true")
    ap.add_argument("--self-test", action="store_true", help="只跑离线纯函数自检")
    args = ap.parse_args()

    rc = self_test()
    if args.self_test:
        return rc

    guard(args.url, args.i_have_authorization)

    s = requests.Session()
    s.headers.update({"User-Agent": "OwnedSiteAudit/1.0 (+self-check)"})

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

    print("\n" + "=" * 70)
    print("总结：把这 7 条做成检查表，你的扫描器误报率会下降一个数量级。")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
