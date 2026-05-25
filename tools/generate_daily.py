#!/usr/bin/env python3
"""
每日 Python 学习内容生成器
自动创建当日学习文件夹、生成内容、提交 git
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(os.path.expanduser("~/code/Learn-Python"))
PROGRESS_FILE = REPO_ROOT / "tools" / "progress.json"
ROADMAP_FILE = REPO_ROOT / "ROADMAP.md"

# ─── 工具函数 ───

def load_progress():
    with open(PROGRESS_FILE) as f:
        return json.load(f)

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def parse_roadmap():
    """从 ROADMAP.md 中提取每日主题列表"""
    roadmap_text = ROADMAP_FILE.read_text()
    days = {}
    
    # 匹配 ### Day XXX — 主题 (使用连字符或破折号)
    pattern = r"### Day (\d+)\s*[—\-]\s*(.+?)\n"
    matches = re.findall(pattern, roadmap_text)
    
    for num, topic in matches:
        day_num = int(num)
        topic_clean = topic.strip()
        
        # 从该行开始，提取子主题（- **xxx**）
        # 找到该行位置到下一个 ### 之间的内容
        line_pattern = re.escape(f"### Day {num}") + r"\s*[—\-]\s*" + re.escape(topic_clean)
        match = re.search(line_pattern, roadmap_text)
        if not match:
            continue
            
        start = match.end()
        
        # 找下一个 ### 或 ---
        next_day = roadmap_text.find("\n### Day ", start)
        next_sep = roadmap_text.find("\n---", start)
        
        if next_day != -1 and next_sep != -1:
            end = min(next_day, next_sep)
        elif next_day != -1:
            end = next_day
        elif next_sep != -1:
            end = next_sep
        else:
            end = len(roadmap_text)
        
        section = roadmap_text[start:end]
        bullets = re.findall(r"- \*\*(.+?)\*\*", section)
        
        days[day_num] = {
            "topic": topic_clean,
            "subtopics": bullets
        }
    
    return days

def get_current_day_info():
    """获取今天应该学习的 Day 信息"""
    progress = load_progress()
    days_map = parse_roadmap()
    
    last_day = progress["last_day"]
    next_day = last_day + 1
    
    if next_day > progress["total_days"]:
        print("🎉 所有学习内容已完成！")
        return None
    
    day_info = days_map.get(next_day, {})
    if not day_info:
        print(f"⚠️ 未找到 Day {next_day} 的信息")
        return None
    
    # 计算所属 Phase
    if next_day <= 15:
        phase = 1
        phase_name = "Python 基础"
    elif next_day <= 30:
        phase = 2
        phase_name = "核心编程概念"
    elif next_day <= 45:
        phase = 3
        phase_name = "面向对象编程"
    elif next_day <= 60:
        phase = 4
        phase_name = "高阶特性"
    elif next_day <= 75:
        phase = 5
        phase_name = "标准库与生态系统"
    elif next_day <= 90:
        phase = 6
        phase_name = "实战项目"
    else:
        phase = 7
        phase_name = "进阶与性能优化"
    
    return {
        "day": next_day,
        "topic": day_info["topic"],
        "subtopics": day_info.get("subtopics", []),
        "phase": phase,
        "phase_name": phase_name,
        "last_day": last_day
    }

def create_day_directory(day_info):
    """为当天创建目录结构"""
    day_num = day_info["day"]
    topic_slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '-', day_info["topic"]).lower()
    dir_name = f"day-{day_num:03d}-{topic_slug}"
    day_dir = REPO_ROOT / "days" / dir_name
    
    # 创建子目录
    (day_dir / "code").mkdir(parents=True, exist_ok=True)
    (day_dir / "diagrams").mkdir(parents=True, exist_ok=True)
    (day_dir / "exercises").mkdir(parents=True, exist_ok=True)
    
    return day_dir, dir_name

def print_day_info(day_info):
    """打印当天学习内容摘要（供 LLM 使用）"""
    print("=" * 60)
    print(f"📅 学习任务生成")
    print("=" * 60)
    print(f"Day {day_info['day']:03d}: {day_info['topic']}")
    print(f"阶段: Phase {day_info['phase']} — {day_info['phase_name']}")
    print(f"子主题: {', '.join(day_info['subtopics'])}")
    print(f"目录: days/day-{day_info['day']:03d}-*/")
    print("=" * 60)
    print()
    print("请按以下结构生成内容：")
    print()
    print("1. README.md — 完整学习内容")
    print("   - 概念解释（每个子主题）")
    print("   - 原理深入（底层机制）")
    print("   - 定义与方法（API 速查）")
    print("   - ASCII/Mermaid 图解")
    print("   - 实战代码案例")
    print("   - 思考题")
    print()
    print("2. code/ — 代码示例文件")
    print("   - 示例命名为 01-xxx.py, 02-xxx.py ...")
    print()
    print("3. diagrams/README.md — 图解")
    print("   - ASCII 图或 Mermaid 图")
    print()
    print("4. exercises/checklist.md — 练习与检查表")
    print()
    print("提交要求：至少 5 次 git commit")
    print("提交示例：")
    print("  docs(concept): 添加 [主题] 概念解释")
    print("  feat(diagram): 添加 [主题] 原理图解")
    print("  docs(example): 添加 [主题] 基础代码示例")
    print("  feat(example): 添加 [主题] 实战案例")
    print("  docs(exercise): 添加 [主题] 练习题")
    print()

def update_progress(day_num):
    """更新进度文件"""
    progress = load_progress()
    progress["last_day"] = day_num
    
    if day_num <= 15:
        progress["current_phase"] = 1
    elif day_num <= 30:
        progress["current_phase"] = 2
    elif day_num <= 45:
        progress["current_phase"] = 3
    elif day_num <= 60:
        progress["current_phase"] = 4
    elif day_num <= 75:
        progress["current_phase"] = 5
    elif day_num <= 90:
        progress["current_phase"] = 6
    else:
        progress["current_phase"] = 7
    
    completed = progress.get("completed_days", [])
    if day_num not in completed:
        completed.append(day_num)
    progress["completed_days"] = sorted(completed)
    
    save_progress(progress)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        # 显示进度状态
        progress = load_progress()
        days_map = parse_roadmap()
        
        next_day = progress["last_day"] + 1
        total = progress["total_days"]
        pct = (progress["last_day"] / total) * 100
        
        print(f"📊 学习进度")
        print(f"  已完成: {progress['last_day']}/{total} 天 ({pct:.1f}%)")
        print(f"  当前阶段: Phase {progress['current_phase']}")
        print(f"  完成天数: {len(progress['completed_days'])}")
        
        if next_day <= total:
            next_info = days_map.get(next_day, {})
            print(f"  下一课: Day {next_day:03d} — {next_info.get('topic', '未知')}")
        
        print()
        sys.exit(0)
    
    # 正常模式：打印当天任务信息
    info = get_current_day_info()
    if info:
        print_day_info(info)
    else:
        print("所有课程已完成或信息获取失败")
