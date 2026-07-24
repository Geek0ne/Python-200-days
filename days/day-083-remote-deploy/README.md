# Day 083 — 远程执行与部署：自动化运维实战

## 📋 今日目标
掌握远程部署的完整流程：代码打包、传输、解压、依赖安装、服务重启、健康检查、回滚策略。

---

## 一、部署策略概览

### 1.1 常见部署模式

```
蓝绿部署 (Blue-Green):
┌──────────┐     ┌──────────┐
│  Blue    │◄────│  负载均衡  │
│  (当前)   │     │          │
└──────────┘     └─────┬────┘
                       │ 切换
                 ┌─────▼────┐
                 │  Green   │
                 │  (新版本) │
                 └──────────┘

滚动更新 (Rolling Update):
  服务器:  S1  S2  S3  S4  S5
  旧版本:  v1  v1  v1  v1  v1
  步骤1:   v2  v1  v1  v1  v1  ← 更新 S1
  步骤2:   v2  v2  v1  v1  v1  ← 更新 S2
  步骤3:   v2  v2  v2  v1  v1  ← 更新 S3
  ...

金丝雀部署 (Canary):
  ┌─────────────────────────┐
  │       负载均衡           │
  │    ┌──────┬──────┐      │
  │    │ 5%   │ 95%  │      │
  │    │ 新版本│ 旧版本│      │
  │    └──────┴──────┘      │
  └─────────────────────────┘
  先将 5% 流量导向新版本，观察无异常后逐步扩大
```

### 1.2 部署流程标准化

```
标准部署流程：
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ 1.打包   │──►│ 2.传输   │──►│ 3.备份   │──►│ 4.解压   │
│ tar.gz  │   │ SCP/SFTP│   │ 旧版本   │   │ 部署    │
└─────────┘   └─────────┘   └─────────┘   └─────────┘
                                                      │
┌─────────┐   ┌─────────┐   ┌─────────┐              │
│ 7.完成   │◄──│ 6.验证   │◄──│ 5.启动   │◄─────────────┘
│ 通知     │   │ 健康检查 │   │ 服务     │
└─────────┘   └─────────┘   └─────────┘
      │
      ▼ 失败
┌─────────┐
│ 回滚     │
│ 恢复旧版 │
└─────────┘
```

---

## 二、代码打包与版本管理

### 2.1 语义化版本号
```python
# 版本号格式: MAJOR.MINOR.PATCH
# MAJOR: 不兼容的 API 修改
# MINOR: 向下兼容的功能性新增
# PATCH: 向下兼容的问题修正

version = "1.2.3"  # 主版本.次版本.补丁
```

### 2.2 打包脚本
```python
#!/usr/bin/env python3
"""应用打包脚本"""

import os
import subprocess
import tarfile
from datetime import datetime

def create_build(version: str, source_dir: str = '.', output_dir: str = 'builds'):
    """创建应用构建包"""
    os.makedirs(output_dir, exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"app-{version}-{timestamp}.tar.gz"
    filepath = os.path.join(output_dir, filename)

    # 排除不需要的文件
    exclude_patterns = [
        '__pycache__', '*.pyc', '.git', 'venv', 'node_modules',
        '.env', '*.log', 'builds'
    ]

    with tarfile.open(filepath, 'w:gz') as tar:
        for root, dirs, files in os.walk(source_dir):
            # 排除目录
            dirs[:] = [d for d in dirs if not any(
                p in d for p in ['__pycache__', '.git', 'venv', 'node_modules']
            )]
            for file in files:
                if any(p in file for p in ['*.pyc', '.env', '*.log']):
                    continue
                filepath_full = os.path.join(root, file)
                tar.add(filepath_full, arcname=os.path.relpath(filepath_full, source_dir))

    print(f"✅ 构建包已创建: {filepath}")
    return filepath
```

---

## 三、远程部署脚本

### 3.1 基础部署器
```python
import paramiko
import os
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class DeployConfig:
    """部署配置"""
    host: str
    port: int = 22
    username: str = 'root'
    password: Optional[str] = None
    key_file: Optional[str] = None
    app_dir: str = '/opt/myapp'
    backup_dir: str = '/opt/myapp/backups'
    service_name: str = 'myapp'

class Deployer:
    def __init__(self, config: DeployConfig):
        self.config = config
        self.client = None

    def connect(self):
        """建立 SSH 连接"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            'hostname': self.config.host,
            'port': self.config.port,
            'username': self.config.username,
            'timeout': 10,
        }
        if self.config.key_file:
            connect_kwargs['key_filename'] = self.config.key_file
        else:
            connect_kwargs['password'] = self.config.password

        self.client.connect(**connect_kwargs)
        print(f"✅ 已连接: {self.config.host}")

    def run(self, command: str, check: bool = True) -> str:
        """执行远程命令"""
        stdin, stdout, stderr = self.client.exec_command(command, timeout=30)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if check and exit_code != 0:
            raise Exception(f"命令失败 [{exit_code}]: {command}\n错误: {error}")

        return output

    def upload(self, local_path: str, remote_path: str):
        """上传文件"""
        sftp = self.client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        print(f"⬆️  上传: {local_path} → {remote_path}")

    def backup(self, version: str):
        """备份当前版本"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.config.backup_dir}/backup_{version}_{timestamp}"

        self.run(f"mkdir -p {self.config.backup_dir}")
        self.run(f"cp -r {self.config.app_dir}/current {backup_path}")
        print(f"📦 已备份: {backup_path}")
        return backup_path

    def deploy(self, package_path: str, version: str):
        """执行部署"""
        print(f"\n{'='*50}")
        print(f"🚀 开始部署 v{version}")
        print(f"{'='*50}")

        try:
            # 1. 连接
            self.connect()

            # 2. 上传包
            remote_package = f"/tmp/app-{version}.tar.gz"
            self.upload(package_path, remote_package)

            # 3. 备份
            self.backup(version)

            # 4. 解压部署
            self.run(f"cd {self.config.app_dir} && tar xzf {remote_package} -C current")

            # 5. 安装依赖
            self.run(f"cd {self.config.app_dir}/current && "
                    f"pip install -r requirements.txt -q", check=False)

            # 6. 数据库迁移（如果需要）
            # self.run(f"cd {self.config.app_dir}/current && python manage.py migrate")

            # 7. 重启服务
            self.run(f"systemctl restart {self.config.service_name}")
            print("🔄 服务已重启")

            # 8. 等待启动
            time.sleep(3)

            # 9. 健康检查
            if self.health_check():
                print(f"✅ 部署成功！v{version} 已上线")
            else:
                print("❌ 健康检查失败，开始回滚...")
                self.rollback()
                return False

        except Exception as e:
            print(f"❌ 部署失败: {e}")
            print("🔄 开始回滚...")
            self.rollback()
            return False
        finally:
            if self.client:
                self.client.close()

        return True

    def health_check(self) -> bool:
        """健康检查"""
        try:
            result = self.run(f"systemctl is-active {self.config.service_name}")
            return result == 'active'
        except:
            return False

    def rollback(self):
        """回滚到上一个备份版本"""
        try:
            if not self.client:
                self.connect()

            # 找到最新的备份
            result = self.run(
                f"ls -t {self.config.backup_dir}/backup_* | head -1"
            )

            if result:
                self.run(f"rm -rf {self.config.app_dir}/current")
                self.run(f"cp -r {result} {self.config.app_dir}/current")
                self.run(f"systemctl restart {self.config.service_name}")
                print(f"✅ 已回滚到: {result}")
            else:
                print("⚠️  没有找到可用的备份")

        except Exception as e:
            print(f"❌ 回滚失败: {e}")

# 使用示例
if __name__ == '__main__':
    config = DeployConfig(
        host='192.168.1.100',
        username='root',
        password='password',
        app_dir='/opt/myapp',
        service_name='myapp'
    )

    deployer = Deployer(config)
    deployer.deploy('builds/app-1.0.0.tar.gz', '1.0.0')
```

---

## 四、监控与告警

### 4.1 监控指标收集
```python
class Monitor:
    """远程监控器"""

    def __init__(self, client: paramiko.SSHClient):
        self.client = client

    def collect_metrics(self) -> dict:
        """收集系统指标"""
        metrics = {}

        # CPU
        output = self._run("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
        metrics['cpu_percent'] = float(output) if output else 0

        # 内存
        output = self._run("free | grep Mem | awk '{printf \"%.1f\", $3/$2*100}'")
        metrics['memory_percent'] = float(output) if output else 0

        # 磁盘
        output = self._run("df / | tail -1 | awk '{print $5}' | tr -d '%'")
        metrics['disk_percent'] = int(output) if output else 0

        # 负载
        output = self._run("cat /proc/loadavg | awk '{print $1}'")
        metrics['load_1m'] = float(output) if output else 0

        # 连接数
        output = self._run("ss -s | grep 'estab' | awk '{print $4}'")
        metrics['connections'] = int(output) if output else 0

        return metrics

    def check_thresholds(self, metrics: dict) -> list:
        """检查阈值告警"""
        alerts = []

        if metrics['cpu_percent'] > 90:
            alerts.append(('critical', f"CPU: {metrics['cpu_percent']:.1f}%"))
        elif metrics['cpu_percent'] > 80:
            alerts.append(('warning', f"CPU: {metrics['cpu_percent']:.1f}%"))

        if metrics['memory_percent'] > 95:
            alerts.append(('critical', f"内存: {metrics['memory_percent']:.1f}%"))
        elif metrics['memory_percent'] > 85:
            alerts.append(('warning', f"内存: {metrics['memory_percent']:.1f}%"))

        if metrics['disk_percent'] > 90:
            alerts.append(('critical', f"磁盘: {metrics['disk_percent']}%"))

        return alerts
```

### 4.2 自动化监控循环
```python
import time
import json
from datetime import datetime

def monitoring_loop(servers: list, interval: int = 60):
    """持续监控循环"""
    while True:
        for server_config in servers:
            try:
                client = create_client(server_config)
                monitor = Monitor(client)
                metrics = monitor.collect_metrics()
                alerts = monitor.check_thresholds(metrics)

                # 记录日志
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'server': server_config['host'],
                    'metrics': metrics,
                    'alerts': alerts
                }
                save_log(log_entry)

                # 发送告警
                for level, message in alerts:
                    send_alert(level, server_config['host'], message)

                client.close()

            except Exception as e:
                send_alert('error', server_config['host'], str(e))

        time.sleep(interval)
```

---

## 五、运维脚本最佳实践

### 5.1 幂等性设计
```python
# ✅ 幂等：重复执行结果一致
def ensure_user_exists(username):
    """确保用户存在（幂等）"""
    run(f"id {username} || useradd -m {username}")

# ✅ 幂等：确保目录存在
def ensure_directory(path):
    run(f"mkdir -p {path}")

# ✅ 幂等：确保服务运行
def ensure_service_running(service_name):
    run(f"systemctl is-active {service_name} || systemctl start {service_name}")
```

### 5.2 超时与重试
```python
import time
from functools import wraps

def retry(max_retries=3, delay=5):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"  ⚠️  重试 {attempt+1}/{max_retries}: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry(max_retries=3, delay=5)
def deploy_with_retry(deployer, package, version):
    return deployer.deploy(package, version)
```

---

## 六、思考题

1. **蓝绿部署和滚动更新各有什么优缺点？** 在什么场景下选择哪种？
2. **如何设计一个支持多环境（dev/staging/prod）的部署系统？** 需要考虑哪些配置差异？
3. **部署失败后的回滚策略有哪些？** 如何保证回滚过程中服务不中断？
4. **如何实现零停机部署？** 提示：考虑 connection draining 和 graceful shutdown。
5. **CI/CD 流水线中，Python 自动化部署脚本应该放在哪个阶段？** 如何与 Jenkins/GitHub Actions 集成？
