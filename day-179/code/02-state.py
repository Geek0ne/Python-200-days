#!/usr/bin/env python3
"""Terraform 状态管理示例

展示 Terraform 状态如何工作以及状态管理的最佳实践。
"""

import json
import os
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class TerraformState:
    """Terraform 状态表示"""
    version: int = 0
    serial: int = 0
    modules: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """转换为 JSON 格式"""
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "TerraformState":
        """从 JSON 创建"""
        state_dict = json.loads(data)
        return cls(**state_dict)


@dataclass
class TerraformResourceState:
    """单个资源的状态"""
    address: str
    type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    nested: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """计算资源状态的哈希值"""
        content = f"{self.address}:{self.type}:{json.dumps(self.attributes, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class TerraformBackend:
    """Terraform 后端配置"""
    type: str = "local"
    config: Dict[str, Any] = field(default_factory=dict)

    def to_hcl(self) -> str:
        """转换为 HCL 后端配置"""
        lines = [f'backend "{self.type}" {{']
        if self.config:
            for k, v in self.config.items():
                if isinstance(v, str):
                    lines.append(f'  {k} = "{v}"')
                elif isinstance(v, bool):
                    lines.append(f'  {k} = {"true" if v else "false"}')
                elif isinstance(v, (int, float)):
                    lines.append(f'  {k} = {v}')
                else:
                    lines.append(f'  {k} = {v}')
        lines.append('}')
        return '\n'.join(lines)


@dataclass
class TerraformWorkspace:
    """Terraform 工作区"""
    name: str = "default"
    path: str = ""

    def workspace_file(self) -> str:
        """获取工作区文件路径"""
        return os.path.join(self.path, ".terraform", "workspace", self.name)


def generate_local_backend() -> str:
    """生成本地后端配置"""
    backend = TerraformBackend(
        type="local",
        config={"path": "./terraform.tfstate"}
    )
    return backend.to_hcl()


def generate_s3_backend() -> str:
    """生成 S3 远程后端配置"""
    backend = TerraformBackend(
        type="s3",
        config={
            "bucket": "my-terraform-state",
            "key": "prod/terraform.tfstate",
            "region": "us-west-2",
            "encrypt": "true"
        }
    )
    return backend.to_hcl()


def generate_workspace_switching() -> str:
    """生成工作区切换示例"""
    lines = ['# 切换工作区']
    lines.append('$ terraform workspace select production')
    lines.append('$ terraform workspace list')
    lines.append('$ terraform workspace new staging')
    return '\n'.join(lines)


def generate_state_migration() -> str:
    """生成状态迁移示例"""
    lines = ['# 状态从本地迁移到 S3']
    lines.append('# 步骤 1: 配置后端')
    lines.append('terraform {')
    lines.append('  backend "s3" {')
    lines.append('    bucket         = "my-terraform-state"')
    lines.append('    key            = "prod/terraform.tfstate"')
    lines.append('    region         = "us-west-2"')
    lines.append('    encrypt        = true')
    lines.append('    dynamodb_table = "terraform-state-lock"')
    lines.append('  }')
    lines.append('}')
    lines.append('# 步骤 2: 迁移状态')
    lines.append('$ terraform init -backend-config="bucket=my-terraform-state"')
    lines.append('$ terraform force-unlock <lock-id>')
    lines.append('$ terraform state pull')
    return '\n'.join(lines)


def main():
    print("=== Terraform 状态管理示例 ===\n")

    print("1. 本地后端配置:")
    print(generate_local_backend())
    print()

    print("2. S3 远程后端配置:")
    print(generate_s3_backend())
    print()

    print("3. 工作区切换:")
    print(generate_workspace_switching())
    print()

    print("4. 状态迁移:")
    print(generate_state_migration())
    print()

    # 创建示例状态
    state = TerraformState(
        version=4,
        serial=12345,
        modules={
            "root": {
                "version": 1,
                "id": "root-module",
                "resources": 5
            }
        }
    )

    print("5. 状态 JSON 表示:")
    print(state.to_json())
    print()

    # 创建资源状态
    resource_state = TerraformResourceState(
        address="aws_instance.web_server",
        type="aws_instance",
        attributes={
            "id": "i-1234567890abcdef0",
            "instance_type": "t2.micro",
            "public_ip": "54.123.45.67"
        }
    )

    print("6. 资源状态:")
    print(f"   地址: {resource_state.address}")
    print(f"   类型: {resource_state.type}")
    print(f"   ID: {resource_state.attributes.get('id')}")
    print(f"   类型: {resource_state.attributes.get('instance_type')}")
    print(f"   IP: {resource_state.attributes.get('public_ip')}")
    print(f"   哈希: {resource_state.compute_hash()}")
    print()

    print("=== 状态管理示例结束 ===")


if __name__ == "__main__":
    main()