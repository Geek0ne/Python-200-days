#!/usr/bin/env python3
"""Day 137 - 02 - 指纹一致性校验器（离线运行）

WAF 风控不只看单个特征，更看"交叉一致性"：
中国 IP + 美国时区 + 英语系统 = 高危。
本脚本实现一个一致性校验器，输出破绽报告。
"""

# 简化时区->预期地区映射
REGION_TZ = {
    "Asia/Shanghai": "CN",
    "America/New_York": "US",
    "America/Los_Angeles": "US",
    "Europe/London": "GB",
    "Asia/Tokyo": "JP",
}

# 语言前缀 -> 地区
LANG_REGION = {
    "zh": "CN", "en": "US/GB", "ja": "JP", "ko": "KR",
}


def check_consistency(fingerprint: dict) -> list:
    """校验一组指纹特征的自洽性，返回破绽列表

    fingerprint 字段:
      ip_country   IP 归属国
      timezone     浏览器时区
      language     navigator.language
      ua_platform  UA 声明的平台
      webrtc_ip    WebRTC 泄漏的真实 IP(应为 None)
      webdriver    navigator.webdriver 值
    """
    issues = []

    # ① 时区与 IP 归属地矛盾
    tz_region = REGION_TZ.get(fingerprint.get("timezone"))
    if tz_region and fingerprint.get("ip_country") not in tz_region.split("/"):
        issues.append(
            f"时区破绽: IP 在 {fingerprint['ip_country']}，"
            f"时区却是 {fingerprint['timezone']}({tz_region})"
        )

    # ② 语言与 IP 矛盾（宽松：zh 与 CN 匹配，en 不算破绽的常见站点）
    lang = (fingerprint.get("language") or "")[:2]
    if lang and lang == "zh" and fingerprint.get("ip_country") != "CN":
        issues.append(f"语言破绽: 中文系统但 IP 在 {fingerprint['ip_country']}")
    if not lang:
        issues.append("语言缺失: navigator.language 为空（爬虫常见）")

    # ③ WebRTC 泄漏
    if fingerprint.get("webrtc_ip"):
        issues.append(
            f"WebRTC 泄漏: 暴露真实内网/公网 IP {fingerprint['webrtc_ip']}，"
            "与代理 IP 不符 -> 代理形同虚设"
        )

    # ④ webdriver 标记
    if fingerprint.get("webdriver"):
        issues.append("自动化标记: navigator.webdriver === true（未做任何处理）")

    # ⑤ UA 平台与硬件特征矛盾
    ua = fingerprint.get("ua_platform", "")
    if "Windows" in ua and fingerprint.get("hardware_concurrency", 0) == 0:
        issues.append("硬件矛盾: UA 是 Windows 但 hardwareConcurrency=0")

    return issues


CASES = [
    {
        "name": "反例：裸 requests + 中国代理",
        "fp": {
            "ip_country": "CN", "timezone": None, "language": None,
            "ua_platform": "Windows NT 10.0", "webrtc_ip": None,
            "webdriver": None, "hardware_concurrency": 0,
        },
    },
    {
        "name": "反例：Selenium 裸奔 + 时区没配",
        "fp": {
            "ip_country": "CN", "timezone": "America/New_York",
            "language": "en-US", "ua_platform": "Windows NT 10.0",
            "webrtc_ip": "222.130.x.x", "webdriver": True,
            "hardware_concurrency": 8,
        },
    },
    {
        "name": "正例：全套自洽的伪装",
        "fp": {
            "ip_country": "CN", "timezone": "Asia/Shanghai",
            "language": "zh-CN", "ua_platform": "Windows NT 10.0",
            "webrtc_ip": None, "webdriver": False,
            "hardware_concurrency": 8,
        },
    },
]

if __name__ == "__main__":
    for case in CASES:
        print("=" * 60)
        print(f"场景: {case['name']}")
        print("=" * 60)
        issues = check_consistency(case["fp"])
        if issues:
            for i, msg in enumerate(issues, 1):
                print(f"  ✗ 破绽{i}: {msg}")
            print(f"  => 风控评分: 高危（{len(issues)} 处破绽）")
        else:
            print("  ✓ 全部自洽，通过一致性检查")
        print()
