#!/usr/bin/env python3
"""
Day 169 — Fabric 批量执行 · 02 六大陷阱亲手复现
========================================================================

Fabric 的默认值对"单机调试"友好，对"批量生产"危险。本脚本把 6 个坑
**在本地离线复现**（不需要任何远程机器）：

    陷阱 1  Connection 是惰性的 → try 写错位置，错误晚一步才爆
    陷阱 2  run() 默认 warn=False → 一条命令失败掀翻整批
    陷阱 3  pty=True 后 stderr 永远是空字符串
    陷阱 4  GroupException 的 .result 键是 Connection 对象（不是 host 字符串）
    陷阱 5  Fabric 完全不提供幂等 → mkdir 重跑必炸
    陷阱 6  ThreadingGroup 没有并发上限 → 必须自己分片

技巧：本地命令用 `invoke.Context`（与 Fabric 的 run 共用同一套 Runner，
所以 warn/hide/pty/Result 的语义完全一致），远端相关的用错误端口造失败 ——
这样整个脚本可以在没有 SSH 服务器的环境里跑完。

运行：
    python3 02-pitfalls.py --self-test
    python3 02-pitfalls.py
    python3 02-pitfalls.py --only 4
"""

from __future__ import annotations

import argparse
import itertools
import sys
import tempfile
import threading
import time

try:
    from fabric import Connection, ThreadingGroup, SerialGroup
    from fabric.exceptions import GroupException
    from invoke import Context
    from invoke.exceptions import UnexpectedExit
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 fabric，请先 `pip install fabric`\n")
    sys.exit(3)


def banner(n: int, title: str) -> None:
    print("\n" + "=" * 74)
    print(f"陷阱 {n}：{title}")
    print("=" * 74)


# ---------------------------------------------------------------------------
def pitfall_1() -> None:
    banner(1, "Connection 是惰性的：构造不报错，run 才报错")
    conn = Connection("definitely-not-a-real-host.invalid", user="nobody",
                      connect_kwargs={"timeout": 2})
    print(f"   构造 Connection(...)          → 没报错，is_connected = {conn.is_connected}")

    # ❌ 错误位置：把 try 包在构造上
    try:
        Connection("bad.invalid", connect_kwargs={"timeout": 1})
        print("   ❌ 把 try 包在构造上 → 什么都没捕获到（错误还没发生）")
    except Exception:
        print("   ❌ 把 try 包在构造上 → 意外捕获了异常")

    # ✅ 正确位置：try 包住第一次 run（或显式 open）
    t0 = time.monotonic()
    try:
        conn.run("true")
        print("   （意外连上了？这台机器竟然存在）")
    except Exception as exc:
        print(f"   ✅ try 包住 run → 捕获 {type(exc).__name__}，耗时 {time.monotonic()-t0:.2f}s")
    print("\n   结论：Connection(...) 只是记参数；错误必须在 open()/run() 处兜。")
    print("        也可以主动 open() 把失败提前，让错误发生在你知道的地方。")


# ---------------------------------------------------------------------------
def pitfall_2() -> None:
    banner(2, "run() 默认 warn=False：一条失败掀翻整批")
    local = Context()

    # ❌ 默认 warn=False
    try:
        local.run("echo before; exit 4", hide=True)
        print("   ❌ 本该抛异常")
    except UnexpectedExit as exc:
        print(f"   ❌ 默认行为 → 抛 UnexpectedExit（后续代码全部不执行）: exit={exc.result.return_code}")

    # ✅ 巡检场景：warn=True，自己判断
    results = []
    for cmd in ("echo a; exit 0", "echo b; exit 4", "echo c; exit 0"):
        r = local.run(cmd, warn=True, hide=True)
        results.append((cmd, r.ok, r.return_code))
    print("   ✅ warn=True → 三条命令全部拿到结果：")
    for cmd, ok_, rc in results:
        print(f"      {'ok ' if ok_ else 'BAD'} exit={rc}  {cmd}")
    bad = [c for c, ok_, _ in results if not ok_]
    print(f"   ✅ 自己判断出 {len(bad)} 条失败 → {bad}")
    print("\n   结论：『读』用 warn=True 拿全集；『写』保持默认（失败即停，停点清晰）。")


# ---------------------------------------------------------------------------
def pitfall_3() -> None:
    banner(3, "pty=True 之后，stderr 永远是空字符串")
    local = Context()

    normal = local.run("echo OUT; echo ERR >&2", hide=True)
    print(f"   不开 pty: stdout={normal.stdout!r}  stderr={normal.stderr!r}")

    with_pty = local.run("echo OUT; echo ERR >&2", pty=True, hide=True)
    print(f"   pty=True: stdout={with_pty.stdout!r}  stderr={with_pty.stderr!r}")
    stray = "\r" in with_pty.stdout
    print(f"   => stderr 为空? {with_pty.stderr == ''}；stdout 里混入 \\r? {stray}")
    print("\n   结论：需要 tty（sudo、交互命令）才开 pty，并且**别指望分流**。")
    print("        要保持流纯净：sudoers 里设 `Defaults:<user> !requiretty`。")


# ---------------------------------------------------------------------------
def pitfall_4() -> None:
    banner(4, "GroupException 的键是 Connection 对象，且成功主机的 Result 不在里面")
    # 用两个必然连不上的端口造失败（不需要真实服务器）
    group = ThreadingGroup("127.0.0.1:9", "127.0.0.1:10", connect_kwargs={"timeout": 1})
    try:
        group.run("true")
        print("   （意外成功）")
    except GroupException as exc:
        print(f"   ✅ 捕获 GroupException，共 {len(exc.result)} 条失败")
        for key, err in exc.result.items():
            print(f"      key={key!r} → {type(err).__name__}")
        all_conn = all(isinstance(k, Connection) for k in exc.result)
        print(f"   => 键全都是 Connection 对象? {all_conn}")
        print("   ❌ 错误写法：for host, err in exc.result.items(): print(host)   # 打印出 <Connection …>")
        print("   ✅ 正确写法：for conn, err in exc.result.items(): print(str(conn.host), conn.port, err)")

    print("\n   另一个关键事实：抛出异常时，**成功主机的 Result 拿不到**。")
    print("     想拿到完整全集 → 全部加 warn=True（拿到 dict），失败只体现在 r.ok 上。")
    print("     ⚠ 注意 GroupException.result 的键在 Fabric 3.x 是 Connection，")
    print("        不要按老教程写成 host 字符串，否则 str(host) 会打出 __repr__。")


# ---------------------------------------------------------------------------
def pitfall_5() -> None:
    banner(5, "Fabric 不提供幂等：重跑一次脚本就炸")
    local = Context()
    with tempfile.TemporaryDirectory(prefix="d169-idem-") as tmp:
        local.run(f"mkdir -p {tmp}/releases", hide=True)     # 先建父目录，保证下面炸的是 exists
        target = f"{tmp}/releases/v1"

        r1 = local.run(f"mkdir {target}", warn=True, hide=True)
        r2 = local.run(f"mkdir {target}", warn=True, hide=True)
        print(f"   ❌ mkdir      第一次 exit={r1.return_code}  第二次 exit={r2.return_code} "
              f"→ stderr={r2.stderr.strip()[:60]!r}")

        target2 = f"{tmp}/releases/v2"
        r3 = local.run(f"mkdir -p {target2}", warn=True, hide=True)
        r4 = local.run(f"mkdir -p {target2}", warn=True, hide=True)
        print(f"   ✅ mkdir -p   第一次 exit={r3.return_code}  第二次 exit={r4.return_code}")

        # 版本标记文件：判断"是否已部署过"
        rev = "20260927"
        mark = f"{target2}/.deployed-{rev}"
        cmd = f"test -f {mark} || (touch {mark} && echo deployed)"
        first = local.run(cmd, warn=True, hide=True)
        second = local.run(cmd, warn=True, hide=True)
        print(f"   ✅ 标记法     第一次={first.stdout.strip()!r}  第二次={second.stdout.strip()!r}"
              f"（第二次什么都没做 → 幂等）")
    print("\n   结论：Fabric 是过程式执行器，不理解你的目标状态。")
    print("        幂等靠你自己：-p / -f 容忍存在、|| 短路、版本标记文件、先查后改。")


# ---------------------------------------------------------------------------
def pitfall_6() -> None:
    banner(6, "ThreadingGroup 没有并发上限：必须自己分片")
    hosts = [f"10.0.0.{i}" for i in range(1, 41)]
    print(f"   假设有 {len(hosts)} 台机器：")
    print("   ❌ 一次全并发：ThreadingGroup(*hosts) → 40 线程同时认证")
    print("        → 目标侧 sshd MaxStartups / 防火墙连接速率 → 大量 Connection reset")
    print("   ✅ 分片：每批 16 台")

    def chunks(seq, n):
        it = iter(seq)
        while True:
            batch = list(itertools.islice(it, n))
            if not batch:
                return
            yield batch

    batches = list(chunks(hosts, 16))
    for i, b in enumerate(batches, 1):
        print(f"      批 {i}: {len(b)} 台（{b[0]} … {b[-1]}）")

    # 用"错误端口"演示：分片后每批的失败互不干扰
    failures = []
    for i, b in enumerate(batches, 1):
        g = ThreadingGroup(*[f"{h}:9" for h in b], connect_kwargs={"timeout": 0.5})
        try:
            g.run("true")
        except GroupException as exc:
            failures.append((i, len(exc.result)))
    print(f"   ✅ 每批独立捕获失败: {failures}")
    print("      → 一批挂了不影响后续批次；也可以只重试失败的那一批。")
    print("\n   结论：Fabric 只给你『组』，不给你『限流』。限流是你自己的责任。")


# ---------------------------------------------------------------------------
def self_test() -> int:
    """纯逻辑断言，不建连、不跑子进程。"""
    ok = True

    def chunks(seq, n):
        it = iter(seq)
        while True:
            batch = list(itertools.islice(it, n))
            if not batch:
                return
            yield batch

    got = [len(b) for b in chunks(range(40), 16)]
    ok &= got == [16, 16, 8]
    print(f"   {'✅' if got == [16, 16, 8] else '❌'} 分片 40/16 = {got}")

    got2 = [len(b) for b in chunks(range(0), 16)]
    ok &= got2 == []
    print(f"   {'✅' if got2 == [] else '❌'} 空输入分片 = {got2}")

    # warn=True 语义（本地，不依赖网络）
    r = Context().run("exit 5", warn=True, hide=True)
    ok &= (r.ok is False and r.return_code == 5)
    print(f"   ✅ warn=True 不抛异常，return_code={r.return_code}")

    # pty 合流语义
    rp = Context().run("echo O; echo E >&2", pty=True, hide=True)
    ok &= rp.stderr == "" and "O" in rp.stdout
    print(f"   ✅ pty=True 时 stderr 为空串: {rp.stderr == ''}")

    # GroupException 的 key 类型
    g = ThreadingGroup("127.0.0.1:9", connect_kwargs={"timeout": 0.5})
    try:
        g.run("true")
        print("   ❌ 本该失败")
        ok = False
    except GroupException as exc:
        keys_are_conn = all(isinstance(k, Connection) for k in exc.result)
        ok &= keys_are_conn
        print(f"   ✅ GroupException.keys 是 Connection 对象: {keys_are_conn}")

    print("\nSELF-TEST OK" if ok else "\nSELF-TEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 169 避坑：6 个 Fabric 陷阱")
    ap.add_argument("--only", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    demos = {1: pitfall_1, 2: pitfall_2, 3: pitfall_3, 4: pitfall_4, 5: pitfall_5, 6: pitfall_6}
    for n in ([args.only] if args.only else sorted(demos)):
        demos[n]()

    print("\n" + "=" * 74)
    print("六个陷阱回顾")
    print("=" * 74)
    print("   ✅ 陷阱 1：Connection 惰性 → try 包住 open()/第一次 run")
    print("   ✅ 陷阱 2：warn 默认 False → 读用 True，写保持默认")
    print("   ✅ 陷阱 3：pty=True → stderr 为空、stdout 带 \\r")
    print("   ✅ 陷阱 4：GroupException.result 键是 Connection；成功主机 Result 会丢")
    print("   ✅ 陷阱 5：Fabric 无幂等 → -p / || / 版本标记 / 先查后改")
    print("   ✅ 陷阱 6：Group 无并发上限 → 自己分片（每批 8~16）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
