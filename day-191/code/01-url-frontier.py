#!/usr/bin/env python3
"""Day 191 · 基础：URL 规范化 + Frontier 去重 + robots 准入

一个爬虫最先崩的地方不是解析，而是**同一个页面被抓了 8 遍**。
本脚本给出爬虫引擎最底层三件套：

  1. normalize()  —— 把“看起来不同的同一个 URL”折叠成一个规范形态
  2. Frontier     —— 待抓队列：去重 + 广度优先 + 抓取预算
  3. RobotsGate   —— robots.txt 的 Allow/Disallow 最长匹配判定

用法：
  python3 01-url-frontier.py --self-test            # 离线自检，不联网
  python3 01-url-frontier.py --demo                 # 打印规范化效果
  python3 01-url-frontier.py --crawl http://127.0.0.1:8099 --limit 30

--crawl 需要先起 00-local-server.py。
"""
from __future__ import annotations

import argparse
import posixpath
import urllib.parse as up
import urllib.request
import urllib.robotparser
from collections import deque

DEFAULT_PORTS = {"http": 80, "https": 443}
TRACKING_PREFIXES = ("utm_", "ref", "fbclid", "gclid", "spm")


def normalize(url: str, base: str | None = None) -> str | None:
    """返回规范 URL；不可抓（非 http/https）返回 None。

    规范化顺序是有讲究的：先补全相对路径，再拆解、再排序，
    否则 /a/../b 这类路径会在 query 排序后算出不同的键。
    """
    if base:
        url = up.urljoin(base, url)
    parts = up.urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme not in DEFAULT_PORTS:
        return None

    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return None
    # IPv6 需要重新加方括号，否则拼回去会坏掉
    netloc = f"[{host}]" if ":" in host else host
    port = parts.port
    if port and port != DEFAULT_PORTS[scheme]:
        netloc = f"{netloc}:{port}"

    # 路径：合并重复斜杠 → 解析 . / .. → 补根斜杠（但保留“无斜杠文件”语义）
    path = up.unquote(parts.path or "/")
    # 先折叠重复斜杠，再用 normpath 解析 . 与 ..（自检抓到过漏掉 .. 的 bug）
    path = "/" + "/".join(seg for seg in path.split("/") if seg)
    path = posixpath.normpath(path)
    if not path.startswith("/"):
        path = "/" + path
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")

    # query：丢掉跟踪参数、按键排序、空值保留
    kept = [(k, v) for k, v in up.parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith(TRACKING_PREFIXES)]
    kept.sort()
    query = up.urlencode(kept)

    # fragment 永不发给服务端，必须丢掉
    return up.urlunsplit((scheme, netloc, path, query, ""))


class Frontier:
    """待抓队列。为什么不用 list：list.pop(0) 是 O(n)，10 万 URL 会拖死。

    为什么不用 set 当队列：set 无序，等于随机爬，深度优先会先撞上
    “无限日历”型网站。deque + seen 组合才是正确姿势。
    """

    def __init__(self, max_pages: int = 1000) -> None:
        self.queue: deque[str] = deque()
        self.seen: set[str] = set()
        self.max_pages = max_pages
        self.done: list[str] = []
        self.skipped = 0
        self.budget_used = 0   # 只统计“真会去抓”的 URL
        self.blocked = 0

    def push(self, url: str, base: str | None = None) -> bool:
        canon = normalize(url, base)
        if canon is None or canon in self.seen or self.budget_used >= self.max_pages:
            self.skipped += canon is not None
            return False
        self.budget_used += 1
        self.seen.add(canon)
        self.queue.append(canon)
        return True

    def release(self) -> None:
        """URL 被 robots 拒绝时归还预算。否则禁区链接会白吃掉抓取额度，
        表现为“设了 40 页预算却只抓到 22 页”（Day 191 实测踩过）。"""
        self.budget_used = max(0, self.budget_used - 1)
        self.blocked += 1

    def pop(self) -> str | None:
        if not self.queue:
            return None
        url = self.queue.popleft()
        self.done.append(url)
        return url

    def __len__(self) -> int:
        return len(self.queue)


class RobotsGate:
    """robots.txt 判定。注意：必须用“最长匹配”而不是“先匹配到的规则”，
    否则 Disallow: /private 会被更早出现的 Allow: / 覆盖掉，
    结果就是爬虫合法地爬进了禁区。Python 的 RobotFileParser 已实现该语义。
    """

    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        self.base = base_url
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.set_url(up.urljoin(base_url, "/robots.txt"))
        self.loaded = False
        self.timeout = timeout

    def load(self) -> None:
        try:
            with urllib.request.urlopen(self.rp.url, timeout=self.timeout) as r:
                self.rp.parse(r.read().decode("utf-8", "replace").splitlines())
            self.loaded = True
        except Exception as e:  # 站点没 robots 是常态，不是错误
            print(f"  (robots 不可用: {e.__class__.__name__}; 默认放行)")
            self.rp.parse([])
            self.loaded = True

    def allowed(self, url: str) -> bool:
        if not self.loaded:
            self.load()
        return self.rp.can_fetch("*", url)


def extract_links(html: str, base: str) -> list[str]:
    """标准库没有 DOM，用最朴素的 href 抽取。生产请上 selectolax/lxml。"""
    out: list[str] = []
    idx = 0
    while True:
        i = html.find('href="', idx)
        if i < 0:
            break
        j = html.find('"', i + 6)
        if j < 0:
            break
        out.append(html[i + 6:j])
        idx = j + 1
    return out


def crawl(start: str, limit: int) -> dict:
    fr = Frontier(max_pages=limit)
    gate = RobotsGate(start)
    gate.load()
    fr.push(start)
    fetched = 0
    robots_blocked = 0
    while len(fr) and fetched < limit:
        url = fr.pop()
        if not gate.allowed(url):
            fr.release()
            robots_blocked += 1
            continue
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                html = r.read().decode("utf-8", "replace")
                fetched += 1
        except Exception as e:
            print(f"  ! {url} -> {e.__class__.__name__}")
            continue
        for link in extract_links(html, url):
            fr.push(link, base=url)
    return {"fetched": fetched, "queued_left": len(fr), "unique_seen": len(fr.seen),
            "dedup_skipped": fr.skipped, "robots_blocked": robots_blocked}


def self_test() -> int:
    cases = [
        ("HTTP://Example.COM:80/a/./b/../c?b=2&a=1#frag", None,
         "http://example.com/a/c?a=1&b=2"),
        ("https://example.com:443/x/?utm_source=t", None, "https://example.com/x"),
        ("http://example.com", None, "http://example.com/"),
        ("http://example.com/a//b///c", None, "http://example.com/a/b/c"),
        ("/page/2", "http://127.0.0.1:8099/page/1", "http://127.0.0.1:8099/page/2"),
        ("javascript:void(0)", None, None),
        ("mailto:a@b.c", None, None),
        ("http://example.com:8080/p", None, "http://example.com:8080/p"),
        ("http://example.com/%E4%B8%AD%E6%96%87", None, "http://example.com/中文"),
    ]
    bad = 0
    for raw, base, want in cases:
        got = normalize(raw, base)
        ok = got == want
        bad += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {raw!r} -> {got!r}" + ("" if ok else f"  (期望 {want!r})"))

    fr = Frontier(max_pages=10)
    for u in ["http://a.com/x", "http://a.com/x#1", "http://a.com/x?utm_source=z", "http://a.com/y"]:
        fr.push(u)
    ok = len(fr.seen) == 2
    bad += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  frontier 去重: seen={len(fr.seen)} (期望 2)")

    ok = fr.push("http://a.com/z") and fr.push("http://a.com/z") is False
    bad += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  frontier 重复入队被拒")
    print(f"\nself-test: {len(cases) + 2 - bad}/{len(cases) + 2} passed")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--crawl")
    ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.demo:
        for u in ["http://Example.com/a/../b/?utm_source=x&b=2&a=1#top",
                  "http://example.com/a/b", "http://example.com//a//b/"]:
            print(f"{u}\n  -> {normalize(u)}")
        return 0
    if a.crawl:
        print(crawl(a.crawl, a.limit))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
