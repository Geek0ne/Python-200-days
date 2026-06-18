# Day 027 — 图解：时间与日期

本目录包含 Day 027 主题相关的 ASCII 图和 Mermaid 图解。

---

## 图一：datetime 模块对象关系图

### ASCII 版本

```text
                    ┌─────────────────────────────────────────┐
                    │            datetime 模块                  │
                    │  (from datetime import ...)              │
                    └─────────────────────────────────────────┘
                                      │
          ┌───────────────┬───────────┴───────────┬───────────────┐
          │               │                       │               │
          ▼               ▼                       ▼               ▼
   ┌──────────┐    ┌──────────┐           ┌──────────┐    ┌──────────────┐
   │   date   │    │   time   │           │ datetime │    │   timedelta  │
   │ (日期)   │    │ (时间)   │           │ (日期+时间)│   │ (时间差)     │
   │          │    │          │           │          │    │              │
   │ year     │    │ hour     │           │ year     │    │ days         │
   │ month    │    │ minute   │ 继承 date │ month    │    │ seconds      │
   │ day      │    │ second   │──────────►│ day      │    │ microseconds │
   │          │    │ microsec │           │ hour     │    │              │
   │ today()  │    │ tzinfo   │           │ minute   │    │ total_secs() │
   │ weekday()│    │          │           │ second   │    │              │
   └──────────┘    └──────────┘           │ microsec │    └──────────────┘
                                          │ tzinfo   │
                                          │          │
                                          │ now()    │
                                          │ strftime │
                                          │ strptime │
                                          │ timestamp│
                                          └──────────┘
```

### Mermaid 版本

```mermaid
classDiagram
    class date {
        -int year
        -int month
        -int day
        +today() date
        +weekday() int
        +strftime(fmt) str
    }
    
    class time {
        -int hour
        -int minute
        -int second
        -int microsecond
        -tzinfo tz
    }
    
    class datetime {
        -int year
        -int month
        -int day
        -int hour
        -int minute
        -int second
        -int microsecond
        -tzinfo tz
        +now() datetime
        +fromtimestamp(ts) datetime
        +timestamp() float
        +strftime(fmt) str
        +strptime(s, fmt) datetime
        +astimezone(tz) datetime
    }
    
    class timedelta {
        -int days
        -int seconds
        -int microseconds
        +total_seconds() float
    }
    
    datetime --|> date : 继承
    datetime ..> timedelta : 运算产生
    datetime ..> time : 包含时间部分
    datetime ..> date : 包含日期部分
```

---

## 图二：时间转换流程

### 三种时间形态的相互转换

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    时间的三重形态                                     │
└─────────────────────────────────────────────────────────────────────┘

                      ┌─────────────────┐
                      │    📦 时间戳      │
                      │  (Unix Epoch秒数) │
                      │  1755000000.0    │
                      └────────┬────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  fromtimestamp() │ │  fromtimestamp() │ │  fromtimestamp()│
    │  (datetime模块)  │ │  (date模块)      │ │  (time模块)     │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │                   │                   │
             ▼                   ▼                   │
    ┌─────────────────┐ ┌─────────────────┐          │
    │  📋 datetime     │ │  📅 date         │          │
    │  2026-06-18      │ │  2026-06-18      │          │
    │  09:15:30        │ │                  │          │
    └────────┬────────┘ └──────────────────┘          │
             │                                        │
             ▼                                        ▼
    ┌─────────────────┐                    ┌─────────────────┐
    │  ✏️ 格式化       │                    │  ⏰ time         │
    │  strftime()     │                    │  09:15:30        │
    │  "2026-06-18..."│                    │                  │
    └─────────────────┘                    └─────────────────┘

               strptime() 反向操作:
               "2026-06-18 09:15:30" ──► datetime对象
```

### Mermaid 流程图

```mermaid
flowchart TD
    subgraph "输入层"
        A["⏱️ 时间戳<br/>float / int"]
        B["📝 时间字符串<br/>'2026-06-18 09:15:30'"]
        C["📐 结构化数据<br/>(year, month, day, ...)"]
    end
    
    subgraph "转换层"
        D["datetime.fromtimestamp()"]
        E["datetime.strptime()"]
        F["datetime(year, month, day, ...)"]
        G["datetime.now() / datetime.utcnow()"]
    end
    
    subgraph "中间表示"
        H["📦 datetime 对象<br/>(带或不带时区)"]
    end
    
    subgraph "输出层"
        I["🔢 timestamp()<br/>→ 时间戳"]
        J["📝 strftime()<br/>→ 字符串"]
        K["📊 date() / time()<br/>→ 部分提取"]
        L["📏 运算 (A-B, A+td)<br/>→ timedelta / datetime"]
    end
    
    A --> D --> H
    B --> E --> H
    C --> F --> H
    G --> H
    
    H --> I
    H --> J
    H --> K
    H --> L
```

---

## 图三：时区转换示意图

### Naive ↔ Aware 转换

```text
              ⚠️ 不允许直接混合运算！ ⚠️

Naive datetime                    Aware datetime
(tzinfo=None)                     (tzinfo=ZoneInfo(...))
    │                                    │
    │                                    │
    │    ┌─────────────────────┐          │
    │    │  方案 A: 补充时区    │          │
    └───►│  replace(tzinfo=utc)│          │
         │                     │◄─────────┘
         │  方案 B: 去除时区    │
         │  replace(tzinfo=None)│
         └─────────────────────┘
                    │
                    ▼
          ⚡ 统一后的 datetime
          (双方类型一致，可以运算)
```

### 跨时区时间转换

```text
UTC 时间 (数据库存储)
    │
    │  astimezone(ZoneInfo('Asia/Shanghai'))
    ▼
北京时间: 2026-06-18 15:00:00 CST (UTC+8)
    │
    │  astimezone(ZoneInfo('America/New_York'))
    ▼
纽约时间: 2026-06-18 03:00:00 EDT (UTC-4)  [夏令时]

关键原则:
┌────────────────────────────────────────────┐
│  ✅ 存储: UTC                              │
│  ✅ 计算: UTC 统一基准                      │
│  ✅ 显示: 根据用户时区转换                   │
│  ❌ 禁止: naive + aware 混用               │
│  ❌ 禁止: 存储带时区的本地时间                │
└────────────────────────────────────────────┘
```

### Mermaid 时序图

```mermaid
sequenceDiagram
    participant User as 用户 (北京)
    participant App as 应用系统
    participant DB as 数据库 (UTC)
    participant NYC as 纽约用户
    
    User->>App: 输入会议时间 15:00 (CST)
    App->>App: 转换为 UTC 07:00
    App->>DB: 存储 UTC 时间
    Note over DB: 2026-06-18 07:00:00 UTC
    
    NYC->>App: 查询会议时间
    App->>DB: 读取 UTC 时间
    App->>App: 转换为纽约时区
    App->>NYC: 显示 03:00 EDT
    Note over NYC: 2026-06-18 03:00 EDT
    
    User->>App: 查询会议时间
    App->>DB: 读取 UTC 时间
    App->>App: 转换为北京时间
    App->>User: 显示 15:00 CST
    Note over User: 2026-06-18 15:00 CST
```

---

## 图四：时间格式解析流程

### strptime 的解析过程

```text
输入: "18/Jun/2026:09:15:30 +0800"
格式: "%d/%b/%Y:%H:%M:%S %z"

解析过程 (从左到右):

位置 0: "1"  → %d 开始, 读入 "18"    → day = 18
位置 2: "/"  → 匹配分隔符 "/"
位置 3: "J"  → %b 开始, 读入 "Jun"   → month = 6
位置 6: "/"  → 匹配分隔符 "/"
位置 7: "2"  → %Y 开始, 读入 "2026"  → year = 2026
位置 11: ":" → 匹配分隔符 ":"
位置 12: "0" → %H 开始, 读入 "09"    → hour = 9
位置 14: ":" → 匹配分隔符 ":"
位置 15: "1" → %M 开始, 读入 "15"    → minute = 15
位置 17: ":" → 匹配分隔符 ":"
位置 18: "3" → %S 开始, 读入 "30"    → second = 30
位置 20: " " → 匹配分隔符 " "
位置 21: "+" → %z 开始, 读入 "+0800" → tz = UTC+08:00

┌────────────────────────────────────────┐
│ 解析结果:                              │
│ datetime(2026, 6, 18, 9, 15, 30,      │
│          tzinfo=timezone(+08:00))      │
└────────────────────────────────────────┘
```

### Mermaid 流程图

```mermaid
flowchart LR
    A["字符串<br/>'18/Jun/2026:09:15:30 +0800'"] --> B["strptime"]
    B --> C["格式模板<br/>'%d/%b/%Y:%H:%M:%S %z'"]
    C --> D{"逐字符匹配"}
    
    D -->|"%d → 18"| E["day=18"]
    D -->|"/ → 分隔符"| F{"继续"}
    D -->|"%b → Jun"| G["month=6"]
    D -->|"/ → 分隔符"| H{"继续"}
    D -->|"%Y → 2026"| I["year=2026"]
    D -->|": → 分隔符"| J{"继续"}
    D -->|"%H → 09"| K["hour=9"]
    D -->|": → 分隔符"| L{"继续"}
    D -->|"%M → 15"| M["minute=15"]
    D -->|": → 分隔符"| N{"继续"}
    D -->|"%S → 30"| O["second=30"]
    D -->|" → 分隔符"| P{"继续"}
    D -->|"%z → +0800"| Q["tz=UTC+8"]
    
    E --> R["✨ datetime 对象<br/>2026-06-18 09:15:30+08:00"]
    G --> R
    I --> R
    K --> R
    M --> R
    O --> R
    Q --> R
```
