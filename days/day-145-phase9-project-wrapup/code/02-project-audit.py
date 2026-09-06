#!/usr/bin/env python3
"""Day 145 - 项目收尾审计器.

检查 Phase 9 每个 Day 目录的交付物完整性:
README.md / code/ / exercises/ / diagrams/

输出审计表 + 缺项警告, 全部通过则 exit 0, 有缺项 exit 1.
用法: python3 02-project-audit.py [day范围如 142-145]
"""
import re
import sys
from pathlib import Path

DAYS_ROOT = Path(__file__).resolve().parents[2]  # .../Learn-Python/days
REQUIRED = ["README.md", "code", "exercises", "diagrams"]


def audit(lo: int, hi: int) -> int:
    problems = 0
    print(f"{'Day':>4}  {'目录':<40} 交付物")
    for path in sorted(DAYS_ROOT.iterdir()):
        m = re.match(r"day-(\d+)-", path.name)
        if not path.is_dir() or not m:
            continue
        day = int(m.group(1))
        if not (lo <= day <= hi):
            continue
        marks = []
        for item in REQUIRED:
            ok = (path / item).exists()
            marks.append(("✓" if ok else "✗") + item)
            if not ok:
                problems += 1
        status = " ".join(marks)
        print(f"{day:>4}  {path.name:<40} {status}")
    print(f"\n审计完成: {'✅ 全部齐全' if problems == 0 else f'❌ 缺 {problems} 项'}")
    return 0 if problems == 0 else 1


def main() -> None:
    rng = sys.argv[1] if len(sys.argv) > 1 else "126-145"
    m = re.match(r"(\d+)-(\d+)$", rng)
    if not m:
        sys.exit(f"范围格式错误: {rng}(应为如 126-145)")
    sys.exit(audit(int(m.group(1)), int(m.group(2))))


if __name__ == "__main__":
    main()
