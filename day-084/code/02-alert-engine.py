#!/usr/bin/env python3
"""
02-alert-engine.py
告警规则引擎示例
演示如何设计和实现灵活的告警规则系统
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import json


class Severity(Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """告警规则定义"""
    name: str
    metric: str
    condition: str
    threshold: float
    severity: Severity
    duration: int = 0
    description: str = ""
    enabled: bool = True


@dataclass
class Alert:
    """告警实例"""
    rule_name: str
    metric: str
    value: Any
    threshold: float
    severity: Severity
    timestamp: datetime
    description: str = ""
    count: int = 1


class RuleEngine:
    """告警规则引擎"""
    
    def __init__(self):
        self.rules: list[AlertRule] = []
        self.alert_history: list[Alert] = []
        self.deduplication_window = timedelta(minutes=5)
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules.append(rule)
        print(f"✅ 添加规则: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """移除告警规则"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        print(f"❌ 移除规则: {rule_name}")
    
    def evaluate_condition(self, value: Any, condition: str, threshold: float) -> bool:
        """评估条件"""
        operators = {
            "gt": lambda v, t: v > t,
            "gte": lambda v, t: v >= t,
            "lt": lambda v, t: v < t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
            "ne": lambda v, t: v != t,
        }
        
        op_func = operators.get(condition)
        if op_func is None:
            raise ValueError(f"未知条件: {condition}")
        
        return op_func(value, threshold)
    
    def is_duplicate(self, rule_name: str) -> bool:
        """检查是否重复告警"""
        now = datetime.now()
        for alert in reversed(self.alert_history):
            if alert.rule_name == rule_name:
                if (now - alert.timestamp) < self.deduplication_window:
                    return True
                break
        return False
    
    def check_rules(self, metrics: dict) -> list[Alert]:
        """检查所有规则"""
        alerts = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # 获取指标值（支持嵌套键）
            value = self._get_nested_value(metrics, rule.metric)
            if value is None:
                continue
            
            # 评估规则
            if self.evaluate_condition(value, rule.condition, rule.threshold):
                # 检查去重
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
                    self.alert_history.append(alert)
                    print(f"🚨 触发告警: {rule.name}")
                else:
                    print(f"⏭️  跳过重复告警: {rule.name}")
        
        return alerts
    
    def _get_nested_value(self, data: dict, key: str) -> Any:
        """获取嵌套字典的值"""
        keys = key.split('.')
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    
    def get_alert_history(self, hours: int = 24) -> list[Alert]:
        """获取历史告警"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alert_history if a.timestamp > cutoff]


class CompositeRule:
    """组合规则（AND/OR 逻辑）"""
    
    def __init__(self, name: str, operator: str, sub_rules: list[AlertRule]):
        self.name = name
        self.operator = operator.upper()  # AND or OR
        self.sub_rules = sub_rules
    
    def evaluate(self, metrics: dict, engine: RuleEngine) -> bool:
        """评估组合规则"""
        results = []
        for rule in self.sub_rules:
            value = engine._get_nested_value(metrics, rule.metric)
            if value is not None:
                result = engine.evaluate_condition(value, rule.condition, rule.threshold)
                results.append(result)
        
        if not results:
            return False
        
        if self.operator == "AND":
            return all(results)
        elif self.operator == "OR":
            return any(results)
        
        return False


class TrendRule:
    """趋势规则（检测变化率）"""
    
    def __init__(self, name: str, metric: str, 
                 increase_threshold: float, window_minutes: int = 60):
        self.name = name
        self.metric = metric
        self.increase_threshold = increase_threshold
        self.window = timedelta(minutes=window_minutes)
        self.history: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    
    def record(self, metrics: dict, engine: RuleEngine):
        """记录当前值"""
        value = engine._get_nested_value(metrics, self.metric)
        if value is not None:
            self.history[self.metric].append((datetime.now(), value))
    
    def check(self) -> Optional[float]:
        """检查趋势"""
        history = self.history.get(self.metric, [])
        if len(history) < 2:
            return None
        
        cutoff = datetime.now() - self.window
        recent = [(t, v) for t, v in history if t > cutoff]
        
        if len(recent) < 2:
            return None
        
        # 计算变化率
        first_value = recent[0][1]
        last_value = recent[-1][1]
        
        if first_value == 0:
            return None
        
        change_rate = ((last_value - first_value) / first_value) * 100
        
        if change_rate > self.increase_threshold:
            return change_rate
        
        return None


def demo_basic_rules():
    """演示基础规则引擎"""
    print("=" * 60)
    print("📋 演示 1: 基础规则引擎")
    print("=" * 60)
    
    # 创建规则引擎
    engine = RuleEngine()
    
    # 添加规则
    engine.add_rule(AlertRule(
        name="CPU使用率过高",
        metric="cpu.usage_percent",
        condition="gt",
        threshold=90,
        severity=Severity.CRITICAL,
        description="CPU使用率超过90%"
    ))
    
    engine.add_rule(AlertRule(
        name="内存使用率警告",
        metric="memory.percent",
        condition="gt",
        threshold=80,
        severity=Severity.WARNING,
        description="内存使用率超过80%"
    ))
    
    engine.add_rule(AlertRule(
        name="磁盘空间不足",
        metric="disk.percent",
        condition="gt",
        threshold=90,
        severity=Severity.CRITICAL,
        description="磁盘使用率超过90%"
    ))
    
    # 测试指标（正常）
    print("\n📊 测试 1: 正常指标")
    metrics_normal = {
        "cpu": {"usage_percent": 45},
        "memory": {"percent": 60},
        "disk": {"percent": 70}
    }
    alerts = engine.check_rules(metrics_normal)
    print(f"告警数量: {len(alerts)}")
    
    # 测试指标（异常）
    print("\n📊 测试 2: 异常指标")
    metrics_abnormal = {
        "cpu": {"usage_percent": 95},
        "memory": {"percent": 85},
        "disk": {"percent": 92}
    }
    alerts = engine.check_rules(metrics_abnormal)
    print(f"告警数量: {len(alerts)}")
    for alert in alerts:
        print(f"  - {alert.rule_name}: {alert.value}% (阈值: {alert.threshold}%)")
    
    # 去重测试
    print("\n📊 测试 3: 去重测试")
    alerts = engine.check_rules(metrics_abnormal)
    print(f"告警数量: {len(alerts)} (应为0，因为5分钟内重复)")


def demo_composite_rules():
    """演示组合规则"""
    print("\n" + "=" * 60)
    print("📋 演示 2: 组合规则")
    print("=" * 60)
    
    engine = RuleEngine()
    
    # 创建组合规则：CPU > 80% AND 内存 > 85%
    high_cpu = AlertRule(
        name="CPU高",
        metric="cpu.usage_percent",
        condition="gt",
        threshold=80,
        severity=Severity.WARNING
    )
    
    high_memory = AlertRule(
        name="内存高",
        metric="memory.percent",
        condition="gt",
        threshold=85,
        severity=Severity.WARNING
    )
    
    # 测试指标
    metrics = {
        "cpu": {"usage_percent": 85},
        "memory": {"percent": 90}
    }
    
    # 单独评估
    cpu_alert = engine.evaluate_condition(
        metrics["cpu"]["usage_percent"], 
        high_cpu.condition, 
        high_cpu.threshold
    )
    mem_alert = engine.evaluate_condition(
        metrics["memory"]["percent"],
        high_memory.condition,
        high_memory.threshold
    )
    
    print(f"CPU 触发: {cpu_alert}")
    print(f"内存触发: {mem_alert}")
    print(f"AND 逻辑: {cpu_alert and mem_alert}")
    print(f"OR 逻辑: {cpu_alert or mem_alert}")


def demo_trend_rules():
    """演示趋势规则"""
    print("\n" + "=" * 60)
    print("📋 演示 3: 趋势规则")
    print("=" * 60)
    
    engine = RuleEngine()
    trend = TrendRule(
        name="内存使用率快速增长",
        metric="memory.percent",
        increase_threshold=20,
        window_minutes=60
    )
    
    # 模拟内存使用率增长
    print("\n📊 模拟内存使用率增长:")
    base_value = 50
    for i in range(5):
        metrics = {
            "memory": {"percent": base_value + i * 5}
        }
        trend.record(metrics, engine)
        print(f"  记录: {base_value + i * 5}%")
    
    # 检查趋势
    change_rate = trend.check()
    if change_rate:
        print(f"\n⚠️  检测到内存使用率增长: {change_rate:.1f}%")
    else:
        print(f"\n✅ 内存使用率变化在正常范围内")


def main():
    """主函数"""
    print("🔧 Python 告警规则引擎演示")
    print()
    
    # 演示各种规则类型
    demo_basic_rules()
    demo_composite_rules()
    demo_trend_rules()
    
    print("\n" + "=" * 60)
    print("✅ 演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
