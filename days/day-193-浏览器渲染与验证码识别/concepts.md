# Day 193 概念词典 — 浏览器渲染与验证码

> 按"看到这个词要知道什么"组织，每条都尽量给出**为什么**，而不只是定义。

## 渲染侧

**DOM（Document Object Model）**
浏览器把 HTML 解析成树，再由 JS 修改。爬虫拿 HTML，浏览器拿 DOM——
两者的差就是"JS 执行的结果"。判断要不要渲染，看目标字段在不在原始 HTML 里。

**无头（headless）**
没有窗口的浏览器。渲染、网络、JS 全都在，只是不绘制到屏幕。
Playwright 的 `headless=True` 在新版本里默认用 `chrome-headless-shell`，指纹与完整 Chrome 不同。

**CDP（Chrome DevTools Protocol）**
浏览器暴露的调试协议，Playwright/Puppeteer 都建立在它上面。
`page.click()` 最终是 `Input.dispatchMouseEvent`。

**load / DOMContentLoaded**
`DOMContentLoaded`：HTML 解析完；`load`：同步资源（图片等）也加载完。
两者都**不保证**异步数据已到。

**networkidle**
"最近 500ms 没有网络请求"。它描述过去，不预测未来：
定时器还没发请求时，它会提前判定空闲（本课实测 698ms 返回 0 条）。

**wait_for_selector / wait_for_function**
前者等元素状态（存在/可见），后者等任意 JS 表达式为真。
等"目标数据"而不是"页面某处存在某个标签"，是可靠性的分界线。

**resource_type**
Playwright 路由拦截里的资源分类：`document`/`script`/`image`/`font`/`media`/`xhr`/`fetch`。
阻断 `image/media/font` 通常能显著降耗时，但改字体可能改变 Canvas 指纹。

**context 与 page**
`browser` 是进程，`context` 是隔离的会话（cookie/localStorage 独立），`page` 是标签页。
生产上复用 browser、每任务一个 context，比每次 launch 省一个数量级。

## 指纹侧

**指纹（fingerprint）**
一组能区分设备/环境的信号：网络层（IP、TLS）、JS 层（UA、时区）、渲染层（Canvas、WebGL）、行为层（鼠标轨迹）。

**Canvas 指纹**
把文字/图形画到 canvas，读像素哈希。它绑定字体版本、抗锯齿、GPU 驱动。
本课四个配置哈希相同（`37db8d7b`），因为渲染栈没变。

**WebGL renderer**
`UNMASKED_RENDERER_WEBGL` 能拿到真实 GPU（或 `SwiftShader` 软件渲染）。
无头 + 无显卡环境几乎必然暴露 `SwiftShader`，这是最难伪装的一项。

**一致性检测**
不看你"像不像人"，看你"自相矛盾不矛盾"：
UA=Windows 但 platform=Linux、屏幕 800x600 但声称桌面、时区 UTC 但语言 zh-CN。

**navigator.webdriver**
自动化框架的显式标记。可用 `add_init_script` 改写，但只是去掉一个破绽，
其余（WebGL、字体、核数）仍在。

**字体探测**
用 `offsetWidth` 比较候选字体与基准字体的宽度差，判断字体是否安装。
容器里通常只有 5 个字体，真实桌面机几十个。

## 验证码侧

**CAPTCHA**
区分人与程序的挑战。常见：字符扭曲、点选、滑块、行为验证。
它同时是"技术挑战"和"授权信号"——站点在说"请勿自动化"。

**一次性会话**
验证码绑定 `sid`，校验后立即作废（无论对错）。所以重试 = 换图 + 重新识别。

**OCR**
光学字符识别。ddddocr 用 CNN 提特征 + CTC 解码，不需要切分字符。

**CTC（Connectionist Temporal Classification）**
允许模型输出"每列一个字符"再合并重复，解决不定长对齐。
副作用：相似字形（O/0、Q/O）容易混。

**Otsu 阈值**
自动选一个让"前景/背景类间方差最大"的阈值。对双峰直方图有效；
对噪声重、笔画细的图会把笔画切断。

**形态学开运算**
先腐蚀后膨胀，去掉孤立小噪点。代价是细笔画也被腐蚀——
本课 medium 噪声下它让准确率从 91% 掉到 86%。

**打码平台**
把图片发给第三方识别。成本、延迟、隐私与合规都要评估；
涉及账号或敏感数据时不可用。

**熔断 / max_tries**
失败次数上限。没有它，"重试"会变成"高频刷新验证码"，直接触发风控。

## 工程侧

**幂等入库**
`INSERT ... ON CONFLICT DO UPDATE`。同一批数据重复采集不产生重复行，
这是"可重复运行"的基础。

**指标（metrics）**
成功率、平均尝试次数、平均耗时、失败原因分布。
没有指标，"跑通了"只是一次运气，无法回归。
