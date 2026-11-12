#!/usr/bin/env python3
"""
Day 169 — Fabric 批量执行 · 01 基础用法
========================================================================

Fabric 把"连接 + 执行 + 取结果"压成了三行代码。但**省事的地方往往是出事的
地方**：默认参数（warn=False、pty=False、无超时）在单机调试时很舒服，
一上批量就会变成"一台失败中断整批"或"永远挂住"。

本脚本给出"最小但不天真"的单机用法：

    ① Connection 的惰性建连（构造不连，run 才连）
    ② 三个超时（connect/banner/auth）都塞进 connect_kwargs
    ③ run / sudo / put / get 四个动作的返回值与异常语义
    ④ 用 Result 的 ok / return_code / tail() 做结构化判断
    ⑤ with Connection(...) 保证收尾（否则脚本可能不退出）

运行：
    python3 01-basic-fabric.py --self-test
    python3 01-basic-fabric.py --host 127.0.0.1 --port 2222 --user root \
            --key /tmp/sshtest/id_ed25519 --cmd "uname -a" --cmd "df -h /"
    python3 01-basic-fabric.py --host <h> --user <u> --key <k> \
            --put ./a.txt:/tmp/a.txt --get /etc/hostname:./hostname.bak
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

try:
    from fabric import Connection
    from invoke.exceptions import UnexpectedExit
    from invoke.runners import Result
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 fabric，请先 `pip install fabric`\n")
    sys.exit(3)


# ---------------------------------------------------------------------------
# 1. 纯函数（可离线单测）
# ---------------------------------------------------------------------------
@dataclass
class HostSpec:
    host: str
    port: int | None = None

    @property
    def label(self) -> str:
        return f"{self.host}:{self.port}" if self.port else self.host


def parse_hostspec(text: str) -> HostSpec:
    """`host[:port]` → HostSpec。

    注意与 Day 168 的区别：Fabric 的 Connection 把 user/port 拆成独立参数，
    所以这里只解析 host 与 port（user 走 --user）。
    ⚠ 端口缺省时**返回 None**，交给 Fabric 用 22 作为默认值 —— 不要自己填 22，
       否则会覆盖 ~/.ssh/config 或 Config 里的配置（配置分层的意义就在这）。
    """
    text = text.strip()
    if not text:
        raise ValueError("主机不能为空")
    if text.startswith("["):                       # IPv6 字面量 [::1]:22
        end = text.find("]")
        if end == -1:
            raise ValueError(f"IPv6 缺少右方括号: {text!r}")
        host = text[1:end]
        tail = text[end + 1:]
        if not tail:
            return HostSpec(host, None)
        if not tail.startswith(":"):
            raise ValueError(f"IPv6 之后只能是 :port，收到 {tail!r}")
        return HostSpec(host, _port(tail[1:]))
    if ":" in text:
        host, _, p = text.rpartition(":")
        if not host:
            raise ValueError(f"主机不能为空: {text!r}")
        return HostSpec(host, _port(p))
    return HostSpec(text, None)


def _port(p: str) -> int:
    try:
        v = int(p)
    except ValueError as exc:
        raise ValueError(f"端口必须是数字: {p!r}") from exc
    if not 1 <= v <= 65535:
        raise ValueError(f"端口越界: {v}")
    return v


def describe(r: Result) -> str:
    """把 Result 压成一行人类可读摘要。"""
    state = "ok" if r.ok else f"FAILED(exit={r.return_code})"
    body = (r.stdout or "").strip() or (r.stderr or "").strip()
    first = body.splitlines()[0][:60] if body else "(无输出)"
    return f"[{state}] {r.command} → {first}"


def classify(r: Result) -> str:
    """把 Result 归类到自动化能消费的四种状态。

    ⚠ 重要的 API 事实（我踩过）：invoke 的 `Result.exited` **不是 bool**，
      它就是退出码本身（int，没跑完时为 None）；`return_code` 只是它的别名，
      `ok` 才是 `exited == 0`。所以千万不要写 `if not r.exited`
      —— 成功的命令 exited=0，会被你误判成"没跑完"。

    为什么要分类而不是只用 bool：
      "命令失败"(exit != 0) 与 "被信号杀"(exit >= 128 / < 0) 是两类问题，
      前者要人看内容，后者要人查 OOM/被杀。混在一起会让告警失去指向性。
    """
    rc = r.return_code
    if rc is None:
        return "aborted"                     # 超时/自动应答失败 → 没跑完
    if rc == 0:
        return "ok"
    if rc < 0 or rc >= 128:
        return "killed"                      # 被信号终止（如 137=SIGKILL）
    return "failed"


# ---------------------------------------------------------------------------
# 2. 连接与执行
# ---------------------------------------------------------------------------
def make_connection(spec: HostSpec, user: str, key: str | None,
                    timeout: float = 10.0, known_hosts: str | None = None) -> Connection:
    """构造 Connection（惰性，不产生网络 IO）。

    ⚠ Fabric 的 timeout 只能通过 connect_kwargs 传给 paramiko；
      Connection 自身没有 timeout 参数。
    """
    kwargs: dict = {
        "timeout": timeout,
        "banner_timeout": timeout,
        "auth_timeout": timeout,
        "allow_agent": key is None,
        "look_for_keys": key is None,
    }
    if key:
        kwargs["key_filename"] = os.path.expanduser(key)

    conn = Connection(spec.host, user=user, port=spec.port, connect_kwargs=kwargs)
    return conn


def run_cmd(conn: Connection, command: str, warn: bool = True,
            hide: bool = False, echo: bool = False,
            timeout: float | None = None) -> Result:
    """执行命令。

    默认 warn=True：脚本自己判断 r.ok，而不是让第一个非 0 退出码掀翻整个流程。
    ⚠ 但变更类操作（重启/迁移）不要用 warn=True —— 那会静默吞掉真故障，
      这正是 README 陷阱 2 强调的分工。

    echo=True 会把远端命令本身打到本地输出，方便审计；
    但如果命令里带敏感参数（token/password），echo 会泄到日志里 —— 那时要关掉。
    """
    return conn.run(command, warn=warn, hide=hide, echo=echo, timeout=timeout)


# ---------------------------------------------------------------------------
# 3. 离线自检
# ---------------------------------------------------------------------------
def self_test() -> int:
    ok = True

    print("自检 1：parse_hostspec")
    cases = [
        ("web-01", HostSpec("web-01", None)),
        ("10.0.0.1:2222", HostSpec("10.0.0.1", 2222)),
        ("[::1]", HostSpec("::1", None)),
        ("[::1]:2200", HostSpec("::1", 2200)),
    ]
    for text, want in cases:
        got = parse_hostspec(text)
        flag = "✅" if got == want else "❌"
        ok &= got == want
        print(f"   {flag} {text!r} → {got.label}")
    for bad in ("", ":22", "h:abc", "h:70000"):
        try:
            parse_hostspec(bad)
            print(f"   ❌ {bad!r} 本该报错")
            ok = False
        except ValueError as exc:
            print(f"   ✅ {bad!r} 如期报错: {exc}")

    print("\n自检 2：Result 结构化判断（用 invoke.Result 真对象，不 mock）")
    r_ok = Result(command="true", stdout="fine\n", exited=0)
    r_bad = Result(command="false", stdout="", stderr="boom\n", exited=3)
    r_killed = Result(command="sleep 999", exited=137)
    r_aborted = Result(command="x", exited=None)       # 没跑完：exited 为 None

    checks = [(r_ok, "ok"), (r_bad, "failed"), (r_killed, "killed"), (r_aborted, "aborted")]
    for r, want in checks:
        got = classify(r)
        flag = "✅" if got == want else "❌"
        ok &= got == want
        print(f"   {flag} {r.command!r}(exited={r.exited}) → {got}（期望 {want}）")
        print(f"      describe(): {describe(r)}")
    ok &= (r_ok.ok is True and r_ok.return_code == 0)
    print("   ✅ exited=0 时 ok=True（证明 exited 是退出码而非布尔）")

    print("\n自检 3：tail() 是方法，取指定流的末尾")
    r_many = Result(command="seq", stdout="\n".join(str(i) for i in range(20)) + "\n",
                    stderr="last-err\n", exited=0)
    t = r_many.tail("stdout", 3)
    ok &= "19" in t and "0" not in t.splitlines()[0:1]
    print(f"   ✅ tail('stdout', 3) = {t!r}")
    ok &= "last-err" in r_many.tail("stderr")
    print(f"   ✅ tail('stderr') = {r_many.tail('stderr')!r}")

    print("\n自检 4：Connection 是惰性的（构造不联网）")
    conn = make_connection(parse_hostspec("this-host-does-not-exist.invalid"), "u", None, timeout=1)
    ok &= conn.is_connected is False
    print(f"   ✅ 构造后 is_connected = {conn.is_connected}（未联网）")
    print("   ℹ 真正建连发生在第一次 run/put/get/open")

    print("\nSELF-TEST OK" if ok else "\nSELF-TEST FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# 4. CLI
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Day 169 基础：Fabric Connection 用法")
    ap.add_argument("--host")
    ap.add_argument("--port", type=int)
    ap.add_argument("--user", default=os.environ.get("USER", "root"))
    ap.add_argument("--key")
    ap.add_argument("--cmd", action="append", default=[])
    ap.add_argument("--put", action="append", default=[], help="本地:远端")
    ap.add_argument("--get", action="append", default=[], help="远端:本地")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--echo", action="store_true", help="把远端命令本身打印到本地（审计友好）")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.host:
        ap.error("需要 --host（或 --self-test）")

    spec = parse_hostspec(args.host)
    if args.port:
        spec = HostSpec(spec.host, args.port)

    # ⚠ 用 with 保证收尾（否则 paramiko 后台线程可能让解释器不退出）
    with make_connection(spec, args.user, args.key, args.timeout) as conn:
        try:
            conn.open()          # 主动建连：把"连不上"提前暴露在这里
        except Exception as exc:
            print(f"❌ 连接失败 {spec.label}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

        print(f"🔌 已连接 {args.user}@{spec.label}")
        for cmd in (args.cmd or ["uname -a"]):
            r = run_cmd(conn, cmd, warn=True, echo=args.echo)
            print(f"  {describe(r)}")
            if r.stderr.strip():
                print(f"    stderr: {r.stderr.strip().splitlines()[0][:100]}")

        for spec_s in args.put:
            local, _, remote = spec_s.partition(":")
            conn.put(local, remote)
            print(f"  ✅ put {local} → {remote}")
        for spec_s in args.get:
            remote, _, local = spec_s.partition(":")
            conn.get(remote, local)
            print(f"  ✅ get {remote} → {local}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
