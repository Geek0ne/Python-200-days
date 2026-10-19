#!/usr/bin/env python3
"""告警接收端（Webhook Sink）。GET /health、GET /counts、POST /alert。"""
from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DATA_DIR = os.environ.get("DATA_DIR", "/data")
PORT = int(os.environ.get("PORT", "8080"))
START = time.time()
LOCK = threading.Lock()
STATE = {"alerts": 0, "items": 0, "duplicates": 0, "invalid": 0, "last_at": None}
SEEN: dict[str, int] = {}


def record(payload: dict) -> dict:
    with LOCK:
        STATE["alerts"] += 1
        items = payload.get("items", [])
        STATE["items"] += len(items)
        for item in items:
            fp = f"{item.get('rule')}|{item.get('asset')}"
            if fp in SEEN:
                STATE["duplicates"] += 1
            SEEN[fp] = SEEN.get(fp, 0) + 1
        STATE["last_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, "alerts.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return dict(STATE, distinct=len(SEEN))


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._json(200, {"status": "ok", "uptime": round(time.time() - START, 1)})
        elif self.path == "/counts":
            with LOCK:
                self._json(200, dict(STATE, distinct=len(SEEN)))
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/alert":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            with LOCK:
                STATE["invalid"] += 1
            self._json(400, {"error": "invalid json"})
            return
        if not isinstance(payload.get("items"), list) or "title" not in payload:
            with LOCK:
                STATE["invalid"] += 1
            self._json(422, {"error": "schema: title + items required"})
            return
        self._json(200, {"ok": True, "counts": record(payload)})

    def log_message(self, fmt, *args):
        print(f"[sink] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[sink] listening on :{PORT} data={DATA_DIR}", flush=True)
    server.serve_forever()
