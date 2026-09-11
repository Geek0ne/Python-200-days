#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 153 · 示例 03：自动化端口扫描器（实战案例 / 多线程 + 结果导出）
================================================================================

⚠️ 授权声明
--------------------------------------------------------------------------------
本脚本默认目标 `127.0.0.1`，并且**内置硬性护栏**：
只要目标不是本机回环地址/本机名，脚本就会打印警告并要求显式加
`--i-own-this-target` 才会继续。加这个参数等于你在声明：
「我确认该资产属于我，或我已取得书面授权，且我了解当地法律。」

这不是形式主义。真实的渗透测试项目里，**授权书（Scope/ROE）**是第一步，
扫描范围、时间窗、允许的技术手段都写在里面。越界扫描 = 违法。

本脚本面向**安全防御与教学**：它的价值在于让你快速看清自己的机器/服务器
上"到底有哪些门开着、门后面是谁"，从而去关掉不该开的服务。

--------------------------------------------------------------------------------
功能
--------------------------------------------------------------------------------
  1. 多线程 TCP connect 扫描（ThreadPoolExecutor + 限流）
  2. 端口范围解析：`top`（内置常用表）/ `1-1024` / `22,80,443` / 混合 `22,8000-8100`
  3. banner 抓取 + 服务指纹识别（HTTP / SSH / SMTP / FTP / Redis / MySQL 等）
  4. 记录每个端口的状态（open/closed/filtered）与耗时
  5. 结果导出三种格式：JSON（给程序）/ CSV（给表格）/ Markdown（给人看）
  6. 启动本机演示服务，保证 `python3 03-auto-port-scanner.py` 一定有结果可看

运行
--------------------------------------------------------------------------------
    # 最简：扫本机内置常用端口 + 演示服务
    python3 03-auto-port-scanner.py

    # 指定端口范围
    python3 03-auto-port-scanner.py --ports 1-1024 --workers 128 --timeout 0.5

    # 导出到指定目录
    python3 03-auto-port-scanner.py --ports top --out-dir ./scan-output

只依赖标准库。
"""

from __future__ import annotations

import argparse
import csv
import http.server
import json
import os
import re
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass

# ══════════════════════════════════════════════════════════════════════════
# 配置常量
# ══════════════════════════════════════════════════════════════════════════

LOCAL_TARGETS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

# 内置常用端口表（`--ports top` 使用）。
# 为什么是这些端口？它们覆盖了：绝大多数 Web 服务、最常见的数据库、
# 最常被攻击者惦记的管理端口（RDP/Redis/MongoDB/Elasticsearch）。
TOP_PORTS: list[int] = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139,
    143, 161, 389, 443, 445, 465, 514, 587, 631, 636,
    873, 993, 995, 1080, 1433, 1521, 2049, 2181, 2375, 3000,
    3306, 3389, 5000, 5432, 5601, 5900, 5984, 6379, 7001, 8000,
    8080, 8081, 8443, 8888, 9000, 9090, 9200, 9300, 10000, 11211,
    27017, 50000,
]

# 服务名映射：socket.getservbyport() 在有些系统上依赖 /etc/services，
# 缺失或不准确时用这张表兜底（尤其是数据库/中间件的非标准端口）。
FALLBACK_SERVICES = {
    3306: "mysql", 5432: "postgresql", 6379: "redis", 27017: "mongodb",
    9200: "elasticsearch", 9300: "elasticsearch-node", 11211: "memcached",
    8080: "http-alt", 8443: "https-alt", 8888: "http-alt", 1433: "ms-sql-s",
    3389: "ms-wbt-server", 5000: "http-alt", 9000: "http-alt", 2181: "zookeeper",
    2375: "docker", 5601: "kibana", 5900: "vnc", 7001: "weblogic",
}

# 指纹规则：(服务名, 编译好的正则)。
# 【为什么要用 re.compile 预编译？】因为扫描 65535 个端口时，每条 banner 都要
# 对全部规则跑一遍；预编译只做一次正则解析，能省下可观的 CPU。
FINGERPRINTS: list[tuple[str, re.Pattern]] = [
    ("http",    re.compile(rb"^HTTP/\d\.\d \d{3}", re.MULTILINE)),
    ("ssh",     re.compile(rb"^SSH-\d\.\d-")),
    ("smtp",    re.compile(rb"^220[\s\S]*?(E?SMTP|Mail)", re.IGNORECASE)),
    ("ftp",     re.compile(rb"^220[\s\S]*?(FTP|ftp)", re.IGNORECASE)),
    ("pop3",    re.compile(rb"^\+OK")),
    ("imap",    re.compile(rb"^\* OK")),
    ("mysql",   re.compile(rb"mysql_native_password|\x00\x00\x00\x0a")),
    ("redis",   re.compile(rb"^\$?\d*\s*[-+]?(PONG|NOAUTH|ERR)")),
    ("mongodb", re.compile(rb"isdbgrid|MongoDB", re.IGNORECASE)),
    ("vnc",     re.compile(rb"^RFB \d{3}\.\d{3}")),
    ("rdp",     re.compile(rb"^\x03\x00\x00")),
    ("telnet",  re.compile(rb"^\xff[\xfb-\xfe]")),   # Telnet 协商字节以 0xFF 开头
]


# ══════════════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class PortResult:
    """单个端口的扫描结果。

    【为什么用 dataclass 而不是 dict？】
      · 字段名有类型提示，IDE 和静态检查能帮你抓拼写错误；
      · asdict() 直接转成 JSON 可序列化的 dict，导出链路干净；
      · 比裸 dict 多一层"这是结构化数据"的语义，后面接数据库、接报表都方便。
    """
    host: str
    port: int
    state: str                    # open / closed / filtered
    service: str = ""             # 探测到的服务名（指纹优先，其次 /etc/services）
    banner: str = ""              # 可读的 banner 首行（截断）
    latency_ms: float = 0.0       # 从发起到有结论的耗时
    error: str = ""               # 失败原因（便于排查）


# ══════════════════════════════════════════════════════════════════════════
# 端口解析
# ══════════════════════════════════════════════════════════════════════════

def parse_ports(spec: str) -> list[int]:
    """解析端口表达式，支持 `top` / `1-1024` / `22,80,443` / `22,8000-8100`。

    【为什么要支持混合写法？】真实扫描的需求往往是"全端口 + 重点端口加密扫"，
    一个表达式能表达清楚，比让用户写三次命令友好得多。

    【为什么要去重排序？】线程池的调度顺序会影响完成顺序，但输出和导出的
    稳定性要求"同样的输入得到同样的列表"。排序 + 去重是最省事的确定性保证。
    """
    if spec.strip().lower() in ("top", "common", "default"):
        return sorted(set(TOP_PORTS))

    ports: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            # ⚠️ 用 split("-", 1)：端口号里不可能有第二个负号，安全
            lo_s, hi_s = chunk.split("-", 1)
            try:
                lo, hi = int(lo_s), int(hi_s)
            except ValueError:
                raise ValueError(f"无法解析端口范围: {chunk!r}") from None
            if not (1 <= lo <= hi <= 65535):
                raise ValueError(f"端口范围非法（须 1<=lo<=hi<=65535）: {chunk!r}")
            ports.update(range(lo, hi + 1))
        else:
            try:
                p = int(chunk)
            except ValueError:
                raise ValueError(f"无法解析端口: {chunk!r}") from None
            if not (1 <= p <= 65535):
                raise ValueError(f"端口越界（1-65535）: {p}")
            ports.add(p)
    return sorted(ports)


def service_name(port: int) -> str:
    """查端口对应的服务名，先查系统 /etc/services，再查内置表。"""
    try:
        # getservbyport 需要网络字节序的端口号，所以要 htons 转换
        return socket.getservbyport(port, "tcp")
    except OSError:
        return FALLBACK_SERVICES.get(port, "")


# ══════════════════════════════════════════════════════════════════════════
# 探针与指纹
# ══════════════════════════════════════════════════════════════════════════

HTTP_HINT_PORTS = {80, 81, 443, 591, 8000, 8008, 8080, 8081, 8443, 8888, 9000, 9090, 10000}


def choose_probe(port: int) -> bytes | None:
    """按端口号挑一个"开场白"，没有把握就返回 None（只读）。

    【设计取舍】这里用**端口号 + /etc/services 是否认识它**做启发式，
    而不是"先只读、超时再补探针"。原因：两段式探测会把每个端口的耗时
    翻倍（未知端口永远要白等一个 timeout）。

    三级策略（从确定到猜测）：
      1. 在明确的 Web 端口清单里            → 发 HTTP 请求；
      2. 是 Redis 默认端口                  → 发 PING；
      3. **/etc/services 完全不认识的高位端口** → 猜它是 Web（现代服务
         跑在随机高位端口上很常见），仍发 HTTP 请求；
      4. 其余（22/25/143… 这类协议自己会先说话的）→ 只读。

    代价是可能给非 HTTP 端口发 HTTP 请求 —— 对大多数服务无害（它会把请求
    当成垃圾数据忽略或直接断开），拿到空 banner 也不影响"端口开放"的结论。
    真实工具（nmap -sV）会用探针库 + 响应聚类，精度高得多，但慢得多。
    """
    if port in HTTP_HINT_PORTS:
        return b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\nUser-Agent: day153-scanner/1.0\r\n\r\n"
    if port == 6379:
        return b"PING\r\n"          # Redis：发 PING 看是否回 +PONG / -NOAUTH
    if not service_name(port):       # 既不在常用清单，系统也不认识 → 猜 Web
        return b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\nUser-Agent: day153-scanner/1.0\r\n\r\n"
    return None                      # SMTP/SSH/FTP 等会主动打招呼，只读即可


def identify_service(raw_banner: bytes) -> str:
    """用指纹规则识别服务。命中返回服务名，否则返回空串。

    【为什么要基于"原始 bytes"做匹配？】因为字符串解码会引入信息损失
    （errors="replace" 会把二进制字节变成 U+FFFD，丢掉原始特征）。指纹库
    用 bytes 正则，表达能力最强。展示给人看时才解码。
    """
    for name, pattern in FINGERPRINTS:
        if pattern.search(raw_banner):
            return name
    return ""


# ══════════════════════════════════════════════════════════════════════════
# 核心：单端口扫描
# ══════════════════════════════════════════════════════════════════════════

def scan_one_port(host: str, port: int, timeout: float, want_banner: bool = True) -> PortResult:
    """扫描单个端口，返回 PortResult。**这个函数被线程池并发调用。**

    【线程安全性说明】本函数不读写任何共享可变状态，只依赖入参，因此可以在
    任意多个线程里同时跑 —— 这是并发代码最容易出错的地方，避开它的最简单
    办法就是**让工作函数保持纯函数**，结果通过返回值（future）收集。

    【三态判定逻辑】
        connect 成功                        → open，继续抓 banner
        connect_ex == ECONNREFUSED(111)     → closed（主机在，端口没监听）
        connect_ex == ETIMEDOUT(110)        → filtered（被丢弃/超时）
        其它错误                            → filtered，并记录错误码
    """
    started = time.perf_counter()
    result = PortResult(host=host, port=port, state="closed")

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            result.state = "open"
            result.service = service_name(port)

            if want_banner:
                probe = choose_probe(port)
                raw = b""
                if probe:
                    try:
                        sock.sendall(probe)
                    except OSError:
                        pass
                # 最多读 4 次，够覆盖绝大多数文本 banner；再读不到就放弃。
                # 【为什么要限次数而不是"读到超时"？】因为在 open 端口上
                # "读到超时"意味着每个端口都要白等一个完整的 timeout，
                # 65535 个端口乘以 1 秒就是灾难。用"读几次就停"把上限钉死。
                for _ in range(4):
                    try:
                        chunk = sock.recv(512)
                    except socket.timeout:
                        break
                    except (ConnectionResetError, OSError):
                        break
                    if not chunk:
                        break
                    raw += chunk
                    if b"\n" in chunk or len(raw) >= 1024:
                        break

                if raw:
                    guess = identify_service(raw)
                    if guess:
                        result.service = guess
                    # 展示用 banner：解码容错 + 只保留第一行 + 截断到 120 字符
                    first_line = raw.decode("utf-8", errors="replace").splitlines()[0]
                    result.banner = first_line.strip()[:120]

    except ConnectionRefusedError:
        result.state = "closed"
        result.error = "connection refused"
    except socket.timeout:
        result.state = "filtered"
        result.error = "timeout"
    except socket.gaierror as exc:
        result.state = "filtered"
        result.error = f"resolve error: {exc}"
    except OSError as exc:
        # 其它 errno（如 EHOSTUNREACH=113、ENETUNREACH=101）统一归为 filtered
        result.state = "filtered"
        result.error = f"errno={exc.errno}"

    result.latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return result


# ══════════════════════════════════════════════════════════════════════════
# 扫描调度器
# ══════════════════════════════════════════════════════════════════════════

def run_scan(host: str, ports: list[int], workers: int, timeout: float,
             show_closed: bool = False) -> tuple[list[PortResult], float]:
    """并发扫描一组端口，返回 (结果列表, 总耗时秒数)。

    【为什么用 ThreadPoolExecutor 而不是开 N 个 Thread？】
      1. 线程复用：线程池里的线程执行完一个任务就接下一个，没有反复创建销毁
         的开销（扫描几万个端口时这点很关键）；
      2. 背压：`max_workers` 天然限制了"同时在飞"的连接数，等于自动限流；
      3. 收结果方便：`as_completed` 让你**按完成顺序**拿到结果，可以边扫边打印，
         不用等全部结束（用户体验好很多）。
    【为什么不用 asyncio？】connect + recv 是阻塞 I/O；asyncio 版本需要
    loop.sock_connect 之类的 API，代码复杂度上升，而收益主要在更高并发。
    几千端口量级下，线程池完全够用，且更容易读。示例 04 之外没必要上 asyncio。
    """
    results: list[PortResult] = []
    done = 0
    total = len(ports)
    started = time.perf_counter()

    print(f"开始扫描 {host}，共 {total} 个端口，并发 {workers}，超时 {timeout}s")
    print("-" * 74)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(scan_one_port, host, p, timeout): p for p in ports}
        for fut in as_completed(futures):
            port = futures[fut]
            try:
                res = fut.result()
            except Exception as exc:  # 兜底：单个任务崩了不能带走整个扫描
                res = PortResult(host=host, port=port, state="filtered",
                                 error=f"worker crashed: {exc!r}")
            results.append(res)
            done += 1
            if res.state == "open":
                svc = res.service or "unknown"
                extra = f"  |  {res.banner}" if res.banner else ""
                print(f"  [{done:>5}/{total}] ✅ {port:>5}/tcp open   {svc}{extra}")
            elif show_closed:
                print(f"  [{done:>5}/{total}]    {port:>5}/tcp {res.state}")

    elapsed = time.perf_counter() - started
    results.sort(key=lambda r: r.port)     # 输出确定性：永远按端口升序
    return results, elapsed


# ══════════════════════════════════════════════════════════════════════════
# 结果导出
# ══════════════════════════════════════════════════════════════════════════

def export_json(results: list[PortResult], host: str, elapsed: float, path: str) -> None:
    """导出 JSON：给程序/CI 消费。

    【为什么要带 meta 段？】只导出端口列表的话，拿到文件的人不知道这份数据
    是什么时候、对谁、用什么参数产生的 —— 报告必须自带上下文（溯源）。
    """
    payload = {
        "meta": {
            "tool": "day153-auto-port-scanner",
            "host": host,
            "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(elapsed, 3),
            "total_ports": len(results),
            "open_ports": sum(1 for r in results if r.state == "open"),
        },
        "results": [asdict(r) for r in results],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def export_csv(results: list[PortResult], path: str) -> None:
    """导出 CSV：给 Excel / pandas 消费。

    【注意 newline=""】csv 模块要求以 `newline=""` 打开文件，否则在 Windows 上
    每行之间会多出一个空行（这是官方文档明确要求的写法）。
    """
    fields = ["host", "port", "state", "service", "latency_ms", "banner", "error"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


def export_markdown(results: list[PortResult], host: str, elapsed: float, path: str) -> None:
    """导出 Markdown 报告：给人看。

    【为什么要做 Markdown？】扫描的产出最终要"能读懂"。把开放端口排在最前、
    标注服务与 banner，一份报告 10 秒就能扫完 —— 这是安全自检的核心需求。
    """
    opens = [r for r in results if r.state == "open"]
    others = [r for r in results if r.state != "open"]

    lines: list[str] = []
    lines.append("# 端口扫描报告（Day 153 实战脚本）")
    lines.append("")
    lines.append(f"- **目标**: `{host}`")
    lines.append(f"- **扫描时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **端口总数**: {len(results)}")
    lines.append(f"- **开放端口**: {len(opens)}")
    lines.append(f"- **总耗时**: {elapsed:.2f} 秒")
    lines.append("")
    lines.append("> ⚠️ 本报告仅用于自有资产的防御性自检。请勿对未授权目标使用。")
    lines.append("")
    lines.append("## 开放端口")
    lines.append("")
    if opens:
        lines.append("| 端口 | 服务 | 耗时(ms) | Banner |")
        lines.append("|---|---|---|---|")
        for r in opens:
            banner = r.banner.replace("|", "\\|") if r.banner else ""
            lines.append(f"| {r.port}/tcp | {r.service or '-'} | {r.latency_ms} | {banner} |")
    else:
        lines.append("（无）")
    lines.append("")
    lines.append("## 关闭 / 过滤端口")
    lines.append("")
    lines.append("| 端口 | 状态 | 说明 |")
    lines.append("|---|---|---|")
    for r in others:
        lines.append(f"| {r.port}/tcp | {r.state} | {r.error or '-'} |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


# ══════════════════════════════════════════════════════════════════════════
# 本机演示服务（保证脚本一定扫得出东西）
# ══════════════════════════════════════════════════════════════════════════

class _QuietHTTPServer(http.server.ThreadingHTTPServer):
    """不把扫描器造成的连接重置噪声打到屏幕上的演示 HTTP 服务。

    扫描器常在建连后立刻 RST 断开；socketserver 默认会把整个 traceback 打到
    stderr，把扫描输出冲乱。演示服务只是靶子，靶子不会抱怨。
    """

    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        return None


class _DemoHTTPHandler(http.server.BaseHTTPRequestHandler):
    server_version = "day153-demo-http/1.0"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802
        body = b"day 153 demo\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        return None


class _GreeterServer(threading.Thread):
    """一个主动发 banner 的假 SMTP 服务，用来演示指纹识别。"""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(16)
        self.port = self._sock.getsockname()[1]
        self._stop = threading.Event()

    def run(self) -> None:
        self._sock.settimeout(0.3)
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                try:
                    conn.sendall(b"220 day153-demo ESMTP LearnPython ready\r\n")
                    time.sleep(0.05)
                except OSError:
                    pass

    def stop(self) -> None:
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass


def start_demo_services() -> tuple[list[tuple[int, str]], list]:
    """起两个本机演示服务，返回 ([(端口, 说明)], [需要清理的对象])。"""
    services: list[tuple[int, str]] = []
    cleanup: list = []

    http_srv = _QuietHTTPServer(("127.0.0.1", 0), _DemoHTTPHandler)
    threading.Thread(target=http_srv.serve_forever, daemon=True).start()
    services.append((http_srv.server_address[1], "演示 HTTP 服务"))
    cleanup.append(http_srv)

    greeter = _GreeterServer()
    greeter.start()
    services.append((greeter.port, "演示 SMTP(banner) 服务"))
    cleanup.append(greeter)

    return services, cleanup


# ══════════════════════════════════════════════════════════════════════════
# 命令行
# ══════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Day 153 实战：多线程端口扫描器（仅限自有资产/书面授权目标）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python3 03-auto-port-scanner.py
  python3 03-auto-port-scanner.py --ports 1-1024 --workers 128 --timeout 0.5
  python3 03-auto-port-scanner.py --ports 22,80,443,8000-8100 --show-closed
""",
    )
    # 默认值就是本机 —— 让"直接运行"永远安全
    p.add_argument("--target", default="127.0.0.1", help="目标（默认 127.0.0.1，非本机需额外授权声明）")
    p.add_argument("--ports", default="top", help="端口：top / 1-1024 / 22,80,443 / 混合")
    p.add_argument("--workers", type=int, default=64, help="并发线程数（默认 64，建议不超过 200）")
    p.add_argument("--timeout", type=float, default=0.6, help="单端口超时秒数（默认 0.6）")
    p.add_argument("--out-dir", default="./scan-output", help="结果输出目录")
    p.add_argument("--show-closed", action="store_true", help="同时打印关闭/过滤的端口")
    p.add_argument("--no-demo", action="store_true", help="不启动本机演示服务")
    p.add_argument("--i-own-this-target", action="store_true",
                   help="声明目标为自有/已授权资产（非本机目标时必须显式加上）")
    return p


def enforce_scope(args: argparse.Namespace) -> None:
    """授权护栏。非本机目标必须显式声明，否则退出。

    【为什么默认拒绝？】因为"默认允许 + 事后追责"在安全工具里是错误的默认值。
    这里的护栏很弱（一个 flag 就能过），但它的价值在于**强制用户做出一次
    明确的意思表示**，而不是手滑打了别人的 IP。
    """
    if args.target in LOCAL_TARGETS:
        return
    if not args.i_own_this_target:
        print(f"❌ 拒绝扫描 {args.target}：目标不是本机地址。")
        print("   本脚本只允许扫描 127.0.0.1 / localhost / ::1。")
        print("   若该资产确实属于你或你已获得**书面授权**，请加 --i-own-this-target")
        print("   重新运行，并确认授权书中的 IP 段与时间窗覆盖本次扫描。")
        sys.exit(2)
    print("⚠️  你声明了对该目标拥有授权。请确认：")
    print("    · 目标在授权书的扫描范围内；")
    print("    · 当前时间在授权的时间窗内；")
    print("    · 你使用的技术手段在授权允许的范围内。")
    print("   按 Ctrl+C 可立即中止，5 秒后继续……")
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\n已中止。")
        sys.exit(130)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    enforce_scope(args)

    if not (1 <= args.workers <= 500):
        print(f"❌ --workers 必须在 1~500 之间（当前 {args.workers}）")
        return 2
    if not (0.05 <= args.timeout <= 30):
        print(f"❌ --timeout 必须在 0.05~30 秒之间（当前 {args.timeout}）")
        return 2

    try:
        ports = parse_ports(args.ports)
    except ValueError as exc:
        print(f"❌ {exc}")
        return 2

    cleanup: list = []
    demo_ports: list[int] = []
    if not args.no_demo:
        services, cleanup = start_demo_services()
        print("已启动本机演示服务（保证扫描有结果）：")
        for port, desc in services:
            print(f"    {port:>5}/tcp  {desc}")
            demo_ports.append(port)
        # 把随机端口并进扫描列表 —— 这是演示脚本"结果永远非空"的关键
        ports = sorted(set(ports) | set(demo_ports))
        print()

    try:
        results, elapsed = run_scan(
            args.target, ports, workers=args.workers,
            timeout=args.timeout, show_closed=args.show_closed,
        )
    finally:
        for item in cleanup:
            if isinstance(item, _GreeterServer):
                item.stop()
            else:
                item.shutdown()
                item.server_close()

    # ── 统计 ──
    opens = [r for r in results if r.state == "open"]
    filtered = [r for r in results if r.state == "filtered"]
    closed = [r for r in results if r.state == "closed"]

    print("-" * 74)
    print(f"扫描完成：{len(results)} 个端口，耗时 {elapsed:.2f}s "
          f"（平均 {elapsed / max(len(results), 1) * 1000:.1f} ms/端口）")
    print(f"  open={len(opens)}  filtered={len(filtered)}  closed={len(closed)}")

    # ── 导出 ──
    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, "scan-result.json")
    csv_path = os.path.join(args.out_dir, "scan-result.csv")
    md_path = os.path.join(args.out_dir, "scan-report.md")
    export_json(results, args.target, elapsed, json_path)
    export_csv(results, csv_path)
    export_markdown(results, args.target, elapsed, md_path)

    print("已导出：")
    for p in (json_path, csv_path, md_path):
        print(f"  {p}  ({os.path.getsize(p)} 字节)")

    if opens:
        print("\n开放端口一览：")
        for r in opens:
            svc = r.service or "unknown"
            print(f"  {r.port:>5}/tcp  {svc:<16} {r.latency_ms:>7.2f} ms  {r.banner}")
    print("\n防御建议：")
    print("  · 只监听必要的端口；能绑 127.0.0.1 就绝不绑 0.0.0.0；")
    print("  · 用防火墙（安全组/nftables）做默认拒绝 + 白名单放行；")
    print("  · 数据库/Redis/MongoDB/Elasticsearch 绝不能暴露到公网；")
    print("  · 定期跑一次本脚本，对比历次结果，异常新增端口要立刻查证。")

    # 退出码设计：有 filtered（可能被防火墙丢弃）记 1，纯 open/closed 记 0。
    # 【为什么要设计退出码？】这样才能接进 CI / 定时任务做"配置漂移告警"。
    return 1 if filtered else 0


if __name__ == "__main__":
    sys.exit(main())
