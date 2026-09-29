"""
高级监控系统 - 结构化日志 + 指标收集 + 告警
功能：完整的爬虫监控解决方案，包括日志记录、指标收集和异常告警
"""

import json
import time
import logging
import smtplib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import deque
from email.mime.text import MIMEText
from enum import Enum


# ==================== 日志系统 ====================

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件路径（可选）
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # 文件处理器（可选）
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    def log_scrape_event(self, url: str, status: str, duration: float, items: int = 0):
        """记录爬取事件"""
        event = {
            "event_type": "scrape",
            "url": url,
            "status": status,
            "duration_seconds": round(duration, 2),
            "items_count": items,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.info(json.dumps(event, ensure_ascii=False))
        return event
    
    def log_price_change(self, product_id: str, name: str, old_price: float, new_price: float):
        """记录价格变动"""
        change_pct = (new_price - old_price) / old_price * 100
        event = {
            "event_type": "price_change",
            "product_id": product_id,
            "product_name": name,
            "old_price": old_price,
            "new_price": new_price,
            "change_percent": round(change_pct, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        if change_pct < 0:
            self.logger.info(f"💰 降价提醒: {name} {old_price} -> {new_price} ({change_pct:+.1f}%)")
        else:
            self.logger.debug(json.dumps(event, ensure_ascii=False))
        
        return event
    
    def log_error(self, error_type: str, message: str, context: Optional[Dict] = None):
        """记录错误事件"""
        event = {
            "event_type": "error",
            "error_type": error_type,
            "message": message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        self.logger.error(json.dumps(event, ensure_ascii=False))
        return event
    
    def log_alert(self, alert_level: str, message: str):
        """记录告警事件"""
        event = {
            "event_type": "alert",
            "alert_level": alert_level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if alert_level == "critical":
            self.logger.critical(f"🚨 {message}")
        elif alert_level == "warning":
            self.logger.warning(f"⚠️ {message}")
        else:
            self.logger.info(f"ℹ️ {message}")
        
        return event


# ==================== 指标收集器 ====================

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警信息"""
    level: AlertLevel
    message: str
    timestamp: datetime
    resolved: bool = False


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, window_size: int = 60):
        """
        初始化指标收集器
        
        Args:
            window_size: 统计窗口大小（秒）
        """
        self.window_size = window_size
        self.start_time = time.time()
        
        # 计数器
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.items_scraped = 0
        self.items_dropped = 0
        
        # 时间序列数据
        self.request_times: deque = deque()  # (timestamp, success, duration)
        self.response_times: deque = deque()  # (timestamp, duration)
        
        # 错误统计
        self.errors: deque = deque(maxlen=1000)
        self.error_counts: Dict[str, int] = {}
        
        # 告警
        self.alerts: List[Alert] = []
        self.alert_thresholds = {
            "error_rate": 0.1,        # 错误率超过 10%
            "response_time": 5.0,     # 响应时间超过 5 秒
            "items_per_minute": 10,   # 每分钟爬取量低于 10
        }
    
    def record_request(self, success: bool, duration: float, error_type: Optional[str] = None):
        """记录请求"""
        now = time.time()
        
        self.total_requests += 1
        self.request_times.append((now, success, duration))
        
        if success:
            self.successful_requests += 1
            self.response_times.append((now, duration))
        else:
            self.failed_requests += 1
            if error_type:
                self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
                self.errors.append({
                    "type": error_type,
                    "timestamp": datetime.now().isoformat()
                })
        
        # 检查告警条件
        self._check_alerts()
    
    def record_item(self, dropped: bool = False):
        """记录数据项"""
        if dropped:
            self.items_dropped += 1
        else:
            self.items_scraped += 1
    
    def _cleanup_old_data(self):
        """清理过期数据"""
        cutoff = time.time() - self.window_size
        
        # 清理请求记录
        while self.request_times and self.request_times[0][0] < cutoff:
            self.request_times.popleft()
        
        # 清理响应时间记录
        while self.response_times and self.response_times[0][0] < cutoff:
            self.response_times.popleft()
    
    def _check_alerts(self):
        """检查告警条件"""
        self._cleanup_old_data()
        now = time.time()
        cutoff = now - self.window_size
        
        # 计算窗口内的错误率
        window_requests = [r for r in self.request_times if r[0] >= cutoff]
        if window_requests:
            window_errors = sum(1 for r in window_requests if not r[1])
            error_rate = window_errors / len(window_requests)
            
            if error_rate > self.alert_thresholds["error_rate"]:
                self._add_alert(
                    AlertLevel.WARNING,
                    f"错误率过高: {error_rate:.1%} (阈值: {self.alert_thresholds['error_rate']:.1%})"
                )
        
        # 检查响应时间
        if self.response_times:
            recent_times = [r[1] for r in self.response_times if r[0] >= cutoff]
            if recent_times:
                avg_time = sum(recent_times) / len(recent_times)
                if avg_time > self.alert_thresholds["response_time"]:
                    self._add_alert(
                        AlertLevel.WARNING,
                        f"响应时间过长: {avg_time:.2f}s (阈值: {self.alert_thresholds['response_time']}s)"
                    )
    
    def _add_alert(self, level: AlertLevel, message: str):
        """添加告警"""
        # 避免重复告警
        for alert in self.alerts[-10:]:
            if alert.message == message and not alert.resolved:
                return
        
        alert = Alert(
            level=level,
            message=message,
            timestamp=datetime.now()
        )
        self.alerts.append(alert)
    
    def get_summary(self) -> Dict:
        """获取指标摘要"""
        self._cleanup_old_data()
        
        duration = time.time() - self.start_time
        
        # 窗口内统计
        cutoff = time.time() - self.window_size
        window_requests = [r for r in self.request_times if r[0] >= cutoff]
        window_success = sum(1 for r in window_requests if r[1])
        window_duration = sum(r[2] for r in window_requests if r[1])
        
        # 响应时间统计
        response_times_list = [r[1] for r in self.response_times]
        avg_response = sum(response_times_list) / len(response_times_list) if response_times_list else 0
        
        return {
            "duration_seconds": round(duration, 1),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": f"{self.successful_requests / self.total_requests * 100:.1f}%" if self.total_requests else "0%",
            "avg_response_time": f"{avg_response:.2f}s",
            "requests_per_second": round(self.total_requests / duration, 2) if duration > 0 else 0,
            "items_scraped": self.items_scraped,
            "items_dropped": self.items_dropped,
            "window_error_rate": f"{(len(window_requests) - window_success) / len(window_requests) * 100:.1f}%" if window_requests else "0%",
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "error_types": dict(self.error_counts)
        }
    
    def print_report(self):
        """打印监控报告"""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("📊 爬虫监控报告")
        print("=" * 60)
        print(f"⏱️  运行时长: {summary['duration_seconds']}s")
        print(f"📡 总请求数: {summary['total_requests']}")
        print(f"✅ 成功请求: {summary['successful_requests']}")
        print(f"❌ 失败请求: {summary['failed_requests']}")
        print(f"📈 成功率: {summary['success_rate']}")
        print(f"⚡ 平均响应: {summary['avg_response_time']}")
        print(f"🚀 请求速率: {summary['requests_per_second']}/s")
        print(f"📦 爬取数据: {summary['items_scraped']} 条")
        print(f"🗑️  丢弃数据: {summary['items_dropped']} 条")
        print(f"⚠️  活跃告警: {summary['active_alerts']} 个")
        
        if summary['error_types']:
            print(f"\n🔴 错误类型分布:")
            for error_type, count in summary['error_types'].items():
                print(f"   - {error_type}: {count}")
        
        print("=" * 60)


# ==================== 告警通知 ====================

class AlertNotifier:
    """告警通知器"""
    
    def __init__(self, email_config: Optional[Dict] = None):
        """
        初始化通知器
        
        Args:
            email_config: 邮件配置 {"smtp_host", "smtp_port", "username", "password", "to_addr"}
        """
        self.email_config = email_config
        self.logger = StructuredLogger("AlertNotifier")
    
    def send_email(self, subject: str, body: str):
        """发送邮件告警"""
        if not self.email_config:
            self.logger.log_alert("info", f"[邮件未配置] {subject}: {body}")
            return False
        
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self.email_config["username"]
            msg["To"] = self.email_config["to_addr"]
            
            with smtplib.SMTP_SSL(self.email_config["smtp_host"], self.email_config["smtp_port"]) as server:
                server.login(self.email_config["username"], self.email_config["password"])
                server.send_message(msg)
            
            self.logger.log_alert("info", f"邮件已发送: {subject}")
            return True
        except Exception as e:
            self.logger.log_error("email_send_failed", str(e))
            return False
    
    def notify_price_drop(self, product_name: str, old_price: float, new_price: float):
        """价格下降通知"""
        change_pct = (new_price - old_price) / old_price * 100
        subject = f"💰 降价提醒: {product_name}"
        body = f"""
商品降价提醒
===========
商品名称: {product_name}
原价: ¥{old_price:.2f}
现价: ¥{new_price:.2f}
降幅: {change_pct:.1f}%

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        self.send_email(subject, body)
    
    def notify_error(self, error_type: str, message: str, count: int):
        """错误告警通知"""
        subject = f"🚨 爬虫错误告警: {error_type}"
        body = f"""
爬虫错误告警
===========
错误类型: {error_type}
错误信息: {message}
发生次数: {count}

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        self.send_email(subject, body)


# ==================== 演示 ====================

def demo():
    """演示监控系统"""
    print("🎯 高级监控系统演示")
    print("=" * 40)
    
    # 创建组件
    logger = StructuredLogger("demo_crawler", "demo_crawler.log")
    metrics = MetricsCollector(window_size=30)
    notifier = AlertNotifier()
    
    # 模拟爬取过程
    import random
    
    print("\n🔄 模拟爬取过程...")
    for i in range(50):
        # 模拟请求
        success = random.random() > 0.15  # 85% 成功率
        duration = random.uniform(0.5, 4.0)
        
        # 模拟错误
        error_type = None
        if not success:
            error_type = random.choice(["timeout", "connection_error", "parse_error"])
        
        # 记录指标
        metrics.record_request(success, duration, error_type)
        
        # 记录日志
        status = "success" if success else "failed"
        logger.log_scrape_event(
            url=f"https://example.com/product/{i}",
            status=status,
            duration=duration
        )
        
        # 模拟数据爬取
        if success and random.random() > 0.3:
            metrics.record_item(dropped=False)
        else:
            metrics.record_item(dropped=True)
        
        # 模拟价格变动
        if success and random.random() > 0.7:
            old_price = random.uniform(50, 500)
            new_price = old_price * random.uniform(0.85, 1.15)
            logger.log_price_change(
                product_id=f"SKU-{i:03d}",
                name=f"商品{i}",
                old_price=old_price,
                new_price=new_price
            )
        
        time.sleep(0.1)  # 模拟请求间隔
    
    # 打印报告
    metrics.print_report()
    
    # 显示告警
    if metrics.alerts:
        print("\n⚠️  告警记录:")
        for alert in metrics.alerts[-5:]:
            print(f"   [{alert.level.value}] {alert.message}")


if __name__ == "__main__":
    demo()
