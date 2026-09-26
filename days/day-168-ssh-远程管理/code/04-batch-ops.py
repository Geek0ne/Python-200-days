#!/usr/bin/env python3
"""
Day 168 — SSH 远程管理（paramiko）· 04 实战：批量运维工具
========================================================================

把 01/02/03 的零件拼成一个**能上生产的批量运维工具**：

    输入：inventory 文件（Host 段，兼容 ~/.ssh/config 子集）
    处理：线程池并发 → 每台一个 Transport → 每条命令一个 channel
    输出：控制台表格 + JSONL 审计 + JSON 报告 + 退出码契约

三条设计红线（README 7.2 详述）：
    ① 幂等优先（重复执行结果一致）
    ② 结果可审计（每台/每条命令的起止时间、退出码、输出摘要落盘）
    ③ 退出码表达"部分失败"：0 全成功 / 2 部分失败 / 1 全失败

运行：
    python3 04-batch-ops.py --self-test
    python3 04-batch-ops.py --inventory ./inventory.ini --cmd "uptime" --cmd "df -h /"
    python3 04-batch-ops.py --inventory ./inventory.ini --cmd "df -h /" --workers 8 \
            --limit 2 --out ./reports --timeout 8
    python3 04-batch-ops.py --inventory ./inventory.ini --check     # 只做连通性检查
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import paramiko
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 paramiko，请先 `pip install paramiko`\n")
    sys.exit(3)


# ---------------------------------------------------------------------------
# 1. inventory 解析（~/.ssh/config 的子集）
# ---------------------------------------------------------------------------
@dataclass
class HostEntry:
    alias: str
    hostname: str
    user: str | None = None
    port: int = 22
    identity_file: str | None = None

    def __str__(self) -> str:
        return f"{self.alias}({self.user or '?'}@{self.hostname}:{self.port})"


DEFAULT_KEYS = {"hostname", "user", "port", "identityfile"}


def parse_inventory(text: str) -> list[HostEntry]:
    """解析 `Host <别名>` 段。

    为什么用这个格式：`~/.ssh/config` 是人类最熟悉的写法，
    而且几乎每台运维机器上都已经有一份。支持子集：
        Host web-01
            HostName 10.0.0.11
            User deploy
            Port 22
            IdentityFile ~/.ssh/id_ed25519

    ⚠ paramiko 自己不会读 ssh config（陷阱 1），所以这一步必须自己做。
    """
    entries: list[HostEntry] = []
    cur: dict | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        key = parts[0].lower()
        value = parts[1].strip() if len(parts) > 1 else ""
        if key == "host":
            if cur:
                entries.append(_finish(cur))
            # 一个 Host 行可能给多个别名，这里简化：只取第一个
            cur = {"alias": value.split()[0] if value.split() else "unknown"}
        elif cur is not None and key in DEFAULT_KEYS:
            cur[key] = value
    if cur:
        entries.append(_finish(cur))
    return entries


def _finish(cur: dict) -> HostEntry:
    return HostEntry(
        alias=cur["alias"],
        hostname=cur.get("hostname", cur["alias"]),
        user=cur.get("user"),
        port=int(cur.get("port", 22)),
        identity_file=cur.get("identityfile"),
    )


# ---------------------------------------------------------------------------
# 2. 单机执行
# ---------------------------------------------------------------------------
@dataclass
class HostResult:
    host: str
    status: str = "unknown"          # ok / warn / fail / unreachable
    exit_code: int = 0
    seconds: float = 0.0
    outputs: list[dict] = field(default_factory=list)
    error: str = ""

    def summary(self) -> str:
        if self.status == "unreachable":
            return self.error
        for item in self.outputs:
            if item["status"] != 0:
                first = (item["err"] or item["out"] or "").strip().splitlines()
                return f"{item['command']} → exit {item['status']}: " + (first[0][:60] if first else "")
        for item in self.outputs:
            if item["out"].strip():
                return item["out"].strip().splitlines()[0][:70]
        return "(无输出)"


def run_on_host(entry: HostEntry, commands: list[str], timeout: float,
                known_hosts: str | None, keepalive: int = 30) -> HostResult:
    """连一台机器，按顺序执行全部命令。

    返回而非抛出：批量场景里"某台失败"是正常结果，不是异常。
    异常只应该用在"整批任务无法进行"（例如 inventory 文件读不到）。
    """
    res = HostResult(host=str(entry))
    t0 = time.monotonic()
    client = paramiko.SSHClient()
    try:
        if known_hosts:
            if not os.path.exists(known_hosts):
                raise FileNotFoundError(f"known_hosts 不存在: {known_hosts}")
            client.load_system_host_keys(known_hosts)
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            hostname=entry.hostname, port=entry.port, username=entry.user,
            key_filename=os.path.expanduser(entry.identity_file) if entry.identity_file else None,
            timeout=timeout, banner_timeout=timeout, auth_timeout=timeout,
        )
        client.get_transport().set_keepalive(keepalive)

        for cmd in commands:
            ct0 = time.monotonic()
            _stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
            stdout.channel.settimeout(timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")   # ⚠ 两条流都要读
            code = stdout.channel.recv_exit_status()
            res.outputs.append({
                "command": cmd, "status": code, "out": out, "err": err,
                "seconds": round(time.monotonic() - ct0, 3),
            })
        res.status = "ok" if all(o["status"] == 0 for o in res.outputs) else "warn"
        res.exit_code = max((o["status"] for o in res.outputs), default=0)
    except (socket.timeout, paramiko.SSHException, OSError) as exc:
        res.status = "unreachable" if not res.outputs else "fail"
        res.error = f"{type(exc).__name__}: {exc}"
        res.exit_code = -1
    finally:
        try:
            client.close()
        except Exception:
            pass
        res.seconds = round(time.monotonic() - t0, 3)
    return res


# ---------------------------------------------------------------------------
# 3. 退出码契约 & 汇总
# ---------------------------------------------------------------------------
def decide_exit(results: list[HostResult]) -> int:
    """0 = 全成功；2 = 部分失败/有告警；1 = 全部失败。

    为什么要 2 而不是笼统的 1：上游自动化/CI 需要区分
    "整体挂了（该重试整批）" 和 "有几台有问题（该通知人去看）"。
    """
    if not results:
        return 1
    bad = [r for r in results if r.status != "ok"]
    if not bad:
        return 0
    if len(bad) == len(results):
        return 1
    return 2


def render_table(results: list[HostResult]) -> str:
    widths = (24, 12, 8, 8)
    lines = ["=" * 78,
             f"{'主机':<{widths[0]}}{'状态':<{widths[1]}}{'耗时(s)':<{widths[2]}}"
             f"{'退出码':<{widths[3]}}摘要",
             "-" * 78]
    for r in sorted(results, key=lambda x: x.host):
        lines.append(f"{r.host:<{widths[0]}}{r.status:<{widths[1]}}"
                     f"{r.seconds:<{widths[2]}.2f}{str(r.exit_code):<{widths[3]}}"
                     f"{r.summary()}")
    lines.append("=" * 78)
    ok = sum(1 for r in results if r.status == "ok")
    warn = sum(1 for r in results if r.status == "warn")
    fail = sum(1 for r in results if r.status == "fail")
    unreach = sum(1 for r in results if r.status == "unreachable")
    lines.append(f"汇总：成功 {ok} / 告警 {warn} / 失败 {fail} / 不可达 {unreach} / 总计 {len(results)}"
                 f"        退出码 = {decide_exit(results)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. 离线自检
# ---------------------------------------------------------------------------
SAMPLE = """
# 生产 Web 层
Host web-01
    HostName 10.0.0.11
    User deploy
    Port 22
    IdentityFile ~/.ssh/id_ed25519

Host web-02
    HostName 10.0.0.12
    User deploy

Host db-01
    HostName 10.0.0.21
    User root
    Port 2222
"""


def self_test() -> int:
    ok = True

    print("自检 1：inventory 解析")
    hosts = parse_inventory(SAMPLE)
    ok &= len(hosts) == 3
    print(f"   解析到 {len(hosts)} 台: {[str(h) for h in hosts]}")
    ok &= hosts[0].alias == "web-01" and hosts[0].hostname == "10.0.0.11"
    ok &= hosts[0].user == "deploy" and hosts[0].identity_file.endswith("id_ed25519")
    ok &= hosts[1].port == 22                       # 未写 Port → 默认 22
    ok &= hosts[2].port == 2222 and hosts[2].hostname == "10.0.0.21"
    print(f"   {'✅' if ok else '❌'} 字段解析正确（含默认端口与 IdentityFile 展开前的原样值）")

    print("\n自检 2：退出码契约")
    cases = [
        ([], 1),
        ([HostResult("a", "ok")], 0),
        ([HostResult("a", "ok"), HostResult("b", "warn")], 2),
        ([HostResult("a", "warn"), HostResult("b", "unreachable")], 1),
    ]
    for results, want in cases:
        got = decide_exit(list(results))
        flag = "✅" if got == want else "❌"
        ok &= got == want
        print(f"   {flag} {len(results)} 台 → 退出码 {got}（期望 {want}）")

    print("\n自检 3：结果分类与摘要")
    r = HostResult("web-01", "warn", exit_code=2)
    r.outputs = [{"command": "df -h /", "status": 2, "out": "/dev/sda1 98% full\n", "err": "", "seconds": 0.1}]
    ok &= r.summary().startswith("df -h /")
    print(f"   ✅ 摘要 = {r.summary()!r}")
    r2 = HostResult("db-01", "unreachable", error="socket.timeout: connect timeout (8s)")
    ok &= "timeout" in r2.summary()
    print(f"   ✅ 不可达摘要 = {r2.summary()!r}")

    print("\n自检 4：表格渲染")
    table = render_table([
        HostResult("web-01", "ok", 0, 0.42),
        HostResult("web-02", "unreachable", -1, 8.0, error="timeout"),
        HostResult("db-01", "warn", 2, 0.63),
    ])
    ok &= "退出码 = 2" in table and "不可达 1" in table
    for line in table.splitlines():
        print("   " + line)

    print("\nSELF-TEST OK" if ok else "\nSELF-TEST FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# 5. 主流程
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Day 168 实战：批量运维工具")
    ap.add_argument("--inventory", help="inventory 文件（Host 段格式）")
    ap.add_argument("--cmd", action="append", default=[], help="要执行的命令，可重复")
    ap.add_argument("--check", action="store_true", help="只做连通性检查（执行 true）")
    ap.add_argument("--workers", type=int, default=8, help="并发度，建议 8~16，不要超过 32")
    ap.add_argument("--limit", type=int, default=0, help="只执行前 N 台（灰度）")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--known-hosts", help="受信 known_hosts（生产必传）")
    ap.add_argument("--out", help="报告输出目录")
    ap.add_argument("--json", action="store_true", help="额外输出 JSON 报告到 stdout")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.inventory:
        ap.error("需要 --inventory（或 --self-test）")

    commands = ["true"] if args.check else (args.cmd or ["uptime"])
    hosts = parse_inventory(Path(args.inventory).read_text(encoding="utf-8"))
    if args.limit:
        hosts = hosts[: args.limit]
    if not hosts:
        print("❌ inventory 里没有解析到任何 Host", file=sys.stderr)
        return 1

    workers = max(1, min(args.workers, 64))
    print(f"🚀 目标 {len(hosts)} 台 · 命令 {len(commands)} 条 · 并发 {workers} · 超时 {args.timeout}s")
    if workers > 32:
        print("   ⚠ 并发 > 32 可能触发目标机 sshd MaxStartups 限流，建议降到 8~16")

    # 线程池 + 一机一 Transport（run_on_host 内部完成）
    results: list[HostResult] = []
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ssh") as pool:
        futures = {
            pool.submit(run_on_host, h, commands, args.timeout, args.known_hosts): h
            for h in hosts
        }
        for fut in as_completed(futures):
            entry = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:          # 兜底：任何未预期异常都不能让整批丢结果
                results.append(HostResult(str(entry), "fail", -1, 0.0, error=f"{type(exc).__name__}: {exc}"))
    total = time.monotonic() - t0

    print()
    print(render_table(results))
    print(f"总耗时 {total:.2f}s（并发 {workers}，顺序执行预计约 {sum(r.seconds for r in results):.1f}s）")

    # —— 审计落盘：JSONL 每台一行，便于后续 grep/导入 ——
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        jsonl = out_dir / "batch-audit.jsonl"
        with jsonl.open("a", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                     "commands": commands, **asdict(r)}, ensure_ascii=False) + "\n")
        report = out_dir / "batch-report.json"
        report.write_text(json.dumps({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "commands": commands, "workers": workers, "total_seconds": round(total, 3),
            "exit_code": decide_exit(results),
            "results": [asdict(r) for r in results],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📝 审计: {jsonl}")
        print(f"📄 报告: {report}")

    if args.json:
        print(json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2))

    code = decide_exit(results)
    if code == 0:
        print("✅ 全部成功")
    elif code == 2:
        print("⚠ 部分失败（退出码 2）：请看表格里非 ok 的主机")
    else:
        print("❌ 全部失败（退出码 1）")
    return code


if __name__ == "__main__":
    sys.exit(main())
