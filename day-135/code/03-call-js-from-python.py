#!/usr/bin/env python3
"""
03 - 定位加密参数并复现（实战案例）
===================================
完整链路：模拟逆向得到的 JS 算法 -> 摘出为独立 .js 文件 ->
Python subprocess 调 Node 执行 -> 与纯 Python 复现互相验证。

模拟场景（逆向结论）：
  app.js 第 1204 行:
    function genSign(page) { return md5(String(page) + "salt123"); }

运行：python3 03-call-js-from-python.py
依赖：系统需安装 node（node --version 验证）
"""
import hashlib
import json
import shutil
import subprocess
import tempfile
import os

JS_CODE = r"""
// 摘出的原始算法（从 app.js 逆向提取，保持原样以便算法升级时替换）
// md5 实现：Node 内置 crypto
var crypto = require('crypto');
function genSign(page) {
    return crypto.createHash('md5')
                 .update(String(page) + 'salt123')
                 .digest('hex');
}
// stdin 读取 JSON 参数，stdout 输出 JSON 结果（通用调用协议）
var input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
console.log(JSON.stringify({ sign: genSign(input.page) }));
"""

def call_js(page: int) -> str:
    """subprocess 调用 Node 执行摘出的 JS -- 逆向工程标准落地方式"""
    if shutil.which("node") is None:
        raise RuntimeError("未安装 node，请先 apt install nodejs / brew install node")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(JS_CODE)
        path = f.name
    try:
        r = subprocess.run(
            ["node", path],
            input=json.dumps({"page": page}),
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            raise RuntimeError(f"Node 执行失败: {r.stderr}")
        return json.loads(r.stdout)["sign"]
    finally:
        os.unlink(path)

def py_sign(page: int) -> str:
    """纯 Python 复现同一算法（逆向充分理解后的终极形态）"""
    return hashlib.md5(f"{page}salt123".encode()).hexdigest()

if __name__ == "__main__":
    print("== 逆向落地三步验证 ==\n")
    all_ok = True
    for page in (1, 10, 999):
        js_result = call_js(page)
        py_result = py_sign(page)
        ok = js_result == py_result
        all_ok &= ok
        print(f"  page={page:<5} JS版: {js_result}")
        print(f"  {'':<10} Py版: {py_result}   {'✅ 一致' if ok else '❌ 不一致!'}\n")

    print("结论:")
    print("  1. subprocess + Node：算法原样保留，站点升级 JS 时直接替换文件，维护成本最低")
    print("  2. 纯 Python 复现：性能最好，适合算法稳定且简单时（如本例 md5）")
    print("  3. 复杂算法（自定义 VM 混淆、WebAssembly）只能走 Node/浏览器执行路线")

    if not all_ok:
        raise SystemExit("❌ 两版实现不一致，检查逆向结果!")
    print("\n✅ 全部验证通过")
