#!/usr/bin/env python3
"""
Day 186 · 02 — 进阶用法：证书透明日志（crt.sh）被动收集子域名

原理：
  CA 签发 TLS 证书时必须把证书写进 Certificate Transparency (CT) 日志。
  日志公开可查，于是"某域名历史上签发过哪些证书"= "出现过哪些主机名"。
  这条路的好处是**不主动爆破**，对目标零打扰，且能发现字典里没有的名字。

坑：
  · crt.sh 经常 502 / 超时 —— 必须带重试和退避，不能当成稳定 API
  · name_value 一行可能有多个名字（换行分隔），要拆开
  · 结果里有 *.example.com 通配符，入库前通常去掉 '*.' 或单独标记
  · 大小写、末尾点、重复项都要归一化
  · 只能看到"签过证书"的主机，内网名、未上 TLS 的服务看不到

用法：
  python3 02-crt-sh-advanced.py --domain example.com
  python3 02-crt-sh-advanced.py --domain example.com --out crt.json
  python3 02-crt-sh-advanced.py --fixture fixture.json   # 离线解析
  python3 02-crt-sh-advanced.py --self-test              # 离线自证
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CRTSH_URL = "https://crt.sh/?q=%25.{domain}&output=json"
USER_AGENT = "LearnPython-AssetInventory/1.0 (educational; contact: local)"


def normalize_names(raw_names: list[str], domain: str, keep_wildcard: bool = False) -> list[str]:
    """把 crt.sh 的 name_value 列表清洗成规范主机名列表。"""
    domain = domain.lower().rstrip(".")
    out: set[str] = set()
    for raw in raw_names:
        for piece in str(raw).replace("\r", "\n").split("\n"):
            name = piece.strip().lower().rstrip(".")
            if not name or "@" in name:      # 过滤邮箱形式的条目
                continue
            if name.startswith("*."):
                if not keep_wildcard:
                    name = name[2:]
                else:
                    out.add(name)
                    continue
            if name == domain or name.endswith("." + domain):
                out.add(name)
    return sorted(out)


def fetch_crtsh(domain: str, timeout: float = 20.0, retries: int = 3) -> list[dict]:
    """带指数退避的 crt.sh 查询。失败会抛最后一次异常。"""
    url = CRTSH_URL.format(domain=urllib.parse.quote(domain))
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            if not isinstance(data, list):
                raise ValueError("crt.sh 返回的不是 JSON 数组")
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError, ValueError) as exc:
            last_err = exc
            wait = 2 ** (attempt - 1)
            print(f"[!] 第 {attempt}/{retries} 次失败: {exc}; {wait}s 后重试", file=sys.stderr)
            if attempt < retries:
                time.sleep(wait)
    raise RuntimeError(f"crt.sh 查询失败（已重试 {retries} 次）: {last_err}")


def extract_names(records: list[dict], domain: str, keep_wildcard: bool = False) -> list[str]:
    names: list[str] = []
    for record in records:
        value = record.get("name_value") or record.get("common_name") or ""
        names.append(value)
    return normalize_names(names, domain, keep_wildcard=keep_wildcard)


FIXTURE = [
    {"name_value": "www.example.com"},
    {"name_value": "api.example.com\n*.api.example.com"},
    {"name_value": "MAIL.Example.com."},
    {"name_value": "example.com"},
    {"name_value": "evil-example.com"},          # 后缀伪装，必须被过滤
    {"name_value": "notexample.com"},
    {"name_value": "admin@example.com"},          # 邮箱，必须被过滤
]


def self_test() -> int:
    got = extract_names(FIXTURE, "example.com")
    expected = ["api.example.com", "example.com", "mail.example.com", "www.example.com"]
    assert got == expected, (got, expected)

    got_wild = extract_names(FIXTURE, "example.com", keep_wildcard=True)
    assert "*.api.example.com" in got_wild, got_wild

    # 归一化：大小写、末尾点、重复
    dup = normalize_names(["A.Example.com", "a.example.com.", "a.example.com"], "example.com")
    assert dup == ["a.example.com"], dup

    print("✅ self-test passed: 换行拆分 / 通配符 / 大小写与末尾点归一化 / 后缀伪装过滤")
    print("   解析结果:", ", ".join(got))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="从证书透明日志收集子域名")
    parser.add_argument("--domain")
    parser.add_argument("--fixture", help="离线 JSON 文件（crt.sh 原始响应格式）")
    parser.add_argument("--out", help="结果写入 JSON")
    parser.add_argument("--keep-wildcard", action="store_true")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.domain:
        parser.error("需要 --domain，或用 --self-test")

    try:
        if args.fixture:
            with open(args.fixture, encoding="utf-8") as fh:
                records = json.load(fh)
            print(f"[*] 从本地 fixture 读取 {len(records)} 条证书记录")
        else:
            print(f"[*] 查询 crt.sh: {args.domain}（可能较慢，最多重试 {args.retries} 次）")
            records = fetch_crtsh(args.domain, timeout=args.timeout, retries=args.retries)
            print(f"[*] 收到 {len(records)} 条证书记录")
    except Exception as exc:
        print(f"[x] 采集失败: {exc}", file=sys.stderr)
        print("[x] 提示：crt.sh 不稳定，可先用 --fixture 验证解析逻辑；"
              "生产环境应接入多个 CT 数据源并做缓存。", file=sys.stderr)
        return 2

    names = extract_names(records, args.domain, keep_wildcard=args.keep_wildcard)
    print(f"[+] 去重后得到 {len(names)} 个主机名")
    for name in names:
        print(f"  - {name}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"domain": args.domain, "records": len(records), "names": names},
                      fh, ensure_ascii=False, indent=2)
        print(f"[*] 已写入 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

