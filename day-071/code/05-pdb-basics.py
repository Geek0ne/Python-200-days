"""
Day 071 — pdb 调试器基础

运行方式：python 05-pdb-basics.py

pdb 常用命令：
  l        - 显示代码
  n        - 下一步（不进入函数）
  s        - 下一步（进入函数）
  c        - 继续执行
  p var    - 打印变量
  b 10     - 在第 10 行设断点
  q        - 退出
"""
import pdb


def calculate_discount(price, quantity, is_vip=False):
    """计算折扣价格"""
    subtotal = price * quantity

    if is_vip:
        discount = 0.2
    else:
        discount = 0.1

    total = subtotal * (1 - discount)

    # 方式 1：传统 pdb
    # import pdb; pdb.set_trace()

    # 方式 2：Python 3.7+ 推荐
    # breakpoint()

    return total


def find_max(numbers):
    """找最大值"""
    if not numbers:
        return None

    max_val = numbers[0]
    for num in numbers:
        if num > max_val:
            max_val = num
    return max_val


def main():
    print("=" * 50)
    print("🔧 pdb 调试器演示")
    print("=" * 50)

    # 演示 1：正常计算
    result1 = calculate_discount(100, 3, is_vip=True)
    print(f"VIP 折扣: 100 x 3 x 0.8 = {result1}")

    result2 = calculate_discount(100, 3, is_vip=False)
    print(f"普通折扣: 100 x 3 x 0.9 = {result2}")

    # 演示 2：找最大值
    numbers = [3, 1, 4, 1, 5, 9, 2, 6]
    max_val = find_max(numbers)
    print(f"最大值: {max_val}")

    print("\n" + "=" * 50)
    print("💡 调试技巧：")
    print("1. 在代码中添加 breakpoint() 设置断点")
    print("2. 运行程序后会自动暂停")
    print("3. 使用 n/s/p 等命令调试")
    print("4. 使用 c 继续执行")
    print("=" * 50)

    # 如果想测试 pdb，取消下面的注释：
    # breakpoint()
    # print("断点后继续执行")


if __name__ == "__main__":
    main()
