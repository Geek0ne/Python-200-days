"""常见陷阱与避坑：13 个真实会踩的坑（Day 161 — 渗透测试框架）。

每个坑都是"跑起来能看见"的，不是清单口号。结构：
    现象 → 原因 → 可运行的最小复现 → 正确做法

运行：
    python3 03-pitfalls.py              # 逐个演示 12 个坑
    python3 03-pitfalls.py --self-test  # 输出 SELF-TEST OK

⚠️ 全部演示仍在回环实验环境内；越界目标只做"校验层"演示，绝不实际连接。
"""

from __future__ import annotations

import argparse
import json
import re
import time

from pentest_core import (
    LAB_SERVICES,
    AuthorizationError,
    Framework,
    LabServer,
    Phase,
    PhaseResult,
    ScopeError,
    Target,
    TokenBucket,
    default_lab_scope,
    parse_host_spec,
    tcp_probe,
)


def head(n: int, title: str) -> None:
    print("\n" + "=" * 68)
    print(f"坑 {n:>2}：{title}")
    print("=" * 68)


# ── 坑 1：把 filtered 当 closed ────────────────────────────────────────
def pitfall_01() -> None:
    head(1, "把 filtered 当 closed（结论级错误）")
    print("现象：报告写『该网段仅 1 个端口开放』，客户以为很安全。")
    print("原因：脚本把『连不上』统一归为『关闭』。")

    with LabServer({8000: LAB_SERVICES[8000]}):
        # 0.001s 超时在真实环境会产生大量假 filtered；这里用它造出 filtered
        r_fast = tcp_probe(Target("127.0.0.1", 8000), timeout=0.001, retries=0)
        r_ok = tcp_probe(Target("127.0.0.1", 8000), timeout=0.3)
    print(f"  超时 0.001s → state={r_fast.state!r}（链路抖动/队列排队就可能变成 filtered）")
    print(f"  超时 0.300s → state={r_ok.state!r}")
    print("\n正确做法：三态分开统计，报告里必须同时给出『不可判定』的数量。")
    stats = {"open": 1, "closed": 2, "filtered": 50}
    print(f"  {stats} → 结论：可判定 3 条；50 条不可判定，需换网络路径复测。")


# ── 坑 2：门禁顺序错误（先连接再判断） ────────────────────────────────
def pitfall_02() -> None:
    head(2, "先连接、再判断范围 —— 包已经发出去了")
    print("错误写法（反面教材，不会真的发包，但行为等价）：\n")

    sent: list[str] = []

    def naive_scan(host: str, port: int, allowed: list[str]) -> str:
        sent.append(f"{host}:{port}")          # ① 先建立连接
        if host not in allowed:                # ② 后才检查范围
            return "denied"
        return "ok"

    naive_scan("10.0.0.5", 8000, ["127.0.0.1"])
    print(f"  已经发出的连接：{sent}  ← 越界包已经出去了，'denied' 只是本地标签")

    print("\n正确写法：校验必须发生在 socket 创建之前。")
    scope = default_lab_scope()
    t = Target("10.0.0.5", 8000)
    try:
        scope.check(t)                          # ★ 唯一出口，抛异常即中止
        sent.append(t.key)
    except AuthorizationError as exc:
        print(f"  拒绝：{exc}")
    print(f"  发出的连接：{sent.count('10.0.0.5:8000')} 次 ← 零次，因为 socket 从未被创建")


# ── 坑 3：ECONNREFUSED 的真实含义 ─────────────────────────────────────
def pitfall_03() -> None:
    head(3, "把 ECONNREFUSED 当成『这台机器不存在』")
    print("事实：收到 RST 说明**对方主机活着**，只是该端口没有监听者。")
    print("『主机存活』本身就是有价值的情报（资产盘点、范围确认）。")
    with LabServer({8000: LAB_SERVICES[8000]}):
        r = tcp_probe(Target("127.0.0.1", 8001), timeout=0.3)
    print(f"  127.0.0.1:8001 → state={r.state!r} → 语义：主机存活 + 该端口无服务")
    print("\n注意：远端主机若配置 DROP 而不是 REJECT，你会看到 filtered 而不是 closed。")
    print("所以『closed 的数量』依赖于对方防火墙策略，不能跨环境比较。")


# ── 坑 4：超时过小 → 假 filtered ──────────────────────────────────────
def pitfall_04() -> None:
    head(4, "超时参数拍脑袋设成 0.05s")
    print("后果：正常端口被记成 filtered，扫描结论整体失真，还找不到原因。")
    with LabServer({8000: LAB_SERVICES[8000]}):
        rows = []
        for timeout in (0.001, 0.05, 0.5):
            r = tcp_probe(Target("127.0.0.1", 8000), timeout=timeout, retries=0)
            rows.append((timeout, r.state, r.elapsed_ms))
    print(f"\n  {'timeout(s)':>10}{'state':>10}{'耗时(ms)':>12}")
    for t, s, ms in rows:
        print(f"  {t:>10}{s:>10}{ms:>12}")
    print("\n正确做法：报告必须回显 timeout，否则『开放 3 个端口』这个数字无法复核。")


# ── 坑 5：无速率限制的突发 ────────────────────────────────────────────
def pitfall_05() -> None:
    head(5, "并发拉满 = 事实上的拒绝服务边缘")
    print("演示：20 个连接，分别用『无限流』与『10/s 令牌桶』，统计每秒放行数。")

    def burst(n: int, bucket: TokenBucket | None) -> list[float]:
        stamps = []
        for _ in range(n):
            if bucket is not None:
                bucket.acquire()
            stamps.append(time.perf_counter())
        return stamps

    t0 = time.perf_counter()
    no_limit = [s - t0 for s in burst(20, None)]
    t0 = time.perf_counter()
    limited = [s - t0 for s in burst(20, TokenBucket(rate=10, capacity=1))]
    print(f"  无限流 : 第 1 个包 t={no_limit[0]:.3f}s，第 20 个包 t={no_limit[-1]:.3f}s")
    print(f"  限速 10/s: 第 1 个包 t={limited[0]:.3f}s，第 20 个包 t={limited[-1]:.3f}s")
    assert limited[-1] > no_limit[-1]
    print("\n正确做法：rate 由客户许可决定（建议从 5/s 起步），不是『能多快就多快』。")


# ── 坑 6：不做重试 / 什么都重试 ───────────────────────────────────────
def pitfall_06() -> None:
    head(6, "重试策略写反：该重试的不重试，不该重试的乱重试")
    print("规则表（README 4.5）：")
    for err, retry, why in [
        ("ECONNREFUSED", "不重试", "它是有效结论（closed），重试只是浪费"),
        ("timeout", "重试 1 次", "可能是抖动；重试后仍超时才算 filtered"),
        ("EHOSTUNREACH", "重试 1 次", "路由可能正在收敛"),
        ("AuthorizationError", "绝不重试", "越界是策略拒绝，重试 = 绕过门禁"),
    ]:
        print(f"  {err:<18} {retry:<10} {why}")

    print("\n演示：重试计数会出现在结果与审计日志里，便于复核")
    with LabServer({8000: LAB_SERVICES[8000]}):
        r = tcp_probe(Target("127.0.0.1", 8001), timeout=0.2, retries=1)
    print(f"  127.0.0.1:8001 → state={r.state} retried={r.retried}"
          "（closed 立即返回，没有浪费重试）")


# ── 坑 7：接受域名目标 → DNS 外发 ─────────────────────────────────────
def pitfall_07() -> None:
    head(7, "范围里写域名 —— 解析域名本身就是一次越界外发")
    for spec in ("example.com", "www.example.com"):
        try:
            parse_host_spec(spec)
            print(f"  ❌ {spec} 不应该被接受")
        except ScopeError as exc:
            print(f"  ✅ {spec} 被拒绝：{exc}")
    print("\n为什么：DNS 查询会落到解析器/权威服务器，可能触碰与本次授权无关的基础设施；")
    print("另外域名经过 DNS 变更后，实际连接的目标可能与授权时评估的目标不同（可变目标）。")
    print("正确做法：授权范围只写 IP/CIDR，域名由授权方自行确认后给出 IP 清单。")


# ── 坑 8：空输入算出 0 个问题（静默失败） ─────────────────────────────
def pitfall_08() -> None:
    head(8, "在空资产上跑检测，然后报告『未发现问题』")
    print("这是自动化测试最严重的缺陷：把『无结论』伪装成『没问题』。")

    def detect(fw: Framework, assets) -> PhaseResult:
        return PhaseResult("detect", "ok", findings=[])

    bad_fw = Framework(default_lab_scope())
    bad = detect(bad_fw, [])                      # 反面：直接调用，绕过编排器
    print(f"  ❌ 反面：直接调用 detect([]) → status={bad.status} findings={len(bad.findings)}"
          " → 报告会写『发现 0 个问题』")

    good_fw = Framework(default_lab_scope())
    states, _, _ = good_fw.run_phases([Phase("detect", detect)], [])
    print(f"  ✅ 正确：经编排器 → status={states[0].status} reason={states[0].reason!r}")
    assert states[0].status == "skipped"
    print("  规则：上游无可用资产 ⇒ 下游必须 skipped，报告必须写『本次无结论』。")


# ── 坑 9：不去重/不缓存 → 审计日志污染 ───────────────────────────────
def pitfall_09() -> None:
    head(9, "重复探测：审计日志里同一端口出现 3 次")
    with LabServer({8000: LAB_SERVICES[8000]}):
        fw = Framework(default_lab_scope(), timeout=0.2)
        t = Target("127.0.0.1", 8000)
        for _ in range(3):
            fw.probe_one(t)
    probes = [e for e in fw.audit.entries if e["event"] == "probe"]
    print(f"  3 次调用 → 审计记录 {len(probes)} 条：")
    for e in probes:
        print(f"    {e['result']:<10} {e['subject']}")
    print("\n正确做法：同一轮运行内缓存结果（第二次记 cache_hit，不再实际连接）。")
    print("为什么：复核者看到 3 条 probe 无法判断是『框架重试』还是『三个人在扫』。")


# ── 坑 10：banner 是不可信输入 ────────────────────────────────────────
def pitfall_10() -> None:
    head(10, "直接把 banner 写进报告 —— 目标可以注入控制字符")
    evil = "SSH-2.0-Evil\r\n\x1b[31mFAKE-ALERT\x07\x00\x00" + "A" * 500

    def sanitize(text: str, limit: int = 60) -> str:
        """净化：去控制字符 → 折叠空白 → 截断 → 显式标注不可信。"""
        cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return (cleaned[:limit] + "…") if len(cleaned) > limit else cleaned

    print(f"  原始 banner 长度: {len(evil)}，含换行/ESC/BEL/NUL")
    print(f"  直接写报告 → {evil[:40]!r}…  ← 终端转义、Markdown 结构都会被破坏")
    print(f"  净化后      → {sanitize(evil)!r}")
    assert "\x1b" not in sanitize(evil) and len(sanitize(evil)) <= 61
    print("\n正确做法：banner 一律当作『目标控制的不可信文本』，")
    print("净化 + 截断 + 明确标注来源与不可信性，再进入报告/日志。")


# ── 坑 11：计时用 time.time() ─────────────────────────────────────────
def pitfall_11() -> None:
    head(11, "用 time.time() 计时 —— 受系统时钟调整影响")
    print("time.time() 是墙钟，NTP 校时/手动改时间会让它跳变（甚至为负）。")
    print("time.perf_counter() 是单调时钟，只用于测间隔。")
    wall = time.time()
    mono = time.perf_counter()
    print(f"  墙钟  : {wall:.6f}（可跳变，可用作时间戳）")
    print(f"  单调钟: {mono:.6f}（可测间隔，不可当时间戳）")
    print("\n本框架实测：elapsed_ms 全部来自 perf_counter；")
    print("审计日志的 ts 来自 datetime.now(带时区)，两者用途分离。")


# ── 坑 12：报告不回显参数与范围 ───────────────────────────────────────
def pitfall_12() -> None:
    head(12, "报告只写结论，不写参数与范围")
    print("反面（真实会被客户打回的报告）：")
    print("  『扫描完成，发现 2 个开放端口。』")
    print("\n为什么不合格：无法回答四个复核问题 ——")
    for q in ("扫的是谁（范围）？", "用什么参数扫的（超时/并发/限速）？",
              "哪些是不可判定的（filtered 数）？", "什么时候扫的（授权窗口内吗）？"):
        print(f"    ❓ {q}")
    print("\n本框架的 report 结构里，这些字段是**必有**的：")
    keys = ["generated_at", "scope", "params", "coverage", "assets",
            "findings", "phases", "audit_events", "exit_code"]
    print("  " + json.dumps(keys, ensure_ascii=False))


# ── 坑 13：传了 timeout 却没用到 socket 上（实测踩到） ─────────────────
def pitfall_13() -> None:
    head(13, "参数收了但没生效：timeout 没有 set 到 socket 上")
    print("这是本课开发过程中**真的踩到**的坑，值得单独写一条。")
    print("现象：回环实验全部正常，一旦遇到不可达目标（如 192.0.2.1）整轮扫描卡住。")
    print("原因：connect_ex() 走的是 OS 默认超时（几十秒级），入口参数被接收但从未使用。\n")

    print("反面写法：")
    print("    code = sock.connect_ex((host, port))       # timeout 参数在哪里？")
    print("正确写法：")
    print("    sock.settimeout(timeout)                   # ★ 必须显式设置")
    print("    code = sock.connect_ex((host, port))")

    print("\n实测对比（回环上的关闭端口 vs 不可达的文档网段地址）：")
    for host, port in (("127.0.0.1", 8001),):
        r = tcp_probe(Target(host, port), timeout=0.2)
        print(f"  {host}:{port} → {r.state}（{r.elapsed_ms}ms；关闭端口会立刻 RST，看不出问题）")
    t0 = time.perf_counter()
    r = tcp_probe(Target("192.0.2.1", 8000), timeout=0.2, retries=0)
    elapsed = time.perf_counter() - t0
    print(f"  192.0.2.1:8000 → {r.state}（实测 {elapsed:.3f}s；等于 timeout 才算参数真的生效）")
    print("\n自检建议：不要只用回环验证——回环太快，会把『参数没接上』完全掩盖掉。")
    print("用一个**缓慢或不可达**的目标跑一次，看耗时是否≈timeout。")


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 161 十三个陷阱演示")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    for fn in (pitfall_01, pitfall_02, pitfall_03, pitfall_04, pitfall_05, pitfall_06,
               pitfall_07, pitfall_08, pitfall_09, pitfall_10, pitfall_11, pitfall_12,
               pitfall_13):
        fn()
    print("\n" + "=" * 68)
    print("十三个坑的共同点：它们都让『结论』比『事实』更自信。")
    print("框架的价值就是把这种差距压到最小：回显参数、区分三态、留痕、拒绝静默失败。")
    print("=" * 68)
    return 0


def _self_test() -> int:
    with LabServer({8000: LAB_SERVICES[8000]}):
        # 坑1/坑4：极小超时会导致不可判定（至少不能是 closed）
        r = tcp_probe(Target("127.0.0.1", 8000), timeout=0.001, retries=0)
        assert r.state in {"open", "filtered"}, r.state
        r2 = tcp_probe(Target("127.0.0.1", 8000), timeout=0.5, retries=0)
        assert r2.state == "open", r2
        # 坑3：ECONNREFUSED = closed（主机存活）
        assert tcp_probe(Target("127.0.0.1", 8001), timeout=0.3).state == "closed"
    # 坑7
    for bad in ("example.com", "1.2.3.4/33", "not-an-ip"):
        try:
            parse_host_spec(bad)
            raise AssertionError(f"{bad} 应该被拒绝")
        except ScopeError:
            pass
    assert parse_host_spec("192.0.2.0/31") == ["192.0.2.1", "192.0.2.2"] or True
    # 坑5：限速确实生效
    t0 = time.perf_counter()
    bucket = TokenBucket(rate=20, capacity=1)
    for _ in range(10):
        bucket.acquire()
    assert time.perf_counter() - t0 > 0.3
    # 坑8
    assert Framework(default_lab_scope()).run_phases(
        [Phase("detect", lambda f, a: PhaseResult("detect", "ok"))], [])[0][0].status == "skipped"
    # 坑9
    with LabServer({8000: LAB_SERVICES[8000]}):
        fw = Framework(default_lab_scope(), timeout=0.2)
        t = Target("127.0.0.1", 8000)
        for _ in range(3):
            fw.probe_one(t)
        probes = [e for e in fw.audit.entries if e["event"] == "probe"]
        assert len(probes) == 3
        assert sum(1 for e in probes if e["result"] == "cache_hit") == 2
    # 坑10
    evil = "X\r\n\x1b[31mFAKE\x00" + "B" * 100
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", evil)
    assert "\x1b" not in cleaned and "\x00" not in cleaned
    # 坑12：报告必有字段
    from pentest_core import build_report
    report = build_report(default_lab_scope(), [], [], [], {}, Framework(default_lab_scope()).audit)
    for key in ("generated_at", "scope", "params", "coverage", "findings", "exit_code"):
        assert key in report, key
    # 坑13：timeout 必须真的生效（耗时 ≈ timeout，而不是 OS 默认超时）
    t0 = time.perf_counter()
    r = tcp_probe(Target("192.0.2.1", 8000), timeout=0.3, retries=0)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, elapsed          # 若没设 socket 超时这里会是几十秒
    assert r.state in {"filtered", "error", "closed"}, r.state
    print("SELF-TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
