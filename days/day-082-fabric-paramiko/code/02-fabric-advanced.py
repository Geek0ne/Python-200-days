#!/usr/bin/env python3
"""
Day 082 - 进阶用法：Fabric 批量运维与错误处理
演示 Fabric 高级特性：并行执行、错误处理、连接池
"""

from fabric import Connection
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ============ 1. 基础 Fabric 连接 ============
print("=" * 50)
print("1. Fabric 基础连接与命令执行")
print("=" * 50)

try:
    # 连接单台服务器
    conn = Connection('root@localhost', connect_kwargs={'password': 'password'})

    # run() 执行命令
    result = conn.run('uname -a', hide=True)
    print(f"系统信息: {result.stdout.strip()}")

    # sudo() 以 root 执行
    result = conn.sudo('whoami', hide=True)
    print(f"当前用户: {result.stdout.strip()}")

    # 检查退出码
    result = conn.run('ls /nonexistent_path', hide=True, warn=True)
    print(f"命令退出码: {result.exited}")
    if result.failed:
        print(f"  命令失败（预期行为）")

    conn.close()

except Exception as e:
    print(f"⚠️  连接失败: {e}")
    print("  （Fabric 需要可连接的 SSH 服务器）")

# ============ 2. Context Manager ============
print("\n" + "=" * 50)
print("2. Context Manager 自动管理连接")
print("=" * 50)

try:
    with Connection('root@localhost', connect_kwargs={'password': 'password'}) as conn:
        conn.run('echo "✅ Context Manager 工作正常"')
        # 离开 with 块时自动关闭连接
    print("  连接已自动关闭")

except Exception as e:
    print(f"⚠️  {e}")

# ============ 3. 批量并行执行 ============
print("\n" + "=" * 50)
print("3. 批量并行执行（ThreadPoolExecutor）")
print("=" * 50)

def check_server(host, user='root', password='password'):
    """检查单台服务器状态"""
    try:
        conn = Connection(f'{user}@{host}',
                         connect_kwargs={'password': password, 'timeout': 5})
        result = conn.run('uptime && free -h | grep Mem', hide=True, timeout=10)
        conn.close()
        return {
            'host': host,
            'status': 'ok',
            'output': result.stdout.strip()
        }
    except Exception as e:
        return {
            'host': host,
            'status': 'error',
            'error': str(e)
        }

# 模拟多服务器（实际使用时替换为真实 IP）
servers = ['localhost']  # 可扩展为 ['192.168.1.101', '192.168.1.102', ...]

print("  🔄 并行检查服务器...")
start = time.time()

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(check_server, s): s for s in servers}
    for future in as_completed(futures):
        result = future.result()
        if result['status'] == 'ok':
            print(f"  ✅ {result['host']}:")
            for line in result['output'].split('\n'):
                print(f"     {line}")
        else:
            print(f"  ❌ {result['host']}: {result['error']}")

elapsed = time.time() - start
print(f"  ⏱️  耗时: {elapsed:.2f}s")

# ============ 4. 高级错误处理 ============
print("\n" + "=" * 50)
print("4. 高级错误处理模式")
print("=" * 50)

from fabric.exceptions import CommandTimeout

def safe_execute(host, command, user='root', password='password'):
    """安全执行命令，带完整错误处理"""
    conn = None
    try:
        conn = Connection(f'{user}@{host}',
                         connect_kwargs={'password': password, 'timeout': 5})
        result = conn.run(command, hide=True, timeout=10)
        return True, result.stdout.strip()

    except CommandTimeout:
        return False, "命令执行超时"
    except Exception as e:
        return False, f"执行错误: {type(e).__name__}: {e}"
    finally:
        if conn:
            conn.close()

# 测试各种情况
test_commands = [
    ('echo "成功"', '应该成功'),
    ('sleep 100', '应该超时'),
    ('exit 1', '应该返回非零退出码'),
]

for cmd, desc in test_commands:
    success, output = safe_execute('localhost', cmd)
    status = "✅" if success else "❌"
    print(f"  {status} [{desc}] {cmd[:40]}...")
    if not success:
        print(f"     → {output}")

# ============ 5. 避坑指南 ============
print("\n" + "=" * 50)
print("5. 常见避坑")
print("=" * 50)

# 坑1: hide 参数
print("  📌 坑1: hide 参数控制输出")
print("     hide=True  → 不打印命令输出到终端")
print("     hide='out' → 只隐藏 stdout")
print("     hide='err' → 只隐藏 stderr")
print("     默认: 打印所有输出")

# 坑2: warn 参数
print("\n  📌 坑2: warn 参数控制失败行为")
print("     warn=True  → 命令失败不抛异常，检查 result.failed")
print("     默认: 命令失败抛异常")

# 坑3: sudo 密码
print("\n  📌 坑3: sudo 需要密码时")
print("     conn.sudo('cmd', hide=True)  # 如果 sudoers 配置了 NOPASSWD")
print("     conn.sudo('cmd', pty=True)   # 交互式输入密码")

print("\n🎉 Fabric 进阶用法演示完成！")
