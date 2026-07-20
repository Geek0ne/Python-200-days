# Day 074 — 单元测试进阶

## 概述

Day 070 我们学习了测试基础（unittest 和 pytest），今天我们深入**高级测试技巧**。

- 测试驱动开发（TDD）：先写测试，再写代码
- 参数化测试：用一个测试函数覆盖多个场景
- 集成测试 vs 单元测试：不同层级的测试策略
- 异步测试：如何测试 asyncio 代码
- **实战：为 Flask API 写完整测试套件**

> 💡 **为什么测试进阶很重要？**
> - 基础测试只能验证"对不对"，进阶测试能验证"好不好"
> - TDD 能提高代码质量和设计水平
> - 参数化测试减少重复代码
> - 集成测试确保模块间协作正确

---

## 1. 测试驱动开发（TDD）

### 1.1 TDD 流程

```python
# TDD 的核心循环：
# 1. Red：写一个失败的测试
# 2. Green：写最少的代码让测试通过
# 3. Refactor：重构代码，保持测试通过

# 示例：实现一个计算器类
# 第一步：写测试
"""
test_calculator.py
"""
import pytest
from calculator import Calculator


def test_add():
    """测试加法"""
    calc = Calculator()
    assert calc.add(2, 3) == 5
    assert calc.add(-1, 1) == 0
    assert calc.add(0, 0) == 0


def test_subtract():
    """测试减法"""
    calc = Calculator()
    assert calc.subtract(5, 3) == 2
    assert calc.subtract(0, 5) == -5


def test_multiply():
    """测试乘法"""
    calc = Calculator()
    assert calc.multiply(2, 3) == 6
    assert calc.multiply(-1, 3) == -3
    assert calc.multiply(0, 5) == 0


def test_divide():
    """测试除法"""
    calc = Calculator()
    assert calc.divide(6, 3) == 2.0
    assert calc.divide(5, 2) == 2.5


def test_divide_by_zero():
    """测试除以零"""
    calc = Calculator()
    with pytest.raises(ZeroDivisionError):
        calc.divide(1, 0)
"""

# 第二步：写最少的代码让测试通过
"""
calculator.py
"""
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        return a / b
"""

# 第三步：重构（如果需要）
# 目前代码已经很简洁，不需要重构
```

### 1.2 TDD 实战：字符串计算器

```python
"""
TDD 实战：字符串计算器
输入格式："1,2,3" 返回 6
支持自定义分隔符：//;\n1;2;3 返回 6
"""
import pytest


# 第一步：写测试
class TestStringCalculator:
    """字符串计算器测试"""

    def test_empty_string(self):
        """空字符串返回 0"""
        assert add("") == 0

    def test_single_number(self):
        """单个数字返回自身"""
        assert add("1") == 1

    def test_two_numbers(self):
        """两个数字相加"""
        assert add("1,2") == 3

    def test_multiple_numbers(self):
        """多个数字相加"""
        assert add("1,2,3,4,5") == 15

    def test_custom_delimiter(self):
        """自定义分隔符"""
        assert add("//;\n1;2;3") == 6

    def test_negative_numbers(self):
        """负数抛出异常"""
        with pytest.raises(ValueError, match="负数不允许"):
            add("1,-2,3")

    def test_numbers_greater_than_1000(self):
        """大于1000的数字忽略"""
        assert add("1000,1001,2") == 1002


# 第二步：实现
def add(numbers: str) -> int:
    """字符串计算器

    Args:
        numbers: 逗号分隔的数字字符串，支持自定义分隔符

    Returns:
        数字之和

    Raises:
        ValueError: 包含负数时抛出
    """
    if not numbers:
        return 0

    # 处理自定义分隔符
    if numbers.startswith("//"):
        delimiter = numbers[2]
        numbers = numbers[4:]

    # 分割并转换为整数
    nums = [int(n) for n in numbers.split(",")]

    # 检查负数
    negatives = [n for n in nums if n < 0]
    if negatives:
        raise ValueError(f"负数不允许: {negatives}")

    # 过滤大于1000的数字
    nums = [n for n in nums if n <= 1000]

    return sum(nums)


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 1.3 TDD 的好处

```python
# 1. 设计更好
#    - 先考虑接口，再考虑实现
#    - 代码更模块化、更易测试

# 2. Bug 更少
#    - 每个功能都有测试覆盖
#    - 重构时有安全网

# 3. 文档更全
#    - 测试就是最好的文档
#    - 展示了代码的各种用法

# 4. 重构更安全
#    - 修改代码后立即知道是否破坏了功能
#    - 有信心进行大胆的重构
```

---

## 2. 参数化测试

### 2.1 pytest.mark.parametrize

```python
import pytest


# 基本用法
@pytest.mark.parametrize("input,expected", [
    ("hello", 5),
    ("", 0),
    ("a", 1),
    ("hello world", 11),
])
def test_string_length(input, expected):
    """测试字符串长度"""
    assert len(input) == expected


# 多个参数
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
    (100, 200, 300),
])
def test_addition(a, b, expected):
    """测试加法"""
    assert a + b == expected


# 嵌套参数化
@pytest.mark.parametrize("x", [1, 2, 3])
@pytest.mark.parametrize("y", [10, 20])
def test_multiply(x, y):
    """测试乘法（6个组合）"""
    result = x * y
    assert result > 0
    assert result == x * y


# 使用 ids 自定义测试名称
@pytest.mark.parametrize("input,expected", [
    (None, False),       # None
    (0, False),          # 零
    ("", False),         # 空字符串
    ([], False),         # 空列表
    ({}, False),         # 空字典
    (1, True),           # 非零数字
    ("hello", True),     # 非空字符串
    ([1, 2], True),      # 非空列表
], ids=["none", "zero", "empty-string", "empty-list",
        "empty-dict", "nonzero", "non-empty-string", "non-empty-list"])
def test_bool_conversion(value, expected):
    """测试布尔转换"""
    assert bool(value) == expected
```

### 2.2 高级参数化

```python
import pytest
from dataclasses import dataclass


# 使用 fixture + parametrize
@pytest.fixture
def sample_data():
    """测试数据 fixture"""
    return {"name": "test", "value": 42}


@pytest.mark.parametrize("key,expected", [
    ("name", "test"),
    ("value", 42),
])
def test_dict_access(sample_data, key, expected):
    """测试字典访问"""
    assert sample_data[key] == expected


# 使用类级别的参数化
class TestMath:
    """数学运算测试类"""

    @pytest.mark.parametrize("a,b,operation,expected", [
        (2, 3, "add", 5),
        (5, 3, "subtract", 2),
        (2, 3, "multiply", 6),
        (6, 3, "divide", 2.0),
    ])
    def test_operations(self, a, b, operation, expected):
        """测试各种数学运算"""
        if operation == "add":
            assert a + b == expected
        elif operation == "subtract":
            assert a - b == expected
        elif operation == "multiply":
            assert a * b == expected
        elif operation == "divide":
            assert a / b == expected


# 使用 parametrize + mark
@pytest.mark.parametrize("input,expected", [
    pytest.param(1, 1.0, id="int-to-float"),
    pytest.param(2.5, 2.5, id="float-to-float"),
    pytest.param("3", 3.0, id="str-to-float"),
],)
def test_convert_to_float(input, expected):
    """测试转换为浮点数"""
    assert float(input) == expected
```

### 2.3 参数化 vs 循环

```python
import pytest


# ❌ 不推荐：循环写测试
def test_bad_practice():
    """不推荐的循环测试"""
    test_cases = [
        (1, 2, 3),
        (0, 0, 0),
        (-1, 1, 0),
    ]
    for a, b, expected in test_cases:
        assert a + b == expected  # 失败时无法知道是哪个用例


# ✅ 推荐：参数化
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
])
def test_addition(a, b, expected):
    """参数化测试"""
    assert a + b == expected
    # 失败时会显示具体是哪个用例失败
```

**避坑说明：**
- ⚠️ 参数化测试的用例太多会导致测试时间过长
- ⚠️ 参数化测试失败时，错误信息可能不够清晰
- ⚠️ 复杂的测试逻辑不要参数化，保持简单

---

## 3. 集成测试 vs 单元测试

### 3.1 测试金字塔

```
        /\
       /  \        E2E 测试（少量）
      /    \       集成测试（适量）
     /      \      单元测试（大量）
    /________\
```

### 3.2 单元测试

```python
# 单元测试：测试单个函数或类
# 特点：快速、独立、不依赖外部资源

import pytest


def calculate_discount(price, discount_percent):
    """计算折扣后的价格"""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("折扣百分比必须在 0-100 之间")
    return price * (1 - discount_percent / 100)


class TestCalculateDiscount:
    """折扣计算测试"""

    def test_no_discount(self):
        """无折扣"""
        assert calculate_discount(100, 0) == 100

    def test_full_discount(self):
        """全额折扣"""
        assert calculate_discount(100, 100) == 0

    def test_half_discount(self):
        """半价折扣"""
        assert calculate_discount(100, 50) == 50

    def test_invalid_discount_negative(self):
        """负数折扣"""
        with pytest.raises(ValueError):
            calculate_discount(100, -10)

    def test_invalid_discount_over_100(self):
        """超过100%的折扣"""
        with pytest.raises(ValueError):
            calculate_discount(100, 150)
```

### 3.3 集成测试

```python
# 集成测试：测试多个模块协作
# 特点：可能依赖数据库、网络、文件系统

import pytest
import tempfile
import os


class TestFileProcessing:
    """文件处理集成测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_read_write_file(self, temp_dir):
        """测试文件读写"""
        filepath = os.path.join(temp_dir, "test.txt")

        # 写入文件
        with open(filepath, "w") as f:
            f.write("Hello, World!")

        # 读取文件
        with open(filepath, "r") as f:
            content = f.read()

        assert content == "Hello, World!"

    def test_process_multiple_files(self, temp_dir):
        """测试处理多个文件"""
        # 创建多个文件
        for i in range(5):
            filepath = os.path.join(temp_dir, f"file_{i}.txt")
            with open(filepath, "w") as f:
                f.write(f"Content {i}")

        # 读取所有文件
        contents = []
        for filename in sorted(os.listdir(temp_dir)):
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, "r") as f:
                contents.append(f.read())

        assert len(contents) == 5
        assert contents[0] == "Content 0"
```

### 3.4 测试分类

```python
# 测试分类标记
import pytest


@pytest.mark.unit
def test_unit_example():
    """单元测试"""
    assert 1 + 1 == 2


@pytest.mark.integration
def test_integration_example():
    """集成测试"""
    # 可能需要数据库或网络
    pass


@pytest.mark.slow
def test_slow_example():
    """慢测试"""
    import time
    time.sleep(1)  # 模拟耗时操作


# 运行特定类型的测试
# pytest -m unit        # 只运行单元测试
# pytest -m integration # 只运行集成测试
# pytest -m "not slow"  # 排除慢测试
```

---

## 4. 测试异步代码

### 4.1 pytest-asyncio 基础

```python
import pytest
import asyncio


# 定义异步函数
async def async_add(a, b):
    """异步加法"""
    await asyncio.sleep(0.1)  # 模拟异步操作
    return a + b


# 测试异步函数
@pytest.mark.asyncio
async def test_async_add():
    """测试异步加法"""
    result = await async_add(2, 3)
    assert result == 5


# 异步 fixture
@pytest.fixture
async def async_data():
    """异步 fixture"""
    await asyncio.sleep(0.1)
    return {"key": "value"}


@pytest.mark.asyncio
async def test_with_async_fixture(async_data):
    """使用异步 fixture"""
    assert async_data["key"] == "value"
```

### 4.2 异步类测试

```python
import pytest
import asyncio


class AsyncAPIClient:
    """异步 API 客户端"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = None

    async def connect(self):
        """连接到服务器"""
        await asyncio.sleep(0.1)  # 模拟连接
        self.session = True

    async def disconnect(self):
        """断开连接"""
        await asyncio.sleep(0.1)
        self.session = None

    async def get(self, path):
        """发送 GET 请求"""
        if not self.session:
            raise RuntimeError("未连接")
        await asyncio.sleep(0.1)
        return {"status": "ok", "path": path}


@pytest.fixture
async def api_client():
    """异步 API 客户端 fixture"""
    client = AsyncAPIClient("https://api.example.com")
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_api_connect(api_client):
    """测试 API 连接"""
    assert api_client.session is True


@pytest.mark.asyncio
async def test_api_get(api_client):
    """测试 API GET 请求"""
    result = await api_client.get("/users")
    assert result["status"] == "ok"
    assert result["path"] == "/users"
```

### 4.3 异步测试最佳实践

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch


# 使用 AsyncMock 模拟异步对象
@pytest.mark.asyncio
async def test_with_async_mock():
    """使用异步 mock"""
    mock_func = AsyncMock(return_value=42)

    result = await mock_func()

    assert result == 42
    mock_func.assert_called_once()


# 使用 patch 模拟异步方法
@pytest.mark.asyncio
async def test_with_patch():
    """使用 patch 模拟异步方法"""
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await asyncio.sleep(1)
        mock_sleep.assert_called_once_with(1)


# 异步生成器测试
@pytest.mark.asyncio
async def test_async_generator():
    """测试异步生成器"""

    async def async_range(n):
        for i in range(n):
            await asyncio.sleep(0.01)
            yield i

    results = []
    async for num in async_range(5):
        results.append(num)

    assert results == [0, 1, 2, 3, 4]


# 超时测试
@pytest.mark.asyncio
async def test_with_timeout():
    """测试异步操作超时"""
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            asyncio.sleep(10),
            timeout=0.1
        )
```

**避坑说明：**
- ⚠️ 异步测试必须使用 `@pytest.mark.asyncio`
- ⚠️ 不要在异步测试中使用 `time.sleep()`
- ⚠️ 使用 `AsyncMock` 模拟异步对象
- ⚠️ 注意异步测试的超时设置

---

## 5. 测试覆盖率

### 5.1 安装 pytest-cov

```bash
pip install pytest-cov
```

### 5.2 生成覆盖率报告

```bash
# 基本用法
pytest --cov=my_package

# 生成 HTML 报告
pytest --cov=my_package --cov-report=html

# 显示未覆盖的行
pytest --cov=my_package --cov-report=term-missing

# 设置覆盖率阈值
pytest --cov=my_package --cov-fail-under=80
```

### 5.3 覆盖率配置

```ini
# setup.cfg 或 pyproject.toml
[tool:pytest]
addopts = --cov=my_package --cov-report=term-missing

[coverage:run]
source = my_package
omit = tests/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    if __name__ == .__main__
    raise NotImplementedError
```

---

## 实战项目：为 Flask API 写完整测试套件

```python
"""
实战：为 Flask API 写完整测试套件
运行方式：pytest test_flask_api.py -v
"""
import pytest
from flask import Flask, jsonify, request


# ========== 应用代码 ==========
def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    app.config["TESTING"] = True

    # 内存数据库
    users = {}
    next_id = 1

    @app.route("/users", methods=["GET"])
    def get_users():
        """获取所有用户"""
        return jsonify(list(users.values()))

    @app.route("/users/<int:user_id>", methods=["GET"])
    def get_user(user_id):
        """获取单个用户"""
        user = users.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        return jsonify(user)

    @app.route("/users", methods=["POST"])
    def create_user():
        """创建用户"""
        nonlocal next_id
        data = request.get_json()

        if not data or "name" not in data:
            return jsonify({"error": "缺少 name 字段"}), 400

        user = {
            "id": next_id,
            "name": data["name"],
            "email": data.get("email", ""),
        }
        users[next_id] = user
        next_id += 1

        return jsonify(user), 201

    @app.route("/users/<int:user_id>", methods=["PUT"])
    def update_user(user_id):
        """更新用户"""
        user = users.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404

        data = request.get_json()
        if "name" in data:
            user["name"] = data["name"]
        if "email" in data:
            user["email"] = data["email"]

        return jsonify(user)

    @app.route("/users/<int:user_id>", methods=["DELETE"])
    def delete_user(user_id):
        """删除用户"""
        if user_id not in users:
            return jsonify({"error": "用户不存在"}), 404

        del users[user_id]
        return "", 204

    return app


# ========== 测试代码 ==========
@pytest.fixture
def app():
    """创建测试应用"""
    app = create_app()
    yield app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestGetUsers:
    """测试获取用户列表"""

    def test_empty_list(self, client):
        """空列表"""
        response = client.get("/users")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_with_users(self, client):
        """有用户时"""
        # 先创建用户
        client.post("/users", json={"name": "Alice"})
        client.post("/users", json={"name": "Bob"})

        response = client.get("/users")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2


class TestGetUser:
    """测试获取单个用户"""

    def test_existing_user(self, client):
        """存在的用户"""
        # 创建用户
        response = client.post("/users", json={"name": "Alice"})
        user_id = response.get_json()["id"]

        # 获取用户
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.get_json()["name"] == "Alice"

    def test_nonexistent_user(self, client):
        """不存在的用户"""
        response = client.get("/users/999")
        assert response.status_code == 404
        assert "用户不存在" in response.get_json()["error"]


class TestCreateUser:
    """测试创建用户"""

    def test_create_success(self, client):
        """成功创建"""
        response = client.post("/users", json={
            "name": "Alice",
            "email": "alice@example.com"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Alice"
        assert data["email"] == "alice@example.com"
        assert "id" in data

    def test_create_without_name(self, client):
        """缺少 name 字段"""
        response = client.post("/users", json={"email": "test@example.com"})
        assert response.status_code == 400
        assert "缺少 name 字段" in response.get_json()["error"]

    def test_create_empty_body(self, client):
        """空请求体"""
        response = client.post("/users", json={})
        assert response.status_code == 400

    def test_create_multiple_users(self, client):
        """创建多个用户"""
        for i in range(3):
            response = client.post("/users", json={"name": f"User{i}"})
            assert response.status_code == 201

        response = client.get("/users")
        assert len(response.get_json()) == 3


class TestUpdateUser:
    """测试更新用户"""

    def test_update_name(self, client):
        """更新名字"""
        # 创建用户
        response = client.post("/users", json={"name": "Alice"})
        user_id = response.get_json()["id"]

        # 更新名字
        response = client.put(f"/users/{user_id}", json={"name": "Bob"})
        assert response.status_code == 200
        assert response.get_json()["name"] == "Bob"

    def test_update_nonexistent_user(self, client):
        """更新不存在的用户"""
        response = client.put("/users/999", json={"name": "Bob"})
        assert response.status_code == 404


class TestDeleteUser:
    """测试删除用户"""

    def test_delete_success(self, client):
        """成功删除"""
        # 创建用户
        response = client.post("/users", json={"name": "Alice"})
        user_id = response.get_json()["id"]

        # 删除用户
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 204

        # 验证已删除
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_user(self, client):
        """删除不存在的用户"""
        response = client.delete("/users/999")
        assert response.status_code == 404


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 今日总结

- **TDD**：先写测试，再写代码，Red-Green-Refactor 循环
- **参数化测试**：`@pytest.mark.parametrize` 减少重复代码
- **集成测试**：测试多个模块协作，可能依赖外部资源
- **异步测试**：`@pytest.mark.asyncio` + `AsyncMock`
- **覆盖率**：`pytest-cov` 生成覆盖率报告

---

## 练习题

### 练习 1：TDD 实践 ⭐⭐
用 TDD 方式实现一个购物车类：
- 添加商品
- 移除商品
- 计算总价
- 应用折扣
- 清空购物车

### 练习 2：参数化测试 ⭐⭐
为以下函数编写参数化测试：
- 字符串反转
- 斐波那契数列
- 质数判断

### 练习 3：集成测试 ⭐⭐⭐
为一个简单的文件处理系统写集成测试：
- 创建临时文件
- 读取文件内容
- 处理文件（转换大小写）
- 写入新文件
- 验证结果

### 练习 4：异步测试 ⭐⭐⭐
测试一个异步 HTTP 客户端：
- 使用 aioresponses 模拟 HTTP 请求
- 测试成功和失败场景
- 测试超时处理
- 测试重试机制

### 练习 5：完整测试套件 ⭐⭐⭐⭐
为一个 REST API 写完整的测试套件：
- 单元测试（工具函数）
- 集成测试（数据库操作）
- API 测试（端点测试）
- 性能测试（响应时间）
- 生成覆盖率报告

---

## 明天预告

Day 075 我们将进行**阶段项目：标准库综合实战**——构建一个完整的 CLI 工具，综合运用 Phase 5 所有知识！
