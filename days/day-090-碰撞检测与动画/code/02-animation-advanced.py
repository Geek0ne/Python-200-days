#!/usr/bin/env python3
"""
Day 090 - 碰撞检测与动画: 动画系统与进阶技巧
演示帧动画、状态机、缓动函数、四叉树
"""

import math
import time
import random


# ═══════════════════════════════════════════════
# 1. 帧动画系统
# ═══════════════════════════════════════════════

class Animation:
    """帧动画类"""
    def __init__(self, frames, fps=10, loop=True):
        """
        frames: 帧列表（字符串模拟）
        fps: 每秒帧数
        loop: 是否循环
        """
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.current_frame = 0
        self.timer = 0.0
        self.finished = False
    
    def update(self, dt):
        """更新动画 (dt = 帧间隔时间)"""
        if self.finished:
            return
        
        self.timer += dt
        frame_duration = 1.0 / self.fps
        
        while self.timer >= frame_duration:
            self.timer -= frame_duration
            self.current_frame += 1
            
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.finished = True
    
    def get_frame(self):
        """获取当前帧"""
        return self.frames[self.current_frame]
    
    def reset(self):
        """重置动画"""
        self.current_frame = 0
        self.timer = 0.0
        self.finished = False


# ═══════════════════════════════════════════════
# 2. 动画状态机
# ═══════════════════════════════════════════════

class AnimationState:
    """动画状态"""
    def __init__(self, name, animation):
        self.name = name
        self.animation = animation
        self.transitions = {}  # {事件: 目标状态名}


class AnimationStateMachine:
    """动画状态机"""
    def __init__(self):
        self.states = {}
        self.current_state = None
    
    def add_state(self, state):
        """添加状态"""
        self.states[state.name] = state
    
    def set_initial(self, state_name):
        """设置初始状态"""
        self.current_state = self.states[state_name]
    
    def add_transition(self, from_state, event, to_state):
        """添加状态转换"""
        self.states[from_state].transitions[event] = to_state
    
    def handle_event(self, event):
        """处理事件，触发状态转换"""
        if not self.current_state:
            return
        
        if event in self.current_state.transitions:
            next_name = self.current_state.transitions[event]
            self.current_state.animation.reset()
            self.current_state = self.states[next_name]
            return True
        return False
    
    def update(self, dt):
        """更新当前状态的动画"""
        if self.current_state:
            self.current_state.animation.update(dt)
    
    def get_frame(self):
        """获取当前帧"""
        if self.current_state:
            return self.current_state.animation.get_frame()
        return None
    
    def get_state_name(self):
        """获取当前状态名"""
        return self.current_state.name if self.current_state else "None"


# ═══════════════════════════════════════════════
# 3. 缓动函数 (Easing Functions)
# ═══════════════════════════════════════════════

def ease_linear(t):
    """线性 - 匀速"""
    return t

def ease_in_quad(t):
    """二次加速 - 越来越快"""
    return t * t

def ease_out_quad(t):
    """二次减速 - 越来越慢"""
    return t * (2 - t)

def ease_in_out_quad(t):
    """二次缓动 - 先慢后快再慢"""
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

def ease_in_cubic(t):
    """三次加速"""
    return t * t * t

def ease_out_cubic(t):
    """三次减速"""
    t -= 1
    return t * t * t + 1

def ease_out_bounce(t):
    """弹跳效果"""
    if t < 1/2.75:
        return 7.5625 * t * t
    elif t < 2/2.75:
        t -= 1.5/2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5/2.75:
        t -= 2.25/2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625/2.75
        return 7.5625 * t * t + 0.984375

def ease_out_elastic(t):
    """弹性效果"""
    if t == 0 or t == 1:
        return t
    return math.pow(2, -10 * t) * math.sin((t - 0.075) * (2 * math.pi) / 0.3) + 1


# ═══════════════════════════════════════════════
# 4. 线性插值 (Lerp)
# ═══════════════════════════════════════════════

def lerp(start, end, t):
    """线性插值: 在 start 和 end 之间按比例 t 取值"""
    return start + (end - start) * t

def lerp_color(color_a, color_b, t):
    """颜色插值"""
    return tuple(int(lerp(a, b, t)) for a, b in zip(color_a, color_b))


# ═══════════════════════════════════════════════
# 5. 四叉树 (Quadtree) 空间分区
# ═══════════════════════════════════════════════

class AABB:
    """轴对齐包围盒"""
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
    
    def contains(self, point):
        """检查点是否在盒子内"""
        return (self.x <= point[0] < self.x + self.w and
                self.y <= point[1] < self.y + self.h)
    
    def intersects(self, other):
        """检查两个盒子是否相交"""
        return not (other.x > self.x + self.w or
                    other.x + other.w < self.x or
                    other.y > self.y + self.h or
                    other.y + other.h < self.y)


class Quadtree:
    """四叉树空间分区"""
    CAPACITY = 4  # 每个节点最多存储的物体数
    
    def __init__(self, boundary):
        self.boundary = boundary  # AABB
        self.points = []
        self.divided = False
        self.northeast = None
        self.northwest = None
        self.southeast = None
        self.southwest = None
    
    def subdivide(self):
        """将当前区域分成四个子区域"""
        x, y, w, h = self.boundary.x, self.boundary.y, self.boundary.w, self.boundary.h
        nw = AABB(x, y, w/2, h/2)
        ne = AABB(x + w/2, y, w/2, h/2)
        sw = AABB(x, y + h/2, w/2, h/2)
        se = AABB(x + w/2, y + h/2, w/2, h/2)
        
        self.northwest = Quadtree(nw)
        self.northeast = Quadtree(ne)
        self.southwest = Quadtree(sw)
        self.southeast = Quadtree(se)
        self.divided = True
    
    def insert(self, point):
        """插入点"""
        if not self.boundary.contains(point):
            return False
        
        if len(self.points) < self.CAPACITY and not self.divided:
            self.points.append(point)
            return True
        
        if not self.divided:
            self.subdivide()
        
        return (self.northwest.insert(point) or
                self.northeast.insert(point) or
                self.southwest.insert(point) or
                self.southeast.insert(point))
    
    def query_range(self, range_rect):
        """查询范围内的点"""
        results = []
        if not self.boundary.intersects(range_rect):
            return results
        
        for point in self.points:
            if range_rect.contains(point):
                results.append(point)
        
        if self.divided:
            results.extend(self.northwest.query_range(range_rect))
            results.extend(self.northeast.query_range(range_rect))
            results.extend(self.southwest.query_range(range_rect))
            results.extend(self.southeast.query_range(range_rect))
        
        return results


# ═══════════════════════════════════════════════
# 6. 精灵动画控制器
# ═══════════════════════════════════════════════

class SpriteAnimator:
    """精灵动画控制器 - 管理多组动画"""
    def __init__(self):
        self.animations = {}  # {名称: Animation}
        self.current = None
        self.current_name = ""
    
    def add_animation(self, name, animation):
        """添加动画组"""
        self.animations[name] = animation
    
    def play(self, name, restart=False):
        """播放指定动画"""
        if name == self.current_name and not restart:
            return
        
        if name in self.animations:
            if self.current:
                self.current.reset()
            self.current = self.animations[name]
            self.current_name = name
    
    def update(self, dt):
        """更新当前动画"""
        if self.current:
            self.current.update(dt)
    
    def get_frame(self):
        """获取当前帧"""
        if self.current:
            return self.current.get_frame()
        return None


# ═══════════════════════════════════════════════
# 主函数: 演示所有进阶技巧
# ═══════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Day 090 — 动画系统与进阶技巧演示")
    print("=" * 60)
    
    # --- 帧动画 ---
    print("\n【1. 帧动画系统】")
    print("-" * 40)
    
    walk_frames = ["🚶", "🚶‍♂️", "🚶", "🚶‍♀️"]
    run_frames = ["🏃", "🏃‍♂️", "🏃", "🏃‍♀️"]
    
    walk_anim = Animation(walk_frames, fps=4, loop=True)
    
    print(f"  走路动画: {walk_frames}")
    print(f"  帧率: 4fps, 循环: True")
    
    # 模拟 1 秒的动画
    dt = 1.0 / 30  # 30 FPS
    print(f"\n  模拟 1 秒 (30帧):")
    for i in range(30):
        walk_anim.update(dt)
        if i % 5 == 0:
            print(f"    帧 {i:>2}: {walk_anim.get_frame()}")
    
    # --- 动画状态机 ---
    print("\n【2. 动画状态机】")
    print("-" * 40)
    
    idle_anim = Animation(["🧑‍🦯"] * 4, fps=2)
    walk_anim2 = Animation(["🚶"] * 4, fps=6)
    run_anim = Animation(["🏃"] * 4, fps=10)
    jump_anim = Animation(["🧑‍🦘"] * 2, fps=8, loop=False)
    
    fsm = AnimationStateMachine()
    fsm.add_state(AnimationState("idle", idle_anim))
    fsm.add_state(AnimationState("walk", walk_anim2))
    fsm.add_state(AnimationState("run", run_anim))
    fsm.add_state(AnimationState("jump", jump_anim))
    
    fsm.set_initial("idle")
    fsm.add_transition("idle", "press_right", "walk")
    fsm.add_transition("walk", "hold_shift", "run")
    fsm.add_transition("walk", "press_space", "jump")
    fsm.add_transition("run", "press_space", "jump")
    fsm.add_transition("jump", "land", "idle")
    fsm.add_transition("walk", "release", "idle")
    fsm.add_transition("run", "release", "idle")
    
    events = ["press_right", "hold_shift", "press_space", "land"]
    print(f"  初始状态: {fsm.get_state_name()}")
    
    for event in events:
        changed = fsm.handle_event(event)
        status = "✓" if changed else "✗"
        print(f"  事件 '{event}' → {status} 当前状态: {fsm.get_state_name()}")
    
    # --- 缓动函数 ---
    print("\n【3. 缓动函数对比】")
    print("-" * 40)
    
    easings = [
        ("线性", ease_linear),
        ("二次加速", ease_in_quad),
        ("二次减速", ease_out_quad),
        ("二次缓动", ease_in_out_quad),
        ("三次加速", ease_in_cubic),
        ("弹跳", ease_out_bounce),
    ]
    
    steps = 10
    for name, func in easings:
        bar = ""
        for i in range(steps + 1):
            t = i / steps
            val = func(t)
            filled = int(val * 10)
            bar += "█" * filled + "░" * (10 - filled) + " "
        print(f"  {name:>8}: {bar}")
    
    # --- 插值动画 ---
    print("\n【4. 线性插值动画】")
    print("-" * 40)
    
    start_pos = (0, 0)
    end_pos = (100, 50)
    
    print(f"  起点: {start_pos}")
    print(f"  终点: {end_pos}")
    print()
    
    for i in range(11):
        t = i / 10
        x = lerp(start_pos[0], end_pos[0], t)
        y = lerp(start_pos[1], end_pos[1], t)
        marker = "●" * int(x / 10)
        print(f"  t={t:.1f}: ({x:>5.1f}, {y:>5.1f}) {marker}")
    
    # 颜色插值
    red = (255, 0, 0)
    blue = (0, 0, 255)
    print(f"\n  颜色渐变: 红→蓝")
    for i in range(6):
        t = i / 5
        color = lerp_color(red, blue, t)
        print(f"    t={t:.1f}: RGB{color}")
    
    # --- 四叉树 ---
    print("\n【5. 四叉树空间分区】")
    print("-" * 40)
    
    random.seed(42)
    boundary = AABB(0, 0, 100, 100)
    qt = Quadtree(boundary)
    
    # 插入随机点
    points = [(random.randint(0, 100), random.randint(0, 100)) for _ in range(50)]
    for p in points:
        qt.insert(p)
    
    # 查询一个区域
    query_rect = AABB(25, 25, 25, 25)
    found = qt.query_range(query_rect)
    
    print(f"  空间范围: (0,0) 到 (100,100)")
    print(f"  插入 {len(points)} 个随机点")
    print(f"  查询区域: (25,25) 大小 25x25")
    print(f"  找到 {len(found)} 个点: {found[:10]}...")
    
    # 性能对比
    print(f"\n  空间分区性能:")
    for n in [100, 1000, 5000]:
        boundary = AABB(0, 0, 1000, 1000)
        qt = Quadtree(boundary)
        pts = [(random.randint(0, 1000), random.randint(0, 1000)) for _ in range(n)]
        
        start = time.time()
        for p in pts:
            qt.insert(p)
        insert_time = (time.time() - start) * 1000
        
        query = AABB(400, 400, 200, 200)
        start = time.time()
        found = qt.query_range(query)
        query_time = (time.time() - start) * 1000
        
        print(f"    {n:>5} 点: 插入 {insert_time:.2f}ms, 查询 {query_time:.3f}ms, 找到 {len(found)} 个")
    
    # --- 精灵动画控制器 ---
    print("\n【6. 精灵动画控制器】")
    print("-" * 40)
    
    animator = SpriteAnimator()
    animator.add_animation("idle", Animation(["😊"] * 4, fps=2))
    animator.add_animation("walk", Animation(["🚶", "🏃"] * 2, fps=6))
    animator.add_animation("run", Animation(["🏃", "💨"] * 2, fps=10))
    animator.add_animation("jump", Animation(["🦘", "⬆️"], fps=8, loop=False))
    
    actions = [("idle", False), ("walk", True), ("run", True), ("jump", False)]
    for name, restart in actions:
        animator.play(name, restart=restart)
        animator.update(0.1)
        print(f"  播放 '{name}': 帧={animator.get_frame()}, 状态={animator.current_name}")
    
    print("\n✅ 动画系统与进阶技巧演示完成!")


if __name__ == "__main__":
    main()
