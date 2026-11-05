#!/usr/bin/env python3
"""
07-list-playground.py — Day 006 补充
列表趣味应用：排序可视化、井字棋、数据流分析

可直接运行：python3 07-list-playground.py
"""

import random
import time
from typing import List, Optional


# ============================================================
# 应用 1：排序可视化（ASCII 柱状图）
# ============================================================

def visualize_sort():
    """用 ASCII 柱状图可视化排序过程"""
    print("=" * 60)
    print("  应用 1: 排序过程可视化")
    print("=" * 60)

    def display(arr, label=""):
        """以柱状图显示列表"""
        max_val = max(arr) if arr else 1
        print(f"  {label}")
        for i, val in enumerate(arr):
            bar_len = int(val / max_val * 20)
            bar = "█" * bar_len
            print(f"    [{i:2d}] {val:3d} {bar}")
        print()

    def bubble_sort_visual(arr):
        """冒泡排序 — 每一步可视化"""
        arr = arr.copy()
        n = len(arr)
        display(arr, "初始状态:")
        steps = 0

        for i in range(n):
            swapped = False
            for j in range(n - 1 - i):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    swapped = True
                    steps += 1
            if not swapped:
                break
            if steps % 2 == 0:  # 每两步显示一次，避免太多输出
                display(arr, f"第 {i+1} 轮后:")

        display(arr, f"排序完成（{steps} 次交换）:")
        return arr

    data = [random.randint(1, 50) for _ in range(8)]
    print(f"\n  原始数据: {data}")
    bubble_sort_visual(data)


# ============================================================
# 应用 2：井字棋（Tic-Tac-Toe）
# ============================================================

def tic_tac_toe():
    """用列表实现简单的井字棋游戏"""
    print("\n" + "=" * 60)
    print("  应用 2: 命令行井字棋")
    print("=" * 60)

    class TicTacToe:
        """井字棋游戏"""
        WINNING_LINES = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # 行
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # 列
            [0, 4, 8], [2, 4, 6],             # 对角线
        ]

        def __init__(self):
            self.board = [" "] * 9  # 3×3 棋盘，用一维列表表示

        def display(self):
            """显示棋盘"""
            b = self.board
            print(f"\n      {b[0]} │ {b[1]} │ {b[2]}")
            print("     ───┼───┼───")
            print(f"      {b[3]} │ {b[4]} │ {b[5]}")
            print("     ───┼───┼───")
            print(f"      {b[6]} │ {b[7]} │ {b[8]}")

        def move(self, pos: int, player: str) -> bool:
            """下棋"""
            if pos < 0 or pos > 8 or self.board[pos] != " ":
                return False
            self.board[pos] = player
            return True

        def check_winner(self) -> Optional[str]:
            """检查是否有赢家"""
            for line in self.WINNING_LINES:
                if self.board[line[0]] == self.board[line[1]] == self.board[line[2]] != " ":
                    return self.board[line[0]]
            return None

        def is_full(self) -> bool:
            return " " not in self.board

        def get_available_moves(self) -> List[int]:
            """获取可用位置"""
            return [i for i, v in enumerate(self.board) if v == " "]

        def evaluate(self) -> int:
            """评估当前局面（AI 用）"""
            winner = self.check_winner()
            if winner == "O":
                return 10
            elif winner == "X":
                return -10
            return 0

        def minimax(self, depth: int, is_maximizing: bool) -> int:
            """极小极大算法 — AI 决策"""
            score = self.evaluate()
            if score != 0:
                return score - depth if is_maximizing else score + depth
            if self.is_full():
                return 0

            if is_maximizing:
                best = -1000
                for move in self.get_available_moves():
                    self.board[move] = "O"
                    best = max(best, self.minimax(depth + 1, False))
                    self.board[move] = " "
                return best
            else:
                best = 1000
                for move in self.get_available_moves():
                    self.board[move] = "X"
                    best = min(best, self.minimax(depth + 1, True))
                    self.board[move] = " "
                return best

        def ai_move(self) -> int:
            """AI 决策（O 方）"""
            best_val = -1000
            best_move = -1
            for move in self.get_available_moves():
                self.board[move] = "O"
                val = self.minimax(0, False)
                self.board[move] = " "
                if val > best_val:
                    best_val = val
                    best_move = move
            return best_move

    # 模拟一场 AI vs AI 对局
    print(f"\n  AI vs AI 演示:")
    game = TicTacToe()
    game.display()

    player = "X"  # X 先手
    for _ in range(9):
        if player == "O":
            pos = game.ai_move()
        else:
            # AI(X) 使用简单策略：随机走
            moves = game.get_available_moves()
            if not moves:
                break
            pos = random.choice(moves)

        game.move(pos, player)
        game.display()
        print(f"    {'AI(O)' if player == 'O' else 'AI(X)'} 走 {pos}")

        winner = game.check_winner()
        if winner:
            print(f"\n  🏆 {'AI(O)' if winner == 'O' else 'AI(X)'} 赢了！")
            return
        if game.is_full():
            print(f"\n  🤝 平局！")
            return

        player = "O" if player == "X" else "X"


# ============================================================
# 应用 3：数据流滑动统计
# ============================================================

def sliding_statistics():
    """滑动窗口统计：实时数据流分析"""
    print("\n" + "=" * 60)
    print("  应用 3: 数据流滑动统计")
    print("=" * 60)

    class SlidingStats:
        """滑动窗口统计器"""

        def __init__(self, window_size: int = 5):
            self._window = []  # 当前窗口数据
            self._size = window_size
            self._history = []  # 所有历史数据

        def add(self, value: float) -> dict:
            """添加数据点，返回当前窗口统计"""
            self._window.append(value)
            self._history.append(value)

            if len(self._window) > self._size:
                self._window.pop(0)

            if not self._window:
                return {}

            n = len(self._window)
            sorted_w = sorted(self._window)
            avg = sum(self._window) / n

            variance = sum((x - avg) ** 2 for x in self._window) / n

            return {
                "value": value,
                "window_size": n,
                "mean": round(avg, 2),
                "min": min(self._window),
                "max": max(self._window),
                "median": sorted_w[n // 2] if n % 2 == 1
                         else (sorted_w[n // 2 - 1] + sorted_w[n // 2]) / 2,
                "std": round(variance ** 0.5, 2),
                "trend": "上升" if len(self._window) >= 2
                         and self._window[-1] > self._window[-2]
                         else "下降" if len(self._window) >= 2
                         and self._window[-1] < self._window[-2]
                         else "平稳",
            }

    # 模拟传感器数据流
    stats = SlidingStats(window_size=5)
    base_temp = 25.0

    print(f"\n  模拟温度传感器（窗口=5）:")
    print(f"  {'序号':<5} {'值':<8} {'均值':<8} {'中位数':<8} {'标准差':<8} {'趋势'}")
    print(f"  {'-' * 50}")

    for i in range(15):
        # 模拟带噪声的温度数据
        noise = random.uniform(-2, 2)
        if 5 <= i <= 8:
            noise += 3  # 模拟异常升温
        value = round(base_temp + noise, 1)

        result = stats.add(value)
        if result:
            print(f"  {i:<5} {result['value']:<8} {result['mean']:<8} "
                  f"{result['median']:<8} {result['std']:<8} {result['trend']}")

    print(f"\n  💡 滑动窗口统计可在 O(1)~O(k) 时间内实时分析数据流")


# ============================================================
# 主程序
# ============================================================

def main():
    visualize_sort()
    tic_tac_toe()
    sliding_statistics()

    print("\n" + "=" * 60)
    print("  ✅ 列表趣味应用演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
