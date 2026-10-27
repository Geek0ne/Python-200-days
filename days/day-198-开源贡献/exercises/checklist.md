# Day 198 练习与验收清单 — 开源贡献

> 所有命令都可以直接复制执行。默认在 `days/day-198-开源贡献/code` 目录下运行。
> 实验需要写 `/tmp`，不需要 root，不需要网络（实验 5 需要联网克隆 CPython）。

## 今日完成清单

- [ ] 能说清 issue → PR → review → merge 的五个门禁
- [ ] 能解释 hunk 头四个数字的含义
- [ ] 能说出 `git am` 与 `git am -3` 的区别
- [ ] 跑通 `01-contribution-workflow.py --self-test`
- [ ] 跑通 `02-patch-doctor.py --self-test`
- [ ] 跑通 `03-contribution-kit.py --self-test`
- [ ] 亲手复现一次 `git am` 失败并修好
- [ ] 亲手解决一次冲突并 `am --continue`
- [ ] 用 `git diff --check` 抓到一次尾随空白
- [ ] 清理所有临时目录与文件

## 练习 1（基础）：读懂一个 hunk

给下面的 hunk 标出：旧文件起始行、旧文件行数、新文件起始行、新增/删除/上下文行。

```text
@@ -12,7 +12,8 @@ def parse(path):
     with open(path) as fh:
         lines = fh.readlines()
-    return [ln.strip() for ln in lines]
+    cleaned = [ln.strip() for ln in lines]
+    return [ln for ln in cleaned if ln]
 
 def main():
     pass
```

**自检命令**：

```bash
cat > /tmp/hunk.patch <<'PATCH'
--- a/demo.py
+++ b/demo.py
@@ -12,7 +12,8 @@ def parse(path):
     with open(path) as fh:
         lines = fh.readlines()
-    return [ln.strip() for ln in lines]
+    cleaned = [ln.strip() for ln in lines]
+    return [ln for ln in cleaned if ln]
 
 def main():
     pass
PATCH
python3 02-patch-doctor.py /tmp/hunk.patch
```

预期：0 error（若你的 hunk 头数字写错，会看到 error）。

## 练习 2（基础）：让一个 patch 失败，再让它成功

1. 建一个临时仓库，提交一行文本；
2. 复制仓库，在副本里改这一行并生成 patch；
3. 在原仓库里改同一 hunk 的另一行；
4. 用 `git am` 应用，观察失败；
5. 用 `git am -3` 应用，观察成功。

**验收标准**：你能指出失败信息里的文件名与行号，并解释为什么 `-3` 能成功。

## 练习 3（进阶）：制造并解决同一行冲突

重复实验 3，但解决方式换成「保留贡献者的措辞」，然后：

```bash
git add guide.rst
git am --continue
git log --oneline -2
```

**验收标准**：`git log` 里只有一个新提交，且提交信息仍是 patch 的 subject。

## 练习 4（进阶）：用体检器抓住三类问题

构造三个 patch，分别包含：

1. 尾随空白；
2. hunk 头行数 +1；
3. subject 超过 72 字符。

**验收标准**：

```bash
for p in /tmp/bad1.patch /tmp/bad2.patch /tmp/bad3.patch; do
  python3 02-patch-doctor.py "$p" || true
done
```

每个文件至少出现 1 条对应级别的提示；退出码分别为 1。

## 练习 5（挑战）：给你的真实仓库做一次「准 PR」

选一个你自己的小仓库（或本仓库的 `days` 目录），完成：

```bash
git switch -c demo-contribution
# 做一处最小改动（只改一个文件的一段）
git commit -am "gh-0001: fix something small"
python3 03-contribution-kit.py --repo . --commit HEAD --out /tmp/my-kit
cat /tmp/my-kit/pr-body.md
cat /tmp/my-kit/checklist.md
```

**验收标准**：

- `/tmp/my-kit` 下有 4 个文件；
- `pr-body.md` 含「摘要 / 关联 issue / 变更 / 测试计划」四段；
- `news-entry.rst` 的文件名符合 `时间戳.gh-issue-N.摘要.rst`；
- 体检器输出 `0 error(s)`。

## 综合验收

```bash
cd days/day-198-开源贡献/code
python3 01-contribution-workflow.py --self-test
python3 02-patch-doctor.py --self-test
python3 03-contribution-kit.py --self-test

# 用真实 patch 再验一次（若还没有，就先跑实验 1 生成）
python3 02-patch-doctor.py /tmp/oss-lab-a/fix-typo.patch
```

全部输出 `✅ self-test passed` 且体检器 `0 error(s)` 即通过。

## 清理

```bash
rm -rf /tmp/oss-lab* /tmp/cpython-lab /tmp/kit-out /tmp/my-kit
rm -f /tmp/*.patch /tmp/hunk.patch
ls -d /tmp/oss-lab* 2>/dev/null || echo "clean"
```
