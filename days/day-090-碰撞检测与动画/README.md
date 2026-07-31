# Day 090 — 碰撞检测与动画

> 🎮 Phase 6 实战项目 | Python 游戏开发第三天

## 📚 学习目标

今天我们将掌握游戏开发中两个核心主题：**碰撞检测**和**动画系统**。碰撞检测是让游戏世界"真实"的关键，而动画则让游戏角色和场景"活"起来。

---

## 一、碰撞检测基础

### 1.1 为什么需要碰撞检测？

在没有碰撞检测的游戏里，角色可以穿过墙壁、子弹打不到敌人、两个角色可以重叠。碰撞检测就是让游戏物体之间产生"物理交互"的机制。

```
没有碰撞检测:          有碰撞检测:
  🧑 → 🧱              🧑 🧱
  (穿过去了!)           (被墙挡住!)
```

### 1.2 碰撞检测的三种主要类型

| 类型 | 原理 | 性能 | 适用场景 |
|------|------|------|----------|
| **AABB（轴对齐包围盒）** | 用矩形框住物体 | ⭐⭐⭐ 极快 | 矩形物体、快速原型 |
| **圆形碰撞** | 检查两个圆是否重叠 | ⭐⭐⭐ 极快 | 球类游戏、子弹 |
| **像素级碰撞** | 逐像素检查重叠 | ⭐ 很慢 | 需要精确碰撞的场景 |

### 1.3 AABB 碰撞检测（Axis-Aligned Bounding Box）

AABB 是最常用的碰撞检测方式，原理简单：

**核心判断条件：**
```
两个矩形 AABB 碰撞 ⟺
  A.left < B.right  AND
  A.right > B.left  AND
  A.top < B.bottom  AND
  A.bottom > B.top
```

```python
def aabb_collision(rect_a, rect_b):
    """检测两个矩形是否碰撞"""
    return (
        rect_a.left < rect_b.right and
        rect_a.right > rect_b.left and
        rect_a.top < rect_b.bottom and
        rect_a.bottom > rect_b.top
    )
```

**为什么是这个顺序？** 因为我们需要检查的是"不重叠"的条件——只要任一条件不满足，就说明没有碰撞。取反后就是"发生碰撞"的条件。

### 1.4 圆形碰撞检测

```python
import math

def circle_collision(pos_a, radius_a, pos_b, radius_b):
    """检测两个圆形是否碰撞"""
    distance = math.sqrt(
        (pos_a[0] - pos_b[0])**2 +
        (pos_a[1] - pos_b[1])**2
    )
    return distance <= (radius_a + radius_b)
```

**原理图解：**
```
      A ●──── r_a
         \     
          \  ← 距离 d
           \
      B ●──── r_b

碰撞条件: d <= r_a + r_b
```

### 1.5 混合碰撞检测

实际游戏中，物体形状复杂，通常用 **包围盒 + 细化检测**：

```python
def smart_collision(obj_a, obj_b):
    """先用 AABB 快速排除，再做精确检测"""
    # 第一步：AABB 快速过滤
    if not aabb_collision(obj_a.rect, obj_b.rect):
        return False
    
    # 第二步：圆形精确检测（如果物体大致是圆的）
    if obj_a.shape == 'circle' and obj_b.shape == 'circle':
        return circle_collision(
            obj_a.center, obj_a.radius,
            obj_b.center, obj_b.radius
        )
    
    # 第三步：像素级检测（如果需要精确）
    if obj_a.shape == 'sprite' and obj_b.shape == 'sprite':
        return pixel_perfect_collision(obj_a.mask, obj_b.mask)
    
    return True  # 默认用 AABB 结果
```

---

## 二、碰撞响应

碰撞检测告诉你"撞了"，碰撞响应告诉你"撞了之后怎么办"。

### 2.1 碰撞响应类型

```
碰撞类型:
├── 弹性碰撞 (Elastic)    → 物体反弹，动能守恒
├── 非弹性碰撞 (Inelastic) → 物体粘在一起
├── 反射碰撞 (Bounce)     → 反射速度方向
└── 穿透碰撞 (Penetrate)  → 物体穿过（子弹打墙）
```

### 2.2 反射碰撞（反弹）

```python
def bounce_response(velocity, normal):
    """根据法线计算反弹速度"""
    # 反射公式: v' = v - 2(v·n)n
    dot = velocity[0] * normal[0] + velocity[1] * normal[1]
    return (
        velocity[0] - 2 * dot * normal[0],
        velocity[1] - 2 * dot * normal[1]
    )
```

### 2.3 停止碰撞（墙壁阻挡）

```python
def stop_response(position, velocity, wall_rect):
    """碰到墙壁时停止移动"""
    if position[0] < wall_rect.left:
        position = (wall_rect.left, position[1])
        velocity = (0, velocity[1])
    elif position[0] > wall_rect.right:
        position = (wall_rect.right, position[1])
        velocity = (0, velocity[1])
    
    if position[1] < wall_rect.top:
        position = (position[0], wall_rect.top)
        velocity = (velocity[0], 0)
    elif position[1] > wall_rect.bottom:
        position = (position[0], wall_rect.bottom)
        velocity = (velocity[0], 0)
    
    return position, velocity
```

### 2.4 分离碰撞（推开）

```python
def separate_response(obj_a, obj_b):
    """将两个重叠的物体分开"""
    dx = obj_a.center_x - obj_b.center_x
    dy = obj_a.center_y - obj_b.center_y
    distance = math.sqrt(dx*dx + dy*dy)
    
    if distance == 0:
        dx, dy = 1, 0  # 避免除零
        distance = 1
    
    # 计算重叠量
    overlap = (obj_a.radius + obj_b.radius) - distance
    
    # 按距离比例分开
    ratio = overlap / (2 * distance)
    obj_a.x += dx * ratio
    obj_a.y += dy * ratio
    obj_b.x -= dx * ratio
    obj_b.y -= dy * ratio
```

---

## 三、动画系统

### 3.1 帧动画原理

帧动画就是快速播放一系列图片，利用人眼的视觉暂留产生运动效果：

```
时间轴:  0ms    100ms   200ms   300ms   400ms
画面:    🧑🚶   🧑🏃   🧑🏃   🧑🚶   🧑🏃
         帧1    帧2    帧3    帧4    帧1(循环)
```

### 3.2 精灵表（Sprite Sheet）

精灵表将多帧画面放在一张大图里，减少文件IO：

```
┌─────────────────────────────────┐
│  帧1    帧2    帧3    帧4       │  ← 行1: 走路
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐   │
│ │ 🧑 │ │ 🧑 │ │ 🧑 │ │ 🧑 │   │
│ └────┘ └────┘ └────┘ └────┘   │
├─────────────────────────────────┤
│  帧1    帧2    帧3    帧4       │  ← 行2: 跑步
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐   │
│ │ 🧑 │ │ 🧑 │ │ 🧑 │ │ 🧑 │   │
│ └────┘ └────┘ └────┘ └────┘   │
└─────────────────────────────────┘
```

### 3.3 动画状态机

游戏角色可以有多种动画状态：

```
         ┌──────────┐
    ┌───→│   空闲   │←───┐
    │    │  idle    │    │
    │    └────┬─────┘    │
    │         │ 按键     │ 松开
    │         ↓          │
    │    ┌──────────┐    │
    └────│   行走   │────┘
         │  walk    │
         └────┬─────┘
              │ 速度>阈值
              ↓
         ┌──────────┐
         │   跑步   │
         │  run     │
         └────┬─────┘
              │ 跳跃
              ↓
         ┌──────────┐
         │   跳跃   │
         │  jump    │
         └──────────┘
```

### 3.4 插值动画

除了帧动画，还可以用数学公式平滑地改变属性：

```python
def lerp(start, end, t):
    """线性插值 (Linear Interpolation)"""
    return start + (end - start) * t

# 用法：从 A 点平滑移动到 B 点
current_x = lerp(start_x, end_x, progress)  # progress: 0.0 → 1.0
```

**缓动函数（Easing）：**
```python
def ease_in_quad(t):
    """二次加速"""
    return t * t

def ease_out_quad(t):
    """二次减速"""
    return t * (2 - t)

def ease_in_out_quad(t):
    """加速后减速"""
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t
```

```
缓动效果:
线性:     ╱╱╱╱╱╱╱╱╱╱  匀速
加速:    ╱  ╱ ╱╱╱╱╱╱  先慢后快
减速:    ╱╱╱╱╱ ╱  ╱   先快后慢
S曲线:   ╱  ╱╱╱╱  ╱   慢→快→慢
```

---

## 四、Pygame 碰撞与动画实战

### 4.1 Pygame 内置碰撞检测

```python
import pygame

# 矩形碰撞
if player.rect.colliderect(enemy.rect):
    print("碰撞了!")

# 圆形碰撞
if pygame.sprite.collide_circle(player, enemy):
    print("圆形碰撞!")

# 精灵组碰撞检测
hits = pygame.sprite.groupcollide(bullets, enemies, True, True)
# 参数: 组A, 组B, 碰撞后销毁A, 碰撞后销毁B

# 精灵与组碰撞
hits = pygame.sprite.spritecollide(player, enemies, False)
```

### 4.2 碰撞遮罩（像素级）

```python
# 创建碰撞遮罩
mask_a = pygame.mask.from_surface(image_a)
mask_b = pygame.mask.from_surface(image_b)

# 像素级碰撞检测
offset = (rect_b.x - rect_a.x, rect_b.y - rect_a.y)
if mask_a.overlap(mask_b, offset):
    print("像素级碰撞!")
```

### 4.3 动画实现

```python
class AnimatedSprite:
    def __init__(self, sprite_sheet, frame_width, frame_height, fps=10):
        self.frames = []
        self.current_frame = 0
        self.timer = 0
        self.fps = fps
        
        # 从精灵表切割帧
        cols = sprite_sheet.get_width() // frame_width
        rows = sprite_sheet.get_height() // frame_height
        for row in range(rows):
            for col in range(cols):
                frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
                frame.blit(sprite_sheet, (0, 0),
                          (col * frame_width, row * frame_height,
                           frame_width, frame_height))
                self.frames.append(frame)
    
    def update(self, dt):
        """更新动画帧"""
        self.timer += dt
        if self.timer >= 1.0 / self.fps:
            self.timer = 0
            self.current_frame = (self.current_frame + 1) % len(self.frames)
    
    def get_frame(self):
        """获取当前帧"""
        return self.frames[self.current_frame]
```

---

## 五、性能优化

### 5.1 空间分区（Spatial Partitioning）

当物体很多时，逐一检测太慢。空间分区可以快速排除不可能碰撞的物体：

```
全部物体逐一检测: O(n²)
  物体1 vs 物体2,3,4,5,6,7,8...
  物体2 vs 物体1,3,4,5,6,7,8...
  ...

网格分区后:       O(n)
  ┌───┬───┬───┐
  │1,2│ 3 │4,5│  → 只检测同一格子内的物体
  ├───┼───┼───┤
  │ 6 │7,8│   │
  └───┴───┴───┘
```

### 5.2 四叉树（Quadtree）

```python
class Quadtree:
    """四叉树空间分区"""
    MAX_OBJECTS = 5
    MAX_LEVELS = 5
    
    def __init__(self, level, bounds):
        self.level = level
        self.bounds = bounds
        self.objects = []
        self.nodes = []
    
    def split(self):
        """将当前区域分成四个子区域"""
        x, y, w, h = self.bounds
        sub_w, sub_h = w / 2, h / 2
        
        self.nodes = [
            Quadtree(self.level + 1, (x, y, sub_w, sub_h)),         # 左上
            Quadtree(self.level + 1, (x + sub_w, y, sub_w, sub_h)), # 右上
            Quadtree(self.level + 1, (x, y + sub_h, sub_w, sub_h)), # 左下
            Quadtree(self.level + 1, (x + sub_w, y + sub_h, sub_w, sub_h)), # 右下
        ]
    
    def insert(self, obj):
        """插入物体"""
        if len(self.objects) >= self.MAX_OBJECTS and self.level < self.MAX_LEVELS:
            if not self.nodes:
                self.split()
            self._insert_to_node(obj)
        else:
            self.objects.append(obj)
    
    def retrieve(self, rect):
        """检索可能与给定矩形碰撞的物体"""
        candidates = list(self.objects)
        if self.nodes:
            for node in self.nodes:
                if self._intersects(rect, node.bounds):
                    candidates.extend(node.retrieve(rect))
        return candidates
```

---

## 六、实战：飞机大战完整示例

### 游戏流程图

```
┌─────────────────────────────────────┐
│            游戏主循环               │
│  ┌───────┐  ┌───────┐  ┌───────┐  │
│  │ 事件  │→│ 更新  │→│ 渲染  │  │
│  │ 处理  │  │ 逻辑  │  │ 画面  │  │
│  └───────┘  └───┬───┘  └───────┘  │
│                 │                   │
│         ┌───────┴───────┐          │
│         ↓               ↓          │
│   ┌──────────┐   ┌──────────┐     │
│   │ 移动检测 │   │ 碰撞检测 │     │
│   └──────────┘   └────┬─────┘     │
│                       ↓            │
│              ┌──────────────┐      │
│              │  碰撞响应    │      │
│              │ (扣血/爆炸)  │      │
│              └──────────────┘      │
└─────────────────────────────────────┘
```

---

## 七、思考题

1. **碰撞检测频率**：如果游戏运行在 60 FPS，每帧都做全量碰撞检测是否合理？什么情况下需要做"物理帧"和"渲染帧"分离？

2. **AABB 的局限性**：当游戏角色是旋转的矩形时，AABB 碰撞检测会出问题吗？如何解决？

3. **动画流畅性**：帧动画的帧率应该和游戏帧率同步吗？如果游戏从 60 FPS 降到 30 FPS，动画会怎么表现？

4. **四叉树 vs 网格**：在什么场景下四叉树比网格分区更优？反之呢？

5. **碰撞预测**：在高速移动的物体（如子弹）中，可能出现"穿透"问题（一帧从墙这边跳到墙那边）。如何解决？

---

## 📖 延伸阅读

- [Pygame 官方文档 - Sprite](https://www.pygame.org/docs/ref/sprite.html)
- [Game Programming Patterns - Double Buffer](https://gameprogrammingpatterns.com/double-buffer.html)
- [Red Blob Games - 碰撞检测](https://www.redblobgames.com/articles/visibility/)
