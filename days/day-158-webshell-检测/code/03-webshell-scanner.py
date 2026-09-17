"""离线只读静态审阅 CLI；JSON 写到标准输出，不自动隔离/删除。"""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from static_scan import LIMIT, scan_tree


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sample = root / 'review.txt'
        sample.write_text('API名索引：ProcessBuilder', encoding='utf-8')
        before = hashlib.sha256(sample.read_bytes()).hexdigest()
        (root / 'large.txt').write_bytes(b'x' * (LIMIT + 1))
        (root / 'invalid.txt').write_bytes(b'\xff')
        report = scan_tree(root)
        rows = {x['file']: x for x in report['files']}
        assert rows['review.txt']['findings'][0]['rule'] == 'process_api'
        assert rows['large.txt']['reason'] == 'too_large'
        assert rows['invalid.txt']['reason'] == 'not_utf8'
        assert before == hashlib.sha256(sample.read_bytes()).hexdigest()
        assert json.loads(json.dumps(report)) == report
        try:
            scan_tree(root / 'missing')
        except ValueError:
            pass
        else:
            raise AssertionError('不存在目录必须报错')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', type=Path, help='自己的离线证据副本目录')
    parser.add_argument('--max-files', type=int, default=1000)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print('SELF-TEST OK')
        return 0
    if args.target is None:
        parser.error('必须显式指定本地目录；或使用 --self-test')
    try:
        report = scan_tree(args.target, args.max_files)
    except ValueError as exc:
        parser.error(str(exc))
    report['notice'] = '命中仅供人工复核；无命中不代表安全。未执行任何文件。'
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # 检查覆盖不全返回2；规则命中仍返回0，因为它不是确定的恶意判定。
    incomplete = report['truncated'] or report['walk_errors'] or any(
        f['status'] != 'scanned' for f in report['files'])
    return 2 if incomplete else 0


if __name__ == '__main__':
    raise SystemExit(main())
