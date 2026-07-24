# Day 082 — Fabric 与 Paramiko

## ✅ 今日完成清单

- [ ] 了解 SSH 连接原理（密钥交换、认证、通道）
- [ ] 掌握 Paramiko 密码/密钥认证连接
- [ ] 掌握 Paramiko SFTP 文件传输
- [ ] 掌握 Fabric run/sudo/put/get 操作
- [ ] 实现批量服务器并行执行
- [ ] 完成服务器巡检工具实战
- [ ] 完成下方练习题

---

## 📝 基础练习题

### 练习 1：SSH 连接封装
创建一个 SSH 连接封装类 `SSHClient`：
```python
class SSHClient:
    def __init__(self, host, user, password=None, key_file=None):
        ...
    def run(self, command):
        """执行命令，返回 (stdout, stderr, exit_code)"""
        ...
    def upload(self, local_path, remote_path):
        """上传文件"""
        ...
    def download(self, remote_path, local_path):
        """下载文件"""
        ...
    def __enter__(self):
        ...
    def __exit__(self, *args):
        ...
```
要求：
- 支持密码和密钥两种认证方式
- 自动处理连接异常
- 支持 context manager

### 练习 2：批量命令执行
编写脚本，在多台服务器上批量执行以下命令并收集结果：
```python
servers = ['192.168.1.101', '192.168.1.102', '192.168.1.103']
commands = ['uptime', 'free -h', 'df -h /']
```
要求：
- 并行执行以提高效率
- 输出格式化的结果表格
- 统计成功/失败数量

### 练习 3：文件同步工具
实现一个简单的文件同步函数：
```python
def sync_to_remote(local_dir, remote_dir, host, user, password):
    """将本地目录同步到远程服务器"""
    # 1. 上传目录中所有文件
    # 2. 跳过已存在的文件（可选）
    # 3. 报告同步结果
```

---

## 🚀 进阶挑战题

### 挑战 1：部署流水线
实现一个完整的部署脚本，包含：
1. 打包本地代码为 tar.gz
2. 上传到远程服务器
3. 备份旧版本
4. 解压新版本
5. 安装依赖
6. 重启服务
7. 验证部署结果
8. 失败时自动回滚

### 挑战 2：实时日志监控
使用 Paramiko 的 `invoke_shell()` 实现实时日志监控：
```python
def monitor_log(host, user, password, log_path):
    """实时监控远程日志文件"""
    # 类似 tail -f 的效果
    # 支持关键字高亮
    # 支持日志级别过滤
```

### 挑战 3：SSH 隧道与端口转发
学习并实现 SSH 本地端口转发：
```python
# 将本地 8080 端口转发到远程服务器的 80 端口
# 适用于访问内网服务
```
