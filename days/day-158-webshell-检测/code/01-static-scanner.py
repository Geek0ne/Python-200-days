"""实战演练：真实特征样本集的静态扫描与评分定级。

样本集中保留了实战常见的真实特征（命令执行、动态求值、编码混淆），
载荷部分使用占位符，保证不可直接作为后门部署。本脚本只做只读扫描。
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

        # 评分函数与分级一致性
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