"""代理循环逻辑 —— 调用 API → 执行工具 → 继续对话"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from ..protocol import _sse_line, _uid
from . import TOOL_EXECUTORS
from .sse_events import emit_final_output

logger = logging.getLogger("codex-adapter-bridge")

MAX_TOOL_ROUNDS = 5


async def run_tool_loop(
    chat_req: dict,
    make_api_call,
    response_id: str,
    model: str,
) -> AsyncIterator[str]:
    """代理循环：调用 API → 执行工具 → 继续对话，最多 MAX_TOOL_ROUNDS 轮"""
    import time as time_module

    created_at = int(time_module.time())

    for round_num in range(MAX_TOOL_ROUNDS):
        result = await make_api_call(chat_req)

        if result.get("error"):
            logger.error("上游错误: %s", result["error"])
            yield _sse_line({
                "type": "response.created",
                "response": {"id": response_id, "object": "response", "model": model,
                             "status": "in_progress", "output": []},
            })
            yield _sse_line({"type": "error", "error": {"message": result["error"]}})
            yield _sse_line({
                "type": "response.completed",
                "response": {"id": response_id, "object": "response", "model": model,
                             "status": "failed", "output": []},
            })
            return

        # 收集需要服务端执行的工具调用
        tool_results = []
        for idx in sorted(result.get("tool_calls", {}).keys()):
            tc = result["tool_calls"][idx]
            if tc["name"] in TOOL_EXECUTORS:
                executor = TOOL_EXECUTORS[tc["name"]]
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                query = args.get("query", str(args))
                try:
                    exec_result = await executor(query)
                except Exception as e:
                    exec_result = f"Tool error: {e}"
                tool_results.append((tc["name"], tc["id"], exec_result))
                logger.info("Tool %s: %.100s...", tc["name"], str(exec_result)[:100])

        if not tool_results:
            # 没有服务端工具需要执行，输出最终结果
            for event_line in emit_final_output(result, response_id, model, created_at):
                yield event_line
            return

        # 追加 assistant 消息 + tool 结果到对话历史
        messages = list(chat_req["messages"])
        a_msg = {"role": "assistant", "content": result.get("text") or None}
        tc_list = [
            {"id": result["tool_calls"][idx]["id"], "type": "function",
             "function": {"name": result["tool_calls"][idx]["name"],
                          "arguments": result["tool_calls"][idx]["arguments"]}}
            for idx in sorted(result["tool_calls"].keys())
            if result["tool_calls"][idx]["name"] in TOOL_EXECUTORS
        ]
        if tc_list:
            a_msg["tool_calls"] = tc_list
        messages.append(a_msg)
        for name, call_id, output in tool_results:
            messages.append({"role": "tool", "tool_call_id": call_id, "content": output})

        chat_req = {"model": chat_req["model"], "messages": messages, "stream": True}

    # 超过最大轮数
    yield _sse_line({
        "type": "response.created",
        "response": {"id": response_id, "object": "response", "model": model,
                     "status": "in_progress", "output": []},
    })
    yield _sse_line({"type": "error", "error": {"message": "Max tool rounds exceeded"}})
    yield _sse_line({
        "type": "response.completed",
        "response": {"id": response_id, "object": "response", "model": model,
                     "status": "failed", "output": []},
    })
