# Day 027 — 时间处理实战场景

## 场景一：日志时间戳批量转换

### 问题
你的服务器日志使用 UTC 时间，但你想要按本地时间（UTC+8）分析。

### 解决方案

```python
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

def convert_log_timestamp(log_time_str: str, target_tz: str = 'Asia/Shanghai') -> str:
    """将日志中的 UTC 时间转换为指定时区"""
    # 假设日志格式: "2026-06-18T01:15:30Z  GET /api/users 200"
    dt_utc = datetime.strptime(log_time_str.strip('Z'), '%Y-%m-%dT%H:%M:%S')
    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    local = dt_utc.astimezone(ZoneInfo(target_tz))
    return local.strftime('%Y-%m-%d %H:%M:%S %Z')

log_line = "2026-06-18T01:15:30Z  GET /api/users 200"
# UTC 01:15 → 北京 09:15
print(convert_log_timestamp("2026-06-18T01:15:30Z"))
```

### 关键点
- 日志中的 `Z` 表示 UTC
- 先解析为 naive，再补充时区信息
- 用户只看本地时间，系统只存 UTC

---

## 场景二：定时任务的时区感知

### 问题
你的定时脚本需要在每天北京时间早上 9 点执行，但服务器可能使用 UTC。

### 解决方案

```python
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

def next_run_time(target_hour: int = 9, target_tz: str = 'Asia/Shanghai') -> datetime:
    """计算下一次定时执行时间"""
    tz = ZoneInfo(target_tz)
    now = datetime.now(tz)
    
    # 今天的执行时间
    run_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    
    # 如果已经过了，就安排到明天
    if now >= run_time:
        from datetime import timedelta
        run_time = (run_time + timedelta(days=1))
        # 跨天可能需要处理月份/年份边界
        # timedelta 会自动处理
    
    return run_time

# 北京时间 9 点执行
next = next_run_time(9, 'Asia/Shanghai')
print(f"下次执行: {next}")
```

### 关键点
- 使用 aware datetime，明确时区
- 不要依赖服务器本地时间
- 要处理"已经过了今天执行时间"的情况

---

## 场景三：有效期检查

### 问题
需要检查用户的 token/订阅是否过期。

### 解决方案

```python
from datetime import datetime, timezone, timedelta

class TokenManager:
    """简单的 Token 有效期管理器"""
    
    @staticmethod
    def is_expired(expires_at: datetime) -> bool:
        """检查是否已过期"""
        now = datetime.now(timezone.utc) if expires_at.tzinfo else datetime.now()
        return now >= expires_at
    
    @staticmethod
    def remaining_days(expires_at: datetime) -> float:
        """计算剩余天数"""
        now = datetime.now(timezone.utc) if expires_at.tzinfo else datetime.now()
        delta = expires_at - now
        return delta.total_seconds() / 86400
    
    @staticmethod
    def generate_expiry(days: int = 30) -> datetime:
        """生成到期时间"""
        return datetime.now(timezone.utc) + timedelta(days=days)

# 使用
expires = TokenManager.generate_expiry(30)
print(f"到期时间: {expires}")
print(f"已过期: {TokenManager.is_expired(expires)}")
print(f"剩余天数: {TokenManager.remaining_days(expires):.1f}")
```

### 关键点
- 有效期判断需要明确时区
- 使用 UTC 统一存储和比较
- 注意"正好到期"的边界情况

---

## 场景四：批处理时间窗口

### 问题
每天 02:00-04:00 (UTC+8) 是系统维护窗口，这段时间不处理业务请求。

### 解决方案

```python
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

def is_maintenance_window(now: datetime = None) -> bool:
    """判断是否在维护窗口内"""
    if now is None:
        now = datetime.now(ZoneInfo('Asia/Shanghai'))
    
    # 维护窗口: 02:00 - 04:00
    window_start = time(2, 0, 0)
    window_end = time(4, 0, 0)
    
    current_time = now.time()
    
    if window_start <= current_time < window_end:
        return True
    # 处理跨天情况（如果窗口跨午夜）
    if window_start >= window_end:
        if current_time >= window_start or current_time < window_end:
            return True
    
    return False

now = datetime.now(ZoneInfo('Asia/Shanghai'))
print(f"当前时间: {now.strftime('%H:%M')}")
print(f"是否在维护窗口: {is_maintenance_window(now)}")
```

### 关键点
- 时间比较要处理跨天情况（开始 > 结束）
- 明确时区，不要假设服务器本地时间
- 时间比较用 `time` 对象更清晰

---

## 场景五：时区敏感的数据报表

### 问题
生成按"用户所在时区"统计的日报表。

### 解决方案

```python
from datetime import datetime, timezone, timedelta
from collections import defaultdict

def generate_timezone_report(
    events: list[tuple[datetime, str]],
    user_timezone: str = 'Asia/Shanghai'
) -> dict:
    """
    按用户时区生成报表
    
    Args:
        events: [(utc_timestamp, event_type), ...]
        user_timezone: 用户所在的时区
    """
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(user_timezone)
    report = defaultdict(int)
    
    for utc_dt, event_type in events:
        # 确保是 aware UTC
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        
        # 转换为用户时区的日期
        local_dt = utc_dt.astimezone(tz)
        day_key = local_dt.strftime('%Y-%m-%d')
        hour_key = local_dt.hour
        
        report[f"{day_key}"] += 1
        report[f"{day_key}_{hour_key:02d}h"] += 1
    
    return dict(report)

# 模拟数据
events = [
    (datetime(2026, 6, 18, 1, 0, tzinfo=timezone.utc), "login"),
    (datetime(2026, 6, 18, 8, 0, tzinfo=timezone.utc), "login"),
    (datetime(2026, 6, 17, 16, 0, tzinfo=timezone.utc), "purchase"),
]

report = generate_timezone_report(events, 'America/New_York')
for k, v in sorted(report.items()):
    print(f"  {k}: {v}")
```

### 关键点
- 事件存储为 UTC，报表按用户时区分组
- 时区转换不改变时间点，只改变显示
- 跨天事件的处理
