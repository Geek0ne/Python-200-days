"""流量审计共享引擎（Day 164 · 安全审计工具箱 第 3 天）。

Day 162 解决"**资产面**"（有什么：端口 / 目录 / 指纹），
Day 163 解决"**漏洞面**"（哪里可能有问题：SQLi / XSS），
本模块解决"**流量面**"（**实际发生了什么**：请求与响应长什么样）。

为什么需要"流量面"？因为前两天的结论都是**推断**：

| 阶段 | 得到的结论 | 结论的性质 |
|---|---|---|
| Day 162 资产面 | "80 端口开着，`/search` 返回 200" | 快照，**没看到参数怎么传** |
| Day 163 漏洞面 | "`id` 参数疑似布尔差分注入" | 探针推断，**没看到真实业务流量** |
| Day 164 流量面 | "登录口令以明文出现在请求体第 3 行" | **事实**，可复核、可留证 |

中间人（MITM）代理的价值就在于：把"推断"变成"事实"。
它坐在客户端与目标之间，**每一个字节都从它手里过**，
所以它能回答前两个阶段回答不了的问题：

* 凭据是明文还是密文？
* 敏感数据走的是 Header / URL 查询串 / 请求体？
* Cookie 有没有 `HttpOnly` / `Secure`？
* 重定向链有多长、中间跳到哪去？
* 哪些流量**根本看不见**（TLS 隧道）？

它提供六样东西：

1. **Scope（范围门禁）**：与 Day 162/163 同构，**独立成文件**，
   保证本课可以"冻结快照"式复现，不依赖前两天的目录还在不在。
2. **LabOrigin（本机实验网站）**：只绑定 `127.0.0.1`，
   故意做出"会泄密的流量"，让规则引擎有东西可抓：

   | 端点 | 行为 | 用来演示的规则 |
   |---|---|---|
   | `POST /login` | 接收表单口令，回 `Set-Cookie`（**缺** HttpOnly/Secure） | 明文凭据 / Cookie 缺标记 |
   | `GET /api/user?id=1` | 正常 JSON；`id` 带引号则返回 500 + SQL 报错 | 报错回显 |
   | `GET /search?q=&token=` | 把 `token` 放在**查询串**里 | 敏感参数出现在 URL |
   | `GET /secret` | 响应体里带 `api_key` | 响应体泄密 |
   | `GET /redirect?to=` | 302 跳一次 | 重定向链 |
   | `GET /slow` | 睡眠 400ms | 慢响应 |
   | `GET /large` | 返回 200KB 大页 | 响应体截断 |
   | `GET /admin` | 403 | 权限边界 |
   | `PUT /api/user/1` | 接受写操作 | 只读原则被破坏的告警 |

3. **AuditProxy（本机中间人代理）**：纯 `socket` 实现的**正向 HTTP 代理**，
   支持 `GET / POST` 的**绝对 URI 形式**、`CONNECT` 隧道（**只能看到它有，看不到里面**）。
   每处理完一次往返就落一条 **flow** 到 JSONL——这就是"流量档案"。
4. **LabOpaqueTCP**：一个**假装的 TLS 服务**（纯文本回声）。
   客户端对它发 `https://` 请求时，代理只能建隧道、**读不到内容**。
   这不是缺陷，是本课最重要的**覆盖缺口**演示。
5. **LabSession（脚本化客户端）**：模拟一次"审计会话"，
   走代理发出上面那张表里的请求，用来产生真实流量。
6. **FlowAnalyzer（规则引擎）**：15 条规则，把 flow 变成 **Finding**，
   产出 JSON + Markdown 报告 + **语义化退出码**。

## 安全边界（刻意为之，读完再用）

* 只对**你自己拥有、或已获书面授权**的目标使用；
* 只绑定 `127.0.0.1`，只允许回环地址 + RFC 5737 文档网段（`192.0.2.0/24`）；
* **代理默认只监听回环**，绝不监听 `0.0.0.0`——否则你就成了"公开的开放代理"，
  那是一个真正会被追责的法律问题，不是一个配置选项；
* 流量档案**默认脱敏**：口令 / 令牌 / Cookie 的**值**不落盘，
  只留"字段名 + 值指纹（sha256 前 8 位）+ 长度"。
  这样报告能证明"明文传输了"，却**不能**被当成二次泄密的渠道；
* 本工具**不做**任何解密绕过：`CONNECT` 隧道一律如实记为"不可见"，
  不尝试伪造证书、不尝试降级 TLS、不中间人劫持真实站点；
* 只做**观测与记录**，不做**利用**：不改包、不重放攻击、不注入响应。

自检：
    python3 mitm_core.py --self-test     # 输出 SELF-TEST OK
"""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import select
import socket
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, Sequence

# ─────────────────────────────────────────────────────────────────────────────
# 0. 常量：严重度、退出码、敏感词表、报错特征
# ─────────────────────────────────────────────────────────────────────────────

#: 严重度 → 数值。**为什么要有数？** 因为优先级 = 严重度 × 置信度（见 3.7），
#: 没有数值就没法排序；而"先看哪个"在动辄上千条 flow 的报告里是唯一的阅读入口。
SEVERITY_SCORE: dict[str, float] = {
    "critical": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
    "info": 0.5,
}

#: 五个语义化退出码。**为什么退出码要"语义化"而不是 0/1？**
#: 因为 CI 里要能区分四种完全不同的处境：
#:   * 干净通过 → 0
#:   * 被门禁拦下（根本没测） → 2   ← 这是**配置问题**，不是安全问题
#:   * 有发现（需要人看）     → 3   ← 这是**安全结果**
#:   * 测了但有盲区（结论不可信） → 4 ← 这是**结论可信度问题**
#: 如果全塌缩成 1，运维收到告警时无法判断"该改配置还是该修漏洞"。
EXIT_OK = 0
EXIT_GATE_REJECTED = 2
EXIT_FINDINGS = 3
EXIT_INCOMPLETE = 4

#: 值需要脱敏的**字段名**（小写比较）。**注意：匹配的是"名"不是"值"。**
#: 这是因为我们要保留"这个字段被明文的传了"这一事实，
#: 同时不把秘密本身写进报告——两份收益，一份成本（看报告时要对照字段名读）。
SENSITIVE_KEYS: frozenset[str] = frozenset({
    "password", "passwd", "pwd", "pass",
    "token", "access_token", "refresh_token", "id_token",
    "api_key", "apikey", "api-key", "secret", "client_secret",
    "session", "sessionid", "session_id", "sid", "jsessionid",
    "csrf", "csrf_token", "xsrf", "otp", "pin", "totp",
    "authorization", "auth", "bearer",
    "idcard", "id_card", "card", "credit_card", "cvv",
})

#: 请求头里**整条脱敏**的头（这些头的值本身就是凭据）。
REDACT_HEADERS: frozenset[str] = frozenset({
    "authorization", "proxy-authorization", "cookie", "set-cookie",
    "x-api-key", "x-auth-token", "x-csrf-token",
})

#: 逐跳头（hop-by-hop）。**为什么必须剔除？**
#: `Connection` / `Keep-Alive` / `Transfer-Encoding` 这些头只描述"这一段连接"，
#: 不属于"消息本身"。代理如果不剔除就会把它们转发到下一跳，
#: 造成"两段连接的状态互相污染"——这是手写代理最常见的功能性 bug。
HOP_BY_HOP: frozenset[str] = frozenset({
    "connection", "proxy-connection", "keep-alive",
    "te", "trailer", "transfer-encoding", "upgrade",
    "proxy-authenticate", "proxy-authorization",
})

#: 响应体里的"报错回显"特征。这些字符串出现在响应里，
#: 说明服务端把**内部实现细节**吐给了客户端。
ERROR_SIGNATURES: tuple[tuple[str, str], ...] = (
    ("SQL 报错", r"(SQL syntax|mysql_fetch|ORA-\d{4,5}|PostgreSQL.*ERROR|SQLite3::|sqlite3\.OperationalError|unclosed quotation mark)"),
    ("堆栈回显", r"(Traceback \(most recent call last\)|at java\.|at org\.springframework|File \"/.*\", line \d+)"),
    ("框架调试页", r"(Werkzeug Debugger|Django.*DEBUG = True|Whoops\\Exception)"),
    ("路径回显", r"(/var/www/|C:\\\\inetpub\\\\|/home/\w+/app)"),
)

#: 响应体里的"敏感字段名"。出现说明响应体本身在泄密。
SECRET_BODY_KEYS: frozenset[str] = frozenset({
    "api_key", "apikey", "secret", "client_secret", "token",
    "private_key", "access_key", "password",
})

#: PII（个人可识别信息）模式。**为什么检测这个？**
#: 因为"日志/流量里出现 PII"本身就是合规问题（GDPR / 个保法），
#: 即使这些数据是你的用户"正常"提交的——你也不该把它记进审计档案。
PII_PATTERNS: tuple[tuple[str, str], ...] = (
    ("邮箱", r"[\w.+-]+@[\w-]+\.[\w.]{2,}"),
    ("手机号(CN)", r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    ("身份证(CN)", r"(?<!\d)\d{17}[\dXx](?!\d)"),
)

#: 文档网段 + 回环。教学代码只允许在这里折腾。
DOC_NET = "192.0.2."
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})

#: 代理抓下来的响应体最多存多少字节。**为什么要截断？**
#: 审计档案是"证据"，不是"镜像"：全量存 200KB 页面 × 上千请求 = 报告变垃圾场。
#: 截断 + 记 `body_truncated` 标记，比"悄悄少存"诚实得多。
MAX_BODY_BYTES = 64 * 1024

#: 查找"慢响应"的阈值（毫秒）。
SLOW_MS = 300.0


# ─────────────────────────────────────────────────────────────────────────────
# 1. 门禁：Scope + 两个异常
# ─────────────────────────────────────────────────────────────────────────────


class AuthorizationError(RuntimeError):
    """越界访问。**语义是「根本没开始测」**，所以它映射到退出码 2（而不是 3）。"""


class ScopeError(RuntimeError):
    """触及硬闸门（探针上限 / 频率上限 / 隧道不可见）。"""


@dataclass
class Scope:
    """授权范围：主机白名单 + 端口白名单 + 工单号。

    与 Day 162/163 同构，但**不 import 它们的模块**——教学代码每一天都必须是
    可独立复现的快照。共用代码看着更"优雅"，代价是"前一天的目录被删，今天的课跑不起来"。
    """

    hosts: frozenset[str] = field(default_factory=lambda: frozenset(LOOPBACK_HOSTS))
    ports: tuple[int, ...] = ()
    ticket: str = "(no-ticket)"

    def check_host(self, host: str) -> bool:
        h = (host or "").strip().lower()
        if h in self.hosts:
            return True
        return h.startswith(DOC_NET)  # RFC 5737 文档网段

    def check_port(self, port: int) -> bool:
        return not self.ports or port in self.ports

    def check_url(self, url: str) -> tuple[str, int]:
        """校验 URL，返回 (host, port)；越界抛 AuthorizationError。"""
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https"):
            raise AuthorizationError(f"不支持的 scheme：{parts.scheme!r}")
        host = parts.hostname or ""
        port = parts.port or (443 if parts.scheme == "https" else 80)
        if not self.check_host(host):
            raise AuthorizationError(f"主机越界：{host!r}（工单 {self.ticket}）")
        if not self.check_port(port):
            raise AuthorizationError(f"端口越界：{port}（工单 {self.ticket}）")
        return host, port


# ─────────────────────────────────────────────────────────────────────────────
# 2. 脱敏：把"秘密的值"换成"值的指纹"
# ─────────────────────────────────────────────────────────────────────────────


def value_fingerprint(value: str) -> str:
    """返回 `sha256 前 8 位/长度`。**为什么不干脆删掉？**

    因为"删掉"会丢掉两个可用于交叉比对的信号：
      * 指纹相同 → 同一个口令在多处重复使用（横向风险）；
      * 长度   → 口令是否短于 8 位（弱口令信号）。
    这两个信号都是**结构性**的，不依赖明文，所以能安全保留。
    """
    digest = hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:8]
    return f"<redacted:{digest}/{len(value)}B>"


def redact_mapping(items: Iterable[tuple[str, str]]) -> dict[str, str]:
    """按**字段名**决定是否脱敏一个键值对序列（头 / 表单 / 查询串通用）。"""
    out: dict[str, str] = {}
    for key, value in items:
        if key.lower() in REDACT_HEADERS or key.lower() in SENSITIVE_KEYS:
            out[key] = value_fingerprint(value)
        else:
            out[key] = value
    return out


def redact_url(url: str) -> tuple[str, list[str]]:
    """脱敏 URL 里的查询串，返回 (脱敏后 URL, 命中的敏感参数名列表)。

    **为什么 URL 也要脱敏？** 因为查询串会被三层东西记下来：
    访问日志、浏览器历史、`Referer` 头。把 token 放在 `?token=` 上，
    等于把凭据抄送给了沿途所有人——规则 `sensitive-in-url` 抓的就是这件事。
    """
    parts = urllib.parse.urlsplit(url)
    if not parts.query:
        return url, []
    hits: list[str] = []
    pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    safe_pairs = []
    for key, value in pairs:
        if key.lower() in SENSITIVE_KEYS:
            hits.append(key)
            safe_pairs.append((key, value_fingerprint(value)))
        else:
            safe_pairs.append((key, value))
    safe_query = urllib.parse.urlencode(safe_pairs)
    rebuilt = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, safe_query, parts.fragment)
    )
    return rebuilt, hits


def redact_body(body: str, content_type: str) -> tuple[str, list[str]]:
    """脱敏请求/响应体，返回 (脱敏后正文, 命中的敏感字段名列表)。

    支持三种常见载体：
      * `application/x-www-form-urlencoded` → 当查询串处理；
      * `application/json` → 递归走字典，按 key 脱敏；
      * 其他 → 逐行做 PII 替换（**只做替换，不改结构**）。
    """
    hits: list[str] = []
    ctype = (content_type or "").lower()

    if "application/x-www-form-urlencoded" in ctype:
        pairs = urllib.parse.parse_qsl(body, keep_blank_values=True)
        safe = []
        for key, value in pairs:
            if key.lower() in SENSITIVE_KEYS:
                hits.append(key)
                safe.append((key, value_fingerprint(value)))
            else:
                safe.append((key, value))
        return urllib.parse.urlencode(safe), hits

    if "application/json" in ctype:
        try:
            parsed = json.loads(body)
        except (ValueError, TypeError):
            return body, hits

        def walk(node: Any) -> Any:
            if isinstance(node, dict):
                out: dict[str, Any] = {}
                for key, value in node.items():
                    if isinstance(key, str) and key.lower() in SENSITIVE_KEYS:
                        hits.append(key)
                        out[key] = value_fingerprint(str(value))
                    else:
                        out[key] = walk(value)
                return out
            if isinstance(node, list):
                return [walk(item) for item in node]
            return node

        return json.dumps(walk(parsed), ensure_ascii=False), hits

    return body, hits


def mask_pii(text: str) -> tuple[str, list[str]]:
    """把 PII 替换成占位符，返回 (替换后文本, 命中的类别)。

    **注意方向**：这里不是"检测"而是"擦除"。
    检测结论会写进 Finding（那是报告需要的），而正文里的 PII 必须**当场消失**。
    """
    hits: list[str] = []
    for label, pattern in PII_PATTERNS:
        if re.search(pattern, text):
            hits.append(label)
            text = re.sub(pattern, f"<pii:{label}>", text)
    return text, hits


# ─────────────────────────────────────────────────────────────────────────────
# 3. Flow 模型与 FlowStore
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Flow:
    """一次"请求→响应"往返的完整档案。

    字段设计遵循一条原则：**报告要能自证，但不含秘密。**
    所以凡是"值"都脱敏，凡是"结构"（字段名、长度、状态码、耗时、指纹）都保留。
    """

    fid: str
    ts: str
    scheme: str
    method: str
    host: str
    port: int
    path: str
    url: str
    query_keys: list[str] = field(default_factory=list)
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: str = ""
    request_body_truncated: bool = False
    response_status: int = 0
    response_reason: str = ""
    response_headers: list[list[str]] = field(default_factory=list)
    response_body: str = ""
    response_body_truncated: bool = False
    response_bytes: int = 0
    duration_ms: float = 0.0
    inspected: bool = True
    error: str = ""
    note: str = ""
    #: 本条 flow 里出现过的 PII **类别**（如「手机号(CN)」）。
    #: 只存类别，不存值——报告需要"有 PII"这个结论，不需要"PII 是什么"。
    pii_labels: list[str] = field(default_factory=list)

    # —— 便捷派生属性 ——

    @property
    def content_type(self) -> str:
        for name, value in self.response_headers:
            if name.lower() == "content-type":
                return value
        return ""

    @property
    def is_tunnel(self) -> bool:
        return self.method.upper() == "CONNECT"

    def header(self, name: str) -> str:
        """取响应头（同名取第一个）。**为什么取第一个？** 因为 `Set-Cookie` 之外的头
        在 HTTP 里就该唯一；`Set-Cookie` 用 `headers_of()` 单独遍历。"""
        for key, value in self.response_headers:
            if key.lower() == name.lower():
                return value
        return ""

    def headers_of(self, name: str) -> list[str]:
        return [v for k, v in self.response_headers if k.lower() == name.lower()]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FlowStore:
    """JSONL 流量档案。

    **为什么用 JSONL 而不是一个大 JSON 数组？**
    因为中间人代理是**流式**写盘的：一个请求一封，写完就落。
    如果顶层是个数组，就必须"读全量 → 改 → 覆写全量"，
    代理跑到一半被 Ctrl-C，档案就整份损坏。
    JSONL 的语义是"追加即安全"：坏一行只丢一行。
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._counter = 0

    def next_id(self) -> str:
        self._counter += 1
        return f"f-{self._counter:06d}"

    def append(self, flow: Flow) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(flow.to_dict(), ensure_ascii=False) + "\n")

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # 坏行跳过而不是整体报错 —— 这就是 JSONL 的抗损性。
                    continue
        return rows


# ─────────────────────────────────────────────────────────────────────────────
# 4. LabOrigin：本机实验网站（故意做出"会泄密的流量"）
# ─────────────────────────────────────────────────────────────────────────────


class _LabHandler(BaseHTTPRequestHandler):
    """实验网站的请求处理器。**只绑定 127.0.0.1**，见 `LabOrigin`。"""

    server_version = "LabOrigin/1.0"
    protocol_version = "HTTP/1.1"

    # 关掉默认的 stderr 访问日志：靶标自己刷屏会淹没教学输出。
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        return

    # —— 工具方法 ——

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return ""
        return self.rfile.read(length).decode("utf-8", "replace")

    def _send(
        self,
        status: int,
        body: str = "",
        ctype: str = "text/html; charset=utf-8",
        extra: Sequence[tuple[str, str]] = (),
    ) -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        for key, value in extra:
            self.send_header(key, value)
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def _json(self, status: int, payload: dict[str, Any], extra: Sequence[tuple[str, str]] = ()) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8", extra)

    # —— 各路由 ——

    def do_GET(self) -> None:  # noqa: N802
        parts = urllib.parse.urlsplit(self.path)
        route = parts.path
        query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))

        if route == "/":
            self._send(200, LAB_INDEX_HTML)
        elif route == "/health":
            self._send(204, "")
        elif route == "/api/user":
            uid = query.get("id", "1")
            # 故意：把 id 原样拼进"SQL"，并模拟报错回显（与 Day 163 同源）。
            if "'" in uid or '"' in uid:
                # ⚠️ 这里**不能**用 `%` 格式化来拼 uid：SQL 片段里本来就含 `%`，
                # 会撞上 Python 的 `%` 转换语法（第一版就炸在这里）。
                # 教学代码尤其要避免这种"看起来对、跑起来 TypeError"的写法。
                fake_sql = "SELECT * FROM users WHERE id='" + uid + "'"
                self._send(
                    500,
                    "SQL syntax error near position 27 at line 1\n"
                    "  File \"/srv/app/models.py\", line 42, in get_user\n"
                    "    cur.execute(\"" + fake_sql + "\")\n",
                    "text/plain; charset=utf-8",
                )
                return
            if not uid.isdigit():
                self._send(400, "bad id", "text/plain; charset=utf-8")
                return
            self._json(200, {
                "id": int(uid),
                "name": "ada",
                "email": "ada@example.com",
                "role": "user",
            })
        elif route == "/search":
            # 故意：token 允许出现在查询串里（演示 sensitive-in-url）。
            token = query.get("token", "")
            note = "已收到查询" + ("（含 token）" if token else "")
            self._send(200, f"<html><body><h1>搜索</h1><p>{note}</p></body></html>")
        elif route == "/secret":
            # 故意：响应体里带 api_key（演示 secret-in-body）。
            self._json(200, {"service": "billing", "api_key": "sk_live_164_FAKE_NOT_REAL"})
        elif route == "/redirect":
            target = query.get("to", "/")
            self._send(302, "", "text/plain; charset=utf-8", [("Location", target)])
        elif route == "/slow":
            time.sleep(0.4)
            self._json(200, {"ok": True, "slept_ms": 400})
        elif route == "/large":
            filler = "<p>" + ("A" * 120) + "</p>\n"
            self._send(200, "<html><body>" + filler * 1600 + "</body></html>")
        elif route == "/admin":
            self._send(403, "forbidden", "text/plain; charset=utf-8")
        elif route == "/missing":
            self._send(404, "not found", "text/plain; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        route = urllib.parse.urlsplit(self.path).path
        body = self._read_body()
        if route == "/login":
            # 故意：Set-Cookie 缺 HttpOnly / Secure（演示 cookie-missing-flags）。
            self._json(
                200,
                {"ok": True, "user": "ada"},
                [("Set-Cookie", "lsession=abc123def456; Path=/"), ("X-Powered-By", "LabOrigin")],
            )
            return
        self._send(404, "not found", "text/plain; charset=utf-8")

    def do_PUT(self) -> None:  # noqa: N802
        self._send(200, json.dumps({"ok": True, "wrote": True}), "application/json; charset=utf-8")

    def do_DELETE(self) -> None:  # noqa: N802
        self._send(404, "not found", "text/plain; charset=utf-8")


LAB_INDEX_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>LabOrigin 164</title></head>
<body>
<h1>LabOrigin · Day 164 实验网站</h1>
<p>这个站点只在 127.0.0.1 上服务，端点行为见 code/mitm_core.py 顶部文档。</p>
<ul>
  <li>POST /login</li>
  <li>GET /api/user?id=1</li>
  <li>GET /search?q=&amp;token=</li>
  <li>GET /secret</li>
  <li>GET /redirect?to=/login</li>
  <li>GET /slow · /large · /admin · /missing</li>
</ul>
</body></html>
"""


class LabOrigin:
    """本机实验网站（上下文管理器）。

    **为什么刻意不设 `Cache-Control: no-store`、不设 CSP？**
    因为它要演示的就是"缺安全头"这件事。真实项目里这些规则应当**全部修好**，
    修好之后 `missing-security-headers` 规则自然沉默——这叫"规则的负样本"。
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        # bind 到回环：port=0 让内核分配空闲端口，避免"端口被占"打断教学。
        self.httpd = ThreadingHTTPServer((host, port), _LabHandler)
        self.httpd.daemon_threads = True
        self.host, self.port = self.httpd.server_address[:2]
        self._thread: threading.Thread | None = None

    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> "LabOrigin":
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True, name="lab-origin")
        self._thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def __enter__(self) -> "LabOrigin":
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 5. LabOpaqueTCP：假装的 TLS 服务（用来演示"隧道不可见"）
# ─────────────────────────────────────────────────────────────────────────────


class LabOpaqueTCP(socketserver.ThreadingTCPServer):
    """纯文本 TCP 服务，冒充 TLS 端点。

    **它到底演示了什么？** 客户端对 `https://` 发请求时，
    会先让代理建一条 `CONNECT` 隧道，然后在**隧道内部**握手。
    代理只能看见"隧道建立了、传了 N 字节、然后关闭"，
    **看不见里面的明文**——因为我们没有、也不该有目标的私钥。

    结论：任何号称"HTTP 代理就能看到 HTTPS 内容"的方案，
    本质上都是在客户端**装了信任的根证书**（企业 MDM / 自签 CA）。
    这在**自己拥有**的设备上是合法的内网审计手段，
    在**别人**的设备上就是中间人攻击。同一段代码，两种性质，差别只在授权。
    """

    allow_reuse_address = True

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        super().__init__((host, port), _OpaqueHandler)
        self.host, self.port = self.server_address[:2]
        self._thread: threading.Thread | None = None

    def start(self) -> "LabOpaqueTCP":
        self._thread = threading.Thread(target=self.serve_forever, daemon=True, name="lab-opaque")
        self._thread.start()
        return self

    def stop(self) -> None:
        self.shutdown()
        self.server_close()


class _OpaqueHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        # 发一段"看起来像某种协议握手"的字节，然后回声。
        # 客户端如果按 TLS 去解析它，会在握手阶段就失败 —— 这正是我们要的。
        try:
            self.request.sendall(b"\x16\x03\x03\x00\x2a" + b"LAB-OPAQUE-164" + b"\n")
            self.request.settimeout(0.5)
            while True:
                chunk = self.request.recv(4096)
                if not chunk:
                    break
                self.request.sendall(chunk)
        except (OSError, socket.timeout):
            return


# ─────────────────────────────────────────────────────────────────────────────
# 6. AuditProxy：纯 socket 实现的正向 HTTP 代理
# ─────────────────────────────────────────────────────────────────────────────


class _ProxyHandler(socketserver.StreamRequestHandler):
    """一次连接 → 一次请求 → 一条 flow。

    **为什么"一次连接只处理一个请求"？** 为了让代码配得上"教学"两个字。
    真实代理要处理 keep-alive 长连接、流水线（pipelining）、分块请求体……
    本课主动放弃这些，换来了"60 行核心逻辑就能读懂"。
    代价写清楚：**不支持 keep-alive**，我们统一回 `Connection: close`，
    客户端（urllib / requests）都会正确降级，这是 HTTP/1.1 允许的行为。
    """

    server: "AuditProxy"   # 由 socketserver 在实例化时注入

    def handle(self) -> None:
        started = time.monotonic()
        raw_line = self.rfile.readline(65537)
        if not raw_line:
            return
        try:
            request_line = raw_line.decode("latin-1").rstrip("\r\n")
        except Exception:
            return
        parts = request_line.split(" ")
        if len(parts) != 3:
            self._plain(400, "Bad Request")
            return
        method, target, _version = parts[0].upper(), parts[1], parts[2]

        headers = self._read_headers()

        if method == "CONNECT":
            self._handle_connect(target, headers, started)
            return

        try:
            scheme, host, port, path = self._resolve(method, target, headers)
        except ValueError as exc:
            self._plain(400, f"Bad Request: {exc}")
            return

        # —— 门禁：代理自己也要守范围，不能变成"开放代理" ——
        if not self.server.scope.check_host(host) or not self.server.scope.check_port(port):
            self._plain(403, "Forbidden: out of scope")
            self.server.log(f"[gate] 拒绝 {method} {host}:{port}{path}")
            return

        body = self._read_client_body(headers, method)
        self._forward(method, scheme, host, port, path, headers, body, started)

    def _plain(self, status: int, text: str) -> None:
        """回一个最小可读的错误响应。

        **为什么不直接甩掉连接？** 因为"连接被重置"和"代理拒绝了请求"
        在客户端看来很像，排查时会浪费大量时间。
        明确回一个带原因的 4xx/5xx，是把"代理做了什么"变成可观测的事实。
        """
        body = text.encode("utf-8")
        reason = http.client.responses.get(status, "Error")
        head = (
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Type: text/plain; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("latin-1")
        self.wfile.write(head + body)

    # —— 解析与读包 ——

    def _read_headers(self) -> list[tuple[str, str]]:
        headers: list[tuple[str, str]] = []
        while True:
            line = self.rfile.readline(65537)
            if not line or line in (b"\r\n", b"\n"):
                break
            text = line.decode("latin-1").rstrip("\r\n")
            if ":" not in text:
                continue
            name, _, value = text.partition(":")
            headers.append((name.strip(), value.strip()))
        return headers

    def _read_client_body(self, headers: list[tuple[str, str]], method: str) -> bytes:
        lower = {k.lower(): v for k, v in headers}
        if "transfer-encoding" in lower and "chunked" in lower["transfer-encoding"].lower():
            return self._read_chunked()
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            length = int(lower.get("content-length") or 0)
            if length > 0:
                return self.rfile.read(length)
        return b""

    def _read_chunked(self) -> bytes:
        """读分块请求体。**为什么要支持？** 因为 `requests` 在传文件/生成器时
        会自动改用 `Transfer-Encoding: chunked`；不支持的代理会静默截断请求体，
        表现为"服务端收到的表单是空的"——一个极其难查的 bug。"""
        chunks: list[bytes] = []
        while True:
            size_line = self.rfile.readline(65537).strip()
            if not size_line:
                break
            try:
                size = int(size_line.split(b";")[0], 16)
            except ValueError:
                break
            if size == 0:
                self.rfile.readline(65537)  # 末尾 CRLF
                break
            chunks.append(self.rfile.read(size))
            self.rfile.readline(65537)  # 每块后的 CRLF
        return b"".join(chunks)

    def _resolve(self, method: str, target: str, headers: list[tuple[str, str]]) -> tuple[str, str, int, str]:
        """把请求行里的 target 还原成 (scheme, host, port, path)。

        正向代理收到的通常是**绝对 URI 形式**（`GET http://h:p/p HTTP/1.1`），
        但也可能是**源站形式**（`GET /p HTTP/1.1` + `Host:` 头）——
        后者出现在"客户端把自己配成代理"或某些库的实现里。
        两种都要支持，否则会看到莫名其妙的 400。
        """
        if target.startswith("http://") or target.startswith("https://"):
            parts = urllib.parse.urlsplit(target)
            scheme = parts.scheme
            host = parts.hostname or ""
            port = parts.port or (443 if scheme == "https" else 80)
            path = urllib.parse.urlunsplit(("", "", parts.path or "/", parts.query, ""))
            return scheme, host, port, path

        if target.startswith("/"):
            host_header = ""
            for key, value in headers:
                if key.lower() == "host":
                    host_header = value
                    break
            if not host_header:
                raise ValueError("源站形式请求缺少 Host 头")
            host, _, port_text = host_header.partition(":")
            port = int(port_text) if port_text else 80
            return "http", host, port, target

        raise ValueError(f"无法解析的 target：{target!r}")

    # —— 转发与记录 ——

    def _forward(
        self,
        method: str,
        scheme: str,
        host: str,
        port: int,
        path: str,
        headers: list[tuple[str, str]],
        body: bytes,
        started: float,
    ) -> None:
        url = f"{scheme}://{host}:{port}{path}"
        raw_url, query_keys = redact_url(url)
        # ⚠️ 只脱敏 URL 是不够的：`path` 里**同样带着查询串**。
        # 如果档案把未脱敏的 path 也存一份，前面所有脱敏工作就全白做了
        # （自检第 ② 条就是专门抓这个的：`tk_live_164_fake` 曾经从这里漏出去）。
        safe_path = _redact_query_in_path(path)

        # 构造转发头：剔除逐跳头；**剔除 Accept-Encoding**（见下方长注释）。
        fwd: list[tuple[str, str]] = []
        for key, value in headers:
            low = key.lower()
            if low in HOP_BY_HOP:
                continue
            # ⚠️ 关键设计决策：代理**主动去掉 Accept-Encoding**。
            # 为什么？因为我们要把响应体当"文本证据"读。
            # 如果让服务端返回 gzip，落到档案里就是一串二进制垃圾，
            # 规则引擎要么看不懂，要么不得不再实现一遍解压（还可能踩
            # `gzip` 嵌套、`br`(brotli) 不支持的坑）。
            # 代价：代理会拿到更大的响应体（多用带宽），
            # 以及**改变了客户端的观测**（客户端本来可能想要压缩）。
            # 真实生产代理应当"透传 + 按需解压"，本课选"简化 + 明说"。
            if low == "accept-encoding":
                continue
            if low == "content-length":
                continue  # 长度我们按去压缩后的真实 body 重算
            fwd.append((key, value))
        fwd.append(("Content-Length", str(len(body))))
        fwd.append(("Connection", "close"))

        req_body_text = body.decode("utf-8", "replace")
        req_body_redacted, body_hits = redact_body(req_body_text, _ct_of(headers))
        # 请求体同样要擦 PII。**但"擦掉"和"检测"必须分开**：
        # 值擦掉之后正则再也匹配不到，所以必须在这里**当场**把命中类别记下来
        # （`pii_labels` 字段），否则 `pii-in-request` 规则会永远沉默。
        req_body_redacted, req_pii = mask_pii(req_body_redacted)

        status, reason, resp_headers, resp_bytes, error = 0, "", [], b"", ""
        try:
            conn = http.client.HTTPConnection(host, port, timeout=6)
            conn.request(method, path, body=body or None, headers=dict(fwd))
            resp = conn.getresponse()
            status, reason = resp.status, resp.reason
            resp_headers = [(k, v) for k, v in resp.getheaders()]
            resp_bytes = resp.read()
            conn.close()
        except (OSError, http.client.HTTPException) as exc:
            error = f"{type(exc).__name__}: {exc}"

        duration_ms = (time.monotonic() - started) * 1000.0

        # 响应正文：解码 → PII 擦除 → 截断
        try:
            resp_text = resp_bytes.decode("utf-8", "replace")
        except Exception:
            resp_text = ""
        # ⚠️ 顺序很重要：**先脱敏字段值，再擦除 PII，最后截断。**
        # 反过来（先截断）会让"刚好跨过截断点的密钥"漏出原文；
        # 而漏掉"响应体也要脱敏"这一步，会让 /secret 这类端点把密钥原样写进档案
        # —— 一个"审计工具自己成了泄密渠道"的绝佳反面教材（本模块第一版就是这样）。
        resp_text, resp_hits = redact_body(resp_text, _ct_of(resp_headers))
        resp_text, resp_pii = mask_pii(resp_text)
        truncated = len(resp_bytes) > MAX_BODY_BYTES
        if truncated:
            resp_text = resp_text[:MAX_BODY_BYTES]

        # 回给客户端（失败则 502）
        if error:
            self._plain(502, f"Bad Gateway: {error}")
        else:
            self._respond_to_client(status, reason, resp_headers, resp_bytes)

        flow = Flow(
            fid=self.server.store.next_id(),
            ts=datetime.now().isoformat(timespec="milliseconds"),
            scheme=scheme,
            method=method,
            host=host,
            port=port,
            path=safe_path,
            url=raw_url,
            query_keys=query_keys,
            request_headers=redact_mapping(headers),
            request_body=req_body_redacted,
            response_status=status,
            response_reason=reason,
            response_headers=[[k, v] if k.lower() not in REDACT_HEADERS else [k, value_fingerprint(v)]
                              for k, v in resp_headers],
            response_body=resp_text,
            response_body_truncated=truncated,
            response_bytes=len(resp_bytes),
            duration_ms=round(duration_ms, 2),
            inspected=True,
            error=error,
            note=_build_note(body_hits, resp_hits),
            pii_labels=sorted(set(req_pii) | set(resp_pii)),
        )
        self.server.store.append(flow)
        self.server.log(
            f"[flow] {flow.fid} {method:6s} {status or '---':>3} "
            f"{flow.duration_ms:8.1f}ms  {raw_url}"
        )

    def _respond_to_client(
        self, status: int, reason: str, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        lines = [f"HTTP/1.1 {status} {reason}"]
        for key, value in headers:
            if key.lower() in HOP_BY_HOP or key.lower() == "content-length":
                continue
            lines.append(f"{key}: {value}")
        lines.append(f"Content-Length: {len(body)}")
        lines.append("Connection: close")
        payload = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")
        self.wfile.write(payload + body)

    def _handle_connect(
        self, target: str, headers: list[tuple[str, str]], started: float
    ) -> None:
        """处理 `CONNECT`：建隧道 + **如实记录"看不见"**。

        这段代码是本课的价值核心。它不假装自己能解密，
        而是把"不可见"这件事**变成一条可统计的覆盖缺口**，
        最终把退出码推到 `4`——告诉上层"这轮结论不完整"。
        """
        host, _, port_text = target.partition(":")
        try:
            port = int(port_text or 443)
        except ValueError:
            port = 443
        raw_url = f"https://{host}:{port}"
        in_scope = self.server.scope.check_host(host) and self.server.scope.check_port(port)
        if not in_scope:
            self._plain(403, "Forbidden: out of scope")
            return

        error = ""
        upstream: socket.socket | None = None
        try:
            upstream = socket.create_connection((host, port), timeout=3)
        except OSError as exc:
            error = f"{type(exc).__name__}: {exc}"

        if upstream is None:
            self._plain(502, f"Bad Gateway: {error}")
        else:
            self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            self.wfile.flush()
            self._blind_pipe(upstream)
            upstream.close()

        duration_ms = (time.monotonic() - started) * 1000.0
        flow = Flow(
            fid=self.server.store.next_id(),
            ts=datetime.now().isoformat(timespec="milliseconds"),
            scheme="https",
            method="CONNECT",
            host=host,
            port=port,
            path="",
            url=raw_url,
            request_headers=redact_mapping(headers),
            response_status=200 if upstream else 502,
            response_reason="Connection Established" if upstream else "Bad Gateway",
            duration_ms=round(duration_ms, 2),
            inspected=False,
            error=error,
            note="TLS 隧道：无 MITM 证书，内容不可见",
        )
        self.server.store.append(flow)
        self.server.log(f"[flow] {flow.fid} CONNECT {raw_url} → inspected=False（覆盖缺口）")

    def _blind_pipe(self, upstream: socket.socket) -> None:
        """在两条 socket 之间盲转发字节，直到任一端关闭或超时。

        **为什么要有 `TUNNEL_SECONDS` 上限？** 因为隧道可能是长连接（WebSocket、
        流式 API）。教学实验里必须能"自己结束"，否则脚本会挂住不返回。
        生产实现应当无限期转发直到对端关闭 —— 这个差异要写出来，不能装作没差。
        """
        deadline = time.monotonic() + TUNNEL_SECONDS
        client = self.connection
        sockets = [client, upstream]
        for sock in sockets:
            sock.setblocking(False)
        try:
            while time.monotonic() < deadline:
                ready, _, _ = select.select(sockets, [], [], 0.2)
                if not ready:
                    continue
                for src in ready:
                    dst = upstream if src is client else client
                    try:
                        chunk = src.recv(65536)
                    except (BlockingIOError, InterruptedError):
                        continue
                    except OSError:
                        return
                    if not chunk:
                        return
                    try:
                        dst.sendall(chunk)
                    except OSError:
                        return
        finally:
            for sock in sockets:
                sock.setblocking(True)


class AuditProxy:
    """本机中间人代理（上下文管理器）。

    用法：

        with LabOrigin() as origin, AuditProxy("flows.jsonl") as proxy:
            ... 让客户端把 proxy.url 配成 http 代理 ...

    **绝不监听非回环地址。** 构造函数里显式断言这一点：
    一个"监听 0.0.0.0 的开放 HTTP 代理"在互联网上会在几分钟内被扫到并滥用，
    后果是真实的法律责任。这不是可以留给用户"自己小心"的事项。
    """

    def __init__(
        self,
        store_path: str | Path,
        host: str = "127.0.0.1",
        port: int = 0,
        scope: Scope | None = None,
        verbose: bool = True,
    ) -> None:
        if host not in LOOPBACK_HOSTS:
            raise AuthorizationError(
                f"AuditProxy 只允许监听回环地址，收到 {host!r}。"
                "开放代理是真实的法律风险，本工具不提供这个开关。"
            )
        self.scope = scope or Scope()

        class _Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self._srv = _Server((host, port), _ProxyHandler)
        self._srv.store = FlowStore(store_path)
        self._srv.scope = self.scope
        self._srv.log = self._log if verbose else (lambda _m: None)
        self.host, self.port = self._srv.server_address[:2]
        self._thread: threading.Thread | None = None
        self._lines: list[str] = []
        self.store: FlowStore = self._srv.store

    def _log(self, message: str) -> None:
        self._lines.append(message)
        print(message, flush=True)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> "AuditProxy":
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True, name="audit-proxy")
        self._thread.start()
        return self

    def stop(self) -> None:
        self._srv.shutdown()
        self._srv.server_close()

    def __enter__(self) -> "AuditProxy":
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()


#: 隧道盲转发的时长上限（秒）。见 `_blind_pipe` 的说明。
TUNNEL_SECONDS = 1.5


# ─────────────────────────────────────────────────────────────────────────────
# 7. LabSession：脚本化客户端（产生真实流量）
# ─────────────────────────────────────────────────────────────────────────────


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """把"不跟随重定向"变成**显式**行为。

    `urllib.request.build_opener()` 在你不传 `HTTPRedirectHandler` 时
    会**自动补上默认实现**——也就是说"我组装 opener 时没装它"并**不**等于
    "它不在里面"。这是一个非常容易踩的坑（本模块第一版就踩了：
    重定向被悄悄跟到 `/login`，报告里看到的是 404 而不是 302，
    `redirect-chain` 规则永远沉默）。

    正确做法：提供**子类**并让 `redirect_request()` 返回 `None`，
    urllib 就会把 3xx 当成 `HTTPError` 抛给我们——正好是我们想要的"停在第一跳"。
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


class LabSession:
    """走代理发请求的"审计会话"。

    **为什么用 `urllib` 而不是 `requests`？** 为了保持零第三方依赖——
    教学代码在"别人的机器上能不能跑"比"写起来短两行"重要得多。
    `urllib` 走代理只需一个 `ProxyHandler`，功能完全够用。

    **为什么默认不跟随重定向？** 因为我们要**数**重定向链。
    自动跟随会把 302 藏起来，`redirect-chain` 规则就永远抓不到东西。
    去掉 `HTTPRedirectHandler` 后，302 会以 `HTTPError` 形式抛出，
    我们照样能读到状态码和头 —— 这正是"只跟随到第一跳"的实现方式。
    """

    def __init__(self, proxy_url: str, scope: Scope | None = None, rate: float = 8.0) -> None:
        self.proxy_url = proxy_url
        self.scope = scope or Scope()
        self.rate = rate
        self._last = 0.0
        # 只装 ProxyHandler，**不装** HTTPRedirectHandler → 不跟随跳转
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}),
            _NoRedirect(),                # ← 必须显式传入，见 _NoRedirect 的说明
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(),
        )

    def _throttle(self) -> None:
        gap = 1.0 / max(self.rate, 0.001)
        wait = self._last + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """发一次请求。**返回字典而不是抛异常** —— 审计工具要"继续跑完"，
        单个目标失败不能中断整轮；失败本身也是一条要记录的事实。"""
        host, port = self.scope.check_url(url)  # 越界在这里就抛，不进网络
        self._throttle()
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                return {"status": resp.status, "ok": True, "body": resp.read(MAX_BODY_BYTES).decode("utf-8", "replace")}
        except urllib.error.HTTPError as err:
            # 4xx/5xx 以及"没被跟随"的 3xx 都会走到这里，这是**预期路径**。
            return {"status": err.code, "ok": False, "body": err.read(MAX_BODY_BYTES).decode("utf-8", "replace")}
        except Exception as exc:  # noqa: BLE001 —— 网络层什么都可能抛
            return {"status": 0, "ok": False, "body": "", "error": f"{type(exc).__name__}: {exc}"}

    # —— 具体动作（每个都对应 LabOrigin 的一个端点）——

    def run_demo(self, origin_base: str, opaque_port: int | None = None) -> list[dict[str, Any]]:
        """跑一遍"典型审计会话"，返回每步结果摘要。

        步骤顺序是**刻意设计**的：先看正常流量（建立基线），
        再进行有风险的探测，最后演示不可见的隧道。
        这样报告里的发现能对应上"哪一步产生的"。
        """
        results: list[dict[str, Any]] = []

        def step(label: str, **kwargs: Any) -> None:
            res = self.request(**kwargs)
            res["label"] = label
            results.append(res)
            print(f"  · {label:<28} → status={res['status']:<4} ok={res['ok']}", flush=True)

        step("首页（建立基线）", method="GET", url=f"{origin_base}/")
        step("健康检查", method="GET", url=f"{origin_base}/health")
        step("正常 API 查询", method="GET", url=f"{origin_base}/api/user?id=1")
        step("报错回显探测", method="GET", url=f"{origin_base}/api/user?id=1%27")
        step(
            "登录（明文口令）",
            method="POST",
            url=f"{origin_base}/login",
            body=urllib.parse.urlencode({"username": "ada", "password": "Sup3rSecret!"}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # 注意：这里把 token 放进查询串**是为了演示规则**，
        # 真实审计中你应当把这种写法当成一个需要立即修的问题。
        step("token 出现在 URL", method="GET", url=f"{origin_base}/search?q=python&token=tk_live_164_fake")
        step("响应体泄密", method="GET", url=f"{origin_base}/secret")
        step("重定向链", method="GET", url=f"{origin_base}/redirect?to=/login")
        step("慢响应", method="GET", url=f"{origin_base}/slow")
        step("大响应（触发截断）", method="GET", url=f"{origin_base}/large")
        step("权限边界 403", method="GET", url=f"{origin_base}/admin")
        step(
            "写方法（破坏只读）",
            method="PUT",
            url=f"{origin_base}/api/user/1",
            body=b'{"role":"admin"}',
            headers={"Content-Type": "application/json"},
        )
        step(
            "PII 出现在请求体",
            method="POST",
            url=f"{origin_base}/login",
            body=urllib.parse.urlencode({"username": "13800138000", "password": "x"}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if opaque_port:
            # 最后一步：https 隧道。此时客户端会先发 CONNECT，
            # 代理只能记下"有这么一条隧道"，然后握手失败。
            res = self.request(method="GET", url=f"https://127.0.0.1:{opaque_port}/")
            res["label"] = "TLS 隧道（不可见）"
            results.append(res)
            print(f"  · {'TLS 隧道（不可见）':<26} → 预期失败：{res.get('error', res['status'])}", flush=True)

        return results


# ─────────────────────────────────────────────────────────────────────────────
# 8. FlowAnalyzer：规则引擎
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Finding:
    """一条发现。

    `why` 字段是刻意设计的：**每一条发现都必须解释"为什么这是问题"**，
    而不是只丢一个标签。理由是报告会被"非本工具作者"阅读（运维、开发、客户），
    没有 `why` 的规则输出会退化成"看名字猜意思"。
    """

    rule: str
    severity: str
    confidence: float
    flow_id: str
    url: str
    evidence: str
    why: str
    fix: str

    @property
    def priority(self) -> float:
        return round(SEVERITY_SCORE.get(self.severity, 0.5) * self.confidence, 2)

    @property
    def level(self) -> str:
        """把连续优先级压成 P0~P3 四档，便于人读。"""
        p = self.priority
        if p >= 3.0:
            return "P0"
        if p >= 2.0:
            return "P1"
        if p >= 1.0:
            return "P2"
        return "P3"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["priority"] = self.priority
        data["level"] = self.level
        return data


class FlowAnalyzer:
    """把 flow 列表变成 findings。

    **设计原则：一条 flow 可以触发多条规则，一条规则可以命中多条 flow。**
    不要试图"归并"成一条 —— 归并会丢证据。
    报告的可信度来自"每个结论都能点回到具体的那一条 flow"。
    """

    def __init__(self, scope: Scope | None = None) -> None:
        self.scope = scope or Scope()
        self.findings: list[Finding] = []
        self.facts: dict[str, Any] = {}

    # —— 入口 ——

    def analyze(self, rows: Sequence[dict[str, Any]]) -> list[Finding]:
        self.findings = []
        self._last_rows = list(rows)   # 供 scope_violation 做二次校验
        for row in rows:
            self._analyze_one(row)
        self._summarize(rows)
        return self.findings

    def _add(
        self,
        row: dict[str, Any],
        rule: str,
        severity: str,
        confidence: float,
        evidence: str,
        why: str,
        fix: str,
    ) -> None:
        self.findings.append(
            Finding(
                rule=rule,
                severity=severity,
                confidence=confidence,
                flow_id=row.get("fid", "?"),
                url=row.get("url", ""),
                evidence=evidence,
                why=why,
                fix=fix,
            )
        )

    # —— 单条 flow 的规则 ——

    def _analyze_one(self, row: dict[str, Any]) -> None:
        scheme = row.get("scheme", "http")
        is_plain = scheme == "http"
        method = (row.get("method") or "").upper()
        status = int(row.get("response_status") or 0)

        # R10 CONNECT 隧道：覆盖缺口（最先判定，因为它决定"其他规则是否可信"）
        if method == "CONNECT" or not row.get("inspected", True):
            self._add(
                row, "tls-tunnel-uninspected", "medium", 1.0,
                f"CONNECT {row.get('url')}：隧道内容未解密（{row.get('note') or '无说明'}）",
                "中间人代理在没有目标私钥（或客户端未安装自签 CA）时，"
                "HTTPS 流量只是被**转发**，不是被**读懂**。"
                "报告里出现这种 flow，意味着这一部分流量**没有结论**——"
                "不能写成'未发现问题'，那是把'看不见'说成'没问题'。",
                "要么接受盲区并在报告里显式标注覆盖率；"
                "要么在自己拥有、且已获授权的终端上部署受信任的内网 CA 做解密。",
            )
            return

        # R2 敏感参数出现在 URL
        if row.get("query_keys"):
            keys = ", ".join(sorted(set(row["query_keys"])))
            self._add(
                row, "sensitive-in-url", "medium", 0.95,
                f"URL 查询串含敏感参数：{keys}（值已脱敏）",
                "URL 会被沿途的每一层记录下来：访问日志、CDN 日志、浏览器历史、"
                "以及跨站跳转时的 Referer 头。把凭据放在查询串，等于主动把它抄送给所有人。",
                "凭据走请求体或自定义头；必须放 URL 的场景用一次性、短过期、可撤销的签名。",
            )

        # R15 大响应（先记录，供截断说明）
        if row.get("response_body_truncated"):
            self._add(
                row, "response-body-truncated", "info", 1.0,
                f"响应体 {row.get('response_bytes')} 字节，档案只保留前 {MAX_BODY_BYTES} 字节",
                "档案截断意味着**规则引擎没有看到全部内容**："
                "如果泄密片段落在截断之后，本工具会漏报。"
                "把这条记成 info 而不是忽略，是为了让『漏报的可能性』本身可见。",
                "需要完整正文时单独导出该 flow 的响应体（注意它可能含 PII）。",
            )

        # R9 重定向链
        if status in (301, 302, 303, 307, 308):
            self._add(
                row, "redirect-chain", "info", 1.0,
                f"{status} → Location: {row.get('response_headers') and _find_header(row, 'location')}",
                "重定向是**审计视野的断点**：本工具默认不跟随跳转，"
                "所以 Location 指向的下一跳如果没有被单独访问，它的响应就没有被检查过。",
                "把重定向目标加入待审清单（这正是 Day 162 目录爆破要产出的东西）。",
            )

        # R8 服务端错误
        if status >= 500:
            self._add(
                row, "server-error", "medium", 0.9,
                f"HTTP {status} {row.get('response_reason')}",
                "5xx 说明服务端在自己的逻辑里摔了一跤。"
                "如果这一跤是**被输入触发的**（例如带引号的 id），"
                "它同时是『缺少输入校验』的证据（见 R6 报错回显）。",
                "修输入校验；把 5xx 纳入监控与告警，不要让它们出现在生产流量里。",
            )

        # R11 非只读方法
        if method in ("PUT", "PATCH", "DELETE", "POST") and not _is_benign_post(row):
            self._add(
                row, "state-changing-method", "info", 1.0,
                f"观测到 {method} {row.get('path')}",
                "审计的第一原则是**只读**。写方法一旦执行，"
                "你就改变了被审对象的状态——它不再是『审计』，而成了『操作』。"
                "很多合规体系里这两件事的授权等级完全不同。",
                "审计流量只发幂等方法（GET/HEAD）；需要验证写逻辑时，用专门的测试账号 + 一次性数据。",
            )

        # R1 明文凭据（请求体）
        body = row.get("request_body") or ""
        ctype = _ct_of_rows(row.get("request_headers") or {})
        if is_plain and _body_has_sensitive_marker(body, ctype):
            self._add(
                row, "cleartext-credential", "high", 0.95,
                f"{method} {row.get('path')} 的请求体含敏感字段（值已脱敏为指纹）",
                "HTTP 是明文协议：路径上的每一个设备（交换机镜像、Wi-Fi 热点、"
                "运营商、企业网关）都能完整读到这段请求体。"
                "这里记录的是**字段指纹**而非明文——足以证明泄露发生，不足以二次泄露。",
                "全站 HTTPS + HSTS；凭据禁止出现在 URL；服务端只存不可逆哈希。",
            )

        # R3 Authorization 头走明文
        req_headers = {k.lower(): v for k, v in (row.get("request_headers") or {}).items()}
        if is_plain and "authorization" in req_headers:
            self._add(
                row, "auth-header-cleartext", "high", 0.9,
                f"明文连接上发送了 Authorization 头（值：{req_headers['authorization']}）",
                "Bearer Token 本身就是『一次性通行证』。"
                "在明文连接上发送它，等价于把这个通行证贴在信封外面寄出去。",
                "强制 HTTPS；对令牌设置短过期与受众（audience）限制。",
            )

        # R4 Cookie 缺标记
        for cookie in _headers_of(row, "set-cookie"):
            missing = [flag for flag in ("HttpOnly", "Secure") if flag.lower() not in cookie.lower()]
            if missing:
                self._add(
                    row, "cookie-missing-flags", "medium", 0.85,
                    f"Set-Cookie 缺少 {'/'.join(missing)}：{cookie.split(';')[0]}…",
                    "HttpOnly 挡住 XSS 偷 cookie（JS 读不到 `document.cookie`）；"
                    "Secure 挡住明文连接上的 cookie 泄露。缺一个就少一道闸门，"
                    "缺两个等于把会话令牌放在两处可被拿走的地方。",
                    "所有会话 cookie 加 `HttpOnly; Secure; SameSite=Lax`（或 Strict）。",
                )

        # R14 服务端指纹外泄
        for banner in ("server", "x-powered-by", "x-aspnet-version"):
            value = _find_header(row, banner)
            if value:
                self._add(
                    row, "server-banner", "info", 0.8,
                    f"响应头 {banner}: {value}",
                    "版本号是攻击者的**检索关键词**：知道你是哪个版本，"
                    "就能直接去找那个版本的已知漏洞（CVE），不用试错。",
                    "隐藏或统一化版本头；真正的防线是「及时打补丁」，不是靠藏版本号。",
                )

        # R6 报错回显（响应体）
        resp_body = row.get("response_body") or ""
        for label, pattern in ERROR_SIGNATURES:
            if re.search(pattern, resp_body):
                self._add(
                    row, "error-disclosure", "high", 0.9,
                    f"响应体出现{label}特征（{pattern[:40]}…）",
                    "内部实现细节出现在响应里，等于把数据模型、文件路径、"
                    "甚至**注入点**主动告诉对方。Day 163 的 SQLi 检测正是靠这类回显做第一段判定的。",
                    "统一错误页：对外只回「请求无法处理」+ 追踪 ID；细节只写进服务端日志。",
                )
                break

        # R7 响应体泄密
        ct = (row.get("response_headers") and _find_header(row, "content-type")) or ""
        if not row.get("response_body_truncated") and _body_has_sensitive_marker(resp_body, ct):
            self._add(
                row, "secret-in-response-body", "high", 0.85,
                "响应体包含敏感字段名（值已脱敏）",
                "密钥出现在响应体，意味着它会被：浏览器缓存、代理缓冲、"
                "客户端日志、以及任何抓包工具完整记录。API Key 一类的长期凭据**绝不该**下发到前端。",
                "密钥只在服务端使用；下发给客户端的只能是短期、限定范围、可撤销的令牌。",
            )

        # R5 缺安全响应头（只对 HTML 200 报告，避免噪音）
        if status == 200 and "text/html" in ct.lower():
            missing = [h for h in ("x-content-type-options", "content-security-policy", "strict-transport-security")
                       if not _find_header(row, h)]
            if missing:
                self._add(
                    row, "missing-security-headers", "low", 0.8,
                    f"HTML 响应缺少：{', '.join(missing)}",
                    "这些头是**低成本高收益**的默认防线："
                    "nosniff 阻止 MIME 混淆，CSP 限制脚本来源，HSTS 阻止降级到明文。"
                    "缺了不一定会被打穿，但一旦被打穿，它们本可以把影响限制住。",
                    "在反向代理/框架层统一注入这些头（一个中间件搞定，不要逐页面加）。",
                )

        # R12 慢响应
        if float(row.get("duration_ms") or 0) >= SLOW_MS:
            self._add(
                row, "slow-response", "low", 0.7,
                f"耗时 {row.get('duration_ms')}ms（阈值 {SLOW_MS}ms）",
                "慢响应对审计有两个含义：① 可能是**无索引查询**一类的性能问题；"
                "② 若某些输入能显著拉长响应时间，那它可能是**时间盲注**的入口"
                "（Day 163 刻意排除了时间盲注探测，但流量层能看到它的痕迹）。",
                "巡检慢查询日志；把响应时间纳入监控基线。",
            )

        # R13 请求体里的 PII（用捕获时记下的类别，而不是重扫正文——
        # 正文里的 PII 已经被擦掉了，重扫必然为空）
        pii_hits = row.get("pii_labels") or []
        if pii_hits:
            self._add(
                row, "pii-in-request", "medium", 0.8,
                f"请求体含 PII：{', '.join(sorted(set(pii_hits)))}（档案中已擦除）",
                "即使这是用户「正常提交」的数据，把它**完整记进审计档案**本身就是合规风险"
                "（最小必要原则）。审计记录应当证明『发生过』，而不是复制『内容』。",
                "审计档案默认擦除 PII；确需留存时做加密 + 访问审计 + 保留期限制。",
            )

    # —— 汇总 ——

    def _summarize(self, rows: Sequence[dict[str, Any]]) -> None:
        inspected = [r for r in rows if r.get("inspected", True)]
        tunnels = [r for r in rows if not r.get("inspected", True)]
        errors = [r for r in rows if r.get("error")]
        self.facts = {
            "flows": len(rows),
            "inspected": len(inspected),
            "uninspected": len(tunnels),
            "transport_errors": len(errors),
            "status_classes": _status_classes(rows),
            "methods": _count_by(rows, "method"),
            "rules_hit": _count_by(self.findings, "rule"),
            "severity_counts": _count_by(self.findings, "severity"),
            "coverage_percent": round(100.0 * len(inspected) / len(rows), 1) if rows else 0.0,
        }

    # —— 结论 ——

    @property
    def coverage_incomplete(self) -> bool:
        """覆盖不完整 = 有看不见的流量，或有传输错误。

        **为什么传输错误也算不完整？** 因为"连不上"和"没问题"在报告里长得一样：
        都是"没有发现"。如果不显式区分，报告就在撒谎。
        """
        return bool(self.facts.get("uninspected")) or bool(self.facts.get("transport_errors"))

    @property
    def scope_violation(self) -> bool:
        for row in getattr(self, "_last_rows", []):
            host = row.get("host") or ""
            if not self.scope.check_host(host):
                return True
        return False

    @property
    def findings_by_severity(self) -> list[Finding]:
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        return sorted(self.findings, key=lambda f: (order.get(f.severity, 9), -f.priority, f.flow_id))

    def exit_code(self) -> int:
        """语义化退出码。判定顺序就是**优先级**（见README 3.8 的说明）。"""
        if self.scope_violation:
            return EXIT_GATE_REJECTED
        if self.coverage_incomplete:
            return EXIT_INCOMPLETE
        if any(f.level in ("P0", "P1") for f in self.findings):
            return EXIT_FINDINGS
        return EXIT_OK


#: `FlowAnalyzer` 内部用到的模块级小工具（放在类后面，避免打断类定义的可读性）。


def _redact_query_in_path(path: str) -> str:
    """脱敏 `path` 里的查询串（保留结构，值换指纹）。见 `_forward` 的踩坑注释。"""
    if "?" not in path:
        return path
    base, _, query = path.partition("?")
    pairs = urllib.parse.parse_qsl(query, keep_blank_values=True)
    safe = [
        (key, value_fingerprint(value) if key.lower() in SENSITIVE_KEYS else value)
        for key, value in pairs
    ]
    return base + "?" + urllib.parse.urlencode(safe)


def _build_note(body_hits: Sequence[str], resp_hits: Sequence[str]) -> str:
    """把"这条 flow 命中了哪些敏感字段"写成一句话，作为档案里的注释。"""
    bits: list[str] = []
    if body_hits:
        bits.append("请求体命中敏感字段：" + ",".join(sorted(set(body_hits))))
    if resp_hits:
        bits.append("响应体命中敏感字段：" + ",".join(sorted(set(resp_hits))))
    return "；".join(bits)


def _find_header(row: dict[str, Any], name: str) -> str:
    for key, value in row.get("response_headers") or []:
        if key.lower() == name.lower():
            return value
    return ""


def _headers_of(row: dict[str, Any], name: str) -> list[str]:
    return [v for k, v in (row.get("response_headers") or []) if k.lower() == name.lower()]


def _ct_of(headers: list[tuple[str, str]]) -> str:
    for key, value in headers:
        if key.lower() == "content-type":
            return value
    return ""


def _ct_of_rows(headers: dict[str, str]) -> str:
    for key, value in headers.items():
        if key.lower() == "content-type":
            return value
    return ""


def _is_benign_post(row: dict[str, Any]) -> bool:
    """判断一个 POST 是否"无害"。

    **为什么需要这个豁免？** 因为登录、搜索这类业务本身就是 POST，
    把它们全报成"破坏只读"会让规则淹没在噪音里。
    判定标准：请求体里**没有敏感字段**且**没有 PII** → 视为常规业务提交。
    这条豁免有代价（真实的写操作可能被漏掉），所以它是**显式**的、写在这里的。
    """
    body = row.get("request_body") or ""
    if row.get("pii_labels"):
        return False
    if _body_has_sensitive_marker(body, _ct_of_rows(row.get("request_headers") or {})):
        return False
    return True


def _body_has_sensitive_marker(body: str, ctype: str) -> bool:
    """body 里是否出现"脱敏后的敏感字段"标记。

    注意：代理已把值换成 `<redacted:...>`，所以这里**只能**靠
    字段名出现（`password=` 或 `"api_key": "<redacted:...>"`）来判定。
    这个"先脱敏、再检测"的顺序是本课的关键：
    检测逻辑**看不到明文也能工作**。
    """
    if not body:
        return False
    lowered = body.lower()
    # ⚠️ 注意这里两种写法都要认：表单体被 urlencode 后，冒号会变成 %3A。
    # 只认 "redacted:" 会让所有 form 表单的检测静默失效（又是一个真实踩坑）。
    if "redacted:" not in lowered and "redacted%3a" not in lowered:
        return False
    for key in SENSITIVE_KEYS:
        if f"{key}=" in lowered or f'"{key}"' in lowered or f"'{key}'" in lowered:
            return True
    for key in SECRET_BODY_KEYS:
        if f'"{key}"' in lowered or f"'{key}'" in lowered:
            return True
    return False


def _pii_labels(text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern in PII_PATTERNS:
        if re.search(pattern, text):
            hits.append(label)
    return hits


def _count_by(items: Sequence[Any], key: str) -> dict[str, int]:
    """按字段值计数。同时接受 dict（flow 行）与 dataclass（Finding）。"""
    out: dict[str, int] = {}
    for item in items:
        if isinstance(item, dict):
            value = item.get(key)
        else:
            value = getattr(item, key, None)
        if value is None:
            continue
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def _status_classes(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        status = int(row.get("response_status") or 0)
        if status == 0:
            label = "无响应"
        elif status < 200:
            label = "1xx"
        elif status < 300:
            label = "2xx"
        elif status < 400:
            label = "3xx"
        elif status < 500:
            label = "4xx"
        else:
            label = "5xx"
        out[label] = out.get(label, 0) + 1
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 9. 报告渲染
# ─────────────────────────────────────────────────────────────────────────────


def render_json(
    findings: Sequence[Finding],
    facts: dict[str, Any],
    exit_code_value: int,
    meta: dict[str, Any] | None = None,
) -> str:
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tool": "traffic-audit (Day 164)",
        "meta": meta or {},
        "summary": facts,
        "exit_code": exit_code_value,
        "findings": [f.to_dict() for f in findings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_markdown(
    findings: Sequence[Finding],
    facts: dict[str, Any],
    exit_code_value: int,
    meta: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = []
    lines.append("# 流量审计报告（Day 164）")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}")
    for key, value in (meta or {}).items():
        lines.append(f"- {key}：{value}")
    lines.append(f"- **退出码**：`{exit_code_value}`（{EXIT_MEANING.get(exit_code_value, '未知')}）")
    lines.append("")

    lines.append("## 覆盖率")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|---|---|")
    lines.append(f"| 总 flow | {facts.get('flows', 0)} |")
    lines.append(f"| 已检查 | {facts.get('inspected', 0)} |")
    lines.append(f"| **未检查（隧道）** | **{facts.get('uninspected', 0)}** |")
    lines.append(f"| 传输错误 | {facts.get('transport_errors', 0)} |")
    lines.append(f"| **覆盖率** | **{facts.get('coverage_percent', 0.0)}%** |")
    lines.append("")

    classes = facts.get("status_classes") or {}
    if classes:
        lines.append("状态码分布：" + " ".join(f"`{k}`={v}" for k, v in classes.items()))
        lines.append("")

    lines.append("## 发现汇总")
    lines.append("")
    sev = facts.get("severity_counts") or {}
    if not findings:
        lines.append("（本规则集未命中任何发现。注意：这不等于『安全』，见覆盖率一节。）")
    else:
        lines.append("| 级别 | 数量 |")
        lines.append("|---|---|")
        for name in ("critical", "high", "medium", "low", "info"):
            if sev.get(name):
                lines.append(f"| {name} | {sev[name]} |")
        lines.append("")
        lines.append("按优先级排序的明细：")
        lines.append("")
        for idx, f in enumerate(findings, 1):
            lines.append(f"### {idx}. [{f.level}·{f.severity}] {f.rule}")
            lines.append("")
            lines.append(f"- **flow**：`{f.flow_id}`  {f.url}")
            lines.append(f"- **证据**：{f.evidence}")
            lines.append(f"- **为什么是问题**：{f.why}")
            lines.append(f"- **修复建议**：{f.fix}")
            lines.append(f"- **优先级**：{f.priority}（严重度 {SEVERITY_SCORE.get(f.severity, 0.5)} × 置信度 {f.confidence}）")
            lines.append("")

    lines.append("## 本工具不做的事")
    lines.append("")
    lines.append("- 不伪造证书、不降级 TLS、不破解隧道内容")
    lines.append("- 不改包、不重放、不注入响应")
    lines.append("- 不在档案里保存口令/令牌/Cookie 的明文值")
    lines.append("- 不对未授权目标发起任何请求")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> 覆盖率 < 100% 时，本报告的『未发现』只表示『在已检查的流量里未发现』，")
    lines.append("> 不表示目标安全。请先看覆盖率，再看结论。")
    lines.append("")
    return "\n".join(lines)


EXIT_MEANING = {
    EXIT_OK: "干净通过",
    EXIT_GATE_REJECTED: "被范围门禁拒绝（根本没开始测）",
    EXIT_FINDINGS: "有 P0/P1 发现，需要人工复核",
    EXIT_INCOMPLETE: "覆盖不完整（存在未检查流量），结论不可信",
}


# ─────────────────────────────────────────────────────────────────────────────
# 10. 自检
# ─────────────────────────────────────────────────────────────────────────────


def _self_test() -> None:
    """端到端自检：起靶场 → 起代理 → 跑会话 → 分析 → 断言关键结论。

    **为什么教学模块也值得写自检？** 因为"能跑"和"跑对"是两件事。
    自检把"我认为它会怎样"变成"它必须怎样"，改了规则忘了改预期时会立刻炸。
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "flows.jsonl"
        scope = Scope()

        with LabOrigin() as origin, LabOpaqueTCP() as opaque, AuditProxy(store_path, scope=scope, verbose=False) as proxy:
            session = LabSession(proxy.url, scope=scope, rate=50)
            session.run_demo(origin.base, opaque_port=opaque.port)

        rows = FlowStore(store_path).load()
        assert rows, "档案为空：代理没有记录到任何 flow"

        analyzer = FlowAnalyzer(scope=scope)
        findings = analyzer.analyze(rows)
        rules = {f.rule for f in findings}

        # ① 每条必要的规则都要命中
        for expected in (
            "cleartext-credential",
            "sensitive-in-url",
            "cookie-missing-flags",
            "error-disclosure",
            "secret-in-response-body",
            "redirect-chain",
            "slow-response",
            "server-banner",
            "pii-in-request",
            "tls-tunnel-uninspected",
            "response-body-truncated",
        ):
            assert expected in rules, f"规则未命中：{expected}；实际命中 {sorted(rules)}"

        # ② 脱敏必须生效：档案里不能出现明文口令 / 明文 token
        blob = store_path.read_text(encoding="utf-8")
        assert "Sup3rSecret!" not in blob, "明文口令泄漏进了档案！"
        assert "tk_live_164_fake" not in blob, "明文 token 泄漏进了档案！"
        assert "sk_live_164_FAKE_NOT_REAL" not in blob, "响应体密钥泄漏进了档案！"
        assert "13800138000" not in blob, "PII 泄漏进了档案！"
        assert "redacted:" in blob, "档案里没有脱敏标记，说明脱敏逻辑没跑"

        # ③ 隧道必须被记为"未检查"，且覆盖率 < 100%
        assert analyzer.facts["uninspected"] >= 1, "CONNECT 隧道没有被记为未检查"
        assert analyzer.facts["coverage_percent"] < 100.0, "覆盖率不该是 100%"

        # ④ 退出码：有隧道 → 必须是 4（不是 3，也不是 0）
        assert analyzer.exit_code() == EXIT_INCOMPLETE, f"退出码应为 4，实际 {analyzer.exit_code()}"

        # ⑤ 越界必须被代理门禁拒绝（不允许开放代理）
        try:
            AuditProxy(Path(tmp) / "x.jsonl", host="0.0.0.0", verbose=False)
            raise AssertionError("AuditProxy 允许监听 0.0.0.0 —— 这是必须禁止的")
        except AuthorizationError:
            pass

        # ⑥ 门禁拒绝对文档网段以外的 URL 发请求
        try:
            LabSession("http://127.0.0.1:1", scope=scope).request("GET", "http://8.8.8.8/")
            raise AssertionError("门禁没有拦住 8.8.8.8")
        except AuthorizationError:
            pass

        # ⑦ 报告渲染必须包含关键小节
        md = render_markdown(findings, analyzer.facts, analyzer.exit_code())
        assert "覆盖率" in md and "本工具不做的事" in md
        js = json.loads(render_json(findings, analyzer.facts, analyzer.exit_code()))
        assert js["exit_code"] == EXIT_INCOMPLETE and js["findings"]

    print("SELF-TEST OK")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        _self_test()
    else:
        print(__doc__)
