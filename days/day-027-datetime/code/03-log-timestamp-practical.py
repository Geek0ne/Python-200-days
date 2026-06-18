"""
Day 027 — 实战：日志时间戳解析器

学习目标：
1. 解析多种格式的日志时间戳
2. 处理时区信息
3. 实现时间过滤和分析功能
4. 实战场景：日志分析工具箱

运行方式：
    python 03-log-timestamp-practical.py
"""

# ============================================================================
# 第一部分：导入模块
# ============================================================================
from datetime import datetime, date, time, timezone, timedelta
from typing import Optional, Generator
import re
import json

# 尝试导入 zoneinfo（Python 3.9+）
try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False
    # 降级方案
    class ZoneInfo:
        def __init__(self, key):
            self.key = key
        def __str__(self):
            return self.key


# ============================================================================
# 第二部分：日志时间戳解析器
# ============================================================================
print("=" * 70)
print("📝 Part 1: 日志时间戳解析器")
print("=" * 70)


class LogTimestampParser:
    """
    多格式日志时间戳解析器

    支持常见的日志时间格式：
    - Nginx/Apache 格式: 18/Jun/2026:09:15:30 +0800
    - ISO 8601 格式: 2026-06-18T09:15:30+08:00
    - Python 默认格式: 2026-06-18 09:15:30.123456
    - Unix 日志格式: Jun 18 09:15:30
    - Syslog 格式: 2026-06-18T09:15:30.123456Z
    """

    # 预定义的时间格式模板
    TIME_FORMATS = {
        'nginx': '%d/%b/%Y:%H:%M:%S %z',
        'apache': '[%d/%b/%Y:%H:%M:%S %z]',
        'iso_with_tz': '%Y-%m-%dT%H:%M:%S%z',
        'iso_with_tz_micro': '%Y-%m-%dT%H:%M:%S.%f%z',
        'iso_space': '%Y-%m-%d %H:%M:%S',
        'iso_space_micro': '%Y-%m-%d %H:%M:%S.%f',
        'syslog_rfc3339': '%Y-%m-%dT%H:%M:%S.%fZ',
        'unix_syslog': '%b %d %H:%M:%S',
        'us_date': '%m/%d/%Y %H:%M:%S',
        'compact': '%Y%m%d_%H%M%S',
    }

    @staticmethod
    def parse_timestamp(time_str: str) -> Optional[datetime]:
        """
        自动检测格式并解析时间字符串

        Args:
            time_str: 时间字符串

        Returns:
            datetime 对象（如果解析失败则返回 None）
        """
        # 去除首尾空白
        time_str = time_str.strip()

        # 尝试所有预定义格式
        for fmt_name, fmt in LogTimestampParser.TIME_FORMATS.items():
            try:
                dt = datetime.strptime(time_str, fmt)
                # 如果是 naive datetime，设为 UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        # 如果都不匹配，尝试正则提取
        return LogTimestampParser._regex_fallback(time_str)

    @staticmethod
    def _regex_fallback(time_str: str) -> Optional[datetime]:
        """正则表达式兜底方案"""
        patterns = [
            # ISO 格式带 T 和 Z
            r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z',
            # ISO 格式带时区偏移 ±HH:MM
            r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?([+-]\d{2}):(\d{2})',
            # Nginx 格式
            r'(\d{2})/(\w{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})\s+([+-]\d{4})',
            # 标准 YYYY-MM-DD HH:MM:SS
            r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})',
        ]

        for pattern in patterns:
            m = re.match(pattern, time_str)
            if m:
                groups = m.groups()
                if len(groups) == 6:
                    # YYYY-MM-DD HH:MM:SS
                    return datetime(
                        int(groups[0]), int(groups[1]), int(groups[2]),
                        int(groups[3]), int(groups[4]), int(groups[5]),
                        tzinfo=timezone.utc
                    )
                elif len(groups) == 7 and '+' in groups[6] or '-' in groups[6]:
                    # Nginx 格式 +0800
                    offset_str = groups[6]
                    offset_hours = int(offset_str[:3])
                    offset_minutes = int(offset_str[3:] or '0')
                    tz = timezone(timedelta(hours=offset_hours, minutes=offset_minutes))
                    return datetime(
                        int(groups[2]),
                        LogTimestampParser._month_to_num(groups[1]),
                        int(groups[0]),
                        int(groups[3]), int(groups[4]), int(groups[5]),
                        tzinfo=tz
                    )

        return None

    @staticmethod
    def _month_to_num(month_str: str) -> int:
        """将英文月份缩写转为数字"""
        months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
            'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
            'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
        }
        return months.get(month_str.capitalize(), 1)

    @staticmethod
    def format_datetime(dt: datetime, fmt_name: str = 'iso_space') -> str:
        """将 datetime 格式化为指定格式"""
        fmt = LogTimestampParser.TIME_FORMATS.get(fmt_name)
        if fmt:
            return dt.strftime(fmt)
        return dt.isoformat()

    @staticmethod
    def list_supported_formats():
        """列出所有支持的格式"""
        print("\n支持的日志时间格式:")
        print(f"{'格式名':<20} {'格式模板':<35} {'示例'}")
        print("-" * 90)
        for name, fmt in LogTimestampParser.TIME_FORMATS.items():
            try:
                # 生成一个示例
                example_dt = datetime(2026, 6, 18, 9, 15, 30, 123456,
                                      tzinfo=timezone(timedelta(hours=8)))
                example = example_dt.strftime(fmt)
                print(f"{name:<20} {fmt:<35} {example}")
            except Exception:
                print(f"{name:<20} {fmt:<35} (依赖输入)")


# 测试解析器
parser = LogTimestampParser()
parser.list_supported_formats()

# 测试各种格式的解析
print("\n" + "=" * 70)
print("🔍 Part 2: 解析测试")
print("=" * 70)

test_cases = [
    "18/Jun/2026:09:15:30 +0800",
    "2026-06-18T09:15:30+08:00",
    "2026-06-18 09:15:30.123456",
    "Jun 18 09:15:30",
    "2026-06-18T09:15:30.123456Z",
    "06/18/2026 09:15:30",
    "20260618_091530",
    "2026-06-18 09:15:30",
]

for case in test_cases:
    result = parser.parse_timestamp(case)
    if result:
        print(f"  ✅ '{case}'")
        print(f"     → ISO: {result.isoformat()}")
        print(f"     → UTC: {result.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print()
    else:
        print(f"  ❌ '{case}' → 解析失败")


# ============================================================================
# 第三部分：日志分析工具箱
# ============================================================================
print("=" * 70)
print("🔧 Part 3: 日志分析工具箱")
print("=" * 70)


class LogAnalyzer:
    """
    日志时间分析器

    支持：
    - 解析多条日志中的时间戳
    - 按时间范围过滤
    - 按小时/天/周统计日志量
    - 计算响应时间
    """

    def __init__(self):
        self.entries: list[dict] = []

    def parse_log_line(self, line: str, timestamp_pattern: str = None) -> Optional[dict]:
        """
        解析单行日志

        Args:
            line: 日志行
            timestamp_pattern: 时间戳的正则模式（可选）

        Returns:
            解析后的字典，包含时间戳和其他字段
        """
        line = line.strip()
        if not line:
            return None

        # 如果提供了正则模式，使用它提取时间戳
        if timestamp_pattern:
            m = re.search(timestamp_pattern, line)
            if m:
                time_str = m.group(1) if m.lastindex else m.group(0)
                dt = parser.parse_timestamp(time_str)
            else:
                return None
        else:
            # 自动尝试从行首提取时间
            # 常见日志格式: "TIMESTAMP [LEVEL] message"
            words = line.split(None, 1)
            if not words:
                return None
            dt = parser.parse_timestamp(words[0])
            if dt is None:
                # 尝试前两个词（如 Jun 18 09:15:30）
                if len(words) > 1:
                    combined = words[0] + " " + words[1].split(None, 1)[0]
                    dt = parser.parse_timestamp(combined)
                    if dt:
                        return {
                            'timestamp': dt,
                            'raw': line,
                            'message': words[1].split(None, 1)[-1] if len(words[1].split(None, 1)) > 1 else ''
                        }
                return None

        message = words[1] if len(words) > 1 else ''
        return {
            'timestamp': dt,
            'raw': line,
            'message': message,
        }

    def add_entry(self, entry: dict):
        """添加一条解析后的日志条目"""
        if entry and 'timestamp' in entry:
            self.entries.append(entry)

    def filter_by_hour(self, hour: int) -> list[dict]:
        """过滤指定小时（0-23）的日志"""
        return [
            e for e in self.entries
            if e['timestamp'].hour == hour
        ]

    def filter_by_date(self, start_date: date, end_date: date) -> list[dict]:
        """按日期范围过滤"""
        return [
            e for e in self.entries
            if start_date <= e['timestamp'].date() <= end_date
        ]

    def filter_by_time_range(self, start: datetime, end: datetime) -> list[dict]:
        """按时间范围过滤（aware datetime）"""
        return [
            e for e in self.entries
            if start <= e['timestamp'] <= end
        ]

    def hourly_distribution(self) -> dict:
        """按小时统计日志数量"""
        dist = {h: 0 for h in range(24)}
        for e in self.entries:
            hour = e['timestamp'].hour
            dist[hour] = dist.get(hour, 0) + 1
        return dist

    def daily_distribution(self) -> dict:
        """按天统计日志数量"""
        dist = {}
        for e in self.entries:
            day = e['timestamp'].strftime('%Y-%m-%d')
            dist[day] = dist.get(day, 0) + 1
        return dict(sorted(dist.items()))

    def summary(self) -> dict:
        """生成日志摘要统计"""
        if not self.entries:
            return {'count': 0}

        timestamps = [e['timestamp'] for e in self.entries]

        return {
            'count': len(self.entries),
            'start_time': min(timestamps).isoformat(),
            'end_time': max(timestamps).isoformat(),
            'duration': str(max(timestamps) - min(timestamps)),
            'hourly_distribution': self.hourly_distribution(),
            'daily_distribution': self.daily_distribution(),
        }


# ============================================================================
# 第四部分：生成模拟日志并分析
# ============================================================================
print("=" * 70)
print("📊 Part 4: 模拟日志分析演示")
print("=" * 70)


def generate_sample_logs() -> list[str]:
    """生成模拟的系统日志"""
    from datetime import datetime as dt
    import random

    messages = [
        "INFO - User login successful - user_id=1234",
        "WARN - High memory usage - 85%",
        "ERROR - Database connection timeout - retry=3",
        "INFO - Request processed in 245ms - /api/users",
        "DEBUG - Cache miss for key=user:1234",
        "ERROR - 500 Internal Server Error - /api/orders",
        "INFO - Scheduled job completed - cleanup_old_sessions",
        "WARN - SSL certificate expires in 30 days",
        "INFO - New user registration - user_id=5678",
        "ERROR - Disk space warning - /dev/sda1 92% full",
        "INFO - Backup completed - size=2.3GB",
        "WARN - API rate limit approaching - 85/100",
    ]

    logs = []
    base_time = dt(2026, 6, 15, 0, 0, 0, tzinfo=timezone.utc)

    for i in range(50):
        # 时间逐步递增，间隔 5-60 分钟
        offset = timedelta(
            hours=i // 4,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )
        log_time = base_time + offset
        message = random.choice(messages)

        # 使用多种时间格式输出
        if i % 3 == 0:
            # Nginx 格式
            time_fmt = log_time.strftime('%d/%b/%Y:%H:%M:%S %z')
        elif i % 3 == 1:
            # ISO 格式
            time_fmt = log_time.strftime('%Y-%m-%dT%H:%M:%S%z')
        else:
            # 标准格式
            time_fmt = log_time.strftime('%Y-%m-%d %H:%M:%S')

        logs.append(f"{time_fmt} - {message}")

    return logs


# 生成并分析日志
sample_logs = generate_sample_logs()
print(f"\n生成 {len(sample_logs)} 条模拟日志，预览前5条:\n")
for log in sample_logs[:5]:
    print(f"  {log}")

print("\n" + "-" * 50)

# 使用分析器处理
analyzer = LogAnalyzer()
parse_errors = []

for log in sample_logs:
    entry = analyzer.parse_log_line(log)
    if entry:
        analyzer.add_entry(entry)
    else:
        parse_errors.append(log)

print(f"成功解析: {len(analyzer.entries)}, 解析失败: {len(parse_errors)}")

# 生成统计摘要
summary = analyzer.summary()
print(f"\n日志统计摘要:")
print(f"  总条数: {summary['count']}")
print(f"  开始时间: {summary['start_time']}")
print(f"  结束时间: {summary['end_time']}")
print(f"  时间跨度: {summary['duration']}")

print(f"\n每小时分布:")
for hour, count in summary['hourly_distribution'].items():
            if count > 0:
                bar = "█" * count
                print(f"  {hour:02d}:00  {bar} ({count})")

print(f"\n每天分布:")
for day, count in summary['daily_distribution'].items():
    print(f"  {day}: {count} 条")


# ============================================================================
# 第五部分：响应时间计算器
# ============================================================================
print("\n" + "=" * 70)
print("⏱️ Part 5: 响应时间计算器")
print("=" * 70)


class ResponseTimeCalculator:
    """
    计算 HTTP 请求响应时间
    
    假设日志格式：
    2026-06-18 09:15:30.123 - START - request_id=abc123
    2026-06-18 09:15:30.456 - END - request_id=abc123
    """

    def __init__(self):
        self.requests: dict[str, dict] = {}

    def parse_and_record(self, log_line: str) -> Optional[float]:
        """
        解析日志行并记录请求开始/结束

        Returns:
            如果请求完成，返回响应时间（秒）；否则返回 None
        """
        # 匹配格式: "TIMESTAMP - START|END - request_id=XXX"
        pattern = r'([\d/:\s+\-TZ.]+)\s*-\s*(START|END)\s*-\s*request_id=(\S+)'
        m = re.match(pattern, log_line.strip())
        if not m:
            return None

        time_str = m.group(1).strip()
        event_type = m.group(2)
        request_id = m.group(3)

        # 解析时间戳
        dt = parser.parse_timestamp(time_str)
        if dt is None:
            return None

        if event_type == 'START':
            self.requests[request_id] = {'start': dt}
            return None
        elif event_type == 'END':
            if request_id in self.requests and 'start' in self.requests[request_id]:
                start_time = self.requests[request_id]['start']
                response_time = (dt - start_time).total_seconds()
                self.requests[request_id]['end'] = dt
                self.requests[request_id]['response_time'] = response_time
                return response_time

        return None

    def stats(self) -> dict:
        """计算响应时间统计"""
        times = [
            v['response_time'] for v in self.requests.values()
            if 'response_time' in v
        ]
        if not times:
            return {'count': 0}

        return {
            'count': len(times),
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times),
            'p50': sorted(times)[len(times) // 2],
            'p95': sorted(times)[int(len(times) * 0.95)],
            'p99': sorted(times)[int(len(times) * 0.99)],
        }


# 测试响应时间计算器
print("\n模拟的请求日志:")
simulated_logs = [
    "2026-06-18 09:15:30.123 - START - request_id=abc123",
    "2026-06-18 09:15:30.456 - END - request_id=abc123",
    "2026-06-18 09:16:00.000 - START - request_id=def456",
    "2026-06-18 09:16:02.500 - END - request_id=def456",
    "2026-06-18 09:16:05.000 - START - request_id=ghi789",
    "2026-06-18 09:16:05.050 - END - request_id=ghi789",
    "2026-06-18 09:17:00.000 - START - request_id=jkl012",
    "2026-06-18 09:17:10.000 - END - request_id=jkl012",
]

calc = ResponseTimeCalculator()
for log in simulated_logs:
    result = calc.parse_and_record(log)
    if result is not None:
        print(f"  ✅ 请求完成: {result*1000:.1f}ms")
    else:
        print(f"  📝 记录请求: {log.split('-')[2].strip()}")

stats = calc.stats()
print(f"\n响应时间统计:")
if stats['count'] > 0:
    print(f"  请求总数: {stats['count']}")
    print(f"  最小: {stats['min']*1000:.1f}ms")
    print(f"  最大: {stats['max']*1000:.1f}ms")
    print(f"  平均: {stats['avg']*1000:.1f}ms")
    print(f"  P50:  {stats['p50']*1000:.1f}ms")
    print(f"  P95:  {stats['p95']*1000:.1f}ms")
    print(f"  P99:  {stats['p99']*1000:.1f}ms")


# ============================================================================
# 第六部分：UTC ⇄ 本地时间批量转换器
# ============================================================================
print("\n" + "=" * 70)
print("🔄 Part 6: 批量时间戳转换器")
print("=" * 70)


class BatchTimestampConverter:
    """批量时间戳转换器"""

    @staticmethod
    def convert_batch(
        timestamps: list,
        input_format: str = 'timestamp',
        target_tz: str = 'Asia/Shanghai',
    ) -> list[dict]:
        """
        批量转换时间戳

        Args:
            timestamps: 时间列表（可以是时间戳或字符串）
            input_format: 输入格式（'timestamp' 或 'iso'）
            target_tz: 目标时区

        Returns:
            转换结果列表
        """
        results = []

        # 获取目标时区
        try:
            if HAS_ZONEINFO:
                target = ZoneInfo(target_tz)
            else:
                import pytz
                target = pytz.timezone(target_tz)
        except Exception:
            target = timezone.utc

        for ts in timestamps:
            if input_format == 'timestamp':
                # 输入是 Unix 时间戳
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    continue
            elif input_format == 'iso':
                # 输入是 ISO 字符串
                dt = parser.parse_timestamp(ts)
                if dt is None:
                    results.append({
                        'input': ts,
                        'error': '无法解析'
                    })
                    continue
            else:
                continue

            # 转换到目标时区
            local_dt = dt.astimezone(target)

            results.append({
                'input': ts,
                'utc': dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'local': local_dt.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'timestamp': dt.timestamp(),
                'iso': dt.isoformat(),
            })

        return results


# 测试批量转换
print("\n时间戳批量转换:")
converter = BatchTimestampConverter()
test_timestamps = [
    1755000000,
    1755086400,
    1755172800,
    1755259200,
]
results = converter.convert_batch(test_timestamps, input_format='timestamp')
for r in results:
    if 'error' in r:
        print(f"  ❌ {r['input']}: {r['error']}")
    else:
        print(f"  📌 {r['input']}")
        print(f"     UTC: {r['utc']}")
        print(f"     上海: {r['local']}")
        print()


# ============================================================================
# 第七部分：完整日志分析流水线
# ============================================================================
print("=" * 70)
print("🚀 Part 7: 完整日志分析流水线")
print("=" * 70)


def log_analysis_demo():
    """完整的日志分析流水线演示"""
    print("\n步骤 1: 生成模拟日志")
    logs = generate_sample_logs()
    print(f"  生成了 {len(logs)} 条日志")

    print("\n步骤 2: 解析日志")
    analyzer = LogAnalyzer()
    for log in logs:
        entry = analyzer.parse_log_line(log)
        if entry:
            analyzer.add_entry(entry)
    print(f"  成功解析 {len(analyzer.entries)} 条")

    print("\n步骤 3: 统计摘要")
    summary = analyzer.summary()
    print(json.dumps({
        'count': summary['count'],
        'time_range': f"{summary['start_time']} → {summary['end_time']}",
        'duration': summary['duration'],
    }, indent=2))

    print("\n步骤 4: 按小时过滤（只看 9:00-17:00）")
    work_hours_logs = []
    for h in range(9, 18):
        work_hours_logs.extend(analyzer.filter_by_hour(h))
    print(f"  工作时间内日志: {len(work_hours_logs)} 条 (占 {len(work_hours_logs)/len(analyzer.entries)*100:.1f}%)")

    print("\n步骤 5: 按日期过滤")
    # 假设只关心 6月15日到6月16日
    filtered = analyzer.filter_by_date(date(2026, 6, 15), date(2026, 6, 16))
    print(f"  6月15日-16日的日志: {len(filtered)} 条")

    print("\n✅ 日志分析流水线完成！")


log_analysis_demo()


# ============================================================================
# 第八部分：要点总结
# ============================================================================
print("\n" + "=" * 70)
print("💡 实战要点总结")
print("=" * 70)

print("""
📌 日志时间戳解析要点:

1. 格式多样性
   - 不同系统使用不同时间格式
   - Nginx/ Apache 使用 18/Jun/2026:09:15:30 +0800
   - Syslog 使用 Jun 18 09:15:30
   - 现代系统倾向于 ISO 8601

2. 时区处理
   - 日志中可能有时区偏移 (+0800)
   - syslog 可能是 UTC（带 Z 后缀）
   - 没有时区信息的日志通常假设为本地时间

3. 性能考虑
   - 大量日志时，优先使用预编译正则
   - 顺序尝试格式匹配，最先匹配最快的格式
   - 考虑使用缓存（缓存已解析的日期部分）

4. 容错处理
   - 总有一些日志行格式特殊或损坏
   - 解析失败时要记录错误，不要中断流程
   - 提供兜底方案（正则提取）

5. 数据分析
   - 时间过滤 → 缩小分析范围
   - 时间聚合 → 发现趋势和异常
   - 响应时间 → 性能监控
""")

print("\n✅ Day 027 — 日志时间戳解析器完成！")
