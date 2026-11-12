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

**参考答案**

因为**游戏要运行多久是不确定的**——玩家可能玩 10 秒，也可能玩 2 小时，退出时机完全由用户决定。`for` 循环适合「已知次数」或「遍历一个集合」，而游戏主循环是「事件驱动、无限期持续」的，事先根本不知道要循环多少次。

`while running` 用一个**布尔开关**表达「一直跑，直到该退出」：每帧处理输入、更新、渲染，一旦收到退出事件（点关闭按钮 `QUIT`、按 `ESC`）就把 `running = False`，循环自然结束。这正好匹配「运行时长不可预知」的需求。

- 小例子：`running = True` → `while running:` 每帧 `for event in pygame.event.get(): if event.type == pygame.QUIT: running = False`。
- 硬要用 `for` 也得写成 `for _ in iter(int, 1)` 这类「无限迭代」，本质还是无限循环，反而更绕。

💡 提示：也可以写 `while True:` 配合 `break` 退出，但 `while running` 把「退出条件」显式化，更易读，也方便在多个地方（暂停、游戏结束、退出）统一置 `False`。

2. **如果不用 `Clock.tick(60)`，在一台能跑 200 FPS 的电脑和一台只能跑 30 FPS 的电脑上，同一个游戏会有什么区别？**

**参考答案**

如果逻辑是「每帧推进固定量」（比如每帧 `x += 5`），那么**游戏速度直接正比于帧率**。在 200 FPS 的电脑上物体每秒移动 `200 × 5 = 1000` 像素，在 30 FPS 的电脑上每秒只移动 `30 × 5 = 150` 像素——相差约 6.7 倍。

后果：

- 快机器上游戏飞快、难以操控，物理失稳（一帧位移过大甚至穿墙）；慢机器上慢如蜗牛。
- 体验不一致、对玩家不公平（竞技游戏尤其致命）；基于帧数的计时/动画也会错乱。
- 快机器不限帧还会 CPU/GPU 满载、发热耗电。

解决办法有两层：① 用 `clock.tick(60)` 把两台机器都**限制到 ≤60 FPS**，缩小差距；② 更根本的是让逻辑**与帧率解耦**——按真实时间 `dt` 更新（`x += speed * dt`）或用固定时间步长累积器，这样无论帧率高低，物体每秒移动的距离都一致。

- 小例子：每帧 `x += 5` → 200FPS 是 1000px/s、30FPS 是 150px/s；改成 `x += 300 * dt` → 两台机器都是 300px/s。

⚠️ 注意：`tick` 只能限速不能提速，慢机器一帧超过 16.7ms 时仍会低于 60 FPS，必须靠 dt / 固定步长兜底。

3. **KEYDOWN 事件和 `get_pressed()` 分别适合什么场景？为什么移动用 `get_pressed`，跳跃用 `KEYDOWN`？**

**参考答案**

关键在于两种输入的「触发模型」不同，正好对应两类动作：

- **移动是「持续状态」**：按住方向键期间，希望物体每帧都往前挪一点。`get_pressed()` 是电平触发——只要按住，每帧查询都为 `True`，天然表达「持续」。而 `KEYDOWN` 只在按下瞬间给一次事件，无法表达「按住一直走」。
- **跳跃是「瞬时动作」**：按一次空格只该跳一次。`KEYDOWN` 是边沿触发——按下瞬间触发一次，正好匹配。若用 `get_pressed()` 做跳跃，按住空格会**每帧都触发跳跃**，变成连跳/飞天。

所以：移动用 `get_pressed`（要持续），跳跃用 `KEYDOWN`（要一次性）。

- 小例子：移动 `if keys[pygame.K_LEFT]: x -= 5`；跳跃 `if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and on_ground: jump()`。

💡 提示：跳跃通常再配合一个 `on_ground`（是否在地面）标志，避免在空中重复起跳；落地后重置该标志。

4. **自定义事件 `USEREVENT + N` 中的 N 有什么限制？如果定义了太多自定义事件会怎样？**

**参考答案**

pygame 的事件类型是**整数编号**，系统预留了前面一段（`0 .. USEREVENT-1`），用户自定义事件必须落在 `[USEREVENT, NUMEVENTS)` 这个区间里。在 pygame 2.x 中 `USEREVENT = 24`、`NUMEVENTS = 32`，也就是说大约只有 **8 个**可用编号（`USEREVENT+0` 到 `USEREVENT+7`）。

所以 N 的限制是：`USEREVENT + N` 不能 ≥ `NUMEVENTS`（越界），也不能和系统事件或别的自定义事件**撞号**。

如果定义太多自定义事件：

- **可用编号耗尽**：多个定时器/事件被迫共用同一编号，`pygame.time.set_timer` 会**互相覆盖**（同一事件类型只保留最后一个定时器）。
- **无法区分来源**：收到一个事件却分不清是谁触发的，逻辑错乱。
- **越界无效**：超出合法范围的事件编号会被忽略或行为异常。

应对办法：复用少量事件类型，在事件里附带「子类型/数据」字段来区分；或用新版 pygame 的 `pygame.event.custom_type()` 动态分配空闲编号；提前规划好编号用途。

- 小例子：只有 8 个槽位，却定义 10 个 `USEREVENT+N`，后两个要么越界、要么与前面冲突。

⚠️ 注意：`USEREVENT`、`NUMEVENTS` 的具体值随 pygame 版本变化，应直接用 `pygame.USEREVENT`、`pygame.NUMEVENTS` 查询，不要硬编码数字。

5. **固定时间步长的"累积器"模式为什么需要内部 `while` 循环而不是 `if`？**  
   提示：考虑帧率突然下降的情况。

**参考答案**

累积器（accumulator）把「真实经过的时间」攒起来，每攒够一个 `FIXED_DT` 就推进一个物理步。当某帧**突然耗时很长**（掉帧）时，这一帧往累积器里倒进了「好几个步长」的时间。

- 用 **`while`**：能在本帧把「欠下的步数」**一次性全部补走**，让模拟时间追上真实时间，物理保持稳定、可复现。
- 用 **`if`**：每帧最多只走一步，欠下的步数永远补不完，模拟越来越滞后于真实时间——游戏变成「慢动作」，物理与时间脱节。

下面用纯标准库模拟「帧率突然下降」（无需 pygame，已验证）：

```python
# 固定时间步长累积器：对比内部用 while 与 if 的区别（纯标准库模拟，无需 pygame）
FIXED_DT = 1 / 60          # 每个物理步长固定 1/60 秒
TOTAL_TIME = 1.0           # 模拟真实世界经过 1 秒

# 模拟「帧率突然下降」：每帧耗时忽大忽小（秒），合计 1.0 秒，其中两帧严重超时
frame_times = [0.4, 0.016, 0.5, 0.084]


def run(use_while):
    accumulator = 0.0
    steps = 0
    for dt in frame_times:
        accumulator += dt
        if use_while:
            while accumulator >= FIXED_DT:   # 把欠下的步数一次补齐
                accumulator -= FIXED_DT
                steps += 1
        else:
            if accumulator >= FIXED_DT:      # 每帧最多只走一步
                accumulator -= FIXED_DT
                steps += 1
    return steps


while_steps = run(True)
if_steps = run(False)
print(f"真实经过时间: {sum(frame_times):.3f} 秒，应走 {round(TOTAL_TIME / FIXED_DT)} 步")
print(f"内部用 while: 实际走了 {while_steps} 步（追上真实时间）")
print(f"内部用 if   : 实际走了 {if_steps} 步（严重滞后，游戏变慢动作）")
```

预期输出：

```
真实经过时间: 1.000 秒，应走 60 步
内部用 while: 实际走了 60 步（追上真实时间）
内部用 if   : 实际走了 4 步（严重滞后，游戏变慢动作）
```

1 秒里只来了 4 帧（其中两帧严重超时），本应推进 60 个物理步：`while` 补满了 60 步，`if` 只走了 4 步——差距一目了然。

⚠️ 注意：极端掉帧时 `while` 可能一次补非常多步，导致「越补越卡」的死亡螺旋。实践中要给单帧步数或累积器设上限（clamp），超出就丢弃部分时间，宁可短暂慢一点也不要卡死。

---

> **下一步**：Day 090 — 碰撞检测与动画
