"""基础用法：端口扫描（只读 TCP connect + banner 与服务推断）（Day 162）。

本文件只讲一件事：**怎么正确地把"端口是不是开着"这件事测出来并写清楚**。

四个要点：
1. TCP connect 的**三态**：open / closed / filtered（filtered = 不可判定）；
2. 服务推断**两步走**：banner 优先（高置信），端口表兜底（低置信，必须标注）；
3. 范围门禁在**创建 socket 之前**（越界立即抛 AuthorizationError）；
4. 限速：连端口扫描也要限速（突发连接在真实网络里会被 IDS 标记）。

运行：
    python3 01-port-scan.py              # 启动本机实验服务 → 扫描 → 打印表格与统计
    python3 01-port-scan.py --self-test  # 输出 SELF-TEST OK

⚠️ 只扫描 127.0.0.1 的 8000-8099 实验端口段；越界目标会在校验层被拒绝。
"""

from __future__ import annotations

import argparse
import json
import socket
import threading

from audit_core import (
    AuthorizationError,
    LabHTTP,
    Scope,
    default_lab_scope,
    parse_host_spec,
    parse_port_spec,
    scan_port,
    scan_ports,
)

BANNER = "=" * 70


def demo_specs() -> None:
    print(BANNER)
    print("① 目标与端口表达式")
    print(BANNER)
    print(f"parse_host_spec('127.0.0.0/30') = {parse_host_spec('127.0.0.0/30')}")
    print(f"parse_port_spec('8000,8080-8082') = {parse_port_spec('8000,8080-8082')}")
    print("\n★ 域名会被拒绝（解析域名本身就是一次外发）：")
    try:
        parse_host_spec("example.com")
    except Exception as exc:  # noqa: BLE001
        print(f"   {type(exc).__name__}: {exc}")


def demo_gate(scope: Scope) -> None:
    print("\n" + BANNER)
    print("② 范围门禁：在校验层就拦住越界")
    print(BANNER)
    cases = [("127.0.0.1", 8080), ("127.0.0.1", 22), ("10.0.0.5", 8080)]
    for host, port in cases:
        try:
            scope.check_host_port(host, port)
            print(f"   ✅ {host}:{port:<6} 允许")
        except AuthorizationError as exc:
            print(f"   ⛔ {host}:{port:<6} 拒绝 —— {exc}")
    print("\n注意顺序：check → 才有资格创建 socket。包一旦发出，'拒绝'就只是本地标签。")


def demo_three_states(scope: Scope) -> None:
    print("\n" + BANNER)
    print("③ 三态实测（本机实验服务）")
    print(BANNER)
    with LabHTTP(port=8080) as lab:
        print(f"实验 HTTP 服务已启动在 127.0.0.1:{lab.port}")
        results = scan_ports(["127.0.0.1"], [8080, 8081, 8082], scope, timeout=0.5)
    print(f"\n   {'目标':<20}{'状态':<11}{'服务':<10}{'来源':<11}{'耗时(ms)':>9}")
    for r in results:
        print(f"   {r.key:<20}{r.state:<11}{r.service:<10}{r.service_source or '-':<11}"
              f"{r.elapsed_ms:>9}")
    stats = {s: sum(1 for r in results if r.state == s)
             for s in ("open", "closed", "filtered", "error")}
    print(f"\n   统计：{stats}")
    print("   ★ filtered 是『不可判定』，绝不能写成『关闭』。")
    print("     把 filtered 当 closed 会让报告谎称『只有 1 个端口开放』。")


def demo_service_source(scope: Scope) -> None:
    print("\n" + BANNER)
    print("④ 服务推断的两种来源（置信度不同）")
    print(BANNER)
    # A) 「主动问候」型服务：SSH 会先说话 → banner 优先，高置信
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)
    port = srv.getsockname()[1]

    def loop() -> None:
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            try:
                conn.sendall(b"SSH-2.0-OpenSSH_8.9p1 lab\r\n")
            except OSError:
                pass
            finally:
                conn.close()

    threading.Thread(target=loop, daemon=True).start()
    try:
        r_banner = scan_port("127.0.0.1", port, timeout=0.5)
    finally:
        srv.close()

    # B) 「请求先行」型服务：HTTP 不会主动说话 → 只能靠端口表，低置信
    with LabHTTP(port=8081) as lab:
        r_map = scan_port("127.0.0.1", lab.port, timeout=0.5)

    print(f"   A) 端口 {port}（主动问候）：service={r_banner.service!r} "
          f"source={r_banner.service_source!r} banner={r_banner.banner!r}")
    print(f"   B) 端口 {r_map.port}（请求先行）：service={r_map.service!r} "
          f"source={r_map.service_source!r}")
    print("\n   ★ 报告里必须带上 source：")
    print("     service_source=banner   → 「服务自报家门」，高置信")
    print("     service_source=port_map → 「端口号约定」，低置信（端口可以随意改）")


def demo_rate(scope: Scope) -> None:
    print("\n" + BANNER)
    print("⑤ 为什么端口扫描也要限速")
    print(BANNER)
    print("  限速参数：rate=50/s（教学环境），真实授权环境建议从 5/s 起步。")
    print("  理由：")
    print("    1) 目标连接表被打满 = 事实上的拒绝服务边缘；")
    print("    2) IDS/WAF 会把你标记为攻击源，客户安全团队会叫停；")
    print("    3) 目标丢包会让结果充满 filtered，数据质量反而下降。")
    print("  限速由客户许可决定，不由『我能多快』决定。")


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 162 基础用法：端口扫描")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()

    scope = default_lab_scope()
    demo_specs()
    demo_gate(scope)
    demo_three_states(scope)
    demo_service_source(scope)
    demo_rate(scope)

    if args.json:
        with LabHTTP(port=8082) as lab:
            results = scan_ports(["127.0.0.1"], [lab.port, lab.port + 1], scope, timeout=0.5)
        print("\nJSON 输出：")
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    return 0


def _self_test() -> int:
    scope = default_lab_scope()

    # 范围：端口与主机都要卡住
    assert scope.allows_port(8080) and not scope.allows_port(22)
    assert scope.allows_host("127.0.0.1") and not scope.allows_host("10.0.0.5")
    try:
        scope.check_host_port("127.0.0.1", 22)
        raise AssertionError("越界端口必须被拒绝")
    except AuthorizationError:
        pass

    with LabHTTP(port=8080) as lab:
        assert lab.port == 8080
        results = scan_ports(["127.0.0.1"], [8080, 8081], scope, timeout=0.5)
        states = {r.port: r.state for r in results}
        assert states[8080] == "open", states
        assert states[8081] == "closed", states
        # HTTP 请求先行 → 只能靠端口表（低置信）
        assert results[0].service_source == "port_map", results[0]

    # banner 优先
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)
    port = srv.getsockname()[1]

    def loop() -> None:
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            try:
                conn.sendall(b"SSH-2.0-lab\r\n")
            except OSError:
                pass
            finally:
                conn.close()

    threading.Thread(target=loop, daemon=True).start()
    try:
        r = scan_port("127.0.0.1", port, timeout=0.5)
        assert r.state == "open" and r.service == "ssh" and r.service_source == "banner", r
    finally:
        srv.close()

    # 关闭端口：closed（主机存活），不是 error
    r_closed = scan_port("127.0.0.1", 8081, timeout=0.5)
    assert r_closed.state == "closed", r_closed

    # timeout 参数真的生效（不可达的文档网段地址）
    import time
    t0 = time.perf_counter()
    r_far = scan_port("192.0.2.1", 8080, timeout=0.3, retries=0)
    assert time.perf_counter() - t0 < 2.0
    assert r_far.state in ("filtered", "error"), r_far

    print("SELF-TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
