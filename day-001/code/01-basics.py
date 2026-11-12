#!/usr/bin/env python3
"""
Day 001 - 基础代码示例集合
"""

import sys
import dis
import datetime


def demo_print():
    """print() 函数各种用法"""
    print("=" * 50, "print() 用法", "=" * 50)

    # 基础
    print("Hello, World!")

    # 多参数
    print("Hello", "World")

    # 自定义分隔符
    print("2026", "05", "26", sep="-")

    # 不换行
    print("加载中", end="")
    print("...完成!")

    # 格式化
    name, score = "小明", 95.5
    print(f"{name} 的分数是 {score} 分")
    print("{} 的分数是 {} 分".format(name, score))

    print()


def demo_bytecode():
    """查看 Python 字节码"""
    print("=" * 50, "字节码分析", "=" * 50)

    def greet(name):
        msg = f"Hello, {name}!"
        print(msg)
        return len(msg)

    dis.dis(greet)
    print()


def demo_interactive():
    """模拟交互式输入输出"""
    print("=" * 50, "输入输出", "=" * 50)

    name = input("请输入你的名字: ")
    age = input("请输入你的年龄: ")

    print(f"\n你好, {name}!")
    print(f"你今年 {age} 岁，Python 欢迎你！")

    # 类型转换
    age_num = int(age)
    birth_year = 2026 - age_num
    print(f"你大概出生于 {birth_year} 年前后")
    print()


def demo_datetime():
    """日期和时间演示"""
    print("=" * 50, "日期时间", "=" * 50)

    now = datetime.datetime.now()
    print(f"当前时间: {now}")
    print(f"年: {now.year}")
    print(f"月: {now.month}")
    print(f"日: {now.day}")
    print(f"时: {now.hour}:{now.minute}:{now.second}")

    # 格式化
    print(f"格式化: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"中文格式: {now.strftime('%Y 年 %m 月 %d 日')}")
    print()


def demo_system_info():
    """系统信息"""
    print("=" * 50, "系统信息", "=" * 50)

    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"Python 实现: {sys.implementation.name}")
    print(f"操作系统: {sys.platform}")
    print(f"路径编码: {sys.getfilesystemencoding()}")
    print(f"默认编码: {sys.getdefaultencoding()}")
    print()


if __name__ == "__main__":
    demo_print()
    demo_bytecode()
    demo_datetime()
    demo_system_info()

    # 如果交互式模式
    if "-i" in sys.argv:
        demo_interactive()
