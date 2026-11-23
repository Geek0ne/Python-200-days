"""
Day 032 — 属性与方法：实战案例
======================================================================
银行账户系统完整实现
  1. 账户基类 (验证、property、三种方法)
  2. 储蓄账户 (带利息)
  3. 支票账户 (带交易费)
  4. 账户管理器
======================================================================
"""

from datetime import datetime, timedelta
import random


# ====================================================================
# 1. 账户基类
# ====================================================================
class BankAccount:
    """银行账户基类 — 综合运用属性与方法"""

    # ── 类属性 ──
    bank_name = "Python 银行"
    _total_accounts = 0
    daily_withdraw_limit = 10000

    def __init__(self, owner, initial_balance=0, account_type="普通"):
        self._owner = None
        self._balance = 0
        self._frozen = False
        self._transactions = []
        self._daily_withdrawn = 0
        self._last_transaction_date = datetime.now().date()

        # 通过 property 设置
        self.owner = owner
        self.account_number = f"PY{datetime.now().strftime('%Y%m%d')}{BankAccount._total_accounts + 1:06d}"
        self.account_type = account_type

        BankAccount._total_accounts += 1

        if initial_balance > 0:
            self.deposit(initial_balance, "开户存款")

    # ── Property: 账户所有者 ──
    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, value):
        if not isinstance(value, str) or len(value.strip()) < 1:
            raise ValueError("账户所有者姓名不能为空")
        self._owner = value.strip().title()

    # ── Property: 余额（只读） ──
    @property
    def balance(self):
        return self._balance

    # ── Property: 冻结状态 ──
    @property
    def frozen(self):
        return self._frozen

    @frozen.setter
    def frozen(self, value):
        if not isinstance(value, bool):
            raise TypeError("frozen 必须是布尔值")
        self._frozen = value

    # ── Property: 交易数（只读计算） ──
    @property
    def transaction_count(self):
        return len(self._transactions)

    # ── Property: 今日交易统计 ──
    @property
    def today_summary(self):
        today = datetime.now().date()
        today_txns = [t for t in self._transactions
                      if t['date'].date() == today]
        total_in = sum(t['amount'] for t in today_txns if t['type'] == 'deposit')
        total_out = sum(t['amount'] for t in today_txns if t['type'] == 'withdraw')
        return {'count': len(today_txns), 'in': total_in, 'out': total_out}

    # ── Instance methods ──
    def deposit(self, amount, description="存款"):
        """存款"""
        self._validate_amount(amount)
        self._check_frozen()
        self._balance += amount
        self._add_transaction('deposit', amount, description)
        return self._balance

    def withdraw(self, amount, description="取款"):
        """取款"""
        self._validate_amount(amount)
        self._check_frozen()
        self._check_sufficient(amount)
        self._check_daily_limit(amount)

        self._balance -= amount
        self._daily_withdrawn += amount
        self._add_transaction('withdraw', amount, description)
        return self._balance

    def transfer(self, target_account, amount, description="转账"):
        """转账"""
        if not isinstance(target_account, BankAccount):
            raise TypeError("目标必须是 BankAccount 实例")
        self.withdraw(amount, f"转账转出: {description}")
        target_account.deposit(amount, f"转账转入: {description}")
        return True

    def get_statement(self, days=30):
        """获取交易明细（最近 N 天）"""
        cutoff = datetime.now() - timedelta(days=days)
        return [t for t in self._transactions if t['date'] >= cutoff]

    def display_statement(self, days=30):
        """显示交易明细"""
        txns = self.get_statement(days)
        print(f"\n  📋 {self.owner} 账户交易明细 (最近{days}天)")
        print(f"  {'='*55}")
        print(f"  {'日期':<20} {'类型':<10} {'金额':>10} {'说明'}")
        print(f"  {'-'*55}")
        balance = self._balance
        for t in reversed(txns):
            date_str = t['date'].strftime('%Y-%m-%d %H:%M')
            amount_str = f"+${t['amount']:.2f}" if t['type'] == 'deposit' else f"-${t['amount']:.2f}"
            print(f"  {date_str:<20} {t['type']:<10} {amount_str:>10} {t['description']}")
        print(f"  {'-'*55}")
        print(f"  {'当前余额':>40}: ${balance:.2f}")

    # ── 类方法 ──
    @classmethod
    def from_balance(cls, owner, balance):
        """从指定余额创建（工厂方法）"""
        return cls(owner, balance)

    @classmethod
    def get_total_accounts(cls):
        """获取总账户数"""
        return cls._total_accounts

    @classmethod
    def create_random_account(cls):
        """创建随机账户（演示用）"""
        owners = ["张三", "李四", "王五", "赵六", "钱七"]
        owner = random.choice(owners)
        balance = random.randint(0, 100000)
        return cls(owner, balance)

    # ── 静态方法 ──
    @staticmethod
    def _validate_amount(amount):
        if not isinstance(amount, (int, float)):
            raise TypeError("金额必须是数字")
        if amount <= 0:
            raise ValueError("金额必须大于0")

    @staticmethod
    def format_amount(amount):
        """格式化金额"""
        return f"${amount:,.2f}"

    @staticmethod
    def calculate_interest(principal, rate, years):
        """计算复利"""
        return principal * (1 + rate) ** years

    # ── 私有辅助方法 ──
    def _check_frozen(self):
        if self._frozen:
            raise RuntimeError("账户已冻结")

    def _check_sufficient(self, amount):
        if amount > self._balance:
            raise ValueError(
                f"余额不足! 需要 {self.format_amount(amount)}, "
                f"当前 {self.format_amount(self._balance)}")

    def _check_daily_limit(self, amount):
        today = datetime.now().date()
        if self._last_transaction_date != today:
            self._daily_withdrawn = 0
            self._last_transaction_date = today
        if self._daily_withdrawn + amount > self.daily_withdraw_limit:
            raise ValueError(
                f"今日已取款 {self.format_amount(self._daily_withdrawn)}, "
                f"再取 {self.format_amount(amount)} 超出限额")

    def _add_transaction(self, txn_type, amount, description):
        self._transactions.append({
            'date': datetime.now(),
            'type': txn_type,
            'amount': amount,
            'description': description,
        })

    def __str__(self):
        return (f"[{self.account_type}] {self.owner} "
                f"(#{self.account_number}) "
                f"余额: {self.format_amount(self._balance)}" +
                (" 🔒" if self._frozen else ""))


# ====================================================================
# 2.  SavingsAccount — 储蓄账户
# ====================================================================
class SavingsAccount(BankAccount):
    """储蓄账户 — 带利息"""

    annual_interest_rate = 0.035  # 年利率 3.5%

    def __init__(self, owner, initial_balance=0):
        super().__init__(owner, initial_balance, account_type="储蓄账户")
        self._last_interest_date = datetime.now()

    def apply_interest(self):
        """计算并应用利息"""
        days = (datetime.now() - self._last_interest_date).days
        if days > 0:
            daily_rate = self.annual_interest_rate / 365
            interest = self._balance * daily_rate * days
            self._balance += interest
            self._add_transaction('interest', interest,
                                  f"利息收入 ({days}天)")
            self._last_interest_date = datetime.now()
            return interest
        return 0.0

    def withdraw(self, amount, description="取款"):
        """储蓄账户取款（带手续费）"""
        fee = max(1.0, amount * 0.005)  # 0.5% 手续费，最低 $1
        total = amount + fee
        self._validate_amount(amount)
        self._check_frozen()
        self._check_sufficient(total)
        self._balance -= total
        self._add_transaction('withdraw', amount,
                              f"{description} (手续费: ${fee:.2f})")
        return self._balance


# ====================================================================
# 3. CheckingAccount — 支票账户
# ====================================================================
class CheckingAccount(BankAccount):
    """支票账户 — 低利息，无手续费"""

    monthly_fee = 5.00
    free_transactions = 10

    def __init__(self, owner, initial_balance=0):
        super().__init__(owner, initial_balance, account_type="支票账户")
        self._month_txns = 0

    def withdraw(self, amount, description="取款"):
        """支票账户取款"""
        self._month_txns += 1
        return super().withdraw(amount, description)

    def apply_monthly_fee(self):
        """应用月费"""
        if self._month_txns > self.free_transactions:
            extra = self._month_txns - self.free_transactions
            fee = self.monthly_fee + extra * 0.50
            self._validate_amount(fee)
            self._check_sufficient(fee)
            self._balance -= fee
            self._add_transaction('fee', fee, f"月费 (超{extra}笔)")
            return True
        self._add_transaction('fee', 0, "月费 (免费交易数内)")
        return False


# ====================================================================
# 4. Bank 类 — 账户管理器
# ====================================================================
class Bank:
    """银行 — 管理多个账户"""

    def __init__(self, name="Python 银行"):
        self.name = name
        self.accounts = {}  # account_number → BankAccount

    def open_account(self, account):
        """开立账户"""
        self.accounts[account.account_number] = account
        print(f"  🏦 开立账户: {account}")
        return account.account_number

    def get_account(self, account_number):
        """获取账户"""
        return self.accounts.get(account_number)

    def total_deposits(self):
        """总存款"""
        return sum(a.balance for a in self.accounts.values())

    def account_count(self):
        """账户数"""
        return len(self.accounts)

    def display_all_accounts(self):
        """显示所有账户"""
        print(f"\n  🏛️  {self.name} — 账户一览")
        print(f"  {'='*55}")
        print(f"  {'账号':<20} {'类型':<10} {'户主':<8} {'余额':>12}")
        print(f"  {'-'*55}")
        for acc in self.accounts.values():
            print(f"  {acc.account_number:<20} {acc.account_type:<10} "
                  f"{acc.owner:<8} {BankAccount.format_amount(acc.balance):>12}")
        print(f"  {'-'*55}")
        print(f"  {'总存款:':>38} {BankAccount.format_amount(self.total_deposits()):>12}")


# ====================================================================
# 5. 完整演示
# ====================================================================
print("=" * 60)
print("🏦  银行账户系统 — 完整演示")
print("=" * 60)

# 创建银行
bank = Bank()

# 开立账户
print(f"\n─── 开立账户 ───")
# 使用直接实例化
acc1 = BankAccount("张三", 10000)
bank.open_account(acc1)

# 使用工厂方法
acc2 = BankAccount.from_balance("李四", 50000)
bank.open_account(acc2)

# 储蓄账户
savings = SavingsAccount("王五", 200000)
bank.open_account(savings)

# 支票账户
checking = CheckingAccount("赵六", 30000)
bank.open_account(checking)

# 显示所有账户
bank.display_all_accounts()

# 交易操作
print(f"\n─── 交易操作 ───")
print(f"  张三: 存款 $5,000")
acc1.deposit(5000, "工资收入")
print(f"  张三: 取款 $2,000")
acc1.withdraw(2000, "购物消费")

print(f"\n  李四 转账 $10,000 给 张三")
acc2.transfer(acc1, 10000, "借款")

# 储蓄账户利息
print(f"\n─── 储蓄利息 ───")
print(f"  王五 (储蓄账户):")
interest = savings.apply_interest()
print(f"  利息收入: ${interest:.2f}")
print(f"  当前余额: ${savings.balance:.2f}")

# 交易明细
print(f"\n─── 交易明细 ───")
acc1.display_statement(days=30)

# 冻结测试
print(f"\n─── 冻结测试 ───")
acc1.frozen = True
try:
    acc1.withdraw(100)
except RuntimeError as e:
    print(f"  成功拦截: {e}")
acc1.frozen = False
print(f"  解冻后取款: ${acc1.withdraw(100):.2f}")

# 余额不足测试
print(f"\n─── 余额不足测试 ───")
try:
    acc1.withdraw(9999999)
except ValueError as e:
    print(f"  成功拦截: {e}")

# 统计
print(f"\n─── 银行统计 ───")
print(f"  银行: {bank.name}")
print(f"  总账户数: {bank.account_count()}")
print(f"  总存款: {BankAccount.format_amount(bank.total_deposits())}")
print(f"  账户类总账户数: {BankAccount.get_total_accounts()}")

# 复利计算
print(f"\n─── 复利计算（静态方法）───")
principal = 10000
rate = 0.05
for years in [1, 5, 10, 20]:
    total = BankAccount.calculate_interest(principal, rate, years)
    print(f"  ${principal:,.0f} @ {rate*100}% 在 {years:2d} 年后: ${total:,.2f}")

print(f"\n" + "=" * 60)
print(f"🏆  银行账户系统运行完毕!")
print(f"    营业: {bank.name}")
print(f"    账户: {bank.account_count()} 个")
print(f"    存款: {BankAccount.format_amount(bank.total_deposits())}")
print("=" * 60)
