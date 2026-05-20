"""适配器上下文 —— 请求级不可变快照，解决并发安全问题"""

from __future__ import annotations

from dataclasses import dataclass

from .base import BaseAdapter


@dataclass(frozen=True)
class AdapterContext:
    """不可变的适配器配置快照

    每次请求创建一个新实例，避免修改全局单例 adapter 的 base_url，
    从而消除并发竞态条件。

    - adapter: 全局单例适配器的只读引用
    - base_url: 请求级别的 API 基地址（来自 provider 配置）
    - api_key: 请求级别的 API Key
    """

    adapter: BaseAdapter
    base_url: str
    api_key: str

    def get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def build_chat_url(self) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/chat/completions"

    def build_image_gen_url(self) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}/images/generations"

    @property
    def api_key_env(self) -> str:
        return self.adapter.api_key_env

    @property
    def name(self) -> str:
        return self.adapter.name

    # ── 委托方法：路由到只读 adapter 实例 ──────────────────────────

    def preprocess_chat_request(self, chat_req: dict) -> dict:
        return self.adapter.preprocess_chat_request(chat_req)

    def postprocess_chat_response(self, chat_resp: dict) -> dict:
        return self.adapter.postprocess_chat_response(chat_resp)

    def stream_event_transform(self, raw_event: dict) -> dict:
        return self.adapter.stream_event_transform(raw_event)

    def preprocess_image_gen_request(self, req: dict) -> dict:
        return self.adapter.preprocess_image_gen_request(req)

    def supports_tool_calls(self) -> bool:
        return self.adapter.supports_tool_calls()

    def extract_tool_calls_from_content(self, content: str) -> list[dict] | None:
        return self.adapter.extract_tool_calls_from_content(content)
