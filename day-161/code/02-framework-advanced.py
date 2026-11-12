"""进阶用法与避坑：插件注册表 · 限速并发 · 阶段状态机 · 报告（Day 161）。

本文件是框架的"骨架长成"演示，四个进阶点：

1. **插件注册表**：检测项与编排器解耦；分层执行（事实层 → 推断层 → 结论层）；
2. **限速与并发**：实测令牌桶的 `throttle_wait_s`，看清 workers 与 rate 的分工；
3. **阶段状态机**：ok / skipped / failed 的传播规则，以及"静默失败"如何被禁止；
4. **报告**：Finding → 优先级 → JSON + Markdown。

运行：
    python3 02-framework-advanced.py              # 完整演示
    python3 02-framework-advanced.py --self-test  # 输出 SELF-TEST OK

⚠️ 依旧只操作回环实验环境（127.0.0.1:8000-8099），不含任何攻击载荷。
"""

from __future__ import annotations

import argparse
import json
import time

from pentest_core import (
    LAB_SERVICES,
    Finding,
    Framework,
    LabServer,
    Phase,
    PhaseResult,
    PluginContext,
    Target,
    build_report,
    default_lab_scope,
    render_markdown,
)

# ── 插件定义（按 priority 分层：事实 → 推断 → 结论） ───────────────────
# 约定：插件只能读 ctx，结果必须 return Finding 列表（不允许写回全局状态）。

PLUGIN_TITLES: dict[str, str] = {}


def register_plugins(fw: Framework) -> None:
    """把四个插件注册进框架实例（也可以在模块级用 @fw.plugin 装饰器）。"""

    @fw.plugin("banner_evidence", priority=20)          # 事实层
    def banner_evidence(ctx: PluginContext) -> list[Finding]:
        """记录 open 端口主动吐出的 banner。这是**事实**，不是漏洞。"""
        asset = ctx.asset
        if asset.state != "open" or not asset.banner:
            return []
        return [Finding(
            key="banner_evidence",
            title=f"服务问候语: {asset.banner[:40]!r}",
            severity="info", confidence="high",      # 事实：看到就是看到
            target=asset.target.key,
            evidence=f"service={asset.service} banner_len={len(asset.banner)}",
            detail={"banner": asset.banner},
        )]

    @fw.plugin("version_disclosure", priority=30)       # 推断层
    def version_disclosure(ctx: PluginContext) -> list[Finding]:
        """banner 里带版本号 → 版本泄露。**推断**：泄露不等于可利用。"""
        asset = ctx.asset
        if asset.state != "open":
            return []
        tokens = [t for t in asset.banner.replace("/", " ").split()
                  if any(ch.isdigit() for ch in t)]
        if not tokens:
            return []
        return [Finding(
            key="version_disclosure",
            title=f"版本信息泄露: {' '.join(tokens[:2])}",
            severity="low", confidence="high",
            target=asset.target.key,
            evidence=f"banner={asset.banner[:60]!r}",
        )]

    @fw.plugin("cleartext_protocol", priority=40)       # 结论层
    def cleartext_protocol(ctx: PluginContext) -> list[Finding]:
        """明文协议：telnet/ftp/http 在**同一网络**内等于凭据可被旁路嗅探。"""
        asset = ctx.asset
        if asset.state != "open":
            return []
        if asset.service in {"telnet", "ftp", "http", "pop3", "imap"}:
            return [Finding(
                key="cleartext_protocol",
                title=f"明文协议暴露: {asset.service}",
                severity="high", confidence="medium",   # 明确协议，但影响要看网络边界
                target=asset.target.key,
                evidence=f"service={asset.service} port={asset.target.port}",
            )]
        return []

    # 故意注册一个会抛异常的插件，用来演示框架的兜底
    @fw.plugin("broken_plugin", priority=99)
    def broken_plugin(ctx: PluginContext) -> list[Finding]:
        raise ZeroDivisionError("演示用：插件内部崩溃")


# ── 演示 1：插件注册表 ────────────────────────────────────────────────

def demo_registry(fw: Framework, results) -> list[Finding]:
    print("=" * 68)
    print("① 插件注册表 —— 检测项与编排器解耦")
    print("=" * 68)
    print(f"注册顺序即 priority 顺序：{fw.registry.names()}")
    for name, prio, _fn in fw.registry.ordered():
        print(f"  [{prio:>3}] {name}")
    print("\n分层理由：事实层(10-20) → 推断层(30) → 结论层(40+)。")
    print("如果结论层先跑，它可能会依赖推断层的输出，导致顺序敏感的 bug。")

    findings = fw.run_plugins(results)
    print(f"\n插件产出 {len(findings)} 条 Finding：")
    for f in findings:
        print(f"  {f.priority} {f.severity}/{f.confidence}  {f.key:<20} {f.target}  {f.title}")

    print("\n⚠️ 注意 broken_plugin（priority=99）：它崩溃了，但整轮没有中断。")
    print("   框架在 Registry 层统一包了 try/except，异常被写成审计记录：")
    failed = [e for e in fw.audit.entries if e["result"] == "failed"]
    for e in failed[-2:]:
        print("   " + json.dumps(e, ensure_ascii=False))
    print("   如果崩溃被静默吞掉，『插件没跑成』会被误读成『插件跑了但没发现问题』，")
    print("   而这两件事对复核者的含义完全相反。")
    return findings


def call_plugins_safely(fw: Framework, plugin_name: str, ctx: PluginContext) -> tuple[list[Finding], str]:
    """安全调用单个插件：返回 (findings, error)。**框架层该做的事**。"""
    fn = next(f for n, _p, f in fw.registry.ordered() if n == plugin_name)
    try:
        out = fn(ctx) or []
        fw.audit.record("plugin_end", ctx.asset.target.key, f"ok findings={len(out)}",
                        plugin=plugin_name)
        return out, ""
    except Exception as exc:  # noqa: BLE001 - 兜底必须宽
        fw.audit.record("plugin_end", ctx.asset.target.key, "failed", plugin=plugin_name,
                        error=f"{type(exc).__name__}: {exc}")
        return [], f"{type(exc).__name__}: {exc}"


def demo_plugin_failure(fw: Framework, results) -> None:
    asset = next(r for r in results if r.state == "open")
    ctx = PluginContext(framework=fw, asset=asset, assets=list(results))
    out, err = call_plugins_safely(fw, "broken_plugin", ctx)
    print(f"\n单独调用 broken_plugin → findings={out} error={err!r}")
    assert err and not out
    print("审计日志里的对应记录：")
    print("  " + json.dumps(fw.audit.entries[-1], ensure_ascii=False))
    print("\n为什么要单独提供 call_plugins_safely？")
    print("  框架内部（run_plugins）已经兜底；单独调用是为了：")
    print("  1) 在开发期让插件错误可见（不会被批量执行淹没）；")
    print("  2) 让你能选择『严格模式』：开发时崩溃即中止，交付时崩溃即降级。")


# ── 演示 2：限速与并发 ────────────────────────────────────────────────

def demo_rate_limit() -> None:
    print("\n" + "=" * 68)
    print("② 限速与并发 —— workers（背压）与 rate（礼貌）是两个参数")
    print("=" * 68)
    rows = []
    with LabServer({8000: LAB_SERVICES[8000]}):
        for workers, rate in ((8, 500), (2, 500), (8, 20)):
            fw = Framework(default_lab_scope(), timeout=0.2, workers=workers, rate=rate)
            targets = fw.authorize(fw.build_targets(["127.0.0.1"], ["8000-8019"]))
            t0 = time.perf_counter()
            fw.probe_many(targets)
            elapsed = time.perf_counter() - t0
            rows.append((workers, rate, elapsed, fw.bucket.waited_s))
    print(f"\n{'workers':>8}{'rate/s':>8}{'总耗时(s)':>12}{'限速等待(s)':>14}")
    for workers, rate, elapsed, waited in rows:
        print(f"{workers:>8}{rate:>8}{elapsed:>12.3f}{waited:>14.3f}")
    print("\n读表方式：")
    print("  workers=2 时耗时明显变长 → 并发不足（背压参数起作用）")
    print("  rate=20 时出现 throttle_wait_s → 令牌桶在主动限速")
    print("\n为什么要主动限速（不是性能问题）：")
    print("  1) 目标连接表被打满 = 事实上的拒绝服务边缘；")
    print("  2) IDS/WAF 会把你标记为攻击源，客户安全团队会叫停；")
    print("  3) 目标丢包会让结果充满 filtered，数据质量反而下降。")


# ── 演示 3：阶段状态机 ────────────────────────────────────────────────

def demo_phase_machine(fw: Framework, results) -> None:
    print("\n" + "=" * 68)
    print("③ 阶段状态机 —— ok / skipped / failed 的传播规则")
    print("=" * 68)

    def detect(framework: Framework, assets) -> PhaseResult:
        fw_ = framework
        fs = fw_.run_plugins(assets)
        return PhaseResult("detect", "ok", findings=fs)

    def exploit_placeholder(framework: Framework, assets) -> PhaseResult:
        """★ 本课的空实现：不产生任何网络行为 ★"""
        return PhaseResult("exploit", "skipped",
                           "本课不提供利用能力；仅输出人工验证清单",
                           findings=[Finding(
                               key="needs_manual_verification",
                               title="待人工在授权窗口内验证的点位",
                               severity="info", confidence="info",
                               target=a.target.key) for a in assets if a.state == "open"])

    def report_phase(framework: Framework, assets) -> PhaseResult:
        return PhaseResult("report", "ok")

    phases = [
        Phase("detect", detect, critical=True),
        Phase("exploit", exploit_placeholder, optional=True),
        Phase("report", report_phase),
    ]
    results_out, assets_out, findings = fw.run_phases(phases, list(results))
    for r in results_out:
        print(f"  {r.name:<10} {r.status:<9} findings={len(r.findings):<3} {r.reason}")

    print("\n现在演示『上游无资产』（模拟全部 filtered）：")
    empty_fw = Framework(default_lab_scope())
    empty_out, _, _ = empty_fw.run_phases(phases, [])
    for r in empty_out:
        print(f"  {r.name:<10} {r.status:<9} findings={len(r.findings):<3} {r.reason}")
    assert all(r.status == "skipped" for r in empty_out)
    print("\n★ 关键：从来没有产出资产的阶段，检测阶段必须 skipped，")
    print("  绝不能输出『检测完成，发现 0 个问题』——那是把『无结论』伪装成『没问题』。")

    print("\n关键阶段失败会终止整轮：")
    crash_fw = Framework(default_lab_scope())
    try:
        crash_fw.run_phases([Phase("detect", _crash, critical=True)], list(results))
        print("  ❌ 不应该走到这里")
    except RuntimeError as exc:
        print(f"  ✅ 已终止：{exc}")
        print("  审计日志：" + json.dumps(crash_fw.audit.entries[-1], ensure_ascii=False))


def _crash(framework: Framework, assets) -> PhaseResult:
    raise RuntimeError("演示用：关键阶段崩溃")


# ── 演示 4：报告 ──────────────────────────────────────────────────────

def demo_report(fw: Framework, results, findings) -> None:
    print("\n" + "=" * 68)
    print("④ 报告：Finding → 优先级 → JSON / Markdown")
    print("=" * 68)
    params = {"timeout_s": fw.timeout, "workers": fw.workers, "rate_per_s": fw.bucket.rate,
              "plugins": fw.registry.names()}
    report = build_report(fw.scope, results, [], findings, params, fw.audit)
    print("优先级公式：priority_score = (severity+1) × (confidence+1)")
    print("  ≥20 → P0 ；≥12 → P1 ；≥6 → P2 ；其余 → P3")
    for f in findings:
        s = ["info", "low", "medium", "high", "critical"].index(f.severity)
        c = ["info", "low", "medium", "high", "critical"].index(f.confidence)
        print(f"  ({s + 1}×{c + 1}={((s + 1) * (c + 1)):>2}) {f.priority}  {f.key}")

    print("\nJSON 关键字段（节选）：")
    print(json.dumps({k: report[k] for k in
                      ("coverage", "audit_events", "exit_code")},
                     ensure_ascii=False, indent=2))
    print("\nMarkdown 报告前 20 行：")
    for line in render_markdown(report).splitlines()[:20]:
        print("  " + line)
    print(f"\n退出码：{report['exit_code']}（4=有 filtered/error → 本轮无结论）")


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 161 进阶：插件 · 限速 · 阶段 · 报告")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()

    with LabServer({8000: LAB_SERVICES[8000], 8080: LAB_SERVICES[8080]}):
        fw = Framework(default_lab_scope(), timeout=0.3, workers=4, rate=100)
        register_plugins(fw)
        targets = fw.authorize(fw.build_targets(["127.0.0.1"], ["8000-8002", "8080"]))
        results = fw.probe_many(targets)
        findings = demo_registry(fw, results)
        demo_plugin_failure(fw, results)
    demo_rate_limit()
    demo_phase_machine(fw, results)
    demo_report(fw, results, findings)
    return 0


def _self_test() -> int:
    with LabServer({8000: LAB_SERVICES[8000], 8080: LAB_SERVICES[8080]}):
        fw = Framework(default_lab_scope(), timeout=0.3, workers=4, rate=200)
        register_plugins(fw)
        # 注册表有序且 priority 升序
        prios = [p for _n, p, _f in fw.registry.ordered()]
        assert prios == sorted(prios), prios
        assert "banner_evidence" in fw.registry.names()

        # 重名注册必须报错
        try:
            fw.registry.register("banner_evidence", lambda ctx: [])
            raise AssertionError("重名插件必须被拒绝")
        except ValueError:
            pass

        targets = fw.authorize(fw.build_targets(["127.0.0.1"], ["8000-8002", "8080"]))
        results = fw.probe_many(targets)
        findings = fw.run_plugins(results)

        keys = {f.key for f in findings}
        assert "banner_evidence" in keys, keys
        assert "version_disclosure" in keys, keys
        assert "cleartext_protocol" in keys, keys      # 8080 伪装成 http

        # 事实层 severity=info(0+1=1) × confidence=high(3+1=4) = 4 → P3（低优先级但不丢弃）
        banner_f = next(f for f in findings if f.key == "banner_evidence")
        assert (banner_f.severity, banner_f.confidence, banner_f.priority) == ("info", "high", "P3")

        # 插件崩溃被兜住并留痕
        asset = next(r for r in results if r.state == "open")
        ctx = PluginContext(framework=fw, asset=asset, assets=list(results))
        out, err = call_plugins_safely(fw, "broken_plugin", ctx)
        assert out == [] and err.startswith("ZeroDivisionError"), (out, err)
        assert fw.audit.entries[-1]["result"] == "failed"

        # 阶段状态机：空资产必须 skipped；关键阶段崩溃必须终止
        phases = [Phase("detect", lambda f, a: PhaseResult("detect", "ok"), critical=True)]
        out_states, _, _ = Framework(default_lab_scope()).run_phases(phases, [])
        assert out_states[0].status == "skipped"
        try:
            Framework(default_lab_scope()).run_phases(
                [Phase("detect", _crash, critical=True)], list(results))
            raise AssertionError("关键阶段崩溃必须抛错")
        except RuntimeError:
            pass

        # 报告可生成、退出码语义正确
        report = build_report(fw.scope, results, [], findings,
                              {"timeout_s": fw.timeout}, fw.audit)
        assert report["coverage"]["targets"] == 4
        # 8000/8080 open、8001/8002 closed → filtered=0；有 P1（cleartext_protocol）→ 3
        assert report["exit_code"] == 3, report["exit_code"]
        md = render_markdown(report)
        assert "覆盖与结论可信度" in md
    print("SELF-TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
