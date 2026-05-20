"""图片生成处理"""

from __future__ import annotations

import asyncio
import base64
import logging
import os

import httpx
from fastapi.responses import JSONResponse

from ..config import get_config
from ..models import build_error_response, build_responses_response, make_message_output_item, _uid
from .helpers import resolve_adapter

logger = logging.getLogger("codex-adapter-bridge")


async def handle_responses_image_gen(body: dict, model: str) -> JSONResponse:
    cfg = get_config()
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
        ctx, _, _ = resolve_adapter(provider_name, img_target)
    except ValueError as exc:
        return JSONResponse(build_error_response(str(exc)), status_code=400)

    img_body = {
        "model": img_target,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    img_body = ctx.preprocess_image_gen_request(img_body)
    img_url = ctx.build_image_gen_url()
    headers = ctx.get_headers()

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
                        image_data = base64.b64encode(img_resp.content).decode("ascii")
                    else:
                        logger.warning("下载生图结果失败: HTTP %d", img_resp.status_code)
            except Exception as exc:
                logger.warning("下载生图结果异常: %s", exc)

    if not image_data:
        return JSONResponse(build_error_response("生图 API 返回了结果但没有图片数据", "no_image_data"), status_code=500)

    img_bytes = base64.b64decode(image_data)
    cwd = os.getcwd()
    img_filename = f"generated_image_{_uid('img')}.png"
    img_filepath = os.path.join(cwd, img_filename)
    await asyncio.to_thread(_write_image_file, img_filepath, img_bytes)
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


def _write_image_file(filepath: str, data: bytes) -> None:
    with open(filepath, "wb") as f:
        f.write(data)
