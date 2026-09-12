# Day 155 — mitmproxy 中间人 · 完成清单与练习

> 阶段：Phase 7 — 进阶与性能优化
> 目标：能独立搭起 mitmproxy、解释 TLS 拆分的每一步、写出可用的 Addon 并避开 8 大坑。

---

## ✅ 今日完成清单

### 理解层面

- [ ] 能解释 **HTTP 代理为什么不需要证书，HTTPS 为什么需要**
- [ ] 能画出「客户端 ↔ mitmproxy ↔ 服务器」的双 TLS 会话（TLS① / TLS②）
- [ ] 能说明 mitmproxy CA 私钥（`mitmproxy-ca.pem`）泄露的后果
- [ ] 能说出 `CONNECT` 请求的作用，以及代理如何在隧道里"扮演服务器"
- [ ] 能解释 **certificate pinning** 为什么能防住 MITM
- [ ] 能说出 `requestheaders` / `request` / `responseheaders` / `response` 的区别
- [ ] 能解释"改 body 必须重算 `Content-Length`"，以及为什么 `chunked` 也要处理
- [ ] 能解释"为什么 Addon 里不能 `time.sleep`"（事件循环 / 单线程）
- [ ] 能区分正向 / 透明 / 反向 / 上游 四种代理模式的用途

### 操作层面

- [ ] `pip install mitmproxy` 成功，`mitmdump --version` 有输出
- [ ] 运行过 `mitmdump -s code/01-addon-basics.py -p 8080`
- [ ] 用 `curl -x ... --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem` 成功看到明文
- [ ] 浏览器访问过 `http://mitm.it` 并安装 CA
- [ ] 跑通 `python3 code/02-addon-pitfalls.py --self-test`（全绿）
- [ ] 跑通 `python3 code/03-traffic-tool.py --self-test`（全绿）
- [ ] 生成过一份 `report.html` 并打开看过
- [ ] 在 `mitmproxy` TUI 里试过 `e`（编辑）+ `r`（重放）

### 产出物

- [ ] 一份 `flows.jsonl`
- [ ] 一份 `report.html`
- [ ] 一张自己画的 TLS 拆分图

---

## 📝 基础练习（必做）

<details>
<summary>点击展开答案要点</summary>

### Q1 判断：哪些操作合法？

| 操作 | 合法？ | 理由 |
|---|---|---|
| 抓自己浏览器访问自己博客的流量 | ? | |
| 抓自己手机 App 访问公司内部测试环境的流量 | ? | |
| 在公共 WiFi 上跑透明代理，看别人的请求 | ? | |
| 公司授权下，对内部 App 做抓包审计（员工已签知情书） | ? | |
| 用 mitmproxy 改自己的响应，去掉广告 | ? | |

**答案要点：**

- 抓自己浏览器 → ✅ 合法，你就是数据主体；
- 抓自己手机访问**内部测试环境** → ✅ 合法（自有设备 + 自有服务），
  但要确认公司安全制度允许携带设备接入；
- 公共 WiFi 抓别人 → ❌ **刑事**，中国大陆适用《刑法》285 条 /
  侵犯公民个人信息罪；这不是"技术问题"；
- 公司授权 + 知情书 → ⚠️ 合法但需严格合规：明确范围、留存记录、最小必要、
  员工可退出；
- 改自己的响应去广告 → ⚠️ 灰区：技术合法，但可能违反服务条款（ToS）。

### Q2 最小 Addon：给所有请求加一个头

```python
from mitmproxy import http

class AddHeader:
    def request(self, flow: http.HTTPFlow):
        flow.request.headers["X-Debug-By"] = "mitmproxy"

addons = [AddHeader()]
```

运行：

```bash
mitmdump -s add_header.py -p 8080
```

**要点：** 不需要继承任何基类，**方法名就是事件名**；
模块级 `addons` 列表是唯一的注册入口。

### Q3 改响应体：把 JSON 里的 `role` 改掉（越权测试）

```python
from mitmproxy import http
import json

class PrivilegeProbe:
    """在授权渗透测试里，验证服务端是否真的校验角色。"""

    def response(self, flow: http.HTTPFlow):
        if "/api/me" not in flow.request.path:
            return
        ct = flow.response.headers.get("Content-Type", "")
        if "json" not in ct:
            return
        try:
            data = json.loads(flow.response.text)   # ✅ .text 自动解压+解码
        except Exception:
            return
        if isinstance(data, dict) and data.get("role") == "user":
            data["role"] = "admin"
            flow.response.text = json.dumps(data)   # ✅ 自动重算 Content-Length
```

**要点：** 必须是**已授权**测试；改的是"客户端看到的"，服务端是否买账
取决于它有没有真的校验——这正是测试目的。

### Q4 解释：为什么这行会白屏？

```python
flow.response.content = flow.response.content.replace(b"foo", b"foobar")
```

**答案要点：**

1. 若响应是 `gzip`，`content` 是**压缩字节**，`replace` 匹配不到；
2. 即使匹配到，长度变了，`Content-Length` 仍是旧值；
3. 客户端读到旧长度，多出的字节被当作下一个响应 → 协议错乱 / 白屏；
4. 正确：`flow.response.text = flow.response.text.replace("foo", "foobar")`。

### Q5 写一个"只记录含敏感参数的请求"的 Addon

```python
from mitmproxy import ctx, http

SENSITIVE = ("token", "password", "passwd", "secret", "api_key")

class SensitiveWatch:
    def request(self, flow: http.HTTPFlow):
        path = flow.request.path.lower()
        q = flow.request.query
        hits = [k for k in q.keys() if any(s in k.lower() for s in SENSITIVE)]
        if hits or any(s in path for s in SENSITIVE):
            # ⚠️ 只记录"存在敏感参数"这个事实，绝不记录值
            ctx.log.warn(f"[sensitive] {flow.request.method} "
                         f"{flow.request.host}{flow.request.path.split('?')[0]} "
                         f"敏感参数={hits}")

addons = [SensitiveWatch()]
```

**要点：** 这就是"**记录事实，不记录值**"的最小示例。
很多事故不是被黑，而是日志里存了明文密码。

</details>

---

## 🚀 进阶挑战（选做）

<details>
<summary>点击展开</summary>

### C1 用 `asyncio.to_thread` 消除阻塞

需求：写一个 Addon，在 `request` 里调用一个**同步**函数（模拟 500ms 的
外部校验），但不阻塞事件循环。

```python
import asyncio, time
from mitmproxy import http, ctx

def slow_check(path: str) -> bool:
    time.sleep(0.5)                 # 模拟同步阻塞
    return "admin" in path

class AsyncGuard:
    async def request(self, flow: http.HTTPFlow) -> None:
        # mitmproxy 支持 async 事件回调
        ok = await asyncio.to_thread(slow_check, flow.request.path)
        if not ok:
            flow.response = http.Response.make(403, b"blocked")
            ctx.log.info("已拦截（未阻塞事件循环）")

addons = [AsyncGuard()]
```

**对比实验：** 用 20 并发压测，对比 `time.sleep` 版与
`asyncio.to_thread` 版的吞吐差异。**这就是"代理为什么慢"的答案。**

### C2 实现"响应延迟注入"（弱网测试）

需求：随机给 10% 的响应注入 1~3 秒延迟，用于测试客户端的超时处理。

```python
import asyncio, random
from mitmproxy import http

class LatencyInjector:
    async def response(self, flow: http.HTTPFlow) -> None:
        if random.random() < 0.1:
            await asyncio.sleep(random.uniform(1, 3))

addons = [LatencyInjector()]
```

**思考：** 为什么要在 `response` 而不是 `request` 注入延迟？

### C3 从 JSONL 里找出"疑似越权成功"

需求：给 `03-traffic-tool.py` 加一个 `--find-idor` 参数，扫描 JSONL，
找出满足以下条件的记录：

1. 请求里带了 `id` / `user_id` / `order_id` 参数；
2. 响应的 status 是 200；
3. 响应体里出现了与请求 id **不同**的 id（说明"拿别人的数据"成功了）。

输出可疑清单（脱敏后的 URL + 差异 id）。

### C4 写一个 `map_local` 风格的 mock 服务

需求：不用真后端，用 `flow.response` 直接返回 mock 数据：

```python
import json
from mitmproxy import http

MOCKS = {
    "/api/user": {"name": "mock-user", "role": "user"},
    "/api/orders": [{"id": 1}, {"id": 2}],
}

class Mocker:
    def request(self, flow: http.HTTPFlow):
        path = flow.request.path.split("?")[0]
        if path in MOCKS:
            flow.response = http.Response.make(
                200, json.dumps(MOCKS[path]).encode(),
                {"Content-Type": "application/json"})

addons = [Mocker()]
```

**思考：** mitmproxy 自带的 `map_local` / `map_remote` 选项能直接做这件事，
为什么还要手写 Addon？（提示：需要动态逻辑/鉴权/随机数据时）

### C5 检测"我的流量是否被 MITM"

写一个脚本（不依赖 mitmproxy），检查指定站点的证书链：

```python
import ssl, socket, sys
host = sys.argv[1] if len(sys.argv) > 1 else "example.com"
ctx = ssl.create_default_context()
with socket.create_connection((host, 443), timeout=5) as sock:
    with ctx.wrap_socket(sock, server_hostname=host) as ssock:
        cert = ssock.getpeercert()
        print("颁发者:", cert["issuer"])
        print("主题  :", cert["subject"])
        print("有效期:", cert["notBefore"], "→", cert["notAfter"])
```

**判断依据：** 如果颁发者不是你预期的 CA（或与前一天看到的不一致），
就要怀疑链路被中间人接管了。**这就是普通的证书检查，也是每个客户端
每天在做的事。**

</details>

---

## 📌 今日自检的三个问题

1. 为什么"抓得到 HTTPS 流量"从来不意味着"服务器不安全"？
2. `flow.response.text` 和 `flow.response.content`，什么时候必须用哪个？
3. 如果只能给你的 App 加一项防抓包措施，你加什么？为什么？

---

## 🚫 今日红线

- ❌ 不抓任何**不属于你**的设备/账号的流量；
- ❌ 不把 `mitmproxy-ca.pem`（CA 私钥）提交到 git 或发到聊天里；
- ❌ 不在"公共网络 + `--listen-host 0.0.0.0`"下长时间开着代理；
- ❌ 不把抓到的真实凭据写进任何日志/报表（本日工具已内置脱敏，但你要确认）；
- ❌ 不用透明代理去"研究"别人家 WiFi 的流量；
- ✅ 用完立刻在客户端**移除被信任的 mitmproxy CA**。
