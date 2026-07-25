# 监控告警系统最佳实践

## 1. 性能优化

### 1.1 采集频率控制

```python
# ❌ 错误：过于频繁的采集
while True:
    metrics = collect_all()  # 每秒采集会消耗大量 CPU
    time.sleep(1)

# ✅ 正确：合理的采集间隔
while True:
    metrics = collect_all()
    time.sleep(60)  # 每分钟采集一次
```

**建议采集频率：**

| 指标类型 | 建议间隔 | 原因 |
|----------|----------|------|
| CPU 使用率 | 30-60秒 | 需要足够采样时间 |
| 内存使用率 | 60秒 | 变化相对缓慢 |
| 磁盘使用率 | 300秒 | 变化很慢 |
| 网络流量 | 10-30秒 | 需要实时监控 |
| 进程状态 | 60秒 | 避免频繁遍历 |

### 1.2 异步采集

```python
import asyncio
import psutil

async def collect_cpu():
    """异步采集 CPU"""
    return psutil.cpu_percent(interval=None)

async def collect_memory():
    """异步采集内存"""
    return psutil.virtual_memory()

async def collect_all_async():
    """异步并行采集"""
    cpu, mem = await asyncio.gather(
        collect_cpu(),
        collect_memory()
    )
    return {"cpu": cpu, "memory": mem}
```

### 1.3 数据压缩

```python
import zlib
import json

def compress_metrics(metrics: dict) -> bytes:
    """压缩指标数据"""
    json_str = json.dumps(metrics)
    return zlib.compress(json_str.encode())

def decompress_metrics(data: bytes) -> dict:
    """解压指标数据"""
    return json.loads(zlib.decompress(data).decode())
```

---

## 2. 告警设计原则

### 2.1 告警分级

```
┌─────────────────────────────────────────────────────────────┐
│                    告警分级策略                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Level 1: INFO (信息)                                       │
│  ├─ 用途: 记录正常事件                                      │
│  ├─ 通知: 仅日志                                            │
│  └─ 示例: 服务启动、配置加载                                │
│                                                             │
│  Level 2: WARNING (警告)                                    │
│  ├─ 用途: 提示潜在问题                                      │
│  ├─ 通知: 日志 + 即时通讯                                   │
│  └─ 示例: CPU > 80%, 内存 > 85%                            │
│                                                             │
│  Level 3: ERROR (错误)                                      │
│  ├─ 用途: 功能受损                                          │
│  ├─ 通知: 日志 + 即时通讯 + 邮件                            │
│  └─ 示例: 服务响应慢、磁盘空间不足                          │
│                                                             │
│  Level 4: CRITICAL (严重)                                   │
│  ├─ 用途: 服务不可用                                        │
│  ├─ 通知: 日志 + 即时通讯 + 邮件 + 短信 + 电话              │
│  └─ 示例: 服务宕机、数据丢失                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 告警去重策略

```python
class AlertDeduplicator:
    """告警去重器"""
    
    def __init__(self):
        self.alerts = {}  # rule_name -> (count, first_time, last_time)
        self.window = 300  # 5分钟窗口
    
    def should_alert(self, rule_name: str) -> bool:
        """判断是否应该发送告警"""
        import time
        now = time.time()
        
        if rule_name in self.alerts:
            count, first_time, last_time = self.alerts[rule_name]
            
            # 在窗口内
            if now - last_time < self.window:
                self.alerts[rule_name] = (count + 1, first_time, now)
                return False
            
            # 窗口外，重置
            self.alerts[rule_name] = (1, now, now)
            return True
        
        # 新告警
        self.alerts[rule_name] = (1, now, now)
        return True
```

### 2.3 告警升级

```python
class AlertEscalation:
    """告警升级机制"""
    
    def __init__(self):
        self.escalation_rules = {
            "WARNING": {"after_minutes": 30, "escalate_to": "ERROR"},
            "ERROR": {"after_minutes": 15, "escalate_to": "CRITICAL"},
        }
        self.alert_start_times = {}
    
    def check_escalation(self, alert_name: str, current_level: str) -> str:
        """检查是否需要升级"""
        import time
        now = time.time()
        
        if alert_name not in self.alert_start_times:
            self.alert_start_times[alert_name] = now
            return current_level
        
        start_time = self.alert_start_times[alert_name]
        elapsed_minutes = (now - start_time) / 60
        
        rule = self.escalation_rules.get(current_level)
        if rule and elapsed_minutes >= rule["after_minutes"]:
            return rule["escalate_to"]
        
        return current_level
```

---

## 3. 安全考虑

### 3.1 权限控制

```python
import os

def check_permissions():
    """检查运行权限"""
    if os.geteuid() == 0:
        print("⚠️  警告: 正在以 root 权限运行")
        print("   建议使用普通用户运行监控服务")
    
    # 检查必要的文件权限
    config_file = "config.json"
    if os.path.exists(config_file):
        mode = os.stat(config_file).st_mode
        if mode & 0o077:  # 检查是否有其他用户权限
            print(f"⚠️  警告: {config_file} 权限过于宽松")
```

### 3.2 敏感信息保护

```python
import os
from pathlib import Path

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config = {}
    
    def load_from_env(self):
        """从环境变量加载配置"""
        self.config = {
            "db_password": os.getenv("DB_PASSWORD"),
            "api_key": os.getenv("API_KEY"),
            "webhook_url": os.getenv("WEBHOOK_URL"),
        }
    
    def load_from_file(self, path: str):
        """从文件加载配置（确保文件权限正确）"""
        config_path = Path(path)
        
        # 检查文件权限
        if config_path.exists():
            mode = config_path.stat().st_mode
            if mode & 0o077:
                print(f"⚠️  警告: {path} 权限过于宽松，建议设置为 600")
        
        import json
        with open(config_path) as f:
            self.config = json.load(f)
```

### 3.3 日志脱敏

```python
import re

def sanitize_log(message: str) -> str:
    """日志脱敏"""
    # 脱敏密码
    message = re.sub(r'password["\s:=]+\S+', 'password=***', message, flags=re.IGNORECASE)
    
    # 脱敏 API Key
    message = re.sub(r'api[_-]?key["\s:=]+\S+', 'api_key=***', message, flags=re.IGNORECASE)
    
    # 脱敏 IP 地址（可选）
    # message = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'x.x.x.x', message)
    
    return message
```

---

## 4. 故障排查

### 4.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| CPU 使用率不准确 | `cpu_percent` 首次调用返回 0 | 使用 `interval=1` 或多次调用 |
| 内存数据异常 | Linux 缓存被计入已用 | 使用 `available` 而非 `free` |
| 进程信息获取失败 | 进程已退出或权限不足 | 使用 try-except 捕获异常 |
| 告警重复发送 | 去重机制未生效 | 检查去重时间窗口配置 |
| 数据库写入失败 | 并发写入冲突 | 使用连接池或队列 |

### 4.2 调试技巧

```python
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

# 使用 psutil 的调试模式
import psutil
psutil.debug = True

# 检查 psutil 版本
print(f"psutil 版本: {psutil.__version__}")
```

### 4.3 性能分析

```python
import cProfile
import psutil

def profile_collection():
    """分析采集性能"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 执行采集
    for _ in range(100):
        psutil.cpu_percent(interval=0.1)
        psutil.virtual_memory()
        psutil.disk_usage('/')
    
    profiler.disable()
    profiler.print_stats(sort='cumtime')

if __name__ == "__main__":
    profile_collection()
```

---

## 5. 生产环境部署

### 5.1 systemd 服务配置

```ini
# /etc/systemd/system/monitor.service
[Unit]
Description=Python Monitoring Service
After=network.target

[Service]
Type=simple
User=monitor
Group=monitor
WorkingDirectory=/opt/monitoring
ExecStart=/usr/bin/python3 /opt/monitoring/service.py
Restart=always
RestartSec=10

# 安全限制
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/monitoring/data

[Install]
WantedBy=multi-user.target
```

### 5.2 Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

CMD ["python3", "service.py"]
```

### 5.3 监控服务自身监控

```python
import psutil
from datetime import datetime

class SelfMonitor:
    """监控服务自身监控"""
    
    def __init__(self):
        self.start_time = datetime.now()
    
    def get_health(self) -> dict:
        """获取自身健康状态"""
        process = psutil.Process()
        
        return {
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / (1024**2),
            "threads": process.num_threads(),
            "status": process.status()
        }
```

---

> 💡 遵循这些最佳实践可以构建更可靠、更安全的监控系统
