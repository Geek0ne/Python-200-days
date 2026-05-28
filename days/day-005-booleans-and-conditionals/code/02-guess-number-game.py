"""
Day 005 — 实战：猜数字游戏
======================================================================
综合应用布尔值、条件判断、逻辑运算等知识。
可直接运行: python3 02-guess-number-game.py
"""

import random
import sys


# =====================================================================
# 核心游戏逻辑
# =====================================================================

def generate_hint(target: int, guess: int) -> str:
    """
    生成方向提示（使用三元表达式 + 德摩根定律）
    
    参数:
        target: 目标数字
        guess: 玩家猜测
    
    返回:
        提示字符串
    """
    # 使用三元表达式生成提示
    return "🎉 猜中了！" if guess == target else (
        "📈 太小了，大一点" if guess < target else "📉 太大了，小一点"
    )


def get_valid_guess(min_val: int, max_val: int) -> int | None:
    """
    获取有效的用户猜测输入
    
    参数:
        min_val: 最小值
        max_val: 最大值
    
    返回:
        有效数字，或 None（用户退出）
    """
    while True:
        raw_input = input(f"\n请输入 {min_val}-{max_val} 之间的数字（输入 q 退出）: ").strip()
        
        # 检查退出条件
        if raw_input.lower() in ("q", "quit", "exit"):
            return None
        
        # 使用短路求值：先检查能否转为数字，再检查范围
        try:
            guess = int(raw_input)
        except ValueError:
            print("❌ 无效输入，请输入整数！")
            continue
        
        # 使用链式比较检查范围
        if min_val <= guess <= max_val:
            return guess
        else:
            print(f"❌ 数字超出范围！请输入 {min_val}-{max_val} 之间的整数。")


def guess_number_game(
    min_val: int = 1,
    max_val: int = 100,
    max_attempts: int = 7,
) -> dict:
    """
    猜数字游戏主逻辑
    
    参数:
        min_val: 范围最小值
        max_val: 范围最大值
        max_attempts: 最大尝试次数
    
    返回:
        包含游戏统计信息的字典
    """
    # 生成随机目标数字
    target = random.randint(min_val, max_val)
    attempts = 0
    history = []
    
    print(f"\n{'='*60}")
    print(f"  🎯 猜数字游戏")
    print(f"{'='*60}")
    print(f"\n📋 规则:")
    print(f"  • 猜测范围: {min_val} ~ {max_val}")
    print(f"  • 最大次数: {max_attempts} 次")
    print(f"  • 输入 q 随时退出")
    
    while attempts < max_attempts:
        attempts += 1
        print(f"\n{'─'*40}")
        print(f"  🔢 第 {attempts}/{max_attempts} 次猜测")
        print(f"{'─'*40}")
        
        # 获取玩家输入
        guess = get_valid_guess(min_val, max_val)
        
        # 检查是否退出
        if guess is None:
            return {
                "won": False,
                "target": target,
                "attempts": attempts - 1,  # 不计数退出那次
                "history": history,
                "quit_early": True,
            }
        
        # 记录猜测
        history.append(guess)
        
        # 条件判断核心逻辑
        if guess == target:
            remaining = max_attempts - attempts
            
            # 利用 Truthy/Falsy：剩余次数为 0 时输出不同内容
            message = (
                f"🎉 恭喜你猜中了！目标数字就是 {target}！\n"
                f"📊 用了 {attempts} 次 {'机会' if attempts == 0 else '机会'}"
            )
            if remaining:
                message += f"\n💪 还剩 {remaining} 次机会没用到！"
            
            print(f"\n{'='*60}")
            print(f"  {message}")
            print(f"{'='*60}")
            
            return {
                "won": True,
                "target": target,
                "attempts": attempts,
                "history": history,
                "quit_early": False,
            }
        else:
            # 使用三元表达式获取提示
            hint = generate_hint(target, guess)
            
            # 计算差距百分比（用绝对值）
            diff_percent = abs(guess - target) / max_val * 100
            
            # 使用布尔值做条件输出
            if diff_percent > 30:
                cold_warm = "❄️ 还很远"
            elif diff_percent > 15:
                cold_warm = "🌤️ 有动静"
            elif diff_percent > 5:
                cold_warm = "🔥 很近了！ "
            else:
                cold_warm = "🔥🔥 近在咫尺！"
            
            # 输出提示（使用 f-string 格式化）
            print(f"\n  {hint}")
            print(f"  {cold_warm} (相差 {abs(guess - target)} 个数)")
            
            # 显示剩余机会
            remaining = max_attempts - attempts
            print(f"\n  ⏳ 还剩 {remaining} 次机会" if remaining > 0 else "\n  ⚠️  最后一次机会！")
    
    # 所有机会用完
    print(f"\n{'='*60}")
    print(f"  😅 游戏结束！")
    print(f"  🎯 目标数字是: {target}")
    print(f"  📊 你猜了 {attempts} 次，全部用完")
    print(f"{'='*60}")
    
    return {
        "won": False,
        "target": target,
        "attempts": attempts,
        "history": history,
        "quit_early": False,
    }


# =====================================================================
# 统计与复盘功能
# =====================================================================

def analyze_game(stats: dict):
    """
    分析游戏数据（使用条件判断和布尔值）
    
    参数:
        stats: 游戏统计字典
    """
    print(f"\n{'='*60}")
    print(f"  📊 数据复盘")
    print(f"{'='*60}")
    
    # 使用布尔值判断
    if not stats["won"]:
        if stats["quit_early"]:
            print(f"\n  ℹ️  提前退出")
        else:
            print(f"\n  😔 未猜中")
    else:
        print(f"\n  🎉 猜中！")
    
    print(f"  🎯 目标数字: {stats['target']}")
    print(f"  🔢 猜测次数: {stats['attempts']}")
    
    if stats["history"]:
        # 分析猜测历史（使用条件判断）
        history = stats["history"]
        
        # 判断猜测趋势（使用链式比较）
        if len(history) >= 2:
            first_diff = abs(history[0] - stats["target"])
            last_diff = abs(history[-1] - stats["target"])
            
            if last_diff < first_diff:
                print(f"  📈 趋势: 不断接近目标 👍")
            elif last_diff == 0 and stats["won"]:
                print(f"  📈 趋势: 最终命中 🎯")
            else:
                print(f"  📉 趋势: 猜测方向波动较大")
        
        # 显示猜测序列
        print(f"\n  猜测序列: {' → '.join(str(h) for h in history)}")
    
    # 评分（使用多重条件判断）
    attempts = stats["attempts"]
    
    if not stats["won"]:
        rating = "❌ 无评级"
    elif attempts <= 2:
        rating = "🏆 S 级 — 简直是读心术！"
    elif attempts <= 4:
        rating = "⭐ A 级 — 非常厉害！"
    elif attempts <= 6:
        rating = "👍 B 级 — 表现不错"
    else:
        rating = "💪 C 级 — 刚好过关"
    
    print(f"\n  {rating}")


# =====================================================================
# 难度选择系统（演示条件嵌套与守卫子句）
# =====================================================================

def select_difficulty() -> tuple:
    """
    选择游戏难度
    
    返回:
        (min_val, max_val, max_attempts) 元组
    """
    print("\n  🎮 选择难度:")
    print("    1. 简单 (1-50, 10 次机会)")
    print("    2. 普通 (1-100, 7 次机会)")
    print("    3. 困难 (1-200, 5 次机会)")
    print("    4. 地狱 (1-1000, 8 次机会)")
    
    choice = input("\n  请选择 (1-4，默认 2): ").strip()
    
    # 守卫子句风格
    if not choice:
        return (1, 100, 7)  # 默认普通
    
    if choice == "1":
        return (1, 50, 10)
    elif choice == "2":
        return (1, 100, 7)
    elif choice == "3":
        return (1, 200, 5)
    elif choice == "4":
        return (1, 1000, 8)
    else:
        print("  无效选择，使用默认难度（普通）")
        return (1, 100, 7)


# =====================================================================
# AI 对手（演示逻辑运算在算法中的应用）
# =====================================================================

def ai_guess(min_val: int, max_val: int, target: int) -> dict:
    """
    AI 使用二分查找策略猜测数字
    
    参数:
        min_val: 范围最小值
        max_val: 范围最大值
        target: 目标数字
    
    返回:
        AI 游戏统计
    """
    print(f"\n{'='*60}")
    print(f"  🤖 AI 猜数字演示（二分查找）")
    print(f"{'='*60}")
    print(f"  🎯 目标: {target}（隐藏值）")
    print(f"  📋 范围: {min_val}-{max_val}")
    
    low, high = min_val, max_val
    attempts = 0
    history = []
    
    while low <= high:
        attempts += 1
        # 二分查找核心：取中间值
        mid = (low + high) // 2
        history.append(mid)
        
        print(f"\n  🤖 AI 猜测第 {attempts} 次: {mid}")
        
        # 条件判断核心
        if mid == target:
            print(f"  ✅ AI 猜中了！目标就是 {mid}")
            break
        elif mid < target:
            print(f"  📈 AI 说: 目标大于 {mid}，继续搜索右半区间")
            low = mid + 1
        else:  # mid > target
            print(f"  📉 AI 说: 目标小于 {mid}，继续搜索左半区间")
            high = mid - 1
    
    # AI 结果显示
    print(f"\n{'─'*40}")
    print(f"  📊 AI 统计:")
    print(f"  • 猜测次数: {attempts}")
    print(f"  • 猜测序列: {history}")
    
    # 计算理论最小次数
    import math
    theoretical_min = math.ceil(math.log2(max_val - min_val + 1))
    print(f"  • 理论最少次数: {theoretical_min}")
    print(f"  • {'✅ AI 最优！' if attempts <= theoretical_min else '⚠️  有优化空间'}")
    
    return {"attempts": attempts, "history": history}


# =====================================================================
# 批量测试模式（演示条件判断 + 统计）
# =====================================================================

def batch_test(rounds: int = 1000):
    """
    批量测试模式：让 AI 自动玩多轮并统计胜率
    
    参数:
        rounds: 测试轮数
    """
    print(f"\n{'='*60}")
    print(f"  🔬 批量测试模式（{rounds} 轮）")
    print(f"{'='*60}")
    
    min_val, max_val = 1, 100
    won_count = 0
    total_attempts = 0
    
    for i in range(1, rounds + 1):
        target = random.randint(min_val, max_val)
        low, high = min_val, max_val
        attempts = 0
        won = False
        
        while low <= high:
            attempts += 1
            mid = (low + high) // 2
            
            if attempts > 100:  # 安全阀
                break
            
            if mid == target:
                won = True
                break
            elif mid < target:
                low = mid + 1
            else:
                high = mid - 1
        
        if won:
            won_count += 1
            total_attempts += attempts
    
    # 统计结果输出
    win_rate = (won_count / rounds) * 100
    avg_attempts = total_attempts / won_count if won_count > 0 else 0
    
    print(f"\n  测试结果:")
    print(f"  • 总轮数: {rounds}")
    print(f"  • 胜利场次: {won_count}")
    print(f"  • 胜率: {win_rate:.2f}%")
    print(f"  • 平均猜测次数: {avg_attempts:.2f}")
    print(f"  • {'🎉 100% 胜率！二分查找总是能赢' if win_rate == 100 else '⚠️  出现异常'}")


# =====================================================================
# 欢迎界面
# =====================================================================

def show_welcome():
    """显示欢迎界面"""
    print(f"""
{'='*60}
  🐍 Python Day 005 实战 — 猜数字游戏
  {'='*60}
  
  📖 本游戏演示了以下知识点：
  
  1️⃣  布尔类型 — bool 是 int 的子类
  2️⃣  Truthy/Falsy — 空字符串、0、None 等判假规则
  3️⃣  比较运算符 — ==, !=, >, <, >=, <=, is, in
  4️⃣  逻辑运算符 — and, or, not 的短路求值
  5️⃣  条件分支 — if/elif/else + 守卫子句
  6️⃣  三元表达式 — 值_when_true if 条件 else 值_when_false
  
  {'='*60}
""")


# =====================================================================
# 主菜单
# =====================================================================

def main():
    """主程序入口"""
    show_welcome()
    
    while True:
        print("\n📋 功能菜单:")
        print("  1. 🎮 开始游戏")
        print("  2. 🤖 AI 演示（二分查找）")
        print("  3. 🔬 批量测试")
        print("  4. ❌ 退出")
        
        choice = input("\n 请选择 (1-4): ").strip()
        
        if not choice or choice == "1":
            # 选择难度
            min_val, max_val, max_attempts = select_difficulty()
            # 开始游戏
            stats = guess_number_game(min_val, max_val, max_attempts)
            analyze_game(stats)
            
        elif choice == "2":
            # AI 演示
            target = random.randint(1, 100)
            ai_guess(1, 100, target)
            
        elif choice == "3":
            try:
                rounds = input("  测试轮数 (默认 1000): ").strip()
                rounds = int(rounds) if rounds else 1000
                if rounds > 0:
                    batch_test(rounds)
                else:
                    print("  ❌ 轮数必须大于 0")
            except ValueError:
                print("  ❌ 请输入有效数字")
                
        elif choice == "4":
            print("\n  👋 再见！")
            break
        else:
            print("  ❌ 无效选择，请重试")


# =====================================================================
# 程序入口
# =====================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  👋 程序被用户中断，再见！")
        sys.exit(0)
