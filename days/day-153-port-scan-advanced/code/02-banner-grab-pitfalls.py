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

import http.server
import socket
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
                if b"\n" in data:
                    break

            raw = b"".join(chunks)
            return raw.decode("utf-8", errors="replace") if raw else None
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
    meaning = {0: "open", 111: "closed/rejected", 110: "filtered/timeout", 113: "host unreachable"}
    print(f"    实测 {TARGET}:{probe_port} → connect_ex 返回 {code}（{meaning.get(code, '其它')}）")


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

def main() -> None:
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
    main()
