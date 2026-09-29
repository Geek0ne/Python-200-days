#!/usr/bin/env python3
"""
Day 089 — 游戏循环与事件：帧率对比实验
对比不同帧率下游戏的流畅度和 CPU 占用。
按键 1/2/3 切换帧率，观察 FPS 变化。
"""

import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 800, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("帧率对比实验 — 按 1/2/3 切换")

clock = pygame.time.Clock()

# 颜色
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
GREEN = (50, 200, 50)
BLUE = (50, 100, 220)
YELLOW = (220, 200, 50)

# 球的状态
ball_x = WIDTH // 2
ball_y = HEIGHT // 2
ball_speed_x = 3
ball_speed_y = 2
ball_radius = 15

# 帧率设置
fps_options = [30, 60, 120]
fps_labels = ["30 FPS（流畅）", "60 FPS（标准）", "120 FPS（高帧率）"]
current_fps_index = 1  # 默认 60 FPS
current_fps = fps_options[current_fps_index]

# 轨迹记录
trail = []
MAX_TRAIL = 30

# 运行时间
start_ticks = pygame.time.get_ticks()

running = True
while running:

    # 处理事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_1:
                current_fps_index = 0
                current_fps = fps_options[0]
            elif event.key == pygame.K_2:
                current_fps_index = 1
                current_fps = fps_options[1]
            elif event.key == pygame.K_3:
                current_fps_index = 2
                current_fps = fps_options[2]

    # 更新
    ball_x += ball_speed_x
    ball_y += ball_speed_y

    if ball_x - ball_radius <= 0 or ball_x + ball_radius >= WIDTH:
        ball_speed_x = -ball_speed_x
    if ball_y - ball_radius <= 0 or ball_y + ball_radius >= HEIGHT:
        ball_speed_y = -ball_speed_y

    trail.append((int(ball_x), int(ball_y)))
    if len(trail) > MAX_TRAIL:
        trail.pop(0)

    # 渲染
    screen.fill(BLACK)

    # 绘制轨迹
    for i, pos in enumerate(trail):
        alpha = int(255 * (i + 1) / len(trail))
        color = (alpha, alpha // 2, 0)
        r = max(2, int(ball_radius * (i + 1) / len(trail)))
        pygame.draw.circle(screen, color, pos, r)

    # 绘制球
    pygame.draw.circle(screen, RED, (int(ball_x), int(ball_y)), ball_radius)

    # 绘制信息
    font = pygame.font.SysFont(None, 28)
    elapsed = (pygame.time.get_ticks() - start_ticks) / 1000

    info_lines = [
        f"当前帧率: {current_fps} FPS",
        f"实际 FPS: {clock.get_fps():.1f}",
        f"帧间隔: {clock.get_time()} ms",
        f"运行时间: {elapsed:.1f}s",
        "",
        f"[1] 30 FPS   [2] 60 FPS   [3] 120 FPS",
        "ESC: 退出",
    ]

    for i, line in enumerate(info_lines):
        color = YELLOW if i == 0 else WHITE
        text = font.render(line, True, color)
        screen.blit(text, (10, 10 + i * 28))

    pygame.display.flip()

    # 帧率控制
    clock.tick(current_fps)

pygame.quit()
sys.exit()
