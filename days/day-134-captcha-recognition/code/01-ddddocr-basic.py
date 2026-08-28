#!/usr/bin/env python3
"""
01 - ddddocr 图形验证码识别（基础用法）
======================================
演示：ddddocr 识别本地/网络图形验证码。

为什么用 ddddocr：
- 端到端深度学习模型，无需字符切分与图像预处理
- 纯 CPU 推理（onnxruntime），开箱即用

运行前安装：pip install ddddocr pillow requests
运行：python3 01-ddddocr-basic.py
"""
import io
import requests
from PIL import Image, ImageFilter, ImageOps
import ddddocr

# ---------------------------------------------------------------
# 1. 初始化（首次运行会自动加载内置模型）
# ---------------------------------------------------------------
ocr = ddddocr.DdddOcr(show_ad=False)

# ---------------------------------------------------------------
# 2. 识别本地生成的"验证码样图"
#    这里用 PIL 动手画一张带噪点/干扰线的验证码模拟真实场景
# ---------------------------------------------------------------
def make_fake_captcha(text: str) -> bytes:
    """生成一张简易验证码图片（灰底黑字+噪点+干扰线）"""
    from PIL import ImageDraw, ImageFont
    img = Image.new("RGB", (160, 60), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    x = 15
    for ch in text:
        draw.text((x, random_y()), ch, fill=(20, 20, 20), font=font)
        x += 28
    # 噪点
    import random
    for _ in range(120):
        draw.point((random.randint(0, 159), random.randint(0, 59)), fill=(150, 150, 150))
    # 干扰线
    for _ in range(3):
        draw.line([(0, random.randint(0, 59)), (159, random.randint(0, 59))],
                  fill=(120, 120, 120), width=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def random_y():
    import random
    return random.randint(5, 20)

if __name__ == "__main__":
    import random, string
    ok, total = 0, 20
    for i in range(total):
        text = "".join(random.choices(string.digits + string.ascii_lowercase, k=4))
        img_bytes = make_fake_captcha(text)
        result = ocr.classification(img_bytes)
        hit = result.strip().lower() == text.lower()
        ok += hit
        print(f"[{i+1:02d}] 真实: {text:6s} 识别: {result.strip():8s} {'✅' if hit else '❌'}")
    print(f"\n识别率: {ok}/{total} = {ok/total:.0%}")
    print("提示：真实站点验证码更扭曲，识别率通常在 80%~95% 之间")
