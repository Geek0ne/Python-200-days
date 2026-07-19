"""
Day 070 — Mock 与 Patch 详解
运行方式：pytest 04-mock-patch.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call


# ========== 被测试的代码 ==========

def get_user_from_api(user_id: int) -> dict:
    """从 API 获取用户信息"""
    import requests
    response = requests.get(f"https://api.example.com/users/{user_id}")
    if response.status_code == 200:
        return response.json()
    return {"error": "User not found"}

def send_email(to: str, subject: str, body: str) -> bool:
    """发送邮件"""
    import smtplib
    server = smtplib.SMTP("smtp.example.com", 587)
    server.starttls()
    server.login("user", "pass")
    server.sendmail("me@example.com", to, f"Subject: {subject}\n\n{body}")
    server.quit()
    return True

def process_payment(amount: float) -> dict:
    """处理支付"""
    if amount <= 0:
        raise ValueError("金额必须大于 0")
    # 调用外部支付服务
    import requests
    response = requests.post(
        "https://payment.example.com/charge",
        json={"amount": amount}
    )
    return response.json()


# ========== Mock 基础 ==========

def test_mock_basic():
    """Mock 基本用法"""
    mock_obj = Mock()
    
    # 设置返回值
    mock_obj.get_user.return_value = {"name": "Alice", "id": 1}
    
    # 调用
    result = mock_obj.get_user(1)
    assert result == {"name": "Alice", "id": 1}
    
    # 验证调用
    mock_obj.get_user.assert_called_once_with(1)

def test_mock_side_effect():
    """Mock side_effect——模拟异常"""
    mock_obj = Mock()
    mock_obj.connect.side_effect = ConnectionError("连接失败")
    
    with pytest.raises(ConnectionError, match="连接失败"):
        mock_obj.connect()

def test_mock_side_effect_list():
    """Mock side_effect 列表——多次调用返回不同值"""
    mock_obj = Mock()
    mock_obj.read.side_effect = ["line1", "line2", "line3"]
    
    assert mock_obj.read() == "line1"
    assert mock_obj.read() == "line2"
    assert mock_obj.read() == "line3"
    
    with pytest.raises(StopIteration):
        mock_obj.read()  # 第四次调用抛异常


# ========== Patch ==========

@patch("requests.get")
def test_get_user_from_api(mock_get):
    """Patch 替换 requests.get"""
    # 设置 mock 返回值
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"name": "Alice", "id": 1}
    mock_get.return_value = mock_response

    # 调用被测试的函数
    result = get_user_from_api(1)

    # 验证结果
    assert result == {"name": "Alice", "id": 1}

    # 验证 mock 被正确调用
    mock_get.assert_called_once_with("https://api.example.com/users/1")

@patch("requests.get")
def test_get_user_from_api_not_found(mock_get):
    """测试用户不存在的情况"""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    result = get_user_from_api(999)
    assert result == {"error": "User not found"}

@patch("requests.post")
def test_process_payment_success(mock_post):
    """测试支付成功"""
    mock_response = Mock()
    mock_response.json.return_value = {"status": "success", "transaction_id": "txn_123"}
    mock_post.return_value = mock_response

    result = process_payment(99.9)
    assert result["status"] == "success"
    mock_post.assert_called_once()

@patch("requests.post")
def test_process_payment_failure(mock_post):
    """测试支付失败"""
    mock_response = Mock()
    mock_response.json.return_value = {"status": "failed", "error": "Insufficient funds"}
    mock_post.return_value = mock_response

    result = process_payment(999999)
    assert result["status"] == "failed"

def test_process_payment_invalid_amount():
    """测试无效金额"""
    with pytest.raises(ValueError, match="金额必须大于 0"):
        process_payment(-10)


# ========== 上下文管理器 Patch ==========

def test_patch_context_manager():
    """使用 with 语句进行 patch"""
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "Bob"}
        mock_get.return_value = mock_response

        result = get_user_from_api(2)
        assert result == {"name": "Bob"}
        
        # 验证调用
        mock_get.assert_called_once()


# ========== MagicMock ==========

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
    
    # 模拟字符串表示
    mock.__str__.return_value = "Mock Object"
    assert str(mock) == "Mock Object"


# ========== 验证调用 ==========

def test_call_verification():
    """验证调用次数和参数"""
    mock = Mock()
    
    mock(1)
    mock(2)
    mock(3)
    
    assert mock.call_count == 3
    assert mock.call_args_list == [call(1), call(2), call(3)]
    mock.assert_called_with(3)  # 最后一次调用


# ========== 运行 ==========
# pytest 04-mock-patch.py -v
# pytest 04-mock-patch.py -v -s
