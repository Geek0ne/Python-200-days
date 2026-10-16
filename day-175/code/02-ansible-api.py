#!/usr/bin/env python3
"""
Python 调用 Ansible API 批量部署爬虫集群

本脚本演示如何用 Python 程序化地调用 Ansible：
1. 用 ansible-runner 启动 playbook
2. 实时打印执行过程
3. 收集统计结果

为什么用 ansible-runner 而不是 subprocess.run？
- ansible-runner 自动处理事件流、日志、结果对象
- 提供 status / rc / stats / events 等结构化结果
- 支持 json_mode 方便解析
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def run_ansible_playbook(
    playbook: str,
    inventory: str,
    extra_vars: dict = None,
    quiet: bool = False
) -> dict:
    """
    调用 Ansible 执行 Playbook

    Args:
        playbook: Playbook 文件路径
        inventory: Inventory 文件路径
        extra_vars: 额外变量字典
        quiet: 是否静默模式

    Returns:
        包含执行结果的字典
    """
    try:
        import ansible_runner
    except ImportError:
        print("❌ 请先安装: pip install ansible-runner")
        sys.exit(1)

    extra_vars = extra_vars or {}
    extra_vars["crawler_version"] = os.environ.get("CRAWLER_VERSION", "3.8.0")

    result = ansible_runner.run(
        playbook=playbook,
        inventory=inventory,
        extravars=extra_vars,
        quiet=quiet,
        json_mode=True,
        project_dir=str(Path(playbook).parent.absolute())
    )

    stats = {"ok": 0, "changed": 0, "failed": 0, "unreachable": 0, "skipped": 0}
    if result.stats:
        for host, host_stats in result.stats.items():
            for key in stats:
                stats[key] += host_stats.get(key, 0)

    return {
        "status": result.status,
        "rc": result.rc,
        "playbook": playbook,
        "hosts": list(result.hosts.keys()) if result.hosts else [],
        "stats": stats,
        "started_at": str(result.started_at),
        "finished_at": str(result.finished_at)
    }


def format_duration(started: str, finished: str) -> str:
    """计算并格式化执行时长"""
    try:
        s = datetime.fromisoformat(started)
        f = datetime.fromisoformat(finished)
        delta = (f - s).total_seconds()
        if delta < 60:
            return f"{delta:.1f} 秒"
        return f"{delta / 60:.1f} 分钟"
    except (ValueError, TypeError):
        return "未知"


def main():
    """主函数：执行批量部署"""
    print("=" * 60)
    print("🚀 Ansible 批量部署爬虫集群（Python API 控制）")
    print("=" * 60)

    current_dir = Path.cwd()
    playbook = current_dir / "code" / "deploy-crawler.yml"
    inventory = current_dir / "hosts.ini"

    if not playbook.exists():
        print(f"❌ Playbook 不存在: {playbook}")
        sys.exit(1)
    if not inventory.exists():
        print(f"⚠️  Inventory 不存在: {inventory}")
        print("   请先生成: python3 code/01-generate-inventory.py")
        sys.exit(1)

    print(f"📋 Playbook:  {playbook}")
    print(f"📦 Inventory: {inventory}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    result = run_ansible_playbook(
        playbook=str(playbook),
        inventory=str(inventory)
    )

    duration = format_duration(result["started_at"], result["finished_at"])

    report = [
        "",
        "=" * 60,
        "📊 部署完成报告",
        "=" * 60,
        f"Playbook:     {result['playbook']}",
        f"状态:         {result['status']}",
        f"返回码:       {result['rc']}",
        f"执行耗时:     {duration}",
        f"涉及主机:     {', '.join(result['hosts']) if result['hosts'] else '未指定'}",
        "",
        "📈 统计:",
        f"  ✅ ok:        {result['stats']['ok']}",
        f"  🔄 changed:   {result['stats']['changed']}",
        f"  ❌ failed:    {result['stats']['failed']}",
        f"  ⚠️ unreachable: {result['stats']['unreachable']}",
        f"  ⏭ skipped:   {result['stats']['skipped']}",
        "=" * 60
    ]
    print("\n".join(report))

    report_file = f"deploy_report_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n📄 详细结果已保存至: {report_file}")

    return 0 if result["status"] == "successful" else 1


if __name__ == "__main__":
    sys.exit(main())