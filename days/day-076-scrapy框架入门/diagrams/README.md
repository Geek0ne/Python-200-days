# Day 076 — Scrapy 架构图解

## 1. Scrapy 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Scrapy Engine                         │
│              控制数据流，触发信号，协调各组件               │
└─────┬────────────┬────────────┬────────────┬────────────┘
      │            │            │            │
      ▼            ▼            ▼            ▼
┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│ Scheduler │ │Downloader │ │   Spider  │ │   Item    │
│   调度器   │ │  下载器    │ │   爬虫    │ │  Pipeline │
│           │ │           │ │           │ │           │
│ · 请求队列 │ │ · HTTP请求 │ │ · 解析逻辑│ │ · 数据验证│
│ · URL去重 │ │ · 响应下载 │ │ · 提取数据│ │ · 数据清洗│
│ · 优先级   │ │ · 重试    │ │ · 生成Item│ │ · 数据存储│
└───────────┘ └───────────┘ └───────────┘ └───────────┘
```

## 2. 数据流详解

```
Spider                Engine              Scheduler
  │                     │                    │
  │  ① 生成 Request     │                    │
  │ ─────────────────>  │                    │
  │                     │  ② 请求入队         │
  │                     │ ────────────────>  │
  │                     │                    │
  │                     │  ③ 取出下一个请求    │
  │                     │ <────────────────  │
  │                     │                    │
  │                     │     Downloader     │
  │                     │  ④ 发送请求        │
  │                     │ ────────────────>  │
  │                     │                    │
  │                     │  ⑤ 返回 Response   │
  │                     │ <────────────────  │
  │                     │                    │
  │  ⑥ 传递 Response    │                    │
  │ <─────────────────  │                    │
  │                     │                    │
  │  ⑦ 解析，产出:      │                    │
  │  - Item ──────────────────────────────> Pipeline
  │  - 新Request ─────> 回到 ②              │
```

## 3. Pipeline 执行流程

```
Spider 产出 Item
       │
       ▼
┌──────────────────┐
│ Pipeline 1 (100) │  ← 验证：检查必填字段
│ ValidationPipeline│
└────────┬─────────┘
         │
    ┌────┴────┐
    │ 有效？   │
    └────┬────┘
    是 ↓   否 ↓ DropItem
         │
┌────────┴─────────┐
│ Pipeline 2 (200) │  ← 清洗：去空白、标准化
│  CleanPipeline   │
└────────┬─────────┘
         │
┌────────┴─────────┐
│ Pipeline 3 (300) │  ← 去重：内容指纹比对
│ DuplicateFilter  │
└────────┬─────────┘
         │
┌────────┴─────────┐
│ Pipeline 4 (400) │  ← 存储：写入数据库/文件
│ StoragePipeline  │
└──────────────────┘
```

## 4. 中间件位置

```
        Spider Middleware          Downloader Middleware
        (Spider 输入/输出)          (请求/响应预处理)
              │                          │
Spider ──> [Middleware] ──> Engine ──> [Middleware] ──> Downloader
              │                          │
              ▼                          ▼
        修改 Item/Request          修改 Request/Response

常用 Downloader Middleware:
├── UserAgentMiddleware      (UA 轮换)
├── RetryMiddleware          (自动重试)
├── HttpProxyMiddleware      (代理设置)
├── CookiesMiddleware        (Cookie 管理)
└── HttpCacheMiddleware      (缓存)
```

## 5. 项目目录结构

```
myspider/
├── scrapy.cfg              # 部署配置
└── myspider/
    ├── __init__.py
    ├── items.py            # 数据模型（Item 定义）
    ├── middlewares.py       # 中间件
    ├── pipelines.py        # 数据管道
    ├── settings.py         # 项目设置
    └── spiders/
        ├── __init__.py
        └── quotes.py       # 具体爬虫
```

## 6. Scrapy vs 手动爬虫对比

```
┌─────────────┬──────────────────┬──────────────────┐
│    特性      │  Scrapy (框架级)  │ requests + BS4   │
├─────────────┼──────────────────┼──────────────────┤
│ 并发        │ Twisted 异步      │ 同步/手动多线程    │
│ 去重        │ 内置指纹          │ 手动实现          │
│ 重试        │ 内置              │ 手动 try-except   │
│ 限速        │ AutoThrottle     │ 手动 time.sleep   │
│ Pipeline    │ 完整流水线        │ 无               │
│ 中间件      │ 请求/响应可拦截    │ 无               │
│ 学习曲线    │ 陡峭              │ 平缓             │
│ 适用场景    │ 大规模爬虫        │ 简单/小规模       │
└─────────────┴──────────────────┴──────────────────┘
```
