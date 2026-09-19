"""实战规则引擎：多语言特征词典 + 加权评分 + 风险分级。

只读静态分析：把文件当数据读取，匹配词法特征，从不导入、解码、
执行或被扫描内容。命中是"需人工复核的线索"，不是恶意结论。
"""
import os
import re
import stat
from pathlib import Path

# ---------------------------------------------------------------- 规则库
# weight：该特征单独出现时的可疑程度（1=常见于正常代码，3=高度可疑）
# 同一规则在文件里多次出现会累加（第 2、3 次起权重递减），
# 反复混淆/重复调用在真实后门里很常见。

Rule = tuple  # (name, pattern, weight, category, languages)

RULES = [
    # ---- PHP 命令执行 ----
    ('php_cmd_exec',
     re.compile(r'\b(?:system|exec|shell_exec|passthru|popen|proc_open|pcntl_exec)\s*\(', re.I),
     3, 'command', {'php'}),
    ('php_backtick_exec',
     re.compile(r'`[^`]*`', re.I),
     2, 'command', {'php'}),
    ('php_dynamic_eval',
     re.compile(r'\b(?:eval|assert|create_function)\s*\(', re.I),
     3, 'dynamic', {'php'}),
    ('php_call_user_func',
     re.compile(r'\b(?:call_user_func(?:_array)?)\s*\(', re.I),
     2, 'dynamic', {'php'}),
    # ---- 编码 / 混淆（真实后门曲线解码常用）----
    ('encode_decode',
     re.compile(r'\b(?:base64_decode|gzinflate|gzuncompress|str_rot13|hex2bin|pack)\s*\(', re.I),
     2, 'encoding', {'php', 'asp', 'aspx'}),
    ('encode_encode',
     re.compile(r'\b(?:base64_encode|gzcompress|str_rot13|bin2hex)\s*\(', re.I),
     1, 'encoding', {'php', 'asp', 'aspx'}),
    ('php_error_suppress',
     re.compile(r'@\s*(?:system|exec|shell_exec|passthru|eval|assert|mysql|include|require|file_put_contents)\b', re.I),
     1, 'obfuscation', {'php'}),
    ('php_superglobal_input',
     re.compile(r'\$(?:_GET|_POST|_REQUEST|_COOKIE|_FILES)\s*\[', re.I),
     1, 'input', {'php'}),
    ('php_long_obfuscated_var',
     re.compile(r'\$[a-zA-Z_]\w{15,}\s*='),
     1, 'obfuscation', {'php'}),
    ('php_globals_var',
     re.compile(r'\$GLOBALS\s*\[', re.I),
     1, 'obfuscation', {'php'}),
    # ---- 文件系统后门动作 ----
    ('file_write',
     re.compile(r'\b(?:fwrite|fputs|file_put_contents|move_uploaded_file)\s*\(', re.I),
     2, 'filesystem', {'php'}),
    ('file_mod',
     re.compile(r'\b(?:chmod|unlink|rename|copy)\s*\(', re.I),
     1, 'filesystem', {'php'}),
    # ---- 网络外联 ----
    ('network_socket',
     re.compile(r'\b(?:fsockopen|pfsockopen|stream_socket_client|socket_create|curl_exec)\s*\(', re.I),
     2, 'network', {'php'}),
    # ---- 文件包含 ----
    ('include_dynamic',
     re.compile(r'\b(?:include|include_once|require|require_once)\s*\(\s*[\'"$]', re.I),
     1, 'include', {'php'}),
    # ---- JSP ----
    ('jsp_runtime_exec',
     re.compile(r'Runtime\s*\.\s*getRuntime\s*\(\s*\)\s*\.\s*exec', re.I),
     3, 'command', {'jsp'}),
    ('jsp_process_builder',
     re.compile(r'\bProcessBuilder\s*\(', re.I),
     3, 'command', {'jsp'}),
    ('jsp_define_class',
     re.compile(r'\bdefineClass\s*\(', re.I),
     2, 'dynamic', {'jsp'}),
    # ---- ASPX / ASP ----
    ('aspx_process_start',
     re.compile(r'\bProcess\s*\.\s*Start\s*\(', re.I),
     3, 'command', {'aspx'}),
    ('asp_wscript_shell',
     re.compile(r'CreateObject\s*\(\s*["\']W?Script\.Shell["\']', re.I),
     3, 'command', {'asp'}),
    ('asp_execute',
     re.compile(r'\bExecute(?:Global)?\s*\(', re.I),
     2, 'dynamic', {'asp'}),
]

# 语言标签 → 展示名
LANG_NAMES = {'php': 'PHP', 'jsp': 'JSP', 'aspx': 'ASPX', 'asp': 'ASP'}

# 扩展名 → 语言集合：用于压制跨语言误报（如 Java 的 .exec() 不应命中 PHP 规则）
EXT_LANGS = {
    '.php': {'php'}, '.php3': {'php'}, '.php5': {'php'}, '.phtml': {'php'},
    '.jsp': {'jsp'}, '.jspx': {'jsp'},
    '.aspx': {'aspx'},
    '.asp': {'asp'},
    # 未知扩展名（txt/log/conf…）：不限定语言，全部规则参与匹配
}

LIMIT = 1024 * 1024  # 单文件读取上限 1 MiB

# 风险分级阈值（累计得分）
SEVERITY_LEVELS = [
    (8, 'critical'),
    (5, 'high'),
    (3, 'medium'),
    (1, 'low'),
]


def classify_score(score):
    for threshold, level in SEVERITY_LEVELS:
        if score >= threshold:
            return level
    return 'clean'


def inspect_text(text, languages=None):
    """返回命中列表：规则名、类别、权重、行号。只做词法匹配。"""
    findings = []
    for name, pattern, weight, category, langs in RULES:
        if languages and not (langs & languages):
            continue
        for match in pattern.finditer(text):
            findings.append({
                'rule': name,
                'category': category,
                'weight': weight,
                'line': text.count('\n', 0, match.start()) + 1,
            })
    findings.sort(key=lambda f: (f['line'], f['rule']))
    return findings


def score_findings(findings):
    """加权评分：每规则首次命中记 weight，重复命中记 1（封顶 3 次）。"""
    counts = {}
    for f in findings:
        counts[f['rule']] = counts.get(f['rule'], 0) + 1
    score = 0
    for rule, count in counts.items():
        weight = next(w for name, _, w, _, _ in RULES if name == rule)
        score += weight + max(0, min(count, 3) - 1) * 1
    return score


def summarize(findings):
    """按规则聚合，给人工复核压缩后的摘要。"""
    summary = {}
    for f in findings:
        entry = summary.setdefault(f['rule'], {'category': f['category'],
                                               'weight': f['weight'],
                                               'lines': []})
        entry['lines'].append(f['line'])
    return summary


def inspect_file(path):
    """读取单个文件并返回扫描结果；本机安全守卫：O_NOFOLLOW + 大小/编码/类型限制。"""
    path = Path(path)
    try:
        if path.is_symlink():
            return {'status': 'skipped', 'reason': 'symlink'}
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return {'status': 'skipped', 'reason': 'not_regular'}
            data = stream.read(LIMIT + 1)
        if len(data) > LIMIT:
            return {'status': 'skipped', 'reason': 'too_large'}
        if b'\0' in data:
            return {'status': 'skipped', 'reason': 'binary'}
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            return {'status': 'skipped', 'reason': 'not_utf8'}
        findings = inspect_text(text, EXT_LANGS.get(path.suffix.lower()))
        return {'status': 'scanned', 'findings': findings,
                'score': score_findings(findings),
                'severity': classify_score(score_findings(findings)),
                'summary': summarize(findings)}
    except OSError as exc:
        return {'status': 'error', 'reason': type(exc).__name__}


def scan_tree(root, max_files=1000):
    """遍历目录。不跟随链接，不删改文件；上限由 max_files 控制。"""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('目标必须是存在的普通目录，不能是符号链接')
    if max_files < 1:
        raise ValueError('max_files 必须大于零')
    results, walk_errors = [], []

    def onerror(exc):
        walk_errors.append(type(exc).__name__)

    for parent, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        dirs[:] = sorted(d for d in dirs if not (Path(parent) / d).is_symlink())
        for name in sorted(files):
            if len(results) >= max_files:
                return {'files': results, 'truncated': True, 'walk_errors': walk_errors}
            path = Path(parent) / name
            results.append({'file': str(path.relative_to(root)), **inspect_file(path)})
    return {'files': results, 'truncated': False, 'walk_errors': walk_errors}


def print_rules():
    """--rules 输出：规则总览（类别 / 权重 / 覆盖语言）。"""
    lines = []
    for name, _, weight, category, langs in sorted(RULES, key=lambda r: (-r[2], r[0])):
        names = ', '.join(LANG_NAMES[l] for l in langs)
        lines.append(f'{name:24s} w={weight}  {category:12s} {names}')
    return '\n'.join(lines)


# ---------------------------------------------------------------- 自测
def self_test():
    """规则引擎离线自测：不读磁盘、不联网、不依赖第三方库。

    验证的四件事：规则库结构合法 / 分级阈值正确 / 评分含封顶 / 语言过滤生效。
    """
    # 1) 规则库结构合法：名称唯一、权重 1-3、类别与语言非空、pattern 已编译
    names = [name for name, *_ in RULES]
    assert len(names) == len(set(names)), '规则名必须唯一'
    assert len(RULES) >= 20, '规则数不应少于教学基线'
    for name, pattern, weight, category, langs in RULES:
        assert 1 <= weight <= 3, f'{name} 权重越界'
        assert category and langs, f'{name} 缺少类别或语言标签'
        assert hasattr(pattern, 'finditer'), f'{name} 的 pattern 未编译'

    # 2) 分级阈值边界
    assert classify_score(0) == 'clean'
    assert classify_score(1) == 'low'
    assert classify_score(2) == 'low'
    assert classify_score(3) == 'medium'
    assert classify_score(4) == 'medium'
    assert classify_score(5) == 'high'
    assert classify_score(7) == 'high'
    assert classify_score(8) == 'critical'

    # 3) 命中 + 评分：单个命令执行特征 = 权重 3
    findings = inspect_text("<?php system('id');")
    assert any(f['rule'] == 'php_cmd_exec' for f in findings), findings
    assert score_findings(findings) == 3

    # 4) 重复命中：第 2、3 次各 +1，第 4 次起封顶（3 + 2 = 5）
    repeated = inspect_text("<?php system('a');system('b');system('c');system('d');")
    hits = [f for f in repeated if f['rule'] == 'php_cmd_exec']
    assert len(hits) == 4, hits
    assert score_findings(repeated) == 5, score_findings(repeated)

    # 5) 语言过滤：JSP 文件不应命中 PHP 规则（跨语言误报压制）
    jsp_findings = inspect_text('Runtime.getRuntime().exec(cmd);', {'jsp'})
    assert all(f['rule'] != 'php_cmd_exec' for f in jsp_findings), jsp_findings
    assert any(f['rule'] == 'jsp_runtime_exec' for f in jsp_findings), jsp_findings

    # 6) summarize 按规则聚合，并给出可复核的行号
    summary = summarize(findings)
    assert 'php_cmd_exec' in summary and summary['php_cmd_exec']['lines'], summary

    # 7) 规则表可打印且包含核心规则
    assert 'php_cmd_exec' in print_rules()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='WebShell 静态规则引擎（被 01/02/03 共用）')
    parser.add_argument('--self-test', action='store_true', help='运行离线自测')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print('SELF-TEST OK')
    else:
        print(f'规则数: {len(RULES)}（用 03-webshell-scanner.py --rules 查看详情）')