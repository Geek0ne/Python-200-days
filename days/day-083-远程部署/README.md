# Day 083 — 远程部署

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

**参考答案**

**蓝绿部署（Blue-Green）**：准备两套完整环境，Blue 跑当前生产版本，Green 部署新版本；Green 测试通过后，在负载均衡/路由处把流量**一次性整体**从 Blue 切到 Green。

- 优点：切换瞬间完成；**回滚极快**（流量切回 Blue 即可，旧环境原封不动）；新版本先在隔离环境完整验证，上线风险低；不存在新旧混跑。
- 缺点：要**双倍资源**（两套完整环境）；数据库 schema 变更棘手（两套版本可能要兼容同一个库）；切换是"全量"的，出问题影响面大（虽然回滚快）。
- 适用：资源充足、对上线安全性/快速回滚要求高、无状态或 DB 兼容的服务、大版本发布。

**滚动更新（Rolling Update）**：逐批替换实例（如每次 1～2 台），摘流量→更新→健康检查→加回，再下一批，直到全部变成新版本。

- 优点：**省资源**（无需双倍环境）；渐进发布，出问题只影响一小部分，可中途暂停。
- 缺点：发布期间**新旧版本共存**（要求 API/DB 向前向后兼容）；整体耗时长；回滚要反向再滚一遍，比蓝绿慢。
- 适用：集群规模大、资源有限、能容忍短暂新旧共存、日常小步迭代（Kubernetes 默认策略）。

一句话选型：**要"秒级切换 + 秒级回滚"且资源够 → 蓝绿；要省资源、渐进小步 → 滚动；想先用真实小流量验证 → 金丝雀**（先导 5% 流量到新版本，观察无异常再扩大）。

💡 提示：无论哪种策略，数据库迁移都要"先扩展后收缩"（expand-contract）——先加兼容字段，等新旧版本都稳定后再删旧字段，否则新旧共存或回滚时会因 schema 不兼容报错。

2. **如何设计一个支持多环境（dev/staging/prod）的部署系统？** 需要考虑哪些配置差异？

**参考答案**

设计要点：

1. **配置分层/分离**：把"配置"抽成独立一层，每个环境一套（dev/staging/prod），**代码同一份、配置各不同**。常见做法：基础配置 + 各环境覆盖，或独立配置文件/配置中心（Consul、Nacos、Apollo）。
2. **环境选择机制**：用环境变量（如 `DEPLOY_ENV`）或命令行参数指定目标环境，**默认落到最低风险的 dev**，防止误部署生产。
3. **常见配置差异项**：
   - 机器列表 / 副本数（dev 1 台，prod 多台）
   - 调试开关、日志级别（dev DEBUG，prod INFO/WARN）
   - 数据库/缓存/第三方服务的地址与凭证
   - 域名、端口、资源限制、限流阈值
   - 功能开关（feature flag，灰度用）
4. **密钥管理**：密码/密钥/证书**绝不硬编码、不进 Git**，用环境变量、密钥管理（Vault、K8s Secret、云 KMS）在运行时注入，并按环境区分权限。
5. **一致性与隔离**：同一份部署脚本、同一个构建产物（build once, deploy many），只换配置；环境间网络隔离，prod 加审批/灰度。

小例子（已验证，stdlib 多环境配置 + 运行时注入密钥）：

```python
import os
from dataclasses import dataclass, replace

@dataclass
class DeployConfig:
    env: str
    hosts: list
    app_dir: str
    debug: bool
    replicas: int
    db_url: str = ""   # 敏感信息运行时注入，不硬编码

# 各环境静态配置（差异：机器列表、调试开关、副本数、部署路径等）
CONFIGS = {
    "dev":     DeployConfig("dev",     ["dev-1"],                    "/opt/app", True,  1),
    "staging": DeployConfig("staging", ["stage-1", "stage-2"],       "/opt/app", False, 2),
    "prod":    DeployConfig("prod",    ["prod-1", "prod-2", "prod-3"], "/srv/app", False, 3),
}

def load_config():
    # 环境由环境变量 DEPLOY_ENV 选择，默认 dev（防止误部署到生产）
    env = os.environ.get("DEPLOY_ENV", "dev")
    if env not in CONFIGS:
        raise ValueError(f"未知环境: {env}")
    # 敏感信息运行时从环境变量/密钥管理注入，返回副本以免污染静态配置
    return replace(CONFIGS[env], db_url=os.environ.get("DB_URL", ""))

# 模拟通过环境变量选择 prod
os.environ["DEPLOY_ENV"] = "prod"
os.environ["DB_URL"] = "postgres://prod-db:5432/app"   # 由密钥管理注入，不硬编码
cfg = load_config()
print("当前环境:", cfg.env)
print("目标主机:", cfg.hosts)
print("调试模式:", cfg.debug)
print("副本数:", cfg.replicas)
print("DB URL 来自环境变量:", cfg.db_url)

# 切到 dev 验证配置隔离
os.environ["DEPLOY_ENV"] = "dev"
print("切到 dev 后主机:", load_config().hosts, "调试:", load_config().debug)
```

预期输出：

```
当前环境: prod
目标主机: ['prod-1', 'prod-2', 'prod-3']
调试模式: False
副本数: 3
DB URL 来自环境变量: postgres://prod-db:5432/app
切到 dev 后主机: ['dev-1'] 调试: True
```

同一份代码，靠 `DEPLOY_ENV` 切换环境、靠环境变量注入密钥，dev/prod 配置互不污染。

💡 提示：坚持"一次构建、多环境部署"——产物（tar.gz/镜像）在各环境应是同一个，只换配置；别为每个环境重新打包，否则无法保证"staging 测过的就是 prod 跑的"。

3. **部署失败后的回滚策略有哪些？** 如何保证回滚过程中服务不中断？

**参考答案**

常见回滚策略：

1. **指针/软链切回**：版本化 `releases/vN` + `current` 软链，回滚 = 把 `current` 指回旧 release 目录再 reload，**无需重新上传，秒级完成**（最常用）。
2. **蓝绿切回**：蓝绿部署时把流量切回旧环境（Blue），旧环境原封不动，回滚最快。
3. **反向滚动**：滚动更新时，把已更新到新版本的实例逐批换回旧版本，较慢但省资源。
4. **重新部署旧产物**：保留历史构建产物（tar.gz / 镜像 tag），回滚即重新部署上一个稳定版本；容器化环境直接改 image tag 最方便。
5. **数据库/配置回滚**：代码回滚 ≠ 数据回滚。DB 迁移要有 down 脚本或备份恢复，配置变更也要版本化——这是回滚里最难的一环。

如何保证回滚过程服务不中断：

- **多实例 + 负载均衡**：先把要回滚的实例从 LB 摘除（draining 排空在途连接），回滚并健康检查后再加回；其余实例继续服务，用户无感。
- **原子切换**：软链用 `ln -sfn` 这类原子操作，避免"半新半旧"的中间态被请求看到。
- **优雅关闭**：旧进程收 SIGTERM 后处理完在途请求再退出（见第 4 题），别 `kill -9`。
- **回滚也要健康检查**：回滚后确认旧版本健康再加回流量；若回滚也失败，立即告警转人工。
- **兼容性兜底**：DB 用 expand-contract、API 向前向后兼容，让新旧共存与回滚都不报错。

💡 提示：回滚应是"提前演练过的常规操作"，不是出事才临时想办法——定期在 staging 演练回滚，保留历史产物与备份，并记录每次回滚的原因便于复盘。

4. **如何实现零停机部署？** 提示：考虑 connection draining 和 graceful shutdown。

**参考答案**

零停机的核心：**任何时刻都有健康实例对外服务，切换/重启不丢用户请求。** 关键机制：

1. **多实例 + 负载均衡**：至少 2 个实例挂在 LB 后，更新其中一个时其余照常服务。
2. **连接排空（connection draining）**：更新某实例前，先把它从 LB 摘除（标记不健康/权重置 0），LB 不再发新请求给它，但**允许已有连接处理完**。
3. **优雅关闭（graceful shutdown）**：给进程发 SIGTERM，进程收到后：停止接收新请求 → 处理完在途请求 → 关闭资源 → 退出；设一个超时（如 30s），超时才 SIGKILL，绝不一上来就 `kill -9`。
4. **健康检查门禁**：新实例启动并通过就绪/健康检查后**才加回 LB**；不通过就不加回并触发回滚。
5. **分批滚动 / 蓝绿**：配合第 1 题的策略逐批或整体切换，保证全程"剩余健康实例足够"。

单实例更新的典型时序：

```text
从 LB 摘除(draining) → 等在途请求完成 → SIGTERM 优雅退出
   → 部署新版本 → 启动 → 健康检查通过 → 加回 LB → 下一台
```

小例子（已验证，stdlib 模拟"SIGTERM → 停收新请求 → 完成在途 → 安全退出"）：

```python
import signal

class GracefulServer:
    def __init__(self):
        self.shutting_down = False
        self.active = 0          # 正在处理中的请求数
        self.done = []
        signal.signal(signal.SIGTERM, self._on_sigterm)

    def _on_sigterm(self, signum, frame):
        print("收到 SIGTERM → 停止接收新请求，进入 draining")
        self.shutting_down = True

    def handle(self, name):
        if self.shutting_down:
            print(f"  拒绝新请求 {name}（负载均衡已摘除本实例）")
            return
        self.active += 1
        print(f"  处理 {name}...")
        self.active -= 1          # 模拟处理完成
        self.done.append(name)

    def shutdown(self):
        # 优雅关闭：等在途请求全部处理完再退出
        while self.active > 0:
            print(f"  等待 {self.active} 个在途请求完成...")
        print(f"优雅关闭完成，共处理 {len(self.done)} 个请求，可安全退出")

s = GracefulServer()
s.handle("req-1")
s.handle("req-2")
signal.raise_signal(signal.SIGTERM)   # 部署系统发来 SIGTERM（Windows 下也能触发 Python 处理器）
s.handle("req-3")                     # 新请求被拒绝
s.shutdown()
print("已处理:", s.done)
```

预期输出：

```
  处理 req-1...
  处理 req-2...
收到 SIGTERM → 停止接收新请求，进入 draining
  拒绝新请求 req-3（负载均衡已摘除本实例）
优雅关闭完成，共处理 2 个请求，可安全退出
已处理: ['req-1', 'req-2']
```

收到 SIGTERM 后不再接新请求（req-3 被拒），已接的 req-1/req-2 处理完才退出——这就是 graceful shutdown + draining 的最小骨架。

💡 提示：真实服务还要处理长连接/WebSocket/后台任务，draining 超时要覆盖最长请求；Kubernetes 里用 `preStop` hook + `readinessProbe` + `terminationGracePeriodSeconds` 配合实现。

5. **CI/CD 流水线中，Python 自动化部署脚本应该放在哪个阶段？** 如何与 Jenkins/GitHub Actions 集成？

**参考答案**

**放在哪个阶段**：典型流水线是 `提交 → 构建 → 测试 → 打包产物 →（部署 staging → 集成/冒烟测试）→ 部署 prod → 部署后验证`。Python 自动化部署脚本属于 **CD（Deploy/Release）阶段**，即"构建 + 测试 + 产物"都通过**之后**才执行。CI 负责"构建并验证"，CD 负责"把产物送到目标环境"，别把部署混进构建/测试阶段。部署脚本本身要版本化进仓库（如 `deploy/`），由流水线调用，目标环境用环境变量/参数传入。

**GitHub Actions 集成示例**（示意 YAML）：

```yaml
name: deploy
on:
  push:
    branches: [main]
jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: pytest            # CI：测试必须通过
      - run: python build.py   # 打包产物
      - uses: actions/upload-artifact@v4
        with: { name: app, path: builds/app.tar.gz }
  deploy-prod:
    needs: build-test          # 构建测试成功后才部署
    runs-on: ubuntu-latest
    environment: production    # 可配置人工审批/保护规则
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: app }
      - run: pip install fabric paramiko
      - run: python deploy/deploy.py   # CD：调用 Python 部署脚本
        env:
          DEPLOY_ENV: prod
          SSH_KEY: ${{ secrets.SSH_KEY }}   # 密钥从 Secrets 注入
```

**Jenkins 集成示例**（示意 Jenkinsfile）：

```groovy
pipeline {
  agent any
  stages {
    stage('Build & Test') {
      steps {
        sh 'pip install -r requirements.txt'
        sh 'pytest'
        sh 'python build.py'
      }
    }
    stage('Deploy to Prod') {
      steps {
        // 凭证用 Jenkins Credentials 注入，不硬编码
        withCredentials([sshUserPrivateKey(credentialsId: 'prod-ssh', keyFileVariable: 'KEY')]) {
          sh 'DEPLOY_ENV=prod python deploy/deploy.py --key $KEY'
        }
      }
    }
  }
}
```

集成关键点：

- **门禁**：用 `needs`/stage 依赖，测试通过才进部署。
- **审批保护**：prod 用 `environment`/人工审批，防止误部署。
- **密钥注入**：用 Secrets/Credentials，绝不写进脚本或日志。
- **幂等 + 可回滚**：部署脚本要幂等、支持回滚，流水线失败时能自动/手动触发回滚。

💡 提示：上面 YAML/Jenkinsfile 是示意片段，实际字段以所用平台版本为准；被调用的 `deploy.py` 就是第 2/3 题里那套 Fabric/Paramiko 部署逻辑，流水线只负责"在正确的阶段、带正确的环境和密钥"去调用它。
