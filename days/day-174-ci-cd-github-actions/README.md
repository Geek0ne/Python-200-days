# Day 174 — CI/CD（GitHub Actions）

> Phase 11 — 自动化运维与 DevOps · 实战
>
> 本课所有输出均为 **2026-10-05 在本机真机执行捕获**，不是示意。
> 环境：Ubuntu 5.15 / Docker 29.1.3 (overlayfs) / act 0.2.89 / Python 3.12.15 (容器内) / Python 3.11.17 (矩阵另一实例)

---

## 一、概念解释

### 1.1 CI 是什么

**Continuous Integration（持续集成）**：每次有人往仓库推代码，机器立刻自动做一遍「这份代码还是好的吗」的验证。

它要回答的问题只有三个，且必须快：

1. **语法/风格对吗** → lint
2. **行为还对吗** → 单元测试、集成测试
3. **在所有承诺支持的环境里都对吗** → 矩阵

**为什么需要它**：没有 CI 时，「代码能不能跑」只有作者知道。作者本地环境能跑 ≠ 生产能跑。
CI 把「我这边能跑」这个不可验证的信念，换成了一份所有人都能点开看的绿/红记录。

**为什么它必须是自动的**：需要人手动点一下才跑的东西，一周后必然没人点。

### 1.2 CD 是什么

**Continuous Delivery / Deployment**：把通过 CI 验证的产物，自动送到用户能拿到的地方。

- **Delivery**：能发，但需要人点一下「发布」按钮
- **Deployment**：连按钮都不要，合到主干就自动上线

CD 的目标不是「更快上线」，而是**把上线这个动作的风险降到可控**。所以它必须回答：

- 能不能回滚？（这是硬要求，不是加分项）
- 上线后怎么知道是好的？（健康检查）
- 坏了怎么通知？（对应本仓库 Day 171 通知告警）

### 1.3 CI 与 CD 的分界点

两者共用同一个 workflow 文件，靠 `needs` 串成一条链，靠一个 `if` 分界：

```yaml
jobs:
  lint:    ...
  test:    needs: [lint]
  package: needs: [test]
           if: github.ref == 'refs/heads/main'   # ← 这行就是分界
```

| | CI | CD |
|---|---|---|
| 触发 | 每个 PR、每次 push | 只在主干分支 |
| 目标 | 证明改动是安全的 | 把产物送到用户手里 |
| 速度要求 | **快**（开发者还在等着看结果） | 稳 |
| 失败代价 | 几分钟，当场能修 | 影响真实用户 |

### 1.4 Workflow 是什么

一个 workflow = 放在 `.github/workflows/*.yml` 下的一个 YAML 文件，描述「什么事件触发、跑哪些 job、每个 job 做哪几步」。

同一个仓库可以有任意多个 workflow 文件，各管一件事（CI、发布、代码质量……）。
GitHub 会**按文件名**排序去触发，所以 `00-lint.yml` 会排在 `99-deploy.yml` 前面执行。

**GitHub Actions 本身不执行任何东西。** 它只做一件事：把 event 匹配到 workflow，
再把 job 分配给某个 runner。真正跑代码的是 runner —— `ubuntu-latest` 是一台临时开的
虚拟机（4 核 16G），用完即销毁，代码留在上面也是转瞬即逝。

这个理解很重要：因为 runner 是**无状态的**，所以：
- 想跨 job 传文件？必须用 artifact（而 artifact 需要 GitHub 的后端，`act` 跑不了）
- 想跨 job 复用依赖？必须用 cache
- 想在 runner 上留下手工排查的现场？做不到，得靠日志

---

## 二、原理深入

### 2.1 一次 push 的完整生命周期

```
git push
   │
   ▼
GitHub 生成 event payload（JSON，含 ref / commit / 发送者…）
   │
   ▼
按每个 workflow 的 on: 规则匹配 → 决定哪些 workflow 被触发
   │
   ▼
对被触发的 workflow：读 jobs 的 needs，构 DAG，拓扑排序
   │
   ▼
入度为 0 的 job 立刻分配 runner（并行，上限 256）
   │  ┌─ lint  ─┐
   │  └─ test ─┘   同层并行
   ▼
某个 job 结束 → 检查它的下游是否入度归零 → 是则启动
   │
   ▼
全部完成 → 汇总状态 → 通知（邮件 / GitHub 通知 / Webhook）
```

**推论**：流水线总时长 ≈ 最长路径之和，不是所有 job 之和。
所以依赖少串行是慢的主因，而「加缓存」是缩短单步时长的手段——两者要分清。

### 2.2 step 的五阶段生命周期

```
Set up job          ← GitHub 自动生成，下载并准备 action
      ▼
Main: step 1        ← 你写的 steps 依次执行
Main: step 2
      ▼
Post: 逆序执行     ← ⚠️ 即使 Main 失败也照跑
      ▼
Complete job        ← 汇总：任一 step 非 0 退出码 → job 失败
```

**Post 步骤无条件执行**是新手最容易忽略的点。它的正确用途是清理
（停掉后台进程、关掉数据库连接）；错误用法是「成功后才做的事」——那样在失败路径上会误触发。

### 2.3 表达式的隐含 success()

`if` 条件如果不显式调用状态函数，会**隐含前置 `success()`**：

```yaml
if: matrix.py == '3.12'
# 实际含义：
if: success() && matrix.py == '3.12'
```

这解释了一个常见困惑：「为什么我写的 `if` 在失败后从来不执行？」
因为前面失败了，`success()` 就是 false，短路了。

要「无论成败都执行」必须显式写：

```yaml
if: always() && github.event_name == 'push'
```

四把状态钥匙：

| 函数 | 语义 | 典型用途 |
|------|------|----------|
| `success()` | 至今无失败（默认隐含） | 大多数条件 |
| `always()` | 恒为真 | 无论成败的通知/清理 |
| `failure()` | 有步骤失败过 | 失败时导出诊断日志 |
| `cancelled()` | 被取消 | 记录中断原因 |

### 2.4 矩阵展开的完整语义

```yaml
strategy:
  fail-fast: false        # 关键：跑兼容性矩阵必须设 false
  matrix:
    py: ["3.11", "3.12"]
    os: [ubuntu, macos]
    exclude:
      - {py: "3.11", os: macos}
    include:
      - {py: "3.12", experimental: true}
```

展开顺序是**先笛卡尔积，再 exclude，最后 include**：

```
初始 2×2 = 4 组
  {3.11,ubuntu}  {3.11,macos}  {3.12,ubuntu}  {3.12,macos}

exclude 剔除 {3.11, macos} → 3 组
  {3.11,ubuntu}  {3.12,ubuntu}  {3.12,macos}

include 的 {py:3.12} 能对上后两条 → 就地扩展它们 → 3 组
  {3.11,ubuntu}
  {3.12,ubuntu, experimental:true}
  {3.12,macos,  experimental:true}
```

`include` 的匹配规则是：**对 include 里出现的每个 key，若组合中已有该 key，则值必须相等**。
如果 include 的所有 key 都对不上任何已有组合，它会作为**新组合追加**。

`fail-fast` 默认 `true`：一组失败立刻取消其余。默认行为在测兼容性矩阵时是错的——
因为最先挂的往往是老版本，你反而看不到老版本的具体错误。

### 2.5 为什么 cache / artifact 需要 GitHub 后端

`actions/cache` 和 `actions/upload-artifact` 都需要一个环境变量
`ACTIONS_RUNTIME_TOKEN` 来向 GitHub 的存储服务换取上传/下载凭证。

在真实 runner 上，这个 token 由 GitHub 在 job 启动时注入。
在 `act` 跑的本机容器里，**没有任何东西注入它**——因为根本没有那个后端服务。

这就是为什么本课实验 4 的 `upload-artifact` 步骤会报
`Unable to get the ACTIONS_RUNTIME_TOKEN env variable`：
不是配置错了，是本地根本没有这个东西可以取。

理解了这一点，就不会去 debug 一个根本不可能在本地修好的问题。

---

## 三、API 速查

### 3.1 workflow 顶层键

| 键 | 必填 | 说明 |
|----|------|------|
| `name` | 否 | UI 上显示的名字 |
| `on` | **是** | 触发条件 |
| `env` | 否 | 全局环境变量 |
| `jobs` | **是** | 至少一个 job |
| `concurrency` | 否 | 并发控制 |
| `permissions` | 否 | 令牌权限 |
| `defaults.run` | 否 | `run` 的默认 shell / working-directory |

### 3.2 常见 `on:` 写法

```yaml
on: [push, pull_request]                     # 数组
on: {push: {branches: [main]}}               # 限定分支
on:
  push:
    branches: [main]
    paths-ignore: ['docs/**', '*.md']        # 改文档不触发
  pull_request:
    types: [opened, synchronize]             # 只关心哪几类事件
  schedule:
    - cron: "0 3 * * *"                      # 每天 03:00 UTC
  workflow_dispatch:                         # 允许手动点按钮触发
  workflow_call:                             # 被别的 workflow 复用
```

### 3.3 常用内置环境变量

| 变量 | 含义 | 典型用法 |
|------|------|----------|
| `GITHUB_SHA` | 触发 commit 的完整 SHA | 打 tag / docker tag |
| `GITHUB_REF` | 完整 ref，如 `refs/heads/main` | 判断分支 |
| `GITHUB_REF_NAME` | 短名，如 `main` | 生成 tag 名 |
| `GITHUB_EVENT_NAME` | 事件名，如 `push` | 判断触发源 |
| `GITHUB_REPOSITORY` | `owner/repo` | 生成镜像全名 |
| `GITHUB_RUN_ID` | 本次 run 的唯一 ID | 关联日志/trace |
| `GITHUB_TOKEN` | 内置令牌 | 默认只读，权限靠 `permissions` 提权 |

### 3.4 常用 context 表达式

| 表达式 | 含义 |
|--------|------|
| `github.ref == 'refs/heads/main'` | 在主干上 |
| `github.event_name == 'push'` | 由 push 触发 |
| `matrix.py` | 矩阵里的 py 值 |
| `steps.<id>.outputs.<name>` | 某 step 通过 `$GITHUB_OUTPUT` 传出的值 |
| `hashFiles('requirements.txt')` | 文件内容哈希，用作 cache key |
| `secrets.DOCKER_TOKEN` | 仓库密钥 |
| `env.FOO` | 环境变量 |

### 3.5 常用官方 action

| action | 用途 | 备注 |
|--------|------|------|
| `actions/checkout@v4` | 拉代码 | 不用它，工作区是空的 |
| `actions/setup-python@v5` | 装指定 Python | 装依赖前必须有 |
| `actions/cache@v4` | 缓存目录 | key 用 hashFiles |
| `actions/upload-artifact@v4` | 上传产物 | job 之间传文件的唯一方式 |
| `docker/build-push-action@v6` | 构建并推镜像 | 配 cache-from/to 加速 |

> 版本号用 `@v4` 这种 major tag。严格安全要求可锁到 commit SHA（`@v4.2.1` 或
> `@8f4b7f8...`），代价是升级要手动改——对生产部署的流水线值得。

---

## 四、图解

完整图解见 [`diagrams/README.md`](diagrams/README.md)，含 7 张图：

1. 一次 push 的完整调度链路
2. needs 构成的有向无环图
3. step 的五阶段生命周期（Set up / Main / Post / Complete）
4. `if` 表达式的隐含 `success()` 与四把状态钥匙
5. matrix 展开规则（笛卡尔积 → exclude → include）
6. CI 与 CD 的分界
7. `act` 的工作方式与能力边界

---

## 五、实战代码案例

| 文件 | 定位 | 用法 |
|------|------|------|
| `code/01-workflow-lint.py` | **基础**：用 Python 校验 workflow YAML | `python3 code/01-workflow-lint.py workflows/ci.yml` |
| `code/02-pipeline-builder.py` | **进阶**：needs 拓扑排序 + 环检测 + 矩阵展开 + 生成 | `python3 code/02-pipeline-builder.py topo workflows/ci.yml` |
| `code/03-cd-deploy-pipeline.py` | **实战**：CD 全流程演练（门禁→构建→发布→回滚） | `python3 code/03-cd-deploy-pipeline.py run` |

三个脚本都支持 `--self-test`，离线可跑：

```
$ python3 code/01-workflow-lint.py --self-test
✅ self-test 通过：好文件 0 error，坏文件捕获 4 个 error

$ python3 code/02-pipeline-builder.py --self-test
✅ self-test 通过：环检测/拓扑/矩阵/生成 6 组断言全过

$ python3 code/03-cd-deploy-pipeline.py --self-test
✅ self-test 通过：版本/发布/回滚/门禁 6 组断言全过
```

### 实战脚本的实测输出

```
$ rm -rf /tmp/cd-pipeline
$ python3 code/03-cd-deploy-pipeline.py run
▶ CD 部署流水线
  ✅ lint   语法检查通过  (0.07s)
  ✅ test   coverage=100.0% (阈值 80.0%)  (0.00s)
  ✅ build  产物 dist/app-v1.0.1.tar.gz  (0.00s)
  ✅ deploy ✅ registry.local/app:v1.0.1 上线  (0.00s)
────────────────────────────────────────────────────────────
结果: 发布成功  总耗时 0.068s

$ python3 code/03-cd-deploy-pipeline.py run      # 第二次
  ✅ deploy ✅ registry.local/app:v1.0.2 上线  (0.00s)

$ python3 code/03-cd-deploy-pipeline.py run --flaky   # 故意让新版不健康
  ❌ deploy ❌ registry.local/app:v1.0.3 健康检查失败，已回滚到 registry.local/app:v1.0.2
────────────────────────────────────────────────────────────
结果: 发布失败并回滚  总耗时 0.039s

$ cat /tmp/cd-pipeline/releases.json | python3 -c "import json,sys;print([r['version'] for r in json.load(sys.stdin)])"
['v1.0.1', 'v1.0.2']
```

注意最后一行：**`v1.0.3` 不在里面**。回滚的正确语义是「新版本从未进入可用列表」，
而不是「上了再撤」——后者会有一段用户请求打到坏实例的时间窗。

---

## 六、实战实验手册

### 实验 1：用 act 在本机跑通完整 pipeline

**目的**：验证一个含 lint / 测试矩阵 / 打包的 pipeline 能真的从 YAML 跑出绿色结果，
并搞清 GitHub Actions 的调度与 step 语义。

**环境**：
- act 0.2.89（`nektos/act`）
- Docker 29.1.3，overlayfs 存储驱动
- runner 镜像 `catthehacker/ubuntu:act-latest`（约 2GB）
- 容器内 Python 3.12.15 / 3.11.17

**准备**：

```bash
# 1) 安装 act
curl -sL https://github.com/nektos/act/releases/download/v0.2.89/act_Linux_x86_64.tar.gz \
  | tar xz act && sudo mv act /usr/local/bin/

# 2) 告诉 act 用哪个镜像当 ubuntu-latest
#    （不配的话 act 会弹交互式菜单选择镜像大小，非交互环境下会直接 EOF 退出）
mkdir -p /root/.config/act
echo "-P medium=catthehacker/ubuntu:act-latest" > /root/.config/act/actrc

# 3) 拉 runner 镜像
docker pull catthehacker/ubuntu:act-latest
```

**执行**（在 `/tmp/gha-demo`，一个最小 Python 项目）：

```bash
act -P ubuntu-latest=catthehacker/ubuntu:act-latest push
```

**预期结果**：4 个 job（`lint` / `test-1` / `test-2` / `package`）全部 `Job succeeded`。

**实际结果**（经过 6 次失败修正后，最终成功的一次；完整日志见下）：

```
[CI Pipeline/lint]   🏁  Job succeeded
[CI Pipeline/test-1] 🏁  Job succeeded
[CI Pipeline/test-2] 🏁  Job succeeded
[CI Pipeline/package] 🏁  Job succeeded
exit=0
```

最终 pipeline 的关键输出：

```
[CI Pipeline/lint]   | All checks passed!
[CI Pipeline/test-1] | ...                            [100%]
[CI Pipeline/test-1] | Name               Stmts   Miss  Cover
[CI Pipeline/test-1] | src/__init__.py        0      0   100%
[CI Pipeline/test-1] | src/calc.py            6      0   100%
[CI Pipeline/test-1] | src/test_calc.py       9      0   100%
[CI Pipeline/test-1] | TOTAL                 15      0   100%
[CI Pipeline/test-1] | 3 passed in 0.03s
[CI Pipeline/test-2] | 3 passed in 0.04s
[CI Pipeline/package] | Successfully built gha_demo-0.1.0-py3-none-any.whl
[CI Pipeline/package] | -rw-r--r-- 1 root root 1774 Oct  4 22:09 gha_demo-0.1.0-py3-none-any.whl
[CI Pipeline/package] | Processing ./dist/gha_demo-0.1.0-py3-none-any.whl
[CI Pipeline/package] | wheel ok: 5
```

**实测的各 step 耗时**（第二次运行，工具链已缓存）：

| step | 耗时 |
|------|------|
| `actions/checkout@v4` | 26–32 ms |
| `actions/setup-python@v5` | 632–685 ms（已缓存 toolcache；首次 14.4 s） |
| `pip install -r requirements.txt` | 835–886 ms |
| `pytest -q --cov=src` | 443–480 ms |
| `python -m build --wheel` | 4.15 s |
| wheel 验证（装 wheel + import） | 644 ms |

**结论**：验证了——(a) `needs` 串起的三级 DAG 真实生效，
执行顺序 `lint → test(×2 并行) → package` 与拓扑序一致；
(b) matrix 确实展开成 2 个独立 job，各自装到不同 Python 版本；
(c) `actions/setup-python` 首次约 14.4 s，命中 toolcache 后降到 0.6 s 左右。

**清理**：

```bash
# act 的 job 容器在结束时自动删除，残留的是 act 的 action 缓存
docker ps -a --filter "name=act-" | awk '{print $1}' | xargs -r docker rm -f
rm -rf /root/.cache/act
rm -rf /tmp/gha-demo
# 镜像按需保留（复用可省下 2GB 下载）；确定不用了再删：
# docker rmi catthehacker/ubuntu:act-latest
```

---

### 实验 2：实测 pip 缓存的真实收益

**目的**：量化「加 `actions/cache` 缓存 `~/.cache/pip`」到底能省多少秒。

**环境**：同实验 1；依赖集 `bench-requirements.txt`（8 个包，含 sqlalchemy / pydantic 等带传递依赖的），
冷/热各跑一次，取单次值。

**准备**：

```bash
# 用同一个 workflow（workflows/cache-bench.yml）跑两次安装，
# 关键是两次必须装进【互相隔离的 venv】，否则第二次全是 "already satisfied"，
# 下载量为 0，测出来的数毫无意义（见下方翻车实验二）
```

**执行**：

```bash
act -P ubuntu-latest=catthehacker/ubuntu:act-latest workflow_dispatch
```

**预期结果**：热安装应明显快于冷安装。

**实际结果**（2026-10-05，本机）：

```
[Cache Bench/bench]   | COLD_secs=11.66
[Cache Bench/bench]   | WARM_secs=7.45
[Cache Bench/bench]   | cache_size=14M
```

**结论**：冷装 11.66 s → 热装 7.45 s，**省 4.21 s，约 36%**；缓存体积 14 MB。

**这个数字怎么用**：省下的绝对时间不大（4 秒），所以**不要为了 4 秒去引入 cache 的复杂度**。
但如果依赖里有大型二进制轮子（torch、opencv、playwright），下载量能从几十 MB 涨到 GB，
同一个比例换算下来就是几十秒——那才值得加 cache。
判断标准是**依赖体积**，不是「包的数量」。

**清理**：

```bash
rm -rf /tmp/gha-demo   # 缓存目录在容器内，随容器销毁，无需额外清理
```

---

### 实验 3：CD 流水线的门禁与回滚

**目的**：验证「门禁失败能阻断部署」和「新版本不健康能自动回滚」这两件事真的成立。

**环境**：纯 Python 标准库，无外部依赖，Linux 本机。

**准备**：无。

**执行**：

```bash
rm -rf /tmp/cd-pipeline
python3 code/03-cd-deploy-pipeline.py run
python3 code/03-cd-deploy-pipeline.py run
python3 code/03-cd-deploy-pipeline.py run --flaky
cat /tmp/cd-pipeline/releases.json
```

**预期结果**：前两次成功且版本递增；第三次失败并回滚，`releases.json` 不含 `v1.0.3`。

**实际结果**：

```
第一次:
  ✅ deploy ✅ registry.local/app:v1.0.1 上线
  结果: 发布成功  总耗时 0.068s

第二次:
  ✅ deploy ✅ registry.local/app:v1.0.2 上线
  结果: 发布成功  总耗时 0.065s

第三次（--flaky）:
  ❌ deploy ❌ registry.local/app:v1.0.3 健康检查失败，已回滚到 registry.local/app:v1.0.2
  结果: 发布失败并回滚  总耗时 0.039s

releases.json:
[{"version": "v1.0.1", "image": "registry.local/app:v1.0.1", "healthy": true},
 {"version": "v1.0.2", "image": "registry.local/app:v1.0.2", "healthy": true}]
```

**结论**：`v1.0.3` 确实没有进入记录 —— 回滚发生在「新版本被记为可用」**之前**，
不是先上线再撤。这正是自动化部署该有的语义。

**清理**：

```bash
rm -rf /tmp/cd-pipeline
```

---

## 七、翻车实验（最有价值的部分）

### 翻车一：`upload-artifact` 在 act 里永远跑不通

**现象**：

```
[CI Pipeline/package]   ❌  Failure - Main actions/upload-artifact@v4 [592.195905ms]
[CI Pipeline/package]   ❗  ::error::Unable to get the ACTIONS_RUNTIME_TOKEN env variable
[CI Pipeline/package]   exitcode '1': failure
```

**假设**：版本不对 / 路径写错 / `path` 没匹配到文件。

**验证手段**：翻日志发现前面三行都是绿的——
`With the provided path, there will be 1 file uploaded` / `Artifact name is valid!` /
`Root directory input is valid!`——说明配置和文件都没问题，是凭证环节挂了。

**真实根因**：`upload-artifact` 需要 `ACTIONS_RUNTIME_TOKEN` 向 GitHub 的存储后端换取上传凭证。
本机跑 act 时没有任何东西注入这个变量，因为**那个后端根本不存在**。
同理 `actions/cache@v4` 在 act 里也跑不通（我为此卡了 6 分钟，见下）。

**修复**：不是「修好它」，而是承认边界——加一道本地可跳过的条件：

```yaml
- name: Verify wheel          # 真正想验证的东西：wheel 能装能用
  run: |
    pip install dist/*.whl
    python -c "from src.calc import add; print('wheel ok:', add(2, 3))"
- uses: actions/upload-artifact@v4
  if: env.ACTIONS_RUNTIME_TOKEN != ''   # act 本地跳过，真实 runner 上才上传
  with: {name: dist, path: dist/}
```

**复测结果**：4 个 job 全绿，且 `wheel ok: 5` 证明产物确实可用。

**教训**：`act` 跑绿 ≠ GitHub 上跑绿，反之亦然。act 的价值是秒级反馈，
它的边界（artifact / cache / 真实 GitHub API 上下文）必须心里有数，
否则会把「本地环境缺后端」误当成「我的配置写错了」，白查半小时。

---

### 翻车二：缓存基准第一次测出了假数据

**现象**：第一次跑冷/热对照，得到

```
COLD_secs=0.81
WARM_secs=0.47
cache_size=80K
```

比第二次的 11.66 / 7.45 快了十几倍，明显不对。

**假设**：容器里已有缓存（runner 镜像预置了 toolcache）。

**验证手段**：看 `cache_size=80K`。14 MB 的依赖只存下 80 KB，说明**几乎没有下载发生**。
再看 pip 输出，满屏 `Requirement already satisfied: ... in site-packages`。

**真实根因**：两个 job 写在**同一个 workflow**里，act 复用了同一个 site-packages 目录。
第一次跑完，依赖已经装进 site-packages；第二次执行 `pip install` 只是确认了版本一致，
下载量为 0。所谓「热装 0.47 秒」测的是 pip 的版本检查速度，**跟缓存一点关系都没有**。

**修复**：让两次安装互相隔离——各建一个空 venv，只共享 `PIP_CACHE_DIR`：

```python
subprocess.run(["python3", "-m", "venv", "/tmp/venv1"])
subprocess.run(["python3", "-m", "venv", "/tmp/venv2"])
# venv1 用空缓存装（冷），venv2 用 venv1 填好的缓存装（热）
```

**复测结果**：

```
COLD_secs=11.66
WARM_secs=7.45
cache_size=14M
```

14 MB 的缓存体积对上了 8 个包（含传递依赖）的合理量级。

**教训**：**基准测试的第一要务是确认被测变量真的变了**。
跑出「好得离谱」的数时，先怀疑自己的实验设计，而不是庆祝。
这个坑在 Day 173 测 Compose 启动时延时也踩过一次（当时靠对照 workflow 组的
差异才确认测的是依赖等待而非镜像拉取）。

---

### 翻车三（附带）：`bc` 在容器里不存在

用 `date +%s.%N` 前后取差来计时是最直白的写法，但 act 的 runner 镜像里**没有 `bc`**：

```
[Cache Bench/bench]   | cold_secs=
[Cache Bench/bench]   | warm_secs=
```

`echo "$E - $S" | bc` 失败了，`$( )` 得到空串，但 **step 依然返回 0**——
所以流水线是绿的，数字却是空的。这比直接报错更危险。

**修复**：既然容器里就有 Python，用 `time.perf_counter()`：

```python
import time
t0 = time.perf_counter()
subprocess.run([...], check=True)
print(f"{label}_secs={time.perf_counter() - t0:.2f}")
```

**教训**：在 CI 里，任何"计算类"步骤都要**校验输出非空**。静默的空结果比崩溃难查得多。

---

## 八、思考题

1. **`actions/checkout` 为什么是几乎所有 workflow 的第一步？**
   提示：runner 是全新虚拟机，工作区是空的。没有 checkout，`run: pytest` 会报
   "no tests ran" 或 "file not found"——而且**不报错**，只是没有测试通过，
   是很隐蔽的一种失败（pytest 找不到文件时退出码非 0，但如果配置成
   `pytest || true` 就会假绿）。

2. **`needs` 和 `dependencies` 式的「顺序」有什么本质区别？**
   提示：没有 `needs` 的 job 一定并行。想强制顺序，除了 `needs` 还能用什么？
   （答案之一是 `concurrency` + 同一个 group，或者把两个 job 合并成一个。
   合并的代价是并行度丧失，权衡点在哪？）

3. **矩阵测试时 `fail-fast: false` 是必须的，还是可选的？**
   想清楚：默认的 `true` 在什么情况下更省资源？什么情况下更危险？
   一个 20 个组合的矩阵，某几个老版本装不上依赖，你希望看到什么信息？

4. **如果 `test` job 失败了，`package` job 在日志里显示什么？**
   是「没有日志」还是「skipped」？这两种在排查时体验有何不同？
   （答案是 `skipped`，会明确标注。这引出一个设计问题：门禁失败时，
   你希望 `package` 静默跳过，还是跳过并发一条「为什么不发布」的说明？）

5. **Day 174 的实验全部在 Linux 容器上跑。如果要做 macOS/Windows 矩阵，**
   **哪些部分能复用、哪些必须重来？** 提示：想想路径分隔符、shell 差异、
   以及 `runs-on: macos-latest` 的计费（macOS runner 的倍率是 Linux 的多少倍？）。

6. **CD 里的「健康检查」应该由谁做？**
   提示：容器自报的 `/health` 说"我活着"和你从外部探测 `/health` 说"用户能访问到"
   是两件事。蓝绿部署时，新旧实例同时在线，你探测哪个？
   什么时候才把旧实例下线？

---

## 九、参考产出

本次真机验证最终通过的 workflow 已随本课保存：

- `workflows/ci.yml` —— 三级 pipeline（lint → test 矩阵 → package），含 5 条踩坑注释
- `workflows/cache-bench.yml` —— 冷/热缓存对照
- `bench-requirements.txt` —— 基准用的依赖集

`workflows/ci.yml` 末尾附了本课所有踩坑的注释，可以直接拷进自己的项目。
