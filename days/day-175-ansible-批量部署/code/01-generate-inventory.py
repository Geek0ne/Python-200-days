#!/usr/bin/env python3
"""
动态生成 Ansible Inventory
根据爬虫集群规模自动生成主机清单

真实场景：当你要部署 100 台爬虫节点时，手动写 100 行 inventory
几乎是不可能的。我们用一个 Python 脚本根据集群规模动态生成。
"""

import os
from pathlib import Path


def generate_inventory(num_nodes: int, base_ip: str = "10.0.1") -> str:
    """
    生成爬虫集群的 Inventory（INI 格式）

    Args:
        num_nodes: 爬虫节点数量
        base_ip: 基础 IP 段（如 10.0.1）

    Returns:
        完整的 INI 格式 inventory 内容
    """
    lines = [
        "# Auto-generated Ansible Inventory",
        "# 由 generate_inventory.py 生成 — 请勿手动编辑",
        "",
        "[crawler_nodes]",
    ]

    for i in range(1, num_nodes + 1):
        host = f"crawler-{i}"
        ip = f"{base_ip}.{i + 10}"
        role = "spider" if i <= num_nodes // 2 else "parser"
        lines.append(f"{host} ansible_host={ip} node_role={role}")

    lines.append("")
    lines.append("[crawler_nodes:vars]")
    lines.append("ansible_user=root")
    lines.append("ansible_ssh_private_key_file=~/.ssh/id_rsa")
    lines.append("python_interpreter=/usr/bin/python3")
    lines.append("redis_host=10.0.1.100")
    lines.append("redis_port=6379")
    lines.append("project_dir=/opt/crawler")
    lines.append("log_dir=/var/log/crawler")
    lines.append("")
    lines.append("[all:vars]")
    lines.append("ansible_python_interpreter=/usr/bin/python3")

    return "\n".join(lines) + "\n"


def save_inventory(content: str, path: str = "hosts.ini"):
    """保存 Inventory 到文件，并保证 UTF-8 编码"""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with path_obj.open("w", encoding="utf-8") as f:
        f.write(content)


def main():
    """主函数：生成 5 节点爬虫集群的 Inventory"""
    print("=" * 50)
    print("📦 Ansible Inventory 生成器（爬虫集群版）")
    print("=" * 50)

    num_nodes = 5  # 本示例生成 5 台节点，可按需修改
    content = generate_inventory(num_nodes)

    save_inventory(content)
    print(f"✅ Inventory 已生成至 hosts.ini")
    print(f"   节点数量: {num_nodes}")

    print("\n📊 集群拓扑:")
    for i in range(1, num_nodes + 1):
        host = f"crawler-{i}"
        ip = f"10.0.1.{i + 10}"
        role = "spider" if i <= num_nodes // 2 else "parser"
        print(f"   {host:12} ({ip:12}) 角色={role}")

    print("\n📝 hosts.ini 预览:")
    print("-" * 40)
    print(content)


if __name__ == "__main__":
    main()