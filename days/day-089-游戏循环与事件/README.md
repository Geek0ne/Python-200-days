# Day 089 — 游戏循环与事件

> **阶段**：Phase 6 — 实战项目  
> **主题**：游戏循环与事件系统  
> **前置**：Day 088 — Pygame 框架入门

---

## 📚 本日目标

掌握游戏开发的核心——**游戏循环**和**事件处理系统**。理解游戏如何响应用户输入、处理时间节奏、管理帧率，以及如何构建一个完整的游戏主循环。

---

## 1. 游戏循环（Game Loop）

### 1.1 什么是游戏循环？

游戏循环是游戏运行的"心脏"。几乎所有游戏都遵循同一个模式：

```
初始化 → [处理输入 → 更新状态 → 渲染画面] × N → 退出
```

**为什么需要游戏循环？**

- 游戏不像普通程序那样"执行完就结束"
- 游戏需要**持续运行**，不断响应输入、更新画面
- 游戏循环决定了游戏的**流畅度**和**响应速度**

### 1.2 最基本的游戏循环

```python
import pygame

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
running = True

while running:
    # 1. 处理事件（输入）
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # 2. 更新游戏状态
    # （移动物体、检查碰撞等）
    
    # 3. 渲染画面
    screen.fill((0, 0, 0))
    pygame.display.flip()
    
    # 4. 控制帧率
    clock.tick(60)

pygame.quit()
```

### 1.3 为什么需要 Clock？

`Clock.tick(fps)` 做了两件关键的事：

1. **控制帧率**：确保游戏以固定速度运行（如 60 FPS）
2. **提供时间间隔**：`clock.get_time()` 返回上一帧花费的时间（毫秒）

**为什么帧率控制很重要？**

```python
# ❌ 不控制帧率：不同电脑速度不同，游戏快慢不一
while running:
    # ...游戏逻辑...
    # 在快电脑上可能跑 200 FPS，在慢电脑上只有 30 FPS

# ✅ 控制帧率：游戏体验一致
while running:
    # ...游戏逻辑...
    clock.tick(60)  # 所有电脑都限制在 60 FPS
```

### 1.4 固定时间步长 vs 可变时间步长

| 方式 | 原理 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|----------|
| 固定时间步长 | 每帧更新固定时间量 | 物理模拟稳定、可复现 | 慢电脑可能卡顿 | 物理引擎、竞技游戏 |
| 可变时间步长 | 根据实际耗时更新 | 帧率无关、流畅 | 物理可能不稳定 | 大多数休闲游戏 |

**固定时间步长示例：**

```python
FIXED_DT = 1 / 60  # 固定 60 FPS 的时间步长
accumulator = 0.0

while running:
    dt = clock.get_time() / 1000.0  # 转为秒
    accumulator += dt
    
    while accumulator >= FIXED_DT:
        update(FIXED_DT)  # 用固定时间步长更新
        accumulator -= FIXED_DT
    
    render()
    clock.tick(60)
```

---

## 2. 事件系统（Event System）

### 2.1 Pygame 事件队列

Pygame 使用**事件队列**来管理所有输入和系统事件：

```
用户按下键盘 → 事件入队 → game loop 读取 → 做出响应
鼠标移动     → 事件入队 → game loop 读取 → 做出响应
窗口关闭     → 事件入队 → game loop 读取 → 退出游戏
```

**为什么用队列而不是直接回调？**

- 游戏循环需要**按顺序**处理每一帧的事件
- 事件队列保证**不丢失**任何输入
- 可以在游戏的**固定时间点**统一处理，而不是随时被中断

### 2.2 事件类型一览

| 事件类型 | 常用属性 | 说明 |
|----------|----------|------|
| `QUIT` | — | 窗口关闭按钮 |
| `KEYDOWN` | `key`, `mod` | 按键按下 |
| `KEYUP` | `key`, `mod` | 按键松开 |
| `MOUSEMOTION` | `pos`, `rel`, `buttons` | 鼠标移动 |
| `MOUSEBUTTONDOWN` | `pos`, `button` | 鼠标按下 |
| `MOUSEBUTTONUP` | `pos`, `button` | 鼠标松开 |
| `USEREVENT` | 自定义 | 用户自定义事件 |

### 2.3 事件处理模式

#### 模式一：逐事件处理（推荐用于精确响应）

```python
for event in pygame.event.get():
    if event.type == pygame.QUIT:
        running = False
    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_SPACE:
            player.jump()       # 精确响应：按下瞬间触发
        elif event.key == pygame.K_LEFT:
            player.move_left()  # 按下瞬间触发一次
```

#### 模式二：按键状态轮询（推荐用于持续移动）

```python
keys = pygame.key.get_pressed()
if keys[pygame.K_LEFT]:
    player.x -= 5    # 只要按住就持续移动
if keys[pygame.K_RIGHT]:
    player.x += 5
```

**两种模式的区别：**

```
按键时间线：
  按下 ──────── 持续 ──────── 松开
  │                           │
  ▼ KEYDOWN 事件               ▼ KEYUP 事件

KEYDOWN: 按下瞬间触发一次（跳转）
get_pressed: 持续按住期间每帧都为 True（移动）
```

### 2.4 自定义事件

当内置事件不够用时，可以创建自定义事件：

```python
# 定义自定义事件
SPAWN_ENEMY = pygame.USEREVENT + 1
WEAPON_READY = pygame.USEREVENT + 2

# 定时触发
pygame.time.set_timer(SPAWN_ENEMY, 2000)  # 每 2 秒生成敌人

# 在事件循环中处理
for event in pygame.event.get():
    if event.type == SPAWN_ENEMY:
        spawn_enemy()
```

---

## 3. 时间管理

### 3.1 Pygame 时间工具

| 工具 | 用途 | 精度 |
|------|------|------|
| `Clock.tick(fps)` | 控制帧率 | 毫秒级 |
| `Clock.get_time()` | 上一帧耗时 | 毫秒 |
| `Clock.get_fps()` | 当前实际 FPS | — |
| `pygame.time.get_ticks()` | 游戏启动至今毫秒数 | 毫秒 |
| `pygame.time.set_timer()` | 定时触发事件 | 毫秒 |

### 3.2 定时器的使用

```python
# 创建定时器：每 1000 毫秒（1秒）触发一次
TIMER_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(TIMER_EVENT, 1000)

# 在事件循环中
for event in pygame.event.get():
    if event.type == TIMER_EVENT:
        update_score()  # 每秒更新一次分数
```

**⚠️ 避坑：set_timer 会覆盖**

```python
# ❌ 同一个事件类型只能有一个定时器
pygame.time.set_timer(MY_EVENT, 1000)
pygame.time.set_timer(MY_EVENT, 2000)  # 覆盖了上面的 1000ms

# ✅ 用不同的事件类型
pygame.time.set_timer(EVENT_A, 1000)
pygame.time.set_timer(EVENT_B, 2000)
```

---

## 4. 游戏循环优化

### 4.1 分离逻辑与渲染

```python
# ❌ 所有逻辑和渲染混在一起
while running:
    handle_events()
    move_player()        # 逻辑
    check_collisions()   # 逻辑
    draw_background()    # 渲染
    draw_player()        # 渲染
    pygame.display.flip() # 渲染

# ✅ 清晰分离
while running:
    handle_events()      # 输入阶段
    update(dt)           # 逻辑阶段（用时间步长）
    render(screen)       # 渲染阶段
    clock.tick(60)
```

### 4.2 避免在事件循环中做重活

```python
# ❌ 在事件处理中做复杂计算
for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
        recalculate_pathfinding()  # 耗时操作会卡顿！

# ✅ 事件只做标记，实际处理放在 update 阶段
for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
        player.wants_to_move = True  # 只做标记

update(dt)  # 在这里处理移动逻辑
```

### 4.3 脏矩形渲染（Dirty Rectangle）

只重绘变化的部分，而非整个屏幕：

```python
# 每帧只重绘变化的区域
changed_rects = []

# 更新时记录变化区域
old_rect = player.rect.copy()
player.update()
changed_rects.append(old_rect)
changed_rects.append(player.rect)

# 只更新变化的部分
pygame.display.update(changed_rects)
```

---

## 5. 完整游戏循环架构

```
┌─────────────────────────────────────────┐
│              游戏初始化                   │
│  pygame.init() → 创建窗口 → 加载资源     │
└──────────────────┬──────────────────────┘
                   ▼
         ┌─────────────────┐
         │    主循环开始     │◄────────────┐
         └────────┬────────┘             │
                  ▼                      │
         ┌─────────────────┐             │
         │  1. 处理事件     │             │
         │  (用户输入/系统)  │             │
         └────────┬────────┘             │
                  ▼                      │
         ┌─────────────────┐             │
         │  2. 更新状态     │             │
         │  (移动/碰撞/AI)  │             │
         └────────┬────────┘             │
                  ▼                      │
         ┌─────────────────┐             │
         │  3. 渲染画面     │             │
         │  (绘制/翻转显示)  │             │
         └────────┬────────┘             │
                  ▼                      │
         ┌─────────────────┐             │
         │  4. 帧率控制     │             │
         │  clock.tick(60) │             │
         └────────┬────────┘             │
                  │                      │
                  ├── running=True ──────┘
                  │
                  ▼
         ┌─────────────────┐
         │    游戏退出      │
         │  pygame.quit()   │
         └─────────────────┘
```

---

## 6. 实战代码

见 `code/` 目录：

| 文件 | 内容 | 难度 |
|------|------|------|
| `01-game-loop-basics.py` | 基础游戏循环演示 | ⭐ |
| `02-event-handling.py` | 完整事件处理系统 | ⭐⭐ |
| `03-real-game-example.py` | 实战：贪吃蛇游戏 | ⭐⭐⭐ |

---

## 7. 思考题

1. **为什么游戏循环要用 `while running` 而不是 `for` 循环？**  
   提示：思考游戏运行的不确定性——玩家什么时候退出？

2. **如果不用 `Clock.tick(60)`，在一台能跑 200 FPS 的电脑和一台只能跑 30 FPS 的电脑上，同一个游戏会有什么区别？**

3. **KEYDOWN 事件和 `get_pressed()` 分别适合什么场景？为什么移动用 `get_pressed`，跳跃用 `KEYDOWN`？**

4. **自定义事件 `USEREVENT + N` 中的 N 有什么限制？如果定义了太多自定义事件会怎样？**

5. **固定时间步长的"累积器"模式为什么需要内部 `while` 循环而不是 `if`？**  
   提示：考虑帧率突然下降的情况。

---

> **下一步**：Day 090 — 碰撞检测与动画
