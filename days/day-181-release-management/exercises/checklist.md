# Day 181 · 练习与检查表

> 目标：亲手把「提交 → CHANGELOG → 版本号 → 构建 → 校验 → 上传」
> 这条链路跑通，并且亲眼看见三种坏情况被拦在门外。
> **前置**：Python 3.9+（本机 3.12.3）。四个脚本纯标准库即可自检；
> 只有「官方 build 前端 + twine check」两步需要
> `python3 -m pip install --target /tmp/day181/.deps build twine`。

---

## 一、动手题（必做）

### 练习 1 — 把版本号排成一队（5 分钟）

```bash
cd days/day-181-release-management
python3 code/01-semver.py --self-test
python3 code/01-semver.py --sort 1.0.0 1.0.0-alpha 1.0.0-beta.2 1.0.0-beta.11 1.0.0-rc.1 0.9.9
```

- [ ] 把上面 6 个版本号按优先级排序，写出来
- [ ] `1.0.0-beta.11` 和 `1.0.0-beta.2` 谁在前？为什么？
- [ ] `--compare 1.0.0+build.1 1.0.0+build.999` 的结果是什么？解释这个结果

<details><summary>参考答案</summary>

排序：`0.9.9 → 1.0.0-alpha → 1.0.0-beta.2 → 1.0.0-beta.11 → 1.0.0-rc.1 → 1.0.0`
`beta.2 < beta.11`：数字段按**数值**比较（2 < 11），不是字典序。
`+build` 不参与优先级比较，两者**相等**（返回 0）。

</details>

### 练习 2 — 从假提交日志推出下一个版本（10 分钟）

```bash
printf '%s\n' \
 'a1b2c3d feat(api): 新增分页参数' \
 '9f8e7d6 fix(api): 修正越界读取' \
 '7d6c5b4 docs: 补充说明' > /tmp/day181.log
python3 code/02-changelog.py --from /tmp/day181.log --current 1.1.4 --dry-run
```

- [ ] 下一个版本是多少？依据是什么？
- [ ] `docs` 那条去哪了？怎么才能让它进 CHANGELOG？

<details><summary>参考答案</summary>

`1.2.0`（有 `feat`、无 breaking → MINOR +1）。
`docs` 属于内部改动，默认被跳过（`跳过 1 条`）；
加 `--include-internal` 会让它落到 Changed。

</details>

### 练习 3 — 让「破坏性变更」改变结论（10 分钟）

```bash
printf '%s\n' \
 'a1b2c3d feat(api): 新增分页参数' \
 '8b7a6f5 refactor(cli)!: 重命名 --output 为 --format' \
 '' \
 'BREAKING CHANGE: --output 已移除' > /tmp/day181b.log
python3 code/02-changelog.py --from /tmp/day181b.log --current 1.1.4 --dry-run
```

- [ ] 版本变成多少？和第 2 题差在哪？
- [ ] `BREAKING CHANGES` 区里出现了几条？内容是什么？
- [ ] 把 `!` 删掉但保留正文里的 `BREAKING CHANGE:`，结论会变吗？

<details><summary>参考答案</summary>

变成 `2.0.0`（有 breaking → MAJOR +1）。
BREAKING 区一条：`重命名 --output 为 --format`。
**不会变**——正文里的 `BREAKING CHANGE:` 与 `!` 等价，两者任一成立即为 breaking。
（可以再说一次：这就是为什么两种写法都必须认。）

</details>

### 练习 4 — 真机构建一次，并核对三件事（15 分钟）

```bash
mkdir -p /tmp/day181 && python3 -m pip install --quiet --target /tmp/day181/.deps build twine
python3 code/03-build-verify.py --self-test
```

- [ ] 产物是哪两个文件？各自多少字节？（写清测量条件：哪次运行）
- [ ] wheel 里有几个文件？METADATA 里的 Name/Version 是什么？
- [ ] 把 wheel 的**文件名版本**改成 9.9.9（内容不动），再跑一次校验，
      脚本报了几个问题？

<details><summary>参考答案</summary>

`demo_release_pkg-1.2.3-py3-none-any.whl`（本机实测 1458 字节）与
`demo_release_pkg-1.2.3.tar.gz`（实测 1210–1227 字节，**每次不同**，
因为 tar 写入打包时刻）。
wheel 内含 5 个文件；METADATA 里 `Name: demo-release-pkg`、
`Version: 1.2.3`。
改名成 9.9.9 后报 **2 个问题**（文件名版本与元数据不一致、wheel/sdist 版本不一致）——
这证明校验器不是安慰剂。

</details>

### 练习 5 — 端到端跑一遍，看清哪一步在拦人（15 分钟，重点）

```bash
python3 code/04-release-pipeline.py --self-test
```

- [ ] 六步里哪一步负责「tag 与包内版本对不上」？它拦下时，构建发生了吗？
- [ ] 没有 token 时脚本的行为是什么？这属于 fail open 还是 fail closed？
- [ ] 桩为什么必须真的算一遍 sha256？如果不算，自检会变成什么样？

<details><summary>参考答案</summary>

第 2 步（对版本）。拦下时**连构建都没做**——实测输出里那之后直接是下一条反向验证，
没有 `[4/6]`。
没有 token → 拒绝上传并返回失败，是 **fail closed**（宁可明确失败，也不发半成品）。
桩如果不算摘要，只会无条件回 200；那「篡改摘要必须被发现」这条断言就永远通过——
**一个自我麻醉的空测试**（本日翻车复盘第 5 条就是这个问题的真实版本）。

</details>

### 练习 6 — 真实索引只能验到边界（10 分钟）

```bash
python3 - <<'PY'
import json, urllib.request
with urllib.request.urlopen('https://test.pypi.org/pypi/sampleproject/json', timeout=15) as r:
    d = json.load(r)
print(r.status, d['info']['name'], d['info']['version'])
for f in d['urls']:
    print(f['filename'], f['size'], f['digests']['sha256'][:16])
PY
```

- [ ] 这个 JSON 里的 `digests.sha256` 和 `size` 有什么用？
- [ ] 如果自己真发布了，怎么用它确认「索引上的文件 = 我构建的文件」？
- [ ] 为什么本日**没有**真的上传一次？

<details><summary>参考答案</summary>

它们是**发布后校验**的依据：拿本地产物算 sha256，与索引公布的值逐字节比对，
就能确认中间没有损坏或错版。
本日没真传，是因为需要一个有效 token（真实凭据），且发出去就是公开且不可逆的——
所以只实测到「假 token 被 403 拒绝」这个边界，成功上传标注为**未实测**，
并写清了原因、预期结果、验证方法（README 实验 6）。

</details>

---

## 二、判断题（对/错 + 一句话理由）

- [ ] `1.0.0+build.9` 比 `1.0.0+build.1` 新。
- [ ] `1.2.3-rc.1` 的 patch 递增是 `1.2.4`。
- [ ] 只要 `twine check` 通过，包就一定能正常安装。
- [ ] CHANGELOG 应该包含 `chore: 升级 CI 缓存` 这类提交，这样才完整。
- [ ] 上传时 `Authorization` 的用户名应该填自己的 PyPI 用户名。
- [ ] 版本号写错时，可以删掉再从同版本号重新上传一次。
- [ ] 校验失败时应该先怀疑产物，而不是先怀疑校验器。

<details><summary>答案</summary>

1. ✗ 构建元数据不参与比较，两者优先级相等。
2. ✗ 预发布转正是 `1.2.3`（丢弃预发布段，patch 不再 +1）。
3. ✗ 它只检查元数据与 README 渲染；检查不到「包能不能 import」、
   「依赖是否写全」、「包数据是否漏打」等。
4. ✗ 内部改动对使用者无意义，默认应过滤掉。
5. ✗ 用户名固定 `__token__`，密码才是 token；否则 403。
6. ✗ PyPI 不允许覆盖同名文件，只能发新版本（或 yank 旧的）。
7. ✗ **先怀疑校验器**——本日第 1 条翻车就是校验器自己的正则错了，
   让所有合法产物都变红。

</details>

---

## 三、排障演练

给三个现象，说出「先查哪一步 / 哪个命令」：

| 现象 | 你的第一步 |
|---|---|
| `pip install` 报 `ModuleNotFoundError` | |
| `twine upload` 返回 403 | |
| 索引上的版本与 git tag 不一致 | |

<details><summary>参考答案</summary>

1. 先 `python3 -m zipfile -l dist/*.whl` 看包里到底有没有那个模块——
   多半是 `packages.find` 的 `where` 配错（src 布局常见）。
2. 检查 token：是不是设了 `DAY181_INDEX_TOKEN`、用户名是不是 `__token__`、
   token 的 scope 是否覆盖这个项目名。本日实验 6 实测过：假 token 就是 403。
3. 跑流水线第 2 步的比对（`tag 版本 vs pyproject version`），
   再确认 tag 打在了正确的提交上。

</details>

---

## 四、验收清单（做完打勾）

- [ ] `01 --self-test` 退出码 0，能背出「预发布低于正式版 + `+build` 不参与比较」
- [ ] `02 --self-test` 退出码 0，能解释「为什么 7 条提交跳过了 2 条」
- [ ] `03 --self-test` 退出码 0，说出「反向断言」（改错文件名版本要能被抓到）为什么必须有
- [ ] `04 --self-test` 退出码 0，并**用 `echo REAL_EXIT=$?` 确认过退出码**
      （不要用管道后的 `$?`，那是 grep 的）
- [ ] 亲手构建出过 wheel + sdist，并 `pip install` + `import` 成功一次
- [ ] 亲眼见过三种拦截：版本不一致 / 无 token / 摘要不符
- [ ] 知道本日哪些是**未实测**的（真实成功上传、隔离构建、CI、GPG 签名）
- [ ] 清理完成：`ls -d /tmp/day181-* 2>/dev/null` 无输出，`ss -ltnp` 无 181xx 端口

---

## 五、延伸（选做）

1. 给 `02` 加一条 `--commit-msg` 检查：模拟 `commit-msg` 钩子，
   非规范提交直接拒绝（退出码非 0），并想清楚为什么这一步放在**本地**比放在 CI 更省事。
2. 用 `setuptools_scm` 把版本改成单一数据源，然后**故意**让 tag 与包内版本
   不一致，看流水线第 2 步是否还能拦住（提示：这一改动会让该事故在结构上消失，
   请想清楚「变安全」和「少了一个检查」之间的差别）。
3. 把 `03` 的校验加一条「wheel 里必须包含 README 声明的 license 文件」，
   并先构造一个**缺文件**的 wheel 验证这条新检查真的会红。
