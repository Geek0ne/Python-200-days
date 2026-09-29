#!/usr/bin/env python3
"""
Day 062 - 数据序列化
示例 2: pickle / msgpack / YAML 进阶用法

本示例演示：
1. pickle 序列化 (Python 专属二进制格式)
2. msgpack 序列化 (跨语言二进制格式)
3. PyYAML 配置解析
4. 三种格式的序列化体积与性能对比

运行方式: python3 02-pickle-msgpack-yaml.py
"""

import pickle
import json
import time
import sys
from datetime import datetime
from pathlib import Path

# msgpack 和 yaml 是第三方库，需要安装
# pip install msgpack pyyaml

print("=" * 60)
print("📦 pickle / msgpack / YAML 序列化")
print("=" * 60)

# ─── 准备测试数据 ───
test_data = {
    "name": "Python 序列化测试",
    "version": 3.12,
    "list": list(range(1000)),
    "nested": {
        "dict": {"a" * i: i for i in range(50)}
    },
    "is_active": True,
    "score": 99.99,
    "numbers": [float(i) * 1.5 for i in range(500)]
}

print(f"\n测试数据大小: 约 {sys.getsizeof(json.dumps(test_data)) / 1024:.1f} KB (JSON 字符串)")

# ════════════════════════════════════════════
# 1. pickle — Python 专属二进制序列化
# ════════════════════════════════════════════

print("\n" + "=" * 50)
print("1️⃣  pickle — Python 专属")

# pickle 支持几乎所有的 Python 对象
pickle_data = pickle.dumps(test_data)
print(f"pickle 序列化大小: {len(pickle_data)} bytes ({len(pickle_data)/1024:.2f} KB)")

restored = pickle.loads(pickle_data)
print(f"反序列化成功: {restored['name']}")

# pickle 支持自定义类
print("\n--- pickle 自定义类 ---")


class User:
    """用户类 — pickle 可以直接序列化"""
    def __init__(self, name: str, age: int, roles: list):
        self.name = name
        self.age = age
        self.roles = roles
        self.created_at = datetime.now()

    def __repr__(self):
        return f"User(name={self.name}, age={self.age}, roles={self.roles})"


user = User("Alice", 30, ["admin", "editor"])
pickled_user = pickle.dumps(user)
print(f"自定义类序列化后大小: {len(pickled_user)} bytes")

restored_user = pickle.loads(pickled_user)
print(f"恢复对象: {restored_user}")
print(f"类型一致: {type(restored_user).__name__}")

# 不同协议版本对比
print("\n--- pickle 协议版本对比 ---")
for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
    data_bytes = pickle.dumps(test_data, protocol=protocol)
    size_kb = len(data_bytes) / 1024
    print(f"Protocol {protocol}: {len(data_bytes)} bytes ({size_kb:.2f} KB)")

# pickle 不安全演示
print("\n--- pickle 安全警告 ---")
print("⚠️  pickle.loads() 可以执行任意代码！")
print("   永远不要反序列化不可信来源的 pickle 数据！")


class Dangerous:
    """演示 pickle 的安全风险"""
    def __reduce__(self):
        # __reduce__ 告诉 pickle 如何重建对象
        # 这里我们可以指定任意可调用对象和参数
        # 实际攻击中会调用 os.system 等危险函数
        return (print, ("⚠️  这个代码在反序列化时被执行了！",))


# 序列化危险对象
danger_pickle = pickle.dumps(Dangerous())
print("\n反序列化危险 pickle...")
restored_danger = pickle.loads(danger_pickle)
# 上面这行会执行 print("⚠️  这个代码在反序列化时被执行了！")

# ════════════════════════════════════════════
# 2. msgpack — 跨语言二进制序列化
# ════════════════════════════════════════════

print("\n" + "=" * 50)
print("2️⃣  msgpack — 跨语言二进制")

try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False
    print("⚠️  msgpack 未安装。安装: pip install msgpack")
    print("   跳过 msgpack 演示。")

if HAS_MSGPACK:
    # 基础使用
    packed = msgpack.packb(test_data)
    print(f"msgpack 序列化大小: {len(packed)} bytes ({len(packed)/1024:.2f} KB)")

    unpacked = msgpack.unpackb(packed)
    print(f"反序列化成功: {unpacked['name']}")

    # 自定义类型扩展
    print("\n--- msgpack 自定义类型 ---")

    # msgpack 使用 ExtType 来处理自定义类型
    # 定义类型编码
    EXT_DATETIME = 1

    def encode_datetime(obj):
        if isinstance(obj, datetime):
            return msgpack.ExtType(EXT_DATETIME, obj.isoformat().encode())
        raise TypeError(f"Unknown type: {type(obj)}")

    def decode_datetime(code, data):
        if code == EXT_DATETIME:
            return datetime.fromisoformat(data.decode())
        return msgpack.ExtType(code, data)

    data_with_dt = {
        "name": "测试",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    packed_ext = msgpack.packb(data_with_dt, default=encode_datetime)
    print(f"含 datetime 的 msgpack 大小: {len(packed_ext)} bytes")

    unpacked_ext = msgpack.unpackb(packed_ext, ext_hook=decode_datetime)
    print(f"恢复的 datetime: {unpacked_ext['created_at']}")

# ════════════════════════════════════════════
# 3. YAML — 人类可读的配置文件格式
# ════════════════════════════════════════════

print("\n" + "=" * 50)
print("3️⃣  YAML — 人类可读的配置格式")

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("⚠️  pyyaml 未安装。安装: pip install pyyaml")
    print("   跳过 YAML 演示。")

if HAS_YAML:
    # 基础使用
    yaml_str = yaml.dump(test_data, default_flow_style=False)
    print(f"YAML 字符串大小: {len(yaml_str)} bytes ({len(yaml_str)/1024:.2f} KB)")
    print(f"\nYAML 输出预览 (前 300 字符):\n{yaml_str[:300]}...")

    # safe_load 是推荐的加载方式
    restored_yaml = yaml.safe_load(yaml_str)
    print(f"\nYAML 反序列化成功: {restored_yaml['name']}")

    # YAML 高级特性: 锚点 & 别名
    print("\n--- YAML 锚点与别名 ---")

    yaml_anchors = """
defaults: &defaults
  timeout: 30
  retries: 3
  debug: false

development:
  <<: *defaults
  debug: true
  host: localhost

production:
  <<: *defaults
  host: api.example.com
  timeout: 60
"""

    config = yaml.safe_load(yaml_anchors)
    print(f"Development 配置: {config['development']}")
    print(f"Production 配置:  {config['production']}")
    print(f"  -> production.debug = {config['production']['debug']}")  # 覆盖为 false

    # YAML 多文档
    print("\n--- YAML 多文档 ---")

    multi_yaml = """
---
api_version: v1
endpoints:
  - /users
  - /posts
---
api_version: v2
endpoints:
  - /api/v2/users
  - /api/v2/posts
"""
    docs = list(yaml.safe_load_all(multi_yaml))
    print(f"YAML 多文档数量: {len(docs)}")
    for i, doc in enumerate(docs):
        print(f"  文档 {i+1}: api_version={doc['api_version']}")

    # YAML 写入文件
    temp_yaml = Path("/tmp/day062_test.yaml")
    with open(temp_yaml, "w", encoding="utf-8") as f:
        yaml.dump(test_data, f, default_flow_style=False, allow_unicode=True)
    print(f"\nYAML 文件已写入: {temp_yaml}")
    
    # 验证读回
    with open(temp_yaml, "r") as f:
        verify = yaml.safe_load(f)
    print(f"文件读回验证: {verify['name']}")
    temp_yaml.unlink()

# ════════════════════════════════════════════
# 4. 性能与体积对比
# ════════════════════════════════════════════

print("\n" + "=" * 50)
print("4️⃣  序列化格式性能与体积对比")
print("=" * 50)

N = 5000
results = []

# JSON
json_str = json.dumps(test_data)
results.append(("JSON", len(json_str)))

# pickle
pickle_bytes = pickle.dumps(test_data)
results.append(("pickle", len(pickle_bytes)))

if HAS_MSGPACK:
    packed = msgpack.packb(test_data)
    results.append(("msgpack", len(packed)))

if HAS_YAML:
    yaml_out = yaml.dump(test_data, default_flow_style=False)
    results.append(("YAML", len(yaml_out)))

print(f"\n{'格式':<12} {'大小(bytes)':<16} {'相对JSON':<12}")
print("-" * 40)
json_size = len(json_str)

for name, size in results:
    ratio = size / json_size
    bar = "█" * int(ratio * 20)
    print(f"{name:<12} {size:<16} {ratio*100:<6.1f}%  {bar}")

# 序列化速度测试
print(f"\n{'格式':<12} {'序列化(ms)':<16} {'反序列化(ms)':<16}")
print("-" * 44)

# JSON
start = time.perf_counter()
for _ in range(N):
    json.dumps(test_data)
json_ser = (time.perf_counter() - start) / N * 1000

start = time.perf_counter()
for _ in range(N):
    json.loads(json_str)
json_deser = (time.perf_counter() - start) / N * 1000
print(f"{'JSON':<12} {json_ser:<16.3f} {json_deser:<16.3f}")

# pickle
start = time.perf_counter()
for _ in range(N):
    pickle.dumps(test_data)
pickle_ser = (time.perf_counter() - start) / N * 1000

start = time.perf_counter()
for _ in range(N):
    pickle.loads(pickle_bytes)
pickle_deser = (time.perf_counter() - start) / N * 1000
print(f"{'pickle':<12} {pickle_ser:<16.3f} {pickle_deser:<16.3f}")

if HAS_MSGPACK:
    start = time.perf_counter()
    for _ in range(N):
        msgpack.packb(test_data)
    msg_ser = (time.perf_counter() - start) / N * 1000

    start = time.perf_counter()
    for _ in range(N):
        msgpack.unpackb(packed)
    msg_deser = (time.perf_counter() - start) / N * 1000
    print(f"{'msgpack':<12} {msg_ser:<16.3f} {msg_deser:<16.3f}")

print("\n📊 结论:")
print("  - pickle 速度最快，但仅限 Python 生态")
print("  - msgpack 体积最小，适合网络传输")
print("  - JSON 均衡，跨语言兼容性最好")
print("  - YAML 最慢最胖，但人类可读性最好")

print("\n✅ 示例完成！")
