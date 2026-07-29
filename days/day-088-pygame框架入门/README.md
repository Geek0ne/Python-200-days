# Day 088 — Pygame 框架入门

> **学习目标**：掌握 Pygame 游戏开发框架的核心概念，理解游戏循环、事件处理和基本绘图，能够创建一个可运行的窗口程序。

---

## 1. 什么是 Pygame？

Pygame 是一个基于 SDL（Simple DirectMedia Layer）的 Python 游戏开发库。它提供了图形渲染、声音播放、事件处理、碰撞检测等功能，是 Python 生态中最流行的 2D 游戏框架。

### 为什么选择 Pygame？

| 特性 | 说明 |
|------|------|
| **简单易学** | API 设计直观，适合初学者快速上手 |
| **跨平台** | 支持 Windows、macOS、Linux |
| **纯 Python** | 无需 C/C++ 知识，纯 Python 编写游戏逻辑 |
| **社区丰富** | 大量教程、示例代码和开源项目 |
| **功能完整** | 2D 渲染、声音、字体、碰撞检测一应俱全 |

### Pygame 的核心模块

```
pygame 核心模块
├── pygame.display    — 窗口管理与显示
├── pygame.event      — 事件处理（键盘、鼠标、窗口事件）
├── pygame.draw       — 基本图形绘制（圆、矩形、线）
├── pygame.sprite     — 精灵系统（游戏对象管理）
├── pygame.image      — 图片加载与显示
├── pygame.mixer      — 声音与音乐播放
├── pygame.font       — 字体与文字渲染
├── pygame.time       — 时间管理与帧率控制
├── pygame.rect       — 矩形区域（碰撞检测基础）
└── pygame.transform  — 图像变换（缩放、旋转、翻转）
```

---

## 2. 安装与环境准备

### 安装 Pygame

```bash
# 推荐使用 pip 安装
pip install pygame

# 如果需要特定版本
pip install pygame==2.5.2
```

### 验证安装

```python
import pygame
print(f"Pygame 版本: {pygame.__version__}")
```

### 系统要求

- Python 3.7+
- 图形显示环境（X11/Wayland on Linux，原生窗口 on Windows/macOS）
- 部分系统需要额外依赖（如 Ubuntu: `sudo apt install python3-dev libsdl2-dev`）

---

## 3. 游戏开发的核心概念

### 3.1 游戏循环（Game Loop）

游戏循环是所有游戏的心脏。它不断重复执行以下步骤：

```
┌─────────────────────────────────────────────┐
│              游戏主循环                       │
│                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ 事件处理  │ → │  游戏更新  │ → │  画面渲染  │ │
│  └──────────┘   └──────────┘   └──────────┘ │
│       ↑                              │       │
│       └──────────────────────────────┘       │
│                  (每帧重复)                    │
└─────────────────────────────────────────────┘
```

**每帧执行三件事：**
1. **事件处理**：检查用户输入（键盘、鼠标、关闭窗口）
2. **游戏更新**：更新游戏状态（位置、分数、碰撞检测）
3. **画面渲染**：把当前状态画到屏幕上

### 3.2 帧率（FPS）

帧率 = 每秒渲染的画面数。常见标准：
- 30 FPS：基本流畅
- 60 FPS：标准流畅（大多数游戏的目标）
- 144+ FPS：电竞级

Pygame 使用 `pygame.time.Clock` 控制帧率：

```python
clock = pygame.time.Clock()
while running:
    # ... 游戏逻辑 ...
    clock.tick(60)  # 限制为 60 FPS
```

### 3.3 坐标系

Pygame 使用左上角为原点的坐标系：

```
(0, 0) ─────────────────→ X 轴（右）
  │
  │
  │
  │
  ↓
Y 轴（下）
```

- X 增大 = 向右
- Y 增大 = 向下（注意：与数学坐标系相反！）

### 3.4 颜色系统

Pygame 使用 RGB 颜色元组 `(R, G, B)`，每个分量 0-255：

```python
WHITE  = (255, 255, 255)  # 白色
BLACK  = (0,   0,   0  )  # 黑色
RED    = (255, 0,   0  )  # 红色
GREEN  = (0,   255, 0  )  # 绿色
BLUE   = (0,   0,   255)  # 蓝色
YELLOW = (255, 255, 0  )  # 黄色
```

---

## 4. Pygame 基础用法

### 4.1 初始化与窗口创建

```python
import pygame
import sys

# 初始化 Pygame
pygame.init()

# 创建窗口（宽度, 高度）
screen = pygame.display.set_mode((800, 600))

# 设置窗口标题
pygame.display.set_caption("我的第一个 Pygame 游戏")

# 游戏主循环
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # 用黑色清屏
    screen.fill((0, 0, 0))
    
    # 更新显示
    pygame.display.flip()

# 退出
pygame.quit()
sys.exit()
```

**关键步骤解释：**
1. `pygame.init()` — 初始化所有 Pygame 模块
2. `pygame.display.set_mode()` — 创建游戏窗口
3. `pygame.event.get()` — 获取所有待处理的事件
4. `screen.fill()` — 用颜色填充整个屏幕（清屏）
5. `pygame.display.flip()` — 将绘制的内容显示到屏幕上

### 4.2 事件处理

事件是用户与游戏的交互：按键、鼠标移动、关闭窗口等。

```python
for event in pygame.event.get():
    if event.type == pygame.QUIT:
        running = False
    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            running = False
        elif event.key == pygame.K_SPACE:
            print("空格键被按下！")
    elif event.type == pygame.MOUSEBUTTONDOWN:
        print(f"鼠标点击位置: {event.pos}")
```

**常用事件类型：**

| 事件类型 | 说明 |
|----------|------|
| `pygame.QUIT` | 点击窗口关闭按钮 |
| `pygame.KEYDOWN` | 键盘按下 |
| `pygame.KEYUP` | 键盘松开 |
| `pygame.MOUSEBUTTONDOWN` | 鼠标按下 |
| `pygame.MOUSEBUTTONUP` | 鼠标松开 |
| `pygame.MOUSEMOTION` | 鼠标移动 |

### 4.3 持续按键检测

`event` 只在按下瞬间触发一次。要检测持续按住某个键，使用 `pygame.key.get_pressed()`：

```python
keys = pygame.key.get_pressed()
if keys[pygame.K_LEFT]:
    player_x -= 5
if keys[pygame.K_RIGHT]:
    player_x += 5
if keys[pygame.K_UP]:
    player_y -= 5
if keys[pygame.K_DOWN]:
    player_y += 5
```

### 4.4 绘制基本图形

```python
import pygame

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
RED   = (255, 0,   0)
GREEN = (0,   255, 0)
BLUE  = (0,   0,   255)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 0, 0))  # 黑色背景

    # 绘制矩形 (surface, color, (x, y, width, height))
    pygame.draw.rect(screen, RED, (100, 100, 200, 150))

    # 绘制圆形 (surface, color, (center_x, center_y), radius)
    pygame.draw.circle(screen, GREEN, (500, 200), 80)

    # 绘制线段 (surface, color, start_pos, end_pos, width)
    pygame.draw.line(screen, BLUE, (100, 400), (700, 400), 3)

    # 绘制空心矩形（第5个参数控制宽度，0=填充）
    pygame.draw.rect(screen, WHITE, (400, 350, 150, 100), 3)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
```

### 4.5 绘制文字

```python
# 创建字体对象
font_large = pygame.font.SysFont("Arial", 48)  # 系统字体
font_custom = pygame.font.Font(None, 36)        # Pygame 默认字体

# 渲染文字 (文字, 抗锯齿, 颜色)
text_surface = font_large.render("Hello Pygame!", True, (255, 255, 255))

# 将文字绘制到屏幕上
screen.blit(text_surface, (200, 100))
```

---

## 5. 游戏对象管理——精灵系统

精灵（Sprite）是 Pygame 中管理游戏对象的核心机制。每个游戏对象（玩家、敌人、子弹）都可以是一个精灵。

### 精灵系统的工作原理

```
┌────────────────────────────────────────────┐
│            Sprite Group（精灵组）             │
│  ┌────────┐  ┌────────┐  ┌────────┐        │
│  │ Player │  │ Enemy  │  │ Bullet │        │
│  │ sprite │  │ sprite │  │ sprite │        │
│  └────────┘  └────────┘  └────────┘        │
│       ↓            ↓            ↓           │
│  group.update()  — 自动调用每个精灵的 update │
│  group.draw()    — 自动绘制所有精灵         │
└────────────────────────────────────────────┘
```

### 基本精灵类

```python
import pygame

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # 创建一个 50x50 的红色方块作为玩家外观
        self.image = pygame.Surface((50, 50))
        self.image.fill((255, 0, 0))
        
        # 获取矩形区域，用于定位和碰撞检测
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        
        # 速度
        self.speed = 5
    
    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if keys[pygame.K_UP]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.rect.y += self.speed
```

### 精灵组的使用

```python
# 创建精灵组
all_sprites = pygame.sprite.Group()
players = pygame.sprite.Group()
enemies = pygame.sprite.Group()

# 添加精灵
player = Player(400, 300)
all_sprites.add(player)
players.add(player)

# 在游戏循环中
all_sprites.update()   # 更新所有精灵
all_sprites.draw(screen)  # 绘制所有精灵
```

---

## 6. 碰撞检测基础

### 矩形碰撞（AABB）

最简单的碰撞检测——两个矩形是否重叠：

```python
if player.rect.colliderect(enemy.rect):
    print("碰撞了！")
```

### 精灵组碰撞

```python
# 检查一个精灵与一组精灵的碰撞
hits = pygame.sprite.spritecollide(player, enemies, False)
# 返回与 player 碰撞的所有 enemies 精灵
# 第二个参数 False 表示碰撞后不删除精灵

# 检查两组精灵之间的碰撞
hits = pygame.sprite.groupcollide(players, enemies, False, True)
# 最后一个 True 表示碰撞后删除 enemy
```

---

## 7. 加载图片

```python
# 加载图片
player_image = pygame.image.load("player.png").convert_alpha()

# 缩放图片
player_image = pygame.transform.scale(player_image, (64, 64))

# 显示图片
screen.blit(player_image, (100, 100))
```

**`convert()` vs `convert_alpha()`：**
- `convert()` — 转换为与显示相同的像素格式（更快，但无透明通道）
- `convert_alpha()` — 保留 alpha 透明通道（PNG 图片用这个）

---

## 8. 完整示例：弹跳小球

一个完整的游戏示例，展示所有核心概念的综合运用：

```python
import pygame
import sys
import random

# 初始化
pygame.init()

# 常量
WIDTH, HEIGHT = 800, 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)

# 创建窗口和时钟
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("弹跳小球")
clock = pygame.time.Clock()

# 小球类
class Ball(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.radius = 20
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, RED, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        
        self.vx = random.choice([-4, 4])
        self.vy = random.choice([-4, 4])
    
    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        
        # 碰到边界反弹
        if self.rect.left <= 0 or self.rect.right >= WIDTH:
            self.vx = -self.vx
        if self.rect.top <= 0 or self.rect.bottom >= HEIGHT:
            self.vy = -self.vy

# 主函数
def main():
    ball = Ball()
    all_sprites = pygame.sprite.Group(ball)
    
    font = pygame.font.Font(None, 36)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        all_sprites.update()
        
        screen.fill(BLACK)
        all_sprites.draw(screen)
        
        # 显示提示
        text = font.render("按 ESC 退出", True, WHITE)
        screen.blit(text, (10, 10))
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
```

---

## 9. 常见陷阱与避坑指南

### ❌ 陷阱 1：忘记 pygame.init()

```python
# 错误：直接使用 pygame 功能
screen = pygame.display.set_mode((800, 600))  # 可能报错

# 正确：先初始化
pygame.init()
screen = pygame.display.set_mode((800, 600))
```

### ❌ 陷阱 2：在循环外获取事件

```python
# 错误：事件只获取一次
events = pygame.event.get()  # 只在循环外获取一次
while running:
    for event in events:  # 永远是同一批事件！
        ...

# 正确：每帧都获取事件
while running:
    for event in pygame.event.get():  # 每帧重新获取
        ...
```

### ❌ 陷阱 3：修改 rect 时忘记边界检查

```python
# 错误：球可能飞出屏幕
self.rect.x += self.vx

# 正确：先移动再检查边界
self.rect.x += self.vx
if self.rect.left < 0:
    self.rect.left = 0
    self.vx = -self.vx
```

### ❌ 陷阱 4：FPS 不稳定

```python
# 错误：用 time.sleep 控制帧率
time.sleep(0.016)  # 不精确，且阻塞

# 正确：用 Clock
clock.tick(60)  # 精确控制，自动补偿处理时间
```

### ❌ 陷阱 5：忘记退出清理

```python
# 错误：直接退出
sys.exit()  # 可能导致资源未释放

# 正确：先退出 Pygame
pygame.quit()
sys.exit()
```

---

## 10. Pygame API 速查表

### 初始化与窗口

| 函数/方法 | 说明 |
|-----------|------|
| `pygame.init()` | 初始化所有模块 |
| `pygame.quit()` | 取消初始化所有模块 |
| `pygame.display.set_mode((w, h))` | 创建窗口 |
| `pygame.display.set_caption("title")` | 设置窗口标题 |
| `pygame.display.flip()` | 更新整个显示表面 |
| `pygame.display.update()` | 更新显示（可指定区域） |

### 事件处理

| 函数/方法 | 说明 |
|-----------|------|
| `pygame.event.get()` | 获取所有事件 |
| `pygame.event.poll()` | 获取一个事件 |
| `pygame.key.get_pressed()` | 获取所有按键状态 |

### 绘制

| 函数/方法 | 说明 |
|-----------|------|
| `pygame.draw.rect(surface, color, rect, width=0)` | 绘制矩形 |
| `pygame.draw.circle(surface, color, center, radius)` | 绘制圆形 |
| `pygame.draw.line(surface, color, start, end, width)` | 绘制线段 |
| `surface.fill(color)` | 填充整个表面 |
| `surface.blit(source, dest)` | 将一个表面绘制到另一个 |

### 精灵

| 函数/方法 | 说明 |
|-----------|------|
| `pygame.sprite.Sprite` | 精灵基类 |
| `pygame.sprite.Group()` | 精灵组 |
| `group.add(sprite)` | 添加精灵 |
| `group.update()` | 更新所有精灵 |
| `group.draw(surface)` | 绘制所有精灵 |

### 时间

| 函数/方法 | 说明 |
|-----------|------|
| `pygame.time.Clock()` | 创建时钟对象 |
| `clock.tick(fps)` | 控制帧率 |
| `clock.get_fps()` | 获取当前实际 FPS |
| `pygame.time.get_ticks()` | 获取程序运行毫秒数 |

---

## 11. 思考题

1. **为什么游戏循环要分开"事件处理→更新→渲染"这三个步骤？如果把它们混在一起会怎样？**

2. **`pygame.event.get()` 和 `pygame.key.get_pressed()` 有什么区别？分别适合什么场景？**

3. **为什么 Pygame 的 Y 轴是向下增长的？这和计算机屏幕的扫描方式有什么关系？**

4. **如果游戏运行在不同性能的电脑上，帧率不稳定会导致什么问题？`clock.tick(60)` 如何帮助解决这个问题？**

5. **精灵组（Sprite Group）的设计有什么好处？如果不使用精灵组，手动管理多个游戏对象会面临什么问题？**

---

## 今日小结

- Pygame 是基于 SDL 的 Python 2D 游戏框架
- 游戏循环是游戏的心脏：事件处理 → 更新 → 渲染
- `pygame.display` 负责窗口和显示，`pygame.event` 负责用户输入
- 精灵系统提供了高效的游戏对象管理机制
- 碰撞检测从简单的矩形碰撞开始
- 帧率控制确保游戏在不同机器上体验一致

**下一课预告**：Day 089 将深入游戏循环与事件处理，实现一个完整的贪吃蛇游戏！
