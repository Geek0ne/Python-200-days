# Git 提交规范

本仓库采用 **[Conventional Commits](https://www.conventionalcommits.org/)** 规范。

## 提交格式

```
<type>(<scope>): <subject>

<body>
```

### type（必填）

| 类型 | 说明 |
|------|------|
| `feat` | 新增学习内容 / 功能 |
| `docs` | 文档/注释类内容 |
| `refactor` | 代码重构 |
| `test` | 新增测试 |
| `chore` | 杂项（配置、工具脚本等） |
| `fix` | 修正错误 |
| `style` | 代码格式调整 |

### scope（可选）

| 范围 | 说明 |
|------|------|
| `concept` | 概念解释 |
| `example` | 代码示例 |
| `diagram` | 图解 / 示意图 |
| `exercise` | 练习题 |
| `summary` | 每日总结 |
| `project` | 项目实战 |
| `config` | 仓库配置 |

### subject（必填）

简短描述，中文即可，不超过 50 字，**不加句号**。

### body（可选）

详细说明，每行不超过 72 字。

## 提交示例

```
feat(concept): 添加变量作用域与原理解释

详细说明了 LEGB 规则以及变量查找顺序
配合图解说明 global/nonlocal 关键字的使用
```

```
docs(example): 添加装饰器实战代码案例

包含：计时装饰器、缓存装饰器、权限校验装饰器
```

```
feat(diagram): 添加 Python 内存管理示意图

ASCII 图展示堆栈内存分配与垃圾回收机制
```

```
feat: day-03 字符串与编码完整学习内容

包含 Unicode、UTF-8 原理解释，字符串操作方法
实战：文本分析工具
```

