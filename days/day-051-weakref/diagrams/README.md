# Day 051 — 弱引用图解

## 1. 强引用 vs 弱引用

```mermaid
graph LR
    subgraph 强引用
        A[变量 a] -->|强引用| B[对象 42]
        C[变量 b] -->|强引用| B
    end

    subgraph 弱引用
        D[变量 c] -->|强引用| E[对象 99]
        F[weakref.ref] -.->|弱引用| E
    end
```

## 2. 弱引用生命周期

```mermaid
sequenceDiagram
    participant User
    participant Object as 对象
    participant WeakRef as weakref.ref

    User->>Object: 创建对象
    User->>WeakRef: 创建弱引用
    WeakRef->>Object: 指向对象（不增加引用计数）

    Note over Object: 对象仍然存活

    User->>Object: del 对象
    Note over Object: 引用计数归零
    Note over WeakRef: 弱引用返回 None
```

## 3. 循环引用问题

```mermaid
graph LR
    A[对象A] -->|强引用| B[对象B]
    B -->|强引用| A

    style A fill:#ff6b6b,color:#fff
    style B fill:#ff6b6b,color:#fff
```

## 4. 弱引用打破循环

```mermaid
graph LR
    A[对象A] -->|强引用| B[对象B]
    B -.->|弱引用| A

    style A fill:#51cf66,color:#fff
    style B fill:#51cf66,color:#fff
```

## 5. WeakValueDictionary 工作原理

```mermaid
sequenceDiagram
    participant Cache as WeakValueDictionary
    participant Obj as 对象

    Cache->>Cache: 存储弱引用指向对象
    Note over Cache: 对象仍在使用

    Obj->>Obj: 删除对象
    Cache->>Cache: 弱引用失效
    Cache->>Cache: 自动清理条目
```

## 6. 观察者模式中的弱引用

```mermaid
graph TD
    subgraph EventBus
        WS[WeakSet]
    end

    subgraph Observers
        O1[观察者1]
        O2[观察者2]
        O3[观察者3]
    end

    O1 -.->|弱引用| WS
    O2 -.->|弱引用| WS
    O3 -.->|弱引用| WS

    WS -->|发布事件| O1
    WS -->|发布事件| O2
    WS -->|发布事件| O3
```

## 7. 引用计数变化

```mermaid
graph TD
    A[创建对象] -->|refcount = 1| B[强引用 a]
    B -->|refcount = 2| C[创建弱引用]
    C -->|refcount 不变| D[弱引用不影响计数]
    D -->|refcount = 1| E[del a]
    E -->|refcount = 0| F[对象被 GC 回收]
    F -->|弱引用返回 None| G[弱引用失效]
```

## 8. 内存布局对比

```
强引用:                          弱引用:
┌─────────────┐                  ┌─────────────┐
│ 变量 a      │                  │ 变量 a      │
└──────┬──────┘                  └──────┬──────┘
       │                               │
       ▼                               ▼
┌─────────────┐                  ┌─────────────┐
│ 对象        │                  │ 对象        │
│ refcount=2  │                  │ refcount=1  │
└─────────────┘                  └─────────────┘
                                        ▲
                                        │
                                 ┌──────────────┐
                                 │ weakref.ref  │
                                 │ (不增加计数) │
                                 └──────────────┘
```
