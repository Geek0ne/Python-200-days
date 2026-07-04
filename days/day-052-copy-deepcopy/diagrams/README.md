# Day 052 — 深拷贝与浅拷贝图解

## 1. 赋值 vs 浅拷贝 vs 深拷贝

```mermaid
graph TD
    subgraph 赋值
        A[变量 a] --> Obj[列表对象]
        B[变量 b] --> Obj
    end

    subgraph 浅拷贝
        C[变量 c] --> NewObj1[新列表对象]
        NewObj1 -->|共享引用| Elem[元素 1, 2, 3]
        Obj -->|共享引用| Elem
    end

    subgraph 深拷贝
        D[变量 d] --> NewObj2[新列表对象]
        NewObj2 -->|独立引用| NewElem[新元素 1, 2, 3]
    end
```

## 2. 内存布局对比

```
赋值:
┌─────────────┐
│ 变量 a      │──┐
└─────────────┘  │
                 ▼
┌─────────────┐  │
│ 变量 b      │──┘
└─────────────┘
                 │
                 ▼
          ┌─────────────┐
          │ 列表对象     │
          │ refcount=2  │
          └─────────────┘

浅拷贝:
┌─────────────┐          ┌─────────────┐
│ 变量 a      │          │ 变量 c      │
└──────┬──────┘          └──────┬──────┘
       │                        │
       ▼                        ▼
┌─────────────┐          ┌─────────────┐
│ 原列表对象   │          │ 新列表对象   │
└──────┬──────┘          └──────┬──────┘
       │                        │
       └──────────┬─────────────┘
                  ▼
          ┌─────────────┐
          │ 共享元素     │
          │ [1, 2, 3]   │
          └─────────────┘

深拷贝:
┌─────────────┐          ┌─────────────┐
│ 变量 a      │          │ 变量 d      │
└──────┬──────┘          └──────┬──────┘
       │                        │
       ▼                        ▼
┌─────────────┐          ┌─────────────┐
│ 原列表对象   │          │ 新列表对象   │
└──────┬──────┘          └──────┬──────┘
       │                        │
       ▼                        ▼
┌─────────────┐          ┌─────────────┐
│ 元素 [1,2,3]│          │ 新元素 [1,2,3]│
└─────────────┘          └─────────────┘
```

## 3. 浅拷贝陷阱

```mermaid
graph LR
    subgraph 浅拷贝
        A[变量 a] --> Obj1[列表对象]
        B[变量 b] --> Obj2[新列表对象]
        Obj1 -->|共享| Nested[嵌套列表]
        Obj2 -->|共享| Nested
    end

    style Nested fill:#ff6b6b,color:#fff
```

## 4. 深拷贝完全独立

```mermaid
graph TD
    subgraph 深拷贝
        A[变量 a] --> Obj1[列表对象]
        B[变量 b] --> Obj2[新列表对象]
        Obj1 --> Nested1[嵌套列表 1]
        Obj2 --> Nested2[嵌套列表 2]
    end

    style Nested1 fill:#51cf66,color:#fff
    style Nested2 fill:#51cf66,color:#fff
```

## 5. memo 参数处理循环引用

```mermaid
sequenceDiagram
    participant User
    participant Deepcopy as copy.deepcopy
    participant Memo as memo 字典
    participant Obj as 对象A

    User->>Deepcopy: deepcopy(对象A)
    Deepcopy->>Memo: 检查 id(对象A)
    Note over Memo: 未找到，继续拷贝

    Deepcopy->>Obj: 拷贝对象A的属性
    Deepcopy->>Memo: memo[id(对象A)] = 新对象A

    Note over Deepcopy: 发现循环引用

    Deepcopy->>Memo: 检查 id(对象A)
    Note over Memo: 已找到，返回已拷贝的对象
```

## 6. 深拷贝去重

```mermaid
graph TD
    subgraph 原始容器
        C1[索引 0] --> Obj[共享对象]
        C2[索引 1] --> Obj
        C3[索引 2] --> Obj
    end

    subgraph 深拷贝容器
        D1[索引 0] --> NewObj[新共享对象]
        D2[索引 1] --> NewObj
        D3[索引 2] --> NewObj
    end

    style Obj fill:#ff6b6b,color:#fff
    style NewObj fill:#51cf66,color:#fff
```

## 7. 快照与回滚

```mermaid
graph LR
    subgraph 状态历史
        S1[状态 1] --> S2[状态 2] --> S3[状态 3]
    end

    subgraph 当前状态
        C[当前] -.->|undo| S2
        C -.->|redo| S3
    end
```

## 8. 拷贝方式速查

```mermaid
graph TD
    A[需要拷贝] --> B{对象类型?}

    B -->|不可变: int/str/tuple| C[不需要拷贝]
    B -->|可变: list/dict/set| D{嵌套可变对象?}

    D -->|否| E[copy.copy]
    D -->|是| F[copy.deepcopy]

    C --> G[直接赋值]
    E --> H[浅拷贝]
    F --> I[深拷贝]
```
