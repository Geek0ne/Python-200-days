#!/usr/bin/env python3
"""
Day 089 — 游戏循环与事件：常见陷阱与避坑指南
列出游戏循环开发中最常犯的错误及解决方案。
运行此文件会在终端输出所有陷阱说明。
"""

import textwrap


def print_trap(num, title, problem, solution, code_bad="", code_good=""):
    """打印一个陷阱说明"""
    print(f"\n{'='*60}")
    print(f"⚠️  陷阱 #{num}: {title}")
    print(f"{'='*60}")
    print(f"\n❌ 问题：")
    print(textwrap.indent(problem, "  "))
    print(f"\n✅ 解决：")
    print(textwrap.indent(solution, "  "))
    if code_bad:
        print(f"\n❌ 错误写法：")
        for line in code_bad.strip().split("\n"):
            print(f"    {line}")
    if code_good:
        print(f"\n✅ 正确写法：")
        for line in code_good.strip().split("\n"):
            print(f"    {line}")


def main():
    print("🐍 Day 089 — 游戏循环与事件：常见陷阱与避坑")
    print("=" * 60)

    # 陷阱 1
    print_trap(
        1,
        "忘记调用 pygame.quit()",
        "程序退出时不调用 pygame.quit()，可能导致残留进程、\n"
        "资源未释放，甚至在某些系统上导致段错误。",
        "在游戏循环结束后务必调用 pygame.quit()，\n"
        "最好再加 sys.exit() 确保程序完全退出。",
        code_good='''pygame.quit()
sys.exit()'''
    )

    # 陷阱 2
    print_trap(
        2,
        "事件循环和状态更新混在一起",
        "在事件处理中直接修改游戏状态（如移动玩家），\n"
        "会导致同一帧内事件处理和状态更新的顺序不确定，\n"
        "出现难以调试的 bug。",
        "事件循环只做"标记"或"记录意图"，\n"
        "实际状态更新统一放在 update() 阶段。",
        code_bad='''for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
        player.x -= 10  # 直接改状态！''',
        code_good='''# 事件阶段：只记录意图
for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
        player.move_left = True

# 更新阶段：统一处理
if player.move_left:
    player.x -= player.speed'''
    )

    # 陷阱 3
    print_trap(
        3,
        "set_timer 同一事件类型只能有一个定时器",
        "对同一个 USEREVENT+N 多次调用 set_timer，\n"
        "后面的会覆盖前面的，不会叠加。",
        "为每个定时器分配不同的 USEREVENT+N。",
        code_bad='''# ❌ 第二个覆盖了第一个
pygame.time.set_timer(MY_EVENT, 1000)
pygame.time.set_timer(MY_EVENT, 2000)  # 覆盖！''',
        code_good='''# ✅ 用不同的事件类型
TIMER_A = pygame.USEREVENT + 1
TIMER_B = pygame.USEREVENT + 2
pygame.time.set_timer(TIMER_A, 1000)
pygame.time.set_timer(TIMER_B, 2000)'''
    )

    # 陷阱 4
    print_trap(
        4,
        "不用 Clock.tick() 导致 CPU 满载",
        "游戏循环中不调用 clock.tick()，\n"
        "循环会以 CPU 极限速度运行，\n"
        "导致 CPU 占用 100%，风扇狂转。",
        "每帧末尾必须调用 clock.tick(fps) 来限制帧率，\n"
        "让 CPU 有时间休息。",
        code_bad='''while running:
    # ... 游戏逻辑 ...
    # 没有 clock.tick()！CPU 空转！''',
        code_good='''while running:
    # ... 游戏逻辑 ...
    clock.tick(60)  # 限制 60 FPS'''
    )

    # 陷阱 5
    print_trap(
        5,
        "KEYDOWN 和 get_pressed 用错场景",
        "用 get_pressed() 处理"按一次触发一次"的动作（如跳跃），\n"
        "会导致每帧都触发，角色无限连跳。\n"
        "反过来用 KEYDOWN 处理持续移动，只能移动一小段。",
        "一次性动作（跳跃、射击）→ KEYDOWN\n"
        "持续动作（移动）→ get_pressed()",
        code_bad='''# ❌ 每帧都跳跃
keys = pygame.key.get_pressed()
if keys[pygame.K_SPACE]:
    player.jump()  # 每帧都跳！''',
        code_good='''# ✅ 按下瞬间跳一次
for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_SPACE:
            player.jump()'''
    )

    # 陷阱 6
    print_trap(
        6,
        "在事件循环中做耗时操作",
        "在 for event 循环中做路径规划、加载文件、\n"
        "网络请求等耗时操作，会导致帧率骤降、卡顿。",
        "事件循环只做最轻量的操作（设置标志位）。\n"
        "耗时操作放在 update() 或单独的线程中。",
        code_bad='''for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
        path = a_star(start, goal)  # 耗时！''',
        code_good='''for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
        need_pathfinding = True  # 只标记

# 在 update 中处理
if need_pathfinding:
    path = a_star(start, goal)'''
    )

    # 陷阱 7
    print_trap(
        7,
        "不处理 pygame.event.get() 导致窗口无响应",
        "如果一帧内不调用 pygame.event.get()，\n"
        "事件队列会堆积，操作系统认为程序无响应，\n"
        "弹出"未响应"对话框。",
        "每一帧都必须调用 pygame.event.get()，\n"
        "即使你不需要处理任何事件。",
        code_bad='''while running:
    # 假设这一帧不需要处理输入
    # 忘记调用 event.get() 了！
    update()
    render()''',
        code_good='''while running:
    for event in pygame.event.get():  # 每帧都要调用！
        if event.type == pygame.QUIT:
            running = False
    update()
    render()'''
    )

    # 陷阱 8
    print_trap(
        8,
        "display.flip() 和 display.update() 混用",
        "flip() 重绘整个屏幕，update() 可以只重绘部分区域。\n"
        "对于简单游戏用 flip() 就够了，\n"
        "对于复杂场景可以用 update(rects) 优化性能。",
        "初学者用 flip() 即可。\n"
        "需要性能优化时再考虑 update(dirty_rects)。",
        code_good='''# 简单用法
pygame.display.flip()

# 优化用法（脏矩形渲染）
dirty = [player.rect, enemy.rect]
pygame.display.update(dirty)'''
    )

    print(f"\n{'='*60}")
    print("💡 记住：游戏开发中 80% 的 bug 都来自游戏循环的顺序问题")
    print("   输入 → 更新 → 渲染 → 帧率控制，顺序不能乱！")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
