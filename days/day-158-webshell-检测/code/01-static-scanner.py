"""入门：在临时目录扫描无执行能力的教学文本。"""
import json
import tempfile
from pathlib import Path
from static_scan import scan_tree


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'clean.txt').write_text('普通业务文档', encoding='utf-8')
        # 只是未闭合的API名称文本，没有脚本标签、输入或执行载荷。
        (root / 'review.txt').write_text('文档提及 eval(\nbase64_decode(', encoding='utf-8')
        (root / 'link.txt').symlink_to(root / 'clean.txt')
        (root / 'binary.dat').write_bytes(b'\x00')
        report = scan_tree(root)
        rows = {x['file']: x for x in report['files']}
        assert rows['clean.txt']['findings'] == []
        assert len(rows['review.txt']['findings']) == 2
        assert rows['link.txt']['reason'] == 'symlink'
        assert rows['binary.dat']['reason'] == 'binary'
        assert scan_tree(root, 1)['truncated']
        return report


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test', action='store_true')
    args = p.parse_args()
    result = self_test()
    print('SELF-TEST OK' if args.self_test else json.dumps(result, ensure_ascii=False, indent=2))
