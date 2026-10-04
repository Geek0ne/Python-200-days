# Day 174 图解 — CI/CD（GitHub Actions）

## 1. 一次 push 到底发生了什么

```
        git push
            │
            ▼
   ┌──────────────────┐
   │ GitHub 收到 push  │  → 生成 event payload（JSON）
   └────────┬─────────┘
            │  按 on: 的规则匹配哪个 workflow 该被触发
            ▼
   ┌──────────────────┐
   │ 匹配 .github/     │
   │ workflows/*.yml  │  （一个仓库可以有 N 个 workflow）
   └────────┬─────────┘
            │  为每个匹配的 job 分配 runner
            ▼
   ┌──────────────────────────────────────────────┐
   │  调度器：读 needs 建 DAG，拓扑排序决定顺序     │
   │  无依赖的 job 并行跑（最多 256 个并发）       │
   └────────┬─────────────────────────────────────┘
            │
      ┌─────┴─────┐
      ▼           ▼
  ┌───────┐   ┌───────┐
  │ lint  │   │ test  │   ← 两者无依赖，并行
  └───┬───┘   └───┬───┘
      │           │
      └─────┬─────┘
            ▼
       ┌────────┐
       │package │   ← needs: [test]，且只在 main 分支跑
       └────────┘
```

**关键理解**：GitHub Actions 本身不执行任何东西，它只做**调度**。
真正干活的是 runner（`ubuntu-latest` 是一台临时开的虚拟机，用完即销毁）。
所以「为什么我的流水线卡住」的答案往往是「在等 runner 排队」。

## 2. needs 构成的有向无环图

```
        ┌─────────┐
        │  lint   │  静态检查，最快，失败要尽早暴露
        └────┬────┘
             │ needs
             ▼
   ┌──────────────────┐
   │  test (matrix)   │  一个 job 展开成 N 个并行实例
   │  ├─ py 3.11      │──┐
   │  └─ py 3.12      │──┤ 共享同一份代码，但环境独立
   └────────┬─────────┘  │
            │            ▼
            │      每个实例都是独立的 runner
            ▼
   ┌──────────────────┐
   │     package      │  合并前才执行
   └──────────────────┘
```

`needs` 表达的是**依赖**，不是**顺序**。没有 `needs` 的 job 一定并行。
本课 `code/02-pipeline-builder.py` 用 Kahn 算法把这张图拓扑排序，
并能检出环（GitHub 只会报一句含糊的 `Invalid workflow file`）。

## 3. 一次 step 的生命周期

```
   ┌──────────┐
   │ Set up   │  GitHub 自动生成：装 action、准备环境变量
   └────┬─────┘
        ▼
   ┌─────────────────────────────────────────────┐
   │ Main  actions/checkout@v4                    │  ← uses：调用别人的 action
   │      ├ 下载 action 源码                      │     （本质是一个 Docker/JS 程序）
   │      └ 把仓库代码拉到工作区                    │
   ├─────────────────────────────────────────────┤
   │ Main  pip install -r requirements.txt         │  ← run：执行 shell 命令
   │      └ 在 runner 上真的起了一个 shell         │
   ├─────────────────────────────────────────────┤
   │ Main  pytest -q                              │
   └────┬────────────────────────────────────────┘
        ▼
   ┌──────────┐
   │ Post     │  逆序执行 Post 步骤（即使失败也会跑）
   │ steps    │  典型用途：保存 cache、上传覆盖率
   └────┬─────┘
        ▼
   ┌──────────┐
   │ Complete │  汇总状态：任一 step 非 0 退出码 → job 失败
   │  job     │  后续依赖它的 job 全部 skipped
   └──────────┘
```

**这是最容易踩坑的地方**：Post 步骤即使 Main 失败也会执行。
所以清理逻辑要放 Post，但**不能**放任何"发布成功后才做"的事。

## 4. 表达式求值：if 的三种常见形态

```yaml
# 1. 直接布尔（最常见）
if: github.ref == 'refs/heads/main'

# 2. 隐式成功检查：没有 status() 包裹时，隐含 && success()
if: matrix.py == '3.12'
#   ↑ 完整含义是：success() && matrix.py == '3.12'
#   ↑ 这就是为什么 "always() 很重要" —— 失败后这个 if 永远为 false

# 3. 显式状态函数（需要「即使失败也要跑」时必须显式写）
if: always() && github.event_name == 'push'
if: failure() && steps.build.outcome == 'failure'
```

四把状态钥匙：

| 函数 | 含义 | 典型场景 |
|------|------|----------|
| `success()` | 到目前为止没失败过（默认） | 大多数情况 |
| `always()` | 永远为真 | 无论成败都要做的通知/清理 |
| `failure()` | 有步骤失败过 | 失败时打诊断信息 |
| `cancelled()` | 被取消 | 记录中断原因 |

## 5. matrix 展开规则

```yaml
strategy:
  fail-fast: false          # 一个组合失败，其余继续跑完
  matrix:
    py: ["3.11", "3.12"]
    os: [ubuntu, macos]
    exclude:
      - py: "3.11"
        os: macos
    include:
      - py: "3.12"
        experimental: true
```

展开过程：

```
初始笛卡尔积（2 × 2 = 4）：
  {py:3.11, os:ubuntu}   {py:3.11, os:macos}
  {py:3.12, os:ubuntu}   {py:3.12, os:macos}

应用 exclude（剔除 py3.11+macos）：
  {py:3.11, os:ubuntu}   {py:3.12, os:ubuntu}   {py:3.12, os:macos}

应用 include（能对上 py3.12 的两条就扩展它们）：
  {py:3.11, os:ubuntu}
  {py:3.12, os:ubuntu, experimental:true}
  {py:3.12, os:macos,  experimental:true}

最终 3 个并行 job
```

`fail-fast` 默认是 `true`：一个组合失败，其余立刻取消。
**跑兼容性矩阵时务必设 `false`**，否则老 Python 版本挂了你永远看不到它的错误。

## 6. CI 与 CD 的分界

```
   提交代码
      │
      ├──────────── CI（Continuous Integration）────────────┐
      │  目的：证明这次改动是安全的                        │
      │  内容：lint → 单测 → 覆盖率 → 多版本矩阵           │
      │  失败代价：几分钟，开发者当场就能修                 │
      │  特点：**每个 PR 都跑，要求快**                    │
      └──────────────────────────────────────────────────┘
      │ 全绿
      ▼
   合并到 main
      │
      ├──────────── CD（Continuous Delivery/Deployment）────┐
      │  目的：把已验证的产物送到用户手里                    │
      │  内容：构建镜像 → 推 registry → 灰度 → 健康检查     │
      │  失败代价：影响真实用户，必须能回滚                 │
      │  特点：**只在 main 跑，要求稳**                     │
      └──────────────────────────────────────────────────┘
```

两者共用同一份 workflow，靠 `needs` 串起来。分界点通常是一个 `if`：

```yaml
package:
  needs: [test]
  if: github.ref == 'refs/heads/main'   # ← 这行就是 CI / CD 的分界
```

## 7. 本地跑 GitHub Actions（act）

GitHub 官方 runner 不开源，但社区项目 `act` 用 Docker 复刻了调度逻辑：

```
   你的 workflow.yml
          │
          ▼
   ┌──────────────┐   解析 YAML，展开 matrix，建 needs 图
   │     act      │   ── 与 GitHub 用的是同一套语义 ──
   └──────┬───────┘
          │ 对每个 job
          ▼
   ┌──────────────┐
   │ docker run   │   用 catthehacker/ubuntu:act-latest
   │ (每个 job    │   模拟 ubuntu-latest runner
   │  一个容器)    │
   └──────────────┘
          │
    ✅ 能跑：run 步骤、setup-python、矩阵、build、容器内测试
    ❌ 跑不了：upload-artifact / actions/cache
              （都依赖 ACTIONS_RUNTIME_TOKEN，本地没有 artifact 后端）
```

**局限必须知道**：`act` 跑通不等于 GitHub 上跑通。
第 4 节讲过 Post 步骤、`if: github.ref` 这些，act 都做了近似实现而非完全一致。
它的价值是**秒级反馈**，不是替代真实 runner。
