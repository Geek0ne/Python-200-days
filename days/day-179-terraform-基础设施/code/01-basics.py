#!/usr/bin/env python3
"""Terraform 基础概念示例

This script demonstrates core Terraform concepts using Python representations.
Terraform uses HCL (HashiCorp Configuration Language) to define infrastructure.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class TerraformResource:
    """Terraform 资源数据类"""
    resource_type: str
    resource_name: str
    attributes: Dict[str, str]
    depends_on: List[str] = None
    lifecycle: Dict = None

    def to_hcl(self) -> str:
        """转换为 HCL 格式"""
        lines = [f'  "{self.resource_name}" {{']
        for key, value in self.attributes.items():
            lines.append(f'    {key} = "{value}"')
        if self.depends_on:
            lines.append(f'    depends_on = {self.depends_on}')
        if self.lifecycle:
            for k, v in self.lifecycle.items():
                lines.append(f'    lifecycle {{ {k} = {v} }}')
        lines.append('  }')
        return '\n'.join(lines)


@dataclass
class TerraformProvider:
    """Terraform 提供商配置"""
    name: str
    region: str
    features: Dict = None

    def to_hcl(self) -> str:
        """转换为 HCL 提供商配置"""
        lines = [f'provider "{self.name}" {{']
        lines.append(f'  region = "{self.region}"')
        if self.features:
            for k, v in self.features.items():
                lines.append(f'  {k} = {v}')
        lines.append('}')
        return '\n'.join(lines)


@dataclass
class TerraformModule:
    """Terraform 模块"""
    source: str
    name: str
    inputs: Dict = None
    outputs: Dict = None

    def to_hcl(self) -> str:
        """转换为模块声明"""
        lines = [f'module "{self.name}" {{']
        lines.append(f'  source = "{self.source}"')
        if self.inputs:
            for k, v in self.inputs.items():
                if isinstance(v, str):
                    lines.append(f'  {k} = "{v}"')
                elif isinstance(v, bool):
                    lines.append(f'  {k} = {"true" if v else "false"}')
                elif isinstance(v, (int, float)):
                    lines.append(f'  {k} = {v}')
                else:
                    lines.append(f'  {k} = {v}')
        if self.outputs:
            lines.append('  output {')
            for k, v in self.outputs.items():
                lines.append(f'    {k} = {v}')
            lines.append('  }')
        lines.append('}')
        return '\n'.join(lines)


def generate_provider_config() -> str:
    """生成 AWS 提供商配置"""
    provider = TerraformProvider(
        name="aws",
        region="us-west-2",
        features={"profile": "default", "region": "us-west-2"}
    )
    return provider.to_hcl()


def generate_vpc_resource() -> str:
    """生成 VPC 资源配置"""
    vpc = TerraformResource(
        resource_type="aws_vpc",
        resource_name="main",
        attributes={
            "cidr_block": "10.0.0.0/16",
            "enable_dns_hostnames": "true",
            "enable_dns_support": "true"
        },
        tags={"Name": "example-vpc", "Environment": "production"}
    )
    return vpc.to_hcl()


def generate_ec2_resource() -> str:
    """生成 EC2 实例资源配置"""
    instance = TerraformResource(
        resource_type="aws_instance",
        resource_name="web_server",
        attributes={
            "ami": "ami-0c55b159cbfafe1f0",
            "instance_type": "t2.micro",
            "key_name": "my-key-pair"
        },
        depends_on=[],
        lifecycle={
            "create_before_destroy": "true",
            "prevent_destroy": "false"
        }
    )
    return instance.to_hcl()


def generate_security_group() -> str:
    """生成安全组资源配置"""
    sg = TerraformResource(
        resource_type="aws_security_group",
        resource_name="allow_ssh",
        attributes={
            "name": "allow_ssh",
            "description": "Allow SSH inbound traffic",
            "vpc_id": "vpc-12345678"
        }
    )
    # Add ingress/egress blocks inline
    hcl = sg.to_hcl()
    hcl += '\n  ingress {\n    description = "SSH from anywhere"\n    from_port = 22\n    to_port = 22\n    protocol = "tcp"\n    cidr_blocks = ["0.0.0.0/0"]\n  }\n  egress {\n    from_port = 0\n    to_port = 0\n    protocol = "-1"\n    cidr_blocks = ["0.0.0.0/0"]\n  }'
    return hcl


def generate_outputs() -> str:
    """生成 outputs 部分"""
    outputs = TerraformModule(
        name="example",
        source="./modules/network",
        inputs={"vpc_cidr": "10.0.0.0/16"},
        outputs={
            "vpc_id": "value = aws_vpc.main.id",
            "public_subnet_ids": "value = aws_subnet.public[*].id"
        }
    )
    return outputs.to_hcl()


if __name__ == "__main__":
    print("=== Terraform HCL 配置生成示例 ===\n")

    print("1. 提供商配置:")
    print(generate_provider_config())
    print()

    print("2. VPC 资源:")
    print(generate_vpc_resource())
    print()

    print("3. 安全组资源:")
    print(generate_security_group())
    print()

    print("4. EC2 实例资源:")
    print(generate_ec2_resource())
    print()

    print("5. 模块声明:")
    print(generate_outputs())
    print()

    print("=== 示例结束 ===")