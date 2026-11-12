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

**参考答案**

核心概念：**一条 SSH 连接 = 一个 TCP 连接 + 一个加密的"传输层"（Transport），传输层之上可以再开多条逻辑"通道"（Channel）。**

- **传输层（Transport）**：完成 TCP 握手、SSH 协议协商、密钥交换、认证后建立，整条连接只此一份，负责加密/解密和收发数据包。
- **通道（Channel）**：传输层上的独立双向数据流，每条有自己的编号、流控窗口和 stdin/stdout/stderr。SSH 协议靠"通道编号"区分不同数据流，于是**多条通道复用同一条 TCP 连接和同一套加密会话**，这就是"多路复用"。

Paramiko 里的具体体现（已核对源码）：

- 每调用一次 `client.exec_command(cmd)`，内部都会 `transport.open_session()` → `open_channel("session")` **新开一条 session 通道**来跑这条命令。所以执行 10 条命令 = 同一连接上开 10 条通道，**不必重新建 TCP、重新认证**。
- `client.open_sftp()` 开的是一条跑 SFTP 子系统的通道；`client.invoke_shell()` 开的是一条带伪终端的交互 shell 通道；端口转发则用 `direct-tcpip` 等类型的通道。

```text
一条 TCP 连接(22端口) + 一个加密传输层 Transport
        │
        ├── Channel 0 (session): exec_command('uname -a')
        ├── Channel 1 (session): exec_command('df -h')
        ├── Channel 2 (session): open_sftp() 文件传输
        └── Channel 3 (session): invoke_shell() 交互终端
   所有通道复用同一连接，按编号区分，各自独立 stdin/stdout/stderr
```

好处：省去反复握手/认证的开销；多命令可并行；一条通道阻塞不影响其它通道。

💡 提示：通道有流控窗口，若长时间不读某通道的 stdout，窗口写满后远端命令会被阻塞——所以大输出要及时读取（或用 `makefile` 流式读），别等命令结束才一次性 read。

2. **Fabric 的 `run()` 和 `sudo()` 底层有什么区别？** sudo 是如何实现提权的？

**参考答案**

两者**最终走的是同一个"远程命令执行器"**（通过 Paramiko 开 session 通道执行命令字符串），区别只在于"执行什么命令串"和"要不要自动应答密码"。

- `run('cmd')`：直接以**当前登录用户**的权限执行 `cmd`。
- `sudo('cmd')`：Fabric/Invoke 先把命令包装成（已核对 invoke 源码）：

  ```text
  sudo -S -p '[sudo] password: ' cmd
  ```

  - `-S`：让 sudo 从 **stdin** 读密码（而不是终端），这样程序才能自动喂密码；
  - `-p '[sudo] password: '`：显式指定提示语，方便自动应答器精确匹配；
  - 若传了 `user=`，还会加 `-H -u <user>`（以指定用户身份执行并设置正确的 `$HOME`）。

  然后挂一个**自动应答器**（`FailingResponder`）：盯着输出流，一旦出现上面那句提示，就把配置好的 sudo 密码 + 换行写进 stdin；若看到 `Sorry, try again.`（密码错）则抛 `AuthFailure`。

**提权到底是谁干的？**

- 真正提权的是**远端服务器上的 `sudo` 程序**，不是 Fabric/Paramiko。`sudo` 是一个 **setuid root** 程序：它先检查调用者是否在 `/etc/sudoers` 授权列表里、密码是否正确，通过后以 root（或目标用户）权限 fork 子进程执行命令。
- Fabric 只是"帮你敲 sudo 命令并自动填密码"，**权限边界仍由服务器的 sudoers 控制**——没授权的用户，Fabric 也提不了权。

💡 提示：若服务器配了免密 sudo（`NOPASSWD`），`sudo()` 看不到密码提示就直接执行；如果你想手动输密码，应改用 `run('sudo cmd')`，否则自动应答器反而会碍事。

3. **在批量部署中，如果某台服务器部署失败，你会如何设计回滚策略？**

**参考答案**

设计要点（核心是"可秒级回退 + 集群版本一致"）：

1. **版本化发布 + 指针切换**：每次部署放进独立目录 `releases/vN`，用软链 `current` 指向生效版本。部署 = 上传新版本 + 切指针；回滚 = 把指针指回旧版本，**无需重新上传，秒级完成**。
2. **先健康检查再切换**：新版本上传后先跑冒烟测试/健康检查，**通过才切 `current`**；不通过就不切，这台机器自然停在旧版本。
3. **批量一致性**：任一台失败，就把**已切换的机器也回滚**到旧版本，避免集群新旧混跑（灰度/金丝雀发布除外，那是有意保留部分新版本）。
4. **保留历史 + 数据备份**：保留最近 N 个 release 以便回退到任意近期版本；数据库迁移、配置变更要单独备份/准备 down 脚本（代码指针切回去不代表数据能自动回退）。
5. **记录与告警**：每次部署/回滚写日志，失败及时通知。

小例子（已验证，内存模拟"上传→健康检查→切指针→失败回滚"）：

```python
class Server:
    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail
        self.releases = {"v1": "旧版本代码"}  # 历史版本仓库
        self.current = "v1"                   # 当前生效版本（相当于 current 软链）
        self.backup = None

    def deploy(self, new_version):
        self.backup = self.current            # 1. 记录旧版本，便于回滚
        self.releases[new_version] = f"{new_version} 代码"  # 2. 上传新版本
        if self.fail:                         # 3. 先对新版本做健康检查
            raise RuntimeError(f"{self.name} 新版本健康检查失败")
        self.current = new_version            # 4. 检查通过才原子切换指针
        return True

    def rollback(self):
        if self.backup:
            self.current = self.backup
            return True
        return False

servers = [Server("web-1"), Server("web-2", fail=True), Server("web-3")]
deployed = []
try:
    for s in servers:
        s.deploy("v2")
        deployed.append(s)
        print(f"✅ {s.name} 切换到 v2")
except RuntimeError as e:
    print(f"❌ {e}（该服务器未切换，仍在旧版本）")
    for s in deployed:                        # 回滚已切换的，保证集群版本一致
        s.rollback()
        print(f"↩️  {s.name} 回滚到 {s.current}")
print("最终各服务器版本:", {s.name: s.current for s in servers})
```

预期输出：

```
✅ web-1 切换到 v2
❌ web-2 新版本健康检查失败（该服务器未切换，仍在旧版本）
↩️  web-1 回滚到 v1
最终各服务器版本: {'web-1': 'v1', 'web-2': 'v1', 'web-3': 'v1'}
```

web-2 健康检查失败、指针没切（停在 v1），已切换的 web-1 被回滚到 v1，web-3 还没轮到——最终全集群一致回到 v1。

💡 提示：真实项目用 `ln -sfn releases/vN current` 做原子切换；数据库这类有状态服务要单独设计回滚（备份恢复或 down 迁移），不能只切代码指针。

4. **SSH 密钥认证比密码认证更安全，为什么？** 从密码学角度解释。

**参考答案**

**密码认证的弱点**：客户端把密码（一个"共享秘密"）经加密通道发给服务器比对。风险在于——服务器端能看到明文密码（服务器被攻破即泄露）；弱密码可被暴力/字典攻击；人们常多站复用同一密码，一处泄露处处遭殃。

**密钥认证基于"非对称加密 + 挑战-应答（challenge-response）"**：

- 密钥对分**私钥**（只留在客户端，**永不传输**）和**公钥**（放进服务器的 `authorized_keys`）。
- 登录时服务器下发一个**随机挑战**（与本次会话绑定的随机数）；客户端用**私钥对挑战签名**，把签名发回；服务器用**公钥验签**。
- 密码学保证：只有私钥持有者能造出通过公钥验证的签名；**从公钥反推私钥在计算上不可行**（RSA 依赖大整数分解难题，Ed25519 依赖椭圆曲线离散对数难题）。

由此带来的安全优势：

1. **私钥不出本机、网络上不传任何可复用的秘密**——窃听者拿不到能冒充你的东西。
2. **挑战每次随机**，旧签名无法重放（replay）。
3. **服务器被攻破也只泄露公钥**，攻击者无法据此冒充客户端登录其它机器。
4. 私钥还能再用 passphrase 加密存储（静态加密），配合 ssh-agent 兼顾安全与便利。

小例子（已验证，用 paramiko 在内存里做 RSA 挑战-应答，无需真实服务器）：

```python
import paramiko
import os

# 客户端生成密钥对；私钥永远留在客户端
private_key = paramiko.RSAKey.generate(2048)

# 服务端只拿到公钥（asbytes() 导出公钥 blob，对应 authorized_keys 里那行）
public_key = paramiko.RSAKey(data=private_key.asbytes())
print("服务端只有公钥，能签名吗:", public_key.can_sign())

# 1) 服务端下发随机挑战（与本次会话绑定的随机数）
challenge = os.urandom(32)
# 2) 客户端用私钥对挑战签名（私钥不出本机）
sig = private_key.sign_ssh_data(challenge)
# 3) 服务端用公钥验签（Message 读完会移动指针，验签前先 rewind 复位）
sig.rewind()
print("公钥验签通过:", public_key.verify_ssh_sig(challenge, sig))
# 篡改挑战后验签应失败
sig.rewind()
print("篡改挑战后验签:", public_key.verify_ssh_sig(os.urandom(32), sig))
```

预期输出：

```
服务端只有公钥，能签名吗: False
公钥验签通过: True
篡改挑战后验签: False
```

服务端对象只有公钥（`can_sign=False`，无法签名），却能验证客户端私钥的签名（`True`）；挑战被篡改后验签失败（`False`）——直观演示了"私钥签名、公钥验签、私钥从不传输"。

💡 提示：优先用 Ed25519（密钥短、速度快、安全性高）；RSA 至少 2048 位（建议 3072+）。私钥务必设 passphrase 并收紧文件权限（`chmod 600`）。

5. **如何设计一个断线重连机制？** 当网络不稳定时，如何保证批量任务的可靠性？

**参考答案**

设计要点：

1. **检测断线**：捕获网络异常（`ConnectionError`、`SSHException`、`socket.timeout` 等）；也可用心跳/keepalive（Paramiko 的 `transport.set_keepalive(间隔)`）尽早发现死连接。
2. **指数退避 + 随机抖动**：失败后先等 `base_delay`，每次翻倍（0.1→0.2→0.4…），再叠加随机抖动。退避避免猛捶尚未恢复的服务器；抖动防止大量客户端同一时刻重连造成"惊群"。
3. **上限 + 熔断**：设最大重试次数和最大延迟，超过就放弃并告警（或熔断快速失败），不要无限阻塞。
4. **幂等 + 断点续传**：批量任务记录"哪些机器/步骤已完成"，重连后只补做未完成部分；操作设计成幂等（重复执行无副作用），重试才安全。
5. **重建连接而非复用**：断线后旧连接/通道通常已失效，要新建 `Connection` 重新认证，别在死 socket 上继续发命令。

小例子（已验证，stdlib 重试装饰器 + 模拟不稳定连接）：

```python
import time
import random
import functools

def retry(max_attempts=4, base_delay=0.1, backoff=2.0, exceptions=(ConnectionError,)):
    """断线重连装饰器：指数退避 + 随机抖动"""
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        print(f"  第 {attempt} 次仍失败，放弃: {e}")
                        raise
                    # 加随机抖动，避免大量客户端同一时刻重连（惊群）
                    sleep = delay + random.uniform(0, delay)
                    print(f"  第 {attempt} 次失败({e})，{sleep:.2f}s 后重连")
                    time.sleep(sleep)
                    delay *= backoff
        return wrapper
    return deco

random.seed(42)
state = {"n": 0}

@retry(max_attempts=4, base_delay=0.05)
def flaky_task():
    state["n"] += 1
    if state["n"] < 3:            # 前两次断线，第三次成功
        raise ConnectionError("网络断开")
    return "任务完成"

print("结果:", flaky_task())
print("总尝试次数:", state["n"])
```

预期输出（抖动值因随机种子而异，此处固定 seed=42）：

```
  第 1 次失败(网络断开)，0.08s 后重连
  第 2 次失败(网络断开)，0.10s 后重连
结果: 任务完成
总尝试次数: 3
```

前两次"断线"，装饰器按退避 0.08s、0.10s 自动重连，第三次成功——整个过程对调用者透明。

💡 提示：真实 Fabric 场景把"建连接 + 执行命令"整体放进被重试的函数里，每次重试都新建 `Connection`；批量任务再配合"已完成清单"实现断点续传，避免重复部署已成功的机器。
