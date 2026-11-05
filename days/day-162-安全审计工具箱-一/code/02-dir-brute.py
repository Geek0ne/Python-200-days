"""进阶用法与避坑：目录爆破的判定逻辑（Day 162 — 安全审计工具箱）。

目录爆破最容易写成"状态码 200 就算存在"——那是错的。本文件把四件事讲透：

1. **软 404 基线**：先用随机路径测出"不存在时"的 (状态码, 长度)；
2. **状态码语义**：403/401 往往才是最有价值的发现；429 不是"不存在"；
3. **429 指数退避**：0.5 → 1 → 2 → 4（上限），并把"未完成"写进报告；
4. **urljoin 越界**：词条里出现绝对 URL 时会跳出授权范围，拼接后**必须复检**。

运行：
    python3 02-dir-brute.py              # 完整演示
    python3 02-dir-brute.py --self-test  # 输出 SELF-TEST OK

⚠️ 请求全部是只读 GET，只发往 127.0.0.1 的自建实验服务；
   词表是内置的 30 条公开文档化路径；默认限速 5 请求/秒。
"""

from __future__ import annotations

import argparse
import time

from audit_core import (
    DEFAULT_WORDS,
    AuthorizationError,
    LabHTTP,
    Scope,
    build_baseline,
    dir_brute,
    fetch,
)

BANNER = "=" * 70


def lab_scope(port: int) -> Scope:
    return Scope(networks=["127.0.0.1/32"], ports=[(port, port)],
                 http_bases=[f"http://127.0.0.1:{port}"], ticket="LAB-SELF-002")


def demo_baseline(port: int) -> None:
    print(BANNER)
    print("① 为什么必须先取软 404 基线")
    print(BANNER)
    base = f"http://127.0.0.1:{port}"
    sc = lab_scope(port)
    # 随机路径：如果服务器"对不存在的路径也返回 200"，就能立刻看出来
    for word in ("a7f3k2", "z9q1m4"):
        res = fetch(f"{base}/{word}")
        print(f"   GET /{word:<8} → {res.status} len={res.length}")
    baseline = build_baseline(base, sc, samples=3)
    print(f"\n   基线：status={baseline.status} length={baseline.length}")
    print(f"   样本：{[ (s['status'], s['length']) for s in baseline.samples ]}")
    print("\n   ★ 这个实验服务模拟了真实世界里极常见的错误配置：")
    print("     重写规则（SPA/伪静态）把所有未匹配路径都交给同一个页面 → 统统 200。")
    print("     只认 200 的脚本会在这里产出满屏假发现。")


def demo_classify(port: int) -> None:
    print("\n" + BANNER)
    print("② 状态码分类实测（内置词表）")
    print(BANNER)
    base = f"http://127.0.0.1:{port}"
    sc = lab_scope(port)
    entries, baseline, coverage = dir_brute(base, DEFAULT_WORDS, sc, rate=200.0)
    print(f"   基线 status={baseline.status} len={baseline.length}；"
          f"词条 {coverage['total']} 条，已完成 {coverage['completed']}，"
          f"被限速 {coverage['throttled']}")
    print(f"\n   {'路径':<22}{'状态':<6}{'分类':<14}{'长度':>6}  说明")
    for e in entries:
        note = "软 404 可疑" if e.soft_404_suspect else (e.redirect_to or "")
        print(f"   /{e.word:<21}{e.status:<6}{e.category:<14}{e.length:>6}  {note}")

    by_cat: dict[str, list[str]] = {}
    for e in entries:
        by_cat.setdefault(e.category, []).append(e.word)
    print("\n   分类统计：")
    for cat, words in sorted(by_cat.items()):
        print(f"     {cat:<14} {len(words):>2} 条：{', '.join(words[:5])}"
              f"{' …' if len(words) > 5 else ''}")
    print("\n   ★ 重点看 protected：403/401 说明『路径存在，只是当前身份没权限』。")
    print("     只认 200 的工具会把这些最有价值的入口全部漏掉。")


def demo_throttle(port: int) -> None:
    print("\n" + BANNER)
    print("③ 429 与指数退避（目标主动限速）")
    print(BANNER)
    base = f"http://127.0.0.1:{port}"
    sc = lab_scope(port)
    words = ["healthz"] * 8          # 同一个词条重复，只为把请求数打上去
    t0 = time.perf_counter()
    entries, _bl, coverage = dir_brute(base, words, sc, rate=200.0, max_backoff=0.5)
    elapsed = time.perf_counter() - t0
    statuses = [e.status for e in entries]
    print(f"   8 次请求：状态序列 {statuses}")
    print(f"   429 次数={coverage['throttled']} 退避事件={coverage['backoff_events']} "
          f"最大退避={coverage['max_backoff_s']}s 耗时={elapsed:.2f}s")
    print(f"   coverage.incomplete = {coverage['incomplete']}")
    print("\n   ★ 429 ≠ 不存在。它意味着『你问得太快』：")
    print("     - 正确动作：指数退避（0.5→1→2→4 上限），并把未完成写进报告；")
    print("     - 错误动作：继续猛冲（加剧压力）或把 429 记成 404（谎称『无发现』）；")
    print("     - 只要出现 429，本轮『未发现』的结论就不成立 → 退出码至少 4。")


def demo_scope_escape(port: int) -> None:
    print("\n" + BANNER)
    print("④ urljoin 越界：词条可以把你带到范围外")
    print(BANNER)
    import urllib.parse
    base = f"http://127.0.0.1:{port}"
    sc = lab_scope(port)
    for word in ("admin/", "//evil.example/x", "https://evil.example/y"):
        url = urllib.parse.urljoin(base.rstrip("/") + "/", word)
        try:
            sc.check_url(url)
            print(f"   ✅ {word:<26} → {url}（通过）")
        except AuthorizationError as exc:
            print(f"   ⛔ {word:<26} → {url}")
            print(f"      拒绝：{exc}")
    print("\n   ★ 字符串相加不会出现这个问题（拼出来是坏 URL，连不上），")
    print("     而 urljoin 会**正确地**拼出绝对 URL —— 于是一个来自词表的词条")
    print("     就能让你去请求完全无关的第三方主机。")
    print("     规则：任何由外部输入构造的目标，使用前必须重新过一遍范围门禁。")


def demo_scope_abort(port: int) -> None:
    print("\n" + BANNER)
    print("⑤ 整轮终止 vs 跳过：越界词条怎么处理")
    print(BANNER)
    base = f"http://127.0.0.1:{port}"
    sc = lab_scope(port)
    try:
        dir_brute(base, ["healthz", "//evil.example/x"], sc, rate=200.0)
        print("   ❌ 不应该走到这里")
    except AuthorizationError as exc:
        print(f"   ✅ 已整轮终止：{exc}")
    print("\n   为什么是终止而不是跳过？")
    print("     越界意味着『目标清单的来源不可信』（词表/配置可能被污染）。")
    print("     此时继续扫剩下的词条，等于在不可信输入上继续执行——")
    print("     正确做法是停下来检查输入来源，而不是悄悄少扫几条。")


def demo_tolerance(port: int) -> None:
    print("\n" + BANNER)
    print("⑥ 长度容差：为什么用『接近』而不是『相等』")
    print(BANNER)
    base = f"http://127.0.0.1:{port}"
    sc = lab_scope(port)
    baseline = build_baseline(base, sc)
    print(f"   基线 len={baseline.length}")
    for delta, label in ((0, "完全相同"), (20, "差 20 字节（时间戳/ID 噪声）"),
                         (60, "差 60 字节"), (200, "差 200 字节")):
        verdict = baseline.matches(baseline.status, baseline.length + delta)
        print(f"   {label:<28} → matches={verdict}")
    print("\n   容差公式（本课实现）：|len - baseline| ≤ max(32, 5% × baseline)")
    print("   ★ 容差太大 → 真实页面被误判成软 404（漏报）；")
    print("     容差太小 → 噪声页面被当成发现（误报）。")
    print("     所以实现里**同时保留** soft_404_suspect 与原始长度，供人工复核。")


def demo_ethics() -> None:
    print("\n" + BANNER)
    print("⑦ 目录爆破的伦理下限（三条硬规则）")
    print(BANNER)
    for i, rule in enumerate([
        "默认 5 请求/秒、串行（约等于人工浏览速度）；",
        "词表上限 30 条，全部是公开文档化的常见路径；",
        "出现 429 立刻退避并记录覆盖缺口，不硬冲。",
    ], 1):
        print(f"   {i}) {rule}")
    print("\n这些不是性能妥协，而是**授权边界的技术表达**：")
    print("『我被允许探测，但没有被允许压垮目标。』")


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 162 进阶用法：目录爆破")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    if args.self_test:
        return _self_test()

    with LabHTTP(port=args.port):
        demo_baseline(args.port)
        demo_classify(args.port)
        demo_scope_escape(args.port)
        demo_scope_abort(args.port)
        demo_tolerance(args.port)
    with LabHTTP(port=args.port, throttle_after=4):
        demo_throttle(args.port)
    demo_ethics()
    return 0


def _self_test() -> int:
    # ① 基线：软 404 服务器 → 随机路径 200，与真实页面可区分
    with LabHTTP(port=0) as lab:
        base = f"http://127.0.0.1:{lab.port}"
        sc = lab_scope(lab.port)
        baseline = build_baseline(base, sc)
        assert baseline.status == 200, baseline
        assert all(s["status"] == 200 for s in baseline.samples), baseline.samples

        # ② 分类正确性
        entries, _bl, cov = dir_brute(
            base, ["healthz", "admin", "admin/", "logs/", "portal", "phpinfo.php",
                   "legacy/app", "backup.zip"],
            sc, rate=500.0)
        got = {e.word: e for e in entries}
        assert got["healthz"].category == "accessible", got["healthz"]
        assert got["admin"].category == "redirect" and got["admin"].redirect_to == "/admin/", got["admin"]
        assert got["admin/"].category == "protected" and got["admin/"].status == 403, got["admin/"]
        assert got["logs/"].category == "protected" and got["logs/"].status == 401, got["logs/"]
        assert got["phpinfo.php"].category == "missing", got["phpinfo.php"]
        assert got["legacy/app"].category == "soft_404", got["legacy/app"]
        assert got["backup.zip"].category == "accessible", got["backup.zip"]
        assert cov["incomplete"] is False, cov
        assert cov["completed"] == 8, cov

        # ③ urljoin 越界必须被拦住，且整轮终止
        import urllib.parse
        escaped = urllib.parse.urljoin(base.rstrip("/") + "/", "//evil.example/x")
        assert escaped == "http://evil.example/x", escaped
        try:
            sc.check_url(escaped)
            raise AssertionError("越界 URL 必须被拒绝")
        except AuthorizationError:
            pass
        try:
            dir_brute(base, ["healthz", "//evil.example/x"], sc, rate=500.0)
            raise AssertionError("越界词条必须终止整轮")
        except AuthorizationError:
            pass

        # ④ 长度容差：噪声内视为软 404，超出则视为真实页面
        assert baseline.matches(200, baseline.length + 20) is True
        assert baseline.matches(200, baseline.length + 400) is False

    # ⑤ 429 指数退避与覆盖缺口
    with LabHTTP(port=0, throttle_after=2) as lab2:
        base2 = f"http://127.0.0.1:{lab2.port}"
        sc2 = lab_scope(lab2.port)
        t0 = time.perf_counter()
        entries2, _b2, cov2 = dir_brute(base2, ["healthz"] * 6, sc2,
                                        rate=500.0, max_backoff=0.4)
        elapsed = time.perf_counter() - t0
        assert cov2["throttled"] >= 1, (cov2, [e.status for e in entries2])
        assert cov2["incomplete"] is True
        assert cov2["max_backoff_s"] > 0
        # 至少发生了 throttled 次退避等待
        assert elapsed >= 0.4 * (cov2["backoff_events"] - 1) - 0.1, (elapsed, cov2)
        assert any(e.category == "throttled" for e in entries2)

    print("SELF-TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
