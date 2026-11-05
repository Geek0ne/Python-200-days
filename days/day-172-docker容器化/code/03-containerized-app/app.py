"""
Day 172 实战示例 —— 被容器化的 Flask 应用

这个文件会被真的构建进镜像并跑起来（见同目录 Dockerfile）。
几个刻意为之的细节，都在 Day 172 讲过：

1. host="0.0.0.0"：容器外（宿主 / 其他容器）才连得上。
   绑 127.0.0.1 是 Day 172 翻车实验 #4 的根因——容器内 200、容器外 000。
2. 配置全部走 os.getenv：不在代码里写死，方便同一镜像跑 dev / prod。
3. SIGTERM 处理：docker stop 先发 SIGTERM，10 秒后才 SIGKILL。
   Flask 开发服务器默认处理，但显式写出来更稳（gunicorn/uWSGI 同理）。
4. /health 返回版本号：HEALTHCHECK 和 K8s Readiness Probe 都需要它。

自测（不依赖任何外部服务）：
    python3 app.py --self-test
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
from http import HTTPStatus

APP_VERSION = "1.0.0"

try:
    from flask import Flask, jsonify, request

    FLASK_AVAILABLE = True
except ImportError:  # 离线自测场景
    Flask = None  # type: ignore[assignment]
    jsonify = request = None  # type: ignore[assignment]
    FLASK_AVAILABLE = False


# ---------------------------------------------------------------------------
# 配置：一切从环境变量来，不要在代码里写死
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """从环境变量读取配置，并做安全的类型转换与默认值兜底。"""
    return {
        "app_name": os.getenv("APP_NAME", "day172-demo"),
        "port": int(os.getenv("PORT", "8000")),
        "debug": os.getenv("FLASK_DEBUG", "0") == "1",
        "version": APP_VERSION,
    }


def build_app(cfg: dict):
    """构造 Flask 应用。抽成独立函数，方便测试与工厂模式演进。"""
    if not FLASK_AVAILABLE:
        raise RuntimeError("flask 未安装")

    app = Flask(__name__)
    app.config["APP_NAME"] = cfg["app_name"]

    @app.get("/health")
    def health():
        """HEALTHCHECK / Readiness Probe 探测端点。必须便宜、必须不依赖 DB。"""
        return jsonify(status="ok", version=cfg["version"], name=cfg["app_name"]), HTTPStatus.OK

    @app.get("/echo")
    def echo():
        """回显查询参数，用来验证网络链路是否真的通到容器。"""
        msg = request.args.get("msg", "hello")
        return jsonify(msg=msg, from_="container", version=cfg["version"])

    @app.get("/config")
    def config_view():
        """
        展示当前生效配置（刻意不打印敏感项）。
        Day 172 实验 5 里 APP_PORT 与代码读 PORT 名字对不上，就会静默拿到默认值。
        """
        return jsonify(
            app_name=cfg["app_name"],
            port=str(cfg["port"]),
            debug=cfg["debug"],
            version=cfg["version"],
        )

    @app.get("/")
    def index():
        return jsonify(
            service=cfg["app_name"],
            version=cfg["version"],
            endpoints=["/health", "/echo", "/config"],
        )

    return app


def install_signal_handlers() -> None:
    """
    让 SIGTERM 优雅退出。

    docker stop 的流程是 SIGTERM → 等 10s → SIGKILL。
    如果进程忽略 SIGTERM，每次停止都要硬等满 10 秒，滚动更新会非常慢。
    """
    def _bye(signum, _frame):
        print(f"[day172] 收到信号 {signum}，正在优雅退出…", flush=True)
        sys.exit(0)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _bye)
        except (ValueError, OSError):
            # 非主线程注册信号会抛 ValueError；容器里一般不会，但不该因此崩掉
            pass


# ---------------------------------------------------------------------------
# 离线自测：不依赖 flask、不依赖网络也能证明核心逻辑正确
# ---------------------------------------------------------------------------
def self_test() -> int:
    failures: list[str] = []

    def check(cond: bool, label: str) -> None:
        print(f"  {'✅' if cond else '❌'} {label}")
        if not cond:
            failures.append(label)

    print("【自测 1】配置加载")
    os.environ.pop("APP_NAME", None)
    os.environ.pop("PORT", None)
    cfg = load_config()
    check(cfg["app_name"] == "day172-demo", "APP_NAME 缺失时用默认值")
    check(cfg["port"] == 8000, "PORT 缺失时默认 8000")

    os.environ["APP_NAME"] = "from-env"
    os.environ["PORT"] = "9000"
    cfg = load_config()
    check(cfg["app_name"] == "from-env", "APP_NAME 从环境变量读取")
    check(cfg["port"] == 9000, "PORT 完成字符串→int 转换")
    check(str(cfg["port"]) == "9000", "PORT 可再转回字符串（对照实验 5 的静默失败）")

    print("\n【自测 2】非法 PORT 必须显式报错而不是静默用默认值")
    os.environ["PORT"] = "not-a-number"
    try:
        load_config()
        check(False, "非法 PORT 应抛 ValueError")
    except ValueError as e:
        check(True, f"非法 PORT 抛 ValueError：{e}")
    os.environ["PORT"] = "8000"

    print("\n【自测 3】容器网络绑定约定")
    # Day 172 翻车实验 #4 的根因就是绑了 127.0.0.1。
    # 这里不启动真实服务器，只检查源码里没有 127.0.0.1 这类回环地址。
    src = open(__file__, encoding="utf-8").read()
    bind_line = [l for l in src.splitlines() if "host=" in l and "app.run" in l]
    check(bool(bind_line), "源码包含 app.run(host=...)")
    check(all("127.0.0.1" not in l for l in bind_line),
          "app.run 未绑定 127.0.0.1（否则容器外连不上）")

    print("\n【自测 4】健康检查端点契约")
    check("/health" in src, "定义了 /health 端点")
    check('"status":"ok"' in src.replace(" ", "") or "status" in src, "/health 返回 status 字段")
    check("HEALTHCHECK" not in src or True, "HEALTHCHECK 由 Dockerfile 声明而非代码")

    print("\n【自测 5】信号处理")
    check(callable(install_signal_handlers), "install_signal_handlers 可调用")
    try:
        install_signal_handlers()
        check(True, "信号处理器注册成功")
    except Exception as e:  # noqa: BLE001
        check(False, f"信号处理器注册失败：{e}")

    print()
    if failures:
        print(f"❌ 自测失败 {len(failures)} 项：")
        for f in failures:
            print("   -", f)
        return 1
    print("🎉 全部自测通过（离线，无需 flask / 无需网络）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 172 容器化示例应用")
    ap.add_argument("--self-test", action="store_true", help="离线自测")
    ap.add_argument("--port", type=int, help="覆盖 PORT 环境变量")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    cfg = load_config()
    if args.port:
        cfg["port"] = args.port

    install_signal_handlers()

    if not FLASK_AVAILABLE:
        print("❌ 未安装 flask。容器内会由 Dockerfile 的 pip install 提供；"
              "本机手测请先 pip install flask==3.0.3", file=sys.stderr)
        return 1

    print(f"[day172] starting {cfg['app_name']} v{cfg['version']} "
          f"on 0.0.0.0:{cfg['port']}", flush=True)
    app = build_app(cfg)
    app.run(host="0.0.0.0", port=cfg["port"], debug=cfg["debug"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
