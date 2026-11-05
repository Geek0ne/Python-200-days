#!/usr/bin/env python3
"""Day 163 · 进阶用法与避坑：反射型 XSS 检测的四个判定层次。

运行（默认在本机回环靶标上做实验，不碰任何外部目标）：

    python3 02-xss-detect.py

这个脚本回答四个问题——它们正好构成 XSS 检测的**四层判定**：

```text
第 1 层  反射确认    输入到底有没有回到响应里？      → reflected
第 2 层  转义判定    回来的是原样字节还是 HTML 实体？ → raw_tag / escaped
第 3 层  上下文判定  回在文本节点、属性、还是 <script> 里？ → context
第 4 层  缓解措施    CSP / nosniff / charset 有没有？ → mitigations
```

**只有四层都看完，才能给出"严重度 + 置信度"。** 任何一层被跳过，
结论都会失真：

* 只做第 1 层 → 把"回显"当"漏洞"（`/echo` 就是专治这个的假阳性陷阱）；
* 跳过第 2 层 → 把"已转义"当"已注入"（安全对照 `/safe-search` 会误报）；
* 跳过第 3 层 → 把所有反射都评成同一个严重度（文本节点和 `<script>` 差一级）；
* 跳过第 4 层 → 漏掉"注入成立后有没有兜底"这个关键判断。

## 为什么探针**不是**可执行载荷（本课最重要的避坑点）

新手最容易写出的探针是 `<script>alert(1)</script>`。本课刻意**不用**它，理由有三：

1. **没必要**：检测只需要证明"危险字符原样进入了 HTML"，
   判断依据是**响应体里的字节**，不需要浏览器真的执行；
2. **有副作用**：一旦有任何人（包括你自己后续用浏览器复核）打开那个 URL，
   脚本就会在**你的**浏览器上下文里执行——从"只读审计"变成"真的攻击了自己"；
3. **会被 WAF/浏览器拦**：`<script>` 是最先被过滤/拦截的模式，
   测出来的"安全"其实只是"被挡了"，反而掩盖真实缺陷。

所以本课探针是 `zq163x7"'><zq163>`：唯一标记 + 破引号 + 破标签 +
一个**自定义标签** `<zq163>`（浏览器不认识，不会执行，但能证明标签注入成立）。

⚠️ 边界：只发 GET、只做检测、每参数最多 2 个探针、默认限速 2 请求/秒。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vuln_core import (  # noqa: E402
    XSS_MARKER,
    XSS_PROBE,
    LabVulnHTTP,
    check_xss_mitigations,
    default_lab_scope,
    detect_xss,
    fetch,
)

PORT = 18087


def show(title: str, url: str, scope) -> object:
    """跑一次 XSS 检测并逐层打印四个判定层次。"""
    print(f"\n{'=' * 72}\n{title}\n  URL: {url}\n{'=' * 72}")

    # 额外发一次请求，用于展示"响应里到底长什么样"（检测器内部也会发一次）
    raw = fetch(url)
    print(f"  [原始响应] status={raw.status} len={raw.length} "
          f"content-type={raw.headers.get('Content-Type', '—')}")

    result = detect_xss(url, scope, rate=20)

    print(f"  探针      : {result.probe!r}")
    print(f"  ① 反射确认: reflected={result.reflected} "
          f"（标记 {XSS_MARKER!r} {'出现' if result.reflected else '未出现'}在响应中）")
    print(f"  ② 转义判定: raw_tag={result.raw_tag}  raw_full={result.raw_full}  "
          f"escaped={result.escaped}")
    print(f"  ③ 上下文  : {result.context}")
    print(f"  ④ 缓解措施: {len(result.mitigations)} 项缺口")
    for m in result.mitigations:
        print(f"              · {m}")
    print(f"  → 严重度  : {result.severity}   置信度: {result.confidence}")
    print(f"  → 结论    : {result.risk_note}")
    return result


def main() -> int:
    print("探针（非可执行载荷）:", repr(XSS_PROBE))
    print("  说明：<zq163> 是自定义标签，浏览器不执行；它只用来证明「标签注入成立」。")

    with LabVulnHTTP(port=PORT) as lab:
        scope = default_lab_scope(lab.port)
        base = f"http://127.0.0.1:{lab.port}"

        # ① 有缺陷：原样反射进文本节点
        r1 = show("① 有缺陷 /search（反射进文本节点）", f"{base}/search?q=hello", scope)
        assert r1.reflected and r1.raw_tag and r1.context == "text_node", r1
        assert r1.severity == "medium", r1

        # ② 有缺陷：反射进双引号属性内
        r2 = show("② 有缺陷 /profile（反射进双引号属性）", f"{base}/profile?name=ops", scope)
        assert r2.context == "attr_quoted_double" and r2.severity == "medium", r2

        # ③ 最危险：反射进 <script> 块 → 闭合字符串即可执行
        r3 = show("③ 最危险 /greeting（反射进 <script> 块）", f"{base}/greeting?name=ops", scope)
        assert r3.context == "script_block" and r3.severity == "high", r3

        # ④ 反射进 HTML 注释 → 严重度更低（要先闭合注释）
        r4 = show("④ 上下文 /comment（反射进 HTML 注释）", f"{base}/comment?note=hi", scope)
        assert r4.context == "html_comment" and r4.severity == "low", r4

        # ⑤ 安全对照：转义 + CSP → 检测器必须沉默
        r5 = show("⑤ 安全对照 /safe-search（html.escape + CSP）", f"{base}/safe-search?q=hi", scope)
        assert not r5.raw_tag and r5.escaped, r5
        assert r5.mitigations == [], f"安全对照不应缺缓解措施: {r5.mitigations}"

        # ⑥ 假阳性陷阱：原样回显但已转义
        r6 = show("⑥ 假阳性陷阱 /echo（回显但已转义）", f"{base}/echo?id=hi", scope)
        assert not r6.raw_tag and r6.escaped, r6

        # ⑦ 缓解措施缺口本身也是一条独立发现
        print(f"\n{'=' * 72}\n⑦ 缓解措施缺口单独看：头部缺失=事实，不是结论\n{'=' * 72}")
        for path_label, url in (("有缺陷 /search", f"{base}/search?q=hi"),
                                ("安全 /safe-search", f"{base}/safe-search?q=hi")):
            res = fetch(url)
            missing = check_xss_mitigations(res.headers)
            print(f"  {path_label:<20} 缺口 {len(missing)} 项")
            for m in missing:
                print(f"      · {m}")
        print("  注意：缺头**不等于**有洞——它的意义是「注入一旦成立，没有纵深防御兜底」。")

    print("\n[结论] 四层判定缺一不可：")
    print("  ① 只确认反射   → /echo 会误报")
    print("  ② 加上转义判定 → /echo 与 /safe-search 沉默（假阳性被消掉）")
    print("  ③ 加上上下文   → 严重度分级：script_block(high) > 文本节点/属性(medium) > 注释(low)")
    print("  ④ 加上缓解措施 → 产出「注入成立后有没有兜底」的独立发现")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
