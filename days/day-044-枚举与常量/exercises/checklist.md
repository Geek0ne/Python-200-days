# Day 44：枚举与常量 — 练习题与完成清单

## ✅ 今日完成清单

- [x] 理解枚举的设计目的（为什么需要枚举）
- [x] 掌握基本 Enum 定义与访问（.name / .value）
- [x] 理解枚举成员的"单例"特性
- [x] 掌握枚举的三种查找方式（按名称、按值、按成员）
- [x] 理解 IntEnum 与普通 Enum 的区别和适用场景
- [x] 掌握 `auto()` 自动赋值及自定义策略
- [x] 掌握 `@unique` 装饰器保证值唯一
- [x] 理解枚举别名机制
- [x] 掌握 IntFlag 位标志
- [x] 实战：订单状态机（合法状态转移）
- [x] 实战：游戏角色状态机
- [x] README.md — 完整的概念解释和原理分析

---

## 📝 基础练习题

### 练习 1：定义基本枚举

定义一个 `TrafficLight` 枚举，包含 `RED`、`YELLOW`、`GREEN` 三个成员，值从 1 开始。要求：
- 打印每个成员的名字和值
- 用 `is` 比较两个 RED 成员是否相同
- 尝试按值 2 查找并打印结果

### 练习 2：用枚举替代魔法数字

下面的代码使用了魔法数字，请用枚举重构：

```python
def process_payment(status: int):
    if status == 1:
        print("待支付")
    elif status == 2:
        print("已支付")
    elif status == 3:
        print("支付失败")

# 调用
process_payment(1)
process_payment(2)
process_payment(999)  # 不会报错！
```

要求：
1. 定义 `PaymentStatus` 枚举
2. 改为 `process_payment(status: PaymentStatus)`
3. 验证非法值会被类型提示工具发现

### 练习 3：auto() 与自定义值

定义一个 `Priority` 枚举，要求：
- `LOW` = auto()
- `MEDIUM` = auto()
- `HIGH` = auto()
- `CRITICAL` = auto()

打印出它们的值。然后思考：如果希望 `CRITICAL = 999`，其余用 auto() 从 1 开始，应该怎么做？

---

## 🚀 进阶练习题

### 练习 4：交通灯状态机

实现一个交通灯系统，状态转换规则为：
- `RED` → `GREEN`
- `GREEN` → `YELLOW`
- `YELLOW` → `RED`

用枚举定义状态，并实现一个 `TrafficLightMachine` 类：
- 有 `current_state` 属性
- 有 `change()` 方法，执行合法转换
- 非法转换抛出异常

### 练习 5：权限系统（IntFlag）

用 IntFlag 实现一个文件权限系统：
- `READ` = 4
- `WRITE` = 2
- `EXECUTE` = 1

要求：
1. 定义一个 `Permission` 枚举（IntFlag）
2. 实现一个 `File` 类，每个文件有 owner/group/other 三组权限
3. 实现方法 `can_read(user)`、`can_write(user)`、`can_execute(user)`
4. 打印测试结果

---

## 💡 思考题

1. **为什么 Enum 成员默认从 1 开始而不是 0？**

2. **如果不用 `@unique`，两个成员值相同会发生什么？** 后定义的会成为别名还是独立成员？

3. **为什么推荐用 `is` 而不是 `==` 比较枚举成员？** 什么极端情况下 `==` 会意外返回 True？

4. **设计题**：设计一个电梯状态机——楼层选择、运行方向、开关门。用枚举实现。

---

## 参考资料

- [PEP 435 — Adding an Enum type to the Python standard library](https://peps.python.org/pep-0435/)
- [Python enum 官方文档](https://docs.python.org/3/library/enum.html)
- [Python 3.11 StrEnum](https://docs.python.org/3/library/enum.html#strenum)
