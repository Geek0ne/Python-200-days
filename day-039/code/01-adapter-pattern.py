"""
Day 39 — 设计模式（结构型）
01-adapter-pattern.py
适配器模式 — 将不兼容的接口转换为客户端期望的接口

场景：系统期望 XML 数据输出，但第三方库只输出 JSON。
适配器将 JSON 输出转换成 XML 格式，无需修改第三方库。

┌────────────────────┐     ┌──────────────────┐     ┌──────────────┐
│ 系统（期望 XML）    │────▶│  XMLAdapter       │────▶│ ThirdPartyLib│
│                    │     │  (适配器)         │     │ (输出 JSON)  │
└────────────────────┘     │  将 JSON 转 XML  │     └──────────────┘
                           └──────────────────┘
"""

from abc import ABC, abstractmethod
import json


# ── 目标接口：系统期望的 XML 输出接口 ──────────────────

class XMLTarget(ABC):
    """客户端（系统）期望的 XML 输出接口"""
    
    @abstractmethod
    def get_xml_data(self) -> str:
        """返回 XML 格式数据"""
        pass


# ── 被适配者：第三方库（只输出 JSON） ──────────────────

class ThirdPartyWeatherAPI:
    """第三方天气查询服务，只返回 JSON 格式数据"""
    
    def __init__(self, api_key: str):
        self._api_key = api_key
    
    def fetch_weather(self, city: str) -> str:
        """
        模拟查询天气，返回 JSON 字符串
        
        真实情况下这里会调用第三方 HTTP API，
        返回类似响应：
        {"city": "北京", "temp": 28, "humidity": 65, "wind": "3级"}
        """
        data = {
            "city": city,
            "temp": 28,
            "humidity": 65,
            "wind": "3级",
            "condition": "晴"
        }
        return json.dumps(data, ensure_ascii=False)
    
    def fetch_forecast(self, city: str, days: int) -> str:
        """模拟获取未来天气预报"""
        forecasts = []
        base_temp = 28
        for i in range(days):
            forecasts.append({
                "city": city,
                "date": f"2026-06-{23 + i:02d}",
                "temp_high": base_temp + i * 2,
                "temp_low": base_temp - 5 + i,
                "condition": "晴" if i % 2 == 0 else "多云"
            })
        return json.dumps(forecasts, ensure_ascii=False)


# ── 适配器：将 JSON 转换为 XML ────────────────────────

class WeatherXMLAdapter(XMLTarget):
    """
    适配器：将 JSON 输出转换为 XML 格式
    
    设计思路：
    - 使用对象适配器（组合方式），而非类适配器（继承方式）
    - 持有被适配者引用，在其基础上做接口转换
    - 不修改第三方库代码
    """
    
    def __init__(self, api: ThirdPartyWeatherAPI):
        self._api = api  # 组合：持有被适配对象
    
    def get_xml_data(self) -> str:
        """
        实现目标接口：返回 XML 格式数据
        内部调用第三方库的 JSON API 并转换
        """
        # 1. 调用第三方库获得 JSON
        json_str = self._api.fetch_weather("北京")
        
        # 2. 解析 JSON
        data = json.loads(json_str)
        
        # 3. 构建 XML
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<weather>"
        ]
        
        # 通用转换逻辑：遍历字典的所有键值对
        for key, value in data.items():
            xml_parts.append(f"  <{key}>{value}</{key}>")
        
        xml_parts.append("</weather>")
        
        return "\n".join(xml_parts)
    
    def get_forecast_xml(self, city: str, days: int) -> str:
        """适配天气预报功能：JSON → XML"""
        json_str = self._api.fetch_forecast(city, days)
        forecasts = json.loads(json_str)
        
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<forecasts>"
        ]
        
        for forecast in forecasts:
            xml_parts.append("  <day>")
            for key, value in forecast.items():
                xml_parts.append(f"    <{key}>{value}</{key}>")
            xml_parts.append("  </day>")
        
        xml_parts.append("</forecasts>")
        
        return "\n".join(xml_parts)


# ── 测试 ──────────────────────────────────────────────

def test_adapter():
    """测试适配器模式的功能"""
    
    print("=" * 60)
    print("适配器模式 — 接口转换演示")
    print("=" * 60)
    
    # 1. 第三方库（只能输出 JSON）
    api_key = "sk-weather-123456"
    third_party_api = ThirdPartyWeatherAPI(api_key)
    
    print("\n📦 第三方库原始输出（JSON）：")
    json_data = third_party_api.fetch_weather("北京")
    print(f"  {json_data}")
    
    # 2. 通过适配器接入系统
    print("\n🔌 通过适配器转换后（XML）：")
    adapter = WeatherXMLAdapter(third_party_api)
    xml_data = adapter.get_xml_data()
    print(f"  {xml_data}")
    
    # 3. 天气预报适配
    print("\n📅 天气预报适配（XML）：")
    forecast_xml = adapter.get_forecast_xml("北京", 3)
    print(f"  {forecast_xml}")
    
    print("\n" + "=" * 60)
    print("✅ 适配器模式测试通过！")
    print("   第三方库未修改，接口已成功转换。")
    print("=" * 60)


# ── 扩展：适配多个数据源 ──────────────────────────────

class CSVDataSource:
    """另一个被适配者：CSV 数据源"""
    
    def get_csv(self) -> str:
        return "city,temp,humidity\n北京,28,65\n上海,30,70"


class CSVToXMLAdapter(XMLTarget):
    """CSV → XML 适配器"""
    
    def __init__(self, csv_source: CSVDataSource):
        self._csv_source = csv_source
    
    def get_xml_data(self) -> str:
        csv_text = self._csv_source.get_csv()
        lines = csv_text.strip().split("\n")
        
        if len(lines) < 2:
            return "<data/>"
        
        headers = lines[0].split(",")
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<records>"]
        
        for line in lines[1:]:
            values = line.split(",")
            xml_parts.append("  <record>")
            for header, value in zip(headers, values):
                xml_parts.append(f"    <{header}>{value}</{header}>")
            xml_parts.append("  </record>")
        
        xml_parts.append("</records>")
        return "\n".join(xml_parts)


# ── 统一客户端接口 ────────────────────────────────────

def process_xml_data(source: XMLTarget):
    """
    所有适配器都实现了 XMLTarget 接口
    客户端无需关心数据来源是 JSON、CSV 还是其他格式
    这就是适配器模式的核心价值：接口统一
    """
    xml = source.get_xml_data()
    print(f"  统一处理 XML 数据（长度: {len(xml)} 字符）")
    # 实际系统中会进一步解析 XML
    return xml


if __name__ == "__main__":
    test_adapter()
    
    print("\n🔄 统一接口处理演示：")
    
    weather_api = ThirdPartyWeatherAPI("key")
    csv_source = CSVDataSource()
    
    # 两种不同的数据源，通过各自适配器统一处理
    print("\n1️⃣  天气 JSON → XML 适配器 → 统一处理")
    xml1 = process_xml_data(WeatherXMLAdapter(weather_api))
    
    print("\n2️⃣  CSV 数据 → XML 适配器 → 统一处理")
    xml2 = process_xml_data(CSVToXMLAdapter(csv_source))
    
    print("\n✅ 两个不同的数据源都通过 XMLTarget 接口统一处理！")

"""
运行结果示例：
============================================================
适配器模式 — 接口转换演示
============================================================

📦 第三方库原始输出（JSON）：
  {"city": "北京", "temp": 28, "humidity": 65, "wind": "3级", "condition": "晴"}

🔌 通过适配器转换后（XML）：
  <?xml version="1.0" encoding="UTF-8"?>
  <weather>
    <city>北京</city>
    <temp>28</temp>
    <humidity>65</humidity>
    <wind>3级</wind>
    <condition>晴</condition>
  </weather>
"""
