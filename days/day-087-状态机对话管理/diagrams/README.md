# Day 087 — 状态机对话管理 · 图解

## 1. 客服机器人状态流转图

```mermaid
stateDiagram-v2
    [*] --> WelcomeState : 用户首次进入

    WelcomeState --> WelcomeState : 问候/寒暄
    WelcomeState --> CollectingState : 预订/投诉意图
    WelcomeState --> QueryState : 查询意图
    WelcomeState --> CancelState : 取消意图
    WelcomeState --> ByeState : 告别意图

    CollectingState --> CollectingState : 填充槽位
    CollectingState --> ProcessingState : 所有槽位已满
    CollectingState --> WelcomeState : 取消操作
    CollectingState --> ByeState : 告别

    ProcessingState --> WelcomeState : 处理完成

    QueryState --> WelcomeState : 查询完毕

    CancelState --> WelcomeState : 取消完成

    ByeState --> [*]
```

## 2. 槽位填充流程

```mermaid
flowchart TD
    A[用户输入] --> B{意图识别}
    B -->|预订| C[初始化预订槽位]
    B -->|投诉| D[初始化投诉槽位]
    B -->|其他| E[对应处理]

    C --> F{获取下一个空槽位}
    D --> F

    F -->|有空槽位| G[提问: 请提供xxx]
    G --> H[用户回答]
    H --> I{验证通过?}
    I -->|是| J[填充槽位]
    I -->|否| K[提示格式错误, 重新提问]
    K --> G

    J --> L{所有槽位已满?}
    L -->|否| F
    L -->|是| M[执行业务逻辑]
    M --> N[返回结果, 重置状态]
```

## 3. 对话上下文数据结构

```mermaid
classDiagram
    class DialogueContext {
        +str user_id
        +Intent intent
        +Dict slots
        +List~SlotDef~ slot_defs
        +List~Dict~ history
        +int turn_count
        +fill_slot(name, value) bool
        +get_next_slot() SlotDef
        +all_slots_filled() bool
        +add_message(role, text)
        +reset()
    }

    class SlotDef {
        +str name
        +str question
        +bool required
        +Callable validator
    }

    class Intent {
        <<enumeration>>
        GREET
        BOOK
        QUERY
        COMPLAINT
        CANCEL
        BYE
        UNKNOWN
    }

    DialogueContext "1" --> "*" SlotDef : slot_defs
    DialogueContext --> Intent : intent
```

## 4. 状态模式 UML 类图

```mermaid
classDiagram
    class State {
        <<abstract>>
        +handle(ctx, input) State
        +get_response(ctx) str
    }

    class WelcomeState {
        +handle(ctx, input) State
        +get_response(ctx) str
    }

    class CollectingState {
        +handle(ctx, input) State
        +get_response(ctx) str
    }

    class ProcessingState {
        +handle(ctx, input) State
        +get_response(ctx) str
    }

    class QueryState {
        +handle(ctx, input) State
        +get_response(ctx) str
    }

    class CancelState {
        +handle(ctx, input) State
        +get_response(ctx) str
    }

    class ByeState {
        +handle(ctx, input) State
        +get_response(ctx) str
    }

    State <|-- WelcomeState
    State <|-- CollectingState
    State <|-- ProcessingState
    State <|-- QueryState
    State <|-- CancelState
    State <|-- ByeState

    class ChatbotEngine {
        +Dict sessions
        +get_context(user_id) DialogueContext
        +chat(user_id, message) str
        +get_history(user_id) List
    }

    ChatbotEngine --> DialogueContext
    DialogueContext --> State : _state
```

## 5. 预订流程时序图

```mermaid
sequenceDiagram
    actor U as 用户
    participant B as ChatbotEngine
    participant S as WelcomeState
    participant C as CollectingState
    participant P as ProcessingState

    U->>B: "我要订机票"
    B->>S: handle(ctx, "我要订机票")
    S-->>B: 返回 CollectingState
    B-->>U: "请问出发城市？"

    U->>B: "北京"
    B->>C: handle(ctx, "北京")
    C-->>B: 填充 departure
    B-->>U: "请问目的地？"

    U->>B: "上海"
    B->>C: handle(ctx, "上海")
    C-->>B: 填充 destination
    B-->>U: "请问日期？"

    U->>B: "明天"
    B->>C: handle(ctx, "明天")
    C-->>B: 填充 date, 所有槽位已满
    C-->>B: 返回 ProcessingState

    B->>P: handle(ctx, "明天")
    P-->>B: 生成订单
    B-->>U: "✅ 预订成功！订单号: BK2026..."
```

## 6. 红绿灯状态转换（ASCII）

```
    ┌─────────┐
    │  红灯 🔴  │
    │  停止    │
    └────┬────┘
         │ timer
         ▼
    ┌─────────┐
    │  绿灯 🟢  │
    │  通行    │
    └────┬────┘
         │ timer
         ▼
    ┌─────────┐
    │  黄灯 🟡  │
    │  警示    │
    └────┬────┘
         │ timer
         └──────→ 回到红灯
```
