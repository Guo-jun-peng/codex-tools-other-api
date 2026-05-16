"""配置管理 —— YAML 配置文件加载、环境变量注入、热加载"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATHS = [
    Path.home() / ".codex-adapter-bridge.yaml",
    Path("config.yaml"),
]


def _load_dotenv(dotenv_path: Path) -> None:
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


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


class Config:
    """配置管理器"""

    def __init__(self, config_path: str | Path | None = None):
        self._config_path: Path | None = None
        self._data: dict[str, Any] = {}
        self._lock = threading.RLock()
        self.load(config_path)

    def load(self, config_path: str | Path | None = None) -> None:
        path = self._resolve_path(config_path)
        if path:
            _load_dotenv(path.parent / ".env")
        _load_dotenv(Path.home() / ".codex-adapter-bridge.env")
        if path and path.exists():
            with self._lock:
                self._config_path = path
                self._data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        else:
            self._data = {}
        self._inject_env()

    def reload(self) -> None:
        self.load(self._config_path)

    def save(self) -> None:
        with self._lock:
            if self._config_path:
                data = self._data.copy()
                env_api_keys = {}
                for name, info in data.get("providers", {}).items():
                    if "api_key" in info and info.get("api_key_env", ""):
                        env_api_keys[name] = info.pop("api_key")
                self._config_path.write_text(
                    yaml.dump(data, allow_unicode=True, default_flow_style=False),
                    encoding="utf-8",
                )
                for name, key in env_api_keys.items():
                    data["providers"][name]["api_key"] = key

    @property
    def config_path(self) -> Path | None:
        return self._config_path

    @property
    def data(self) -> dict:
        return self._data

    def _resolve_path(self, config_path: str | Path | None) -> Path | None:
        if config_path:
            p = Path(config_path)
            if p.is_file():
                return p
            return None
        for p in DEFAULT_CONFIG_PATHS:
            if p.is_file():
                return p
        return None

    def _inject_env(self) -> None:
        providers = self._data.setdefault("providers", {})
        for name, info in providers.items():
            env_var = info.get("api_key_env", "")
            if env_var:
                env_val = os.environ.get(env_var, "")
                if env_val:
                    info["api_key"] = env_val
                elif "api_key" not in info:
                    info["api_key"] = ""
            elif "api_key" not in info:
                info["api_key"] = ""
        self._normalize_mapping()

    def _normalize_mapping(self) -> None:
        mapping = self._data.get("model_mapping", {})
        normalized = {}
        for alias, entry in mapping.items():
            if isinstance(entry, str):
                normalized[alias] = {
                    "target": entry,
                    "provider": "",
                    "enabled": True,
                    "is_multimodal": False,
                    "vision_alias": None,
                    "is_image_gen": False,
                    "image_gen_alias": None,
                    "is_video_gen": False,
                    "video_gen_alias": None,
                }
            elif isinstance(entry, dict):
                entry.setdefault("provider", "")
                entry.setdefault("is_multimodal", False)
                entry.setdefault("vision_alias", None)
                entry.setdefault("is_image_gen", False)
                entry.setdefault("image_gen_alias", None)
                entry.setdefault("is_video_gen", False)
                entry.setdefault("video_gen_alias", None)
                entry.setdefault("enabled", True)
                normalized[alias] = entry
        self._data["model_mapping"] = normalized

    @property
    def server_host(self) -> str:
        return self._data.get("server", {}).get("host", "127.0.0.1")

    @property
    def server_port(self) -> int:
        return self._data.get("server", {}).get("port", 8899)

    @property
    def vision_routing(self) -> dict:
        return self._data.get("vision_routing", {})

    @property
    def providers(self) -> dict:
        return self._data.get("providers", {})

    @property
    def model_mapping(self) -> dict[str, dict]:
        return self._data.get("model_mapping", {})

    def get_provider(self, name: str) -> dict | None:
        return self.providers.get(name)

    def _has_api_key(self, provider: dict) -> bool:
        if provider.get("api_key", ""):
            return True
        env_var = provider.get("api_key_env", "")
        if env_var and os.environ.get(env_var, ""):
            return True
        return False

    def _enabled_providers(self) -> dict:
        return {k: v for k, v in self.providers.items()
                if v.get("enabled", True) and self._has_api_key(v)}

    def resolve_model(self, model_name: str) -> tuple[str, str]:
        entry = self.model_mapping.get(model_name)
        if isinstance(entry, dict) and entry.get("enabled", True):
            target = entry.get("target", model_name)
            provider_name = entry.get("provider", "")
            if not provider_name:
                provider_name = self._find_provider_for_target(target)
            if provider_name and provider_name in self.providers:
                p = self.providers[provider_name]
                if self._has_api_key(p):
                    return provider_name, target

        # Fuzzy match: prefer siliconflow for models with provider/model format
        # (e.g., deepseek-ai/DeepSeek-V3.2 is a SiliconFlow model)
        if "/" in model_name:
            for pname in ("siliconflow",):
                pinfo = self.providers.get(pname)
                if pinfo and self._has_api_key(pinfo):
                    return pname, model_name

        for pname, pinfo in self.providers.items():
            if pinfo.get("enabled", True) and self._has_api_key(pinfo) and pname in model_name.lower():
                return pname, model_name

        enabled = self._enabled_providers()
        if enabled:
            first = next(iter(enabled.items()))
            return first[0], model_name
        return "unknown", model_name

    def _find_provider_for_target(self, target: str) -> str | None:
        for pname, pinfo in self.providers.items():
            if not self._has_api_key(pinfo):
                continue
            if pinfo.get("adapter") == target or pname == target:
                return pname
        for pname, pinfo in self.providers.items():
            if not self._has_api_key(pinfo):
                continue
            if pname in target.lower():
                return pname
        enabled = self._enabled_providers()
        return next(iter(enabled), None) if enabled else None

    def _get_default_model(self, provider_name: str) -> str:
        pname = provider_name
        for alias, entry in self.model_mapping.items():
            target = entry.get("target", entry) if isinstance(entry, dict) else entry
            found = self._find_provider_for_target(target)
            if found == pname:
                return target
        return pname

    @staticmethod
    def generate_default(output_path: Path) -> None:
        default = {
            "server": {"host": "127.0.0.1", "port": 8899},
            "providers": {
                "siliconflow": {
                    "adapter": "siliconflow",
                    "base_url": "https://api.siliconflow.cn/v1",
                    "api_key_env": "SILICONFLOW_API_KEY",
                },
                "qwen": {
                    "adapter": "qwen",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "api_key_env": "QWEN_API_KEY",
                },
                "deepseek": {
                    "adapter": "deepseek",
                    "base_url": "https://api.deepseek.com/v1",
                    "api_key_env": "DEEPSEEK_API_KEY",
                },
                "kimi": {
                    "adapter": "kimi",
                    "base_url": "https://api.moonshot.cn/v1",
                    "api_key_env": "KIMI_API_KEY",
                },
                "doubao": {
                    "adapter": "doubao",
                    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                    "api_key_env": "ARK_API_KEY",
                },
                "zhipu": {
                    "adapter": "zhipu",
                    "base_url": "https://open.bigmodel.cn/api/paas/v4",
                    "api_key_env": "ZHIPU_API_KEY",
                },
            },
            "model_mapping": {
                "gpt-5.5": {"target": "deepseek-ai/DeepSeek-V4", "provider": "siliconflow", "enabled": True},
                "gpt-5-code": {"target": "deepseek-ai/DeepSeek-V3.2", "provider": "siliconflow", "enabled": True},
                "gpt-5-code-light": {"target": "deepseek-ai/DeepSeek-Coder-V2-Instruct", "provider": "siliconflow", "enabled": True},
            },
            "tools": {
                "web_search": {"enabled": True},
            },
            "codex": {
                "auto_manage": False,
                "backup_suffix": ".codex_adapter_backup",
            },
        }
        output_path.write_text(
            yaml.dump(default, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )


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
