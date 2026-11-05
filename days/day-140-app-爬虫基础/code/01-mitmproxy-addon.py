"""
01 - mitmproxy 抓包脚本（基础用法）
====================================
用 mitmdump 加载本脚本，实时捕获 App 的 HTTPS 请求并保存 JSON 数据。

运行方式（先安装: pip install mitmproxy）:
    mitmdump -s 01-mitmproxy-addon.py -w app.flow

说明:
    手机设置 Wi-Fi 代理指向电脑 IP:8080，
    并安装 mitmproxy CA 证书（浏览器访问 mitm.it）。
"""

import json
import time
from pathlib import Path

from mitmproxy import http

# 只关心这个域名的接口（按实际情况修改）
TARGET_HOST = "api.example.com"
OUTPUT_FILE = Path(__file__).parent / "captured_data.jsonl"


class AppCapture:
    """mitmproxy 插件类：每次请求/响应都会回调对应方法"""

    def response(self, flow: http.HTTPFlow) -> None:
        """响应到达时触发——在这里读数据最合适"""
        if TARGET_HOST not in flow.request.pretty_host:
            return

        req = flow.request
        resp = flow.response

        record = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": req.method,
            "url": req.pretty_url,
            # 请求头里通常能挖到 token / device_id / sign
            "req_headers": dict(req.headers),
            "req_body": req.get_text() or "",
            "status": resp.status_code,
            "resp_body": resp.get_text()[:5000],  # 截断防止文件爆炸
        }

        # 追加写入 JSONL（每行一个 JSON，方便 pandas 读取）
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 终端打印摘要
        print(f"[捕获] {req.method} {req.path} -> {resp.status_code}")


# mitmproxy 约定：模块级变量 addons 是插件列表
addons = [AppCapture()]


# ═══════════════ 不启动 mitmproxy 也能本地自测 ═══════════════
if __name__ == "__main__":
    print("本文件设计为 mitmdump 插件，请用: mitmdump -s 01-mitmproxy-addon.py")
    print(f"目标域名: {TARGET_HOST}")
    print(f"输出文件: {OUTPUT_FILE}")
