"""适配器基类 —— 定义国产模型适配器的抽象接口"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """国产模型适配器基类

    子类必须设置:
      - name: 适配器名称 (如 "qwen", "deepseek")
      - base_url: 模型 API 基地址
      - api_key_env: API Key 对应的环境变量名
    """

    name: str = ""
    base_url: str = ""
    api_key_env: str = ""

    # ── 钩子方法 ─────────────────────────────────────────────────

    def preprocess_chat_request(self, chat_req: dict) -> dict:
        """请求体微调 —— 发送给上游模型之前调用

        默认执行公共清理（移除未使用参数），子类可覆盖并 super() 调用。
        """
        self._common_cleanup(chat_req)
        self._normalize_request_tools(chat_req)
        return chat_req

    def postprocess_chat_response(self, chat_resp: dict) -> dict:
        """非流式响应微调 —— 协议转换之前调用

        默认规范化 message 中的 tool_calls 格式。
        子类可覆盖并 super() 调用。
        """
        for choice in chat_resp.get("choices", []):
            msg = choice.get("message", {})
            self._normalize_tool_calls(msg.get("tool_calls") or [])
        return chat_resp

    def stream_event_transform(self, raw_event: dict) -> dict:
        """单个 SSE chunk 结构调整 —— 统一为标准 Chat Completions chunk 格式

        默认规范化 delta 中的 tool_calls 格式。
        子类可覆盖并 super() 调用。
        """
        for choice in raw_event.get("choices", []):
            delta = choice.get("delta", {})
            self._normalize_tool_calls(delta.get("tool_calls", []))
        return raw_event

    # ── 工具调用相关 ─────────────────────────────────────────────

    def supports_tool_calls(self) -> bool:
        """是否原生支持 function calling"""
        return True

    def extract_tool_calls_from_content(self, content: str) -> list[dict] | None:
        """尝试从 message.content 文本中提取 tool_calls"""
        return None

    # ── 内部工具方法 ─────────────────────────────────────────────

    def _common_cleanup(self, chat_req: dict) -> None:
        """移除上游 API 不支持的参数"""
        chat_req.pop("logprobs", None)
        chat_req.pop("logit_bias", None)
        chat_req.pop("user", None)

    def _normalize_request_tools(self, chat_req: dict) -> None:
        """规范化请求中的 tools 字段为标准 OpenAI 格式"""
        tools = chat_req.get("tools")
        if not tools:
            return
        for tool in tools:
            if "function" not in tool and "name" in tool:
                tool["function"] = {
                    "name": tool.pop("name"),
                    "description": tool.pop("description", ""),
                    "parameters": tool.pop("parameters", {}),
                }
            if "type" not in tool:
                tool["type"] = "function"
            params = tool.get("function", {}).get("parameters")
            if not params or not isinstance(params, dict):
                tool.setdefault("function", {})["parameters"] = {"type": "object", "properties": {}}
            elif params.get("type") != "object":
                params["type"] = "object"
                params.setdefault("properties", {})

    @staticmethod
    def _normalize_tool_calls(tool_calls: list[dict]) -> None:
        """规范化 tool_calls 数组中每个元素的 type 和 arguments 格式"""
        for tc in tool_calls:
            if "type" not in tc:
                tc["type"] = "function"
            func = tc.get("function", {})
            if "arguments" in func and isinstance(func["arguments"], dict):
                func["arguments"] = json.dumps(func["arguments"], ensure_ascii=False)

    # ── 公共方法 ─────────────────────────────────────────────────

    def get_headers(self, api_key: str) -> dict:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def build_chat_url(self) -> str:
        """构建 Chat Completions API URL"""
        base = self.base_url.rstrip("/")
        return f"{base}/chat/completions"

    def build_image_gen_url(self) -> str:
        """构建 Image Generation API URL"""
        base = self.base_url.rstrip("/")
        return f"{base}/images/generations"

    def preprocess_image_gen_request(self, req: dict) -> dict:
        """生图请求预处理"""
        return req
