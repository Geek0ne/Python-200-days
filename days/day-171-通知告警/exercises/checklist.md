# Day 171 — 通知告警 · 完成清单与练习

## 一、环境准备

```bash
cd days/day-171-通知告警/code
python3 -V          # 本课在 Python 3.12.3 上编写与验证
```

**不需要**：真实 IM 机器人、邮箱账号、外网、任何第三方包。
所有脚本都带 `--self-test`，纯标准库即可跑通。
（`04-alert-hub.py` 的真实指标采集会优先用 `psutil`，没装会自动降级到 `os.statvfs`。）

想装 psutil 以启用完整真实指标：

```bash
pip install psutil        # 注意：本机 pip 为 PEP 668 托管环境，可能需要
                          #   pip install --break-system-packages psutil
                          # 或 python3 -m venv .venv
```

---

## 二、今日完成清单

打勾表示你在自己机器上跑过并看到了对应输出。

### 环境与自检

- [ ] `python3 smtp_capture_server.py --self-test` → `SELFTEST PASS`
- [ ] `python3 01-basic-smtplib.py --self-test` → `SELFTEST PASS`
- [ ] `python3 02-webhook-notify.py --self-test` → `SELFTEST PASS`
- [ ] `python3 03-pitfalls.py --self-test` → 9 个陷阱全部复现
- [ ] `python3 04-alert-hub.py --self-test` → `SELFTEST PASS`

### 概念理解

- [ ] 能画出告警系统的四层模型（采集 / 判定 / 路由 / 送达）
- [ ] 说清 SMTP 的 Envelope sender 与 Header From 的区别与用途
- [ ] 解释 `Subject: =?utf-8?b?...?=` 是什么编码，为什么必须有它
- [ ] 说出 `add_attachment` 传入 `str` / `bytes` / `BytesIO` 时参数规则的差异

### ⭐ 核心结论

- [ ] **能解释为什么 `raise_for_status()` 不够**
- [ ] 背出钉钉 `300005` / `410100`、企业微信 `93000` / `45009` 的含义
- [ ] 说出哪个错误该退避重试、哪个错误重试无意义

### 实战实验（README 第 6 章）

- [ ] 实验 1：启动抓包服务器，看清完整 SMTP 会话与 MIME 原文
- [ ] 实验 2：`python3 02-webhook-notify.py --probe` 真连官方端点，看 HTTP 200 + errcode
- [ ] 实验 3：验证双重判定与全渠道降级
- [ ] 实验 4：`--storm` 压测，确认 600 事件 → 21 条通知
- [ ] 实验 5：`03-pitfalls.py --self-test` 9 个陷阱
- [ ] 实验 6：`--demo` 观察「触发 → 抖动 → 恢复」闭环

### 翻车实验复盘（README 第 7 章）

- [ ] 能复述「`MAIL FROM` 里的 `size=` 参数」是怎么坑到我的
- [ ] 知道 `python -m smtpd` 在 3.12 已不存在（PEP 594）
- [ ] 知道 `pkill -f` 为什么会杀掉自己，以及 `[.]` 字符类解法
- [ ] 理解「先跑出数字，再写断言」的道理

---

## 三、练习题

### 基础 1 —— 判定成功

**题目**：下面这段代码为什么在 token 写错时依然报告"发送成功"？改写它。

```python
def send(url, title, body):
    r = requests.post(url, json={"text": title}, timeout=10)
    r.raise_for_status()
    return True          # 永远返回 True
```

**自测命令**（不需要外网）：

```bash
python3 02-webhook-notify.py --self-test
```

**要求**：你的新函数在本地 mock 返回 `{"errcode":300005,"errmsg":"token is not exist"}`
且 HTTP 200 时，必须返回 `False`，并把 `errmsg` 透出来。

<details><summary>参考</summary>

```python
def send(url, title, body):
    r = requests.post(url, json={"text": title}, timeout=10)
    r.raise_for_status()          # 第一层：传输层
    data = r.json()
    code = data.get("errcode", -1)   # 第二层：业务层 —— 千万别漏
    if code != 0:
        return False               # 或 raise NotifyError(code, data.get("errmsg"))
    return True
```
</details>

---

### 基础 2 —— 邮件附件

**题目**：给 `01-basic-smtplib.py` 的 `send_with_attachment` 增加一个 **PDF 附件**（二进制）。

**自测命令**：

```bash
python3 01-basic-smtplib.py --self-test
```

**要求**：写出你踩到的异常类型。想清楚为什么传 `BytesIO` 会失败。
（提示：见 README 第 7 章翻车 2 的 6 格矩阵。）

<details><summary>参考</summary>

```python
with open("report.pdf", "rb") as f:
    pdf_bytes = f.read()
msg.add_attachment(pdf_bytes,
                   maintype="application", subtype="pdf",
                   filename="report.pdf")
```

注意：`BytesIO` 在 3.12 会直接 `KeyError`，必须传 `bytes`。
</details>

---

### 基础 3 —— 重试分类

**题目**：给 `send_with_retry` 增加逻辑：**4xx 重试、5xx 不重试**。

**自测命令**：

```bash
python3 03-pitfalls.py --only 2      # 陷阱 2 就是重试风暴
```

**要求**：跑完后，永久错误场景下发出的请求数应从 5 降到 1。
请解释为什么"限流错误"和"token 错误"的处理策略必须不同。

---

### 进阶 1 —— 给 AlertHub 加「滞回阈值」

**背景**：当前抑制窗口是固定 30 分钟。但对于「磁盘 89% ↔ 91%」这种来回抖动，
更好的方案是**滞回（hysteresis）**：触发阈值用 90%，恢复阈值用 85%，
中间地带（85%~90%）维持当前状态不动。

**自测命令**：

```bash
python3 04-alert-hub.py --demo
```

**要求**：改造 `AlertHub.fire()`，让它接受两个阈值。
喂入 `92, 87, 93, 86, 91, 84` 这串值，最终应该只发 **1 条告警 + 1 条恢复**，
而不是随抖动来回切换。思考：滞回和抑制窗口，哪种更适合"缓慢泄漏"型故障？

---

### 进阶 2 —— 接入真实 Webhook

**题目**：去你自己的群里建一个机器人，把 URL 填进 `04-alert-hub.py` 的 `WebhookChannel`，
跑一次真实告警。

```python
hub = AlertHub([
    WebhookChannel("dingtalk", "https://oapi.dingtalk.com/robot/send?access_token=你的token",
                   "dingtalk"),
    WebhookChannel("wecom", "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key",
                   "wecom"),
])
hub.fire(Alert("disk_usage", "web-01", "/", "93%", "85%", "critical"))
```

**要求**：
1. 先故意写错 token 跑一次，确认你**能看到** `errcode=300005`（这一步是本课的灵魂）；
2. 再填对 token，确认收到消息；
3. ⚠️ **不要**把真实 token 提交进 git。本课的 `.gitignore` 不会保护你手滑粘进源码的密钥。

<details><summary>关于安全</summary>

Webhook URL 等同于密码。任何人拿到就能往你群里发任意消息。
建议：开启平台的 IP 白名单 + 加签，URL 放环境变量：

```python
import os
url = os.environ["DINGTALK_WEBHOOK"]
```
</details>

---

### 挑战 —— 「谁来监控告警系统」

**题目**：这是 README 思考题 5。设计一个**送达路径完全独立**的"告警系统自身健康"方案。

**要求回答**：
1. 为什么它必须走一条**与业务告警不共用**的路径？
   （提示：业务告警和健康告警共用 SMTP / 同一个机器人时，会发生什么？）
2. 给出至少 2 种不同技术栈的方案（例如：外部拨测 / 云监控 / 心跳文件 + 独立机器人）。
3. 心跳类方案如何区分「服务真的挂了」和「监控链路自己断了」？
   （提示：双向心跳 —— 服务定期上报，服务也定期检查"我上次上报成功了吗"，
   且这个检查走另一条路。）

<details><summary>参考思路</summary>

成熟做法是**多层独立**：

- **L0 主动拨测**：外部服务每分钟访问你的健康检查端点，
  连续失败 3 次直接走短信/电话（这条路径不依赖你的机器还能发消息）；
- **L1 心跳上报**：你的进程每 30s 向云监控上报；
- **L2 反向看门狗**：上报失败超过 2 分钟，由**另一个进程**告警；
- **L3 静态兜底**：DNS 记录里带一个由外部系统定期检查的 TXT/子域名，
  完全不依赖你的应用栈。

关键原则：**监控链路与被监控链路必须尽可能不共享故障域**。
</details>

---

## 四、清理

本课所有实验都不在外部系统留下状态。若你跑过抓包服务器，请用 `Ctrl-C` 停止；
若误留下了进程：

```bash
pkill -f "smtp_capture_server[.]py"      # 注意 [.] 写法，避免 pkill 匹配到自己
```

确认无残留：

```bash
pgrep -af "smtp_capture_server[.]py" || echo "无残留进程"
```

若装了 psutil 且不想保留：

```bash
pip uninstall -y psutil
```
