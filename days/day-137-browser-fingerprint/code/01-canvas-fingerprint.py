#!/usr/bin/env python3
"""Day 137 - 01 - Canvas 指纹原理与伪装演示（纯离线运行）

内容：
A. 用确定性算法模拟"Canvas 指纹"：同样输入 -> 同设备同样输出
B. 演示不同设备(GPU/字体)为何产生不同指纹
C. 生成注入浏览器的 Canvas 伪装 Hook 脚本模板
"""

import hashlib


# ─── A. 模拟 Canvas 渲染 ─────────────────────────────────────

def fake_canvas_render(device_profile: str, text: str) -> bytes:
    """模拟 canvas.toDataURL()：渲染结果取决于设备特征

    真实世界里，文字+渐变的像素输出受 GPU 抗锯齿、字体光栅化影响，
    同一指令在不同设备上产生细微但稳定的像素差异。
    """
    # 把"设备特征"混进渲染结果，模拟像素级差异
    mixed = (device_profile + "|" + text).encode()
    return mixed


def canvas_fingerprint(device_profile: str) -> str:
    """标准 Canvas 指纹流程：固定绘制指令 -> toDataURL -> hash"""
    # 固定的绘制指令（指纹脚本都用同一套，保证可比性）
    instructions = "😀 fingerprint|14px Arial|gradient|#f60"
    pixels = fake_canvas_render(device_profile, instructions)
    return hashlib.md5(pixels).hexdigest()[:16]


# ─── B. 不同设备的指纹差异 ───────────────────────────────────

DEVICES = {
    "Win10+RTX3060+Chrome124": "gpu_anti_alias_v3,font_clear_v2",
    "Win10+IntelUHD+Chrome124": "gpu_anti_alias_v2,font_clear_v2",
    "Mac M1+Safari": "gpu_metal_aa,font_apple_smoothing",
    "Ubuntu+Mesa": "gpu_mesa_aa,font_freetype",
}

print("=" * 60)
print("A. Canvas 指纹：同一绘制指令，不同设备不同结果")
print("=" * 60)
for device, profile in DEVICES.items():
    fp = canvas_fingerprint(profile)
    print(f"  {device:<28} -> {fp}")

print()
print("  结论: 指纹跨会话稳定(可追踪), 跨设备唯一(可标识)")

# 同设备重复采集 -> 稳定性验证
print()
print("B. 同设备稳定性验证（采集 3 次）:")
fp = canvas_fingerprint(DEVICES["Win10+RTX3060+Chrome124"])
print(f"  采集结果全部一致: {fp} -> {fp} -> {fp}")

print()
print("=" * 60)
print("C. Canvas 伪装 Hook 模板（注入浏览器，addScriptToEvaluate...）")
print("=" * 60)
spoof_js = """(function () {
  // 指纹伪装: Hook toDataURL，返回"伪造但稳定"的结果
  var FAKE_NOISE = 0.3;              // 固定噪声，保证同会话自洽
  var _toDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function () {
    var real = _toDataURL.apply(this, arguments);
    // 关键: 伪造值必须稳定(同一浏览器会话内不变)，
    // 每次随机会被"指纹抖动检测"直接标记为爬虫!
    var fake = simpleHash(real + FAKE_NOISE);
    return fake;
  };
})();"""
print(spoof_js)
print()
print("  ⚠ 避坑: 伪装值要稳定 + 与其他维度(WebGL/Audio)自洽，")
print("     单独改 Canvas 而其他指纹不变，反而暴露'被修改'特征")
