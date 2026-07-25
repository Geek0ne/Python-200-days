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
2. **优化题**：当监控指标数据量很大时，如何优化存储和查询性能？
3. **扩展题**：如何添加"趋势告警"功能（如内存使用率在1小时内增长超过20%）？
4. **实战题**：如何实现告警通知的升级机制（如连续3次告警后自动升级到更高级别通知）？
5. **架构题**：如何设计监控系统的高可用性，确保监控服务本身不会成为单点故障？

---

## 📚 参考资源

- [psutil 官方文档](https://psutil.readthedocs.io/)
- [Python 监控最佳实践](https://realpython.com/python-monitoring/)
- [Prometheus + Grafana](https://prometheus.io/) - 工业级监控方案

---

> 🎯 **今日产出**：一个完整的服务器监控告警系统，支持指标采集、规则引擎、告警通知和巡检报告
