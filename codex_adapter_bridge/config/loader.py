"""配置加载 —— YAML 文件读取、.env 注入、路径解析"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CONFIG_PATHS = [
    Path.home() / ".codex-adapter-bridge.yaml",
    Path("config.yaml"),
]


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.is_file():
        return
    try:
        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


def deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def resolve_config_path(config_path: str | Path | None) -> Path | None:
    if config_path:
        p = Path(config_path)
        if p.is_file():
            return p
        return None
    for p in DEFAULT_CONFIG_PATHS:
        if p.is_file():
            return p
    return None
