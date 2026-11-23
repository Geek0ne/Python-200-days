#!/usr/bin/env python3
"""
Day 089 — 游戏循环与事件：实战 — 贪吃蛇游戏
完整的游戏循环 + 事件处理 + 游戏逻辑，可直接运行。

操作：
  方向键/WASD  移动
  空格         重新开始
  ESC          退出
"""

import pygame
import sys
import random

# ─── 初始化 ───
pygame.init()

# 窗口
CELL_SIZE = 20
COLS, ROWS = 30, 25
WIDTH = COLS * CELL_SIZE
HEIGHT = ROWS * CELL_SIZE
INFO_HEIGHT = 40  # 顶部信息栏高度

screen = pygame.display.set_mode((WIDTH, HEIGHT + INFO_HEIGHT))
pygame.display.set_caption("🐍 贪吃蛇 — 游戏循环与事件实战")

clock = pygame.time.Clock()
FPS = 10  # 贪吃蛇不需要太高帧率

# ─── 颜色 ───
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GREEN = (0, 150, 0)
GREEN = (0, 200, 0)
LIGHT_GREEN = (50, 220, 50)
RED = (220, 50, 50)
GRAY = (40, 40, 40)
DARK_GRAY = (30, 30, 30)
YELLOW = (220, 200, 50)

# ─── 方向常量 ───
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# ─── 游戏状态类 ───
class GameState:
    """管理所有游戏状态"""

    def __init__(self):
        self.reset()

    def reset(self):
        """重置游戏"""
        # 蛇：初始在中间，3 节身体
        mid_x, mid_y = COLS // 2, ROWS // 2
        self.snake = [(mid_x, mid_y), (mid_x - 1, mid_y), (mid_x - 2, mid_y)]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.score = 0
        self.game_over = False
        self.paused = False
        self.food = None
        self.spawn_food()

    def spawn_food(self):
        """在随机空位生成食物"""
        while True:
            x = random.randint(0, COLS - 1)
            y = random.randint(0, ROWS - 1)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break

    def change_direction(self, new_dir):
        """改变方向（防止 180 度掉头）"""
        # 不能直接反向
        if (new_dir[0] + self.direction[0] == 0 and
            new_dir[1] + self.direction[1] == 0):
            return
        self.next_direction = new_dir

    def update(self):
        """更新游戏逻辑（每帧调用一次）"""
        if self.game_over or self.paused:
            return

        self.direction = self.next_direction

        # 计算新头部位置
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # 撞墙检测
        if new_head[0] < 0 or new_head[0] >= COLS or \
           new_head[1] < 0 or new_head[1] >= ROWS:
            self.game_over = True
            return

        # 撞自己检测
        if new_head in self.snake:
            self.game_over = True
            return

        # 移动蛇
        self.snake.insert(0, new_head)

        # 吃食物
        if new_head == self.food:
            self.score += 10
            self.spawn_food()
        else:
            self.snake.pop()  # 没吃到就去掉尾巴


# ─── 渲染函数 ───
def draw_game(state):
    """绘制整个游戏画面"""

    # 信息栏背景
    pygame.draw.rect(screen, DARK_GRAY, (0, 0, WIDTH, INFO_HEIGHT))

    # 绘制网格背景
    for y in range(ROWS):
        for x in range(COLS):
            rect = (x * CELL_SIZE, y * CELL_SIZE + INFO_HEIGHT, CELL_SIZE, CELL_SIZE)
            color = BLACK if (x + y) % 2 == 0 else DARK_GRAY
            pygame.draw.rect(screen, color, rect)

    # 绘制食物
    if state.food:
        fx, fy = state.food
        food_rect = (fx * CELL_SIZE + 2, fy * CELL_SIZE + 2 + INFO_HEIGHT,
                     CELL_SIZE - 4, CELL_SIZE - 4)
        pygame.draw.rect(screen, RED, food_rect, border_radius=4)

    # 绘制蛇
    for i, (sx, sy) in enumerate(state.snake):
        rect = (sx * CELL_SIZE + 1, sy * CELL_SIZE + 1 + INFO_HEIGHT,
                CELL_SIZE - 2, CELL_SIZE - 2)
        if i == 0:
            # 蛇头
            pygame.draw.rect(screen, LIGHT_GREEN, rect, border_radius=3)
        else:
            # 蛇身（渐变色）
            g = max(100, 200 - i * 3)
            pygame.draw.rect(screen, (0, g, 0), rect, border_radius=2)

    # 绘制信息栏
    font = pygame.font.SysFont(None, 28)
    score_text = font.render(f"分数: {state.score}", True, YELLOW)
    screen.blit(score_text, (10, 8))

    length_text = font.render(f"长度: {len(state.snake)}", True, WHITE)
    screen.blit(length_text, (150, 8))

    if state.game_over:
        go_text = font.render("GAME OVER — 按空格重新开始", True, RED)
        text_rect = go_text.get_rect(center=(WIDTH // 2, INFO_HEIGHT // 2))
        screen.blit(go_text, text_rect)
    elif state.paused:
        pause_text = font.render("已暂停 — 按 P 继续", True, YELLOW)
        text_rect = pause_text.get_rect(center=(WIDTH // 2, INFO_HEIGHT // 2))
        screen.blit(pause_text, text_rect)

    # 操作提示（底部）
    small_font = pygame.font.SysFont(None, 20)
    hint = small_font.render("方向键/WASD:移动  空格:重来  P:暂停  ESC:退出", True, (100, 100, 100))
    screen.blit(hint, (10, HEIGHT + INFO_HEIGHT - 25))


# ─── 主程序 ───
def main():
    state = GameState()
    running = True

    while running:

        # ═══════════════════════════════════════
        # 1. 处理事件
        # ═══════════════════════════════════════
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:

                # 方向控制
                if event.key in (pygame.K_UP, pygame.K_w):
                    state.change_direction(UP)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    state.change_direction(DOWN)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    state.change_direction(LEFT)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    state.change_direction(RIGHT)

                # 空格：重新开始
                elif event.key == pygame.K_SPACE:
                    if state.game_over:
                        state.reset()

                # P：暂停/继续
                elif event.key == pygame.K_p:
                    state.paused = not state.paused

                # ESC：退出
                elif event.key == pygame.K_ESCAPE:
                    running = False

        # ═══════════════════════════════════════
        # 2. 更新游戏状态
        # ═══════════════════════════════════════
        state.update()

        # ═══════════════════════════════════════
        # 3. 渲染
        # ═══════════════════════════════════════
        screen.fill(BLACK)
        draw_game(state)
        pygame.display.flip()

        # ═══════════════════════════════════════
        # 4. 帧率控制
        # ═══════════════════════════════════════
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
