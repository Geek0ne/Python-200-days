"""
Day 070 — pytest Fixture 详解
运行方式：pytest 03-pytest-fixtures.py -v -s
"""
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
    测试结束后自动清理
    """
    file = tmp_path / "test.txt"
    file.write_text("Hello, pytest!\nLine 2")
    return file

@pytest.fixture
def db_connection():
    """
    模拟数据库连接
    
    yield 之前的代码 = setup（准备）
    yield 之后的代码 = teardown（清理）
    """
    print("\n  📦 建立数据库连接")
    connection = {"connected": True, "data": [], "queries": 0}
    yield connection  # 把连接传给测试函数
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

@pytest.fixture
def user_list():
    """用户列表"""
    return [
        {"name": "Alice", "age": 25},
        {"name": "Bob", "age": 30},
        {"name": "Charlie", "age": 35},
    ]


# ========== 使用 Fixture 的测试 ==========

def test_list_operations(sample_data):
    """使用 sample_data fixture"""
    assert len(sample_data) == 5
    assert sum(sample_data) == 15
    assert max(sample_data) == 5

def test_list_sorted(sample_data):
    """测试排序"""
    assert sorted(sample_data) == [1, 2, 3, 4, 5]

def test_temp_file_content(temp_file):
    """使用临时文件 fixture"""
    content = temp_file.read_text()
    assert "Hello, pytest!" in content
    assert "Line 2" in content

def test_database_insert(db_connection):
    """使用数据库连接 fixture"""
    db_connection["data"].append("record1")
    db_connection["queries"] += 1
    assert len(db_connection["data"]) == 1
    assert db_connection["connected"] is True

def test_database_query(db_connection):
    """同一个 fixture 实例在每个测试中独立"""
    # 每个测试都会得到新的连接（因为没有 scope 参数）
    assert len(db_connection["data"]) == 0  # 新的空连接

def test_user_ages(user_list):
    """测试用户数据"""
    ages = [u["age"] for u in user_list]
    assert sum(ages) == 90
    assert max(ages) == 35

def test_user_names(user_list):
    """测试用户名"""
    names = [u["name"] for u in user_list]
    assert "Alice" in names
    assert len(names) == 3


# ========== 参数化测试 ==========

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (0, 0),
    (-1, -2),
])
def test_double(input, expected):
    """参数化测试"""
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
# pytest 03-pytest-fixtures.py -v -s --tb=short
