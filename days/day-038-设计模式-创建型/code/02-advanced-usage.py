"""
Day 038 — 创建型设计模式：进阶用法
====================================

涵盖：
1. 抽象工厂模式
2. 建造者模式（Builder）
3. 原型模式（Prototype）
4. 线程安全的单例
5. 懒初始化与对象池
"""


# ====================================
# 1. 抽象工厂模式
# ====================================
print("=" * 60)
print("1️⃣ 抽象工厂模式")
print("=" * 60)

from abc import ABC, abstractmethod


# ── 抽象产品 ──

class Button(ABC):
    @abstractmethod
    def render(self) -> str: pass

    @abstractmethod
    def click(self) -> str: pass


class Checkbox(ABC):
    @abstractmethod
    def render(self) -> str: pass

    @abstractmethod
    def check(self) -> str: pass


# ── Windows 产品 ──

class WindowsButton(Button):
    def render(self) -> str:
        return "  [ Windows 按钮 🪟 ]"

    def click(self) -> str:
        return "  🖱️ Windows 按钮被点击"


class WindowsCheckbox(Checkbox):
    def render(self) -> str:
        return "  [✓] Windows 复选框"

    def check(self) -> str:
        return "  ✅ Windows 复选框已选中"


# ── macOS 产品 ──

class MacButton(Button):
    def render(self) -> str:
        return "  [ macOS Button 🍎 ]"

    def click(self) -> str:
        return "  🖱️ macOS 按钮被点击"


class MacCheckbox(Checkbox):
    def render(self) -> str:
        return "  [✓] macOS Checkbox"

    def check(self) -> str:
        return "  ✅ macOS 复选框已选中"


# ── Linux 产品 ──

class LinuxButton(Button):
    def render(self) -> str:
        return "  [ Linux 按钮 🐧 ]"

    def click(self) -> str:
        return "  🖱️ Linux 按钮被点击"


class LinuxCheckbox(Checkbox):
    def render(self) -> str:
        return "  [✓] Linux 复选框"

    def check(self) -> str:
        return "  ✅ Linux 复选框已选中"


# ── 抽象工厂 ──

class GUIFactory(ABC):
    """抽象工厂 —— 创建一系列相关产品"""

    @abstractmethod
    def create_button(self) -> Button: pass

    @abstractmethod
    def create_checkbox(self) -> Checkbox: pass


class WindowsFactory(GUIFactory):
    def create_button(self) -> Button:
        return WindowsButton()

    def create_checkbox(self) -> Checkbox:
        return WindowsCheckbox()


class MacFactory(GUIFactory):
    def create_button(self) -> Button:
        return MacButton()

    def create_checkbox(self) -> Checkbox:
        return MacCheckbox()


class LinuxFactory(GUIFactory):
    def create_button(self) -> Button:
        return LinuxButton()

    def create_checkbox(self) -> Checkbox:
        return LinuxCheckbox()


# ── 客户端 ──

class Application:
    """应用 —— 使用抽象工厂创建 UI"""

    def __init__(self, factory: GUIFactory):
        self.factory = factory
        self.button = factory.create_button()
        self.checkbox = factory.create_checkbox()

    def render(self) -> str:
        return f"{self.button.render()}\n{self.checkbox.render()}"


def create_factory(os_type: str) -> GUIFactory:
    """简单工厂 + 抽象工厂 结合"""
    factories = {
        "windows": WindowsFactory(),
        "mac": MacFactory(),
        "linux": LinuxFactory(),
    }
    factory = factories.get(os_type.lower())
    if not factory:
        raise ValueError(f"不支持的操作系统: {os_type}")
    return factory


print("  抽象工厂演示:")
for os_name in ["Windows", "Mac", "Linux"]:
    factory = create_factory(os_name)
    app = Application(factory)
    print(f"\n  {os_name}:")
    print(f"  {app.button.click()}")
    print(f"  {app.checkbox.check()}")


# ====================================
# 2. 建造者模式
# ====================================
print("\n" + "=" * 60)
print("2️⃣ 建造者模式（Builder）")
print("=" * 60)


class Pizza:
    """披萨产品"""

    def __init__(self):
        self.size = None
        self.crust = None
        self.sauce = None
        self.toppings = []
        self.cheese = None
        self.bake_time = 0

    def __repr__(self):
        toppings = ', '.join(self.toppings) if self.toppings else '无'
        return (f"Pizza(size={self.size}\", crust={self.crust}, "
                f"sauce={self.sauce}, cheese={self.cheese}, "
                f"toppings=[{toppings}], "
                f"bake={self.bake_time}min)")


class PizzaBuilder:
    """披萨建造者 —— 链式调用构建复杂对象"""

    def __init__(self):
        self._pizza = Pizza()

    def size(self, inches: int):
        """设置尺寸"""
        valid_sizes = {9, 12, 15, 18}
        if inches not in valid_sizes:
            raise ValueError(f"尺寸必须在 {valid_sizes} 中")
        self._pizza.size = inches
        return self

    def crust(self, type_: str):
        """设置饼底"""
        valid_crusts = ['薄脆', '厚底', '芝心', '全麦']
        if type_ not in valid_crusts:
            raise ValueError(f"饼底必须在 {valid_crusts} 中")
        self._pizza.crust = type_
        return self

    def sauce(self, type_: str):
        """设置酱料"""
        self._pizza.sauce = type_
        return self

    def cheese(self, type_: str, extra: bool = False):
        """设置芝士"""
        self._pizza.cheese = f"{'双倍' if extra else ''}{type_}"
        return self

    def add_topping(self, topping: str):
        """添加配料"""
        self._pizza.toppings.append(topping)
        return self

    def add_toppings(self, *toppings: str):
        """批量添加配料"""
        self._pizza.toppings.extend(toppings)
        return self

    def well_done(self):
        """烤久一点"""
        self._pizza.bake_time = 14
        return self

    def build(self) -> Pizza:
        """构建最终产品"""
        if self._pizza.size is None:
            raise ValueError("必须设置披萨尺寸")
        if self._pizza.bake_time == 0:
            self._pizza.bake_time = 10
        return self._pizza


# 使用建造者
margherita = PizzaBuilder() \
    .size(12) \
    .crust('薄脆') \
    .sauce('番茄') \
    .cheese('马苏里拉') \
    .add_topping('罗勒叶') \
    .build()

pepperoni = PizzaBuilder() \
    .size(15) \
    .crust('厚底') \
    .sauce('番茄') \
    .cheese('马苏里拉', extra=True) \
    .add_toppings('意大利辣香肠', '蘑菇', '青椒') \
    .well_done() \
    .build()

custom = PizzaBuilder() \
    .size(9) \
    .crust('芝心') \
    .sauce('白酱') \
    .cheese('切达') \
    .add_toppings('鸡肉', '菠萝', '洋葱') \
    .build()

print("  🍕 披萨建造者:")
print(f"  • 玛格丽特: {margherita}")
print(f"  • 辣香肠: {pepperoni}")
print(f"  • 定制: {custom}")


# Director 可选
class PizzaChef:
    """披萨师傅 —— Director，封装常见配方"""

    def __init__(self, builder: PizzaBuilder):
        self._builder = builder

    def make_margherita(self) -> Pizza:
        return self._builder \
            .size(12).crust('薄脆') \
            .sauce('番茄').cheese('马苏里拉') \
            .add_topping('罗勒叶').build()

    def make_pepperoni(self) -> Pizza:
        return self._builder \
            .size(15).crust('厚底') \
            .sauce('番茄').cheese('马苏里拉', extra=True) \
            .add_toppings('意大利辣香肠').well_done().build()


chef = PizzaChef(PizzaBuilder())
print("\n  🧑‍🍳 披萨师傅（Director）:")
print(f"  • 经典: {chef.make_margherita()}")
print(f"  • 主厨推荐: {chef.make_pepperoni()}")


# ====================================
# 3. 原型模式
# ====================================
print("\n" + "=" * 60)
print("3️⃣ 原型模式（Prototype）")
print("=" * 60)

import copy


class Prototype:
    """原型基类"""

    def clone(self):
        """浅拷贝"""
        return copy.copy(self)

    def deep_clone(self):
        """深拷贝"""
        return copy.deepcopy(self)


class DocumentTemplate(Prototype):
    """文档模板 —— 使用原型模式快速创建变体"""

    def __init__(self, name: str, header: str, footer: str,
                 content: str = "", variables: dict = None):
        self.name = name
        self.header = header
        self.footer = footer
        self.content = content
        self.variables = variables or {}

    def render(self, **kwargs) -> str:
        merged = {**self.variables, **kwargs}
        result = f"{self.header}\n{self.content}\n{self.footer}"
        for key, value in merged.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def __repr__(self):
        return f"DocumentTemplate({self.name}, vars={self.variables})"


# 创建原型
base_template = DocumentTemplate(
    "基础合同",
    "={ 合同标题: {{title}} }=",
    "--- 甲方签字: ________  乙方签字: ________ ---",
    "兹有 {{party_a}} (甲方) 与 {{party_b}} (乙方) "
    "就 {{subject}} 达成如下协议..."
)

# 通过原型创建变体
service_contract = base_template.clone()
service_contract.name = "服务合同"
service_contract.variables = {
    "title": "服务合同",
    "party_a": "甲方公司",
    "party_b": "乙方公司",
    "subject": "技术服务"
}

nba_contract = base_template.clone()
nba_contract.name = "NBA 球员合同"
nba_contract.variables = {
    "title": "球员合同",
    "party_a": "球队",
    "party_b": "球员姓名",
    "subject": "篮球比赛"
}

print(f"  原型: {base_template}")
print(f"  原型变体1: {service_contract}")
print(f"  原型变体2: {nba_contract}")
print(f"\n  渲染服务合同:")
print(f"  {service_contract.render(party_a='阿里巴巴', party_b='腾讯')}")


# ====================================
# 4. 线程安全的单例
# ====================================
print("\n" + "=" * 60)
print("4️⃣ 线程安全的单例")
print("=" * 60)

import threading


class ThreadSafeSingleton:
    """线程安全的单例 —— 使用锁"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # 双重检查锁定 (Double-Checked Locking)
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, name: str = "default"):
        if not self._initialized:
            self.name = name
            self._initialized = True


def test_singleton(name):
    instance = ThreadSafeSingleton(name)
    print(f"  线程 {threading.current_thread().name}: "
          f"instance.name = {instance.name}, "
          f"id = {id(instance)}")


print("  线程安全单例测试:")
threads = []
for i in range(5):
    t = threading.Thread(target=test_singleton, args=(f"thread-{i}",))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("  ✅ 所有线程获得同一实例")


# ====================================
# 5. 懒初始化与对象池
# ====================================
print("\n" + "=" * 60)
print("5️⃣ 懒初始化与对象池")
print("=" * 60)

import time


class DatabaseConnection:
    """模拟数据库连接"""

    def __init__(self, conn_id: int):
        self.conn_id = conn_id
        print(f"    🏗️ 创建连接 #{conn_id}")
        time.sleep(0.05)  # 模拟创建开销

    def query(self, sql: str) -> str:
        return f"  [连接 #{self.conn_id}] 执行: {sql}"


class ConnectionPool:
    """连接池 —— 对象池模式"""

    def __init__(self, min_size: int = 2, max_size: int = 5):
        self._min_size = min_size
        self._max_size = max_size
        self._pool = []
        self._in_use = set()
        self._counter = 0
        self._lock = threading.Lock()

        # 预热：创建最小连接数
        print(f"  🔥 预热连接池 (min={min_size})...")
        for _ in range(min_size):
            self._create_connection()

    def _create_connection(self) -> DatabaseConnection:
        self._counter += 1
        conn = DatabaseConnection(self._counter)
        return conn

    def acquire(self) -> DatabaseConnection:
        """获取连接"""
        with self._lock:
            # 优先复用空闲连接
            if self._pool:
                conn = self._pool.pop()
                self._in_use.add(conn)
                print(f"  ✅ 复用连接 #{conn.conn_id}")
                return conn

            # 创建新连接（如果没超过上限）
            if len(self._in_use) < self._max_size:
                conn = self._create_connection()
                self._in_use.add(conn)
                print(f"  🆕 新建连接 #{conn.conn_id}")
                return conn

            raise RuntimeError("所有连接都在使用中！")

    def release(self, conn: DatabaseConnection):
        """释放连接"""
        with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                self._pool.append(conn)
                print(f"  ↩️ 释放连接 #{conn.conn_id}")

    @property
    def stats(self) -> dict:
        return {
            "created": self._counter,
            "idle": len(self._pool),
            "in_use": len(self._in_use),
        }


# 演示
print("\n  连接池演示:")
pool = ConnectionPool(min_size=2)

print(f"\n  池状态: {pool.stats}")

# 获取连接
conn1 = pool.acquire()
conn2 = pool.acquire()

print(f"\n  使用连接:")
print(conn1.query("SELECT * FROM users"))
print(conn2.query("SELECT * FROM orders"))

# 释放并获取新连接
pool.release(conn1)
pool.release(conn2)

conn3 = pool.acquire()  # 复用
print(f"\n  池状态: {pool.stats}")
