"""FastAPI 服务器 —— 提供 /v1/responses 端点、管理 API 和 WebSocket"""

from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import mimetypes

# Fix MIME types for Windows (otherwise .js files are served as text/plain)
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_config, reload_config
from .adapters import get_registry
from .adapters.base import BaseAdapter
from .protocol import translate_request, translate_response, StreamTranslator
from .client import UpstreamClient
from .middleware import (
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware,
    ApiKeyFilter,
)
from .models import build_error_response, build_responses_response, make_message_output_item, _uid
from .stats import get_stats, RequestLog
from .tools import TOOL_EXECUTORS
from .admin_api import router as admin_router

logger = logging.getLogger("codex-adapter-bridge")


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt)

    root = logging.getLogger("codex-adapter-bridge")
    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(ApiKeyFilter())
    root.addHandler(console)

    log_file = Path(__file__).resolve().parent.parent / "bridge.log"
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)


def _get_adapter_for_model(model: str) -> tuple[BaseAdapter, str, str, str]:
    cfg = get_config()
    provider_name, target_model = cfg.resolve_model(model)
    return _resolve_adapter(provider_name, target_model)


def _resolve_adapter(provider_name: str, target_model: str) -> tuple[BaseAdapter, str, str, str]:
    cfg = get_config()
    provider = cfg.get_provider(provider_name)

    if not provider:
        raise ValueError(
            f"未找到 provider '{provider_name}' 配置。"
            f"请在 config.yaml 中配置 providers。"
        )

    adapter_name = provider.get("adapter", provider_name)
    reg = get_registry()
    adapter = reg.get(adapter_name)
    if not adapter:
        raise ValueError(
            f"未找到适配器 '{adapter_name}'。"
            f"可用适配器: {reg.list()}"
        )

    api_key = provider.get("api_key", "")
    if not api_key:
        raise ValueError(
            f"Provider '{provider_name}' 的 API Key 未设置。"
            f"请设置环境变量 {provider.get('api_key_env', '???')}"
        )

    if provider.get("base_url"):
        adapter.base_url = provider["base_url"]

    return adapter, provider_name, target_model, api_key


def _has_images(input_items: list[dict]) -> bool:
    for item in input_items:
        for field in ("content", "output"):
            content = item.get(field, "")
            if isinstance(content, list):
                for part in content:
                    if part.get("type") in ("input_image", "image_url"):
                        return True
    return False


async def _handle_responses_image_gen(body: dict, cfg, model: str) -> JSONResponse:
    import json as _json
    import base64 as _base64

    prompt = ""
    size = "2560x1440"
    for item in reversed(body.get("input", [])):
        if item.get("type") == "message" and item.get("role") == "user":
            content = item.get("content", "")
            if isinstance(content, list):
                parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                prompt = " ".join(parts)
            else:
                prompt = str(content)
            break

    tools = body.get("tools", [])
    for t in tools:
        if t.get("type") == "image_gen":
            t_size = t.get("size", "")
            if t_size:
                size = t_size
            break

    if not prompt:
        return JSONResponse(
            build_error_response("无法从请求中提取生图提示词", "invalid_request"),
            status_code=400,
        )

    img_alias = ""
    img_target = ""
    img_provider = ""
    mapping = cfg.model_mapping
    for alias, entry in mapping.items():
        if isinstance(entry, dict) and entry.get("is_image_gen"):
            img_alias = alias
            img_target = entry.get("target", alias)
            img_provider = entry.get("provider", "")
            break

    if not img_alias:
        return JSONResponse(
            build_error_response("未配置生图模型", "no_image_gen_model"),
            status_code=400,
        )

    provider_name = img_provider
    if not provider_name:
        for pname in cfg.providers:
            if pname in img_target.lower():
                provider_name = pname
                break
    if not provider_name and cfg.providers:
        provider_name = next(iter(cfg.providers))

    if not provider_name or provider_name not in cfg.providers:
        return JSONResponse(
            build_error_response(f"生图模型 {img_alias} 的 provider 不存在"),
            status_code=400,
        )

    try:
        adapter, _, _, api_key = _resolve_adapter(provider_name, img_target)
    except ValueError as exc:
        return JSONResponse(build_error_response(str(exc)), status_code=400)

    img_body = {
        "model": img_target,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    img_body = adapter.preprocess_image_gen_request(img_body)
    img_url = adapter.build_image_gen_url()
    headers = adapter.get_headers(api_key)

    logger.info("image_gen → %s: prompt=%.80s..., size=%s", img_url, prompt[:80], size)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120)) as client:
            resp = await client.post(img_url, json=img_body, headers=headers)
            result = resp.json()
    except httpx.TimeoutException:
        return JSONResponse(build_error_response("生图请求超时（120秒）", "timeout"), status_code=504)
    except Exception as exc:
        logger.exception("生图 API 调用失败")
        return JSONResponse(build_error_response(f"生图 API 调用失败: {exc}", "image_gen_failed"), status_code=500)

    if resp.status_code != 200:
        err_msg = result.get("error", {}).get("message", str(result))
        logger.warning("生图失败: %s", err_msg)
        return JSONResponse(build_error_response(f"生图失败: {err_msg}", "image_gen_failed"), status_code=resp.status_code)

    image_data = None
    image_url_from_api = ""
    data_items = result.get("data", [])
    if data_items:
        first = data_items[0]
        image_url_from_api = first.get("url", "")
        b64 = first.get("b64_json", "")
        if b64:
            image_data = b64
        elif image_url_from_api:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(60)) as client:
                    img_resp = await client.get(image_url_from_api)
                    if img_resp.status_code == 200:
                        image_data = _base64.b64encode(img_resp.content).decode("ascii")
                    else:
                        logger.warning("下载生图结果失败: HTTP %d", img_resp.status_code)
            except Exception as exc:
                logger.warning("下载生图结果异常: %s", exc)

    if not image_data:
        return JSONResponse(build_error_response("生图 API 返回了结果但没有图片数据", "no_image_data"), status_code=500)

    import os as _os
    img_bytes = _base64.b64decode(image_data)
    cwd = _os.getcwd()
    img_filename = f"generated_image_{_uid('img')}.png"
    img_filepath = _os.path.join(cwd, img_filename)
    with open(img_filepath, "wb") as f:
        f.write(img_bytes)
    logger.info("图片已保存: %s (%d bytes)", img_filepath, len(img_bytes))

    call_id = _uid("call_")
    img_output = image_url_from_api or ("data:image/jpeg;base64," + image_data)

    output_items = [
        {
            "id": _uid("icall"),
            "object": "realtime.item",
            "type": "image_generation_call",
            "call_id": call_id,
            "prompt": prompt,
            "size": size,
            "status": "completed",
        },
        {
            "id": _uid("icall_out"),
            "object": "realtime.item",
            "type": "image_generation_call_output",
            "call_id": call_id,
            "output": img_output,
        },
    ]
    output_items.append(make_message_output_item(f"图片已生成并保存到: {img_filepath}"))

    logger.info("image_gen 完成: file=%s", img_filename)
    return JSONResponse(content=build_responses_response(output_items, model, None))


def _route_vision(model: str, body: dict) -> tuple[BaseAdapter, str, str, str]:
    cfg = get_config()
    input_items = body.get("input", [])

    if not _has_images(input_items):
        return _get_adapter_for_model(model)

    entry = cfg.model_mapping.get(model)
    if isinstance(entry, dict):
        if entry.get("is_multimodal"):
            logger.info("模型 %s 是多模态的，使用自身处理图片", model)
            return _get_adapter_for_model(model)
        vision_alias = entry.get("vision_alias")
        if vision_alias and vision_alias in cfg.model_mapping:
            ventry = cfg.model_mapping[vision_alias]
            v_target = ventry.get("target", vision_alias)
            v_provider = ventry.get("provider", "") or ventry.get("target", "")
            try:
                logger.info("检测到图片输入，切换到视觉模型: %s/%s", v_provider, v_target)
                return _resolve_adapter(v_provider, v_target)
            except ValueError as exc:
                logger.warning("视觉模型 %s/%s 不可用: %s", v_provider, v_target, exc)

    vr = cfg.vision_routing
    if vr.get("enabled"):
        vision_provider = vr.get("provider", "doubao")
        vision_model = vr.get("model", "doubao-vision-pro-32k")
        try:
            logger.info("检测到图片输入，使用全局视觉路由: %s/%s", vision_provider, vision_model)
            return _resolve_adapter(vision_provider, vision_model)
        except ValueError as exc:
            logger.warning("全局视觉路由不可用: %s", exc)

    logger.warning("视觉路由未配置，使用文本模型（图片已移除）")
    _strip_images_from_input(input_items)
    return _get_adapter_for_model(model)


def _strip_images_from_input(input_items: list[dict]) -> None:
    for item in input_items:
        for field in ("content", "output"):
            content = item.get(field)
            if isinstance(content, list):
                item[field] = [p for p in content if p.get("type") not in ("input_image", "image_url")]


# ── 应用工厂 ───────────────────────────────────────────────────────

def create_app(verbose: bool = False) -> FastAPI:
    _setup_logging(verbose)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Codex 国内模型适配工具 启动中...")
        cfg = get_config()
        reg = get_registry()
        logger.info("已加载适配器: %s", reg.list())
        logger.info("服务地址: http://%s:%d", cfg.server_host, cfg.server_port)
        yield
        logger.info("Codex 国内模型适配工具 已关闭")

    app = FastAPI(
        title="Codex 国内模型适配工具",
        version="1.0.0",
        description="OpenAI Responses API → Chat Completions API 协议转换代理",
        lifespan=lifespan,
    )

    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "app://."],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(admin_router)

    @app.get("/health")
    async def health():
        reg = get_registry()
        cfg = get_config()
        return {
            "status": "ok",
            "adapters": reg.list(),
            "model_mapping": cfg.model_mapping,
        }

    @app.get("/v1/models")
    async def list_models():
        cfg = get_config()
        models = []
        for alias, entry in cfg.model_mapping.items():
            if entry.get("enabled", True):
                models.append({
                    "id": alias,
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": entry.get("provider", "codex-adapter-bridge"),
                })
        return {"object": "list", "data": models}

    @app.post("/admin/reload-config")
    async def admin_reload():
        reload_config()
        return {"status": "ok", "message": "配置已重新加载"}

    @app.post("/v1/responses")
    async def responses_endpoint(request: Request):
        start_time = time.time()
        status_code = 200
        error_msg = ""

        try:
            body = await request.json()
        except Exception:
            return _record_and_respond(
                start_time, status_code=400, error="无效的 JSON 请求体",
                model="unknown", stream=False, provider="", target_model="",
            )

        model = body.get("model", "unknown")
        stream = body.get("stream", False)

        # Extract API key from Authorization header (Codex passes auth.json key)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            header_api_key = auth_header[7:]
            # Inject into all providers that don't have an API key set
            cfg = get_config()
            for pname, pinfo in cfg._data.get("providers", {}).items():
                if not pinfo.get("api_key", ""):
                    pinfo["api_key"] = header_api_key

        try:
            adapter, provider_name, target_model, api_key = _route_vision(model, body)
        except ValueError as exc:
            status_code = 400
            error_msg = str(exc)
            _record_request(start_time, model, "responses", status_code, stream, error_msg, provider="", target_model="")
            return JSONResponse(content=build_error_response(error_msg), status_code=400)

        provider_timeout = get_config().get_provider(provider_name).get("timeout", 120) if provider_name else 120
        client = UpstreamClient(adapter, api_key, timeout=provider_timeout, stream_timeout=max(provider_timeout, 600))

        try:
            cfg = get_config()
            chat_req = translate_request(body, adapter, target_model)
            has_image_gen = chat_req.pop("_has_image_gen", False)

            if has_image_gen:
                return await _handle_responses_image_gen(body, cfg, model)

            logger.info("Chat request -> %s: model=%s, msgs=%d, tools=%d, stream=%s",
                target_model, chat_req.get("model"),
                len(chat_req.get("messages", [])),
                len(chat_req.get("tools", []) or []),
                chat_req.get("stream"))

            # Only use agent loop if request actually has server-executable tools
            request_tool_names = [t.get("function", {}).get("name", "") for t in (chat_req.get("tools") or [])]
            has_server_tools = any(name in TOOL_EXECUTORS for name in request_tool_names)

            if stream and has_server_tools:
                return StreamingResponse(
                    _handle_stream_with_tools(client, adapter, chat_req, model, start_time, provider_name, target_model),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )
            elif stream:
                return StreamingResponse(
                    _handle_stream(client, adapter, chat_req, model, start_time, provider_name, target_model),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )
            else:
                chat_resp = await client.chat_completion(chat_req)
                responses_resp = translate_response(chat_resp, adapter, model)
                tokens = chat_resp.get("usage", {}).get("total_tokens", 0)
                _record_request(start_time, model, "responses", 200, False, "", tokens, provider=provider_name, target_model=target_model)
                return JSONResponse(content=responses_resp)

        except Exception as exc:
            status_code = 500
            error_msg = str(exc)
            logger.exception("请求处理异常")
            _record_request(start_time, model, "responses", status_code, stream, error_msg, provider=provider_name, target_model=target_model)
            return JSONResponse(content=build_error_response(error_msg), status_code=500)
        finally:
            if not stream:
                await client.close()

    @app.post("/v1/chat/completions")
    async def chat_completions_endpoint(request: Request):
        start_time = time.time()
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(content=build_error_response("无效的 JSON 请求体"), status_code=400)

        model = body.get("model", "unknown")
        stream = body.get("stream", False)

        try:
            adapter, provider_name, target_model, api_key = _get_adapter_for_model(model)
        except ValueError as exc:
            _record_request(start_time, model, "chat", 400, stream, str(exc), provider="", target_model="")
            return JSONResponse(content=build_error_response(str(exc)), status_code=400)

        body["model"] = target_model
        body = adapter.preprocess_chat_request(body)

        provider_timeout = get_config().get_provider(provider_name).get("timeout", 120) if provider_name else 120
        client = UpstreamClient(adapter, api_key, timeout=provider_timeout, stream_timeout=max(provider_timeout, 600))
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
                resp = adapter.postprocess_chat_response(resp)
                tokens = resp.get("usage", {}).get("total_tokens", 0)
                _record_request(start_time, model, "chat", 200, False, "", tokens, provider=provider_name, target_model=target_model)
                return JSONResponse(content=resp)
        except Exception as exc:
            _record_request(start_time, model, "chat", 500, stream, str(exc), provider=provider_name, target_model=target_model)
            return JSONResponse(content=build_error_response(str(exc)), status_code=500)
        finally:
            await client.close()

    # ── 静态前端 (React SPA) ────────────────────────────────────
    _dist = Path(__file__).resolve().parent.parent / "desktop" / "dist"
    if _dist.is_dir() and (_dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """SPA fallback: 所有非 API 路径返回 index.html"""
            file_path = _dist / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(_dist / "index.html")

        logger.info("静态前端已挂载: %s", _dist)

    return app


# ── 流式处理 ────────────────────────────────────────────────────────

async def _handle_stream(
    client: UpstreamClient,
    adapter: BaseAdapter,
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

            chunk = adapter.stream_event_transform(chunk)

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
        _record_request(start_time, model, "responses", 500, True, stream_error, provider=provider, target_model=target_model)
    else:
        _record_request(start_time, model, "responses", 200, True, "", provider=provider, target_model=target_model)

    await client.close()


async def _handle_stream_with_tools(
    client: UpstreamClient,
    adapter: BaseAdapter,
    chat_req: dict,
    model: str,
    start_time: float,
    provider: str = "",
    target_model: str = "",
):
    """流式处理 + 服务端工具代理循环 (web_search 等)"""
    from .tools import run_tool_loop

    async def _make_api_call(req: dict) -> dict:
        """单次 API 调用，收集结果"""
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
        _record_request(start_time, model, "responses", 500, True, str(exc), provider=provider, target_model=target_model)
    else:
        _record_request(start_time, model, "responses", 200, True, "", provider=provider, target_model=target_model)

    await client.close()


def _record_request(
    start_time: float,
    model: str,
    endpoint: str,
    status_code: int,
    stream: bool,
    error: str = "",
    tokens: int = 0,
    provider: str = "",
    target_model: str = "",
):
    elapsed = (time.time() - start_time) * 1000
    get_stats().record(RequestLog(
        timestamp=start_time,
        model=model,
        endpoint=endpoint,
        status_code=status_code,
        elapsed_ms=elapsed,
        tokens=tokens,
        error=error,
        stream=stream,
        provider=provider,
        target_model=target_model,
    ))


def _record_and_respond(
    start_time: float,
    status_code: int,
    error: str,
    model: str,
    stream: bool,
    provider: str = "",
    target_model: str = "",
):
    _record_request(start_time, model, "responses", status_code, stream, error, provider=provider, target_model=target_model)
    return JSONResponse(content=build_error_response(error), status_code=status_code)
