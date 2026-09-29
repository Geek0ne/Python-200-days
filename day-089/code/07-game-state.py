#!/usr/bin/env python3
"""
Day 089 — 游戏循环与事件：游戏状态管理
演示如何用状态机管理游戏的不同阶段（菜单、游戏、暂停、结束）。
"""

import pygame
import sys

pygame.init()

WIDTH, HEIGHT = 600, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("游戏状态管理 — 菜单/游戏/暂停/结束")

clock = pygame.time.Clock()
FPS = 60

# ─── 颜色 ───
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
RED = (220, 50, 50)
GREEN = (50, 200, 50)
BLUE = (50, 100, 220)
YELLOW = (220, 200, 50)

# ─── 游戏状态 ───
class State:
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"

current_state = State.MENU

# 游戏数据
score = 0
player_x, player_y = WIDTH // 2, HEIGHT // 2
player_speed = 4
enemies = []

# ─── 状态处理函数 ───

def handle_menu_events(event):
    """菜单状态的事件处理"""
    global current_state
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            current_state = State.PLAYING
            reset_game()
        elif event.key == pygame.K_ESCAPE:
            return False  # 退出游戏
    return True

def handle_playing_events(event):
    """游戏状态的事件处理"""
    global current_state, score
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
            current_state = State.PAUSED
        elif event.key == pygame.K_q:
            current_state = State.GAME_OVER
    return True

def handle_paused_events(event):
    """暂停状态的事件处理"""
    global current_state
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
            current_state = State.PLAYING
        elif event.key == pygame.K_q:
            current_state = State.GAME_OVER
    return True

def handle_gameover_events(event):
    """游戏结束状态的事件处理"""
    global current_state
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            current_state = State.PLAYING
            reset_game()
        elif event.key == pygame.K_ESCAPE:
            current_state = State.MENU
    return True

# 事件处理器映射
event_handlers = {
    State.MENU: handle_menu_events,
    State.PLAYING: handle_playing_events,
    State.PAUSED: handle_paused_events,
    State.GAME_OVER: handle_gameover_events,
}

def reset_game():
    """重置游戏数据"""
    global score, player_x, player_y, enemies
    score = 0
    player_x, player_y = WIDTH // 2, HEIGHT // 2
    enemies.clear()

# ─── 更新函数 ───

def update_playing():
    """游戏状态的更新"""
    global player_x, player_y, score, current_state

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player_x -= player_speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player_x += player_speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        player_y -= player_speed
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        player_y += player_speed

    player_x = max(15, min(WIDTH - 15, player_x))
    player_y = max(15, min(HEIGHT - 15, player_y))

    # 简单敌人 AI
    import random
    if random.random() < 0.02:
        ex = random.randint(20, WIDTH - 20)
        ey = random.randint(20, HEIGHT - 20)
        enemies.append([ex, ey])

    for enemy in enemies[:]:
        dx = player_x - enemy[0]
        dy = player_y - enemy[1]
        dist = (dx**2 + dy**2) ** 0.5
        if dist > 0:
            enemy[0] += dx / dist * 1.5
            enemy[1] += dy / dist * 1.5

        # 碰撞检测
        if dist < 25:
            current_state = State.GAME_OVER
            break

    score += 1

update_handlers = {
    State.MENU: lambda: None,
    State.PLAYING: update_playing,
    State.PAUSED: lambda: None,
    State.GAME_OVER: lambda: None,
}

# ─── 渲染函数 ───

def render_menu():
    """渲染菜单"""
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 48)
    small = pygame.font.SysFont(None, 30)

    title = font.render("🎮 状态管理演示", True, YELLOW)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 3)))

    hint = small.render("按 ENTER 开始游戏", True, WHITE)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT * 2 // 3)))

    controls = small.render("WASD/方向键: 移动 | P: 暂停 | Q: 结束", True, GRAY)
    screen.blit(controls, controls.get_rect(center=(WIDTH // 2, HEIGHT - 40)))

def render_playing():
    """渲染游戏"""
    screen.fill(BLACK)

    # 网格
    for x in range(0, WIDTH, 40):
        pygame.draw.line(screen, (30, 30, 30), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (30, 30, 30), (0, y), (WIDTH, y))

    # 玩家
    pygame.draw.circle(screen, GREEN, (int(player_x), int(player_y)), 15)

    # 敌人
    for enemy in enemies:
        pygame.draw.circle(screen, RED, (int(enemy[0]), int(enemy[1])), 10)

    # 分数
    font = pygame.font.SysFont(None, 28)
    score_text = font.render(f"分数: {score}", True, WHITE)
    screen.blit(score_text, (10, 10))

    # 状态指示
    state_text = font.render("状态: 游戏中 (P=暂停, Q=结束)", True, GRAY)
    screen.blit(state_text, (10, HEIGHT - 30))

def render_paused():
    """渲染暂停画面"""
    render_playing()  # 先画游戏画面

    # 半透明遮罩
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.fill((0, 0, 0))
    overlay.set_alpha(150)
    screen.blit(overlay, (0, 0))

    font = pygame.font.SysFont(None, 60)
    text = font.render("⏸ 暂停", True, YELLOW)
    screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30)))

    small = pygame.font.SysFont(None, 30)
    hint = small.render("按 P 继续 | Q 结束", True, WHITE)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

def render_game_over():
    """渲染游戏结束画面"""
    screen.fill(BLACK)

    font = pygame.font.SysFont(None, 60)
    text = font.render("GAME OVER", True, RED)
    screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 3)))

    score_font = pygame.font.SysFont(None, 40)
    score_text = score_font.render(f"最终分数: {score}", True, WHITE)
    screen.blit(score_text, score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    small = pygame.font.SysFont(None, 30)
    hint = small.render("ENTER: 重新开始 | ESC: 返回菜单", True, GRAY)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT * 2 // 3)))

render_handlers = {
    State.MENU: render_menu,
    State.PLAYING: render_playing,
    State.PAUSED: render_paused,
    State.GAME_OVER: render_game_over,
}

# ─── 主循环 ───
running = True
while running:

    # 事件处理（分发到当前状态）
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        else:
            handler = event_handlers.get(current_state)
            if handler:
                should_continue = handler(event)
                if not should_continue:
                    running = False

    # 更新（分发到当前状态）
    updater = update_handlers.get(current_state)
    if updater:
        updater()

    # 渲染（分发到当前状态）
    renderer = render_handlers.get(current_state)
    if renderer:
        renderer()

    # 状态指示器
    font = pygame.font.SysFont(None, 20)
    state_label = font.render(f"当前状态: {current_state}", True, (80, 80, 80))
    screen.blit(state_label, (WIDTH - 150, 5))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
