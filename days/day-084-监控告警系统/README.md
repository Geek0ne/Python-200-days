# Day 084 — 监控告警系统

> 📅 2026-07-26 | 🎯 Phase 6: 实战项目 — 项目三：自动化运维工具（Day 3/3）

---

## 📋 今日学习目标

1. 理解监控系统的设计原理与架构
2. 掌握系统指标采集（CPU、内存、磁盘、网络）
3. 学会实现告警规则引擎
4. 构建完整的服务器巡检与告警系统

---

## 1. 监控系统架构设计

### 1.1 什么是监控告警系统？

监控告警系统是运维自动化的**眼睛和耳朵**，负责：

```
┌─────────────────────────────────────────────────────────────┐
│                    监控告警系统架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │  数据采集 │───▶│ 数据存储  │───▶│ 分析引擎 │             │
│   │ Collector │    │  Store   │    │ Analyzer │             │
│   └──────────┘    └──────────┘    └──────────┘             │
│        │                               │                    │
│        │                               ▼                    │
│        │                        ┌──────────┐               │
│        │                        │ 告警规则  │               │
│        │                        │  Rules   │               │
│        │                        └──────────┘               │
│        │                               │                    │
│        ▼                               ▼                    │
│   ┌──────────┐                   ┌──────────┐              │
│   │  指标源   │                   │  通知渠道 │              │
│   │ (服务器)  │                   │ (邮件/钉钉)│             │
│   └──────────┘                   └──────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**核心组件：**

| 组件 | 职责 | 常用技术 |
|------|------|----------|
| 数据采集 (Collector) | 从目标服务器收集指标 | psutil, subprocess |
| 数据存储 (Store) | 存储历史指标数据 | SQLite, JSON文件 |
| 分析引擎 (Analyzer) | 对比指标与阈值 | 自定义规则引擎 |
| 告警规则 (Rules) | 定义告警触发条件 | 阈值、趋势、组合 |
| 通知渠道 (Notifier) | 发送告警通知 | 钉钉、邮件、短信 |

### 1.2 设计原则

1. **低侵入性**：监控本身不应影响被监控系统的性能
2. **可扩展性**：轻松添加新的监控指标和告警规则
3. **容错性**：采集失败不应导致整个系统崩溃
4. **实时性**：关键指标需要秒级采集

---

## 2. 系统指标采集

### 2.1 psutil 模块详解

`psutil` 是 Python 最强大的系统监控库，提供跨平台的系统信息访问。

#### 安装

```bash
pip install psutil
```

#### 核心 API 速查表

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `psutil.cpu_percent(interval=1)` | float | CPU 使用率 (%) |
| `psutil.cpu_count()` | int | CPU 核心数 |
| `psutil.cpu_freq()` | namedtuple | CPU 频率信息 |
| `psutil.virtual_memory()` | percent | 内存使用情况 |
| `psutil.disk_usage('/')` | percent | 磁盘使用情况 |
| `psutil.net_io_counters()` | namedtuple | 网络 I/O 统计 |
| `psutil.Process(pid)` | Process | 进程信息 |

#### 内存信息详解

```python
import psutil

# 完整内存信息
mem = psutil.virtual_memory()
print(f"总量: {mem.total / (1024**3):.2f} GB")
print(f"可用: {mem.available / (1024**3):.2f} GB")
print(f"已用: {mem.used / (1024**3):.2f} GB")
print(f"使用率: {mem.percent}%")
```

**内存字段说明：**

```
┌─────────────────────────────────────────┐
│              物理内存                      │
├─────────────────────────────────────────┤
│  total (总量)                            │
│  ┌──────────────────────────────────┐   │
│  │ used (已用)  │   available (可用)  │   │
│  │              │   ├─ free (空闲)   │   │
│  │              │   └─ buffers/cached│   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

> ⚠️ **常见误区**：`available` ≠ `free`。Linux 会利用空闲内存做磁盘缓存，这部分在需要时可被回收，所以 `available` 才是真正可用的内存。

#### 磁盘信息详解

```python
import psutil

# 磁盘使用情况
disk = psutil.disk_usage('/')
print(f"总量: {disk.total / (1024**3):.2f} GB")
print(f"已用: {disk.used / (1024**3):.2f} GB")
print(f"可用: {disk.free / (1024**3):.2f} GB")
print(f"使用率: {disk.percent}%")

# 磁盘 I/O 统计
io = psutil.disk_io_counters()
print(f"读取: {io.read_bytes / (1024**2):.2f} MB")
print(f"写入: {io.write_bytes / (1024**2):.2f} MB")
```

#### 网络信息详解

```python
import psutil

# 网络 I/O 统计
net = psutil.net_io_counters()
print(f"发送: {net.bytes_sent / (1024**2):.2f} MB")
print(f"接收: {net.bytes_recv / (1024**2):.2f} MB")

# 网络连接
connections = psutil.net_connections()
for conn in connections:
    if conn.status == 'ESTABLISHED':
        print(f"连接: {conn.laddr} -> {conn.raddr}")
```

### 2.2 进程监控

```python
import psutil

# 获取所有进程
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
    if proc.info['cpu_percent'] > 10:  # CPU 使用率 > 10%
        print(f"高 CPU 进程: {proc.info['name']} (PID: {proc.info['pid']})")
        print(f"  CPU: {proc.info['cpu_percent']}%")
        print(f"  内存: {proc.info['memory_percent']:.2f}%")
```

---

## 3. 告警规则引擎

### 3.1 规则设计模式

告警规则可以分为几类：

```
┌─────────────────────────────────────────────┐
│              告警规则类型                      │
├─────────────────────────────────────────────┤
│                                             │
│  1. 阈值规则 (Threshold)                     │
│     CPU > 90% 持续 5 分钟 → 告警             │
│                                             │
│  2. 趋势规则 (Trend)                         │
│     内存使用率 1 小时内增长 > 20% → 告警      │
│                                             │
│  3. 组合规则 (Composite)                     │
│     CPU > 80% AND 内存 > 85% → 严重告警     │
│                                             │
│  4. 时间规则 (Time-based)                    │
│     每天凌晨 2:00 检查磁盘空间               │
│                                             │
└─────────────────────────────────────────────┘
```

### 3.2 规则类设计

```python
from dataclasses import dataclass
from typing import Callable, Any
from enum import Enum

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class AlertRule:
    """告警规则定义"""
    name: str
    metric: str           # 监控指标名称
    condition: str        # 条件: "gt", "lt", "eq", "contains"
    threshold: float      # 阈值
    severity: Severity    # 告警级别
    duration: int = 0     # 持续时间（秒），0 表示立即触发
    description: str = "" # 规则描述

class RuleEngine:
    """告警规则引擎"""
    
    def __init__(self):
        self.rules: list[AlertRule] = []
        self.alert_history: list[dict] = []
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules.append(rule)
    
    def evaluate(self, rule: AlertRule, value: Any) -> bool:
        """评估规则是否触发"""
        if rule.condition == "gt":
            return value > rule.threshold
        elif rule.condition == "lt":
            return value < rule.threshold
        elif rule.condition == "eq":
            return value == rule.threshold
        elif rule.condition == "gte":
            return value >= rule.threshold
        elif rule.condition == "lte":
            return value <= rule.threshold
        return False
    
    def check_all_rules(self, metrics: dict) -> list[dict]:
        """检查所有规则"""
        alerts = []
        for rule in self.rules:
            value = metrics.get(rule.metric)
            if value is not None and self.evaluate(rule, value):
                alert = {
                    "rule": rule.name,
                    "metric": rule.metric,
                    "value": value,
                    "threshold": rule.threshold,
                    "severity": rule.severity.value,
                    "description": rule.description
                }
                alerts.append(alert)
                self.alert_history.append(alert)
        return alerts
```

### 3.3 通知渠道

```python
import json
import urllib.request
from abc import ABC, abstractmethod

class Notifier(ABC):
    """通知基类"""
    
    @abstractmethod
    def send(self, alert: dict) -> bool:
        """发送告警通知"""
        pass

class DingTalkNotifier(Notifier):
    """钉钉通知"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, alert: dict) -> bool:
        """发送钉钉消息"""
        severity_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨"
        }
        
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"{severity_emoji.get(alert['severity'], '📢')} 服务器告警",
                "text": f"""
### {alert['rule']}

- **指标**: {alert['metric']}
- **当前值**: {alert['value']}
- **阈值**: {alert['threshold']}
- **级别**: {alert['severity']}
- **描述**: {alert['description']}
                """
            }
        }
        
        try:
            data = json.dumps(message).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req)
            return True
        except Exception as e:
            print(f"钉钉通知失败: {e}")
            return False

class ConsoleNotifier(Notifier):
    """控制台输出（开发测试用）"""
    
    def send(self, alert: dict) -> bool:
        print(f"\n{'='*50}")
        print(f"🚨 告警: {alert['rule']}")
        print(f"   指标: {alert['metric']} = {alert['value']}")
        print(f"   阈值: {alert['threshold']}")
        print(f"   级别: {alert['severity']}")
        print(f"{'='*50}\n")
        return True
```

---

## 4. 完整监控系统实现

### 4.1 系统架构

```python
import psutil
import time
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import threading
from queue import Queue

class MetricsCollector:
    """系统指标采集器"""
    
    def __init__(self):
        self._prev_net_io = None
    
    def collect_cpu(self) -> dict:
        """采集 CPU 指标"""
        return {
            "usage_percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        }
    
    def collect_memory(self) -> dict:
        """采集内存指标"""
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent
        }
    
    def collect_disk(self, path: str = '/') -> dict:
        """采集磁盘指标"""
        disk = psutil.disk_usage(path)
        io = psutil.disk_io_counters()
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "read_bytes": io.read_bytes if io else 0,
            "write_bytes": io.write_bytes if io else 0
        }
    
    def collect_network(self) -> dict:
        """采集网络指标"""
        io = psutil.net_io_counters()
        
        # 计算速率（需要保存上次的值）
        sent_rate = 0
        recv_rate = 0
        if self._prev_net_io:
            sent_rate = (io.bytes_sent - self._prev_net_io.bytes_sent)
            recv_rate = (io.bytes_recv - self._prev_net_io.bytes_recv)
        
        self._prev_net_io = io
        
        return {
            "bytes_sent": io.bytes_sent,
            "bytes_recv": io.bytes_recv,
            "sent_rate": sent_rate,
            "recv_rate": recv_rate,
            "packets_sent": io.packets_sent,
            "packets_recv": io.packets_recv
        }
    
    def collect_all(self) -> dict:
        """采集所有指标"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": self.collect_cpu(),
            "memory": self.collect_memory(),
            "disk": self.collect_disk(),
            "network": self.collect_network()
        }


class MetricsStore:
    """指标存储（SQLite）"""
    
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def save(self, metrics: dict):
        """保存指标数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO metrics (timestamp, data) VALUES (?, ?)",
            (metrics["timestamp"], json.dumps(metrics))
        )
        conn.commit()
        conn.close()
    
    def query(self, start_time: str, end_time: str) -> list:
        """查询历史指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data FROM metrics WHERE timestamp BETWEEN ? AND ?",
            (start_time, end_time)
        )
        results = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        return results
```

### 4.2 主监控服务

```python
class MonitoringService:
    """监控服务主类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.collector = MetricsCollector()
        self.store = MetricsStore(config.get("db_path", "metrics.db"))
        self.rule_engine = RuleEngine()
        self.notifiers = []
        self.running = False
        
        # 初始化规则
        self._setup_rules()
        
        # 初始化通知器
        self._setup_notifiers()
    
    def _setup_rules(self):
        """设置告警规则"""
        rules = [
            AlertRule(
                name="CPU使用率过高",
                metric="cpu.usage_percent",
                condition="gt",
                threshold=90,
                severity=Severity.CRITICAL,
                description="CPU使用率超过90%，持续5分钟可能影响服务"
            ),
            AlertRule(
                name="内存使用率过高",
                metric="memory.percent",
                condition="gt",
                threshold=85,
                severity=Severity.WARNING,
                description="内存使用率超过85%，建议清理或扩容"
            ),
            AlertRule(
                name="磁盘空间不足",
                metric="disk.percent",
                condition="gt",
                threshold=90,
                severity=Severity.CRITICAL,
                description="磁盘使用率超过90%，需要清理空间"
            ),
            AlertRule(
                name="磁盘空间警告",
                metric="disk.percent",
                condition="gt",
                threshold=80,
                severity=Severity.WARNING,
                description="磁盘使用率超过80%，请关注"
            )
        ]
        
        for rule in rules:
            self.rule_engine.add_rule(rule)
    
    def _setup_notifiers(self):
        """设置通知渠道"""
        # 默认使用控制台输出
        self.notifiers.append(ConsoleNotifier())
        
        # 如果配置了钉钉 webhook，添加钉钉通知
        webhook_url = self.config.get("dingtalk_webhook")
        if webhook_url:
            self.notifiers.append(DingTalkNotifier(webhook_url))
    
    def _get_nested_value(self, data: dict, key: str):
        """获取嵌套字典的值，如 'cpu.usage_percent'"""
        keys = key.split('.')
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    
    def check_alerts(self, metrics: dict):
        """检查告警"""
        # 将嵌套的 metrics 转换为扁平格式用于规则匹配
        flat_metrics = {}
        for key in ["cpu.usage_percent", "memory.percent", "disk.percent"]:
            value = self._get_nested_value(metrics, key)
            if value is not None:
                flat_metrics[key] = value
        
        alerts = self.rule_engine.check_all_rules(flat_metrics)
        
        for alert in alerts:
            for notifier in self.notifiers:
                notifier.send(alert)
    
    def run_once(self):
        """执行一次采集和检查"""
        try:
            # 采集指标
            metrics = self.collector.collect_all()
            
            # 存储指标
            self.store.save(metrics)
            
            # 检查告警
            self.check_alerts(metrics)
            
            return metrics
        except Exception as e:
            print(f"采集失败: {e}")
            return None
    
    def run(self, interval: int = 60):
        """持续运行监控"""
        self.running = True
        print(f"🚀 监控服务启动，采集间隔: {interval}秒")
        
        while self.running:
            metrics = self.run_once()
            if metrics:
                print(f"✅ 采集完成: {metrics['timestamp']}")
            
            time.sleep(interval)
    
    def stop(self):
        """停止监控"""
        self.running = False
        print("🛑 监控服务停止")
```

---

## 5. 实战：服务器巡检报告

### 5.1 巡检报告生成器

```python
class InspectionReport:
    """服务器巡检报告"""
    
    def __init__(self, store: MetricsStore):
        self.store = store
    
    def generate(self, hours: int = 24) -> str:
        """生成巡检报告"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        metrics_list = self.store.query(
            start_time.isoformat(),
            end_time.isoformat()
        )
        
        if not metrics_list:
            return "⚠️ 无数据可生成报告"
        
        # 统计各项指标
        report = []
        report.append("=" * 60)
        report.append(f"📊 服务器巡检报告")
        report.append(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
        report.append(f"数据点数: {len(metrics_list)}")
        report.append("=" * 60)
        
        # CPU 统计
        cpu_values = [m['cpu']['usage_percent'] for m in metrics_list]
        report.append(f"\n🖥️  CPU 统计:")
        report.append(f"  平均使用率: {sum(cpu_values)/len(cpu_values):.1f}%")
        report.append(f"  最大使用率: {max(cpu_values):.1f}%")
        report.append(f"  最小使用率: {min(cpu_values):.1f}%")
        
        # 内存统计
        mem_values = [m['memory']['percent'] for m in metrics_list]
        report.append(f"\n💾 内存统计:")
        report.append(f"  平均使用率: {sum(mem_values)/len(mem_values):.1f}%")
        report.append(f"  最大使用率: {max(mem_values):.1f}%")
        
        # 磁盘统计
        disk_values = [m['disk']['percent'] for m in metrics_list]
        report.append(f"\n💿 磁盘统计:")
        report.append(f"  当前使用率: {disk_values[-1]:.1f}%")
        report.append(f"  最大使用率: {max(disk_values):.1f}%")
        
        # 告警统计
        alerts = []
        for metrics in metrics_list:
            for key in ["cpu.usage_percent", "memory.percent", "disk.percent"]:
                value = self._get_nested_value(metrics, key)
                if value and value > 90:
                    alerts.append({"time": metrics['timestamp'], "metric": key, "value": value})
        
        report.append(f"\n🚨 告警统计:")
        report.append(f"  总告警数: {len(alerts)}")
        if alerts:
            for alert in alerts[:5]:  # 只显示前5条
                report.append(f"  - {alert['time']}: {alert['metric']} = {alert['value']:.1f}%")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def _get_nested_value(self, data: dict, key: str):
        """获取嵌套字典的值"""
        keys = key.split('.')
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
```

### 5.2 使用示例

```python
def main():
    # 配置
    config = {
        "db_path": "server_metrics.db",
        "dingtalk_webhook": None  # 设置钉钉 webhook URL
    }
    
    # 创建监控服务
    service = MonitoringService(config)
    
    # 执行一次巡检
    print("🔍 执行服务器巡检...")
    metrics = service.run_once()
    
    if metrics:
        print("\n📊 当前系统状态:")
        print(f"  CPU: {metrics['cpu']['usage_percent']}%")
        print(f"  内存: {metrics['memory']['percent']}%")
        print(f"  磁盘: {metrics['disk']['percent']}%")
    
    # 生成巡检报告
    report_generator = InspectionReport(service.store)
    report = report_generator.generate(hours=1)
    print(report)
    
    # 持续监控（每60秒采集一次）
    # service.run(interval=60)

if __name__ == "__main__":
    main()
```

---

## 6. 进阶：告警去重与聚合

### 6.1 告警去重

```python
from collections import defaultdict
from datetime import datetime, timedelta

class AlertDeduplicator:
    """告警去重器"""
    
    def __init__(self, cooldown_seconds: int = 300):
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.last_alerts = {}  # rule_name -> last_alert_time
    
    def should_alert(self, rule_name: str) -> bool:
        """判断是否应该发送告警"""
        now = datetime.now()
        last_time = self.last_alerts.get(rule_name)
        
        if last_time is None or (now - last_time) > self.cooldown:
            self.last_alerts[rule_name] = now
            return True
        
        return False
```

### 6.2 告警聚合

```python
class AlertAggregator:
    """告警聚合器"""
    
    def __init__(self, window_seconds: int = 60):
        self.window = timedelta(seconds=window_seconds)
        self.pending_alerts = []
    
    def add_alert(self, alert: dict):
        """添加告警到聚合窗口"""
        self.pending_alerts.append({
            **alert,
            "timestamp": datetime.now()
        })
    
    def get_aggregated(self) -> list:
        """获取聚合后的告警"""
        now = datetime.now()
        
        # 清理过期告警
        self.pending_alerts = [
            a for a in self.pending_alerts
            if (now - a["timestamp"]) < self.window
        ]
        
        # 按规则分组
        groups = defaultdict(list)
        for alert in self.pending_alerts:
            groups[alert["rule"]].append(alert)
        
        # 聚合
        aggregated = []
        for rule_name, alerts in groups.items():
            aggregated.append({
                "rule": rule_name,
                "count": len(alerts),
                "first_occurrence": min(a["timestamp"] for a in alerts),
                "last_occurrence": max(a["timestamp"] for a in alerts),
                "severity": alerts[0]["severity"]
            })
        
        return aggregated
```

---

## 7. 思考题

1. **设计题**：如何设计一个支持多服务器的分布式监控系统？需要考虑哪些问题？

**参考答案**

分层架构（采集 → 传输 → 处理 → 存储 → 展示/告警）：

```text
被监控服务器 × N
  每台跑一个轻量 Agent（psutil 采集 CPU/内存/磁盘/网络）
        │ 周期上报(push) 或 中心拉取(pull)
        ▼
  采集网关 / 消息队列（Kafka、Redis：削峰、解耦）
        ▼
  中心处理（规则引擎、聚合、去重、升级）
        ▼
  时序存储（InfluxDB / TimescaleDB / Prometheus，分片 + 副本）
        ▼
  可视化（Grafana） + 告警通知（钉钉/邮件/短信，多渠道）
```

需要考虑的问题：

1. **采集方式**：push（agent 主动上报，实时性好、适合大规模）vs pull（中心定时抓取，如 Prometheus，便于控制目标）；agent 要低开销、容错（采集失败不崩溃、断网本地缓存补传）。
2. **可扩展性**：采集/处理/存储都能水平扩容；按指标/租户/时间分片；服务发现（新机器自动注册，如 Consul、K8s）。
3. **时间与顺序**：各机器时钟同步（NTP），用统一时间戳并容忍乱序到达；统一时区与单位。
4. **网络与容错**：上报失败重试 + 退避 + 本地缓冲；容忍网络分区，宁可漏采也不误报；写入幂等防重复。
5. **存储**：时序库 + 降采样 + 保留策略（见第 2 题）；多副本防单点。
6. **告警治理**：去重、聚合、静默、升级（见第 4 题），避免"告警风暴"；多渠道通知保证可达。
7. **安全**：agent 认证（token/mTLS）、最小权限、传输加密、不采集敏感数据。
8. **自监控**：监控系统本身也要被监控（见第 5 题），即"元监控"。

💡 提示：小规模用"中心 SSH 轮询 + SQLite"（本章方案）即可；上百上千台再演进到"agent + 消息队列 + 时序库"，工业级直接上 Prometheus + Grafana，别重复造轮子。

2. **优化题**：当监控指标数据量很大时，如何优化存储和查询性能？

**参考答案**

优化方向：

1. **用时序数据库**：InfluxDB/TimescaleDB/Prometheus 专为"写多、按时间范围查"优化（列式存储、压缩、时间索引），远胜 SQLite 逐行存 JSON。
2. **降采样/预聚合（rollup）**：秒级原始数据只留短期（如 7 天），预先聚合成分钟/小时/天级汇总长期保存；查大时间范围直接命中汇总表，扫描行数骤减。
3. **时间分区 + 索引**：按天/月分区，timestamp 建索引；查询只扫相关分区（分区裁剪）。
4. **批量写入**：多条指标合并成一个事务/`executemany`，别逐条 commit（磁盘 fsync 是瓶颈）。
5. **压缩与列存**：数值指标用列式 + 编码（delta/gorilla）压缩率高，省空间省 IO。
6. **保留策略（TTL）**：过期数据自动删除/归档，控制总量。
7. **查询侧**：避免 `SELECT *`、只取需要的列；大范围聚合用近似算法；缓存热点查询结果。

小例子（已验证，sqlite 预聚合：7 天分钟级原始数据 → 小时级 rollup，同一查询少扫 60 倍行）：

```python
import sqlite3, time, tempfile, os, random

random.seed(42)
with tempfile.TemporaryDirectory() as tmp:   # 临时库，用完自动清理
    db = os.path.join(tmp, "metrics.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("CREATE TABLE raw(ts INTEGER, mem REAL)")
    c.execute("CREATE TABLE rollup_hourly(hour INTEGER, avg_mem REAL, n INTEGER)")

    # 模拟 7 天分钟级数据 = 10080 个原始点
    rows = [(i * 60, 50 + random.uniform(-5, 20)) for i in range(7 * 24 * 60)]
    c.executemany("INSERT INTO raw VALUES(?,?)", rows)   # 批量写入
    # 预聚合：按小时汇总成 rollup（168 行）
    c.execute("INSERT INTO rollup_hourly SELECT ts/3600, AVG(mem), COUNT(*) FROM raw GROUP BY ts/3600")
    conn.commit()

    raw_n = c.execute("SELECT COUNT(*) FROM raw").fetchone()[0]
    roll_n = c.execute("SELECT COUNT(*) FROM rollup_hourly").fetchone()[0]

    # 查询"7 天平均内存"：原始表要扫全部行
    t0 = time.perf_counter()
    raw_val = c.execute("SELECT AVG(mem) FROM raw").fetchone()[0]
    raw_t = (time.perf_counter() - t0) * 1000
    # rollup 表按样本数加权平均，只扫 168 行
    t0 = time.perf_counter()
    roll_val = c.execute("SELECT SUM(avg_mem*n)/SUM(n) FROM rollup_hourly").fetchone()[0]
    roll_t = (time.perf_counter() - t0) * 1000

    print("原始表行数:", raw_n)
    print("rollup 表行数:", roll_n)
    print(f"原始表查询平均: {raw_val:.4f}（耗时 {raw_t:.2f}ms）")
    print(f"rollup 查询平均: {roll_val:.4f}（耗时 {roll_t:.2f}ms）")
    print("结果一致:", abs(raw_val - roll_val) < 1e-9)
    conn.close()
```

预期输出（耗时因机器/版本而异，下面为示例值；行数与结果一致是确定的）：

```
原始表行数: 10080
rollup 表行数: 168
原始表查询平均: 57.5077（耗时 0.26ms）
rollup 查询平均: 57.5077（耗时 0.03ms）
结果一致: True
```

原始表 10080 行，rollup 表仅 168 行（少 60 倍）；查"7 天平均"两者结果完全一致（加权平均保证正确），但 rollup 扫描行数少得多、更快。数据量越大、查询范围越广，收益越明显。

💡 提示：rollup 求总平均要按样本数加权（`SUM(avg*n)/SUM(n)`），不能直接 `AVG(avg)`——否则各小时样本数不同时会算偏。

3. **扩展题**：如何添加"趋势告警"功能（如内存使用率在1小时内增长超过20%）？

**参考答案**

实现思路：

1. **维护滑动窗口**：用 `deque` 保存窗口内（如 1 小时）的 `(时间戳, 值)` 样本，新样本进来时把滑出窗口的旧样本丢掉。
2. **计算增长率**：拿最新值和窗口内最旧值比较，`growth = (最新 - 最旧) / 最旧`。
3. **触发条件**：`growth > 阈值`（如 20%）就发趋势告警；可再要求"窗口内至少 N 个样本"，避免数据稀疏时误报。
4. **工程细节**：基线可选最旧值/窗口均值/昨日同时刻；分母 ≤ 0 要保护跳过；配合去重与冷却（同一趋势别反复告警）；也可与绝对阈值组合（"既高又涨得快"才告警）。

小例子（已验证，滑动窗口检测 1 小时增长 >20%）：

```python
from collections import deque

class TrendDetector:
    def __init__(self, window_seconds=3600, growth_threshold=0.20):
        self.window = window_seconds
        self.threshold = growth_threshold
        self.samples = deque()   # (timestamp, value)

    def check(self, ts, value):
        self.samples.append((ts, value))
        # 丢弃滑出窗口的旧样本
        while self.samples and ts - self.samples[0][0] > self.window:
            self.samples.popleft()
        if len(self.samples) < 2:
            return None
        oldest_ts, oldest_val = self.samples[0]
        if oldest_val <= 0:
            return None
        growth = (value - oldest_val) / oldest_val
        if growth > self.threshold:
            return f"趋势告警: {self.window//60} 分钟内增长 {growth*100:.1f}%（>{self.threshold*100:.0f}%）"
        return None

d = TrendDetector(window_seconds=3600, growth_threshold=0.20)
print(d.check(0, 50.0))       # 第一个点，无告警
print(d.check(1800, 60.0))    # +20%，等于阈值不算"超过"
print(d.check(3600, 75.0))    # +50%，触发告警
print(d.check(7200, 76.0))    # 窗口滑动，旧增长不再触发
```

预期输出：

```
None
None
趋势告警: 60 分钟内增长 50.0%（>20%）
None
```

内存 1 小时内从 50% 涨到 75%（+50% > 20%）触发告警；到 ts=7200 时窗口滑动，最旧样本变成 75%，增长仅约 1.3%，不再告警——体现"滑动窗口"只看最近 1 小时。

💡 提示：生产里样本通常存时序库、用范围查询取窗口数据，或直接用 Prometheus 的 `delta()`/`predict_linear()` 等函数；deque 版适合单机轻量场景。

4. **实战题**：如何实现告警通知的升级机制（如连续3次告警后自动升级到更高级别通知）？

**参考答案**

实现思路：

1. **统计连续告警次数**：为每条规则（或每个告警对象）维护一个"连续触发计数"，触发就 +1，恢复就清零。
2. **级别映射**：把次数映射到通知级别，如 1～3 次→邮件、4～6 次→短信、7 次以上→电话值班；可用 `(n-1)//3` 算级别索引，封顶最高级。
3. **升级对象**：不仅换渠道，还要换接收人（普通运维→运维主管→经理），确保有人兜底负责。
4. **重置与冷却**：告警恢复后计数清零；配合冷却/去重，避免抖动反复触发升级；也可加"未确认超时升级"（N 分钟没人 ack 就升级）。
5. **记录审计**：每次升级写日志，便于复盘。

小例子（已验证，连续 3 次后升一级，恢复后清零）：

```python
class AlertEscalation:
    def __init__(self, escalate_after=3):
        self.escalate_after = escalate_after
        self.counts = {}                          # rule -> 连续告警次数
        self.levels = ["邮件", "短信", "电话值班"]   # 通知级别逐级升级

    def on_alert(self, rule):
        self.counts[rule] = self.counts.get(rule, 0) + 1
        n = self.counts[rule]
        # 每连续 escalate_after 次升一级（封顶最高级）
        idx = min((n - 1) // self.escalate_after, len(self.levels) - 1)
        print(f"第 {n} 次告警 [{rule}] → 用「{self.levels[idx]}」通知")
        return self.levels[idx]

    def on_resolve(self, rule):
        if rule in self.counts:
            print(f"[{rule}] 已恢复，计数清零")
            self.counts[rule] = 0

esc = AlertEscalation(escalate_after=3)
for i in range(7):
    esc.on_alert("内存过高")
esc.on_resolve("内存过高")
esc.on_alert("内存过高")   # 恢复后重新从邮件开始
```

预期输出：

```
第 1 次告警 [内存过高] → 用「邮件」通知
第 2 次告警 [内存过高] → 用「邮件」通知
第 3 次告警 [内存过高] → 用「邮件」通知
第 4 次告警 [内存过高] → 用「短信」通知
第 5 次告警 [内存过高] → 用「短信」通知
第 6 次告警 [内存过高] → 用「短信」通知
第 7 次告警 [内存过高] → 用「电话值班」通知
[内存过高] 已恢复，计数清零
第 1 次告警 [内存过高] → 用「邮件」通知
```

前 3 次用邮件，第 4 次起升短信，第 7 次起升电话；恢复后计数清零，下次告警又从邮件开始。

💡 提示：更稳妥的是"未确认（ack）超时升级"而非纯计数——告警虽频繁但已有人处理时就不必打扰更高级别；计数升级更适合无人值守场景。

5. **架构题**：如何设计监控系统的高可用性，确保监控服务本身不会成为单点故障？

**参考答案**

监控系统自己不能挂，关键设计：

1. **多实例 + 无状态**：采集/处理/告警服务跑多副本，状态外置到 DB/队列，前面挂负载均衡，任一实例宕机不影响整体。
2. **主选举 + 故障转移**：对必须单例的有状态组件（如某些聚合任务），用 leader 选举（etcd/ZooKeeper/Redis 锁），主挂了备自动顶上。
3. **存储多副本**：时序库与配置存储做副本/主从（如 Prometheus + Thanos、InfluxDB 集群），防单点丢数据或不可用。
4. **通知多渠道 + 降级**：告警同时走多渠道（钉钉 + 邮件 + 短信），某渠道失败自动切备用；通知服务本身也多实例。
5. **死人开关（dead man's switch / 心跳看门狗）**：监控系统定期向一个**独立的外部看门狗**发"我还活着"心跳；看门狗收不到心跳就反过来告警"监控系统挂了"——这是防"监控静默失效"的关键。
6. **元监控**：用另一套独立、简单的监控（或云厂商监控）来监控本监控系统，形成互相监督；跨机器/跨可用区部署，避免同机架故障。
7. **自保护**：限流、熔断、背压，防止监控系统自己被指标洪流压垮；采集失败要降级而非崩溃。

```text
监控集群（多实例、跨可用区）
   ├── 采集/处理 × N（无状态 + 负载均衡）
   ├── 存储（多副本）
   └── 定期心跳 ──► 独立外部看门狗
                  （收不到心跳 → 告警"监控挂了"）
```

💡 提示：最容易被忽略的是"死人开关"——监控进程若卡死，它自己就发不出告警了，必须靠独立外部组件发现"它没声音了"，否则故障会被静默漏掉。

---

## 📚 参考资源

- [psutil 官方文档](https://psutil.readthedocs.io/)
- [Python 监控最佳实践](https://realpython.com/python-monitoring/)
- [Prometheus + Grafana](https://prometheus.io/) - 工业级监控方案

---

> 🎯 **今日产出**：一个完整的服务器监控告警系统，支持指标采集、规则引擎、告警通知和巡检报告
