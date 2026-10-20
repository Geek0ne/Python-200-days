# Day 191 · 完成清单与练习

## 一、本机验收（按顺序执行，约 2 分钟）

```bash
cd days/day-191-crawler-engine-skeleton/code

# 1. 五个脚本全部离线自检，必须全 PASS
for f in 00-local-server.py 01-url-frontier.py 02-rate-limited-engine.py 03-retry-and-sink.py 04-pitfall-per-worker-sleep.py; do
  echo "== $f"; python3 "$f" --self-test || break
done

# 2. 起靶站（另开终端，或同一行用 & 后台）
python3 00-local-server.py --port 8099 & SRV=$!; sleep 1

# 3. 比对限速写法
python3 04-pitfall-per-worker-sleep.py --url http://127.0.0.1:8099 --rate 20 --workers 8 --pages 120

# 4. 看引擎偏差
python3 02-rate-limited-engine.py --url http://127.0.0.1:8099 --pages 120 --rate 20 --workers 8

# 5. BFS + robots
python3 01-url-frontier.py --crawl http://127.0.0.1:8099 --limit 40

# 6. 重试 + 幂等 + 续爬
rm -f /tmp/day191.sqlite*
python3 03-retry-and-sink.py --url http://127.0.0.1:8099 --pages 40 --db /tmp/day191.sqlite
python3 03-retry-and-sink.py --url http://127.0.0.1:8099 --pages 40 --db /tmp/day191.sqlite --resume

# 7. 查看落库结果
sqlite3 /tmp/day191.sqlite "select count(*) from pages; select count(*) from failures;"

# 8. 清理（必须做）
kill $SRV; rm -f /tmp/day191.sqlite*
```

**验收标准**

- [ ] 5 个 `--self-test` 全绿（6/6、11/11、4/4、12/12、4/4）
- [ ] 坑1 的 `achieved_rps` ≥ 目标 4 倍，正解偏差 < 3%
- [ ] BFS 的 `fetched` 等于 `--limit`（预算不泄漏）
- [ ] 续爬 `todo` 为 0，`rows_total` 不变
- [ ] `failures` 表为 0 行（靶站只在首次 503，重试可成功）
- [ ] 靶站进程已 kill，`lsof -i :8099` 无输出

## 二、基础练习

1. **补规范化规则**：让 `normalize` 额外处理
   - `http://example.com/a%2Fb`（编码后的斜杠，不应还原成路径分隔符）
   - 重复的 query 键 `?a=1&a=2`（保留顺序，不要排序后打乱语义）
   写进 `--self-test` 用例，跑通再提交。

2. **统计口径**：给 `CrawlEngine` 增加 `attempts` 指标（总请求次数，含重试），
   验证它恒等于 `ok + http_err + net_err`。若不等，说明哪个分支没记账？

3. **robots 缓存**：同一个域只拉一次 `/robots.txt`。
   在 `RobotsGate` 里加 `dict[host, RobotFileParser]`，
   并解释为什么不能按“完整 URL”缓存。

## 三、进阶练习

4. **两级限速**：为“列表页”和“详情页”各建一个令牌桶，
   列表 1 req/s、详情 5 req/s，共用 8 个 worker。
   跑 20 个列表页 + 每页 10 个详情，报告两个桶各自的 `waited`。
   提示：worker 取任务时要先知道“这是哪一类 URL”。

5. **预算与优先级**：给 `Frontier` 加优先级队列（`heapq`），
   高优先级 URL 先抓，但**同域仍受全局桶约束**。
   验证：插入 5 个高优先级 + 500 个低优先级，前 5 个请求是否是高优先级？

6. **崩溃恢复演练**：在 `03-retry-and-sink.py` 里加 `--crash-after N`，
   抓 N 条后 `os._exit(1)`。然后用 `--resume` 续跑，
   证明最终 `pages` 行数 = 全量 URL 数，且 `fetched_at` 不重复。

## 四、思考题（口述即可）

- 为什么 `list.pop(0)` 在大队列下会拖慢整个爬虫？给出复杂度。
- `capacity=rate` 为什么在长任务里几乎看不出来，在短任务里却翻倍？
- 如果目标站点返回 200 但正文是“请求过于频繁”，重试分类器该放在哪一层？
- 断点续爬用差集查询，在 500 万行时慢在哪？水位线方案会漏抓什么？
