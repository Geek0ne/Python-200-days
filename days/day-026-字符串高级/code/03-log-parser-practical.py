#!/usr/bin/env python3
"""
Day 026 — 实战：日志解析器与字符串编码处理

涵盖：
1. Nginx 日志解析器（正则提取结构化数据）
2. 日志统计分析
3. 字符串编码实战（ASCII/Unicode/UTF-8 转换）
4. 编码错误处理
5. 文件编码检测与自动修复

可直接运行：python3 03-log-parser-practical.py
"""

import re
import json
from collections import Counter, defaultdict

print("=" * 60)
print("1. Nginx 日志解析器")
print("=" * 60)

# 模拟 Nginx 访问日志
NGINX_LOG_LINES = [
    '192.168.1.1 - - [17/Jun/2026:10:15:30 +0800] "GET /api/users HTTP/1.1" 200 1234 "https://example.com" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"',
    '127.0.0.1 - admin [17/Jun/2026:10:16:45 +0800] "POST /api/login HTTP/1.1" 401 56 "-" "curl/7.68.0"',
    '10.0.0.5 - - [17/Jun/2026:10:17:01 +0800] "GET /static/style.css HTTP/1.1" 304 0 "https://example.com/home" "Mozilla/5.0"',
    '192.168.1.1 - - [17/Jun/2026:10:18:22 +0800] "POST /api/data HTTP/1.1" 500 234 "-" "python-requests/2.28"',
    '203.0.113.5 - - [17/Jun/2026:10:19:00 +0800] "GET /api/users HTTP/1.1" 200 5678 "-" "Go-http-client/2.0"',
    '192.168.1.1 - - [17/Jun/2026:10:20:15 +0800] "DELETE /api/users/123 HTTP/1.1" 403 89 "-" "Mozilla/5.0"',
    '10.0.0.5 - - [17/Jun/2026:10:21:30 +0800] "GET /api/health HTTP/1.1" 200 45 "-" "kube-probe/1.26"',
]

# 编译正则（匹配 Nginx Combined Log Format）
LOG_PATTERN = re.compile(r"""
    (?P<ip>\S+)                    # 客户端 IP
    \s+                            # 分隔空白
    (?P<ident>\S+)                 # ident
    \s+                            # 分隔空白
    (?P<auth>\S+)                  # 认证用户
    \s+                            # 分隔空白
    \[(?P<time>[^\]]+)\]           # 时间戳 [17/Jun/2026:10:15:30 +0800]
    \s+                            # 分隔空白
    "(?P<method>\S+)               # HTTP 方法 (GET/POST...)
    \s+                            # 空白
    (?P<path>\S+)                  # 请求路径
    \s+                            # 空白
    (?P<protocol>[^"]+)"           # 协议版本
    \s+                            # 分隔空白
    (?P<status>\d{3})              # 状态码
    \s+                            # 分隔空白
    (?P<size>\d+)                  # 响应大小
    \s+                            # 分隔空白
    "(?P<referer>[^"]*)"           # Referer
    \s+                            # 分隔空白
    "(?P<user_agent>[^"]*)"        # User-Agent
""", re.VERBOSE)


def parse_log_line(line: str) -> dict | None:
    """解析单行日志，返回结构化字典"""
    m = LOG_PATTERN.match(line)
    if not m:
        return None
    return {
        'ip': m.group('ip'),
        'auth': m.group('auth') if m.group('auth') != '-' else None,
        'time': m.group('time'),
        'method': m.group('method'),
        'path': m.group('path'),
        'protocol': m.group('protocol'),
        'status': int(m.group('status')),
        'size': int(m.group('size')),
        'referer': m.group('referer') if m.group('referer') != '-' else None,
        'user_agent': m.group('user_agent'),
    }


# 解析所有日志
parsed_logs = []
failed_lines = []
for i, line in enumerate(NGINX_LOG_LINES, 1):
    result = parse_log_line(line)
    if result:
        parsed_logs.append(result)
    else:
        failed_lines.append((i, line))

print(f"共解析 {len(parsed_logs)} 条日志, 失败 {len(failed_lines)} 条")
print("\n--- 解析结果预览（前3条）---")
for entry in parsed_logs[:3]:
    print(f"  IP: {entry['ip']:<15} | {entry['method']:<6} {entry['path']:<25} → {entry['status']}")

print("\n" + "=" * 60)
print("2. 日志统计分析")
print("=" * 60)

# 2.1 状态码分布
status_counter = Counter(e['status'] for e in parsed_logs)
print("--- 状态码分布 ---")
for code, count in sorted(status_counter.items()):
    emoji = {200: '✅', 304: '↪️', 401: '🔒', 403: '🚫', 500: '💥'}.get(code, '❓')
    print(f"  {emoji} {code}: {count} 次 ({count/len(parsed_logs)*100:.1f}%)")

# 2.2 IP 访问统计
ip_counter = Counter(e['ip'] for e in parsed_logs)
print("\n--- IP 访问统计 ---")
for ip, count in ip_counter.most_common():
    print(f"  {ip:<15} → {count} 次请求")

# 2.3 请求方法分布
method_counter = Counter(e['method'] for e in parsed_logs)
print("\n--- 请求方法 ---")
for m, count in method_counter.most_common():
    print(f"  {m:<8} {count} 次")

# 2.4 每秒请求数（简单统计时间分布）
time_counts = Counter()
for e in parsed_logs:
    # 提取小时和分钟：17/Jun/2026:10:15:30 → 10:15
    hour_min = e['time'].split(':')[1] + ':' + e['time'].split(':')[2]
    time_counts[hour_min] += 1

print("\n--- 请求时间分布 ---")
for t in sorted(time_counts):
    print(f"  {t} → {time_counts[t]} 次请求")

# 2.5 响应大小统计
sizes = [e['size'] for e in parsed_logs]
print(f"\n--- 响应大小分析 ---")
print(f"  总传输: {sum(sizes):,} bytes")
print(f"  平均值: {sum(sizes)/len(sizes):,.0f} bytes")
print(f"  最小值: {min(sizes):,} bytes")
print(f"  最大值: {max(sizes):,} bytes")

print("\n" + "=" * 60)
print("3. 数据提取器 — 按条件过滤")
print("=" * 60)


class LogFilter:
    """可组合的日志过滤器"""

    def __init__(self, logs: list[dict]):
        self.logs = logs

    def by_status(self, code: int) -> 'LogFilter':
        """按状态码过滤"""
        return LogFilter([e for e in self.logs if e['status'] == code])

    def by_path(self, prefix: str) -> 'LogFilter':
        """按路径前缀过滤"""
        return LogFilter([e for e in self.logs if e['path'].startswith(prefix)])

    def by_method(self, method: str) -> 'LogFilter':
        return LogFilter([e for e in self.logs if e['method'] == method])

    def export_json(self) -> str:
        """导出为 JSON"""
        return json.dumps(self.logs, ensure_ascii=False, indent=2)

    def export_csv(self) -> str:
        """导出为 CSV"""
        if not self.logs:
            return ""
        keys = self.logs[0].keys()
        lines = [",".join(keys)]
        for e in self.logs:
            lines.append(",".join(str(e[k]) for k in keys))
        return "\n".join(lines)

    def summary(self) -> dict:
        return {
            'total': len(self.logs),
            'endpoints': list(set(e['path'] for e in self.logs)),
            'ips': list(set(e['ip'] for e in self.logs)),
        }

    def __len__(self):
        return len(self.logs)


# 使用过滤器
filtered = (LogFilter(parsed_logs)
            .by_status(200)
            .by_path('/api'))

print(f"状态码 200 的 API 请求数: {len(filtered)}")
print(f"端点: {filtered.summary()['endpoints']}")

# 导出前2条为 JSON
print("\n--- JSON 导出（前2条）---")
for entry in filtered.logs[:2]:
    print(json.dumps(entry, ensure_ascii=False, indent=2))

print("\n" + "=" * 60)
print("4. 字符串编码实战")
print("=" * 60)

# 4.1 字符串编码/解码演示
print("--- 编码/解码基础 ---")
text = 'Hello 你好 😊'
print(f"原始字符串: '{text}'")
print(f"  str 长度: {len(text)} 个字符")

# 编码为不同格式
for encoding in ['utf-8', 'utf-16', 'utf-32', 'gbk', 'ascii']:
    try:
        b = text.encode(encoding)
        print(f"  {encoding:7s}: {b.hex(' ')} ({len(b)} bytes)")
    except UnicodeEncodeError as e:
        print(f"  {encoding:7s}: ❌ {e}")

# 4.2 乱码场景模拟与修复
print("\n--- 编码错误场景 ---")
# 场景：收到其他编码的 bytes
raw_bytes = '你好世界'.encode('gbk')
print(f"GBK 编码的 bytes: {raw_bytes.hex(' ')}")
try:
    raw_bytes.decode('utf-8')  # 用 UTF-8 解码 GBK → 乱码
except UnicodeDecodeError as e:
    print(f"用 UTF-8 解码: ❌ UnicodeDecodeError: {e}")

# 正确解码
correct = raw_bytes.decode('gbk')
print(f"用 GBK 解码: ✅ {correct}")

# 4.3 编码错误处理策略
print("\n--- errors 参数处理策略 ---")
s = 'Hello 你好 😊'
for strategy in ['strict', 'ignore', 'replace', 'xmlcharrefreplace', 'backslashreplace']:
    try:
        result = s.encode('ascii', errors=strategy)
        print(f"  {strategy:20s}: {result}")
    except UnicodeEncodeError as e:
        print(f"  {strategy:20s}: ❌ {e}")

# 4.4 文件编码检测
print("\n--- 简易编码检测器 ---")


def detect_encoding(data: bytes) -> str:
    """简易编码检测（仅用于演示，生产用 chardet）"""
    if data.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if data.startswith(b'\xff\xfe'):
        return 'utf-16-le'
    if data.startswith(b'\xfe\xff'):
        return 'utf-16-be'
    # 尝试常用编码
    for enc in ['utf-8', 'gbk', 'latin-1']:
        try:
            data.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return 'unknown'


test_data = [
    ('UTF-8 BOM', b'\xef\xbb\xbfhello'),
    ('纯 ASCII', b'hello world'),
    ('UTF-8 中文', '你好'.encode('utf-8')),
    ('GBK 中文', '你好'.encode('gbk')),
]

for name, data in test_data:
    detected = detect_encoding(data)
    print(f"  {name:15s}: bytes={data.hex(' ')} → 检测为 {detected}")

# 4.5 统一编码处理
print("\n--- 统一编码规范化 ---")


def normalize_text(text_or_bytes, source_encoding='utf-8', target='utf-8'):
    """将输入统一为 UTF-8 字符串"""
    if isinstance(text_or_bytes, bytes):
        return text_or_bytes.decode(source_encoding)
    return text_or_bytes


def safe_decode(data: bytes, fallback_encodings=None) -> tuple[str, str]:
    """安全解码，尝试多种编码，返回 (文本, 实际编码)"""
    if fallback_encodings is None:
        fallback_encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'shift_jis']
    for enc in fallback_encodings:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    # 最终 fallback
    return data.decode('latin-1'), 'latin-1'


# 模拟从不同来源获取的数据
mixed_data = [
    ('来自 API', '{"status": "ok"}'.encode('utf-8')),
    ('来自旧系统', '用户信息'.encode('gbk')),
    ('来自日本服务器', 'こんにちは'.encode('shift_jis')),
]

print("统一解码多种编码来源的数据:")
for source, data in mixed_data:
    text, encoding = safe_decode(data)
    print(f"  [{source}] detected={encoding:10s}: {text}")

print("\n" + "=" * 60)
print("5. 生成综合解析报告")
print("=" * 60)


def generate_report(logs: list[dict]) -> str:
    """生成日志解析 HTML 格式报告"""
    status_dist = Counter(e['status'] for e in logs)
    method_dist = Counter(e['method'] for e in logs)
    top_ips = Counter(e['ip'] for e in logs).most_common(3)
    total_size = sum(e['size'] for e in logs)

    report = []
    report.append("=" * 50)
    report.append("  📊 日志解析报告")
    report.append("=" * 50)
    report.append(f"  共处理日志: {len(logs)} 条")
    report.append(f"  总传输数据: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    report.append("")
    report.append(f"  📈 状态码分布:")
    for code, count in sorted(status_dist.items()):
        bar = "█" * count + "░" * (10 - count)
        report.append(f"    {code}: {bar} ({count}次)")
    report.append("")
    report.append(f"  📌 请求方法:")
    for m, count in method_dist.most_common():
        report.append(f"    {m}: {count}次")
    report.append("")
    report.append(f"  🌐 活跃 IP TOP 3:")
    for ip, count in top_ips:
        report.append(f"    {ip}: {count}次请求")
    report.append("")
    report.append(f"  错误请求（4xx/5xx）: {sum(c for s, c in status_dist.items() if s >= 400)} 条")
    report.append("=" * 50)

    return "\n".join(report)


print(generate_report(parsed_logs))

print("\n✅ 实战案例演示完成！")
print("💡 试试修改 NGINX_LOG_LINES 加入你自己的日志数据！")
