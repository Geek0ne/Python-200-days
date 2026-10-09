# Day 177 · 练习与检查表

> 目标：亲手跑通「应用暴露 → Prometheus 采集 → PromQL 查询 → Grafana 看板」这条链路，
> 并亲眼看见 `rate()` 的窗口陷阱。
> **前置**：Docker 可用；`python3 -m pip install --target ./.deps prometheus_client`。

---

## 一、动手题（必做）

### 练习 1 — 把指标指出来（5 分钟）

起应用并抓一次指标：

```bash
PYTHONPATH=./.deps python3 code/01-expose-metrics.py --once | head -40
```

- [ ] 找到 `# HELP` / `# TYPE` / 样本行这三类行，各抄一行
- [ ] 指出这个输出里有几**条时间线**（提示：数不同的标签组合）
- [ ] 说明为什么 `app_http_requests_total{...} 2.0` 里是 `2.0` 而不是 `2`

<details><summary>参考答案</summary>

时间线数 = 不同 `(method,path,status)` 组合数（示例里是 3 条）。
`2.0` 是因为 Prometheus 的值统一是 float64，文本格式不区分整数写法。

</details>

### 练习 2 — 四种类型的语义（10 分钟）

```bash
PYTHONPATH=./.deps python3 code/02-metric-types.py --demo
PYTHONPATH=./.deps python3 code/02-metric-types.py --self-test
```

- [ ] `demo_latency_seconds_bucket{le="0.5"}` 和 `le="0.1"` 谁大？为什么？
- [ ] `summary` 为什么没有 `_bucket`？它的分位去哪了？
- [ ] 如果我要监控「当前活跃连接数」，该用哪种类型？

<details><summary>参考答案</summary>

1. `le="0.5"` ≥ `le="0.1"`，因为桶是**累计**的（each bucket includes all smaller）。
2. 0.26.0 起 summary 不再输出分位（`quantiles=` 已被移除），只有 `_sum`/`_count`；
   官方指向 Histogram。
3. Gauge（可增可减）。

</details>

### 练习 3 — 让 Prometheus 来拉（15 分钟）

```bash
python3 code/04-scrape-and-dashboard.py --out /tmp/day177/stack
setsid nohup env PYTHONPATH=./.deps python3 code/01-expose-metrics.py --port 9101 &
docker run -d --name d177-prom --network host \
  -v /tmp/day177/stack/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  prom/prometheus:v3.0.1 --config.file=/etc/prometheus/prometheus.yml
sleep 15
curl -s localhost:9090/api/v1/targets | python3 -c "import json,sys;[print(t['labels']['job'],t['health']) for t in json.load(sys.stdin)['data']['activeTargets']]"
```

- [ ] 两个目标都是 `up` 吗？
- [ ] **不修改应用**，把 `scrape_interval` 从 `5s` 改成 `1s`，改的是哪个文件？
      这验证了 pull 模型的哪条推论？
- [ ] 把应用的 `--port` 改成 9102（配置不改），30 秒后 `up` 变成什么？为什么？

<details><summary>参考答案</summary>

1. `app` 与 `prometheus` 都应为 `up`。
2. 改采集端 `/tmp/day177/stack/prometheus.yml`；推论是「改采集范围不用动应用」。
3. `up{job="app"}=0`（连接被拒）。这就是「拉不到 = 挂了」的直接体现。

</details>

### 练习 4 — 亲手复现 `rate()` 的 0（15 分钟，重点）

```bash
# 造一批流量，然后立刻查（[1m] 窗口内有增量）
for i in $(seq 1 20); do curl -s -o /dev/null localhost:9101/; done
sleep 12
python3 code/03-promql-query.py --query 'sum(rate(app_http_requests_total[1m]))'

# 什么流量都不打，等 90 秒再查同一个表达式
sleep 90
python3 code/03-promql-query.py --query 'sum(rate(app_http_requests_total[1m]))'
```

- [ ] 两次结果分别是多少？为什么第二次是 `0` 而不是「空」？
- [ ] 把第二次的窗口从 `[1m]` 改成 `[5m]`，结果变了吗？为什么？

<details><summary>参考答案</summary>

第一次非零（约 0.3–0.5），第二次为 `0`。因为窗口内所有样本值相等 → 增量为 0。
`rate()` 对「有样本但没变化」返回 0，对「窗口内没有样本」返回空（该时间线不出现）。
改成 `[5m]` 若把早些时候的增量包进来就会非零——窗口决定看到什么。

</details>

### 练习 5 — 看板是 JSON（10 分钟）

```bash
python3 code/04-scrape-and-dashboard.py --out /tmp/day177/stack
python3 -m json.tool /tmp/day177/stack/grafana/dashboards/day177-app.json | head -40
```

- [ ] 找出 4 个面板的 `expr`，说明每个在问什么问题
- [ ] 如果把面板里的 `datasource.uid` 改成不存在的值，图会怎样？
      `--self-test` 为什么专门断言这一点？

<details><summary>参考答案</summary>

`up`（活没活）、`sum by (status)(rate(...))`（QPS 分布）、
`histogram_quantile(0.95, ...)`（P95）、`app_http_inflight`（积压）。
uid 不匹配 → 面板报 "datasource not found"，图全空；这正是 provisioning
最常见的事故，所以自检把它钉成断言。

</details>

---

## 二、判断题（对/错 + 一句话理由）

- [ ] Prometheus 是被采集的应用把指标推上去的。
- [ ] 指标里加一个 `request_id` 标签能提高排障精度，值得加。
- [ ] `app_inflight` 用 Counter 类型也没问题，反正数字都在涨。
- [ ] `histogram_quantile(0.95, app_latency_seconds_bucket)` 不带 `rate()` 也对。
- [ ] `up{job="app"}` 需要在应用里写代码上报。

<details><summary>答案</summary>

1. ✗ Prometheus 主动拉（pull）。
2. ✗ 无限取值 → 高基数，是 Prometheus 头号事故源。
3. ✗ 需要减的时候 Counter 给不了，硬减会让 rate() 变负。
4. ✗ `_bucket` 是累计 counter，必须先 `rate()` 再插值，否则被历史累计污染。
5. ✗ 采集端自动生成。

</details>

---

## 三、排障演练

给三个现象，说出「先查哪条 PromQL / 哪个接口」：

| 现象 | 你的第一步 |
|---|---|
| 看板全空，一个点都没有 | |
| 图有数据但一直是直线（不变） | |
| 只有 P95 那条线是 `NaN` | |

<details><summary>参考答案</summary>

1. 先 `GET /api/v1/targets` 看 `health`；再 `up{job="app"}`。多半是目标没在拉。
2. 换 `[5m]` 试；确认 `scrape_interval` 与流量是否真的有变化（实验 3 同款陷阱）。
3. 检查桶边界：样本全部落在最大的桶之外时插值会得到 `NaN`——把 `le` 最大值调大。

</details>

---

## 四、验收清单（做完打勾）

- [ ] `01 --self-test` 两种 backend 都通过（有/无 `prometheus_client`）
- [ ] `02 --self-test` 通过，能说出四种类型的差别
- [ ] `03 --self-test` 通过（离线桩，不需要 Prometheus）
- [ ] `04 --self-test` + `--dry-run` 通过，生成了 4 个文件
- [ ] Prometheus 里 `up{job="app"}=1`
- [ ] 亲手看到过 `rate()` 返回 `0` 并说得出原因
- [ ] 看板 JSON 里每句话（expr）都能解释
- [ ] 清理完成：`ss -ltnp | grep -E ':9101|:9090|:3000'` 无输出

---

## 五、延伸（选做）

1. 把 `01` 的 `/metrics` 换成 `http.server` 之外的框架（Flask / FastAPI），
   想想为什么框架集成时更容易踩「指标注册两次」的坑。
2. 给 `04` 加一条**告警规则**文件（`rules.yml`），让
   `up{job="app"} == 0` 持续 1 分钟后触发——先不接 Alertmanager，只在 `/api/v1/rules` 里看到状态。
3. 用 `docker stats` 观察 Prometheus 容器在采集 1 个目标与 100 个假目标时的内存差异，
   顺便想清楚：**为什么 Prometheus 官方文档反复强调「别把 user_id 当标签」**。
