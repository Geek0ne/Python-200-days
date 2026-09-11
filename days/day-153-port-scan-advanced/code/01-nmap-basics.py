#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 153 · 示例 01：Nmap 基础命令与常用扫描类型（基础用法）
================================================================================

⚠️ 法律与道德声明 —— 请先读完这一段再用任何扫描工具
--------------------------------------------------------------------------------
本文件里所有示例的目标都被**硬编码为 127.0.0.1（本机回环地址）**。

端口扫描在绝大多数司法管辖区都被视为"对计算机系统的探测行为"：
  · 中国《刑法》第 285 条（非法侵入计算机信息系统罪 / 非法获取计算机信息
    系统数据罪）、第 286 条（破坏计算机信息系统罪）；
  · 美国 CFAA（18 U.S.C. § 1030）；
  · 英国 Computer Misuse Act 1990。
未经授权扫描他人资产，**哪怕只是发一个 SYN 包**，都可能构成违法。

✅ 允许的场景（白名单）：
  1. 你自己的机器 / 你自己的云主机；
  2. 你所在组织的资产，且**持有书面授权**（授权书需写明 IP 段 + 时间窗 + 联系人）；
  3. 专门的授权靶场（VulnHub / HackTheBox / 自建 DVWA 等）。

❌ 禁止的场景：任何"我想看看这个网站开了什么端口"的冲动。这不是技术问题，
   是法律问题。本系列面向**安全防御与教学**。

--------------------------------------------------------------------------------
本示例要教什么
--------------------------------------------------------------------------------
1. Nmap 的四种常用扫描类型：TCP connect / TCP SYN / UDP / 服务版本探测；
2. 端口选择（-p）与**时序模板（-T0~-T5）**的取舍；
3. 用 Python 调 Nmap 的**两种方式**：
     (a) subprocess 调命令行 + 解析 XML 输出（永远可用，最稳）；
     (b) python-nmap 库（封装好，但**可能没装**）；
4. 当上面两条路都走不通时，如何用**标准库 socket** 做一个 connect 扫描兜底。

运行
--------------------------------------------------------------------------------
    python3 01-nmap-basics.py

依赖
--------------------------------------------------------------------------------
    - Python 3.8+（只用了标准库）
    - 可选：系统里的 `nmap` 可执行文件（没有就走 socket 兜底，照样能跑完）
    - 可选：`pip install python-nmap`（没装会打印一行提示，不影响运行）

阅读顺序
--------------------------------------------------------------------------------
    ① 常量与安全检查        —— 先学"怎么不把自己玩进去"
    ② demo_scan_types()     —— 四种扫描类型的命令矩阵
    ③ NmapViaSubprocess     —— 用命令行 + XML 解析（推荐的生产做法）
    ④ demo_python_nmap()    —— python-nmap 的用法与优雅降级
    ⑤ connect_scan()        —— 纯 socket 兜底实现
    ⑥ main()                —— 起一个本机 HTTP 服务，把上面全部真实跑一遍
"""

from __future__ import annotations

import http.server
import shutil
import socket
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET

# ══════════════════════════════════════════════════════════════════════════
# ① 常量与安全检查
# ══════════════════════════════════════════════════════════════════════════

# 【为什么把目标写成常量？】
# 因为这是本系列最重要的一条纪律：目标必须是"显式写死的、你确认过属于自己
# 或已获授权的"地址。绝不能从命令行参数、环境变量、用户输入里动态取目标——
# 那会让一个教学脚本随时变成攻击工具。真要扫描别的资产，请手动改这一行，
# 并在心里过一遍"我有没有书面授权"。
TARGET = "127.0.0.1"

# 允许的"本地目标"集合。任何不在这个集合里的地址，脚本都会拒绝执行。
# 这是**纵深防御**里最便宜也最有效的一层：默认拒绝（deny by default）。
ALLOWED_LOCAL_TARGETS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

# 时序模板说明（这是 Nmap 里最容易"调错"的参数）
TIMING_TEMPLATES = {
    "T0": "paranoid  —— 每 5 分钟一个包，用于躲避 IDS，慢到无法接受",
    "T1": "sneaky    —— 每 15 秒一个包，同样用于躲避检测",
    "T2": "polite    —— 降低速率减少对目标的压力，适合脆弱的生产设备",
    "T3": "normal    —— **默认值**，绝大多数场景就用它",
    "T4": "aggressive—— 增加速率，局域网/自己机器上很舒服，可能丢包",
    "T5": "insane    —— 极快，会牺牲准确率，容易触发限速/封禁",
}

# 一个"小而准"的常用端口清单。为什么不用 nmap 默认的 top 1000？
# 因为扫描时间 ∝ 端口数 × 探测复杂度。教学和日常自检，40 个端口绰绰有余。
COMMON_PORTS = [
    21,      # FTP      —— 明文传输，现代系统应关闭或换成 SFTP
    22,      # SSH      —— 远程管理，注意别暴露公网
    23,      # Telnet   —— 明文，绝对不该开
    25,      # SMTP     —— 邮件传输
    53,      # DNS      —— 注意 UDP/TCP 都用
    80,      # HTTP
    110,     # POP3
    143,     # IMAP
    443,     # HTTPS
    445,     # SMB      —— 永恒之蓝（MS17-010）的入口，务必别暴露公网
    993,     # IMAPS
    995,     # POP3S
    1433,    # MSSQL
    1521,    # Oracle
    2049,    # NFS
    3000,    # 常见 Web 开发端口
    3306,    # MySQL    —— 默认只该监听 127.0.0.1
    3389,    # RDP      —— 爆破重灾区
    5000,    # Flask/开发服务
    5432,    # PostgreSQL
    5601,    # Kibana
    5900,    # VNC      —— 很多没密码
    6379,    # Redis    —— 未授权访问可写 SSH key / crontab
    7001,    # WebLogic
    8000,    # 常见 Web
    8080,    # HTTP 代理 / Tomcat
    8443,    # HTTPS 备用
    8888,    # Jupyter  —— 未授权等于拿到 shell
    9000,    # PHP-FPM / SonarQube
    9200,    # Elasticsearch —— 未授权可读全量数据
    9300,    # Elasticsearch 集群通信
    11211,   # Memcached
    27017,   # MongoDB  —— 未授权访问经典目标
]


def assert_target_is_allowed(target: str) -> None:
    """校验目标是否在允许清单内。不在就**直接退出**，不做任何"问问用户"的操作。

    【为什么用 assert 风格直接退出，而不是给个交互式确认？】
    因为交互式确认会被人用 `yes |` 之类的方式绕过；而代码里写死的白名单不会。
    安全功能的默认行为，应该是"没被显式允许 = 拒绝"。
    """
    if target not in ALLOWED_LOCAL_TARGETS:
        print(f"❌ 拒绝执行：目标 {target!r} 不在本地白名单内。")
        print("   本教学脚本只允许扫描本机。若你持有书面授权，请手动修改")
        print("   源码中的 TARGET 常量，并确认你已获得合法授权。")
        sys.exit(2)


def print_header(title: str) -> None:
    print("\n" + "═" * 72)
    print(f"  {title}")
    print("═" * 72)


# ══════════════════════════════════════════════════════════════════════════
# ② 本机演示服务：让扫描"真的能扫出东西"
# ══════════════════════════════════════════════════════════════════════════

class _QuietHTTPServer(http.server.ThreadingHTTPServer):
    """一个不会把扫描器造成的连接重置噪声打到屏幕上的 HTTP 服务。

    【为什么需要它？】扫描器（尤其是 nmap 的 connect 扫描）经常在建立连接后
    立刻发 RST 断开。socketserver 的默认行为是在 handle_error() 里把**整个
    traceback** 打到 stderr —— 于是一个正常的扫描会让屏幕刷满
    `ConnectionResetError: [Errno 104] Connection reset by peer`，
    把教学输出冲得没法看，读者还以为脚本跑挂了。
    演示服务只是靶子，靶子不该抱怨被打。
    """

    daemon_threads = True

    def handle_error(self, request, client_address) -> None:  # noqa: D102
        return None


class _QuietHandler(http.server.BaseHTTPRequestHandler):
    """一个安静的 HTTP 处理器。

    【为什么要自定义而不是直接用 SimpleHTTPRequestHandler？】
    两个原因：
      1. 默认 handler 会把每个请求打到 stderr，把扫描结果输出冲乱；
      2. 我们要**故意伪造一个 Server 头**，用来演示后面的"服务识别"：
         端口开着 ≠ 服务是什么，只有抓到 banner/指纹才能判断。
    """

    server_version = "LearnPythonDemoServer/1.0"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802 （http.server 规定的方法名）
        body = b"Day 153 demo server: it works.\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # 覆盖掉默认的日志输出
        return None


def start_local_demo_server() -> tuple[http.server.ThreadingHTTPServer, int]:
    """在本机随机端口起一个 HTTP 服务，作为扫描目标。

    返回 (server 对象, 端口号)。端口用 0 表示"让操作系统挑一个空闲端口"，
    这样脚本永远不会因为"端口被占用"而失败——这是写演示脚本的实用技巧。
    """
    server = _QuietHTTPServer((TARGET, 0), _QuietHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


# ══════════════════════════════════════════════════════════════════════════
# ③ 扫描类型知识矩阵（先懂"为什么"，再动手）
# ══════════════════════════════════════════════════════════════════════════

def demo_scan_types(extra_port: int) -> None:
    """打印四种常用扫描类型的命令、原理与取舍，并真跑一遍（若装了 nmap）。"""
    print_header("③ 四种常用扫描类型：命令 / 原理 / 取舍")

    print("""
┌────────────┬──────────────────────────────┬────────────────┬──────────────┐
│ 扫描类型    │ 底层机制                      │ 需要 root?      │ 特点          │
├────────────┼──────────────────────────────┼────────────────┼──────────────┤
│ TCP connect│ 调 connect()，完成三次握手     │ 否             │ 最兼容、最慢  │
│ （-sT）     │ 被扫描方日志里**留下记录**      │                │ 任何用户可跑  │
├────────────┼──────────────────────────────┼────────────────┼──────────────┤
│ TCP SYN     │ 只发 SYN，收到 SYN/ACK 就发 RST│ **是**         │ 快、隐蔽      │
│ （-sS）     │ 半开扫描，很少被应用层记录      │ （需原始套接字）│ 默认扫描方式  │
├────────────┼──────────────────────────────┼────────────────┼──────────────┤
│ UDP（-sU）  │ 发空 UDP 包，看是否回 ICMP     │ 多数需 root     │ **极慢极不可靠**│
│             │ port unreachable               │                │ 但 DNS/SNMP 必需│
├────────────┼──────────────────────────────┼────────────────┼──────────────┤
│ 版本探测     │ 抓 banner + 发探针做指纹匹配   │ 否（配合 -sT）  │ 慢，但信息最全 │
│ （-sV）     │ 匹配 nmap-service-probes 规则   │                │ 服务识别关键   │
└────────────┴──────────────────────────────┴────────────────┴──────────────┘

【为什么 SYN 扫描比 connect 扫描"隐蔽"？】
因为 connect 扫描走的是完整的操作系统 TCP 栈：三次握手**完成**了，应用层
（比如 nginx、sshd）会正常 accept 连接、写自己的访问日志，甚至可能被
fail2ban、WAF 记下来。而 SYN 扫描在握手"第三步"之前就发 RST 掐断，
连接从未进入 ESTABLISHED 状态，应用层的 accept() 不会返回，日志里通常
什么也看不到。这就是"半开（half-open）"名字的由来。

【为什么 UDP 扫描这么难？】
因为 UDP 是无连接协议，没有握手可以判断。目标端口关闭时通常回一个
ICMP port unreachable；但目标端口**开着**时，服务可能什么都不回
（合法的"沉默"）。于是扫描器只能靠"超时"来猜，而超时和丢包长得一模一样。
再加上大多数系统默认对 ICMP 限速（Linux 的 net.ipv4.icmp_ratelimit），
UDP 扫描的误报/漏报率天然很高。-sU 建议只扫你真正关心的少数端口。
""")

    print("  时序模板（-T）—— 速率与「被发现的概率」的权衡：")
    for key, desc in TIMING_TEMPLATES.items():
        print(f"    -{key}: {desc}")

    print(f"""
  【为什么默认是 T3 而不是 T5？】
  T5 把超时压到 0.3 秒、并发拉到最大。在真实网络里这会：
    · 大量丢包 → 把"开着的端口"误报成"关闭"（漏报）；
    · 触发目标防火墙的 SYN Flood 防护 → 你的 IP 被拉黑，后续全错；
    · 打满目标链路 → 影响业务（在授权的生产环境里这是事故）。
  正确姿势是：**先 T3 摸清情况，再针对性加速**，而不是一上来就 T5。
""")

    # ── 给出等价命令行（仅打印，不自动执行，方便你手动对照）──
    print("  等价命令行（本机演示，端口 %d 是脚本刚起的 HTTP 服务）：" % extra_port)
    cmds = [
        f"nmap -sT -p {extra_port} -T3 {TARGET}          # connect 扫描单个端口",
        f"nmap -sS -p {extra_port} -T3 {TARGET}          # SYN 半开扫描（需 root）",
        f"nmap -sT -sV -p {extra_port} -T3 {TARGET}      # 带版本探测",
        f"nmap -sT -p 1-1000 -T4 {TARGET}                # 扫 1~1000 端口",
        f"nmap -sT -p- -T4 {TARGET}                       # 全端口（-p- 即 1-65535）",
        f"nmap -Pn -sT -p 53 -sU -T3 {TARGET}            # UDP 探测（-Pn 跳过主机存活检查）",
        f"nmap -sT -p {extra_port} -oX - {TARGET}         # 输出 XML 到 stdout（好解析）",
    ]
    for c in cmds:
        print("    " + c)


# ══════════════════════════════════════════════════════════════════════════
# ④ 方式 A：subprocess 调 nmap 命令行 + 解析 XML（推荐的生产做法）
# ══════════════════════════════════════════════════════════════════════════

def nmap_available() -> bool:
    """检查系统里有没有 nmap 可执行文件。

    【为什么用 shutil.which 而不是 try: subprocess.run("nmap")？】
    which 只查 PATH，零副作用；直接运行会真的启动一个进程（慢，且可能因为
    版本不兼容打印一堆东西）。判断"工具在不在"，就用最轻的办法。
    跨平台（Linux/macOS 用 which，Windows 用 where）由 shutil 内部处理。
    """
    return shutil.which("nmap") is not None


def nmap_version() -> str:
    """取 nmap 版本号，失败时返回 '未知'。"""
    try:
        out = subprocess.run(
            ["nmap", "--version"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        # --version 的第一行长这样：Nmap version 7.94 ( https://nmap.org )
        first = out.stdout.splitlines()[0] if out.stdout else ""
        return first.strip() or "未知"
    except (OSError, subprocess.SubprocessError, IndexError):
        return "未知"


def nmap_via_subprocess(target: str, ports: list[int], do_version: bool = True) -> list[dict]:
    """用 subprocess 调 nmap，并解析 `-oX -`（XML 输出到标准输出）的结果。

    【为什么推荐 XML 而不是解析人类可读输出？】
    Nmap 的普通输出是给人看的，列宽、换行、警告语都会变，用正则解析极其脆弱
    （换个版本就崩）。XML（`-oX -`）是官方稳定接口，有结构、有明确字段名，
    xml.etree 十行代码就能拿全。**能被机器解析的接口，才是好接口。**
    """
    port_arg = ",".join(str(p) for p in ports)
    cmd = ["nmap", "-sT", "-Pn", "-T3", "-p", port_arg]
    if do_version:
        cmd.append("-sV")
    cmd += ["-oX", "-", target]

    print(f"    $ {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180, check=False,
        )
    except subprocess.TimeoutExpired:
        print("    ⚠️ nmap 超时（180 秒），已放弃")
        return []
    except OSError as exc:
        print(f"    ⚠️ 无法执行 nmap: {exc}")
        return []

    if not proc.stdout.strip():
        print(f"    ⚠️ nmap 没有输出。stderr: {proc.stderr.strip()[:200]}")
        return []

    return parse_nmap_xml(proc.stdout)


def parse_nmap_xml(xml_text: str) -> list[dict]:
    """把 nmap 的 XML 输出解析成 [{port, state, service, product, version}, ...]。

    XML 的层级结构（简化）：
        <nmaprun>
          <host>
            <ports>
              <port protocol="tcp" portid="80">
                <state state="open"/>
                <service name="http" product="nginx" version="1.18.0"/>
              </port>
            </ports>
          </host>
        </nmaprun>

    【为什么要把 xmlns 剥掉？】
    nmap 的 XML 带默认命名空间，ElementTree 里标签会变成
    '{http://nmap.org/nmap}port' 这种带花括号的丑样子。用字符串替换剥掉
    xmlns 声明，标签就恢复干净，查找逻辑简单十倍。这是处理第三方 XML 的
    常用小技巧（前提：确认文档里没有多命名空间混用）。
    """
    cleaned = xml_text.replace('xmlns="http://nmap.org/nmap"', "")
    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        print(f"    ⚠️ XML 解析失败: {exc}")
        return []

    results: list[dict] = []
    for port_el in root.iter("port"):
        state_el = port_el.find("state")
        svc_el = port_el.find("service")
        results.append({
            "port": int(port_el.get("portid", "0")),
            "protocol": port_el.get("protocol", "tcp"),
            "state": (state_el.get("state") if state_el is not None else "unknown"),
            "service": (svc_el.get("name") if svc_el is not None else "") or "",
            "product": (svc_el.get("product") if svc_el is not None else "") or "",
            "version": (svc_el.get("version") if svc_el is not None else "") or "",
        })
    return results


# ══════════════════════════════════════════════════════════════════════════
# ⑤ 方式 B：python-nmap 库（并演示"没装怎么办"）
# ══════════════════════════════════════════════════════════════════════════

try:
    import nmap as _python_nmap  # type: ignore  # pip install python-nmap
    HAS_PYTHON_NMAP = True
except ImportError:
    _python_nmap = None
    HAS_PYTHON_NMAP = False


def demo_python_nmap(target: str, ports: list[int]) -> None:
    """演示 python-nmap 的三个核心 API：PortScanner / scan() / 结果结构。

    【关于优雅降级】
    python-nmap 是一个**第三方库**，很多环境（尤其是干净容器、CI）里没有。
    生产脚本里对可选的第三方依赖，正确做法是：
        try import → 成功就用
        ImportError → 打印一行"怎么装"的提示，然后**走标准库兜底路径**，
                     绝不让整个脚本崩掉。
    这就叫"优雅降级（graceful degradation）"。下面两个分支都会真实执行。
    """
    port_arg = ",".join(str(p) for p in ports)

    if not HAS_PYTHON_NMAP:
        print("    ⚠️ 未检测到 python-nmap，已自动降级到 socket 兜底方案。")
        print("       安装方法：pip install python-nmap")
        print()
        print("       ── 装上之后，下面这段就会真正执行（Python-nmap 用法速查）──")
        print("""
         import nmap
         nm = nmap.PortScanner()

         # scan() 的参数和 nmap 命令行一一对应：
         #   hosts     → 目标（就是命令行的位置参数）
         #   ports     → 等价 -p
         #   arguments → 等价"其余所有参数"的字符串，如 '-sS -sV -T4'
         nm.scan(hosts='127.0.0.1', ports='22,80,443', arguments='-sT -sV -T3')

         nm.all_hosts()                      # ['127.0.0.1']  扫描到的主机列表
         nm['127.0.0.1'].state()             # 'up' / 'down'
         nm['127.0.0.1'].all_protocols()     # ['tcp']
         nm['127.0.0.1']['tcp'].keys()       # dict_keys([22, 80, 443]) 端口号
         nm['127.0.0.1']['tcp'][80]          # {'state':'open','name':'http',
                                             #  'product':'nginx','version':'1.18.0'}
         # 一行式：拿了就跑
         for host in nm.all_hosts():
             for proto in nm[host].all_protocols():
                 for p in nm[host][proto]:
                     info = nm[host][proto][p]
                     if info['state'] == 'open':
                         print(host, p, info['name'], info.get('product',''))

         # 如果你想跑 NSE 脚本（-sC / --script）：
         nm.scan('127.0.0.1', arguments='-sT -sC -p 22,80')
         nm['127.0.0.1']['tcp'][80].get('script', {})   # {'http-title': '...'}
        """)
        return

    # ── 真的装了 python-nmap，走真实调用 ──
    print(f"    ✅ python-nmap {getattr(_python_nmap, '__version__', '')} 已就绪，执行真实扫描")
    scanner = _python_nmap.PortScanner()
    # arguments 里不要重复写 -p，ports 参数会自己转成 -p
    scanner.scan(hosts=target, ports=port_arg, arguments="-sT -Pn -sV -T3")
    print(f"    扫描命令（python-nmap 实际拼出来的）: {scanner.command_line()}")

    for host in scanner.all_hosts():
        print(f"    主机 {host} 状态: {scanner[host].state()}")
        for proto in scanner[host].all_protocols():
            print(f"      协议 {proto}:")
            for port in sorted(scanner[host][proto].keys()):
                info = scanner[host][proto][port]
                if info["state"] != "open":
                    continue
                name = info.get("name", "")
                product = info.get("product", "")
                version = info.get("version", "")
                print(f"        端口 {port:<6} {info['state']:<6} {name} {product} {version}".rstrip())


# ══════════════════════════════════════════════════════════════════════════
# ⑥ 方式 C：纯标准库 socket 兜底（不需要 nmap，不需要 root）
# ══════════════════════════════════════════════════════════════════════════

def connect_scan(target: str, ports: list[int], timeout: float = 0.35) -> list[int]:
    """用 socket.connect_ex() 做 TCP connect 扫描，返回开放端口列表。

    【为什么用 connect_ex 而不是 connect？】
    connect() 失败会抛异常。扫描 100 个端口就要 try/except 100 次，
    又慢又难看。connect_ex() 在失败时**返回错误码**而不是抛异常：
        0        → 连接成功 → 端口开放
        111      → Connection refused (ECONNREFUSED) → 端口关闭
        110/101  → 超时 / 网络不可达 → 被防火墙 DROP（大概没开）
    这是"用返回值代替异常"的经典 API 设计，扫描场景下效率高得多。

    【超时为什么要设得这么小？】
    每个端口最长等 timeout 秒。扫描 1000 个端口、timeout=1 秒，最坏情况
    串行要 1000 秒。真实扫描器必须用并发（示例 03 会讲），这里先用小超时
    把串行版本的代价压下来。0.35 秒对**本机**足够（回环地址延迟 < 0.1ms）。
    """
    open_ports: list[int] = []
    for port in ports:
        # AF_INET + SOCK_STREAM = TCP/IPv4
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            # connect_ex 返回 errno；0 表示成功。这里**不抛异常**，很好循环。
            if sock.connect_ex((target, port)) == 0:
                open_ports.append(port)
    return open_ports


# ══════════════════════════════════════════════════════════════════════════
# ⑦ 主流程
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    assert_target_is_allowed(TARGET)

    print(f"目标（硬编码，仅本机）: {TARGET}")
    print(f"Python: {sys.version.split()[0]}")

    server, demo_port = start_local_demo_server()
    print(f"已在本机启动演示服务: http://{TARGET}:{demo_port}/")

    try:
        # ── ③ 知识矩阵 + 等价命令 ──
        demo_scan_types(demo_port)

        # 扫描列表 = 我们的演示端口 + 几个很可能开着的常见端口
        scan_ports = sorted(set([demo_port] + [22, 80, 443, 3306, 6379, 8080]))

        # ── ④ 方式 A：subprocess + XML ──
        print_header("④ 方式 A：subprocess 调 nmap + 解析 XML")
        if nmap_available():
            print(f"检测到 nmap: {nmap_version()}")
            rows = nmap_via_subprocess(TARGET, scan_ports, do_version=True)
            if rows:
                print("    解析结果：")
                for r in rows:
                    svc = " ".join(x for x in (r["service"], r["product"], r["version"]) if x)
                    print(f"      {r['state']:<8} {r['port']:<6}/tcp  {svc}")
            else:
                print("    （没有解析到任何端口记录）")
        else:
            print("未检测到 nmap 可执行文件，跳过方式 A。")
            print("安装：Debian/Ubuntu → sudo apt install nmap；macOS → brew install nmap")

        # ── ⑤ 方式 B：python-nmap ──
        print_header("⑤ 方式 B：python-nmap（含未安装时的优雅降级）")
        demo_python_nmap(TARGET, scan_ports)

        # ── ⑥ 方式 C：socket 兜底 ──
        print_header("⑥ 方式 C：纯 socket connect 扫描（兜底，永远可用）")
        found = connect_scan(TARGET, COMMON_PORTS, timeout=0.35)
        print(f"    扫描了 {len(COMMON_PORTS)} 个常用端口，开放的有 {len(found)} 个：")
        for p in found:
            print(f"      {p}/tcp  open")
        if not found:
            print("      （无）—— 注意本机演示服务在随机端口上，可能不在上面的清单里")

        # 单独验证一下演示端口（确保演示结果非空，教学更直观）
        demo_found = connect_scan(TARGET, [demo_port], timeout=0.5)
        print(f"    验证演示端口 {demo_port}: {'open ✅' if demo_found else '未开放 ❌'}")

    finally:
        # 【为什么放在 finally 里？】
        # 演示服务是 daemon 线程，进程退出会一起死；但显式 shutdown 是
        # 更好的习惯——释放端口、让日志干净、给读者一个"资源要收尾"的示范。
        server.shutdown()
        server.server_close()

    print_header("小结")
    print("""
• Nmap 四种扫描类型：connect（兼容）/ SYN（快、隐蔽，需 root）/ UDP（慢、不可靠）/
  版本探测（信息最全，也最慢）。默认用 -sT + -T3 起步，别一上来就 -T5。
• 端口选择用 -p，范围写 1-1000，全端口写 -p-（扫描时间会显著增加）。
• 调 nmap 的三种方式，按可靠性排序：
    1) subprocess + `-oX -` 解析 XML（永远可用，机器可读，推荐生产）
    2) python-nmap（API 舒服，但是第三方依赖，必须优雅降级）
    3) 纯 socket connect 扫描（无依赖、无需 root，但功能最弱）
• "端口开着"只是最粗的一层信息。要知道背后是什么服务，需要 banner 抓取
  与指纹识别 —— 那是示例 02 的主题。
• 全程只扫本机。这不是胆子小，这是专业。
""")


if __name__ == "__main__":
    main()
