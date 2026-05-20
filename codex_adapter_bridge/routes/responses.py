"""/v1/responses 端点 + 流式处理"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import get_config
from ..protocol import translate_request, translate_response, StreamTranslator
from ..client import UpstreamClient
from ..models import build_error_response, _uid
from ..tools import TOOL_EXECUTORS
from .helpers import route_vision, record_request, record_and_respond
from .image_gen import handle_responses_image_gen

logger = logging.getLogger("codex-adapter-bridge")


async def responses_endpoint(request: Request):
    start_time = time.time()
    status_code = 200
    error_msg = ""

    try:
        body = await request.json()
    except Exception:
        return record_and_respond(
            start_time, status_code=400, error="无效的 JSON 请求体",
            model="unknown", stream=False, provider="", target_model="",
        )

    model = body.get("model", "unknown")
    stream = body.get("stream", False)

    auth_header = request.headers.get("Authorization", "")
    header_api_key = auth_header[7:] if auth_header.startswith("Bearer ") else ""

    try:
        ctx, provider_name, target_model = route_vision(model, body)
    except ValueError as exc:
        if header_api_key:
            cfg = get_config()
            for pname, pinfo in cfg.providers.items():
                if not pinfo.get("api_key", ""):
                    cfg.add_or_update_provider(pname, {"api_key": header_api_key})
                    break
            try:
                ctx, provider_name, target_model = route_vision(model, body)
            except ValueError as exc2:
                status_code = 400
                error_msg = str(exc2)
                record_request(start_time, model, "responses", status_code, stream, error_msg, provider="", target_model="")
                return JSONResponse(content=build_error_response(error_msg), status_code=400)
        else:
            status_code = 400
            error_msg = str(exc)
            record_request(start_time, model, "responses", status_code, stream, error_msg, provider="", target_model="")
            return JSONResponse(content=build_error_response(error_msg), status_code=400)

    provider_timeout = get_config().get_provider(provider_name).get("timeout", 120) if provider_name else 120
    client = UpstreamClient(ctx, timeout=provider_timeout, stream_timeout=max(provider_timeout, 600))

    try:
        cfg = get_config()
        chat_req = translate_request(body, ctx.adapter, target_model)
        has_image_gen = chat_req.pop("_has_image_gen", False)

        if has_image_gen:
            return await handle_responses_image_gen(body, model)

        logger.info("Chat request -> %s: model=%s, msgs=%d, tools=%d, stream=%s",
            target_model, chat_req.get("model"),
            len(chat_req.get("messages", [])),
            len(chat_req.get("tools", []) or []),
            chat_req.get("stream"))

        request_tool_names = [t.get("function", {}).get("name", "") for t in (chat_req.get("tools") or [])]
        has_server_tools = any(name in TOOL_EXECUTORS for name in request_tool_names)

        if stream and has_server_tools:
            return StreamingResponse(
                handle_stream_with_tools(client, ctx, chat_req, model, start_time, provider_name, target_model),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        elif stream:
            return StreamingResponse(
                handle_stream(client, ctx, chat_req, model, start_time, provider_name, target_model),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            chat_resp = await client.chat_completion(chat_req)
            responses_resp = translate_response(chat_resp, ctx.adapter, model)
            tokens = chat_resp.get("usage", {}).get("total_tokens", 0)
            record_request(start_time, model, "responses", 200, False, "", tokens, provider=provider_name, target_model=target_model)
            return JSONResponse(content=responses_resp)

    except Exception as exc:
        status_code = 500
        error_msg = str(exc)
        logger.exception("请求处理异常")
        record_request(start_time, model, "responses", status_code, stream, error_msg, provider=provider_name, target_model=target_model)
        return JSONResponse(content=build_error_response(error_msg), status_code=500)
    finally:
        if not stream:
            await client.close()


async def handle_stream(
    client: UpstreamClient,
    ctx,
    chat_req: dict,
    model: str,
    start_time: float,
    provider: str = "",
    target_model: str = "",
):
    translator = StreamTranslator(model=model)
    stream_error = ""
    chat_stream = client.chat_completion_stream(chat_req)

    try:
        while True:
            try:
                chunk = await asyncio.wait_for(anext(chat_stream), timeout=120.0)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
                continue
            except StopAsyncIteration:
                break

            chunk = ctx.stream_event_transform(chunk)

            for event_line in translator.translate_chunk(chunk):
                yield event_line

    except Exception as exc:
        stream_error = str(exc)
        logger.exception("流式处理异常")

    if not stream_error:
        try:
            for event_line in translator._finish():
                yield event_line
        except Exception:
            pass

    if stream_error:
        record_request(start_time, model, "responses", 500, True, stream_error, provider=provider, target_model=target_model)
    else:
        record_request(start_time, model, "responses", 200, True, "", provider=provider, target_model=target_model)

    await client.close()


async def handle_stream_with_tools(
    client: UpstreamClient,
    ctx,
    chat_req: dict,
    model: str,
    start_time: float,
    provider: str = "",
    target_model: str = "",
):
    from ..tools.tool_loop import run_tool_loop

    async def _make_api_call(req: dict) -> dict:
        result = {"text": "", "reasoning": "", "tool_calls": {}, "has_text": False,
                  "has_reasoning": False, "chunks": 0, "error": None}
        try:
            async for chunk in client.chat_completion_stream(req):
                result["chunks"] += 1
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})

                r = delta.get("reasoning_content", "")
                if r:
                    result["has_reasoning"] = True
                    result["reasoning"] += r

                c = delta.get("content", "")
                if c:
                    result["has_text"] = True
                    result["text"] += c

                for td in delta.get("tool_calls", []):
                    idx = td.get("index", 0)
                    if idx not in result["tool_calls"]:
                        result["tool_calls"][idx] = {"id": td.get("id", ""), "name": "", "arguments": ""}
                    tc = result["tool_calls"][idx]
                    fn = td.get("function", {})
                    if fn.get("name"):
                        tc["name"] = fn["name"]
                    if fn.get("arguments"):
                        tc["arguments"] += fn["arguments"]
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
        return result

    response_id = _uid("resp")

    try:
        async for event_line in run_tool_loop(chat_req, _make_api_call, response_id, model):
            yield event_line
    except Exception as exc:
        logger.exception("工具代理循环异常")
        yield f"data: {json.dumps(build_error_response(str(exc)), ensure_ascii=False)}\n\n"
        record_request(start_time, model, "responses", 500, True, str(exc), provider=provider, target_model=target_model)
    else:
        record_request(start_time, model, "responses", 200, True, "", provider=provider, target_model=target_model)

    await client.close()
