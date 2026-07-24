#!/usr/bin/env python3
"""
Day 082 - 基础用法：Paramiko SSH 连接与命令执行
演示密码认证、密钥认证、命令执行、文件传输
"""

import paramiko
import os

# ============ 1. 密码认证连接 ============
print("=" * 50)
print("1. 密码认证连接")
print("=" * 50)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    # 连接本地或远程服务器
    # 注意：这里用 localhost 演示，实际使用时替换为真实服务器
    client.connect(
        hostname='localhost',
        port=22,
        username='root',
        password='password',
        timeout=5
    )
    print("✅ 连接成功！")

    # 执行命令
    stdin, stdout, stderr = client.exec_command('uname -a')
    output = stdout.read().decode().strip()
    print(f"系统信息: {output}")

    # 获取退出码
    exit_code = stdout.channel.recv_exit_status()
    print(f"退出码: {exit_code}")

except paramiko.AuthenticationException:
    print("❌ 认证失败 — 检查用户名/密码")
except paramiko.SSHException as e:
    print(f"❌ SSH 连接失败: {e}")
except Exception as e:
    print(f"❌ 连接错误: {e}")
finally:
    client.close()
    print("连接已关闭\n")

# ============ 2. 密钥认证连接 ============
print("=" * 50)
print("2. 密钥认证连接（推荐）")
print("=" * 50)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    # 检查密钥文件是否存在
    key_path = os.path.expanduser('~/.ssh/id_rsa')
    if os.path.exists(key_path):
        private_key = paramiko.RSAKey.from_private_key_file(key_path)
        client.connect(
            hostname='localhost',
            username='root',
            pkey=private_key,
            timeout=5
        )
        print(f"✅ 使用密钥认证连接: {key_path}")

        stdin, stdout, stderr = client.exec_command('whoami')
        print(f"当前用户: {stdout.read().decode().strip()}")
    else:
        print(f"⚠️  密钥文件不存在: {key_path}")
        print("  请先生成密钥: ssh-keygen -t rsa")

except Exception as e:
    print(f"❌ 连接失败: {e}")
finally:
    client.close()
    print()

# ============ 3. 多命令执行 ============
print("=" * 50)
print("3. 多命令执行")
print("=" * 50)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('localhost', username='root', password='password', timeout=5)

    commands = [
        'hostname',
        'date',
        'uptime',
        'df -h / | tail -1',
        'free -h | grep Mem',
    ]

    for cmd in commands:
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode().strip()
        print(f"  $ {cmd}")
        print(f"    → {output}")

except Exception as e:
    print(f"❌ 错误: {e}")
finally:
    client.close()
    print()

# ============ 4. SFTP 文件传输 ============
print("=" * 50)
print("4. SFTP 文件传输")
print("=" * 50)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect('localhost', username='root', password='password', timeout=5)
    sftp = client.open_sftp()

    # 创建测试文件
    test_content = "Hello from Paramiko SFTP!\n"
    with open('/tmp/test_upload.txt', 'w') as f:
        f.write(test_content)
    print("📁 本地文件已创建: /tmp/test_upload.txt")

    # 上传文件
    sftp.put('/tmp/test_upload.txt', '/tmp/uploaded.txt')
    print("⬆️  上传完成: /tmp/uploaded.txt")

    # 下载文件
    sftp.get('/tmp/uploaded.txt', '/tmp/downloaded.txt')
    print("⬇️  下载完成: /tmp/downloaded.txt")

    # 验证
    with open('/tmp/downloaded.txt') as f:
        print(f"📄 文件内容: {f.read().strip()}")

    # 列出目录
    files = sftp.listdir('/tmp/')
    print(f"📂 /tmp/ 目录文件: {len(files)} 个")

    sftp.close()

except Exception as e:
    print(f"❌ 错误: {e}")
finally:
    client.close()
    print()

# ============ 5. 批量执行 ============
print("=" * 50)
print("5. 批量执行示例")
print("=" * 50)

# 模拟多服务器
servers = [
    {'host': 'localhost', 'user': 'root', 'password': 'password'},
]

for server in servers:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(server['host'], username=server['user'],
                       password=server['password'], timeout=5)
        stdin, stdout, stderr = client.exec_command('hostname')
        hostname = stdout.read().decode().strip()
        print(f"  ✅ {server['host']} → {hostname}")
    except Exception as e:
        print(f"  ❌ {server['host']}: {e}")
    finally:
        client.close()

print("\n🎉 Paramiko 基础用法演示完成！")
