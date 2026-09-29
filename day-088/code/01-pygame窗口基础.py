"""
Day 088 - Pygame 基础用法：创建窗口与事件处理
=============================================

学习目标：
- 初始化 Pygame 并创建游戏窗口
- 理解游戏循环的基本结构
- 处理键盘和鼠标事件
- 实现基本的图形绘制

运行方式：
    python3 01-pygame窗口基础.py
"""

import pygame
import sys

# ==================== 第一步：初始化 Pygame ====================
# pygame.init() 会初始化所有 Pygame 模块（display, font, mixer 等）
# 如果不调用 init，很多功能会报错
pygame.init()

# ==================== 第二步：创建游戏窗口 ====================
# set_mode((宽, 高)) 返回一个 Surface 对象，代表整个窗口
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))

# 设置窗口标题
pygame.display.set_caption("Day 088 - Pygame 入门")

# ==================== 第三步：定义颜色常量 ====================
# Pygame 使用 (R, G, B) 元组表示颜色，每个值 0-255
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 50, 255)

# ==================== 第四步：创建帧率控制器 ====================
# Clock 对象用于控制游戏帧率
# tick(60) 表示每秒最多渲染 60 帧
clock = pygame.time.Clock()

# ==================== 第五步：游戏主循环 ====================
# 这是游戏的核心——一个不断重复的 while 循环
# 每次循环叫做"一帧"（frame）

running = True

while running:
    # ---- 5.1 事件处理 ----
    # pygame.event.get() 返回所有待处理的事件列表
    for event in pygame.event.get():
        # 窗口关闭事件（点击 X 按钮）
        if event.type == pygame.QUIT:
            running = False
        
        # 键盘按下事件
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                print("空格键被按下！")
            elif event.key == pygame.K_a:
                print("A 键被按下！")
        
        # 鼠标点击事件
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            print(f"鼠标点击位置: ({mouse_x}, {mouse_y})")
    
    # ---- 5.2 清屏 ----
    # 每帧开始前用黑色填充整个屏幕
    # 如果不清屏，上一帧的画面会残留
    screen.fill(BLACK)
    
    # ---- 5.3 绘制内容 ----
    # 绘制一个白色矩形 (surface, color, (x, y, width, height))
    pygame.draw.rect(screen, WHITE, (50, 50, 200, 100))
    
    # 绘制一个红色矩形
    pygame.draw.rect(screen, RED, (300, 50, 200, 100))
    
    # 绘制一个绿色圆形 (surface, color, (center_x, center_y), radius)
    pygame.draw.circle(screen, GREEN, (650, 100), 50)
    
    # 绘制一条蓝色线段 (surface, color, start, end, width)
    pygame.draw.line(screen, BLUE, (50, 200), (750, 200), 3)
    
    # ---- 5.4 更新显示 ----
    # flip() 将后台缓冲区的内容显示到屏幕上
    # 这是双缓冲机制——先画到后台，再一次性显示
    pygame.display.flip()
    
    # ---- 5.5 控制帧率 ----
    # tick(60) 会自动等待，确保每帧不超过 1/60 秒
    clock.tick(60)

# ==================== 第六步：清理退出 ====================
# pygame.quit() 释放所有 Pygame 资源
pygame.quit()
sys.exit()
