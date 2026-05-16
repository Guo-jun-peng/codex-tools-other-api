"""协议转换引擎 —— OpenAI Responses API ↔ Chat Completions API 双向转换"""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from .models import (
    _uid,
    build_responses_response,
    build_error_response,
    make_function_call_output_item,
    make_output_text,
    make_message_output_item,
)
from .adapters.base import BaseAdapter


# ═══════════════════════════════════════════════════════════════════
# 请求转换: Responses API → Chat Completions API
# ═══════════════════════════════════════════════════════════════════

def translate_request(
    responses_body: dict,
    adapter: BaseAdapter,
    target_model: str,
) -> dict:
    """将 Responses API 请求转换为 Chat Completions API 请求"""
    messages = _map_input_to_messages(responses_body.get("input", []))

    instructions = responses_body.get("instructions", "").strip()
    if instructions:
        messages.insert(0, {"role": "system", "content": instructions})

    chat_req: dict = {
        "model": target_model,
        "messages": messages,
        "stream": responses_body.get("stream", False),
    }

    _map_optional(responses_body, chat_req, "temperature")
    _map_optional(responses_body, chat_req, "top_p")
    _map_optional(responses_body, chat_req, "stop")

    if "max_output_tokens" in responses_body:
        chat_req["max_tokens"] = responses_body["max_output_tokens"]

    tools = responses_body.get("tools")
    has_image_gen = False
    if tools:
        normalized = []
        for t in tools:
            tool_type = t.get("type", "function")
            if tool_type == "image_gen":
                has_image_gen = True
                normalized.append(_make_image_gen_tool(t))
            elif tool_type in ("web_search", "code_interpreter", "file_search"):
                # Codex 内置工具 → function tool
                normalized.append(_make_builtin_function_tool(t))
            else:
                normalized.append(_normalize_tool(t))
        chat_req["tools"] = [t for t in normalized if t.get("function", {}).get("name", "").strip()]
        if has_image_gen:
            chat_req["_has_image_gen"] = True

    tool_choice = responses_body.get("tool_choice")
    if tool_choice and tools:
        chat_req["tool_choice"] = tool_choice

    chat_req = adapter.preprocess_chat_request(chat_req)
    return chat_req


_ROLE_MAP = {"developer": "system"}


def _extract_reasoning_text(item: dict) -> str:
    parts = []
    for field in ("summary", "content"):
        for part in item.get(field, []) or []:
            text = part.get("text", "")
            if text:
                parts.append(text)
    return "\n".join(parts)


def _map_input_to_messages(input_items: list[dict]) -> list[dict]:
    messages = []
    pending_tool_calls: list[dict] = []
    pending_reasoning: str = ""

    def _flush_tool_calls():
        nonlocal pending_reasoning
        if pending_tool_calls:
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": pending_tool_calls.copy(),
            }
            msg["reasoning_content"] = pending_reasoning or "Tool calls."
            pending_reasoning = ""
            messages.append(msg)
            pending_tool_calls.clear()

    for item in input_items:
        item_type = item.get("type", "")

        if item_type == "reasoning":
            pending_reasoning = _extract_reasoning_text(item) or pending_reasoning
            continue

        if item_type == "function_call_output":
            _flush_tool_calls()
            output = item.get("output", "")
            if isinstance(output, list):
                output = "".join(p.get("text", "") for p in output)
            elif not isinstance(output, str):
                output = str(output)
            messages.append({
                "role": "tool",
                "tool_call_id": item.get("call_id", ""),
                "content": output,
            })
            continue

        if item_type == "function_call":
            tc = {
                "type": "function",
                "id": item.get("call_id", ""),
                "function": {
                    "name": item.get("name", ""),
                    "arguments": item.get("arguments", ""),
                },
            }
            pending_tool_calls.append(tc)
            continue

        _flush_tool_calls()

        role = item.get("role", "user")
        role = _ROLE_MAP.get(role, role)
        content = _normalize_content(item.get("content", ""))
        msg = {"role": role}
        if content is not None:
            msg["content"] = content or None
        if "name" in item:
            msg["name"] = item["name"]
        if "tool_call_id" in item:
            msg["tool_call_id"] = item["tool_call_id"]
        if "tool_calls" in item:
            msg["tool_calls"] = item["tool_calls"]
            if not msg.get("content"):
                msg["content"] = None

        if role == "assistant" and pending_reasoning:
            msg["reasoning_content"] = pending_reasoning
            pending_reasoning = ""

        messages.append(msg)

    _flush_tool_calls()

    if pending_reasoning:
        for m in reversed(messages):
            if m.get("role") == "assistant":
                m["reasoning_content"] = pending_reasoning
                break
        pending_reasoning = ""

    return messages


def _normalize_content(content) -> str | list[dict] | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        has_text = False
        for part in content:
            ptype = part.get("type", "")
            if ptype == "input_text":
                parts.append({"type": "text", "text": part.get("text", "")})
                has_text = True
            elif ptype == "input_image":
                parts.append({"type": "image_url", "image_url": part.get("image_url", {})})
            elif ptype == "output_text":
                parts.append({"type": "text", "text": part.get("text", "")})
                has_text = True
            else:
                parts.append(part)
        if len(parts) == 1 and has_text:
            return parts[0]["text"]
        return parts if parts else None
    return content


def _make_image_gen_tool(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": "image_gen",
            "description": "Generate images from a text prompt. Call this when the user asks to create, draw, generate, or design an image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "A detailed image generation prompt describing what to create."
                    },
                    "size": {
                        "type": "string",
                        "enum": ["2560x1440", "2048x2048", "3840x2160", "4096x4096"],
                        "description": "Output image dimensions. Default 2560x1440."
                    },
                },
                "required": ["prompt"]
            }
        }
    }


def _make_builtin_function_tool(tool: dict) -> dict:
    """将 Codex 内置工具 (web_search, code_interpreter, file_search) 转换为 function tool"""
    tool_type = tool.get("type", "")
    name = tool_type
    desc = tool.get("description", "")
    params = tool.get("parameters", {})

    if tool_type == "web_search":
        name = "web_search"
        desc = desc or "Search the web for current information"
        params = params or {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The search query"}},
            "required": ["query"],
        }
    elif tool_type == "code_interpreter":
        name = "code_interpreter"
        desc = desc or "Execute Python code and return the result"
        params = params or {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code to execute"}},
            "required": ["code"],
        }
    elif tool_type == "file_search":
        name = "file_search"
        desc = desc or "Search for files in the workspace"
        params = params or {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query for files"}},
            "required": ["query"],
        }

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": params,
        }
    }


def _normalize_tool(tool: dict) -> dict:
    if "type" not in tool:
        tool = {"type": "function", **tool}
    if "function" not in tool:
        tool["function"] = {
            "name": tool.pop("name", ""),
            "description": tool.pop("description", ""),
            "parameters": tool.pop("parameters", {}),
        }
        tool["type"] = "function"
    params = tool["function"].get("parameters")
    if not params or not isinstance(params, dict):
        tool["function"]["parameters"] = {"type": "object", "properties": {}}
    elif params.get("type") != "object":
        params["type"] = "object"
        if "properties" not in params:
            params["properties"] = {}
    return tool


def _map_optional(src: dict, dst: dict, key: str) -> None:
    if key in src and src[key] is not None:
        dst[key] = src[key]


# ═══════════════════════════════════════════════════════════════════
# 非流式响应转换: Chat Completions API → Responses API
# ═══════════════════════════════════════════════════════════════════

def translate_response(
    chat_resp: dict,
    adapter: BaseAdapter,
    model: str,
) -> dict:
    chat_resp = adapter.postprocess_chat_response(chat_resp)

    choices = chat_resp.get("choices", [])
    usage = chat_resp.get("usage", {})
    output_items: list[dict] = []

    for choice in choices:
        msg = choice.get("message", {})
        content = msg.get("content")
        tool_calls = msg.get("tool_calls") or []

        if content:
            output_items.append(make_message_output_item(content))

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            arguments = fn.get("arguments", "")
            call_id = tc.get("id", "")
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments, ensure_ascii=False)
            output_items.append(
                make_function_call_output_item(name, arguments, call_id)
            )

    return build_responses_response(output_items, model, usage)


# ═══════════════════════════════════════════════════════════════════
# 流式转换: Chat Completions SSE → Responses API SSE
# ═══════════════════════════════════════════════════════════════════

def _sse_line(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class StreamTranslator:
    """有状态的流式转换器"""

    def __init__(self, response_id: str | None = None, model: str = ""):
        self.response_id = response_id or _uid("resp")
        self.model = model

        self._created_sent = False
        self._done = False
        self._output_index = -1

        self._text_item_index = -1
        self._text_item_id = ""
        self._text_content_index = -1
        self._text_buf: list[str] = []
        self._text_started = False

        self._tc_buf: dict[int, dict] = {}
        self._output_items: list[dict] = []

        self._accumulated_text = ""
        self._finish_reason = ""

    async def translate_stream(
        self,
        chat_stream: AsyncIterator[dict],
    ) -> AsyncIterator[str]:
        try:
            async for chunk in chat_stream:
                for event_line in self._process_chunk(chunk):
                    yield event_line
            for event_line in self._finish():
                yield event_line
        except Exception as exc:
            yield _sse_line(build_error_response(str(exc)))

    def translate_chunk(self, chunk: dict) -> list[str]:
        return list(self._process_chunk(chunk))

    def _process_chunk(self, chunk: dict):
        if self._done:
            return

        if not self._created_sent:
            yield from self._emit_created()

        choices = chunk.get("choices", [])
        if not choices:
            return

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason") or ""
        if finish_reason:
            self._finish_reason = finish_reason

        content = delta.get("content")
        if content:
            yield from self._handle_text_delta(content)

        tool_calls = delta.get("tool_calls", [])
        for tc in tool_calls:
            yield from self._handle_tool_call_delta(tc)

        if finish_reason:
            yield from self._finish()

    def _finish(self) -> list[str]:
        if self._done:
            return []
        events: list[str] = []

        if self._text_started:
            events.extend(self._emit_text_done())

        for idx in sorted(self._tc_buf.keys()):
            events.extend(self._emit_tool_call_done(idx))

        events.append(
            _sse_line({
                "type": "response.completed",
                "response": {
                    "id": self.response_id,
                    "object": "response",
                    "model": self.model,
                    "status": "completed",
                    "output": self._output_items,
                },
            })
        )
        self._done = True
        return events

    def _emit_created(self):
        events = []
        events.append(
            _sse_line({
                "type": "response.created",
                "response": {
                    "id": self.response_id,
                    "object": "response",
                    "model": self.model,
                    "status": "in_progress",
                    "output": [],
                },
            })
        )
        self._created_sent = True
        return events

    def _handle_text_delta(self, content: str) -> list[str]:
        events = []
        if not self._text_started:
            self._output_index += 1
            self._text_item_index = self._output_index
            self._text_item_id = _uid("msg")
            self._text_content_index = 0
            self._text_buf = []
            self._text_started = True

            item = {
                "id": self._text_item_id,
                "object": "realtime.item",
                "type": "message",
                "role": "assistant",
                "status": "in_progress",
                "content": [],
            }
            self._output_items.append(item)

            events.append(
                _sse_line({
                    "type": "response.output_item.added",
                    "output_index": self._text_item_index,
                    "item": item,
                })
            )

            part = {"type": "output_text", "text": "", "annotations": []}
            item["content"].append(part)
            events.append(
                _sse_line({
                    "type": "response.content_part.added",
                    "output_index": self._text_item_index,
                    "content_index": self._text_content_index,
                    "part": part,
                })
            )

        self._text_buf.append(content)
        self._accumulated_text += content

        events.append(
            _sse_line({
                "type": "response.output_text.delta",
                "output_index": self._text_item_index,
                "content_index": self._text_content_index,
                "delta": content,
            })
        )
        return events

    def _emit_text_done(self) -> list[str]:
        if not self._text_started:
            return []
        events = []

        if self._text_item_index < len(self._output_items):
            item = self._output_items[self._text_item_index]
            item["status"] = "completed"
            if item["content"]:
                item["content"][0]["text"] = self._accumulated_text

        events.append(
            _sse_line({
                "type": "response.output_item.done",
                "output_index": self._text_item_index,
                "item": self._output_items[self._text_item_index] if self._text_item_index < len(self._output_items) else {},
            })
        )
        self._text_started = False
        return events

    def _handle_tool_call_delta(self, tc: dict) -> list[str]:
        events = []
        tc_index = tc.get("index", 0)
        fn = tc.get("function", {})
        fn_name = fn.get("name", "")
        fn_args = fn.get("arguments", "")
        tc_id = tc.get("id", "")

        if tc_index not in self._tc_buf:
            self._output_index += 1
            item_id = tc_id or _uid("func")
            call_id = tc_id or _uid("call")

            self._tc_buf[tc_index] = {
                "id": item_id,
                "call_id": call_id,
                "name": "",
                "arguments": "",
                "item_index": self._output_index,
                "name_done": False,
            }

            item = {
                "id": item_id,
                "object": "realtime.item",
                "type": "function_call",
                "call_id": call_id,
                "name": "",
                "arguments": "",
                "status": "in_progress",
            }
            self._output_items.append(item)

        buf = self._tc_buf[tc_index]

        if fn_name and not buf["name_done"]:
            buf["name"] = fn_name
            buf["name_done"] = True
            if buf["item_index"] < len(self._output_items):
                self._output_items[buf["item_index"]]["name"] = fn_name

            events.append(
                _sse_line({
                    "type": "response.output_item.added",
                    "output_index": buf["item_index"],
                    "item": self._output_items[buf["item_index"]],
                })
            )

        if fn_args:
            buf["arguments"] += fn_args
            if buf["item_index"] < len(self._output_items):
                self._output_items[buf["item_index"]]["arguments"] = buf["arguments"]

            events.append(
                _sse_line({
                    "type": "response.function_call_arguments.delta",
                    "output_index": buf["item_index"],
                    "delta": fn_args,
                })
            )

        return events

    def _emit_tool_call_done(self, idx: int) -> list[str]:
        if idx not in self._tc_buf:
            return []
        buf = self._tc_buf[idx]
        if buf["item_index"] < len(self._output_items):
            self._output_items[buf["item_index"]]["status"] = "completed"

        events = []
        events.append(
            _sse_line({
                "type": "response.output_item.done",
                "output_index": buf["item_index"],
                "item": self._output_items[buf["item_index"]] if buf["item_index"] < len(self._output_items) else {},
            })
        )
        return events
