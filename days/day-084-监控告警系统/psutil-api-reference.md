# psutil API 速查表

## CPU 相关

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `cpu_percent(interval=None, percpu=False)` | float/list | CPU 使用率 (%) |
| `cpu_count(logical=True)` | int | CPU 核心数 |
| `cpu_freq(percpu=False)` | namedtuple | CPU 频率 (current, min, max) |
| `cpu_times(percpu=False)` | namedtuple | CPU 时间分配 |
| `cpu_stats()` | namedtuple | CPU 统计信息 |
| `getloadavg()` | tuple | 系统负载 (1/5/15分钟) |

### 使用示例

```python
import psutil

# CPU 使用率（阻塞1秒获取准确值）
cpu_percent = psutil.cpu_percent(interval=1)

# 每个核心的使用率
per_cpu = psutil.cpu_percent(interval=1, percpu=True)

# CPU 频率
freq = psutil.cpu_freq()
print(f"当前频率: {freq.current}MHz")

# 系统负载（Linux/macOS）
load1, load5, load15 = psutil.getloadavg()
```

---

## 内存相关

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `virtual_memory()` | namedtuple | 虚拟内存信息 |
| `swap_memory()` | namedtuple | 交换内存信息 |

### virtual_memory 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 内存总量 (bytes) |
| `available` | int | 可用内存 (bytes) |
| `used` | int | 已用内存 (bytes) |
| `free` | int | 空闲内存 (bytes) |
| `percent` | float | 使用率 (%) |
| `active` | int | 活跃内存 (Linux) |
| `inactive` | int | 非活跃内存 (Linux) |
| `buffers` | int | 缓冲区 (Linux) |
| `cached` | int | 缓存 (Linux) |

### 使用示例

```python
import psutil

mem = psutil.virtual_memory()

# 转换为 GB
total_gb = mem.total / (1024**3)
available_gb = mem.available / (1024**3)
used_gb = mem.used / (1024**3)

print(f"总量: {total_gb:.2f} GB")
print(f"可用: {available_gb:.2f} GB")
print(f"已用: {used_gb:.2f} GB")
print(f"使用率: {mem.percent}%")
```

---

## 磁盘相关

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `disk_usage(path)` | namedtuple | 磁盘使用情况 |
| `disk_io_counters(perdisk=False, nowrap=True)` | namedtuple | 磁盘 I/O 统计 |
| `disk_partitions(all=False)` | list | 磁盘分区信息 |

### disk_usage 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 总容量 (bytes) |
| `used` | int | 已用 (bytes) |
| `free` | int | 可用 (bytes) |
| `percent` | float | 使用率 (%) |

### 使用示例

```python
import psutil

# 根目录使用情况
disk = psutil.disk_usage('/')
print(f"使用率: {disk.percent}%")

# 磁盘 I/O 统计
io = psutil.disk_io_counters()
print(f"读取: {io.read_bytes / (1024**2):.2f} MB")
print(f"写入: {io.write_bytes / (1024**2):.2f} MB")

# 列出所有分区
for part in psutil.disk_partitions():
    print(f"{part.device}: {part.mountpoint}")
```

---

## 网络相关

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `net_io_counters(pernic=False, nowrap=True)` | namedtuple | 网络 I/O 统计 |
| `net_connections(kind='inet')` | list | 网络连接 |
| `net_if_addrs()` | dict | 网络接口地址 |
| `net_if_stats()` | dict | 网络接口状态 |

### net_io_counters 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `bytes_sent` | int | 发送字节数 |
| `bytes_recv` | int | 接收字节数 |
| `packets_sent` | int | 发送包数 |
| `packets_recv` | int | 接收包数 |
| `errin` | int | 接收错误数 |
| `errout` | int | 发送错误数 |
| `dropin` | int | 丢弃的入站包 |
| `dropout` | int | 丢弃的出站包 |

### 使用示例

```python
import psutil

# 网络流量统计
net = psutil.net_io_counters()
print(f"发送: {net.bytes_sent / (1024**2):.2f} MB")
print(f"接收: {net.bytes_recv / (1024**2):.2f} MB")

# 网络连接
connections = psutil.net_connections()
for conn in connections:
    if conn.status == 'ESTABLISHED':
        print(f"连接: {conn.laddr} -> {conn.raddr}")

# 网络接口
for name, addrs in psutil.net_if_addrs().items():
    print(f"{name}: {addrs}")
```

---

## 进程相关

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `pids()` | list | 所有进程 PID |
| `Process(pid)` | Process | 进程对象 |
| `process_iter(attrs=None, ad_value=None)` | iterator | 遍历所有进程 |

### Process 方法

| 方法 | 说明 |
|------|------|
| `pid` | 进程 ID |
| `name()` | 进程名称 |
| `exe()` | 可执行文件路径 |
| `cwd()` | 工作目录 |
| `status()` | 进程状态 |
| `create_time()` | 创建时间 |
| `cpu_percent()` | CPU 使用率 |
| `memory_percent()` | 内存使用率 |
| `memory_info()` | 内存详情 |
| `io_counters()` | I/O 统计 |
| `connections()` | 网络连接 |
| `kill()` | 终止进程 |
| `terminate()` | 终止进程 |

### 使用示例

```python
import psutil

# 获取所有进程
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
    try:
        if proc.info['cpu_percent'] > 10:
            print(f"高 CPU: {proc.info['name']} (PID: {proc.info['pid']})")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

# 获取特定进程
proc = psutil.Process(1234)
print(f"名称: {proc.name()}")
print(f"状态: {proc.status()}")
print(f"CPU: {proc.cpu_percent()}%")
```

---

## 系统信息

| 函数 | 返回值 | 说明 |
|------|--------|------|
| `boot_time()` | float | 系统启动时间 |
| `users()` | list | 登录用户 |
| `sistimeinfo()` | namedtuple | 系统时间信息 |

### 使用示例

```python
import psutil
from datetime import datetime

# 系统启动时间
boot_time = datetime.fromtimestamp(psutil.boot_time())
print(f"启动时间: {boot_time}")

# 运行时间
uptime = datetime.now() - boot_time
print(f"运行时间: {uptime}")

# 登录用户
for user in psutil.users():
    print(f"用户: {user.name}, 终端: {user.terminal}")
```

---

> 💡 更多信息请参考 [psutil 官方文档](https://psutil.readthedocs.io/)
