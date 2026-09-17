"""只读静态审阅辅助：词法命中不是恶意判定，也不证明数据流可达。"""
import os
import re
from pathlib import Path

# 单独出现时常见于正常程序。只报告规则名/行号，不导出源码或凭据。
RULES = {
    'dynamic_evaluation': re.compile(r'\b(?:eval|assert)\s*\(', re.I),
    'encoded_content': re.compile(r'\b(?:base64_decode|gzinflate)\s*\(', re.I),
    'process_api': re.compile(r'\b(?:ProcessBuilder|child_process)\b', re.I),
}
LIMIT = 1024 * 1024


def inspect_text(text):
    """扫描纯文本；不会解析、解码、执行或导入被扫描内容。"""
    return [{'rule': name, 'line': text.count('\n', 0, m.start()) + 1}
            for name, regex in RULES.items() for m in regex.finditer(text)]


def inspect_file(path):
    """Linux 上以 O_NOFOLLOW 打开，拒绝符号链接和特殊文件。"""
    import stat
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
        return {'status': 'scanned', 'findings': inspect_text(text)}
    except OSError as exc:
        return {'status': 'error', 'reason': type(exc).__name__}


def scan_tree(root, max_files=1000):
    """显式本地目录；不跟随链接，不删改文件，最多处理 max_files 个条目。

    用于离线、稳定的证据副本。不是对恶意并发目录替换的安全沙箱。
    """
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
