"""
Day 062 — 配置管理：分层加载（默认值 < 配置文件 < 环境变量）
运行方式：python 04-config-management.py --self-test
"""
import json
import os
import sys


def load_dotenv_file(path=".env"):
    """零依赖的 dotenv 风格解析：KEY=VALUE，# 注释，不覆盖已有环境变量"""
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip().strip("'\"")
    return values


def env_overrides(environ, prefix="APP_"):
    """环境变量覆盖层：APP_DB_HOST → db_host"""
    out = {}
    for k, v in environ.items():
        if k.startswith(prefix):
            out[k[len(prefix):].lower()] = v
    return out


def load_config(defaults, config_file=None, environ=None, prefix="APP_"):
    """分层合并：defaults < config_file(JSON) < 环境变量"""
    cfg = dict(defaults)
    if config_file and os.path.exists(config_file):
        with open(config_file, encoding="utf-8") as f:
            cfg.update(json.load(f))
    cfg.update(env_overrides(environ or os.environ, prefix))
    return cfg


DEFAULTS = {"db_host": "localhost", "db_port": 5432, "debug": False}


def self_test():
    import tempfile

    # 1. dotenv 解析
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as f:
        f.write("# comment\nDB_HOST=10.0.0.1\nAPI_KEY='sk-test'\nBADLINE\n")
        env_path = f.name
    vals = load_dotenv_file(env_path)
    assert vals == {"DB_HOST": "10.0.0.1", "API_KEY": "sk-test"}, vals
    os.unlink(env_path)

    # 2. 三层优先级：默认值 < 配置文件 < 环境变量
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"db_host": "cfg-host", "debug": True}, f)
        cfg_path = f.name
    cfg = load_config(DEFAULTS, cfg_path, environ={"APP_DB_HOST": "env-host", "APP_DB_PORT": "6543"})
    assert cfg["db_host"] == "env-host", f"环境变量应胜出: {cfg}"
    assert cfg["db_port"] == "6543", f"环境变量覆盖: {cfg}"
    assert cfg["debug"] is True, f"配置文件覆盖默认值: {cfg}"
    os.unlink(cfg_path)

    # 3. 无文件无环境变量时回退默认值
    cfg = load_config(DEFAULTS, None, environ={})
    assert cfg == DEFAULTS, cfg

    print("✅ self-test 全部通过（dotenv 解析 / 三层优先级 / 默认值回退）")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        cfg = load_config(DEFAULTS, "config.json", environ=dict(os.environ))
        print("当前配置:", json.dumps(cfg, ensure_ascii=False, indent=2))
