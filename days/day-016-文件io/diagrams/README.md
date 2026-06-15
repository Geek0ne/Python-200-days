# 文件 I/O 图解

---

## 1. 文件打开模式体系图

```mermaid
graph TB
    subgraph "打开模式体系"
        direction TB
        MODE[open(file, mode)]
        MODE --> BASIC[基本操作]
        MODE --> TYPE[文件类型]
        MODE --> EXTRA[附加操作]
        
        BASIC --> R["r - 只读"]
        BASIC --> W["w - 写入(清空)"]
        BASIC --> A["a - 追加"]
        BASIC --> X["x - 排他创建"]
        
        TYPE --> T["t - 文本模式(默认)"]
        TYPE --> B["b - 二进制模式"]
        
        EXTRA --> PLUS["+ - 读写"]
    end
    
    subgraph "常见组合"
        COM1["r+t"] --> |"文本读写<br>常用: JSON编辑"| COM1U
        COM2["w+b"] --> |"二进制读写<br>常用: 图片处理"| COM2U
        COM3["a+t"] --> |"追加读取<br>常用: 日志查看"| COM3U
        COM4["x+t"] --> |"排他写<br>常用: 避免覆盖"| COM4U
    end
```

## 2. `with` 语句执行流程

```mermaid
sequenceDiagram
    participant User as 代码块
    participant With as with 语句
    participant Enter as __enter__
    participant Body as 文件操作
    participant Exit as __exit__
    participant File as 文件
    
    User->>With: with open("file", "r") as f:
    With->>Enter: 调用 f.__enter__()
    Enter->>File: 打开文件
    Enter-->>With: 返回文件对象 f
    Note over With,Body: 进入缩进块
    Body->>File: 读写操作
    Note over Body: 读写正常 或 发生异常
    Body->>Exit: 离开缩进块
    Exit->>File: f.close()
    
    alt 无异常
        Exit-->>With: 返回 None
        With-->>User: 继续执行
    else 有异常
        Exit-->>With: 返回 True → 吞异常<br>返回 False → 抛异常
        With-->>User: 处理异常
    end
```

## 3. 文本模式 vs 二进制模式处理流程

```mermaid
flowchart LR
    subgraph "文本模式 (t)"
        direction TB
        A1["字符串 str<br>'Hello'"] -->|"encode()<br>UTF-8"| A2["字节流<br>b'Hello'"]
        A2 -->|"write()"| A3["文件系统"]
        A3 -->|"read()"| A4["字节流<br>b'Hello'"]
        A4 -->|"decode()<br>UTF-8"| A5["字符串 str<br>'Hello'"]
    end
    
    subgraph "二进制模式 (b)"
        direction TB
        B1["字节串 bytes<br>b'Hello'"] -->|"write()"| B2["文件系统"]
        B2 -->|"read()"| B3["字节串 bytes<br>b'Hello'"]
    end
    
    A3 -.->|"\\n ↔ \\r\\n<br>平台转换"| A3_PLATFORM
```

## 4. 文件指针 seek/tell 示意图

```ascii
文件内容:  H e l l o   W o r l d  \n
          0 1 2 3 4 5 6 7 8 9 10 11
          
① open() 后:
  H e l l o   W o r l d  \n
  ↑
  pos=0 (文件开头)

② f.read(5) 后:
  H e l l o   W o r l d  \n
            ↑
            pos=5

③ f.read() 后 (读完):
  H e l l o   W o r l d  \n
                              ↑
                              pos=12 (文件末尾)

④ f.seek(6): 移动到第 6 个位置
  H e l l o   W o r l d  \n
              ↑
              pos=6

⑤ f.seek(-3, 2): 从末尾往前 3
  H e l l o   W o r l d  \n
                          ↑
                          pos=9
```

## 5. 不同打开模式的文件指针位置

```ascii
┌────────────────────────────────────────────┐
│                   文件内容                    │
│  ┌─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┐  │
│  │H│e│l│l│o│ │W│o│r│l│d│ │!│\n│T│e│s│t│  │
│  └─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┘  │
│  pos:  0       5       10        15         │
└────────────────────────────────────────────┘

模式 r/r+:    ↑ (pos=0)         只读或读写
模式 w/w+:    清空 → ↑ (pos=0)  先清空再写
模式 a/a+:                     ↑ (pos=18) 追加到末尾
模式 x:       新文件 → ↑ (pos=0) 不存在才创建
```

## 6. 编码错误处理策略对比

```mermaid
flowchart TD
    ENC[读取文件] --> CHECK{编码匹配?}
    CHECK -->|"✅ 是"| OK[正常读取]
    CHECK -->|"❌ 否"| ERR[编码错误]
    
    ERR --> STRATEGY{处理策略}
    
    STRATEGY -->|"strict (默认)"| RAISE["抛出 UnicodeDecodeError<br>最安全，不丢失数据"]
    STRATEGY -->|"ignore"| IGNORE["静默跳过非法字节<br>⚠️ 可能丢失数据"]
    STRATEGY -->|"replace"| REPLACE["用 ? 替换<br>保留内容长度"]
    STRATEGY -->|"backslashreplace"| BS["用 \\xNN 转义<br>不丢失信息"]
    STRATEGY -->|"surrogateescape"| SE["Python 专用编码<br>用于 OS 接口"]
```

## 7. 文件操作 API 速查图

```mermaid
classDiagram
    class FileObject {
        +name: str
        +mode: str
        +encoding: str
        +closed: bool
        +read(n) str
        +readline() str
        +readlines() list
        +write(s) int
        +writelines(lines)
        +seek(offset, whence) int
        +tell() int
        +truncate(size)
        +flush()
        +close()
        +fileno() int
        +seekable() bool
        +readable() bool
        +writable() bool
        +detach() IOBase
    }
    
    class TextIOWrapper {
        +encoding: str
        +errors: str
        +newlines: str
        文本模式包装器
    }
    
    class BufferedRandom {
        可读写的缓冲流
    }
    
    FileObject <|-- TextIOWrapper
    FileObject <|-- BufferedRandom
```

---

## 8. 大文件处理策略对比

```mermaid
flowchart LR
    subgraph "小文件 (<100MB)"
        A["f.read()"] -->|"一次性加载<br>速度最快"| A_RES["✅ 简单直接"]
    end
    
    subgraph "大文本文件"
        B["for line in f"] -->|"逐行迭代<br>内存高效"| B_RES["✅ 逐行处理"]
    end
    
    subgraph "超大二进制文件"
        C["while chunk = f.read(8KB)"] -->|"分块读取<br>可控内存"| C_RES["✅ 流式处理"]
    end
    
    FILE_SIZE{文件大小} --> A
    FILE_SIZE --> B
    FILE_SIZE --> C
```
