# Day 193 — 浏览器渲染与验证码识别

> **阶段**：Phase 12 — 综合实战
> **项目**：AI 赋能反爬数据平台 · 第 3/5 天
> **子主题**：无头浏览器 · JS 渲染等待 · 浏览器指纹 · 验证码预处理 · OCR · 重试状态机
> **代码**：1 个自建靶站 + 1 个验证码库 + 4 个可独立运行脚本，全部带 `--self-test`
> **实测环境**：Linux 7.0.0-34-generic / Python 3.12.3 / Playwright 1.64.1 / Chromium 151.0.7922.34 / ddddocr 1.6.1 / 2026-10-23 06:00–06:45 CST

---

## 今天在项目里的位置

```text
Day 191  引擎骨架      → 队列、限速、重试、落库                    ✅
Day 192  代理池        → IP 轮换、健康检查、按目标分配出口          ✅
Day 193  浏览器与验证码 → JS 渲染、指纹、验证码识别                 ← 今天
Day 194  AI 增强       → 反爬策略预测、内容归类、数据管道
Day 195  运维与交付    → 调度、加密、鉴权、Docker + CI/CD
```

Day 191 的 Fetcher 只会发 HTTP，Day 192 给它换了出口。
今天要解决的是**内容根本不在 HTML 里**这件事，以及登录口上那道验证码。

一句话概括今天：**渲染解决"数据在哪"，验证码解决"门怎么开"，指纹解决"门为什么对你关着"。**

---

## 概念速览

完整图解见 **diagrams/README.md**。

| 概念 | 一句话 | 为什么重要 |
|---|---|---|
| 无头浏览器 | 没有界面的真浏览器 | 它执行 JS，`requests` 不执行 |
| Headless Shell | 只跑渲染的精简 Chrome | 比完整 Chromium 更省内存，但指纹更"裸" |
| CDP | Chrome DevTools Protocol | Playwright/Puppeteer 的底层协议 |
| load / DOMContentLoaded | 文档与资源加载完成 | **不代表异步数据到了** |
| networkidle | 500ms 内无网络活动 | 定时器未触发时它会提前返回（实测坑） |
| 内容等待 | 等目标元素/条件出现 | 唯一可靠的"数据已就绪"信号 |
| 资源阻断 | 拦图片/字体/媒体 | 渲染耗时和带宽能降一大截 |
| 指纹 | UA、Canvas、WebGL、时区、字体… | 单项可伪造，**组合的自洽性难伪造** |
| Canvas 指纹 | 文字栅格化后的像素哈希 | 依赖字体与 GPU，与本机环境强绑定 |
| WebGL renderer | GPU 型号或 SwiftShader | 无头环境常暴露为软件渲染 |
| 验证码 | 区分人与程序的挑战 | 一次性、绑定会话、错一次就换图 |
| 图像预处理 | 灰度/二值化/去噪 | 对强噪声有效，对干净图**有害** |
| OCR | 光学字符识别 | ddddocr 是 CNN + CTC 的轻量实现 |
| 打码平台 | 人工/远程识别服务 | 成本与合规风险都要算进预算 |
| 熔断重试 | 失败换图、次数上限 | 无上限刷新 = 主动触发风控 |

---

## 一、概念解释

### 1. 为什么 `requests` 拿不到数据：DOM 是"执行结果"，不是"文件"

服务端返回的是一段**程序**（HTML + JS），浏览器把它执行成 **DOM**。
爬虫拿到的是程序，浏览器拿到的是结果。

```text
你的请求  → 服务器 → HTML 文本（含 <script>）
                        │
                        ├─ requests 读到 → 字符串里只有空 <ul>
                        └─ 浏览器读到 → 执行 JS → fetch → 渲染 → DOM 里有 12 条
```

**所以**：判断"要不要上浏览器"的标准不是"页面看起来复杂"，而是
**目标数据是否出现在原始 HTML 里**。一条命令就能判断：

```bash
curl -s https://example.com/page | grep -c '目标字段'
```

今天是 0，就必须渲染。

### 2. 无头浏览器到底是什么

它就是一个完整的 Chromium，只是不画窗口。进程结构没变：

```text
browser 进程（UI/网络/调度）
 ├── renderer 进程（Blink + V8，执行页面 JS）
 ├── GPU 进程 / SwiftShader（无显卡时软件渲染）
 └── 若干 utility 进程（网络、存储、音频）
```

Playwright 通过 **CDP**（WebSocket 上的 JSON 协议）指挥它：
`Page.navigate`、`Runtime.evaluate`、`Network.setBlockedURLs`……
你在 Python 里写的 `page.click()`，本质是发了一条 CDP 命令。

**代价**：一个 browser 上下文约 100–300MB 内存，启动 200–500ms。
所以生产上要复用 browser、按需新建 context，而不是每个 URL 启一次。

### 3. 等待策略：等"事件"、等"元素"、等"条件"是三件事

| 策略 | 语义 | 什么时候可信 |
|---|---|---|
| `wait_until="load"` | 文档与同步资源加载完 | 静态页 |
| `wait_for_selector("#status")` | 元素**存在** | ❌ 元素常常先于内容存在 |
| `wait_for_selector("#list li")` | 目标元素出现 | ✅ 列表类页面首选 |
| `wait_for_load_state("networkidle")` | 500ms 无请求 | ⚠️ 定时器未触发时会提前返回 |
| `wait_for_function(...)` | 任意 JS 条件 | ✅ 最精确，可等"数量/文本/状态" |
| `sleep(n)` | 固定等待 | ❌ 慢了浪费，快了失败 |

今天实测的六个策略见实验 2：**只有"等内容"的两个成功**，
而 `networkidle` 在 698ms 就返回了——因为 700ms 的定时器还没到，
页面"确实"没有网络活动。这是一个语义陷阱，不是 bug。

### 4. 资源阻断：渲染快 3 倍的正确姿势

爬虫只需要 DOM/文本，不需要图片、字体、媒体、统计脚本。阻断它们：

```python
ctx.route("**/*", lambda route: route.abort()
          if route.request.resource_type in {"image", "media", "font"} else route.continue_())
```

**注意**：阻断字体可能改变 Canvas 指纹（字体缺失 → 像素不同），
如果目标站用 Canvas 做风控，阻断字体等于自己举手。这是"性能 vs 隐身"的取舍。

### 5. 浏览器指纹：不是一项，是一组"互相印证"的事实

目标站会同时读：

```text
网络层    IP、ASN、TLS 指纹(JA3)、HTTP/2 帧序
JS 层     UA、platform、languages、timezone、screen、DPR、CPU 核数
渲染层    Canvas 像素哈希、WebGL vendor/renderer、字体列表、AudioContext
行为层    鼠标轨迹、滚动、打字节奏、页面停留
```

**单项都能改，难的是让它们互相自洽。** 今天实测：
- 只改 UA/时区/语言 → 破绽从 2 个变 **3** 个（新增"UA=Windows 但 platform=Linux"）；
- 再抹掉 `navigator.webdriver` → 回到 2 个，但 WebGL 仍报 SwiftShader；
- Canvas 哈希在 4 种配置下**完全相同**（`37db8d7b`）——改 UA 不会改变字体栅格化结果。

这说明：**指纹的熵主要来自渲染环境，不来自你写在配置里的字符串。**

### 6. 验证码：为什么"重试同一个答案"永远错

服务端流程：

```text
GET /captcha → 生成答案 A，存 session[sid]=A，返回图片
POST /login  → 取出 session[sid]，**无论对错都删除**
              → 比较答案；对 → 200，错 → 403
```

所以 403 之后的正确动作是 **重新 GET 一张新图**。
继续提交同一个答案只会连续 403，还会把 attempts 刷满。
今天靶站的 `/login` 明确实现了"一次性"，自检里也专门验证了这条。

### 7. OCR 与预处理：为什么"二值化"有时是减分项

ddddocr 的模型是卷积网络 + CTC 解码，训练数据是**彩色、带噪声**的真实验证码。
你把它不认识的彩色图强行二值化，等于把输入分布改成了训练时没见过的样子。

实测（每种 100 张）：

| 噪声 | 不处理 | 灰度 | Otsu 二值化 | 二值化+去噪 |
|---|---|---|---|---|
| clean | **98%** | 98% | 96% | 94% |
| medium | **91%** | 91% | 89% | 86% |
| hard | 86% | 85% | **92%** | 91% |

**规律**：噪声弱 → 预处理是负担（干净图的细笔画被阈值切断）；
噪声强 → 二值化能救回 6pp。**必须按噪声强度 A/B，不能固定一条流水线。**

### 8. 工程边界：什么时候该停

- 有 `max_tries`：3 次不对就放弃并记录，不能无限刷图。
- 有 `Retry-After` 就遵守；没有就至少 `sleep` 几百毫秒再换图。
- 打码平台是**外包**：把你的目标站点内容发给第三方，合规与泄密风险要评估。
- 只采公开数据、遵守 robots 与站点条款；验证码本身是"请勿自动化"的明确信号，
  真实项目里应优先走官方 API。本课所有实验都在**自建靶站**上完成。

---

## 二、原理深入

### 1. 一次 `page.goto` 到底发生了什么

```text
Python            Playwright driver          Chromium
  │ goto(url)  →  │ CDP Page.navigate    →   │ 网络请求
  │              │                      ←   │ 响应头/正文
  │              │ ← Page.frameNavigated    │ 解析 HTML 建 DOM
  │              │ ← Page.loadEventFired    │ load 事件（≈185ms）
  │              │                          │ setTimeout(700ms)
  │              │ ← Runtime.consoleAPICalled│ fetch('/api/items')
  │              │ ← Network.responseReceived│ 700ms 后返回
  │              │                          │ innerHTML 更新 → 12 个 <li>
  │ inner_text ← │ Runtime.evaluate     →   │ 读 DOM
```

**要点**：`goto` 返回时，`loadEventFired` 可能刚发生，异步数据还在路上。
Playwright 默认的 `wait_until="load"` 不会替你等业务数据。

### 2. 为什么无头浏览器一眼就被认出来

不是某一个 API，而是**一组"不该同时出现"的事实**：

```text
HeadlessChrome/151  +  navigator.webdriver=true
                    +  WebGL=SwiftShader
                    +  fonts=5
                    +  1280x720
                    +  CPU=4
```

真实桌面机：`Chrome/131`、`webdriver=undefined`、GPU 型号具体、字体几十个、
屏幕 1920x1080 起。所以检测器不需要"高深算法"，做一致性校验就够了。

反过来，这也解释了为什么"指纹浏览器"要一整套环境（真实 GPU、字体、分辨率），
而不是一个 `--user-agent` 参数。

### 3. Canvas 指纹的熵来自哪里

```js
ctx.font = '16px "DejaVu Sans"';
ctx.fillText('Day193 指纹 😀 CwWm', 4, 8);
canvas.toDataURL()   // → 像素级哈希
```

同一段文字在不同**字体版本 / 抗锯齿 / GPU 驱动 / 缩放比**下，像素不同。
今天 4 个配置哈希全相同（`37db8d7b`），因为渲染栈没变——
换了 UA、时区、视口，但字体和 SwiftShader 没变。
**结论：想改 Canvas 哈希，得改渲染环境，不是改 HTTP 头。**

### 4. ddddocr 的推理流程

```text
输入 160x60 RGB
  → 缩放/归一化
  → CNN 特征图（宽度方向保留序列信息）
  → 按列预测字符 + CTC 合并重复
  → "AB3D"
```

CTC 的好处是不用切分字符；坏处是**相似字形**（O/0、I/1、B/8）容易混。
所以合成数据集时特意去掉了 `O0I1L`——否则测出来的是"字体歧义"，不是"模型能力"。

### 5. 为什么"渲染 + OCR + 重试"必须是一个状态机

三个不确定源叠加：页面慢、识别错、验证码一次性。
如果不把状态显式化，代码会写成"嵌套 if + 全局变量"，最终无法回答：
"这次失败是渲染没等到，还是 OCR 错了，还是被风控了？"

今天 04 的做法：每次登录一行记录（`ok/attempts/chars/ms`），
失败原因可从 `attempts` 与 `chars` 反推。这是可运维性的最低要求。

---

## 三、定义与使用方法（API 速查）

### Playwright（同步 API）

| API | 作用 | 备注 |
|---|---|---|
| `sync_playwright().start()` | 启动 driver | 用 `with` 自动清理 |
| `p.chromium.launch(headless=True)` | 启动浏览器 | 版本不匹配时传 `executable_path` |
| `browser.new_context(**opts)` | 独立会话 | `user_agent`/`locale`/`timezone_id`/`viewport` |
| `context.add_init_script(js)` | 每次导航前注入 | 改 `navigator.*` 的唯一正确时机 |
| `context.route(pattern, handler)` | 拦截请求 | `route.abort()` / `continue_()` |
| `page.goto(url, wait_until=...)` | 导航 | `load`/`domcontentloaded`/`networkidle`/`commit` |
| `page.wait_for_selector(sel)` | 等元素 | 默认 `state="visible"` |
| `page.wait_for_function(expr)` | 等 JS 条件 | 最精确 |
| `page.locator(sel).count()` | 计数 | 不等待，取瞬时值 |
| `page.evaluate(js)` | 执行 JS 并取返回值 | 可直接读 `window.__fp` |
| `context.request.get(url)` | 带共享 Cookie 的 HTTP | 绕过页面直接打接口 |
| `page.screenshot(path=...)` | 截图 | 调试渲染问题时最有用 |

### ddddocr

| 用法 | 说明 |
|---|---|
| `DdddOcr(show_ad=False)` | 初始化（首次会加载 ONNX 模型） |
| `ocr.classification(img)` | 支持 `PIL.Image` / `bytes` / `Path` |
| 返回 | 字符串；可能为空串或长度不符 |

### 图像预处理（Pillow / OpenCV）

| 操作 | 代码 | 适用 |
|---|---|---|
| 灰度 | `img.convert("L")` | 彩色干扰 |
| 中值滤波 | `ImageFilter.MedianFilter(3)` | 椒盐噪声 |
| Otsu 二值化 | `cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)` | 前景背景分明 |
| 形态学开 | `cv2.morphologyEx(..., cv2.MORPH_OPEN, ...)` | 去孤立噪点（会伤细笔画） |
| 正弦扭曲 | `cv2.remap` + `sin` | 合成训练数据 |

### SQLite 幂等写入

```sql
INSERT INTO items (id, title, price, fetched_at, source)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    title=excluded.title, price=excluded.price,
    fetched_at=excluded.fetched_at, source=excluded.source;
```

---

## 四、图解

完整版见 **diagrams/README.md**，包含：
1. 静态抓取 vs 浏览器渲染的数据流
2. 六种等待策略的时间线（真实耗时）
3. 指纹一致性矩阵（含破绽位置）
4. 验证码识别流水线
5. 预处理准确率对比图
6. 端到端状态机（Mermaid）
7. 本课实验拓扑

---

## 五、实战实验手册

> 全部实验在**本机自建靶站**上完成，不访问任何第三方站点。
> 靶站、数据集、数据库都在 `/tmp`，实验结束有清理章节。

### 实验 1：静态抓取 vs 浏览器渲染

**目的**：证明"数据不在 HTML 里"时，渲染是唯一路径。

**环境**：Python 3.12.3；Playwright 1.64.1；Chromium 151.0.7922.34；本机 16GB / 4 核可见。

**准备**：
```bash
cd days/day-193-browser-captcha/code
python3 00-lab-target.py --self-test     # 先确认靶站逻辑正确（8 项）
```

**执行**：
```bash
python3 01-basic-render.py
```

**预期结果**：静态抓取 0 条；至少一种等待策略拿到 12 条。

**实际结果**（2026-10-23 06:05 CST，真实 stdout）：
```text
靶站: http://127.0.0.1:39625/

① 纯 HTTP 抓取（无 JS）
   耗时 26ms  商品数 = 0   HTML 4257 字节
   页面里看到的是: #list li{padding:6px 0;...} / <p id="status">booting…</p> / <ul id="list"><!-- JS 注入前是空的 --></u

② 浏览器渲染 × 6 种等待策略（每种 2 轮，取第 2 轮以避开冷启动）
   ❌ load                 185ms  items= 0  status='booting…'
   ❌ selector-exists      250ms  items= 0  status='booting…'
   ✅ selector-items      1550ms  items=12  status='ready items=12 took=1407ms'
   ❌ sleep-1s            1268ms  items= 0  status='booting…'
   ❌ networkidle          698ms  items= 0  status='booting…'
   ✅ wait-function       1452ms  items=12  status='ready items=12 took=1409ms'

③ 结论
   最快且正确: wait-function (1452ms)
   陷阱: load → items=0 (等待条件不充分)
   陷阱: selector-exists → items=0 (等待条件不充分)
   陷阱: sleep-1s → items=0 (等待条件不充分)
   陷阱: networkidle → items=0 (等待条件不充分)
   静态抓取漏掉 12 条数据 → 渲染不是升级版抓取，而是唯一能拿到内容的方式
```

**结论**：
- 同样一条 URL，静态 26ms 拿到 4257 字节但 **0 条数据**；渲染 1452ms 拿到 12 条。
- 6 种策略里 2 种正确、4 种"看起来成功但结果是空"。
  这 4 种才是最危险的——它们不报错，只是静默返回空列表。
- `sleep(1s)` 差 400ms 就失败：靶站总延迟约 1.4s。固定 sleep 的本质是赌。

**清理**：脚本自己在 `finally` 里 `terminate()` 靶站；无残留端口。
`
**复现要点**：`01-basic-render.py` 自动分配空闲端口，不会和 8931 冲突。

---

### 实验 2：浏览器指纹的四种配置

**目的**：量化"改配置"能消除多少破绽，以及会新增哪些矛盾。

**环境**：同上；靶站页面内计算 Canvas/WebGL/字体。

**执行**：
```bash
python3 02-pitfall-fingerprint.py
```

**实际结果**（真实 stdout，列宽已按终端截断）：
```text
字段                  A 默认无头          B 只改 UA/时区/语言   C B + 抹掉 webdr  D 无 GPU 的软件渲染
------------------------------------------------------------------------------------
webdriver           True            True            None            True
timezone            Asia/Shanghai   America/New_Yo  America/New_Yo  Asia/Shanghai
platform            Linux x86_64    Linux x86_64    Linux x86_64    Linux x86_64
screen              1280x720        1920x1080       1920x1080       1280x720
hardwareConcurrency 4               4               4               4
webglRenderer       Google, Vulkan  Google, Vulkan  Google, Vulkan  Google, Vulkan
canvas              37db8d7b        37db8d7b        37db8d7b        37db8d7b
fontsCount          5               5               5               5
risk                2               3               2               2

各配置被识别出的破绽：
  A 默认无头               risk=2  ['navigator.webdriver=true', 'WebGL=SwiftShader 软件渲染']
  B 只改 UA/时区/语言        risk=3  ['navigator.webdriver=true', 'UA=Windows 但 platform=Linux', 'WebGL=SwiftShader 软件渲染']
  C B + 抹掉 webdriver   risk=2  ['UA=Windows 但 platform=Linux', 'WebGL=SwiftShader 软件渲染']
  D 无 GPU 的软件渲染        risk=2  ['navigator.webdriver=true', 'WebGL=SwiftShader 软件渲染']
```

完整 WebGL 字符串：
```text
ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)
```

**结论**：
- 只改 UA **提高了**风险（2→3）：新增 UA/platform 矛盾。这是本次最反直觉的实测结果。
- 抹掉 `navigator.webdriver` 只去掉 1 个破绽，WebGL 仍暴露软件渲染。
- Canvas 哈希四种配置完全相同：`37db8d7b`。改 header 改不了渲染栈。
- 四个配置 `hardwareConcurrency` 都是 4、字体都只有 5 个——容器环境本身的特征最难藏。

**清理**：脚本 `finally` 关闭 browser 与靶站。

---

### 实验 3：验证码识别基准（4 预处理 × 3 噪声）

**目的**：用固定 seed 的 300 张带标签样本，量出预处理到底帮不帮忙。

**准备**：
```bash
python3 03-captcha-ocr.py --self-test        # 8 项：图形/二值/可复现/指标函数
python3 03-captcha-ocr.py --n 100            # 生成数据集 + 跑 12 组
```

**数据集构成**：4 字符、去掉 `O0I1L`、每字符独立旋转与着色；
medium 加 120 噪点 + 2 条干扰线 + 1.2px 正弦扭曲；hard 加 260 噪点 + 5 线 + 3 弧 + 2.6px 扭曲。

**实际结果**（2026-10-23 06:10 CST，每种噪声 100 张，单进程 CPU）：
```text
=== 噪声强度: clean (100 张) ===
预处理           全对      准确率      字符准确率    ms/张   错例
none          98    98.0%      99.2%    79.2   7JWF→7JW KAJD→KAD
gray          98    98.0%      99.2%    66.3   7JWF→7JW KAJD→KAD
otsu          96    96.0%      98.8%    96.7   4NJS→4NUS 7JWF→7JW D7HZ→O7HZ
denoise       94    94.0%      98.2%    94.7   W4MR→WAMR 4NJS→4NUS 7JWF→>JW

=== 噪声强度: medium (100 张) ===
预处理           全对      准确率      字符准确率    ms/张   错例
none          91    91.0%      97.0%   121.4   4WTH→4WH QABV→0ABV 7JJH→>了JH
gray          91    91.0%      97.0%    97.9   4WTH→4WH QABV→0ABV 7JJH→>了JH
otsu          89    89.0%      96.5%   118.9   QABV→OABV N7TA→N>TA 7JJH→>JJH
denoise       86    86.0%      95.0%    75.9   4WTH→4WH QABV→OABV Q6FS→O6FS

=== 噪声强度: hard (100 张) ===
预处理           全对      准确率      字符准确率    ms/张   错例
none          86    86.0%      96.0%    84.7   9AQQ→9AO0 FQBA→F0BA WDU7→WPU7
gray          85    85.0%      95.8%    73.4   9AQQ→9AO0 FQBA→F0BA WDU7→WPU7
otsu          92    92.0%      97.8%   107.4   MKZZ→MXZZ DC2D→OC2D 7VRP→>VRP
denoise       91    91.0%      97.5%    64.8   MKZZ→MXZZ DC2D→OC2D HV2E→HVZE

=== 横向对比：每种噪声下的最佳预处理 ===
  clean    最佳=none     98.0%  最差=denoise  94.0%  差距 +4.0pp
  medium   最佳=none     91.0%  最差=denoise  86.0%  差距 +5.0pp
  hard     最佳=otsu     92.0%  最差=gray     85.0%  差距 +7.0pp
```

**结论**：
- 干净/中等噪声：**不处理最好**。二值化把笔画细节切掉，准确率降 2–5pp。
- 强噪声：Otsu **+6pp**（86%→92%），去噪再快 20ms 但少 1pp。
- 单张耗时 65–121ms，波动主要来自进程调度；同一张图的差异不是模型随机性（CTC 是确定性的）。
- 业务含义：100 张验证码按 92% 算，约 8 次失败。若每次失败要换图重试，
  平均尝试次数 ≈ 1.09；但**连续 3 次失败**的概率约 0.05%，所以 `max_tries=3` 足够。

**清理**：数据集在 `/tmp/captcha-ds`（约 300 张 PNG），不需要时 `rm -rf /tmp/captcha-ds`。

---

### 实验 4：端到端采集（渲染 → 识别 → 登录 → 入库）

**目的**：验证三块能力接起来后，成功率与延迟是多少；以及重复跑是否幂等。

**执行**：
```bash
python3 04-production-scraper.py --logins 10
python3 04-production-scraper.py --dry-run --logins 5 --db /tmp/day193-dry.db
```

**实际结果（浏览器模式，真实 stdout）**：
```text
模式: 浏览器渲染
  渲染拿到 12 条商品
  第  1 次登录: ✅ 识别='G3XM' 尝试=1 286ms
  第  2 次登录: ✅ 识别='C2WF' 尝试=1 276ms
  第  3 次登录: ✅ 识别='2GHS' 尝试=1 248ms
  第  4 次登录: ✅ 识别='XV3Y' 尝试=1 238ms
  第  5 次登录: ✅ 识别='J2SQ' 尝试=1 211ms
  第  6 次登录: ✅ 识别='QQ4Z' 尝试=1 211ms
  第  7 次登录: ✅ 识别='FGQV' 尝试=1 245ms
  第  8 次登录: ✅ 识别='ZMS9' 尝试=1 178ms
  第  9 次登录: ✅ 识别='J5MZ' 尝试=1 286ms
  第 10 次登录: ✅ 识别='T3J8' 尝试=1 277ms

指标: {"login_attempts_total": 10, "login_ok": 10, "login_success_rate": 1.0,
       "avg_attempts_per_login": 1.0, "avg_ms": 245.6, "items": 12}
数据库: /tmp/day193-scraper.db
```

**实际结果（纯 HTTP 降级路径）**：
```text
模式: 纯 HTTP（--dry-run）
  HTTP 拿到 12 条商品（无需渲染）
  第 1..5 次登录全部 ✅ 尝试=1
指标: {"login_attempts_total": 5, "login_ok": 5, "login_success_rate": 1.0,
       "avg_attempts_per_login": 1.0, "avg_ms": 132.9, "items": 12}
```

**结论**：
- 浏览器模式单次登录 **245.6ms**；纯 HTTP **132.9ms**（约 1.85×）。
  差距来自 Playwright 的 CDP 往返与页面 JS 执行，不是 OCR（OCR 只占 60–70ms）。
- 10/10 成功，平均 1.0 次尝试：说明 medium 噪声下 ddddocr 对这类合成图很稳。
- 幂等：连跑两次 `items` 仍是 12 行（`ON CONFLICT` 生效）。

**清理**：
```bash
rm -f /tmp/day193-scraper.db /tmp/day193-dry.db
```
脚本 `finally` 会终止靶站；无需手动 kill 端口。

---

### 实验 5（翻车实验）：正确答案却一直 403

这是今天真实踩到的坑，发生在靶站的自检里。过程比结论值钱。

**现象**：
```text
✅ 错误验证码 → 403
✅ 验证码一次性（重复用正确码也失败）
❌ 正确验证码 → 200
❌ /health 统计可读
自检结果：2 项失败
```

**假设**（按可能性排序）：
1. Cookie 没带对 → 服务端认为 `no_sid`；
2. 答案比较有大小写/空格问题；
3. 第二张验证码的 sid 取了但没用上。

**验证手段**：把 `post()` 的响应体打出来，而不是只看状态码。

```python
# 临时调试：打印服务端 reason
print("post correct", post(answer2, True))
# → (403, b'{"ok": false, "reason": "no_sid"}')
```

`no_sid` 直接排除了"答案错"：服务端根本没找到会话。

**真实根因**：`post()` 是闭包，捕获了外层变量 `sid`（第一张图的会话）。
第二次请求 `/captcha` 后拿到 `sid2`，但函数里仍发 `sid`——那个会话已经被上一次
"重复使用"测试消耗掉了。

```python
# 错误：闭包捕获外层 sid
def post(ans, use_sid):
    ... headers={"Cookie": f"sid={sid}"}

# 修复：会话显式传参
def post(ans, sess, use_sid=True):
    ... headers={"Cookie": f"sid={sess}"}
```

**修复后复测**：
```text
✅ 首页返回 HTML 且含空列表骨架  22ms
✅ 延迟接口真的延迟了 ≥0.6s  0.70s
✅ 接口返回 12 条商品
✅ 验证码是 PNG 且 >1KB  9682B
✅ 错误验证码 → 403
✅ 验证码一次性（重复用正确码也失败）
✅ 正确验证码 → 200
✅ /health 统计可读

自检结果：全部通过
```

**教训**：验证码场景里，"哪一张图的会话"是最容易丢的状态。
只要状态超过一个，就应该显式传参，不要依赖闭包。
`no_sid` 与 `wrong` 必须能区分——这正是我在响应里加 `reason` 字段的原因。

---

### 实验 6（翻车实验）：`networkidle` 提前 700ms 返回

**现象**：实验 1 里 `networkidle` 用了 698ms，结果是 `items=0`。

**假设**：
1. `wait_for_load_state("networkidle")` 在 `goto` 之后调用时状态已满足，立即返回；
2. 或者页面请求被缓存，没有产生网络活动。

**验证**：在页面里记录 `performance.now()` 与请求时间；同时看 `#status` 文本仍是 `booting…`。
靶站的 fetch 在 `setTimeout(700ms)` 里，而 `networkidle` 只要"最近 500ms 无请求"就成立。
在 0–700ms 区间，页面**一个请求都没发**，所以条件成立。

**真实根因**：`networkidle` 衡量的是"过去"，不是"未来"。
它无法知道一个定时器即将发请求。这不是 bug，是语义。

**修复**：
```python
# ❌ 不可靠
page.wait_for_load_state("networkidle")

# ✅ 等业务条件
page.wait_for_selector("#list li")
# 或更精确
page.wait_for_function("document.querySelectorAll('#list li').length >= 12")
```

**复测**：`selector-items` 1550ms / `wait-function` 1452ms，均拿到 12 条。

**教训**：等待条件要**指向目标数据本身**，而不是指向"浏览器觉得网络安静了"。

---

### 实验 7（翻车实验）：预处理把准确率拉低 5pp

**现象**：medium 噪声下，`denoise` 只有 86%，比 `none` 的 91% 低 5pp。

**假设**：形态学开运算（2×2）把细笔画腐蚀掉了；或者中值滤波把字符边缘磨平。

**验证**：把同一张图的 `none` / `denoise` 并排保存，肉眼对比 + 看错例：

```text
none     4WTH→4WH    （少识别 1 字符，但字符本身对）
denoise  4WTH→4WH / QABV→OABV / Q6FS→O6FS  （O/0、Q/O 混淆增加）
```

**根因**：中值滤波 + 二值化让 O 和 Q 的尾巴、Q 和 O 的开口差别变小，
模型的字形判别边界被推到了错误一侧。噪声不是主要矛盾时，
预处理只是**主动丢信息**。

**修复**：不固定流水线，按噪声强度选：

```python
def pick_mode(noise_level: str) -> str:
    return "otsu" if noise_level in ("hard", "severe") else "none"
```

**复测**：hard 下 `otsu` 92% > `none` 86%；clean/medium 下 `none` 最优。与上表一致。

---

## 六、实测数字汇总

| 指标 | 数值 | 条件 |
|---|---|---|
| 静态抓取商品数 | 0 / 12 | 4257 字节 HTML，26ms |
| 渲染首次正确内容 | 1407ms（页面内计时） | 700ms 定时器 + 700ms 接口延迟 |
| 最快正确等待策略 | 1452ms（wait-function） | 冷启动后第 2 轮 |
| 最危险策略 | networkidle 698ms 返回 0 条 | 语义陷阱 |
| 固定 sleep(1s) | 0 条 | 差约 400ms |
| 指纹破绽数 | 2 / 3 / 2 / 2 | A/B/C/D 四配置 |
| Canvas 哈希 | 37db8d7b（四配置相同） | SwiftShader + 同字体栈 |
| OCR clean | 98%（none） | 100 张 |
| OCR medium | 91%（none） | 100 张 |
| OCR hard | 92%（otsu，+6pp） | 100 张 |
| OCR 单张耗时 | 65–121ms | CPU 推理 |
| 端到端登录 | 10/10，245.6ms/次 | 浏览器模式 |
| 纯 HTTP 登录 | 5/5，132.9ms/次 | --dry-run |
| 幂等落库 | 12 行不变 | 重复运行 |

---

## 七、工程边界与合规

- 本课所有"目标站"都是本地自建靶站，没有对任何真实站点发起自动化请求。
- 验证码是站点明确表达"请不要自动化"的方式。真实项目优先找官方 API / 数据授权。
- 打码平台会把图片发往第三方：涉及账号、隐私、商业数据时不可用。
- 指纹伪装在法律与平台条款层面风险高；本课只做**检测视角**的教学，不提供绕过方案。
- 生产爬虫的三条底线：遵守 robots 与速率、不采个人隐私、不破坏服务可用性。

---

## 思考题

1. 你的目标页在 `DOMContentLoaded` 后 2 秒才出现数据，但 `networkidle` 在 300ms 就返回了。
   写出至少两种能稳定等到数据的条件，并说明各自的失效场景。
2. 为什么"只改 UA"会让指纹风险**上升**？如果让你按优先级修，你会先改哪三项，为什么？
3. Canvas 哈希在本机四个配置下完全相同。要让哈希变化，最小改动是什么？
   这个改动会不会带来新的破绽？
4. 验证码识别率 92%，`max_tries=3`。请估算"最终登录成功率"，并说明这个估算依赖哪个独立性假设。
5. 如果目标站把验证码换成"点选图中所有红绿灯"，今天这套 OCR 流水线还适用吗？
   你会怎么改造数据与模型？
6. 端到端 245ms/次里，OCR 只占约 60ms。剩下的时间花在哪？
   如果要把吞吐提高 3 倍，你会先优化哪一段？

---

## 清理记录

本次编写过程中产生的临时物：

| 路径 | 内容 | 处理 |
|---|---|---|
| `/tmp/captcha-ds` | 300 张合成验证码 + labels.csv | 已删除（脚本固定 seed 可重建） |
| `/tmp/day193-*.json` | 实验原始结果 | 已删除（数字已写入本文） |
| `/tmp/day193-scraper.db`、`/tmp/day193-dry.db` | 端到端落库 | 已删除 |
| `/tmp/pwtest.py`、`/tmp/dbg*.py` | 调试脚本 | 已删除 |
| `/tmp/r*.log`、`/tmp/verify*.log` | 实验日志 | 已删除 |
| 靶站进程 | 随机端口，脚本 `finally` 终止 | 无残留 |

**环境改动**：本机通过 `pip3 install --break-system-packages playwright` 安装了
Playwright 1.64.1（浏览器二进制使用已有的 `chromium-1234` 缓存，通过
`executable_path` 指定）。如需还原：`pip3 uninstall playwright`。

---

## 一句话总结

**渲染不是"更强的 requests"，它是唯一能拿到 JS 生成内容的方式；
验证码不是"识别问题"，是"一次性状态 + 失败重试"的工程问题；
指纹不是"改 UA"，是一组必须互相自洽的事实。**
