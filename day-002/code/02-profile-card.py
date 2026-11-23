#!/usr/bin/env python3
"""
Day 002 — 实战案例：个人信息卡片生成器
===================================

一个综合应用变量与数据类型的实战项目。
能够收集用户信息并格式化输出。

运行方式：
  python3 02-profile-card.py          # 交互模式
  echo -e "李明\n28\n175.5\n" | python3 02-profile-card.py  # 管道输入
"""

import sys


def get_user_input() -> dict:
    """
    获取用户输入，返回包含个人信息的字典。
    
    如果 stdin 没有重定向，使用 input() 交互式输入；
    否则从管道读取（方便测试）。
    """
    use_stdin = not sys.stdin.isatty()
    
    if use_stdin:
        # 从管道读取（非交互模式）
        lines = [line.strip() for line in sys.stdin.readlines() if line.strip()]
        name = lines[0] if len(lines) > 0 else "访客"
        age_str = lines[1] if len(lines) > 1 else "0"
        height_str = lines[2] if len(lines) > 2 else "0"
    else:
        # 交互模式
        print("=" * 40)
        print("     📋 个人信息采集")
        print("=" * 40)
        name = input("请输入姓名: ").strip()
        if not name:
            name = "访客"
        
        age_str = input("请输入年龄: ").strip()
        height_str = input("请输入身高(cm): ").strip()
    
    return {"name": name, "age_str": age_str, "height_str": height_str}


def validate_and_convert(data: dict) -> tuple:
    """
    验证输入并转换为正确的数据类型。
    
    返回 (name, age, height, is_student, hobby) 元组。
    如果输入无效，使用默认值。
    """
    name = data["name"]
    
    # 年龄：尝试转换为 int
    try:
        age = int(data["age_str"])
        if age < 0 or age > 150:
            print(f"⚠️  年龄 {age} 超出合理范围(0-150)，使用默认值 0")
            age = 0
    except ValueError:
        print(f"⚠️  年龄 '{data['age_str']}' 无效，使用默认值 0")
        age = 0
    
    # 身高：尝试转换为 float
    try:
        height = float(data["height_str"])
        if height < 0 or height > 300:
            print(f"⚠️  身高 {height}cm 超出合理范围(0-300)，使用默认值 0")
            height = 0.0
    except ValueError:
        print(f"⚠️  身高 '{data['height_str']}' 无效，使用默认值 0")
        height = 0.0
    
    # 是否是学生（根据年龄推断）
    is_student = 6 <= age <= 25
    
    # 爱好：交互模式额外询问，管道模式设为 None
    if sys.stdin.isatty():
        hobby_input = input("请输入爱好（可选，直接回车跳过）: ").strip()
        hobby = hobby_input if hobby_input else None
    else:
        hobby = None
    
    return name, age, height, is_student, hobby


def create_card(name: str, age: int, height: float, 
                is_student: bool, hobby: str | None) -> str:
    """
    创建格式化的个人信息卡片（返回多行字符串）。
    
    此函数展示了 str 类型操作的多种方式：
    - 字符串拼接
    - f-string 格式化
    - 格式化对齐
    - 布尔值条件输出
    - None 值处理
    """
    lines = []
    
    # 卡片边框
    border = "=" * 42
    title_border = "-" * 42
    
    lines.append(border)
    lines.append("  🆔  个人名片")
    lines.append(border)
    
    # 姓名
    lines.append(f"  姓名：{name}")
    
    # 年龄
    age_str = f"{age} 岁"
    if 0 <= age <= 3:
        age_str += " 👶 婴幼儿期"
    elif age <= 12:
        age_str += " 👦 儿童期"
    elif age <= 17:
        age_str += " 🧑 青少年期"
    elif age <= 35:
        age_str += " 🧑 青年期"
    elif age <= 55:
        age_str += " 👨 中年期"
    else:
        age_str += " 👴 老年期"
    lines.append(f"  年龄：{age_str}")
    
    # 身高
    if height > 0:
        lines.append(f"  身高：{height:.1f} cm")
        # 简单体型提示
        bmi = age / (height / 100) ** 2 if height > 0 else 0  # 这不是 BMI，只是演示
        if height < 150:
            lines.append(f"  📐 体型：偏矮")
        elif height > 190:
            lines.append(f"  📐 体型：高大")
        else:
            lines.append(f"  📐 体型：标准")
    else:
        lines.append(f"  身高：未填写")
    
    # 是否学生
    student_status = "🎓 是（学生身份）" if is_student else "💼 否（非学生）"
    lines.append(f"  学生：{student_status}")
    
    # 爱好（可能为 None）
    if hobby is None:
        hobby_display = "未设定"
    else:
        hobby_display = hobby
    lines.append(f"  爱好：{hobby_display}")
    
    # 类型信息（教育性展示）
    lines.append(title_border)
    lines.append("  📊 数据类型一览")
    lines.append(title_border)
    lines.append(f"  姓名 | str   | {name!r}")
    lines.append(f"  年龄 | int   | {age}")
    lines.append(f"  身高 | float | {height}")
    lines.append(f"  学生 | bool  | {is_student}")
    lines.append(f"  爱好 | str/NoneType | {hobby!r}")
    
    # 卡片的 id 信息
    lines.append(title_border)
    lines.append(f"  变量 name 的内存 id: {id(name)}")
    lines.append(f"  变量 age  的内存 id: {id(age)}")
    lines.append(f"  变量 height 的内存 id: {id(height)}")
    
    lines.append(border)
    lines.append("  💡 type() 查看类型 | id() 查看内存地址")
    lines.append(border)
    
    return "\n".join(lines)


def print_type_table():
    """打印数据类型速查表"""
    print()
    print("=" * 42)
    print("         📘 数据类型速查表")
    print("=" * 42)
    
    samples = [
        ("整数", 42, type(42)),
        ("浮点数", 3.14, type(3.14)),
        ("字符串", "你好", type("你好")),
        ("布尔值", True, type(True)),
        ("空值", None, type(None)),
    ]
    
    for name, value, typ in samples:
        print(f"  {name:<8} {str(value):<8} → {typ}")


def main():
    """主函数"""
    print("\n" + "🐍" * 21)
    print("  🌟 个人信息卡片生成器 v1.0")
    print("🐍" * 21 + "\n")
    
    # 步骤 1：获取输入
    raw_data = get_user_input()
    
    # 步骤 2：验证和转换
    name, age, height, is_student, hobby = validate_and_convert(raw_data)
    
    # 步骤 3：创建卡片
    card = create_card(name, age, height, is_student, hobby)
    
    # 步骤 4：输出卡片
    print("\n" + "🎴" * 21)
    print("  生成结果如下")
    print("🎴" * 21 + "\n")
    
    # 模拟延迟效果（非交互模式跳过）
    if sys.stdin.isatty():
        import time
        print("生成中", end="", flush=True)
        for _ in range(3):
            time.sleep(0.3)
            print(".", end="", flush=True)
        print(" ✅\n")
    
    print(card)
    
    # 额外：类型速查
    print_type_table()
    
    print("\n✅ 个人信息卡片生成完毕！")


if __name__ == "__main__":
    main()
