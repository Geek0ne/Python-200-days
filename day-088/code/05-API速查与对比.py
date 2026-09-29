"""
Day 088 - API 速查与对比
========================

这个文件是 Day 088 所有核心 API 的速查手册。
可以直接运行查看效果，也可以作为参考文档阅读。

运行方式：
    python3 05-API速查与对比.py
"""

import pygame
import sys

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Day 088 - API 速查与对比")
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 50, 255)
YELLOW = (255, 255, 0)


def demo_display_api():
    """演示 display 模块 API"""
    # 设置窗口大小（运行时动态改变）
    # screen = pygame.display.set_mode((1024, 768))
    
    # 设置窗口标题
    pygame.display.set_caption("新标题")
    
    # 更新显示
    # pygame.display.flip()     # 更新整个屏幕
    # pygame.display.update()    # 更新整个屏幕（或指定区域）
    # pygame.display.update([rect1, rect2])  # 只更新指定区域（更高效）
    
    # 获取显示信息
    info = pygame.display.Info()
    print(f"显示器分辨率: {info.current_w}x{info.current_h}")
    print(f"窗口大小: {screen.get_size()}")


def demo_event_api():
    """演示事件处理 API"""
    # 方式 1：获取所有事件
    events = pygame.event.get()
    # 返回 Event 列表，用完即清
    
    # 方式 2：获取一个事件（非阻塞）
    event = pygame.event.poll()
    # 返回一个 Event，如果没有则返回 NOEVENT
    
    # 方式 3：等待事件（阻塞）
    # event = pygame.event.wait()  # 会阻塞直到有事件
    
    # 事件属性
    # event.type  — 事件类型（如 pygame.KEYDOWN）
    # event.key   — 按键代码（KEYDOWN/KEYUP 时可用）
    # event.pos   — 鼠标位置（MOUSE 事件时可用）
    # event.button — 鼠标按钮（MOUSEBUTTONDOWN/UP 时可用）
    
    # 持续按键检测（不同于事件检测）
    keys = pygame.key.get_pressed()
    # 返回一个布尔数组，索引是 K_LEFT, K_RIGHT 等
    # 按住时每帧都返回 True
    
    # 鼠标状态
    mouse_pos = pygame.mouse.get_pos()      # (x, y) 当前位置
    mouse_pressed = pygame.mouse.get_pressed()  # (左, 中, 右) 按钮状态


def demo_draw_api():
    """演示绘制 API"""
    # 矩形
    pygame.draw.rect(screen, RED, (10, 50, 100, 60))           # 填充
    pygame.draw.rect(screen, GREEN, (120, 50, 100, 60), 3)     # 边框（width=3）
    
    # 圆形
    pygame.draw.circle(screen, BLUE, (300, 80), 40)            # 填充
    pygame.draw.circle(screen, YELLOW, (400, 80), 40, 3)       # 边框
    
    # 线段
    pygame.draw.line(screen, WHITE, (10, 150), (500, 150), 2)  # 宽度 2
    
    # 多条线（抗锯齿）
    pygame.draw.aaline(screen, WHITE, (10, 170), (500, 170))
    
    # 多边形
    points = [(600, 50), (650, 150), (550, 150)]
    pygame.draw.polygon(screen, RED, points)  # 三角形
    
    # 圆弧
    pygame.draw.arc(screen, GREEN, (10, 200, 100, 100), 0, 3.14, 2)


def demo_sprite_api():
    """演示精灵系统 API"""
    # 创建精灵
    # class MySprite(pygame.sprite.Sprite):
    #     def __init__(self):
    #         super().__init__()
    #         self.image = pygame.Surface((50, 50))
    #         self.image.fill(RED)
    #         self.rect = self.image.get_rect()
    #     
    #     def update(self):
    #         self.rect.x += 1
    
    # 精灵组操作
    # group = pygame.sprite.Group()
    # group.add(sprite)          # 添加单个精灵
    # group.add(s1, s2, s3)     # 添加多个精灵
    # group.remove(sprite)       # 移除精灵
    # group.update()             # 调用所有精灵的 update()
    # group.draw(surface)        # 绘制所有精灵
    # group.empty()              # 清空组
    # len(group)                 # 获取精灵数量
    
    # 碰撞检测
    # hits = pygame.sprite.spritecollide(sprite, group, False)
    #   返回与 sprite 碰撞的 group 中的精灵列表
    #   False = 不删除碰撞到的精灵
    #   True = 删除碰撞到的精灵
    
    # hits = pygame.sprite.groupcollide(g1, g2, False, True)
    #   返回 {sprite_from_g1: [sprites_from_g2]}
    #   第二个 False = 不删除 g1 中的精灵
    #   最后一个 True = 删除 g2 中的精灵


def demo_time_api():
    """演示时间 API"""
    # 时钟
    # clock = pygame.time.Clock()
    # clock.tick(60)         # 限制 60 FPS
    # actual_fps = clock.get_fps()  # 获取实际 FPS
    
    # 时间函数
    # ticks = pygame.time.get_ticks()  # 程序启动后的毫秒数
    
    # 定时器事件
    # pygame.time.set_timer(EVENT_TYPE, interval_ms)
    # 每隔 interval_ms 毫秒触发一次自定义事件


def demo_image_api():
    """演示图片 API"""
    # 加载图片
    # image = pygame.image.load("path/to/image.png")
    # 
    # 转换格式（提高绘制性能）
    # image = image.convert()        # 无透明通道
    # image = image.convert_alpha()  # 有透明通道（PNG）
    #
    # 缩放
    # image = pygame.transform.scale(image, (64, 64))
    # image = pygame.transform.smoothscale(image, (64, 64))  # 平滑缩放
    #
    # 旋转
    # image = pygame.transform.rotate(image, 45)  # 逆时针旋转 45°
    #
    # 翻转
    # image = pygame.transform.flip(image, True, False)  # 水平翻转
    pass


def main():
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 28)
    
    running = True
    frame = 0
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        frame += 1
        
        screen.fill(BLACK)
        
        # 绘制一些 API 示例图形
        demo_draw_api()
        
        # 显示信息
        info = [
            "Day 088 - Pygame API 速查",
            f"FPS: {clock.get_fps():.0f}",
            "",
            "按方向键移动绿色方块测试持续检测",
        ]
        
        for i, text in enumerate(info):
            if text:
                surface = font.render(text, True, WHITE)
                screen.blit(surface, (10, 350 + i * 30))
        
        # 持续按键检测演示
        keys = pygame.key.get_pressed()
        x, y = 400, 450
        if keys[pygame.K_LEFT]:  x -= 5
        if keys[pygame.K_RIGHT]: x += 5
        if keys[pygame.K_UP]:    y -= 5
        if keys[pygame.K_DOWN]:  y += 5
        x = max(0, min(WIDTH - 30, x))
        y = max(0, min(HEIGHT - 30, y))
        pygame.draw.rect(screen, GREEN, (x, y, 30, 30))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
