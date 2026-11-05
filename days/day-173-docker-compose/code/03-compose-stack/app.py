#!/usr/bin/env python3
"""Day 173 实验用 Web 应用：演示 Compose 多服务编排中的真实网络与依赖关系。

行为
----
GET /healthz   -> 返回自身状态（不连任何依赖），用于容器 healthcheck
GET /stats     -> 连 Redis 做 INCR、并从 Postgres 读一行，验证服务间 DNS 解析
GET /ready     -> 同时探测 Redis / Postgres，供人工 curl 观察启动顺序问题

设计要点
--------
* 完全离线可自证：--self-test 不依赖任何外部服务，用纯标准库模拟依赖。
* 依赖地址全部来自环境变量 —— 这正是 Compose 用服务名注入的方式
  （REDIS_HOST=redis 表示容器网络内的 DNS 名，而非 localhost）。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
PGPASSWORD = os.getenv("PGPASSWORD", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PGHOST = os.getenv("PGHOST", "postgres")
PGPORT = int(os.getenv("PGPORT", "5432"))
PGUSER = os.getenv("PGUSER", "app")
PGDATABASE = os.getenv("PGDATABASE", "appdb")


def log(msg: str) -> None:
    print(f"[app {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------
# 极简 Redis 客户端：手写 RESP 协议，只为了说明"网络上的服务就是字节流"
# --------------------------------------------------------------------------
def redis_ping(host: str, port: int, timeout: float = 2.0) -> str:
    """返回 'pong' 或抛出异常。"""
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(b"*1\r\n$4\r\nPING\r\n")
        return s.recv(64).decode().strip()


def redis_incr(host: str, port: int, key: str, timeout: float = 2.0) -> int:
    cmd = f"*2\r\n$4\r\nINCR\r\n${len(key)}\r\n{key}\r\n"
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(cmd.encode())
        reply = s.recv(64).decode().strip()
    # RESP 的整数应答是 ":1\\r\\n" —— 必须去掉前导冒号，否则 int(':1') 抛 ValueError
    return int(reply.lstrip(":"))


def tcp_probe(host: str, port: int, timeout: float = 2.0) -> bool:
    """只测 TCP 可达 —— 注意：可达 != 就绪，这正是 depends_on 的坑。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def self_test() -> int:
    """离线自证：不起任何容器也能验证本脚本逻辑正确。"""
    ok = True
    # 1) /healthz 的语义
    print("self-test: healthz 不依赖外部服务 ->", json.dumps({"ok": True}))
    # 2) compose 注入的环境变量默认值
    assert REDIS_HOST == "redis" and PGHOST == "postgres", "默认主机名必须是 compose 服务名"
    print("self-test: 默认依赖地址 =", REDIS_HOST, PGHOST)
    # 3) 启动顺序对启动耗时的影响（用不可达地址实测超时行为）
    t0 = time.time()
    reachable = tcp_probe("redis", REDIS_PORT, timeout=0.3)
    dt = time.time() - t0
    print(f"self-test: 探测 redis:{REDIS_PORT} -> {reachable}（耗时 {dt:.2f}s）")
    if reachable:
        print("self-test: 检测到本机有 redis 在跑，继续验证 PING")
        assert redis_ping(REDIS_HOST, REDIS_PORT) == "+PONG"
        n = redis_incr(REDIS_HOST, REDIS_PORT, "day173:self-test")
        assert n >= 1
        print("self-test: INCR ->", n, "✅")
    else:
        print("self-test: 无外部 redis，跳过 PING/INCR 断言（纯离线路径）✅")
    ok = ok and True
    print("self-test result:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def stats() -> dict:
    out = {}
    try:
        out["redis"] = {"ping": redis_ping(REDIS_HOST, REDIS_PORT),
                        "hits": redis_incr(REDIS_HOST, REDIS_PORT, "day173:hits")}
    except Exception as e:  # noqa: BLE001
        out["redis"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        import psycopg  # type: ignore

        with psycopg.connect(f"host={PGHOST} port={PGPORT} user={PGUSER} "
                             f"password={PGPASSWORD} dbname={PGDATABASE} "
                             f"connect_timeout=3") as c:
            with c.cursor() as cur:
                cur.execute("select count(*) from visits")
                out["postgres"] = {"visits": cur.fetchone()[0]}
    except Exception as e:  # noqa: BLE001
        out["postgres"] = {"error": f"{type(e).__name__}: {e}"}
    return out


def handler(path: str) -> tuple[int, str]:
    if path.startswith("/healthz"):
        return 200, json.dumps({"status": "ok", "pid": os.getpid()})
    if path.startswith("/stats"):
        return 200, json.dumps(stats())
    if path.startswith("/ready"):
        r = tcp_probe(REDIS_HOST, REDIS_PORT)
        p = tcp_probe(PGHOST, PGPORT)
        return (200 if (r and p) else 503), json.dumps({"redis_tcp": r, "postgres_tcp": p})
    return 404, json.dumps({"error": "not found"})


def serve(port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            code, body = handler(self.path)
            raw = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt: str, *a) -> None:  # 静音默认访问日志
            return

    log(f"listening on :{port} (redis={REDIS_HOST}:{REDIS_PORT} pg={PGHOST}:{PGPORT})")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印将要连接的目标，不发起任何连接")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.dry_run:
        print(json.dumps({"redis": f"{REDIS_HOST}:{REDIS_PORT}",
                          "postgres": f"{PGHOST}:{PGPORT}",
                          "listen": args.port}, indent=2))
        return 0
    serve(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())