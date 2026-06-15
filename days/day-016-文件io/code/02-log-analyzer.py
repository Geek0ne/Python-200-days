#!/usr/bin/env python3
"""
Day 016 — 日志分析器实战
=========================
功能：
1. 解析标准日志文件
2. 统计日志级别分布
3. 计算错误率
4. 时间段过滤
5. 生成分析报告
6. 大文件流式处理
"""

import os
import re
import sys
import gzip
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path


# ════════════════════════════════════════════
# 日志解析器核心
# ════════════════════════════════════════════

# 标准日志格式（示例）：
# 2024-01-15 10:30:45 [INFO] 用户登录成功
# 2024-01-15 10:31:02 [WARNING] 登录尝试次数过多
# 2024-01-15 10:31:15 [ERROR] 数据库连接超时
# 2024-01-15 10:31:16 [CRITICAL] 服务不可用

# 支持的日志级别和权重（数值越大越严重）
LOG_LEVELS = {
    "DEBUG": 0,
    "INFO": 1,
    "NOTICE": 2,
    "WARNING": 3,
    "WARN": 3,
    "ERROR": 4,
    "CRITICAL": 5,
    "FATAL": 5,
}

# 标准日志行正则表达式
# 匹配: 日期 时间 [级别] 消息
LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"
    r"\[(?P<level>[A-Z]+)\]\s+"
    r"(?P<message>.+)$"
)


class LogEntry:
    """单条日志条目"""
    
    def __init__(self, timestamp: datetime, level: str, message: str, raw: str = ""):
        self.timestamp = timestamp
        self.level = level.upper()
        self.message = message
        self.raw = raw
        self.severity = LOG_LEVELS.get(self.level, -1)
    
    def __repr__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] [{self.level}] {self.message}"
    
    def is_error(self) -> bool:
        """是否为错误级别及以上"""
        return self.severity >= LOG_LEVELS["ERROR"]
    
    def is_warning(self) -> bool:
        """是否为警告级别"""
        return self.severity == LOG_LEVELS["WARNING"]
    
    def is_info(self) -> bool:
        """是否为信息级别"""
        return self.level == "INFO"
    
    def is_debug(self) -> bool:
        return self.level == "DEBUG"


class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, filename: str = None, encoding: str = "utf-8"):
        self.filename = filename
        self.encoding = encoding
        self.entries: list[LogEntry] = []
        self.total_lines = 0
        self.skipped_lines = 0
        self._parsed = False
    
    def parse(self, filename: str = None) -> "LogAnalyzer":
        """解析日志文件，流式逐行处理"""
        if filename:
            self.filename = filename
        
        if not self.filename or not os.path.exists(self.filename):
            raise FileNotFoundError(f"日志文件不存在: {self.filename}")
        
        filepath = Path(self.filename)
        self.entries = []
        self.total_lines = 0
        self.skipped_lines = 0
        
        # 支持 gzip 压缩文件
        open_func = gzip.open if filepath.suffix == ".gz" else open
        
        with open_func(self.filename, "rt", encoding=self.encoding) as f:
            for raw_line in f:
                self.total_lines += 1
                line = raw_line.strip()
                if not line:
                    continue
                
                match = LOG_PATTERN.match(line)
                if match:
                    try:
                        timestamp = datetime.strptime(
                            match.group("timestamp"),
                            "%Y-%m-%d %H:%M:%S"
                        )
                        entry = LogEntry(
                            timestamp=timestamp,
                            level=match.group("level"),
                            message=match.group("message"),
                            raw=line,
                        )
                        self.entries.append(entry)
                    except ValueError:
                        self.skipped_lines += 1
                else:
                    # 可能是多行日志的续行，合并到上一条
                    if self.entries:
                        self.entries[-1].message += "\n" + line
                    else:
                        self.skipped_lines += 1
        
        self._parsed = True
        return self
    
    def filter_by_level(self, min_level: str = "WARNING") -> list[LogEntry]:
        """按最低级别过滤"""
        min_sev = LOG_LEVELS.get(min_level.upper(), 0)
        return [e for e in self.entries if e.severity >= min_sev]
    
    def filter_by_time_range(
        self, start: datetime, end: datetime
    ) -> list[LogEntry]:
        """按时间范围过滤"""
        return [e for e in self.entries if start <= e.timestamp <= end]
    
    def filter_by_keyword(self, keyword: str) -> list[LogEntry]:
        """按关键词过滤"""
        return [e for e in self.entries if keyword.lower() in e.message.lower()]
    
    # ════════════════════════════════════════════
    # 统计方法
    # ════════════════════════════════════════════
    
    def count_by_level(self) -> dict[str, int]:
        """统计各级别出现次数"""
        return dict(Counter(e.level for e in self.entries))
    
    def count_by_hour(self) -> dict[str, int]:
        """按小时统计日志量"""
        hour_counts = Counter()
        for e in self.entries:
            hour_key = e.timestamp.strftime("%Y-%m-%d %H:00")
            hour_counts[hour_key] += 1
        return dict(sorted(hour_counts.items()))
    
    def count_by_message_pattern(self) -> dict[str, int]:
        """按消息模式统计（提取消息类型）"""
        # 提取消息中的关键动作模式
        patterns = [
            (r"用户登录(成功|失败)", "登录事件"),
            (r"数据库(连接|查询|写入|超时|断开)", "数据库事件"),
            (r"API.*调用.*失败", "API调用失败"),
            (r"服务(启动|停止|重启|不可用)", "服务状态变更"),
            (r"权限|认证|授权", "权限事件"),
            (r"超时", "超时事件"),
            (r"重试", "重试事件"),
            (r"内存|CPU|磁盘", "资源事件"),
        ]
        
        pattern_counts: dict[str, int] = defaultdict(int)
        other = 0
        
        for e in self.entries:
            matched = False
            for pattern, category in patterns:
                if re.search(pattern, e.message, re.IGNORECASE):
                    pattern_counts[category] += 1
                    matched = True
                    break
            if not matched:
                other += 1
        
        if other:
            pattern_counts["其他"] = other
        
        return dict(pattern_counts)
    
    def get_error_rate(self) -> float:
        """计算错误率（ERROR及以上 / 总数）"""
        if not self.entries:
            return 0.0
        errors = sum(1 for e in self.entries if e.is_error())
        return errors / len(self.entries)
    
    def get_time_range(self) -> tuple[datetime | None, datetime | None]:
        """获取日志的时间范围"""
        if not self.entries:
            return None, None
        timestamps = [e.timestamp for e in self.entries]
        return min(timestamps), max(timestamps)
    
    def get_top_errors(self, n: int = 10) -> list[tuple[str, int]]:
        """获取出现最多的错误消息"""
        error_messages = [
            e.message for e in self.entries if e.is_error()
        ]
        return Counter(error_messages).most_common(n)
    
    # ════════════════════════════════════════════
    # 报告生成
    # ════════════════════════════════════════════
    
    def generate_report(self, title: str = "日志分析报告") -> str:
        """生成完整分析报告"""
        if not self._parsed:
            return "⚠️ 请先调用 parse() 方法解析日志文件"
        
        level_counts = self.count_by_level()
        error_rate = self.get_error_rate()
        time_start, time_end = self.get_time_range()
        hour_counts = self.count_by_hour()
        
        lines = []
        lines.append("=" * 66)
        lines.append(f"  {title}")
        lines.append("=" * 66)
        lines.append(f"  文件: {self.filename or '未知'}")
        lines.append(f"  总行数: {self.total_lines}")
        lines.append(f"  解析条目: {len(self.entries)}")
        lines.append(f"  跳过行: {self.skipped_lines}")
        
        if time_start and time_end:
            duration = time_end - time_start
            lines.append(f"  时间范围: {time_start} → {time_end}")
            lines.append(f"  跨度: {duration}")
        
        lines.append("")
        lines.append("─" * 66)
        lines.append("  日志级别分布")
        lines.append("─" * 66)
        
        total = len(self.entries)
        if total > 0:
            for level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTICE"]:
                count = level_counts.get(level, 0)
                if count > 0:
                    pct = count / total * 100
                    bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
                    lines.append(f"  {level:<10s} {count:>8d} ({pct:5.1f}%) {bar}")
        
        lines.append("")
        lines.append("─" * 66)
        lines.append(f"  错误率: {error_rate:.2%}")
        lines.append(f"  （ERROR + CRITICAL / 总计）")
        lines.append("")
        
        # 错误级别详情
        error_count = sum(level_counts.get(lv, 0) for lv in ["ERROR", "CRITICAL"])
        if error_count > 0:
            lines.append("─" * 66)
            lines.append(f"  最常出现的错误 TOP 10")
            lines.append("─" * 66)
            for i, (msg, cnt) in enumerate(self.get_top_errors(10), 1):
                lines.append(f"  {i:2d}. [{cnt:4d}次] {msg[:80]}")
        
        lines.append("")
        lines.append("─" * 66)
        lines.append(f"  按小时分布（峰值时段）")
        lines.append("─" * 66)
        
        if hour_counts:
            max_count = max(hour_counts.values())
            for hour, count in list(hour_counts.items())[:24]:
                bar_len = int(count / max_count * 30) if max_count > 0 else 0
                bar = "▓" * bar_len + "░" * (30 - bar_len)
                lines.append(f"  {hour} {bar} {count}")
        
        lines.append("")
        lines.append("─" * 66)
        lines.append(f"  消息模式统计")
        lines.append("─" * 66)
        pattern_counts = self.count_by_message_pattern()
        for pattern, count in sorted(
            pattern_counts.items(), key=lambda x: -x[1]
        ):
            pct = count / total * 100 if total > 0 else 0
            lines.append(f"  {pattern:<12s} {count:>6d} ({pct:5.1f}%)")
        
        lines.append("")
        lines.append("═" * 66)
        
        return "\n".join(lines)


# ════════════════════════════════════════════
# 日志文件生成器（用于测试）
# ════════════════════════════════════════════

def generate_sample_logs(
    output_path: str,
    days: int = 1,
    entries_per_hour: int = 60,
    error_rate: float = 0.05,
    warning_rate: float = 0.10,
):
    """生成模拟日志样本"""
    
    levels = []
    weights = []
    
    # 构建级别分布
    lev_conf = {
        "DEBUG": 0.15,
        "INFO": 1.0 - error_rate - warning_rate - 0.02,
        "NOTICE": 0.02,
        "WARNING": warning_rate,
        "ERROR": error_rate * 0.8,
        "CRITICAL": error_rate * 0.2,
    }
    
    for level, weight in lev_conf.items():
        levels.append(level)
        weights.append(weight)
    
    # 归一化
    total_w = sum(weights)
    weights = [w / total_w for w in weights]
    
    # 消息模板
    info_messages = [
        "用户登录成功",
        "用户退出系统",
        "页面请求返回 200",
        "数据库查询完成",
        "缓存命中",
        "定时任务执行完成",
        "API 调用成功",
        "数据同步完成",
        "邮件发送成功",
        "文件上传完成",
    ]
    
    warning_messages = [
        "登录尝试次数过多",
        "磁盘使用率超过 80%",
        "API 响应延迟 > 2s",
        "数据库连接池已满 90%",
        "内存使用率超过 85%",
        "证书即将过期（剩余 7 天）",
        "请求频率超限",
        "重试次数过多",
    ]
    
    error_messages = [
        "数据库连接超时",
        "数据库查询失败: table not found",
        "API 调用返回 500",
        "内存不足: OOM Killer 触发",
        "磁盘写入失败: 空间不足",
        "认证令牌无效",
        "配置文件解析错误",
        "网络连接断开",
    ]
    
    critical_messages = [
        "服务不可用 — 健康检查失败",
        "服务进程崩溃",
        "磁盘故障: I/O Error",
        "数据库主从同步中断",
        "安全告警: 检测到入侵尝试",
    ]
    
    import random
    random.seed(42)
    
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    with open(output_path, "w", encoding="utf-8") as f:
        total_entries = days * 24 * entries_per_hour
        
        for i in range(total_entries):
            minutes_offset = i // (entries_per_hour // 60)
            seconds_offset = (i % (entries_per_hour // 60)) * (60 // (entries_per_hour // 60))
            
            if entries_per_hour >= 60:
                actual_seconds = i % entries_per_hour
                ts = base_time + timedelta(
                    hours=i // entries_per_hour,
                    seconds=actual_seconds,
                )
            else:
                ts = base_time + timedelta(
                    hours=i // entries_per_hour,
                    minutes=minutes_offset,
                    seconds=seconds_offset,
                )
            
            # 选择级别
            level = random.choices(levels, weights=weights)[0]
            
            # 选择消息
            if level == "INFO" or level == "DEBUG" or level == "NOTICE":
                msg = random.choice(info_messages)
            elif level == "WARNING":
                msg = random.choice(warning_messages)
            elif level == "ERROR":
                msg = random.choice(error_messages)
            else:  # CRITICAL
                msg = random.choice(critical_messages)
            
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{ts_str} [{level}] {msg}\n")
    
    print(f"✅ 生成了 {total_entries} 条模拟日志: {output_path}")
    return output_path


# ════════════════════════════════════════════
# 命令行接口
# ════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="日志分析器 — 统计日志级别分布、错误率等",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s app.log
  %(prog)s app.log --min-level ERROR
  %(prog)s app.log --since "2024-01-15" --until "2024-01-16"
  %(prog)s app.log --keyword "数据库"
  %(prog)s app.log.gz                          # 支持 gzip
  %(prog)s --generate sample.log --days 7     # 生成测试日志
        """,
    )
    
    parser.add_argument("logfile", nargs="?", help="日志文件路径")
    parser.add_argument("--generate", help="生成测试日志到指定路径")
    parser.add_argument("--days", type=int, default=1, help="生成测试日志的天数")
    parser.add_argument(
        "--min-level",
        default=None,
        help="最低级别过滤 (DEBUG/INFO/WARNING/ERROR/CRITICAL)",
    )
    parser.add_argument("--since", help="起始时间 (YYYY-MM-DD)")
    parser.add_argument("--until", help="结束时间 (YYYY-MM-DD)")
    parser.add_argument("--keyword", help="按关键词过滤")
    parser.add_argument(
        "--encoding", default="utf-8", help="文件编码 (默认: utf-8)"
    )
    parser.add_argument("--output", "-o", help="报告输出文件")
    parser.add_argument(
        "--errors-only", action="store_true", help="只显示错误级别及以上"
    )
    
    args = parser.parse_args()
    
    # 生成测试日志模式
    if args.generate:
        generate_sample_logs(args.generate, days=args.days)
        return
    
    # 分析日志
    if not args.logfile:
        parser.print_help()
        print("\n⚠️  请指定日志文件路径或使用 --generate 生成测试日志")
        print("   示例: python 02-log-analyzer.py --generate sample.log --days 1")
        print("         python 02-log-analyzer.py sample.log")
        return
    
    analyzer = LogAnalyzer(args.logfile, encoding=args.encoding)
    
    try:
        analyzer.parse()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"❌ 编码错误: {e}")
        print("   尝试修改 --encoding 参数（如 gbk）")
        sys.exit(1)
    
    if args.errors_only:
        analyzer.entries = [
            e for e in analyzer.entries if e.is_error()
        ]
        print(f"过滤后保留 {len(analyzer.entries)} 条错误日志")
    
    if args.min_level:
        analyzer.entries = analyzer.filter_by_level(args.min_level)
        print(f"过滤后保留 {len(analyzer.entries)} 条 {args.min_level} 及以上日志")
    
    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d")
        analyzer.entries = [
            e for e in analyzer.entries if e.timestamp >= since
        ]
    
    if args.until:
        until = datetime.strptime(args.until, "%Y-%m-%d") + timedelta(days=1)
        analyzer.entries = [
            e for e in analyzer.entries if e.timestamp <= until
        ]
    
    if args.keyword:
        analyzer.entries = analyzer.filter_by_keyword(args.keyword)
        print(f"关键词 '{args.keyword}' 过滤后保留 {len(analyzer.entries)} 条")
    
    report = analyzer.generate_report(
        title=f"日志分析报告 — {os.path.basename(args.logfile)}"
    )
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"📄 报告已保存至: {args.output}")
    
    print(report)


if __name__ == "__main__":
    main()
