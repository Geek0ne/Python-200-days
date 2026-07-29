"""
Day 088 - 常见陷阱与避坑指南
============================

这个文件演示了 Pygame 初学者常犯的错误，以及正确的做法。
每个错误都附有注释说明。

运行方式：
    python3 04-常见陷阱避坑.py
"""

import pygame
import sys

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Day 088 - 常见陷阱避坑指南")
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


# ============================================================
# 陷阱 1：忘记初始化
# ============================================================
# 错误写法：
# screen = pygame.display.set_mode((800, 600))  # 直接用会报错
#
# 正确写法：
# pygame.init()  # 必须先初始化
# screen = pygame.display.set_mode((800, 600))
#
# 说明：pygame.init() 初始化 display, font, mixer 等所有模块
# 如果不调用，某些功能会报 AttributeError


# ============================================================
# 陷阱 2：事件只获取一次
# ============================================================
# 错误写法：
# events = pygame.event.get()  # 在循环外获取
# while running:
#     for event in events:  # 永远是同一批事件！
#         ...
#
# 正确写法（在循环内每帧获取）：
# while running:
#     for event in pygame.event.get():  # 每帧重新获取
#         ...
#
# 说明：pygame.event.get() 会清空事件队列
# 只获取一次意味着后续帧再也收不到新事件


# ============================================================
# 陷阱 3：混淆 fill 和 blit 的顺序
# ============================================================
# 错误写法：
# screen.blit(player_image, (100, 100))  # 先画玩家
# screen.fill(BLACK)  # 再清屏 —— 把玩家覆盖了！
#
# 正确写法：
# screen.fill(BLACK)  # 先清屏
# screen.blit(player_image, (100, 100))  # 再画玩家
#
# 说明：fill 会覆盖整个屏幕
# 必须在绘制任何内容之前调用 fill


# ============================================================
# 陷阱 4：不用 clock.tick 控制帧率
# ============================================================
# 错误写法：
# while running:
#     # 游戏逻辑...
#     pygame.display.flip()
#     # 没有 tick！在快电脑上跑得飞快，慢电脑上跑得慢
#
# 正确写法：
# while running:
#     # 游戏逻辑...
#     pygame.display.flip()
#     clock.tick(60)  # 限制 60 FPS
#
# 说明：tick 会根据处理时间自动等待
# 确保游戏在不同性能的电脑上体验一致


# ============================================================
# 陷阱 5：修改 rect 后不做边界检查
# ============================================================
# 错误写法：
# self.rect.x += self.vx  # 可能移出屏幕
#
# 正确写法：
# self.rect.x += self.vx
# if self.rect.left < 0:
#     self.rect.left = 0
#     self.vx = -self.vx  # 反弹
#
# 说明：不检查边界，精灵会飞出屏幕"消失"
# 用 clamp_ip() 也能快速实现边界限制：
# self.rect.clamp_ip(screen.get_rect())


# ============================================================
# 陷阱 6：忘记退出清理
# ============================================================
# 错误写法：
# sys.exit()  # 直接退出，可能资源泄露
#
# 正确写法：
# pygame.quit()  # 先释放 Pygame 资源
# sys.exit()
#
# 说明：pygame.quit() 会关闭音频设备、释放显示资源等
# 虽然进程退出时 OS 会回收，但显式清理是好习惯


# ============================================================
# 演示：带边界检查的安全移动
# ============================================================
class SafeBall:
    """演示如何正确处理边界"""
    
    def __init__(self):
        self.x = 400.0
        self.y = 300.0
        self.radius = 20
        self.vx = 4.0
        self.vy = 3.0
    
    def update(self):
        # 先移动
        self.x += self.vx
        self.y += self.vy
        
        # 再检查边界并反弹
        if self.x - self.radius <= 0:
            self.x = self.radius
            self.vx = abs(self.vx)
        elif self.x + self.radius >= WIDTH:
            self.x = WIDTH - self.radius
            self.vx = -abs(self.vx)
        
        if self.y - self.radius <= 0:
            self.y = self.radius
            self.vy = abs(self.vy)
        elif self.y + self.radius >= HEIGHT:
            self.y = HEIGHT - self.radius
            self.vy = -abs(self.vy)
    
    def draw(self, surface):
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius)


# ==================== 主循环 ====================
def main():
    ball = SafeBall()
    font = pygame.font.Font(None, 36)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        ball.update()
        
        screen.fill(BLACK)
        ball.draw(screen)
        
        info = font.render("安全弹跳小球 - 注意边界处理", True, WHITE)
        screen.blit(info, (10, 10))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
