#!/usr/bin/env python3
"""
Day 064 - 网络请求
示例 3: 实战 — 天气预报 CLI 工具

本示例实现一个命令行天气预报工具 WeatherCLI，支持：
1. 通过城市名称查询实时天气
2. 自动缓存（避免频繁请求 API）
3. 友好的彩色终端输出
4. 错误处理与自动重试
5. 支持多个数据源（含示例数据，无需 API Key 即可运行）

运行方式: python3 03-weather-cli.py [城市名]
         python3 03-weather-cli.py 北京
         python3 03-weather-cli.py 上海 --days 3

注意：使用免费公开 API（wttr.in），无需 API Key
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# 尝试安装请求库
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ════════════════════════════════════════════
# 终端颜色工具
# ════════════════════════════════════════════

class Colors:
    """终端 ANSI 颜色"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    DIM = "\033[2m"


def color(text: str, color_code: str, bold: bool = False) -> str:
    """给文本加颜色"""
    prefix = Colors.BOLD if bold else ""
    return f"{prefix}{color_code}{text}{Colors.RESET}"


# ════════════════════════════════════════════
# 天气 API 接口
# ════════════════════════════════════════════

# 使用 wttr.in — 免费公开天气 API，无需 API Key
# 文档: https://github.com/chubin/wttr.in

class WeatherAPI:
    """天气数据获取器"""

    BASE_URL = "https://wttr.in"

    @classmethod
    def fetch_weather(cls, city: str, days: int = 1) -> dict:
        """
        获取城市天气
        
        Args:
            city: 城市名称（中文或拼音）
            days: 预报天数 (0=今天, 1-3=预报天数)
        
        Returns:
            dict: 天气数据字典
        """
        params = {
            "format": "j1",  # JSON 格式输出
            "lang": "zh",    # 中文
        }

        # wttr.in URL 格式: https://wttr.in/{city}?format=j1&lang=zh
        url = f"{cls.BASE_URL}/{city}"

        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return cls._parse_weather_data(data)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise WeatherError(f"未找到城市: {city}")
            raise WeatherError(f"HTTP 错误: {e}")
        except requests.exceptions.ConnectionError:
            raise WeatherError("网络连接失败，请检查网络")
        except requests.exceptions.Timeout:
            raise WeatherError("请求超时")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # 如果 API 返回非 JSON 格式（可能被限制）
            raise WeatherError(f"数据解析失败: {e}")


class WeatherError(Exception):
    """天气 API 错误"""
    pass


# ════════════════════════════════════════════
# 天气缓存
# ════════════════════════════════════════════

class WeatherCache:
    """天气缓存（避免频繁请求 API）"""

    CACHE_DIR = Path("/tmp/weather_cache")
    CACHE_DURATION = timedelta(minutes=30)  # 缓存有效期 30 分钟

    @classmethod
    def get(cls, city: str) -> dict | None:
        """获取缓存的天气数据"""
        cache_file = cls.CACHE_DIR / f"{city}.json"
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_time = datetime.fromisoformat(data["_cached_at"])
            if datetime.now() - cached_time < cls.CACHE_DURATION:
                return data
            else:
                cache_file.unlink()  # 缓存过期，删除
                return None
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            return None

    @classmethod
    def set(cls, city: str, data: dict):
        """缓存天气数据"""
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = cls.CACHE_DIR / f"{city}.json"
        data["_cached_at"] = datetime.now().isoformat()
        cache_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    @classmethod
    def clear(cls, city: str = None):
        """清除缓存"""
        if city:
            cache_file = cls.CACHE_DIR / f"{city}.json"
            if cache_file.exists():
                cache_file.unlink()
        else:
            import shutil
            if cls.CACHE_DIR.exists():
                shutil.rmtree(cls.CACHE_DIR)


# ════════════════════════════════════════════
# 天气数据解析与显示
# ════════════════════════════════════════════

def _parse_weather_data(raw_data: dict) -> dict:
    """解析 wttr.in 原始 JSON 数据为结构化的天气字典"""
    current = raw_data.get("current_condition", [{}])[0]

    # 温度
    temp = current.get("temp_C", "N/A")
    feels_like = current.get("FeelsLikeC", "N/A")

    # 天气描述
    weather_desc = current.get("lang_zh", [{}])[0].get("value", "未知")
    weather_code = current.get("weatherCode", "")

    # 风速/湿度/能见度
    wind_speed = current.get("windspeedKmph", "N/A")
    humidity = current.get("humidity", "N/A")
    visibility = current.get("visibility", "N/A")
    uv_index = current.get("uvIndex", "N/A")

    # 气压
    pressure = current.get("pressure", "N/A")

    # 预报
    forecasts = []
    for day in raw_data.get("weather", [])[:5]:
        date_str = day.get("date", "")
        astro = day.get("astronomy", [{}])[0] if day.get("astronomy") else {}
        hourly = day.get("hourly", [])

        # 最高最低温度
        temp_max = day.get("maxtempC", "N/A")
        temp_min = day.get("mintempC", "N/A")

        # 平均天气条件
        desc_list = []
        for h in hourly:
            desc = h.get("lang_zh", [{}])[0].get("value", "") if h.get("lang_zh") else ""
            if desc:
                desc_list.append(desc)

        avg_desc = max(set(desc_list), key=desc_list.count) if desc_list else ""

        forecasts.append({
            "date": date_str,
            "temp_max": temp_max,
            "temp_min": temp_min,
            "description": avg_desc,
            "sunrise": astro.get("sunrise", ""),
            "sunset": astro.get("sunset", ""),
            "hourly": hourly,
        })

    return {
        "city": raw_data.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", "未知"),
        "country": raw_data.get("nearest_area", [{}])[0].get("country", [{}])[0].get("value", ""),
        "current": {
            "temp": temp,
            "feels_like": feels_like,
            "description": weather_desc,
            "wind_speed": wind_speed,
            "humidity": humidity,
            "visibility": visibility,
            "uv_index": uv_index,
            "pressure": pressure,
        },
        "forecasts": forecasts,
        "_cached_at": datetime.now().isoformat(),
    }


def format_weather(data: dict) -> str:
    """格式化天气数据为可读文本"""
    lines = []
    city = data.get("city", "未知")
    country = data.get("country", "")
    current = data.get("current", {})

    # 标题
    lines.append("")
    lines.append(color(f"  ☀️  {city} {country} 天气预报", Colors.CYAN, bold=True))
    lines.append(color(f"  {'─' * 50}", Colors.DIM))

    # 当前天气
    temp = current.get("temp", "N/A")
    feels = current.get("feels_like", "N/A")
    desc = current.get("description", "")

    # 温度 emoji
    try:
        temp_num = float(temp)
        temp_emoji = "🥵" if temp_num >= 35 else "☀️" if temp_num >= 25 else "🌤️" if temp_num >= 15 else "🌥️" if temp_num >= 5 else "❄️"
    except (ValueError, TypeError):
        temp_emoji = "🌡️"

    lines.append(f"\n  {temp_emoji}  现在: {color(temp, Colors.YELLOW, bold=True)}°C "
                 f"(体感 {color(feels, Colors.YELLOW)}°C)  {desc}")

    # 详细数据
    wind = current.get("wind_speed", "N/A")
    humidity = current.get("humidity", "N/A")
    vis = current.get("visibility", "N/A")
    uv = current.get("uv_index", "N/A")
    pressure = current.get("pressure", "N/A")

    lines.append(color(f"\n  📊 详细数据:", Colors.MAGENTA))
    lines.append(f"     💨 风速: {wind} km/h    💧 湿度: {humidity}%")
    lines.append(f"     👁️  能见度: {vis} km     ☀️  紫外线: {uv}")
    lines.append(f"     🌀 气压: {pressure} hPa")

    # 预报
    forecasts = data.get("forecasts", [])
    if forecasts:
        lines.append(color(f"\n  📅 未来预报:", Colors.MAGENTA))

        for day in forecasts[:3]:
            date_str = day.get("date", "")
            t_max = day.get("temp_max", "N/A")
            t_min = day.get("temp_min", "N/A")
            desc = day.get("description", "")

            # 日期格式化
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                weekday = ["一", "二", "三", "四", "五", "六", "日"][dt.weekday()]
                date_display = f"{dt.month}月{dt.day}日 (周{weekday})"
            except:
                date_display = date_str

            lines.append(f"     {date_display}: "
                         f"{color(t_max, Colors.RED)}/{color(t_min, Colors.BLUE)}°C "
                         f"  {desc}")

    return "\n".join(lines)


# ════════════════════════════════════════════
# 主 CLI 入口
# ════════════════════════════════════════════

def fetch_weather_with_retry(city: str, max_retries: int = 3) -> dict:
    """带重试的天气查询"""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return WeatherAPI.fetch_weather(city)
        except WeatherError as e:
            last_error = e
            if attempt < max_retries:
                wait = attempt * 2
                print(f"  ⚠️  重试 {attempt}/{max_retries} (等待 {wait}s): {e}")
                time.sleep(wait)
    raise last_error


def main():
    """主函数"""
    print(color("\n" + "=" * 58, Colors.DIM))
    print(color("  🌤️  WeatherCLI — 命令行天气预报工具", Colors.CYAN, bold=True))
    print(color("=" * 58, Colors.DIM))

    # 解析参数
    args = sys.argv[1:]
    city = "北京"  # 默认城市
    days = 1
    force_refresh = False

    if args:
        if args[0] in ("--clear", "-c"):
            WeatherCache.clear()
            print(color("  ✅ 缓存已清除", Colors.GREEN))
            return
        if args[0] in ("--help", "-h"):
            print("用法: python3 03-weather-cli.py [城市名] [--days N] [--clear]")
            print("  城市名: 默认为 '北京'")
            print("  --days N: 预报天数 (1-3)")
            print("  --clear: 清除缓存")
            return

        city = args[0]
        if "--days" in args:
            idx = args.index("--days")
            if idx + 1 < len(args):
                try:
                    days = max(1, min(3, int(args[idx + 1])))
                except ValueError:
                    pass

    if not HAS_REQUESTS:
        print(color("  ❌ 需要安装 requests: pip install requests", Colors.RED))
        sys.exit(1)

    # 检查缓存
    print(f"\n  🔍 查询: {color(city, Colors.YELLOW, bold=True)}")

    cached = WeatherCache.get(city)
    if cached:
        print(color("  📦 使用缓存数据 (30分钟内有效)", Colors.DIM))
        print(format_weather(cached))
        return

    # 查询天气（带重试）
    try:
        data = fetch_weather_with_retry(city)
        WeatherCache.set(city, data)
        print(format_weather(data))
    except WeatherError as e:
        print(color(f"\n  ❌ 查询失败: {e}", Colors.RED))

        # 降级：使用默认数据
        print(color("\n  📋 使用离线示例数据...", Colors.DIM))
        demo_data = _get_demo_weather(city)
        print(format_weather(demo_data))

    print(color(f"\n  最后更新: {datetime.now().strftime('%H:%M:%S')}", Colors.DIM))
    print(color("=" * 58, Colors.DIM))


def _get_demo_weather(city: str) -> dict:
    """离线示例天气数据（API 不可用时的降级方案）"""
    import random
    random.seed(hash(city) % (2**31))

    temp = random.randint(20, 35)
    weathers = ["晴", "多云", "阴", "小雨", "晴转多云"]
    desc = random.choice(weathers)

    return {
        "city": city,
        "country": "中国",
        "current": {
            "temp": str(temp),
            "feels_like": str(temp + random.randint(-2, 2)),
            "description": desc,
            "wind_speed": str(random.randint(5, 30)),
            "humidity": str(random.randint(30, 80)),
            "visibility": str(random.randint(5, 20)),
            "uv_index": str(random.randint(1, 10)),
            "pressure": str(random.randint(1000, 1025)),
        },
        "forecasts": [
            {
                "date": (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d"),
                "temp_max": str(temp + random.randint(0, 5)),
                "temp_min": str(temp - random.randint(5, 10)),
                "description": random.choice(weathers),
            }
            for d in range(1, 4)
        ],
    }


if __name__ == "__main__":
    main()
