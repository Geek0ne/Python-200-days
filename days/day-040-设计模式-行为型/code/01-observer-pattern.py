#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观察者模式（Observer Pattern）基础实现

定义对象间一对多的依赖关系，当一个对象状态变化时，
所有依赖它的对象都得到通知并自动更新。

本示例展示：
1. 标准 OOP 实现（Subject + Observer 接口）
2. 天气预报系统的观察者订阅机制
3. 支持推模型和拉模型两种通知方式

运行：python3 01-observer-pattern.py
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
import time


# ============================================================
# 第1部分：观察者接口与抽象基类
# ============================================================

class Observer(ABC):
    """观察者抽象基类"""

    @abstractmethod
    def update(self, subject: "Subject", data: Optional[Any] = None) -> None:
        """
        接收通知的更新方法。

        参数：
            subject: 触发通知的被观察者对象（支持拉模型）
            data:    可选的通知数据（支持推模型）
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """观察者名称，用于标识"""
        pass


class Subject(ABC):
    """被观察者抽象基类"""

    @abstractmethod
    def attach(self, observer: Observer) -> None:
        """注册观察者"""
        pass

    @abstractmethod
    def detach(self, observer: Observer) -> None:
        """移除观察者"""
        pass

    @abstractmethod
    def notify(self, data: Optional[Any] = None) -> None:
        """通知所有观察者"""
        pass


# ============================================================
# 第2部分：具体被观察者 —— 天气预报站
# ============================================================

class WeatherStation(Subject):
    """
    天气预报站（被观察者）

    维护天气数据并通知所有注册的观察者。
    支持推模型（推送完整天气数据）和拉模型（观察者主动拉取）。
    """

    def __init__(self, station_name: str = "中央气象台"):
        self._station_name = station_name
        self._observers: List[Observer] = []
        # 天气数据
        self._temperature: float = 25.0
        self._humidity: float = 60.0
        self._pressure: float = 1013.25
        self._weather_condition: str = "晴"

    # ── 观察者管理 ──

    def attach(self, observer: Observer) -> None:
        """注册观察者"""
        if observer not in self._observers:
            self._observers.append(observer)
            print(f"[{self._station_name}] {observer.name} 已订阅天气预报")
        else:
            print(f"[{self._station_name}] {observer.name} 已订阅，无需重复操作")

    def detach(self, observer: Observer) -> None:
        """移除观察者"""
        if observer in self._observers:
            self._observers.remove(observer)
            print(f"[{self._station_name}] {observer.name} 已取消订阅")
        else:
            print(f"[{self._station_name}] {observer.name} 未订阅，无法取消")

    # ── 通知机制（核心）──

    def notify(self, data: Optional[Any] = None) -> None:
        """
        通知所有观察者。

        推模型：将当前天气数据作为 data 推送
        拉模型：观察者可调用 get_weather_data() 自行获取
        """
        print(f"\n[{self._station_name}] 正在通知 {len(self._observers)} 个观察者...")
        for observer in self._observers:
            # 推模型：传入完整数据
            observer.update(self, data or self.get_weather_data())

    # ── 天气数据更新（触发通知）──

    def set_weather(self, temperature: float, humidity: float,
                    pressure: float, condition: str) -> None:
        """
        更新天气数据并自动通知所有观察者。
        这是被观察者状态变化的入口。
        """
        print(f"\n{'='*55}")
        print(f"🌤  天气更新：{self._station_name}")
        print(f"   温度：{temperature}°C | 湿度：{humidity}% | "
              f"气压：{pressure}hPa | 天气：{condition}")
        print(f"{'='*55}")

        self._temperature = temperature
        self._humidity = humidity
        self._pressure = pressure
        self._weather_condition = condition

        # 状态变化后立即通知
        self.notify()

    def get_weather_data(self) -> dict:
        """获取当前天气数据（支持拉模型）"""
        return {
            "station": self._station_name,
            "temperature": self._temperature,
            "humidity": self._humidity,
            "pressure": self._pressure,
            "condition": self._weather_condition,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }


# ============================================================
# 第3部分：具体观察者
# ============================================================

class PhoneApp(Observer):
    """手机天气应用 —— 关注温度"""

    def __init__(self, name: str = "手机天气App"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def update(self, subject: Subject, data: Optional[dict] = None) -> None:
        """接收通知并以手机 App 风格展示"""
        if data is None and isinstance(subject, WeatherStation):
            data = subject.get_weather_data()

        print(f"  📱 [{self._name}]")
        print(f"     当前温度：{data['temperature']}°C")
        print(f"     天气状况：{data['condition']}")
        print(f"     更新时间：{data['timestamp']}")


class DisplayBoard(Observer):
    """户外显示屏 —— 关注完整天气信息"""

    def __init__(self, name: str = "户外信息屏"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def update(self, subject: Subject, data: Optional[dict] = None) -> None:
        if data is None and isinstance(subject, WeatherStation):
            data = subject.get_weather_data()

        print(f"  🖥  [{self._name}]")
        print(f"     ┌─────────────────────────────┐")
        print(f"     │  {data['station']}                    │")
        print(f"     │  温度：{data['temperature']:>4}°C              │")
        print(f"     │  湿度：{data['humidity']:>4}%               │")
        print(f"     │  气压：{data['pressure']:>4.1f} hPa           │")
        print(f"     │  天气：{data['condition']}                   │")
        print(f"     │  时间：{data['timestamp']}        │")
        print(f"     └─────────────────────────────┘")


class AlertSystem(Observer):
    """警报系统 —— 关注极端天气"""

    def __init__(self, name: str = "极端天气警报"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def update(self, subject: Subject, data: Optional[dict] = None) -> None:
        if data is None and isinstance(subject, WeatherStation):
            data = subject.get_weather_data()

        alerts = []

        # 检测极端温度
        if data["temperature"] > 40:
            alerts.append(f"🔥 高温警报：{data['temperature']}°C，请减少户外活动！")
        elif data["temperature"] < -10:
            alerts.append(f"❄️ 低温警报：{data['temperature']}°C，注意防寒保暖！")

        # 检测极端湿度（>95% 可能下雨）
        if data["humidity"] > 90:
            alerts.append(f"💧 高湿警报：{data['humidity']}%，暴雨风险较高！")

        # 检测低压（<1000hPa 可能台风）
        if data["pressure"] < 990:
            alerts.append(f"🌀 低压警报：{data['pressure']}hPa，注意台风！")

        if alerts:
            print(f"  🚨 [{self._name}]")
            for alert in alerts:
                print(f"     {alert}")
        else:
            print(f"  ✅ [{self._name}] 天气状况正常，无需警报")


# ============================================================
# 第4部分：主程序 —— 演示观察者模式
# ============================================================

def main():
    print("=" * 55)
    print("  观察者模式 —— 天气预报订阅系统演示")
    print("=" * 55)

    # 创建被观察者（天气站）
    station = WeatherStation("国家气象中心")

    # 创建观察者
    phone = PhoneApp("小米天气")
    board = DisplayBoard("市中心广场大屏")
    alert = AlertSystem("应急管理部")

    # ── 场景1：订阅 ──
    print("\n📋 场景1：观察者注册订阅")
    print("-" * 40)
    station.attach(phone)
    station.attach(board)
    station.attach(alert)

    # ── 场景2：天气变化，自动通知 ──
    print("\n📋 场景2：天气数据更新 → 自动通知所有观察者")
    print("-" * 40)
    station.set_weather(28.5, 65.0, 1012.0, "多云")

    # ── 场景3：再次变化 ──
    print("\n📋 场景3：天气恶化 → 触发警报")
    print("-" * 40)
    station.set_weather(42.3, 92.0, 988.0, "台风红色预警")

    # ── 场景4：取消订阅 ──
    print("\n📋 场景4：手机用户取消订阅")
    print("-" * 40)
    station.detach(phone)

    print("\n📋 场景5：天气再次更新（手机不再收到通知）")
    print("-" * 40)
    station.set_weather(30.0, 55.0, 1015.0, "晴")

    # ── 场景6：拉模型演示 ──
    print(f"\n{'='*55}")
    print("  📌 拉模型演示：观察者主动获取最新数据")
    print(f"{'='*55}")
    latest = station.get_weather_data()
    print(f"  任意观察者可随时调用 get_weather_data():")
    print(f"    温度：{latest['temperature']}°C")
    print(f"    湿度：{latest['humidity']}%")
    print(f"    气压：{latest['pressure']} hPa")

    print(f"\n{'='*55}")
    print("  观察者模式演示结束！")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
