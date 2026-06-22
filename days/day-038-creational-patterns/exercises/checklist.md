# Day 038 — 创建型设计模式：检查清单

> ✅ 完成后勾选，标记为 `[x]`

## 📚 概念理解

- [ ] 理解 GoF 23 种设计模式的三大分类
- [ ] 理解创建型模式的作用：封装对象创建逻辑
- [ ] 掌握单例模式的 3 种 Python 实现方式
- [ ] 理解简单工厂、工厂方法、抽象工厂的区别
- [ ] 理解建造者模式的链式调用和 Director
- [ ] 理解原型模式的克隆机制
- [ ] 理解「优先组合而非继承」在设计模式中的体现
- [ ] 了解 Python 模块作为天然单例的用法

## 💻 代码实践

- [ ] 实现 __new__ 方式的单例
- [ ] 实现装饰器方式的单例
- [ ] 实现简单工厂
- [ ] 实现工厂方法模式
- [ ] 实现抽象工厂模式
- [ ] 实现建造者模式（含 Director）
- [ ] 实现原型模式（浅/深拷贝）
- [ ] 实现线程安全的单例
- [ ] 实现对象池模式

## 🧪 练习题

请完成以下练习，每题创建一个单独的 `.py` 文件。

### 练习 1：日志单例

创建一个日志类 `AppLogger`，使用单例模式：

- 使用 `__new__` 确保唯一实例
- 支持 `info()`, `warning()`, `error()` 方法
- 可设置日志级别（DEBUG < INFO < WARNING < ERROR）
- 支持输出到控制台和文件
- 支持 `set_level()` 运行时切换日志级别

**示例：**
```python
logger = AppLogger()
logger.set_level("DEBUG")
logger.info("系统启动")      # 输出
logger.debug("调试信息")     # 输出（因为级别 ≤ DEBUG）
logger.set_level("WARNING")
logger.info("这不会被输出")  # 不输出（级别 < WARNING）
```

### 练习 2：支付工厂

实现一个支付工厂系统：

- `Payment` 抽象基类：`pay(amount)`, `refund(amount)`
- 实现 `Alipay`, `WechatPay`, `CreditCardPay`
- `PaymentFactory.create(method)` 创建支付实例
- 工厂支持注册新的支付方式
- 增加「组合支付」功能：同时使用多种支付方式

### 练习 3：UI 组件工厂

实现一个跨平台 UI 组件工厂：

- 支持 Windows、macOS、Linux 三套主题
- 每种主题包含：Button、Menu、Slider 三个组件
- 使用抽象工厂模式
- 工厂可以根据操作系统自动选择对应主题

### 练习 4：计算机建造者

使用建造者模式实现 `ComputerBuilder`：

```python
gaming = ComputerBuilder() \
    .cpu("i9-13900K") \
    .gpu("RTX 4090") \
    .ram(32, "DDR5") \
    .storage(2048, "NVMe SSD") \
    .cooling("水冷") \
    .build()

office = ComputerBuilder() \
    .cpu("i5-13400") \
    .ram(16, "DDR4") \
    .storage(512, "SSD") \
    .build()
```

Computer 应有 `spec()` 方法返回完整配置字符串。

### 练习 5：文档对象池

实现一个文档编辑器中的对象池：

- `Document` 类：包含内容、样式、大小等属性
- `DocumentPool` 类：管理 Document 对象的复用
- 池的最小/最大容量可配置
- 池会「预热」创建初始文档
- 获取的 Document 会被「重置」到初始状态
- 超出的请求会等待释放

---

## 📊 进度追踪

| 项目 | 完成情况 |
|------|---------|
| 阅读 README.md | [ ] |
| 运行 01-basic-usage.py | [ ] |
| 运行 02-advanced-usage.py | [ ] |
| 运行 03-config-manager.py | [ ] |
| 练习 1：日志单例 | [ ] |
| 练习 2：支付工厂 | [ ] |
| 练习 3：UI 组件工厂 | [ ] |
| 练习 4：计算机建造者 | [ ] |
| 练习 5：文档对象池 | [ ] |
| 完成检查清单 | [ ] |
