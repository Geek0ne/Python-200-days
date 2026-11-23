#!/usr/bin/env python3
"""
02 - tesserocr 预处理管线与避坑（进阶用法）
==========================================
演示：传统 OCR 的黄金预处理四步，以及 tesserocr 不可用时
如何降级用 pytesseract，同时覆盖常见坑。

避坑点：
1. tesserocr 安装常与系统 Tesseract 版本冲突 -> 用 pytesseract 降级
2. --psm 模式选错识别率天差地别：验证码用 psm 7（单行）
3. 二值化阈值不是越小越好：先用直方图估阈值
4. 验证码必须与登录共用同一个 Session（服务端按会话存答案）

运行：python3 02-tesseract-pipeline.py
"""
import io
import random
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# ---------------------------------------------------------------
# 1. 生成测试验证码
# ---------------------------------------------------------------
def make_captcha(text: str) -> Image.Image:
    img = Image.new("RGB", (180, 60), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
    except OSError:
        font = ImageFont.load_default()
    x = 12
    for ch in text:
        draw.text((x, random.randint(4, 14)), ch, fill=(30, 30, 30), font=font)
        x += 30
    for _ in range(150):  # 噪点
        draw.point((random.randint(0, 179), random.randint(0, 59)), fill=(160, 160, 160))
    return img

# ---------------------------------------------------------------
# 2. 黄金预处理四步：灰度 -> 二值化 -> 中值滤波 -> 对比度增强
# ---------------------------------------------------------------
def preprocess(img: Image.Image, threshold: int = 140) -> Image.Image:
    gray = img.convert("L")                                   # ① 灰度化
    binary = gray.point(lambda p: 255 if p > threshold else 0)  # ② 二值化
    denoised = binary.filter(ImageFilter.MedianFilter(3))     # ③ 去噪
    enhanced = ImageOps.autocontrast(denoised)                # ④ 增强对比度
    return enhanced

# ---------------------------------------------------------------
# 3. OCR 调用：优先 tesserocr，降级 pytesseract
# ---------------------------------------------------------------
def ocr_image(img: Image.Image) -> str:
    try:
        import tesserocr
        return tesserocr.image_to_text(img).strip()
    except ImportError:
        import pytesseract
        # psm 7 = 单行文本；oem 3 = 默认 LSTM 引擎
        return pytesseract.image_to_string(img, config="--psm 7 -oem 3").strip()

def clean(result: str) -> str:
    # 只保留字母数字（Tesseract 常把噪点识别成符号）
    return "".join(c for c in result if c.isalnum())

if __name__ == "__main__":
    ok, total = 0, 15
    tesseract_missing = False
    try:
        import tesserocr  # noqa
    except ImportError:
        try:
            import pytesseract  # noqa
        except ImportError:
            tesseract_missing = True

    if tesseract_missing:
        print("⚠️ 未安装 tesserocr / pytesseract，演示预处理效果后退出。")
        print("   安装：pip install pytesseract && apt install tesseract-ocr")
        img = make_captcha("ab3d")
        img.save("/tmp/captcha_raw.png")
        preprocess(img).save("/tmp/captcha_processed.png")
        print("已保存对比图: /tmp/captcha_raw.png / /tmp/captcha_processed.png")
    else:
        for i in range(total):
            text = "".join(random.choices(string.digits + string.ascii_lowercase, k=4))
            img = make_captcha(text)
            processed = preprocess(img)
            raw_result = clean(ocr_image(img))
            result = clean(ocr_image(processed))
            hit = result.lower() == text.lower()
            ok += hit
            print(f"[{i+1:02d}] 真实:{text} 原图识别:{raw_result:8s} "
                  f"预处理后:{result:8s} {'✅' if hit else '❌'}")
        print(f"\n预处理后识别率: {ok}/{total} = {ok/total:.0%}")
        print("结论：预处理能显著提升传统 OCR 对验证码的识别率，")
        print("      但仍不如 ddddocr 稳定 —— 复杂验证码直接上深度学习方案。")
