#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 153 · 示例 02：Banner 抓取与服务识别的 8 个坑（进阶 / 避坑）
================================================================================

⚠️ 目标声明：本文件所有网络操作**只连接 127.0.0.1**，而且连接的是脚本自己
   在本机临时启动的演示服务。没有对外部任何地址发起连接。

--------------------------------------------------------------------------------
为什么"抓 banner"比"扫端口"难
--------------------------------------------------------------------------------
端口扫描只回答一个问题：**这个门开着吗？**
Banner 抓取要回答：**门后面是谁？**

难点在于"服务"的行为千差万别：
  · 有的服务连上就主动打招呼（SMTP: `220 mail.example.com ESMTP`）；
  · 有的服务**必须你先开口**它才回话（HTTP：你不发请求它就一直等）；
  · 有的服务连上就沉默，等你先发开场的"问候语"（如 Redis 的 `PING`、
    MySQL 的握手反而又是服务端先发）；
  · 有的服务收到不认识的字节直接断线。

所以"抓 banner"本质上是：**在正确的时机、用正确的探针、在正确的时间预算内，
读到一个或一段特征字符串，再拿它去比对指纹库。**

本示例会先在本机起三类"性格不同"的服务，然后用代码把 8 个最常见的坑
一个个踩给你看，并给出修复写法。

运行
--------------------------------------------------------------------------------
    python3 02-banner-grab-pitfalls.py

只依赖标准库。所有演示都在本机完成，秒级返回。
"""

from __future__ import annotations

import argparse
import http.server
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

TARGET = "127.0.0.1"          # 硬编码：只扫本机
LISTEN_HOST = "127.0.0.1"     # 演示服务也只绑定回环地址，绝不监听 0.0.0.0

DEFAULT_TIMEOUT = 1.0         # 单次读写的超时预算
MAX_BANNER_BYTES = 4096       # 单个 banner 最多读多少字节（防内存放大）


def print_header(title: str) -> None:
    print("\n" + "═" * 74)
    print(f"  {title}")
    print("═" * 74)


# ══════════════════════════════════════════════════════════════════════════
# ① 三个"性格不同"的演示服务
# ══════════════════════════════════════════════════════════════════════════

class ChatterboxServer(threading.Thread):
    """【性格 A：话痨】连上就主动发 banner —— 模拟 SMTP / FTP / SSH。

    SSH 会发 `SSH-2.0-OpenSSH_8.9p1`，SMTP 会发 `220 ... ESMTP ...`，
    FTP 会发 `220 ... FTP server ready`。这类服务最好抓：connect 后直接 read。
    """

    GREETING = b"220 day153-demo ESMTP LearnPython Demo Server ready\r\n"

    def __init__(self, port: int = 0) -> None:
        super().__init__(daemon=True)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # SO_REUSEADDR：避免 TIME_WAIT 期间端口无法立即重用，反复调试必备
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((LISTEN_HOST, port))
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
                    conn.sendall(self.GREETING)   # 主动开口
                    time.sleep(0.05)
                except OSError:
                    pass

    def stop(self) -> None:
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass


class MuteServer(threading.Thread):
    """【性格 B：哑巴】accept 后什么都不发，也什么都不回 —— 模拟"沉默端口"。

    真实世界里很多服务是这样：等你先说话，或者干脆挂在那里不响应。
    这正是"没设超时就会永久卡死"的现场。
    """

    def __init__(self, port: int = 0) -> None:
        super().__init__(daemon=True)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((LISTEN_HOST, port))
        self._sock.listen(16)
        self.port = self._sock.getsockname()[1]
        self._keepalive: list[socket.socket] = []
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
            # 故意不关闭：让客户端一直"等"着，制造超时场景
            self._keepalive.append(conn)

    def stop(self) -> None:
        self._stop.set()
        for c in self._keepalive:
            try:
                c.close()
            except OSError:
                pass
        try:
            self._sock.close()
        except OSError:
            pass


class _ProbeHTTPHandler(http.server.BaseHTTPRequestHandler):
    """【性格 C：要你先开口】只有在收到请求行之后才回响应。"""

    server_version = "day153-probe-http/2.1"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802
        body = b"ok\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("X-Demo", "day-153")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        return None


def start_probe_http(port: int = 0) -> tuple[http.server.ThreadingHTTPServer, int]:
    """起一个"必须发请求才响应"的 HTTP 服务。"""
    server = http.server.ThreadingHTTPServer((LISTEN_HOST, port), _ProbeHTTPHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


# ══════════════════════════════════════════════════════════════════════════
# ②-a 判读层的三个纯函数（从 grab_banner 里抽出来，便于离线自测）
# ══════════════════════════════════════════════════════════════════════════
# 【为什么要把这几行抽成函数？】
#   它们和"发不发包"完全无关，只关心"拿到字节之后怎么判读"。
#   抽出来之后，`--self-test` 就能在**没有任何网络**的情况下把判读逻辑钉死：
#   二进制 banner 会不会炸？读到哪里算收工？errno 到底代表 open 还是 filtered？
#   这几条恰恰是踩坑最多的地方，而它们本来就不需要联网才能验证。

def decode_banner(raw: bytes) -> str:
    """把原始字节解码成可读文本，**任何字节都不允许抛异常**。

    【为什么必须 errors="replace"？】
    banner 里出现非 UTF-8 字节是常态：
      · Telnet 的协商指令（0xFF 0xFB …）；
      · 老设备的 Latin-1 主机名；
      · MySQL/MongoDB 的二进制握手包。
    如果直接用 raw.decode("utf-8")，一个字节就能抛 UnicodeDecodeError，
    在线程池里会变成"某个端口的结果凭空消失"，非常难查。
    errors="replace" 用 U+FFFD 顶替坏字节：**信息会损失一点，但流程永远不中断**。
    （另一个可行选择是 latin-1，它永不失败且字节可逆；代价是可读性差。）

    返回空串而不是 None：调用方可以统一 `or None` 把"没读到"显式化。
    """
    return raw.decode("utf-8", errors="replace") if raw else ""


def banner_is_complete(chunk: bytes) -> bool:
    """启发式判断"这一段读完之后，banner 是不是已经够用了"。

    【为什么要有这个判据？】这里对应坑 3：
        TCP 是**字节流**，不是消息流 —— 一次 recv() 拿到的可能只是半行，
        也可能是好几行拼在一起。反过来，如果傻等到超时，每个开放端口都要
        白等一个完整的 timeout（扫描几万个端口时这是灾难）。
    实践中的折中：**看到换行符就认为"至少拿到了一行标识"，可以收手**。
    对 SMTP/SSH/HTTP 这类文本协议，第一行恰恰就是最有信息量的那行。
    对二进制协议（如不认识的私有协议）这个启发式可能提前收手 ——
    但要记住：banner 抓取的目的是**识别服务**，不是完整读取会话。
    """
    return b"\n" in chunk


# connect_ex() 返回值的含义表。
# 【为什么要区分这三态？】见坑 8：closed（RST）和 filtered（DROP）在
# 安全上意义完全不同 —— 前者说明对方明确拒绝，后者说明流量被静默丢弃，
# 很可能存在防火墙。把它们混为一谈，就会漏掉"被防火墙保护"这个事实。
CONNECT_CODE_MEANING = {
    0: "open",                 # 连接建立成功 → 端口开放
    111: "closed/rejected",    # ECONNREFUSED → 有主机、无监听（对方回了 RST）
    110: "filtered/timeout",   # ETIMEDOUT → 无响应（被 DROP，扫描器只能等到超时）
    113: "host unreachable",   # EHOSTUNREACH → 路由 / ACL 阻断
}


def describe_connect_code(code: int) -> str:
    """把 connect_ex 的返回值翻译成人类可读的状态结论（纯函数）。"""
    return CONNECT_CODE_MEANING.get(code, f"其它 errno {code}")


# ══════════════════════════════════════════════════════════════════════════
# ② 抓 banner 的核心函数（正确版本，后面逐个坑都拿它对比）
# ══════════════════════════════════════════════════════════════════════════

def grab_banner(
    host: str,
    port: int,
    probe: bytes | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = MAX_BANNER_BYTES,
) -> str | None:
    """抓取端口 banner。返回可读字符串；失败返回 None。

    参数
    ----
    probe     : 连上后主动发送的字节。HTTP 用 `b"GET / HTTP/1.0\\r\\n\\r\\n"`。
                设为 None 就只读（适合 SMTP/SSH 这类主动打招呼的服务）。
    timeout   : **务必设置**。socket 默认是阻塞且无超时的。
    max_bytes : 读取上限，防止恶意服务吐 10GB 数据把内存撑爆。

    【这个函数为什么长这样？逐条对应后面的坑】
      · settimeout(timeout)  → 坑 1（不设超时 = 永久卡死）
      · probe                → 坑 2（有些服务不主动说话）
      · 循环 recv            → 坑 3（一次 recv 只拿到一个 TCP 段）
      · errors="replace"     → 坑 4（二进制 banner 会让 utf-8 解码失败）
      · with 语句            → 坑 5（不关 socket 会耗尽文件描述符）
      · shutdown(SHUT_WR)    → 坑 7（告诉服务端"我说完了"，促使其回话）
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)

            if probe:
                sock.sendall(probe)
                # 【技巧】半关闭写方向：TCP 是双向的，shutdown(SHUT_WR) 发出
                # FIN，等于告诉服务端"我不再发数据了"。很多老服务（如
                # inetd 式的、部分 FTP）只有在看到 FIN 之后才会把 banner 吐出来。
                # 注意：对 HTTP/1.1 的 keep-alive 服务这样做通常也没问题，
                # 但对方可能把连接关掉，所以 probe 场景下要谨慎使用——
                # 这里演示这个能力，示例 03 里对 HTTP 就没用 SHUT_WR。
                try:
                    sock.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

            chunks: list[bytes] = []
            total = 0
            while total < max_bytes:
                try:
                    data = sock.recv(1024)
                except socket.timeout:
                    break              # 超时 = "暂时没有更多了"，不算错误
                except ConnectionResetError:
                    break              # 被 RST：对方直接掐断，已有数据仍可用
                if not data:
                    break              # 对方正常关闭（FIN）
                chunks.append(data)
                total += len(data)
                # 启发式：读到换行就认为 banner 到齐了，提前退出省时间
                # （判据抽成了 banner_is_complete()，理由见该函数注释）
                if banner_is_complete(data):
                    break

            raw = b"".join(chunks)
            # 解码容错统一走 decode_banner()：二进制 banner 不许炸线程
            return decode_banner(raw) or None
    except (ConnectionRefusedError, socket.timeout, OSError):
        return None


# ══════════════════════════════════════════════════════════════════════════
# ③ 八个坑：错误写法 → 为什么错 → 正确写法
# ══════════════════════════════════════════════════════════════════════════

def pitfall_1_no_timeout(mute_port: int) -> None:
    print_header("坑 1：不设超时 —— 一个端口就能把脚本挂死")
    print(f"""
  ❌ 错误写法：
        s = socket.socket()
        s.connect(("{TARGET}", {mute_port}))
        data = s.recv(1024)          # ← 这里会永远等下去

  【为什么会卡死】TCP socket 默认是"阻塞 + 无超时"。recv() 会一直等：
      · 等到有数据，
      · 或等到对方关闭连接，
      · 或等到系统 TCP keepalive 发现连接死了（Linux 默认要 **2 小时 11 分**）。
  如果目标端口是一个"只 accept 不回话"的服务（本演示的哑巴服务就是），
  你的脚本会原地冻结。扫描器卡死 99% 是这一条。

  ✅ 正确写法：连接和读写都要设超时。""")

    started = time.time()
    banner = grab_banner(TARGET, mute_port, timeout=0.8)
    elapsed = time.time() - started
    print(f"        socket.create_connection(..., timeout=0.8)")
        # 上一行同样是 print，用来保持缩进对齐的演示效果
    print(f"        实测：等待 {elapsed:.2f} 秒后返回，banner={banner!r}（超时按「无 banner」处理）")

    print("""
  【为什么 create_connection 也要传 timeout？】
  因为默认的 connect 超时是**操作系统给的**（Linux 上 SYN 重试约 2 分钟），
  一个被防火墙 DROP 的端口（不回 RST，只丢包）会让 connect 卡两分钟。
  必须给"连接阶段"和"读写阶段"都设预算。
""")


def pitfall_2_real_port_without_probe(http_port: int) -> None:
    print_header("坑 2：端口开着 ≠ 抓得到 banner（HTTP 要你先开口）")
    print("  先看「只读不写」会发生什么：")
    started = time.time()
    passive = grab_banner(TARGET, http_port, probe=None, timeout=0.8)
    print(f"    ❌ 不发请求直接读：banner={passive!r}，等了 {time.time() - started:.2f} 秒")

    probe = b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n"
    started = time.time()
    active = grab_banner(TARGET, http_port, probe=probe, timeout=1.0)
    print(f"    ✅ 发 GET 探针后再读：拿到 {len(active or '')} 字节，耗时 {time.time() - started:.2f} 秒")
    print("\n  响应头（前 8 行）：")
    for line in (active or "").splitlines()[:8]:
        print(f"    | {line}")

    print("""
  【为什么会这样】HTTP 是**请求-响应（request-response）**协议：服务端只有
  读到完整请求行 + 空行，才会生成响应。你在 connect 之后干等着，双方就一起
  等到超时。这就是"端口开着但抓不到 banner"最常见的原因。

  【正确的探针选择】不同协议要不同开场白：
    · HTTP  →  b"GET / HTTP/1.0\\r\\nHost: <host>\\r\\n\\r\\n"（用 1.0 避免 chunked）
    · HTTPS →  不能明文探！必须先 TLS 握手（ssl.wrap_socket），再发 GET
    · Redis →  b"PING\\r\\n"（回 +PONG 或 -NOAUTH）
    · MySQL →  服务端先发握手包，客户端**只读**即可
    · SMTP/FTP/SSH → 服务端主动发 banner，客户端**只读**
    · DNS/TFTP(HTTP 无关) → 需构造协议报文，属于"协议探测"而非"文字 banner"

  ⚠️ 另一个坑：`GET / HTTP/1.1` 不带 `Host` 头，很多服务器直接 400 甚至断连。
     用 HTTP/1.0，或者老老实实把 Host 头写上。
""")


def pitfall_3_single_recv(chatter_port: int) -> None:
    print_header("坑 3：只 recv 一次 —— banner 可能被切碎")
    print(f"""
  ❌ 错误写法：
        data = s.recv(1024)          # 只有一次！

  【为什么不够】TCP 是**字节流**，不是"消息流"。服务端发的 banner 可能被
  拆成多个 TCP 段到达（网络 MTU、Nagle 算法、中间设备都可能切分）。
  一次 recv 只能拿到"当前已到达内核缓冲区的那部分"，剩下的还没来。
  结果就是 banner 被截断，指纹匹配失败。

  ✅ 正确写法：循环 recv，直到超时 / 对方关闭 / 达到上限。
  下面实测同一个端口，两种写法的差异。""")

    # 错误写法：只读一次
    with socket.create_connection((TARGET, chatter_port), timeout=1.0) as sock:
        sock.settimeout(0.5)
        one = sock.recv(1024)

    # 正确写法：循环读
    full = grab_banner(TARGET, chatter_port, timeout=0.5)

    print(f"    recv 一次  → {len(one)} 字节: {one!r}")
    print(f"    循环读取   → {len(full or b'')} 字节: {(full or '')!r}")
    if len(one) == len(full or b""):
        print("    （本次两者一致：banner 很短，一个段就装下了。但**不能依赖**这一点——")
        print("      签名长的服务如 SSH 的 server banner + KEXINIT 就会出现差异）")

    print("""
  【边界怎么定？】"读到什么时候算完"没有万能答案，三种常用启发式：
    1. 读到换行/双换行（HTTP 头结束标记 \\r\\n\\r\\n）→ 精确，但只适合文本协议；
    2. 读到超时（TCP 上"沉默"通常意味着该服务暂时没话说了）→ 通用但要花钱等；
    3. 读到固定字节数上限 → 兜底防内存爆炸。
  生产代码里通常是 2 + 3 组合，再加 1 做加速。这就是 grab_banner 的 while 循环。
""")


def pitfall_4_decode_error(chatter_port: int) -> None:
    print_header("坑 4：banner 不一定是文本 —— 解码会炸")
    # 手工模拟一个"二进制 banner"：SSH 版本串之后紧跟着 KEXINIT 二进制包
    fake_binary = b"SSH-2.0-OpenSSH_8.9p1\r\n" + bytes([0, 0, 0, 0x1c, 0x0a, 0x14, 0xff, 0xfe, 0x80, 0x81])
    print(f"  一段真实的「半文本半二进制」数据（{len(fake_binary)} 字节）：{fake_binary!r}")

    try:
        strict = fake_binary.decode("utf-8")
        print(f"  utf-8 严格解码成功：{strict[:40]!r}")
    except UnicodeDecodeError as exc:
        print(f"  ❌ utf-8 严格解码失败：{exc}")
        print("     这在扫描器里会直接抛异常，把整个扫描线程干掉。")

    lenient = fake_binary.decode("utf-8", errors="replace")
    latin = fake_binary.decode("latin-1")
    print(f"  ✅ errors=\"replace\"：{lenient[:40]!r}")
    print(f"  ✅ latin-1（1 字节 = 1 字符，永不失败）：{latin[:40]!r}")

    print("""
  【为什么会有二进制 banner】SSH 协议在版本串之后立刻发二进制的 KEXINIT 包；
  MySQL 握手包里有二进制盐值；很多工控协议（Modbus/S7）整体就是二进制。
  扫描器**永远不要假设 banner 是干净的 UTF-8**。

  【三种策略怎么选】
    · errors="replace"  → 保留可读部分，坏字节变 U+FFFD。做**指纹匹配**时首选。
    · errors="ignore"   → 直接丢掉坏字节，可能让本不相邻的字符连在一起 → 误判。
    · latin-1           → 永远成功、可逆（encode 回去字节完全一样），适合需要
                          保留原始字节做哈希/正则的场景。
  做服务识别时，更稳的做法是**同时保留原始 bytes 和展示用的字符串**。
""")


def pitfall_5_fd_leak(chatter_port: int) -> None:
    print_header("坑 5：不关 socket —— 文件描述符泄漏")
    print("""
  ❌ 错误写法：
        s = socket.socket()
        s.connect((host, port))
        banner = s.recv(1024)
        # 忘了 s.close()，或者中间 return / 抛异常提前跳出

  【为什么致命】每个 socket 占用一个文件描述符（fd）。Linux 默认单进程上限
  通常是 1024（`ulimit -n`）。扫描 5000 个端口、每个泄漏一个 fd，脚本会以
  `OSError: [Errno 24] Too many open files` 崩掉。而且连接不会被回收，
  目标侧会看到一堆 CLOSE_WAIT 状态的连接 —— 在授权的生产环境里这是事故。

  ✅ 正确写法：用 `with` 语句。socket 支持上下文管理器协议，退出时自动 close，
  即使中途抛异常也会关。""")

    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    print(f"    本机 fd 上限：soft={soft}, hard={hard}")

    # 演示 with 的自动关闭
    with socket.create_connection((TARGET, chatter_port), timeout=1.0) as sock:
        fd = sock.fileno()
        print(f"    with 块内 fd = {fd}")
    print("    with 块结束后，该 fd 已被自动 close（可以对比 /proc/self/fd 数量验证）")

    print("""
  【同一类的坑还有】
    · 忘了 stop/join 演示用的后台线程 → 进程退不干净；
    · ThreadPoolExecutor 用 submit 后不取结果、不等待 → 主线程先退出，
      扫描结果丢一半（示例 03 会用 as_completed 收齐）。
""")


def pitfall_6_concurrency(chatter_port: int, mute_port: int, http_port: int) -> None:
    print_header("坑 6：并发不做限流 —— 要么打爆自己，要么打爆目标")
    ports = [chatter_port, mute_port, http_port]

    print("  串行耗时（以哑巴端口 0.8s 超时为例，总耗时 = 各端口耗时之和）：")
    started = time.time()
    for p in ports:
        grab_banner(TARGET, p, timeout=0.8)
    serial = time.time() - started
    print(f"    串行 3 个端口: {serial:.2f}s")

    print("  ❌ 错误写法：一个端口一个线程，开一千个")
    print("     后果 A（打爆自己）：线程栈内存 + fd 耗尽，`RuntimeError: can't start new thread`")
    print("     后果 B（打爆目标）：瞬间几百个 SYN 打过去，等于对目标做了一次小型 DoS，")
    print("                        触发 fail2ban/WAF/云厂商流量告警 —— 这在授权测试里")
    print("                        也算「超出授权范围的行为」。")

    print("  ✅ 正确写法：ThreadPoolExecutor(max_workers=N) + 每个任务内部仍有超时预算")
    started = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(grab_banner, TARGET, p, None, 0.8): p for p in ports}
        for fut in as_completed(futures):
            port = futures[fut]
            results[port] = fut.result()
    parallel = time.time() - started
    print(f"    并发（max_workers=8）3 个端口: {parallel:.2f}s")
    for p in sorted(results):
        b = results[p]
        print(f"      {p}/tcp → {(b or '').strip()[:60] or '(无 banner)'}")

    print(f"""
  【max_workers 该开多大？】判断标准有三个，取最小：
    1. **礼貌**：默认值一般是 10~50，别超过 100（除非你明确知道目标扛得住）；
    2. **自己的资源**：线程数 ≤ fd 上限 - 已用（保守取上限的 1/4）；
    3. **目标承受力**：对内网设备/嵌入式设备，5~10 就走得很稳。
  本日示例 03 用 64 作为默认值，并允许命令行调小。

  【为什么 3 个端口的并发没比串行快 3 倍】因为哑巴端口是 0.8 秒超时，
  并发时它和其他两个同时跑，所以总耗时 ≈ max(各端口耗时) = 0.8s 左右，
  而不是 0.8+0.8+0.8。这就是"并发把等待时间重叠起来"的本质。
""")


def pitfall_7_half_close(chatter_port: int) -> None:
    print_header("坑 7：不发 FIN —— 有些服务在等你说完")
    print("""
  TCP 是全双工的。`shutdown(socket.SHUT_WR)` 只关闭**写方向**（发一个 FIN），
  读方向仍然可以继续 recv。它的作用是把"我没有更多数据要发了"这个信息
  传达给对端 —— 很多基于行的老协议（FTP 控制通道、部分 telnet 服务、
  inetd 派生的小服务）会**等到收到 FIN 才生成完整响应**。

        s.sendall(probe)
        s.shutdown(socket.SHUT_WR)   # ← 我说完了，该你说了
        data = s.recv(4096)

  与 close() 的区别：close() 是双向关闭，如果还有数据没读完，内核会发 RST，
  对端可能**丢掉已发出的数据**。所以"发完探针想继续读"就绝不能用 close()。
""")
    probe = b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n"
    out = grab_banner(TARGET, chatter_port, probe=probe, timeout=0.6)
    print(f"    顺带验证一下往 SMTP 服务发 HTTP 请求的结果（协议不匹配）：")
    print(f"      {out!r}")
    print("    → 服务已经把 banner 发出去了，所以仍能拿到；真实世界里协议不匹配")
    print("      常见结果是连接被直接关闭（RST）或返回一堆乱码，需要靠"
          "「探针组合 + 响应聚类」来判断，这正是 nmap -sV 做的事情。")


def pitfall_8_filtered_vs_closed() -> None:
    print_header("坑 8：把「超时」当成「关闭」 —— 过滤与关闭的区别")
    print("""
  connect_ex 的返回值告诉我们三件**不同**的事：

    ┌────────────────────────┬─────────────────────────┬──────────────────┐
    │ 返回值                  │ 含义                     │ 防火墙状态        │
    ├────────────────────────┼─────────────────────────┼──────────────────┤
    │ 0                       │ 端口开放                 │ 放行              │
    │ ECONNREFUSED (111)      │ 端口关闭（有主机，无监听）│ **REJECT**（回RST）│
    │ ETIMEDOUT (110)         │ 无响应 → 被 **DROP**     │ 丢弃，无 RST      │
    │ EHOSTUNREACH (113)      │ 网络/主机不可达           │ 路由或 ACL 阻断   │
    └────────────────────────┴─────────────────────────┴──────────────────┘

  【为什么这个区别很重要】
    · REJECT（拒绝）说明有防火墙**主动**回你 RST —— 这类防火墙配置通常
      会记录日志，也意味着**你的扫描行为被看见了**；
    · DROP（丢弃）是"沉默" —— 扫描器会卡到超时，浪费你的时间预算，
      但这才是更强的防御姿态；
    · 把两者混为一谈，会把"被防火墙吞掉的端口"误判为"关闭的服务"，
      从而漏掉真正需要关注的暴露面。

  【为什么 connect 扫描区分不出"过滤"和"关闭"？】
  因为 connect_ex 只能看到"没连上"，看不到**为什么**没连上（RST 还是超时）。
  只有用原始套接字（SYN 扫描 + 读 ICMP）才能精确区分。这就是 nmap 的
  `filtered` 状态比"closed"更有信息量的原因。

  ⚠️ 另外一个现实：**在本机演示里这些状态几乎看不到**，因为回环地址没有
  中间防火墙：端口没监听就是干脆的 ECONNREFUSED。所以防火墙行为要在
  带网络隔离的环境中（云主机安全组、iptables DROP 规则）才能真正观察。
""")
    # 本机实测：一个几乎不可能开的端口 → 应该是 ECONNREFUSED (111)
    probe_port = 9  # discard 端口，通常无监听
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        code = sock.connect_ex((TARGET, probe_port))
    print(f"    实测 {TARGET}:{probe_port} → connect_ex 返回 {code}"
          f"（{describe_connect_code(code)}）")
    print("    【注意】本机没有中间防火墙，所以这里几乎只会看到 111/0 这两种；")
    print("    要观察 110（DROP）请在有安全组的云主机或本机 iptables DROP 规则下实测。")


# ══════════════════════════════════════════════════════════════════════════
# ④ 综合演示：把修好的写法跑一遍
# ══════════════════════════════════════════════════════════════════════════

def combined_demo(ports: dict[str, int]) -> None:
    print_header("④ 综合演示：用正确写法识别三个性格不同的服务")

    probes = {
        "chatterbox": None,                                  # 主动打招呼 → 只读
        "mute": b"PING\r\n",                                 # 哑巴 → 先发个探针
        "http": b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n",  # 请求-响应 → 发探针
    }

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(grab_banner, TARGET, port, probes[name], 1.0): name
            for name, port in ports.items()
        }
        for fut in as_completed(futures):
            name = futures[fut]
            port = ports[name]
            banner = fut.result() or ""
            first_line = banner.strip().splitlines()[0] if banner.strip() else "(无响应)"
            print(f"    {name:<12} {port:>6}/tcp  第一行: {first_line[:70]}")

    print("""
  【怎么看这个结果】
    · chatterbox 抓到 `220 ... ESMTP` → 可以判定是 SMTP 类服务（指纹：^220 .*ESMTP）；
    · http 抓到 `HTTP/1.0 200 OK` + `Server: day153-probe-http/2.1`
      → 两个信息点：协议是 HTTP，服务端软件是 day153-probe-http；
    · mute 拿到空 → **这不代表端口关闭**。它只是"沉默"。要区分"关闭 vs
      沉默"，得回看 connect 阶段是否成功：connect 成功 + 无 banner
      = 端口开放但服务不说话（或需要更合适的探针）。
  这三条恰好覆盖了服务识别的全部难点：**探针 + 超时 + 结果判读**。
""")


# ══════════════════════════════════════════════════════════════════════════
# ⑤ 主流程
# ══════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════
# ⑨ 自测（--self-test）：把"能离线验证的部分"从"必须联网的部分"里拆出来
# ══════════════════════════════════════════════════════════════════════════
# 【设计思路：抽取纯函数】
#   grab_banner() 里真正容易写错的并不是 socket 调用本身，而是**判读逻辑**：
#       · 收到的字节怎么解码？（二进制 banner 会不会把线程炸掉）
#       · 什么时候算"这个 banner 读完了"？
#       · connect_ex 的返回值各自代表什么状态？
#   这三件事全部可以做成**不碰网络的纯函数**（decode_banner / banner_is_complete /
#   describe_connect_code），于是自测可以在完全离线的环境里把它们逐一钉死。
#   而"真的能连上本机服务并抓到 banner"由默认运行（本机三个性格不同的演示服务）
#   来验证 —— 两者分工：**自测证明判读正确，演示证明链路打通**。

class _SelfTest:
    """极简断言收集器：失败时打印「期望 vs 实际」，最后汇总。"""

    def __init__(self) -> None:
        self.total = 0
        self.failures: list[str] = []

    def check(self, label: str, ok: bool, expect: str, actual: str) -> None:
        self.total += 1
        if ok:
            print(f"   ✅ {label}")
        else:
            self.failures.append(label)
            print(f"   ❌ {label}")
            print(f"        期望: {expect}")
            print(f"        实际: {actual}")

    def eq(self, label: str, actual, expect) -> None:
        self.check(label, actual == expect, repr(expect), repr(actual))

    def contains(self, label: str, haystack: str, needle: str) -> None:
        self.check(label, needle in haystack, f"包含 {needle!r}", _clip(haystack))

    def absent(self, label: str, haystack: str, needle: str) -> None:
        self.check(label, needle not in haystack, f"不包含 {needle!r}", _clip(haystack))

    def true(self, label: str, cond: bool, detail: str = "") -> None:
        self.check(label, cond, "True", f"False {detail}".strip())


def _clip(text: str, limit: int = 200) -> str:
    flat = " ".join(str(text).split())
    return repr(flat[:limit] + ("…" if len(flat) > limit else ""))


def self_test() -> int:
    """离线自测，返回失败项数量。0 = 全部通过。"""
    t = _SelfTest()

    # ══ A. 解码容错（坑 4 的回归测试） ═══════════════════════════
    print("\n[A] decode_banner()：任何字节都不能让解码抛异常")
    t.eq("正常 UTF-8 banner 原样还原",
         decode_banner("220 你好 ESMTP\r\n".encode("utf-8")), "220 你好 ESMTP\r\n")
    t.eq("空字节流 → 空字符串（而不是 None，便于统一处理）",
         decode_banner(b""), "")

    binary = b"\xff\xfd\x01\xff\xfb\x01\x00\x9c"
    try:
        decoded = decode_banner(binary)
        raised = None
    except Exception as exc:          # noqa: BLE001 —— 这里就是要把任何异常都抓住
        decoded, raised = "", repr(exc)
    t.eq("二进制 banner（Telnet 协商字节之类）不会抛 UnicodeDecodeError",
         raised, None)
    t.contains("解码失败的部分用 U+FFFD 顶替（errors='replace' 的效果）",
               decoded, "\ufffd")
    t.eq("解码后仍是 str 类型（下游 .splitlines() 才不会炸）",
         isinstance(decoded, str), True)

    # ══ B. "banner 读完了吗" 的判据（坑 3 的回归测试） ═════════════
    print("\n[B] banner_is_complete()：什么时候可以停止 recv")
    t.eq("含换行 → 认为一行 banner 已到齐，可以提前收手",
         banner_is_complete(b"SSH-2.0-OpenSSH_8.9p1\r\n"), True)
    t.eq("不含换行 → 还要继续读（一个 TCP 段不等于一条完整 banner）",
         banner_is_complete(b"220 mail.example.com"), False)
    t.eq("只有 \\n 也算（有些服务不发 \\r）",
         banner_is_complete(b"+OK\n"), True)
    t.eq("空片段 → 不要死循环，交给调用方 break",
         banner_is_complete(b""), False)

    # ══ C. connect 返回值的三态语义（坑 8 的回归测试） ════════════
    print("\n[C] describe_connect_code()：把 errno 翻译成三态结论")
    t.eq("0 → open（连接成功）", describe_connect_code(0), "open")
    t.eq("111 (ECONNREFUSED) → closed/rejected（有主机、没监听，被 REJECT）",
         describe_connect_code(111), "closed/rejected")
    t.eq("110 (ETIMEDOUT) → filtered/timeout（被 DROP，静默丢弃）",
         describe_connect_code(110), "filtered/timeout")
    t.eq("113 (EHOSTUNREACH) → host unreachable（路由/ACL 阻断）",
         describe_connect_code(113), "host unreachable")
    t.contains("未知 errno 也要给出可读说明（不要把数字直接丢给人）",
               describe_connect_code(999), "999")
    t.contains("未知 errno 的说明里带「其它」标记，便于日志检索",
               describe_connect_code(999), "其它")

    # ══ D. 演示服务的"性格"是否与文档一致 ════════════════════════
    print("\n[D] 三个演示服务的协议特征（它们是后面指纹识别的素材）")
    greeting = ChatterboxServer.GREETING
    t.eq("话痨服务的问候是 SMTP 风格（220 开头）",
         greeting.startswith(b"220 "), True)
    t.eq("SMTP 多行协议必须以 CRLF 结尾（否则客户端会一直等下一行）",
         greeting.endswith(b"\r\n"), True)
    t.contains("问候里带 ESMTP 关键字 —— 这正是指纹规则 ^220.*(E?SMTP|Mail) 依赖的特征",
               greeting.decode("ascii", "replace"), "ESMTP")
    t.eq("话痨服务的 banner 是单行（读一次 recv 就能拿到，方便对照坑 3）",
         len(greeting.strip().splitlines()), 1)
    t.true("DEFAULT_TIMEOUT 是正数（不设超时的坑就是「它必须存在」）",
           DEFAULT_TIMEOUT > 0, f"DEFAULT_TIMEOUT={DEFAULT_TIMEOUT}")
    t.true("MAX_BANNER_BYTES 有限且至少能装下一条 ordinary banner",
           1024 <= MAX_BANNER_BYTES <= 1024 * 1024,
           f"MAX_BANNER_BYTES={MAX_BANNER_BYTES}")

    # ══ E. probes 组合的完整性（综合演示用到的三种探针策略） ══════
    print("\n[E] 探针策略：三种服务性格对应三种探法")
    probes = {
        "话痨型（主动打招呼）": None,
        "哑巴型（必须主动问）": b"PING\r\n",
        "请求-响应型（HTTP）": b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n",
    }
    t.eq("话痨型：只读，不发任何探针（发了反而可能被当成非法指令断开）",
         probes["话痨型（主动打招呼）"], None)
    t.true("哑巴型：探针以 CRLF 结尾（很多文本协议按行解析）",
           probes["哑巴型（必须主动问）"].endswith(b"\r\n"))
    t.true("HTTP 型：探针是一个合法请求（请求行 + Host + 空行）",
           probes["请求-响应型（HTTP）"].startswith(b"GET / HTTP/1.0\r\n")
           and probes["请求-响应型（HTTP）"].endswith(b"\r\n\r\n"))

    print(f"\n   断言总数: {t.total}，失败: {len(t.failures)}")
    return len(t.failures)


def main(argv: list[str] | None = None) -> int:
    """命令行入口。

        python3 02-banner-grab-pitfalls.py              → 完整演示（本机三个演示服务）
        python3 02-banner-grab-pitfalls.py --self-test  → 纯离线自测（不建任何连接）
    """
    parser = argparse.ArgumentParser(
        description="Day 153 示例 02：Banner 抓取与服务识别的 8 个坑（仅限本机回环）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python3 02-banner-grab-pitfalls.py              # 完整演示\n"
            "  python3 02-banner-grab-pitfalls.py --self-test  # 离线自测\n"
        ),
    )
    parser.add_argument("--self-test", action="store_true",
                        help="只跑离线自测（判读逻辑断言，不发起任何连接）")
    args = parser.parse_args(argv)

    if args.self_test:
        failures = self_test()
        print()
        if failures:
            print(f"❌ SELF-TEST FAILED：{failures} 项断言未通过"
                  "（请回看上面打印的「期望 / 实际」）")
            return 1
        print("✅ SELF-TEST OK（banner 判读逻辑断言全部通过；未建立任何 socket 连接）")
        return 0

    demo()
    return 0


def demo() -> None:
    assert TARGET == "127.0.0.1", "教学示例只允许扫描本机回环地址"

    print(f"目标（硬编码）: {TARGET}")
    chatter = ChatterboxServer()          # 随机端口
    mute = MuteServer()                   # 随机端口
    http_server, http_port = start_probe_http()
    chatter.start()
    mute.start()

    ports = {"chatterbox": chatter.port, "mute": mute.port, "http": http_port}
    print("已启动本机演示服务：")
    for name, port in ports.items():
        print(f"    {name:<12} 127.0.0.1:{port}")

    try:
        pitfall_1_no_timeout(mute.port)
        pitfall_2_real_port_without_probe(http_port)
        pitfall_3_single_recv(chatter.port)
        pitfall_4_decode_error(chatter.port)
        pitfall_5_fd_leak(chatter.port)
        pitfall_6_concurrency(chatter.port, mute.port, http_port)
        pitfall_7_half_close(chatter.port)
        pitfall_8_filtered_vs_closed()
        combined_demo(ports)
    finally:
        chatter.stop()
        mute.stop()
        http_server.shutdown()
        http_server.server_close()

    print_header("小结：banner 抓取的正确姿势清单")
    print("""
  [1] 连接和读写都要设超时（create_connection(timeout=) + settimeout()）
  [2] 知道协议行为再选探针：只读 / 发请求 / 发半关闭 FIN
  [3] 循环 recv 到超时或分隔符，别只读一次
  [4] 永远用 errors="replace" 或 latin-1 解码，别让二进制 banner 炸掉线程
  [5] with socket... 保证关闭；用线程池要等待全部完成
  [6] 并发必须限流（max_workers + 超时），既保护自己也保护目标
  [7] 区分 open / closed / filtered：connect_ex 返回值有三种含义
  [8] 记住"无 banner"≠"端口关闭"，这两件事要在报告里分开写
""")


if __name__ == "__main__":
    sys.exit(main())
