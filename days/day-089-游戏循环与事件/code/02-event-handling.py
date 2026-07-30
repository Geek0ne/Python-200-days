#!/usr/bin/env python3
"""
Day 089 — 游戏循环与事件：完整事件处理系统
演示所有常见事件类型：键盘、鼠标、自定义事件、定时器。
"""

import pygame
import sys

# ─── 初始化 ───
pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Day 089 — 事件处理系统")

clock = pygame.time.Clock()
FPS = 60

# ─── 颜色 ───
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 50, 50)
GREEN = (50, 200, 50)
BLUE = (50, 100, 220)
YELLOW = (220, 200, 50)

# ─── 游戏状态 ───
# 玩家
player_x, player_y = WIDTH // 2, HEIGHT // 2
player_speed = 5
player_color = RED

# 事件日志（显示最近的事件）
event_log = []
MAX_LOG = 8

# 按键状态追踪
moving_left = False
moving_right = False
moving_up = False
moving_down = False

# 自定义事件
FLASH_EVENT = pygame.USEREVENT + 1
SPAWN_EVENT = pygame.USEREVENT + 2
flash_active = False
flash_timer = 0

# 子弹列表（鼠标点击发射）
bullets = []

# 敌人列表（定时生成）
enemies = []

# 启动定时器
pygame.time.set_timer(FLASH_EVENT, 3000)   # 每 3 秒闪光一次
pygame.time.set_timer(SPAWN_EVENT, 1500)   # 每 1.5 秒生成敌人

# ─── 辅助函数 ───
def add_log(text):
    """添加事件日志"""
    event_log.append(text)
    if len(event_log) > MAX_LOG:
        event_log.pop(0)

def spawn_enemy():
    """在随机位置生成敌人"""
    import random
    x = random.randint(50, WIDTH - 50)
    y = random.randint(50, HEIGHT - 50)
    enemies.append({"x": x, "y": y, "radius": 15})

# ─── 游戏主循环 ───
running = True
while running:

    # ═══════════════════════════════════════
    # 阶段 1：处理事件
    # ═══════════════════════════════════════
    for event in pygame.event.get():

        # --- 系统事件 ---
        if event.type == pygame.QUIT:
            running = False

        # --- 键盘事件：按下 ---
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                moving_left = True
                add_log("← 左移开启")

            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                moving_right = True
                add_log("→ 右移开启")

            elif event.key == pygame.K_UP or event.key == pygame.K_w:
                moving_up = True
                add_log("↑ 上移开启")

            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                moving_down = True
                add_log("↓ 下移开启")

            elif event.key == pygame.K_SPACE:
                # 空格键：改变颜色
                import random
                player_color = (
                    random.randint(50, 255),
                    random.randint(50, 255),
                    random.randint(50, 255),
                )
                add_log("🎨 颜色随机改变")

            elif event.key == pygame.K_c:
                # 清空所有子弹和敌人
                bullets.clear()
                enemies.clear()
                add_log("🧹 清空所有对象")

        # --- 键盘事件：松开 ---
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                moving_left = False
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                moving_right = False
            elif event.key == pygame.K_UP or event.key == pygame.K_w:
                moving_up = False
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                moving_down = False

        # --- 鼠标事件：移动 ---
        elif event.type == pygame.MOUSEMOTION:
            # 仅在没有按键移动时跟随鼠标
            if not (moving_left or moving_right or moving_up or moving_down):
                player_x, player_y = event.pos

        # --- 鼠标事件：左键点击发射子弹 ---
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键
                mx, my = event.pos
                # 计算方向向量
                dx = mx - player_x
                dy = my - player_y
                length = max((dx ** 2 + dy ** 2) ** 0.5, 1)
                bullets.append({
                    "x": player_x,
                    "y": player_y,
                    "dx": dx / length * 8,
                    "dy": dy / length * 8,
                })
                add_log(f"🔫 发射子弹 → ({mx}, {my})")

            elif event.button == 3:  # 右键
                add_log(f"🖱️ 右键点击 ({event.pos[0]}, {event.pos[1]})")

            elif event.button == 2:  # 中键
                add_log("🖱️ 中键点击")

        # --- 自定义事件：闪光效果 ---
        elif event.type == FLASH_EVENT:
            flash_active = True
            flash_timer = 15  # 持续 15 帧
            add_log("⚡ 闪光事件触发！")

        # --- 自定义事件：生成敌人 ---
        elif event.type == SPAWN_EVENT:
            spawn_enemy()
            add_log(f"👾 生成敌人 (总数: {len(enemies)})")

    # ═══════════════════════════════════════
    # 阶段 2：更新状态
    # ═══════════════════════════════════════

    # 键盘移动（持续按住）
    if moving_left:
        player_x -= player_speed
    if moving_right:
        player_x += player_speed
    if moving_up:
        player_y -= player_speed
    if moving_down:
        player_y += player_speed

    # 边界限制
    player_x = max(20, min(WIDTH - 20, player_x))
    player_y = max(20, min(HEIGHT - 20, player_y))

    # 更新子弹位置
    for bullet in bullets[:]:
        bullet["x"] += bullet["dx"]
        bullet["y"] += bullet["dy"]
        # 移除出界子弹
        if bullet["x"] < -10 or bullet["x"] > WIDTH + 10 or \
           bullet["y"] < -10 or bullet["y"] > HEIGHT + 10:
            bullets.remove(bullet)

    # 闪光倒计时
    if flash_active:
        flash_timer -= 1
        if flash_timer <= 0:
            flash_active = False

    # ═══════════════════════════════════════
    # 阶段 3：渲染
    # ═══════════════════════════════════════
    # 闪光效果：交替背景色
    if flash_active and flash_timer % 4 < 2:
        screen.fill((30, 30, 50))
    else:
        screen.fill(BLACK)

    # 绘制玩家
    pygame.draw.circle(screen, player_color, (int(player_x), int(player_y)), 20)

    # 绘制子弹
    for bullet in bullets:
        pygame.draw.circle(screen, YELLOW, (int(bullet["x"]), int(bullet["y"])), 4)

    # 绘制敌人
    for enemy in enemies:
        pygame.draw.circle(screen, GREEN, (int(enemy["x"]), int(enemy["y"])), enemy["radius"])

    # 绘制事件日志（右上角）
    font = pygame.font.SysFont(None, 24)
    log_title = font.render("=== 事件日志 ===", True, BLUE)
    screen.blit(log_title, (WIDTH - 220, 10))
    for i, log_text in enumerate(event_log):
        text = font.render(log_text, True, WHITE)
        screen.blit(text, (WIDTH - 220, 35 + i * 22))

    # 绘制操作提示（底部）
    help_font = pygame.font.SysFont(None, 22)
    help_lines = [
        "WASD/方向键: 移动 | 鼠标: 跟随 | 左键: 发射 | 空格: 变色 | C: 清空 | ESC: 退出"
    ]
    for i, line in enumerate(help_lines):
        text = help_font.render(line, True, (150, 150, 150))
        screen.blit(text, (10, HEIGHT - 30 + i * 20))

    # FPS 显示
    fps_text = font.render(f"FPS: {clock.get_fps():.0f} | 子弹: {len(bullets)} | 敌人: {len(enemies)}", True, WHITE)
    screen.blit(fps_text, (10, 10))

    pygame.display.flip()

    # ═══════════════════════════════════════
    # 阶段 4：帧率控制
    # ═══════════════════════════════════════
    clock.tick(FPS)

pygame.quit()
sys.exit()
