#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_core.py — 安全审计工具箱 · 报告核心库（Day 165）

设计目标（本文件的每一条都是刻意的取舍，不是随手写出来的）：

1. **单一数据源（single source of truth）**
   所有渲染器（Markdown / HTML / JSON / SARIF）都从同一份 `Report.model()`
   派生。渲染器里**不允许**出现"计算"。一旦在渲染层算东西，四个格式就会
   慢慢漂移，最后没人知道哪个是对的。

2. **确定性（determinism）**
   同一份输入 → 字节级相同的输出。做法：
     - Finding 的 id 由内容哈希决定，而不是自增序号；
     - 排序键写死（severity → target → rule_id → id），不依赖输入顺序；
     - 报告头里的生成时间**由调用方传入**（`generated_at`），
       不在这里读 `datetime.now()`。这一条是让报告能进 git、能 diff 的关键。
   为什么较真？因为"报告变了"必须意味着"目标变了"。
   如果每次跑出来的报告都因为时间戳/顺序不同而变，那么 diff 就失去意义，
   代码评审、回归对比、CI 门禁全部失效。

3. **脱敏继承（redaction by design）**
   Day 164 定下的规矩是"口令/令牌/Cookie 的值不落盘"。
   报告层是**最后一道**出口，这里再兜一层：`redact_text()` 会兜底擦掉
   形如 `password=...`、`Authorization: Bearer ...` 的明文。
   注意：脱敏与检测是**两件事**——擦掉之后就检测不到了，
   所以检测必须在数据进入报告层**之前**完成（见 Day 164 的"先脱敏再检测"）。

4. **不虚构证据**
   Finding 里没有 `evidence` 的条目允许存在（例如"配置建议"），
   但渲染时必须显式写"（无证据，属建议项）"，绝不能凭空补一段像证据的文字。

安全边界：本模块只做**数据整理与渲染**，不发包、不探测、不改目标。
"""

from __future__ import annotations

import hashlib
import html as _html
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

__all__ = [
    "Finding",
    "Report",
    "SEVERITY_ORDER",
    "SEVERITY_WEIGHT",
    "stable_id",
    "redact_text",
    "redact_mapping",
    "summarize",
]

# ──────────────────────────────────────────────────────────────────────
# 常量：严重度的**唯一**排序与权重来源
# ──────────────────────────────────────────────────────────────────────
# 为什么把顺序和权重写死成常量，而不是在各个函数里现写？
# 因为"critical 到底排第几"这种问题只应该有一个答案。
# 一旦有第二处定义，早晚会打架（典型的：报告按 high>critical 排，门禁按反之）。
SEVERITY_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}
SEVERITY_WEIGHT: dict[str, int] = {
    "critical": 40,
    "high": 25,
    "medium": 12,
    "low": 5,
    "info": 1,
}
KNOWN_SEVERITIES = tuple(SEVERITY_ORDER)


# ──────────────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────────────
def stable_id(*parts: Any, length: int = 12) -> str:
    """由内容派生稳定 id。

    为什么不用 uuid4()？因为 uuid 每次都变，报告无法 diff。
    为什么不用自增序号？因为并发/分片收集时序号不稳定，
    而且"第 3 条 finding"在增删后含义会变。
    内容哈希的好处：同一条问题无论出现在哪一次运行，id 都一样——
    于是"新增/修复"可以直接用集合差算出来。
    """
    joined = "\x1f".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:length]


# 兜底脱敏规则。
#
# 【踩过的坑】第一版把授权头的取值写成 `\S+`，结果：
#     "Authorization: Bearer zzz" → "Authorization: <REDACTED> zzz"
# 令牌的尾巴漏出去了。原因是 `\S+` 只吃掉第一个词（"Bearer"），
# 后面的真实令牌留在原地；而把 Bearer 规则放前面又会先把它替换掉。
# 正确做法：**头字段类规则直接吃到行尾**（`[^\r\n]+`），
# 这样无论取值里有几个词，整段都被擦掉。顺序也就不再敏感。
#
# 另一条经验：值里排除 `,;&"'` 等分隔符（见下面 password 规则），
# 否则 "password=a; token=b" 会连 token 一起吞掉，
# 导致该报的秘密反而没被单独记录。
_REDACT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b(authorization|proxy-authorization|cookie|set-cookie)\s*[:=]\s*[^\r\n]+"),
     r"\1: <REDACTED>"),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-+/=]{8,}"), r"\1 <REDACTED>"),
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[-_]?key)\s*[:=]\s*[^\s,;&\"']+"),
     r"\1=<REDACTED>"),
    (re.compile(r"(?i)\b(\w+://)[^:@/\s]+:[^@/\s]+@"), r"\1<REDACTED>:<REDACTED>@"),
)


def redact_text(text: str) -> str:
    """对一段文本做**幂等**脱敏。

    幂等很重要：脱敏函数被调用两次的结果必须和一次一样，
    否则渲染链路里每加一层就会再擦一遍，最终把正常文本也吃掉。
    """
    out = text
    for pattern, repl in _REDACT_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    """递归脱敏字典（报告中 evidence 可能是嵌套结构）。

    只处理 str 值；数字/布尔/None 原样保留——它们通常不含秘密，
    而且改动类型会让下游 JSON schema 校验炸掉。
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = redact_text(value)
        elif isinstance(value, dict):
            result[key] = redact_mapping(value)
        elif isinstance(value, list):
            result[key] = [
                redact_text(v) if isinstance(v, str)
                else redact_mapping(v) if isinstance(v, dict)
                else v
                for v in value
            ]
        else:
            result[key] = value
    return result


# ──────────────────────────────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Finding:
    """一条可交付的问题记录。

    字段为什么是这几个？它们对应报告读者的三个问题：
      - 是什么（title / rule_id）
      - 多严重（severity / confidence）
      - 凭什么这么说（evidence / reason）
    以及修复者的一个额外问题：怎么办（remediation）。
    "凭什么"和"怎么办"必须分开写：把两者混在一段里，
    读者会分不清"观察到的事实"和"作者的推断"。
    """

    rule_id: str
    title: str
    severity: str
    target: str
    reason: str
    remediation: str = ""
    confidence: str = "high"          # high | medium | low
    evidence: tuple[str, ...] = ()    # 事实切片，可为空（建议项）
    tags: tuple[str, ...] = ()
    phase: str = ""                   # 来自四天项目中的哪一天/哪一层

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(
                f"未知 severity={self.severity!r}，只允许 {KNOWN_SEVERITIES}"
            )
        if self.confidence not in ("high", "medium", "low"):
            raise ValueError(f"未知 confidence={self.confidence!r}")

    # ---- 派生属性 ----
    @property
    def id(self) -> str:
        """稳定 id：**不含** severity 之外的可变字段，避免轻微改写就换 id。

        这里刻意把 target + rule_id 作为主键的一部分，把 title/reason 排除，
        因为改文案不应该被当成"新问题"。
        """
        return stable_id(self.target, self.rule_id, self.severity)

    @property
    def risk(self) -> int:
        """风险分 = 权重 × 置信度系数。

        为什么乘置信度？因为"疑似"和"确认"混在一起排序会误导人。
        低置信度的高危项应该往下沉，而不是压住已确认的中危项。
        """
        factor = {"high": 1.0, "medium": 0.6, "low": 0.3}[self.confidence]
        return int(SEVERITY_WEIGHT[self.severity] * factor)

    @property
    def sort_key(self) -> tuple[int, str, str, str]:
        """唯一的排序键。所有渲染器都必须用它。"""
        return (
            SEVERITY_ORDER[self.severity],
            -self.risk,
            self.target,
            self.rule_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """转成可 JSON 化的 dict，并在出口处做一次脱敏。"""
        payload = {
            "id": self.id,
            "rule_id": self.rule_id,
            "title": self.title,
            "severity": self.severity,
            "confidence": self.confidence,
            "risk": self.risk,
            "target": self.target,
            "phase": self.phase,
            "reason": self.reason,
            "remediation": self.remediation,
            "evidence": list(self.evidence),
            "tags": list(self.tags),
        }
        return redact_mapping(payload)


@dataclass
class Report:
    """一份报告 = 元信息 + 若干 Finding + 覆盖缺口。

    `coverage_gaps` 单独拿出来，是因为"没查到"和"查不到"是两回事：
    前者是结论，后者是**结论的边界**。把边界藏起来就是虚假的安全感。
    """

    title: str
    scope: str
    generated_at: str                      # ISO-8601，由调用方决定
    tool_version: str = "audit-toolbox/1.0"
    findings: list[Finding] = field(default_factory=list)
    coverage_gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    # ---- 收集 ----
    def add(self, finding: Finding) -> "Report":
        self.findings.append(finding)
        return self

    def extend(self, findings: Iterable[Finding]) -> "Report":
        for f in findings:
            self.findings.append(f)
        return self

    # ---- 归一化 ----
    def ordered_findings(self) -> list[Finding]:
        """稳定排序 + 去重（同 id 只留风险最高的一条）。"""
        best: dict[str, Finding] = {}
        for f in self.findings:
            prev = best.get(f.id)
            if prev is None or f.risk > prev.risk:
                best[f.id] = f
        return sorted(best.values(), key=lambda f: f.sort_key)

    def counts(self) -> dict[str, int]:
        """按严重度计数，**包含 0 值**。

        为什么要填 0？因为表格里缺一行 "critical 0" 和
        "根本不检查 critical" 在读者眼里长得一样。
        """
        out = {s: 0 for s in SEVERITY_ORDER}
        for f in self.ordered_findings():
            out[f.severity] += 1
        return out

    def total_risk(self) -> int:
        return sum(f.risk for f in self.ordered_findings())

    def model(self) -> dict[str, Any]:
        """规范化的、与渲染无关的中间表示（IR）。"""
        ordered = self.ordered_findings()
        return {
            "schema": "audit-report/1",
            "title": self.title,
            "scope": self.scope,
            "tool_version": self.tool_version,
            "generated_at": self.generated_at,
            "total_risk": self.total_risk(),
            "counts": self.counts(),
            "coverage_gaps": sorted(self.coverage_gaps),
            "notes": list(self.notes),
            "findings": [f.to_dict() for f in ordered],
        }

    # ---- 渲染：只做字符串拼接，绝不做计算 ----
    def render_json(self, *, indent: int = 2) -> str:
        """机器消费者（CI / 归档 / 二次分析）。"""
        return json.dumps(self.model(), ensure_ascii=False, indent=indent, sort_keys=False) + "\n"

    def render_markdown(self) -> str:
        """人类消费者（代码评审 / 工单 / README 附件）。"""
        m = self.model()
        lines: list[str] = []
        lines.append(f"# {m['title']}")
        lines.append("")
        lines.append(f"- **审计范围**：`{m['scope']}`")
        lines.append(f"- **生成时间**：{m['generated_at']}")
        lines.append(f"- **工具版本**：`{m['tool_version']}`")
        lines.append(f"- **风险总分**：{m['total_risk']}")
        lines.append("")

        lines.append("## 严重度分布")
        lines.append("")
        lines.append("| 严重度 | 数量 |")
        lines.append("|:------|:----:|")
        for sev in SEVERITY_ORDER:
            lines.append(f"| {sev} | {m['counts'][sev]} |")
        lines.append("")

        if m["findings"]:
            lines.append("## 问题清单")
            lines.append("")
            for f in m["findings"]:
                lines.append(f"### [{f['severity'].upper()}] {f['title']}")
                lines.append("")
                lines.append(f"- `id`：`{f['id']}`（规则 `{f['rule_id']}`）")
                lines.append(f"- `target`：`{f['target']}`")
                lines.append(f"- 置信度：{f['confidence']} · 风险分：{f['risk']}")
                if f["phase"]:
                    lines.append(f"- 发现层：{f['phase']}")
                lines.append("")
                lines.append(f"**原因**：{f['reason']}")
                lines.append("")
                if f["evidence"]:
                    lines.append("**证据**：")
                    lines.append("")
                    lines.append("```text")
                    for ev in f["evidence"]:
                        lines.append(str(ev))
                    lines.append("```")
                else:
                    lines.append("**证据**：（无证据，属建议项）")
                lines.append("")
                if f["remediation"]:
                    lines.append(f"**修复建议**：{f['remediation']}")
                    lines.append("")
        else:
            lines.append("## 问题清单")
            lines.append("")
            lines.append("本次审计未发现问题（注意：这不等于没有问题，见下方覆盖缺口）。")
            lines.append("")

        lines.append("## 覆盖缺口（必须随报告一起交付）")
        lines.append("")
        if m["coverage_gaps"]:
            for gap in m["coverage_gaps"]:
                lines.append(f"- ⚠️ {gap}")
        else:
            lines.append("- 无（本次所有计划层面均已覆盖）")
        lines.append("")

        if m["notes"]:
            lines.append("## 备注")
            lines.append("")
            for note in m["notes"]:
                lines.append(f"- {note}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(
            "> 本报告由自动化工具生成，仅覆盖 `scope` 范围内、"
            "且列于覆盖缺口之外的部分。"
        )
        lines.append("")
        return "\n".join(lines)

    def render_html(self) -> str:
        """HTML 渲染：注意**必须转义**，否则证据里的 `<script>` 会变成 XSS。

        这是一个真实的坑：审计报告的"证据"字段内容来自被审计目标，
        目标是**不可信输入**。把不可信输入直接拼进 HTML，
        等于审计工具自己变成了攻击载荷的投递渠道。
        """
        m = self.model()
        esc = _html.escape
        rows = []
        for f in m["findings"]:
            ev = "<br>".join(esc(e) for e in f["evidence"]) or "<i>（无证据，属建议项）</i>"
            rows.append(
                "    <tr>"
                f"<td class='sev sev-{esc(f['severity'])}'>{esc(f['severity'])}</td>"
                f"<td><code>{esc(f['id'])}</code></td>"
                f"<td>{esc(f['title'])}<div class='reason'>{esc(f['reason'])}</div>"
                f"<div class='fix'>修复：{esc(f['remediation']) or '—'}</div></td>"
                f"<td><code>{esc(f['target'])}</code></td>"
                f"<td class='ev'>{ev}</td>"
                f"<td>{f['risk']}</td>"
                "</tr>"
            )
        gaps = "".join(f"<li>{esc(g)}</li>" for g in m["coverage_gaps"]) or "<li>无</li>"
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{esc(m['title'])}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "PingFang SC", sans-serif;
         margin: 0; padding: 32px; background: #0f1115; color: #e6e6e6; }}
  h1 {{ font-size: 22px; }}
  .meta {{ color: #9aa4b2; font-size: 13px; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ border-bottom: 1px solid #23262d; padding: 10px 8px;
           vertical-align: top; text-align: left; }}
  th {{ color: #9aa4b2; font-weight: 600; }}
  code {{ background: #1b1e25; padding: 1px 5px; border-radius: 4px; }}
  .sev {{ font-weight: 700; text-transform: uppercase; }}
  .sev-critical {{ color: #ff5c5c; }}
  .sev-high {{ color: #ff9a3c; }}
  .sev-medium {{ color: #ffd93c; }}
  .sev-low {{ color: #6ec1ff; }}
  .sev-info {{ color: #9aa4b2; }}
  .reason {{ color: #c9d1d9; margin-top: 4px; }}
  .fix {{ color: #7ee787; margin-top: 4px; font-size: 12px; }}
  .ev {{ color: #9aa4b2; font-family: ui-monospace, Consolas, monospace; }}
  .gaps {{ margin-top: 24px; color: #ffd93c; }}
</style>
</head>
<body>
  <h1>{esc(m['title'])}</h1>
  <div class="meta">
    范围 <code>{esc(m['scope'])}</code> · 生成于 {esc(m['generated_at'])} ·
    工具 <code>{esc(m['tool_version'])}</code> · 风险总分 <b>{m['total_risk']}</b>
  </div>
  <table>
    <thead><tr><th>严重度</th><th>ID</th><th>问题</th><th>目标</th><th>证据</th><th>风险</th></tr></thead>
    <tbody>
{chr(10).join(rows) if rows else "    <tr><td colspan='6'>未发现问题</td></tr>"}
    </tbody>
  </table>
  <div class="gaps">
    <b>覆盖缺口</b>
    <ul>{gaps}</ul>
  </div>
</body>
</html>
"""

    def render_sarif(self) -> str:
        """SARIF 2.1.0 渲染：给 GitHub Code Scanning / IDE 消费。

        关键映射：
          - rule_id  → `ruleId`（同一规则只描述一次，放在 `tool.driver.rules`）
          - target   → `locations[].physicalLocation.artifactLocation.uri`
          - severity → `level`（只有 error/warning/note 三档，必然有信息损失）
        这就是为什么我们**不能**只输出 SARIF：三档装不下五档严重度，
        真正的排序信息在 `properties` 里另外带上。
        """
        m = self.model()
        rules: dict[str, dict[str, Any]] = {}
        results: list[dict[str, Any]] = []
        level_map = {"critical": "error", "high": "error", "medium": "warning",
                     "low": "note", "info": "note"}
        for f in m["findings"]:
            rules.setdefault(f["rule_id"], {
                "id": f["rule_id"],
                "name": f["rule_id"],
                "shortDescription": {"text": f["title"]},
                "help": {"text": f["remediation"] or "无"},
                "defaultConfiguration": {"level": level_map[f["severity"]]},
            })
            results.append({
                "ruleId": f["rule_id"],
                "level": level_map[f["severity"]],
                "message": {"text": f["reason"]},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": f["target"]},
                        "region": {"startLine": 1},
                    }
                }],
                "partialFingerprints": {"auditId/v1": f["id"]},
                "properties": {
                    "severity": f["severity"],
                    "confidence": f["confidence"],
                    "risk": f["risk"],
                    "evidence": f["evidence"],
                },
            })
        sarif = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {
                    "name": "audit-toolbox",
                    "version": m["tool_version"],
                    "informationUri": "https://example.invalid/audit-toolbox",
                    "rules": [rules[k] for k in sorted(rules)],
                }},
                "results": results,
                "properties": {
                    "scope": m["scope"],
                    "generatedAt": m["generated_at"],
                    "totalRisk": m["total_risk"],
                    "coverageGaps": m["coverage_gaps"],
                },
            }],
        }
        return json.dumps(sarif, ensure_ascii=False, indent=2) + "\n"


def summarize(report: Report) -> str:
    """一行摘要，给 CLI / 日志用。"""
    m = report.model()
    c = m["counts"]
    return (
        f"findings={len(m['findings'])} "
        f"critical={c['critical']} high={c['high']} medium={c['medium']} "
        f"low={c['low']} info={c['info']} risk={m['total_risk']} "
        f"gaps={len(m['coverage_gaps'])}"
    )
