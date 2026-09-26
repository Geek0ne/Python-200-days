#!/usr/bin/env python3
"""
Day 169 — Fabric 批量执行 · 03 进阶：分片并发 / 串行滚动 / 跳板机 / 分组巡检
========================================================================

Fabric 给了 Group，但没给"限流"、"滚动"、"分组"。03 就把这三件补齐：

    ① chunked_run()    —— 分片并发（每批 N 台），失败按批隔离、可单独重试
    ② rolling_run()    —— 串行滚动（变更类操作），一台失败立刻停并报告停点
    ③ with_gateway()   —— 跳板机（bastion）链路
    ④ survey()/巡检汇总 —— 把每台的 Result 归一化成结构化结论 + 退出码契约

核心设计取舍（README 2.4 / 3.4 讲过，这里落地）：
    · 读用并发：失败互不影响、可容忍单点
    · 写用串行：失败可判定、停点清晰
    · 并发必须分片：Fabric 无上限，200 台会撞目标机 MaxStartups

运行：
    python3 03-advanced-fabric.py --self-test
    python3 03-advanced-fabric.py --hosts 127.0.0.1:2222,127.0.0.1:9 \
            --user root --key /tmp/sshtest/id_ed25519 --cmd "uptime" --batch 8
    python3 03-advanced-fabric.py --hosts h1,h2 --user u --key k \
            --rolling --cmd "systemctl restart nginx"
    python3 03-advanced-fabric.py --hosts h1 --user u --key k \
            --gateway ops@bastion.example.com --cmd "hostname"
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys
import time
from dataclasses import dataclass, field

try:
    from fabric import Connection, ThreadingGroup, SerialGroup
    from fabric.exceptions import GroupException
    from invoke.runners import Result
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 fabric，请先 `pip install fabric`\n")
    sys.exit(3)


# ---------------------------------------------------------------------------
# 1. 纯逻辑：分片 & 结果归一化（可离线单测）
# ---------------------------------------------------------------------------
def chunked(seq: list, size: int):
    """把 seq 切成每片最多 size 个。size<=0 抛 ValueError（别静默当成不切）。"""
    if size <= 0:
        raise ValueError("batch 必须 > 0")
    it = iter(seq)
    while True:
        piece = list(itertools.islice(it, size))
        if not piece:
            return
        yield piece


@dataclass
class HostOutcome:
    host: str
    status: str = "ok"            # ok / failed / unreachable / skipped
    return_code: int | None = 0
    seconds: float = 0.0
    tail: str = ""
    error: str = ""

    def line(self) -> str:
        rc = "-" if self.return_code is None else self.return_code
        body = self.error or self.tail.splitlines()[0][:60] if (self.error or self.tail) else "(无输出)"
        return f"{self.host:<28}{self.status:<14}{str(rc):<6}{self.seconds:<8.2f}{body}"


def classify_exception(exc: BaseException) -> str:
    """异常 → 状态。为什么要分：'连不上' 和 '命令失败' 的处置完全不同。"""
    name = type(exc).__name__
    if name in ("NoValidConnectionsError", "AuthenticationException",
                "SSHException", "gaierror", "timeout", "TimeoutError"):
        return "unreachable"
    if name == "UnexpectedExit":
        return "failed"
    return "failed"


def decide_exit(outcomes: list[HostOutcome]) -> int:
    """0 全成功 / 2 部分失败 / 1 全失败（与 Day 168 的契约保持一致）。"""
    if not outcomes:
        return 1
    bad = [o for o in outcomes if o.status != "ok"]
    if not bad:
        return 0
    return 1 if len(bad) == len(outcomes) else 2


def render(outcomes: list[HostOutcome]) -> str:
    lines = ["=" * 96,
             f"{'主机':<26}{'状态':<14}{'退出码':<6}{'耗时(s)':<8}摘要",
             "-" * 96]
    for o in sorted(outcomes, key=lambda x: x.host):
        lines.append(o.line())
    lines.append("=" * 96)
    counts: dict[str, int] = {}
    for o in outcomes:
        counts[o.status] = counts.get(o.status, 0) + 1
    summary = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    lines.append(f"汇总：{summary}  总计={len(outcomes)}  退出码={decide_exit(outcomes)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. 分片并发（读）
# ---------------------------------------------------------------------------
def _host_label(conn) -> str:
    """Connection → 可读标签。

    ⚠ GroupResult 的键是 Connection 对象（不是字符串），
      而且 Connection 没有自定义 __str__，直接 print 会得到 <Connection host=…>。
    """
    host = getattr(conn, "host", None)
    port = getattr(conn, "port", None)
    if host is None:
        return str(conn)
    return f"{host}:{port}" if port else host


def _outcome_from(conn, value, seconds: float) -> HostOutcome:
    """把 GroupResult 的一个 (连接, 值) 归一化成 HostOutcome。

    关键：值可能是 **Result（成功或命令失败）**，也可能是 **Exception（连不上等）**。
    因为 GroupException 是对 GroupResult 的“薄包装”——异常时成功主机的 Result
    仍然藏在 exc.result 里。不会区分这两者，就会把成功的主机报成失败。
    """
    host = _host_label(conn)
    if isinstance(value, Result):
        tail = (value.tail("stdout") or value.tail("stderr")).strip()
        return HostOutcome(host, "ok" if value.ok else "failed",
                           value.return_code, seconds, tail)
    return HostOutcome(host, classify_exception(value), None, seconds,
                       error=f"{type(value).__name__}: {value}")


def chunked_run(hosts: list[str], commands: list[str], batch: int = 8,
                **conn_kwargs) -> list[HostOutcome]:
    """每批 batch 台并发执行；一批的失败不影响下一批。"""
    outcomes: list[HostOutcome] = []
    for bi, piece in enumerate(chunked(hosts, batch), 1):
        print(f"\n🔀 第 {bi} 批（{len(piece)} 台）: {', '.join(piece)}")
        t0 = time.monotonic()
        group = ThreadingGroup(*piece, **conn_kwargs)
        # warn=True：命令层面的非 0 退出码不抛异常，而是反映在 Result.ok 上。
        # ⚠ 但**连接级**失败（连不上/认证失败）仍然会抛 GroupException，
        #   所以两条路径都要处理 —— 而 GroupException 里其实同时包含
        #   成功主机的 Result 与失败主机的 Exception，不要一股脑当成失败。
        try:
            results = group.run(" && ".join(commands), warn=True, hide=True)
        except GroupException as exc:
            for conn, value in exc.result.items():
                outcomes.append(_outcome_from(conn, value, time.monotonic() - t0))
            continue
        for conn, r in results.items():
            outcomes.append(_outcome_from(conn, r, time.monotonic() - t0))
    return outcomes


# ---------------------------------------------------------------------------
# 3. 串行滚动（写）
# ---------------------------------------------------------------------------
def rolling_run(hosts: list[str], commands: list[str],
                health_cmd: str | None = None, **conn_kwargs) -> list[HostOutcome]:
    """一台一台来：失败立刻停，并明确报告"停在第几台"。

    为什么变更必须串行（README 2.4）：并发变更一旦中途失败，
    集群会处于"一半新一半旧"的中间态，而且你很难判断停在哪。
    串行的失败是"清晰可判定"的。
    """
    outcomes: list[HostOutcome] = []
    for i, host in enumerate(hosts, 1):
        print(f"\n▶ 滚动 {i}/{len(hosts)}: {host}")
        t0 = time.monotonic()
        try:
            with Connection(host, **conn_kwargs) as conn:
                for cmd in commands:
                    r = conn.run(cmd, warn=False, hide=True)   # 变更：失败即抛
                    print(f"   ✅ {cmd} (exit={r.return_code})")
                if health_cmd:
                    h = conn.run(health_cmd, warn=True, hide=True)
                    if not h.ok:
                        outcomes.append(HostOutcome(
                            host, "failed", h.return_code, time.monotonic() - t0,
                            h.tail("stdout") + h.tail("stderr"),
                            error=f"健康检查失败: {health_cmd}"))
                        print(f"   ❌ 健康检查失败 → 停止滚动（已成功 {i-1} 台）")
                        break
                    print(f"   ✅ 健康检查通过 ({health_cmd})")
            outcomes.append(HostOutcome(host, "ok", 0, time.monotonic() - t0, "全部命令成功"))
        except Exception as exc:
            status = classify_exception(exc)
            outcomes.append(HostOutcome(host, status, None, time.monotonic() - t0,
                                        error=f"{type(exc).__name__}: {exc}"))
            print(f"   ❌ {type(exc).__name__}: {exc}")
            print(f"   ⛔ 停止滚动：已成功 {i-1} 台，失败在第 {i} 台")
            # 后续主机标记为 skipped —— 让报告能看出"剩下的是被主动跳过的"
            for rest in hosts[i:]:
                outcomes.append(HostOutcome(rest, "skipped", None, 0.0,
                                            error="滚动已中止，未执行"))
            break
    return outcomes


# ---------------------------------------------------------------------------
# 4. 跳板机
# ---------------------------------------------------------------------------
def make_gateway(spec: str, key: str | None, timeout: float):
    """把 `user@host[:port]` 变成 gateway Connection。"""
    user, _, hostport = spec.partition("@")
    host, _, port = hostport.partition(":")
    kw = {"timeout": timeout, "banner_timeout": timeout, "auth_timeout": timeout}
    if key:
        kw["key_filename"] = os.path.expanduser(key)
    return Connection(host, user=user or None, port=int(port) if port else None,
                      connect_kwargs=kw)


# ---------------------------------------------------------------------------
# 5. 离线自检
# ---------------------------------------------------------------------------
def self_test() -> int:
    ok = True

    print("自检 1：chunked 分片")
    got = [len(p) for p in chunked(list(range(40)), 16)]
    ok &= got == [16, 16, 8]
    print(f"   {'✅' if got == [16, 16, 8] else '❌'} 40/16 → {got}")
    ok &= [len(p) for p in chunked([], 4)] == []
    print("   ✅ 空输入 → 无分片")
    try:
        list(chunked([1], 0))
        print("   ❌ batch=0 本该报错")
        ok = False
    except ValueError as exc:
        print(f"   ✅ batch=0 如期报错: {exc}")

    print("\n自检 2：异常分类")
    class NoValidConnectionsError(Exception): ...
    class AuthenticationException(Exception): ...
    class UnexpectedExit(Exception): ...
    cases = [(NoValidConnectionsError(), "unreachable"),
             (AuthenticationException(), "unreachable"),
             (UnexpectedExit(), "failed"),
             (ValueError(), "failed")]
    for exc, want in cases:
        got = classify_exception(exc)
        flag = "✅" if got == want else "❌"
        ok &= got == want
        print(f"   {flag} {type(exc).__name__} → {got}（期望 {want}）")

    print("\n自检 3：退出码契约")
    cases2 = [
        ([], 1),
        ([HostOutcome("a", "ok")], 0),
        ([HostOutcome("a", "ok"), HostOutcome("b", "failed", 1)], 2),
        ([HostOutcome("a", "unreachable", None)], 1),
        ([HostOutcome("a", "ok"), HostOutcome("b", "skipped", None)], 2),
    ]
    for outs, want in cases2:
        got = decide_exit(outs)
        flag = "✅" if got == want else "❌"
        ok &= got == want
        print(f"   {flag} {[o.status for o in outs]} → {got}（期望 {want}）")

    print("\n自检 4：报告渲染")
    table = render([HostOutcome("web-01", "ok", 0, 0.4, "up 3 days"),
                    HostOutcome("db-01", "unreachable", None, 8.0, error="timeout"),
                    HostOutcome("web-02", "skipped", None, 0.0, error="滚动已中止")])
    ok &= "退出码=2" in table and "skipped=1" in table
    for line in table.splitlines():
        print("   " + line)

    print("\nSELF-TEST OK" if ok else "\nSELF-TEST FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# 6. CLI
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Day 169 进阶：分片并发 / 滚动 / 跳板机")
    ap.add_argument("--hosts", help="逗号分隔的 host[:port]")
    ap.add_argument("--user")
    ap.add_argument("--key")
    ap.add_argument("--cmd", action="append", default=[])
    ap.add_argument("--batch", type=int, default=8, help="每批并发台数（8~16 推荐）")
    ap.add_argument("--rolling", action="store_true", help="串行滚动（变更类操作用）")
    ap.add_argument("--health-cmd", help="滚动模式下的健康检查命令")
    ap.add_argument("--gateway", help="跳板机 user@host[:port]")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.hosts:
        ap.error("需要 --hosts（或 --self-test）")

    hosts = [h.strip() for h in args.hosts.split(",") if h.strip()]
    commands = args.cmd or ["uptime"]

    ck: dict = {"timeout": args.timeout, "banner_timeout": args.timeout,
                "auth_timeout": args.timeout}
    if args.key:
        ck["key_filename"] = os.path.expanduser(args.key)
    gw = make_gateway(args.gateway, args.key, args.timeout) if args.gateway else None

    print(f"🎯 {len(hosts)} 台 · {'串行滚动' if args.rolling else f'分片并发(batch={args.batch})'}"
          f" · 命令 {commands}" + (f" · 跳板 {args.gateway}" if gw else ""))
    if gw:
        print("   ℹ 跳板模式下需逐台建连（Group 与 gateway 一起用时，建议改用 per-host Connection）")

    if args.rolling:
        outcomes = rolling_run(hosts, commands, args.health_cmd,
                               user=args.user, connect_kwargs=ck, gateway=gw)
    else:
        if gw:
            outcomes = []
            for h in hosts:
                outcomes.extend(chunked_run([h], commands, batch=1,
                                            user=args.user, connect_kwargs=ck, gateway=gw))
        else:
            outcomes = chunked_run(hosts, commands, batch=args.batch,
                                   user=args.user, connect_kwargs=ck)

    print("\n" + render(outcomes))
    return decide_exit(outcomes)


if __name__ == "__main__":
    sys.exit(main())
