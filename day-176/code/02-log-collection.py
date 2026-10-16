#!/usr/bin/env python3
"""
Day 176 — ELK 日志系统
采集 Nginx 日志并写入 Elasticsearch
"""

import os
import json
import time
import gzip
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import urllib.request
import urllib.error

# ─── 配置 ───
ES_HOST = os.environ.get("ES_HOST", "http://localhost:9200")
INDEX_PREFIX = os.environ.get("ES_INDEX", "logs")
LOG_PATH = os.environ.get("LOG_PATH", "/var/log/nginx/access.log")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100"))
FLUSH_INTERVAL = float(os.environ.get("FLUSH_INTERVAL", "5"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("log-collector")


class ElasticsearchClient:
    """轻量 ES 客户端，封装常用 API"""

    def __init__(self, host: str):
        self.host = host.rstrip("/")

    def health(self) -> Dict[str, Any]:
        with urllib.request.urlopen(f"{self.host}/_cluster/health", timeout=10) as resp:
            return json.loads(resp.read())

    def index(self, index: str, doc: dict) -> bool:
        url = f"{self.host}/{index}/_doc"
        data = json.dumps(doc).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read())
                return body.get("result") in ("created", "updated")
        except urllib.error.HTTPError as e:
            log.error(f"ES index error: {e.code} {e.reason}")
            return False

    def bulk_index(self, index: str, docs: list[dict]) -> int:
        """_bulk API 批量写入"""
        if not docs:
            return 0
        body = ""
        for doc in docs:
            body += json.dumps({"index": {"_index": index}}) + "\n"
            body += json.dumps(doc) + "\n"
        url = f"{self.host}/_bulk"
        req = urllib.request.Request(url, data=body.encode("utf-8"), headers={"Content-Type": "application/x-ndjson"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                errors = result.get("errors", False)
                if errors:
                    failed = [i for i, item in enumerate(result.get("items", [])) if item.get("index", {}).get("error")]
                    log.warning(f"bulk: {len(failed)}/{len(docs)} failed")
                return len(docs) - len(failed) if errors else len(docs)
        except urllib.error.HTTPError as e:
            log.error(f"bulk error: {e.code}")
            return 0


def parse_nginx_log(line: str) -> Optional[dict]:
    """解析 Nginx combined log 格式"""
    import re
    pattern = r'^(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"(\S+)\s+(\S+)\s+\S+"\s+(\d+)\s+(\d+)\s+"([^"]*)"\s+"([^"]*)"'
    m = re.match(pattern, line)
    if not m:
        return None
    return {
        "clientip": m.group(1),
        "timestamp": m.group(2),
        "verb": m.group(3),
        "request": m.group(4),
        "response": int(m.group(5)),
        "bytes": int(m.group(6)),
        "referer": m.group(7),
        "agent": m.group(8),
        "@timestamp": datetime.now(timezone.utc).isoformat(),
    }


def follow_file(path: str, batch_size: int = 100, flush_interval: float = 5.0):
    """tail -F 模式：读取新行并写入 ES"""
    es = ElasticsearchClient(ES_HOST)
    index = f"{INDEX_PREFIX}-{datetime.now():%Y.%m.%d}"
    batch = []
    last_flush = time.time()

    # 检查 ES 健康
    health = es.health()
    log.info(f"ES status: {health.get('status')}")

    with open(path, "r") as f:
        f.seek(0, 2)  # 移到文件末尾
        log.info(f"following {path} ...")
        while True:
            line = f.readline()
            if not line:
                if batch and (time.time() - last_flush > flush_interval):
                    n = es.bulk_index(index, batch)
                    log.info(f"flushed {n} docs")
                    batch = []
                    last_flush = time.time()
                time.sleep(0.1)
                continue
            doc = parse_nginx_log(line.strip())
            if doc:
                batch.append(doc)
            if len(batch) >= batch_size:
                n = es.bulk_index(index, batch)
                log.info(f"flushed {n} docs")
                batch = []
                last_flush = time.time()


def read_existing(path: str) -> list[dict]:
    """读取已有日志文件（全量导入）"""
    docs = []
    open_func = gzip.open if path.endswith(".gz") else open
    mode = "rt" if path.endswith(".gz") else "r"
    with open_func(path, mode) as f:
        for line in f:
            doc = parse_nginx_log(line.strip())
            if doc:
                docs.append(doc)
    log.info(f"parsed {len(docs)} docs from {path}")
    return docs


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Day 176 — ELK 日志采集")
    parser.add_argument("--follow", action="store_true", help="tail -F 模式")
    parser.add_argument("--input", default=LOG_PATH, help="日志文件路径")
    parser.add_argument("--count", type=int, default=0, help="生成 N 条测试日志")
    parser.add_argument("--output", default=None, help="输出到文件（测试用）")
    args = parser.parse_args()

    if args.count > 0:
        # 生成测试日志
        import random
        methods = ["GET", "POST", "PUT", "DELETE"]
        paths = ["/api/users", "/api/login", "/api/data", "/health", "/metrics"]
        statuses = [200, 200, 200, 200, 301, 404, 500]
        lines = []
        for _ in range(args.count):
            ip = f"192.168.1.{random.randint(1,254)}"
            ts = datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
            m = random.choice(methods)
            p = random.choice(paths)
            s = random.choice(statuses)
            b = random.randint(100, 5000)
            lines.append(f'{ip} - - [{ts}] "{m} {p} HTTP/1.1" {s} {b} "-" "Mozilla/5.0"')
        if args.output:
            with open(args.output, "w") as f:
                f.write("\n".join(lines) + "\n")
            log.info(f"wrote {args.count} lines to {args.output}")
        else:
            for line in lines:
                print(line)
        return

    if args.follow:
        follow_file(args.input, BATCH_SIZE, FLUSH_INTERVAL)
    else:
        docs = read_existing(args.input)
        es = ElasticsearchClient(ES_HOST)
        n = es.bulk_index(f"{INDEX_PREFIX}-{datetime.now():%Y.%m.%d}", docs)
        log.info(f"indexed {n} docs")


if __name__ == "__main__":
    main()
