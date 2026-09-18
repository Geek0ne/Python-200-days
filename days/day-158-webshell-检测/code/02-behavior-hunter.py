"""实战行为关联：日志特征 + 评分 + 跨主机/实例隔离。

输入为合成审计事件（模拟 Web 访问日志与进程事件），输出命中主机。
不采集真实进程，不发网络请求。
"""
import argparse
import json

# 行为信号：名称 → (得分, 需要的外键字段)
# 生产采集时 instance 必须是进程启动标识，不能只用可复用的 PID。
SIGNALS = {
    'upload_script_write': (3, {'host', 'instance', 'request'}),
    'child_start': (2, {'host', 'instance'}),
    'cmd_arg_shell': (2, {'host', 'instance'}),
    'suspicious_ua': (1, {'host'}),
    'many_failed_auth': (1, {'host'}),
    'upload_then_delete': (2, {'host', 'instance', 'request'}),
}

# 触达这些分数即要求人工复核
REVIEW_THRESHOLD = 4


def analyze(events, window_ok=True):
    """按 (host, instance) 分组加和信号分；达到阈值输出 review_required。

    window_ok=False 可模拟"时间窗口信息缺失"，此时任何结论都不可靠，
    直接返回需人工复核但标记 time_window_unknown。
    """
    if not window_ok:
        hosts = sorted({e['host'] for e in events if 'host' in e})
        return [{'host': h, 'instance': 'unknown', 'review_required': True,
                 'signals': [], 'score': 0, 'reason': 'time_window_unknown'}
                for h in hosts]
    groups = {}
    for event in events:
        key = (event.get('host'), event.get('instance', '?'))
        for name, (weight, fields) in SIGNALS.items():
            if event.get('kind') != name:
                continue
            missing = fields - set(event)
            if missing:
                raise ValueError(f'事件缺少必要字段 {sorted(missing)}')
            entry = groups.setdefault(key, {'signals': [], 'score': 0})
            entry['signals'].append(name)
            entry['score'] += weight
    return [{'host': h, 'instance': i, 'review_required': entry['score'] >= REVIEW_THRESHOLD,
             'signals': sorted(set(entry['signals'])), 'score': entry['score']}
            for (h, i), entry in sorted(groups.items())]


def self_test():
    base = {'host': 'lab', 'instance': 'worker-start-1', 'request': '/upload.php'}
    events = [
        {**base, 'kind': 'upload_script_write'},   # +3
        {**base, 'kind': 'child_start'},           # +2 → 5 ≥ 4 复核
        {**base, 'kind': 'cmd_arg_shell'},
    ]
    assert len(analyze(events)) == 1
    assert analyze(events)[0]['review_required'] is True

    # 跨主机：其他主机的上传事件不能算进 lab 组（各自分组，分数不叠加）
    other_host = {**events[0], 'host': 'other'}
    mixed = analyze([other_host] + events)
    lab_entry = next(e for e in mixed if e['host'] == 'lab')
    assert lab_entry['score'] == 7 and lab_entry['review_required'] is True
    other_entry = next(e for e in mixed if e['host'] == 'other')
    assert other_entry['score'] == 3 and other_entry['review_required'] is False

    # 跨实例：PID 复用 ≠ 同一进程。child_start 换到"新启动标识"后不得叠加到原组
    moved = [{**e, 'instance': 'start-2'} if e['kind'] == 'child_start' else e
             for e in events]
    results = analyze(moved)
    orig = next(e for e in results if e['instance'] == 'worker-start-1')
    assert orig['score'] == 5 and orig['review_required'] is True
    new_inst = next(e for e in results if e['instance'] == 'start-2')
    assert new_inst['score'] == 2 and new_inst['review_required'] is False

    # 分数不足不触发
    low = analyze([{**base, 'kind': 'upload_script_write'}])
    assert low and low[0]['review_required'] is False

    # 时间窗口缺失时拒绝下结论
    assert analyze(events, window_ok=False)[0]['reason'] == 'time_window_unknown'

    # 缺字段必须报错
    try:
        analyze([{'host': 'lab', 'instance': 'i', 'kind': 'upload_script_write'}])
    except ValueError:
        pass
    else:
        raise AssertionError('缺 request 字段必须报错')
    return analyze(events)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--events', type=json.loads, default=None,
                        help='JSON 数组，如 [{"host":"lab","instance":"i","kind":"child_start"}]')
    parser.add_argument('--no-window', action='store_true',
                        help='模拟缺少时间窗口信息的场景')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print('SELF-TEST OK')
    elif args.events is not None:
        try:
            print(json.dumps(analyze(args.events, window_ok=not args.no_window),
                             ensure_ascii=False, indent=2))
        except ValueError as exc:
            parser.error(str(exc))
    else:
        parser.print_help()