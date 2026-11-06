#!/usr/bin/env python3
"""
Day 181 — 发布管理
04 · 自动化发布流水线：tag -> 构建 -> 校验 -> 发布

手动发布的问题不是「麻烦」，而是**同一步骤在不同时间会做出不同结果**：
今天你记得先跑测试再传包，下个版本你可能就忘了；这次 tag 是 v1.2.3、
包里写的是 1.2.3，下次就成了 v1.2.4 + 1.2.3。
流水线的价值是**把顺序和一致性变成代码**，谁跑、什么时候跑，结果都一样。

本脚本把六步串起来，每一步失败都**在把包传出去之前**停下：

  1. 认 tag        v1.2.3 -> 1.2.3（SemVer 校验）
  2. 对版本        tag 的版本必须等于 pyproject / __init__ 里的版本（最常见事故）
  3. 查 CHANGELOG  有没有这一版的条目（没写就是没打算发布）
  4. 构建          wheel + sdist
  5. 校验          文件名/元数据/一致性（复用 03 的逻辑）
  6. 发布          上传到索引（PyPI / TestPyPI / 本地桩）

用法：
    python3 04-release-pipeline.py --self-test                    # 起本地桩，端到端全跑
    python3 04-release-pipeline.py --tag v1.2.3 --project ../mypkg --dry-run
    python3 04-release-pipeline.py --tag v1.2.3 --project ../mypkg --repository testpypi
"""

import argparse
import base64
import email
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 抓一份 hash 函数的引用放在模块级。原因见自检最后一步：
# 如果校验端在运行时去查 hashlib.sha256，那么测试里 patch("hashlib.sha256")
# 会把「发送端」和「校验端」同时 patch 掉，两边算出的错值一模一样，
# 「篡改摘要必须被发现」这条断言就永远成立 —— 一个自我麻醉的空测试。
_SHA256 = hashlib.sha256


def load_sibling(filename):
    """按路径加载同目录的脚本（文件名以数字开头，不能直接 import）。"""
    spec = importlib.util.spec_from_file_location(filename.replace("-", "_").rstrip(".py"), HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


semver = load_sibling("01-semver.py")
chlog = load_sibling("02-changelog.py")
builder = load_sibling("03-build-verify.py")


# --- 本地桩：一个最小的 PyPI 上传端点 ----------------------------------------
class UploadIndex:
    """记录上传，并按 PyPI 的 legacy upload 协议校验。

    它存在的意义：**在没有凭据、也不想真的把包发出去的情况下，
    证明「上传这一步」真的跑通过**——包括 multipart 编码、Basic 认证头、
    sha256 校验、文件名解析。桩只实现协议里被用到的部分，其余不猜。
    """

    def __init__(self):
        self.received = []          # [{name, version, filename, size, sha256}]
        self.rejected = []          # [{filename, reason}]

    def handler(self, results):
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self):
                body = json.dumps({"releases": outer.received}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                auth = self.headers.get("Authorization", "")
                if not auth.startswith("Basic "):
                    return self._fail(403, "缺少 Basic 认证头")
                try:
                    user, _, secret = base64.b64decode(auth[6:]).decode().partition(":")
                except Exception:
                    return self._fail(403, "认证头无法解码")
                if user != "__token__" or not secret.startswith("pypi-"):
                    return self._fail(403, "token 形态不对（应为 __token__:pypi-...）")

                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length)
                ctype = self.headers.get("Content-Type", "")
                msg = email.message_from_bytes(
                    b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + raw)
                fields, files = {}, {}
                for part in msg.walk():
                    if part.get_content_maintype() == "multipart":
                        continue
                    disp = part.get("Content-Disposition", "")
                    name = part.get_param("name", header="content-disposition")
                    if "filename" in disp:
                        files[name] = (part.get_filename(), part.get_payload(decode=True))
                    else:
                        fields[name] = (part.get_payload(decode=True) or b"").decode("utf-8", "replace")

                if fields.get(":action") != "file_upload":
                    return self._fail(400, "缺少 :action=file_upload")
                if "content" not in files:
                    return self._fail(400, "缺少 content 字段")
                filename, data = files["content"]
                digest = _SHA256(data).hexdigest()
                if fields.get("sha256_digest") != digest:
                    # 这是桩的核心断言：传输损坏 / 传错文件必须被发现
                    outer.rejected.append({"filename": filename, "reason": "sha256 不匹配"})
                    return self._fail(400, "sha256_digest 与实际内容不符")
                meta = fields.get("metadata", "")
                meta_name = next((l.split(": ", 1)[1] for l in meta.splitlines()
                                  if l.startswith("Name: ")), "")
                meta_ver = next((l.split(": ", 1)[1] for l in meta.splitlines()
                                 if l.startswith("Version: ")), "")
                outer.received.append({
                    "name": meta_name, "version": meta_ver, "filename": filename,
                    "size": len(data), "sha256": digest[:16],
                })
                body = json.dumps({"message": "OK"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                results["uploads"] = outer.received

            def _fail(self, code, why):
                body = json.dumps({"message": why}).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        return H


def upload_artifact(url, path, token, metadata, repository="pypi", timeout=20):
    """按 PyPI 的 legacy upload 协议上传一个文件（stdlib 实现，不需要 twine）。"""
    path = Path(path)          # 允许传 str，省得调用方自己转
    data = path.read_bytes()
    boundary = "----day181" + uuid.uuid4().hex
    filetype = "bdist_wheel" if path.suffix == ".whl" else "sdist"
    pyversion = "py3" if path.suffix == ".whl" else "source"
    fields = {
        ":action": "file_upload",
        "protocol_version": "1",
        "name": metadata.get("Name", ""),
        "version": metadata.get("Version", ""),
        "filetype": filetype,
        "pyversion": pyversion,
        "metadata": "\n".join(f"{k}: {v}" for k, v in metadata.items()) + "\n",
        "sha256_digest": hashlib.sha256(data).hexdigest(),
    }
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"content\"; "
        f"filename=\"{path.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode())
    parts.append(data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Content-Length", str(len(body)))
    # 用户名固定 __token__，密码才是 token —— 这是 PyPI 的约定，忘了会 403
    req.add_header("Authorization",
                   "Basic " + base64.b64encode(f"__token__:{token}".encode()).decode())
    req.add_header("User-Agent", f"day181-release-pipeline/1.0 ({repository})")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return 0, f"网络不可达：{e.reason}"


def read_project_version(project: Path):
    """读 pyproject 里的版本号（[project] version）。"""
    import tomllib
    with open(project / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data.get("project", {}).get("version")


REPOSITORIES = {
    "pypi": "https://upload.pypi.org/legacy/",
    "testpypi": "https://test.pypi.org/legacy/",
}


def pipeline(tag, project, dist, repository, token, out, dry_run=False):
    """跑完六步。返回 (成功?, 统计)。"""
    stats = {}
    t_all = time.time()

    # 1. 认 tag
    t0 = time.time()
    version = tag[1:] if tag.startswith("v") else tag
    semver.parse(version)
    out(f"[1/6] tag {tag} -> 版本 {version} · SemVer 合法 ({int((time.time()-t0)*1000)} ms)")

    # 2. 对版本：tag 与包里写的是不是同一个
    proj_ver = read_project_version(project)
    out(f"[2/6] pyproject version = {proj_ver}")
    if proj_ver != version:
        out(f"  ❌ tag 与包内版本不一致（{version} != {proj_ver}）—— "
            f"这一步不拦，PyPI 上会出现一个跟 git tag 对不上的版本")
        return False, stats

    # 3. CHANGELOG
    cl = project / "CHANGELOG.md"
    if cl.exists():
        problems, st = chlog.lint(cl.read_text(encoding="utf-8"))
        out(f"[3/6] CHANGELOG {cl.name}: {st['版本段']} 个版本段，{len(problems)} 个问题")
        if problems:
            for p in problems:
                out(f"  ❌ {p}")
            return False, stats
    else:
        out(f"[3/6] 没有 {cl.name}，跳过（正式项目应强制要求）")

    # 4. 构建
    dist.mkdir(parents=True, exist_ok=True)
    for old in builder.collect(dist):
        old.unlink()
    rc, ms, backend = builder.do_build(project, dist, out)
    out(f"[4/6] 构建 backend={backend} 耗时={ms} ms rc={rc}")
    if rc != 0:
        return False, stats
    arts = builder.collect(dist)
    stats["artifacts"] = [a.name for a in arts]

    # 5. 校验
    ok, nprob = builder.verify(arts, out)
    out(f"[5/6] 校验 {'通过' if ok else '失败'}（{nprob} 个问题）")
    if not ok:
        return False, stats

    # 6. 发布
    if dry_run or repository == "none":
        out("[6/6] --dry-run / 未指定仓库：不发布。真实执行时会做：")
        for a in arts:
            out(f"        POST {REPOSITORIES.get(repository, '<url>')}"
                f"  file={a.name}  Authorization: Basic __token__:***")
        stats["uploaded"] = []
        return True, stats

    url = REPOSITORIES.get(repository)
    if url is None:
        out(f"  ❌ 未知仓库 {repository}（可选：{' / '.join(REPOSITORIES)} / none）")
        return False, stats
    if not token:
        out(f"  ❌ 环境变量 {TOKEN_ENV} 里没有 token，拒绝尝试上传。"
            f"（宁可明确失败，也不要发一个半成品到公开索引）")
        return False, stats

    uploaded = []
    for a in arts:
        fields, _ = builder.read_metadata(a)
        code, body = upload_artifact(url, a, token, fields, repository)
        mark = "✅" if code == 200 else "❌"
        out(f"[6/6] {mark} {a.name} -> HTTP {code} {body.strip()[:120]}")
        if code != 200:
            return False, stats
        uploaded.append(a.name)
    stats["uploaded"] = uploaded
    stats["total_ms"] = int((time.time() - t_all) * 1000)
    out(f"# 全流程 {stats['total_ms']} ms")
    return True, stats


TOKEN_ENV = "DAY181_INDEX_TOKEN"


def self_test():
    tmp = Path(tempfile.mkdtemp(prefix="day181-pipeline-"))
    out_lines = []

    def out(s):
        out_lines.append(s)
        print(s)

    index = UploadIndex()
    results = {}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), index.handler(results))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/legacy/"
    try:
        project = builder.make_demo_project(tmp / "proj", version="1.2.3")
        # 3 步依赖的 CHANGELOG 也造一份，让「查 CHANGELOG」这步真的跑
        (project / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [Unreleased]\n\n## [1.2.3] - 2026-10-16\n\n### Added\n\n- 首个版本\n",
            encoding="utf-8")
        dist = tmp / "dist"

        # 正例：tag 与包内版本一致 -> 应全绿
        ok, stats = pipeline("v1.2.3", project, dist, "none", "", out, dry_run=True)
        assert ok, "tag 与版本一致时流水线不该失败"
        assert len(stats["artifacts"]) == 2

        # 负例 1：tag 与包内版本不一致 -> 必须在构建之前就停
        ok2, _ = pipeline("v9.9.9", project, dist, "none", "", lambda s: None, dry_run=True)
        assert ok2 is False, "版本不一致居然没被拦住"
        out("# 反向验证：tag=v9.9.9 而包内是 1.2.3 -> 第 2 步拦下（未构建、未上传）")

        # 负例 2：没有 token -> 拒绝上传
        ok3, _ = pipeline("v1.2.3", project, dist, "testpypi", "", lambda s: None)
        assert ok3 is False, "没有 token 居然还想上传"
        out("# 反向验证：无 token 时拒绝上传（fail closed，不是 fail open）")

        # 正例 2：真上传到本地桩（token 是假的，桩只校验形态）
        fake_token = "pypi-" + "A" * 20
        REPOSITORIES["_stub"] = url
        try:
            ok4, stats4 = pipeline("v1.2.3", project, dist, "_stub", fake_token, out)
        finally:
            del REPOSITORIES["_stub"]
        assert ok4, "上传到本地桩失败"
        assert len(results["uploads"]) == 2, results
        names = sorted(u["filename"] for u in results["uploads"])
        # 只断言「两种文件各一个」，不要断言排序后的先后 ——
        # 按文件名排序时 .whl 排在 .tar.gz 前面（'p' < 't'），
        # 之前写成 names[0].endswith(".tar.gz") 就是我自己的想当然
        assert any(n.endswith(".tar.gz") for n in names), names
        assert any(n.endswith(".whl") for n in names), names
        for u in results["uploads"]:
            assert u["name"] == "demo-release-pkg" and u["version"] == "1.2.3", u
        out(f"# 桩收到的上传：{json.dumps(results['uploads'], ensure_ascii=False)}")

        # 负例 3：桩的 sha256 校验不是摆设 —— 篡改 digest 必须 400
        good = builder.collect(dist)[0]
        fields, _ = builder.read_metadata(good)
        import unittest.mock as mock
        real_sha = hashlib.sha256
        calls = {"n": 0}

        def bad_sha_factory(data=b""):
            calls["n"] += 1
            h = real_sha(data)
            h.update(b"x")          # 让 digest 与实际内容不符
            return h
        with mock.patch("hashlib.sha256", side_effect=bad_sha_factory):
            code, body = upload_artifact(url, good, fake_token, fields, "_stub")
        assert code == 400, f"篡改 digest 后桩仍返回 {code}，说明校验是假的"
        assert index.rejected, "桩没有记录这次拒绝"
        out(f"# 反向验证：把 sha256 改坏后桩返回 HTTP {code}（{body.strip()}）")

        print("✅ self-test 通过：六步全跑通（含真上传到本地桩）；"
              "版本不一致/无 token/摘要不符 三种坏情况都被拦下")
        return 0
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"# 已清理临时目录 {tmp}")


def main():
    ap = argparse.ArgumentParser(description="Day 181 · 04 发布流水线")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--tag", help="git tag，如 v1.2.3")
    ap.add_argument("--project", help="项目根目录")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--repository", default="none", choices=sorted(REPOSITORIES) + ["none"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.tag or not args.project:
        ap.error("需要 --tag 与 --project（或 --self-test）")
    token = os.environ.get(TOKEN_ENV, "")
    print(f"# token 来源：环境变量 {TOKEN_ENV}（{'已设置，长度 ' + str(len(token)) if token else '未设置'}）")
    ok, stats = pipeline(args.tag, Path(args.project).resolve(), Path(args.dist).resolve(),
                         args.repository, token, print, dry_run=args.dry_run)
    print(f"# 结论：{'✅ 可以发布' if ok else '❌ 流水线中断（未发布）'} {json.dumps(stats, ensure_ascii=False)}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
