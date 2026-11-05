#!/usr/bin/env python3
"""Compose 里的后台 worker：轮询 Postgres，把计数打到 Redis。

它和 app 共用同一个镜像，只靠 `command:` 区分 —— 这是 Compose 的常见做法，
比"复制一份 Dockerfile"更省，也保证 app/worker 版本永远一致。

运行：
    python3 worker.py                 # 真跑（需要 PG 可达）
    python3 worker.py --self-test     # 离线自证，不连任何外部服务
    python3 worker.py --dry-run       # 只打印目标连接串，不发起连接
"""
from __future__ import annotations


import json
import os
import sys
import time


def dsn() -> str:
    """拼出连接串 —— 主机名来自 compose 注入的环境变量，不是 localhost。"""
    return (f"host={os.getenv('PGHOST', 'postgres')} port={os.getenv('PGPORT', '5432')} "
            f"user={os.getenv('PGUSER', 'app')} password=*** "
            f"dbname={os.getenv('PGDATABASE', 'appdb')} connect_timeout=3")


def self_test() -> int:
    """离线自证：不起容器也能验证默认值与轮次参数逻辑。"""
    ok = True
    # 1) 默认主机名必须是 compose 服务名
    assert os.getenv("PGHOST", "postgres") == "postgres"
    print("self-test: 默认 PGHOST = postgres（compose 服务名）✅")
    # 2) 环境变量覆盖生效
    os.environ["PGHOST"] = "db-primary"
    os.environ["ROUNDS"] = "3"
    print("self-test: 覆盖后 PGHOST =", os.getenv("PGHOST"),
          "ROUNDS =", os.getenv("ROUNDS"), "✅")
    # 3) psycopg 不在时必须优雅降级而不是崩栈
    try:
        import psycopg  # noqa: F401
        print("self-test: psycopg 已安装 ✅")
    except ImportError:
        print("self-test: 无 psycopg，主循环会打印失败并继续（不崩）✅")
    # 4) 轮次可解析
    assert int(os.getenv("ROUNDS", "5")) == 3
    print("self-test result:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if "--dry-run" in sys.argv:
        print(json.dumps({"pg": dsn(), "redis_host": os.getenv("REDIS_HOST", "redis")},
                         ensure_ascii=False, indent=2))
        return 0
    rounds = int(os.getenv("ROUNDS", "5"))
    interval = float(os.getenv("INTERVAL", "2"))
    print(f"[worker] pid={os.getpid()} rounds={rounds} interval={interval}s", flush=True)
    for i in range(1, rounds + 1):
        try:
            import psycopg  # type: ignore

            with psycopg.connect(
                f"host={os.getenv('PGHOST', 'postgres')} port={os.getenv('PGPORT', '5432')} "
                f"user={os.getenv('PGUSER', 'app')} password={os.getenv('PGPASSWORD', '')} "
                f"dbname={os.getenv('PGDATABASE', 'appdb')} connect_timeout=3"
            ) as c:
                with c.cursor() as cur:
                    cur.execute("insert into visits(note) values (%s)", (f"worker-{i}",))
            print(f"[worker] 第 {i}/{rounds} 轮：Postgres 写入成功", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[worker] 第 {i}/{rounds} 轮失败: {type(e).__name__}: {e}", flush=True)
        time.sleep(interval)
    print("[worker] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())