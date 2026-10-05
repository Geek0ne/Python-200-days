# Day 175 — Ansible 批量部署

## 今日完成清单

### 一、知识学习

- [ ] 理解 Ansible Inventory（主机清单）的概念与 INI/YAML 格式
- [ ] 理解 Playbook 结构与 YAML 语法
- [ ] 掌握常见 Ansible 模块（file/apt/pip/git/template/systemd）
- [ ] 理解无代理、推送模式、幂等性、并行执行四大原理
- [ ] 掌握 Python 调用 Ansible API（ansible-runner）的方法
- [ ] 看懂并会画 Ansible 架构图（控制节点 → SSH → 目标节点）
- [ ] 理解变量作用域与优先级层级

### 二、动手实验（在本机真实执行）

实验 1：生成 Inventory
```bash
cd ~/code/Learn-Python
python3 days/day-175-ansible-批量部署/code/01-generate-inventory.py
cat days/day-175-ansible-批量部署/hosts.ini
```
验收标准：输出 `crawler-1` ~ `crawler-5`，每个有 `ansible_host` 和 `node_role`

实验 2：健康检查脚本自检
```bash
python3 days/day-175-ansible-批量部署/code/03-healthcheck.py --self-test
```
验收标准：JSON 输出中包含 Python 版本、脚本行数、ssh_available 字段

实验 3：dry-run 模拟
```bash
python3 days/day-175-ansible-批量部署/code/03-healthcheck.py --dry-run
```
验收标准：输出 "干跑模式：不会连接任何真实主机"，不连接任何外部 IP

实验 4（进阶）：用 Python 生成 100 节点清单并验证格式
```bash
cd ~/code/Learn-Python
python3 - <<'EOF'
import sys
sys.path.insert(0, 'days/day-175-ansible-批量部署/code')
from 01_generate_inventory import generate_inventory
content = generate_inventory(100, "10.0.1")
print(content.count("crawler-"))  # 应输出 100
EOF
```

### 三、思考题（手写答案）

1. Ansible 为什么不需要在目标节点安装 agent？SSH 扮演什么角色？
2. 幂等性为什么重要？Ansible 模块如何实现幂等性？
3. 当管理 1000+ 机器时，静态 Inventory 有什么缺陷？动态 Inventory 如何设计？
4. `ansible-runner` 与 `subprocess.run(['ansible-playbook'])` 的本质区别是什么？
5. `any_errors_fatal` 和 `max_fail_percentage` 有什么区别？如何设计回滚？

### 四、清理（实验后必须执行）

```bash
cd ~/code/Learn-Python
rm -f days/day-175-ansible-批量部署/hosts.ini
rm -f days/day-175-ansible-批量部署/deploy_report_*.json
rm -f days/day-175-ansible-批量部署/deploy_check_*.json
```

## 练习题

### 基础题

**L1**：写出 INI 格式 Inventory 中定义一个主机组 `[webservers]` 含 2 台主机的写法，并为该组添加变量 `http_port=80`。

**L2**：写一个 Playbook 的 tasks 片段：在远程主机上创建目录 `/opt/myapp`（权限 0755），并安装 `nginx` 包。

**L3**：解释 `changed: true` 和 `changed: false` 在 Ansible 输出中的含义，以及它为什么是幂等性的基础。

### 进阶题

**A1**：编写一个 Playbook 片段，使用 `template` 模块把本地 `templates/config.j2` 渲染到远程主机 `/etc/myapp/config`，并在文件变更后通知 handler `restart myapp`。

**A2**：设计一个带错误处理的 playbook：部署 5 台节点，允许最多 1 台失败，其余继续；失败的主机在 `rescue` 区块中被标记（在 control node 上写日志到 `/tmp/failed_hosts`）。

**A3**：用 Python 调用 `ansible_runner` 执行 Playbook，并实时打印每个 Task 的执行结果（遍历 `result.events`，过滤 `runner_on_ok` / `runner_on_failed`）。

## 评分标准

| 等级 | 要求 |
|------|------|
| 优秀 | 完成全部清单 + 3 道进阶题 + 思考题全部答对 |
| 良好 | 完成全部清单 + 2 道进阶题 + 实验 1-2 真实跑通 |
| 合格 | 完成基础清单 + 1-2 道基础题 + 实验 1 真实跑通 |
| 待改进 | 未完成清单或实验未真实执行 |