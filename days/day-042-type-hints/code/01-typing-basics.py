"""
Day 42 - 01-typing-basics.py
typing 模块基础用法

本文件展示了 typing 模块中最常用的类型提示工具。
所有代码均可直接运行，类型注解被 Python 解释器忽略，
但可以被 mypy / pyright 等工具检查。
"""

from typing import List, Dict, Tuple, Set, Optional, Union, Any, Callable


# ============================================================
# 1. 基础容器类型
# ============================================================

def demo_basic_collections() -> None:
    """
    演示 List, Dict, Tuple, Set 的基本用法。
    Python 3.9+ 可直接使用 list[str] 等内置泛型。
    """
    print("=" * 60)
    print("1. 基础容器类型")
    print("=" * 60)

    # List：同类型元素列表
    names: List[str] = ["Alice", "Bob", "Charlie"]
    names.append("Diana")
    print(f"names = {names}")

    # Dict：键值对映射
    scores: Dict[str, int] = {"Alice": 95, "Bob": 87, "Charlie": 92}
    print(f"scores = {scores}")

    # Tuple：固定长度，每个位置独立类型
    point: Tuple[float, float, str] = (1.5, 3.2, "home")
    x, y, label = point
    print(f"point = ({x}, {y}, '{label}')")

    # Set：无序不重复集合
    tags: Set[str] = {"python", "typing", "basics"}
    tags.add("python")  # 无效果，已存在
    print(f"tags = {tags}")

    print()


def demo_optional_union() -> None:
    """
    演示 Optional 和 Union 的使用场景。

    Optional[X] = Union[X, None]
    表示值可能是 X 类型，也可能是 None。
    Python 3.10+ 可以用 X | None 替代。
    """
    print("=" * 60)
    print("2. Optional 与 Union")
    print("=" * 60)

    # Optional：可能为 None
    def find_user(uid: int, users: Dict[int, str]) -> Optional[str]:
        """根据 uid 查找用户名，找不到返回 None"""
        return users.get(uid)

    users_db: Dict[int, str] = {1: "Alice", 2: "Bob"}
    result1 = find_user(1, users_db)
    result2 = find_user(999, users_db)
    print(f"find_user(1)  = {result1!r}")
    print(f"find_user(999) = {result2!r}")

    # Union：多种可能的类型
    def format_value(value: Union[int, float, str]) -> str:
        """接受 int、float 或 str，统一返回字符串"""
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    print(f"format_value(42)       = {format_value(42)!r}")
    print(f"format_value(3.14159)  = {format_value(3.14159)!r}")
    print(f"format_value('hello')  = {format_value('hello')!r}")

    print()


def demo_any_callable() -> None:
    """
    演示 Any 和 Callable 的使用。

    Any：跳过类型检查的逃生口（应尽量少用）。
    Callable[[参数类型], 返回值类型]：描述可调用对象类型。
    """
    print("=" * 60)
    print("3. Any 与 Callable")
    print("=" * 60)

    # Any：任意类型
    def log_message(message: Any) -> None:
        """接受任意类型的日志消息"""
        print(f"[LOG] {message}")

    log_message("Server started")
    log_message(42)
    log_message([1, 2, 3])
    print("log_message 接受任意类型参数")

    # Callable：描述函数类型
    # Callable[[str, int], str] 表示接受 (str, int) 参数并返回 str 的函数
    def run_processor(
        processor: Callable[[str, int], str],
        text: str,
        times: int,
    ) -> str:
        """运行一个处理器函数"""
        return processor(text, times)

    # 定义一个匹配 Callable[[str, int], str] 的函数
    def repeat(text: str, times: int) -> str:
        return text * times

    result = run_processor(repeat, "Ha! ", 3)
    print(f"run_processor(repeat, 'Ha! ', 3) = {result!r}")

    # 使用 lambda
    result2 = run_processor(lambda t, n: t.upper() * n, "echo", 2)
    print(f"run_processor(lambda, 'echo', 2)  = {result2!r}")

    print()


def demo_literal_final() -> None:
    """
    演示 Literal 和 Final 的用法。
    Python 3.8+ 引入 Literal，3.10+ 广泛使用。
    """
    print("=" * 60)
    print("4. Literal 与 Final")
    print("=" * 60)

    from typing import Literal, Final

    # Literal：限定具体字面量值
    def set_mode(mode: Literal["read", "write", "append"]) -> None:
        """mode 只能是 'read'、'write' 或 'append'"""
        print(f"Mode set to: {mode}")

    set_mode("read")
    set_mode("write")
    # set_mode("delete")  # ← mypy 会报错

    # Final：常量，不可被重新赋值
    MAX_RETRIES: Final[int] = 3
    # MAX_RETRIES = 5  # ← mypy 会报错

    print(f"MAX_RETRIES = {MAX_RETRIES}")
    print()


# ============================================================
# 5. 类型别名
# ============================================================

# 类型别名让复杂类型更易读
UserID = int
UserName = str
UserScore = Optional[int]
UserDict = Dict[UserID, tuple[UserName, UserScore]]


def create_user_db() -> UserDict:
    """创建用户数据库"""
    return {
        1: ("Alice", 95),
        2: ("Bob", None),
        3: ("Charlie", 88),
    }


def demo_type_alias() -> None:
    """演示类型别名"""
    print("=" * 60)
    print("5. 类型别名")
    print("=" * 60)

    db = create_user_db()
    for uid, (name, score) in db.items():
        score_str = f"{score}分" if score is not None else "未考试"
        print(f"  [{uid}] {name}: {score_str}")
    print()


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    """运行所有演示"""
    demo_basic_collections()
    demo_optional_union()
    demo_any_callable()
    demo_literal_final()
    demo_type_alias()
