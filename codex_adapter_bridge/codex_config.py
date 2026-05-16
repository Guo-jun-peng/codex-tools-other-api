"""Codex 配置管理 —— 自动检测、备份、修改和恢复 Codex 的 config.toml 和 auth.json"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger("codex-adapter-bridge")

APP_NAME = "Codex 国内模型适配工具"
BACKUP_SUFFIX = ".codex_adapter_backup"
USER_CONFIG_PATH = Path.home() / ".codex_adapter_config.json"


class CodexConfigManager:
    """管理 Codex 的 config.toml 和 auth.json"""

    def __init__(self):
        self._codex_dir: Path | None = None

    def detect_codex_dir(self) -> Path | None:
        env_home = os.environ.get("CODEX_HOME", "")
        if env_home:
            p = Path(env_home)
            if p.is_dir():
                self._codex_dir = p
                logger.info("通过 CODEX_HOME 找到配置目录: %s", p)
                return p

        home = Path.home()
        candidates = [home / ".codex"]
        if sys.platform == "win32":
            userprofile = os.environ.get("USERPROFILE", "")
            if userprofile:
                candidates.insert(0, Path(userprofile) / ".codex")

        for candidate in candidates:
            if candidate.is_dir():
                self._codex_dir = candidate
                logger.info("自动检测到 Codex 配置目录: %s", candidate)
                return candidate

        logger.warning("未找到 .codex 目录")
        return None

    @property
    def codex_dir(self) -> Path | None:
        if not self._codex_dir:
            self.detect_codex_dir()
        return self._codex_dir

    def backup_configs(self) -> bool:
        if not self.codex_dir:
            logger.error("无法备份: 未找到 Codex 配置目录")
            return False

        config_toml = self.codex_dir / "config.toml"
        auth_json = self.codex_dir / "auth.json"
        any_backed = False

        for f in [config_toml, auth_json]:
            if f.exists():
                backup = f.with_name(f.name + BACKUP_SUFFIX)
                if not backup.exists():
                    shutil.copy2(f, backup)
                    logger.info("已备份: %s -> %s", f.name, backup.name)
                else:
                    logger.info("备份已存在，跳过: %s", backup.name)
                any_backed = True

        return any_backed

    def restore_configs(self) -> bool:
        if not self.codex_dir:
            logger.error("无法恢复: 未找到 Codex 配置目录")
            return False

        restored = False
        for name in ["config.toml", "auth.json"]:
            current = self.codex_dir / name
            backup = self.codex_dir / (name + BACKUP_SUFFIX)
            if backup.exists():
                shutil.copy2(backup, current)
                logger.info("已恢复: %s", name)
                restored = True
            else:
                logger.warning("备份文件不存在: %s", backup)

        return restored

    def has_backup(self) -> bool:
        if not self.codex_dir:
            return False
        return (self.codex_dir / ("config.toml" + BACKUP_SUFFIX)).exists()

    def get_status(self) -> dict:
        codex_dir = self.codex_dir or self.detect_codex_dir()
        if not codex_dir:
            return {"found": False, "dir": "", "has_backup": False, "config_exists": False}

        config_toml = codex_dir / "config.toml"
        current_model = ""
        current_port = ""
        if config_toml.exists():
            try:
                content = config_toml.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("model = "):
                        current_model = line.split("=", 1)[1].strip().strip('"')
                    if "localhost:" in line and "/v1" in line:
                        import re
                        m = re.search(r'localhost:(\d+)', line)
                        if m:
                            current_port = m.group(1)
            except Exception:
                pass

        return {
            "found": True,
            "dir": str(codex_dir),
            "has_backup": self.has_backup(),
            "config_exists": config_toml.exists(),
            "current_model": current_model,
            "current_port": current_port,
        }

    def write_codex_config(self, model: str, port: int) -> bool:
        if not self.codex_dir:
            if not self.detect_codex_dir():
                logger.error("无法写入配置: 未找到 Codex 配置目录")
                return False

        assert self.codex_dir is not None
        config_path = self.codex_dir / "config.toml"

        if config_path.exists():
            new_content = self._rebuild_config_toml(config_path, model, port)
        else:
            logger.warning("config.toml 不存在，创建新文件")
            new_content = self._make_minimal_config(model, port)

        config_path.write_text(new_content, encoding="utf-8")
        logger.info("已更新 config.toml: model=%s, port=%d", model, port)

        auth_path = self.codex_dir / "auth.json"
        auth_path.write_text(json.dumps({"OPENAI_API_KEY": "PROXY_MANAGED"}, indent=2), encoding="utf-8")
        logger.info("已更新 auth.json")

        return True

    def _rebuild_config_toml(self, config_path: Path, model: str, port: int) -> str:
        raw_lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)

        preserved_lines: list[str] = []
        in_custom_provider = False
        skip_keys = {"model", "model_provider", "model_reasoning_effort", "model_reasoning_summary",
                     "disable_response_storage"}
        skip_empty_headers = {"[model_providers]", "[mcp_servers]"}

        for line in raw_lines:
            stripped = line.strip()

            if stripped in skip_empty_headers:
                continue

            if stripped.startswith("[model_providers.custom]"):
                in_custom_provider = True
                continue

            if in_custom_provider and stripped.startswith("[") and stripped.endswith("]"):
                in_custom_provider = False
                preserved_lines.append(line)
                continue

            if in_custom_provider:
                continue

            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in skip_keys:
                    continue

            preserved_lines.append(line)

        result_lines = [
            f'model_provider = "custom"\n',
            f'model = "{model}"\n',
            'model_reasoning_effort = "medium"\n',
        ]
        result_lines.extend(preserved_lines)
        result_lines.append("\n")
        result_lines.append("[model_providers.custom]\n")
        result_lines.append(f'name = "{APP_NAME}"\n')
        result_lines.append(f'base_url = "http://localhost:{port}/v1"\n')
        result_lines.append('wire_api = "responses"\n')
        result_lines.append("requires_openai_auth = true\n")

        return "".join(result_lines)

    def _make_minimal_config(self, model: str, port: int) -> str:
        return (
            f'model_provider = "custom"\n'
            f'model = "{model}"\n'
            'model_reasoning_effort = "medium"\n\n'
            f"[model_providers.custom]\n"
            f'name = "{APP_NAME}"\n'
            f'base_url = "http://localhost:{port}/v1"\n'
            'wire_api = "responses"\n'
            "requires_openai_auth = true\n"
        )

    @staticmethod
    def load_user_config() -> dict:
        if USER_CONFIG_PATH.exists():
            try:
                return json.loads(USER_CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    @staticmethod
    def save_user_config(data: dict):
        USER_CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
