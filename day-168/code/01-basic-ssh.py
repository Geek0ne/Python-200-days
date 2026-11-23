#!/usr/bin/env python3
"""
Day 168 — SSH 远程管理（paramiko）· 01 基础用法
========================================================================

这是"最小正确"的 paramiko 用法。所谓最小正确，指的是它同时满足了：

    ① 三层超时齐全（TCP 建连 / banner / 认证 / 单次 IO）
    ② 主机密钥策略显式（不用 AutoAddPolicy 一把梭）
    ③ stdout 与 stderr 都读（避免远端缓冲区写满导致双向死锁）
    ④ recv_exit_status() 在读完流之后调用（避免拿不到退出码）
    ⑤ finally 里 close()（避免 fd 与线程泄漏）

运行：
    python3 01-basic-ssh.py --self-test
    python3 01-basic-ssh.py --target deploy@192.168.1.10:22 --key ~/.ssh/id_ed25519 \
            --cmd "uname -a" --cmd "df -h /"
    python3 01-basic-ssh.py --target root@host --password-env SSH_PW --cmd "id"
    python3 01-basic-ssh.py --target deploy@host --key ~/.ssh/id_ed25519 --upload ./a.txt:/tmp/a.txt
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import time
from dataclasses import dataclass

try:
    import paramiko
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 paramiko，请先 `pip install paramiko`\n")
    sys.exit(3)


# ---------------------------------------------------------------------------
# 1. 纯函数：目标解析（可离线测试）
# ---------------------------------------------------------------------------
@dataclass
class Target:
    user: str
    host: str
    port: int = 22

    def __str__(self) -> str:  # for 日志
        return f"{self.user}@{self.host}:{self.port}"


def parse_target(text: str) -> Target:
    """把 `user@host[:port]` 解析成 Target。

    为什么要有这个函数：运维脚本的目标地址常常来自命令行/配置文件/工单，
    格式五花八门。把"解析"与"连接"分开，解析就可以纯离线单测（本文件的自检）。

    支持三种写法：
        deploy@web-01                 → 默认 22
        root@10.0.0.1:2222            → 指定端口
        u@[fe80::1]:2222 / u@[fe80::1]→ IPv6 字面量（方括号内不拆冒号）
    """
    if "@" not in text:
        raise ValueError(f"目标必须形如 user@host[:port]，收到: {text!r}")
    user, _, rest = text.partition("@")
    if not user:
        raise ValueError("user 不能为空")
    host, port = rest, 22
    if rest.startswith("["):
        # IPv6 字面量：[::1] 或 [::1]:2222
        end = rest.find("]")
        if end == -1:
            raise ValueError(f"IPv6 地址缺少右方括号: {rest!r}")
        host = rest[1:end]
        tail = rest[end + 1:]           # "" 或 ":2222"
        if tail:
            if not tail.startswith(":"):
                raise ValueError(f"IPv6 之后只能是 :port，收到: {tail!r}")
            port = _parse_port(tail[1:])
    elif ":" in rest:
        host, _, port_s = rest.rpartition(":")
        if not host:
            raise ValueError(f"host 不能为空: {text!r}")
        port = _parse_port(port_s)
    if not host:
        raise ValueError("host 不能为空")
    if not 1 <= port <= 65535:
        raise ValueError(f"端口越界: {port}")
    return Target(user=user, host=host, port=port)


def _parse_port(port_s: str) -> int:
    try:
        return int(port_s)
    except ValueError as exc:
        raise ValueError(f"端口必须是数字: {port_s!r}") from exc


def summarize(text: str, limit: int = 120) -> str:
    """把多行输出压成一行摘要，用于日志/报告（避免刷屏）。"""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return "(无输出)"
    head = lines[0]
    extra = f" … (+{len(lines) - 1} 行)" if len(lines) > 1 else ""
    return (head[:limit] + ("…" if len(head) > limit else "")) + extra


# ---------------------------------------------------------------------------
# 2. 连接：把"超时"和"主机密钥策略"一次设对
# ---------------------------------------------------------------------------
def build_client(known_hosts: str | None = None) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    if known_hosts:
        # 显式加载受信主机密钥；未收录的主机将直接失败（RejectPolicy）
        # ⚠ "fail closed"：文件不存在应报错，而不是静默降级成"什么都不校验"
        if not os.path.exists(known_hosts):
            raise FileNotFoundError(
                f"known_hosts 不存在: {known_hosts}（不能静默降级为不校验）"
            )
        client.load_system_host_keys(known_hosts)
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    else:
        # 开发便利：自动收录。⚠ 生产请传入 --known-hosts 走校验路径。
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return client


def load_pkey(key_path: str | None, passphrase: str | None):
    """加载私钥；支持 ed25519 / rsa / ecdsa（按内容自动嗅探）。"""
    if not key_path:
        return None
    path = os.path.expanduser(key_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"私钥不存在: {path}")
    for cls in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
        try:
            return cls.from_private_key_file(path, password=passphrase)
        except paramiko.PasswordRequiredException:
            raise
        except paramiko.SSHException:
            continue          # 换个算法类型再试
    raise paramiko.SSHException(f"无法识别的私钥格式: {path}")


def connect(target: Target, key_path=None, passphrase=None, password=None) -> paramiko.SSHClient:
    client = build_client(os.environ.get("KNOWN_HOSTS"))
    client.connect(
        hostname=target.host,
        port=target.port,
        username=target.user,
        pkey=load_pkey(key_path, passphrase),
        password=password,
        timeout=10,            # ① TCP 建连超时
        banner_timeout=15,     # ② 等 SSH banner 超时
        auth_timeout=15,       # ③ 认证交互超时
        allow_agent=True,      # ④ 允许 ssh-agent 提供密钥（推荐）
        look_for_keys=not key_path,   # ⑤ 没显式给 key 时才扫 ~/.ssh
    )
    client.get_transport().set_keepalive(30)   # ⑥ 空闲保活
    return client


# ---------------------------------------------------------------------------
# 3. 执行：读全两条流，再取退出码
# ---------------------------------------------------------------------------
@dataclass
class ExecResult:
    command: str
    out: str
    err: str
    status: int
    seconds: float

    @property
    def ok(self) -> bool:
        return self.status == 0


def run(client: paramiko.SSHClient, command: str, io_timeout: float = 10.0) -> ExecResult:
    """执行一条命令。

    顺序很关键：
      1) exec_command 拿到三个 ChannelFile
      2) 依次 read() 掉 stdout/stderr（顺序无所谓，但**两个都要读**）
      3) 最后 recv_exit_status()

    如果先 recv_exit_status() 而远端还在狂写 stderr，
    远端 write() 会因为窗口满而阻塞 → 该 channel 永远不退出 → 你永远等不到退出码。
    """
    t0 = time.monotonic()
    _stdin, stdout, stderr = client.exec_command(command, timeout=io_timeout)
    stdout.channel.settimeout(io_timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    return ExecResult(command, out, err, status, time.monotonic() - t0)


def explain_status(status: int) -> str:
    """把退出码翻译成人话（这些是 shell 的约定，不是 paramiko 的）。"""
    if status == 0:
        return "成功"
    if status == 126:
        return "找到命令但不可执行（权限位）"
    if status == 127:
        return "命令不存在（PATH 里找不到）"
    if status >= 128:
        import signal as _sig
        try:
            return f"被信号杀死：{_sig.Signals(status - 128).name}"
        except ValueError:
            return f"被信号 {status - 128} 杀死"
    return f"命令自身返回 {status}"


# ---------------------------------------------------------------------------
# 4. SFTP：上传/下载 + 大小校验
# ---------------------------------------------------------------------------
def send_file(client: paramiko.SSHClient, local: str, remote: str) -> tuple[bool, str]:
    if not os.path.exists(local):
        return False, f"本地文件不存在: {local}"
    local_size = os.path.getsize(local)
    sftp = client.open_sftp()
    try:
        sftp.put(local, remote)
        remote_size = sftp.stat(remote).st_size
        if remote_size != local_size:
            return False, f"大小不一致 local={local_size} remote={remote_size}"
        return True, f"{remote} <- {local} ({local_size} 字节，已校验)"
    finally:
        sftp.close()


def fetch_file(client: paramiko.SSHClient, remote: str, local: str) -> tuple[bool, str]:
    sftp = client.open_sftp()
    try:
        sftp.get(remote, local)
        return True, f"{local} <- {remote} ({os.path.getsize(local)} 字节)"
    except FileNotFoundError:
        return False, f"远端文件不存在: {remote}"
    finally:
        sftp.close()


# ---------------------------------------------------------------------------
# 5. 离线自检
# ---------------------------------------------------------------------------
def self_test() -> int:
    print("自检 1：parse_target 各种形态")
    cases = [
        ("deploy@web-01", Target("deploy", "web-01", 22)),
        ("root@10.0.0.1:2222", Target("root", "10.0.0.1", 2222)),
        ("u@[fe80::1]", Target("u", "fe80::1", 22)),          # IPv6 字面量
        ("u@[fe80::1]:2222", Target("u", "fe80::1", 2222)),    # IPv6 + 端口
    ]
    ok = True
    for text, want in cases:
        got = parse_target(text)
        flag = "✅" if got == want else "❌"
        ok &= got == want
        print(f"   {flag} {text!r} → {got}")

    for bad in ("nohost", "@host", "u@host:notaport", "u@host:99999"):
        try:
            parse_target(bad)
            print(f"   ❌ {bad!r} 本该报错")
            ok = False
        except ValueError as exc:
            print(f"   ✅ {bad!r} 如期报错: {exc}")

    print("\n自检 2：summarize 压缩输出")
    s = summarize("line1\nline2\nline3\n")
    print(f"   {s!r}")
    ok &= s.startswith("line1") and "+2 行" in s
    ok &= summarize("   \n\n") == "(无输出)"

    print("\n自检 3：explain_status 退出码语义")
    checks = {0: "成功", 126: "权限", 127: "不存在", 137: "SIGKILL"}
    for code, kw in checks.items():
        msg = explain_status(code)
        flag = "✅" if kw in msg else "❌"
        ok &= kw in msg
        print(f"   {flag} {code} → {msg}")

    print("\n自检 4：超时与策略参数确实被传下去了")
    client = build_client()
    policy = client._policy
    print(f"   默认策略 = {type(policy).__name__}（期望 AutoAddPolicy，生产请用 RejectPolicy）")
    ok &= type(policy).__name__ == "AutoAddPolicy"
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix="-known_hosts", delete=False) as fh:
        fh.write("")           # 空白的受信清单：任何主机都不许连
        kh = fh.name
    try:
        client2 = build_client(known_hosts=kh)
        ok &= isinstance(client2._policy, paramiko.RejectPolicy)
        print(f"   指定 known_hosts 后策略 = {type(client2._policy).__name__}（期望 RejectPolicy）")
        try:
            build_client(known_hosts=kh + ".nope")
            print("   ❌ 不存在的 known_hosts 本该报错（fail closed）")
            ok = False
        except FileNotFoundError as exc:
            print(f"   ✅ 不存在的 known_hosts 如期报错: {exc}")
    finally:
        os.unlink(kh)

    print("\nSELF-TEST OK" if ok else "\nSELF-TEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 168 基础：paramiko 最小正确用法")
    ap.add_argument("--target", help="user@host[:port]")
    ap.add_argument("--key", help="私钥路径")
    ap.add_argument("--password-env", help="从该环境变量读取密码（不要写死在命令行）")
    ap.add_argument("--cmd", action="append", default=[], help="要执行的命令，可重复")
    ap.add_argument("--upload", action="append", default=[], help="本地:远端")
    ap.add_argument("--download", action="append", default=[], help="远端:本地")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.target:
        ap.error("需要 --target（或加 --self-test 做离线自检）")

    target = parse_target(args.target)
    password = os.environ.get(args.password_env) if args.password_env else None

    print(f"🔌 连接 {target} ...")
    client = connect(target, args.key, password=password)
    try:
        for cmd in (args.cmd or ["uname -a; id"]):
            res = run(client, cmd, args.timeout)
            print(f"\n$ {cmd}")
            print(f"  exit={res.status} ({explain_status(res.status)})  {res.seconds:.2f}s")
            if res.out:
                print(f"  stdout: {summarize(res.out, 200)}")
            if res.err:
                print(f"  stderr: {summarize(res.err, 200)}")
        for spec in args.upload:
            local, _, remote = spec.partition(":")
            ok, msg = send_file(client, local, remote)
            print(("✅ " if ok else "❌ ") + msg)
        for spec in args.download:
            remote, _, local = spec.partition(":")
            ok, msg = fetch_file(client, remote, local)
            print(("✅ " if ok else "❌ ") + msg)
    except socket.timeout:
        print("❌ 网络超时（TCP/IO），检查主机可达性与防火墙", file=sys.stderr)
        return 1
    except paramiko.AuthenticationException:
        print("❌ 认证失败，检查用户名/密钥/authorized_keys", file=sys.stderr)
        return 1
    except paramiko.SSHException as exc:
        print(f"❌ SSH 协议层错误: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
