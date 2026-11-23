"""
Day 037 — 组合与聚合：实战案例
===============================

实战：汽车-引擎-轮胎模型 —— 组合 + 聚合 + 依赖注入综合应用

架构设计：
- Engine → 组合（随 Car 创建/销毁）
- Tire → 聚合（可独立更换）
- GPS → 依赖注入（可选外部组件）
- Transmission, FuelTank → 组合
"""

import time
from typing import List, Optional, Tuple


# ====================================
# 组合组件：引擎
# ====================================

class Engine:
    """引擎 —— 组合关系（随 Car 一起创建和销毁）"""

    def __init__(self, displacement: float, horsepower: int,
                 fuel_type: str = "汽油"):
        self.displacement = displacement
        self.horsepower = horsepower
        self.fuel_type = fuel_type
        self._running = False
        self._rpm = 0
        self._temperature = 20.0  # 摄氏度
        self._total_revolutions = 0

    def start(self) -> str:
        if self._running:
            return "引擎已经在运转"
        self._running = True
        self._rpm = 800
        return (f"🔑 引擎启动 — {self.displacement}L {self.fuel_type} "
                f"({self.horsepower}HP) 怠速 {self._rpm}rpm")

    def stop(self) -> str:
        if not self._running:
            return "引擎已熄火"
        self._running = False
        self._rpm = 0
        return "🔑 引擎熄火"

    def accelerate(self, target_rpm: int) -> Tuple[str, int]:
        """加速到目标转速"""
        if not self._running:
            return "请先启动引擎", 0

        target_rpm = max(800, min(7000, target_rpm))
        self._rpm = target_rpm
        self._temperature = min(95, self._temperature + target_rpm * 0.005)
        self._total_revolutions += target_rpm

        return f"⚡ 引擎转速: {self._rpm} rpm", self._rpm

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def rpm(self) -> int:
        return self._rpm

    @property
    def temperature(self) -> float:
        return self._temperature

    def __repr__(self) -> str:
        status = "运转中" if self._running else "熄火"
        return (f"Engine({self.displacement}L {self.fuel_type}, "
                f"{self.horsepower}HP, {status})")


# ====================================
# 组合组件：变速箱
# ====================================

class Transmission:
    """变速箱 —— 组合关系"""

    GEARS = ['P', 'R', 'N', 'D', '1', '2', '3', '4', '5', '6']

    def __init__(self, type_: str = "自动"):
        self.type = type_
        self._gear = 'P'
        self._gear_index = 0

    def shift(self, gear: str) -> str:
        gear = gear.upper()
        if gear not in self.GEARS:
            return f"❌ 无效档位: {gear}"

        new_index = self.GEARS.index(gear)
        self._gear = gear
        self._gear_index = new_index
        return f"⚙️ 换档至 {gear}"

    def auto_shift(self, rpm: int) -> str:
        """根据转速自动换档（模拟）"""
        if self._gear not in ('D', '1', '2', '3', '4', '5', '6'):
            return ""

        current = self._gear_index - 3  # D 是 index 3
        new_gear = current

        if rpm > 4000 and current < 6:
            new_gear = min(current + 1, 6)
        elif rpm < 1500 and current > 1:
            new_gear = max(current - 1, 1)

        if new_gear != current:
            target = self.GEARS[new_gear + 3]
            self._gear = target
            self._gear_index = new_gear + 3
            return f"⚙️ 自动升档至 {target}"
        return ""

    @property
    def gear(self) -> str:
        return self._gear

    def __repr__(self) -> str:
        return f"Transmission({self.type}, 档位: {self._gear})"


# ====================================
# 组合组件：油箱
# ====================================

class FuelTank:
    """油箱 —— 组合关系"""

    def __init__(self, capacity: float = 55.0):
        self.capacity = capacity  # 升
        self._level = capacity    # 满油

    def refill(self, liters: float) -> str:
        if liters <= 0:
            return "❌ 加油量必须为正数"
        old_level = self._level
        self._level = min(self.capacity, self._level + liters)
        added = self._level - old_level
        return (f"⛽ 加油 {added:.1f}L，当前油量: "
                f"{self._level:.1f}/{self.capacity:.1f}L "
                f"({self.percentage():.0f}%)")

    def consume(self, liters: float) -> bool:
        """消耗燃油，返回是否够用"""
        if self._level >= liters:
            self._level -= liters
            return True
        self._level = 0
        return False

    def percentage(self) -> float:
        return (self._level / self.capacity) * 100

    def is_empty(self) -> bool:
        return self._level <= 0

    @property
    def level(self) -> float:
        return self._level

    def __repr__(self) -> str:
        return f"FuelTank({self._level:.1f}/{self.capacity:.1f}L)"


# ====================================
# 聚合组件：轮胎
# ====================================

class Tire:
    """轮胎 —— 聚合关系（可以独立于 Car 存在）"""

    SEASONS = ['夏季', '冬季', '全季节']

    def __init__(self, brand: str, model: str = "",
                 size: str = "205/55R16",
                 season: str = "全季节"):
        self.brand = brand
        self.model = model
        self.size = size
        self.season = season if season in self.SEASONS else "全季节"
        self._pressure = 32.0  # PSI
        self._tread_depth = 8.0  # mm
        self._total_km = 0

    def inflate(self, psi: float) -> str:
        if psi < 20 or psi > 50:
            return f"❌ [{self.brand}] 胎压 {psi} PSI 超出安全范围 (20-50)"
        self._pressure = psi
        return f"✅ [{self.brand}] 胎压设为 {psi} PSI"

    def get_pressure(self) -> float:
        return self._pressure

    def check_tread(self) -> str:
        if self._tread_depth <= 0:
            return f"⚠️ [{self.brand}] 轮胎已磨平！需要立即更换！"
        if self._tread_depth < 1.6:
            return f"⚠️ [{self.brand}] 胎纹深度 {self._tread_depth:.1f}mm，建议更换"
        return f"✅ [{self.brand}] 胎纹深度 {self._tread_depth:.1f}mm"

    def wear(self, km: float = 1.0):
        """轮胎磨损（与行驶距离成正比）"""
        wear_amount = km * 0.0001
        self._tread_depth = max(0, self._tread_depth - wear_amount)
        self._total_km += km

    def status(self) -> str:
        pos = "🟢" if self._tread_depth > 3 else ("🟡" if self._tread_depth > 1.6 else "🔴")
        return (f"{pos} {self.brand} {self.model} | "
                f"胎压: {self._pressure}PSI | "
                f"胎纹: {self._tread_depth:.1f}mm | "
                f"行驶: {self._total_km:.0f}km")

    def __repr__(self) -> str:
        return f"Tire({self.brand} {self.model})"


# ====================================
# 依赖注入组件：GPS
# ====================================

class GPS:
    """GPS 导航 —— 依赖注入（可选外部组件）"""

    def __init__(self, model: str = "标准导航"):
        self.model = model
        self._destination = None
        self._route = []

    def set_destination(self, destination: str) -> str:
        self._destination = destination
        self._route = ["起点", "途经点A", "途经点B", destination]
        return f"🗺️ 已规划前往 {destination} 的路线"

    def navigate(self) -> str:
        if not self._destination:
            return "📍 请先设置目的地"
        return (f"🗺️ [{self.model}] 导航中 → {self._destination}, "
                f"剩余 {len(self._route) - 1} 个途经点")

    def get_current_location(self) -> str:
        return "📍 当前位置: 北京市朝阳区"

    def __repr__(self) -> str:
        return f"GPS({self.model})"


# ====================================
# Car：组合 + 聚合 + 依赖注入
# ====================================

class Car:
    """
    汽车类 —— 展示组合/聚合/依赖注入的混合使用

    组合关系：Engine, Transmission, FuelTank
    聚合关系：Tire（可以从外部传入和更换）
    依赖注入：GPS（可选，运行时注入）
    """

    def __init__(self, brand: str, model: str, year: int = 2026):
        self.brand = brand
        self.model = model
        self.year = year

        # ── 组合：在 Car 的构造器中创建，随 Car 销毁 ──
        self._engine = Engine(2.0, 200, "汽油")
        self._transmission = Transmission("自动")
        self._fuel_tank = FuelTank(55.0)

        # ── 聚合：从外部传入，可以独立更换 ──
        self._tires: List[Tire] = []

        # ── 依赖注入：可选外部组件 ──
        self._gps: Optional[GPS] = None

        # ── 状态 ──
        self._speed = 0
        self._odometer = 0.0
        self._locked = True

    # ═══════════════════════════════════════
    # 轮胎管理（聚合）
    # ═══════════════════════════════════════

    def install_tires(self, tires: List[Tire]) -> str:
        """安装轮胎（聚合 — 轮胎从外部传入）"""
        if len(tires) != 4:
            return "❌ 需要 4 个轮胎"
        self._tires = tires
        return f"✅ 已安装 4 个 {tires[0].brand} {tires[0].model} 轮胎"

    def replace_tire(self, position: int, new_tire: Tire) -> str:
        """更换单个轮胎（展示聚合的灵活性）"""
        if not 0 <= position < len(self._tires):
            return f"❌ 位置 {position} 无效 (0-3)"
        old = self._tires[position]
        self._tires[position] = new_tire
        return f"🔄 轮胎 {position + 1}: {old.brand} → {new_tire.brand} {new_tire.model}"

    def check_tires(self) -> List[str]:
        """检查所有轮胎状态"""
        return [
            f"  轮胎 {i + 1}: {tire.status()}"
            for i, tire in enumerate(self._tires)
        ]

    # ═══════════════════════════════════════
    # GPS 管理（依赖注入）
    # ═══════════════════════════════════════

    def install_gps(self, gps: GPS) -> str:
        """安装 GPS（依赖注入）"""
        self._gps = gps
        return f"✅ 已安装 GPS: {gps.model}"

    def navigate(self, destination: str) -> str:
        """使用 GPS 导航"""
        if not self._gps:
            return "❌ 未安装 GPS"
        return self._gps.set_destination(destination)

    # ═══════════════════════════════════════
    # 驾驶操作
    # ═══════════════════════════════════════

    def unlock(self) -> str:
        self._locked = False
        return "🔓 车门已解锁"

    def lock(self) -> str:
        self._locked = True
        return "🔒 车门已锁定"

    def start(self) -> str:
        if self._locked:
            return "❌ 请先解锁车门"
        if len(self._tires) < 4:
            return "❌ 轮胎不足 4 个，无法安全行驶"
        return self._engine.start()

    def drive(self, distance_km: float = 10.0, speed: int = 60) -> List[str]:
        """驾驶一段距离"""
        logs = []

        if not self._engine.is_running:
            logs.append("❌ 请先启动引擎")
            return logs

        # 换档到 D
        logs.append(self._transmission.shift('D'))

        # 加速
        target_rpm = speed * 30  # 简单换算
        rpm_log, current_rpm = self._engine.accelerate(target_rpm)
        logs.append(rpm_log)
        self._speed = speed

        # 行驶
        segments = max(1, int(distance_km / 0.5))
        for i in range(segments):
            seg_km = distance_km / segments

            # 消耗燃油 (8L/100km)
            fuel_needed = seg_km * 0.08
            if not self._fuel_tank.consume(fuel_needed):
                logs.append("⛽ 燃油耗尽！")
                break

            # 轮胎磨损
            for tire in self._tires:
                tire.wear(seg_km)

            # 里程增加
            self._odometer += seg_km

            # 自动换档
            shift_log = self._transmission.auto_shift(current_rpm)
            if shift_log:
                logs.append(shift_log)

            if i % 5 == 0:
                logs.append(f"  行驶中... {seg_km * (i + 1):.1f}km, "
                           f"油量 {self._fuel_tank.percentage():.0f}%")

        logs.append(f"🏁 到达！总计行驶: {distance_km:.1f}km")
        return logs

    def stop(self) -> str:
        self._speed = 0
        engine_log = self._engine.stop()
        park_log = self._transmission.shift('P')
        return f"{engine_log}\n{park_log}"

    def refuel(self, liters: float) -> str:
        return self._fuel_tank.refill(liters)

    # ═══════════════════════════════════════
    # 信息查询
    # ═══════════════════════════════════════

    def dashboard(self) -> str:
        """仪表盘信息"""
        lines = [
            f"╔══════════════════════════════╗",
            f"║  🚗 {self.brand} {self.model} ({self.year})",
            f"║  ⚡ {self._speed} km/h | {self._engine.rpm} rpm",
            f"║  ⛽ 油量: {self._fuel_tank.percentage():.0f}% | "
            f"🌡️  {self._engine.temperature:.0f}°C",
            f"║  ⚙️  {self._transmission.gear} | "
            f"📏 {self._odometer:.0f} km",
            f"║  🛞 轮胎: {len(self._tires)}个",
            f"║  🗺️  GPS: {self._gps.model if self._gps else '未安装'}",
            f"╚══════════════════════════════╝",
        ]
        return "\n".join(lines)

    def spec(self) -> str:
        """车辆规格"""
        return (f"\n🚗 {self.brand} {self.model} 规格:\n"
                f"  引擎: {self._engine}\n"
                f"  变速箱: {self._transmission}\n"
                f"  油箱: {self._fuel_tank}\n"
                f"  轮胎: {', '.join(str(t) for t in self._tires)}\n"
                f"  GPS: {self._gps}")

    def __repr__(self) -> str:
        return f"Car({self.brand} {self.model}, {self.year})"


# ====================================
# 演示
# ====================================

def demo():
    print("=" * 60)
    print("🚗 汽车模型 — 组合/聚合/依赖注入演示")
    print("=" * 60)

    # 创建汽车（组合组件在内部创建）
    my_car = Car("Toyota", "Camry", 2026)

    # 创建轮胎（聚合 — 独立对象）
    tires = [
        Tire("Michelin", "Primacy 4+"),
        Tire("Michelin", "Primacy 4+"),
        Tire("Michelin", "Primacy 4+"),
        Tire("Michelin", "Primacy 4+"),
    ]
    # 调整胎压
    for t in tires:
        t.inflate(34)

    # 安装轮胎（聚合动作）
    print(f"\n📦 安装组件:")
    print(f"  {my_car.install_tires(tires)}")

    # 安装 GPS（依赖注入）
    gps = GPS("高德地图车机版")
    print(f"  {my_car.install_gps(gps)}")

    # 仪表盘
    print(f"\n📊 初始状态:")
    print(my_car.dashboard())

    # 驾驶
    print(f"\n🏎️ 驾驶体验:")
    print(f"  {my_car.unlock()}")
    print(f"  {my_car.start()}")

    drive_logs = my_car.drive(distance_km=50, speed=80)
    for log in drive_logs:
        print(f"  {log}")

    # 检查轮胎
    print(f"\n🛞 轮胎检查:")
    for status in my_car.check_tires():
        print(f"  {status}")

    # 更换一个轮胎（聚合的优势）
    print(f"\n🔄 更换轮胎:")
    new_tire = Tire("Bridgestone", "Turanza T005")
    new_tire.inflate(36)
    print(f"  {my_car.replace_tire(0, new_tire)}")

    # 导航
    print(f"\n🗺️ GPS 导航:")
    print(f"  {my_car.navigate('北京首都机场')}")

    # 停车
    print(f"\n🅿️ 停车:")
    print(f"  {my_car.stop()}")
    print(f"  {my_car.lock()}")

    # 最终信息
    print(f"\n📊 最终状态:")
    print(my_car.spec())

    # 验证关系
    print(f"\n🔍 关系验证:")
    print(f"  Car → Engine: 组合（Engine 在 Car 内部创建）")
    print(f"  Car → Tire: 聚合（Tire 从外部传入，可独立更换）")
    print(f"  Car → GPS: 依赖注入（可选，运行时安装/卸载）")

    print("\n" + "=" * 60)
    print("✅ 汽车模型演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
