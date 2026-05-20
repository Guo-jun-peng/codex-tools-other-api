"""默认配置常量"""

from __future__ import annotations

DEFAULT_SERVER = {
    "host": "127.0.0.1",
    "port": 8899,
    "default_slash_provider": "siliconflow",
}

DEFAULT_PROVIDERS = {
    "siliconflow": {
        "adapter": "siliconflow",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "enabled": True,
    },
    "qwen": {
        "adapter": "qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "QWEN_API_KEY",
        "enabled": True,
    },
    "deepseek": {
        "adapter": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "enabled": True,
    },
    "kimi": {
        "adapter": "kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "api_key_env": "KIMI_API_KEY",
        "enabled": True,
    },
    "doubao": {
        "adapter": "doubao",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "ARK_API_KEY",
        "enabled": True,
    },
    "zhipu": {
        "adapter": "zhipu",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
        "enabled": True,
    },
}

DEFAULT_MODEL_MAPPING = {
    "gpt-5.5": {
        "target": "deepseek-ai/DeepSeek-V4",
        "provider": "siliconflow",
        "enabled": True,
    },
    "gpt-5-code": {
        "target": "deepseek-ai/DeepSeek-V3.2",
        "provider": "siliconflow",
        "enabled": True,
    },
    "gpt-5-code-light": {
        "target": "deepseek-ai/DeepSeek-Coder-V2-Instruct",
        "provider": "siliconflow",
        "enabled": True,
    },
}

DEFAULT_TOOLS = {
    "web_search": {"enabled": True},
}

DEFAULT_CODEX = {
    "auto_manage": False,
    "backup_suffix": ".codex_adapter_backup",
}
