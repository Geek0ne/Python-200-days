#!/usr/bin/env python3
"""
Day 082 - 实战案例：服务器巡检与自动告警系统
完整的运维工具，包含：服务器状态收集、健康检查、告警通知
"""

import paramiko
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional

# ============ 数据模型 ============
@dataclass
class ServerConfig:
    """服务器配置"""
    host: str
    port: int = 22
    username: str = 'root'
    password: Optional[str] = None
    key_file: Optional[str] = None
    name: str = ''

    def __post_init__(self):
        if not self.name:
            self.name = self.host

@dataclass
class HealthMetrics:
    """健康指标"""
    hostname: str = ''
    uptime: str = ''
    cpu_usage: float = 0.0
    memory_total: str = ''
    memory_used: str = ''
    memory_percent: float = 0.0
    disk_total: str = ''
    disk_used: str = ''
    disk_percent: float = 0.0
    load_avg: str = ''
    network_connections: int = 0
    timestamp: str = ''

@dataclass
class HealthCheckResult:
    """巡检结果"""
    server: str
    status: str  # healthy / warning / critical / error
    metrics: Optional[HealthMetrics] = None
    alerts: List[str] = None
    error: str = ''

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []

# ============ 巡检引擎 ============
class ServerInspector:
    """服务器巡检引擎"""

    # 告警阈值
    CPU_WARN = 80.0
    CPU_CRIT = 95.0
    MEMORY_WARN = 80.0
    MEMORY_CRIT = 95.0
    DISK_WARN = 80.0
    DISK_CRIT = 90.0

    def __init__(self):
        self.results: List[HealthCheckResult] = []

    def _connect(self, config: ServerConfig) -> paramiko.SSHClient:
        """建立 SSH 连接"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            'hostname': config.host,
            'port': config.port,
            'username': config.username,
            'timeout': 10,
        }

        if config.key_file:
            connect_kwargs['key_filename'] = config.key_file
        elif config.password:
            connect_kwargs['password'] = config.password

        client.connect(**connect_kwargs)
        return client

    def _exec(self, client: paramiko.SSHClient, cmd: str) -> str:
        """执行命令并返回输出"""
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        return stdout.read().decode().strip()

    def collect_metrics(self, config: ServerConfig) -> HealthMetrics:
        """收集服务器指标"""
        metrics = HealthMetrics(timestamp=datetime.now().isoformat())

        client = self._connect(config)
        try:
            # 主机名
            metrics.hostname = self._exec(client, 'hostname')

            # 运行时间
            metrics.uptime = self._exec(client, 'uptime -p')

            # CPU 使用率
            cpu_str = self._exec(client,
                "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
            try:
                metrics.cpu_usage = float(cpu_str)
            except ValueError:
                metrics.cpu_usage = 0.0

            # 内存
            mem_info = self._exec(client, "free -h | grep Mem")
            if mem_info:
                parts = mem_info.split()
                metrics.memory_total = parts[1] if len(parts) > 1 else 'N/A'
                metrics.memory_used = parts[2] if len(parts) > 2 else 'N/A'
                try:
                    metrics.memory_percent = float(parts[2].replace('Gi', '')) / \
                                            float(parts[1].replace('Gi', '')) * 100
                except (ValueError, ZeroDivisionError):
                    metrics.memory_percent = 0.0

            # 磁盘
            disk_info = self._exec(client, "df -h / | tail -1")
            if disk_info:
                parts = disk_info.split()
                metrics.disk_total = parts[1] if len(parts) > 1 else 'N/A'
                metrics.disk_used = parts[2] if len(parts) > 2 else 'N/A'
                try:
                    metrics.disk_percent = float(parts[4].replace('%', ''))
                except (ValueError, IndexError):
                    metrics.disk_percent = 0.0

            # 负载
            metrics.load_avg = self._exec(client, "cat /proc/loadavg | awk '{print $1, $2, $3}'")

            # 网络连接数
            conn_str = self._exec(client, "ss -s | grep 'estab' | awk '{print $4}'")
            try:
                metrics.network_connections = int(conn_str)
            except ValueError:
                metrics.network_connections = 0

        finally:
            client.close()

        return metrics

    def check_health(self, config: ServerConfig) -> HealthCheckResult:
        """检查单台服务器健康状态"""
        result = HealthCheckResult(server=config.name)

        try:
            metrics = self.collect_metrics(config)
            result.metrics = metrics

            # 检查告警条件
            alerts = []

            if metrics.cpu_usage >= self.CPU_CRIT:
                alerts.append(f"🔴 CPU 使用率 {metrics.cpu_usage:.1f}% >= {self.CPU_CRIT}%")
            elif metrics.cpu_usage >= self.CPU_WARN:
                alerts.append(f"🟡 CPU 使用率 {metrics.cpu_usage:.1f}% >= {self.CPU_WARN}%")

            if metrics.memory_percent >= self.MEMORY_CRIT:
                alerts.append(f"🔴 内存使用率 {metrics.memory_percent:.1f}% >= {self.MEMORY_CRIT}%")
            elif metrics.memory_percent >= self.MEMORY_WARN:
                alerts.append(f"🟡 内存使用率 {metrics.memory_percent:.1f}% >= {self.MEMORY_WARN}%")

            if metrics.disk_percent >= self.DISK_CRIT:
                alerts.append(f"🔴 磁盘使用率 {metrics.disk_percent:.1f}% >= {self.DISK_CRIT}%")
            elif metrics.disk_percent >= self.DISK_WARN:
                alerts.append(f"🟡 磁盘使用率 {metrics.disk_percent:.1f}% >= {self.DISK_WARN}%")

            result.alerts = alerts

            # 判定状态
            if any('🔴' in a for a in alerts):
                result.status = 'critical'
            elif alerts:
                result.status = 'warning'
            else:
                result.status = 'healthy'

        except Exception as e:
            result.status = 'error'
            result.error = str(e)

        return result

    def run_inspection(self, servers: List[ServerConfig]) -> List[HealthCheckResult]:
        """批量巡检"""
        self.results = []
        for server in servers:
            print(f"🔍 检查 {server.name} ({server.host})...")
            result = self.check_health(server)
            self.results.append(result)

            # 打印结果
            if result.status == 'healthy':
                print(f"  ✅ 健康")
            elif result.status == 'warning':
                print(f"  ⚠️  警告")
            elif result.status == 'critical':
                print(f"  🔴 严重")
            else:
                print(f"  ❌ 错误: {result.error}")

            if result.metrics:
                m = result.metrics
                print(f"     CPU: {m.cpu_usage:.1f}% | 内存: {m.memory_percent:.1f}% | 磁盘: {m.disk_percent:.1f}%")
            if result.alerts:
                for alert in result.alerts:
                    print(f"     {alert}")
            print()

        return self.results

    def save_report(self, filename: str = 'inspection_report.json'):
        """保存巡检报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_servers': len(self.results),
            'healthy': sum(1 for r in self.results if r.status == 'healthy'),
            'warning': sum(1 for r in self.results if r.status == 'warning'),
            'critical': sum(1 for r in self.results if r.status == 'critical'),
            'error': sum(1 for r in self.results if r.status == 'error'),
            'servers': [asdict(r) for r in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"📋 报告已保存: {filename}")
        return report

# ============ 告警通知 ============
class AlertNotifier:
    """告警通知器"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url

    def send_alert(self, result: HealthCheckResult):
        """发送告警通知"""
        if result.status == 'healthy':
            return

        # 构建告警消息
        severity = '🔴 严重' if result.status == 'critical' else '⚠️ 警告'
        message = f"""
{severity} — {result.server}
{'=' * 40}
"""

        if result.metrics:
            m = result.metrics
            message += f"""
主机: {m.hostname}
运行时间: {m.uptime}
CPU: {m.cpu_usage:.1f}%
内存: {m.memory_percent:.1f}%
磁盘: {m.disk_percent:.1f}%
负载: {m.load_avg}
"""

        if result.alerts:
            message += "\n告警详情:\n"
            for alert in result.alerts:
                message += f"  {alert}\n"

        if result.error:
            message += f"\n错误: {result.error}\n"

        print(message)

        # 如果配置了 webhook，发送到 Slack/Discord 等
        if self.webhook_url:
            self._send_webhook(message)

    def _send_webhook(self, message: str):
        """发送到 Webhook（示例）"""
        # import requests
        # requests.post(self.webhook_url, json={'text': message})
        print("  📤 Webhook 通知已发送（模拟）")

# ============ 主程序 ============
if __name__ == '__main__':
    print("🏥 服务器巡检与自动告警系统")
    print("=" * 60)

    # 配置服务器列表
    servers = [
        ServerConfig(
            host='localhost',
            username='root',
            password='password',
            name='本地测试服务器'
        ),
        # 添加更多服务器：
        # ServerConfig(
        #     host='192.168.1.101',
        #     username='root',
        #     key_file='/root/.ssh/id_rsa',
        #     name='Web 服务器 01'
        # ),
    ]

    # 执行巡检
    inspector = ServerInspector()
    results = inspector.run_inspection(servers)

    # 保存报告
    report = inspector.save_report('inspection_report.json')

    # 发送告警
    notifier = AlertNotifier()
    for result in results:
        notifier.send_alert(result)

    # 汇总
    print("=" * 60)
    print(f"📊 巡检汇总:")
    print(f"  总计: {report['total_servers']} 台")
    print(f"  健康: {report['healthy']} ✅")
    print(f"  警告: {report['warning']} ⚠️")
    print(f"  严重: {report['critical']} 🔴")
    print(f"  错误: {report['error']} ❌")
    print("🎉 巡检完成！")
