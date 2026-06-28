# Day 41 — SOLID 原则：完成清单 & 练习题

## ✅ 今日完成清单

- [ ] 理解 SOLID 五大原则的定义和目的
- [ ] 理解 SRP（单一职责原则）：一个类只有一个变化原因
- [ ] 理解 OCP（开闭原则）：对扩展开放，对修改关闭
- [ ] 理解 LSP（里氏替换原则）：子类必须可替换父类
- [ ] 理解 ISP（接口隔离原则）：接口要小而专
- [ ] 理解 DIP（依赖反转原则）：依赖抽象而非具体
- [ ] 看懂每个原则的违反反例和正确示例
- [ ] 理解设计原则与设计模式的关系
- [ ] 阅读并运行 `code/01-srp-ocp.py`
- [ ] 阅读并运行 `code/02-lsp-isp.py`
- [ ] 阅读并运行 `code/03-code-refactoring.py`（重构前后对比）

---

## 📝 练习题

### 练习 1：识别 SOLID 违反

阅读下面的代码，找出它违反了哪些 SOLID 原则，并说明理由。

```python
class FileManager:
    def read_data(self, filename):
        with open(filename, 'r') as f:
            return f.read()

    def parse_json(self, data):
        import json
        return json.loads(data)

    def save_to_db(self, data):
        print(f"保存到数据库: {data}")

    def send_report(self, data, email):
        print(f"发送报表到 {email}: {data}")
```

### 练习 2：OCP 重构

重构下面的代码，使其遵循开闭原则：

```python
class Logger:
    def log(self, message, target):
        if target == "console":
            print(message)
        elif target == "file":
            with open("app.log", "a") as f:
                f.write(message + "\n")
        elif target == "network":
            # 发送到远程日志服务器
            print(f"[NETWORK] {message}")
```

提示：使用策略模式，让 `Logger` 依赖抽象的日志目标。

### 练习 3：LSP 问题诊断

以下代码违反了里氏替换原则，请指出问题并修复：

```python
class Account:
    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("余额不足")
        self.balance -= amount

class SavingsAccount(Account):
    def withdraw(self, amount):
        if amount > 5000:
            raise ValueError("储蓄账户单次取款不能超过 5000")
        super().withdraw(amount)

def process_withdrawal(account: Account, amount):
    account.withdraw(amount)  # SavingsAccount 会抛不同的异常
```

### 练习 4：完整重构

你接手了一个小型订单系统，当前代码将所有功能混在一起。请按照 SOLID 原则将其重构。

原始代码（需要重构）：

```python
class OrderAPI:
    def handle_request(self, data):
        # 1. 解析请求
        order_id = data["order_id"]
        items = data["items"]
        user_id = data["user_id"]
        payment_method = data.get("payment", "credit")

        # 2. 验证订单
        if not items:
            return {"error": "商品列表为空"}

        # 3. 计算总价
        total = sum(item["price"] * item["qty"] for item in items)
        if total > 1000:
            total *= 0.95  # 满 1000 打 95 折

        # 4. 处理支付
        if payment_method == "credit":
            print(f"信用卡支付 ¥{total}")
        elif payment_method == "alipay":
            print(f"支付宝支付 ¥{total}")
        else:
            return {"error": "不支持的支付方式"}

        # 5. 记录到日志文件
        with open("orders.log", "a") as f:
            f.write(f"{order_id},{total}\n")

        # 6. 发送确认
        print(f"确认邮件已发送")
        print(f"确认短信已发送")

        return {"success": True, "order_id": order_id, "total": total}
```

**要求：** 将以上代码拆分为以下模块（你可以用伪代码或实际 Python 代码实现）：
- `OrderValidator` — 验证
- `PriceCalculator` — 计算价格和折扣
- `PaymentProcessor` — 处理支付（多态支持不同支付方式）
- `OrderRepository` — 存储订单
- `Notifier` — 发送通知
- `OrderAPI` — 编排以上组件（依赖注入）

### 练习 5：日常代码自检清单

对于你自己写的或项目中的代码，检查每个类是否符合以下标准：

| 检查项 | 是/否 | 改进方案 |
|--------|-------|----------|
| 这个类是不是只做一件事？（SRP） | □ | |
| 加新功能需要改这个类的代码吗？（OCP） | □ | |
| 子类替换父类会出问题吗？（LSP） | □ | |
| 这个类的方法是不是都被用到了？（ISP） | □ | |
| 有没有面向接口编程？（DIP） | □ | |

---

## 🔗 参考资源

- [SOLID: The First 5 Principles of Object Oriented Design (DigitalOcean)](https://www.digitalocean.com/community/conceptual-articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design)
- [Clean Code: A Handbook of Agile Software Craftsmanship (Robert C. Martin)](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [Python 的 ABC 模块文档](https://docs.python.org/3/library/abc.html)
- [Python 的 typing.Protocol 文档](https://docs.python.org/3/library/typing.html#typing.Protocol)
