#!/usr/bin/env python3
"""
Day 168 — SSH 远程管理（paramiko）· 02 六大陷阱亲手复现
========================================================================

原则：**能离线复现的坑，就不要靠"记住它"**。
本脚本用本地进程/pty/socket 复现 6 个 SSH 自动化里最常见的坑，
每一项都是"先给错误写法，跑给你看后果，再给正确写法"。

    陷阱 1  命令拼接 → 注入（用真实 sh -c 跑出危害，沙箱在临时目录内）
    陷阱 2  只读 stdout 不读 stderr → 双向死锁（真的会挂住）
    陷阱 3  不开 pty 时 sudo 报 "must have a tty"；开了 pty 却丢了 stderr 分离
    陷阱 4  connect 不设 timeout → 连黑洞 IP 时卡住分钟级
    陷阱 5  AutoAddPolicy 等价"谁都信"（用 paramiko 的 HostKeys 直接证明）
    陷阱 6  并发度无上限 → 目标机 MaxStartups 限流，失败率陡升（本地模拟）

运行：
    python3 02-pitfalls.py --self-test        # 只跑"纯逻辑"断言，最快
    python3 02-pitfalls.py                    # 完整复现 6 个陷阱（约 10 秒）
    python3 02-pitfalls.py --only 2           # 只看第 2 个
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

try:
    import paramiko
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 paramiko，请先 `pip install paramiko`\n")
    sys.exit(3)


def banner(n: int, title: str) -> None:
    print("\n" + "=" * 72)
    print(f"陷阱 {n}：{title}")
    print("=" * 72)


# ---------------------------------------------------------------------------
# 陷阱 1：命令拼接 → 注入
# ---------------------------------------------------------------------------
def pitfall_1() -> None:
    banner(1, "命令拼接 = 把远端 shell 的解析权交给用户输入")
    with tempfile.TemporaryDirectory(prefix="d168-inject-") as sandbox:
        # 准备一个"重要文件"，模拟生产目录
        victim = os.path.join(sandbox, "important.txt")
        with open(victim, "w") as fh:
            fh.write("production data\n")

        user_input = f"{sandbox}/x; rm -f {shlex.quote(victim)}"

        # ❌ 错误写法：直接 f-string 拼接
        bad = f"ls {user_input}"
        print(f"   用户输入   : {user_input!r}")
        print(f"   拼接后命令 : {bad}")
        subprocess.run(["/bin/sh", "-c", bad], capture_output=True)
        print(f"   ❌ 执行后 important.txt 还在吗？ {'在' if os.path.exists(victim) else '已被删除！'}")

        # 复原
        with open(victim, "w") as fh:
            fh.write("production data\n")

        # ✅ 正确写法：转义
        good = f"ls {shlex.quote(user_input)}"
        print(f"   转义后命令 : {good}")
        r = subprocess.run(["/bin/sh", "-c", good], capture_output=True, text=True)
        print(f"   ✅ important.txt 还在吗？ {'在' if os.path.exists(victim) else '已被删除！'}")
        print(f"   ✅ ls 的退出码 = {r.returncode}（文件不存在，说明分号失效了）")

        print("\n   原理：exec_command 把字符串交给远端 /bin/sh -c 再解释一次。")
        print("        `shlex.quote` 把危险字符包进单引号 → 变回一个普通参数。")


# ---------------------------------------------------------------------------
# 陷阱 2：只读 stdout，不读 stderr → 双向死锁
# ---------------------------------------------------------------------------
def pitfall_2() -> None:
    banner(2, "只读 stdout 不读 stderr → 远端写满缓冲区 → 双方永久等待")

    code = (
        "import sys\n"
        "for i in range(4000):\n"
        "    sys.stderr.write('E' * 200 + '\\n')\n"
        "sys.stderr.flush()\n"
        "sys.stdout.write('done\\n')\n"
    )

    def run_case(drain_stderr: bool, timeout: float = 4.0) -> str:
        p = subprocess.Popen(
            [sys.executable, "-c", code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result = {"state": "pending"}

        def worker() -> None:
            if drain_stderr:
                # ✅ 同时读两条流（顺序无所谓，关键是不能只读一条）
                th = threading.Thread(target=lambda: p.stderr.read(), daemon=True)
                th.start()
                p.stdout.read()
                th.join(timeout=2)
            else:
                p.stdout.read()        # ❌ 只读 stdout，stderr 攒在管道里
            result["state"] = "finished"

        th = threading.Thread(target=worker, daemon=True)
        th.start()
        th.join(timeout=timeout)
        if th.is_alive():
            p.kill()
            p.wait()
            return "DEADLOCK"
        p.wait()
        return "OK" if p.returncode == 0 else f"rc={p.returncode}"

    print("   ❌ 只读 stdout           →", run_case(drain_stderr=False))
    print("   ✅ 同时读 stdout+stderr  →", run_case(drain_stderr=True))
    print("\n   为什么：管道缓冲区（Linux 默认 64 KiB）写满后，子进程的 write() 阻塞，")
    print("       它在等缓冲区腾空；而你在等 stdout 出现 EOF —— 互相等，永远不动。")


# ---------------------------------------------------------------------------
# 陷阱 3：pty 的代价
# ---------------------------------------------------------------------------
def pitfall_3() -> None:
    banner(3, "pty：既要 tty 又要流分离，是做不到的（本地 pty 演示）")
    # 用 pty 跑一条"同时往 stdout 和 stderr 写"的命令，看 pty 下二者是否合流
    import pty

    def run_with_pty() -> str:
        pid, fd = pty.fork()
        if pid == 0:  # 子进程
            os.execvp("/bin/sh", ["sh", "-c", "echo OUT; echo ERR >&2; exit 0"])
        chunks = []
        while True:
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
        os.waitpid(pid, 0)
        os.close(fd)
        return b"".join(chunks).decode(errors="replace")

    def run_pipes() -> tuple[str, str]:
        r = subprocess.run(["/bin/sh", "-c", "echo OUT; echo ERR >&2"],
                           capture_output=True, text=True)
        return r.stdout, r.stderr

    pty_out = run_with_pty()
    out, err = run_pipes()
    print(f"   ❌ 开 pty 的输出一次性混流: {pty_out!r}")
    print(f"   ✅ 用管道（不开 pty）可分离: stdout={out!r} stderr={err!r}")
    print("\n   结论：需要 tty（sudo/交互命令）时开 pty，代价是 stdout/stderr 合流 + \\r。")
    print("        生产建议：在 sudoers 里设 `Defaults:deploy !requiretty`，保持流纯净。")


# ---------------------------------------------------------------------------
# 陷阱 4：不设 connect timeout
# ---------------------------------------------------------------------------
def pitfall_4() -> None:
    banner(4, "不设 timeout：连一个不回包的地址会卡住很久")
    # 192.0.2.0/24 是 RFC 5737 保留给文档用的 TEST-NET-1，通常被静默丢弃
    # ⚠ 注意：不设 timeout 时 TCP 会按内核的 SYN 重传节奏等上百秒，
    #    所以这里用"后台线程 + 观察窗口"演示，绝不让本脚本自己挂住。
    blackhole = "192.0.2.1"

    def attempt(timeout: float | None, holder: dict) -> None:
        t0 = time.monotonic()
        try:
            socket.create_connection((blackhole, 22), timeout=timeout)
            holder["outcome"] = "意外地连上了（本机把 TEST-NET 路由到了别处）"
        except socket.timeout:
            holder["outcome"] = f"socket.timeout（timeout={timeout}）"
        except OSError as exc:
            holder["outcome"] = f"{type(exc).__name__}: {exc}"
        holder["elapsed"] = time.monotonic() - t0

    for timeout, window in ((None, 3.0), (1.5, 6.0)):
        holder: dict = {}
        th = threading.Thread(target=attempt, args=(timeout, holder), daemon=True)
        th.start()
        th.join(window)
        label = "❌ 不设 timeout" if timeout is None else f"✅ timeout={timeout}s"
        if th.is_alive():
            print(f"   {label} → 已观察 {window:.0f}s，仍在阻塞（TCP 还在重传 SYN）")
        else:
            print(f"   {label} → 实际耗时 {holder['elapsed']:.2f}s，结果：{holder['outcome']}")

    print("\n   结论：paramiko 的 connect(timeout=) 只管 TCP 建连；")
    print("        还必须有 banner_timeout、auth_timeout，以及 channel.settimeout()。")
    print("        三层齐全才算「不会挂死」。")


# ---------------------------------------------------------------------------
# 陷阱 5：AutoAddPolicy 等价于"谁都信"
# ---------------------------------------------------------------------------
def pitfall_5() -> None:
    banner(5, "AutoAddPolicy：把陌生主机密钥照单全收（用假 sshd 实测两种策略）")

    class FakeServer(paramiko.ServerInterface):
        def get_allowed_auths(self, username):
            return "password,publickey"

        def check_auth_password(self, username, password):
            return paramiko.AUTH_SUCCESSFUL

        def check_auth_publickey(self, username, key):
            return paramiko.AUTH_SUCCESSFUL

        def check_channel_request(self, kind, chanid):
            return paramiko.OPEN_SUCCEEDED

    # 服务端主机密钥：就是一把"你从未见过"的指纹
    # ⚠ paramiko 的 Ed25519Key 没有 generate()，用 RSAKey.generate() 即可
    host_key = paramiko.RSAKey.generate(2048)

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(4)
    port = sock.getsockname()[1]
    accepted = {"n": 0}

    def server_loop():
        """假 sshd：最多接受 2 次连接，够演示两种策略。"""
        while accepted["n"] < 2:
            try:
                conn, _ = sock.accept()
                accepted["n"] += 1
                trans = paramiko.Transport(conn)
                trans.add_server_key(host_key)
                trans.start_server(server=FakeServer())
                time.sleep(1.0)
                trans.close()
            except Exception:
                break

    th = threading.Thread(target=server_loop, daemon=True)
    th.start()
    time.sleep(0.2)

    with tempfile.TemporaryDirectory() as tmp:
        kh = os.path.join(tmp, "known_hosts")
        open(kh, "w").close()          # 空白受信清单：没有任何指纹被信任

        def try_connect(mode: str) -> str:
            c = paramiko.SSHClient()
            c.load_system_host_keys(kh)
            if mode == "auto":
                c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                c.set_missing_host_key_policy(paramiko.RejectPolicy())
            try:
                c.connect("127.0.0.1", port=port, username="x", password="x",
                          allow_agent=False, look_for_keys=False,
                          timeout=3, auth_timeout=3, banner_timeout=3)
                return "连上了（凭据已交给这把陌生指纹的主机）"
            except paramiko.SSHException as exc:
                return f"被拒绝：{type(exc).__name__}: {exc}"
            finally:
                c.close()

        print(f"   ❌ AutoAddPolicy → {try_connect('auto')}")
        print(f"   ✅ RejectPolicy   → {try_connect('reject')}")

    sock.close()
    print("\n   结论：生产必须加载受信 known_hosts + RejectPolicy。")
    print("        否则一次 DNS 污染/ARP 欺骗，你的密码与全部操作就交给了攻击者。")
    print(f"   （假 sshd 共被连接 {accepted['n']} 次 → 两次尝试都真的建到了 TCP 层，")
    print("     差别不在网络，而在你是「照单全收」还是「验指纹」。）")


# ---------------------------------------------------------------------------
# 陷阱 6：并发度无上限
# ---------------------------------------------------------------------------
def pitfall_6() -> None:
    banner(6, "并发度无上限：自己把目标机打成不可用（本地模拟 MaxStartups）")
    from concurrent.futures import ThreadPoolExecutor

    # 模拟 sshd 的 MaxStartups 10:30:100 —— 未认证连接超过 10 就随机丢弃
    limit = threading.Semaphore(10)
    rng_state = {"x": 42}

    def rand() -> float:
        # 可复现的伪随机（避免每次输出不同）
        rng_state["x"] = (1103515245 * rng_state["x"] + 12345) % (2 ** 31)
        return rng_state["x"] / 2 ** 31

    def fake_connect(_i: int) -> bool:
        if not limit.acquire(blocking=False):
            return rand() < 0.5          # 超过 MaxStartups 的连接被随机丢弃
        try:
            time.sleep(0.05)
            return True
        finally:
            limit.release()

    for workers in (8, 16, 100):
        t0 = time.monotonic()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(fake_connect, range(200)))
        ok = sum(results)
        print(f"   workers={workers:>3} → 成功 {ok:>3}/200  失败 {200 - ok:>3}  "
              f"耗时 {time.monotonic() - t0:.2f}s")
    print("\n   结论：并发不是越大越好。ingress 侧有 MaxStartups，")
    print("        你只会在日志里看到一堆 Connection reset，然后误判成网络故障。")


# ---------------------------------------------------------------------------
def self_test() -> int:
    """纯逻辑断言：不启动网络/子进程，速度最快。"""
    ok = True
    # shlex.quote 的语义
    assert shlex.quote("a; rm -rf /") == "'a; rm -rf /'"
    assert shlex.quote("plain") == "plain"
    print("   ✅ shlex.quote 语义正确")

    # pty 模块存在（陷阱 3 依赖它）
    import pty as _pty
    assert hasattr(_pty, "fork")
    print("   ✅ pty 模块可用")

    # paramiko 的策略类存在且语义不同
    assert paramiko.AutoAddPolicy is not paramiko.RejectPolicy
    print("   ✅ AutoAddPolicy / RejectPolicy 是不同策略")

    # 线程池并发模拟：确定性可复现
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(lambda x: x * 2, range(4))) == 12
    print("   ✅ 线程池 map 结果正确")

    print("\nSELF-TEST OK" if ok else "\nSELF-TEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 168 避坑：6 个 SSH 自动化陷阱")
    ap.add_argument("--only", type=int, default=0, help="只跑指定编号的陷阱")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    demos = {1: pitfall_1, 2: pitfall_2, 3: pitfall_3, 4: pitfall_4, 5: pitfall_5, 6: pitfall_6}
    targets = [args.only] if args.only else sorted(demos)
    for n in targets:
        demos[n]()

    print("\n" + "=" * 72)
    print("六个陷阱回顾")
    print("=" * 72)
    print("   ✅ 陷阱 1：命令拼接注入 → shlex.quote / 白名单")
    print("   ✅ 陷阱 2：只读 stdout → 双向死锁 → 两条流都要 drain")
    print("   ✅ 陷阱 3：pty 的代价 → 需要 tty 才开，否则保持流分离")
    print("   ✅ 陷阱 4：不设 timeout → 三层超时缺一不可")
    print("   ✅ 陷阱 5：AutoAddPolicy → 受信 known_hosts + RejectPolicy")
    print("   ✅ 陷阱 6：并发无上限 → workers 默认 8~16，别超 32")
    return 0


if __name__ == "__main__":
    sys.exit(main())
