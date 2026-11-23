"""
Day 033 — 继承：基础用法
======================================================================
单继承、方法重写、super()、MRO、isinstance/issubclass
======================================================================
"""

# ====================================================================
# 1. 单继承基础
# ====================================================================
print("=" * 60)
print("1️⃣  单继承基础 — is-a 关系")
print("=" * 60)


class Animal:
    """动物基类"""

    def __init__(self, name, age=0):
        self.name = name
        self.age = age

    def speak(self):
        return "... (无声)"

    def move(self):
        return f"{self.name} 在移动"

    def __str__(self):
        return f"{self.name} ({self.age}岁)"


class Dog(Animal):
    """狗 — 继承 Animal"""

    def speak(self):
        return "汪汪! Woof!"

    def wag_tail(self):
        return f"{self.name} 摇尾巴了! 🐕"


class Cat(Animal):
    """猫 — 继承 Animal"""

    def speak(self):
        return "喵喵! Meow~"

    def purr(self):
        return f"{self.name} 在打呼噜... 😸"


class Bird(Animal):
    """鸟 — 继承 Animal"""

    def __init__(self, name, age, can_fly=True):
        super().__init__(name, age)
        self.can_fly = can_fly

    def speak(self):
        return "啾啾! Chirp~"

    def move(self):
        if self.can_fly:
            return f"{self.name} 飞走了!"
        return super().move()


print("  创建动物:")
animals = [
    Dog("旺财", 3),
    Cat("咪咪", 2),
    Bird("小叽", 1),
    Bird("企鹅", 2, can_fly=False),
]

for animal in animals:
    print(f"\n  {animal}:")
    print(f"    → speak(): {animal.speak()}")
    print(f"    → move():  {animal.move()}")

print(f"\n  多态 — 统一处理:")
for animal in animals:
    print(f"    {animal.name}: {animal.speak()}")

# 子类专属方法
dog = Dog("Lucky", 4)
print(f"\n  子类专属方法:")
print(f"    {dog.wag_tail()}")


# ====================================================================
# 2. 方法重写 (Override)
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  方法重写 — 保留父类行为 + 扩展")
print("=" * 60)


class Vehicle:
    """交通工具"""

    def __init__(self, brand, model):
        self.brand = brand
        self.model = model
        self._speed = 0

    def start(self):
        return f"{self.brand} {self.model} 启动"

    def accelerate(self, amount):
        self._speed += amount
        return f"加速中... 当前速度: {self._speed} km/h"

    def stop(self):
        self._speed = 0
        return f"已停止"

    def info(self):
        return f"{self.brand} {self.model}"


class Car(Vehicle):
    """汽车 — 重写加速"""

    def __init__(self, brand, model, doors=4):
        super().__init__(brand, model)
        self.doors = doors

    def start(self):
        base = super().start()
        return f"{base} 🚗 引擎轰鸣!"

    def accelerate(self, amount):
        if amount > 30:
            print(f"  ⚠️  急加速!")
        return super().accelerate(amount)

    def honk(self):
        return "📯 滴滴!"  # 新增方法


class ElectricCar(Car):
    """电动车"""

    def __init__(self, brand, model, battery_kwh):
        super().__init__(brand, model, doors=4)
        self.battery_kwh = battery_kwh

    def start(self):
        base = Vehicle.start(self)  # 跳过 Car.start
        return f"{base} ⚡ (静音启动, 电量: {self.battery_kwh}kWh)"

    def accelerate(self, amount):
        self.battery_kwh -= amount * 0.1
        return f"{super().accelerate(amount)} [电量: {self.battery_kwh:.1f}kWh]"


print("  车辆测试:")
car = Car("Toyota", "Camry", 4)
tesla = ElectricCar("Tesla", "Model 3", 75)

print(f"  🚗 {car.info()}:")
print(f"    {car.start()}")
print(f"    {car.accelerate(20)}")
print(f"    {car.accelerate(40)}")
print(f"    {car.stop()}")
print(f"    {car.honk()}")

print(f"\n  ⚡ {tesla.info()}:")
print(f"    {tesla.start()}")
print(f"    {tesla.accelerate(30)}")
print(f"    {tesla.accelerate(50)}")


# ====================================================================
# 3. super() 详解
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  super() 详解 — 调用父类方法")
print("=" * 60)


class A:
    def __init__(self):
        print(f"    A.__init__ (id={id(self)})")
        self.a = 1

    def method(self):
        return "A.method"


class B(A):
    def __init__(self):
        print(f"    B.__init__ (id={id(self)})")
        super().__init__()
        self.b = 2

    def method(self):
        return f"B.method → {super().method()}"


class C(A):
    def __init__(self):
        print(f"    C.__init__")
        super().__init__()
        self.c = 3

    def method(self):
        return f"C.method → {super().method()}"


print("  创建 B 实例:")
obj_b = B()
print(f"    obj_b.a = {obj_b.a}, obj_b.b = {obj_b.b}")
print(f"    obj_b.method(): {obj_b.method()}")

print("\n  super() 的本质:")
print(f"    B.__mro__ = {[c.__name__ for c in B.__mro__]}")


# ====================================================================
# 4. MRO (方法解析顺序)
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  MRO — 方法解析顺序")
print("=" * 60)


class X:
    def method(self):
        return "X"

class Y(X):
    def method(self):
        return f"Y → {super().method()}"

class Z(X):
    def method(self):
        return f"Z → {super().method()}"

class W(Y, Z):
    def method(self):
        return f"W → {super().method()}"


print("  菱形继承 D(B, C):")
print(f"    W.__mro__ = {[c.__name__ for c in W.__mro__]}")
print(f"    W().method() = {W().method()}")
print("  → W → Y → Z → X → object")
print("  → super() 在 Y 中调用的是 Z (不是 X!)")

# isinstance 和 issubclass
print(f"\n  isinstance/issubclass:")
print(f"    isinstance(W(), Y): {isinstance(W(), Y)}")
print(f"    isinstance(W(), Z): {isinstance(W(), Z)}")
print(f"    isinstance(W(), X): {isinstance(W(), X)}")
print(f"    issubclass(W, Y): {issubclass(W, Y)}")
print(f"    issubclass(W, Z): {issubclass(W, Z)}")
print(f"    issubclass(W, X): {issubclass(W, X)}")

# type 不检查继承
print(f"\n  type vs isinstance:")
w = W()
print(f"    type(w) is W: {type(w) is W}")
print(f"    type(w) is Y: {type(w) is Y}")  # False!
print(f"    isinstance(w, Y): {isinstance(w, Y)}")  # True


# ====================================================================
# 5. 多继承
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  多继承基础")
print("=" * 60)


class AudioPlayer:
    """音频播放器"""

    def __init__(self):
        self.volume = 50

    def play(self, track):
        return f"🎵 播放: {track} (音量: {self.volume}%)"

    def set_volume(self, vol):
        self.volume = max(0, min(100, vol))


class VideoPlayer:
    """视频播放器"""

    def __init__(self):
        self.brightness = 100

    def play(self, track):
        return f"🎬 播放视频: {track} (亮度: {self.brightness}%)"

    def set_brightness(self, bri):
        self.brightness = max(0, min(100, bri))


class MediaPlayer(AudioPlayer, VideoPlayer):
    """媒体播放器 — 多继承"""

    def __init__(self):
        AudioPlayer.__init__(self)
        VideoPlayer.__init__(self)

    def play(self, track):
        # 明确指定调用哪个父类的方法
        audio_info = AudioPlayer.play(self, track)
        video_info = VideoPlayer.play(self, track)
        return f"{audio_info}\n    {video_info}"


print("  多继承:")
mp = MediaPlayer()
mp.set_volume(70)
mp.set_brightness(80)
print(f"    Music: {AudioPlayer.play(mp, '晴天')}")
print(f"    Video: {VideoPlayer.play(mp, '电影.mp4')}")
print(f"    Combined:")
print(f"      {mp.play('音乐MV.mp4')}")
print(f"    MRO: {[c.__name__ for c in MediaPlayer.__mro__]}")


print("\n" + "=" * 60)
print("✅  Day 33 基础用法演示完成!")
print("=" * 60)
