#!/usr/bin/env python3
"""
Day 083 - 基础用法：远程执行与部署基础
演示打包、传输、解压、服务管理的完整流程
"""

import os
import tarfile
import time
from datetime import datetime

# ============ 1. 本地打包演示 ============
print("=" * 50)
print("1. 应用打包")
print("=" * 50)

def create_deploy_package(source_dir: str, version: str) -> str:
    """创建部署包"""
    os.makedirs('builds', exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"app-{version}-{timestamp}.tar.gz"
    filepath = os.path.join('builds', filename)

    # 需要排除的目录和文件
    exclude = {'__pycache__', '.git', 'venv', 'node_modules', '.env', '*.log'}

    with tarfile.open(filepath, 'w:gz') as tar:
        for root, dirs, files in os.walk(source_dir):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in exclude]
            for file in files:
                if file.endswith('.pyc') or file in exclude:
                    continue
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, source_dir)
                tar.add(full_path, arcname=arcname)

    size = os.path.getsize(filepath)
    print(f"✅ 打包完成: {filepath}")
    print(f"   大小: {size / 1024:.1f} KB")
    return filepath

# 演示打包当前目录
try:
    pkg = create_deploy_package('.', '1.0.0')
except Exception as e:
    print(f"⚠️  打包演示: {e}")

# ============ 2. 远程执行命令 ============
print("\n" + "=" * 50)
print("2. 远程执行命令（模拟）")
print("=" * 50)

# 模拟远程命令执行（实际使用时替换为 Paramiko）
def simulate_remote_exec(command: str) -> tuple:
    """模拟远程命令执行"""
    # 实际使用:
    # stdin, stdout, stderr = client.exec_command(command)
    # return stdout.read().decode(), stderr.read().decode(), stdout.channel.recv_exit_status()
    return f"[模拟输出] 执行: {command}", "", 0

commands = [
    'hostname',
    'uname -a',
    'free -h | grep Mem',
    'df -h / | tail -1',
    'systemctl is-active nginx',
]

for cmd in commands:
    output, error, code = simulate_remote_exec(cmd)
    status = "✅" if code == 0 else "❌"
    print(f"  {status} $ {cmd}")
    print(f"     → {output}")

# ============ 3. 服务管理 ============
print("\n" + "=" * 50)
print("3. 服务管理流程")
print("=" * 50)

class ServiceManager:
    """服务管理器"""

    def __init__(self, service_name: str):
        self.service_name = service_name

    def status(self) -> str:
        """获取服务状态"""
        # 实际: client.exec_command(f'systemctl is-active {self.service_name}')
        return 'active'

    def restart(self):
        """重启服务"""
        print(f"  🔄 重启 {self.service_name}...")
        # 实际: client.exec_command(f'systemctl restart {self.service_name}')
        time.sleep(1)  # 模拟重启时间
        print(f"  ✅ {self.service_name} 已重启")

    def stop(self):
        """停止服务"""
        print(f"  ⏹️  停止 {self.service_name}...")
        # 实际: client.exec_command(f'systemctl stop {self.service_name}')
        print(f"  ✅ {self.service_name} 已停止")

    def start(self):
        """启动服务"""
        print(f"  ▶️  启动 {self.service_name}...")
        # 实际: client.exec_command(f'systemctl start {self.service_name}')
        print(f"  ✅ {self.service_name} 已启动")

    def health_check(self) -> bool:
        """健康检查"""
        status = self.status()
        return status == 'active'

sm = ServiceManager('nginx')
print(f"  状态: {sm.status()}")
sm.restart()
print(f"  健康检查: {'✅ 通过' if sm.health_check() else '❌ 失败'}")

# ============ 4. 回滚机制 ============
print("\n" + "=" * 50)
print("4. 回滚机制演示")
print("=" * 50)

class RollbackManager:
    """回滚管理器"""

    def __init__(self, app_dir: str, backup_dir: str):
        self.app_dir = app_dir
        self.backup_dir = backup_dir

    def backup(self, version: str) -> str:
        """备份当前版本"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.backup_dir}/v{version}_{timestamp}"

        print(f"  📦 备份当前版本到: {backup_path}")
        # 实际:
        # client.exec_command(f"mkdir -p {self.backup_dir}")
        # client.exec_command(f"cp -r {self.app_dir}/current {backup_path}")
        return backup_path

    def rollback(self) -> bool:
        """回滚到最新备份"""
        print("  🔄 执行回滚...")

        # 查找最新备份
        # 实际: result = client.exec_command(f"ls -t {self.backup_dir}/v* | head -1")
        latest_backup = f"{self.backup_dir}/v1.0.0_20240101_120000"

        print(f"  📂 恢复自: {latest_backup}")
        # 实际:
        # client.exec_command(f"rm -rf {self.app_dir}/current")
        # client.exec_command(f"cp -r {latest_backup} {self.app_dir}/current")

        print("  ✅ 回滚完成")
        return True

rb = RollbackManager('/opt/myapp', '/opt/myapp/backups')
backup_path = rb.backup('1.0.0')
rb.rollback()

# ============ 5. 部署清单检查 ============
print("\n" + "=" * 50)
print("5. 部署前检查清单")
print("=" * 50)

def pre_deploy_check(checks: list) -> bool:
    """部署前检查"""
    all_passed = True
    for name, check_func in checks:
        try:
            result = check_func()
            status = "✅" if result else "❌"
            print(f"  {status} {name}")
            if not result:
                all_passed = False
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            all_passed = False
    return all_passed

# 定义检查项
checks = [
    ("磁盘空间 > 1GB", lambda: True),  # 模拟
    ("内存可用 > 512MB", lambda: True),
    ("目标目录可写", lambda: True),
    ("数据库连接正常", lambda: True),
    ("备份目录存在", lambda: True),
]

result = pre_deploy_check(checks)
print(f"\n  {'✅ 所有检查通过，可以部署' if result else '❌ 检查未通过，请修复后重试'}")

print("\n🎉 远程部署基础演示完成！")
