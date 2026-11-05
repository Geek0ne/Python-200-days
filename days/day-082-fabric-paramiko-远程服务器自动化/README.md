# Day 082 — Fabric 与 Paramiko：远程服务器自动化

## 📋 今日目标
掌握使用 Fabric 和 Paramiko 实现远程服务器自动化操作，包括远程命令执行、文件传输、批量管理。

---

## 一、远程自动化概述

### 1.1 为什么需要远程自动化？
在运维场景中，经常需要：
- 批量在多台服务器上执行命令
- 上传/下载文件
- 部署应用
- 收集系统信息
- 监控服务状态

手动 SSH 操作效率低且容易出错，自动化工具是必选项。

### 1.2 工具对比

| 特性 | Paramiko | Fabric |
|------|----------|--------|
| 定位 | SSH 底层库 | 高级运维框架 |
| 接口 | 低级、灵活 | 高级、简洁 |
| 学习曲线 | 陡峭 | 平缓 |
| 适合场景 | 自定义 SSH 协议操作 | 批量运维任务 |
| 连接管理 | 手动管理 | 内置连接池 |

**选择建议：**
- 简单运维任务 → **Fabric**（推荐）
- 需要精细控制 SSH 协议 → **Paramiko**
- 两者结合使用 → Fabric 内部调用 Paramiko

---

## 二、Paramiko 基础

### 2.1 SSH 连接原理
```
┌──────────┐                          ┌──────────┐
│  客户端    │    TCP 连接 (22端口)       │  服务端    │
│  Python   │◄────────────────────────►│  SSHD    │
│           │                          │          │
│  Paramiko │  1. TCP 握手              │  Linux   │
│           │  2. SSH 协议协商           │          │
│           │  3. 密钥交换               │          │
│           │  4. 认证 (密码/密钥)        │          │
│           │  5. 通道建立               │          │
│           │  6. 命令执行               │          │
└──────────┘                          └──────────┘
```

### 2.2 密码认证连接
```python
import paramiko

# 创建 SSH 客户端
client = paramiko.SSHClient()

# 自动添加未知主机密钥（生产环境应谨慎）
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# 连接服务器
client.connect(
    hostname='192.168.1.100',
    port=22,
    username='root',
    password='your_password',
    timeout=10
)

# 执行命令
stdin, stdout, stderr = client.exec_command('uname -a')
output = stdout.read().decode()
error = stderr.read().decode()
exit_code = stdout.channel.recv_exit_status()

print(f"输出: {output}")
print(f"错误: {error}")
print(f"退出码: {exit_code}")

# 关闭连接
client.close()
```

### 2.3 密钥认证连接（推荐）
```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# 使用私钥认证
private_key = paramiko.RSAKey.from_private_key_file('/root/.ssh/id_rsa')
# 或 Ed25519Key
# private_key = paramiko.Ed25519Key.from_private_key_file('/root/.ssh/id_ed25519')

client.connect(
    hostname='192.168.1.100',
    username='root',
    pkey=private_key
)

stdin, stdout, stderr = client.exec_command('hostname')
print(stdout.read().decode())

client.close()
```

### 2.4 SFTP 文件传输
```python
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.100', username='root', password='pass')

# 打开 SFTP 会话
sftp = client.open_sftp()

# 上传文件
sftp.put('/local/path/file.txt', '/remote/path/file.txt')

# 下载文件
sftp.get('/remote/path/file.txt', '/local/path/downloaded.txt')

# 列出远程目录
files = sftp.listdir('/remote/path/')
print(files)

# 检查文件是否存在
try:
    stat = sftp.stat('/remote/path/file.txt')
    print(f"文件大小: {stat.st_size} bytes")
except FileNotFoundError:
    print("文件不存在")

sftp.close()
client.close()
```

### 2.5 交互式 Shell
```python
import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.100', username='root', password='pass')

# 获取交互式 shell
shell = client.invoke_shell()

# 发送命令
shell.send('ls -la\n')
time.sleep(1)

# 读取输出
output = shell.recv(65536).decode()
print(output)

# 继续发送命令
shell.send('df -h\n')
time.sleep(1)
output = shell.recv(65536).decode()
print(output)

shell.close()
client.close()
```

---

## 三、Fabric 核心用法

### 3.1 Fabric 简介
Fabric 是基于 Paramiko 的高级运维框架，提供简洁的 Python API 来执行远程命令和管理服务器。

### 3.2 基础连接
```python
from fabric import Connection

# 基础连接
conn = Connection('root@192.168.1.100')

# 带密码连接
conn = Connection('root@192.168.1.100', connect_kwargs={'password': 'pass'})

# 带密钥连接
conn = Connection('root@192.168.1.100',
                  connect_kwargs={'key_filename': '/root/.ssh/id_rsa'})

# 执行命令
result = conn.run('uname -a', hide=True)
print(result.stdout)
```

### 3.3 远程命令执行
```python
from fabric import Connection

conn = Connection('root@192.168.1.100')

# run() — 执行命令
result = conn.run('ls -la /var/log', hide=True)
print(result.stdout)

# sudo() — 以 root 执行
result = conn.sudo('apt update', hide=True)

# 检查命令是否成功
if result.exited == 0:
    print("命令执行成功")
else:
    print(f"命令失败: {result.stderr}")

# 多行脚本
conn.run('''
    cd /opt/app
    source venv/bin/activate
    python manage.py migrate
    python manage.py collectstatic --noinput
''', hide=True)
```

### 3.4 文件操作
```python
from fabric import Connection

conn = Connection('root@192.168.1.100')

# 上传文件
conn.put('/local/app.tar.gz', '/opt/deploy/app.tar.gz')

# 下载文件
conn.get('/var/log/syslog', '/tmp/remote_syslog.txt')

# 创建目录
conn.run('mkdir -p /opt/deploy/backup')

# 解压
conn.run('cd /opt/deploy && tar xzf app.tar.gz')

# 搜索文件
result = conn.run('find /var/log -name "*.log" -mtime -7', hide=True)
print(result.stdout)
```

### 3.5 Context Manager
```python
from fabric import Connection

# 使用 context manager 自动管理连接
with Connection('root@192.168.1.100') as conn:
    conn.run('echo "Connected!"')
    # 离开 with 块时自动关闭连接
```

---

## 四、批量服务器管理

### 4.1 多服务器并行执行
```python
from fabric import Connection
from concurrent.futures import ThreadPoolExecutor

servers = [
    'root@192.168.1.101',
    'root@192.168.1.102',
    'root@192.168.1.103',
    'root@192.168.1.104',
]

def check_server(host):
    """检查单台服务器状态"""
    try:
        conn = Connection(host, connect_kwargs={'timeout': 5})
        result = conn.run('uptime && free -h', hide=True, timeout=10)
        return {'host': host, 'status': 'ok', 'output': result.stdout}
    except Exception as e:
        return {'host': host, 'status': 'error', 'error': str(e)}

# 并行执行
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(check_server, servers))

for r in results:
    if r['status'] == 'ok':
        print(f"✅ {r['host']}:\n{r['output']}")
    else:
        print(f"❌ {r['host']}: {r['error']}")
```

### 4.2 批量部署
```python
from fabric import Connection

def deploy(host, app_path='/opt/myapp'):
    """部署应用到指定服务器"""
    conn = Connection(host)

    # 1. 上传代码
    print(f"📦 部署到 {host}...")
    conn.put('app.tar.gz', f'{app_path}/app.tar.gz')

    # 2. 解压备份
    conn.sudo(f'''
        cd {app_path}
        cp -r current backup_$(date +%Y%m%d)
        tar xzf app.tar.gz -C current
    ''')

    # 3. 安装依赖
    conn.sudo(f'''
        cd {app_path}/current
        source venv/bin/activate
        pip install -r requirements.txt
    ''')

    # 4. 重启服务
    conn.sudo('systemctl restart myapp')

    # 5. 验证
    result = conn.run('systemctl is-active myapp', hide=True)
    if result.stdout.strip() == 'active':
        print(f"✅ {host} 部署成功！")
    else:
        print(f"❌ {host} 部署失败！")
        conn.close()
        return False

    conn.close()
    return True

# 批量部署
servers = ['192.168.1.101', '192.168.1.102', '192.168.1.103']
for server in servers:
    deploy(f'root@{server}')
```

---

## 五、Fabric 项目配置

### 5.1 fabric.yml 配置文件
```yaml
# fabric.yml
host1:
  host: 192.168.1.101
  user: root
  connect_kwargs:
    key_filename: ~/.ssh/id_rsa

host2:
  host: 192.168.1.102
  user: deploy
  connect_kwargs:
    password: secret

web_servers:
  hosts:
    - host1
    - host2
```

### 5.2 使用配置文件
```python
from fabric import Connection
from yaml import safe_load

with open('fabric.yml') as f:
    config = safe_load(f)

# 连接单个服务器
conn = Connection.from_config(config['host1'])

# 批量连接
for name, cfg in config.items():
    if isinstance(cfg, dict) and 'host' in cfg:
        conn = Connection.from_config(cfg)
        result = conn.run('hostname', hide=True)
        print(f"{name}: {result.stdout.strip()}")
```

---

## 六、安全最佳实践

### 6.1 密钥管理
```python
# ✅ 推荐：使用 SSH Agent
from fabric import Connection

conn = Connection('root@server', connect_kwargs={
    'allow_agent': True,
    'look_for_keys': True
})

# ❌ 避免：硬编码密码
# conn = Connection('root@server', connect_kwargs={'password': 'hardcoded'})
```

### 6.2 连接超时
```python
conn = Connection('root@server', connect_kwargs={
    'timeout': 10,         # 连接超时 10 秒
    'banner_timeout': 30,  # SSH banner 超时
    'auth_timeout': 30,    # 认证超时
})
```

### 6.3 错误处理
```python
from fabric import Connection
from paramiko.ssh_exception import SSHException, AuthenticationException

try:
    conn = Connection('root@server')
    conn.run('ls /nonexistent', hide=True)
except AuthenticationException:
    print("认证失败：检查用户名/密码/密钥")
except SSHException as e:
    print(f"SSH 错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
finally:
    if 'conn' in locals():
        conn.close()
```

---

## 七、实战：服务器巡检工具

```python
#!/usr/bin/env python3
"""服务器巡检工具 — 使用 Paramiko 批量检查服务器状态"""

import paramiko
import json
from datetime import datetime

class ServerInspector:
    def __init__(self, servers):
        self.servers = servers
        self.results = []

    def inspect(self, host, port=22, username='root', password=None, key_file=None):
        """检查单台服务器"""
        result = {
            'host': host,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'metrics': {}
        }

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # 连接
            connect_kwargs = {'hostname': host, 'port': port, 'username': username, 'timeout': 10}
            if key_file:
                connect_kwargs['key_filename'] = key_file
            else:
                connect_kwargs['password'] = password
            client.connect(**connect_kwargs)

            # 收集信息
            commands = {
                'hostname': 'hostname',
                'uptime': 'uptime',
                'cpu_usage': "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'",
                'memory': "free -h | grep Mem | awk '{printf \"%s/%s (%.1f%%)\", $3, $2, $3/$2*100}'",
                'disk': "df -h / | tail -1 | awk '{printf \"%s/%s (%s)\", $3, $2, $5}'",
                'load_avg': "cat /proc/loadavg | awk '{print $1, $2, $3}'",
                'connections': "ss -s | grep 'estab' | awk '{print $4}'",
            }

            for metric, cmd in commands.items():
                stdin, stdout, stderr = client.exec_command(cmd, timeout=5)
                value = stdout.read().decode().strip()
                if value:
                    result['metrics'][metric] = value

            result['status'] = 'healthy'

        except paramiko.AuthenticationException:
            result['status'] = 'auth_error'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        finally:
            client.close()

        return result

    def run_inspection(self):
        """批量巡检"""
        print("🔍 开始服务器巡检...\n")
        for server in self.servers:
            print(f"  检查 {server['host']}...")
            result = self.inspect(**server)
            self.results.append(result)

            if result['status'] == 'healthy':
                metrics = result['metrics']
                print(f"    ✅ CPU: {metrics.get('cpu_usage', 'N/A')}%")
                print(f"    ✅ 内存: {metrics.get('memory', 'N/A')}")
                print(f"    ✅ 磁盘: {metrics.get('disk', 'N/A')}")
            else:
                print(f"    ❌ 状态: {result['status']}")
            print()

        return self.results

    def save_report(self, filename='inspection_report.json'):
        """保存巡检报告"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"📋 报告已保存: {filename}")


# 使用示例
if __name__ == '__main__':
    servers = [
        {'host': '192.168.1.101', 'username': 'root', 'password': 'pass1'},
        {'host': '192.168.1.102', 'username': 'root', 'key_file': '/root/.ssh/id_rsa'},
    ]

    inspector = ServerInspector(servers)
    results = inspector.run_inspection()
    inspector.save_report()
```

---

## 八、思考题

1. **Paramiko 的 SSH 通道机制是什么？** 它如何在同一连接上复用多个命令执行？
2. **Fabric 的 `run()` 和 `sudo()` 底层有什么区别？** sudo 是如何实现提权的？
3. **在批量部署中，如果某台服务器部署失败，你会如何设计回滚策略？**
4. **SSH 密钥认证比密码认证更安全，为什么？** 从密码学角度解释。
5. **如何设计一个断线重连机制？** 当网络不稳定时，如何保证批量任务的可靠性？
