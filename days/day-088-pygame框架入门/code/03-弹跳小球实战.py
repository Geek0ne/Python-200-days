"""
Day 088 - 实战案例：弹跳小球游戏
================================

学习目标：
- 综合运用所有 Day 088 学到的知识
- 实现一个完整的小游戏
- 理解游戏状态管理
- 掌握随机数在游戏中的应用

运行方式：
    python3 03-弹跳小球实战.py
"""

import pygame
import sys
import random
import math

# ==================== 初始化 ====================
pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Day 088 - 弹跳小球")
clock = pygame.time.Clock()

# 颜色
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 80, 80)
GREEN = (80, 255, 80)
BLUE = (80, 80, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)


# ==================== 小球精灵 ====================
class Ball(pygame.sprite.Sprite):
    """一个会弹跳的小球"""
    
    def __init__(self):
        super().__init__()
        
        self.radius = random.randint(15, 30)
        # 创建带透明通道的 Surface
        self.image = pygame.Surface(
            (self.radius * 2, self.radius * 2),
            pygame.SRCALPHA
        )
        
        # 随机颜色
        self.color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255),
        )
        
        pygame.draw.circle(
            self.image,
            self.color,
            (self.radius, self.radius),
            self.radius
        )
        
        self.rect = self.image.get_rect()
        
        # 随机初始位置
        self.rect.x = random.randint(0, WIDTH - self.radius * 2)
        self.rect.y = random.randint(0, HEIGHT - self.radius * 2)
        
        # 随机速度
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
    
    def update(self):
        # 移动
        self.rect.x += self.vx
        self.rect.y += self.vy
        
        # 碰到边界反弹
        if self.rect.left <= 0:
            self.rect.left = 0
            self.vx = abs(self.vx)
        elif self.rect.right >= WIDTH:
            self.rect.right = WIDTH
            self.vx = -abs(self.vx)
        
        if self.rect.top <= 0:
            self.rect.top = 0
            self.vy = abs(self.vy)
        elif self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.vy = -abs(self.vy)


# ==================== 粒子效果 ====================
class Particle(pygame.sprite.Sprite):
    """碰撞时产生的粒子"""
    
    def __init__(self, x, y, color):
        super().__init__()
        self.size = random.randint(2, 6)
        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        self.image.fill((*color, 200))
        self.rect = self.image.get_rect(center=(x, y))
        
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 4)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        
        self.life = random.randint(20, 40)  # 帧数
    
    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.life -= 1
        
        if self.life <= 0:
            self.kill()  # 从所有精灵组中移除


# ==================== 主游戏 ====================
def main():
    # 精灵组
    all_sprites = pygame.sprite.Group()
    balls = pygame.sprite.Group()
    particles = pygame.sprite.Group()
    
    # 字体
    font_large = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 30)
    
    # 游戏状态
    score = 0
    game_over = False
    
    # 创建初始小球
    for _ in range(5):
        ball = Ball()
        all_sprites.add(ball)
        balls.add(ball)
    
    running = True
    while running:
        # ---- 事件处理 ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    # 重新开始
                    all_sprites.empty()
                    balls.empty()
                    particles.empty()
                    score = 0
                    game_over = False
                    for _ in range(5):
                        ball = Ball()
                        all_sprites.add(ball)
                        balls.add(ball)
                elif event.key == pygame.K_SPACE and not game_over:
                    # 空格键：添加新球
                    ball = Ball()
                    all_sprites.add(ball)
                    balls.add(ball)
                    score += 1
            
            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                # 鼠标点击：在点击位置添加小球
                ball = Ball()
                ball.rect.center = event.pos
                all_sprites.add(ball)
                balls.add(ball)
                score += 1
        
        # ---- 更新 ----
        all_sprites.update()
        
        # 粒子碰撞检测（小球之间）
        ball_list = balls.sprites()
        for i in range(len(ball_list)):
            for j in range(i + 1, len(ball_list)):
                b1, b2 = ball_list[i], ball_list[j]
                if b1.rect.colliderect(b2.rect):
                    # 简单的弹性碰撞
                    b1.vx, b2.vx = b2.vx, b1.vx
                    b1.vy, b2.vy = b2.vy, b1.vy
                    
                    # 产生粒子效果
                    mid_x = (b1.rect.centerx + b2.rect.centerx) // 2
                    mid_y = (b1.rect.centery + b2.rect.centery) // 2
                    for _ in range(8):
                        p = Particle(mid_x, mid_y, WHITE)
                        all_sprites.add(p)
                        particles.add(p)
        
        # ---- 渲染 ----
        screen.fill(BLACK)
        
        # 绘制背景网格
        for x in range(0, WIDTH, 50):
            pygame.draw.line(screen, (20, 20, 20), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 50):
            pygame.draw.line(screen, (20, 20, 20), (0, y), (WIDTH, y))
        
        # 绘制所有精灵
        all_sprites.draw(screen)
        
        # HUD 信息
        score_text = font_large.render(f"小球: {len(balls)}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        controls = [
            "空格/鼠标点击: 添加小球",
            "R: 重新开始",
            "ESC: 退出",
        ]
        for i, text in enumerate(controls):
            surface = font_small.render(text, True, GRAY)
            screen.blit(surface, (10, HEIGHT - 80 + i * 24))
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
