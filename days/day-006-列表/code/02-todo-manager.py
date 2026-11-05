#!/usr/bin/env python3
"""
Day 006 — 实战：待办事项管理器（Todo List Manager）
====================================================
一个完整的命令行待办事项应用，运用列表的所有知识：
- 增删改查
- 排序与筛选
- 状态管理

可直接运行： python3 02-todo-manager.py
"""

import json
import os
from datetime import datetime

# =================================================================
# 数据存储
# =================================================================
# 每个待办事项用字典表示：
# {
#     "id": 1,           # 唯一标识
#     "title": "...",    # 标题
#     "done": False,     # 是否完成
#     "priority": 2,     # 优先级：1(高), 2(中), 3(低)
#     "created_at": "..." # 创建时间
# }

DATA_FILE = "todos_data.json"


def load_todos() -> list:
    """从文件加载待办列表"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_todos(todos: list):
    """保存待办列表到文件"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


# =================================================================
# 核心功能
# =================================================================

def _next_id(todos: list) -> int:
    """生成下一个可用的 ID"""
    if not todos:
        return 1
    return max(t["id"] for t in todos) + 1


def add_todo(todos: list, title: str, priority: int = 2) -> dict:
    """
    添加一个待办事项。

    append 方法 → 在列表末尾添加新元素
    """
    todo = {
        "id": _next_id(todos),
        "title": title,
        "done": False,
        "priority": priority,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    todos.append(todo)
    print(f"  ✅ 已添加: [{todo['id']}] {title}")
    return todo


def list_todos(todos: list, filter_key: str = None, filter_value=None):
    """
    列出所有待办事项（可筛选）。

    enumerate 函数 → 同时获取索引和元素
    列表推导式 → 筛选符合条件的元素
    """
    if not todos:
        print("  📭 待办列表为空")
        return

    # 应用筛选
    if filter_key is not None:
        filtered = [t for t in todos if t.get(filter_key) == filter_value]
    else:
        filtered = todos[:]  # 浅拷贝，不要影响原列表

    if not filtered:
        print("  🔍 没有匹配的待办事项")
        return

    print(f"\n  {'ID':<4} {'状态':<6} {'优先级':<8} {'标题':<20} {'创建时间'}")
    print(f"  {'-'*4} {'-'*6} {'-'*8} {'-'*20} {'-'*16}")

    for todo in filtered:
        status = "✅" if todo["done"] else "⬜"
        priority_str = {1: "🔴高", 2: "🟡中", 3: "🟢低"}.get(
            todo.get("priority", 2), "?"
        )
        print(
            f"  {todo['id']:<4} {status:<6} {priority_str:<8} "
            f"{todo['title']:<20} {todo.get('created_at', '')}"
        )


def toggle_todo(todos: list, todo_id: int) -> bool:
    """
    切换待办事项的完成状态。

    index 方法 → 查找元素位置
    pop/insert → 修改列表元素
    """
    for todo in todos:
        if todo["id"] == todo_id:
            todo["done"] = not todo["done"]
            status = "已完成" if todo["done"] else "未完成"
            print(f"  🔄 [{todo_id}] 已标记为 {status}")
            save_todos(todos)
            return True

    print(f"  ❌ 未找到 ID 为 {todo_id} 的待办事项")
    return False


def remove_todo(todos: list, todo_id: int) -> bool:
    """
    删除一个待办事项。

    remove 方法 → 通过值删除
    """
    for todo in todos:
        if todo["id"] == todo_id:
            todos.remove(todo)
            print(f"  🗑️ 已删除: [{todo_id}] {todo['title']}")
            save_todos(todos)
            return True

    print(f"  ❌ 未找到 ID 为 {todo_id} 的待办事项")
    return False


def sort_todos(todos: list, by: str = "priority", reverse: bool = False):
    """
    对待办列表进行排序。

    sort 方法 → 原地排序
    key 参数 → 自定义排序规则
    """
    sort_keys = {
        "priority": lambda t: t.get("priority", 2),
        "created": lambda t: t.get("created_at", ""),
        "id": lambda t: t["id"],
        "title": lambda t: t["title"],
        "status": lambda t: t["done"],
    }

    key_func = sort_keys.get(by, sort_keys["priority"])
    todos.sort(key=key_func, reverse=reverse)

    print(f"  📊 已按「{by}」排序{'（降序）' if reverse else ''}")
    list_todos(todos)


def search_todos(todos: list, keyword: str):
    """
    搜索待办事项（标题模糊匹配）。

    列表推导式 + in 运算符 → 模糊搜索
    """
    keyword_lower = keyword.lower()
    results = [t for t in todos if keyword_lower in t["title"].lower()]

    if results:
        print(f"  🔍 找到 {len(results)} 个匹配「{keyword}」的待办:")
        list_todos(results)
    else:
        print(f"  🔍 未找到包含「{keyword}」的待办事项")


def clear_done(todos: list):
    """
    清除所有已完成的待办事项。

    列表推导式 → 创建新列表（过滤掉已完成的）
    切片赋值 → 用新列表替换原列表所有元素
    """
    done_count = len([t for t in todos if t["done"]])
    if done_count == 0:
        print("  ℹ️  没有已完成的待办事项")
        return

    # 保留未完成的事项
    todos[:] = [t for t in todos if not t["done"]]
    print(f"  🧹 已清除 {done_count} 项已完成待办")


def show_stats(todos: list):
    """
    显示统计数据。

    len → 总数
    sum + 列表推导式 → 聚合统计
    """
    total = len(todos)
    done = sum(1 for t in todos if t["done"])
    pending = total - done

    # 优先级统计
    high = sum(1 for t in todos if t.get("priority") == 1 and not t["done"])
    medium = sum(1 for t in todos if t.get("priority") == 2 and not t["done"])
    low = sum(1 for t in todos if t.get("priority") == 3 and not t["done"])

    print(f"\n  📊 待办统计")
    print(f"  {'─' * 30}")
    print(f"  总计: {total} 项")
    print(f"  ✅ 已完成: {done}")
    print(f"  ⬜ 待处理: {pending}")
    print(f"  ├─ 🔴 高优先级: {high}")
    print(f"  ├─ 🟡 中优先级: {medium}")
    print(f"  └─ 🟢 低优先级: {low}")
    print(f"  完成率: {done/total*100:.1f}%" if total > 0 else "  暂无数据")


# =================================================================
# 主程序
# =================================================================

def show_menu():
    """显示菜单"""
    print("\n" + "═" * 50)
    print("  📋 Python 待办事项管理器")
    print("═" * 50)
    print("  1. 📝 添加待办")
    print("  2. 📋 查看所有")
    print("  3. ✅ 切换完成状态")
    print("  4. 🗑️  删除待办")
    print("  5. 🔍 搜索")
    print("  6. 📊 排序")
    print("  7. 🧹 清除已完成")
    print("  8. 📈 统计")
    print("  9. 🚪 退出")
    print("═" * 50)


def main():
    """主函数"""
    todos = load_todos()

    # 如果没有任何待办，添加几个示例
    if not todos:
        print("  🌟 首次运行，添加示例待办...")
        add_todo(todos, "学习 Python 列表", priority=1)
        add_todo(todos, "写完 Day 006 的代码", priority=1)
        add_todo(todos, "做练习题", priority=2)
        add_todo(todos, "喝杯咖啡", priority=3)
        save_todos(todos)

    while True:
        show_menu()
        choice = input("\n  👉 请选择操作 (1-9): ").strip()

        if choice == "1":
            title = input("  标题: ").strip()
            if not title:
                print("  ❌ 标题不能为空")
                continue
            priority_str = input("  优先级 (1=高, 2=中, 3=低) [默认2]: ").strip()
            priority = int(priority_str) if priority_str in "123" else 2
            add_todo(todos, title, priority)
            save_todos(todos)

        elif choice == "2":
            print("\n  ── 查看待办 ──")
            print("  a) 全部")
            print("  b) 未完成")
            print("  c) 已完成")
            sub = input("  👉 选择 (a/b/c): ").strip().lower()
            if sub == "b":
                list_todos(todos, "done", False)
            elif sub == "c":
                list_todos(todos, "done", True)
            else:
                list_todos(todos)

        elif choice == "3":
            try:
                tid = int(input("  请输入要切换的 ID: ").strip())
                toggle_todo(todos, tid)
            except ValueError:
                print("  ❌ 请输入有效的数字 ID")

        elif choice == "4":
            try:
                tid = int(input("  请输入要删除的 ID: ").strip())
                remove_todo(todos, tid)
            except ValueError:
                print("  ❌ 请输入有效的数字 ID")

        elif choice == "5":
            keyword = input("  搜索关键词: ").strip()
            search_todos(todos, keyword)

        elif choice == "6":
            print("  排序依据:")
            print("    p) 优先级")
            print("    c) 创建时间")
            print("    t) 标题")
            print("    s) 完成状态")
            by_map = {"p": "priority", "c": "created", "t": "title", "s": "status"}
            sub = input("  👉 选择: ").strip().lower()
            by = by_map.get(sub, "priority")

            rev = input("  降序? (y/n): ").strip().lower() == "y"
            sort_todos(todos, by, rev)
            save_todos(todos)

        elif choice == "7":
            clear_done(todos)
            save_todos(todos)

        elif choice == "8":
            show_stats(todos)

        elif choice == "9":
            save_todos(todos)
            print("  👋 再见！")
            break

        else:
            print("  ❌ 无效选择，请输入 1-9")

        # 每次操作后自动保存
        save_todos(todos)

    # 程序结束，清理临时数据文件
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)


if __name__ == "__main__":
    main()
