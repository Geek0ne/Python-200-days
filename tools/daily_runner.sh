#!/bin/bash
# 每日 Python 学习内容生成器（cron 入口）
# 被定时任务调用，在后台生成当日学习内容并提交

set -e

REPO_DIR="$HOME/code/Learn-Python"
cd "$REPO_DIR"

# 获取当天任务信息
python3 tools/generate_daily.py > /tmp/python-daily-info.txt
cat /tmp/python-daily-info.txt

echo ""
echo "🔄 准备生成今日学习内容..."

# Git 状态
echo "当前分支: $(git branch --show-current)"
echo "最新提交: $(git log --oneline -1)"
echo "未提交文件: $(git status --short | wc -l)"

# 输出用于 cron 的环境变量
echo "REPO_DIR=$REPO_DIR"
echo "DATE=$(date +%Y-%m-%d)"
