#!/usr/bin/env python3
"""
03-monitoring-service.py
完整监控服务示例
演示如何构建一个生产级的监控告警系统
"""

import psutil
import time
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod


# ==================== 数据模型 ====================

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    name: str
    metric: str
    condition: str
    threshold: float
    severity: Severity
    description: str = ""


@dataclass
class Alert:
    rule_name: str
    metric: str
    value: float
    threshold: float
    severity: Severity
    timestamp: datetime
    description: str = ""


# ==================== 指标采集器 ====================

class MetricsCollector:
    """系统指标采集器"""
    
    def __init__(self):
        self._prev_net_io = None
        self._prev_time = None
    
    def collect_cpu(self) -> dict:
        """采集 CPU 指标"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        return {
            "usage_percent": cpu_percent,
            "count": cpu_count,
            "freq_current": cpu_freq.current if cpu_freq else 0
        }
    
    def collect_memory(self) -> dict:
        """采集内存指标"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent
        }
    
    def collect_disk(self, path: str = '/') -> dict:
        """采集磁盘指标"""
        try:
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
        except Exception:
            return {"percent": 0, "total": 0, "used": 0, "free": 0}
    
    def collect_network(self) -> dict:
        """采集网络指标"""
        io = psutil.net_io_counters()
        
        # 计算速率
        now = time.time()
        sent_rate = 0
        recv_rate = 0
        
        if self._prev_net_io and self._prev_time:
            elapsed = now - self._prev_time
            if elapsed > 0:
                sent_rate = (io.bytes_sent - self._prev_net_io.bytes_sent) / elapsed
                recv_rate = (io.bytes_recv - self._prev_net_io.bytes_recv) / elapsed
        
        self._prev_net_io = io
        self._prev_time = now
        
        return {
            "bytes_sent": io.bytes_sent,
            "bytes_recv": io.bytes_recv,
            "sent_rate": sent_rate,
            "recv_rate": recv_rate
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


# ==================== 指标存储 ====================

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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                threshold REAL,
                severity TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_metrics(self, metrics: dict):
        """保存指标数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO metrics (timestamp, data) VALUES (?, ?)",
            (metrics["timestamp"], json.dumps(metrics))
        )
        conn.commit()
        conn.close()
    
    def save_alert(self, alert: Alert):
        """保存告警"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO alerts (rule_name, metric, value, threshold, severity, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (alert.rule_name, alert.metric, alert.value, alert.threshold,
             alert.severity.value, alert.description)
        )
        conn.commit()
        conn.close()
    
    def query_metrics(self, hours: int = 24) -> list:
        """查询历史指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        cursor.execute(
            "SELECT data FROM metrics WHERE timestamp > ? ORDER BY timestamp",
            (cutoff,)
        )
        
        results = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def query_alerts(self, hours: int = 24) -> list:
        """查询历史告警"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        cursor.execute(
            "SELECT * FROM alerts WHERE created_at > ? ORDER BY created_at DESC",
            (cutoff,)
        )
        
        results = cursor.fetchall()
        conn.close()
        return results


# ==================== 告警引擎 ====================

class AlertEngine:
    """告警引擎"""
    
    def __init__(self, store: MetricsStore):
        self.store = store
        self.rules: list[AlertRule] = []
        self.dedup_window = timedelta(minutes=5)
        self._last_alerts: dict[str, datetime] = {}
    
    def add_rule(self, rule: AlertRule):
        """添加规则"""
        self.rules.append(rule)
    
    def evaluate(self, value: float, condition: str, threshold: float) -> bool:
        """评估条件"""
        ops = {
            "gt": value > threshold,
            "gte": value >= threshold,
            "lt": value < threshold,
            "lte": value <= threshold,
            "eq": value == threshold,
            "ne": value != threshold
        }
        return ops.get(condition, False)
    
    def get_nested_value(self, data: dict, key: str):
        """获取嵌套值"""
        for k in key.split('.'):
            if isinstance(data, dict):
                data = data.get(k)
            else:
                return None
        return data
    
    def is_duplicate(self, rule_name: str) -> bool:
        """检查去重"""
        last_time = self._last_alerts.get(rule_name)
        if last_time and (datetime.now() - last_time) < self.dedup_window:
            return True
        return False
    
    def check(self, metrics: dict) -> list[Alert]:
        """检查所有规则"""
        alerts = []
        
        for rule in self.rules:
            value = self.get_nested_value(metrics, rule.metric)
            if value is None:
                continue
            
            if self.evaluate(value, rule.condition, rule.threshold):
                if not self.is_duplicate(rule.name):
                    alert = Alert(
                        rule_name=rule.name,
                        metric=rule.metric,
                        value=value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        timestamp=datetime.now(),
                        description=rule.description
                    )
                    alerts.append(alert)
                    self._last_alerts[rule.name] = datetime.now()
                    self.store.save_alert(alert)
        
        return alerts


# ==================== 通知器 ====================

class Notifier(ABC):
    """通知基类"""
    
    @abstractmethod
    def send(self, alert: Alert) -> bool:
        pass


class ConsoleNotifier(Notifier):
    """控制台通知"""
    
    def send(self, alert: Alert) -> bool:
        severity_emoji = {
            Severity.INFO: "ℹ️",
            Severity.WARNING: "⚠️",
            Severity.CRITICAL: "🚨"
        }
        
        emoji = severity_emoji.get(alert.severity, "📢")
        print(f"\n{emoji} 告警触发!")
        print(f"  规则: {alert.rule_name}")
        print(f"  指标: {alert.metric} = {alert.value}")
        print(f"  阈值: {alert.threshold}")
        print(f"  级别: {alert.severity.value}")
        print(f"  时间: {alert.timestamp}")
        if alert.description:
            print(f"  描述: {alert.description}")
        
        return True


class WebhookNotifier(Notifier):
    """Webhook 通知"""
    
    def __init__(self, url: str):
        self.url = url
    
    def send(self, alert: Alert) -> bool:
        # 实际实现中使用 requests 发送
        print(f"📤 Webhook 通知: {alert.rule_name} -> {self.url}")
        return True


# ==================== 巡检报告 ====================

class InspectionReport:
    """巡检报告生成器"""
    
    def __init__(self, store: MetricsStore):
        self.store = store
    
    def generate(self, hours: int = 1) -> str:
        """生成报告"""
        metrics = self.store.query_metrics(hours)
        alerts = self.store.query_alerts(hours)
        
        report = []
        report.append("=" * 60)
        report.append("📊 服务器巡检报告")
        report.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"统计周期: 最近 {hours} 小时")
        report.append("=" * 60)
        
        if not metrics:
            report.append("\n⚠️ 无数据")
            return "\n".join(report)
        
        # CPU 统计
        cpu_values = [m['cpu']['usage_percent'] for m in metrics]
        report.append(f"\n🖥️  CPU:")
        report.append(f"  平均: {sum(cpu_values)/len(cpu_values):.1f}%")
        report.append(f"  最高: {max(cpu_values):.1f}%")
        report.append(f"  最低: {min(cpu_values):.1f}%")
        
        # 内存统计
        mem_values = [m['memory']['percent'] for m in metrics]
        report.append(f"\n💾 内存:")
        report.append(f"  平均: {sum(mem_values)/len(mem_values):.1f}%")
        report.append(f"  最高: {max(mem_values):.1f}%")
        
        # 磁盘统计
        disk_values = [m['disk']['percent'] for m in metrics]
        report.append(f"\n💿 磁盘:")
        report.append(f"  当前: {disk_values[-1]:.1f}%")
        report.append(f"  最高: {max(disk_values):.1f}%")
        
        # 告警统计
        report.append(f"\n🚨 告警统计:")
        report.append(f"  总数: {len(alerts)}")
        
        if alerts:
            severity_count = {}
            for a in alerts:
                s = a[5]  # severity 字段
                severity_count[s] = severity_count.get(s, 0) + 1
            
            for s, count in severity_count.items():
                report.append(f"  - {s}: {count}")
        
        report.append("\n" + "=" * 60)
        return "\n".join(report)


# ==================== 监控服务 ====================

class MonitoringService:
    """监控服务主类"""
    
    def __init__(self, db_path: str = "server_metrics.db"):
        self.collector = MetricsCollector()
        self.store = MetricsStore(db_path)
        self.engine = AlertEngine(self.store)
        self.notifiers: list[Notifier] = []
        self.report = InspectionReport(self.store)
        
        # 初始化默认规则
        self._setup_rules()
        
        # 添加控制台通知
        self.notifiers.append(ConsoleNotifier())
    
    def _setup_rules(self):
        """设置默认规则"""
        rules = [
            AlertRule(
                name="CPU使用率过高",
                metric="cpu.usage_percent",
                condition="gt",
                threshold=90,
                severity=Severity.CRITICAL,
                description="CPU使用率超过90%"
            ),
            AlertRule(
                name="内存使用率过高",
                metric="memory.percent",
                condition="gt",
                threshold=85,
                severity=Severity.WARNING,
                description="内存使用率超过85%"
            ),
            AlertRule(
                name="磁盘空间不足",
                metric="disk.percent",
                condition="gt",
                threshold=90,
                severity=Severity.CRITICAL,
                description="磁盘使用率超过90%"
            ),
            AlertRule(
                name="磁盘空间警告",
                metric="disk.percent",
                condition="gt",
                threshold=80,
                severity=Severity.WARNING,
                description="磁盘使用率超过80%"
            ),
            AlertRule(
                name="网络接收速率过高",
                metric="network.recv_rate",
                condition="gt",
                threshold=10*1024*1024,  # 10MB/s
                severity=Severity.WARNING,
                description="网络接收速率超过10MB/s"
            )
        ]
        
        for rule in rules:
            self.engine.add_rule(rule)
    
    def add_notifier(self, notifier: Notifier):
        """添加通知器"""
        self.notifiers.append(notifier)
    
    def collect_once(self) -> dict:
        """执行一次采集"""
        metrics = self.collector.collect_all()
        self.store.save_metrics(metrics)
        
        # 检查告警
        alerts = self.engine.check(metrics)
        
        # 发送通知
        for alert in alerts:
            for notifier in self.notifiers:
                notifier.send(alert)
        
        return metrics
    
    def run(self, interval: int = 60, max_iterations: int = 0):
        """持续运行监控
        
        Args:
            interval: 采集间隔（秒）
            max_iterations: 最大迭代次数，0表示无限
        """
        print(f"🚀 监控服务启动")
        print(f"   采集间隔: {interval}秒")
        print(f"   规则数量: {len(self.engine.rules)}")
        print(f"   按 Ctrl+C 停止")
        print()
        
        iteration = 0
        try:
            while max_iterations == 0 or iteration < max_iterations:
                iteration += 1
                
                # 采集
                metrics = self.collect_once()
                
                # 打印状态
                cpu = metrics['cpu']['usage_percent']
                mem = metrics['memory']['percent']
                disk = metrics['disk']['percent']
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"CPU: {cpu:5.1f}% | 内存: {mem:5.1f}% | 磁盘: {disk:5.1f}%")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 监控服务已停止")
    
    def get_report(self, hours: int = 1) -> str:
        """获取巡检报告"""
        return self.report.generate(hours)


# ==================== 主函数 ====================

def main():
    """主函数"""
    print("🔧 Python 服务器监控服务")
    print()
    
    # 创建监控服务
    service = MonitoringService("demo_metrics.db")
    
    # 执行一次采集
    print("📊 执行单次采集...")
    metrics = service.collect_once()
    
    print(f"\n当前状态:")
    print(f"  CPU: {metrics['cpu']['usage_percent']}%")
    print(f"  内存: {metrics['memory']['percent']}%")
    print(f"  磁盘: {metrics['disk']['percent']}%")
    print(f"  网络发送速率: {metrics['network']['sent_rate']/1024:.2f} KB/s")
    print(f"  网络接收速率: {metrics['network']['recv_rate']/1024:.2f} KB/s")
    
    # 生成报告
    print("\n📋 生成巡检报告...")
    report = service.get_report(hours=1)
    print(report)
    
    # 提示用户
    print("\n" + "=" * 60)
    print("💡 提示:")
    print("  - 取消注释 service.run() 可启动持续监控")
    print("  - 可通过 service.add_notifier() 添加更多通知渠道")
    print("  - 可通过 service.engine.add_rule() 添加更多规则")
    print("=" * 60)
    
    # 启动持续监控（取消注释以运行）
    # service.run(interval=10, max_iterations=5)


if __name__ == "__main__":
    main()
