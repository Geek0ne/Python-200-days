"""基础用法：规则引擎的最小可用示例（Day 159 — 安全审计工具）。

本文件演示四件事：
1. 规则的五要素：id / 严重度 / 置信度 / 为什么 / 怎么修
2. 引擎的真面目：**逐行正则 + 文件级 glob 过滤**，没有魔法
3. 命中值在进入结果对象之前就被掩码，明文从不进入结果
4. triage 分值 = (severity + 1) × (confidence + 1)，用来排优先级

运行方式（不需要任何第三方库）：
    python3 01-scanner-core.py              # 扫描内存样本并打印表
    python3 01-scanner-core.py --self-test  # 自测，输出 SELF-TEST OK

样本中的凭据全部是公开示例值或占位符，不可用于任何真实系统。
"""

import argparse

from audit_core import (
    fingerprint,
    inspect_text,
    local_rules,
    mask,
    priority,
    triage_band,
)

# ── 内存样本 ─────────────────────────────────────────────────────────────
# 为什么用内存样本？因为基础示例要能"零副作用"地解释引擎行为：
# 不碰磁盘、不依赖环境、failing test 也能一眼看出是哪条规则的问题。
SAMPLES = {
    "app/settings.py": """# 演示配置：所有值均为占位符
DEBUG = True
DB_PASSWORD = "ChangeMe-Demo-123"
TLS_VERIFY = False
requests.get(url, verify=False)
subprocess.run(cmd, shell=True)
ALLOWED_HOSTS = ["demo.local"]
""",
    "deploy/pip.conf": """[global]
index-url = http://pypi.demo.local/simple
trusted-host = pypi.demo.local
""",
    "requirements.txt": """requests
flask==3.0.0
""",
    "deploy/chmod.sh": """#!/bin/sh
chmod 777 /srv/app/uploads
""",
    "app/legacy_client.py": """API_KEY = "AKIAIOSFODNN7EXAMPLE"   # AWS 官方文档示例值
TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vIn0.abcdefghijklmnop"
""",
    "app/plugin_loader.py": """def load(expr):
    return eval(expr)   # 低置信度命中：是否危险取决于 expr 是否可控
""",
    "docs/README.md": """团队文档：配置项 password = "example-value" 只用于本地演示，
请不要在真实环境使用 MD5 做口令哈希。
""",
}


def build_and_scan():
    """对内存样本跑一遍引擎，返回 (findings, suppressed)。"""
    rules = local_rules()
    findings, suppressed = [], []
    for name, text in SAMPLES.items():
        hits, muted = inspect_text(name, text, rules)
        findings.extend(hits)
        suppressed.extend(muted)
    findings.sort(key=lambda f: (-priority(f.severity, f.confidence), f.path, f.line))
    return findings, suppressed


def render(findings) -> str:
    """把命中渲染成对齐的文本表（报告生成的极简版本）。"""
    header = f"{'PRI':>3} {'BAND':<4} {'SEVERITY':<8} {'CONF':<6} {'RULE':<28} {'LOCATION':<24} EVIDENCE"
    lines = [header, "-" * len(header)]
    for f in findings:
        location = f"{f.path}:{f.line}"
        lines.append(
            f"{priority(f.severity, f.confidence):>3} {f.band:<4} {f.severity:<8} "
            f"{f.confidence:<6} {f.rule_id:<28} {location:<24} {f.masked}"
        )
    return "\n".join(lines)


def self_test() -> None:
    findings, suppressed = build_and_scan()
    rows = {f.rule_id: f for f in findings}

    # 1) 关键规则必须命中
    for rule_id in (
        "config_debug_enabled",
        "tls_verify_disabled",
        "shell_exec_enabled",
        "secret_cloud_access_key",
        "secret_bearer_jwt",
        "insecure_package_index",
        "unpinned_dependency",
        "world_writable_chmod",
        "dynamic_eval",
    ):
        assert rule_id in rows, f"规则未命中: {rule_id}"

    # 2) 明文凭据绝不能出现在结果对象里（脱敏是结构性保证，不是打印时才做）
    dumped = repr([f.to_dict() for f in findings])
    for raw in ("ChangeMe-Demo-123", "AKIAIOSFODNN7EXAMPLE", "eyJhbGciOiJIUzI1NiJ9"):
        assert raw not in dumped, f"结果对象泄露明文: {raw}"

    # 3) 掩码与指纹格式
    assert rows["secret_cloud_access_key"].masked.startswith("AKIA")
    assert set(rows["secret_cloud_access_key"].masked[4:]) == {"*"}
    assert len(rows["secret_cloud_access_key"].evidence_sha256) == 16

    # 4) 分值/分级公式
    assert priority("critical", "high") == 15
    assert triage_band("critical", "high") == "P0"
    assert triage_band("low", "low") == "P3"

    # 5) 误报演示：纯文档也会命中（这正是需要人工复核与 baseline 的原因）
    doc_hits = [f for f in findings if f.path == "docs/README.md"]
    assert doc_hits, "文档样本应当命中，用于演示误报"
    assert all(f.confidence in ("low", "medium") for f in doc_hits), "文档类命中不应给高置信度"

    # 6) 无 baseline 时没有抑制项
    assert suppressed == []

    # 6b) DB_PASSWORD 这种下划线前缀写法也必须命中（常见漏报点）
    assert any(f.path == "app/settings.py" and f.rule_id == "secret_hardcoded_credential" for f in findings)

    # 7) 掩码/指纹是纯函数
    assert mask("abcdefgh") == "abcd****"
    assert mask("ab") == "**"
    long_mask = mask("x" * 100)
    assert long_mask.startswith("xxxx****") and long_mask.endswith("(len=100)")
    assert fingerprint("abc") == fingerprint("abc") != fingerprint("abd")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="运行自测")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("SELF-TEST OK")
    else:
        hits, muted = build_and_scan()
        print(f"规则数: {len(local_rules())}  样本文件: {len(SAMPLES)}")
        print(render(hits))
        print(f"\n命中合计: {len(hits)} 条，抑制: {len(muted)} 条")
        print("提醒：命中只是复核线索，不是漏洞结论；文档/注释也会命中。")
