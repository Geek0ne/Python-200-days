#!/usr/bin/env python3
"""
Day 181 — 发布管理
01 · 语义化版本（SemVer 2.0.0）：解析 / 比较 / 递增 / 范围匹配

SemVer 不是「版本号看起来顺眼」的约定，它是一套**可比较的偏序**：
只有严格三段式 + 预发布 + 构建元数据这四种成分，且比较规则被写进规范，
所以「哪个版本更新」是一个**可以算出来的确定答案**，而不是靠人眼看。

本脚本用纯标准库实现规范里的全部规则（不引第三方 semver 库），
因为：规则本身很短，而依赖一个库就看不见「+build 不参与比较」这类细节。

用法：
    python3 01-semver.py --self-test            # 离线自检：规范原文里的每个例子
    python3 01-semver.py --check 1.2.3-rc.1
    python3 01-semver.py --compare 1.0.0-alpha.1 1.0.0-beta
    python3 01-semver.py --bump 1.2.3 --part minor
    python3 01-semver.py --match '^1.2.3' 1.9.9
    python3 01-semver.py --parse 2.0.0+build.5
"""

import argparse
import re
import sys

# SemVer 2.0.0 规范附录里给出的官方正则（原样搬运，未改）
SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class InvalidVersion(ValueError):
    pass


def parse(version):
    """文本 -> 结构化版本号。不合法就抛 InvalidVersion（绝不做「尽量解析」）。"""
    if not isinstance(version, str):
        raise InvalidVersion(f"版本号必须是字符串，收到 {type(version).__name__}")
    m = SEMVER_RE.match(version.strip())
    if not m:
        raise InvalidVersion(f"不符合 SemVer 2.0.0：{version!r}")
    pre = m.group("prerelease")
    return {
        "major": int(m.group("major")),
        "minor": int(m.group("minor")),
        "patch": int(m.group("patch")),
        "prerelease": pre.split(".") if pre else [],   # 空列表 = 正式版
        "build": (m.group("build") or "").split(".") if m.group("build") else [],
        "raw": version.strip(),
    }


def fmt(v):
    """结构化版本号 -> 文本。"""
    s = f"{v['major']}.{v['minor']}.{v['patch']}"
    if v["prerelease"]:
        s += "-" + ".".join(v["prerelease"])
    if v["build"]:
        s += "+" + ".".join(v["build"])
    return s


def _is_num(x):
    return x.isdigit()


def compare_prerelease(a, b):
    """规则 11：预发布部分逐段比较。

    只有一句话要记：**数字段 < 字母段，且段数少的 < 段数多的**。
    所以 alpha < alpha.1 < beta，而 1.0.0-rc.1 < 1.0.0。
    """
    if not a and not b:
        return 0
    if not a:            # 无预发布 = 正式版 > 任何预发布
        return 1
    if not b:
        return -1
    for x, y in zip(a, b):
        if x == y:
            continue
        xn, yn = _is_num(x), _is_num(y)
        if xn and yn:
            return -1 if int(x) < int(y) else 1
        if xn != yn:
            # 数字标识符永远比字母标识符小
            return -1 if xn else 1
        return -1 if x < y else 1
    # 前缀相同：短的更小（alpha < alpha.1）
    if len(a) == len(b):
        return 0
    return -1 if len(a) < len(b) else 1


def compare(v1, v2):
    """-1 / 0 / 1。注意：**构建元数据不参与比较**（规范第 10 条）。"""
    a, b = (parse(v1), parse(v2)) if isinstance(v1, str) else (v1, v2)
    for key in ("major", "minor", "patch"):
        if a[key] != b[key]:
            return -1 if a[key] < b[key] else 1
    return compare_prerelease(a["prerelease"], b["prerelease"])


def sort_versions(versions):
    """把一批版本号按优先级排序（相同优先级的保持输入顺序）。"""
    import functools
    return sorted(versions, key=functools.cmp_to_key(compare))


def bump(version, part):
    """递增。规则来自规范 FAQ，尤其是「预发布 + patch」这条。"""
    v = parse(version) if isinstance(version, str) else dict(version)
    if part == "major":
        v.update(major=v["major"] + 1, minor=0, patch=0, prerelease=[], build=[])
    elif part == "minor":
        v.update(minor=v["minor"] + 1, patch=0, prerelease=[], build=[])
    elif part == "patch":
        # FAQ 特例：1.0.0-rc.1 的 patch 递增是 1.0.0（丢掉预发布），不是 1.0.0-rc.2
        if not v["prerelease"]:
            v["patch"] += 1
        v.update(prerelease=[], build=[])
    elif part == "prerelease":
        # 1.2.3 -> 1.2.4-0（先把 patch 挑上去，再加预发布），已有预发布则数字位 +1
        if not v["prerelease"]:
            v["patch"] += 1
            v["prerelease"] = ["0"]
        else:
            last = v["prerelease"][-1]
            if _is_num(last):
                v["prerelease"][-1] = str(int(last) + 1)
            else:
                v["prerelease"].append("0")
        v["build"] = []
    else:
        raise ValueError(f"未知的递增段：{part}")
    return fmt(v)


# --- 范围匹配 ---------------------------------------------------------------
def _op_match(op, version, target):
    c = compare(version, target)
    return {"=": c == 0, ">": c > 0, ">=": c >= 0, "<": c < 0, "<=": c <= 0}[op]


def match(expr, version):
    """极简范围匹配：支持 = > >= < <= 与 ^ ~ 与 x 通配，多个条件用空格或逗号连接。

    ^1.2.3  → >=1.2.3 <2.0.0        （0.x 特例见下）
    ~1.2.3  → >=1.2.3 <1.3.0
    1.2.x   → >=1.2.0 <1.3.0
    """
    parse(version)  # 先验证被检版本本身合法
    for clause in re.split(r"[,\s]+", expr.strip()):
        if not clause:
            continue
        if clause.startswith("^"):
            base = parse(clause[1:])
            if base["major"] != 0:
                lo = fmt(base)
                hi = f"{base['major'] + 1}.0.0"
            elif base["minor"] != 0:
                # 0.x 是不稳定区：^0.2.3 → >=0.2.3 <0.3.0（只放开 patch）
                lo = fmt(base)
                hi = f"0.{base['minor'] + 1}.0"
            else:
                lo = fmt(base)
                hi = f"0.0.{base['patch'] + 1}"
            if not (_op_match(">=", version, lo) and _op_match("<", version, hi)):
                return False
        elif clause.startswith("~"):
            base = parse(clause[1:])
            lo = fmt(base)
            hi = f"{base['major']}.{base['minor'] + 1}.0"
            if not (_op_match(">=", version, lo) and _op_match("<", version, hi)):
                return False
        elif "x" in clause.lower():
            base = clause.lower().replace("x", "0").split(".")
            lo = f"{base[0]}.{base[1]}.{base[2]}"
            if clause.lower().endswith(".x"):
                hi = f"{base[0]}.{int(base[1]) + 1}.0"
            else:
                hi = f"{base[0]}.{int(base[1]) + 1}.0"
            if not (_op_match(">=", version, lo) and _op_match("<", version, hi)):
                return False
        else:
            m = re.match(r"^(>=|<=|>|<|=)?(.*)$", clause)
            op = m.group(1) or "="
            if not _op_match(op, version, m.group(2)):
                return False
    return True


# --- 自检 -------------------------------------------------------------------
SPEC_CHAIN = [  # SemVer 规范第 11 条原文给的例子（顺序即优先级从小到大）
    "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta",
    "1.0.0-beta", "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0",
]


def self_test():
    # 1. 规范原文的优先级链，逐对必须 <
    for lo, hi in zip(SPEC_CHAIN, SPEC_CHAIN[1:]):
        assert compare(lo, hi) == -1, f"{lo} 应该 < {hi}"
        assert compare(hi, lo) == 1, f"{hi} 应该 > {lo}"
    assert sort_versions(list(reversed(SPEC_CHAIN))) == SPEC_CHAIN

    # 2. 构建元数据不参与比较
    assert compare("1.0.0+build.1", "1.0.0+build.999") == 0
    assert compare("1.0.0", "1.0.0+sha.abc") == 0

    # 3. 数字段 < 字母段（beta.11 里 11 是数字段）
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-2", "1.0.0-11") == -1, "数字段要按数值比，不是字典序"

    # 4. 非法版本必须报错，而不是被「猜」出来
    for bad in ["1.2", "01.2.3", "1.02.3", "1.2.3-", "1.2.3-01", "1.2.3+", "v1.2.3", "1.2.3.4"]:
        try:
            parse(bad)
        except InvalidVersion:
            pass
        else:
            raise AssertionError(f"{bad!r} 应该被判非法（SemVer 里没有 v 前缀，前导零也不允许）")

    # 5. 递增
    assert bump("1.2.3", "major") == "2.0.0"
    assert bump("1.2.3", "minor") == "1.3.0"
    assert bump("1.2.3", "patch") == "1.2.4"
    assert bump("1.2.3-rc.1", "patch") == "1.2.3", "预发布转正：1.2.3-rc.1 的 patch 递增是 1.2.3"
    assert bump("1.2.3", "prerelease") == "1.2.4-0"
    assert bump("1.2.3-rc.1", "prerelease") == "1.2.3-rc.2"

    # 6. 范围匹配
    assert match("^1.2.3", "1.9.9") and not match("^1.2.3", "2.0.0")
    assert match("^0.2.3", "0.2.9") and not match("^0.2.3", "0.3.0"), "0.x 只放开 patch"
    assert match("~1.2.3", "1.2.9") and not match("~1.2.3", "1.3.0")
    assert match(">=1.2.3, <2.0.0", "1.5.0") and not match(">=1.2.3, <2.0.0", "2.0.0")
    assert not match("^1.2.3", "1.0.0-rc.1"), "预发布默认低于同段正式版对应范围"

    print("✅ self-test 通过：规范优先级链 8 个版本全序正确 / +build 不参与比较 /"
          " 数字段按数值比 / 8 个非法输入被拒 / 6 条递增规则 / 5 条范围匹配规则成立")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Day 181 · 01 SemVer")
    ap.add_argument("--self-test", action="store_true", help="离线自检")
    ap.add_argument("--parse", metavar="V")
    ap.add_argument("--check", metavar="V", help="只验证合法性，退出码 0/1")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    ap.add_argument("--bump", metavar="V")
    ap.add_argument("--part", default="patch", choices=["major", "minor", "patch", "prerelease"])
    ap.add_argument("--match", nargs=2, metavar=("EXPR", "V"))
    ap.add_argument("--sort", nargs="*", metavar="V")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if args.parse:
        v = parse(args.parse)
        print(f"{v['raw']}")
        print(f"  major={v['major']} minor={v['minor']} patch={v['patch']}")
        print(f"  prerelease={v['prerelease'] or '(无 → 正式版)'}")
        print(f"  build={v['build'] or '(无)'}")
        print(f"  是否预发布={bool(v['prerelease'])}")
    elif args.check:
        try:
            parse(args.check)
        except InvalidVersion as e:
            print(f"❌ {e}")
            sys.exit(1)
        print(f"✅ {args.check} 是合法 SemVer")
    elif args.compare:
        c = compare(*args.compare)
        sym = {-1: "<", 0: "==", 1: ">"}[c]
        print(f"{args.compare[0]} {sym} {args.compare[1]}   (compare={c})")
    elif args.bump:
        print(f"{args.bump}  --{args.part}-->  {bump(args.bump, args.part)}")
    elif args.match:
        ok = match(args.match[0], args.match[1])
        print(f"{args.match[1]} {'✅ 落在' if ok else '❌ 不落在'} 范围 {args.match[0]}")
    elif args.sort:
        print(" -> ".join(sort_versions(args.sort)))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
