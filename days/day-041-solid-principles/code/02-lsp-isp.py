"""
Day 41 - 里氏替换原则（LSP）和接口隔离原则（ISP）示例

本文件包含两个原则的独立演示，每个示例都可直接运行。

运行方式：
    python3 days/day-041-solid-principles/code/02-lsp-isp.py
"""

# ============================================================
# 第一部分：LSP（里氏替换原则）
# ============================================================

print("=" * 60)
print("第一部分：LSP — 里氏替换原则")
print("=" * 60)

from abc import ABC, abstractmethod


# --- 违反 LSP 的反例：典型的长方形 vs 正方形问题 ---

class BadRectangle:
    """长方形"""

    def __init__(self, width: float, height: float):
        self._width = width
        self._height = height

    def set_width(self, w: float):
        self._width = w

    def set_height(self, h: float):
        self._height = h

    def area(self) -> float:
        return self._width * self._height


class BadSquare(BadRectangle):
    """
    正方形 —— 看似"是一个"长方形，但行为违背 LSP
    
    子类修改了父类的行为契约（set_width 和 set_height 会互相影响），
    导致任何依赖 BadRectangle 的代码在使用 BadSquare 时都会出问题。
    """

    def set_width(self, w: float):
        self._width = w
        self._height = w  # 强行使宽高相等！

    def set_height(self, h: float):
        self._height = h
        self._width = h  # 强行使宽高相等！

    def area(self) -> float:
        return self._width * self._width  # 等同于 self._width ** 2


def test_rectangle_lsp(rect: BadRectangle):
    """
    这个函数假设：set_width 只改宽度，set_height 只改高度
    
    对 BadRectangle ✅ 通过
    对 BadSquare    ❌ 失败（因为 set_width 也改了高度）
    """
    rect.set_width(5)
    rect.set_height(10)

    expected = 50  # 5 * 10
    actual = rect.area()

    if actual == expected:
        print(f"    ✅ 测试通过: area = {actual}")
    else:
        print(f"    ❌ 测试失败: 期望 {expected}, 实际 {actual}")
        print(f"       BadSquare.set_width(5) 也把 height 改成了 5！")


print("\n>> LSP 违反演示 —— 长方形 vs 正方形:")

bad_rect = BadRectangle(0, 0)
print("  BadRectangle 测试:")
test_rectangle_lsp(bad_rect)

bad_sq = BadSquare(0, 0)
print("  BadSquare 测试:")
test_rectangle_lsp(bad_sq)

print("\n  教训: 现实中的 ‘is-a’ 关系（正方形是一种长方形）")
print("  并不等于编程中的 'is-substitutable' 关系。")


# --- 遵循 LSP 的正确设计 ---

class Shape(ABC):
    """抽象形状 —— 正确的抽象层次"""

    @abstractmethod
    def area(self) -> float:
        pass


class Rectangle(Shape):
    """长方形"""

    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height


class Square(Shape):
    """正方形 —— 有自己独立的 setter，不影响父类契约"""

    def __init__(self, side: float):
        self.side = side

    def area(self) -> float:
        return self.side ** 2

    # 注意：Square 没有 set_width/set_height
    # 它只需要自己的 set_side()


def print_area(shapes: list[Shape]):
    """这个函数接受任何 Shape 子类型 —— 遵循 LSP"""
    print(f"\n  LSP 正确设计: 多种形状的面积计算")
    for shape in shapes:
        print(f"    {type(shape).__name__}: area = {shape.area()}")


print("\n>> LSP 正确设计演示:")
shapes = [
    Rectangle(5, 10),
    Square(7),
    Rectangle(3, 4),
    Square(5),
]
print_area(shapes)


# --- LSP 的 Python 特有场景：鸭子类型 ---

class Duck:
    def quack(self):
        return "🦆 鸭子嘎嘎叫"

    def swim(self):
        return "🦆 鸭子游泳"


class RobotDuck:
    def quack(self):
        return "🤖 机器鸭嘎嘎声"

    def swim(self):
        return "🤖 机器鸭滑行"


def make_it_quack(thing):
    """
    鸭子类型天然支持 LSP —— 只要对象实现了所需方法，
    就可以替换，不需要继承关系。
    """
    print(f"    {thing.quack()}")


print("\n>> Python 鸭子类型与 LSP:")
make_it_quack(Duck())
make_it_quack(RobotDuck())

print("\n  ✅ Python 的鸭子类型在很多场景天然实现了 LSP")


# --- LSP 违反的另一个常见反例：不正确的异常 ---

class Bird(ABC):
    @abstractmethod
    def move(self) -> str:
        pass

    @abstractmethod
    def eat(self) -> str:
        pass


class Sparrow(Bird):
    def move(self) -> str:
        return "🐦 麻雀飞行"

    def eat(self) -> str:
        return "🐦 麻雀吃虫子"


class Penguin(Bird):
    def move(self) -> str:
        return "🐧 企鹅走路/游泳"

    def eat(self) -> str:
        return "🐧 企鹅吃鱼"


class Ostrich(Bird):
    def move(self) -> str:
        return "🦩 鸵鸟奔跑（虽然不会飞）"

    def eat(self) -> str:
        return "🦩 鸵鸟吃植物"


print("\n>> LSP 场景对比 —— 正确的抽象设计:")
print("  将 Bird 抽象为 move() 而非 fly() 是正确设计")
print("  企鹅和鸵鸟都继承了 move() 并合理实现")
birds = [Sparrow(), Penguin(), Ostrich()]
for b in birds:
    print(f"    {b.move()} | {b.eat()}")


# ============================================================
# 第二部分：ISP（接口隔离原则）
# ============================================================

print("\n" + "=" * 60)
print("第二部分：ISP — 接口隔离原则")
print("=" * 60)


# --- 违反 ISP 的反例 ---

class Worker(ABC):
    """胖接口 —— 包含了所有可能的 worker 方法"""

    @abstractmethod
    def work(self) -> str:
        pass

    @abstractmethod
    def eat(self) -> str:
        pass

    @abstractmethod
    def sleep(self) -> str:
        pass

    @abstractmethod
    def code_review(self) -> str:
        pass


class HumanDeveloper(Worker):
    """人类开发者 —— 需要全部四个方法，尚且合理"""

    def work(self) -> str:
        return "👨‍💻 人类开发者在写代码"

    def eat(self) -> str:
        return "🍜 人类开发者在吃泡面"

    def sleep(self) -> str:
        return "😴 人类开发者在睡觉"

    def code_review(self) -> str:
        return "👀 人类开发者在审查代码"


class RobotCI(Worker):
    """
    CI 机器人 —— 被迫实现无意义的方法
    
    问题：RobotCI 并不 eat/sleep，却必须实现这些方法
    这违反 ISP —— 客户端被迫依赖不需要的接口
    """

    def work(self) -> str:
        return "🤖 CI 机器人在运行测试"

    def eat(self) -> str:
        raise NotImplementedError("CI 机器人不需要吃饭！")

    def sleep(self) -> str:
        raise NotImplementedError("CI 机器人不需要睡觉！")

    def code_review(self) -> str:
        return "🔍 CI 机器人在检查代码风格"


print("\n>> ISP 违反演示:")
human = HumanDeveloper()
robot = RobotCI()
print(f"  {human.work()}")
print(f"  {human.eat()}")

try:
    print(f"  {robot.eat()}")
except NotImplementedError as e:
    print(f"  调用 robot.eat(): {e}  (❌ 接口污染)")
try:
    print(f"  {robot.sleep()}")
except NotImplementedError as e:
    print(f"  调用 robot.sleep(): {e} (❌ 接口污染)")


# --- 遵循 ISP 的正确设计 ---

class Workable(ABC):
    """接口 1：可工作的"""

    @abstractmethod
    def work(self) -> str:
        pass


class Eatable(ABC):
    """接口 2：可进食的"""

    @abstractmethod
    def eat(self) -> str:
        pass


class Sleepable(ABC):
    """接口 3：可睡眠的"""

    @abstractmethod
    def sleep(self) -> str:
        pass


class CodeReviewable(ABC):
    """接口 4：可审查代码的"""

    @abstractmethod
    def code_review(self) -> str:
        pass


class GoodHumanDeveloper(Workable, Eatable, Sleepable, CodeReviewable):
    """人类开发者 —— 实现全部需要的接口"""

    def work(self) -> str:
        return "👨‍💻 写代码"

    def eat(self) -> str:
        return "🍜 吃泡面"

    def sleep(self) -> str:
        return "😴 睡觉"

    def code_review(self) -> str:
        return "👀 审查代码"


class GoodRobotCI(Workable, CodeReviewable):
    """CI 机器人 —— 只实现需要的接口，不再有 NotImplementedError"""

    def work(self) -> str:
        return "🤖 运行测试"

    def code_review(self) -> str:
        return "🔍 检查代码风格"


class GoodCoffeeMaker(Workable, Eatable):
    """咖啡机 —— 只能工作（煮咖啡）和吃（消耗咖啡豆），不需要睡觉"""

    def work(self) -> str:
        return "☕ 咖啡机在煮咖啡"

    def eat(self) -> str:
        return "☕ 咖啡机消耗了咖啡豆"


print("\n>> ISP 正确设计演示:")
good_human = GoodHumanDeveloper()
good_robot = GoodRobotCI()
good_coffee = GoodCoffeeMaker()

workers = [good_human, good_robot, good_coffee]
print("  所有工作者都能 work():")
for w in workers:
    print(f"    {w.work()}")

print("\n  只有需要 eat 的才实现 Eatable:")
eaters = [w for w in workers if isinstance(w, Eatable)]
for e in eaters:
    print(f"    {e.eat()}")

print("\n  只有需要 sleep 的才实现 Sleepable:")
sleepers = [w for w in workers if isinstance(w, Sleepable)]
for s in sleepers:
    print(f"    {s.sleep()}")

print("\n  ✅ ISP 优势: 每个类只实现自己需要的接口")
print("  ✅ 没有 NotImplementedError, 类型安全")


# --- ISP + Python Protocol（现代做法） ---

print("\n" + "=" * 60)
print("第三部分：ISP + Python Protocol（优雅做法）")
print("=" * 60)

from typing import Protocol, runtime_checkable


@runtime_checkable
class Drawable(Protocol):
    """可以被绘制的东西"""
    def draw(self) -> str: ...


@runtime_checkable
class Resizable(Protocol):
    """可以被调整大小的东西"""
    def resize(self, factor: float) -> str: ...


@runtime_checkable
class Colorable(Protocol):
    """可以有颜色的东西"""
    def set_color(self, color: str) -> str: ...


class Circle:
    """圆 —— 可绘制、可上色"""

    def draw(self) -> str:
        return "⭕ 绘制圆形"

    def set_color(self, color: str) -> str:
        return f"⭕ 设置圆形颜色为 {color}"


class RectangleShape:
    """矩形 —— 可绘制、可调整大小"""

    def draw(self) -> str:
        return "▭ 绘制矩形"

    def resize(self, factor: float) -> str:
        return f"▭ 矩形尺寸调整为 {factor}倍"


class AdvancedImage:
    """高级图片 —— 支持全部操作"""

    def draw(self) -> str:
        return "🖼️ 绘制图片"

    def resize(self, factor: float) -> str:
        return f"🖼️ 图片尺寸调整为 {factor}倍"

    def set_color(self, color: str) -> str:
        return f"🖼️ 设置图片色调为 {color}"


# 使用 Protocol 实现 ISP —— 函数只依赖自己需要的"接口"
def render_shapes(shapes: list[Drawable]):
    """只依赖 Drawable 接口"""
    print("  渲染所有可绘制的对象:")
    for shape in shapes:
        print(f"    {shape.draw()}")


def resize_all(resizables: list[Resizable], factor: float):
    """只依赖 Resizable 接口"""
    print(f"\n  调整所有可调整大小的对象 (factor={factor}):")
    for r in resizables:
        print(f"    {r.resize(factor)}")


print("\n>> Protocol + ISP 演示:")
render_shapes([Circle(), RectangleShape(), AdvancedImage()])
resize_all([RectangleShape(), AdvancedImage()], 2.0)

print("\n  ✅ Protocol 是 Python 实现 ISP 的最佳方式")
print("  ✅ 没有继承关系，只靠方法签名匹配")


# ============================================================
# 总结
# ============================================================

print("\n" + "=" * 60)
print("总结")
print("=" * 60)
print("""
  LSP（里氏替换原则）：
    - 子类必须可完全替换父类，而不改变程序正确性
    - 核心：行为契约，而非现实分类
    - Python 的鸭子类型天然支持 LSP（但也要注意前置/后置条件）

  ISP（接口隔离原则）：
    - 接口要小而专，客户端不依赖不需要的方法
    - 避免 NotImplementedError（这是 ISP 违反的明显信号）
    - Python Protocol 是实现 ISP 的现代推荐方式
""")
