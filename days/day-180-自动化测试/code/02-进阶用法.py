"""进阶用法与避坑 - 常见错误避免"""
import pytest


class BankAccount:
    """模拟银行账户"""
    
    def __init__(self, initial_balance=0):
        self.balance = initial_balance
    
    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("存款金额必须大于0")
        self.balance += amount
    
    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("取款金额必须大于0")
        if amount > self.balance:
            raise ValueError("余额不足")
        self.balance -= amount


def test_withdraw_insufficient_funds():
    """测试余额不足情况"""
    account = BankAccount(100)
    
    with pytest.raises(ValueError, match="余额不足"):
        account.withdraw(200)


def test_withdraw_negative_amount():
    """测试负数取款 - 应该失败"""
    account = BankAccount(100)
    
    # 正确的断言：期望抛出异常
    with pytest.raises(ValueError, match="取款金额必须大于0"):
        account.withdraw(-50)


def test_deposit_zero_fails():
    """测试零存款应该失败"""
    account = BankAccount()
    
    with pytest.raises(ValueError, match="存款金额必须大于0"):
        account.deposit(0)


def test_account_initial_balance():
    """测试账户初始余额"""
    account = BankAccount(50)
    assert account.balance == 50
    assert account.balance is not None


def test_account_negative_deposit():
    """测试负数存款"""
    account = BankAccount()
    
    # 匹配错误信息
    with pytest.raises(ValueError) as exc_info:
        account.deposit(-100)
    
    # 验证异常信息内容
    assert "存款金额必须大于0" in str(exc_info.value)