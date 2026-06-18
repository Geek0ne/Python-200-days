# Day 027 — 时间日期 API 速查与对比

## 时间获取

| 操作 | 方法 | 类型 |
|------|------|------|
| 当前时间戳 | `time.time()` | float |
| 当前本地时间 | `datetime.now()` | naive datetime |
| 当前 UTC 时间 | `datetime.now(timezone.utc)` ✅ | aware datetime |
| 当前 UTC (旧) | `datetime.utcnow()` ⚠️ | **naive** datetime — 不推荐 |
| 今天日期 | `date.today()` | date |
| 当前时间 | `datetime.now().time()` | time |

## 类型转换

### 时间戳 ↔ datetime
```python
# 时间戳 → datetime (本地)
dt = datetime.fromtimestamp(ts)

# 时间戳 → datetime (UTC, aware)
dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)

# datetime → 时间戳
ts = dt.timestamp()
```

### 字符串 ↔ datetime
```python
# 字符串 → datetime (解析)
dt = datetime.strptime("2026-06-18", "%Y-%m-%d")

# datetime → 字符串 (格式化)
s = dt.strftime("%Y-%m-%d %H:%M:%S")

# datetime → ISO 8601 字符串
s = dt.isoformat()

# ISO 8601 → datetime (Python 3.7+)
dt = datetime.fromisoformat("2026-06-18T09:15:30+08:00")
```

### datetime ↔ date/time 拆分
```python
# datetime → date
d = dt.date()

# datetime → time
t = dt.time()

# datetime → time (保留时区)
t = dt.timetz()

# date + time → datetime
dt = datetime.combine(d, t)
```

## 时间运算

```python
# 加/减天数
dt + timedelta(days=7)
dt - timedelta(days=7)

# 加/减小时/分钟/秒
dt + timedelta(hours=3, minutes=30)

# 两个时间相减
delta = dt2 - dt1  # → timedelta
delta.total_seconds()  # 总秒数

# timedelta 运算
td1 + td2  # 相加
td1 * 2    # 乘以标量
td1 // 2   # 整除
-td1       # 取负

# ⚠️ 不支持加月份
# dt + timedelta(months=1) → TypeError
# 需用 dateutil.relativedelta
```

## 时区转换

### zoneinfo (Python 3.9+)
```python
from zoneinfo import ZoneInfo

# 创建 aware datetime
dt = datetime(2026, 6, 18, 9, 15, tzinfo=ZoneInfo('Asia/Shanghai'))

# 转换时区
dt_ny = dt.astimezone(ZoneInfo('America/New_York'))
dt_utc = dt.astimezone(timezone.utc)
```

### pytz (旧版兼容)
```python
import pytz

# ⚠️ 必须用 localize，不能直接传 tzinfo
shanghai = pytz.timezone('Asia/Shanghai')
dt = shanghai.localize(datetime(2026, 6, 18, 9, 15))

# 转换
dt_ny = dt.astimezone(pytz.timezone('America/New_York'))
```

## 格式化指令

| 指令 | 含义 | 示例 |
|------|------|------|
| `%Y` | 4位年份 | 2026 |
| `%y` | 2位年份 | 26 |
| `%m` | 2位月份 | 06 |
| `%B` | 完整月份 | June |
| `%b` | 缩写月份 | Jun |
| `%d` | 2位日期 | 18 |
| `%H` | 24小时 | 09 |
| `%I` | 12小时 | 09 |
| `%p` | AM/PM | AM |
| `%M` | 分钟 | 15 |
| `%S` | 秒 | 30 |
| `%f` | 微秒 | 123456 |
| `%A` | 完整星期 | Thursday |
| `%a` | 缩写星期 | Thu |
| `%z` | UTC偏移 | +0800 |
| `%Z` | 时区名 | CST |

## 常见的坑

1. **Naive + Aware 混用** → TypeError，需先统一
2. **timedelta 不能加月份** → 用 dateutil.relativedelta
3. **strptime 依赖 locale** → 英文月份需设置英语 locale
4. **utcnow() 返回 naive** → 用 `now(timezone.utc)`
5. **性能测量用 perf_counter** → 不要用 time()
6. **pytz 用 localize** → 不要直接传 tzinfo

## 最佳实践

```
存储 → UTC (aware datetime)
计算 → 统一到 UTC
显示 → 转换到用户时区
测试 → 包含 DST 切换日和闰年
