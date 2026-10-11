# Day 179: Terraform 基础设施 — 练习题与检查清单

## 📝 完成清单

### 基础练习（必做）

- [ ] **创建提供商配置**
  - [ ] 编写 `provider "aws"` 块，指定 region 为 `us-west-2`
  - [ ] 编写 `provider "google"` 块，指定 project 和 region
  - [ ] 编写 `provider "azurerm"` 块，启用 features
  - [ ] **自我测试**：运行 `python3 tools/generate_daily.py` 验证配置语法

- [ ] **创建 VPC 资源**
  - [ ] 定义 `resource "aws_vpc"`，包含 cidr_block 和标签
  - [ ] 启用 `enable_dns_hostnames` 和 `enable_dns_support`
  - [ ] 添加 `tags` 块，包含 Name 和 Environment
  - [ ] **自我测试**：验证 VPC 资源块语法正确

- [ ] **创建安全组**
  - [ ] 定义 `resource "aws_security_group"`，包含 name 和 description
  - [ ] 添加 `ingress` 规则，允许 SSH (端口 22) 从 0.0.0.0/0 访问
  - [ ] 添加 `egress` 规则，允许所有出站流量
  - [ ] 关联 VPC ID
  - [ ] **自我测试**：验证安全组规则语法正确

- [ ] **创建 EC2 实例**
  - [ ] 定义 `resource "aws_instance"`，指定 ami 和 instance_type
  - [ ] 关联安全组和子网
  - [ ] 配置 root_block_device (卷大小、类型、加密)
  - [ ] 添加标签
  - [ ] **自我测试**：验证实例资源语法正确

- [ ] **定义输出**
  - [ ] 创建 `output "vpc_id"` 输出 VPC ID
  - [ ] 创建 `output "public_subnet_ids"` 输出公有子网 ID 列表
  - [ ] 创建 `output "instance_public_ips"` 输出实例公有 IP
  - [ ] **自我测试**：验证输出块语法正确

### 进阶练习（挑战）

- [ ] **创建模块**
  - [ ] 创建 `modules/vpc/main.tf`，包含 VPC 和子网资源
  - [ ] 创建 `modules/vpc/variables.tf`，定义 name、cidr_block、az_count 变量
  - [ ] 创建 `modules/vpc/outputs.tf`，输出 vpc_id 和 public_subnet_ids
  - [ ] 创建根模块使用模块：`module "network" { source = "./modules/vpc" ... }`
  - [ ] **自我测试**：运行 `terraform init && terraform validate` 验证模块

- [ ] **配置远程后端**
  - [ ] 编写 `backend "s3"` 配置，指定 bucket、key、region
  - [ ] 配置 DynamoDB 用于状态锁定：`dynamodb_table = "terraform-state-lock"`
  - [ ] 开启加密：`encrypt = true`
  - [ ] **自我测试**：验证后端配置语法，了解状态迁移流程

- [ ] **创建工作区**
  - [ ] 列出工作区：`terraform workspace list`
  - [ ] 创建新工作区：`terraform workspace new staging`
  - [ ] 切换工作区：`terraform workspace select production`
  - [ ] **自我测试**：验证工作区在 `.terraform/workspaces/` 中创建

- [ ] **编写数据源**
  - [ ] 使用 `data "aws_ami" "amazon_linux"` 获取最新 Amazon Linux AMI
  - [ ] 使用 `data "aws_availability_zones" "available"` 获取可用区列表
  - [ ] 在实例资源中引用数据源：`ami = data.aws_ami.amazon_linux.id`
  - [ ] **自我测试**：验证数据源语法和引用正确

- [ ] **使用循环创建资源**
  - [ ] 使用 `count` 创建多个子网：`count = length(var.az_cidrs)`
  - [ ] 使用 `for_each` 创建安全组规则：`for_each = toset(var.allowed_ports)`
  - [ ] 理解 count 和 for_each 的区别
  - [ ] **自我测试**：验证循环资源创建正确

- [ ] **条件资源创建**
  - [ ] 使用 `var.environment != "production"` 条件控制资源
  - [ ] 使用 `conditional expression`：`ami = var.use_latest_ami ? data.aws_ami.amazon_linux.id : var.ami_id`
  - [ ] 理解条件对状态的影响
  - [ ] **自我测试**：验证条件资源创建和销毁行为

- [ ] **编写模块文档**
  - [ ] 创建 `modules/vpc/README.md`，解释模块用法
  - [ ] 列出所有输入变量，包含描述和默认值
  - [ ] 列出所有输出输出，包含描述
  - [ ] **自我测试**：阅读模块文档，能够正确使用模块

## 💡 思考题

1. **状态管理**：Terraform 状态文件（`.tfstate`）包含什么关键信息？为什么状态管理对团队协作很重要？如何解决状态冲突？

2. **模块 vs 资源**：什么情况下应该创建模块而不是直接编写资源？模块的三大好处是什么？如何设计一个好的 Terraform 模块？

3. **Count vs For_each**：`count` 和 `for_each` 有什么区别？何时使用哪一个？`for_each` 的值类型有什么要求？

4. **远程后端**：为什么需要远程后端存储？S3 后端配合 DynamoDB 锁的作用是什么？如何从本地状态迁移到远程状态？

5. **基础设施即代码（IaC）的原则**：Terraform 如何体现 IaC 理念？与传统的手动配置相比，有什么优势和劣势？

## ✅ 今日完成情况

| 任务 | 状态 | 备注 |
|------|------|------|
| 基础练习全部完成 | ☐ | |
| 进阶练习全部完成 | ☐ | |
| README.md 内容完整 | ☐ | |
| code/ 目录 3 个 .py 文件 | ☐ | |
| exercises/checklist.md | ☐ | |
| diagrams/README.md (如有) | ☐ | |

---
*最后更新：2026-10-12*
*点击查看参考答案：无（需自行完成实验）*