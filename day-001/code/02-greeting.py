#!/usr/bin/env python3
"""
实战项目：个性化问候程序
运行: python3 greeting.py
"""

import datetime
import sys


def main():
    """程序主入口"""
    print("\n" + "🌟" * 20)
    print("  欢迎使用 Python 问候程序")
    print("🌟" * 20 + "\n")

    # 获取用户名
    name = input("你好！请问你叫什么名字？ ").strip()

    if not name:
        name = "朋友"

    # 获取当前时间
    now = datetime.datetime.now()
    hour = now.hour

    # 根据时间判断问候语
    if 5 <= hour < 12:
        greeting = "☀️ 早上好"
    elif 12 <= hour < 14:
        greeting = "🌤️ 中午好"
    elif 14 <= hour < 18:
        greeting = "🌅 下午好"
    else:
        greeting = "🌙 晚上好"

    # 输出个性化问候
    width = 46
    print("\n" + "=" * width)
    print(f"  {greeting}，{name}！")
    print(f"  欢迎来到 {now.year} 年的 Python 世界！")
    print(f"  这是你的第一个 Python 程序 🎉")
    print("=" * width)

    # 小彩蛋：根据名字长度显示
    if len(name) <= 2:
        print(f"  哇，{name} 的名字好简洁！")
    elif len(name) <= 4:
        print(f"  {name}，朗朗上口的好名字！")
    else:
        print(f"  {name}，名字很有特色！")

    print("=" * width)

    # 系统信息
    print(f"\n📊 系统信息")
    print(f"  Python 版本: {sys.version.split()[0]}")
    print(f"  平台: {sys.platform}")
    print(f"  当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  星期: {['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}")

    # 鼓励语句
    quotes = [
        "千里之行，始于足下。",
        "每一个大师都曾是新手。",
        "代码改变世界。",
        "保持好奇，持续学习。",
    ]
    import random
    print(f"\n💡 今日寄语：{random.choice(quotes)}")
    print()


if __name__ == "__main__":
    main()
