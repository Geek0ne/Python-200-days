# Day 178 练习题清单

> 目标：亲手跑通「声明期望 → 调和收敛 → 服务发现 → 滚动更新」这条主链路，
> 并亲眼看见**删 Pod 自愈**。
> **前置**：`kubectl` 可用 + 一个能折腾的集群（minikube / kind / k3d 任选，装一个即可）。
> 没有集群也能完成练习 1 的 YAML 部分（`--dry-run=client` 不碰集群）。

---

## 一、动手题（必做）

### 练习 1 — kubectl 基础与 Python 封装（10 分钟）

先用裸 kubectl 摸清对象，再跑 `code/01-basic-usage.py` 感受封装：

```bash
kubectl get nodes                          # 集群里有哪些节点
kubectl get pods -A                        # 所有命名空间的 Pod
python3 code/01-basic-usage.py             # 走一遍封装好的部署流程
```

- [ ] 能说出 `get` 和 `describe` 的输出差别（一个看列表，一个看事件与详情）
- [ ] 找到 `code/01-basic-usage.py` 里 `run_kubectl_command()` 的异常处理位置，说说它为什么必须存在
- [ ] 预习：`kubectl apply` 成功后马上 `kubectl get pods`，为什么可能一个 Pod 都没有？

<details><summary>参考答案</summary>

1. `get` 是资源列表/状态摘要；`describe` 包含 Events——排障 80% 靠它（镜像拉取失败、调度失败都写在那）。
2. `subprocess` 调 kubectl 任何一步都可能失败（集群不可达、YAML 非法），不捕获就直接抛栈崩掉。
3. `apply` 只是把**期望状态**写进 etcd（见 diagrams/README.md 图 2），Pod 由 controller/kubelet 异步创建，有秒级延迟。

</details>

### 练习 2 — 副本调和与自愈（15 分钟）

```bash
kubectl create deployment nginx --image=nginx:1.14.2 --replicas=3
kubectl get pods -w                      # 另开终端盯住
kubectl delete pod <任意一个 pod 名>     # 故意杀一个
```

- [ ] 记录被删 Pod 的名字，等 30 秒，看新 Pod 名字是否不同
- [ ] `kubectl scale deployment nginx --replicas=5`，观察 Pod 数量变化的节奏
- [ ] 用 diagrams/README.md 图 3 解释：为什么你**不需要**再发一条「补一个 Pod」的命令？

<details><summary>参考答案</summary>

被删的 Pod 不会被「复活」，而是 ReplicaSet 调和发现 2≠3 后**新建**一个（名字后缀不同）。
控制器只对比期望与实际，不关心你删没删——这就是 level-triggered 调和循环的自愈。

</details>

### 练习 3 — Service 与服务发现（15 分钟）

```bash
kubectl expose deployment nginx --port=80 --target-port=80 --type=NodePort
kubectl get svc nginx                    # 记下 ClusterIP 和 NodePort
kubectl get endpoints nginx              # 看 selector 找到了哪些 Pod IP
```

- [ ] 对照 `kubectl get pods -o wide`，确认 Endpoints 里的 IP 就是 Pod IP
- [ ] 删掉一个 Pod，再次 `kubectl get endpoints`，30 秒后有什么变化？
- [ ] 思考：为什么集群内应该用 `nginx.default.svc.cluster.local` 而不是 Pod IP？

<details><summary>参考答案</summary>

Endpoints 由 Service 的 selector 匹配 Pod 标签自动生成；Pod 重建后 IP 必变，
Endpoints 跟着更新，而 Service 的 ClusterIP 和 DNS 名**永远不变**——所以只能用服务名。

</details>

### 练习 4 — ConfigMap 注入配置（10 分钟）

```bash
kubectl create configmap app-config --from-literal=APP_ENV=production --from-literal=LOG_LEVEL=info
kubectl get cm app-config -o yaml
kubectl set env deployment/nginx --from=configmap/app-config   # 注入为环境变量
kubectl describe pod -l app=nginx | grep -A3 Environment
```

- [ ] 说说 ConfigMap 的两种消费方式（env 注入 vs volume 挂载）各自适合什么场景
- [ ] 把 Secret 和 ConfigMap 对比：Secret 多了什么、又**没**多什么？（看 README「敏感数据」一节）

<details><summary>参考答案</summary>

env 适合启动时读一次的配置；volume 挂载适合会被更新的配置文件。
Secret 只是 base64 编码 + 可走加密存储（etcd encryption at rest），**默认并不加密**——
能用 ConfigMap 的别用 Secret，真敏感的还要额外开启静态加密。

</details>

### 练习 5 — 滚动更新与回滚（15 分钟）

```bash
kubectl set image deployment/nginx nginx=nginx:1.15.0
kubectl rollout status deployment/nginx          # 盯着滚完
kubectl rollout history deployment/nginx         # 有 2 个版本了
kubectl rollout undo deployment/nginx            # 回滚到 1.14.2
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}'
```

- [ ] `rollout status` 输出里 ReplicaSet 数量变化和 diagrams/README.md 图 5 对上
- [ ] 回滚后再 `rollout history`，为什么 revision 号不是回到 1 而是新增了 3？

<details><summary>参考答案</summary>

回滚不是撤销，而是把期望状态指向旧模板、再新建一次调和（图 5 要点）。
所以历史里多了一条新 revision，内容等于旧版本——head 永远在 +1。

</details>

---

## 二、思考题（建议全做）

1. **Pod 为什么是「不可预测的」？** 结合 README「Pod 的设计原理」和练习 2 的现象作答。
2. **scheduler 只做绑定，不创建 Pod**——那么「创建 Pod」这四个字到底是谁执行的？
3. Service 的 `targetPort` 和 `port` 为什么可以不一样？各是什么的端口？
4. 如果把 `replicas: 3` 的 Deployment 改成 `replicas: 3`（一字不差重新 apply），集群里会发生什么？为什么这是个好性质？

<details><summary>参考答案要点</summary>

1. Pod 随时可能被重建（自愈、驱逐、滚动更新），名字和 IP 都会变，所以一切依赖 Pod 身份的设计都是错的。
2. 目标节点上的 kubelet（经 containerd）；scheduler 只是把 Pod「指派」到节点。
3. `port` 是 Service 虚拟 IP 暴露的端口，`targetPort` 是容器实际监听的端口，中间由 kube-proxy 转发。
4. 什么都不会发生（调和循环发现实际=期望）。声明式 + 幂等 = 可以放心重复执行，这是 GitOps 的根基。

</details>

---

## 三、自查清单

- [ ] 能画出 kubectl apply 之后到容器运行的 7 步链路（图 2）
- [ ] 能解释「删 Pod 自愈」为什么不需要额外命令（图 3）
- [ ] 知道 ClusterIP / NodePort / LoadBalancer 三层关系（图 4）
- [ ] 独立完成一次 set image → rollout status → rollout undo（图 5）
- [ ] 能说出 ConfigMap 两种消费方式和 Secret 的真实安全边界
