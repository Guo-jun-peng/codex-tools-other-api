"""配置管理器 —— Config 类，提供语义化 CRUD 方法 + YAML 持久化"""

from __future__ import annotations

import copy
import os
import threading
from pathlib import Path
from typing import Any

import yaml

from .defaults import DEFAULT_CODEX, DEFAULT_MODEL_MAPPING, DEFAULT_PROVIDERS, DEFAULT_SERVER, DEFAULT_TOOLS
from .loader import load_dotenv, resolve_config_path
from .validator import normalize_model_entry, validate_port


class Config:
    """配置管理器 —— 线程安全，提供语义化 CRUD 方法"""

    def __init__(self, config_path: str | Path | None = None):
        self._config_path: Path | None = None
        self._data: dict[str, Any] = {}
        self._lock = threading.RLock()
        self.load(config_path)

    # ── 持久化 ──────────────────────────────────────────────

    def load(self, config_path: str | Path | None = None) -> None:
        path = resolve_config_path(config_path)
        if path:
            load_dotenv(path.parent / ".env")
        load_dotenv(Path.home() / ".codex-adapter-bridge.env")
        if path and path.exists():
            with self._lock:
                self._config_path = path
                self._data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                self._inject_env()
        else:
            self._data = {}

    def reload(self) -> None:
        self.load(self._config_path)

    def save(self) -> None:
        with self._lock:
            if self._config_path:
                data = copy.deepcopy(self._data)
                env_api_keys = {}
                for name, info in data.get("providers", {}).items():
                    if "api_key" in info:
                        env_var = info.get("api_key_env", "")
                        env_val = os.environ.get(env_var, "") if env_var else ""
                        if env_val and info["api_key"] == env_val:
                            env_api_keys[name] = info.pop("api_key")
                self._config_path.write_text(
                    yaml.dump(data, allow_unicode=True, default_flow_style=False),
                    encoding="utf-8",
                )
                for name, key in env_api_keys.items():
                    data["providers"][name]["api_key"] = key

    # ── 属性 ─────────────────────────────────────────────────

    @property
    def config_path(self) -> Path | None:
        return self._config_path

    @property
    def data(self) -> dict:
        return self._data

    @property
    def server_host(self) -> str:
        return self._data.get("server", {}).get("host", "127.0.0.1")

    @property
    def server_port(self) -> int:
        return self._data.get("server", {}).get("port", 8899)

    @property
    def server_config(self) -> dict:
        """服务器配置完整字典（供 admin API 使用）"""
        return self._data.get("server", {})

    @property
    def vision_routing(self) -> dict:
        return self._data.get("vision_routing", {})

    @property
    def default_slash_provider(self) -> str:
        return self._data.get("server", {}).get("default_slash_provider", "siliconflow")

    @property
    def providers(self) -> dict:
        return self._data.get("providers", {})

    @property
    def tools(self) -> dict:
        return self._data.get("tools", {})

    @property
    def model_mapping(self) -> dict[str, dict]:
        return self._data.get("model_mapping", {})

    def get_provider(self, name: str) -> dict | None:
        return self.providers.get(name)

    # ── 语义化 CRUD 方法 ─────────────────────────────────────

    def add_model(self, alias: str, entry: dict) -> None:
        """添加模型映射条目。自动规范化并保存。"""
        if not alias or not alias.strip():
            raise ValueError("模型别名不能为空")
        entry = normalize_model_entry(alias, entry)
        provider_name = entry.get("provider", "")
        with self._lock:
            providers = self._data.setdefault("providers", {})
            if provider_name and provider_name not in providers:
                providers[provider_name] = {
                    "adapter": provider_name,
                    "base_url": "",
                    "api_key_env": "",
                    "enabled": True,
                }
            self._data.setdefault("model_mapping", {})[alias] = entry
            self.save()

    def update_model(self, alias: str, fields: dict) -> None:
        """部分更新模型映射。只修改传入的字段。保存。"""
        valid_keys = (
            "target", "provider", "enabled", "is_multimodal", "vision_alias",
            "is_image_gen", "image_gen_alias", "is_video_gen", "video_gen_alias",
        )
        with self._lock:
            mapping = self._data.get("model_mapping", {})
            if alias not in mapping:
                raise KeyError(f"模型别名 '{alias}' 不存在")
            old = mapping[alias]
            merged = {**old, **{k: v for k, v in fields.items() if k in valid_keys}}
            mapping[alias] = normalize_model_entry(alias, merged)
            self.save()

    def delete_model(self, alias: str) -> None:
        """删除模型映射条目。保存。"""
        with self._lock:
            if alias not in self._data.get("model_mapping", {}):
                raise KeyError(f"模型别名 '{alias}' 不存在")
            del self._data["model_mapping"][alias]
            self.save()

    def toggle_model(self, alias: str) -> bool:
        """切换模型启用状态，返回新状态。保存。"""
        with self._lock:
            entry = self._data.get("model_mapping", {}).get(alias)
            if not entry:
                raise KeyError(f"模型别名 '{alias}' 不存在")
            entry["enabled"] = not entry.get("enabled", True)
            self.save()
            return entry["enabled"]

    def update_server(self, fields: dict) -> None:
        """更新服务器配置。校验端口范围。保存。"""
        with self._lock:
            server = self._data.setdefault("server", {})
            if "port" in fields:
                port = int(fields["port"])
                err = validate_port(port)
                if err:
                    raise ValueError(err)
                server["port"] = port
            for key in ("host", "log_level", "auto_start", "close_to_tray", "default_slash_provider"):
                if key in fields:
                    server[key] = fields[key]
            self.save()

    def update_tools(self, data: dict) -> None:
        """更新工具配置。保存。"""
        with self._lock:
            tools = self._data.setdefault("tools", {})
            for name, info in data.items():
                if isinstance(info, dict):
                    tools[name] = info
            self.save()

    def add_or_update_provider(self, name: str, info: dict) -> None:
        """添加或更新 provider 配置。保存。"""
        with self._lock:
            providers = self._data.setdefault("providers", {})
            if name in providers:
                providers[name].update(info)
            else:
                providers[name] = info
            self.save()

    def export_config(self) -> dict:
        """导出配置数据（剥离 API Key 用于安全导出）。"""
        import copy as cp
        data = cp.deepcopy(self._data)
        for p in data.get("providers", {}).values():
            p.pop("api_key", None)
        return data

    def import_config(self, new_data: dict) -> None:
        """合并导入配置，重新规范化并保存。"""
        from .loader import deep_merge
        with self._lock:
            self._data = deep_merge(self._data, new_data)
            self._normalize_mapping()
            self._inject_env()
            self.save()

    # ── 模型解析 ─────────────────────────────────────────────

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

        if "/" in model_name:
            default = self.default_slash_provider
            if default:
                pinfo = self.providers.get(default)
                if pinfo and self._has_api_key(pinfo):
                    return default, model_name

        for pname, pinfo in self.providers.items():
            if pinfo.get("enabled", True) and self._has_api_key(pinfo) and pname in model_name.lower():
                return pname, model_name

        enabled = self._enabled_providers()
        if enabled:
            first = next(iter(enabled.items()))
            return first[0], model_name
        return "unknown", model_name

    # ── 内部方法 ─────────────────────────────────────────────

    def _inject_env(self) -> None:
        providers = self._data.setdefault("providers", {})
        for name, info in providers.items():
            env_var = info.get("api_key_env", "")
            if env_var:
                env_val = os.environ.get(env_var, "")
                if env_val and not info.get("api_key", ""):
                    info["api_key"] = env_val
                elif not env_val and "api_key" not in info:
                    info["api_key"] = ""
            elif "api_key" not in info:
                info["api_key"] = ""
        self._normalize_mapping()

    def _normalize_mapping(self) -> None:
        mapping = self._data.get("model_mapping", {})
        normalized = {}
        for alias, entry in mapping.items():
            if isinstance(entry, str):
                normalized[alias] = normalize_model_entry(alias, {
                    "target": entry,
                })
            elif isinstance(entry, dict):
                normalized[alias] = normalize_model_entry(alias, entry)
        self._data["model_mapping"] = normalized

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
            "server": dict(DEFAULT_SERVER),
            "providers": {k: dict(v) for k, v in DEFAULT_PROVIDERS.items()},
            "model_mapping": {k: dict(v) for k, v in DEFAULT_MODEL_MAPPING.items()},
            "tools": dict(DEFAULT_TOOLS),
            "codex": dict(DEFAULT_CODEX),
        }
        output_path.write_text(
            yaml.dump(default, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
