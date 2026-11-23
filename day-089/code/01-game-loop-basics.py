#!/usr/bin/env python3
"""
Day 089 — 游戏循环与事件：基础游戏循环演示
演示最简单的游戏循环结构，窗口中一个小方块跟随鼠标移动。
"""

import pygame
import sys

# ─── 初始化 ───
pygame.init()

# 窗口设置
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Day 089 — 基础游戏循环")

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 50, 50)

# 时钟对象：控制帧率
clock = pygame.time.Clock()
FPS = 60

# 游戏状态
player_x, player_y = WIDTH // 2, HEIGHT // 2
player_size = 40
running = True

# ─── 游戏主循环 ───
while running:

    # ═══════════════════════════════════════
    # 阶段 1：处理事件（输入）
    # ═══════════════════════════════════════
    for event in pygame.event.get():
        # 窗口关闭事件
        if event.type == pygame.QUIT:
            running = False

        # 键盘按下事件
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_r:
                # 按 R 键重置位置
                player_x, player_y = WIDTH // 2, HEIGHT // 2

    # ═══════════════════════════════════════
    # 阶段 2：更新游戏状态
    # ═══════════════════════════════════════
    # 获取鼠标位置，让方块跟随鼠标
    mouse_x, mouse_y = pygame.mouse.get_pos()
    # 平滑移动（线性插值）
    player_x += (mouse_x - player_x) * 0.1
    player_y += (mouse_y - player_y) * 0.1

    # ═══════════════════════════════════════
    # 阶段 3：渲染画面
    # ═══════════════════════════════════════
    screen.fill(BLACK)

    # 绘制玩家方块
    rect = pygame.Rect(
        int(player_x - player_size // 2),
        int(player_y - player_size // 2),
        player_size,
        player_size
    )
    pygame.draw.rect(screen, RED, rect)

    # 绘制 FPS 信息
    font = pygame.font.SysFont(None, 30)
    fps_text = font.render(f"FPS: {clock.get_fps():.0f}", True, WHITE)
    screen.blit(fps_text, (10, 10))

    # 绘制操作提示
    hint = font.render("R: 重置位置 | ESC: 退出", True, WHITE)
    screen.blit(hint, (10, 40))

    # 翻转显示缓冲区
    pygame.display.flip()

    # ═══════════════════════════════════════
    # 阶段 4：帧率控制
    # ═══════════════════════════════════════
    clock.tick(FPS)

# ─── 退出 ───
pygame.quit()
sys.exit()
