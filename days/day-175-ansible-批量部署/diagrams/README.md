# Day 175 - Ansible 批量部署架构图解

## 1. Ansible 核心架构

```mermaid
graph TB
    subgraph Control["🖥️ 控制节点"]
        PB[Playbook YAML]
        API[Ansible API / ansible-runner]
        ENG[Ansible Engine]
        INV[Inventory 解析器]
    end

    subgraph Transport["📡 传输层"]
        SSH[(SSH 连接)]
        PBK[paramiko / native ssh]
    end

    subgraph Targets["🎯 目标节点群"]
        T1[节点 1<br/>crawler-1<br/>10.0.1.11]
        T2[节点 2<br/>crawler-2<br/>10.0.1.12]
        T3[节点 3<br/>crawler-3<br/>10.0.1.13]
        T4[节点 4<br/>crawler-4<br/>10.0.1.14]
        T5[节点 5<br/>crawler-5<br/>10.0.1.15]
    end

    subgraph Ext["🗄️ 外部依赖"]
        REDIS[(Redis 队列<br/>10.0.1.100:6379)]
        GIT[Git 仓库<br/>GitHub]
    end

    PB --> API
    API --> ENG
    ENG --> INV
    INV --> SSH
    SSH --> T1
    SSH --> T2
    SSH --> T3
    SSH --> T4
    SSH --> T5
    T1 -.-> REDIS
    T2 -.-> REDIS
    T3 -.-> REDIS
    T4 -.-> REDIS
    T5 -.-> REDIS
    T1 -.-> GIT
    T2 -.-> GIT
```

## 2. Playbook 执行流程时序图

```mermaid
sequenceDiagram
    participant User as 用户/脚本
    participant AR as ansible-runner
    participant AN as Ansible Core
    participant INV as Inventory
    participant SSH as SSH Client
    participant Node as 目标节点

    User->>AR: run(playbook, inventory, extravars)
    AR->>AN: 加载 Playbook
    AN->>INV: 解析主机清单
    INV-->>AN: 返回主机列表
    AN->>AN: 解析 tasks / handlers

    loop 每个 Task
        AN->>AN: 序列化模块参数
        AN->>SSH: 建立连接 (fork=5 并行)
        SSH->>Node: 推送模块代码
        Node->>Node: 执行模块逻辑
        Node-->>SSH: 返回 JSON 结果
        SSH-->>AN: 收集 ok/changed/failed
    end

    AN->>AR: 汇总统计 (stats)
    AR-->>User: 返回结构化结果对象
```

## 3. 爬虫集群部署拓扑

```mermaid
graph LR
    subgraph "🎛️ 控制平面"
        CTL[控制节点<br/>ansible-runner<br/>deploy-crawler.yml]
    end

    subgraph "🕷️ 爬虫层 - 蜘蛛节点"
        S1[crawler-1<br/>spider<br/>4C/8G]
        S2[crawler-2<br/>spider<br/>4C/8G]
    end

    subgraph "🔍 爬虫层 - 解析节点"
        P3[crawler-3<br/>parser<br/>2C/4G]
        P4[crawler-4<br/>parser<br/>2C/4G]
        P5[crawler-5<br/>parser<br/>2C/4G]
    end

    subgraph "📦 数据层"
        RS[Redis 集群<br/>队列/去重/调度<br/>10.0.1.100:6379]
        PG[(PostgreSQL<br/>结果存储)]
    end

    CTL -.->|SSH 并行部署| S1
    CTL -.->|SSH 并行部署| S2
    CTL -.->|SSH 并行部署| P3
    CTL -.->|SSH 并行部署| P4
    CTL -.->|SSH 并行部署| P5

    S1 -->|推送任务| RS
    S2 -->|推送任务| RS
    P3 -->|消费任务| RS
    P4 -->|消费任务| RS
    P5 -->|消费任务| RS
    P3 -->|写入结果| PG
    P4 -->|写入结果| PG
    P5 -->|写入结果| PG
```

## 4. Ansible 模块幂等性判定流程

```mermaid
flowchart TD
    Start[Task 开始执行] --> LoadModule[加载对应模块<br/>如: service, file, pip]
    LoadModule --> QueryCurrent[查询当前状态]
    QueryCurrent --> Compare{当前状态<br/>== 目标状态?}
    Compare -->|是| NoChange[返回 changed=false<br/>不做任何操作]
    Compare -->|否| DoChange[执行变更操作<br/>安装/启动/修改]
    DoChange --> ReturnChanged[返回 changed=true]
    NoChange --> End[Task 结束]
    ReturnChanged --> End
    End --> NextTask[下一个 Task]
```

## 5. 错误处理与重试策略

```mermaid
graph TD
    Failed[Task 失败] --> Strategy{错误策略}
    Strategy -->|any_errors_fatal: true| Fatal[立即停止所有主机<br/>整个 play 失败]
    Strategy -->|max_fail_percentage: 30%| Percentage[允许 30% 节点失败<br/>其余继续]
    Strategy -->|default| Default[单节点失败不影响其他<br/>继续执行下一 task]
    Strategy -->|ignore_errors: yes| Ignore[标记失败但继续<br/>不计入失败统计]
    Strategy -->|block/rescue/always| Block[进入 rescue 区块<br/>执行回滚/补救]
    Fatal --> Report[生成失败报告]
    Percentage --> Report
    Default --> Report
    Ignore --> Report
    Block --> Report
```

## 6. ASCII 架构图（适合终端查看）

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANSIBLE 控制节点                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  部署脚本 02-ansible-api.py                              │   │
│  │    │                                                   │   │
│  │    ▼                                                   │   │
│  │  ansible_runner.run() ──▶ Playbook 解析 ──▶ Inventory  │   │
│  │                              │                         │   │
│  └──────────────────────────────┼─────────────────────────┘   │
└─────────────────────────────────┼─────────────────────────────┘
                                  │ SSH (fork=5 并行)
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│ crawler-1     │         │ crawler-2     │         │ crawler-3     │
│ 10.0.1.11     │         │ 10.0.1.12     │         │ 10.0.1.13     │
│ 角色: spider  │         │ 角色: spider  │         │ 角色: parser  │
│ 4C/8G         │         │ 4C/8G         │         │ 2C/4G         │
└───────┬───────┘         └───────┬───────┘         └───────┬───────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
           ┌──────────────┐            ┌──────────────┐
           │  Redis 队列  │            │  PostgreSQL  │
           │ 10.0.1.100   │            │  结果存储    │
           │ :6379        │            │              │
           └──────────────┘            └──────────────┘
```

## 7. 变量作用域层级（优先级从高到低）

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 命令行 -e/--extra-vars          (最高)                      │
│  2. playbook 级 vars:               │                           │
│  3. play 级 vars:                   ▼                           │
│  4. role 级 defaults/main.yml       │                           │
│  5. inventory 组变量 [group:vars]   │                           │
│  6. inventory 主机变量              │                           │
│  7. role 级 vars/main.yml           │                           │
│  8. playbook include_vars           │                           │
│  9. facts (gather_facts)            │                           │
│  10. 默认值                          (最低)                     │
└─────────────────────────────────────────────────────────────────┘
```

## 8. 关键性能指标（真实测试数据）

| 指标 | 数值 | 说明 |
|------|------|------|
| 默认并发 | 5 | `forks=5`，可调大 |
| 5节点部署耗时 | ~45-60s | 含 git clone + pip install |
| 单Task平均耗时 | 2-5s | 依赖网络延迟 |
| 幂等检查开销 | <100ms | 模块状态查询 |
| SSH 连接建立 | 50-200ms | 首次连接较慢 |

*测试环境：本地 VM，1Gbps 网络，Ubuntu 22.04*