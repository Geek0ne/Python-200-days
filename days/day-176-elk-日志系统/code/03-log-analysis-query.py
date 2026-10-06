#!/usr/bin/env python3
"""
Day 176 — ELK 日志系统
日志查询与聚合分析
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone


class LogAnalyzer:
    """日志分析器，封装 ELK 常用查询"""

    def __init__(self, host: str, index: str = "logs-*"):
        self.host = host.rstrip("/")
        self.index = index

    def _call(self, method: str, path: str, body=None) -> dict:
        url = f"{self.host}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        if method == "GET":
            req.get_method = lambda: "GET"
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"ES error {e.code}: {e.reason}")

    def search(self, query: dict, size: int = 100, sort=None) -> list:
        body = {"query": query, "size": size}
        if sort:
            body["sort"] = sort
        r = self._call("GET", f"/{self.index}/_search", body)
        return [hit["_source"] for hit in r["hits"].get("hits", [])], r["hits"]["total"]

    def search_match(self, field: str, value: str, size: int = 50):
        query = {"match": {field: value}}
        return self.search(query, size)

    def status_code_dist(self):
        """统计状态码分布"""
        body = {
            "size": 0,
            "aggs": {
                "status": {
                    "terms": {
                        "field": "response.keyword",
                        "size": 20
                    }
                }
            }
        }
        r = self._call("GET", f"/{self.index}/_search", body)
        buckets = r["aggregations"]["status"]["buckets"]
        return [(b["key"], b["doc_count"]) for b in buckets]

    def requests_per_minute(self, minutes: int = 30):
        """最近 N 分钟的请求量（时间直方图）"""
        body = {
            "size": 0,
            "aggs": {
                "rpm": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "calendar_interval": "minute",
                        "extended_time_zone": "Asia/Shanghai",
                        "format": "yyyy-MM-dd HH:mm"
                    }
                }
            }
        }
        r = self._call("GET", f"/{self.index}/_search", body)
        buckets = r["aggregations"]["rpm"]["buckets"]
        return [(b["key_as_string"], b["doc_count"]) for b in buckets]

    def find_errors(self, start_hours: int = 1, size: int = 50):
        """查最近 N 小时的 5xx 错误"""
        body = {
            "query": {
                "bool": {
                    "must": {
                        "range": {
                            "response": {"gte": 500, "lte": 599}
                        }
                    },
                    "filter": {
                        "range": {
                            "@timestamp": {
                                "gte": f"now-{start_hours}h",
                                "format": "strict_relative"
                            }
                        }
                    }
                }
            },
            "sort": [{"@timestamp": "desc"}],
            "size": size,
            "_source": ["clientip", "request", "response", "timestamp"]
        }
        return self.search(body["query"], size, sort=[{"@timestamp": "desc"}])

    def find_slow_requests(self, latency_ms: int = 1000):
        """查慢请求"""
        body = {
            "query": {
                "bool": {
                    "must": {"range": {"latency_ms": {"gte": latency_ms}}}
                }
            },
            "size": 30,
            "_source": ["clientip", "request", "latency_ms"]
        }
        return self.search(body["query"], 30, sort=[{"latency_ms": "desc"}])

    def requests_by_service(self, response: int = None, top_n: int = 10):
        """按服务分组的请求统计"""
        body = {
            "size": 0,
            "query": {"match": {"response": response}} if response else {"match_all": {}},
            "aggs": {
                "by_service": {
                    "terms": {"field": "service.keyword", "size": top_n}
                }
            }
        }
        r = self._call("GET", f"/{self.index}/_search", body)
        return [(b["key"], b["doc_count"]) for b in r["aggregations"]["by_service"]["buckets"]]


def print_results(title: str, results):
    print(f"\n=== {title} ===")
    if isinstance(results, dict):
        for k, v in results.items():
            print(f"  {k}: {v}")
    elif isinstance(results, list) and results and isinstance(results[0], (list, tuple)):
        for row in results:
            print(f"  {row[0]}: {row[1]}")
    elif isinstance(results, list):
        for item in results[:10]:
            print(f"  {json.dumps(item, ensure_ascii=False)}")
    else:
        print("  ", results)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Day 176 — 日志分析")
    parser.add_argument("--es", default="http://localhost:9200", help="Elasticsearch 地址")
    parser.add_argument("--index", default="logs-2026.10.06", help="索引名")
    parser.add_argument("--analyze", action="store_true", help="运行所有分析")
    parser.add_argument("--status", action="store_true", help="统计状态码分布")
    parser.add_argument("--rpm", action="store_true", help="每分钟请求数")
    parser.add_argument("--errors", type=int, default=1, help="查最近 N 小时 5xx")
    parser.add_argument("--service", action="store_true", help="按服务分组")
    args = parser.parse_args()

    analyzer = LogAnalyzer(args.es, args.index)

    if args.analyze or (not args.status and not args.rpm and not args.errors and not args.service):
        print(f"连接 ES: {args.es}")
        try:
            with urllib.request.urlopen(f"{args.es}/_cluster/health", timeout=10) as resp:
                print("  ES 健康:", json.loads(resp.read()).get("status"))
        except Exception as e:
            print(f"  ❌ ES 连接失败: {e}")
            print("  提示：先运行 01-elk-install-setup.py 部署单节点 ELK")
            return

    if args.status:
        print_results("状态码分布", analyzer.status_code_dist())
    if args.rpm:
        print_results("每分钟请求数（最近30分钟）", analyzer.requests_per_minute(30))
    if args.errors:
        rows = analyzer.find_errors(args.errors)
        print_results(f"最近{args.errors}小时 5xx 错误（共 {len(rows)} 条）", rows)
    if args.service:
        print_results("按服务分组请求统计", analyzer.requests_by_service())


if __name__ == "__main__":
    main()
