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

**参考答案**

物体少时，60 FPS 每帧做全量检测是合理的——AABB/圆形检测本身极快，即使两两 `O(n²)`，n 很小也毫无压力。但物体一多（成百上千），全量两两检测的 `O(n²)` 就会成为瓶颈，这时要么用**空间分区**（网格/四叉树）先粗筛掉不可能碰撞的对，要么降低检测频率。

需要把「物理帧」和「渲染帧」分离的典型情况：

- **物理要稳定/可复现**：物理用固定步长（如 60Hz 或 120Hz），而渲染帧率随机器波动；分离后物理不受渲染快慢影响。
- **物理计算昂贵**：不必每个渲染帧都算物理，比如物理 30Hz、渲染 60Hz，省一半算力。
- **高速物体防穿透**：物理频率要足够高（或配合连续碰撞检测），否则子弹一帧穿过墙。
- **网络同步**：联机游戏要求确定性的物理步长，必须与渲染解耦。

分离的常见做法：用累积器驱动固定步长的物理更新，渲染时对物理状态做**插值**，兼顾稳定与流畅。

- 小例子：渲染跑 144 FPS，但物理固定 60Hz，多出来的渲染帧对前后两个物理状态插值——画面顺滑，物理又稳定可复现。

💡 提示：全量检测前先做空间分区粗筛，能把 `O(n²)` 降到接近 `O(n)`，这是物体多时的第一优化手段。

2. **AABB 的局限性**：当游戏角色是旋转的矩形时，AABB 碰撞检测会出问题吗？如何解决？

**参考答案**

会出问题。AABB 是**轴对齐**包围盒，永远平行于坐标轴。角色一旦旋转，AABB 取的是「能框住旋转后形状的最小轴对齐矩形」，它会比实际形状**大一圈**（旋转 45° 时尤其明显）。结果是：两个物体看起来还没碰到，它们的 AABB 却已经重叠 → **误报碰撞**（false positive）。

注意：AABB 仍然完整包住物体，所以一般不会「漏报」，问题在于「不精确、误报多」。

解决办法（按精度/成本递增）：

- **圆形近似**：圆是旋转不变的，用圆形碰撞代替，简单且不受旋转影响（适合大致是圆的角色）。
- **OBB + 分离轴定理（SAT）**：用「有向包围盒」跟随物体旋转，沿两个矩形各自的边法线做投影，只要存在一条轴让两者投影分离就没碰撞。精确且比像素级快。
- **像素级 mask**：最精确，但最慢，适合形状不规则且必须精确的场景。

- 小例子：一个细长矩形旋转 45°，它的 AABB 变成一个大正方形，对角处的空白区域也被算进碰撞范围，于是「擦边」就被误判为撞上。

⚠️ 注意：pygame 的 `rect` 始终是 AABB，`pygame.transform.rotate` 后 `rect` 会自动变大；要精确碰撞得用 `pygame.mask` 或自己实现 OBB/SAT。

3. **动画流畅性**：帧动画的帧率应该和游戏帧率同步吗？如果游戏从 60 FPS 降到 30 FPS，动画会怎么表现？

**参考答案**

不应该硬同步。帧动画应当按**真实时间**推进（用 `dt` 累积，每隔 `1/动画fps` 秒换一帧），而不是「每个游戏渲染帧换一帧」。

如果把动画绑死在游戏帧率上（每渲染帧换一张），那么游戏从 60 FPS 掉到 30 FPS 时，动画换帧速度也跟着减半 → **动画播放变慢、变成慢动作**，节奏随机器性能漂移，这正是我们要避免的。

正确做法是让动画计时与渲染帧率**解耦**：用 `clock.get_time()` 拿到真实 `dt` 累加，攒够一帧的时间才换帧。掉帧时动画仍按真实时间走（顶多跳过中间帧，但播放速度不变）。另外，动画帧率本身通常就低于游戏帧率（如动画 10~12 FPS、游戏 60 FPS），本来就不该每渲染帧都换。

- 小例子：动画 10 FPS、游戏 60 FPS → 每 6 个渲染帧换一张动画帧；游戏掉到 30 FPS → 每 3 个渲染帧换一张，动画速度始终不变。

💡 提示：当天 `AnimatedSprite.update(dt)` 里「`timer += dt`，攒够 `1/fps` 才换帧」的写法，天然就是帧率无关的，直接复用即可。

4. **四叉树 vs 网格**：在什么场景下四叉树比网格分区更优？反之呢？

**参考答案**

两者都是「空间分区」，目的都是快速排除不可能碰撞的物体，区别在于**分区是否自适应**。

**均匀网格**：把空间切成等大格子，物体按所在格子归类，只查同格/邻格。

- 优点：实现简单、定位 `O(1)`、缓存友好、常数开销小。
- 缺点：物体分布不均时，某些格子会挤爆而退化；格子大小要预先调好；跨格物体需额外处理。

**四叉树**：递归把空间四分，密集处细分、稀疏处保持粗。

- 优点：**自适应非均匀分布**，物体聚集在小区域时仍能细分保持高效；空间尺度跨度大也吃得下。
- 缺点：实现复杂、递归/指针开销大、频繁增删要维护平衡、物体移动跨节点需更新。

选择：

- **四叉树更优**：物体分布高度不均、有明显聚集（如开放世界、粒子向某点汇聚）、空间尺度跨度大。
- **网格更优**：物体分布均匀、数量稳定、格子大小可预估、追求简单与极致常数性能（大多数 2D 游戏、均匀弹幕）。

- 小例子：1000 个物体全挤在屏幕一角——网格会把那一格塞满、退化成 `O(n²)`；四叉树则在那一角不断细分，依旧高效。

💡 提示：均匀分布优先网格（简单又快）；非均匀/多尺度优先四叉树（自适应）。拿不准时先用网格， profiling 发现热点再换四叉树。

5. **碰撞预测**：在高速移动的物体（如子弹）中，可能出现"穿透"问题（一帧从墙这边跳到墙那边）。如何解决？

**参考答案**

这就是**穿透（tunneling）**：高速物体一帧的位移比墙还厚，离散检测只看帧末位置，起点和终点都在墙外，于是「明明穿过了墙」却判定没碰撞。

解决思路是「别只看首尾，要看中间路径」：

- **细分步长（substepping）**：把这一帧的位移切成若干小于墙厚的小步，逐步检测，只要任一小步落在墙里就算命中。简单直观。
- **连续碰撞检测（CCD / 扫掠检测）**：把物体这一帧的运动看成一条射线/扫掠体，直接求它与墙的**首次相交时刻**，精确又高效，是子弹类高速物体的首选。
- **提高物理频率**或**限制最大速度/单帧位移**，从源头减小穿透概率。

下面用纯标准库演示「离散漏检 vs 细分命中」（已验证）：

```python
# 高速物体「穿透」问题：离散检测会漏，细分步长（substepping）可解决
def discrete_hit(x0, x1, wall_left, wall_right):
    """只检查起点和终点是否与墙重叠（离散检测）"""
    def overlap(x):
        return wall_left <= x <= wall_right
    return overlap(x0) or overlap(x1)


def substep_hit(x0, x1, wall_left, wall_right, max_step=1.0):
    """把这一帧的位移切成若干小步，逐步检查（连续碰撞的近似）"""
    distance = x1 - x0
    steps = max(1, int(abs(distance) / max_step) + 1)
    for i in range(steps + 1):
        x = x0 + distance * i / steps
        if wall_left <= x <= wall_right:
            return True
    return False


# 子弹从 x=0 一帧飞到 x=100，墙在 [48, 52]（很薄）
x0, x1 = 0, 100
wall = (48, 52)
print("离散检测（只看首尾）:", discrete_hit(x0, x1, *wall))   # False → 穿透！
print("细分步长检测        :", substep_hit(x0, x1, *wall))    # True → 命中
```

预期输出：

```
离散检测（只看首尾）: False
细分步长检测        : True
```

子弹一帧从 0 飞到 100，薄墙在 `[48,52]`：只看首尾（0 和 100）都在墙外，离散检测漏判为 `False`；细分成小步后能扫到墙，正确返回 `True`。

⚠️ 注意：substepping 简单，但步数多时开销大；对子弹这类高速物体，用 CCD（射线 vs 墙求交）通常更精确高效。

---

## 📖 延伸阅读

- [Pygame 官方文档 - Sprite](https://www.pygame.org/docs/ref/sprite.html)
- [Game Programming Patterns - Double Buffer](https://gameprogrammingpatterns.com/double-buffer.html)
- [Red Blob Games - 碰撞检测](https://www.redblobgames.com/articles/visibility/)
