# Day 072 — 测试与数据库安全

> 🎯 **今日目标**：建立从单元测试到 TDD 的完整质量防线，并把安全纳入测试视角——用参数化与 ORM 防护堵死 SQL 注入。

## 第一部分：测试基础

### 概述

前面 69 天我们学了很多 Python 知识，但如何**确保代码是正确的**？答案是**测试**。

测试是软件开发中**最重要**的环节之一。没有测试的代码就像没有安全带的汽车——平时看起来没问题，出事就晚了。

**今天你将学到：**
1. unittest 框架——Python 内置的测试框架
2. pytest 实战——更现代、更简洁的测试工具
3. Mock 与 Patch——模拟外部依赖
4. 测试覆盖率——量化测试质量
5. **实战：API 测试套件**——为 FastAPI 应用编写完整测试

> 💡 **测试的价值**：
> - **发现 Bug**：在代码上线前发现问题
> - **防止回归**：修改代码后确保旧功能不被破坏
> - **文档作用**：测试用例就是最好的使用文档
> - **重构信心**：有测试保护，放心重构代码

---

### 1. unittest 框架

#### 1.1 什么是 unittest？

unittest 是 Python **内置**的测试框架，基于 xUnit 风格：

```python
# code/01-unittest-basics.py
import unittest


# ========== 被测试的代码 ==========
def add(a: int, b: int) -> int:
    """两数相加"""
    return a + b

def divide(a: float, b: float) -> float:
    """两数相除"""
    if b == 0:
        raise ValueError("除数不能为零")
    return a / b

def is_even(n: int) -> bool:
    """判断是否为偶数"""
    return n % 2 == 0


# ========== 测试类 ==========
class TestMathFunctions(unittest.TestCase):
    """
    测试数学函数
    
    规范：
    - 测试类必须继承 unittest.TestCase
    - 测试方法必须以 test_ 开头
    - 每个测试方法独立运行
    """

    def test_add_positive(self):
        """测试正数相加"""
        self.assertEqual(add(2, 3), 5)

    def test_add_negative(self):
        """测试负数相加"""
        self.assertEqual(add(-1, -1), -2)

    def test_add_zero(self):
        """测试加零"""
        self.assertEqual(add(5, 0), 5)

    def test_divide_normal(self):
        """测试正常除法"""
        self.assertAlmostEqual(divide(10, 3), 3.333, places=2)

    def test_divide_by_zero(self):
        """测试除以零"""
        with self.assertRaises(ValueError):
            divide(10, 0)

    def test_is_even(self):
        """测试偶数判断"""
        self.assertTrue(is_even(4))
        self.assertFalse(is_even(3))
        self.assertTrue(is_even(0))
        self.assertFalse(is_even(-1))


# ========== setUp 和 tearDown ==========
class TestWithSetup(unittest.TestCase):
    """
    setUp: 每个测试方法执行前调用（准备数据）
    tearDown: 每个测试方法执行后调用（清理资源）
    """

    def setUp(self):
        """每个测试前执行"""
        self.data = [3, 1, 4, 1, 5, 9, 2, 6]
        print(f"\n  setUp: 准备数据 {self.data}")

    def tearDown(self):
        """每个测试后执行"""
        print(f"  tearDown: 清理完成")

    def test_length(self):
        self.assertEqual(len(self.data), 8)

    def test_sorted(self):
        self.assertEqual(sorted(self.data), [1, 1, 2, 3, 4, 5, 6, 9])

    def test_max(self):
        self.assertEqual(max(self.data), 9)


# ========== 运行测试 ==========
if __name__ == "__main__":
    unittest.main(verbosity=2)
    # verbosity=2 显示详细输出
```

#### 1.2 常用断言方法

```python
# 断言方法速查表
self.assertEqual(a, b)        # a == b
self.assertNotEqual(a, b)     # a != b
self.assertTrue(x)            # x is True
self.assertFalse(x)           # x is False
self.assertIs(a, b)           # a is b（同一对象）
self.assertIsNone(x)          # x is None
self.assertIn(a, b)           # a in b
self.assertNotIn(a, b)        # a not in b
self.assertIsInstance(a, B)   # isinstance(a, B)
self.assertAlmostEqual(a, b, places=2)  # 浮点数近似相等
self.assertGreater(a, b)      # a > b
self.assertLess(a, b)         # a < b
self.assertRaises(E)          # 期望抛出异常 E
self.assertWarns(W)           # 期望产生警告 W
```

#### 1.3 测试组织

```python
# test_calculator.py
import unittest

class TestAdd(unittest.TestCase):
    """加法测试"""
    def test_add(self):
        self.assertEqual(1 + 1, 2)

class TestSubtract(unittest.TestCase):
    """减法测试"""
    def test_subtract(self):
        self.assertEqual(5 - 3, 2)

# 运行方式：
# python -m unittest test_calculator.py
# python -m unittest discover -s tests/  # 自动发现 tests/ 下所有测试
# python -m unittest TestAdd  # 只运行 TestAdd 类
# python -m unittest TestAdd.test_add  # 只运行单个测试方法
```

---

### 2. pytest 实战

#### 2.1 为什么用 pytest？

pytest 比 unittest 更**简洁**、更**强大**：

```bash
pip install pytest
```

```python
# code/02-pytest-basics.py
"""
pytest 基础用法

pytest 的优势：
1. 不需要继承 TestCase
2. 测试函数直接以 test_ 开头即可
3. assert 语句更自然（不需要 self.assertEqual）
4. 丰富的插件生态
5. fixture 系统更灵活
"""


# ========== 被测试的代码 ==========
def greet(name: str) -> str:
    """打招呼"""
    if not name:
        return "Hello, World!"
    return f"Hello, {name}!"

def factorial(n: int) -> int:
    """计算阶乘"""
    if n < 0:
        raise ValueError("n 不能为负数")
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fizzbuzz(n: int) -> str:
    """FizzBuzz 问题"""
    if n % 15 == 0:
        return "FizzBuzz"
    elif n % 3 == 0:
        return "Fizz"
    elif n % 5 == 0:
        return "Buzz"
    return str(n)


# ========== 测试函数（pytest 风格） ==========
def test_greet_normal():
    assert greet("Alice") == "Hello, Alice!"

def test_greet_empty():
    assert greet("") == "Hello, World!"

def test_factorial():
    assert factorial(5) == 120
    assert factorial(0) == 1
    assert factorial(1) == 1

def test_factorial_negative():
    import pytest
    with pytest.raises(ValueError):
        factorial(-1)

def test_fizzbuzz():
    assert fizzbuzz(1) == "1"
    assert fizzbuzz(3) == "Fizz"
    assert fizzbuzz(5) == "Buzz"
    assert fizzbuzz(15) == "FizzBuzz"
    assert fizzbuzz(7) == "7"


# ========== 运行方式 ==========
# pytest 02-pytest-basics.py -v
# pytest 02-pytest-basics.py::test_greet_normal -v  # 运行单个测试
# pytest 02-pytest-basics.py -k "fizzbuzz" -v  # 按名称过滤
# pytest 02-pytest-basics.py --tb=short  # 简短的错误追踪
# pytest 02-pytest-basics.py -x  # 遇到第一个失败就停止
```

#### 2.2 Fixture：测试夹具

Fixture 是 pytest 的**核心特性**——提供测试前的准备和测试后的清理。

```python
# code/03-pytest-fixtures.py
import pytest


# ========== Fixture 定义 ==========

@pytest.fixture
def sample_data():
    """提供测试数据"""
    return [1, 2, 3, 4, 5]

@pytest.fixture
def temp_file(tmp_path):
    """
    创建临时文件
    
    tmp_path 是 pytest 内置 fixture，提供临时目录
    """
    file = tmp_path / "test.txt"
    file.write_text("Hello, pytest!")
    return file

@pytest.fixture
def db_connection():
    """
    模拟数据库连接——测试后自动清理
    
    yield 之前的代码 = setup（准备）
    yield 之后的代码 = teardown（清理）
    """
    print("\n  📦 建立数据库连接")
    connection = {"connected": True, "data": []}
    yield connection  #  yield 把连接传给测试函数
    print("  🔒 关闭数据库连接")
    connection["connected"] = False

@pytest.fixture(autouse=True)
def auto_setup():
    """
    autouse=True: 自动应用于所有测试
    
    不需要手动传入，每个测试都会执行
    """
    print("\n  ⚙️ 自动 setup")
    yield
    print("  ⚙️ 自动 teardown")


# ========== 使用 Fixture 的测试 ==========

def test_list_operations(sample_data):
    """使用 sample_data fixture"""
    assert len(sample_data) == 5
    assert sum(sample_data) == 15

def test_temp_file(temp_file):
    """使用临时文件 fixture"""
    content = temp_file.read_text()
    assert content == "Hello, pytest!"

def test_database_insert(db_connection):
    """使用数据库连接 fixture"""
    db_connection["data"].append("record1")
    assert len(db_connection["data"]) == 1
    assert db_connection["connected"] is True

def test_database_multiple(db_connection):
    """同一个 fixture 实例在每个测试中独立"""
    assert len(db_connection["data"]) == 0  # 新的连接


# ========== 参数化测试 ==========

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (0, 0),
    (-1, -2),
])
def test_double(input, expected):
    """参数化测试——一个测试函数运行多组数据"""
    assert input * 2 == expected

@pytest.mark.parametrize("a,b,expected", [
    (1, 1, 2),
    (2, 3, 5),
    (-1, 1, 0),
    (0, 0, 0),
])
def test_add(a, b, expected):
    assert a + b == expected


# ========== 异常测试 ==========

def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        1 / 0

def test_value_error_message():
    with pytest.raises(ValueError, match="不能为负"):
        raise ValueError("n 不能为负数")


# ========== 运行 ==========
# pytest 03-pytest-fixtures.py -v -s
# -s 表示显示 print 输出
```

#### 2.3 conftest.py：共享 Fixture

```python
# conftest.py（放在项目根目录，自动被 pytest 加载）
import pytest

@pytest.fixture
def api_client():
    """所有测试共享的 API 客户端"""
    # 在这里初始化
    client = {"base_url": "http://localhost:8000"}
    yield client
    # 在这里清理

@pytest.fixture
def auth_token():
    """认证 Token"""
    return "test-token-12345"
```

---

### 3. Mock 与 Patch

#### 3.1 什么是 Mock？

Mock 用于**模拟外部依赖**（数据库、API、文件系统等），让测试专注于当前代码逻辑。

```python
# code/04-mock-patch.py
from unittest.mock import Mock, patch, MagicMock
import requests


# ========== 被测试的代码 ==========
def get_user_name(user_id: int) -> str:
    """从 API 获取用户名"""
    response = requests.get(f"https://api.example.com/users/{user_id}")
    if response.status_code == 200:
        return response.json()["name"]
    return "Unknown"

def send_notification(message: str) -> bool:
    """发送通知"""
    # 假设这是一个外部服务
    import smtplib
    server = smtplib.SMTP("smtp.example.com")
    server.send_message(message)
    server.quit()
    return True


# ========== Mock 基础 ==========

def test_mock_basic():
    """Mock 基本用法"""
    # 创建 Mock 对象
    mock_obj = Mock()
    
    # 设置返回值
    mock_obj.get_user.return_value = {"name": "Alice"}
    
    # 调用
    result = mock_obj.get_user(1)
    assert result == {"name": "Alice"}
    
    # 验证调用
    mock_obj.get_user.assert_called_once_with(1)


def test_mock_side_effect():
    """Mock side_effect——模拟异常"""
    mock_obj = Mock()
    mock_obj.connect.side_effect = ConnectionError("连接失败")
    
    with pytest.raises(ConnectionError):
        mock_obj.connect()


# ========== Patch：替换真实对象 ==========

@patch("requests.get")
def test_get_user_name(mock_get):
    """
    Patch 替换 requests.get
    
    mock_get 是替换后的 Mock 对象
    """
    # 设置 mock 的返回值
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"name": "Alice"}
    mock_get.return_value = mock_response

    # 调用被测试的函数
    result = get_user_name(1)

    # 验证结果
    assert result == "Alice"

    # 验证 mock 被正确调用
    mock_get.assert_called_once_with("https://api.example.com/users/1")


@patch("requests.get")
def test_get_user_name_error(mock_get):
    """测试 API 返回错误的情况"""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    result = get_user_name(999)
    assert result == "Unknown"


# ========== Patch 上下文管理器 ==========

def test_with_context_manager():
    """使用 with 语句进行 patch"""
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "Bob"}
        mock_get.return_value = mock_response

        result = get_user_name(2)
        assert result == "Bob"


# ========== MagicMock：更强大的 Mock ==========

def test_magic_mock():
    """MagicMock 支持魔术方法"""
    mock = MagicMock()
    
    # 模拟迭代
    mock.__iter__.return_value = iter([1, 2, 3])
    assert list(mock) == [1, 2, 3]
    
    # 模拟上下文管理器
    mock.__enter__.return_value = "entered"
    mock.__exit__.return_value = False
    with mock as ctx:
        assert ctx == "entered"
    
    # 模拟字符串
    mock.__str__.return_value = "Mock Object"
    assert str(mock) == "Mock Object"


# ========== 运行 ==========
# pytest 04-mock-patch.py -v
```

#### 3.2 Mock 实用技巧

```python
# 1. 验证调用次数
mock.method.assert_called()        # 至少调用一次
mock.method.assert_called_once()   # 恰好调用一次
mock.method.assert_called_with()   # 用特定参数调用
mock.method.assert_not_called()    # 没有被调用

# 2. 多次调用返回不同值
mock.method.side_effect = [1, 2, 3]
assert mock.method() == 1
assert mock.method() == 2
assert mock.method() == 3

# 3. 根据参数返回不同值
mock.method.side_effect = lambda x: x * 2
assert mock.method(3) == 6

# 4. 检查调用历史
mock.method.call_args  # 最后一次调用的参数
mock.method.call_count  # 调用次数
mock.method.call_args_list  # 所有调用的参数列表
```

---

### 4. 测试覆盖率

#### 4.1 什么是测试覆盖率？

测试覆盖率衡量**有多少代码被测试执行到了**。

```bash
pip install pytest-cov
```

```bash
# 生成覆盖率报告
pytest --cov=myproject tests/

# 生成 HTML 报告
pytest --cov=myproject --cov-report=html tests/

# 设置覆盖率阈值（低于则失败）
pytest --cov=myproject --cov-fail-under=80 tests/
```

#### 4.2 覆盖率报告解读

```
Name                      Stmts   Miss  Cover
---------------------------------------------
myproject/__init__.py        10      2    80%
myproject/models.py          50      5    90%
myproject/views.py           30     10    67%
myproject/utils.py           20      0   100%
---------------------------------------------
TOTAL                       110     17    85%
```

- **Stmts**: 语句总数
- **Miss**: 未覆盖的语句数
- **Cover**: 覆盖率百分比

#### 4.3 提高覆盖率的策略

```python
# 1. 测试正常路径
def test_normal_flow():
    result = process_order(order)
    assert result.success is True

# 2. 测试边界条件
def test_empty_order():
    result = process_order(empty_order)
    assert result.success is False

# 3. 测试异常路径
def test_invalid_input():
    with pytest.raises(ValueError):
        process_order(invalid_order)

# 4. 排除不需要测试的代码
# pragma: no cover
def helper_function():
    """这个函数不需要测试"""
    pass
```

---

### 5. 测试最佳实践

#### 5.1 AAA 模式

```python
def test_example():
    # Arrange（准备）—— 设置测试数据和条件
    user = User(name="Alice", age=25)
    
    # Act（执行）—— 调用被测试的代码
    result = user.greet()
    
    # Assert（断言）—— 验证结果
    assert result == "Hello, Alice!"
```

#### 5.2 测试命名规范

```python
# 好的命名：清晰表达测试意图
def test_user_with_valid_email_returns_true():
    ...

def test_division_by_zero_raises_value_error():
    ...

# 坏的命名：不知道在测什么
def test_1():
    ...

def test_user():
    ...
```

#### 5.3 测试金字塔

```
        /  E2E 测试  \         ← 少量（慢、贵、稳定）
       /  集成测试    \        ← 适量（中等速度）
      /   单元测试     \       ← 大量（快、便宜、独立）
     ─────────────────
```

- **单元测试**：测试单个函数/类，隔离外部依赖（最多）
- **集成测试**：测试多个组件协作（适量）
- **端到端测试**：模拟真实用户操作（最少）

---

### 实战项目：API 测试套件

#### 项目说明

为 FastAPI 应用编写完整的测试套件，覆盖：
- 单元测试
- 集成测试
- Mock 外部依赖
- 参数化测试

#### 完整代码

```python
# code/06-api-test-suite.py
"""
🧪 API 测试套件 —— 完整实战项目
为 FastAPI 应用编写测试
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from unittest.mock import Mock, patch


# ========== 被测试的 API ==========

app = FastAPI(title="测试示例 API")

# 简单的内存数据库
items_db: dict[int, dict] = {}
next_id = 1


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(gt=0)
    description: str = ""


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str


@app.post("/items/", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate):
    global next_id
    item_data = {"id": next_id, **item.model_dump()}
    items_db[next_id] = item_data
    next_id += 1
    return item_data


@app.get("/items/", response_model=list[ItemResponse])
def list_items():
    return list(items_db.values())


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]


@app.get("/calculate/")
def calculate(a: int, b: int, op: str = "add"):
    if op == "add":
        return {"result": a + b}
    elif op == "multiply":
        return {"result": a * b}
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")


# ========== Fixture ==========

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """每个测试前清空数据库，测试后也清空"""
    items_db.clear()
    global next_id
    next_id = 1
    yield
    items_db.clear()


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_item():
    """示例商品数据"""
    return {"name": "测试商品", "price": 99.9, "description": "测试描述"}


# ========== 单元测试 ==========

class TestCreateItem:
    """创建商品测试"""

    def test_create_item_success(self, client, sample_item):
        """正常创建商品"""
        response = client.post("/items/", json=sample_item)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "测试商品"
        assert data["price"] == 99.9
        assert data["id"] == 1

    def test_create_item_minimal(self, client):
        """只传必填字段"""
        response = client.post("/items/", json={"name": "A", "price": 1})
        assert response.status_code == 201
        assert response.json()["description"] == ""

    def test_create_item_invalid_price(self, client):
        """价格无效"""
        response = client.post("/items/", json={"name": "A", "price": -1})
        assert response.status_code == 422  # 验证失败

    def test_create_item_empty_name(self, client):
        """名称为空"""
        response = client.post("/items/", json={"name": "", "price": 1})
        assert response.status_code == 422


class TestGetItem:
    """获取商品测试"""

    def test_get_item_success(self, client, sample_item):
        """正常获取商品"""
        create_resp = client.post("/items/", json=sample_item)
        item_id = create_resp.json()["id"]

        response = client.get(f"/items/{item_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "测试商品"

    def test_get_item_not_found(self, client):
        """获取不存在的商品"""
        response = client.get("/items/999")
        assert response.status_code == 404


class TestDeleteItem:
    """删除商品测试"""

    def test_delete_item_success(self, client, sample_item):
        """正常删除"""
        create_resp = client.post("/items/", json=sample_item)
        item_id = create_resp.json()["id"]

        response = client.delete(f"/items/{item_id}")
        assert response.status_code == 204

        # 验证已删除
        get_resp = client.get(f"/items/{item_id}")
        assert get_resp.status_code == 404

    def test_delete_item_not_found(self, client):
        """删除不存在的商品"""
        response = client.delete("/items/999")
        assert response.status_code == 404


# ========== 参数化测试 ==========

@pytest.mark.parametrize("a,b,op,expected", [
    (1, 2, "add", 3),
    (5, 3, "add", 8),
    (0, 0, "add", 0),
    (-1, 1, "add", 0),
    (2, 3, "multiply", 6),
    (5, 0, "multiply", 0),
])
def test_calculate(client, a, b, op, expected):
    """参数化测试计算器"""
    response = client.get(f"/calculate/?a={a}&b={b}&op={op}")
    assert response.status_code == 200
    assert response.json()["result"] == expected


def test_calculate_invalid_op(client):
    """无效操作"""
    response = client.get("/calculate/?a=1&b=2&op=divide")
    assert response.status_code == 400


# ========== Mock 测试 ==========

@patch("requests.get")
def test_external_api_call(mock_get):
    """测试外部 API 调用（Mock）"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "mocked"}
    mock_get.return_value = mock_response

    import requests
    response = requests.get("https://api.example.com/data")
    assert response.json() == {"data": "mocked"}
    mock_get.assert_called_once()


# ========== 集成测试 ==========

def test_full_workflow(client):
    """完整工作流测试"""
    # 1. 创建商品
    item1 = client.post("/items/", json={"name": "商品A", "price": 10}).json()
    item2 = client.post("/items/", json={"name": "商品B", "price": 20}).json()

    # 2. 获取列表
    items = client.get("/items/").json()
    assert len(items) == 2

    # 3. 获取单个
    detail = client.get(f"/items/{item1['id']}").json()
    assert detail["name"] == "商品A"

    # 4. 删除一个
    client.delete(f"/items/{item1['id']}")

    # 5. 验证列表
    items = client.get("/items/").json()
    assert len(items) == 1
    assert items[0]["name"] == "商品B"


# ========== 运行 ==========
# pytest 06-api-test-suite.py -v
# pytest 06-api-test-suite.py -v --cov=. --cov-report=term-missing
```

---

### 今日总结

- **unittest** 是 Python 内置测试框架，基于 TestCase 类和 assert 方法
- **pytest** 更简洁，不需要继承 TestCase，assert 更自然
- **Fixture** 提供测试准备和清理，`yield` 实现 setup/teardown
- **参数化测试** `@pytest.mark.parametrize` 一次运行多组数据
- **Mock** 模拟外部依赖，`@patch` 替换真实对象
- **测试覆盖率** 量化测试质量，`pytest --cov` 生成报告
- 测试金字塔：大量单元测试 → 适量集成测试 → 少量 E2E 测试

### 练习题

#### 练习 1：数学函数测试 ⭐⭐
为以下函数编写测试：
- `sqrt(n)` —— 计算平方根（处理负数）
- `fibonacci(n)` —— 计算斐波那契数列
- `is_palindrome(s)` —— 判断回文字符串
- 要求覆盖正常路径、边界条件、异常情况

#### 练习 2：数据库操作测试 ⭐⭐⭐
为 Day 068 的通讯录管理系统编写测试：
- 测试 ContactManager 的所有方法
- 使用 fixture 管理测试数据库
- 测试后自动清理数据

#### 练习 3：Mock 外部服务 ⭐⭐⭐
编写一个邮件发送函数的测试：
- Mock SMTP 服务器
- 测试发送成功和失败的情况
- 验证邮件内容和收件人

#### 练习 4：API 测试套件 ⭐⭐⭐⭐
为一个完整的 REST API 编写测试：
- 覆盖所有 CRUD 操作
- 测试认证和权限
- 使用参数化测试覆盖多种场景
- 目标覆盖率 > 80%

#### 练习 5：TDD 实践 ⭐⭐⭐⭐
用 TDD（测试驱动开发）方式实现一个购物车：
1. 先写测试（红灯）
2. 写最少的代码让测试通过（绿灯）
3. 重构代码（保持测试通过）
4. 重复以上步骤

### 明天预告

Day 071 将学习**日志与调试**——logging 模块详解、日志级别与配置、pdb 调试器、生产级日志配置。让你的代码更易维护、更易调试！

## 第二部分：测试进阶

### 概述

Day 072 我们学习了测试基础（unittest 和 pytest），今天我们深入**高级测试技巧**。

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

### 1. 测试驱动开发（TDD）

#### 1.1 TDD 流程

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

#### 1.2 TDD 实战：字符串计算器

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

#### 1.3 TDD 的好处

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

### 2. 参数化测试

#### 2.1 pytest.mark.parametrize

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

#### 2.2 高级参数化

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

#### 2.3 参数化 vs 循环

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

### 3. 集成测试 vs 单元测试

#### 3.1 测试金字塔

```
        /\
       /  \        E2E 测试（少量）
      /    \       集成测试（适量）
     /      \      单元测试（大量）
    /________\
```

#### 3.2 单元测试

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

#### 3.3 集成测试

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

#### 3.4 测试分类

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

### 4. 测试异步代码

#### 4.1 pytest-asyncio 基础

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

#### 4.2 异步类测试

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

#### 4.3 异步测试最佳实践

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

### 5. 测试覆盖率

#### 5.1 安装 pytest-cov

```bash
pip install pytest-cov
```

#### 5.2 生成覆盖率报告

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

#### 5.3 覆盖率配置

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

### 实战项目：为 Flask API 写完整测试套件

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

### 今日总结

- **TDD**：先写测试，再写代码，Red-Green-Refactor 循环
- **参数化测试**：`@pytest.mark.parametrize` 减少重复代码
- **集成测试**：测试多个模块协作，可能依赖外部资源
- **异步测试**：`@pytest.mark.asyncio` + `AsyncMock`
- **覆盖率**：`pytest-cov` 生成覆盖率报告

---

### 练习题

#### 练习 1：TDD 实践 ⭐⭐
用 TDD 方式实现一个购物车类：
- 添加商品
- 移除商品
- 计算总价
- 应用折扣
- 清空购物车

#### 练习 2：参数化测试 ⭐⭐
为以下函数编写参数化测试：
- 字符串反转
- 斐波那契数列
- 质数判断

#### 练习 3：集成测试 ⭐⭐⭐
为一个简单的文件处理系统写集成测试：
- 创建临时文件
- 读取文件内容
- 处理文件（转换大小写）
- 写入新文件
- 验证结果

#### 练习 4：异步测试 ⭐⭐⭐
测试一个异步 HTTP 客户端：
- 使用 aioresponses 模拟 HTTP 请求
- 测试成功和失败场景
- 测试超时处理
- 测试重试机制

#### 练习 5：完整测试套件 ⭐⭐⭐⭐
为一个 REST API 写完整的测试套件：
- 单元测试（工具函数）
- 集成测试（数据库操作）
- API 测试（端点测试）
- 性能测试（响应时间）
- 生成覆盖率报告

---

### 明天预告

Day 075 我们将进行**阶段项目：标准库综合实战**——构建一个完整的 CLI 工具，综合运用 Phase 5 所有知识！

## 第三部分：数据库安全

> 前两部分解决"代码写得对不对"，这一部分解决"代码安不安全"。SQL 注入常年位居 Web 漏洞前三，而它的防御手段恰恰是测试可以验证的——所以放在这里一起学。

### SQL 注入原理

注入的根源只有一句话：**把用户输入当成了代码**。当 SQL 语句用字符串拼接构造时，输入内容里的引号、注释符会改变语句结构：

```python
# ❌ 致命的拼接方式
username = "' OR '1'='1"
sql = f"SELECT * FROM users WHERE name = '{username}'"
# SELECT * FROM users WHERE name = '' OR '1'='1'  → 全表泄露
```

常见注入类型：

| 类型 | 特征 | 危害 |
|------|------|------|
| 报错注入 | 数据库错误信息回显 | 直接拖库 |
| 布尔盲注 | 页面真假响应不同 | 逐字节猜数据 |
| 时间盲注 | 响应延迟差异 | 无回显也能窃取 |
| 堆叠注入 | 一次执行多条语句 | 删库、写文件 |

### 参数化查询：唯一的正解

参数化（占位符）把**数据和代码彻底分离**——用户输入永远只是"值"，不可能变成"语法"：

```python
# ✅ 参数化查询
cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
```

实测对比见 `code/12-sql-injection-basics.py`（注入复现）与 `code/13-parameterized-queries.py`（防护验证）。三个原则：

1. **所有**动态值都走占位符，包括排序字段、表名以外的一切
2. 表名/列名不能参数化 → 用白名单映射，绝不能直接拼用户输入
3. LIKE 查询用 `LIKE ?` + `f"%{kw}%"` 作为参数，不要拼进语句

### ORM 的自动防注入与它的陷阱

ORM 把拼接封装掉了，但两个常见误区仍会造成注入：

1. **`text()` 裸写 SQL**：`session.execute(text(f"SELECT * FROM users WHERE name='{name}'"))` 照样注入——`text()` 支持 `:name` 占位符，必须用
2. **`filter` 字符串化**：`filter("name = '%s'" % name)` 是弃用且危险的写法，用列对象表达式 `User.name == name`

验证脚本：`code/14-orm-injection-defense.py`（同一攻击 payload 打在拼接版、`text()` 裸写版、正确 ORM 版上的对照实验）。

### 常见绕过手法与防护清单

| 绕过手法 | 示例片段 | 防护 |
|----------|----------|------|
| 引号闭合 | `' OR 1=1 --` | 参数化 |
| 注释截断 | `admin'--` | 参数化 |
| 大小写变形 | `UnIoN SeLeCt` | 参数化（与关键字过滤无关） |
| 编码变形 | `%27`、双写 `/**/` | 参数化 + WAF 兜底 |
| 堆叠执行 | `'; DROP TABLE users;` | 禁用多语句（默认即是）+ 最小权限账号 |

**上线前安全自检：**

- [ ] 全代码库无字符串拼接构造 SQL（可用 AST 扫描 `execute(f"...")`）
- [ ] 数据库账号按最小权限分配（应用账号无 DROP 权限）
- [ ] 错误信息不回显原始 SQL / 数据库报错
- [ ] 关键接口有 SQL 注入的自动化测试用例（拿本章 payload 当测试数据）

> 💡 本部分所有代码只用 `sqlite3` 标准库即可复现，不需要 MySQL 环境——SQL 注入的原理与方言无关。
