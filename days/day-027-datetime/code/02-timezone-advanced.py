"""
Day 027 — 时区处理进阶

学习目标：
1. 使用 zoneinfo 进行时区转换（Python 3.9+）
2. 使用 pytz 进行时区转换（兼容旧版 Python）
3. 理解 naive vs aware datetime
4. 实战：跨时区会议安排系统

运行方式：
    python 02-timezone-advanced.py
"""

# ============================================================================
# 第一部分：导入模块
# ============================================================================
from datetime import datetime, date, time, timezone, timedelta
import sys

# ============================================================================
# 第二部分：zoneinfo 模块（Python 3.9+ 内置）
# ============================================================================
print("=" * 70)
print("🌍 Part 1: zoneinfo — 现代时区处理 (Python 3.9+)")
print("=" * 70)

# 检查 Python 版本
print(f"Python 版本: {sys.version}")

try:
    from zoneinfo import ZoneInfo, available_timezones
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False
    print("⚠️ zoneinfo 不可用（需要 Python 3.9+），跳过 zoneinfo 部分")
    # 创建一个替代类方便代码演示
    class ZoneInfo:
        def __init__(self, key):
            self.key = key
        def __str__(self):
            return self.key

if HAS_ZONEINFO:
    # 1.1 ZoneInfo 基础知识
    print("\n--- 1.1 ZoneInfo 基础知识 ---")

    # 获取所有可用时区（仅显示前10个）
    all_zones = list(available_timezones())
    print(f"系统中共有 {len(all_zones)} 个时区")

    # 常见时区预览
    common_zones = [
        'Asia/Shanghai',
        'Asia/Tokyo',
        'America/New_York',
        'America/Los_Angeles',
        'Europe/London',
        'Europe/Berlin',
        'Australia/Sydney',
        'Pacific/Auckland',
    ]
    print("常见时区:")
    for zone_name in common_zones:
        z = ZoneInfo(zone_name)
        print(f"  - {zone_name}")

    # 1.2 创建 aware datetime
    print("\n--- 1.2 创建 aware datetime ---")

    # 正确方式：创建时直接传入 tzinfo=ZoneInfo()
    beijing = ZoneInfo('Asia/Shanghai')
    dt_beijing = datetime(2026, 6, 18, 9, 15, 30, tzinfo=beijing)
    print(f"北京时间: {dt_beijing}")
    print(f"  tzinfo: {dt_beijing.tzinfo}")
    print(f"  utc offset: {dt_beijing.utcoffset()}")

    # 1.3 时区转换
    print("\n--- 1.3 时区转换 ---")

    # 从北京转换到纽约
    new_york = ZoneInfo('America/New_York')
    dt_ny = dt_beijing.astimezone(new_york)
    print(f"北京时间:   {dt_beijing.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"纽约时间:   {dt_ny.strftime('%Y-%m-%d %H:%M %Z')}")

    # 伦敦（注意夏令时）
    london = ZoneInfo('Europe/London')
    dt_london = dt_beijing.astimezone(london)
    print(f"伦敦时间:   {dt_london.strftime('%Y-%m-%d %H:%M %Z')}")

    # 东京（无夏令时，UTC+9）
    tokyo = ZoneInfo('Asia/Tokyo')
    dt_tokyo = dt_beijing.astimezone(tokyo)
    print(f"东京时间:   {dt_tokyo.strftime('%Y-%m-%d %H:%M %Z')}")

    # 1.4 查看时区的 DST 信息
    print("\n--- 1.4 夏令时 (DST) 信息 ---")

    # 纽约在不同季节的偏移
    summer = datetime(2026, 7, 1, 12, 0, tzinfo=new_york)
    winter = datetime(2026, 1, 1, 12, 0, tzinfo=new_york)

    print(f"纽约夏季 (7月) 偏移: {summer.utcoffset()} - DST: {summer.dst()}")
    print(f"纽约冬季 (1月) 偏移: {winter.utcoffset()} - DST: {winter.dst()}")

    # 北京没有夏令时
    summer_bj = datetime(2026, 7, 1, 12, 0, tzinfo=beijing)
    winter_bj = datetime(2026, 1, 1, 12, 0, tzinfo=beijing)
    print(f"北京夏季偏移: {summer_bj.utcoffset()} - DST: {summer_bj.dst()}")
    print(f"北京冬季偏移: {winter_bj.utcoffset()} - DST: {winter_bj.dst()}")

    # 1.5 时区与 UTC 偏移的区别
    print("\n--- 1.5 ZoneInfo vs 固定偏移 ---")

    # timezone(timedelta(hours=8)) 只是固定偏移
    fixed_utc8 = timezone(timedelta(hours=8))
    dt_fixed = datetime(2026, 6, 18, 9, 15, tzinfo=fixed_utc8)

    # ZoneInfo('Asia/Shanghai') 包含完整时区历史
    dt_zone = datetime(2026, 6, 18, 9, 15, tzinfo=ZoneInfo('Asia/Shanghai'))

    print(f"固定偏移 UTC+8: {dt_fixed}")
    print(f"上海时区:       {dt_zone}")
    print(f"两者相等: {dt_fixed == dt_zone}")  # True（当前时间相同）
    print("但在历史上的时间点可能不同（时区偏移可能变化过）")

else:
    print("\n⚠️ 当前 Python 版本不支持 zoneinfo，演示跳过")
    print("   建议升级到 Python 3.9+ 后重新运行此文件")

# ============================================================================
# 第三部分：pytz 兼容方案
# ============================================================================
print("\n" + "=" * 70)
print("📦 Part 2: pytz — 传统时区处理 (兼容方案)")
print("=" * 70)

try:
    import pytz
    HAS_PYTZ = True
    print(f"pytz 版本: {pytz.__version__ if hasattr(pytz, '__version__') else '已安装'}")
except ImportError:
    HAS_PYTZ = False
    print("⚠️ pytz 未安装，跳过 pytz 部分")

if HAS_PYTZ:
    # 2.1 pytz 的基本用法
    print("\n--- 2.1 pytz 基础 ---")

    # ⚠️ pytz 的特殊性：不能直接传 tzinfo 给 datetime
    # ❌ 错误方式
    beijing_pytz = pytz.timezone('Asia/Shanghai')
    # wrong = datetime(2026, 6, 18, 9, 15, tzinfo=beijing_pytz)
    # 以上用法在 pytz 中结果不正确！

    # ✅ 正确方式：使用 localize
    dt_naive = datetime(2026, 6, 18, 9, 15)
    dt_beijing_pytz = beijing_pytz.localize(dt_naive)
    print(f"pytz 本地化北京: {dt_beijing_pytz}")

    # 2.2 pytz 时区转换
    print("\n--- 2.2 pytz 时区转换 ---")

    new_york_pytz = pytz.timezone('America/New_York')
    dt_ny_pytz = dt_beijing_pytz.astimezone(new_york_pytz)
    print(f"北京时间 (pytz): {dt_beijing_pytz.strftime('%Y-%m-%d %H:%M %Z%z')}")
    print(f"纽约时间 (pytz): {dt_ny_pytz.strftime('%Y-%m-%d %H:%M %Z%z')}")

    # 2.3 时区列表查询
    print(f"\n--- 2.3 可用时区 ---")
    print(f"pytz 共有 {len(pytz.common_timezones)} 个常用时区")
    print("前10个常用时区:")
    for tz in pytz.common_timezones[:10]:
        print(f"  - {tz}")

# ============================================================================
# 第四部分：Naive vs Aware — 核心概念
# ============================================================================
print("\n" + "=" * 70)
print("🎯 Part 3: Naive vs Aware — 核心概念")
print("=" * 70)

# 3.1 两种类型的定义
print("\n--- 3.1 两种类型 ---")

naive = datetime(2026, 6, 18, 9, 15)
aware = datetime(2026, 6, 18, 9, 15, tzinfo=ZoneInfo('Asia/Shanghai') if HAS_ZONEINFO else timezone.utc)

print(f"Naive datetime: {naive}  (tzinfo={naive.tzinfo})")
print(f"Aware datetime: {aware}  (tzinfo={aware.tzinfo})")

# 3.2 混用的后果
print("\n--- 3.2 Naive 和 Aware 不能混合运算 ---")

try:
    # 这会抛出 TypeError
    result = aware - naive
    print(f"  相减结果: {result}")
except TypeError as e:
    print(f"  ❌ 错误: {e}")
    print("  → 解决方案见下方")

# 3.3 解决方案
print("\n--- 3.3 统一类型的方法 ---")

# 方案 A：给 naive 加上时区（假设它是本地时间）
naive_as_utc = naive.replace(tzinfo=timezone.utc)
result_a = aware - naive_as_utc
print(f"  方案 A (假设 naive 是 UTC): {result_a}")

# 方案 B：去掉 aware 的时区信息
aware_as_naive = aware.replace(tzinfo=None)
result_b = aware_as_naive - naive
print(f"  方案 B (去掉 aware 的时区): {result_b}")

# 3.4 最佳实践
print("\n--- 3.4 最佳实践 ---")
print("✅ 永远使用 aware datetime 存储时间")
print("✅ 在存储到数据库时，统一使用 UTC")
print("✅ 只在显示时转换到本地时区")
print("✅ 使用 datetime.now(timezone.utc) 替代 datetime.utcnow()")

# ============================================================================
# 第五部分：UTC vs 本地时间
# ============================================================================
print("\n" + "=" * 70)
print("🔄 Part 4: UTC vs 本地时间")
print("=" * 70)

print("\n--- UTC 存储，本地显示原则 ---")

# 模拟：用户输入的本地时间
user_input = datetime(2026, 6, 18, 9, 15)
user_tz = ZoneInfo('Asia/Shanghai') if HAS_ZONEINFO else timezone.utc
local_dt = user_input.replace(tzinfo=user_tz)

# 转成 UTC 存储
utc_dt = local_dt.astimezone(timezone.utc)
print(f"用户输入 (上海): {local_dt}")
print(f"存储到数据库 (UTC): {utc_dt}")

# 从数据库读取后，转换回用户本地时区
retrieved = utc_dt.astimezone(ZoneInfo('Asia/Shanghai') if HAS_ZONEINFO else timezone.utc)
print(f"读取后转换回上海: {retrieved}")

# 纽约用户看到的时间
ny_user = utc_dt.astimezone(ZoneInfo('America/New_York') if HAS_ZONEINFO else timezone.utc)
print(f"纽约用户看到: {ny_user.strftime('%Y-%m-%d %H:%M %Z')}")

# ============================================================================
# 第六部分：实战 — 跨时区会议安排系统
# ============================================================================
print("\n" + "=" * 70)
print("🏢 Part 5: 实战 — 跨时区会议安排系统")
print("=" * 70)


class MeetingScheduler:
    """
    跨时区会议安排器

    功能：
    - 在指定时区创建会议
    - 显示所有参会者的本地时间
    - 检查时间是否在参会者的工作时间范围内
    """

    # 常用城市时区映射（中英文名均可）
    CITY_TIMEZONES = {
        '北京': 'Asia/Shanghai',
        '上海': 'Asia/Shanghai',
        'Shanghai': 'Asia/Shanghai',
        '东京': 'Asia/Tokyo',
        'Tokyo': 'Asia/Tokyo',
        '首尔': 'Asia/Seoul',
        '新加坡': 'Asia/Singapore',
        '孟买': 'Asia/Kolkata',
        '迪拜': 'Asia/Dubai',
        '柏林': 'Europe/Berlin',
        '巴黎': 'Europe/Paris',
        '伦敦': 'Europe/London',
        'London': 'Europe/London',
        '纽约': 'America/New_York',
        'New_York': 'America/New_York',
        'New York': 'America/New_York',
        '芝加哥': 'America/Chicago',
        '丹佛': 'America/Denver',
        '洛杉矶': 'America/Los_Angeles',
        '悉尼': 'Australia/Sydney',
        'Sydney': 'Australia/Sydney',
        '奥克兰': 'Pacific/Auckland',
    }

    # 默认工作时间（9:00-18:00）
    WORK_START = 9
    WORK_END = 18

    def __init__(self, use_zoneinfo=True):
        self.use_zoneinfo = use_zoneinfo and HAS_ZONEINFO

    def _get_tz(self, city_or_zone: str):
        """根据城市名或时区名获取时区对象"""
        # 如果是城市名，查表
        if city_or_zone in self.CITY_TIMEZONES:
            zone_name = self.CITY_TIMEZONES[city_or_zone]
        else:
            zone_name = city_or_zone

        if self.use_zoneinfo:
            return ZoneInfo(zone_name)
        else:
            # 退回到 pytz
            return pytz.timezone(zone_name)

    def schedule_meeting(
        self,
        host_city: str,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int = 0
    ) -> dict:
        """
        安排会议

        Args:
            host_city: 主持人所在城市
            year/month/day/hour/minute: 会议的本地时间

        Returns:
            包含各城市时间的字典
        """
        host_tz = self._get_tz(host_city)

        # 创建 aware datetime
        if self.use_zoneinfo:
            meeting_time = datetime(year, month, day, hour, minute, tzinfo=host_tz)
        else:
            meeting_time = host_tz.localize(datetime(year, month, day, hour, minute))

        # 转成 UTC 作为基准
        meeting_utc = meeting_time.astimezone(timezone.utc)

        result = {
            'meeting_utc': meeting_utc.strftime('%Y-%m-%d %H:%M UTC'),
            'host': {
                'city': host_city,
                'local_time': meeting_time.strftime('%Y-%m-%d %H:%M %Z'),
            },
            'all_cities': {},
            'ok_for': [],
            'warning_for': [],
        }

        # 计算每个城市的本地时间
        for city in self.CITY_TIMEZONES:
            try:
                tz = self._get_tz(city)
                local = meeting_utc.astimezone(tz)
                local_hour = local.hour
                result['all_cities'][city] = {
                    'time': local.strftime('%H:%M'),
                    'date': local.strftime('%Y-%m-%d'),
                    'tz': local.strftime('%Z'),
                    'in_work_hours': self.WORK_START <= local_hour < self.WORK_END,
                }

                if result['all_cities'][city]['in_work_hours']:
                    result['ok_for'].append(city)
                else:
                    result['warning_for'].append(city)
            except Exception as e:
                result['all_cities'][city] = {'error': str(e)}

        return result

    def display_meeting(self, result: dict):
        """以友好的方式显示会议信息"""
        print(f"\n📅 会议时间 (UTC): {result['meeting_utc']}")
        print(f"👤 主持人 ({result['host']['city']}): {result['host']['local_time']}")
        print()

        # 分页显示
        all_cities = list(result['all_cities'].keys())

        print("全球各地时间:")
        print(f"{'城市':<10} {'日期':<12} {'时间':<10} {'时区':<8} {'工作时间内':<10}")
        print("-" * 55)
        for city in all_cities:
            info = result['all_cities'][city]
            if 'error' in info:
                print(f"{city:<10} ⚠️ {info['error']}")
            else:
                status = "✅" if info['in_work_hours'] else "❌"
                tz_short = info['tz'][:6]
                print(f"{city:<10} {info['date']:<12} {info['time']:<10} {tz_short:<8} {status}")

        print()

        if result['ok_for']:
            print(f"✅ 适合以下城市的参会者 ({len(result['ok_for'])} 个):")
            print(f"   {', '.join(result['ok_for'])}")

        if result['warning_for']:
            print(f"⚠️ 不适合以下城市的参会者 ({len(result['warning_for'])} 个):")
            print(f"   {', '.join(result['warning_for'])}")


# 测试会议安排器
print("\n--- 测试 1: 北京下午 3 点的会议 ---")
scheduler = MeetingScheduler(use_zoneinfo=HAS_ZONEINFO)
result = scheduler.schedule_meeting('北京', 2026, 6, 18, 15, 0)
scheduler.display_meeting(result)

print("\n" + "-" * 60)
print("\n--- 测试 2: 纽约上午 10 点的会议 ---")
result2 = scheduler.schedule_meeting('New_York', 2026, 6, 18, 10, 0)
scheduler.display_meeting(result2)

print("\n" + "-" * 60)
print("\n--- 测试 3: 伦敦下午 2 点的会议 ---")
result3 = scheduler.schedule_meeting('伦敦', 2026, 6, 19, 14, 0)
scheduler.display_meeting(result3)


# ============================================================================
# 第七部分：DST 过渡期处理
# ============================================================================
print("\n" + "=" * 70)
print("🕰️ Part 6: DST 过渡期处理 (夏令时切换)")
print("=" * 70)

if HAS_ZONEINFO:
    print("\n--- DST 开始: 春季拨快 ---")
    # 美国 2026 年夏令时开始：3月8日凌晨2点 → 3点
    try:
        before_dst = datetime(2026, 3, 8, 1, 59, 59, tzinfo=ZoneInfo('America/New_York'))
        print(f"DST 前: {before_dst}")
        print(f"  偏移: {before_dst.utcoffset()}")

        after_dst = datetime(2026, 3, 8, 3, 0, 0, tzinfo=ZoneInfo('America/New_York'))
        print(f"DST 后: {after_dst}")
        print(f"  偏移: {after_dst.utcoffset()}")

        # 凌晨 2:00-2:59 这段时间不存在（被跳过）
        print("\n注意: 2:00 AM 到 2:59 AM 这个小时在 DST 开始日不存在!")
    except Exception as e:
        print(f"  时区数据错误: {e}")

    print("\n--- DST 结束: 秋季拨慢 ---")
    # 美国 2026 年夏令时结束：11月1日凌晨2点 → 1点
    dst_end = datetime(2026, 11, 1, 1, 59, 59, tzinfo=ZoneInfo('America/New_York'))
    print(f"DST 结束前: {dst_end}")
    print(f"  偏移: {dst_end.utcoffset()}")

    # 凌晨 1:00-1:59 会出现两次！
    print("\n注意: 凌晨 1:00-1:59 会出现两次!")
    print("第一次: EDT (UTC-4)")
    print("第二次: EST (UTC-5)")

# ============================================================================
# 第八部分：最佳实践总结
# ============================================================================
print("\n" + "=" * 70)
print("📋 Part 7: 时区处理最佳实践")
print("=" * 70)

print("""
1️⃣ 存储原则
   ✅ 数据库永远存 UTC
   ✅ 使用 aware datetime (带时区信息)
   ❌ 不要存带时区的字符串，存时间戳或 UTC

2️⃣ 显示原则
   ✅ 显示时根据用户时区转换
   ✅ 明确显示时区信息（如 UTC+8）
   ❌ 不要在显示时猜测用户的时区

3️⃣ 计算原则
   ✅ 先将所有时间转到 UTC 再计算
   ✅ 统一时区后再比较
   ❌ 不允许 naive 和 aware 混用

4️⃣ 开发建议
   ✅ Python 3.9+ 优先使用 zoneinfo
   ✅ 兼容旧版 Python 时使用 pytz
   ✅ 永远用 localize() 而不是直接传 tzinfo (pytz)

5️⃣ 测试建议
   ✅ 测试 DST 切换日
   ✅ 测试不同时区的跨天情况
   ✅ 测试闰年 2月29日
""")

print("\n✅ Day 027 — 时区处理进阶完成！")
