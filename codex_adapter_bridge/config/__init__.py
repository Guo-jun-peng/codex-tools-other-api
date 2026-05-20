"""配置子包 —— 向后兼容重导出"""

from __future__ import annotations

import os
from pathlib import Path

from .manager import Config
from .loader import deep_merge as _deep_merge, load_dotenv as _load_dotenv, resolve_config_path as _resolve_config_path, DEFAULT_CONFIG_PATHS
from .validator import validate_alias, validate_port, validate_url, normalize_model_entry
from .defaults import DEFAULT_SERVER, DEFAULT_PROVIDERS, DEFAULT_MODEL_MAPPING, DEFAULT_TOOLS, DEFAULT_CODEX

# 向后兼容：admin_api.py 中有 `from .config import _deep_merge` 的惰性导入
deep_merge = _deep_merge

_config: Config | None = None


def get_config(config_path: str | Path | None = None) -> Config:
    global _config
    if _config is None:
        env_path = os.environ.get("CODEX_ADAPTER_BRIDGE_CONFIG", "")
        if env_path:
            config_path = env_path
        _config = Config(config_path)
    return _config


def reload_config() -> None:
    cfg = get_config()
    cfg.reload()


__all__ = [
    "Config",
    "get_config",
    "reload_config",
    "validate_alias",
    "validate_port",
    "validate_url",
    "normalize_model_entry",
    "DEFAULT_SERVER",
    "DEFAULT_PROVIDERS",
    "DEFAULT_MODEL_MAPPING",
    "DEFAULT_TOOLS",
    "DEFAULT_CODEX",
]
