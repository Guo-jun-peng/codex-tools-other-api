"""路由辅助函数 —— adapter 解析、视觉路由、请求记录"""

from __future__ import annotations

import time

from ..config import get_config
from ..adapters import get_registry
from ..adapters.context import AdapterContext
from ..stats import get_stats, RequestLog


def get_adapter_for_model(model: str) -> tuple[AdapterContext, str, str]:
    cfg = get_config()
    provider_name, target_model = cfg.resolve_model(model)
    return resolve_adapter(provider_name, target_model)


def resolve_adapter(provider_name: str, target_model: str) -> tuple[AdapterContext, str, str]:
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

    base_url = provider.get("base_url") or adapter.base_url
    context = AdapterContext(adapter=adapter, base_url=base_url, api_key=api_key)
    return context, provider_name, target_model


def has_images(input_items: list[dict]) -> bool:
    for item in input_items:
        for field in ("content", "output"):
            content = item.get(field, "")
            if isinstance(content, list):
                for part in content:
                    if part.get("type") in ("input_image", "image_url"):
                        return True
    return False


def strip_images_from_input(input_items: list[dict]) -> None:
    for item in input_items:
        for field in ("content", "output"):
            content = item.get(field)
            if isinstance(content, list):
                item[field] = [p for p in content if p.get("type") not in ("input_image", "image_url")]


def route_vision(model: str, body: dict) -> tuple[AdapterContext, str, str]:
    cfg = get_config()
    input_items = body.get("input", [])

    if not has_images(input_items):
        return get_adapter_for_model(model)

    entry = cfg.model_mapping.get(model)
    if isinstance(entry, dict):
        if entry.get("is_multimodal"):
            return get_adapter_for_model(model)
        vision_alias = entry.get("vision_alias")
        if vision_alias and vision_alias in cfg.model_mapping:
            ventry = cfg.model_mapping[vision_alias]
            v_target = ventry.get("target", vision_alias)
            v_provider = ventry.get("provider", "") or ventry.get("target", "")
            try:
                return resolve_adapter(v_provider, v_target)
            except ValueError:
                pass

    vr = cfg.vision_routing
    if vr.get("enabled"):
        vision_provider = vr.get("provider", "doubao")
        vision_model = vr.get("model", "doubao-vision-pro-32k")
        try:
            return resolve_adapter(vision_provider, vision_model)
        except ValueError:
            pass

    strip_images_from_input(input_items)
    return get_adapter_for_model(model)


def record_request(
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


def record_and_respond(
    start_time: float,
    status_code: int,
    error: str,
    model: str,
    stream: bool,
    provider: str = "",
    target_model: str = "",
):
    from fastapi.responses import JSONResponse
    from ..models import build_error_response
    record_request(start_time, model, "responses", status_code, stream, error, provider=provider, target_model=target_model)
    return JSONResponse(content=build_error_response(error), status_code=status_code)


def write_image_file(filepath: str, data: bytes) -> None:
    with open(filepath, "wb") as f:
        f.write(data)
