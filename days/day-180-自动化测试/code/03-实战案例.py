"""完整的自动化测试套件示例 - 实战案例"""
import pytest
import tempfile
import os
from pathlib import Path
import json


# Fixture：临时目录
@pytest.fixture
def temp_dir():
    """创建临时目录，测试结束自动清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_data():
    """提供测试用的样本数据"""
    return {
        "name": "测试用户",
        "age": 25,
        "email": "test@example.com"
    }


class TestUserManagement:
    """用户管理测试类"""
    
    def test_create_user(self, sample_data):
        """测试创建用户"""
        assert sample_data["name"] == "测试用户"
        assert sample_data["age"] == 25
        assert "@" in sample_data["email"]
    
    def test_user_email_format(self, sample_data):
        """测试邮箱格式验证"""
        parts = sample_data["email"].split("@")
        assert len(parts) == 2
        assert len(parts[1]) > 0
    
    def test_user_name_not_empty(self, sample_data):
        """测试用户名不为空"""
        assert sample_data["name"].strip() != ""


class TestFileOperations:
    """文件操作测试"""
    
    def test_temp_file_creation(self, temp_dir):
        """测试临时文件创建"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello Test")
        assert test_file.exists()
        assert test_file.read_text() == "Hello Test"
    
    def test_temp_file_cleanup(self, temp_dir):
        """测试临时文件自动清理"""
        # 在此之后，temp_dir及其内容会自动删除
        pass
    
    def test_content_integrity(self, temp_dir):
        """测试内容完整性"""
        (temp_dir / "data.json").write_text('{"key": "value"}')
        data = json.loads((temp_dir / "data.json").read_text())
        assert data == {"key": "value"}


class TestCalculator:
    """计算器测试 - 集成测试示例"""
    
    @pytest.fixture
    def calc(self):
        """计算器实例"""
        return Calculator()
    
    def test_add(self, calc):
        assert calc.add(2, 3) == 5
    
    def test_subtract(self, calc):
        assert calc.subtract(5, 3) == 2
    
    def test_multiply(self, calc):
        assert calc.multiply(3, 4) == 12
    
    def test_divide(self, calc):
        assert calc.divide(10, 2) == 5
    
    def test_divide_by_zero(self, calc):
        with pytest.raises(ZeroDivisionError):
            calc.divide(10, 0)


class Calculator:
    """简单计算器类"""
    
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("不能除以零")
        return a / b


# E2E 测试示例 - 模拟用户注册流程
class TestUserRegistrationFlow:
    """用户注册端到端测试"""
    
    def test_registration_flow(self):
        """测试完整注册流程"""
        # 1. 用户提交注册信息
        user_data = {"username": "newuser", "email": "new@test.com", "password": "secure123"}
        
        # 2. 验证输入
        assert len(user_data["username"]) >= 3
        assert "@" in user_data["email"]
        assert len(user_data["password"]) >= 8
        
        # 3. 创建用户（模拟）
        user = {"id": 1, **user_data}
        assert user["id"] == 1
        
        # 4. 发送欢迎邮件（模拟）
        welcome_sent = True
        assert welcome_sent
        
        # 5. 验证最终状态
        assert user["username"] == "newuser"
        assert user["email"] == "new@test.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])