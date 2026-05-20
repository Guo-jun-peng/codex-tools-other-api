"""配置校验 —— 别名格式、端口范围、URL 格式、模型条目规范化"""

from __future__ import annotations

import re

ALIAS_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-_.]*$")


def validate_alias(alias: str) -> str | None:
    if not alias or not alias.strip():
        return "模型别名不能为空"
    if not ALIAS_PATTERN.match(alias):
        return "模型别名只能包含字母、数字、连接线(-)、下划线(_) 和点(.)"
    return None


def validate_port(port: int) -> str | None:
    if port < 1024 or port > 65535:
        return f"端口 {port} 不在有效范围 1024-65535"
    return None


def validate_url(url: str) -> str | None:
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        return "API 地址必须以 http:// 或 https:// 开头"
    return None


def normalize_model_entry(alias: str, entry: dict) -> dict:
    """规范化单个模型映射条目，填充缺失的默认字段"""
    entry.setdefault("target", entry.get("target", ""))
    entry.setdefault("provider", "")
    entry.setdefault("is_multimodal", False)
    entry.setdefault("vision_alias", None)
    entry.setdefault("is_image_gen", False)
    entry.setdefault("image_gen_alias", None)
    entry.setdefault("is_video_gen", False)
    entry.setdefault("video_gen_alias", None)
    entry.setdefault("enabled", True)
    return entry
