#!/usr/bin/env python3
"""Day 136 - 02 - 堆栈回溯 + 补环境避坑（可离线运行）

两大主题：
A. 堆栈回溯：用 Python 的 traceback 模拟 JS 的 Call Stack 分析思路
B. 补环境避坑：演示"漏补属性导致静默走错分支"的经典大坑，
   并生成 Proxy 兜底记录的补环境模板
"""

import traceback
import json


# ═══════════════════════════════════════════════════════════
# A. 堆栈回溯：模拟 XHR 断点停住后向上追加密函数
# ═══════════════════════════════════════════════════════════

def get_sign(params: dict) -> str:
    """★ 栈中第 3 层：加密核心函数（我们要找的目标）"""
    raw = json.dumps(params, sort_keys=True)
    import hashlib
    return hashlib.md5(("salt+" + raw).encode()).hexdigest()


def build_params(page: int) -> dict:
    """栈中第 2 层：拼接参数处"""
    return {"page": page, "ts": 1770000000, "sign": get_sign({"page": page})}


def send_request(page: int):
    """栈顶：相当于 xhr.send()，XHR 断点停在这里"""
    params = build_params(page)
    # 模拟 XHR 断点：在此处"冻结"，打印调用栈
    print("  [XHR 断点] 请求参数（sign 已成品）:", params)
    stack = traceback.extract_stack()
    print("  [Call Stack] 调用链（栈顶 -> 栈底）:")
    for frame in reversed(stack[:-1]):  # 排除当前打印帧自身
        print(f"    {frame.name:<16} <- {frame.filename.split('/')[-1]}:{frame.lineno}")
    # ↓ 在真实 JS 里: 栈里看到 getSign -> 点进去 -> 逆向完成


print("=" * 60)
print("A. 堆栈回溯模拟：从 XHR 断点向上追出 getSign")
print("=" * 60)
send_request(1)

print()


# ═══════════════════════════════════════════════════════════
# B. 补环境避坑：漏补属性 -> 静默走错分支（最难的坑）
# ═══════════════════════════════════════════════════════════

class Env:
    """模拟补环境：故意漏补 platform 属性"""

    def __init__(self, provided: dict):
        self._provided = provided  # 只补了这些

    def __getattr__(self, name):
        # 经典坑: JS 里 env.platform 是 undefined，不报错！
        self.__dict__.setdefault("_missing", set()).add(name)
        return None  # 相当于 JS 的 undefined


def obfuscated_check(env) -> str:
    """模拟反爬 JS 的环境检测"""
    if env.platform is None:            # 漏补 -> 走了 bot 分支（不报错！）
        return "ERROR_SIGN_VERSION_B"   # 签名算法悄悄换了版本
    if env.webdriver:                   # 检测自动化标记
        return "ERROR_SIGN_VERSION_B"
    return "OK"


def run_with_env(provided: dict) -> str:
    env = Env(provided)
    result = obfuscated_check(env)
    missing = getattr(env, "_missing", set())
    if missing:
        print(f"  [警告] 补环境漏了属性: {missing} -> 静默走了异常分支!")
    return result


print("=" * 60)
print("B1. 补环境漏补属性的经典大坑演示")
print("=" * 60)
print("  只补 userAgent，不补 platform:")
print("  结果 =", run_with_env({"userAgent": "Mozilla/5.0 ..."}))

print()
print("  完整补齐 platform + webdriver=False:")
print("  结果 =", run_with_env({
        "userAgent": "Mozilla/5.0 ...",
        "platform": "Win32",
        "webdriver": False,
}))

print()
print("=" * 60)
print("B2. Proxy 兜底补环境模板（Node 用，自动记录访问日志）")
print("=" * 60)
proxy_template = """// env_preset.js —— Proxy 兜底补环境模板（Node 加载目标 JS 之前执行）
globalThis.__env_log__ = [];
function makeProxy(name, target) {
  return new Proxy(target, {
    get(obj, prop) {
      if (!(prop in obj)) {
        globalThis.__env_log__.push(`[补环境日志] ${name}.${String(prop)} 被访问但未提供!`);
        return undefined;
      }
      return obj[prop];
    },
  });
}
var navigator = makeProxy('navigator', {
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
  language: 'zh-CN', platform: 'Win32', webdriver: false,
});
var document = makeProxy('document', {
  cookie: '',
  createElement: () => ({ style: {}, getContext: () => null }),
  getElementById: () => null, addEventListener: () => {},
});
var location = { href: 'https://www.example.com/', hostname: 'www.example.com' };
var window = globalThis;
// 运行完目标 JS 后: console.log(globalThis.__env_log__) 按日志精准补
"""
print(proxy_template)
