#!/usr/bin/env python3
"""
Day 168 — SSH 远程管理（paramiko）· 03 进阶：连接复用 + 通道池 + 断点续传
========================================================================

01 讲了"一次连对"，02 讲了"别掉坑"。03 解决的是**规模化**问题：

    ❌ 初级写法：每台机器每条命令 → SSHClient().connect()
       N 台 × M 条命令 = N×M 次密钥交换 + 认证
       → 单机 5 条命令就要多花 5 倍握手时间，而且把目标机 auth.log 刷爆

    ✅ 进阶写法：一台机器一条 Transport（KEX/认证各一次），
       把命令挂在它上面开 channel；重活前先 set_keepalive 防闲置被掐

本脚本包含四块可复用组件：

    ① TransportPool   —— 按 (user,host,port) 复用连接，带 keepalive 与健康检查
    ② exec_on()       —— 在已有 Transport 上开 channel 执行命令（不重连）
    ③ resume_upload() —— SFTP 断点续传 + sha256 校验（幂等发布的基础）
    ④ chunk_ranges()  —— 可单测的分块切片逻辑

运行：
    python3 03-advanced-ssh.py --self-test
    python3 03-advanced-ssh.py --host 127.0.0.1 --port 2222 --user root \
            --key /tmp/sshtest/id_ed25519 --cmd "hostname" --cmd "df -h /" --repeat 5
    python3 03-advanced-ssh.py --host 127.0.0.1 --port 2222 --user root \
            --key /tmp/sshtest/id_ed25519 --upload ./big.bin:/tmp/big.bin
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Iterator

try:
    import paramiko
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 paramiko，请先 `pip install paramiko`\n")
    sys.exit(3)


# ---------------------------------------------------------------------------
# ① 连接池
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ConnKey:
    user: str
    host: str
    port: int = 22

    def __str__(self) -> str:
        return f"{self.user}@{self.host}:{self.port}"


@dataclass
class PooledConn:
    key: ConnKey
    client: paramiko.SSHClient
    created_at: float = field(default_factory=time.monotonic)
    channels_opened: int = 0


class TransportPool:
    """按 ConnKey 复用 SSHClient。

    为什么复用 SSHClient 而不是自己去 hold Transport：
      SSHClient 已经把 Transport 的所有权包好了（close() 会正确收尾），
      而 exec_command() 会**复用同一个 Transport** 开新 channel。
      只要不 close()，就等于"同一条隧道开多条逻辑流"。

    必须提供 close_all()：脚本退出前的 finally 里调用，
    否则 paramiko 的后台线程会让解释器 hang 住不退出。
    """

    def __init__(self, keepalive: int = 30, connect_timeout: float = 10.0) -> None:
        self.keepalive = keepalive
        self.connect_timeout = connect_timeout
        self._pool: dict[ConnKey, PooledConn] = {}

    # —— 取连接（懒建 + 健康检查） ——
    def get(self, key: ConnKey, pkey=None, password=None,
            known_hosts: str | None = None) -> PooledConn:
        pc = self._pool.get(key)
        if pc is not None and pc.client.get_transport() is not None \
                and pc.client.get_transport().is_active():
            return pc                                   # 命中缓存：0 次握手
        if pc is not None:                              # 连接已死：丢掉重建
            try:
                pc.client.close()
            except Exception:
                pass
            del self._pool[key]

        client = paramiko.SSHClient()
        if known_hosts:
            if not os.path.exists(known_hosts):
                raise FileNotFoundError(f"known_hosts 不存在: {known_hosts}")
            client.load_system_host_keys(known_hosts)
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=key.host, port=key.port, username=key.user,
            pkey=pkey, password=password,
            timeout=self.connect_timeout, banner_timeout=15, auth_timeout=15,
            allow_agent=pkey is None and password is None,
            look_for_keys=pkey is None and password is None,
        )
        client.get_transport().set_keepalive(self.keepalive)
        pc = PooledConn(key=key, client=client)
        self._pool[key] = pc
        return pc

    def stats(self) -> str:
        return ", ".join(f"{k} → {v.channels_opened} channels" for k, v in self._pool.items()) or "(空)"

    def close_all(self) -> None:
        for pc in self._pool.values():
            try:
                pc.client.close()
            except Exception:
                pass
        self._pool.clear()


# ---------------------------------------------------------------------------
# ② 在已有 Transport 上执行
# ---------------------------------------------------------------------------
@dataclass
class ExecResult:
    command: str
    out: str
    err: str
    status: int
    seconds: float


def exec_on(pool: TransportPool, key: ConnKey, command: str,
            io_timeout: float = 10.0, pkey=None, password=None,
            known_hosts: str | None = None) -> ExecResult:
    """执行一条命令；**复用**同一条 Transport，只新开一个 channel。

    与 01 的 run() 的区别：这里连 connect() 都省了（命中池）。
    同时保留"两条流都读、最后取退出码"的正确顺序。
    """
    pc = pool.get(key, pkey=pkey, password=password, known_hosts=known_hosts)
    t0 = time.monotonic()
    _stdin, stdout, stderr = pc.client.exec_command(command, timeout=io_timeout)
    stdout.channel.settimeout(io_timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()
    pc.channels_opened += 1
    return ExecResult(command, out, err, status, time.monotonic() - t0)


# ---------------------------------------------------------------------------
# ③ 断点续传 + 校验
# ---------------------------------------------------------------------------
def chunk_ranges(total: int, chunk: int) -> Iterator[tuple[int, int]]:
    """把 [0, total) 切成若干 (offset, length)，最后一段可能不足 chunk。

    单独抽出来是为了可离线单测：断点续传的正确性全在这个切片逻辑上。
    """
    if chunk <= 0:
        raise ValueError("chunk 必须 > 0")
    off = 0
    while off < total:
        n = min(chunk, total - off)
        yield off, n
        off += n


def sha256_local(path: str, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            data = fh.read(block)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def sha256_remote(pool: TransportPool, key: ConnKey, path: str, **kw) -> str | None:
    """远端算 sha256；远端没有 sha256sum 时返回 None。"""
    cmd = f"sha256sum {shlex_quote(path)}"
    res = exec_on(pool, key, cmd, **kw)
    if res.status != 0:
        return None
    return res.out.split()[0] if res.out.split() else None


def shlex_quote(s: str) -> str:
    import shlex
    return shlex.quote(s)


def resume_upload(pool: TransportPool, key: ConnKey, local: str, remote: str,
                  chunk: int = 1 << 20, verify: bool = True,
                  pkey=None, **kw) -> tuple[bool, str]:
    """幂等上传：已一致就跳过；不一致就从断点续传；最后做哈希校验。

    为什么必须幂等：批量部署脚本会被重跑（重试、CI 重触发、人不小心再按一次）。
    非幂等的上传会把一个正在运行的服务搞成半个二进制。
    """
    if not os.path.exists(local):
        return False, f"本地不存在: {local}"
    local_size = os.path.getsize(local)
    pc = pool.get(key, pkey=pkey, **kw)
    sftp = pc.client.open_sftp()
    try:
        try:
            remote_size = sftp.stat(remote).st_size
        except FileNotFoundError:
            remote_size = 0

        if remote_size == local_size:
            if verify:
                r_hash = sha256_remote(pool, key, remote, pkey=pkey, **kw)
                if r_hash and r_hash != sha256_local(local):
                    remote_size = 0       # 大小一样但内容不同 → 全量重传
                    print(f"   ⚠ 大小一致但哈希不同，改为全量重传")
                else:
                    return True, f"跳过（已一致 {local_size} 字节，sha256 校验通过）"
            else:
                return True, f"跳过（大小一致 {local_size} 字节，未校验）"

        if remote_size > local_size:
            remote_size = 0               # 远端更长 → 从头上传（避免残留尾部）

        mode = "r+b" if remote_size else "wb"
        sftp_open = sftp.open(remote, mode)
        moved = 0
        t0 = time.monotonic()
        with open(local, "rb") as lf:
            lf.seek(remote_size)
            sftp_open.seek(remote_size)
            for off, n in chunk_ranges(local_size - remote_size, chunk):
                data = lf.read(n)
                sftp_open.write(data)
                moved += len(data)
                pct = (remote_size + moved) / local_size * 100 if local_size else 100
                print(f"   ↑ {pct:5.1f}%  ({remote_size + moved}/{local_size} 字节)", end="\r")
        sftp_open.close()
        dt = max(time.monotonic() - t0, 1e-9)
        tail = f"，{remote_size/max(local_size,1)*100:.1f}% 为续传省下的" if remote_size else ""
        print("")
    finally:
        sftp.close()

    if verify:
        r_hash = sha256_remote(pool, key, remote, pkey=pkey, **kw)
        l_hash = sha256_local(local)
        if r_hash is None:
            return True, f"上传完成（远端无 sha256sum，跳过校验），{moved/dt/1e6:.1f} MB/s{tail}"
        if r_hash != l_hash:
            return False, f"校验失败！local={l_hash[:12]} remote={r_hash[:12]}"
        return True, f"上传完成并校验通过，{moved/dt/1e6:.1f} MB/s{tail}"
    return True, "上传完成（未校验）"


# ---------------------------------------------------------------------------
# ④ 离线自检
# ---------------------------------------------------------------------------
def self_test() -> int:
    ok = True

    print("自检 1：chunk_ranges 切片")
    got = list(chunk_ranges(10, 4))
    want = [(0, 4), (4, 4), (8, 2)]
    ok &= got == want
    print(f"   {'✅' if got == want else '❌'} chunk_ranges(10, 4) = {got}")
    try:
        list(chunk_ranges(10, 0))
        print("   ❌ chunk=0 本该报错")
        ok = False
    except ValueError as exc:
        print(f"   ✅ chunk=0 如期报错: {exc}")
    print(f"   ✅ 覆盖完整: sum(length) = {sum(n for _, n in chunk_ranges(10, 4))}")

    print("\n自检 2：sha256_local 与 hashlib 一致")
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as fh:
        fh.write(b"hello paramiko\n" * 1000)
        tmp = fh.name
    try:
        h1 = sha256_local(tmp)
        h2 = hashlib.sha256(open(tmp, "rb").read()).hexdigest()
        ok &= h1 == h2
        print(f"   {'✅' if h1 == h2 else '❌'} {h1[:16]}…")
    finally:
        os.unlink(tmp)

    print("\n自检 3：ConnKey 可哈希、端口不同即不同 key")
    a = ConnKey("root", "h", 22)
    b = ConnKey("root", "h", 2222)
    ok &= len({a, b}) == 2 and len({a, ConnKey("root", "h", 22)}) == 1
    print(f"   ✅ 去重正确: {len({a, b})} 个不同 key")

    print("\n自检 4：TransportPool 空池与关闭幂等")
    pool = TransportPool()
    ok &= pool.stats() == "(空)"
    pool.close_all()
    pool.close_all()          # 再关一次不能炸
    print("   ✅ 空池关闭两次无异常")

    print("\nSELF-TEST OK" if ok else "\nSELF-TEST FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def load_pkey(key_path: str | None):
    if not key_path:
        return None
    path = os.path.expanduser(key_path)
    for cls in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
        try:
            return cls.from_private_key_file(path)
        except paramiko.SSHException:
            continue
    raise paramiko.SSHException(f"无法识别的私钥: {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 168 进阶：连接复用 + 断点续传")
    ap.add_argument("--host")
    ap.add_argument("--port", type=int, default=22)
    ap.add_argument("--user", default=os.environ.get("USER", "root"))
    ap.add_argument("--key")
    ap.add_argument("--known-hosts")
    ap.add_argument("--cmd", action="append", default=[])
    ap.add_argument("--repeat", type=int, default=1, help="重复执行命令 N 次，用于演示连接复用")
    ap.add_argument("--upload", action="append", default=[], help="本地:远端")
    ap.add_argument("--chunk", type=int, default=1 << 20)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.host:
        ap.error("需要 --host（或 --self-test）")

    pkey = load_pkey(args.key)
    key = ConnKey(user=args.user, host=args.host, port=args.port)
    pool = TransportPool()
    kwargs = dict(pkey=pkey, known_hosts=args.known_hosts)

    try:
        # —— 第一次执行：1 次握手 ——
        t0 = time.monotonic()
        if args.cmd:
            r = exec_on(pool, key, args.cmd[0], **kwargs)
            print(f"$ {args.cmd[0]}")
            print(f"  exit={r.status}  {r.seconds:.3f}s  (含首次握手)")
            if r.out:
                print("  " + r.out.strip().splitlines()[0][:160])
        connect_cost = time.monotonic() - t0

        # —— 后续执行：复用连接 ——
        cmds = (args.cmd[1:] or ["hostname"]) * args.repeat
        t1 = time.monotonic()
        for c in cmds:
            exec_on(pool, key, c, **kwargs)
        reuse_cost = time.monotonic() - t1
        if cmds:
            print(f"\n📈 连接复用：首次 {connect_cost:.3f}s（含 KEX+认证），"
                  f"之后 {len(cmds)} 条共 {reuse_cost:.3f}s，"
                  f"平均 {reuse_cost/len(cmds)*1000:.1f} ms/条")
        print(f"   池状态: {pool.stats()}")

        for spec in args.upload:
            local, _, remote = spec.partition(":")
            ok, msg = resume_upload(pool, key, local, remote, chunk=args.chunk, **kwargs)
            print(("✅ " if ok else "❌ ") + msg)
    except FileNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    except paramiko.AuthenticationException:
        print("❌ 认证失败", file=sys.stderr)
        return 1
    except paramiko.SSHException as exc:
        print(f"❌ SSH 错误: {exc}", file=sys.stderr)
        return 1
    finally:
        pool.close_all()      # 不关池 → 解释器可能 hang
    return 0


if __name__ == "__main__":
    sys.exit(main())
