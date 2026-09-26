# Day 167 — 文件监控（watchdog）· 完成清单与练习

> 建议顺序：先读完 `README.md`（尤其第 2、3、5 节），再跑 `code/` 下的 4 个文件，
> 最后做练习。**每个练习都要求"能解释为什么"，而不只是"跑通"。**

---

## ✅ 今日完成清单

### 一、环境与依赖

- [ ] 已确认 Python ≥ 3.9：`python3 -V`
- [ ] 已安装 watchdog：`pip install watchdog`
- [ ] 已验证版本：`python3 -c "import watchdog; print(watchdog.version.VERSION_STRING)"`
- [ ] 已确认后端可用：`python3 -c "from watchdog.observers import Observer; print(Observer)"`
      （Linux 打印 `InotifyObserver`，macOS 打印 `FSEventsObserver`，Windows 打印 `WindowsApiObserver`）

### 二、跑通示例代码（每项都要求先预测输出，再运行验证）

- [ ] `cd days/day-167-文件监控-watchdog/code`
- [ ] `python3 01-basic-watch.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 01-basic-watch.py --path ./sandbox --duration 8`
      在另一个终端 `touch ./sandbox/a.txt`，观察事件类型与字段
- [ ] `python3 02-pitfalls.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 02-pitfalls.py` → 6 个陷阱逐条复现并给出修法
- [ ] `python3 03-advanced-watch.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 03-advanced-watch.py --path ./sandbox --delay 0.5 --duration 10`
      → 连续快速写同一个文件，只看到**一次**业务动作（防抖生效）
- [ ] `python3 04-auto-classify.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 04-auto-classify.py --inbox ./sandbox/inbox --out ./sandbox/out \
      --duration 12 --dry-run` → 只打印、不动文件，`out/operations.jsonl` 出现 `dry_move`

### 三、动手改造（"读懂了"的唯一证明）

- [ ] 往 `inbox/` 丢一个 `a.txt.tmp`，确认**没有被分类**；再 `mv a.txt.tmp a.txt`，
      确认它被搬进 `docs/`（说明"忽略临时名"和"改名后重新识别"两条链路都通）
- [ ] 往 `inbox/` 丢两个同名文件（先后），确认第二个变成 `a-YYYYmmdd-HHMMSS.txt`，
      **第一个没有被覆盖**
- [ ] 把 `04-auto-classify.py` 的 `--workers` 从 2 改成 1 再改成 8，
      观察"一次丢 50 个文件"时的总耗时变化，写下一句结论
- [ ] 给 `04-auto-classify.py` 加一个 `--ext .log=logs` 命令行规则，
      让日志文件也能分桶（提示：解析 `KEY=VALUE` 后 insert 到 `RULES` 最前面）

### 四、概念自检（不看 README，口头或纸面回答）

- [ ] 我能说清 inotify / FSEvents / WindowsApiObserver 三者的能力差异
- [ ] 我能解释"轮询的延迟期望值 ≈ 间隔的一半"这个说法为什么是错的（提示：考虑轮询中修改）
- [ ] 我能画出"vim 保存一个文件"产生的 3~6 条事件序列
- [ ] 我能解释 handler 为什么要快、慢 handler 会引发什么（队列容量 16384）
- [ ] 我能解释 `recursive=True` 时新建目录为什么可能丢 created 事件
- [ ] 我能解释防抖（debounce）与节流（throttle）的区别，并各举一个适用场景
- [ ] 我能解释 `shutil.move` 与 `os.rename` 跨设备时的差异（EXDEV）
- [ ] 我能说出"为什么 stop() 之后必须 join()"，不 join 会发生什么

---

## 📝 基础练习题（1–3）

### 练习 1：最小可用的"新文件落盘播报器"

写一个脚本，监控给定目录（非递归），要求：

1. 只在**文件**创建/修改时输出 `[新文件] name (size bytes)`
2. 输出时**必须**带 `time.strftime("%H:%M:%S")` 前缀
3. 忽略隐藏文件（`.` 开头）和 `.tmp` 结尾的文件
4. 收到 Ctrl+C 后打印 `共收到 N 个事件` 并**干净退出**（进程真的结束，不是假死）

**验收标准**：`ps aux | grep 你的脚本名` 在退出后应该查不到残留进程。

<details>
<summary>💡 提示（先自己写，卡住了再看）</summary>

- 事件对象有 `.is_directory`、`.src_path`、`.event_type`。
- 文件大小用 `os.path.getsize(path)`，但要对 `FileNotFoundError` 兜底
  （事件到达时文件可能已被删）。
- 干净退出三件套：`observer.stop()` → `observer.join()` → `sys.exit(0)`。
</details>

---

### 练习 2：文件名非法字符检查器

写一个 handler，对每个新建文件检查文件名是否包含 `<>:"/\|?*` 或首尾空格，命中就打印
`⚠ 非法文件名: ...`。

思考并回答：**为什么这个检查放在 `on_created` 而不是 `on_any_event` 里更合适？**
（提示：考虑"写一个文件"过程中 modified 事件的数量）

<details>
<summary>💡 提示</summary>

`on_any_event` 会被 created/modified/moved/closed 同时触发，同一个坏名字会被报 3~5 次。
`on_created` 每个文件生命周期只来一次 —— 这就是"事件选择"本身就是一种去重。
</details>

---

### 练习 3：用 PollingObserver 复现"丢事件"

要求：

1. 用 `PollingObserver(timeout=2)` 监控目录
2. 在另一个终端**快速**创建再删除一个文件（存活 < 1 秒）
3. 观察：控制台**没有**任何输出
4. 改用默认 `Observer` 重跑一次，观察这次**有**输出

**写下结论**：轮询丢事件的根因是什么？生产上什么场景可以接受这种丢失？

---
