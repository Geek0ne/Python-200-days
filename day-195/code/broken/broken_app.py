#!/usr/bin/env python3
"""故意坏掉的服务：/healthz 永远 500，用来验证部署脚本能否自动回滚。"""

from http.server import BaseHTTPRequestHandler, HTTPServer


class Broken(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = b'{"status":"broken"}'
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args) -> None:
        pass


if __name__ == "__main__":
    print("broken app listening on :8080", flush=True)
    HTTPServer(("0.0.0.0", 8080), Broken).serve_forever()
