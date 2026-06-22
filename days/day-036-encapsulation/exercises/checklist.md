# Day 036 — 封装与数据隐藏：检查清单

> ✅ 完成后勾选，标记为 `[x]`

## 📚 概念理解

- [ ] 理解封装的概念：隐藏实现细节，暴露简洁接口
- [ ] 理解 Python 的封装哲学：「我们都是成年人了」
- [ ] 掌握 `_single` 和 `__double` 下划线的区别
- [ ] 理解名称改写机制的作用和规则
- [ ] 理解继承中名称改写如何避免冲突
- [ ] 掌握 `@property` 的使用场景（getter/setter/deleter）
- [ ] 理解 Property 的核心价值：向后兼容的接口变更
- [ ] 了解描述符协议的基本概念
- [ ] 了解 `__getattr__` 和 `__setattr__` 的用途

## 💻 代码实践

- [ ] 使用名称改写保护私有属性
- [ ] 演示继承中 `__private` 不冲突的现象
- [ ] 使用 `@property` 实现只读属性
- [ ] 使用 `@property` 实现读写 + 验证属性
- [ ] 使用 `@property` 实现计算属性
- [ ] 实现一个自定义描述符
- [ ] 使用 `__setattr__` 拦截属性赋值
- [ ] 使用 `@cached_property` 实现惰性属性
- [ ] 实现一个包含多层封装的类（公开/保护/私有）

## 🧪 练习题

请完成以下练习，每题创建一个单独的 `.py` 文件。

### 练习 1：银行账户

创建一个 `BankAccount` 类：

- `__account_number`：私有属性，账户号
- `__balance`：私有属性，余额
- `_owner`：受保护属性，户主名
- `balance`：只读 property，返回余额
- `deposit(amount)`：存款（带验证：金额必须 > 0）
- `withdraw(amount)`：取款（带验证：金额 > 0 且不超过余额）
- 子类 `SavingsAccount` 添加 `interest_rate` 属性
- 确保子类不会意外覆盖父类的私有属性

### 练习 2：温度传感器

创建一个 `TemperatureSensor` 类：

- `_celsius`：内部存储的摄氏温度
- `celsius`：property（读写 + 验证 ≥ -273.15）
- `fahrenheit`：property（只读，自动转换）
- `kelvin`：property（只读，自动转换）
- 使用属性 deleter 重置温度为 0

### 练习 3：配置管理器

创建一个 `Config` 类，使用 `__getattr__` 和 `__setattr__` 实现：

- 支持属性风格的配置读写：`config.host = "localhost"`
- 类型验证：字符串不能赋给整数配置项
- 配置冻结：`config.freeze()` 后不能修改
- 变更日志：记录所有配置修改

### 练习 4：用户验证表单

创建一个 `UserForm` 类，使用描述符或 property 验证：

- `username`：3~20 个字符，只允许字母数字
- `email`：有效的邮箱格式
- `age`：0~150 之间的整数
- `password`：至少 8 个字符
- 实现 `validate_all()` 方法，返回所有字段验证结果

### 练习 5：安全的文件存储服务

创建一个 `SecureFileStore` 类：

- `__root_path`：私有属性，文件存储根目录
- `__max_size`：私有属性，最大文件大小
- 只读 property 暴露根路径（不含敏感信息）和最大大小
- 方法 `store(filename, content)`：验证路径安全（防止目录遍历攻击）
- 方法 `retrieve(filename)`：读取文件
- 方法 `list_files()`：列出所有文件
- 防止 `..` 目录遍历：`__validate_path(filename)` 内部方法

---

## 📊 进度追踪

| 项目 | 完成情况 |
|------|---------|
| 阅读 README.md | [ ] |
| 运行 01-basic-usage.py | [ ] |
| 运行 02-advanced-usage.py | [ ] |
| 运行 03-secure-api.py | [ ] |
| 练习 1：银行账户 | [ ] |
| 练习 2：温度传感器 | [ ] |
| 练习 3：配置管理器 | [ ] |
| 练习 4：用户验证表单 | [ ] |
| 练习 5：安全文件存储 | [ ] |
| 完成检查清单 | [ ] |
