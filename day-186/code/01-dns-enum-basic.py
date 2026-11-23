#!/usr/bin/env python3
"""
Day 186 · 01 — 基础用法：并发子域名枚举（纯标准库）

做三件事：
  1. 把"域名 + 字典"展开成候选主机名
  2. 并发做 DNS 解析，只保留能解析出 A/AAAA 记录的主机
  3. 检测 DNS 泛解析（wildcard），把"随机域名也能解析"的假结果过滤掉

为什么必须做第 3 步：
  很多域名配置了 *.example.com 泛解析，任何随机前缀都会返回同一个 IP。
  如果不先识别泛解析，你枚举 1 万个词就会得到 1 万个"资产"，全是假的。

用法：
  python3 01-dns-enum-basic.py --domain example.com
  python3 01-dns-enum-basic.py --domain example.com --workers 32 --json out.json
  python3 01-dns-enum-basic.py --self-test        # 离线自证，不碰网络
"""

from __future__ import annotations

import argparse
import json
import random
import socket
import string
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 一份"够用就好"的小字典。真实项目会读 SecLists 之类的大字典。
DEFAULT_WORDS = [
    "www", "api", "mail", "smtp", "pop", "imap", "dev", "test", "staging",
    "admin", "portal", "blog", "shop", "vpn", "git", "gitlab", "cdn",
    "static", "m", "app", "docs", "wiki", "status", "monitor", "grafana",
]


def resolve_host(host: str, timeout: float = 3.0) -> list[str]:
    """解析一个主机名，返回去重排序后的 IP 列表；失败返回 []。

    这里用 getaddrinfo 而不是 gethostbyname：
      - gethostbyname 只支持 IPv4
      - getaddrinfo 一次能拿到 A + AAAA，且跟随系统解析器（/etc/hosts、DNS）
    """
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, socket.timeout, OSError):
        return []
    finally:
        socket.setdefaulttimeout(old_timeout)

    # info[4] 是 sockaddr，(ip, port) 或 (ip, port, flowinfo, scopeid)
    return sorted({info[4][0] for info in infos})


def random_label(length: int = 12) -> str:
    """生成随机标签，用来探测泛解析。"""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def detect_wildcard(domain: str, resolver, attempts: int = 3) -> set[str]:
    """随机解析若干个不存在的前缀，若能解析，其 IP 集合就是泛解析 IP。

    取多次是为了避开轮询 DNS：泛解析可能返回一组不同的 IP。
    """
    wildcard_ips: set[str] = set()
    for _ in range(attempts):
        wildcard_ips.update(resolver(f"{random_label()}.{domain}"))
    return wildcard_ips


def enumerate_subdomains(
    domain: str,
    words: list[str],
    workers: int = 16,
    resolver=resolve_host,
    timeout: float = 3.0,
    filter_wildcard: bool = True,
) -> tuple[dict[str, list[str]], dict]:
    """并发枚举。返回 (命中字典, 统计信息)。"""
    started = time.perf_counter()

    wildcard_ips = detect_wildcard(domain, lambda h: resolver(h, timeout)) if filter_wildcard else set()

    hits: dict[str, list[str]] = {}
    errors = 0

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(resolver, f"{word}.{domain}", timeout): word
            for word in words
        }
        for fut in as_completed(futures):
            host = f"{futures[fut]}.{domain}"
            try:
                ips = fut.result()
            except Exception:  # 单个任务异常不应拖垮整轮
                errors += 1
                continue
            if not ips:
                continue
            # 泛解析过滤：IP 集合完全等于泛解析集合 -> 判定为假阳性
            if wildcard_ips and set(ips) == wildcard_ips:
                continue
            hits[host] = ips
            print(f"  [+] {host:<40} {', '.join(ips)}")

    elapsed = time.perf_counter() - started
    stats = {
        "domain": domain,
        "candidates": len(words),
        "found": len(hits),
        "errors": errors,
        "workers": workers,
        "wildcard_ips": sorted(wildcard_ips),
        "elapsed_sec": round(elapsed, 3),
        "rate_per_sec": round(len(words) / elapsed, 1) if elapsed else 0.0,
    }
    return hits, stats


def self_test() -> int:
    """离线自测：注入一个假 resolver，验证并发、泛解析过滤、统计。"""
    fake_dns = {
        "www.example.test": ["192.0.2.10"],
        "api.example.test": ["192.0.2.11", "2001:db8::11"],
        "mail.example.test": ["192.0.2.12"],
    }
    wildcard_ip = "192.0.2.99"

    def fake_resolver(host: str, timeout: float = 3.0) -> list[str]:
        time.sleep(0.005)  # 模拟解析延迟，让并发/串行的差异可测
        if host in fake_dns:
            return fake_dns[host]
        # 任何随机前缀都返回泛解析 IP，模拟 *.example.test
        return [wildcard_ip]

    words = ["www", "api", "mail", "nope", "also-nope"]
    hits, stats = enumerate_subdomains(
        "example.test", words, workers=8, resolver=fake_resolver
    )
    assert set(hits) == {"www.example.test", "api.example.test", "mail.example.test"}, hits
    assert hits["api.example.test"] == ["192.0.2.11", "2001:db8::11"]
    assert wildcard_ip in stats["wildcard_ips"]
    assert stats["found"] == 3
    print("✅ self-test passed: 并发枚举 / IPv6 / 泛解析过滤 均正常")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="并发子域名枚举（标准库实现）")
    parser.add_argument("--domain", help="目标根域名，如 example.com")
    parser.add_argument("--words", help="逗号分隔的字典；缺省用内置小字典")
    parser.add_argument("--words-file", help="每行一个词的字典文件")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--json", help="把结果写到这个 JSON 文件")
    parser.add_argument("--no-wildcard-filter", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.domain:
        parser.error("需要 --domain，或用 --self-test 离线自测")

    if args.words_file:
        with open(args.words_file, encoding="utf-8") as fh:
            words = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    elif args.words:
        words = [w.strip() for w in args.words.split(",") if w.strip()]
    else:
        words = DEFAULT_WORDS

    # 去重但保持顺序
    words = list(dict.fromkeys(words))
    print(f"[*] 目标 {args.domain}，候选 {len(words)} 个，并发 {args.workers}")
    hits, stats = enumerate_subdomains(
        args.domain,
        words,
        workers=args.workers,
        timeout=args.timeout,
        filter_wildcard=not args.no_wildcard_filter,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if stats["wildcard_ips"]:
        print(f"[!] 检测到泛解析 IP: {', '.join(stats['wildcard_ips'])}（已过滤）")

    if args.json:
        payload = {"stats": stats, "assets": hits}
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"[*] 已写入 {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

