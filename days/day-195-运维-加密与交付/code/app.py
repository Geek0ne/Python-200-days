#!/usr/bin/env python3
"""
Day 195 · 05 可部署的运维验收服务（零 Web 框架依赖）

接口：
    GET  /healthz                 存活探针（进程活着就 200，不碰磁盘/网络）
    GET  /readyz                  就绪探针（能写库 + 有主密钥才 200）
    GET  /metrics                 进程内计数器（JSON）
    POST /api/v1/records          HMAC 签名鉴权；secret 字段 AES-GCM 加密后落库
    GET  /api/v1/records/{id}     签名鉴权；解密返回
    GET  /api/v1/records          列出 id/name（绝不返回明文）

为什么 liveness 和 readiness 要分开：
- liveness 失败 = 容器该被重启（进程卡死）；
- readiness 失败 = 暂时别给它流量（数据库还没起来、密钥还没挂上）。
把二者合成一个，数据库抖一下就会触发全量重启，把小故障放大成雪崩。

运行：
    python3 app.py --self-test
    DATA_DIR=./data API_SECRET=demo python3 app.py --port 8080
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import signal
import sqlite3
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from crypto_lib import (
    KeyRing, NonceStore, decrypt, encrypt, envelope_kid, sign_request, verify_request,
)
from ops_lib import JsonLogger


# ─────────────────────────────────────────────────────────────
# 指标：线程安全的小计数器
# ─────────────────────────────────────────────────────────────

class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}

    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(sorted(self._counters.items()))


# ─────────────────────────────────────────────────────────────
# 密钥加载：环境变量优先；否则落盘（仅为教学，生产用 KMS）
# ─────────────────────────────────────────────────────────────

def decode_key(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def load_keyring(data_dir: Path) -> KeyRing:
    env_key = os.environ.get("MASTER_KEY")
    if env_key:
        material = decode_key(env_key)
        if len(material) != 32:
            raise SystemExit("MASTER_KEY must decode to 32 bytes")
        return KeyRing({"env": material})

    path = data_dir / "keyring.json"
    if path.exists():
        raw = json.loads(path.read_text())
        keys = {kid: decode_key(value) for kid, value in raw["keys"].items()}
        return KeyRing(keys, raw.get("primary"))

    ring = KeyRing({"local": KeyRing.generate_key()})
    data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"primary": ring.primary, "keys": ring.export()}, indent=2))
    path.chmod(0o600)
    return ring


# ─────────────────────────────────────────────────────────────
# 业务对象：记录 + 静态加密
# ─────────────────────────────────────────────────────────────

class App:
    def __init__(self, data_dir: Path, api_secret: bytes, keyring: KeyRing) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "app.db"
        self.api_secret = api_secret
        self.keyring = keyring
        self.nonces = NonceStore(ttl=300)
        self.metrics = Metrics()
        self.log = JsonLogger("learn195-app")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=3000")
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    ciphertext  TEXT NOT NULL,
                    kid         TEXT NOT NULL,
                    created_at  TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_records_created ON records(created_at)"
            )

    # ── 探针 ──
    def ready(self) -> tuple[int, dict]:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1").fetchone()
            if not self.keyring.primary:
                raise RuntimeError("no primary key")
            return 200, {"status": "ready", "kid": self.keyring.primary}
        except Exception as exc:  # noqa: BLE001
            self.log.error("readiness_failed", error=str(exc))
            return 503, {"status": "not_ready", "reason": str(exc)}

    # ── 鉴权 ──
    def authenticate(self, method: str, path: str, headers,
                     body: bytes) -> tuple[int, str]:
        timestamp = headers.get("X-Timestamp")
        nonce = headers.get("X-Nonce")
        signature = headers.get("X-Signature")
        self.metrics.inc("auth_checks")
        if not (timestamp and nonce and signature):
            self.metrics.inc("auth_failures")
            return 401, "missing_auth_headers"

        ok, reason = verify_request(
            self.api_secret, method, path, timestamp, nonce, body, signature,
            max_skew=300,
        )
        if not ok:
            self.metrics.inc("auth_failures")
            return 401, reason
        if not self.nonces.use(nonce):
            self.metrics.inc("auth_failures")
            return 409, "replayed_nonce"
        return 200, "ok"

    # ── 业务接口 ──
    def handle_api(self, method: str, path: str, headers,
                   body: bytes) -> tuple[int, dict]:
        status, reason = self.authenticate(method, path, headers, body)
        if status != 200:
            return status, {"error": reason}

        if method == "POST" and path == "/api/v1/records":
            return self.create_record(body)
        if method == "GET" and path == "/api/v1/records":
            return self.list_records()
        if method == "GET" and path.startswith("/api/v1/records/"):
            record_id = path.rsplit("/", 1)[-1]
            return self.get_record(record_id)
        return 404, {"error": "not_found"}

    def create_record(self, body: bytes) -> tuple[int, dict]:
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return 400, {"error": "invalid_json"}
        name = payload.get("name")
        secret = payload.get("secret")
        if not isinstance(name, str) or not name.strip():
            return 422, {"error": "name_required"}
        if not isinstance(secret, str) or not secret:
            return 422, {"error": "secret_required"}

        record_id = uuid.uuid4().hex
        token = encrypt(self.keyring, secret.encode("utf-8"), aad=record_id.encode())
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO records (id, name, ciphertext, kid, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (record_id, name, token, envelope_kid(token), now),
            )
        self.metrics.inc("records_created")
        self.log.info("record_created", record_id=record_id, kid=envelope_kid(token))
        return 201, {"id": record_id, "kid": envelope_kid(token), "created_at": now}

    def get_record(self, record_id: str) -> tuple[int, dict]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, ciphertext, kid FROM records WHERE id = ?",
                (record_id,),
            ).fetchone()
        if row is None:
            return 404, {"error": "not_found"}
        try:
            secret = decrypt(self.keyring, row[2], aad=row[0].encode()).decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            # 解密失败通常意味着：换了钥匙没迁移 / 数据被篡改
            self.metrics.inc("decrypt_failures")
            self.log.error("decrypt_failed", record_id=record_id, error=str(exc))
            return 500, {"error": "decrypt_failed"}
        self.metrics.inc("records_read")
        return 200, {"id": row[0], "name": row[1], "secret": secret, "kid": row[3]}

    def list_records(self) -> tuple[int, dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name, kid, created_at FROM records ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
        return 200, {
            "items": [
                {"id": r[0], "name": r[1], "kid": r[2], "created_at": r[3]}
                for r in rows
            ],
            "count": len(rows),
        }


# ─────────────────────────────────────────────────────────────
# HTTP 层
# ─────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "learn195/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = 10

    def log_message(self, fmt: str, *args) -> None:
        pass  # 访问日志由结构化 logger 统一输出

    @property
    def app(self) -> App:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        started = time.perf_counter()
        request_id = self.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        log = self.app.log.bind(request_id=request_id)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        path = urlparse(self.path).path
        self.app.metrics.inc("requests_total")

        try:
            if path == "/healthz":
                status, payload = 200, {"status": "ok", "pid": os.getpid()}
            elif path == "/readyz":
                status, payload = self.app.ready()
            elif path == "/metrics":
                self.app.metrics.inc("metrics_scrapes")
                status, payload = 200, self.app.metrics.snapshot()
            elif path.startswith("/api/v1/records"):
                status, payload = self.app.handle_api(
                    method, path, self.headers, body
                )
            else:
                status, payload = 404, {"error": "not_found"}
        except Exception as exc:  # noqa: BLE001
            self.app.metrics.inc("unhandled_errors")
            log.error("unhandled_error", error=str(exc),
                      traceback=traceback.format_exc())
            status, payload = 500, {"error": "internal_error"}

        if status >= 500:
            self.app.metrics.inc("responses_5xx")
        self._respond(status, payload, request_id)
        log.info(
            "request",
            method=method,
            path=path,
            status=status,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            request_bytes=length,
        )

    def _respond(self, status: int, payload: dict, request_id: str) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-ID", request_id)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class AppServer(ThreadingHTTPServer):
    daemon_threads = False      # 优雅退出：等在途请求处理完
    block_on_close = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], app: App) -> None:
        super().__init__(address, Handler)
        self.app = app


# ─────────────────────────────────────────────────────────────
# 自检：不 bind 端口，直接调 App
# ─────────────────────────────────────────────────────────────

def self_test() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ring = KeyRing({"t": KeyRing.generate_key()})
        app = App(Path(tmp), b"self-test-secret", ring)
        assert app.ready()[0] == 200

        body = json.dumps({"name": "alice", "secret": "s3cr3t-value"}).encode()
        timestamp = int(time.time())
        nonce = "self-1"
        signature = sign_request(app.api_secret, "POST", "/api/v1/records",
                                 timestamp, nonce, body)
        headers = {
            "X-Timestamp": str(timestamp),
            "X-Nonce": nonce,
            "X-Signature": signature,
        }
        status, payload = app.handle_api("POST", "/api/v1/records", headers, body)
        assert status == 201, (status, payload)
        record_id = payload["id"]

        # 重放同一 nonce
        assert app.handle_api("POST", "/api/v1/records", headers, body)[0] == 409

        # 读回并解密
        nonce2 = "self-2"
        path = f"/api/v1/records/{record_id}"
        signature2 = sign_request(app.api_secret, "GET", path, timestamp, nonce2, b"")
        status, payload = app.handle_api("GET", path, {
            "X-Timestamp": str(timestamp),
            "X-Nonce": nonce2,
            "X-Signature": signature2,
        }, b"")
        assert status == 200 and payload["secret"] == "s3cr3t-value", payload

        # 落库必须是密文
        with sqlite3.connect(app.db_path) as connection:
            raw = connection.execute(
                "SELECT ciphertext FROM records WHERE id = ?", (record_id,)
            ).fetchone()[0]
        assert raw.startswith("v1.") and "s3cr3t-value" not in raw, raw

        # 未签名请求
        assert app.handle_api("GET", "/api/v1/records", {}, b"") == (401, {"error": "missing_auth_headers"})
        print("✅ app.py self-test passed (probes / auth / replay / at-rest encryption)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Day 195 运维验收服务")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    parser.add_argument("--data-dir", default=os.environ.get("DATA_DIR", "./data"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    data_dir = Path(args.data_dir)
    api_secret = os.environ.get("API_SECRET", "")
    if not api_secret:
        raise SystemExit("API_SECRET is required (do not ship a default secret)")
    keyring = load_keyring(data_dir)
    app = App(data_dir, api_secret.encode(), keyring)
    app.log.info("startup", port=args.port, data_dir=str(data_dir),
                 kid=keyring.primary, pid=os.getpid())

    server = AppServer(("0.0.0.0", args.port), app)
    stopping = threading.Event()

    def handle_signal(signum, frame) -> None:
        if stopping.is_set():
            return
        stopping.set()
        app.log.info("shutdown_requested", signal=signum)
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        app.log.info("shutdown_complete")


if __name__ == "__main__":
    main()
