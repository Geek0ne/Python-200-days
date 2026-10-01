# Day 172 图解 — Docker 容器化

配套 `../README.md`。本课图解全部围绕一个问题：
**「为什么这些坑会发生」**。

---

## 图 1：容器 vs 虚拟机的隔离层次

```
虚拟机方案                          容器方案
┌──────────────┐                  ┌──────────────┐
│   App A      │                  │   App A      │  ← 各自 PID namespace，
├──────────────┤                  ├──────────────┤    看到彼此 PID=1
│  Guest OS A  │ ← 3GB+ 虚拟磁盘  │  共享内核     │
├──────────────┤                  ├──────────────┤
│  Hypervisor  │                  │   App B      │
├──────────────┤                  ├──────────────┤
│   App B      │                  │  共享内核     │
├──────────────┤                  ├──────────────┤
│  Guest OS B  │                  │   App C      │
├──────────────┤                  └──────────────┘
│  Hypervisor  │
├──────────────┤                  启动：毫秒级
│  Host Kernel │                  体积：MB 级
└──────────────┘
 启动：分钟级                       代价：共享内核 ⇒ 隔离弱于 VM
 体积：GB 级
```

**代价即收益**：省掉虚拟硬件，代价是所有容器共享一个内核 ——
这正是「容器逃逸」风险的理论来源。

---

## 图 2：一次 `docker run` 的完整链路

```
用户              docker CLI           dockerd              containerd-shim
 │                    │                    │                      │
 │ docker run         │                    │                      │
 │───────────────────>│                    │                      │
 │                    │ POST /create      │                      │
 │                    │───────────────────>│                      │
 │                    │                    │ 1. 从镜像快照建可写层  │
 │                    │                    │ 2. 创建 PID/Mount/Net │
 │                    │                    │    namespace          │
 │                    │                    │ 3. cgroup 设限额       │
 │                    │                    │ 4. iptables DNAT:     │
 │                    │                    │    :18000 -> 容器:8000 │
 │                    │                    │ 5. 拉起 shim ─────────>│
 │                    │                    │                      │ fork 主进程
 │                    │ POST /start        │                      │ (容器内 PID 1)
 │                    │───────────────────>│                      │
 │<───────────────────│ 容器 ID            │                      │
 │                    │                    │                      │ 应用开始监听
 │<───── 200 OK ──────│<── 流量经 DNAT ─────│<─────────────────────│
```

---

## 图 3：分层与「删除文件体积不降」

```
lowerdir (只读, 不可变)          upperdir (可写, 临时)
┌────────────────────────┐      ┌────────────────────────┐
│ Layer 0  base   130MB   │      │ 你手动 rm 掉的大文件    │
│ Layer 1  pip     15MB   │      │  ↓                      │
│ Layer 2  app.py  12kB   │      │ whiteout 标记(几字节)   │
└────────────────────────┘      └────────────────────────┘
        ↓ OverlayFS 叠加                 ↓
   ┌──────────────────────────────────────────┐
   │ 容器看到的 /：lower 全部 + upper 的增删改  │
   └──────────────────────────────────────────┘
   磁盘实际占用 = 130 + 15 + 0.012 + upper，
   **rm 一个 50MB 文件，上层标记只有几字节，但下层那 50MB 还在**
```

**推论**：镜像层不可变 ⇒ 想让文件真正消失，只能重新构建一个不含它的层。
这正是多阶段构建存在的理由。

---

## 图 4：缓存命中与否的分界线（实验 3 的核心）

```
改 main.py 之后，哪些层要重跑？

✅ 好的写法                       ❌ 坏的写法
FROM python:3.12-slim      0.1s   FROM python:3.12-slim      0.1s
WORKDIR /app                0.1s   WORKDIR /app                0.1s
COPY requirements.txt .  ✅缓存    COPY . .                 ❌ 失效!
RUN pip install ...      ✅9.0s*   RUN pip install ...      ❌ 重跑 9.4s
COPY main.py .            ❌ 0.3s   CMD ["python",…]            0.1s
RUN compileall …          ❌ 0.5s
USER appuser              ❌ 0.1s                        hot ≈ 9.4s（实测）
ENV …                     ❌ 0.1s
EXPOSE 8000               ❌ 0.1s                        * 只有 requirements.txt
CMD ["python",…]          ❌ 0.1s                          变了才重跑
                         hot ≈ 1.7s（实测）
```

```
                        命中缓存              从此失效
FROM / WORKDIR      ├────────────────┤
COPY requirements   ├────────────────┤
RUN pip install     ├────────────────┤
COPY main.py ────────────────────────┤  ← 代码进了上下文，分界线在此
RUN/USER/ENV/CMD    ────────────────────────┤
```

---

## 图 5：端口映射与 namespace 翻车点

```
宿主 netns                          容器 netns
┌────────────────────────┐          ┌────────────────────────┐
│ 127.0.0.1:18000        │          │ eth0 172.17.0.2         │
│        │               │          │    │                   │
│  iptables DNAT         │          │ 8000│                   │
│  18000 → 172.17.0.2:8000 ────────>│    ▼                   │
│                        │          │ python 监听 0.0.0.0 ✅  │
└────────────────────────┘          └────────────────────────┘

翻车：应用绑 127.0.0.1
┌────────────────────────┐          ┌────────────────────────┐
│ 宿主 127.0.0.1         │  ✗ 两条    │ 容器 127.0.0.1:8000    │
│                        │  127 是    │   ▲                     │
│ 宿主 DNAT 过来的包     │  不同的   │   └── 只接容器内流量    │
│ 落到宿主 127，不转发   │  loopback  │       宿主包进不来 ❌   │
└────────────────────────┘          └────────────────────────┘

结果：容器内 curl → 200；宿主 curl → 000（连接失败）
容器状态却是 Up（因为进程活着），最迷惑人的失败模式。
```

---

## 图 6：多阶段构建与 prefix 陷阱（实验 8 的翻车点）

```
builder 阶段                          final 阶段
RUN pip install --prefix=/install     FROM python:3.12-slim
       │                                     │
       ▼                                     ▼
默认路径              prefix 路径        从这里拷（正确）✅
/usr/local/lib/       /install/lib/      COPY --from=builder
python3.12/site-      python3.12/site-   /install/lib/python3.12/site-packages/
packages/    ✗        packages/    ✅      → /usr/local/lib/python3.12/site-packages/

                ❌ 从 /usr/local/... 拷 = 拷了 final 阶段自己的空目录
                   → 构建成功、history 显示 5MB（其实拷的是别的层的空壳）
                   → 运行时 python 找不到 flask → 容器秒退
```

> `COPY` 一个不存在的路径会报错；`COPY` 一个**存在但为空**的路径**不报错**。
> 这就是「构建全绿但运行失败」的来源。

---

## 图 7：构建上下文与 .dockerignore（实验 6 实测）

```
无 .dockerignore                     有 .dockerignore
$ docker build .                     $ docker build .
Sending build context 60.01MB        Sending build context 10.75kB
   ├─ junk/big.bin   57.2MB 垃圾       └─ 只剩 Dockerfile/源码/requirements
   ├─ __pycache__/   2.8MB 垃圾
   └─ 真实源码        10.75kB
                                      ↓ 压缩约 5,600×
每次构建都要传输 + daemon 端解包上下文
```