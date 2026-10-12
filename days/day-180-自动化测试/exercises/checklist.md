# 今日学习检查表

## 完成清单

- [ ] 阅读 README.md 理解自动化测试概念
- [ ] 运行基础测试示例（01-基础用法.py）
- [ ] 运行进阶测试示例（02-进阶用法.py）
- [ ] 运行实战案例（03-实战案例.py）
- [ ] 完成思考题练习
- [ ] 编写自己的测试用例

## 练习题

### 基础练习

1. 编写一个函数 `is_even(n)` 判断一个整数是否为偶数，并为其编写 pytest 测试用例。
   - 正常情况：2, 4, 6, 8, 10 返回 True
   - 负数情况：-2, -4 返回 True
   - 边界情况：0 返回 True
   - 奇数情况：1, 3, 5, 7, 9 返回 False

2. 编写一个函数 `factorial(n)` 计算阶乘，并测试：
   - 基本情况：factorial(0) = 1
   - 正常情况：factorial(5) = 120
   - 异常情况：负数输入应抛出 ValueError

### 进阶练习

3. 编写一个简单的计算器类 Calculator，包含加、减、乘、除四种运算。
   - 为每种运算编写测试用例
   - 重点测试除法中的除零异常
   - 使用 parametrize 为加法编写多组测试数据

4. 创建一个测试 fixture，用于提供临时数据库连接（可以使用内存 SQLite）。
   - 编写一个测试用例使用此 fixture 进行数据增删改查操作
   - 验证数据在测试之间的隔离性

### 挑战题（可选）

5. 编写一个装饰器 `@retry(max_attempts=3)`，用于自动重试失败的函数。
   - 编写测试验证重试机制
   - 测试场景：网络请求偶尔失败的情况

6. 使用 Mock 测试一个依赖外部API的函数。
   - 创建一个从天气API获取温度的函数
   - 使用 unittest.mock.patch 模拟API响应
   - 测试不同返回值下的业务逻辑

## 参考答案

（教师使用，学习完毕后可查看）

1. `is_even` 函数实现：
```python
def is_even(n):
    """判断整数是否为偶数"""
    return n % 2 == 0
```

2. `factorial` 函数实现：
```python
def factorial(n):
    """计算阶乘"""
    if n < 0:
        raise ValueError("负数没有阶乘")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
```

3. Calculator 类实现：
```python
class Calculator:
    def add(self, a, b): return a + b
    def subtract(self, a, b): return a - b
    def multiply(self, a, b): return a * b
    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("不能除以零")
        return a / b
```