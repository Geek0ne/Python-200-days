"""
Day 027 — datetime 基础用法

学习目标：
1. 创建和操作 date、time、datetime、timedelta 对象
2. 使用 strftime/strptime 进行格式化与解析
3. 掌握时间戳与 datetime 的相互转换
4. 理解 timedelta 的时间计算

运行方式：
    python 01-datetime-basics.py
"""

# ============================================================================
# 第一部分：导入模块
# ============================================================================
from datetime import date, time, datetime, timedelta, timezone

# ============================================================================
# 第二部分：date 对象 — 日期
# ============================================================================
print("=" * 60)
print("📅 date 对象 — 日期")
print("=" * 60)

# 2.1 创建 date 对象
d1 = date(2026, 6, 18)
print(f"指定日期: {d1}")  # 2026-06-18

# 获取今天的日期
today = date.today()
print(f"今天: {today}")

# 从时间戳创建
ts = 1755000000
d_from_ts = date.fromtimestamp(ts)
print(f"时间戳 {ts} 对应的日期: {d_from_ts}")

# 2.2 date 对象的属性
d = date(2026, 6, 18)
print(f"\n属性访问:")
print(f"  年: {d.year}")
print(f"  月: {d.month}")
print(f"  日: {d.day}")

# 2.3 date 对象的常用方法
print(f"\n常用方法:")
print(f"  星期几 (周一=0): {d.weekday()}")
print(f"  星期几 (周一=1): {d.isoweekday()}")
print(f"  ISO 日历: {d.isocalendar()}")
print(f"  替换年份: {d.replace(year=2025)}")

# 2.4 date 对象的比较
print(f"\n比较:")
print(f"  2026-06-18 > 2025-01-01: {d > date(2025, 1, 1)}")
print(f"  2026-06-18 == 2026-06-18: {d == date(2026, 6, 18)}")

# ============================================================================
# 第三部分：time 对象 — 时间
# ============================================================================
print("\n" + "=" * 60)
print("⏰ time 对象 — 时间")
print("=" * 60)

# 3.1 创建 time 对象
t1 = time(9, 15, 30)
print(f"指定时间: {t1}")  # 09:15:30

# 带微秒
t2 = time(9, 15, 30, 123456)
print(f"带微秒: {t2}")  # 09:15:30.123456

# 带时区
tz_shanghai = timezone(timedelta(hours=8))
t3 = time(9, 15, tzinfo=tz_shanghai)
print(f"带时区: {t3}")  # 09:15:00+08:00

# 3.2 time 对象的属性
t = time(14, 30, 45, 654321)
print(f"\n属性访问:")
print(f"  时: {t.hour}")
print(f"  分: {t.minute}")
print(f"  秒: {t.second}")
print(f"  微秒: {t.microsecond}")
print(f"  时区: {t.tzinfo}")

# 3.3 time 对象的不可变性
t_original = time(9, 0, 0)
t_new = t_original.replace(hour=10)
print(f"\n不可变性验证:")
print(f"  原对象: {t_original}  (未被修改)")
print(f"  新对象: {t_new}")

# ============================================================================
# 第四部分：datetime 对象 — 日期 + 时间
# ============================================================================
print("\n" + "=" * 60)
print("📆 datetime 对象 — 日期 + 时间")
print("=" * 60)

# 4.1 创建 datetime 对象的不同方式
print("\n创建方式:")

# 直接指定
dt1 = datetime(2026, 6, 18, 9, 15, 30)
print(f"  直接指定: {dt1}")

# 获取当前时间
now = datetime.now()
utc_now = datetime.utcnow()
print(f"  当前本地时间: {now}")
print(f"  当前 UTC 时间: {utc_now} (naive)")

# 更推荐的方式
now_aware = datetime.now(timezone.utc)
print(f"  当前 UTC (aware): {now_aware}")

# 从时间戳转换
dt_from_ts = datetime.fromtimestamp(ts)
print(f"  时间戳→本地: {dt_from_ts}")

dt_from_ts_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
print(f"  时间戳→UTC: {dt_from_ts_utc}")

# 组合 date 和 time
d = date(2026, 6, 18)
t = time(9, 15, 30)
combined = datetime.combine(d, t)
print(f"  combine date+time: {combined}")

# 4.2 datetime 对象的属性和方法
dt = datetime(2026, 6, 18, 9, 15, 30, 123456)
print(f"\n属性与方法:")

# 提取各部分
print(f"  提取日期 date(): {dt.date()}")
print(f"  提取时间 time(): {dt.time()}")
print(f"  提取星期 weekday(): {dt.weekday()}")

# 转时间戳
timestamp = dt.timestamp()
print(f"  转时间戳: {timestamp}")

# 替换部分字段
dt_replaced = dt.replace(year=2025, hour=0)
print(f"  替换字段: {dt_replaced}")

# ============================================================================
# 第五部分：timedelta — 时间差
# ============================================================================
print("\n" + "=" * 60)
print("⏳ timedelta — 时间差")
print("=" * 60)

# 5.1 创建 timedelta
print("\n创建 timedelta:")
td1 = timedelta(days=5)
td2 = timedelta(hours=3, minutes=30)
td3 = timedelta(weeks=2, days=1)  # weeks 自动转 days
print(f"  5天: {td1}")
print(f"  3小时30分: {td2}")
print(f"  2周1天: {td3}")

# 5.2 内部存储结构
print(f"\n内部结构:")
td = timedelta(hours=25, minutes=90, seconds=30)
print(f"  timedelta(hours=25, minutes=90, seconds=30):")
print(f"    days: {td.days}")           # 1
print(f"    seconds: {td.seconds}")     # 9030 (2.5h = 9000s + 30s)
print(f"    microseconds: {td.microseconds}")
print(f"    total_seconds(): {td.total_seconds()}")

# 5.3 timedelta 的运算
print(f"\n运算:")
start = datetime(2026, 6, 1, 9, 0)
end = datetime(2026, 6, 18, 9, 0)

# datetime - datetime = timedelta
delta = end - start
print(f"  {end} - {start} = {delta}")
print(f"  天数: {delta.days}")
print(f"  总秒数: {delta.total_seconds()}")

# datetime + timedelta = 新的 datetime
future = start + timedelta(days=7)
past = start - timedelta(hours=3)
print(f"  加7天: {future}")
print(f"  减3小时: {past}")

# timedelta 之间的运算
td_a = timedelta(days=3, hours=12)
td_b = timedelta(hours=8)
print(f"  timedelta 相加: {td_a + td_b}")
print(f"  timedelta 乘以2: {td_a * 2}")
print(f"  timedelta 除以2: {td_a / 2}")
print(f"  timedelta 取负: {-td_a}")

# ============================================================================
# 第六部分：strftime / strptime — 格式化与解析
# ============================================================================
print("\n" + "=" * 60)
print("📝 strftime / strptime — 格式化与解析")
print("=" * 60)

# 6.1 strftime: datetime → 字符串
dt = datetime(2026, 6, 18, 9, 15, 30, 123456)

print("\nstrftime (datetime → 字符串):")
# 常见格式
print(f"  ISO 格式: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  中文格式: {dt.strftime('%Y年%m月%d日 %H:%M')}")
print(f"  美国格式: {dt.strftime('%m/%d/%Y %I:%M %p')}")
print(f"  日志格式: {dt.strftime('%d/%b/%Y:%H:%M:%S')}")
print(f"  文件名: {dt.strftime('%Y%m%d_%H%M%S')}")
print(f"  完整格式: {dt.strftime('%A, %B %d, %Y')}")
print(f"  微秒: {dt.strftime('%Y-%m-%d %H:%M:%S.%f')}")

# 6.2 strptime: 字符串 → datetime
print("\nstrptime (字符串 → datetime):")
date_str = "2026-06-18 09:15:30"
fmt = "%Y-%m-%d %H:%M:%S"
parsed = datetime.strptime(date_str, fmt)
print(f"  '{date_str}' → {parsed}")

# 解析不同格式
formats = [
    ("2026/06/18", "%Y/%m/%d"),
    ("06/18/2026", "%m/%d/%Y"),
    ("18-Jun-2026", "%d-%b-%Y"),
    ("20260618_091530", "%Y%m%d_%H%M%S"),
    ("2026-06-18T09:15:30", "%Y-%m-%dT%H:%M:%S"),
]
for s, f in formats:
    parsed_dt = datetime.strptime(s, f)
    print(f"  '{s}' (格式: {f}) → {parsed_dt}")

# 6.3 带时区的解析
log_time = "18/Jun/2026:09:15:30 +0800"
fmt_tz = "%d/%b/%Y:%H:%M:%S %z"
parsed_tz = datetime.strptime(log_time, fmt_tz)
print(f"\n  带时区解析:")
print(f"  '{log_time}' → {parsed_tz}")

# 6.4 ISO 格式的快捷方式
iso_dt = datetime.fromisoformat("2026-06-18T09:15:30+08:00")
print(f"  fromisoformat: {iso_dt}")

# ============================================================================
# 第七部分：时间戳转换完整示例
# ============================================================================
print("\n" + "=" * 60)
print("🔄 时间戳转换完整示例")
print("=" * 60)


def timestamp_converter(ts: float = None) -> dict:
    """
    时间戳全能转换器

    Args:
        ts: Unix 时间戳（秒），None 表示当前时间

    Returns:
        包含各种时间表示的字典
    """
    if ts is None:
        ts = datetime.now().timestamp()

    dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
    dt_local = datetime.fromtimestamp(ts)

    return {
        "timestamp": ts,
        "timestamp_int": int(ts),
        "utc_iso": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "utc_readable": dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "local_iso": dt_local.strftime("%Y-%m-%d %H:%M:%S"),
        "local_readable": dt_local.strftime("%A, %B %d, %Y %I:%M %p"),
        "date_only": dt_local.strftime("%Y-%m-%d"),
        "time_only": dt_local.strftime("%H:%M:%S"),
        "compact": dt_local.strftime("%Y%m%d_%H%M%S"),
    }


# 测试时间戳转换
now_ts = datetime.now().timestamp()
result = timestamp_converter(now_ts)
for key, value in result.items():
    print(f"  {key}: {value}")

# 测试特定时间戳
print("\n特定时间戳 (1755000000):")
result2 = timestamp_converter(1755000000)
print(f"  对应时间: {result2['utc_iso']}")
print(f"  本地时间: {result2['local_iso']}")

# ============================================================================
# 第八部分：常见误区与验证
# ============================================================================
print("\n" + "=" * 60)
print("⚠️ 常见误区验证")
print("=" * 60)

# 误区 1：date 和 datetime 的继承关系
print("\n1. datetime 是 date 的子类:")
d1 = date(2026, 6, 18)
dt1 = datetime(2026, 6, 18, 9, 0)
print(f"   isinstance(d1, date): {isinstance(d1, date)}")  # True
print(f"   isinstance(dt1, date): {isinstance(dt1, date)}")  # True
print(f"   isinstance(d1, datetime): {isinstance(d1, datetime)}")  # False

# 误区 2：不可变性验证
print("\n2. datetime 不可变性:")
dt = datetime(2026, 6, 18, 9, 0)
print(f"   原对象 id: {id(dt)}")
dt_new = dt.replace(hour=10)
print(f"   新对象 id: {id(dt_new)}")
print(f"   id 不同 → 创建了新对象")

# 误区 3：timedelta 不能加月份
print("\n3. timedelta 没有月份参数:")
print("   timedelta(months=1) → TypeError")
print("   如果需加月份，使用 dateutil.relativedelta")

# 误区 4：strptime 的严格性
print("\n4. strptime 验证:")
# 下面这行会报 ValueError，因为 2 月没有 30 天
try:
    datetime.strptime("2026-02-30", "%Y-%m-%d")
    print("   成功！")
except ValueError as e:
    print(f"   预期错误: {e}")

# ============================================================================
# 第九部分：实用工具函数
# ============================================================================
print("\n" + "=" * 60)
print("🔧 实用工具函数")
print("=" * 60)


def days_until(target_date: date) -> int:
    """计算距离目标日期还有多少天"""
    today = date.today()
    delta = target_date - today
    return delta.days


def age_from_birthday(birthday: date) -> int:
    """根据生日计算当前年龄"""
    today = date.today()
    age = today.year - birthday.year
    # 如果今年生日还没过，减一岁
    if (today.month, today.day) < (birthday.month, birthday.day):
        age -= 1
    return age


def format_duration(seconds: float) -> str:
    """将秒数格式化为人类可读的时长字符串"""
    td = timedelta(seconds=seconds)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    parts.append(f"{secs}秒")
    return "".join(parts)


# 测试工具函数
print("\n工具函数测试:")

# 距离 2027-01-01
target = date(2027, 1, 1)
print(f"  距离 {target} 还有 {days_until(target)} 天")

# 年龄计算
birthday = date(1990, 5, 15)
print(f"  1990-05-15 出生, 当前年龄: {age_from_birthday(birthday)} 岁")

# 时长格式化
test_durations = [3661, 86400, 90061, 123456]
for secs in test_durations:
    print(f"  {secs} 秒 → {format_duration(secs)}")

print("\n✅ Day 027 — datetime 基础用法完成！")
