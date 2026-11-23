"""基础用法：范围校验 + 只读端口探测 + 审计留痕（Day 161 — 渗透测试框架）。

本文件只做三件事，都是框架的最小可用形态：

1. 把"授权范围"写成数据结构，并在**创建 socket 之前**校验目标；
2. 用 TCP connect 做只读探测，理解 open / closed / filtered 三态差异；
3. 每一步都写进审计日志，最后打印出来（过程证据）。

运行：
    python3 01-scan-engine.py              # 启动本机实验服务 → 扫描 → 打印审计日志
    python3 01-scan-engine.py --self-test  # 输出 SELF-TEST OK

安全说明：本文件**只**连接 127.0.0.1 的实验端口（8000-8099）。
越界目标（例如 10.0.0.5）会在 socket 创建前被 AuthorizationError 拦下。
"""

from __future__ import annotations

import argparse
import json

from pentest_core import (
    LAB_SERVICES,
    AuthorizationError,
    Framework,
    LabServer,
    Target,
    default_lab_scope,
    parse_host_spec,
    parse_port_spec,
    tcp_probe,
)

BANNER = "=" * 68


def demo_scope_model() -> None:
    """① 范围模型：把授权条款变成代码。"""
    print(BANNER)
    print("① 范围模型（Scope）—— 授权条款 → 数据结构")
    print(BANNER)
    scope = default_lab_scope()
    print(f"允许的网段 : {scope.networks}")
    print(f"允许的端口 : {scope.ports[0][0]}-{scope.ports[0][1]}")
    print(f"排除名单   : {scope.excluded or '（空）'}")
    print(f"授权单号   : {scope.ticket}")
    print(f"raw socket : {scope.allow_raw_sockets}（本课框架恒为 False）")

    cases = [
        Target("127.0.0.1", 8000),   # 在范围内
        Target("127.0.0.1", 22),     # 端口越界
        Target("10.0.0.5", 8000),    # 主机越界
    ]
    print("\n逐个校验：")
    for t in cases:
        try:
            scope.check(t)
            print(f"  ✅ {t.key:<20} 允许")
        except AuthorizationError as exc:
            print(f"  ⛔ {t.key:<20} 拒绝 —— {exc}")

    # 黑名单优先：把 127.0.0.1 加进排除名单，白名单里也照样拒绝
    scope.excluded = ["127.0.0.1/32"]
    print("\n黑名单优先演示（127.0.0.1 同时在白名单与排除名单里）：")
    try:
        scope.check(Target("127.0.0.1", 8000))
        print("  ❌ 不应该通过")
    except AuthorizationError as exc:
        print(f"  ✅ 仍然拒绝 —— {exc}")
    print("\n为什么黑名单优先？排除项通常对应『业务不能停』的机器，")
    print("多扫一台的收益 << 扫错一台的代价。")


def demo_target_building() -> None:
    """② 目标构造：表达式 → 去重后的 Target 列表。"""
    print("\n" + BANNER)
    print("② 目标构造 —— CIDR/端口表达式展开与去重")
    print(BANNER)
    print(f"parse_host_spec('127.0.0.0/30') = {parse_host_spec('127.0.0.0/30')}")
    print(f"parse_port_spec('8000,8080-8082') = {parse_port_spec('8000,8080-8082')}")

    fw = Framework(default_lab_scope())
    targets = fw.build_targets(
        ["127.0.0.1", "127.0.0.0/30", "127.0.0.1"],  # 故意重复，观察去重
        ["8000,8001", "8001-8002"],                   # 故意重叠
    )
    print(f"\n展开结果（已去重）共 {len(targets)} 个：")
    for t in targets:
        print(f"  - {t.key}")
    print("\n去重为什么重要：重复探测会在审计日志里产生多条同一端口的记录，")
    print("复核者无法区分『框架重试』和『三个人在扫』。")


def demo_three_states() -> None:
    """③ 三态语义：open / closed / filtered 必须分开统计。"""
    print("\n" + BANNER)
    print("③ 只读探测 —— open / closed / filtered 三态")
    print(BANNER)
    print("实验服务：8000=伪装 SSH，8080=伪装 HTTP（都在授权端口段内）")
    print("8001 上没有服务（→ closed）；8002 无服务（→ closed）；")
    print("要看到 filtered 需要中间设备静默丢包，这里用 0.001s 超时模拟不可达。")

    with LabServer({8000: LAB_SERVICES[8000], 8080: LAB_SERVICES[8080]}):
        fw = Framework(default_lab_scope(), timeout=0.3, workers=4, rate=100)
        targets = fw.build_targets(["127.0.0.1"], ["8000-8002"])
        fw.authorize(targets)          # ★ 门禁：全部通过才继续
        results = fw.probe_many(targets)

        print("\n探测结果：")
        print(f"  {'目标':<18}{'状态':<10}{'服务':<10}耗时(ms)")
        for r in results:
            print(f"  {r.target.key:<18}{r.state:<10}{r.service or '-':<10}{r.elapsed_ms}")

        stats = Framework.state_counts(results)
        conclusive = stats["open"] + stats["closed"]
        print(f"\n统计：open={stats['open']} closed={stats['closed']} "
              f"filtered={stats['filtered']} error={stats['error']}")
        print(f"可判定 {conclusive} 条；不可判定 {stats['filtered']} 条")
        print("\n⚠️ 关键：filtered 是『不可判定』，不是『关闭』。")
        print("把 filtered 当 closed 写进报告，会让客户以为『只有 1 个端口开放』，")
        print("而真相可能是『50 个端口被防火墙静默丢弃，本次无结论』。")

        print("\nopen 目标抓到的 banner（只读，未发送任何数据）：")
        for r in results:
            if r.state == "open":
                print(f"  {r.target.key} → service={r.service!r} banner={r.banner[:50]!r}")


def demo_exit_codes() -> None:
    """④ 退出码语义：不可信的结果不配当门禁依据。"""
    print("\n" + BANNER)
    print("④ 退出码语义")
    print(BANNER)
    table = [
        ("2", "用法/授权错误（越界、参数非法）", "不可执行，修范围重跑"),
        ("4", "结果不完整（存在 filtered/error）", "本轮无结论，需换路径复测"),
        ("3", "有 P0/P1 发现", "进入人工复核队列"),
        ("0", "干净完成", "归档"),
    ]
    for code, meaning, action in table:
        print(f"  {code}  {meaning:<34} → {action}")
    print("\n优先级：2 > 4 > 3 > 0。『越界』比『发现高危』更需要立即停下。")


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 161 基础用法：范围校验 + 只读探测")
    parser.add_argument("--self-test", action="store_true", help="跑自检并输出 SELF-TEST OK")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出探测结果")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    demo_scope_model()
    demo_target_building()
    demo_three_states()
    demo_exit_codes()

    if args.json:
        with LabServer({8000: LAB_SERVICES[8000]}):
            fw = Framework(default_lab_scope(), timeout=0.3)
            targets = fw.authorize(fw.build_targets(["127.0.0.1"], ["8000,8001"]))
            results = fw.probe_many(targets)
        print("\nJSON 输出：")
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))

    print("\n" + BANNER)
    print("审计日志（过程证据，报告只是结论）：")
    print(BANNER)
    with LabServer({8000: LAB_SERVICES[8000]}):
        fw = Framework(default_lab_scope(), timeout=0.3)
        try:
            fw.authorize(fw.build_targets(["127.0.0.1", "10.0.0.5"], ["8000"]))
        except AuthorizationError:
            pass
        else:
            fw.probe_many(fw.build_targets(["127.0.0.1"], ["8000"]))
    for entry in fw.audit.entries:
        print("  " + json.dumps(entry, ensure_ascii=False))
    print("\n注意最后两条：scope_check=denied + run_abort=exit=2。")
    print("越界时『拒绝』这件事本身也被记录了 —— 这才是可交付的过程证据。")
    return 0


def _self_test() -> int:
    """自检：不需要外部网络，全部在回环实验环境内完成。"""
    scope = default_lab_scope()
    assert scope.allows_port(8000) and not scope.allows_port(22)
    assert scope.allows_host("127.0.0.1") and not scope.allows_host("10.0.0.5")

    with LabServer({8000: LAB_SERVICES[8000]}):
        fw = Framework(scope, timeout=0.3, workers=4, rate=200)
        targets = fw.build_targets(["127.0.0.1", "127.0.0.1"], ["8000-8001"])
        assert len(targets) == 2, targets              # 去重生效
        fw.authorize(targets)
        results = fw.probe_many(targets)
        states = {r.target.key: r.state for r in results}
        assert states == {"127.0.0.1:8000": "open", "127.0.0.1:8001": "closed"}, states
        open_result = next(r for r in results if r.state == "open")
        assert open_result.service == "ssh", open_result
        assert "SSH-2.0" in open_result.banner

        # 越界：必须在 socket 创建前抛异常，并且留下 denied 审计记录
        bad = fw.build_targets(["10.0.0.5"], ["8000"])
        try:
            fw.authorize(bad)
            raise AssertionError("越界必须被拒绝")
        except AuthorizationError:
            pass
        assert any(e["result"] == "denied" for e in fw.audit.entries)
        assert any(e["event"] == "run_abort" for e in fw.audit.entries)

        # filtered 的可判定性与 exit_code 的关系
        from pentest_core import exit_code
        assert exit_code([], {"open": 1, "closed": 1, "filtered": 0, "error": 0}) == 0
        assert exit_code([], {"open": 1, "closed": 1, "filtered": 1, "error": 0}) == 4

        # 单目标探测函数也能直接用（注意：调用者必须自己保证已授权）
        r = tcp_probe(Target("127.0.0.1", 8001), timeout=0.3)
        assert r.state == "closed", r
    print("SELF-TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
