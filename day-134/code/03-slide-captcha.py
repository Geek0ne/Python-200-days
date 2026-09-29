#!/usr/bin/env python3
"""
03 - 滑块验证码：缺口检测 + 人手轨迹生成（实战案例）
====================================================
演示完整滑块处理流程（纯算法层，浏览器执行部分用伪代码标注）：
1. ddddocr.slide_match 定位缺口 x 坐标
2. 生成"先快后慢 + 抖动 + 过头回退"的人类轨迹
3. 轨迹统计分析（加速度方差）验证"像人"

避坑点：
- 拼图小图如有 alpha 通道，需先裁剪有效区域再匹配
- 缺口 x 要减去拼图初始 x 才是实际滑动距离
- 匀速轨迹会被风控一票否决

运行：python3 03-slide-captcha.py
"""
import random
import ddddocr

# ---------------------------------------------------------------
# 1. 用 PIL 生成"背景图 + 缺口 + 拼图块"的模拟素材
# ---------------------------------------------------------------
def make_slide_images():
    """返回 (background_bytes, target_bytes, real_gap_x)"""
    from PIL import Image, ImageDraw
    bg = Image.new("RGB", (340, 180), (200, 210, 220))
    draw = ImageDraw.Draw(bg)
    for i in range(0, 340, 20):  # 纹理
        draw.line([(i, 0), (i, 180)], fill=(190, 200, 210))
    real_gap_x = random.randint(120, 300)
    # 在背景上挖一个深色缺口
    draw.rectangle([real_gap_x, 60, real_gap_x + 50, 130], fill=(90, 95, 105))
    # 拼图块：深色实心方块（真实场景是从原图裁剪并带透明通道）
    tgt = Image.new("RGB", (50, 70), (90, 95, 105))
    import io
    return bg._repr_png_() if False else (to_png(bg), to_png(tgt), real_gap_x)

def to_png(img) -> bytes:
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ---------------------------------------------------------------
# 2. 人类轨迹生成器
# ---------------------------------------------------------------
def human_track(distance: int):
    """
    生成人类滑动轨迹 [(t_ms, dx, dy), ...]
    特征：先快后慢、y 轴抖动、过头后回退
    """
    track, t, cur = [], 0, 0
    overshoot = random.randint(3, 8)          # 过头距离
    target = distance + overshoot
    while cur < target:
        remain = target - cur
        # 前段位移大（冲刺），后段位移小（微调）
        step = max(1, int(remain * 0.35))
        cur = min(target, cur + step)
        t += random.randint(12, 35)
        track.append((t, cur, random.uniform(-2, 2)))
    # 回退阶段：慢速滑回真实缺口位置
    while cur > distance:
        cur = max(distance, cur - random.randint(1, 3))
        t += random.randint(25, 60)
        track.append((t, cur, random.uniform(-1.5, 1.5)))
    return track

def analyze_track(track):
    """计算轨迹统计量：速度方差 -- 风控的核心特征之一"""
    speeds = []
    for i in range(1, len(track)):
        dt = (track[i][0] - track[i-1][0]) / 1000
        dx = track[i][1] - track[i-1][1]
        if dt > 0:
            speeds.append(abs(dx / dt))
    mean = sum(speeds) / len(speeds)
    var = sum((s - mean) ** 2 for s in speeds) / len(speeds)
    return mean, var

if __name__ == "__main__":
    # --- 缺口检测 ---
    bg_bytes, tgt_bytes, real_gap_x = make_slide_images()
    slide = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
    res = slide.slide_match(tgt_bytes, bg_bytes, simple_target=True)
    detected_x = res["target"][0]
    print(f"真实缺口 x = {real_gap_x}, 检测缺口 x = {detected_x}, "
          f"误差 = {abs(detected_x - real_gap_x)}px")

    # --- 轨迹生成（滑块初始 x 假设为 5）---
    slide_start_x = 5
    distance = detected_x - slide_start_x
    track = human_track(distance)
    mean, var = analyze_track(track)
    print(f"滑动距离 = {distance}px, 轨迹点数 = {len(track)}")
    print(f"速度均值 = {mean:.0f}px/s, 速度方差 = {var:.0f}")
    print("✅ 方差 > 0 且轨迹有回退 -> 通过基本人手特征校验" if var > 100
          else "⚠️ 轨迹太平滑，可能被判为机器")

    # --- 浏览器执行（Playwright 伪代码，Day 130 已学）---
    print("""
    # Playwright 执行部分（伪代码）：
    # handle = page.query_selector('.slider-button')
    # box = handle.bounding_box()
    # page.mouse.move(box['x'], box['y'])
    # page.mouse.down()
    # for t, dx, dy in track:
    #     page.mouse.move(box['x'] + dx, box['y'] + dy)
    #     page.wait_for_timeout(10)
    # page.mouse.up()
    """)
