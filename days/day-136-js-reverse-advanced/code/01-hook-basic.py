#!/usr/bin/env python3
"""Day 136 - 01 - Hook 基础原理演示（纯 Python 模拟，可离线运行）

用 Python 复现 JS Hook 的"偷梁换柱"思想：
1. 模拟一个"网站 JS 环境"（伪 window 对象）
2. 模拟"加密函数"（目标网站的签名算法）
3. 注入 Hook 包装函数：记录入参/出参
4. 最后生成一段可直接粘贴到浏览器 Console 的真实 JS Hook 脚本
"""

# ─── 1. 模拟浏览器全局对象 window ───────────────────────────────
class FakeWindow:
    """模拟 JS 的 window：属性即函数/变量容器"""

    def __getattr__(self, name):
        # 模拟 JS 访问不存在属性返回 undefined 而不是报错
        return None


window = FakeWindow()


# ─── 2. 模拟目标网站的加密函数 ────────────────────────────────
def _real_get_sign(params: str) -> str:
    """假设这是网站的核心签名算法（逆向目标）"""
    # 实际可能是几百行混淆代码，这里简化演示
    salt = "secret_salt_2026"
    raw = f"{salt}|{params}"
    # 模拟 md5（不用 hashlib 是为了演示纯手写感觉；实际直接用 hashlib）
    import hashlib
    return hashlib.md5(raw.encode()).hexdigest()


# 把函数挂到 window 上，模拟 window.getSign = ...
window.getSign = _real_get_sign


# ─── 3. Hook 注入：偷梁换柱 ───────────────────────────────────
def hook_function(window_obj, func_name: str):
    """通用的 Hook 器：替换 window 上的函数，前后插桩"""
    original = getattr(window_obj, func_name)          # ① 备份原函数

    def hooked(*args, **kwargs):
        print(f"  [hook] {func_name} 入参: {args}")
        result = original(*args, **kwargs)             # ② 调用原逻辑
        print(f"  [hook] {func_name} 出参: {result}")
        print(f"  [hook] 此处对应 JS 里的 debugger; 可查看调用栈")
        return result                                  # ③ 原样返回，调用方无感

    setattr(window_obj, func_name, hooked)             # ④ 替换


# ─── 4. 模拟业务代码调用 ──────────────────────────────────────
def business_request(params: str):
    """模拟网站业务代码发起请求（它并不知道 Hook 存在）"""
    sign = window.getSign(params)
    print(f"  [业务] 发送请求: ?params={params}&sign={sign}")


if __name__ == "__main__":
    print("=" * 60)
    print("① Hook 之前：直接调用，什么都观察不到")
    print("=" * 60)
    business_request("page=1&size=20")

    print()
    print("=" * 60)
    print("② 注入 Hook 之后：入参/出参全部现形")
    print("=" * 60)
    hook_function(window, "getSign")
    business_request("page=2&size=20")

    print()
    print("=" * 60)
    print("③ 生成的真实 JS Hook 脚本（可粘贴到浏览器 Console）")
    print("=" * 60)
    js_hook = """(function () {
  var _orig = window.getSign;              // 备份原函数
  window.getSign = function () {
    console.log('[hook] getSign 入参:', arguments);
    var result = _orig.apply(this, arguments);
    console.log('[hook] getSign 出参:', result);
    debugger;                              // 冻结现场 -> 看 Call Stack
    return result;
  };
  console.log('[hook] getSign 已被 Hook');
})();"""
    print(js_hook)
