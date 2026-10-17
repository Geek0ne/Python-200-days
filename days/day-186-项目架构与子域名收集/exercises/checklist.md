# Day 186 · 练习与验收清单

## ✅ 今日完成清单

- [ ] 能画出资产模型五层：域名 → 子域名 → IP → 端口/服务 → 漏洞
- [ ] 能说出 A / AAAA / CNAME / MX / TXT 各自在测绘中的用途
- [ ] 能解释 `getaddrinfo` 的解析路径，以及为什么缓存会影响性能测试
- [ ] 能实现"域名 + 字典 → 并发解析 → 去重排序"的最小枚举器
- [ ] 能检测并过滤泛解析造成的假阳性
- [ ] 能调用 crt.sh，并清洗换行、通配符、大小写、末尾点、后缀伪装
- [ ] 能用 SQLite 存快照，并算出 added / removed / changed
- [ ] 能解释为什么"记录数"和"资产数"必须分开报告
- [ ] 跑通 4 个脚本的 `--self-test`
- [ ] 完成下方至少 3 道练习题

---

## 🧪 基础练习

### 练习 1：把字典换成文件

用 `--words-file` 加载一份 50 行的字典（可自己写），对 `example.com` 做枚举，
记录：候选数、命中数、耗时、错误数。

**验收**：输出里能区分"解析失败"和"没有这个子域"。

### 练习 2：给泛解析加单元测试

构造一个假 resolver：任意名字都返回 `192.0.2.99`，但 `www.example.test` 返回 `192.0.2.10`。
验证枚举器只保留 `www`，不保留其他随机名字。

**提示**：仿照 `01-dns-enum-basic.py` 的 `self_test()`，用注入的 resolver，不碰网络。

### 练习 3：手工验证 CT 清洗

用 `day186-crt.json`（或自己查一个域名）统计：
- 原始记录数
- `name_value` 拆分后的名字数
- 去重后的名字数
- 含 `*` 的名字数

写一段 10 行以内的脚本输出这四个数字。

### 练习 4：快照差分补一个场景

给 `03-asset-inventory.py` 增加一个测试：
"同一主机 IP 从 `[A, B]` 变成 `[B, A]` 时，不应判定为 changed"。

**验收**：现有实现已经排序，测试应通过；如果失败，说明排序逻辑被改坏了。

---

## 🚀 进阶挑战

### 挑战 1：加限速器

给枚举器加令牌桶：每秒最多 N 次解析（N 可配置）。
要求：
- 不改变原有结果；
- 记录实际 QPS；
- 当 `workers` 很大时，QPS 仍不超过 N。

**提示**：`threading.Lock` + 上次补充时间，或 `queue.Queue` 预填令牌。

### 挑战 2：多来源合并策略

实现 `merge_sources(ct_names, dns_assets)`：
- 名字取并集；
- IP 取并集；
- 记录每个名字的来源（`ct` / `dns` / `both`）。

用实验 1、2 的真实数据验证：应得到 75 条，其中 7 条 `both`、67 条 `ct`、1 条 `dns`。

### 挑战 3：差分告警分级

设计规则并实现：
- `added` 且名字包含 `dev/test/staging` → 高优先级
- `added` 且是根域或 `www` → 中优先级
- `removed` → 低优先级（可能是正常下线）
- `changed` 且 IP 从公网变内网 → 高优先级

输出一个按优先级排序的告警列表。

### 挑战 4：缓存感知的性能测试

修改 `04-benchmark-concurrency.py`，让真实 DNS 实验使用**每次新生成的随机子域**
（必然 NXDOMAIN，但仍是真实查询），比较：
- 冷缓存串行
- 冷缓存 16 线程
- 热缓存串行

**目标**：用数据说明"缓存让串行看起来很快"这个假象。

---

## 🧹 实验验收命令

在 `days/day-186-项目架构与子域名收集/code` 下逐条执行，全部应返回 0：

```bash
python3 01-dns-enum-basic.py --self-test
python3 02-crt-sh-advanced.py --self-test
python3 03-asset-inventory.py --self-test
python3 04-benchmark-concurrency.py --self-test
```

真实网络实验（可选，需联网）：

```bash
python3 01-dns-enum-basic.py --domain python.org --workers 16
python3 02-crt-sh-advanced.py --domain python.org --retries 3
```

## 📌 提交前自检

- [ ] 没有把 `/tmp` 下的实验产物提交进仓库
- [ ] 没有把真实扫描结果（含内网 IP/域名）提交进公开仓库
- [ ] 所有脚本在无网络时也能 `--self-test` 通过
- [ ] README 中的数字与本次实际运行一致
