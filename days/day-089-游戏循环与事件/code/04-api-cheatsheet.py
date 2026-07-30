#!/usr/bin/env python3
"""
Day 089 — 游戏循环与事件：API 速查
列出游戏循环和事件处理中常用的 API，每个都附带简短示例。
不运行游戏，直接运行即可看到输出。
"""

import pygame
import sys

pygame.init()

# ─── 1. Clock API ───
print("=" * 50)
print("1. Clock API")
print("=" * 50)

clock = pygame.time.Clock()

# tick(fps) — 控制帧率
clock.tick(60)
print(f"  clock.tick(60) → 限制 60 FPS")

# get_time() — 上一帧耗时（毫秒）
dt = clock.get_time()
print(f"  clock.get_time() → {dt} ms")

# get_rawtime() — 上一帧 CPU 耗时（不含 tick 等待）
raw = clock.get_rawtime()
print(f"  clock.get_rawtime() → {raw} ms")

# get_fps() — 当前 FPS
fps = clock.get_fps()
print(f"  clock.get_fps() → {fps:.1f}")

# ─── 2. Event API ───
print("\n" + "=" * 50)
print("2. Event API")
print("=" * 50)

# pygame.event.get() — 获取所有待处理事件
events = pygame.event.get()
print(f"  pygame.event.get() → {len(events)} 个事件")

# pygame.event.peek(type) — 检查是否有某类事件（不移除）
has_quit = pygame.event.peek(pygame.QUIT)
print(f"  pygame.event.peek(QUIT) → {has_quit}")

# pygame.event.clear() — 清空事件队列
pygame.event.clear()
print("  pygame.event.clear() → 清空事件队列")

# pygame.event.post(event) — 手动投递事件
custom_event = pygame.event.Event(pygame.USEREVENT, message="hello")
pygame.event.post(custom_event)
print("  pygame.event.post(USEREVENT) → 手动投递事件")

# ─── 3. Time API ───
print("\n" + "=" * 50)
print("3. Time API")
print("=" * 50)

# pygame.time.get_ticks() — 游戏启动至今毫秒数
ticks = pygame.time.get_ticks()
print(f"  pygame.time.get_ticks() → {ticks} ms")

# pygame.time.set_timer(event, millis) — 定时触发
MY_TIMER = pygame.USEREVENT + 10
pygame.time.set_timer(MY_TIMER, 2000)  # 每 2 秒
print(f"  pygame.time.set_timer(USEREVENT+10, 2000) → 每 2 秒触发")

# 停止定时器：设为 0
pygame.time.set_timer(MY_TIMER, 0)
print("  pygame.time.set_timer(MY_TIMER, 0) → 停止定时器")

# ─── 4. Key API ───
print("\n" + "=" * 50)
print("4. Key API")
print("=" * 50)

# pygame.key.get_pressed() — 返回所有按键状态数组
keys = pygame.key.get_pressed()
print(f"  pygame.key.get_pressed() → 返回 {len(keys)} 个按键状态")
print(f"  keys[K_SPACE] = {keys[pygame.K_SPACE]}")
print(f"  keys[K_LEFT] = {keys[pygame.K_LEFT]}")

# pygame.key.name(key) — 获取按键名称
name = pygame.key.name(pygame.K_SPACE)
print(f"  pygame.key.name(K_SPACE) → '{name}'")

# pygame.key.get_mods() — 获取当前修饰键状态
mods = pygame.key.get_mods()
print(f"  pygame.key.get_mods() → {mods}")

# ─── 5. Mouse API ───
print("\n" + "=" * 50)
print("5. Mouse API")
print("=" * 50)

# pygame.mouse.get_pos() — 鼠标位置
pos = pygame.mouse.get_pos()
print(f"  pygame.mouse.get_pos() → {pos}")

# pygame.mouse.get_rel() — 鼠标相对移动
rel = pygame.mouse.get_rel()
print(f"  pygame.mouse.get_rel() → {rel}")

# pygame.mouse.get_pressed() — 鼠标按钮状态
mouse_buttons = pygame.mouse.get_pressed()
print(f"  pygame.mouse.get_pressed() → 左={mouse_buttons[0]}, 中={mouse_buttons[1]}, 右={mouse_buttons[2]}")

# pygame.mouse.set_pos(x, y) — 设置鼠标位置
# pygame.mouse.set_visible(False) — 隐藏鼠标
print("  pygame.mouse.set_visible(False) → 隐藏鼠标光标")

# ─── 6. 常用常量 ───
print("\n" + "=" * 50)
print("6. 常用事件类型常量")
print("=" * 50)
event_types = [
    ("QUIT", pygame.QUIT),
    ("KEYDOWN", pygame.KEYDOWN),
    ("KEYUP", pygame.KEYUP),
    ("MOUSEMOTION", pygame.MOUSEMOTION),
    ("MOUSEBUTTONDOWN", pygame.MOUSEBUTTONDOWN),
    ("MOUSEBUTTONUP", pygame.MOUSEBUTTONUP),
    ("USEREVENT", pygame.USEREVENT),
]
for name, val in event_types:
    print(f"  pygame.{name:20s} = {val}")

print("\n✅ API 速查完成！")
pygame.quit()
sys.exit()
