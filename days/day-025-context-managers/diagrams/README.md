# Day 025 — 上下文管理器 图解

## 1. with 语句执行流程

```mermaid
flowchart TD
    subgraph Code["源代码"]
        C1["with Expression as Target:"]
        C2["    # 代码块"]
    end

    subgraph Step1["Step 1: 获取管理器"]
        S1["计算 Expression"]
        S2["获取上下文管理器对象"]
    end

    subgraph Step2["Step 2: __enter__"]
        S3["调用 manager.__enter__()"]
        S4["返回值绑定到 Target"]
    end

    subgraph Step3["Step 3: 执行代码块"]
        S5["执行 with 块内的代码"]
        S6{"发生异常?"}
    end

    subgraph Step4["Step 4: __exit__"]
        S7["manager.__exit__(None, None, None)"]
        S8["manager.__exit__(type, val, tb)"]
    end

    subgraph Step5["Step 5: 异常处理"]
        S9{"__exit__ 返回 True?"}
        S10["抑制异常，继续执行"]
        S11["异常继续传播"]
    end

    C1 --> S1
    C2 -.-> S5
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    S5 --> S6
    S6 -- "有异常" --> S8
    S6 -- "无异常" --> S7
    S8 --> S9
    S7 --> E1["正常退出"]
    S9 -- "True" --> S10
    S9 -- "False" --> S11

    style S10 fill:#c8e6c9
    style S11 fill:#ffcdd2
```

## 2. @contextmanager 生成器模式

```mermaid
flowchart TD
    subgraph Generator["生成器函数"]
        G1["def my_cm():"]
        G2["    # setup 代码"]
        G3["    try:"]
        G4["        yield VALUE  ← __enter__ 返回值"]
        G5["    finally:"]
        G6["        # cleanup 代码"]
    end

    subgraph WithBlock["with my_cm() as x:"]
        W1["x = VALUE"]
        W2["执行 with 块"]
    end

    G1 -.-> Setup["__enter__: 执行 yield 之前的代码"]
    G4 -.-> EnterRet["yield 的值 → as 子句"]
    G6 -.-> Exit_["__exit__: 执行 finally 块"]

    Setup --> G2
    G2 --> G3
    G3 --> G4
    G4 --> W1
    W1 --> W2

    W2 -- "无异常" --> G5
    W2 -- "有异常" --> GenErr["异常在 yield 处抛出"]
    GenErr --> G5
    G5 --> G6

    style G4 fill:#fff9c4,stroke:#f9a825
    style W1 fill:#e3f2fd
```

## 3. __exit__ 异常处理决策树

```mermaid
flowchart TD
    A["with 块内发生异常"] --> B{"__exit__ 返回?"}
    B -- "True" --> C["✅ 异常被抑制"]
    B -- "False" --> D["❌ 异常继续传播"]
    B -- "__exit__ 自身抛出异常 E" --> E["E 替代原异常传播"]

    C --> F["程序继续执行<br/>with 块之后的代码"]
    D --> G["原异常传播到外层<br/>try/except 可以捕获"]

    subgraph Notes["注意事项"]
        N1["返回 True 要谨慎：<br/>可能掩盖编程错误"]
        N2["__exit__ 不要轻易抛异常<br/>否则原异常丢失"]
        N3["通常模式：记录日志后<br/>返回 False"]
    end

    style C fill:#c8e6c9
    style D fill:#ffcdd2
    style E fill:#ffcc80
```

## 4. 上下文管理器分层图

```text
┌─────────────────────────────────────────────────────┐
│                 Python 上下文管理器体系                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │        核心协议 (PEP 343)                    │   │
│  │  __enter__(self)  → 返回值绑定到 as          │   │
│  │  __exit__(self, exc_type, exc_val, exc_tb)  │   │
│  │     → 返回 bool 决定是否抑制异常              │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │       标准库 contextlib 模块                  │   │
│  │                                             │   │
│  │  @contextmanager    生成器方式实现            │   │
│  │  closing(obj)       调用 obj.close()         │   │
│  │  suppress(*excs)    忽略指定异常             │   │
│  │  redirect_stdout    重定向 print 输出        │   │
│  │  redirect_stderr    重定向 stderr            │   │
│  │  ExitStack          动态管理多个管理器       │   │
│  │  nullcontext()      空操作上下文             │   │
│  │  ContextDecorator   装饰器+上下文二合一       │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │       内置上下文管理器                        │   │
│  │                                             │   │
│  │  open()            文件操作                  │   │
│  │  threading.Lock    线程锁                   │   │
│  │  subprocess.Popen  子进程                   │   │
│  │  socket.socket     网络套接字               │   │
│  │  decimal.localcontext 十进制上下文          │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │       异步上下文管理器 (Python 3.5+)          │   │
│  │  __aenter__(self)                            │   │
│  │  __aexit__(self, exc_type, exc_val, exc_tb)  │   │
│  │  @asynccontextmanager                        │   │
│  │  async with expr as var:                     │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 5. with 语句的伪代码解释

```text
with EXPRESSION as TARGET:
    BLOCK
```

等价于：

```text
manager = (EXPRESSION)          # 计算表达式得到管理器
value = manager.__enter__()     # 调用 __enter__
TARGET = value                  # 绑定到 as 目标
exc = True                      # 标记是否有异常
try:
    BLOCK                       # 执行代码块
    exc = False                 # 无异常
except:
    exc = True                  # 有异常
    if not manager.__exit__(*sys.exc_info()):
        raise                   # __exit__ 返回 False，继续传播
finally:
    if not exc:
        manager.__exit__(None, None, None)  # 无异常时正常退出
```

注意：实际 CPython 实现更复杂（使用特殊的 `SETUP_WITH` 字节码），
但上述伪代码准确地反映了语义。

## 6. ExitStack 动态管理架构

```mermaid
flowchart LR
    subgraph Entry["进入 ExitStack"]
        E1["stack = ExitStack()"]
        E2["conn1 = stack.enter_context(open('a.txt'))"]
        E3["conn2 = stack.enter_context(open('b.txt'))"]
        E4["conn3 = stack.enter_context(lock)"]
    end

    subgraph Exit["退出 with 块"]
        X1["conn3.close()  ← LIFO 顺序"]
        X2["conn2.close()"]
        X3["conn1.close()"]
    end

    E1 --> E2 --> E3 --> E4
    E4 -.-> X1 --> X2 --> X3

    style Entry fill:#e8f5e9
    style Exit fill:#fce4ec
```

## 7. 异常在 __exit__ 中的传播路径

```text
场景 A：正常退出
  with块 ──(无异常)──→ __exit__(None, None, None)
                               │
                               ↓
                        返回 False → 正常继续

场景 B：异常被抑制
  with块 ──(ZeroDivisionError)──→ __exit__(ZeroDivisionError, ..., ...)
                                           │
                                    返回 True
                                           │
                                           ↓
                                    异常被抑制
                                    程序继续

场景 C：异常被传播
  with块 ──(ValueError)──→ __exit__(ValueError, ..., ...)
                                     │
                              返回 False
                                     │
                                     ↓
                              ValueError 继续传播
                              try/except 可以捕获

场景 D：异常被替换
  with块 ──(ValueError)──→ __exit__(ValueError, ..., ...)
                                     │
                              __exit__ 自身抛出 RuntimeError
                                     │
                                     ↓
                              RuntimeError 替代 ValueError
                              原 ValueError 丢失 (__context__ 中)
```
