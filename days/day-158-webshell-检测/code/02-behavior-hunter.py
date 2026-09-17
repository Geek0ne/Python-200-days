"""对合成审计事件做规则关联，不监控真实进程、不发请求。"""
import argparse
import json


def analyze(events):
    """同一主机同一进程实例有上传目录脚本写入及子进程启动时要求复核。

    instance 来自采集器的进程启动标识，不能只用可能复用的 PID。
    这是已限定时间窗口的数据；本例不实现日志采集和时间窗口切分。
    """
    groups = {}
    for event in events:
        key = (event['host'], event['instance'])
        if event.get('role') != 'web_worker':
            continue
        signals = groups.setdefault(key, set())
        if event['kind'] == 'script_write' and event.get('area') == 'uploads':
            signals.add('upload_script_write')
        if event['kind'] == 'child_start':
            signals.add('child_process')
    return [{'host': h, 'instance': i, 'review_required': True,
             'signals': sorted(signals)}
            for (h, i), signals in sorted(groups.items()) if len(signals) == 2]


def self_test():
    base = {'host': 'lab', 'instance': 'worker-start-1', 'role': 'web_worker'}
    events = [{**base, 'kind': 'script_write', 'area': 'uploads'},
              {**base, 'kind': 'child_start'}]
    assert len(analyze(events)) == 1
    assert analyze(events[:1]) == []
    assert analyze([events[0], {**events[1], 'host': 'different'}]) == []
    assert analyze([events[0], {**events[1], 'instance': 'reused-pid-new-start'}]) == []
    assert analyze([]) == []
    return analyze(events)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    result = self_test()
    print('SELF-TEST OK' if args.self_test else json.dumps(result, indent=2))
