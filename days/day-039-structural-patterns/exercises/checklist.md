# Day 39 — 完成清单 & 练习题

## ✅ 完成清单

- [x] README.md 已编写（概念、原理、图解、对比、实战）
- [x] `01-adapter-pattern.py` — 适配器模式（JSON→XML 接口转换）
- [x] `02-proxy-pattern.py` — 代理模式（延迟加载 + 权限控制）
- [x] `03-cache-proxy.py` — 实战：缓存代理（LRU + TTL + 缓存失效）
- [x] `exercises/checklist.md` — 练习题
- [x] `diagrams/README.md` — 图解

---

## 📝 练习题

### 基础题

#### 1. 识别模式

阅读以下代码片段，判断使用了哪种结构型模式（适配器/代理/装饰器），并说明理由：

```python
# 代码 A
class ServiceWrapper:
    def __init__(self, service):
        self._service = service
    def get_data(self):
        result = self._service.fetch()
        return {"status": "ok", "data": result}
```

```python
# 代码 B
class ImageLoader:
    def __init__(self, path):
        self._path = path
        self._image = None
    def display(self):
        if self._image is None:
            self._image = open(self._path).read()
        return self._image
```

```python
# 代码 C
class CoffeeWithMilk:
    def __init__(self, coffee):
        self._coffee = coffee
    def cost(self):
        return self._coffee.cost() + 5
    def description(self):
        return self._coffee.description() + " + 奶"
```

#### 2. 补全代码

补全以下适配器模式代码，使其能将 `OldLogger` 的 `log_message(msg)` 接口适配为 `NewLogger` 的 `info(msg)` 格式：

```python
from abc import ABC, abstractmethod

class NewLogger(ABC):
    @abstractmethod
    def info(self, msg: str): pass
    @abstractmethod
    def error(self, msg: str): pass

class OldLogger:
    def log_message(self, level, msg):
        print(f"[{level}] {msg}")

# 请补全 Adapter 类
class LoggerAdapter(NewLogger):
    def __init__(self, old_logger: OldLogger):
        # 你的代码
        pass
    
    def info(self, msg: str):
        # 你的代码
        pass
    
    def error(self, msg: str):
        # 你的代码
        pass
```

#### 3. 实现一个简单的缓存代理

为以下 `ExpensiveCalculator` 类编写一个缓存代理：

```python
import time

class ExpensiveCalculator:
    def compute(self, n: int) -> int:
        """模拟耗时计算（比如斐波那契）"""
        time.sleep(0.5 * n)
        return n * n

# 请编写 CacheCalculatorProxy 类
class CacheCalculatorProxy:
    # 你的代码
    pass
```

要求：
- 代理和原类有相同的 `compute(n)` 接口
- 相同 n 值只计算一次，后续返回缓存
- 至少包含 1 个测试用例

---

### 进阶题

#### 4. 设计：多级缓存系统

设计一个**多级缓存代理**，包含两级：
- **L1 缓存**：内存缓存（TTL=10秒，容量=100）
- **L2 缓存**：文件缓存（TTL=3600秒，存储到临时目录）

访问流程：`客户端 → L1 → L2 → 真实服务`

要求：
- L1 未命中查 L2
- L2 未命中才查真实服务
- 查到的结果回填到 L1
- 画出数据访问流程图

#### 5. 设计：API 限流代理

某第三方 API 限制每分钟最多 60 次调用。请设计一个**限流代理**：
- 在代理层控制调用频率
- 超过限制时抛出 `RateLimitError`
- 保留最近一分钟的调用时间戳用于判断
- 支持配置不同的限制策略（如每分钟100次、每小时1000次）

```python
class RateLimiterProxy(APIService):
    def __init__(self, service: APIService, max_calls: int, period_seconds: int):
        # 你的设计
        pass
    
    def call_api(self, endpoint: str) -> dict:
        # 你的实现
        pass
```

#### 6. 思考：设计模式组合

假设有以下需求，你会如何组合使用结构型模式和创建型模式？

> 系统需要访问不同类型的数据库（MySQL、PostgreSQL、MongoDB），
> 每个数据库连接都要有连接池（池化），
> 而且需要记录每个查询的耗时。

请画出架构图，并标注使用了哪些设计模式。

---

## 💡 提示

- 练习题代码可以写在 `exercises/` 下的 `.py` 文件中
- 重点理解三种模式的区别：**适配器**改接口 / **代理**管访问 / **装饰器**加功能
- 缓存代理的 TTL 和 LRU 是实际生产中最常见的组合
