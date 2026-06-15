# Day 017 — 异常处理：图解与分析

## 1️⃣ 异常处理完整执行流

```mermaid
graph TD
    Start(["程序执行 try 子句"]) --> TryBlock["执行 try 代码块"]

    TryBlock --> Check{是否抛出异常?}

    Check -->|否| ElseBlock["执行 else 子句"]
    ElseBlock --> FinallyBlock["执行 finally 子句"]
    FinallyBlock --> End(["继续后续代码"])

    Check -->|是| Match{except 匹配?}
    Match -->|是| ExceptBlock["执行 except 处理"]
    ExceptBlock --> FinallyBlock

    Match -->|否| FinallyBlock2["执行 finally 子句"]
    FinallyBlock2 --> Propagate(["异常继续向上传播"])

    style Start fill:#4a9,color:#fff
    style End fill:#4a9,color:#fff
    style Propagate fill:#e55,color:#fff
    style Check fill:#fa0,color:#000
    style Match fill:#fa0,color:#000
    style FinallyBlock fill:#67b,color:#fff
    style FinallyBlock2 fill:#67b,color:#fff
```

## 2️⃣ 异常传播链

```mermaid
sequenceDiagram
    participant Main as Main
    participant FuncA as function A
    participant FuncB as function B
    participant FuncC as function C

    Main->>FuncA: call A()
    FuncA->>FuncB: call B()
    FuncB->>FuncC: call C()

    Note over FuncC: 💥 发生异常
    FuncC-->>FuncB: 异常向上传播
    Note over FuncB: except? ❌ 不处理
    FuncB-->>FuncA: 异常继续传播
    Note over FuncA: except? ✅ 捕获
    Note over FuncA: 处理完毕

    FuncA-->>Main: 正常返回
```

## 3️⃣ 异常链关系

```mermaid
graph LR
    subgraph "异常链 (raise ... from)"
        Original["FileNotFoundError<br>文件不存在"] -->|from| Business["ConfigError<br>配置加载失败"]
        Business -->|传播| Handler["try/except ConfigError<br>统一处理"]
    end

    subgraph "抑制链 (raise ... from None)"
        Original2["JSONDecodeError"] -.->|from None| Business2["ParseError"]
        Handler2["捕获 ParseError"] -.-> Hidden["(底层细节<br>被隐藏)"]
    end

    subgraph "裸重抛 (raise)"
        Original3["PermissionError"] --> Reraise["记录日志"]
        Reraise -->|裸 raise| Propagate["继续传播<br>保留完整 traceback"]
    end
```

## 4️⃣ 自定义异常层次结构

```mermaid
graph TD
    Exception["Exception<br>(内置基类)"] --> AppError["AppError<br>项目基异常"]
    AppError --> DataError["DataError<br>数据层"]
    AppError --> ValidationError["ValidationError<br>验证层"]
    AppError --> NetworkError["NetworkError<br>网络层"]
    AppError --> AuthError["AuthError<br>认证授权"]
    AppError --> RetryableError["RetryableError<br>可重试(临时故障)"]

    DataError --> DatabaseError["DatabaseError<br>数据库操作"]
    DatabaseError --> ConnErr["ConnectionError<br>连接失败"]
    DatabaseError --> QueryErr["QueryError<br>查询异常"]

    ValidationError --> FieldErr["FieldError<br>字段验证"]

    NetworkError --> TimeoutErr["TimeoutError<br>请求超时"]

    AppError --> RetryErr["RetryError<br>重试耗尽"]

    style Exception fill:#95a5a6,color:#fff
    style AppError fill:#3498db,color:#fff
    style ConnErr fill:#e74c3c,color:#fff
    style FieldErr fill:#e67e22,color:#fff
    style TimeoutErr fill:#9b59b6,color:#fff
```

## 5️⃣ EAFP vs LBYL 对比

```mermaid
graph TB
    subgraph "EAFP 风格 (Pythonic)"
        E1["尝试执行"] --> E2{"异常?"}
        E2 -->|否| E3["使用结果"]
        E2 -->|是| E4["处理异常"]
    end

    subgraph "LBYL 风格"
        L1["检查条件"] --> L2{"检查通过?"}
        L2 -->|是| L3["执行操作"]
        L2 -->|否| L4["跳过或报错"]
    end

    style E1 fill:#2ecc71,color:#fff
    style L1 fill:#f1c40f,color:#000
```

## 6️⃣ finally 执行保证

```mermaid
sequenceDiagram
    participant Try as try
    participant Except as except/else
    participant Finally as finally
    participant Return as return/break

    Note over Try: try 中执行 return
    Try->>Finally: ⚡ 先暂停 return
    Note over Finally: finally 执行
    Finally->>Return: ✅ finally 完毕
    Note over Return: return 生效

    Note over Try: try 中发生异常
    Try->>Except: 跳转
    Except->>Finally: ⚡ 转至清理
    Finally->>Try: 异常继续传播
```

## 7️⃣ 异常处理流程图

```mermaid
flowchart TB
    subgraph Input["用户输入验证"]
        direction TB
        I1["获取原始输入"] --> I2["Required 检查"]
        I2 -->|必填| I3["格式/类型验证"]
        I3 -->|有效| I4["范围验证"]
        I4 -->|通过| I5["✅ 返回清洗值"]
        I2 -->|空| I6["❌ RequiredFieldError"]
        I3 -->|无效| I7["❌ FormatError"]
        I4 -->|超范围| I8["❌ RangeError"]
        I5 --> InputEnd
        I6 --> Retry{{"剩余重试次数?"}}
        I7 --> Retry
        I8 --> Retry
        Retry -->|有| I1
        Retry -->|无| Fail["❌ 最终失败"]
    end

    InputEnd(["结束"])
    Fail --> InputEnd
```

## 8️⃣ 资源管理最佳实践

```mermaid
graph LR
    subgraph "❌ 手动管理"
        A1["手动 open()"] --> A2["try...finally"]
        A2 --> A3["手动 close()"]
        A3 --> A4["容易忘记 or 异常路径漏关"]
    end

    subgraph "✅ with 语句"
        B1["with open() as f:"] --> B2["自动 __enter__"]
        B2 --> B3["代码块执行"]
        B3 --> B4["自动 __exit__<br>(即使异常也执行)"]
    end

    style A4 fill:#e74c3c,color:#fff
    style B4 fill:#2ecc71,color:#fff
```

## 9️⃣ try/except/else/finally 决策树

```mermaid
graph TD
    Start["执行 try 代码块"] --> ExceptOccurred{"异常发生?"}

    ExceptOccurred -->|否| ElseBlock["执行 else 块"]
    ElseBlock --> FinallyBlock["执行 finally 块"]
    FinallyBlock --> Continue["继续程序"]

    ExceptOccurred -->|是| MatchType{"匹配 except?"}
    MatchType -->|匹配| Handle["执行 except 块"]
    Handle --> FinallyBlock

    MatchType -->|不匹配| FinallyProp["执行 finally 块"]
    FinallyProp --> Propagate["异常向上传播"]

    style Start fill:#3498db,color:#fff
    style ExceptOccurred fill:#f39c12,color:#fff
    style MatchType fill:#f39c12,color:#fff
    style Propagate fill:#e74c3c,color:#fff
    style Continue fill:#2ecc71,color:#fff
```

## 🔟 异常链决策流

```mermaid
flowchart LR
    subgraph 异常发生
        E1["异常 A 发生"]
    end

    subgraph 异常链策略
        Decide{选择策略}
        Decide -->|简单抛出| R1["raise A"]
        Decide -->|保留因果| R2["raise B from A"]
        Decide -->|隐藏细节| R3["raise B from None"]
        Decide -->|重抛| R4["raise (裸)"]
    end

    subgraph 结果
        R1 --> C1["新异常，无上下文"]
        R2 --> C2["__cause__ = A<br>保留完整链"]
        R3 --> C3["__cause__ = None<br>隐藏底层细节"]
        R4 --> C4["保留原始 traceback<br>和异常类型"]
    end

    E1 --> Decide
```
