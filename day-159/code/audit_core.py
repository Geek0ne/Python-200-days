"""审计工具箱核心模块（Day 159 — 安全审计工具）。

先读这一节，再看代码：下面每个设计决定，都在解决一个真实发生过的翻车模式。

1. **只读**：审计工具一旦有副作用就不再可信。本模块只读取文件内容，
   不写、不删、不改权限、不发起任何网络请求。
   原则是"扫的不管，管的不管扫"——发现问题与处置问题必须是两套权限。

2. **证据脱敏**：报告会流转（工单、邮件、CI 日志、别人的终端）。
   命中值只保留掩码 + SHA-256 指纹，**模块内部就不保存明文**，
   让"忘记脱敏"这种事故在结构上不可能发生。
   见 `mask()` / `fingerprint()` / `make_finding()`。

3. **覆盖可查**：跳过（过大 / 二进制 / 非法编码 / 符号链接）与读取错误全部计数。
   只要有任何一项非空，`Coverage.complete` 就是 False——报告必须声明覆盖不全，
   否则"0 命中"会被误读成"已确认安全"。

4. **抑制可见**：baseline 命中的条目不删除，只标记 suppressed 并单独计数，
   避免 baseline 文件退化成"永久消音器"。

5. **资源自限**：单文件大小上限、文件数上限、目录黑名单。
   审计脚本跑在别人的机器上，不能把对方的磁盘和 CPU 拖死。
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

# ─────────────────────────── 严重度 / 置信度 ───────────────────────────
# 为什么要把这两件事分开？
#   严重度 = 问题被利用后的**影响**（impact），是客观的
#   置信度 = 这条命中**真是问题的把握**（certainty），取决于匹配方式
# 混在一起就会把"正则误报的高危"和"确凿的低危"排在同一档次，
# 结果就是复核人员被噪音淹没。分开后 triage 分值 = 影响 × 把握。
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}
TRIAGE_BANDS = ((12, "P0"), (8, "P1"), (4, "P2"), (0, "P3"))


def priority(severity: str, confidence: str) -> int:
    """triage 分值，1..15。critical+high = 15，info+low = 1。"""
    return (SEVERITY_ORDER[severity] + 1) * (CONFIDENCE_ORDER[confidence] + 1)


def triage_band(severity: str, confidence: str) -> str:
    """把分值归到 P0..P3，方便在报告里排序和设置门禁。"""
    score = priority(severity, confidence)
    for threshold, band in TRIAGE_BANDS:
        if score >= threshold:
            return band
    return "P3"


def duration_safe(value: str) -> str:
    """辅助函数：把可能含换行的命中值压成单行，避免报告被撑爆。"""
    return " ".join(str(value).split())


def mask(value: str, keep: int = 4, cap: int = 32) -> str:
    """脱敏：只保留前 keep 个字符，其余用 * 代替；超长命中值截断。

    为什么不全留？因为报告会被人复制粘贴到聊天窗口、贴进工单。
    为什么保留前几位？为了让人能在日志/配置里**定位**到它（前 4 位通常
    是前缀，如 AKIA / sk- / eyJ），但不足以还原。
    为什么还要截断？命中值可能是整段带凭据的配置行，几百个星号会把
    报告撑爆、把真正的位置信息挤出屏幕（`(len=...)` 提示原始长度）。
    """
    text = duration_safe(value)
    if len(text) <= keep:
        return "*" * len(text)
    if len(text) > cap:
        return text[:keep] + "*" * 8 + f"(len={len(text)})"
    return text[:keep] + "*" * (len(text) - keep)


def fingerprint(value: str) -> str:
    """证据指纹：用于跨报告比对同一条命中，不含可还原信息。"""
    return hashlib.sha256(duration_safe(value).encode("utf-8", "replace")).hexdigest()[:16]


# ─────────────────────────────── 规则模型 ───────────────────────────────
@dataclass(frozen=True)
class Rule:
    """一条审计规则。

    为什么规则一定要带 `why` 和 `remediation`？
    因为没有修复建议的命中，对复核人员就是一封没有落款的举报信：
    他知道"有个东西不对"，但不知道"不对在哪、下一步做什么"。
    规则是**知识**的载体，不是一个正则字符串。
    """

    id: str
    title: str
    severity: str
    confidence: str
    category: str
    why: str
    remediation: str
    cwe: str = ""
    pattern: str | None = None
    file_glob: str = "*"
    flags: int = re.IGNORECASE

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(f"非法 severity: {self.severity}")
        if self.confidence not in CONFIDENCE_ORDER:
            raise ValueError(f"非法 confidence: {self.confidence}")


def local_rules() -> list[Rule]:
    """内置规则库：本地配置/代码中的已知风险模式（教学基线，按业务调整）。

    规则分四类：secret（凭据）、config（不安全配置）、
    crypto（弱算法）、supply（供应链）。
    """
    return [
        # ── 凭据类 ──
        Rule(
            id="secret_private_key",
            title="疑似私钥内容",
            severity="critical",
            confidence="high",
            category="secret",
            cwe="CWE-798",
            why="私钥进入仓库或备份即等同身份泄露，且无法通过改代码回滚。",
            remediation="从仓库历史移除并**轮换**该密钥；改用密钥管理服务/环境注入。",
            pattern=r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----",
        ),
        Rule(
            id="secret_cloud_access_key",
            title="疑似云平台 Access Key",
            severity="critical",
            confidence="high",
            category="secret",
            cwe="CWE-798",
            why="长期有效的云 Access Key 泄露可直接导致资源被创建/删除（账单事故）。",
            remediation="立即在云控制台禁用并轮换该 Key，改用最小权限的临时凭据。",
            pattern=r"\bAKIA[0-9A-Z]{16}\b",
        ),
        Rule(
            id="secret_hardcoded_credential",
            title="疑似硬编码口令/Token",
            severity="high",
            confidence="medium",
            category="secret",
            cwe="CWE-798",
            why="硬编码凭据会随代码分发到所有人的电脑和所有备份里，无法按人回收。",
            remediation="改为从环境变量/密钥服务读取；轮换已被硬编码的凭据。",
            # 注意：这里**不能**在 password 前加 \b —— 变量名多为 DB_PASSWORD，
            # 下划线是单词字符，\b 会直接漏掉最常见的写法（真实踩坑点）。
            pattern=r"(?i)(password|passwd|secret|token|api_key|apikey)\s*[:=]\s*[\"'][^\"'\s]{6,}[\"']",
        ),
        Rule(
            id="secret_bearer_jwt",
            title="疑似硬编码 JWT",
            severity="medium",
            confidence="medium",
            category="secret",
            cwe="CWE-798",
            why="JWT 是可用凭据；写进代码等于把会话借给所有能读代码的人。",
            remediation="改为运行时下发；确认该 Token 已失效（过有效期或撤销）。",
            pattern=r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}\b",
        ),
        # ── 配置类 ──
        Rule(
            id="config_debug_enabled",
            title="生产配置开启 DEBUG",
            severity="medium",
            confidence="high",
            category="config",
            cwe="CWE-489",
            why="调试模式会暴露堆栈、配置与环境变量，等于给攻击者一份地图。",
            remediation="生产环境关闭 DEBUG，用环境变量区分 dev/prod 配置。",
            pattern=r"(?im)^\s*DEBUG\s*[:=]\s*(true|1|on|yes)\s*$",
        ),
        Rule(
            id="tls_verify_disabled",
            title="关闭 TLS 证书校验",
            severity="high",
            confidence="high",
            category="config",
            cwe="CWE-295",
            why="verify=False 让中间人攻击变得平凡，加密只剩心理安慰作用。",
            remediation="恢复校验；如为自签名证书，改为显式配置受信任的 CA 包。",
            pattern=r"\bverify\s*=\s*False\b",
        ),
        Rule(
            id="tls_legacy_protocol",
            title="启用过时 TLS/SSL 版本",
            severity="medium",
            confidence="high",
            category="config",
            cwe="CWE-327",
            why="TLS 1.0/1.1 与 SSLv3 已被证明存在可利用缺陷，属合规硬性淘汰项。",
            remediation="服务端最低版本设为 TLS 1.2（推荐 1.3），并更新客户端配置。",
            pattern=r"\b(TLSv1(\.[01])?|SSLv3)\b",
        ),
        Rule(
            id="weak_hash_or_cipher",
            title="使用弱哈希/弱算法",
            severity="low",
            confidence="low",
            category="crypto",
            cwe="CWE-327",
            why="MD5/SHA1/DES/RC4 已可被实际碰撞或破解，不再适合安全用途。",
            remediation="哈希改用 SHA-256 及以上；对称加密改用 AES-GCM。",
            pattern=r"(?i)\b(md5|sha1|des|rc4)\b",
        ),
        # ── 代码执行类 ──
        Rule(
            id="shell_exec_enabled",
            title="子进程以 shell 方式执行",
            severity="medium",
            confidence="high",
            category="code",
            cwe="CWE-78",
            why="shell=True 会把参数交给 shell 解析，参数拼接即注入。",
            remediation="改为列表参数形式（shell=False），并对输入做白名单校验。",
            pattern=r"\bshell\s*=\s*True\b",
        ),
        Rule(
            id="dynamic_eval",
            title="动态求值调用",
            severity="medium",
            confidence="low",
            category="code",
            cwe="CWE-95",
            why="eval/exec 会执行任意表达式；是否真的危险取决于输入是否可控。",
            remediation="优先用 ast.literal_eval 或显式解析；确认输入来源与数据流。",
            pattern=r"(?<![\w.])e(?:val|val)\s*\(",
        ),
        Rule(
            id="world_writable_chmod",
            title="授权过宽的文件权限",
            severity="high",
            confidence="medium",
            category="config",
            cwe="CWE-732",
            why="777/666 允许任意本地用户改写脚本或配置，常被用作提权跳板。",
            remediation="按最小权限收紧（脚本 755、配置 640），属主与运行用户对齐。",
            pattern=r"\bchmod\s+(0?777|0?666|a\+rwx)\b",
        ),
        # ── 供应链类 ──
        Rule(
            id="insecure_package_index",
            title="使用明文 HTTP 软件源",
            severity="medium",
            confidence="high",
            category="supply",
            cwe="CWE-494",
            why="明文 HTTP 源可被投毒替换，安装即执行攻击者的包。",
            remediation="改为 HTTPS 源，并验证包签名/哈希。",
            pattern=r"(?i)(--(index|extra)-url\s*[= ]\s*|index-url\s*=\s*)http://",
        ),
        Rule(
            id="unpinned_dependency",
            title="依赖未锁定版本",
            severity="low",
            confidence="medium",
            category="supply",
            cwe="CWE-1104",
            why="未固定版本意味着每次安装都可能拿到不同的代码，构建不可复现。",
            remediation="固定版本（==）并生成锁文件；配合定期升级流程。",
            pattern=r"^[A-Za-z0-9_.\-]+$",
            file_glob="requirements*.txt",
        ),
    ]


# ─────────────────────────────── 结果模型 ───────────────────────────────
@dataclass
class Finding:
    """一条命中。注意：没有 raw 字段——明文从一开始就不进入结果对象。"""

    rule_id: str
    title: str
    severity: str
    confidence: str
    category: str
    cwe: str
    path: str
    line: int
    masked: str
    evidence_sha256: str
    why: str
    remediation: str

    @property
    def key(self) -> tuple:
        return (self.rule_id, self.path, self.line)

    @property
    def band(self) -> str:
        return triage_band(self.severity, self.confidence)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["priority"] = priority(self.severity, self.confidence)
        data["triage_band"] = self.band
        return data


@dataclass
class Coverage:
    """覆盖统计。`complete == False` 时报告不得声称"未发现问题"。"""

    files_scanned: int = 0
    bytes_read: int = 0
    skipped: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    truncated: bool = False

    def skip(self, reason: str, count: int = 1) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + count

    @property
    def complete(self) -> bool:
        return not self.truncated and not self.errors and not self.skipped

    @property
    def gaps(self) -> list:
        gaps = [f"skipped:{k}={v}" for k, v in sorted(self.skipped.items())]
        if self.truncated:
            gaps.append("truncated:达到文件数上限")
        gaps.extend(f"error:{e}" for e in self.errors)
        return gaps

    def to_dict(self) -> dict:
        data = asdict(self)
        data["complete"] = self.complete
        data["gaps"] = self.gaps
        return data


@dataclass
class AuditReport:
    root: str
    findings: list = field(default_factory=list)
    suppressed: list = field(default_factory=list)
    coverage: Coverage = field(default_factory=Coverage)
    rules_evaluated: list = field(default_factory=list)

    def by_severity(self) -> dict:
        counts = {name: 0 for name in SEVERITY_ORDER}
        for f in self.findings:
            counts[f.severity] += 1
        return counts

    def by_band(self) -> dict:
        counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for f in self.findings:
            counts[f.band] += 1
        return counts

    def at_or_above(self, threshold: str = "high") -> list:
        """门禁用：列出严重度 >= threshold 的命中。"""
        limit = SEVERITY_ORDER[threshold]
        return [f for f in self.findings if SEVERITY_ORDER[f.severity] >= limit]

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "rules_evaluated": list(self.rules_evaluated),
            "summary": {
                "findings": len(self.findings),
                "suppressed": len(self.suppressed),
                "by_severity": self.by_severity(),
                "by_triage_band": self.by_band(),
            },
            "coverage": self.coverage.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "suppressed": [f.to_dict() for f in self.suppressed],
        }


# ─────────────────────────────── 扫描引擎 ───────────────────────────────
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".tgz", ".7z", ".rar", ".exe", ".dll", ".so", ".dylib", ".pyc",
    ".class", ".jar", ".bin", ".woff", ".woff2", ".ttf", ".otf", ".mp3",
    ".mp4", ".mov", ".sqlite", ".db", ".pkl",
}
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".tox", "dist", "build", ".idea",
}


def _matches_glob(path: str, pattern: str) -> bool:
    """同时按文件名和相对路径匹配，避免 requirements*.txt 漏掉子目录。"""
    name = Path(path).name
    return fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(path, pattern)


def make_finding(rule: Rule, path: str, line: int, matched: str) -> Finding:
    return Finding(
        rule_id=rule.id,
        title=rule.title,
        severity=rule.severity,
        confidence=rule.confidence,
        category=rule.category,
        cwe=rule.cwe,
        path=str(path),
        line=line,
        masked=mask(matched),
        evidence_sha256=fingerprint(matched),
        why=rule.why,
        remediation=rule.remediation,
    )


def dedupe(findings: Iterable[Finding]) -> list:
    """同一 (规则, 文件, 行) 只留一条。多规则命中同一行时都保留（不同问题）。"""
    seen, out = set(), []
    for finding in findings:
        if finding.key in seen:
            continue
        seen.add(finding.key)
        out.append(finding)
    return out


def baseline_keys(baseline: Iterable[str]) -> set:
    """baseline 支持三种写法：rule:path / rule:sha256 / rule:path:line。"""
    return {str(item).strip() for item in baseline if str(item).strip()}


def inspect_text(name: str, text: str, rules: Sequence[Rule], baseline: Iterable[str] = ()) -> tuple:
    """对一段文本做审计。返回 (findings, suppressed)。"""
    base = baseline_keys(baseline)
    findings, suppressed = [], []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule in rules:
            if not rule.pattern:
                continue
            if not _matches_glob(name, rule.file_glob):
                continue
            for match in re.finditer(rule.pattern, line, rule.flags):
                finding = make_finding(rule, name, lineno, match.group(0))
                keys = {
                    f"{rule.id}:{name}",
                    f"{rule.id}:{finding.evidence_sha256}",
                    f"{rule.id}:{name}:{lineno}",
                }
                if keys & base:
                    suppressed.append(finding)
                else:
                    findings.append(finding)
    return dedupe(findings), dedupe(suppressed)


def scan_path(
    root: str | Path,
    rules: Sequence[Rule] | None = None,
    *,
    max_files: int = 1000,
    max_bytes: int = 1 << 20,
    baseline: Iterable[str] = (),
    exclude_dirs: Iterable[str] | None = None,
    allow_symlinks: bool = False,
) -> AuditReport:
    """只读扫描 `root`（文件或目录）。所有跳过与错误都记录在 coverage 里。"""
    rule_list = list(rules or local_rules())
    target = Path(root)
    if not target.exists():
        raise FileNotFoundError(f"目标不存在: {target}")

    exclude = set(DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs)
    coverage = Coverage()
    findings, suppressed = [], []

    def consume(path: Path, display: str) -> None:
        try:
            raw = path.read_bytes()
        except OSError as exc:  # 权限不足等：记录但不中断
            coverage.errors.append(f"{display}: {exc.__class__.__name__}")
            return
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            coverage.skip("not_utf8")
            return
        coverage.files_scanned += 1
        coverage.bytes_read += len(raw)
        hits, muted = inspect_text(display, text, rule_list, baseline)
        findings.extend(hits)
        suppressed.extend(muted)

    if target.is_file():
        consume(target, target.name)
    else:
        stopped = False
        # 用 os.walk(followlinks=False)：不跟随符号链接目录，避免走出审计范围。
        for dirpath, dirnames, filenames in os.walk(target, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d not in exclude)
            for filename in sorted(filenames):
                if coverage.files_scanned >= max_files:
                    coverage.truncated = True
                    stopped = True
                    break
                path = Path(dirpath) / filename
                display = str(path.relative_to(target))
                if path.is_symlink() and not allow_symlinks:
                    coverage.skip("symlink")
                    continue
                try:
                    size = path.stat().st_size
                except OSError as exc:
                    coverage.errors.append(f"{display}: {exc.__class__.__name__}")
                    continue
                if size > max_bytes:
                    coverage.skip("too_large")
                    continue
                if path.suffix.lower() in BINARY_SUFFIXES:
                    coverage.skip("binary")
                    continue
                consume(path, display)
            if stopped:
                break

    return AuditReport(
        root=str(target),
        findings=sorted(findings, key=lambda f: (-priority(f.severity, f.confidence), f.path, f.line)),
        suppressed=suppressed,
        coverage=coverage,
        rules_evaluated=[r.id for r in rule_list],
    )


def summarize(report: AuditReport) -> str:
    """一行摘要，方便日志/终端输出。"""
    sev = report.by_severity()
    parts = " ".join(f"{k}={v}" for k, v in sev.items() if v)
    state = "覆盖完整" if report.coverage.complete else "覆盖不全"
    return f"findings={len(report.findings)} [{parts or '无'}] suppressed={len(report.suppressed)} {state}"
