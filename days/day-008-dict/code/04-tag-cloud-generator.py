#!/usr/bin/env python3
"""
04-tag-cloud-generator.py
Day 008 — 练习 4：标签云生成器

实现一个带权重的标签云生成器，支持 ASCII 可视化。

可直接运行：python3 04-tag-cloud-generator.py
"""

from collections import Counter
from typing import Optional


def generate_tag_cloud(tags: list, max_tags: int = 30) -> dict:
    """
    从标签列表生成词频字典
    """
    counter = Counter(tags)
    top = counter.most_common(max_tags)
    return dict(top)


def render_tag_cloud(tag_freq: dict,
                     max_font_size: int = 48,
                     min_font_size: int = 12,
                     bar_length: int = 25) -> str:
    """
    渲染 ASCII 标签云
    """
    if not tag_freq:
        return "(无数据)"

    max_freq = max(tag_freq.values())
    min_freq = min(tag_freq.values())
    freq_range = max_freq - min_freq if max_freq > min_freq else 1

    lines = []
    lines.append("=" * 60)
    lines.append("  🏷️  TAG CLOUD")
    lines.append("=" * 60)

    sorted_tags = sorted(tag_freq.items(), key=lambda x: -x[1])

    for tag, freq in sorted_tags:
        # 归一化到 0~1
        normalized = (freq - min_freq) / freq_range

        # "字号"计算
        font_size = int(min_font_size + normalized * (max_font_size - min_font_size))

        # 条形图
        bar_len = max(1, int(normalized * bar_length))
        bar = "▓" * bar_len + "░" * (bar_length - bar_len)

        # 百分比
        pct = freq / max_freq * 100

        lines.append(f"  {tag:<15} {freq:<5} {bar}  {pct:>5.1f}%  (size={font_size})")

    lines.append("=" * 60)

    # 统计信息
    lines.append(f"  📊 总标签数: {sum(tag_freq.values())} | 唯一标签: {len(tag_freq)}")
    lines.append("=" * 60)

    return "\n".join(lines)


def render_color_code(tag_freq: dict) -> str:
    """
    生成 HTML 风格的标签云（颜色编码）
    高频词用暖色(红/橙)，低频词用冷色(蓝/灰)
    
    返回 HTML 片段字符串
    """
    if not tag_freq:
        return ""

    max_freq = max(tag_freq.values())
    sorted_tags = sorted(tag_freq.items(), key=lambda x: -x[1])

    def get_color(normalized: float) -> str:
        """根据归一化值(0~1)返回颜色"""
        if normalized > 0.8:
            return "#e74c3c"  # 红
        elif normalized > 0.6:
            return "#e67e22"  # 橙
        elif normalized > 0.4:
            return "#f1c40f"  # 黄
        elif normalized > 0.2:
            return "#2ecc71"  # 绿
        else:
            return "#3498db"  # 蓝

    tags_html = []
    for tag, freq in sorted_tags:
        normalized = freq / max_freq
        size = 12 + normalized * 28  # 12px ~ 40px
        color = get_color(normalized)
        tags_html.append(
            f'<span style="font-size: {size:.0f}px; color: {color}; '
            f'margin: 4px; display: inline-block;">{tag}</span>'
        )

    return "".join(tags_html)


def render_ascii_table(tag_freq: dict, max_tags: int = 15) -> str:
    """
    渲染为表格格式
    """
    if not tag_freq:
        return ""

    sorted_tags = sorted(tag_freq.items(), key=lambda x: -x[1])[:max_tags]
    total = sum(tag_freq.values())

    lines = []
    lines.append("+----+-----------------+-------+---------+")
    lines.append("| #  | Tag             | Count |   %     |")
    lines.append("+----+-----------------+-------+---------+")

    for rank, (tag, count) in enumerate(sorted_tags, 1):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        lines.append(f"| {rank:<2} | {tag:<15} | {count:<5} | {pct:>5.1f}% | {bar}")
        if rank % 5 == 0 and rank < max_tags:
            lines.append("|....+.................+.......+.........+|")

    lines.append("+----+-----------------+-------+---------+")
    lines.append(f"| 总计: {total:<5} 标签, {len(tag_freq):<3} 唯一标签                |")
    lines.append("+----+-----------------+-------+---------+")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("  🏷️  标签云生成器 — 演示")
    print("=" * 60)

    # 测试数据
    sample_tags = [
        "python", "javascript", "python", "go", "rust", "java",
        "python", "typescript", "go", "python", "rust", "java",
        "javascript", "python", "go", "kotlin", "swift", "python",
        "java", "go", "rust", "python", "elixir", "scala",
        "python", "javascript", "go", "python",
    ] * 5  # 重复增加数据量

    # 生成标签云
    tag_freq = generate_tag_cloud(sample_tags, max_tags=12)

    # 输出方式 1：ASCII 条形云
    print("\n📊 格式一：ASCII 条形云\n")
    print(render_tag_cloud(tag_freq, max_font_size=48, min_font_size=12, bar_length=25))

    # 输出方式 2：表格格式
    print("\n📋 格式二：表格格式\n")
    print(render_ascii_table(tag_freq, max_tags=12))

    # 输出方式 3：HTML 代码（不直接显示，保存为文件方便查看）
    html_output = render_color_code(tag_freq)
    html_full = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Tag Cloud</title>
<style>
body {{ font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }}
.cloud {{ max-width: 600px; margin: 0 auto; padding: 30px;
           background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
h1 {{ text-align: center; color: #333; }}
</style>
</head>
<body>
<div class="cloud">
<h1>🏷️ Tag Cloud</h1>
<p style="text-align:center;color:#888;">字体大小和颜色反映词频高低</p>
<div style="text-align:center; line-height: 2.2;">
{html_output}
</div>
</div>
</body>
</html>"""

    with open("/tmp/tag_cloud.html", "w", encoding="utf-8") as f:
        f.write(html_full)
    print("\n🌐 格式三：HTML 彩色标签云")
    print(f"   已导出 → /tmp/tag_cloud.html")
    print(f"   用浏览器打开查看彩色标签云！")

    # 额外：展示输入数据的统计
    print(f"\n  📈 输入统计:")
    print(f"     原始标签总数: {len(sample_tags)}")
    print(f"     唯一标签数:   {len(tag_freq)}")
    print(f"     最高频标签:   『{list(tag_freq.keys())[0]}』({list(tag_freq.values())[0]}次)")

    print("\n" + "=" * 60)
    print("  ✅ 标签云生成演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
