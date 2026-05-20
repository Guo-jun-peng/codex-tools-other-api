"""SSE 事件构造 —— 将工具执行结果转换为 Responses API SSE 事件流"""

from __future__ import annotations

from ..protocol import _sse_line
from ..models import _uid
from . import TOOL_EXECUTORS


def emit_final_output(result: dict, response_id: str, model: str, created_at: int):
    """将最终结果转换为 Responses API SSE 事件"""
    has_reasoning = result.get("has_reasoning", False)
    has_text = result.get("has_text", False)

    yield _sse_line({
        "type": "response.created",
        "response": {"id": response_id, "object": "response", "model": model,
                     "status": "in_progress", "output": []},
    })

    if has_reasoning:
        rs_id = _uid("rs")
        yield _sse_line({
            "type": "response.output_item.added", "output_index": 0,
            "item": {"id": rs_id, "type": "reasoning", "status": "completed",
                     "summary": [{"type": "summary_text", "text": result["reasoning"], "annotations": []}]},
        })
        yield _sse_line({
            "type": "response.output_item.done", "output_index": 0,
            "item": {"id": rs_id, "type": "reasoning", "status": "completed",
                     "summary": [{"type": "summary_text", "text": result["reasoning"], "annotations": []}]},
        })

    output_index = 1 if has_reasoning else 0
    output_items = []

    if has_text:
        msg_id = _uid("msg")
        yield _sse_line({
            "type": "response.output_item.added", "output_index": output_index,
            "item": {"id": msg_id, "type": "message", "role": "assistant",
                     "status": "in_progress", "content": []},
        })
        yield _sse_line({
            "type": "response.output_text.done", "item_id": msg_id,
            "output_index": output_index, "content_index": 0, "text": result["text"],
        })
        yield _sse_line({
            "type": "response.output_item.done", "output_index": output_index,
            "item": {"id": msg_id, "type": "message", "role": "assistant", "status": "completed",
                     "content": [{"type": "output_text", "text": result["text"], "annotations": []}]},
        })
        output_items.append({
            "id": msg_id, "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": result["text"], "annotations": []}],
        })

    # 输出非服务端工具调用
    for idx in sorted(result.get("tool_calls", {}).keys()):
        tc = result["tool_calls"][idx]
        if tc["name"] in TOOL_EXECUTORS:
            continue
        fc_id = _uid("fc")
        fc_item = {"id": fc_id, "type": "function_call", "call_id": tc["id"],
                   "name": tc["name"], "arguments": tc["arguments"], "status": "completed"}
        output_items.append(fc_item)
        oi = len(output_items) - 1
        yield _sse_line({
            "type": "response.output_item.added", "output_index": oi,
            "item": {"id": fc_id, "type": "function_call", "call_id": tc["id"],
                     "name": tc["name"], "arguments": tc["arguments"], "status": "completed"},
        })
        yield _sse_line({
            "type": "response.output_item.done", "output_index": oi, "item": fc_item,
        })

    yield _sse_line({
        "type": "response.completed",
        "response": {"id": response_id, "object": "response", "model": model,
                     "status": "completed", "output": output_items},
    })
