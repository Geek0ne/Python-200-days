"""
Day 088 - 进阶用法：精灵系统与碰撞检测
======================================

学习目标：
- 使用 pygame.sprite.Sprite 创建游戏对象
- 理解精灵组（Group）的管理机制
- 实现基本的碰撞检测
- 持续按键检测（不同于事件检测）

运行方式：
    python3 02-精灵与碰撞检测.py
"""

import pygame
import sys
import random

# 初始化
pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Day 088 - 精灵与碰撞检测")
clock = pygame.time.Clock()

# 颜色
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 50, 255)
YELLOW = (255, 255, 0)


# ==================== 玩家精灵 ====================
class Player(pygame.sprite.Sprite):
    """玩家精灵：通过键盘控制移动"""
    
    def __init__(self):
        super().__init__()
        
        # 创建玩家外观：一个蓝色方块
        self.image = pygame.Surface((50, 50))
        self.image.fill(BLUE)
        
        # rect 用于定位和碰撞检测
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        
        # 移动速度（像素/帧）
        self.speed = 5
    
    def update(self):
        """
        持续按键检测 vs 事件检测：
        
        事件检测（event.type == pygame.KEYDOWN）：
        - 只在按键按下的瞬间触发一次
        - 适合：跳跃、射击、暂停等"按一次"的操作
        
        持续按键检测（pygame.key.get_pressed()）：
        - 只要按键按住，每帧都返回 True
        - 适合：移动、持续加速等"按住不动"的操作
        """
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.rect.y += self.speed
        
        # 边界限制：确保玩家不会移出屏幕
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))


# ==================== 敌人精灵 ====================
class Enemy(pygame.sprite.Sprite):
    """敌人精灵：随机出现在屏幕上"""
    
    def __init__(self):
        super().__init__()
        
        self.image = pygame.Surface((30, 30))
        self.image.fill(RED)
        
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, WIDTH - 30)
        self.rect.y = random.randint(0, HEIGHT - 30)
    
    def update(self):
        # 敌人不移动（后续课程会添加移动逻辑）
        pass


# ==================== 碰撞检测演示 ====================
def check_collision_demo(player, enemies):
    """
    pygame 提供了几种碰撞检测函数：
    
    1. spritecollide(sprite, group, dokill)
       - 检测一个精灵与一组精灵的碰撞
       - 返回碰撞到的精灵列表
       - dokill=True 会删除碰撞到的精灵
    
    2. groupcollide(group1, group2, dokill1, dokill2)
       - 检测两组精灵之间的碰撞
       - 返回 {sprite1: [sprite2, ...]} 字典
    """
    # 检测玩家与所有敌人的碰撞
    hits = pygame.sprite.spritecollide(player, enemies, False)
    
    if hits:
        # hits 是一个列表，包含所有与玩家碰撞的敌人
        for enemy in hits:
            # 这里可以处理碰撞逻辑（扣血、得分等）
            pass
        return True
    return False


# ==================== 主函数 ====================
def main():
    # 创建精灵组
    all_sprites = pygame.sprite.Group()  # 所有精灵
    enemies = pygame.sprite.Group()      # 仅敌人
    
    # 创建玩家
    player = Player()
    all_sprites.add(player)
    
    # 创建一些敌人
    for _ in range(8):
        enemy = Enemy()
        all_sprites.add(enemy)
        enemies.add(enemy)
    
    # 字体
    font = pygame.font.Font(None, 36)
    
    score = 0
    collision_count = 0
    
    running = True
    while running:
        # ---- 事件处理 ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # 空格键：重置玩家位置
                    player.rect.center = (WIDTH // 2, HEIGHT // 2)
        
        # ---- 更新所有精灵 ----
        # 调用每个精灵的 update() 方法
        all_sprites.update()
        
        # ---- 碰撞检测 ----
        if check_collision_demo(player, enemies):
            collision_count += 1
        
        # ---- 渲染 ----
        screen.fill(BLACK)
        
        # 绘制所有精灵
        all_sprites.draw(screen)
        
        # 显示信息
        info_texts = [
            f"FPS: {clock.get_fps():.0f}",
            f"精灵数量: {len(all_sprites)}",
            f"碰撞次数: {collision_count}",
            "",
            "WASD/方向键: 移动玩家",
            "空格: 重置位置",
            "ESC: 退出",
        ]
        
        for i, text in enumerate(info_texts):
            if text:  # 跳过空行
                surface = font.render(text, True, WHITE)
                screen.blit(surface, (10, 10 + i * 28))
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
