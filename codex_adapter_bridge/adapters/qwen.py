"""通义千问 (Qwen) 适配器"""

from __future__ import annotations

import json
import re

from .base import BaseAdapter


class QwenAdapter(BaseAdapter):
    name = "qwen"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key_env = "QWEN_API_KEY"

    def postprocess_chat_response(self, chat_resp: dict) -> dict:
        super().postprocess_chat_response(chat_resp)

        for choice in chat_resp.get("choices", []):
            msg = choice.get("message", {})
            content = msg.get("content", "")
            if content and isinstance(content, str):
                extracted = self.extract_tool_calls_from_content(content)
                if extracted:
                    msg["tool_calls"] = extracted
                    msg["content"] = None

        return chat_resp

    def stream_event_transform(self, raw_event: dict) -> dict:
        # Qwen wraps chunks in {"output": {"choices": [...]}}
        if "output" in raw_event and "choices" not in raw_event:
            output = raw_event["output"]
            if isinstance(output, dict) and "choices" in output:
                raw_event["choices"] = output["choices"]

        if "choices" not in raw_event:
            return raw_event

        return super().stream_event_transform(raw_event)

    def extract_tool_calls_from_content(self, content: str) -> list[dict] | None:
        if not content:
            return None

        pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
        matches = re.findall(pattern, content, re.DOTALL)
        if not matches:
            return None

        tool_calls = []
        for i, m in enumerate(matches):
            try:
                data = json.loads(m)
                tool_calls.append({
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": data.get("name", ""),
                        "arguments": json.dumps(data.get("arguments", {}), ensure_ascii=False),
                    },
                })
            except json.JSONDecodeError:
                fn_match = re.match(r'(\w+)\s*\((.*)\)', m.strip(), re.DOTALL)
                if fn_match:
                    tool_calls.append({
                        "id": f"call_{i}",
                        "type": "function",
                        "function": {
                            "name": fn_match.group(1),
                            "arguments": fn_match.group(2).strip(),
                        },
                    })

        return tool_calls if tool_calls else None
