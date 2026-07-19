# Day 070 — 测试基础：unittest、pytest 与 Mock

## 概述

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

## 1. unittest 框架

### 1.1 什么是 unittest？

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

### 1.2 常用断言方法

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

### 1.3 测试组织

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

## 2. pytest 实战

### 2.1 为什么用 pytest？

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

### 2.2 Fixture：测试夹具

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

### 2.3 conftest.py：共享 Fixture

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

## 3. Mock 与 Patch

### 3.1 什么是 Mock？

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

### 3.2 Mock 实用技巧

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

## 4. 测试覆盖率

### 4.1 什么是测试覆盖率？

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

### 4.2 覆盖率报告解读

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

### 4.3 提高覆盖率的策略

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

## 5. 测试最佳实践

### 5.1 AAA 模式

```python
def test_example():
    # Arrange（准备）—— 设置测试数据和条件
    user = User(name="Alice", age=25)
    
    # Act（执行）—— 调用被测试的代码
    result = user.greet()
    
    # Assert（断言）—— 验证结果
    assert result == "Hello, Alice!"
```

### 5.2 测试命名规范

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

### 5.3 测试金字塔

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

## 实战项目：API 测试套件

### 项目说明

为 FastAPI 应用编写完整的测试套件，覆盖：
- 单元测试
- 集成测试
- Mock 外部依赖
- 参数化测试

### 完整代码

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

## 今日总结

- **unittest** 是 Python 内置测试框架，基于 TestCase 类和 assert 方法
- **pytest** 更简洁，不需要继承 TestCase，assert 更自然
- **Fixture** 提供测试准备和清理，`yield` 实现 setup/teardown
- **参数化测试** `@pytest.mark.parametrize` 一次运行多组数据
- **Mock** 模拟外部依赖，`@patch` 替换真实对象
- **测试覆盖率** 量化测试质量，`pytest --cov` 生成报告
- 测试金字塔：大量单元测试 → 适量集成测试 → 少量 E2E 测试

## 练习题

### 练习 1：数学函数测试 ⭐⭐
为以下函数编写测试：
- `sqrt(n)` —— 计算平方根（处理负数）
- `fibonacci(n)` —— 计算斐波那契数列
- `is_palindrome(s)` —— 判断回文字符串
- 要求覆盖正常路径、边界条件、异常情况

### 练习 2：数据库操作测试 ⭐⭐⭐
为 Day 068 的通讯录管理系统编写测试：
- 测试 ContactManager 的所有方法
- 使用 fixture 管理测试数据库
- 测试后自动清理数据

### 练习 3：Mock 外部服务 ⭐⭐⭐
编写一个邮件发送函数的测试：
- Mock SMTP 服务器
- 测试发送成功和失败的情况
- 验证邮件内容和收件人

### 练习 4：API 测试套件 ⭐⭐⭐⭐
为一个完整的 REST API 编写测试：
- 覆盖所有 CRUD 操作
- 测试认证和权限
- 使用参数化测试覆盖多种场景
- 目标覆盖率 > 80%

### 练习 5：TDD 实践 ⭐⭐⭐⭐
用 TDD（测试驱动开发）方式实现一个购物车：
1. 先写测试（红灯）
2. 写最少的代码让测试通过（绿灯）
3. 重构代码（保持测试通过）
4. 重复以上步骤

## 明天预告

Day 071 将学习**日志与调试**——logging 模块详解、日志级别与配置、pdb 调试器、生产级日志配置。让你的代码更易维护、更易调试！
