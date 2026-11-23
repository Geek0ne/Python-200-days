#!/usr/bin/env python3
"""
Day 177 — Prometheus + Grafana
04 · 采集配置 + Grafana 看板（一键起栈）

这一个脚本做三件事：
1. 生成 prometheus.yml（告诉 Prometheus 去哪里拉）
2. 生成 Grafana 的 provisioning（数据源 + 看板），
   —— 注意：Grafana 看板是 **JSON**，不是点出来的。可以进版本库、可以 review。
3. 可选：用 docker 把两个容器真的起起来，并调 API 核对。

用法：
    python3 04-scrape-and-dashboard.py --dry-run            # 只生成到临时目录并校验
    python3 04-scrape-and-dashboard.py --out ./out          # 生成到指定目录
    python3 04-scrape-and-dashboard.py --up                 # 生成 + docker 起栈 + 核对
    python3 04-scrape-and-dashboard.py --self-test          # 校验生成物结构
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

PROM_CONFIG = """\
# Day 177 生成：Prometheus 采集配置
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: "prometheus"          # 自己也要被采集（元监控）
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "app"                 # 我们的 Python 应用
    metrics_path: "/metrics"
    static_configs:
      - targets: ["localhost:{app_port}"]
"""

# Grafana 数据源（provisioning，落盘即生效，不用点 UI）
GRAFANA_DATASOURCE = """\
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    uid: day177-prom
    isDefault: true
    jsonData:
      httpMethod: POST
      timeInterval: 5s
"""

# Grafana 看板也是纯 JSON —— 这份可以直接 import
DASHBOARD = {
    "title": "Day 177 · 应用监控看板",
    "uid": "day177-app",
    "schemaVersion": 39,
    "refresh": "5s",
    "time": {"from": "now-15m", "to": "now"},
    "panels": [
        {
            "id": 1, "title": "Target 存活（up）", "type": "stat",
            "datasource": {"type": "prometheus", "uid": "day177-prom"},
            "targets": [{"expr": "up", "legendFormat": "{{job}}"}],
            "gridPos": {"h": 6, "w": 6, "x": 0, "y": 0},
        },
        {
            "id": 2, "title": "QPS（按状态码）", "type": "timeseries",
            "datasource": {"type": "prometheus", "uid": "day177-prom"},
            "targets": [{
                "expr": 'sum by (status) (rate(app_http_requests_total[1m]))',
                "legendFormat": "{{status}}",
            }],
            "gridPos": {"h": 6, "w": 9, "x": 6, "y": 0},
        },
        {
            "id": 3, "title": "P95 延迟", "type": "timeseries",
            "datasource": {"type": "prometheus", "uid": "day177-prom"},
            "targets": [{
                "expr": "histogram_quantile(0.95, "
                        "rate(app_http_request_duration_seconds_bucket[5m]))",
                "legendFormat": "p95",
            }],
            "gridPos": {"h": 6, "w": 9, "x": 0, "y": 6},
        },
        {
            "id": 4, "title": "进行中的请求（gauge）", "type": "timeseries",
            "datasource": {"type": "prometheus", "uid": "day177-prom"},
            "targets": [{"expr": "app_http_inflight", "legendFormat": "inflight"}],
            "gridPos": {"h": 6, "w": 6, "x": 9, "y": 6},
        },
    ],
}


def write_artifacts(out_dir, app_port):
    os.makedirs(os.path.join(out_dir, "grafana", "provisioning", "datasources"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "grafana", "provisioning", "dashboards"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "grafana", "dashboards"), exist_ok=True)

    paths = {}
    p = os.path.join(out_dir, "prometheus.yml")
    with open(p, "w") as f:
        f.write(PROM_CONFIG.format(app_port=app_port))
    paths["prometheus"] = p

    p = os.path.join(out_dir, "grafana", "provisioning", "datasources",
                     "day177-datasource.yml")
    with open(p, "w") as f:
        f.write(GRAFANA_DATASOURCE)
    paths["datasource"] = p

    p = os.path.join(out_dir, "grafana", "provisioning", "dashboards", "day177.yml")
    with open(p, "w") as f:
        f.write("apiVersion: 1\nproviders:\n  - name: 'day177'\n"
                "    folder: ''\n    type: file\n    options:\n"
                "      path: /etc/grafana/dashboards\n")
    paths["dashboard_provider"] = p

    p = os.path.join(out_dir, "grafana", "dashboards", "day177-app.json")
    with open(p, "w") as f:
        json.dump(DASHBOARD, f, ensure_ascii=False, indent=2)
    paths["dashboard"] = p
    return paths


def _mini_yaml_check(text, required_keys):
    """不引入 PyYAML 的前提下做最基本的校验：关键行必须在。"""
    missing = [k for k in required_keys if k not in text]
    if missing:
        raise AssertionError(f"生成的 YAML 缺少关键项: {missing}")


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_artifacts(tmp, 9101)
        prom = open(paths["prometheus"]).read()
        _mini_yaml_check(prom, ["scrape_interval: 5s", "job_name: \"app\"",
                                "metrics_path: \"/metrics\"",
                                "targets: [\"localhost:9101\"]"])
        ds = open(paths["datasource"]).read()
        _mini_yaml_check(ds, ["type: prometheus", "uid: day177-prom", "isDefault: true"])

        dash = json.load(open(paths["dashboard"]))
        assert dash["uid"] == "day177-app"
        exprs = [t["expr"] for panel in dash["panels"] for t in panel["targets"]]
        assert "up" in exprs, "看板缺 up 面板"
        assert any("histogram_quantile(0.95" in e for e in exprs), "看板缺 P95"
        assert any(e.startswith("sum by (status)") for e in exprs), "看板缺按状态聚合"
        # 数据源 uid 必须与看板里引用的 uid 一致，否则图全空
        for panel in dash["panels"]:
            assert panel["datasource"]["uid"] == "day177-prom", "面板数据源 uid 不匹配"

        print(f"✅ self-test 通过：生成 4 个文件；prometheus.yml 指向 :9101、"
              f"看板 {len(dash['panels'])} 个面板，数据源 uid 全场一致")
    return 0


def run_up(out_dir, app_port):
    """真的把栈起起来，并用 HTTP API 核对。需要 docker。"""
    print("→ 启动 prometheus 与 grafana（--network host，便于拉本机 :%d）" % app_port)
    subprocess.run(["docker", "rm", "-f", "d177-prom", "d177-grafana"],
                   capture_output=True)
    subprocess.run([
        "docker", "run", "-d", "--name", "d177-prom", "--network", "host",
        "-v", f"{os.path.abspath(os.path.join(out_dir, 'prometheus.yml'))}:/etc/prometheus/prometheus.yml:ro",
        "prom/prometheus:v3.0.1",
        "--config.file=/etc/prometheus/prometheus.yml",
    ], check=True, capture_output=True)
    subprocess.run([
        "docker", "run", "-d", "--name", "d177-grafana", "--network", "host",
        "-e", "GF_AUTH_ANONYMOUS_ENABLED=true",
        "-e", "GF_AUTH_ANONYMOUS_ORG_ROLE=Admin",
        "-v", f"{os.path.abspath(os.path.join(out_dir, 'grafana', 'provisioning'))}:/etc/grafana/provisioning:ro",
        "-v", f"{os.path.abspath(os.path.join(out_dir, 'grafana', 'dashboards'))}:/etc/grafana/dashboards:ro",
        "grafana/grafana:11.4.0",
    ], check=True, capture_output=True)

    def wait(url, name, timeout=60):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                with urllib.request.urlopen(url, timeout=3) as r:
                    if r.status == 200:
                        print(f"  ✓ {name} 就绪（{time.time()-t0:.1f}s）")
                        return True
            except Exception:
                time.sleep(1)
        print(f"  ✗ {name} 在 {timeout}s 内没起来")
        return False

    ok1 = wait("http://localhost:9090/-/ready", "prometheus")
    ok2 = wait("http://localhost:3000/api/health", "grafana")
    if not (ok1 and ok2):
        return 1

    with urllib.request.urlopen("http://localhost:9090/api/v1/targets", timeout=5) as r:
        targets = json.loads(r.read().decode())
    active = targets["data"]["activeTargets"]
    print(f"  采集目标 {len(active)} 个：")
    for t in active:
        print(f"    - {t['labels'].get('job')} {t['scrapeUrl']} health={t['health']}")
    with urllib.request.urlopen("http://localhost:3000/api/search?query=", timeout=5) as r:
        found = json.loads(r.read().decode())
    titles = [d.get("title") for d in found]
    print(f"  Grafana 已加载看板：{titles}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Day 177 · 04 采集配置 + 看板")
    ap.add_argument("--out", default=None, help="输出目录（默认临时目录）")
    ap.add_argument("--app-port", type=int, default=9101, help="被采集应用端口")
    ap.add_argument("--dry-run", action="store_true", help="只生成并校验，不起容器")
    ap.add_argument("--up", action="store_true", help="生成后 docker 起栈")
    ap.add_argument("--self-test", action="store_true", help="校验生成物结构")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    out_dir = args.out or tempfile.mkdtemp(prefix="day177-")
    paths = write_artifacts(out_dir, args.app_port)
    print("生成：")
    for k, v in paths.items():
        print(f"  {k:20s} {v}")

    if args.up:
        sys.exit(run_up(out_dir, args.app_port))
    print("\n下一步：python3 04-scrape-and-dashboard.py --up    # 真的起栈并核对")


if __name__ == "__main__":
    main()
