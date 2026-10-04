# Day 174 练习与验收清单 — CI/CD（GitHub Actions）

所有命令都在 `days/day-174-ci-cd-github-actions/` 目录下执行。

## 一、今日完成清单

- [ ] 能说清 CI 与 CD 的分界点，并用 `if: github.ref` 表达出来
- [ ] 手写一个含 `lint` / `test` / `package` 三级 `needs` 的 workflow
- [ ] 用矩阵跑通 2 个 Python 版本的测试，且设了 `fail-fast: false`
- [ ] 用本地 lint 脚本校验 workflow YAML（编辑器保存即报错）
- [ ] 用 `act` 在本机把 pipeline 跑绿（至少尝试一次并看懂失败原因）
- [ ] 实测出本机 pip 冷/热缓存的耗时差
- [ ] 跑通 CD 演练器，验证「新版不健康 → 自动回滚」

---

## 二、基础练习

### 练习 1：写一个最小 CI workflow

新建 `.github/workflows/ci.yml`：

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pytest
      - run: pytest -q
```

**验收**：

```bash
python3 code/01-workflow-lint.py .github/workflows/ci.yml
echo "退出码: $?"     # 必须是 0，且输出 0 issues
```

> ⚠️ 思考：为什么 `on: [push, pull_request]` 里的 `on` 不用加引号，
> 而 `on:` 有时会被 YAML 解析成布尔 `True`？用第 4 节实验验证一下。

### 练习 2：本地校验 YAML

```bash
# 好文件
python3 code/01-workflow-lint.py workflows/ci.yml        # 期望 0 issues

# 坏文件（先造一个）
cat > /tmp/bad.yml <<'EOF'
name: Bad
on: [push]
jobs:
  a:
    runs-on: nonexistent-runner
    steps:
      - uses: actions/checkout@v4
        run: echo hi        # uses 和 run 同时出现
  b:
    runs-on: ubuntu-latest
    needs: [a, ghost]       # ghost 不存在
    steps:
      - name: 空 step       # 既没 uses 也没 run
EOF
python3 code/01-workflow-lint.py /tmp/bad.yml
echo "退出码: $?"     # 必须是 1
```

**验收**：退出码为 1，且至少报出 4 个 error。

### 练习 3：拓扑排序与环检测

```bash
python3 code/02-pipeline-builder.py topo workflows/ci.yml
```

**期望输出**（本课最终版 ci.yml 的真实输出）：

```
执行顺序: lint -> test -> package
job test: 展开 2 个组合 -> [{'py': '3.11'}, {'py': '3.12'}]
```

再造一个成环的 workflow 验证报错：

```bash
cat > /tmp/cycle.yml <<'EOF'
name: Cycle
on: [push]
jobs:
  a: {runs-on: ubuntu-latest, needs: [b], steps: [{run: "echo a"}]}
  b: {runs-on: ubuntu-latest, needs: [a], steps: [{run: "echo b"}]}
EOF
python3 code/02-pipeline-builder.py topo /tmp/cycle.yml
echo "退出码: $?"     # 必须是 1，并打印「检测到环」
```

---

## 三、进阶挑战

### 挑战 4：跑通 act 本地流水线

**前置**：本机有 Docker。

```bash
# 安装 act（一次性）
curl -sL https://github.com/nektos/act/releases/download/v0.2.89/act_Linux_x86_64.tar.gz \
  | tar xz act && sudo mv act /usr/local/bin/act

# 准备一个可运行的仓库
mkdir -p /tmp/ci-lab/src /tmp/ci-lab/.github/workflows && cd /tmp/ci-lab
git init -q
touch src/__init__.py
cat > src/calc.py <<'EOF'
def add(a, b):
    return a + b
EOF
cat > src/test_calc.py <<'EOF'
from src.calc import add


def test_add():
    assert add(1, 2) == 3
EOF
printf 'pytest==8.3.4\n' > requirements.txt
cp ~/code/Learn-Python/days/day-174-ci-cd-github-actions/workflows/ci.yml .github/workflows/
cat > pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
[project]
name = "ci-lab"
version = "0.1.0"
requires-python = ">=3.11"
[tool.setuptools]
packages = ["src"]
EOF
git add -A && git -c user.email=a@b -c user.name=c commit -qm init
git branch -m main        # 注意：workflow 的 if 判的是 refs/heads/main

# 跑（第一次要拉镜像，约 2GB，请耐心）
act -P ubuntu-latest=catthehacker/ubuntu:act-latest push
```

**验收**：`lint` / `test-1` / `test-2` / `package` 四个 job 全部 `Job succeeded`。

**清理**：

```bash
docker ps -a --filter "name=act-" | awk '{print $1}' | xargs -r docker rm -f
rm -rf /tmp/ci-lab
```

### 挑战 5：实测 pip 缓存收益

```bash
cd /tmp/ci-lab
cp ~/code/Learn-Python/days/day-174-ci-cd-github-actions/workflows/cache-bench.yml .github/workflows/
git add -A && git -c user.email=a@b -c user.name=c commit -qm bench
act -P ubuntu-latest=catthehacker/ubuntu:act-latest workflow_dispatch 2>&1 \
  | grep -E "COLD_secs|WARM_secs|cache_size"
```

**本机实测参考值**（2026-10-05，8 个包的依赖树，冷/热各一次）：

```
COLD_secs=11.66
WARM_secs=7.45
cache_size=14M
```

> ⚠️ **测这个容易翻车**：如果两个 job 共用同一个 site-packages，
> 第二次装包时全是 `Requirement already satisfied`，下载量为 0，
> 测出来的「热」根本不是缓存的功劳。必须用两个**独立 venv** 才有意义。
> README 的「翻车实验二」记的就是这个。

### 挑战 6：验证 CD 回滚

```bash
cd ~/code/Learn-Python/days/day-174-ci-cd-github-actions
rm -rf /tmp/cd-pipeline

python3 code/03-cd-deploy-pipeline.py run            # 第一次：v1.0.1 上线
python3 code/03-cd-deploy-pipeline.py run            # 第二次：v1.0.2 上线
python3 code/03-cd-deploy-pipeline.py run --flaky    # 第三次：v1.0.3 不健康 → 回滚
cat /tmp/cd-pipeline/releases.json                   # 记录应仍只有两条
```

**期望**（真实输出）：

```
  ❌ deploy ❌ registry.local/app:v1.0.3 健康检查失败，已回滚到 registry.local/app:v1.0.2
结果: 发布失败并回滚  总耗时 0.039s
```

**验收**：`releases.json` 里 `v1.0.3` **不出现**——回滚意味着新版本从未进入可用列表。

**清理**：`rm -rf /tmp/cd-pipeline`

---

## 四、三个脚本的离线自证

不依赖 Docker、不依赖网络，全部在本目录跑：

```bash
python3 code/01-workflow-lint.py --self-test
python3 code/02-pipeline-builder.py --self-test
python3 code/03-cd-deploy-pipeline.py --self-test
```

**期望输出**：

```
✅ self-test 通过：好文件 0 error，坏文件捕获 4 个 error
✅ self-test 通过：环检测/拓扑/矩阵/生成 6 组断言全过
✅ self-test 通过：版本/发布/回滚/门禁 6 组断言全过
```

`03` 的 self-test 会在 `/tmp/cd-selftest` 建临时目录并自动清掉；
若异常中断残留，手动 `rm -rf /tmp/cd-selftest`。
