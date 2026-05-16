"""服务端工具执行 —— web_search 等内置工具的本地执行与代理循环"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator

import httpx

logger = logging.getLogger("codex-adapter-bridge")


async def execute_web_search(query: str) -> str:
    """执行 DuckDuckGo Lite 搜索，返回格式化结果"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            resp = await client.get(
                "https://lite.duckduckgo.com/lite/",
                params={"q": query},
                headers={"User-Agent": "CodexAdapter/1.0"},
            )
            if resp.status_code != 200:
                return f"搜索失败: HTTP {resp.status_code}"

            text = resp.text
            results: list[str] = []
            links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', text)
            snippets = re.findall(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', text, re.DOTALL)

            for i, (url, title) in enumerate(links[:5]):
                if 'duckduckgo.com' in url:
                    continue
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                snippet_clean = ""
                if i < len(snippets):
                    snippet_clean = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                results.append(f"{i+1}. {title_clean}\n   URL: {url}\n   {snippet_clean}")

            if results:
                return "搜索结果:\n\n" + "\n\n".join(results)
            return "未找到相关搜索结果"
    except Exception as e:
        return f"搜索异常: {str(e)}"


TOOL_EXECUTORS = {
    "web_search": execute_web_search,
}


MAX_TOOL_ROUNDS = 5


async def run_tool_loop(
    chat_req: dict,
    make_api_call,
    response_id: str,
    model: str,
) -> AsyncIterator[str]:
    """代理循环：调用 API → 执行工具 → 继续对话，最多 MAX_TOOL_ROUNDS 轮"""
    from .protocol import _sse_line, _uid
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
            for event_line in _emit_final_output(result, response_id, model, created_at):
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


def _emit_final_output(result: dict, response_id: str, model: str, created_at: int):
    """将最终结果转换为 Responses API SSE 事件"""
    from .protocol import _sse_line
    from .models import _uid

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
