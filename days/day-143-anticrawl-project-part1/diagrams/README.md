# Day 143 — 图解

## 1. 代理池生命周期

```text
  采集源A ┐
  采集源B ├──▶ [入库] ──▶ [后台校验线程] ──▶ 评分更新
  采集源C ┘                 │
                            ▼
              ok++ / fail++（连续失败>=3 → 淘汰）
                            │
                            ▼
              爬虫 acquire(): 加权随机(∝score)
                            │
                 feedback(成功/失败) 闭环
```

## 2. 静态/动态分流决策

```mermaid
flowchart TD
    U[URL 队列] --> S[httpx + 代理 静态请求]
    S --> C{status==200 且<br>无框架挂载点?}
    C -- 是 --> O1[✅ 静态解析入库]
    C -- 否/JS渲染 --> P[Playwright 无头渲染<br>inject stealth JS]
    P --> I[监听 response<br>优先捕获 XHR JSON]
    I --> O2[✅ JSON/渲染DOM 入库]
    S -- 被限频/封禁 --> R[代理池 feedback + 换代理重试]
```

## 3. 无头检测对抗的本质

```text
真浏览器指纹:   webdriver=false | 插件5个 | WebGL正常 | 轨迹自然
无头默认指纹:   webdriver=true  | 插件0个 | WebGL异常 | 无鼠标事件
                     │ 注入 init script 抹平 ──────────▶ 差异缩小
对抗是军备竞赛: 检测方加新探针 ←→ 模拟方补特征，没有一劳永逸
```
