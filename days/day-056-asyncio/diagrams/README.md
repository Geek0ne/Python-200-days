# Day 056 — asyncio 原理解析图解

## 1. 事件循环工作流程

```mermaid
flowchart TD
    A[事件循环启动] --> B{就绪队列有任务?}
    B -->|是| C[取出一个协程]
    B -->|否| D{有 I/O 事件?}
    C --> E[执行协程直到 await]
    E --> F{遇到 await?}
    F -->|否| G[协程完成]
    F -->|是| H{await 的是 I/O?}
    H -->|是| I[注册到 I/O 监听器]
    H -->|否| J[注册到定时器]
    I --> K[继续下一个就绪协程]
    J --> K
    G --> L[结果存入 Future]
    K --> B
    D -->|是| M[触发对应回调]
    D -->|否| N[等待下一个事件]
    M --> O[恢复对应协程]
    O --> E
    N --> B
```

## 2. 同步 vs 异步执行对比

```
同步执行（阻塞模型）：
═══════════════════════════════════════════════════════════
任务1: ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
任务2: ░░░░░░░░░░░░░░░░░░░░████████████████████░░░░░░░░░░░░
任务3: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████████
       ├────────────────────┼────────────────────┼──────────►
       0s                   5s                   10s         时间
       总耗时: ~10s（串行等待）

异步执行（非阻塞模型）：
═══════════════════════════════════════════════════════════
任务1: ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
任务2: ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
任务3: ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
       ├────────────────────┼──────────────────────────────►
       0s                   5s                             时间
       总耗时: ~5s（并发执行）
```

## 3. asyncio.gather() 并发原理

```mermaid
sequenceDiagram
    participant Main as 主协程
    participant Loop as 事件循环
    participant T1 as Task 1
    participant T2 as Task 2
    participant T3 as Task 3

    Main->>Loop: gather(task1, task2, task3)
    Loop->>T1: 调度执行
    Loop->>T2: 调度执行
    Loop->>T3: 调度执行
    
    T1->>Loop: await I/O (挂起)
    T2->>Loop: await I/O (挂起)
    T3->>Loop: await I/O (挂起)
    
    Note over Loop: 等待 I/O 完成...
    
    Loop->>T1: I/O 完成，恢复执行
    Loop->>T2: I/O 完成，恢复执行
    Loop->>T3: I/O 完成，恢复执行
    
    T1-->>Main: 返回结果 1
    T2-->>Main: 返回结果 2
    T3-->>Main: 返回结果 3
    
    Main->>Main: 收集所有结果
```

## 4. Task 生命周期状态图

```mermaid
stateDiagram-v2
    [*] --> Pending: create_task()
    Pending --> Running: 事件循环调度
    Running --> Done: 协程完成
    Running --> Done: 协程抛出异常
    Running --> Cancelled: cancel() 被调用
    
    state Done {
        [*] --> HasResult: 正常完成
        [*] --> HasException: 异常完成
        HasResult: result 可用
        HasException: exception 可用
    }
    
    state Cancelled {
        [*] --> CancelledError: await 时抛出
    }
```

## 5. Semaphore 限流原理

```
请求队列: [R1] [R2] [R3] [R4] [R5] [R6] [R7] [R8] [R9] [R10]
                      │
                      ▼
            ┌─────────────────┐
            │  Semaphore(3)   │
            │  可用槽位: 3     │
            └─────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ Worker 1│  │ Worker 2│  │ Worker 3│
   │ (R1)    │  │ (R2)    │  │ (R3)    │
   └────┬────┘  └────┬────┘  └────┬────┘
        │             │             │
        ▼             ▼             ▼
   完成释放槽位 → R4 进入 → R5 进入 → ...
```

## 6. await 挂起与恢复流程

```mermaid
flowchart LR
    A[执行协程] --> B[遇到 await]
    B --> C[保存当前状态]
    C --> D[控制权交给事件循环]
    D --> E[事件循环执行其他协程]
    E --> F[I/O 完成 / 定时器到期]
    F --> G[恢复协程状态]
    G --> H[继续执行后续代码]
```

## 7. 错误处理流程

```mermaid
flowchart TD
    A[协程执行] --> B{抛出异常?}
    B -->|否| C[正常完成]
    B -->|是| D{是 Task?}
    D -->|是| E[异常存储在 Task 中]
    D -->|否| F[直接传播]
    E --> G{await Task?}
    G -->|是| H[重新抛出异常]
    G -->|否| I[Python 发出警告]
    F --> J[try/except 捕获]
    H --> J
```
