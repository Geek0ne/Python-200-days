# Day 037 — 组合与聚合：检查清单

> ✅ 完成后勾选，标记为 `[x]`

## 📚 概念理解

- [ ] 理解组合（Composition）的「has-a」关系
- [ ] 理解聚合（Aggregation）的弱拥有关系
- [ ] 掌握组合和聚合的生命周期区别
- [ ] 理解「组合优于继承」的设计原则
- [ ] 知道继承的「脆弱的基类」问题
- [ ] 理解依赖注入的三种方式（构造器/Setter/方法）
- [ ] 理解紧耦合 vs 松耦合的区别
- [ ] 了解装饰器模式（组合的应用）
- [ ] 了解策略模式（组合替换算法）
- [ ] 了解桥接模式（组合分离抽象和实现）

## 💻 代码实践

- [ ] 实现一个组合关系（一个类在内部创建另一个类）
- [ ] 实现一个聚合关系（对象从外部传入）
- [ ] 展示组合关系中的生命周期绑定
- [ ] 展示聚合关系中的生命周期独立
- [ ] 使用依赖注入实现松耦合
- [ ] 用组合替代不合适的继承关系
- [ ] 实现装饰器模式（通过组合包装对象）
- [ ] 实现策略模式（运行时切换算法）
- [ ] 使用 Mixin 通过组合式复用功能

## 🧪 练习题

请完成以下练习，每题创建一个单独的 `.py` 文件。

### 练习 1：电脑组装工厂

创建一个电脑组装系统，展示组合关系：

```
Computer
├── CPU (组合：构造器中创建)
├── RAM (组合：构造器中创建)
├── Disk (组合：构造器中创建)
├── Monitor (聚合：可以外接/更换)
└── Keyboard (聚合：可以外部接入)
```

Computer 应提供 `spec()` 方法显示完整配置，`connect_monitor(monitor)` 和 `disconnect_monitor()` 方法。

### 练习 2：消息推送系统

使用依赖注入实现消息推送系统：

- `Message`：消息类
- `Sender` 接口：定义 `send(message)`
- 实现 `EmailSender`, `SMSSender`, `WeChatSender`
- `NotificationService`：使用依赖注入接收 Sender
- 可以运行时切换不同的发送渠道

### 练习 3：订单系统

实现订单系统，展示组合与聚合的区别：

- `OrderItem`：订单项（组合—不能离开 Order）
- `Order`：订单（包含 OrderItem 列表）
- `Customer`：客户（聚合—可以独立存在）
- `Payment`：支付方式（聚合—可以独立设置）
- Order 提供 `total()`, `add_item()`, `remove_item()` 方法

### 练习 4：文件系统

设计一个简单的文件系统，使用组合模式（Composite Pattern）：

- `FileSystemNode`：抽象基类
- `File`：文件（叶子节点）
- `Directory`：目录（容器节点，包含 FileSystemNode 列表）
- Directory 可以包含 File 和其他 Directory
- 实现 `get_size()`, `list_contents()`, `search(name)` 方法

### 练习 5：智能家居系统

创建一个智能家居系统，使用多种关系：

- `SmartHome`（组合：包含 Room 列表）
- `Room`（组合：包含 Device 列表）
- `Device`（抽象基类）/ `Light`, `Thermostat`, `Camera`（继承）
- `AutomationRule`（聚合：可以独立创建和分配）
- 实现 `turn_all_lights()`, `get_temperature_summary()`, `add_rule()` 等方法

---

## 📊 进度追踪

| 项目 | 完成情况 |
|------|---------|
| 阅读 README.md | [ ] |
| 运行 01-basic-usage.py | [ ] |
| 运行 02-advanced-usage.py | [ ] |
| 运行 03-car-model.py | [ ] |
| 练习 1：电脑组装 | [ ] |
| 练习 2：消息推送 | [ ] |
| 练习 3：订单系统 | [ ] |
| 练习 4：文件系统 | [ ] |
| 练习 5：智能家居 | [ ] |
| 完成检查清单 | [ ] |
