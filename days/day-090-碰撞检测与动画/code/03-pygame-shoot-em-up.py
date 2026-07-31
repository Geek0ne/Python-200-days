#!/usr/bin/env python3
"""
Day 090 - 碰撞检测与动画: 实战 - 简易弹球游戏
完整实现: 碰撞检测 + 动画 + 游戏逻辑
"""

import math
import time
import random


# ═══════════════════════════════════════════════
# 1. 游戏对象基类
# ═══════════════════════════════════════════════

class GameObject:
    """游戏对象基类"""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.vx = 0  # x方向速度
        self.vy = 0  # y方向速度
        self.active = True
    
    @property
    def left(self):
        return self.x
    
    @property
    def right(self):
        return self.x + self.width
    
    @property
    def top(self):
        return self.y
    
    @property
    def bottom(self):
        return self.y + self.height
    
    @property
    def center_x(self):
        return self.x + self.width / 2
    
    @property
    def center_y(self):
        return self.y + self.height / 2
    
    def update(self, dt):
        """更新位置"""
        self.x += self.vx * dt
        self.y += self.vy * dt


# ═══════════════════════════════════════════════
# 2. 玩家角色
# ═══════════════════════════════════════════════

class Player(GameObject):
    """玩家角色"""
    def __init__(self, x, y):
        super().__init__(x, y, 60, 40)
        self.speed = 300  # 像素/秒
        self.lives = 3
        self.score = 0
        self.invincible = False  # 无敌状态
        self.invincible_timer = 0
    
    def move_left(self):
        self.vx = -self.speed
    
    def move_right(self):
        self.vx = self.speed
    
    def stop(self):
        self.vx = 0
    
    def update(self, dt):
        super().update(dt)
        # 更新无敌状态
        if self.invincible:
            self.invincible_timer -= dt
            if self.invincible_timer <= 0:
                self.invincible = False
    
    def hit(self):
        """被击中"""
        if self.invincible:
            return False
        self.lives -= 1
        self.invincible = True
        self.invincible_timer = 2.0  # 2秒无敌
        return True
    
    def draw(self):
        """绘制玩家"""
        if self.invincible and int(time.time() * 10) % 2 == 0:
            return ""  # 闪烁效果
        return f"🚀 [{self.lives}❤️] 得分:{self.score}"


# ═══════════════════════════════════════════════
# 3. 敌人
# ═══════════════════════════════════════════════

class Enemy(GameObject):
    """敌人"""
    def __init__(self, x, y, enemy_type="basic"):
        super().__init__(x, y, 40, 30)
        self.enemy_type = enemy_type
        self.health = 1
        
        # 根据类型设置属性
        if enemy_type == "basic":
            self.vy = 100  # 向下移动
            self.health = 1
        elif enemy_type == "fast":
            self.vy = 200
            self.health = 1
        elif enemy_type == "tank":
            self.vy = 50
            self.health = 3
    
    def draw(self):
        """绘制敌人"""
        icons = {"basic": "👾", "fast": "👾", "tank": "🤖"}
        return icons.get(self.enemy_type, "👾")
    
    def take_damage(self):
        """受到伤害"""
        self.health -= 1
        if self.health <= 0:
            self.active = False
            return True
        return False


# ═══════════════════════════════════════════════
# 4. 子弹
# ═══════════════════════════════════════════════

class Bullet(GameObject):
    """子弹"""
    def __init__(self, x, y, direction="up"):
        super().__init__(x, y, 8, 12)
        self.speed = 500
        
        if direction == "up":
            self.vy = -self.speed
        elif direction == "down":
            self.vy = self.speed
    
    def draw(self):
        return "│"


# ═══════════════════════════════════════════════
# 5. 碰撞检测管理器
# ═══════════════════════════════════════════════

class CollisionManager:
    """碰撞检测管理器"""
    
    @staticmethod
    def aabb_collision(obj_a, obj_b):
        """AABB 碰撞检测"""
        return (
            obj_a.left < obj_b.right and
            obj_a.right > obj_b.left and
            obj_a.top < obj_b.bottom and
            obj_a.bottom > obj_b.top
        )
    
    @staticmethod
    def circle_collision(obj_a, obj_b):
        """圆形碰撞检测"""
        dx = obj_a.center_x - obj_b.center_x
        dy = obj_a.center_y - obj_b.center_y
        distance = math.sqrt(dx * dx + dy * dy)
        radius_a = max(obj_a.width, obj_a.height) / 2
        radius_b = max(obj_b.width, obj_b.height) / 2
        return distance <= (radius_a + radius_b)
    
    @staticmethod
    def check_bullet_enemy(bullet, enemy):
        """子弹-敌人碰撞"""
        if not bullet.active or not enemy.active:
            return False
        return CollisionManager.aabb_collision(bullet, enemy)
    
    @staticmethod
    def check_enemy_player(enemy, player):
        """敌人-玩家碰撞"""
        if not enemy.active or not player.active:
            return False
        if player.invincible:
            return False
        return CollisionManager.aabb_collision(enemy, player)


# ═══════════════════════════════════════════════
# 6. 粒子效果
# ═══════════════════════════════════════════════

class Particle:
    """粒子"""
    def __init__(self, x, y, vx, vy, lifetime=1.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.active = True
    
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 200 * dt  # 重力
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False
    
    @property
    def alpha(self):
        """透明度 (0-1)"""
        return self.lifetime / self.max_lifetime


class ParticleSystem:
    """粒子系统"""
    def __init__(self):
        self.particles = []
    
    def emit(self, x, y, count=10, color="💥"):
        """发射粒子"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 200)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            lifetime = random.uniform(0.5, 1.5)
            self.particles.append(Particle(x, y, vx, vy, lifetime))
    
    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.active]


# ═══════════════════════════════════════════════
# 7. 游戏主循环
# ═══════════════════════════════════════════════

class Game:
    """弹球游戏"""
    def __init__(self, width=80, height=25):
        self.width = width
        self.height = height
        self.player = Player(width // 2 - 30, height - 4)
        self.bullets = []
        self.enemies = []
        self.particles = ParticleSystem()
        self.running = True
        self.game_over = False
        self.spawn_timer = 0
        self.total_time = 0
        self.frame_count = 0
        
        # 动画相关
        self.shake_timer = 0
        self.flash_timer = 0
    
    def spawn_enemy(self):
        """生成敌人"""
        x = random.randint(5, self.width - 45)
        enemy_type = random.choice(["basic", "basic", "fast", "tank"])
        self.enemies.append(Enemy(x, -5, enemy_type))
    
    def fire_bullet(self):
        """发射子弹"""
        bullet = Bullet(
            self.player.center_x - 4,
            self.player.y - 12,
            "up"
        )
        self.bullets.append(bullet)
    
    def check_collisions(self):
        """检查所有碰撞"""
        # 子弹 vs 敌人
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if CollisionManager.check_bullet_enemy(bullet, enemy):
                    bullet.active = False
                    if enemy.take_damage():
                        # 敌人被消灭
                        self.player.score += {"basic": 10, "fast": 20, "tank": 50}[enemy.enemy_type]
                        self.particles.emit(enemy.center_x, enemy.center_y, 8)
                        self.shake_timer = 0.1
                    else:
                        self.particles.emit(bullet.center_x, bullet.center_y, 3)
                    break
        
        # 敌人 vs 玩家
        for enemy in self.enemies[:]:
            if CollisionManager.check_enemy_player(enemy, player=self.player):
                if self.player.hit():
                    self.flash_timer = 0.2
                    self.shake_timer = 0.15
                    self.particles.emit(self.player.center_x, self.player.center_y, 15)
                    if self.player.lives <= 0:
                        self.game_over = True
                enemy.active = False
        
        # 清理
        self.bullets = [b for b in self.bullets if b.active]
        self.enemies = [e for e in self.enemies if e.active]
    
    def update(self, dt):
        """更新游戏逻辑"""
        if self.game_over:
            return
        
        self.total_time += dt
        self.frame_count += 1
        
        # 更新对象
        self.player.update(dt)
        for bullet in self.bullets:
            bullet.update(dt)
        for enemy in self.enemies:
            enemy.update(dt)
        
        # 限制玩家在屏幕内
        self.player.x = max(0, min(self.width - self.player.width, self.player.x))
        
        # 移除出屏子弹
        self.bullets = [b for b in self.bullets if b.y > -20]
        
        # 移除出屏敌人
        self.enemies = [e for e in self.enemies if e.y < self.height + 20]
        
        # 生成敌人
        self.spawn_timer += dt
        spawn_interval = max(0.5, 2.0 - self.total_time / 30)  # 越来越快
        if self.spawn_timer >= spawn_interval:
            self.spawn_timer = 0
            self.spawn_enemy()
        
        # 自动射击
        if random.random() < 0.3:  # 30% 概率射击
            self.fire_bullet()
        
        # 检查碰撞
        self.check_collisions()
        
        # 更新粒子
        self.particles.update(dt)
        
        # 更新特效计时器
        self.shake_timer = max(0, self.shake_timer - dt)
        self.flash_timer = max(0, self.flash_timer - dt)
    
    def render(self):
        """渲染游戏画面"""
        # 创建画布
        canvas = [[" " for _ in range(self.width)] for _ in range(self.height)]
        
        # 绘制边界
        for x in range(self.width):
            canvas[0][x] = "─"
            canvas[self.height - 1][x] = "─"
        for y in range(self.height):
            canvas[y][0] = "│"
            canvas[y][self.width - 1] = "│"
        canvas[0][0] = "┌"
        canvas[0][self.width - 1] = "┐"
        canvas[self.height - 1][0] = "└"
        canvas[self.height - 1][self.width - 1] = "┘"
        
        # 绘制玩家
        px = int(self.player.x)
        py = int(self.player.y)
        if not (self.flash_timer > 0 and int(time.time() * 20) % 2 == 0):
            player_str = "🚀"
            for i, ch in enumerate(player_str):
                if px + i < self.width - 1:
                    canvas[py][px + i] = ch
        
        # 绘制子弹
        for bullet in self.bullets:
            bx, by = int(bullet.x), int(bullet.y)
            if 0 < bx < self.width - 1 and 0 < by < self.height - 1:
                canvas[by][bx] = "│"
        
        # 绘制敌人
        for enemy in self.enemies:
            ex, ey = int(enemy.x), int(enemy.y)
            if 0 < ex < self.width - 2 and 0 < ey < self.height - 1:
                icons = {"basic": "👾", "fast": "⚡", "tank": "🤖"}
                icon = icons.get(enemy.enemy_type, "👾")
                canvas[ey][ex] = icon[0] if ex < self.width - 1 else " "
                if ex + 1 < self.width - 1:
                    canvas[ey][ex + 1] = icon[1] if len(icon) > 1 else " "
        
        # 绘制粒子
        for p in self.particles.particles:
            px, py = int(p.x), int(p.y)
            if 0 < px < self.width - 1 and 0 < py < self.height - 1:
                canvas[py][px] = "✦" if p.alpha > 0.5 else "·"
        
        # 转换为字符串
        lines = ["".join(row) for row in canvas]
        
        # 添加 HUD
        hud = f" ❤️:{self.player.lives} ⭐:{self.player.score} ⏱️:{self.total_time:.1f}s"
        lines.insert(1, f"│{hud:<{self.width-2}}│")
        
        # 渲染画面
        print("\033[2J\033[H")  # 清屏
        print("\n".join(lines))
        
        # 状态信息
        if self.game_over:
            print(f"\n  💀 GAME OVER! 最终得分: {self.player.score}")
            print(f"  存活时间: {self.total_time:.1f}秒")
            print(f"  消灭敌人: {self.player.score // 10}")


# ═══════════════════════════════════════════════
# 8. 模拟运行（非交互式演示）
# ═══════════════════════════════════════════════

def demo_mode():
    """演示模式: 自动运行几秒展示游戏效果"""
    print("=" * 60)
    print("  Day 090 — 实战: 弹球游戏演示")
    print("=" * 60)
    print()
    print("  游戏特性:")
    print("  • AABB 碰撞检测 (子弹-敌人, 敌人-玩家)")
    print("  • 粒子爆炸效果")
    print("  • 玩家无敌闪烁动画")
    print("  • 敌人生成节奏递增")
    print("  • 得分系统")
    print()
    print("  模拟运行中...")
    print()
    
    game = Game(width=60, height=20)
    dt = 1.0 / 30  # 30 FPS
    
    for frame in range(150):  # 模拟 5 秒
        game.update(dt)
        game.render()
        time.sleep(0.05)  # 实际会更快，这里减速展示
        
        if game.game_over:
            break
    
    # 最终统计
    print(f"\n{'=' * 60}")
    print(f"  📊 游戏统计:")
    print(f"  • 存活时间: {game.total_time:.1f}秒")
    print(f"  • 最终得分: {game.player.score}")
    print(f"  • 渲染帧数: {game.frame_count}")
    print(f"  • 活跃粒子: {len(game.particles.particles)}")
    print(f"  • 碰撞检测: AABB")
    print(f"{'=' * 60}")
    
    # 演示碰撞检测
    print(f"\n  💥 碰撞检测演示:")
    p1 = GameObject(10, 10, 20, 20)
    p2 = GameObject(25, 15, 20, 20)
    p3 = GameObject(50, 50, 20, 20)
    
    print(f"  物体A: ({p1.x},{p1.y}) 大小 {p1.width}x{p1.height}")
    print(f"  物体B: ({p2.x},{p2.y}) 大小 {p2.width}x{p2.height}")
    print(f"  物体C: ({p3.x},{p3.y}) 大小 {p3.width}x{p3.height}")
    print(f"  A vs B: {CollisionManager.aabb_collision(p1, p2)}")
    print(f"  A vs C: {CollisionManager.aabb_collision(p1, p3)}")


if __name__ == "__main__":
    demo_mode()
