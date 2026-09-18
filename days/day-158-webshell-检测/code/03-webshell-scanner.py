"""实战 WebShell 扫描器 CLI：目录扫描 + 评分定级 + JSON 报告。

只读分析：不执行、不联网、不自动隔离/删除。命中仅代表特征匹配，
需结合业务基线人工复核。本扫描器未在真实生产样本集上评测。
"""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from static_scan import LIMIT, classify_score, print_rules, scan_tree, score_findings

# 报告级（整个目录）的提醒阈值
REPORT_SEVERITY_ORDER = {'clean': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}


def _severity_sort(item):
    return REPORT_SEVERITY_ORDER.get(item.get('severity', 'clean'), 0)


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sample = root / 'review.txt'
        # 文档误报演示：txt 未知扩展名 → 全部规则参与，仅命中 encode_encode(权重1)
        sample.write_text('API名索引：base64_encode(', encoding='utf-8')
        before = hashlib.sha256(sample.read_bytes()).hexdigest()
        (root / 'large.txt').write_bytes(b'x' * (LIMIT + 1))
        (root / 'invalid.txt').write_bytes(b'\xff')

        report = scan_tree(root)
        rows = {x['file']: x for x in report['files']}
        assert rows['review.txt']['findings'][0]['rule'] == 'encode_encode'
        assert rows['review.txt']['severity'] == 'low'
        assert rows['large.txt']['reason'] == 'too_large'
        assert rows['invalid.txt']['reason'] == 'not_utf8'
        # 只读性校验
        assert before == hashlib.sha256(sample.read_bytes()).hexdigest()
        # JSON 可序列化
        assert json.loads(json.dumps(report)) == report
        # 缺失目录必须报错
        try:
            scan_tree(root / 'missing')
        except ValueError:
            pass
        else:
            raise AssertionError('不存在的目录必须报错')
        # 分级函数可独立调用
        assert classify_score(score_findings([])) == 'clean'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', type=Path, help='自己的离线证据副本目录')
    parser.add_argument('--max-files', type=int, default=1000)
    parser.add_argument('--rules', action='store_true', help='列出规则库并退出')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()

    if args.rules:
        print(print_rules())
        return 0
    if args.self_test:
        self_test()
        print('SELF-TEST OK')
        return 0
    if args.target is None:
        parser.error('必须显式指定本地目录；或使用 --self-test / --rules')

    try:
        report = scan_tree(args.target, args.max_files)
    except ValueError as exc:
        parser.error(str(exc))

    files = report['files']
    scanned = [f for f in files if f['status'] == 'scanned']
    high = [f for f in scanned if f.get('severity') in ('high', 'critical')]
    high.sort(key=_severity_sort, reverse=True)

    report['notice'] = '命中仅供人工复核；无命中不代表安全。未执行/未联网。'
    report['summary'] = {
        'files_total': len(files),
        'files_scanned': len(scanned),
        'high_or_critical': len(high),
        'top_findings': [{'file': f['file'], 'severity': f['severity'],
                          'score': f.get('score', 0),
                          'rules': list(f.get('summary', {}))}
                         for f in high[:20]],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    incomplete = report['truncated'] or report['walk_errors'] or any(
        f['status'] != 'scanned' for f in files)
    return 2 if incomplete else 0


if __name__ == '__main__':
    raise SystemExit(main())