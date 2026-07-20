# Day 073 练习题清单

## 练习 1：创建虚拟环境 ⭐
为你的项目创建一个虚拟环境：
- 创建虚拟环境
- 激活并安装 3 个包
- 导出 requirements.txt
- 用 requirements.txt 重建环境

**要求：**
- 使用 venv 模块
- 记录每个步骤的命令
- 验证重建后的环境是否正常

## 练习 2：依赖分析 ⭐⭐
分析一个项目的依赖关系：
- 读取 requirements.txt
- 找出直接依赖和间接依赖
- 检查版本冲突
- 生成依赖报告

**要求：**
- 使用 pipdeptree 或手动分析
- 输出依赖树结构
- 标记可能的冲突
- 生成 Markdown 格式的报告

## 练习 3：打包发布 ⭐⭐⭐
将你的一个工具脚本打包成 Python 包：
- 创建标准项目结构
- 编写 pyproject.toml
- 添加测试
- 构建并检查包
- 上传到 TestPyPI

**要求：**
- 使用 src/ 目录结构
- 包含完整的 pyproject.toml
- 编写至少 3 个测试用例
- 使用 twine 检查包
- 成功上传到 TestPyPI

## 练习 4：Poetry 实战 ⭐⭐⭐
使用 Poetry 管理一个项目：
- 用 poetry new 创建项目
- 添加依赖
- 配置开发依赖
- 构建并发布

**要求：**
- 创建完整的项目结构
- 配置 pyproject.toml
- 使用 poetry run 运行测试
- 使用 poetry build 构建
- 生成 poetry.lock

## 练习 5：依赖安全审计 ⭐⭐⭐⭐
编写一个依赖安全审计工具：
- 读取 requirements.txt
- 调用 PyPI API 检查版本
- 检查已知漏洞
- 生成安全报告
- 建议升级版本

**要求：**
- 使用 requests 调用 PyPI API
- 解析 JSON 响应
- 检查 CVE 漏洞（可选）
- 生成 HTML 或 Markdown 报告
- 建议安全的版本升级路径

## 提交要求
- 所有练习的代码文件放在 exercises/ 目录
- 每个文件可以独立运行
- 添加必要的注释和文档字符串
- 包含测试用例和预期输出
