"""/v1/chat/completions 端点"""

from __future__ import annotations

import json
import logging
import time

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import get_config
from ..client import UpstreamClient
from ..models import build_error_response
from .helpers import get_adapter_for_model, record_request

logger = logging.getLogger("codex-adapter-bridge")


async def chat_completions_endpoint(request: Request):
    start_time = time.time()
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content=build_error_response("无效的 JSON 请求体"), status_code=400)

    model = body.get("model", "unknown")
    stream = body.get("stream", False)

    try:
        ctx, provider_name, target_model = get_adapter_for_model(model)
    except ValueError as exc:
        record_request(start_time, model, "chat", 400, stream, str(exc), provider="", target_model="")
        return JSONResponse(content=build_error_response(str(exc)), status_code=400)

    body["model"] = target_model
    body = ctx.preprocess_chat_request(body)

    provider_timeout = get_config().get_provider(provider_name).get("timeout", 120) if provider_name else 120
    client = UpstreamClient(ctx, timeout=provider_timeout, stream_timeout=max(provider_timeout, 600))
    try:
        if stream:
            async def _sse_gen():
                async for chunk in client.chat_completion_stream(body):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                _sse_gen(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )
        else:
            resp = await client.chat_completion(body)
            resp = ctx.postprocess_chat_response(resp)
            tokens = resp.get("usage", {}).get("total_tokens", 0)
            record_request(start_time, model, "chat", 200, False, "", tokens, provider=provider_name, target_model=target_model)
            return JSONResponse(content=resp)
    except Exception as exc:
        record_request(start_time, model, "chat", 500, stream, str(exc), provider=provider_name, target_model=target_model)
        return JSONResponse(content=build_error_response(str(exc)), status_code=500)
    finally:
        await client.close()
