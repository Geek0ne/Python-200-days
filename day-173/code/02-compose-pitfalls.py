#!/usr/bin/env python3
"""Day 173 · 02 进阶与避坑：Compose 里那些「看起来对、实际会炸」的地方。

本文件把 Day 173 真机实验里踩过的坑，做成可离线验证的最小复现模型。

覆盖的坑
--------
1. depends_on 的三种语义：启动顺序 ≠ 就绪就绪（service_started / service_healthy / service_completed_successfully）
2. localhost 在容器里指自己，不是别的服务
3. 端口映射方向搞反：宿主机:容器 vs 容器:宿主机
4. 密码/配置必须显式注入：镜像里的 POSTGRES_PASSWORD 不会自动传给 app
5. 命名卷 vs 绑定挂载：down 与 down -v 的差别
6. 一次性任务（Migrate）用 service_completed_successfully，而不是硬 sleep

运行：
    python3 02-compose-pitfalls.py            # 逐条演示
    python3 02-compose-pitfalls.py --self-test  # 全部结论自证
"""
from __future__ import annotations

import argparse
import json
import sys

# --------------------------------------------------------------------------
# 坑 1：depends_on 的三种语义
# --------------------------------------------------------------------------
# 真实语义（Compose Spec）：
#   service_started                 —— 只等容器进程起来，TCP 都没监听
#   service_healthy                 —— 等 healthcheck 首次变 healthy
#   service_completed_successfully  —— 等容器以 exit code 0 结束（迁移脚本用这个）
#
# 关键：healthy 只在「首次启动」时被等待。运行期依赖挂了，Compose 不会重启你。


class FakeService:
    """模拟一个服务的启动时间线：t=起进程，t+ready 才真正可用。"""

    def __init__(self, name: str, boot_s: float, ready_s: float,
                 healthcheck: bool = False, exit_code: int | None = None):
        self.name = name
        self.boot_s = boot_s          # 进程起来耗时
        self.ready_s = ready_s        # 真正能接受请求的耗时（initdb 之类）
        self.healthcheck = healthcheck
        self.exit_code = exit_code    # 非 None 表示一次性任务

    def becomes_healthy_at(self) -> float | None:
        if not self.healthcheck:
            return None
        return self.boot_s + self.ready_s


def simulate_start_order(svcs: dict[str, FakeService],
                         deps: dict[str, dict[str, str]]) -> tuple[list[str], list[dict]]:
    """返回 (实际可处理请求的时刻列表, 首次请求是否失败的记录)。"""
    started: dict[str, float] = {}
    failures: list[dict] = []

    # service_started：t = 依赖的 started
    # service_healthy：t = 依赖真正 ready 的时刻（无 healthcheck 则永远等不到）
    def ready_time(name: str, seen: set[str]) -> float:
        s = svcs[name]
        base = started.get(name, s.boot_s)
        return base + s.ready_s

    for name, s in svcs.items():
        blockers = deps.get(name, {})
        t = 0.0
        for dep, cond in blockers.items():
            if cond == "service_started":
                t = max(t, started.get(dep, svcs[dep].boot_s))
            elif cond == "service_healthy":
                th = svcs[dep].becomes_healthy_at()
                if th is None:
                    failures.append({"service": name, "dep": dep,
                                     "reason": "dep 没有 healthcheck，Compose 会等到超时"})
                    t = float("inf")
                else:
                    t = max(t, ready_time(dep, set()))
            elif cond == "service_completed_successfully":
                t = max(t, ready_time(dep, set()))
        started[name] = max(s.boot_s, t)

    # 记录「谁在依赖 ready 之前就发了第一个请求」
    for name, blockers in deps.items():
        for dep, cond in blockers.items():
            if started[name] < ready_time(dep, set()):
                failures.append({"service": name, "dep": dep, "condition": cond,
                                 "starts_at_ms": int(started[name] * 1000),
                                 "dep_ready_at_ms": int(ready_time(dep, set()) * 1000),
                                 "reason": "依赖还没就绪就发第一个请求 → 首次调用必失败"})
    return [f"{k}@{int(v * 1000) if v != float('inf') else 'inf'}ms"
            for k, v in started.items()], failures


# --------------------------------------------------------------------------
# 坑 2：localhost 在容器里指自己
# --------------------------------------------------------------------------
def pitfall_localhost() -> None:
    print("【坑 2】app 容器里写 REDIS_HOST=localhost 会连到自己！")
    print("  容器 A 的 localhost = 容器 A 自己，redis 在另一个容器")
    print("  正确写法：REDIS_HOST=redis（Compose 自动注入服务名）")


# --------------------------------------------------------------------------
# 坑 3：端口映射方向
# --------------------------------------------------------------------------
PORT_RULES = [
    ("18080:8000", "宿主 18080 → 容器 8000", "服务内部监听 8000，外部访问 18080"),
    ("8000", "随机映射到宿主机", "不确定端口，只能用 -P 或 compose ps 查"),
    ("8000:80", "宿主 8000 → 容器 80", "容器必须真的监听 80，写错就 502/connection refused"),
]


def pitfall_ports() -> None:
    print("\n【坑 3】端口映射方向：`宿主端口:容器端口`")
    for spec, meaning, note in PORT_RULES:
        print(f"  {spec:12s} {meaning:24s} {note}")


# --------------------------------------------------------------------------
# 坑 4：环境变量不会自动传播
# --------------------------------------------------------------------------
def pitfall_env() -> None:
    print("\n【坑 4】postgres 镜像里的 POSTGRES_PASSWORD 只是它自己的密码，不会传给 app！")
    print("  app 连库必须显式写：")
    print("    environment:")
    print("      PGUSER: app")
    print("      PGPASSWORD: ${PGPASSWORD:-app}   # ← 必须显式注入")


# --------------------------------------------------------------------------
# 坑 5：命名卷 vs 绑定挂载
# --------------------------------------------------------------------------
VOLUME_KINDS = [
    ("dbdata:/var/lib/postgresql/data", "命名卷", "down 保留，down -v 删除", "生产/测试环境首选"),
    ("./data:/var/lib/postgresql/data", "绑定挂载", "down 保留，数据在宿主机可见", "开发调试、挂配置文件"),
]


def pitfall_volumes() -> None:
    print("\n【坑 5】命名卷 vs 绑定挂载")
    print(f"  {'写法':40s} {'类型':8s} {'down 时':16s} 场景")
    for spec, kind, ondown, scene in VOLUME_KINDS:
        print(f"  {spec:40s} {kind:8s} {ondown:16s} {scene}")
    print("  ⚠️ 误用 down -v 会永久删除数据库卷，生产慎用！")


# --------------------------------------------------------------------------
# 坑 6：一次性迁移任务
# --------------------------------------------------------------------------
MIGRATE_COMPOSE = """
  migrate:
    build: .
    command: ["python", "migrate.py"]
    depends_on:
      postgres: {condition: service_healthy}
    restart: "no"          # 跑完就退出，不重启

  app:
    build: .
    depends_on:
      migrate: {condition: service_completed_successfully}
"""
PITFALL_SLEEP_COMPOSE = """
  app:
    build: .
    depends_on:
      postgres: {condition: service_healthy}
    command: ["sh", "-c", "sleep 10 && python app.py"]   # ❌ 用 sleep 猜时间
"""


def pitfall_migrate() -> None:
    print("\n【坑 6】迁移脚本不要用 sleep 猜时间，用 service_completed_successfully")
    print("  ❌ 错误：\n" + PITFALL_SLEEP_COMPOSE)
    print("  ✅ 正确：\n" + MIGRATE_COMPOSE)


def self_test() -> int:
    svcs = {
        "postgres": FakeService("postgres", boot_s=1.0, ready_s=6.0, healthcheck=True),
        "app": FakeService("app", boot_s=0.2, ready_s=0.1),
    }

    # service_started：app 在 postgres 进程起来后立刻启动，但 db 还没 ready
    order, fails = simulate_start_order(svcs, {"app": {"postgres": "service_started"}})
    assert any("必失败" in f["reason"] for f in fails), "service_started 应模拟出首次失败"
    app_start = [o for o in order if o.startswith("app")][0]
    assert app_start == "app@1000ms", app_start

    # service_healthy：app 等到 db 真的 ready
    order2, fails2 = simulate_start_order(svcs, {"app": {"postgres": "service_healthy"}})
    app_start2 = [o for o in order2 if o.startswith("app")][0]
    assert app_start2 == "app@7000ms", app_start2
    assert not any("必失败" in f["reason"] for f in fails2)

    # 坑：要求 healthy 但对方没 healthcheck
    bad = {"postgres": FakeService("postgres", boot_s=1.0, ready_s=6.0, healthcheck=False),
           "app": FakeService("app", boot_s=0.2, ready_s=0.1)}
    _, fails3 = simulate_start_order(bad, {"app": {"postgres": "service_healthy"}})
    assert any("没有 healthcheck" in f["reason"] for f in fails3)

    print("02-compose-pitfalls self-test: PASS（4 组断言全过）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("=== 坑 1：depends_on 三种语义的时间线模拟 ===")
    print("场景：postgres 进程 1.0s 起来，但要跑 initdb，6.0s 后才真正可用\n")
    svcs = {"postgres": FakeService("postgres", boot_s=1.0, ready_s=6.0, healthcheck=True),
            "app": FakeService("app", boot_s=0.2, ready_s=0.1)}

    for cond in ["service_started", "service_healthy"]:
        order, fails = simulate_start_order(svcs, {"app": {"postgres": cond}})
        print(f"  depends_on: postgres → {cond}")
        print(f"    时间线: {order}")
        for f in fails:
            print(f"    ⚠️ {f['service']} 在第 {f.get('starts_at_ms')}ms 就发请求，"
                  f"而依赖 {f.get('dep_ready_at_ms')}ms 才就绪")
        print()

    pitfall_localhost()
    pitfall_ports()
    pitfall_env()
    pitfall_volumes()
    pitfall_migrate()
    print("\n💡 记住：depends_on 管的是「顺序」，healthcheck 管的是「就绪」，"
          "应用自身的重试逻辑才是最后一道保险。")
    return 0


if __name__ == "__main__":
    sys.exit(main())