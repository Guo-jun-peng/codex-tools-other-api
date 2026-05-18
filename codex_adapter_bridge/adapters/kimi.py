"""Moonshot (Kimi) 适配器"""

from __future__ import annotations

import json
import re

from .base import BaseAdapter


class KimiAdapter(BaseAdapter):
    name = "kimi"
    base_url = "https://api.moonshot.cn/v1"
    api_key_env = "KIMI_API_KEY"

    def preprocess_chat_request(self, chat_req: dict) -> dict:
        super().preprocess_chat_request(chat_req)

        if "thinking" not in chat_req:
            chat_req["thinking"] = {"type": "disabled"}

        tools = chat_req.get("tools")
        if tools and not self.supports_tool_calls():
            chat_req.pop("tools", None)
            chat_req.pop("tool_choice", None)
            chat_req = self._inject_tools_as_prompt(chat_req)

        return chat_req

    def postprocess_chat_response(self, chat_resp: dict) -> dict:
        super().postprocess_chat_response(chat_resp)

        for choice in chat_resp.get("choices", []):
            msg = choice.get("message", {})
            content = msg.get("content", "")
            if content and isinstance(content, str) and not msg.get("tool_calls"):
                extracted = self.extract_tool_calls_from_content(content)
                if extracted:
                    msg["tool_calls"] = extracted
                    msg["content"] = None

        return chat_resp

    def extract_tool_calls_from_content(self, content: str) -> list[dict] | None:
        if not content:
            return None

        patterns = [
            r"<function_call>\s*(.*?)\s*</function_call>",
            r'```json\s*(\{.*?"name".*?\})\s*```',
            r"<tool_call>\s*(.*?)\s*</tool_call>",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                tool_calls = []
                for i, m in enumerate(matches):
                    try:
                        data = json.loads(m)
                        name = data.get("name", data.get("function", ""))
                        args = data.get("arguments", data.get("parameters", {}))
                        tool_calls.append({
                            "id": f"call_{i}",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else str(args),
                            },
                        })
                    except json.JSONDecodeError:
                        continue
                if tool_calls:
                    return tool_calls
        return None

    def _inject_tools_as_prompt(self, chat_req: dict) -> dict:
        tools = chat_req.get("tools", [])
        if not tools:
            return chat_req

        tool_descs = []
        for tool in tools:
            fn = tool.get("function", tool)
            name = fn.get("name", "")
            desc = fn.get("description", "")
            params = fn.get("parameters", {})
            tool_descs.append(f"- {name}: {desc}\n  Parameters: {json.dumps(params, ensure_ascii=False)}")

        tool_prompt = (
            "\n\n你可以在回复中通过 JSON 格式调用以下函数：\n"
            + "\n".join(tool_descs)
            + '\n\n调用格式：\n<function_call>\n{"name": "函数名", "arguments": {...}}\n</function_call>'
        )

        messages = chat_req.get("messages", [])
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = (messages[0].get("content", "") + tool_prompt)
        else:
            messages.insert(0, {"role": "system", "content": tool_prompt.lstrip()})

        chat_req["messages"] = messages
        return chat_req
