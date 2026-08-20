"""
Day 121 - 日志异常检测器
=========================
完整的日志异常检测系统：解析、特征提取、检测、告警
支持多种日志格式，可扩展的检测管道
"""

import re
import json
import time
import hashlib
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# ============================================================
# 1. 日志解析器
# ============================================================

class LogParser:
    """通用日志解析器，支持多种格式"""

    # 常见日志格式的正则表达式
    PATTERNS = {
        'apache': re.compile(
            r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s+-\s+\S+\s+'
            r'\[(?P<timestamp>[^\]]+)\]\s+'
            r'"(?P<method>\w+)\s+(?P<path>\S+)\s+\S+"\s+'
            r'(?P<status>\d+)\s+(?P<bytes>\d+)'
        ),
        'syslog': re.compile(
            r'(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+'
            r'(?P<host>\S+)\s+(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?:\s+'
            r'(?P<message>.+)'
        ),
        'app_log': re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'(?P<level>\w+)\s+'
            r'(?P<module>\S+)\s+-\s+'
            r'(?P<message>.+)'
        ),
    }

    def parse(self, line: str, log_type: str = 'app_log') -> Optional[Dict]:
        """解析单行日志"""
        pattern = self.PATTERNS.get(log_type)
        if not pattern:
            return None

        match = pattern.match(line.strip())
        if match:
            return {**match.groupdict(), 'raw': line.strip()}
        return None

    def extract_features(self, parsed_logs: List[Dict]) -> Dict:
        """从解析后的日志中提取特征"""
        features = {}

        # 时间窗口统计
        features['total_count'] = len(parsed_logs)

        if not parsed_logs:
            return features

        # 错误率
        error_levels = ['ERROR', 'FATAL', 'CRITICAL']
        error_count = sum(1 for log in parsed_logs
                         if log.get('level', '') in error_levels)
        features['error_rate'] = error_count / len(parsed_logs)

        # 独特消息数
        messages = [log.get('message', '') for log in parsed_logs]
        features['unique_messages'] = len(set(messages))

        # 消息熵（衡量多样性）
        msg_counter = Counter(messages)
        total = sum(msg_counter.values())
        entropy = -sum((c/total) * np.log2(c/total)
                      for c in msg_counter.values() if c > 0)
        features['message_entropy'] = entropy

        # 模块/组件分布
        modules = [log.get('module', 'unknown') for log in parsed_logs]
        module_counter = Counter(modules)
        features['unique_modules'] = len(module_counter)
        features['top_module_ratio'] = (
            module_counter.most_common(1)[0][1] / len(modules)
            if modules else 0
        )

        # 状态码分布（Apache日志）
        statuses = [log.get('status', '') for log in parsed_logs]
        if any(statuses):
            status_counter = Counter(statuses)
            features['unique_status_codes'] = len(status_counter)
            features['error_status_ratio'] = sum(
                v for k, v in status_counter.items()
                if k.startswith(('4', '5'))
            ) / len(statuses)

        return features

# ============================================================
# 2. 滑动窗口特征提取器
# ============================================================

class SlidingWindowFeatureExtractor:
    """滑动窗口特征提取器"""

    def __init__(self, window_size: int = 60, step_size: int = 10):
        """
        window_size: 窗口大小（秒）
        step_size: 滑动步长（秒）
        """
        self.window_size = window_size
        self.step_size = step_size
        self.parser = LogParser()

    def extract_windows(self, logs: List[Dict]) -> List[Dict]:
        """将日志按时间窗口分组并提取特征"""
        if not logs:
            return []

        # 假设日志有 timestamp 字段
        windows = []
        all_features = []

        # 简单按固定窗口切分（实际应按时间戳）
        window_size = max(1, len(logs) // 20)  # 大约20个窗口
        for i in range(0, len(logs), window_size):
            window_logs = logs[i:i + window_size]
            features = self.parser.extract_features(window_logs)
            features['window_id'] = len(windows)
            all_features.append(features)
            windows.append(window_logs)

        return all_features

# ============================================================
# 3. 日志异常检测器
# ============================================================

class LogAnomalyDetector:
    """端到端日志异常检测器"""

    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.model = None
        self.scaler = StandardScaler()
        self.feature_extractor = SlidingWindowFeatureExtractor()
        self.baseline_features = None

    def train(self, normal_logs: List[str], log_type: str = 'app_log'):
        """用正常日志训练模型"""
        print("📝 解析正常日志...")
        parser = LogParser()
        parsed = [parser.parse(line, log_type)
                 for line in normal_logs if parser.parse(line, log_type)]
        parsed = [p for p in parsed if p is not None]

        print(f"  成功解析: {len(parsed)}/{len(normal_logs)} 条")

        print("🔧 提取特征...")
        window_features = self.feature_extractor.extract_windows(parsed)

        if not window_features:
            raise ValueError("无法提取足够的特征窗口")

        # 转换为特征矩阵
        feature_keys = [k for k in window_features[0].keys()
                       if isinstance(window_features[0][k], (int, float))]
        X = np.array([[wf[k] for k in feature_keys] for wf in window_features])

        print(f"  特征维度: {X.shape}")
        print(f"  特征列: {feature_keys}")

        # 标准化
        X_scaled = self.scaler.fit_transform(X)

        # 训练 Isolation Forest
        print("🌲 训练 Isolation Forest...")
        self.model = IsolationForest(
            n_estimators=100,
            max_samples=min(256, len(X_scaled)),
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_scaled)
        self.feature_keys = feature_keys

        print(f"✅ 模型训练完成！窗口数: {len(X_scaled)}")

    def detect(self, logs: List[str], log_type: str = 'app_log') -> List[Dict]:
        """检测日志异常"""
        if self.model is None:
            raise RuntimeError("模型未训练，请先调用 train()")

        parser = LogParser()
        parsed = [parser.parse(line, log_type)
                 for line in logs if parser.parse(line, log_type)]
        parsed = [p for p in parsed if p is not None]

        window_features = self.feature_extractor.extract_windows(parsed)

        if not window_features:
            return []

        X = np.array([[wf[k] for k in self.feature_keys]
                      for wf in window_features])
        X_scaled = self.scaler.transform(X)

        predictions = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)

        results = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            results.append({
                'window_id': i,
                'is_anomaly': pred == -1,
                'anomaly_score': float(score),
                'features': window_features[i],
                'log_count': window_features[i]['total_count']
            })

        return results

# ============================================================
# 4. 告警系统
# ============================================================

class AlertSystem:
    """简单告警系统"""

    def __init__(self, threshold: float = -0.3):
        self.threshold = threshold
        self.alerts = []

    def check(self, detection_results: List[Dict]) -> List[Dict]:
        """检查检测结果并生成告警"""
        new_alerts = []

        for result in detection_results:
            if result['is_anomaly'] and result['anomaly_score'] < self.threshold:
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'window_id': result['window_id'],
                    'severity': self._get_severity(result['anomaly_score']),
                    'score': result['anomaly_score'],
                    'features': result['features'],
                    'message': self._format_message(result)
                }
                new_alerts.append(alert)
                self.alerts.append(alert)

        return new_alerts

    def _get_severity(self, score: float) -> str:
        if score < -0.5:
            return 'CRITICAL'
        elif score < -0.3:
            return 'HIGH'
        elif score < -0.1:
            return 'MEDIUM'
        return 'LOW'

    def _format_message(self, result: Dict) -> str:
        features = result['features']
        return (
            f"窗口 {result['window_id']} 检测到异常 | "
            f"异常分数: {result['anomaly_score']:.4f} | "
            f"错误率: {features.get('error_rate', 0):.1%} | "
            f"日志数: {features.get('total_count', 0)}"
        )

# ============================================================
# 5. 主程序：完整演示
# ============================================================

def generate_sample_logs(n_normal=500, n_anomaly=50) -> Tuple[List[str], List[str]]:
    """生成示例日志数据"""
    np.random.seed(42)

    levels = ['INFO', 'DEBUG', 'WARNING', 'ERROR']
    modules = ['auth', 'api', 'database', 'cache', 'scheduler']
    messages_normal = [
        'Request processed successfully',
        'User authenticated',
        'Cache hit for key: user_{}',
        'Database query completed in {}ms',
        'Scheduled task executed',
        'Connection pool status: {} active',
    ]
    messages_error = [
        'Connection refused: database timeout',
        'Authentication failed: invalid token',
        'Memory allocation failed',
        'Disk space critically low',
        'Segmentation fault in worker process',
    ]

    normal_logs = []
    for _ in range(n_normal):
        level = np.random.choice(levels, p=[0.5, 0.3, 0.15, 0.05])
        module = np.random.choice(modules)
        ts = datetime(2024, 1, 15, np.random.randint(8, 22),
                     np.random.randint(0, 60), np.random.randint(0, 60))
        if level == 'ERROR':
            msg = np.random.choice(messages_error)
        else:
            msg = np.random.choice(messages_normal).format(
                np.random.randint(1, 1000))
        normal_logs.append(f"{ts} {level} {module} - {msg}")

    anomaly_logs = []
    for _ in range(n_anomaly):
        ts = datetime(2024, 1, 15, np.random.randint(8, 22),
                     np.random.randint(0, 60), np.random.randint(0, 60))
        # 异常：大量ERROR
        level = np.random.choice(['ERROR', 'FATAL', 'CRITICAL'],
                                p=[0.5, 0.3, 0.2])
        module = np.random.choice(modules)
        msg = np.random.choice(messages_error)
        anomaly_logs.append(f"{ts} {level} {module} - {msg}")

    return normal_logs, anomaly_logs

def main():
    print("=" * 60)
    print("🔍 日志异常检测器 - 完整演示")
    print("=" * 60)

    # 1. 生成数据
    print("\n📊 步骤1: 生成示例日志数据")
    normal_logs, anomaly_logs = generate_sample_logs(500, 50)
    print(f"  正常日志: {len(normal_logs)} 条")
    print(f"  异常日志: {len(anomaly_logs)} 条")

    # 2. 训练模型（只用正常日志）
    print("\n🌲 步骤2: 用正常日志训练模型")
    detector = LogAnomalyDetector(contamination=0.1)
    detector.train(normal_logs, log_type='app_log')

    # 3. 检测混合日志
    print("\n🔍 步骤3: 检测异常日志")
    mixed_logs = normal_logs + anomaly_logs
    np.random.shuffle(mixed_logs)  # 打乱顺序

    results = detector.detect(mixed_logs, log_type='app_log')

    anomalies = [r for r in results if r['is_anomaly']]
    normals = [r for r in results if not r['is_anomaly']]

    print(f"  总窗口数: {len(results)}")
    print(f"  检出异常窗口: {len(anomalies)}")
    print(f"  正常窗口: {len(normals)}")

    # 4. 告警
    print("\n🚨 步骤4: 生成告警")
    alert_system = AlertSystem(threshold=-0.3)
    alerts = alert_system.check(results)

    for alert in alerts:
        severity_icon = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }.get(alert['severity'], '⚪')

        print(f"  {severity_icon} [{alert['severity']}] {alert['message']}")

    # 5. 性能分析
    print("\n📈 步骤5: 检测性能分析")
    avg_score_normal = np.mean([r['anomaly_score'] for r in normals]) if normals else 0
    avg_score_anomaly = np.mean([r['anomaly_score'] for r in anomalies]) if anomalies else 0
    print(f"  正常窗口平均分数: {avg_score_normal:.4f}")
    print(f"  异常窗口平均分数: {avg_score_anomaly:.4f}")
    print(f"  分数差距: {abs(avg_score_normal - avg_score_anomaly):.4f}")

    # 6. 特征重要性分析
    print("\n🔬 步骤6: 异常窗口特征分析")
    if anomalies:
        print("  异常窗口共同特征:")
        avg_features = defaultdict(list)
        for a in anomalies:
            for k, v in a['features'].items():
                if isinstance(v, (int, float)):
                    avg_features[k].append(v)

        for feature, values in sorted(avg_features.items()):
            print(f"    {feature}: avg={np.mean(values):.4f}")

    print("\n💡 日志异常检测最佳实践：")
    print("  1. 日志解析是基础 - 不同系统格式差异大")
    print("  2. 特征工程决定效果 - 时间窗口+统计特征")
    print("  3. 用正常数据训练 - 无监督学习不需要异常标注")
    print("  4. 滑动窗口适合流式 - 支持实时检测")
    print("  5. 告警阈值需要调优 - 根据误报率调整")
    print("  6. 定期重训练 - 适应日志模式变化")

if __name__ == '__main__':
    main()
