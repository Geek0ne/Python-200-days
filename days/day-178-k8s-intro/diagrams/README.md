# Day 178 — 原理图解

五张图，从「K8s 由什么组成」到「一次发布怎么滚起来」。

---

## 图 1 · K8s 体系结构：控制平面 + 工作节点

```
                     ┌──────────────────────────────────────────┐
                     │              控制平面 (Control Plane)     │
                     │                                          │
   kubectl ─────────▶│  kube-apiserver ◀────▶ etcd              │
   (只是客户端)      │       ▲    ▲           (唯一状态源)      │
                     │       │    │                             │
                     │       │    └── controller-manager        │
                     │       │        (调和循环的大脑)           │
                     │       └──────── scheduler                │
                     │                (选节点，不创建 Pod)       │
                     └───────────────────┬──────────────────────┘
                                         │ watch / 上报
              ┌──────────────────────────┼──────────────────────┐
              │                          ▼                      │
              │  ┌───────────────┐  ┌──────────────┐            │
              │  │    kubelet    │  │  kube-proxy  │   工作节点  │
              │  │ (节点的管家)  │  │ (Service 转发)│            │
              │  └──────┬────────┘  └──────────────┘            │
              │         ▼                                       │
              │  containerd ──▶ [Pod: 容器A + 容器B]            │
              └─────────────────────────────────────────────────┘
```

要点：**所有组件只和 apiserver 说话**；etcd 是唯一的状态源，apiserver 是唯一的入口。
scheduler 只做「绑定」（把 Pod 指到某个节点），真正的创建动作由该节点的 kubelet 完成。

---

## 图 2 · 一次 `kubectl apply` 的完整链路

```
 ① kubectl apply -f deployment.yaml
        │  (计算 diff，只提交声明的期望状态)
        ▼
 ② kube-apiserver：认证 → 鉴权 → 准入控制 → schema 校验
        │
        ▼
 ③ 写入 etcd（此刻「期望状态」已落库，Pod 还不存在）
        │  watch 事件
        ▼
 ④ controller-manager 发现「实际 ≠ 期望」→ 创建 ReplicaSet
        │
        ▼
 ⑤ scheduler 为每个待调度 Pod 选节点（打分 + 绑定）
        │
        ▼
 ⑥ 目标节点 kubelet 收到任务 → 调 containerd 拉镜像、建容器
        │
        ▼
 ⑦ kubelet 持续上报状态 → apiserver → etcd（「实际状态」）
```

要点：`apply` 成功 ≠ 应用已运行，只是**期望状态已登记**。
第 ③ 和第 ⑦ 步的差值，就是 `kubectl get` 里你看到的 Pending/Running 流转。

---

## 图 3 · 控制链与调和循环（自愈的根源）

```
   Deployment ──owns──▶ ReplicaSet ──owns──▶ Pod × 3
       │                    │                  │
       │   期望: replicas=3 │                  │
       │                    │   每隔几秒调和：  │
       │                    │   数一数活着的 Pod │
       ▼                    ▼                  ▼
  你手动删掉 1 个 Pod ──▶ 实际 2 ≠ 期望 3 ──▶ 补建 1 个新 Pod
```

要点：**调和是幂等的、level-triggered 的**——控制器不关心「发生了什么事件」，
只反复对比「现在是什么样」和「应该是什么样」。所以删 Pod 会自愈、节点宕机会迁移、
改副本数会收敛，这一切都不需要你再发第二条命令。

---

## 图 4 · Service 网络模型

```
                    ClusterIP: 10.96.0.10 (虚拟 IP，永不对应网卡)
   客户端 Pod ──────▶ kube-proxy (iptables/IPVS 规则)
                          │  按 selector{app=nginx} 查 EndpointSlice
                          ├──────────▶ Pod 1 (10.244.0.5:80)
                          ├──────────▶ Pod 2 (10.244.0.7:80)
                          └──────────▶ Pod 3 (10.244.0.9:80)

   访问方式扩展：
   ClusterIP    集群内部（默认）
   NodePort     节点IP:30000-32767 ──▶ ClusterIP ──▶ Pod
   LoadBalancer 云厂商 LB ──▶ NodePort ──▶ ClusterIP ──▶ Pod
```

要点：Service 不是一个进程，是 **VIP + 一组转发规则**。
Endpoints 由 selector 匹配 Pod 标签自动生成——Pod 换了 IP，规则自动跟着变，
所以集群内访问永远用稳定的名字 `nginx-service.default.svc.cluster.local`。

---

## 图 5 · 滚动更新与回滚（RollingUpdate）

```
  初始：  RS-v1: [✅][✅][✅]        RS-v2: [ ]

  更新 image=v2（maxSurge=1, maxUnavailable=0）：

  第1步:  RS-v1: [✅][✅][✅]        RS-v2: [✅]          ← 先加后减，容量不降
  第2步:  RS-v1: [✅][✅][ ]         RS-v2: [✅][✅]
  第3步:  RS-v1: [✅][ ][ ]          RS-v2: [✅][✅][✅]
  终态:   RS-v1: [ ][ ][ ]（保留）  RS-v2: [✅][✅][✅]

  回滚: kubectl rollout undo ──▶ 把「期望」指回 RS-v1 的模板，再走一遍同样的调和
```

要点：滚动更新 = **新建一个 ReplicaSet 扩容、旧的缩容**，两个 RS 交叉推进。
回滚不是「撤销操作」，只是把期望状态改回旧版本——和图 3 的调和循环是同一套机制。
`maxSurge` 控制最多多建几个，`maxUnavailable` 控制最多少几个，两者共同决定「滚多快」。
