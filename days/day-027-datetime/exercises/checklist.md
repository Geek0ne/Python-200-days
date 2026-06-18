# Day 027 — 时间与日期 完成清单

## ✅ 今日完成检查

### 概念理解
- [ ] 理解时间戳（timestamp）的起源与设计原理（Unix Epoch）
- [ ] 理解结构化时间（年/月/日/时/分/秒）与时间戳的关系
- [ ] 掌握 `datetime` 模块四大核心类：`date`、`time`、`datetime`、`timedelta`
- [ ] 理解 `datetime` 继承自 `date` 的设计含义
- [ ] 理解 naive 与 aware datetime 的区别与使用场景
- [ ] 理解时区的本质（UTC 偏移 + DST 规则）
- [ ] 了解 ZoneInfo 与 pytz 的区别与选择

### 核心技能
- [ ] 会创建和操作 `date`、`time`、`datetime` 对象
- [ ] 会使用 `timedelta` 进行时间计算
- [ ] 会使用 `strftime` 将时间格式化为字符串
- [ ] 会使用 `strptime` 将字符串解析为时间对象
- [ ] 会进行时间戳与 `datetime` 的相互转换
- [ ] 会使用时区进行跨时区转换
- [ ] 会使用 `time.perf_counter()` 进行性能测量
- [ ] 知道 `time.sleep()` 的精度限制

### 避坑意识
- [ ] 知道 naive 和 aware 不能混用
- [ ] 知道 `timedelta` 不支持月份加减
- [ ] 知道 `strptime` 依赖 locale 设置
- [ ] 知道性能测量应该用 `perf_counter()` 而非 `time()`
- [ ] 知道 `datetime.utcnow()` 返回 naive datetime 的隐患
- [ ] 知道 pytz 的 `localize()` 用法（而非直接传 tzinfo）

---

## 📝 练习题

### 基础题

**1. 生日倒计时器**

写一个函数 `birthday_countdown(birthday_month, birthday_day)`，计算距离下一个生日还有多少天。

```python
from datetime import date

def birthday_countdown(month: int, day: int) -> int:
    """
    计算距离下一个生日的天数
    
    Args:
        month: 生日月份 (1-12)
        day: 生日日期 (1-31)
    
    Returns:
        距离下一个生日的天数
    
    示例:
    >>> birthday_countdown(12, 25)  # 如果今天是 6月18日
    190  # 距离圣诞节还有 190 天
    """
    # 你的代码
    pass

# 测试
print(birthday_countdown(12, 25))   # 圣诞倒计时
print(birthday_countdown(1, 1))     # 元旦倒计时
print(birthday_countdown(6, 18))    # 今天的生日（应该是 0 或 365）
```

**2. 工作日判断器**

写一个函数 `is_workday(year, month, day)`，判断某一天是否工作日（周一至周五且不是法定节假日）。

```python
from datetime import date

# 简化版：只判断是否周末
def is_workday(year: int, month: int, day: int) -> bool:
    """
    判断是否为工作日
    
    简化实现：只判断是否周一至周五
    
    提示：date.weekday() 返回 0=周一, 6=周日
    """
    # 你的代码
    pass

# 测试
print(is_workday(2026, 6, 18))  # 周四 → True
print(is_workday(2026, 6, 20))  # 周六 → False
print(is_workday(2026, 6, 21))  # 周日 → False

# 进阶：加入法定节假日列表
CN_HOLIDAYS = [
    date(2026, 1, 1),    # 元旦
    date(2026, 5, 1),    # 劳动节
    date(2026, 10, 1),   # 国庆节
    date(2026, 10, 2),
    date(2026, 10, 3),
]

def is_workday_advanced(year: int, month: int, day: int) -> bool:
    """考虑法定节假日的完整版本"""
    # 你的代码
    pass
```

**3. 时间差格式化器**

写一个函数 `format_timedelta(td)`，将 `timedelta` 对象格式化为人类可读的形式。

```python
from datetime import timedelta

def format_timedelta(td: timedelta) -> str:
    """
    将 timedelta 格式化为人类可读字符串
    
    示例:
    >>> format_timedelta(timedelta(days=1, hours=2, minutes=30))
    '1天 2小时 30分钟'
    >>> format_timedelta(timedelta(seconds=3661))
    '1小时 1分钟 1秒'
    >>> format_timedelta(timedelta(seconds=45))
    '45秒'
    
    要求：
    - 只显示非零单位
    - 单数/复数处理（中英文均可）
    - 秒以下精度不显示
    """
    # 你的代码
    pass

# 测试
print(format_timedelta(timedelta(days=5, hours=3, minutes=30)))
print(format_timedelta(timedelta(seconds=90061)))  # 1天 1小时 1分钟 1秒
print(format_timedelta(timedelta(hours=0, minutes=0, seconds=5)))
```

### 进阶题

**4. 跨时区时钟**

写一个类 `WorldClock`，可以同时显示多个时区的当前时间。

```python
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

class WorldClock:
    """
    世界时钟 — 同时显示多个时区的当前时间
    
    示例:
    >>> clock = WorldClock()
    >>> clock.add_city('北京', 'Asia/Shanghai')
    >>> clock.add_city('纽约', 'America/New_York')
    >>> clock.add_city('伦敦', 'Europe/London')
    >>> clock.display()
    北京: 2026-06-18 15:30:00 CST
    纽约: 2026-06-18 03:30:00 EDT
    伦敦: 2026-06-18 08:30:00 BST
    """
    
    def __init__(self):
        self.cities = {}  # {city_name: timezone_string}
    
    def add_city(self, name: str, timezone_str: str):
        """添加一个城市"""
        pass
    
    def remove_city(self, name: str):
        """移除一个城市"""
        pass
    
    def display(self):
        """显示所有城市的当前时间"""
        pass
    
    def get_time(self, city_name: str) -> str:
        """获取指定城市的当前时间字符串"""
        pass

# 测试
clock = WorldClock()
clock.add_city('北京', 'Asia/Shanghai')
clock.add_city('东京', 'Asia/Tokyo')
clock.add_city('纽约', 'America/New_York')
clock.add_city('伦敦', 'Europe/London')
clock.add_city('悉尼', 'Australia/Sydney')
clock.display()
```

**5. 排班日历生成器**

写一个函数 `generate_shift_calendar(year, month, shift_count)`，生成某个月份的排班日历。

```python
from datetime import date, timedelta
from typing import Iterator

def generate_shift_calendar(
    year: int,
    month: int,
    shift_count: int = 3
) -> dict[date, str]:
    """
    生成简单排班日历
    
    假设有 shift_count 个班组轮班（A, B, C...），
    每班连续工作 3 天，然后轮换。
    从该月 1 号开始排班。
    
    Args:
        year: 年份
        month: 月份
        shift_count: 班组数量（默认 3 个班组）
    
    Returns:
        {date: 班组名}
        例如: {date(2026, 6, 1): 'A班', date(2026, 6, 2): 'A班', ...}
    
    要求：
    - 正确处理不同月份的天数差异
    - 输出格式美观的月历视图
    """
    # 你的代码
    pass

# 测试：生成 2026 年 6 月的排班表
calendar = generate_shift_calendar(2026, 6)

# 以日历形式打印
def print_calendar(calendar: dict[date, str], year: int, month: int):
    """以日历格式打印排班表"""
    # 你的代码
    pass

print_calendar(calendar, 2026, 6)

# 输出示例：
"""
2026年6月 排班表
日   一   二   三   四   五   六
     1A  2A  3A  4B  5B  6B
 7C  8C  9C 10A 11A 12A 13B
14B 15B 16C 17C 18C 19A 20A
21A 22B 23B 24B 25C 26C 27C
28A 29A 30A
"""
```

---

## 📚 扩展阅读

- [Python datetime 官方文档](https://docs.python.org/3/library/datetime.html)
- [Python time 模块官方文档](https://docs.python.org/3/library/time.html)
- [zoneinfo 官方文档](https://docs.python.org/3/library/zoneinfo.html)
- [pytz 库文档](https://pythonhosted.org/pytz/)
- [IANA 时区数据库](https://www.iana.org/time-zones)
- [dateutil 文档（relativedelta 等）](https://dateutil.readthedocs.io/)
- [2038 年问题详解](https://en.wikipedia.org/wiki/Year_2038_problem)

---

## 🎯 反思

- 你理解了时间戳为什么从 1970 年开始吗？如果 2038 年问题真的发生，会有什么后果？
- 在使用 strptime 时你遇到了什么问题？locale 依赖给你带来了哪些麻烦？
- 如果你要设计一个跨时区的分布式系统，你会选择用什么方式存储时间？
- 为什么 Python 的 timedelta 不支持月份加减？如果一定要加一个月，你有什么替代方案？
