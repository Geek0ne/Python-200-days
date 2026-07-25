#!/usr/bin/env python3
"""
01-basic-metrics.py
基础系统指标采集示例
演示如何使用 psutil 采集 CPU、内存、磁盘、网络指标
"""

import psutil
import time
from datetime import datetime


def collect_cpu_info():
    """采集 CPU 信息"""
    print("=" * 50)
    print("🖥️  CPU 信息")
    print("=" * 50)
    
    # CPU 使用率（阻塞1秒获取准确值）
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU 使用率: {cpu_percent}%")
    
    # CPU 核心数
    cpu_count = psutil.cpu_count()
    cpu_count_physical = psutil.cpu_count(logical=False)
    print(f"CPU 核心数: {cpu_count} (物理核心: {cpu_count_physical})")
    
    # CPU 频率
    freq = psutil.cpu_freq()
    if freq:
        print(f"CPU 频率: 当前 {freq.current:.0f}MHz, 最小 {freq.min:.0f}MHz, 最大 {freq.max:.0f}MHz")
    
    # 每个核心的使用率
    per_cpu = psutil.cpu_percent(interval=1, percpu=True)
    print(f"各核心使用率: {per_cpu}")
    
    return cpu_percent


def collect_memory_info():
    """采集内存信息"""
    print("\n" + "=" * 50)
    print("💾 内存信息")
    print("=" * 50)
    
    # 虚拟内存
    mem = psutil.virtual_memory()
    print(f"内存总量: {mem.total / (1024**3):.2f} GB")
    print(f"内存已用: {mem.used / (1024**3):.2f} GB")
    print(f"内存可用: {mem.available / (1024**3):.2f} GB")
    print(f"内存使用率: {mem.percent}%")
    
    # 交换内存
    swap = psutil.swap_memory()
    if swap.total > 0:
        print(f"\n交换内存总量: {swap.total / (1024**3):.2f} GB")
        print(f"交换内存已用: {swap.used / (1024**3):.2f} GB")
        print(f"交换内存使用率: {swap.percent}%")
    
    # 内存可视化
    bar_length = 30
    filled = int(bar_length * mem.percent / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\n内存使用: [{bar}] {mem.percent}%")
    
    return mem.percent


def collect_disk_info(path='/'):
    """采集磁盘信息"""
    print("\n" + "=" * 50)
    print("💿 磁盘信息")
    print("=" * 50)
    
    # 磁盘使用情况
    disk = psutil.disk_usage(path)
    print(f"磁盘总量: {disk.total / (1024**3):.2f} GB")
    print(f"磁盘已用: {disk.used / (1024**3):.2f} GB")
    print(f"磁盘可用: {disk.free / (1024**3):.2f} GB")
    print(f"磁盘使用率: {disk.percent}%")
    
    # 磁盘 I/O 统计
    io = psutil.disk_io_counters()
    if io:
        print(f"\n磁盘 I/O 统计:")
        print(f"  读取: {io.read_bytes / (1024**2):.2f} MB")
        print(f"  写入: {io.write_bytes / (1024**2):.2f} MB")
        print(f"  读取次数: {io.read_count}")
        print(f"  写入次数: {io.write_count}")
    
    # 磁盘可视化
    bar_length = 30
    filled = int(bar_length * disk.percent / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\n磁盘使用: [{bar}] {disk.percent}%")
    
    return disk.percent


def collect_network_info():
    """采集网络信息"""
    print("\n" + "=" * 50)
    print("🌐 网络信息")
    print("=" * 50)
    
    # 网络 I/O 统计
    net = psutil.net_io_counters()
    print(f"发送数据: {net.bytes_sent / (1024**2):.2f} MB")
    print(f"接收数据: {net.bytes_recv / (1024**2):.2f} MB")
    print(f"发送包数: {net.packets_sent}")
    print(f"接收包数: {net.packets_recv}")
    
    # 网络连接统计
    connections = psutil.net_connections()
    established = [c for c in connections if c.status == 'ESTABLISHED']
    listening = [c for c in connections if c.status == 'LISTEN']
    print(f"\n网络连接:")
    print(f"  已建立连接: {len(established)}")
    print(f"  监听端口: {len(listing)}")
    
    return net


def collect_process_info():
    """采集进程信息"""
    print("\n" + "=" * 50)
    print("⚙️  进程信息")
    print("=" * 50)
    
    # 进程总数
    process_count = len(psutil.pids())
    print(f"进程总数: {process_count}")
    
    # 获取 CPU 使用率最高的 5 个进程
    print("\nCPU 使用率最高的进程:")
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            if pinfo['cpu_percent'] is not None:
                processes.append(pinfo)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # 按 CPU 使用率排序
    processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
    
    for i, proc in enumerate(processes[:5]):
        print(f"  {i+1}. {proc['name']} (PID: {proc['pid']})")
        print(f"     CPU: {proc['cpu_percent']:.1f}%, 内存: {proc['memory_percent']:.1f}%")


def main():
    """主函数"""
    print("🔍 Python 系统监控 - 基础指标采集")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 采集各项指标
    cpu_usage = collect_cpu_info()
    mem_usage = collect_memory_info()
    disk_usage = collect_disk_info()
    collect_network_info()
    collect_process_info()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 系统健康状态总结")
    print("=" * 50)
    
    # 判断系统状态
    status = "🟢 健康"
    warnings = []
    
    if cpu_usage > 90:
        status = "🔴 危险"
        warnings.append("CPU 使用率过高")
    elif cpu_usage > 70:
        status = "🟡 警告"
        warnings.append("CPU 使用率偏高")
    
    if mem_usage > 90:
        status = "🔴 危险"
        warnings.append("内存使用率过高")
    elif mem_usage > 80:
        status = "🟡 警告"
        warnings.append("内存使用率偏高")
    
    if disk_usage > 90:
        status = "🔴 危险"
        warnings.append("磁盘空间不足")
    elif disk_usage > 80:
        status = "🟡 警告"
        warnings.append("磁盘空间偏少")
    
    print(f"系统状态: {status}")
    
    if warnings:
        print("⚠️  警告:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("✅ 所有指标正常")


if __name__ == "__main__":
    main()
