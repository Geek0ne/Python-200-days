# Day 071 — 日志与调试：logging 模块与 pdb

## 概述

写代码难免会出 Bug，程序出了问题怎么排查？答案是**日志 + 调试**。

- **日志（logging）**：在代码中埋点记录关键信息，出了问题可以回溯
- **调试（debugging）**：暂停程序，一步步检查变量状态，定位问题根源

**今天你将学到：**
1. logging 模块详解——Logger、Handler、Formatter 的关系
2. 日志级别与配置——字典配置、文件配置
3. pdb 调试器——断点、单步执行、变量检查
4. **实战：生产级日志配置**——为真实项目配置日志系统

> 💡 **日志 vs print**：
> - `print` 只能在开发时看，生产环境看不到
> - `logging` 可以控制级别、输出到文件、远程收集
> - 生产代码**禁止使用 print**，全部用 logging

---

## 1. logging 模块详解

### 1.1 为什么需要 logging？

```python
# ❌ 新手写法：用 print 调试
def process_order(order):
    print(f"收到订单: {order}")  # 生产环境看不到！
    result = calculate_total(order)
    print(f"总价: {result}")    # 出了问题无法回溯
    return result

# ✅ 正确写法：用 logging
import logging
logger = logging.getLogger(__name__)

def process_order(order):
    logger.info(f"收到订单: {order}")
    result = calculate_total(order)
    logger.info(f"总价: {result}")
    return result
```

### 1.2 日志级别

```python
import logging

# 从低到高：
logging.debug("调试信息")      # 10 - 开发时详细信息
logging.info("一般信息")       # 20 - 确认程序按预期运行
logging.warning("警告")        # 30 - 意外但不影响运行
logging.error("错误")          # 40 - 某个功能失败
logging.critical("严重错误")   # 50 - 程序可能无法继续运行
```

| 级别 | 数值 | 使用场景 |
|------|------|---------|
| DEBUG | 10 | 详细的调试信息，变量值、函数调用 |
| INFO | 20 | 确认程序正常运行的关键节点 |
| WARNING | 30 | 潜在问题，但程序还能运行 |
| ERROR | 40 | 某个功能失败，需要关注 |
| CRITICAL | 50 | 严重错误，程序可能崩溃 |

### 1.3 基础用法

```python
# code/01-logging-basics.py
import logging

# ========== 1. basicConfig 快速配置 ==========
# 最简单的配置方式（只能调用一次）
logging.basicConfig(
    level=logging.DEBUG,  # 最低级别
    format="%(asctime)s [%(levelname)s] %(message)s",
    # 格式：时间 [级别] 消息
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 创建 logger
logger = logging.getLogger(__name__)

# 使用不同级别
logger.debug("这是调试信息")
logger.info("程序启动成功")
logger.warning("磁盘空间不足")
logger.error("文件不存在: data.csv")
logger.critical("数据库连接失败")

# ========== 2. 输出到文件 ==========
# basicConfig 也可以输出到文件
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    filename="app.log",  # 输出到文件
    filemode="w",        # 'w' 覆盖, 'a' 追加
)

logger = logging.getLogger("file_logger")
logger.info("这条日志会写入 app.log")
```

### 1.4 Logger、Handler、Formatter 的关系

```
Logger（日志记录器）
  ├── Handler（处理器）──→ 控制台输出
  ├── Handler（处理器）──→ 文件输出
  └── Handler（处理器）──→ 邮件发送

Formatter（格式器）──→ 定义每条日志的格式
```

```python
# code/02-logging-components.py
import logging

# ========== 创建 Logger ==========
logger = logging.getLogger("my_app")
logger.setLevel(logging.DEBUG)  # 设置最低级别

# ========== 创建 Formatter ==========
# 详细格式
detailed_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
# %(lineno)d 表示行号，方便定位问题

# 简洁格式
simple_formatter = logging.Formatter(
    fmt="[%(levelname)s] %(message)s"
)

# ========== 创建 Handler ==========
# 控制台 Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # 控制台只显示 INFO 及以上
console_handler.setFormatter(simple_formatter)

# 文件 Handler
file_handler = logging.FileHandler("app.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
file_handler.setFormatter(detailed_formatter)

# 错误文件 Handler（只记录 ERROR 及以上）
error_handler = logging.FileHandler("error.log", encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(detailed_formatter)

# ========== 组装 ==========
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_handler)

# ========== 使用 ==========
logger.debug("详细调试信息")     # 只写入 app.log
logger.info("一般信息")          # 写入控制台 + app.log
logger.warning("警告")          # 写入控制台 + app.log
logger.error("错误信息")        # 写入控制台 + app.log + error.log
logger.critical("严重错误")     # 写入控制台 + app.log + error.log
```

### 1.5 日志格式变量速查

| 变量 | 含义 | 示例 |
|------|------|------|
| %(asctime)s | 时间 | 2024-01-01 12:00:00 |
| %(levelname)s | 级别 | INFO, ERROR |
| %(name)s | Logger 名称 | my_app.views |
| %(message)s | 日志消息 | 用户登录成功 |
| %(filename)s | 文件名 | views.py |
| %(lineno)d | 行号 | 42 |
| %(funcName)s | 函数名 | login |
| %(thread)d | 线程 ID | 140234567890 |
| %(process)d | 进程 ID | 12345 |

---

## 2. 日志配置

### 2.1 字典配置（推荐）

```python
# code/03-dict-config.py
import logging
import logging.config

# 用字典一次性配置整个日志系统
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # 保留已有 logger

    # 格式器
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d "
                      "%(funcName)s() - %(message)s"
        },
    },

    # 处理器
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "app.log",
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.FileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "error.log",
            "encoding": "utf-8",
        },
    },

    # 日志记录器
    "loggers": {
        "": {  # 根 logger
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file"],
        },
        "my_app": {  # 特定模块
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,  # 不传播到根 logger
        },
    },
}

# 应用配置
logging.config.dictConfig(LOGGING_CONFIG)

# 使用
logger = logging.getLogger("my_app")
logger.info("日志系统配置完成")
```

### 2.2 针对第三方库的日志

```python
# 减少第三方库的日志输出
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

### 2.3 日志轮转

```python
# code/04-log-rotation.py
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# ========== 按大小轮转 ==========
# 每个文件最大 5MB，保留 5 个备份
handler = RotatingFileHandler(
    "app.log",
    maxBytes=5*1024*1024,  # 5MB
    backupCount=5,
    encoding="utf-8"
)

# ========== 按时间轮转 ==========
# 每天轮转一次，保留 30 天
handler = TimedRotatingFileHandler(
    "app.log",
    when="midnight",       # 每天午夜轮转
    interval=1,
    backupCount=30,
    encoding="utf-8"
)

# 其他 when 选项：
# "S" - 秒
# "M" - 分钟
# "H" - 小时
# "D" - 天
# "W0"-"W6" - 周一到周日
# "midnight" - 午夜

# 添加到 logger
logger = logging.getLogger("my_app")
logger.addHandler(handler)
```

---

## 3. pdb 调试器

### 3.1 什么是 pdb？

pdb 是 Python **内置**的调试器，可以在代码中设置断点，暂停程序执行，检查变量状态。

```python
# code/05-pdb-basics.py
def calculate_discount(price, quantity, is_vip=False):
    """计算折扣价格"""
    subtotal = price * quantity          # 行 4
    
    if is_vip:                           # 行 6
        discount = 0.2                   # 行 7
    else:
        discount = 0.1                   # 行 9
    
    total = subtotal * (1 - discount)    # 行 12
    
    # 设置断点——程序会在这里暂停
    import pdb; pdb.set_trace()          # 行 15
    
    return total                         # 行 17

# Python 3.7+ 可以直接用 breakpoint()
def calculate_discount_v2(price, quantity, is_vip=False):
    subtotal = price * quantity
    if is_vip:
        discount = 0.2
    else:
        discount = 0.1
    total = subtotal * (1 - discount)
    breakpoint()  # 等价于 import pdb; pdb.set_trace()
    return total

result = calculate_discount(100, 3, is_vip=True)
print(f"总价: {result}")
```

### 3.2 pdb 常用命令

```bash
# 运行后进入 pdb 调试模式
(pdb) 

# ========== 查看代码 ==========
(pdb) l          # list - 显示当前位置前后 11 行
(pdb) l 10,20    # 显示第 10-20 行

# ========== 控制执行 ==========
(pdb) n          # next - 执行下一行（不进入函数）
(pdb) s          # step - 执行下一行（进入函数）
(pdb) c          # continue - 继续执行到下一个断点
(pdb) r          # return - 执行到当前函数返回
(pdb) q          # quit - 退出调试器

# ========== 检查变量 ==========
(pdb) p variable     # 打印变量值
(pdb) p locals()     # 打印所有局部变量
(pdb) p dir()        # 打印当前作用域
(pdb) p type(obj)    # 打印对象类型

# ========== 设置断点 ==========
(pdb) b 15           # 在第 15 行设置断点
(pdb) b function_name # 在函数入口设置断点
(pdb) b              # 查看所有断点
(pdb) cl 15          # 清除第 15 行的断点
(pdb) cl             # 清除所有断点

# ========== 条件断点 ==========
(pdb) b 15, price > 100  # 只在 price > 100 时中断

# ========== 执行表达式 ==========
(pdb) !import pdb; pdb.set_trace()  # 在调试中设置新断点
(pdb) e import json; json.dumps(locals())  # 执行任意表达式
```

### 3.3 代码内嵌 pdb

```python
# 方式 1：传统写法
import pdb; pdb.set_trace()

# 方式 2：Python 3.7+ 推荐
breakpoint()

# 方式 3：条件断点
if some_condition:
    breakpoint()

# 方式 4：在 except 中调试
try:
    dangerous_operation()
except Exception:
    breakpoint()  # 异常发生时暂停，检查错误
```

---

## 4. 现代调试工具

### 4.1 ipdb（增强版 pdb）

```bash
pip install ipdb
```

```python
# ipdb 提供语法高亮、自动补全
import ipdb; ipdb.set_trace()
# 或
breakpoint()  # 如果配置了 PYTHONBREAKPOINT=ipdb.set_trace
```

### 4.2 IDE 调试

```python
# VS Code / PyCharm 的图形化调试更友好：
# 1. 在代码行号左侧点击设置断点
# 2. 点击调试按钮启动
# 3. 悬停查看变量值
# 4. 步进、步过、步出
# 5. 查看调用栈
# 6. 条件断点
```

### 4.3 logging + pdb 组合

```python
import logging

logger = logging.getLogger(__name__)

def process_order(order):
    logger.debug(f"收到订单: {order}")
    
    try:
        result = calculate_total(order)
        logger.info(f"订单处理成功: {result}")
        return result
    except Exception as e:
        logger.error(f"订单处理失败: {e}", exc_info=True)
        # exc_info=True 会记录完整的堆栈信息
        raise
```

---

## 5. 日志最佳实践

### 5.1 该用什么级别？

```python
# DEBUG: 开发时的详细信息
logger.debug(f"SQL: SELECT * FROM users WHERE id={user_id}")

# INFO: 关键业务事件
logger.info(f"用户 {username} 登录成功")
logger.info(f"订单 #{order_id} 已创建")

# WARNING: 潜在问题
logger.warning(f"磁盘空间不足: {free_space}MB")
logger.warning(f"API 响应慢: {elapsed:.2f}秒")

# ERROR: 功能失败
logger.error(f"发送邮件失败: {recipient}", exc_info=True)

# CRITICAL: 系统级故障
logger.critical(f"数据库连接池耗尽!")
```

### 5.2 敏感信息处理

```python
# ❌ 不要记录敏感信息
logger.info(f"用户密码: {password}")  # 千万不要！
logger.info(f"信用卡号: {card_number}")  # 违反 PCI DSS！

# ✅ 脱敏处理
def mask_email(email: str) -> str:
    """邮箱脱敏"""
    local, domain = email.split("@")
    return f"{local[0]}***@{domain}"

logger.info(f"用户邮箱: {mask_email(user.email)}")
```

### 5.3 性能考虑

```python
# ❌ 避免不必要的字符串拼接
logger.debug(f"Processing item {item.id} with name {item.name}")
# 即使 DEBUG 级别被禁用，字符串拼接仍然会执行！

# ✅ 使用延迟格式化
logger.debug("Processing item %s with name %s", item.id, item.name)
# 只有在需要输出时才格式化字符串

# ✅ 或者使用 isEnabledFor 检查
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"详细信息: {expensive_computation()}")
```

---

## 实战项目：生产级日志配置

### 完整代码

```python
# code/06-production-logging.py
"""
📝 生产级日志配置 —— 完整实战项目
功能：多 Handler、日志轮转、格式化、性能优化
"""
import logging
import logging.config
import logging.handlers
import os
from datetime import datetime


# ========== 日志配置字典 ==========
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    # 格式器
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": ("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d "
                       "%(funcName)s() [%(process)d:%(thread)d] - %(message)s"),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            # JSON 格式（方便 ELK 等日志系统收集）
            "format": '{"time":"%(asctime)s","level":"%(levelname)s",'
                      '"logger":"%(name)s","line":%(lineno)d,'
                      '"function":"%(funcName)s","message":"%(message)s"}',
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },

    # 过滤器
    "filters": {
        "context_filter": {
            "()": "production_logging.ContextFilter",
        },
    },

    # 处理器
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/app.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "logs/error.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "timed_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "logs/timed.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "encoding": "utf-8",
        },
    },

    # 日志记录器
    "loggers": {
        "": {  # 根 logger
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file"],
        },
        "my_app": {
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file", "timed_file"],
            "propagate": False,
        },
        "my_app.api": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },

    # 根 logger 兜底
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}


# ========== 自定义过滤器 ==========
class ContextFilter(logging.Filter):
    """添加上下文信息到日志"""

    def __init__(self):
        super().__init__()
        self.request_id = None
        self.user_id = None

    def filter(self, record):
        record.request_id = self.request_id or "N/A"
        record.user_id = self.user_id or "N/A"
        return True


# ========== 初始化 ==========
def setup_logging():
    """初始化日志系统"""
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)

    # 应用配置
    logging.config.dictConfig(LOGGING_CONFIG)

    # 添加自定义过滤器
    logger = logging.getLogger("my_app")
    context_filter = ContextFilter()
    logger.addFilter(context_filter)

    # 减少第三方库的日志噪音
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return context_filter


# ========== 业务代码示例 ==========
def setup_logging():
    """初始化日志系统"""
    os.makedirs("logs", exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)
    context_filter = ContextFilter()
    logger = logging.getLogger("my_app")
    logger.addFilter(context_filter)
    return context_filter


class OrderService:
    """订单服务——展示日志使用方式"""

    def __init__(self):
        self.logger = logging.getLogger("my_app.order")

    def create_order(self, user_id: int, items: list) -> dict:
        """创建订单"""
        self.logger.info(f"创建订单: user_id={user_id}, items={len(items)} 个")

        try:
            # 业务逻辑
            order_id = 1001
            total = sum(item["price"] * item["qty"] for item in items)

            self.logger.info(f"订单创建成功: order_id={order_id}, total={total}")
            return {"order_id": order_id, "total": total}

        except Exception as e:
            self.logger.error(f"订单创建失败: {e}", exc_info=True)
            raise


class UserService:
    """用户服务"""

    def __init__(self):
        self.logger = logging.getLogger("my_app.user")

    def login(self, username: str, password: str) -> bool:
        """用户登录"""
        self.logger.info(f"用户登录尝试: {username}")

        if username == "admin" and password == "123456":
            self.logger.info(f"用户 {username} 登录成功")
            return True
        else:
            self.logger.warning(f"用户 {username} 登录失败: 密码错误")
            return False


# ========== 运行示例 ==========
if __name__ == "__main__":
    context_filter = setup_logging()
    logger = logging.getLogger("my_app")

    logger.info("=" * 50)
    logger.info("🚀 应用启动")
    logger.info("=" * 50)

    # 模拟请求上下文
    context_filter.request_id = "req-12345"
    context_filter.user_id = "user-001"

    # 用户服务
    user_service = UserService()
    user_service.login("admin", "123456")
    user_service.login("hacker", "wrong")

    # 订单服务
    order_service = OrderService()
    order_service.create_order(
        user_id=1,
        items=[
            {"name": "Python书", "price": 59.9, "qty": 1},
            {"name": "键盘", "price": 299, "qty": 1},
        ]
    )

    # 测试异常日志
    try:
        1 / 0
    except Exception:
        logger.error("数学运算错误", exc_info=True)

    logger.info("=" * 50)
    logger.info("🛑 应用关闭")
    logger.info("=" * 50)
```

---

## 今日总结

- **logging 模块**是 Python 标准的日志方案，替代 print
- **五个日志级别**：DEBUG < INFO < WARNING < ERROR < CRITICAL
- **三大组件**：Logger（记录器）→ Handler（处理器）→ Formatter（格式器）
- **字典配置** `logging.config.dictConfig()` 是最灵活的配置方式
- **日志轮转**防止日志文件无限增长（RotatingFileHandler / TimedRotatingFileHandler）
- **pdb 调试器**：`breakpoint()` 暂停程序，`n` 下一步，`p` 打印变量
- **生产环境**：记录到文件、轮转备份、避免敏感信息、延迟格式化

## 练习题

### 练习 1：日志配置 ⭐⭐
为一个 Web 应用配置日志系统：
- 控制台输出 INFO 及以上
- 文件记录 DEBUG 及以上（带行号和函数名）
- 错误文件只记录 ERROR 及以上
- 日志轮转：每个文件最大 5MB，保留 10 个备份

### 练习 2：pdb 调试实践 ⭐⭐
使用 pdb 调试以下代码：
- 找出 bug 并修复
- 练习设置条件断点
- 练习检查调用栈

### 练习 3：日志分析脚本 ⭐⭐⭐
编写一个日志分析脚本：
- 读取日志文件
- 统计每种级别的日志数量
- 查找所有 ERROR 日志
- 按时间范围过滤日志
- 生成分析报告

### 练习 4：结构化日志 ⭐⭐⭐
实现 JSON 格式的结构化日志：
- 每条日志是一个 JSON 对象
- 包含时间、级别、模块、消息、上下文
- 可以直接被 ELK 等日志系统收集

### 练习 5：分布式日志 ⭐⭐⭐⭐
设计一个分布式日志方案：
- 不同服务的日志统一收集
- 使用 request_id 关联同一请求的日志
- 实现日志聚合和查询
- 告警机制（ERROR 数量超过阈值时通知）

## 🎉 恭喜完成 Phase 5！

你已经完成了标准库与生态系统的学习：
- Day 067: FastAPI 入门
- Day 068: 数据库基础
- Day 069: ORM 深入（SQLAlchemy）
- Day 070: 测试基础
- Day 071: 日志与调试

接下来将进入 **Phase 6: 高级主题与项目实战**，学习更高级的 Python 特性和真实项目开发！
