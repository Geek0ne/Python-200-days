#!/usr/bin/env python3
"""Terraform 模块示例

展示 Terraform 模块的创建、使用和最佳实践。
模块是 Terraform 中的可重用组件。
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class TerraformModuleDef:
    """Terraform 模块定义"""
    name: str
    source: str
    version: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_module_block(self) -> str:
        """转换为 Terraform 模块块"""
        lines = [f'module "{self.name}" {{']
        lines.append(f'  source = "{self.source}"')
        if self.version:
            lines.append(f'  version = "{self.version}"')
        if self.inputs:
            lines.append('  # 输入变量')
            for k, v in self.inputs.items():
                if isinstance(v, str):
                    lines.append(f'  {k} = "{v}"')
                elif isinstance(v, bool):
                    lines.append(f'  {k} = {"true" if v else "false"}')
                elif isinstance(v, (int, float)):
                    lines.append(f'  {k} = {v}')
                elif isinstance(v, list):
                    if v and isinstance(v[0], str):
                        lines.append(f'  {k} = [{", ".join(f"\"{x}\"" for x in v)}]')
                    else:
                        lines.append(f'  {k} = {v}')
                else:
                    lines.append(f'  {k} = {v}')
        if self.outputs:
            lines.append('  # 输出变量')
            for k, v in self.outputs.items():
                lines.append(f'  output "{k}" {{')
                if isinstance(v, str):
                    lines.append(f'    value = "{v}"')
                elif isinstance(v, (int, float)):
                    lines.append(f'    value = {v}')
                else:
                    lines.append(f'    value = {v}')
                lines.append('  }')
        lines.append('}')
        return '\n'.join(lines)


@dataclass
class VPCModule:
    """VPC 模块"""
    name: str = "vpc"
    cidr_block: str = "10.0.0.0/16"
    az_count: int = 2
    enable_dns: bool = True

    def module_source(self) -> str:
        """获取模块源路径"""
        return f"./modules/vpc/{self.name}"

    def module_block(self) -> str:
        """生成模块调用块"""
        inputs = {
            "name": self.name,
            "cidr_block": self.cidr_block,
            "az_count": self.az_count,
            "enable_dns": self.enable_dns
        }
        lines = [f'module "{self.name}" {{']
        lines.append(f'  source = "./modules/vpc/{self.name}"')
        lines.append('  # VPC 配置')
        for k, v in inputs.items():
            if isinstance(v, str):
                lines.append(f'  {k} = "{v}"')
            elif isinstance(v, bool):
                lines.append(f'  {k} = {"true" if v else "false"}')
            elif isinstance(v, int):
                lines.append(f'  {k} = {v}')
        lines.append('}')
        return '\n'.join(lines)


@dataclass
class EC2Module:
    """EC2 实例模块"""
    name: str = "web_server"
    instance_type: str = "t2.micro"
    ami: str = "ami-0c55b159cbfafe1f0"
    subnet_ids: List[str] = field(default_factory=list)

    def module_block(self) -> str:
        """生成 EC2 模块调用块"""
        inputs = {
            "name": self.name,
            "instance_type": self.instance_type,
            "ami": self.ami,
            "subnet_ids": self.subnet_ids
        }
        lines = [f'module "{self.name}" {{')
        lines.append(f'  source = "./modules/ec2/{self.name}"')
        lines.append('  # EC2 实例配置')
        for k, v in inputs.items():
            if isinstance(v, str):
                lines.append(f'  {k} = "{v}"')
            elif isinstance(v, (int, float)):
                lines.append(f'  {k} = {v}')
            elif isinstance(v, list):
                if v:
                    lines.append(f'  {k} = [{", ".join(repr(x) for x in v)}]')
                else:
                    lines.append(f'  {k} = []')
            else:
                lines.append(f'  {k} = {v}')
        lines.append('}')
        return '\n'.join(lines)


@dataclass
class SecurityGroupModule:
    """安全组模块"""
    name: str = "allow_ssh"
    description: str = "Allow SSH access"
    cidr_blocks: List[str] = field(default_factory=lambda: ["0.0.0.0/0"])

    def module_block(self) -> str:
        """生成安全组模块调用块"""
        inputs = {
            "name": self.name,
            "description": self.description,
            "cidr_blocks": self.cidr_blocks
        }
        lines = [f'module "{self.name}" {{')
        lines.append(f'  source = "./modules/securitygroup/{self.name}"')
        lines.append('  # 安全组配置')
        for k, v in inputs.items():
            if isinstance(v, str):
                lines.append(f'  {k} = "{v}"')
            elif isinstance(v, (int, float)):
                lines.append(f'  {k} = {v}')
            elif isinstance(v, list):
                lines.append(f'  {k} = [{", ".join(repr(x) for x in v)}]')
            else:
                lines.append(f'  {k} = {v}')
        lines.append('}')
        return '\n'.join(lines)


def generate_vpc_module_tf() -> str:
    """生成 VPC 模块 main.tf"""
    lines = ['# VPC 模块 - main.tf']
    lines.append('variable "name" {')
    lines.append('  description = "VPC 名称"')
    lines.append('  type        = string')
    lines.append('}')
    lines.append('')
    lines.append('variable "cidr_block" {')
    lines.append('  description = "VPC CIDR 范围"')
    lines.append('  type        = string')
    lines.append('  default     = "10.0.0.0/16"')
    lines.append('}')
    lines.append('')
    lines.append('variable "az_count" {')
    lines.append('  description = "可用区数量"')
    lines.append('  type        = number')
    lines.append('  default     = 2')
    lines.append('}')
    lines.append('')
    lines.append('variable "enable_dns" {')
    lines.append('  description = "启用 DNS"')
    lines.append('  type        = bool')
    lines.append('  default     = true')
    lines.append('}')
    lines.append('')
    lines.append('resource "aws_vpc" "main" {')
    lines.append('  name           = var.name')
    lines.append('  cidr_block     = var.cidr_block')
    lines.append('  enable_dns_hostnames = var.enable_dns')
    lines.append('  enable_dns_support    = var.enable_dns')
    lines.append('  tags = {')
    lines.append('    Name        = var.name')
    lines.append('    Environment = "production"')
    lines.append('  }')
    lines.append('}')
    lines.append('')
    lines.append('# 公有子网')
    lines.append('resource "aws_subnet" "public" {')
    lines.append('  count                  = var.az_count')
    lines.append('  vpc_id                 = aws_vpc.main.id')
    lines.append('  cidr_block             = cidrnetmask(var.cidr_block, count.index + 1)')
    lines.append('  availability_zone      = data.aws_availability_zones.available.names[count.index]')
    lines.append('  map_public_ip_on_launch = true')
    lines.append('  tags = {')
    lines.append('    Name        = "${var.name}-public-${count.index + 1}"')
    lines.append('  }')
    lines.append('}')
    lines.append('')
    lines.append('# 输出')
    lines.append('output "vpc_id" {')
    lines.append('  value = aws_vpc.main.id')
    lines.append('}')
    lines.append('output "public_subnet_ids" {')
    lines.append('  value = aws_subnet.public[*].id')
    lines.append('}')
    lines.append('')
    lines.append('# 数据源')
    lines.append('data "aws_availability_zones" "available" {')
    lines.append('  state = "available"')
    lines.append('}')
    lines.append('')
    return '\n'.join(lines)


def generate_ec2_module_tf(subnet_id: str) -> str:
    """生成 EC2 模块 main.tf"""
    lines = ['# EC2 模块 - main.tf']
    lines.append('variable "name" {')
    lines.append('  description = "实例名称"')
    lines.append('  type        = string')
    lines.append('}')
    lines.append('')
    lines.append('variable "instance_type" {')
    lines.append('  description = "EC2 实例类型"')
    lines.append('  type        = string')
    lines.append('  default     = "t2.micro"')
    lines.append('}')
    lines.append('')
    lines.append('variable "ami" {')
    lines.append('  description = "AMI ID"')
    lines.append('  type        = string')
    lines.append('}')
    lines.append('')
    lines.append('variable "subnet_id" {')
    lines.append('  description = "子网 ID"')
    lines.append('  type        = string')
    lines.append('}')
    lines.append('')
    lines.append('resource "aws_instance" "web" {')
    lines.append('  name         = var.name')
    lines.append('  instance_type = var.instance_type')
    lines.append('  ami          = var.ami')
    lines.append('  subnet_id    = var.subnet_id')
    lines.append('  vpc_security_group_ids = [aws_security_group.allow_ssh.id]')
    lines.append('  tags = {')
    lines.append('    Name        = var.name')
    lines.append('    Environment = "production"')
    lines.append('  }')
    lines.append('}')
    lines.append('')
    lines.append('# 输出')
    lines.append('output "instance_id" {')
    lines.append('  value = aws_instance.web.id')
    lines.append('}')
    lines.append('output "public_ip" {')
    lines.append('  value = aws_instance.web.public_ip')
    lines.append('}')
    lines.append('')
    return '\n'.join(lines)


def generate_module_usage_example() -> str:
    """生成模块使用示例"""
    lines = ['# 主配置 - 使用模块']
    lines.append('# 在根模块中使用 VPC 模块')
    lines.append('module "network" {')
    lines.append('  source = "./modules/vpc"')
    lines.append('  name        = "production"')
    lines.append('  cidr_block  = "10.0.0.0/16"')
    lines.append('  az_count    = 3')
    lines.append('  enable_dns  = true')
    lines.append('}')
    lines.append('')
    lines.append('# 在根模块中使用 EC2 模块')
    lines.append('module "server" {')
    lines.append('  source      = "./modules/ec2"')
    lines.append('  name        = "web-server"')
    lines.append('  instance_type = "t3.small"')
    lines.append('  ami         = data.aws_ami.amazon_linux.id')
    lines.append('  subnet_ids  = module.network.public_subnet_ids')
    lines.append('}')
    lines.append('')
    lines.append('# 安全组模块')
    lines.append('module "security" {')
    lines.append('  source      = "./modules/securitygroup"')
    lines.append('  name        = "allow-ssh"')
    lines.append('  description = "Allow SSH access"')
    lines.append('  cidr_blocks = ["0.0.0.0/0"]')
    lines.append('}')
    lines.append('')
    return '\n'.join(lines)


def generate_module_best_practices() -> str:
    """生成模块最佳实践"""
    lines = ['# Terraform 模块最佳实践']
    lines.append('')
    lines.append('## 1. 模块设计原则')
    lines.append('- 保持模块专注：单一职责')
    lines.append('- 使用清晰的变量命名')
    lines.append('- 提供合理的默认值')
    lines.append('- 记录所有输入和输出')
    lines.append('')
    lines.append('## 2. 输入变量最佳实践')
    lines.append('- 使变量标记为 optional，除非必需')
    lines.append('- 使用 validation 块进行验证')
    lines.append('- 标记敏感变量为 sensitive = true')
    lines.append('- 使用 description 解释变量用途')
    lines.append('')
    lines.append('## 3. 输出变量最佳实践')
    lines.append('- 仅输出有用的信息')
    lines.append('- 避免输出敏感数据')
    lines.append('- 使用输出别名进行别名处理')
    lines.append('')
    lines.append('## 4. 模块版本控制')
    lines.append('- 明确指定版本号')
    lines.append('- 使用模块注册表')
    lines.append('- 锁定模块版本')
    lines.append('')
    lines.append('## 5. 模块测试')
    lines.append('- 使用 terraform validate')
    lines.append('- 使用 terraform plan 检查')
    lines.append('- 集成测试框架')
    lines.append('')
    return '\n'.join(lines)


def main():
    print("=== Terraform 模块示例 ===\n")

    print("1. VPC 模块 main.tf:")
    print(generate_vpc_module_tf())
    print()

    print("2. EC2 模块 main.tf (带子网 ID):")
    print(generate_ec2_module_tf("subnet-12345678"))
    print()

    print("3. 模块使用示例:")
    print(generate_module_usage_example())
    print()

    print("4. 模块最佳实践:")
    print(generate_module_best_practices())
    print()

    # 创建模块定义示例
    vpc_module = TerraformModuleDef(
        name="vpc",
        source="./modules/vpc",
        version="3.0.0",
        inputs={
            "name": "production",
            "cidr_block": "10.0.0.0/16",
            "az_count": 3
        },
        outputs={
            "vpc_id": "aws_vpc.main.id",
            "public_subnet_ids": "aws_subnet.public[*].id"
        },
        description="生产环境 VPC 网络模块"
    )

    print("5. 模块定义 JSON 表示:")
    print(json.dumps(asdict(vpc_module), indent=2, ensure_ascii=False))
    print()

    print("=== 模块示例结束 ===")


if __name__ == "__main__":
    main()