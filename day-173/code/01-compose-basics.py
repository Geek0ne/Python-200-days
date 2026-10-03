#!/usr/bin/env python3
"""Day 173 · 01 基础用法：用纯 Python 玩懂 Compose 的三个核心概念。

Compose 看着像 YAML，其实只干三件事：
  1. **声明** 一组容器（services）及其镜像/命令/端口
  2. **连线** 把它们挂到同一个网络，网络里互相用「服务名」当 DNS 名
  3. **排序** 按 depends_on 决定启动先后，并保证可被 wait 住的容器不被当成服务

本文件不依赖 Docker，只用标准库把「一个 compose 文件」建模出来，
并演示：服务名解析、依赖拓扑排序、以及 --dry-run 输出。

运行：
    python3 01-compose-basics.py            # 概念演示
    python3 01-compose-basics.py --self-test  # 自证
    python3 01-compose-basics.py --emit-compose lab.yaml  # 生成一份真 compose 文件
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque

# --------------------------------------------------------------------------
# 1) 服务模型：对应 compose.yaml 里的一个 service
# --------------------------------------------------------------------------


class Service:
    def __init__(self, name: str, image: str | None = None,
                 command: list[str] | None = None,
                 ports: list[str] | None = None,
                 environment: dict[str, str] | None = None,
                 depends_on: dict[str, str] | None = None,
                 healthcheck: bool = False,
                 build: str | None = None):
        self.name = name
        self.image = image
        self.build = build
        self.command = command or []
        self.ports = ports or []
        self.environment = environment or {}
        # key=依赖的服务名，value=condition（service_started / service_healthy）
        self.depends_on = depends_on or {}
        self.healthcheck = healthcheck

    def to_yaml(self) -> str:
        """把这个 Service 渲染成 compose 风格 YAML（教学用，不追求完备）。"""
        lines = [f"  {self.name}:"]
        if self.build:
            lines.append(f"    build: {self.build}")
        if self.image:
            lines.append(f"    image: {self.image}")
        if self.command:
            cmd = ", ".join(json.dumps(c) for c in self.command)
            lines.append(f"    command: [{cmd}]")
        if self.ports:
            lines.append("    ports:")
            lines += [f"      - {p!r}" for p in self.ports]
        if self.environment:
            lines.append("    environment:")
            lines += [f"      {k}: {v}" for k, v in self.environment.items()]
        if self.depends_on:
            lines.append("    depends_on:")
            for dep, cond in self.depends_on.items():
                lines.append(f"      {dep}:")
                lines.append(f"        condition: {cond}")
        if self.healthcheck:
            lines.append("    healthcheck:")
            lines.append('      test: ["CMD", "true"]   # 真实项目里换成探活命令')
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"<Service {self.name} deps={list(self.depends_on)}>"


# --------------------------------------------------------------------------
# 2) Compose 项目：网络 + 服务集合
# --------------------------------------------------------------------------


class ComposeProject:
    def __init__(self, name: str, services: list[Service]):
        self.name = name
        self.services = {s.name: s for s in services}

    # -- 概念 2：网络内的「服务名 → IP」映射 ------------------------------
    def dns_map(self) -> dict[str, str]:
        """真实环境由 Docker 内嵌 DNS(127.0.0.11) 完成这件事。
        这里用 172.18.0.x 段做等价模拟，规则与真实一致。"""
        return {name: f"172.18.0.{i + 2}" for i, name in enumerate(self.services)}

    def resolve(self, hostname: str) -> str:
        """容器内 DNS 解析。localhost 指向自己，不指向别的服务 —— 这是新手最常踩的坑。"""
        if hostname == "localhost":
            return "127.0.0.1"
        return self.dns_map().get(hostname, "NXDOMAIN")

    # -- 概念 3：依赖拓扑排序 --------------------------------------------
    def start_order(self) -> list[str]:
        """Kahn 算法求拓扑序：没有环时返回一种合法的启动顺序。
        真实 Compose 也是按这个依赖图决定创建顺序。"""
        indeg = {n: 0 for n in self.services}
        for s in self.services.values():
            for dep in s.depends_on:
                if dep not in self.services:
                    raise KeyError(f"{s.name} 依赖了不存在的服务 {dep}")
                indeg[s.name] += 1
        q = deque(n for n, d in indeg.items() if d == 0)
        order: list[str] = []
        while q:
            n = q.popleft()
            order.append(n)
            for s in self.services.values():
                if n in s.depends_on and s.name in indeg:
                    indeg[s.name] -= 1
                    if indeg[s.name] == 0:
                        q.append(s.name)
        if len(order) != len(self.services):
            raise RuntimeError("依赖成环，Compose 会直接报错拒绝启动")
        return order

    def to_yaml(self) -> str:
        return (f"name: {self.name}\n\nservices:\n"
                + "\n".join(s.to_yaml() for s in self.services.values())
                + "\n")

    def validate(self) -> list[str]:
        """模拟 `docker compose config` 的最小校验，返回问题列表。"""
        problems: list[str] = []
        for s in self.services.values():
            if not s.image and not s.command and not s.build:
                problems.append(f"服务 {s.name} 既没有 image 也没有 command")
            for dep, cond in s.depends_on.items():
                if cond != "service_healthy":
                    continue
                target = self.services.get(dep)
                if target is None or not target.healthcheck:
                    problems.append(
                        f"服务 {s.name} 要求 {dep} service_healthy，"
                        f"但 {dep} 没有 healthcheck —— 永远等不到，会超时失败")
        try:
            self.start_order()
        except RuntimeError as e:
            problems.append(str(e))
        return problems


# --------------------------------------------------------------------------
# 3) 演示用项目：与 README 实验里的真实栈一一对应
# --------------------------------------------------------------------------


def demo_project() -> ComposeProject:
    return ComposeProject("day173-lab", [
        Service("redis", image="redis:7-alpine",
                healthcheck=True,
                command=["redis-server", "--save", ""]),
        Service("postgres", image="postgres:16-alpine",
                ports=["5432"], healthcheck=True,
                environment={"POSTGRES_USER": "app", "POSTGRES_DB": "appdb"}),
        Service("app", build=".", ports=["18080:8000"],
                depends_on={"redis": "service_healthy",
                            "postgres": "service_healthy"},
                environment={"REDIS_HOST": "redis", "PGHOST": "postgres"},
                healthcheck=True),
        Service("worker", build=".", command=["python", "worker.py"],
                depends_on={"postgres": "service_healthy"},
                environment={"PGHOST": "postgres"}),
        Service("nginx", image="nginx:alpine", ports=["18081:80"],
                depends_on={"app": "service_healthy"}),
    ])


def self_test() -> int:
    p = demo_project()
    assert p.resolve("redis") == "172.18.0.2"
    assert p.resolve("localhost") == "127.0.0.1", "localhost 必须解析到自己"
    assert p.resolve("nope") == "NXDOMAIN"
    order = p.start_order()
    assert order.index("redis") < order.index("app"), "redis 必须先于 app"
    assert order.index("postgres") < order.index("worker")
    assert order.index("app") < order.index("nginx")
    assert p.validate() == [], p.validate()

    # 反例：要求 service_healthy 但对方没 healthcheck
    bad = ComposeProject("bad", [Service("db", image="postgres:16-alpine"),
                                 Service("web", depends_on={"db": "service_healthy"})])
    probs = bad.validate()
    assert any("healthcheck" in x for x in probs), probs

    # 反例：依赖成环
    cyc = ComposeProject("cyc", [Service("a", depends_on={"b": "service_started"}),
                                 Service("b", depends_on={"a": "service_started"})])
    try:
        cyc.start_order()
        raise AssertionError("成环依赖应当抛错")
    except RuntimeError:
        pass

    print("01-compose-basics self-test: PASS（5 组断言全过）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-compose", metavar="PATH")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    p = demo_project()
    print("=== 1) 网络内的服务名解析（Docker 内嵌 DNS 127.0.0.11）===")
    for host in ["redis", "postgres", "app", "nginx", "localhost"]:
        print(f"  {host:10s} -> {p.resolve(host)}")

    print("\n=== 2) 依赖拓扑（Compose 决定启动顺序的依据）===")
    for i, n in enumerate(p.start_order(), 1):
        s = p.services[n]
        cond = set(s.depends_on.values())
        note = "→ 等到依赖 healthy 才启动" if cond == {"service_healthy"} else ""
        print(f"  {i}. {n:9s} {s.image or 'build .':24s} {note}")

    print("\n=== 3) 校验（等价于 docker compose config）===")
    print("  问题列表:", p.validate() or "无")

    print("\n=== 4) 同一镜像不同命令：app 与 worker 共用 build ===")
    for n in ["app", "worker"]:
        s = p.services[n]
        print(f"  {n:7s} image={s.image} build={s.build} command={s.command or '(镜像默认)'}")

    if args.emit_compose:
        with open(args.emit_compose, "w", encoding="utf-8") as f:
            f.write(p.to_yaml())
        print(f"\n已写出 compose 片段: {args.emit_compose}")
    return 0


if __name__ == "__main__":
    sys.exit(main())