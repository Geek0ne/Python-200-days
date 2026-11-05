# Day 070 — Redis

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

## 小结

- 选结构先选场景：计数用 string、队列用 list、排行用 zset
- Cache-Aside + 删除式失效 + TTL 抖动，覆盖 80% 缓存需求
- 队列用 `lpush/brpop`，锁用 `SET NX EX` + token 校验删除
- 线上禁 `KEYS`，value 别贪大，内存设上限
