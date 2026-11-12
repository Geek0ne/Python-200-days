# Day 070 — Redis 基础：缓存、队列与分布式锁

> 🎯 **今日目标**：拿下最高频的缓存中间件——redis-py 基础操作、五大结构的场景选型、缓存与过期策略（穿透 / 击穿 / 雪崩）、队列与分布式锁，最后用「缓存加速 + 任务队列」实战收尾。

## 概述

Redis 是一个内存键值数据库，快（单线程模型 + 内存操作）、结构丰富（string / hash / list / set / zset）、用途广（缓存、队列、锁、计数器、排行榜）。今天的定位是：**把它当作 Python 项目里"随手可用的基础设施"**——知道什么场景该用哪个结构，以及用错会怎样。

> 💡 本日代码同样双模式：有 Redis 环境时用 `redis-py` 打真库；`--self-test` 用内置的 `MiniRedis`（约 60 行的内存模拟）离线验证逻辑，不装任何第三方包。

## 学习目标

- 掌握 redis-py 的连接与五大结构操作
- 能为场景选对数据结构（缓存 / 队列 / 排序 / 去重）
- 理解缓存三大问题：穿透、击穿、雪崩，以及对应防护
- 会用 list 实现任务队列、用 SET NX EX 实现分布式锁
- 知道 KEYS、序列化、大 value 等常见坑

---

## 1. 环境准备

```bash
# Docker 一行起
docker run -d --name redis-dev -p 6379:6379 redis:7

# 安装客户端
pip install redis
```

```python
import redis

r = redis.Redis(host="127.0.0.1", port=6379, db=0,
                decode_responses=True)   # 直接返回 str，强烈建议开启
r.ping()   # True
```

## 2. 五大结构与场景选型

完整代码见 `code/01-redis-basics.py`。

| 结构 | 常用命令 | 典型场景 |
|------|----------|----------|
| string | `set / get / incr / setex` | 缓存对象、计数器、限流计数 |
| hash | `hset / hget / hgetall` | 对象字段级缓存（用户资料） |
| list | `lpush / brpop / lrange` | 任务队列、最新 N 条列表 |
| set | `sadd / smembers / sismember` | 去重、标签、共同好友 |
| zset | `zadd / zrangebyscore` | 排行榜、延时队列、滑动窗口限流 |

```python
# 计数器：文章阅读量（原子自增，天然并发安全）
r.incr("article:1001:views")

# 排行榜：分数更新 + 取前 10
r.zadd("leaderboard", {"alice": 95, "bob": 87, "carol": 92})
r.zrevrange("leaderboard", 0, 9)   # 降序 Top 10
```

## 3. 缓存模式与过期策略

完整代码见 `code/02-cache-patterns.py`。

**Cache-Aside（旁路缓存）**是标准姿势：

```
读：先查缓存 → 命中返回 / 未命中查库 → 回填缓存（设 TTL）
写：更新数据库 → 删除缓存（而不是更新缓存）
```

三大经典问题：

| 问题 | 现象 | 防护 |
|------|------|------|
| 穿透 | 查不存在的 key，每次都打到库 | 空值缓存 / 布隆过滤器 |
| 击穿 | 热点 key 过期瞬间，流量全打到库 | 互斥锁重建 / 逻辑过期 |
| 雪崩 | 大批 key 同时过期 | TTL 加随机抖动 / 多级缓存 |

```python
def get_user(r, db, user_id):
    key = f"user:{user_id}"
    cached = r.get(key)
    if cached is not None:
        return json.loads(cached)
    user = db.query(user_id)
    if user is None:
        r.setex(key, 60, "null")          # 空值缓存，防穿透
    else:
        r.setex(key, 300 + random.randint(0, 60), json.dumps(user))  # TTL 抖动，防雪崩
    return user
```

## 4. 队列与分布式锁

完整代码见 `code/03-queue-and-lock.py`。

**任务队列**——`lpush` 生产 + `brpop` 阻塞消费：

```python
r.lpush("tasks", json.dumps({"type": "email", "to": "a@b.com"}))
task = r.brpop("tasks", timeout=5)   # 阻塞等待，空闲不空转
```

**分布式锁**——`SET key value NX EX` 三件套（原子加锁 + 自动过期）：

```python
def acquire_lock(r, name, ttl=10):
    return r.set(f"lock:{name}", uuid4().hex, nx=True, ex=ttl)

def release_lock(r, name, token):
    # 只删自己的锁（Lua 保证原子，避免误删他人锁）
    script = 'if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) end'
    r.eval(script, 1, f"lock:{name}", token)
```

⚠️ 锁的两条铁律：**必须设 TTL**（防止持锁进程崩溃后死锁）、**只能删自己的锁**（用 token 校验）。生产环境直接用 Redlock / `redis.lock()`，手写锁仅用于理解原理。

## 5. 常见陷阱（实测）

| # | 陷阱 | 后果 | 正确做法 |
|---|------|------|----------|
| 1 | 线上用 `KEYS pattern` | 全库扫描，Redis 卡死 | `SCAN` 游标迭代 |
| 2 | 存大 JSON value | 网络/内存放大，慢查询 | 拆 hash 或压缩 |
| 3 | 忘记 `decode_responses=True` | 到处 `.decode()` | 连接时就开 |
| 4 | 用 Redis 当持久化主存储 | 丢数据 | 它是缓存/协调，不是 source of truth |
| 5 | TTL 全设一样 | 雪崩 | 加随机抖动 |
| 6 | 分布式锁不设过期 | 死锁 | `EX` 必须带 |
| 7 | 更新缓存而非删除 | 并发下脏写 | 删缓存，让读回填 |
| 8 | `hgetall` 大 hash | 一次拉爆带宽 | 按需 `hget` / 分桶 |
| 9 | 单连接裸用 | 高并发连接风暴 | 连接池（redis-py 自带） |
| 10 | 不设内存上限 | 挤爆宿主机 | `maxmemory` + 淘汰策略 |

## 6. 实战：缓存加速 + 任务队列

`code/04-cache-taskqueue.py` 端到端跑通一个小型数据管道：

1. **慢查询模拟**：一个 200ms 的"报表聚合"函数
2. **缓存加速**：Cache-Aside 包一层，对比冷/热查询耗时
3. **任务队列**：聚合结果变更 → 发布失效任务 → 后台 worker 消费重建缓存
4. **防重放**：消费端用 SET NX 做幂等去重

```bash
python code/04-cache-taskqueue.py --self-test   # MiniRedis 离线跑全流程
python code/04-cache-taskqueue.py               # 真实 Redis 环境
```

## 7. 思考题

1. **结构选型与原子性**：文章阅读量、用户资料、任务队列、共同好友、积分排行榜，分别该用哪种结构？为什么 `incr` 天生并发安全，而「`get` → 加 1 → `set`」三步走会丢计数？

**参考答案**

按场景对号入座：

- **阅读量/限流计数** → string + `incr`：一个 key 一个整数，自增即完事。
- **用户资料** → hash + `hset`/`hget`：可以只改一个字段，不必把整个对象序列化后重写。
- **任务队列** → list + `lpush` 生产、`brpop` 阻塞消费：天然有序，`brpop` 空闲时不空转。
- **去重/共同好友** → set + `sadd`/`sismember`/`sinter`：成员唯一，集合运算现成。
- **排行榜** → zset + `zadd`/`zrevrange`：每个成员带分数，按分数有序，取 Top N 是一条命令。

`incr` 安全的原因：Redis 执行命令是**单线程**的，`incr` 把「读—改—写」打包成一条命令，中间不会插进别的客户端操作。而 `get` → 本地加 1 → `set` 是三条命令，两个客户端可能同时读到 100，各自加 1 后都写回 101，两次访问只涨了 1——这就是「丢失更新」。

💡 提示：连接时加 `decode_responses=True`，返回的就是 `str` 而不是 `bytes`，省得到处 `.decode()`；但要注意此时存入的 value 也必须是字符串（对象先 `json.dumps`）。

2. **Cache-Aside 与三大缓存问题（代码）**：请离线实现一个「先查缓存、未命中查库并回填」的读函数，并说明它如何防穿透、防雪崩；击穿又该怎么防？

**参考答案**

```python
# 依赖：仅标准库（用内存字典模拟 Redis；真实环境需自行准备 Redis 并 pip install redis）
import json
import random
import time

class MiniRedis:
    """极简 Redis 模拟：只实现 get / setex / ttl，带过期时间"""
    def __init__(self):
        self.data = {}                      # key -> (value, 过期时刻)

    def get(self, key):
        item = self.data.get(key)
        if item is None:
            return None
        value, expire_at = item
        if time.monotonic() >= expire_at:   # 过期即视为不存在
            del self.data[key]
            return None
        return value

    def setex(self, key, ttl, value):
        self.data[key] = (value, time.monotonic() + ttl)

    def ttl(self, key):
        return round(self.data[key][1] - time.monotonic())

r = MiniRedis()
DB = {1: {"name": "Alice"}, 2: {"name": "Bob"}}   # 假装的数据库
db_calls = {"n": 0}                               # 统计「打到数据库」的次数

def get_user(user_id):
    """Cache-Aside：先查缓存，未命中查库并回填"""
    key = f"user:{user_id}"
    cached = r.get(key)
    if cached is not None:
        return None if cached == "null" else json.loads(cached)
    db_calls["n"] += 1
    user = DB.get(user_id)
    if user is None:
        r.setex(key, 60, "null")                          # 空值缓存，防穿透
    else:
        r.setex(key, 300 + random.randint(0, 60), json.dumps(user))  # TTL 抖动，防雪崩
    return user

print(get_user(1))        # 冷查询：打库一次
print(get_user(1))        # 热查询：命中缓存
print(get_user(2))        # 另一个用户：冷查询
print(get_user(999))      # 不存在的用户：打库一次并缓存空值
print(get_user(999))      # 再查：命中空值缓存，不再打库
print("打库次数:", db_calls["n"])
print("TTL 都在 300~360 之间:", all(300 <= r.ttl(f"user:{i}") <= 360 for i in (1, 2)))
```

预期输出：

```
{'name': 'Alice'}
{'name': 'Alice'}
{'name': 'Bob'}
None
None
打库次数: 3
TTL 都在 300~360 之间: True
```

5 次查询只打库 3 次：第 2 次查 Alice 命中缓存；第 5 次查不存在的 999 命中了「空值缓存」。这就是**防穿透**——把「查不到」这件事也缓存一小段时间（60 秒），恶意刷不存在的 id 就不会次次压到数据库。

**防雪崩**靠 TTL 抖动：`300 + random.randint(0, 60)` 让同一批写入的 key 不在同一秒集体过期，避免瞬时流量全部涌向数据库。

**防击穿**（热点 key 过期瞬间大量并发同时重建）本例没做，标准做法是「互斥锁重建」：未命中时先用 `SET NX EX` 抢一把锁，抢到的线程去查库回填，其余线程短暂等待后重读缓存；或者用「逻辑过期」——value 里存一个过期时间字段，key 本身永不 TTL，发现逻辑过期就异步重建。

⚠️ 注意：写数据时要**更新数据库后删除缓存**，而不是更新缓存，否则并发下容易留下脏值；空值缓存的 TTL 要短，避免新用户注册后长时间查不到。

3. **分布式锁的两条铁律**：为什么加锁必须用 `SET key value NX EX` 一条命令，而不能 `setnx` 之后再 `expire`？为什么释放锁要用 token 校验 + Lua 脚本，直接 `del` 会出什么事？

**参考答案**

`NX` 表示「key 不存在才设置」（抢锁），`EX` 表示同时设置过期时间。**这两件事必须原子完成**：如果拆成 `setnx` + `expire` 两步，进程恰好在两步之间崩溃，锁就永远不过期，其他进程再也抢不到——死锁。一条 `SET ... NX EX` 命令由 Redis 单线程执行，不存在中间状态。

TTL 是「持锁进程崩溃」的兜底：即使进程没了，锁也会自动释放。代价是 TTL 必须大于业务耗时，否则业务还没做完锁就过期，第二个进程拿到锁，两个进程同时操作共享资源。生产环境要么给足余量，要么用带自动续期（看门狗）的实现，如 `redis-py` 的 `redis.lock()`。

释放锁必须**只删自己的锁**。加锁时写入一个唯一 token（如 `uuid4().hex`），释放时先比对 token 再删。直接 `del` 的危险场景：A 持锁超时 → 锁自动过期 → B 抢到锁 → A 业务做完执行 `del`，删掉的却是 B 的锁，于是 C 又能进来，互斥彻底失效。「比对 + 删除」两步同样要原子，所以用 Lua 脚本交给 Redis 一次执行：

```lua
if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) end
```

💡 提示：手写锁只用于理解原理，生产直接用 `redis.lock()` 或 Redlock；另外 Redis 是缓存/协调组件，不是持久化主存储，别把唯一一份业务数据只放在里面。

## 小结

- 选结构先选场景：计数用 string、队列用 list、排行用 zset
- Cache-Aside + 删除式失效 + TTL 抖动，覆盖 80% 缓存需求
- 队列用 `lpush/brpop`，锁用 `SET NX EX` + token 校验删除
- 线上禁 `KEYS`，value 别贪大，内存设上限
