# Day 181 — 发布管理

> **阶段**：Phase 11 — 自动化运维与 DevOps（Day 166–185）
> **子主题**：语义化版本（SemVer）· Changelog 规范（Keep a Changelog / Conventional Commits）· PyPI 发布流程（build / twine / API token）· **实战**：自动化发布流水线（打 tag → 构建 → 校验 → 发布）

---

## 概念解释

### 发布管理在管什么

写代码不是终点，**把代码交到别人手里**才是。发布管理就是这段路上的规矩，
它由三层相互咬合的约定组成，每一层解决的问题不同：

| 层 | 规范 | 回答的问题 | 对谁负责 |
|---|---|---|---|
| 版本号 | **SemVer 2.0.0** | 「这次升级会不会弄坏我的代码？」 | 使用者（依赖方） |
| 变更记录 | **Keep a Changelog** | 「两个版本之间到底改了什么？」 | 使用者（包括未来的你） |
| 提交信息 | **Conventional Commits** | 「这条提交属于哪一类改动？」 | 工具链（自动生成上两层） |

关键在于**它们是可推导的**：提交规范了 → CHANGELOG 能自动生成 → 改动类型已知
→ 下一个版本号能算出来 → 整条发布链路可以无人值守。

```
Conventional Commits ──▶ Keep a Changelog ──▶ SemVer ──▶ tag ──▶ 构建 ──▶ 发布
      （人写）              （机器生成）        （机器算）        （机器做）
```

这条链上**唯一必须人写的东西是提交信息**。这也是本仓库 CONTRIBUTING.md
要求 Conventional Commits 的真正原因：不是为了「好看」，是为了下游能自动化。

### 语义化版本 SemVer 2.0.0

格式只有这四种成分，顺序固定：

```
MAJOR . MINOR . PATCH  -  PRERELEASE   +  BUILD
  1   .   2   .   3    -    rc.1        +  sha.5114f85
```

**三条递增规则**（这是 SemVer 的全部实用性所在）：

| 改动性质 | 递增 | 例子 |
|---|---|---|
| 破坏性变更（不兼容） | MAJOR | 1.2.3 → 2.0.0 |
| 新增功能（向后兼容） | MINOR | 1.2.3 → 1.3.0 |
| 修 bug（向后兼容） | PATCH | 1.2.3 → 1.2.4 |

**两条容易被忽略的细节**：

1. **构建元数据不参与比较**。1.0.0+build.1 和 1.0.0+build.999 的优先级**完全相等**
   （规范第 10 条）。它只是给人看的构建信息，机器比版本时直接忽略。
2. **预发布版比对应正式版低**。1.0.0-rc.1 < 1.0.0。预发布之间比大小靠一套
   很短的规则：**先逐段比，数字段按数值比，数字段 < 字母段，段数少的 < 段数多的**。

规范原文给的这串例子就是全部规则的最好证明（本日脚本逐对断言过）：

```
1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta
            < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0
```

注意 `beta.11` 排在 `beta.2` 之后：**数字段按数值比，不是字典序**。
把 `11` 当成字符串比会得出 `11` < `2` 的错误结论，把「11」判成更早的版本。

**关于 0.x.y**：规范里说「初始开发阶段，任何东西都可能随时改变」。
所以 0.x 的 MINOR 递增就可以带破坏性变更，社区惯例是
`BREAKING → 0.(y+1).0`、其余 → `0.y.(z+1)`。本日脚本用
`--zero-major` 实现了这条惯例（因为它是**惯例**，不是规范强制）。

**常见误解速查**：

| 写法 | 判断 |
|---|---|
| `v1.2.3` | ❌ 不是 SemVer。`v` 是 git tag 的习惯，不属于版本号本身 |
| `1.2` | ❌ 必须三段 |
| `01.2.3` | ❌ 数字段不允许前导零 |
| `1.2.3-01` | ❌ 预发布的数字标识符同样不允许前导零 |
| `1.2.3+build.5` | ✅ 合法；但比较时忽略 `+build.5` |
| `1.2.3-alpha.beta` | ✅ 合法：字母段可以连着字母段 |

### Changelog 规范：Keep a Changelog

它规定了一份面向**人**的变更记录长什么样，核心是六类 + 一个未发布区：

```
# Changelog

## [Unreleased]        ← 已合并但还没发版的改动住这里

## [1.3.0] - 2026-10-16
### Added              ← 新增功能
### Changed            ← 行为变化
### Deprecated         ← 还能用，但下个版本要删
### Removed            ← 这个版本删掉了
### Fixed              ← 修 bug
### Security           ← 安全修复
```

**为什么不直接用 `git log` 当 CHANGELOG？** 因为两者面向的读者不同：

- `git log` 的记录单位是**提交**（实现过程），一条 feat 可能拆成 6 个提交；
- CHANGELOG 的记录单位是**变动**（对外影响），使用者只关心「我升级了会不会有事」。

所以 CHANGELOG 是 `git log` 的**投影与摘要**，不是复制。
`chore: 升级 CI 镜像` 对使用者毫无意义，不该出现在 CHANGELOG 里——
本日脚本默认就把它过滤掉（`docs`/`chore`/`ci` 一类内部改动不进 CHANGELOG）。

### Conventional Commits

格式一句话就能说完：

```
<type>(<scope>)!: <description>
```

- `type`：`feat` / `fix` / `perf` / `refactor` / `docs` / `test` / `chore` / `ci` / `build` / `style` / `revert`
- `(scope)`：影响范围，可选，比如 `(api)`
- `!`：**这个记号表示破坏性变更**，等价于正文里写 `BREAKING CHANGE:`
- 正文里以 `BREAKING CHANGE:` 开头的段落，是破坏性变更的正式声明位置

映射到 Keep a Changelog 的六类（本日脚本内置的映射表）：

| Conventional type | Keep a Changelog 分类 |
|---|---|
| `feat` | Added |
| `fix` | Fixed |
| `perf` / `refactor` / 任何 `!` | Changed |
| `revert` | Removed |
| `docs` / `chore` / `ci` / `build` / `style` / `test` | 不进 CHANGELOG（内部改动） |

### PyPI 发布：两个产物、两个工具、一个 token

**产物有两种，用途不同**：

| | sdist（`.tar.gz`） | wheel（`.whl`） |
|---|---|---|
| 内容 | 源码 + 构建配置 | 已构建好的、可直接解压安装的归档 |
| 安装时 | 需要现场构建（要编译器/依赖） | 直接解压安装 |
| 平台 | 与平台无关 | 可能带平台标签（`cp312-manylinux…`） |
| 谁需要 | 唯一能完整还原源码的形态 | 绝大多数用户（快、不需要编译器） |
| 关系 | wheel 从同一份构建配置产出 | 不是替代，是它的**产物** |

**两个工具，职责不同**：

- `build` —— **PEP 517 前端**。它本身不做构建，只负责「建一个隔离环境 →
  装 build-system.requires 里的后端 → 调后端的 build_wheel/build_sdist」。
- `twine` —— **上传客户端 + 校验器**。`twine check` 检查元数据与 README 渲染，
  `twine upload` 按 PyPI 的 legacy 上传协议发 multipart。**PyPI 已拒绝
  `setup.py upload`**，twine 是官方指定的路径。

**一个 token**：PyPI 的 API token 是唯一凭据，用法有个固定套路——
**用户名固定填 `__token__`，密码才是 token 本体**（`pypi-` 开头）。
写反了或者用真用户名，会直接 403。本日脚本的本地桩专门断言了这一点。

---

## 原理深入

### wheel 文件名就是元数据（PEP 427 / PEP 503 / PEP 625）

`demo_release_pkg-1.2.3-py3-none-any.whl` 这段文件名，每个字段都有含义：

```
demo_release_pkg - 1.2.3 - py3 - none - any .whl
   ▲               ▲       ▲     ▲     ▲
   │               │       │     │     └─ 平台：any = 纯 Python，哪都能装
   │               │       │     └─────── ABI：none = 不依赖某个 C ABI
   │               │       └───────────── 支持的 Python：py3 = Python 3
   │               └───────────────────── 版本（就在文件名里！）
   └───────────────────────────────────── 发行名（PEP 503 归一化后）
```

**为什么文件名这么重要**：PyPI 的索引**只认文件名**。上传时索引从 multipart 的
`metadata` 字段读 Name/Version，但索引页展示、依赖解析、
「这个文件名占不占用」都依赖文件名。文件名里的版本写错，
在索引上就是一个**看起来正常、实际错版**的产物。

另外两条容易踩的规范：

- **PEP 503 归一化**：发行名比较时必须「小写 + 把连续的 `-` `_` `.` 都压成单个 `-`」。
  所以 sdist 文件名里的 `demo_release_pkg` 和元数据里的 `demo-release-pkg`
  **是同一个包**。不做归一化，校验器就会把合法产物误判成错（本日真踩过，见翻车复盘 2）。
- **PEP 625**：sdist 文件名必须是 `{归一化名}-{版本}.tar.gz`，
  老式的 `{name}-{version}.zip` 已经不被接受。

### 一次发布的完整链路，以及它的不可逆性

```
 ① 打 tag          git tag v1.2.3 && git push --tags
        │
 ② 校验一致性      tag 版本 == pyproject 里的 version ？（对不上就该停）
        │
 ③ 构建            python -m build  →  dist/*.whl + dist/*.tar.gz
        │
 ④ 校验产物        文件名 / 元数据 / wheel 与 sdist 版本一致 / twine check
        │
 ⑤ 上传            twine upload（或任何按 legacy 协议实现的客户端）
        │
 ⑥ 索引生效        PyPI 生成页面、JSON API、可 pip install
```

**第 ⑤ 步是不可逆的**：PyPI 不允许覆盖同名文件。版本号 1.2.3 一旦上传，
你**不能**再传一个「修好的 1.2.3」——只能发 1.2.4。
（可以 yank 掉旧版本，但文件仍然占着位置、仍然能被已锁定版本的用户安装。）

这条性质决定了整条链路的形状：**所有校验必须发生在第 ⑤ 步之前**。
本日脚本的六步顺序就是为了这个——第 2 步不一致就在第 2 步停下，
根本不会走到构建，更不会走到上传。

### tag 和包内版本为什么会不一致

这是发布事故里最常见的一类，来源通常有三个：

1. **版本号写死在多个地方**：`pyproject.toml` 写 1.2.3、`__init__.py` 里
   `__version__` 还写 1.2.2、README 徽章又是另一个数。
2. **tag 打错地方**：在别人的提交上打了 tag，或者 tag 是 `v1.2.4` 但
   那批代码里的版本还没升。
3. **手改版本忘了改 tag**：本地 bump 了，tag 复用了上一次。

根治办法是**单一数据源**：让 `pyproject.toml` 只写一次版本，
其他位置（`__init__.py`、CI、打包脚本）从它读。
在第 ② 步做一次机械比对，比任何「仔细一点」都可靠。

### 信息是怎么从提交流到 CHANGELOG 的

```
  git log 的一条提交
  ┌────────────────────────────────────────────────────┐
  │ 8b7a6f5 feat(cli)!: 把 --output 参数改名为 --format  │
  │                                                     │
  │ BREAKING CHANGE: --output 已移除，请改用 --format     │
  └────────────────────────────────────────────────────┘
        │
        ├─▶ 解析 subject → type=feat  scope=cli  bang=!
        ├─▶ 解析 body    → 有 BREAKING CHANGE: → breaking=True，摘出说明句
        │
        ├─▶ 分类：breaking 优先 → Changed（额外进 BREAKING 区）
        ├─▶ 版本决策：出现过 breaking → MAJOR 递增
        └─▶ 渲染：把 scope 拼进条目，附上短 sha 便于回溯
```

注意 `!` 和 `BREAKING CHANGE:` **两种标记都要认**——只认一个，
就会漏掉一半破坏性变更，进而算错版本号。本日脚本的自检专门断言了这两种。

---

## 定义与方法（速查）

### SemVer 操作速查（`code/01-semver.py`）

```bash
python3 code/01-semver.py --self-test                    # 规范原文例子逐对断言
python3 code/01-semver.py --check 1.2.3-rc.1             # 合法性，退出码 0/1
python3 code/01-semver.py --parse 2.0.0-rc.1+build.5     # 拆解成字段
python3 code/01-semver.py --compare 1.0.0-alpha.1 1.0.0-beta
python3 code/01-semver.py --bump 1.2.3 --part minor
python3 code/01-semver.py --match '^1.2.3' 1.9.9
python3 code/01-semver.py --sort 1.0.0 1.0.0-rc.1 0.9.9
```

| 范围表达式 | 含义 | 边界用例 |
|---|---|---|
| `^1.2.3` | >=1.2.3 <2.0.0 | 1.9.9 ✅ / 2.0.0 ❌ |
| `^0.2.3` | >=0.2.3 <0.3.0（0.x 只放开 patch） | 0.2.9 ✅ / 0.3.0 ❌ |
| `~1.2.3` | >=1.2.3 <1.3.0 | 1.2.9 ✅ / 1.3.0 ❌ |
| `>=1.2.3, <2.0.0` | 区间 | 1.5.0 ✅ / 2.0.0 ❌ |
| `1.2.x` | >=1.2.0 <1.3.0 | 通配 |

> 递增的两个反直觉点：`bump('1.2.3-rc.1','patch') = '1.2.3'`（预发布转正是**丢弃**
> 预发布，不是变成 `1.2.4`）；`bump('1.2.3','prerelease') = '1.2.4-0'`
> （先把 patch 挑上去，再加预发布）。

### CHANGELOG 速查（`code/02-changelog.py`）

```bash
python3 code/02-changelog.py --self-test
python3 code/02-changelog.py --from gitlog.txt --current 1.1.4 --dry-run
python3 code/02-changelog.py --from gitlog.txt --current 0.3.1 --zero-major
python3 code/02-changelog.py --lint CHANGELOG.md          # 体检，退出码 0/1
```

提交记录的输入格式（等价于 `git log --pretty=format:'%h %s%n%b'`）：

```
a1b2c3d feat(api): 新增分页参数 page/page_size
8b7a6f5 feat(cli)!: 把 --output 参数改名为 --format

BREAKING CHANGE: --output 已移除，请改用 --format
```

### 构建与校验速查（`code/03-build-verify.py`）

```bash
python3 code/03-build-verify.py --self-test                       # 自造包真构建真校验
python3 code/03-build-verify.py --project . --out dist            # 优先官方 build 前端
python3 code/03-build-verify.py --project . --out dist --dry-run  # 只打印计划
PYTHONPATH=./.deps python3 -m build --no-isolation --outdir dist .   # 等价的原生命令
PYTHONPATH=./.deps python3 -m twine check dist/*
```

`--no-isolation` 的含义：不让 build 建隔离环境、去下载 build-system.requires，
而是直接用当前环境里的后端。**离线可用、快**；代价是后端版本不受 pyproject 约束。
生产 CI 里推荐去掉它以获得可复现构建。

### 流水线速查（`code/04-release-pipeline.py`）

```bash
python3 code/04-release-pipeline.py --self-test                  # 起本地桩，端到端
python3 code/04-release-pipeline.py --tag v1.2.3 --project . --dry-run
DAY181_INDEX_TOKEN=pypi-xxx python3 code/04-release-pipeline.py --tag v1.2.3 --project . --repository testpypi
```

token 只从环境变量读（`DAY181_INDEX_TOKEN`），**不接受命令行传参**——
命令行参数会出现在 `ps`、shell history 和 CI 日志里。

### legacy 上传协议字段（twine 用的就是它）

`POST https://upload.pypi.org/legacy/`，`multipart/form-data`：

| 字段 | 说明 |
|---|---|
| `:action` | 固定 `file_upload` |
| `protocol_version` | 固定 `1` |
| `name` / `version` | 来自 METADATA |
| `filetype` | `sdist` 或 `bdist_wheel` |
| `metadata` | 完整 core metadata 文本（RFC 822 风格） |
| `sha256_digest` / `md5_digest` | 内容摘要，索引端校验传输完整性 |
| `content` | 文件本体，带 `filename=` |

认证头：`Authorization: Basic base64("__token__:pypi-****")`

### 版本决策速查

| 提交里出现了什么 | 下一个版本 |
|---|---|
| 任意 `!` 或 `BREAKING CHANGE:` | MAJOR +1（0.x 时按惯例只是 MINOR +1） |
| 有 `feat`，无 breaking | MINOR +1 |
| 只有 `fix` / 内部改动 | PATCH +1 |
| 什么都没有 | 不该发版 |

---

## 实战环境

| 项 | 版本 / 说明 |
|---|---|
| 主机 | Linux 7.0.0-34-generic (x64)，Docker 29.1.3 |
| Python | 3.12.3（`python3 -V` 实测） |
| pip | 24.0 |
| 构建后端 | setuptools 83.0.0、wheel 0.42.0（系统已装） |
| 官方工具 | `build` **1.6.1**、`twine` **7.0.0**（`pip install --target /tmp/day181/.deps` 隔离安装，不进仓库） |
| 本日代码 | `code/` 下四个脚本，全部纯标准库 |

四个脚本都能**脱离第三方依赖**跑自检：`01`（纯 stdlib）、`02`（纯 stdlib）、
`03`（没装 build 时降级到 setuptools 后端）、`04`（起本地桩，不碰外网）。
只有「真跑官方 build 前端」和「真 twine check」两步需要那三个包。

| 脚本 | `--self-test` 耗时（实测） |
|---|---|
| 01-semver.py | 0.03 s |
| 02-changelog.py | 0.03 s |
| 03-build-verify.py | 0.62 s |
| 04-release-pipeline.py | 2.04 s |

（测速条件：`/usr/bin/time -f '%e s'`，同一台机器，单次运行，
包含一次真实构建；不同运行的耗时会有 ±30% 波动。）

---

## 图解

见 [`diagrams/README.md`](diagrams/README.md)：语义化版本的比较规则可视化、
六步发布链路、构建产物关系、提交到 CHANGELOG 的数据流、上传协议时序。

---

## 实验 1：SemVer 的规则是不是真能算出来

**目的**：把「靠眼看版本号」换成「靠规则算」，并亲眼确认两条反直觉规则。

**准备**：无（纯标准库）。

**执行**：

```bash
python3 code/01-semver.py --self-test
python3 code/01-semver.py --parse 2.0.0-rc.1+build.5
python3 code/01-semver.py --compare 1.0.0-alpha.beta 1.0.0-beta
python3 code/01-semver.py --bump 1.2.3-rc.1 --part patch
python3 code/01-semver.py --match '^1.2.3' 1.9.9
python3 code/01-semver.py --match '^1.2.3' 2.0.0
python3 code/01-semver.py --sort 1.0.0 1.0.0-rc.1 1.0.0-beta.11 0.9.9
```

**预期结果**：`--self-test` 退出码 0；`--compare` 输出 `<`。

**实际结果**（本机真实 stdout，2026-10-16，耗时 0.03 s）：

```
✅ self-test 通过：规范优先级链 8 个版本全序正确 / +build 不参与比较 / 数字段按数值比 / 8 个非法输入被拒 / 6 条递增规则 / 5 条范围匹配规则成立

2.0.0-rc.1+build.5
  major=2 minor=0 patch=0
  prerelease=['rc', '1']
  build=['build', '5']
  是否预发布=True

1.0.0-alpha.beta < 1.0.0-beta   (compare=-1)

1.2.3-rc.1  --patch-->  1.2.3

1.9.9 ✅ 落在 范围 ^1.2.3
2.0.0 ❌ 不落在 范围 ^1.2.3

0.9.9 -> 1.0.0-beta.11 -> 1.0.0-rc.1 -> 1.0.0
```

**结论**：

- 排序把 `1.0.0-beta.11` 放在 `1.0.0-rc.1` 之前、`1.0.0` 之前——
  预发布永远低于对应正式版，这条规则算得出来；
- `bump('1.2.3-rc.1','patch')` 得到 **1.2.3**：预发布的「转正」是丢掉预发布段，
  不是把 patch 再 +1；
- `--sort` 的输出顺序与规范第 11 条的链条完全一致，说明比较函数不是「看起来对」。

**清理**：无（只读，不写盘、不起服务）。

---

## 实验 2：从提交生成 CHANGELOG，并算出下一个版本

**目的**：验证「提交 → 分类 → 版本决策 → CHANGELOG」这条推导链，
并且**只从提交**得到 `2.0.0` 这个结论。

**执行**：

```bash
python3 code/02-changelog.py --self-test
python3 code/02-changelog.py --current 1.1.4 --repo-url https://github.com/Geek0ne/SEOClaw --dry-run
python3 code/02-changelog.py --current 0.3.1 --zero-major --dry-run | head -8
```

**实际结果**（本机真实 stdout，2026-10-16，耗时 0.03 s）：

```
✅ self-test 通过：7 个提交解析（含无空行情形）/ 2 类 BREAKING 识别 / 4 条分类规则 / 4 条版本决策（含 0.x 惯例）/ 渲染 3 条断言 / lint 正反两例
```

`--dry-run` 的输出：

```
# 提交 7 条 · 跳过 2 条（非规范或内部改动） · 版本决策 1.1.4 -> 2.0.0（依据：BREAKING CHANGE）

## [2.0.0] - 2026-10-16

### BREAKING CHANGES

- 把 --output 参数改名为 --format (8b7a6f5)

### Added

- **api**: 新增分页参数 page/page_size (a1b2c3d)

### Changed

- **db**: 用批量查询替换 N+1 查询 (4c3b2a1)
- **cli**: 把 --output 参数改名为 --format (8b7a6f5)

### Fixed

- **api**: 修正 page=0 时的越界读取 (9f8e7d6)
- **cli**: 修正 --format json 时的缩进 (3a2b1c0)

[2.0.0]: https://github.com/Geek0ne/SEOClaw/compare/v1.1.4...v2.0.0

# --dry-run：未写文件
```

同一个输入换成 0.x 项目惯例（`--zero-major`）：

```
# 提交 7 条 · 跳过 2 条（非规范或内部改动） · 版本决策 0.3.1 -> 0.4.0（依据：BREAKING CHANGE）
```

**结论**：

- 7 条提交里 `docs` 和 `chore` 被跳过（**内部改动不进 CHANGELOG**），
  对外可见的 5 条各归其位；
- 版本决策完全由提交推导：有 breaking → 1.1.4 直接跳 **2.0.0**；
  同样的提交在 0.x 项目里只升到 **0.4.0**；
- `!` 和正文里的 `BREAKING CHANGE:` 被识别成同一条 breaking，
  并且正文的说明句被摘出来单独展示——两者缺一都会漏判。

**清理**：`--dry-run` 不写盘。去掉 `--dry-run` 会写出 `CHANGELOG.entry.md`，记得删。

---

## 实验 3：真机构建 —— 用官方 build 前端出 sdist + wheel

**目的**：拿到一份**真的**构建产物，并验证「产物能装、能用」。

**准备**（隔离安装官方工具，不进仓库）：

```bash
mkdir -p /tmp/day181 && cd /tmp/day181
python3 -m pip install --target ./.deps build twine
PYTHONPATH=/tmp/day181/.deps python3 -c "import build,twine;print(build.__version__,twine.__version__)"
```

实测输出 `1.6.1 7.0.0`。

**执行**：先造一个最小可构建项目（脚本内置的 `make_demo_project`），再跑官方命令：

```bash
cd /tmp/day181/demo
PYTHONPATH=/tmp/day181/.deps python3 -m build --no-isolation --outdir dist .
PYTHONPATH=/tmp/day181/.deps python3 -m twine check dist/*
ls -l dist
python3 -m zipfile -l dist/*.whl
```

**实际结果**（2026-10-16；测速条件：`/usr/bin/time -f '%e s'`，首次冷启动、单次运行）：

```
Successfully built demo_release_pkg-1.2.3.tar.gz and demo_release_pkg-1.2.3-py3-none-any.whl
REAL_BUILD_WALL=1.94 s

-rw-r--r-- 1 root root 1458 10月 16 22:25 demo_release_pkg-1.2.3-py3-none-any.whl
-rw-r--r-- 1 root root 1222 10月 16 22:25 demo_release_pkg-1.2.3.tar.gz

Checking dist/demo_release_pkg-1.2.3-py3-none-any.whl: PASSED
Checking dist/demo_release_pkg-1.2.3.tar.gz: PASSED

File Name                                             Modified             Size
demo_pkg/__init__.py                           2026-10-16 14:25:28          103
demo_release_pkg-1.2.3.dist-info/METADATA      2026-10-16 14:25:30          262
demo_release_pkg-1.2.3.dist-info/WHEEL         2026-10-16 14:25:30           91
demo_release_pkg-1.2.3.dist-info/top_level.txt 2026-10-16 14:25:30            9
demo_release_pkg-1.2.3.dist-info/RECORD        2026-10-16 14:25:30          408
```

wheel 里的 METADATA 全文（这就是上传时 `metadata` 字段的来源）：

```
Metadata-Version: 2.4
Name: demo-release-pkg
Version: 1.2.3
Summary: Day 181 演示包：只用来验证构建与校验链路
License: MIT
Requires-Python: >=3.9
Description-Content-Type: text/markdown

# demo-release-pkg

Day 181 构建演示用的最小包。
```

**再往前一步：证明这个 wheel 真的能装、能用**：

```bash
python3 -m pip install --quiet --no-deps --target /tmp/day181/installed /tmp/day181/demo/dist/*.whl
PYTHONPATH=/tmp/day181/installed python3 -c "import demo_pkg; print(demo_pkg.__version__, demo_pkg.greet('day181'))"
```

实测输出：

```
1.2.3 hello, day181
```

**结论**：

- 构建产物很小：wheel **1458 字节**、sdist **1222 字节**，因为包里只有 1 个
  103 字节的模块——**wheel 的体积几乎全是元数据**（METADATA/WHEEL/RECORD）；
- `twine check` 两个产物都 PASSED：元数据完整、README 能被正确渲染成描述；
- wheel 能装能 import，`__version__` 与文件名一致——**这才是「构建成功」的完整含义**；
- 注意 setuptools 对 `project.license` 写成 TOML 表发了弃用警告
  （2027-02-18 后必须改成 SPDX 字符串）。**警告不等于失败**，但它说明
  「能构建」和「符合未来规范」是两件事，实测原话是：

```
WARNING `project.license` as a TOML table is deprecated ... By 2027-Feb-18, you need to update
```

**清理**（本实验产物都在 /tmp，仓库里不留东西）：

```bash
rm -rf /tmp/day181/demo /tmp/day181/installed
```

---

## 实验 4：降级路径 —— 没有 build 也能出产物

**目的**：验证「前端不在，构建能力还在」，并让校验器接受正反两面的检验。

**执行**（不带 `PYTHONPATH`，即环境里没有 `build` / `twine`）：

```bash
python3 code/03-build-verify.py --self-test
python3 code/03-build-verify.py --project /tmp/day181/demo --out /tmp/day181/demo/dist --dry-run
PYTHONPATH=/tmp/day181/.deps python3 code/03-build-verify.py --project /tmp/day181/demo --out /tmp/day181/demo/dist
```

**实际结果**（2026-10-16，无 build/twine 环境，耗时 0.62 s）：

```
# 自检：临时项目 /tmp/day181-build-rdifugn9/proj
  build 未安装 → 降级用 setuptools.build_meta 后端直接构建
  | sdist: demo_release_pkg-1.2.3.tar.gz
  | wheel: demo_release_pkg-1.2.3-py3-none-any.whl
# 构建后端=setuptools-backend  耗时=513 ms
wheel  demo_release_pkg-1.2.3-py3-none-any.whl
       字节=1458  sha256=7384e0eb81207830…
       METADATA Name=demo-release-pkg Version=1.2.3  Requires-Python=>=3.9  内含文件=5
sdist  demo_release_pkg-1.2.3.tar.gz
       字节=1217  sha256=74067333889029ad…
       METADATA Name=demo-release-pkg Version=1.2.3  Requires-Python=>=3.9  内含文件=13
  ✅ 文件名、内部元数据、wheel/sdist 版本一致，四项必填字段齐全
# 反向验证：多放一个只改了文件名版本号的 demo_release_pkg-9.9.9-py3-none-any.whl，校验器报出 2 个问题（符合预期）
# 产物体积：{'demo_release_pkg-1.2.3-py3-none-any.whl': 1458, 'demo_release_pkg-1.2.3.tar.gz': 1217}
  twine 未安装 → 跳过 twine check（上面是内置校验，覆盖的是同一批事实：文件名 + 元数据一致性）
✅ self-test 通过：真构建出 wheel+sdist，元数据一致，且校验器能抓出人名错误
# 已清理临时目录 /tmp/day181-build-rdifugn9
```

带上官方工具时，同一个脚本自己会切到前端路径（**注意 `构建后端=build-frontend`**）：

```
# 项目=/tmp/day181/demo
# 工具：build=有 · twine=有
# 构建后端=build-frontend 耗时=1921 ms 退出码=0
  Checking /tmp/day181/demo/dist/demo_release_pkg-1.2.3-py3-none-any.whl: PASSED
  Checking /tmp/day181/demo/dist/demo_release_pkg-1.2.3.tar.gz: PASSED
```

**结论**：

- **`build` 前端只是个壳**：它建隔离环境、装后端、调后端的
  `build_wheel`/`build_sdist`。壳不在了，直接调后端（`setuptools.build_meta`）
  一样能出全套产物——这就是「降级」为什么可行；
- 耗时对比（同机、单次、本项目用 `--no-isolation`）：后端直调 **513 ms**
  vs 前端 **1921 ms**。差距不是下载依赖造成的（没开隔离），而是前端额外的
  环境准备与产物检查；换来的是隔离与规范符合性检查；
- 自检里**必须有一条反向断言**：故意放一个「文件名版本被改成 9.9.9、内容没动」的
  wheel，校验器报出 2 个问题。**没有这条，校验器可能只是个永远通过的安慰剂**；
- sdist 的体积每次略有差异（1217 / 1210 / 1222 字节都出现过）——因为 tar 会把
  打包时刻写进头部，**同一个源码两次构建的 sdist 不是逐字节相同的**。
  wheel 则稳定在 1458 字节。

**清理**：自检自己用 `tempfile.mkdtemp` 并在 `finally` 里 `shutil.rmtree`，
实测输出末尾那行 `# 已清理临时目录 …` 就是证据。

---

## 实验 5：端到端流水线（含真上传到一个本地索引桩）

**目的**：把六步串起来，并且**真的把包「传」出去一次**——不是在脑子里模拟。

**为什么用本地桩**：真发到 TestPyPI 需要一个有效 token，而发出去的包是公开的、
不可撤回的。桩实现了 legacy 上传协议里被用到的部分（multipart 解析、Basic 认证头、
`sha256_digest` 校验），所以「上传这一步真的跑通过」是被证明的，
而不是被假设的。

**执行**：

```bash
python3 code/04-release-pipeline.py --self-test
```

**实际结果**（2026-10-16，本机真实 stdout，耗时 2.04 s）：

```
[1/6] tag v1.2.3 -> 版本 1.2.3 · SemVer 合法 (0 ms)
[2/6] pyproject version = 1.2.3
[3/6] CHANGELOG CHANGELOG.md: 1 个版本段，0 个问题
  build 未安装 → 降级用 setuptools.build_meta 后端直接构建
[4/6] 构建 backend=setuptools-backend 耗时=543 ms rc=0
wheel  demo_release_pkg-1.2.3-py3-none-any.whl
       字节=1458  sha256=1ef6a777fc4f6f09…
       METADATA Name=demo-release-pkg Version=1.2.3  Requires-Python=>=3.9  内含文件=5
sdist  demo_release_pkg-1.2.3.tar.gz
       字节=1213  sha256=dfd1e95e1a10bc67…
       METADATA Name=demo-release-pkg Version=1.2.3  Requires-Python=>=3.9  内含文件=13
  ✅ 文件名、内部元数据、wheel/sdist 版本一致，四项必填字段齐全
[5/6] 校验 通过（0 个问题）
[6/6] --dry-run / 未指定仓库：不发布。真实执行时会做：
        POST <url>  file=demo_release_pkg-1.2.3-py3-none-any.whl  Authorization: Basic ***
        POST <url>  file=demo_release_pkg-1.2.3.tar.gz  Authorization: Basic ***
# 反向验证：tag=v9.9.9 而包内是 1.2.3 -> 第 2 步拦下（未构建、未上传）
# 反向验证：无 token 时拒绝上传（fail closed，不是 fail open）
[6/6] ✅ demo_release_pkg-1.2.3-py3-none-any.whl -> HTTP 200 {"message": "OK"}
[6/6] ✅ demo_release_pkg-1.2.3.tar.gz -> HTTP 200 {"message": "OK"}
# 全流程 389 ms
# 桩收到的上传：[{"name": "demo-release-pkg", "version": "1.2.3", "filename": "demo_release_pkg-1.2.3-py3-none-any.whl", "size": 1458, "sha256": "1ef6a777fc4f6f09"}, {"name": "demo-release-pkg", "version": "1.2.3", "filename": "demo_release_pkg-1.2.3.tar.gz", "size": 1224, "sha256": "23bee8e7e4994185"}]
# 反向验证：把 sha256 改坏后桩返回 HTTP 400（{"message": "sha256_digest 与实际内容不符"}）
✅ self-test 通过：六步全跑通（含真上传到本地桩）；版本不一致/无 token/摘要不符 三种坏情况都被拦下
# 已清理临时目录 /tmp/day181-pipeline-jq45fy14
```

**结论**：

- 六步全绿时，桩收到了**两个**文件，且 `name`/`version` 与文件名一致——
  说明 multipart 编码、`metadata` 字段、`sha256_digest` 都是按协议发的；
- 三种坏情况都被**拦在门外**：tag 与包内版本不一致（第 2 步、连构建都没做）、
  没有 token（拒绝上传，**fail closed**）、内容摘要对不上（索引端 400）；
- 最后一条最值得注意：它是**校验器自己的校验**。桩如果无条件返回 200，
  这个自检就变成了自我麻醉——所以桩必须真的算一遍摘要（见翻车复盘 5）。

**清理**：`--self-test` 在 `finally` 里关服务、删临时目录；实测输出末尾两行即是证据。
不占端口（绑的是 0 号端口，由内核分配）。

---

## 实验 6：真实索引能碰到什么程度（含未实测部分）

**目的**：把「和真 PyPI 的边界」划清楚——哪些我验过，哪些没验过。

**执行**（只读查询 + 用假 token 试一次上传）：

```bash
python3 - <<'PY'
import json, urllib.request
for url in ['https://test.pypi.org/pypi/sampleproject/json',
            'https://pypi.org/pypi/sampleproject/json']:
    with urllib.request.urlopen(url, timeout=15) as r:
        d = json.load(r)
    print(url, '-> HTTP', r.status)
    print('   name=%s version=%s' % (d['info']['name'], d['info']['version']))
    for f in d['urls']:
        print('   file:', f['filename'], f['size'], 'bytes',
              'sha256=' + f['digests']['sha256'][:16] + '...')
PY
```

**实际结果**（2026-10-16）：

```
https://test.pypi.org/pypi/sampleproject/json -> HTTP 200
   name=sampleproject version=1.2.0 requires_python=None
   release file: sampleproject-1.2.0-py2.py3-none-any.whl 3795 bytes sha256=716f2195be41bd98...
   release file: sampleproject-1.2.0.tar.gz 3148 bytes sha256=9a99bb2beb2acba2...
https://pypi.org/pypi/sampleproject/json -> HTTP 200
   name=sampleproject version=4.0.0 requires_python=>=3.9
   release file: sampleproject-4.0.0-py3-none-any.whl 4661 bytes sha256=c23e447ea90d796d...
   release file: sampleproject-4.0.0.tar.gz 5760 bytes sha256=0ace7980f82c5815...
```

再用一个**假 token** 打真实的 TestPyPI 上传端点（不会发布任何东西，因为认证会失败）：

```
HTTP 403
403 Invalid or non-existent authentication information. See https://test.pypi.org/help/#invalid-auth for more information.
```

**已实测的边界**：

- 真实索引的 JSON API 可用，且**返回的正是我们构建产物的同类信息**
  （文件名、字节数、sha256）——所以「上传成功后拿什么校验」是有答案的；
- 真实上传端点**存在且强制认证**：假 token 立刻 403。这证明
  客户端（我们的 `upload_artifact`）在编码、认证头、协议字段上
  已经能走到「被服务端正确理解并拒绝」这一步——如果协议本身发错了，
  更可能拿到的是 400 而不是 403。

**未实测：真实的成功上传**。

- **原因**：需要一个有效的 PyPI / TestPyPI API token。本日没有使用任何真实凭据
  （也不应该为了教学把包公开出去）。所以「上传成功 → 索引页出现新版本」这一段
  **没有在本机跑过**。
- **预期结果**：`twine upload --repository testpypi dist/*` 打印
  `Uploading distributions to https://test.pypi.org/legacy/` 与
  `View at: https://test.pypi.org/project/<name>/<version>/`；
  随后 `https://test.pypi.org/pypi/<name>/json` 能查到刚上传的文件名与 sha256。
- **验证方法**：注册 TestPyPI 账号 → 在账户页生成 scope 为
  `Entire account (all projects)` 的 token → 设置
  `DAY181_INDEX_TOKEN=pypi-...` → 跑
  `python3 code/04-release-pipeline.py --tag v1.2.3 --project . --repository testpypi`，
  脚本第 6 步会把两个产物的 HTTP 状态码逐个打出来；再按上面的 JSON API
  用 `sha256` 与本地产物比对。**注意 TestPyPI 与 PyPI 是两套账号、两套 token。**

**其他未实测项**（明确列出，避免读者误以为都验过）：

| 项 | 状态 | 原因 |
|---|---|---|
| `build` 的隔离构建（不加 `--no-isolation`） | 未实测 | 本日全部用 `--no-isolation` 以避开网络依赖；隔离模式会另建虚拟环境并下载后端 |
| GitHub Actions 上的 release workflow | 未实测 | 本日只做本地流水线，未接 CI；写法见文末延伸 |
| `twine` 的 GPG 签名（`--sign`） | 未实测 | 需要密钥对与 `gpg`，本日未配置 |
| 私有索引 / devpi | 未实测 | 本日只用本地桩验证协议 |
| 从 TestPyPI 装回刚上传的包 | 未实测 | 依赖上一条（需要真的传上去） |

---

## 翻车复盘（七个真问题，全部在本日实测中出现）

### 1. 正则里漏了一个 `[^-]+`，校验器把合法产物判成非法

**症状**：`03 --self-test` 直接失败：

```
  ❌ demo_release_pkg-1.2.3.tar.gz: 文件名不符合 PEP 625
  ❌ 缺少 wheel 或 sdist（只有 ['wheel']）
```

**假设**：setuptools 生成的 sdist 名字不符合规范？不太可能。
**验证**：把正则单独拿出来试：

```python
SDIST_RE = re.compile(r"^(?P<name>.+)-(?P<version>)\.tar\.gz$")
SDIST_RE.match("demo_release_pkg-1.2.3.tar.gz")   # -> None
```

**根因**：`(?P<version>)` 这个分组**里面什么都没写**，它只能匹配空字符串，
于是正则变成「一串字符 + 一个 '-' + 立刻是 '.tar.gz'」，永远匹配不上。
改法是补上 `[^-]+`：

```python
SDIST_RE = re.compile(r"^(?P<name>.+)-(?P<version>[^-]+)\.tar\.gz$")
```

**复测**：sdist 被正确解析，校验通过。

> 教训：「校验失败」的第一反应不该是「产物有问题」，而是**先证明校验器本身没毛病**。
> 一个写错的正则会让所有合法产物都变红，这和「所有产物真的都坏了」看起来一模一样。

### 2. 不做 PEP 503 归一化，同一个包被判成两个名字

**症状**：

```
  ❌ demo_release_pkg-1.2.3.tar.gz: 文件名里的名字 demo_release_pkg 与元数据 demo-release-pkg 不一致
```

**假设**：元数据里 Name 写错了？
**验证**：读产物内部的 METADATA —— 里面写的是 `Name: demo-release-pkg`，完全正确。
**根因**：sdist 文件名用下划线（`demo_release_pkg`），wheel/元数据里用连字符
（`demo-release-pkg`）——规范规定这两者**是同一个名字**。我的比较是裸字符串比较，
于是把合法状态判成了错误。
**修复**：加 `normalize_name()`（小写 + 把连续 `-_.` 压成单个 `-`），
两边都过一遍再比。
**复测**：`✅ 文件名、内部元数据、wheel/sdist 版本一致，四项必填字段齐全`。

> 教训：**「看起来不一样」和「真的不一样」是两个判断**。包名、邮箱、路径、
> 时区这类东西都有「同一实体的多种写法」，比较前先归一化。

### 3. 提交日志按空行切，把一批提交全吸进了第一个

**症状**：`02 --self-test` 断言失败：`应该解析出 7 个提交，得到 2`。
**假设**：正则没匹配上？但结果只有 2 个，说明是**切分**的问题，不是匹配。
**根因**：我一开始的解析逻辑是「遇到空行才算一个提交结束」。而
`git log --pretty=format:'%h %s%n%b'` 的输出在提交之间**并不加空行**，
于是前 5 条普通提交全部被当成第 1 条提交的正文，实际只切出 2 个块。
**修复**：改成**按行首模式判断新提交**（7–40 位十六进制 sha + 空格 + 主题），
而不是靠空行。
**复测**：`✅ self-test 通过：7 个提交解析（含无空行情形）…`

> 教训：解析「别人生成的文本格式」时，先问一句**分隔符到底是什么**。
> 我这里是凭印象写了「空行分隔」——直到自检把数字报出来（7 vs 2），
> 印象才被证伪。

### 4. 断言「排序后 sdist 在前」——想当然的排序假设

**症状**：

```
AssertionError: ['demo_release_pkg-1.2.3-py3-none-any.whl', 'demo_release_pkg-1.2.3.tar.gz']
```

**根因**：两个文件名共享前缀 `demo_release_pkg-1.2.3.`，下一位是 `p`（wheel 的
`py3`）和 `t`（sdist 的 `tar.gz`），`p < t`，所以**排序后 wheel 在前**。
我写断言时脑子里想的是「sdist 一般排在前面」，就把顺序硬编码进去了。
**修复**：断言改成「两种文件各存在一个」，而不是「第 0 个必须是 sdist」。
**复测**：自检通过（退出码 0）。

> 教训：**断言应该断言不变量，而不是断言顺带观察到的巧合顺序**。
> 排序依赖文件名，文件名依赖构建后端，这属于实现细节。

### 5. 一个自我麻醉的空测试：patch 把校验双方一起 patch 掉了

**症状**：`AssertionError: 篡改 digest 后桩仍返回 200，说明校验是假的`
——也就是说，这条「篡改必须被发现」的断言**本该失败，它却在替我遮掩问题**。
**根因**：自检里用 `mock.patch("hashlib.sha256")` 篡改发送端的摘要，
但**桩的校验端也在同一个进程里调 `hashlib.sha256`**——
patch 是模块级的，两边都拿到了篡改后的同一个函数，算出的错值一模一样，
于是服务端认为「摘要匹配」，返回 200。
**修复**：桩在模块加载时先抓住真函数的引用（`_SHA256 = hashlib.sha256`），
校验时用这个引用，不在运行时去查模块属性。
**复测**：

```
# 反向验证：把 sha256 改坏后桩返回 HTTP 400（{"message": "sha256_digest 与实际内容不符"}）
```

> 教训：**用 mock 篡改一个全局函数时，要问「还有谁在用它」**。
> 如果被测的两端共享同一个全局，patch 就不是「注入错误」，而是「把尺子也改短了」。
> 这类测试最危险的地方在于它**看起来是绿的**。

### 6. `EXIT=$?` 出现在管道后面，看到的是 grep 的退出码

**症状**：我一度认为 `04` 的自检是绿的，因为命令写成

```bash
python3 code/04-release-pipeline.py --self-test | grep -v '^  |' ; echo EXIT=$?
```

而 `$?` 取的是**整个管道最后一条命令**（`grep`）的状态。
`grep` 找到了行就返回 0，所以那个 `EXIT=0` 是 grep 的 0，
Python 其实已经断言失败退出了 1。

**修复**：先把输出落盘再判断（本日最终采用的方式）：

```bash
python3 code/04-release-pipeline.py --self-test >/tmp/day181/04.out 2>/dev/null
echo "REAL_EXIT=$?"
```

**复测**：四个脚本 `REAL_EXIT=0`（修掉上面第 4、5 两条之后）。

> 教训：**「命令看起来绿了」和「命令真的绿了」中间隔着一个 `$?`**。
> 一切「跑一下看看」的验证，都要确保退出码来自那个你真正关心的进程。

### 7. `upload_artifact` 只接受 `Path`，传字符串直接崩

**症状**：

```
AttributeError: 'str' object has no attribute 'read_bytes'
```

**根因**：函数内部按 `Path` 用，但没做转换，外部传 `str` 就炸——
而且炸在函数第一行，看起来像调用方的问题。
**修复**：函数入口加 `path = Path(path)`。
**复测**：用字符串路径调用，正常拿到 `HTTP 403`（见实验 6）。

> 教训：**脚本里的「对外函数」要对自己声明的参数类型宽容一点**。
> 尤其当这条路径只在「手动调用」时才走到——自检全走 `Path` 的话，
> 这个 bug 永远不会被自检发现。

---

## 清理（每次实验后都做）

```bash
rm -rf /tmp/day181-build-* /tmp/day181-pipeline-*   # 自检的临时目录（正常已自删）
rm -rf /tmp/day181/demo /tmp/day181/installed       # 实验 3 的构建产物与安装目录
rm -rf /tmp/day181/.deps                            # 隔离安装的 build/twine
rm -rf /tmp/day181                                  # 全部清掉
```

自检项：

```bash
ls -d /tmp/day181-* 2>/dev/null || echo "无遗留临时目录"
ss -ltnp | grep -E ':181[0-9]' || echo "无遗留端口"
docker ps --format '{{.Names}}' | grep -i day181 || echo "无遗留容器"
git status --short days/day-181-release-management   # 应该只看到本日新增文件
```

本日**没有起任何容器**（全部实验都是本地进程 + 一个绑 0 号端口的临时 HTTP 桩），
所以不需要 `docker rm`；桩进程随 `srv.shutdown()` 结束，端口由内核回收。

---

## 思考题

1. `1.0.0+build.1` 和 `1.0.0+build.2` 谁更大？为什么规范要这么规定？
   如果构建元数据参与比较，会给依赖解析带来什么麻烦？
2. `1.0.0-alpha.1` 和 `1.0.0-alpha.beta` 谁大？`1.0.0-alpha.9` 和
   `1.0.0-alpha.10` 呢？（提示：数字段按数值比）
3. 你的项目在 0.9.0，这次做了破坏性变更。按规范**应该**发什么版本？
   按社区惯例**通常**发什么？两种选择各自的代价是什么？
4. 为什么 PyPI 不允许覆盖同名版本？如果允许覆盖，一个用了
   `pip install foo==1.2.3` 的 CI 会在什么情况下「昨天能过今天不能过」？
5. `twine check` 通过能保证包一定能装吗？说出至少两件它检查不到的事。
6. 为什么 API token 的用户名要固定写 `__token__`？如果直接用自己的用户名会怎样？
7. 你的流水线第 5 步（校验）通过了、第 6 步上传也成功了，但用户装了报
   `ModuleNotFoundError`。问题最可能出在哪一步？怎么在下一次发布前发现它？
8. 实验 5 里「篡改摘要后桩返回 400」这条断言，如果不写会有什么后果？
   举一个「自检全绿但功能其实坏了」的例子（本日正文里有一个真的）。

---

## 交付清单

- `code/01-semver.py` —— SemVer 解析/比较/递增/范围匹配（纯标准库，`--self-test`）
- `code/02-changelog.py` —— Conventional Commits → Keep a Changelog（`--lint` / `--dry-run` / `--self-test`）
- `code/03-build-verify.py` —— 构建 + 产物校验，缺 `build` 时降级到 setuptools 后端（`--project` / `--dry-run` / `--self-test`）
- `code/04-release-pipeline.py` —— 六步发布流水线 + 本地索引桩（`--repository` / `--dry-run` / `--self-test`）
- `diagrams/README.md` —— 五张原理图
- `exercises/checklist.md` —— 练习与检查表

---

## 延伸（选做）

1. 把 `04` 接进 GitHub Actions：`on: push: tags: ['v*']` 触发，
   token 用 `secrets.PYPI_API_TOKEN`（**不要**写进仓库），
   环境用 `environment: release` 做人工审批门，`permissions:`
   最小化（`contents: read`，Trusted Publishing 时加 `id-token: write`）。
2. 把版本改成**单一数据源**：`pyproject.toml` 用
   `dynamic = ["version"]` + `setuptools_scm`，版本直接来自 git tag，
   于是「tag 与包内版本不一致」这类事故在结构上就不可能发生。
3. 给 `03` 加一条「构建可复现性」检查：同一个 commit 构建两次，
   比较 wheel 的 `RECORD` 里每个文件的 sha256，看哪些字段天生不稳定
   （提示：`RECORD` 自身、时间戳），想想为什么 PyPI 上的 wheel 仍然能对上摘要。
