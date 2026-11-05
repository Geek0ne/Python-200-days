#!/usr/bin/env python3
"""
Day 181 — 发布管理
03 · 构建与校验：sdist / wheel 是怎么来的，怎么验

发布链路上最容易「看着成功了其实坏了」的一步就是构建：
文件生成了、名字也对，但版本号写死在代码里、README 渲染报错、
sdist 和 wheel 的版本不一致——这些都要靠**解析产物本身**来发现，
而不是靠「build 命令退出码是 0」。

本脚本做三件事：
  1. 构建：优先用官方 python -m build（PEP 517 前端）；
     **没装 build 时自动降级**到 setuptools 的 PEP 517 后端 build_meta 直接调，
     所以离线、无第三方依赖的环境也能真出一份产物；
  2. 校验：从产物**反读**元数据（wheel 里的 *.dist-info/METADATA、
     sdist 里的 PKG-INFO），断言两边的 Name/Version 一致；
     装了 twine 就顺带跑 twine check；
  3. 量化：打印每个产物的字节数、sha256、构建耗时。

用法：
    python3 03-build-verify.py --self-test                 # 临时建一个包，真构建真校验
    python3 03-build-verify.py --project ../mypkg --out dist
    python3 03-build-verify.py --project ../mypkg --out dist --dry-run
"""

import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

DEMO_PYPROJECT = """\
[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-release-pkg"
version = "1.2.3"
description = "Day 181 演示包：只用来验证构建与校验链路"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}

[tool.setuptools.packages.find]
where = ["src"]
"""

DEMO_INIT = '''\
"""Day 181 演示包。"""

__version__ = "1.2.3"


def greet(who="world"):
    return f"hello, {who}"
'''

DEMO_README = "# demo-release-pkg\n\nDay 181 构建演示用的最小包。\n"


def make_demo_project(root: Path, version="1.2.3"):
    """在 root 下建一个最小可构建项目（src 布局 + pyproject）。"""
    (root / "src" / "demo_pkg").mkdir(parents=True, exist_ok=True)
    pyproject = DEMO_PYPROJECT.replace('version = "1.2.3"', f'version = "{version}"')
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (root / "src" / "demo_pkg" / "__init__.py").write_text(
        DEMO_INIT.replace('"1.2.3"', f'"{version}"'), encoding="utf-8")
    (root / "README.md").write_text(DEMO_README, encoding="utf-8")
    return root


def run(cmd, cwd=None):
    """跑一条命令，返回 (退出码, stdout+stderr)。"""
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def have_module(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def build_with_frontend(project: Path, outdir: Path, isolation=False):
    """官方路径：python -m build（PEP 517 前端，会建隔离环境）。"""
    cmd = [sys.executable, "-m", "build", "--outdir", str(outdir)]
    if not isolation:
        cmd.insert(3, "--no-isolation")   # 不建隔离环境：离线也能跑，快
    cmd.append(str(project))
    t0 = time.time()
    rc, out = run(cmd)
    return rc, out, int((time.time() - t0) * 1000), "build-frontend"


def build_with_backend(project: Path, outdir: Path):
    """降级路径：直接调 PEP 517 后端（setuptools.build_meta）。

    build 前端只是个「替你建隔离环境 + 调后端」的壳；壳不在，
    后端本身还在（setuptools 是 Python 装机自带），所以构建能力并不丢。
    代价：只支持 setuptools 后端，且不做环境隔离（--isolation 才有意义）。
    """
    if not have_module("setuptools"):
        raise RuntimeError("既没有 build 也没有 setuptools，无法构建")
    outdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cwd = os.getcwd()
    os.chdir(project)                      # build_meta 以 cwd 作为项目根
    try:
        import setuptools.build_meta as bm
        sdist = bm.build_sdist(str(outdir))
        wheel = bm.build_wheel(str(outdir))
    finally:
        os.chdir(cwd)
    ms = int((time.time() - t0) * 1000)
    return 0, f"sdist: {sdist}\nwheel: {wheel}\n", ms, "setuptools-backend"


def normalize_name(name):
    """PEP 503 归一化：小写，并把连续的 - _ . 都压成单个 -。

    不归一化就会踩这个坑：sdist 文件名里是 demo_release_pkg，
    wheel/METADATA 里是 demo-release-pkg，其实是同一个包，字符串却不等。
    """
    return re.sub(r"[-_.]+", "-", name).lower()


WHEEL_RE = re.compile(
    r"^(?P<name>[^-]+)-(?P<version>[^-]+)"
    r"(?:-(?P<build>\d[^-]*))?-(?P<py>[^-]+)-(?P<abi>[^-]+)-(?P<plat>[^-]+)\.whl$"
)
SDIST_RE = re.compile(r"^(?P<name>.+)-(?P<version>[^-]+)\.tar\.gz$")


def parse_artifact(path: Path):
    """从**文件名**反读 name/version —— 这是 PEP 427 / PEP 625 规定的。

    文件名校验很重要：PyPI 只认文件名，名字里版本错了，
    在索引上就是一个新包/新版本，本地再怎么测都白搭。
    """
    if path.suffix == ".whl":
        m = WHEEL_RE.match(path.name)
        if not m:
            return {"kind": "wheel", "ok": False, "why": "文件名不符合 PEP 427"}
        d = m.groupdict()
        return {"kind": "wheel", "ok": True, "name": normalize_name(d["name"]),
                "version": d["version"], "py": d["py"], "abi": d["abi"], "plat": d["plat"]}
    if path.name.endswith(".tar.gz"):
        m = SDIST_RE.match(path.name)
        if not m:
            return {"kind": "sdist", "ok": False, "why": "文件名不符合 PEP 625"}
        d = m.groupdict()
        return {"kind": "sdist", "ok": True, "name": normalize_name(d["name"]),
                "version": d["version"]}
    return {"kind": path.suffix, "ok": False, "why": "既不是 wheel 也不是 sdist"}


def read_metadata(path: Path):
    """从产物内部反读元数据：wheel = *.dist-info/METADATA；sdist = 顶层 PKG-INFO。"""
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            meta = next((n for n in names if n.endswith(".dist-info/METADATA")), None)
            if not meta:
                return {}, []
            fields = {}
            for line in z.read(meta).decode("utf-8", "replace").splitlines():
                if not line.strip():
                    break                       # 空行之后是 description 正文
                if ": " in line:
                    k, v = line.split(": ", 1)
                    fields[k] = v
            return fields, names
    with tarfile.open(path) as t:
        member = next((m for m in t.getmembers() if m.name.count("/") == 1
                       and m.name.endswith("PKG-INFO")), None)
        if not member:
            return {}, [m.name for m in t.getmembers()]
        text = t.extractfile(member).read().decode("utf-8", "replace")
        fields = {}
        for line in text.splitlines():
            if not line.strip():
                break
            if ": " in line:
                k, v = line.split(": ", 1)
                fields[k] = v
        return fields, [m.name for m in t.getmembers()]


def sha256(path: Path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(artifacts, out):
    """校验一批产物。返回 (是否全部通过, 行数)。"""
    problems = []
    meta_by_kind = {}
    for p in artifacts:
        info = parse_artifact(p)
        size = p.stat().st_size
        digest = sha256(p)
        out(f"{info['kind']:6s} {p.name}")
        out(f"       字节={size}  sha256={digest[:16]}…")
        if not info["ok"]:
            problems.append(f"{p.name}: {info['why']}")
            continue
        fields, names = read_metadata(p)
        out(f"       METADATA Name={fields.get('Name')} Version={fields.get('Version')}"
            f"  Requires-Python={fields.get('Requires-Python')}  内含文件={len(names)}")
        if normalize_name(fields.get("Name", "")) != info["name"]:
            problems.append(f"{p.name}: 文件名里的名字 {info['name']} 与元数据 "
                            f"{fields.get('Name')} 不一致")
        if fields.get("Version") != info["version"]:
            problems.append(f"{p.name}: 文件名版本 {info['version']} 与元数据 "
                            f"{fields.get('Version')} 不一致")
        for must in ("Name", "Version", "Summary", "Requires-Python"):
            if must not in fields:
                problems.append(f"{p.name}: 元数据缺 {must}")
        meta_by_kind[info["kind"]] = info
    if "wheel" in meta_by_kind and "sdist" in meta_by_kind:
        if meta_by_kind["wheel"]["version"] != meta_by_kind["sdist"]["version"]:
            problems.append("wheel 与 sdist 版本号不一致（发布到 PyPI 会裂成两个版本）")
    else:
        problems.append(f"缺少 wheel 或 sdist（只有 {sorted(meta_by_kind)}）")
    for pr in problems:
        out(f"  ❌ {pr}")
    if not problems:
        out("  ✅ 文件名、内部元数据、wheel/sdist 版本一致，四项必填字段齐全")
    return not problems, len(problems)


def twine_check(dist: Path, out):
    if not have_module("twine"):
        out("  twine 未安装 → 跳过 twine check（上面是内置校验，覆盖的是同一批事实："
            "文件名 + 元数据一致性）")
        return None
    rc, log = run([sys.executable, "-m", "twine", "check", *sorted(str(p) for p in dist.iterdir())])
    for line in log.strip().splitlines():
        out(f"  {line}")
    return rc == 0


def do_build(project: Path, dist: Path, out, isolation=False):
    backend = None
    if have_module("build"):
        rc, log, ms, backend = build_with_frontend(project, dist, isolation)
    else:
        out("  build 未安装 → 降级用 setuptools.build_meta 后端直接构建")
        rc, log, ms, backend = build_with_backend(project, dist)
    for line in log.strip().splitlines():
        out(f"  | {line}")
    return rc, ms, backend


def collect(dist: Path):
    return sorted(p for p in dist.iterdir()
                  if p.suffix == ".whl" or p.name.endswith(".tar.gz"))


def self_test():
    tmp = Path(tempfile.mkdtemp(prefix="day181-build-"))
    lines = []
    def out(s):
        lines.append(s)
        print(s)
    try:
        project = make_demo_project(tmp / "proj", version="1.2.3")
        dist = tmp / "dist"
        out(f"# 自检：临时项目 {project}")
        rc, ms, backend = do_build(project, dist, out)
        assert rc == 0, f"构建失败 rc={rc}"
        arts = collect(dist)
        assert len(arts) == 2, f"应该有 wheel + sdist 两个产物，得到 {[a.name for a in arts]}"
        out(f"# 构建后端={backend}  耗时={ms} ms")
        ok, nprob = verify(arts, out)
        assert ok, f"校验未通过（{nprob} 个问题）"

        # 断言「校验器真的会发现问题」——不然它只是个安慰剂。
        # 做法：把 wheel 的**文件名版本**改成 9.9.9（内容一个字节不动）。
        wheel = next(a for a in arts if a.suffix == ".whl")
        wrong = dist / wheel.name.replace("-1.2.3-", "-9.9.9-")
        shutil.copy(wheel, wrong)
        _, n2 = verify(collect(dist), lambda s: None)
        assert n2 >= 1, "改名成错版本号的 wheel 居然没被校验器发现"
        out(f"# 反向验证：多放一个只改了文件名版本号的 {wrong.name}，"
            f"校验器报出 {n2} 个问题（符合预期）")
        wrong.unlink()

        sizes = {a.name: a.stat().st_size for a in arts}
        out(f"# 产物体积：{sizes}")
        twine_check(dist, out)
        print("✅ self-test 通过：真构建出 wheel+sdist，元数据一致，且校验器能抓出人名错误")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"# 已清理临时目录 {tmp}")


def main():
    ap = argparse.ArgumentParser(description="Day 181 · 03 构建与校验")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--project", help="项目根目录（含 pyproject.toml）")
    ap.add_argument("--out", default="dist", help="产物输出目录")
    ap.add_argument("--isolation", action="store_true", help="让 build 建隔离环境（需联网）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要做什么")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    if not args.project:
        ap.error("需要 --project 或 --self-test")
    project, dist = Path(args.project).resolve(), Path(args.out).resolve()
    if not (project / "pyproject.toml").exists():
        print(f"❌ {project}/pyproject.toml 不存在")
        sys.exit(2)
    has_build, has_twine = have_module("build"), have_module("twine")
    print(f"# 项目={project}")
    print(f"# 输出={dist}")
    print(f"# 工具：build={'有' if has_build else '无（将降级到 setuptools 后端）'} · "
          f"twine={'有' if has_twine else '无（跳过 twine check）'}")
    if args.dry_run:
        print("# --dry-run：不构建、不写盘。真实执行时会：")
        print("#   1) python -m build --no-isolation --outdir dist <project>")
        print("#   2) 解析产物文件名与 METADATA/PKG-INFO，断言版本一致")
        print("#   3) twine check dist/*（若已安装）")
        return
    dist.mkdir(parents=True, exist_ok=True)
    for old in collect(dist):
        old.unlink()
    rc, ms, backend = do_build(project, dist, print)
    print(f"# 构建后端={backend} 耗时={ms} ms 退出码={rc}")
    if rc != 0:
        sys.exit(rc)
    arts = collect(dist)
    ok, nprob = verify(arts, print)
    twine_check(dist, print)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
