"""适配器注册表 —— 模型名到适配器实例的映射管理"""

from __future__ import annotations

from .base import BaseAdapter
from .context import AdapterContext


class AdapterRegistry:
    """适配器注册表"""

    def __init__(self):
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> BaseAdapter | None:
        return self._adapters.get(name)

    def list(self) -> list[str]:
        return list(self._adapters.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._adapters


_registry: AdapterRegistry | None = None


def get_registry() -> AdapterRegistry:
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
        _register_builtins(_registry)
    return _registry


def _register_builtins(reg: AdapterRegistry) -> None:
    from .siliconflow import SiliconFlowAdapter
    from .qwen import QwenAdapter
    from .deepseek import DeepSeekAdapter
    from .kimi import KimiAdapter
    from .doubao import DoubaoAdapter
    from .glm import GlmAdapter

    reg.register(SiliconFlowAdapter())
    reg.register(QwenAdapter())
    reg.register(DeepSeekAdapter())
    reg.register(KimiAdapter())
    reg.register(DoubaoAdapter())
    reg.register(GlmAdapter())
