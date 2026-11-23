#!/usr/bin/env python3
"""
Day 169 — Fabric 批量执行 · 04 实战：可回滚的批量部署工具
========================================================================

把 01/02/03 的零件拼成一份**能上生产的部署脚本**。核心不是"能传文件"，
而是"出错时能安全退回去"：

    ① release 目录         releases/<rev>/  —— 新版本先落地，不影响线上
    ② 原子软链             ln -sfn current → releases/<rev>（rename 语义，无中间态）
    ③ shared 外置          .env / logs 不进 release，用软链共享
    ④ 三级健康检查          进程 → 端口 → 业务（curl /healthz）
    ⑤ 失败自动回滚          切回上一版 release + 重启 + 非 0 退出
    ⑥ 保留 N 版             清理旧 release，但永远留着上一个"好"版本
    ⑦ 串行滚动             一台一台来，失败立刻停并报告停点

⚠ 本脚本默认 **--dry-run**：先打印将要执行的每一步，不真动手。
   生产习惯：先 dry-run 看一遍，再 `--apply`。

运行：
    python3 04-deploy-tool.py --self-test
    python3 04-deploy-tool.py --hosts 127.0.0.1:2222 --user root \
            --key /tmp/sshtest/id_ed25519 --artifact ./app.tar.gz \
            --release 20260927 --root /opt/app            # dry-run（默认）
    python3 04-deploy-tool.py ... --apply                     # 真执行
    python3 04-deploy-tool.py ... --apply --rollback-only     # 只回滚到上一版
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import shlex
import sys
import time
from dataclasses import dataclass, field

try:
    from fabric import Connection
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 fabric，请先 `pip install fabric`\n")
    sys.exit(3)


# ---------------------------------------------------------------------------
# 1. 纯逻辑：部署计划（可离线单测）
# ---------------------------------------------------------------------------
REV_RE = re.compile(r"^[0-9A-Za-z._-]{1,64}$")


@dataclass
class DeployPlan:
    """一次部署的全部路径与命令。把"规划"与"执行"分开，规划就能离线单测。

    restart_cmd / health_cmd 做成模板是因为现实里有多种服务管理器：
        systemctl restart {service}      （systemd）
        supervisorctl restart {service}  （supervisor）
        docker restart {service}         （容器）
    保持可覆盖，同一套部署逻辑才能适配不同环境。
    """

    root: str
    release: str
    artifact_remote: str
    health_path: str = "/healthz"
    keep: int = 3
    service: str = "app"
    restart_cmd: str = "systemctl restart {service}"
    health_cmd: str = "curl -fsS -m 5 http://127.0.0.1{health_path} >/dev/null"

    def __post_init__(self) -> None:
        if not REV_RE.match(self.release):
            # ⚠ 版本号会进 shell 命令 → 必须白名单校验（Day 168 陷阱 1 的教训）
            raise ValueError(f"release 只能是 [0-9A-Za-z._-]{{1,64}}，收到 {self.release!r}")
        if not self.root.startswith("/"):
            raise ValueError(f"root 必须是绝对路径: {self.root!r}")

    def _restart(self) -> str:
        return self.restart_cmd.format(service=shlex.quote(self.service))

    def _health(self) -> str:
        return self.health_cmd.format(health_path=self.health_path)

    @property
    def releases_dir(self) -> str:
        return posixpath.join(self.root, "releases")

    @property
    def new_dir(self) -> str:
        return posixpath.join(self.releases_dir, self.release)

    @property
    def current_link(self) -> str:
        return posixpath.join(self.root, "current")

    @property
    def shared_dir(self) -> str:
        return posixpath.join(self.root, "shared")

    def steps(self) -> list[tuple[str, str]]:
        """返回 (描述, shell 命令) 的有序列表。dry-run 与真执行共用同一份。"""
        r, n, cur, sh = self.root, self.new_dir, self.current_link, self.shared_dir
        return [
            ("准备目录结构", f"mkdir -p {shlex.quote(self.releases_dir)} {shlex.quote(sh)}/logs"),
            ("记录上一版（用于回滚）",
             f"readlink -f {shlex.quote(cur)} 2>/dev/null || true"),
            ("创建新 release 目录", f"mkdir -p {shlex.quote(n)}"),
            ("解包 artifact",
             f"tar -xzf {shlex.quote(self.artifact_remote)} -C {shlex.quote(n)}"),
            ("挂 shared 配置",
             f"ln -sfn {shlex.quote(sh)}/.env {shlex.quote(n)}/.env 2>/dev/null || true"),
            ("挂 shared 日志",
             f"ln -sfn {shlex.quote(sh)}/logs {shlex.quote(n)}/logs 2>/dev/null || true"),
            ("写部署标记", f"date -Iseconds > {shlex.quote(n)}/.deployed-at"),
            ("原子切换 current",
             f"ln -sfn {shlex.quote(n)} {shlex.quote(cur)}"),
            ("重启服务", self._restart()),
            ("健康检查（业务级）", self._health()),
            ("清理旧 release（保留最近 %d 版）" % (self.keep + 1),
             f"ls -1dt {shlex.quote(self.releases_dir)}/*/ 2>/dev/null | tail -n +{self.keep + 2} "
             f"| xargs -r rm -rf"),
        ]

    def rollback_steps(self, prev_release: str) -> list[tuple[str, str]]:
        """回滚：把 current 指回上一版 + 重启 + 健康检查。"""
        if not prev_release:
            return [("回滚", "echo '无上一版可回滚（未记录到 previous）'; exit 1")]
        prev = prev_release if prev_release.startswith("/") else posixpath.join(self.releases_dir, prev_release)
        if not prev.startswith(self.releases_dir + "/"):
            # 防御：previous 必须是 releases 下的目录，避免被诱导到任意路径
            return [("回滚", f"echo '拒绝回滚到非 release 路径: {prev}'; exit 1")]
        return [
            ("回滚 current", f"ln -sfn {shlex.quote(prev)} {shlex.quote(self.current_link)}"),
            ("回滚重启", self._restart()),
            ("回滚健康检查", self._health()),
        ]


def parse_prev_release(readlink_output: str) -> str:
    """从 `readlink -f current` 的输出解析出"上一版"目录名。

    返回空串表示没有上一版（首次部署）。只取 basename，避免把绝对路径
    带进后续命令（虽然 rollback_steps 也做了防御）。
    """
    line = readlink_output.strip().splitlines()[-1] if readlink_output.strip() else ""
    if not line or line in ("", "/"):
        return ""
    return posixpath.basename(line.rstrip("/"))


# ---------------------------------------------------------------------------
# 2. 离线自检
# ---------------------------------------------------------------------------
def self_test() -> int:
    ok = True

    print("自检 1：DeployPlan 路径推导")
    p = DeployPlan(root="/opt/app", release="20260927-0600", artifact_remote="/tmp/app.tar.gz")
    ok &= p.releases_dir == "/opt/app/releases"
    ok &= p.new_dir == "/opt/app/releases/20260927-0600"
    ok &= p.current_link == "/opt/app/current"
    print(f"   ✅ new_dir={p.new_dir}  current={p.current_link}")

    print("\n自检 2：release 白名单（防命令注入，Day 168 教训）")
    for bad in ("2026;rm -rf /", "../../etc", "a b", "", "x" * 65):
        try:
            DeployPlan(root="/opt/app", release=bad, artifact_remote="/tmp/a.tgz")
            print(f"   ❌ {bad!r} 本该被拒绝")
            ok = False
        except ValueError:
            print(f"   ✅ {bad!r} 被拒绝")
    for good in ("20260927", "v1.2.3", "rel_2026-09-27"):
        DeployPlan(root="/opt/app", release=good, artifact_remote="/tmp/a.tgz")
    print("   ✅ 合法版本号通过: 20260927 / v1.2.3 / rel_2026-09-27")

    print("\n自检 3：root 必须是绝对路径")
    try:
        DeployPlan(root="opt/app", release="r1", artifact_remote="/tmp/a.tgz")
        print("   ❌ 相对路径本该被拒绝")
        ok = False
    except ValueError as exc:
        print(f"   ✅ 如期拒绝: {exc}")

    print("\n自检 4：部署步骤顺序（切换必须在解包之后）")
    names = [n for n, _ in p.steps()]
    idx_extract = next(i for i, n in enumerate(names) if "解包" in n)
    idx_switch = next(i for i, n in enumerate(names) if "原子切换" in n)
    idx_health = next(i for i, n in enumerate(names) if "健康检查" in n)
    idx_clean = next(i for i, n in enumerate(names) if "清理" in n)
    ordered = idx_extract < idx_switch < idx_health < idx_clean
    ok &= ordered
    print(f"   {'✅' if ordered else '❌'} 解包({idx_extract}) < 切换({idx_switch}) < 健康({idx_health}) < 清理({idx_clean})")

    print("\n自检 5：parse_prev_release")
    cases = [("/opt/app/releases/20260926-1830\n", "20260926-1830"),
             ("", ""),
             ("/opt/app/current\n", "current")]
    for text, want in cases:
        got = parse_prev_release(text)
        flag = "✅" if got == want else "❌"
        ok &= got == want
        print(f"   {flag} {text!r} → {got!r}（期望 {want!r}）")

    print("\n自检 6：回滚防御（不许跳到 releases 之外）")
    r1 = p.rollback_steps("/opt/app/releases/20260926-1830")
    ok &= "ln -sfn" in r1[0][1] and "20260926-1830" in r1[0][1]
    print(f"   ✅ 合法回滚: {r1[0][1]}")
    r2 = p.rollback_steps("/etc/passwd")
    ok &= "拒绝回滚" in r2[0][1]
    print(f"   ✅ 非法回滚被拒: {r2[0][1]}")
    r3 = p.rollback_steps("")
    ok &= "无上一版" in r3[0][1]
    print(f"   ✅ 无上一版: {r3[0][1]}")

    print("\nSELF-TEST OK" if ok else "\nSELF-TEST FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# 3. 执行
# ---------------------------------------------------------------------------
@dataclass
class HostDeployResult:
    host: str
    status: str = "unknown"        # ok / failed / rolled_back / unreachable / dry_run
    steps_done: int = 0
    prev_release: str = ""
    seconds: float = 0.0
    error: str = ""


def deploy_one(host: str, plan: DeployPlan, *, apply: bool, artifact_local: str | None,
               rollback_only: bool, keep_going: bool, **conn_kwargs) -> HostDeployResult:
    """在一台机器上执行完整部署（含失败回滚）。"""
    res = HostDeployResult(host=host)
    t0 = time.monotonic()
    try:
        with Connection(host, **conn_kwargs) as conn:
            # 0) 记录上一版（回滚锚点）
            prev = conn.run(f"readlink -f {plan.current_link} 2>/dev/null || true",
                            warn=True, hide=True)
            res.prev_release = parse_prev_release(prev.stdout or "")
            print(f"   ℹ 上一版: {res.prev_release or '(首次部署)'}")

            if rollback_only:
                steps = plan.rollback_steps(res.prev_release)
            else:
                if artifact_local:
                    print(f"   ↑ 上传 {artifact_local} → {plan.artifact_remote}")
                    if apply:
                        conn.put(artifact_local, plan.artifact_remote)
                steps = plan.steps()

            for i, (desc, cmd) in enumerate(steps, 1):
                prefix = "   [dry-run] " if not apply else "   "
                print(f"{prefix}② {i:>2}/{len(steps)} {desc}")
                if not apply:
                    res.steps_done += 1
                    continue
                r = conn.run(cmd, warn=True, hide=True)
                if not r.ok:
                    raise RuntimeError(f"步骤失败 [{desc}] exit={r.return_code}: "
                                       f"{(r.stderr or r.stdout).strip()[:200]}")
                res.steps_done += 1

            if not apply:
                res.status = "dry_run"
                return res

            res.status = "ok"
            print("   ✅ 部署成功")
            return res
    except Exception as exc:
        res.error = f"{type(exc).__name__}: {exc}"
        print(f"   ❌ 失败: {res.error}")
        # —— 失败回滚 ——
        if apply and not rollback_only and res.prev_release:
            print(f"   ↩ 触发自动回滚 → {res.prev_release}")
            rb_ok = True
            try:
                with Connection(host, **conn_kwargs) as conn:
                    for desc, cmd in plan.rollback_steps(res.prev_release):
                        r = conn.run(cmd, warn=True, hide=True)
                        if not r.ok:
                            rb_ok = False
                        print(f"      {'✅' if r.ok else '❌'} 回滚: {desc}")
            except Exception as rb_exc:
                rb_ok = False
                res.error += f" | 回滚异常: {type(rb_exc).__name__}: {rb_exc}"
            # ⚠ 只有当回滚步骤**全部成功**才算 rolled_back，
            #   否则必须报 failed —— 不能把"回滚失败"伪装成"已回滚"。
            res.status = "rolled_back" if rb_ok else "failed"
            if not rb_ok:
                res.error += " | 回滚未全部成功，需人工介入"
        else:
            res.status = "failed"
        return res
    finally:
        res.seconds = round(time.monotonic() - t0, 2)


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 169 实战：可回滚的批量部署")
    ap.add_argument("--hosts", help="逗号分隔 host[:port]")
    ap.add_argument("--user")
    ap.add_argument("--key")
    ap.add_argument("--artifact", help="本地 artifact 路径（tar.gz）")
    ap.add_argument("--release", help="版本号（白名单 [0-9A-Za-z._-]）")
    ap.add_argument("--root", default="/opt/app")
    ap.add_argument("--service", default="app")
    ap.add_argument("--health-path", default="/healthz")
    ap.add_argument("--keep", type=int, default=3, help="保留的历史版本数")
    ap.add_argument("--restart-cmd", default="systemctl restart {service}",
                    help="重启命令模板，可用 {service} 占位（如 'supervisorctl restart {service}'）")
    ap.add_argument("--health-cmd", default="curl -fsS -m 5 http://127.0.0.1{health_path} >/dev/null",
                    help="健康检查命令模板，可用 {health_path} 占位")
    ap.add_argument("--apply", action="store_true", help="真执行（默认 dry-run）")
    ap.add_argument("--rollback-only", action="store_true")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.hosts or not args.release:
        ap.error("需要 --hosts 与 --release（或 --self-test）")

    plan = DeployPlan(root=args.root, release=args.release,
                      artifact_remote=f"/tmp/{args.release}.tar.gz",
                      health_path=args.health_path, keep=args.keep, service=args.service,
                      restart_cmd=args.restart_cmd, health_cmd=args.health_cmd)
    hosts = [h.strip() for h in args.hosts.split(",") if h.strip()]

    ck: dict = {"timeout": args.timeout, "banner_timeout": args.timeout,
                "auth_timeout": args.timeout}
    if args.key:
        ck["key_filename"] = os.path.expanduser(args.key)

    mode = "回滚" if args.rollback_only else ("执行" if args.apply else "dry-run")
    print(f"🚀 部署 {args.release} → {len(hosts)} 台 · 模式={mode} · root={args.root}")
    print("-" * 96)

    results: list[HostDeployResult] = []
    for i, host in enumerate(hosts, 1):
        print(f"\n▶ [{i}/{len(hosts)}] {host}")           # 串行滚动：一台一台来
        r = deploy_one(host, plan, apply=args.apply, artifact_local=args.artifact,
                       rollback_only=args.rollback_only, keep_going=True,
                       user=args.user, connect_kwargs=ck)
        results.append(r)
        if r.status in ("failed", "rolled_back"):
            print(f"   ⛔ 停止滚动：失败/回滚发生在第 {i} 台，后续主机未执行")
            for rest in hosts[i:]:
                results.append(HostDeployResult(rest, "skipped",
                                                error="滚动已中止，未执行"))
            break

    print("\n" + "=" * 96)
    print(f"{'主机':<28}{'状态':<16}{'步骤':<8}{'耗时(s)':<10}说明")
    print("-" * 96)
    for r in results:
        note = r.error or (f"上一版 {r.prev_release}" if r.prev_release else "首次部署")
        print(f"{r.host:<28}{r.status:<16}{r.steps_done:<8}{r.seconds:<10.2f}{note[:44]}")
    print("=" * 96)
    bad = [r for r in results if r.status in ("failed", "rolled_back", "skipped")]
    if not bad:
        print(f"✅ 全部完成（{mode}）")
        return 0
    print(f"⚠ {len(bad)} 台存在问题：{[r.host for r in bad]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
