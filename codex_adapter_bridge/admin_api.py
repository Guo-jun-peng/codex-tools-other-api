"""管理 API —— 供桌面 UI 调用的配置管理端点"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from .config import get_config
from .adapters import get_registry
from .adapters.context import AdapterContext
from .stats import get_stats, RequestLog
from .client import UpstreamClient
from .codex_config import CodexConfigManager

logger = logging.getLogger("codex-adapter-bridge")

router = APIRouter(prefix="/admin/api")

_codex_mgr = CodexConfigManager()


# ═══════════════════════════════════════════════════════════════════
# 状态
# ═══════════════════════════════════════════════════════════════════

@router.get("/status")
async def get_status():
    cfg = get_config()
    stats = get_stats()
    return {
        "running": True,
        "host": cfg.server_host,
        "port": cfg.server_port,
        "version": "1.0.0",
        "stats": stats.get_summary(),
    }


# ═══════════════════════════════════════════════════════════════════
# 适配器元数据
# ═══════════════════════════════════════════════════════════════════

@router.get("/adapters")
async def list_adapters():
    reg = get_registry()
    adapters = []
    for name in reg.list():
        adapter = reg.get(name)
        if adapter:
            adapters.append({
                "name": name,
                "base_url": adapter.base_url,
                "api_key_env": adapter.api_key_env,
            })
    return {"adapters": adapters}


# ═══════════════════════════════════════════════════════════════════
# 模型 CRUD
# ═══════════════════════════════════════════════════════════════════

@router.get("/models")
async def list_models():
    cfg = get_config()
    reg = get_registry()
    providers = cfg.providers
    mapping = cfg.model_mapping

    models = []
    for alias, entry in mapping.items():
        target = entry.get("target", alias)
        provider_name = entry.get("provider", "") or _find_provider_for_target(target, providers)
        provider = providers.get(provider_name, {})
        models.append({
            "alias": alias,
            "target_model": target,
            "provider": provider_name or "",
            "adapter": provider.get("adapter", ""),
            "base_url": provider.get("base_url", ""),
            "api_key_env": provider.get("api_key_env", ""),
            "api_key_set": bool(provider.get("api_key", "")),
            "api_key_hint": _mask_key(provider.get("api_key", "")),
            "enabled": entry.get("enabled", True),
            "is_multimodal": entry.get("is_multimodal", False),
            "vision_alias": entry.get("vision_alias") or "",
            "is_image_gen": entry.get("is_image_gen", False),
            "image_gen_alias": entry.get("image_gen_alias") or "",
            "is_video_gen": entry.get("is_video_gen", False),
            "video_gen_alias": entry.get("video_gen_alias") or "",
            "available_adapters": reg.list(),
        })
    return {"models": models}


@router.post("/models")
async def add_model(data: dict):
    cfg = get_config()
    alias = data.get("alias", "").strip()
    target = data.get("target_model", "").strip()

    if not alias or not target:
        return {"error": "alias 和 target_model 为必填项"}, 400

    provider_name = data.get("provider", target)
    provider_info = {
        "adapter": data.get("adapter", provider_name),
        "base_url": data.get("base_url", ""),
        "api_key_env": data.get("api_key_env", ""),
        "enabled": data.get("enabled", True),
    }
    if data.get("api_key"):
        provider_info["api_key"] = data["api_key"]
    advanced = data.get("advanced", {})
    if advanced:
        provider_info["timeout"] = advanced.get("timeout", 120)
        provider_info["max_retries"] = advanced.get("max_retries", 0)
    cfg.add_or_update_provider(provider_name, provider_info)

    entry = {
        "target": target,
        "provider": provider_name,
        "enabled": data.get("enabled", True),
        "is_multimodal": data.get("is_multimodal", False),
        "vision_alias": data.get("vision_alias") or None,
        "is_image_gen": data.get("is_image_gen", False),
        "image_gen_alias": data.get("image_gen_alias") or None,
        "is_video_gen": data.get("is_video_gen", False),
        "video_gen_alias": data.get("video_gen_alias") or None,
    }
    cfg.add_model(alias, entry)
    return {"status": "ok", "alias": alias}


@router.put("/models/{alias}")
async def update_model(alias: str, data: dict):
    cfg = get_config()
    mapping = cfg.model_mapping

    if alias not in mapping:
        return {"error": f"模型别名 '{alias}' 不存在"}, 404

    old_entry = mapping[alias]
    model_fields = {}
    for key in ("target_model", "provider", "enabled", "is_multimodal",
                "vision_alias", "is_image_gen", "image_gen_alias",
                "is_video_gen", "video_gen_alias"):
        if key in data:
            model_fields[key if key == "target_model" else key] = data[key]
    if model_fields:
        cfg.update_model(alias, model_fields)

    provider_name = model_fields.get("provider", old_entry.get("provider", ""))
    if provider_name:
        provider_updates = {}
        if "base_url" in data:
            provider_updates["base_url"] = data["base_url"]
        if "api_key" in data and data["api_key"]:
            provider_updates["api_key"] = data["api_key"]
        if "api_key_env" in data:
            provider_updates["api_key_env"] = data["api_key_env"]
        if "enabled" in data:
            provider_updates["enabled"] = data["enabled"]
        advanced = data.get("advanced", {})
        if advanced:
            provider_updates["timeout"] = advanced.get("timeout", 120)
            provider_updates["max_retries"] = advanced.get("max_retries", 0)
        if provider_updates:
            cfg.add_or_update_provider(provider_name, provider_updates)

    return {"status": "ok", "alias": alias}


@router.delete("/models/{alias}")
async def delete_model(alias: str):
    cfg = get_config()
    if alias not in cfg.model_mapping:
        return {"error": f"模型别名 '{alias}' 不存在"}, 404
    cfg.delete_model(alias)
    return {"status": "ok"}


@router.put("/models/{alias}/toggle")
async def toggle_model(alias: str):
    cfg = get_config()
    if alias not in cfg.model_mapping:
        return {"error": f"模型别名 '{alias}' 不存在"}, 404
    try:
        new_state = cfg.toggle_model(alias)
        return {"status": "ok", "alias": alias, "enabled": new_state}
    except KeyError:
        return {"error": "旧格式模型不支持切换，请编辑模型"}, 400


# ═══════════════════════════════════════════════════════════════════
# 连接测试
# ═══════════════════════════════════════════════════════════════════

@router.post("/models/{alias}/test")
async def test_connection(alias: str, data: dict | None = None):
    cfg = get_config()
    reg = get_registry()
    mapping = cfg.model_mapping

    entry = mapping.get(alias, alias)
    if isinstance(entry, dict):
        target = entry.get("target", alias)
        provider_name = entry.get("provider", "") or _find_provider_for_target(target, cfg.providers)
    else:
        target = entry
        provider_name = _find_provider_for_target(target, cfg.providers)

    if not provider_name:
        return {"status": "error", "message": f"未找到模型 '{alias}' 的 provider 配置"}

    provider = cfg.providers[provider_name]
    adapter_name = provider.get("adapter", provider_name)
    adapter = reg.get(adapter_name)
    if not adapter:
        return {"status": "error", "message": f"未找到适配器 '{adapter_name}'"}

    api_key = data.get("api_key") if data else None
    if not api_key:
        api_key = provider.get("api_key", "")
    if not api_key:
        return {"status": "error", "message": "API Key 未设置"}

    if data and data.get("base_url"):
        base_url = data["base_url"]
    elif provider.get("base_url"):
        base_url = provider["base_url"]
    else:
        base_url = adapter.base_url

    ctx = AdapterContext(adapter=adapter, base_url=base_url, api_key=api_key)
    headers = ctx.get_headers()
    chat_url = ctx.build_chat_url()
    chat_body = ctx.preprocess_chat_request({
        "model": target,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
        "stream": False,
    })

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as client:
            resp = await client.post(chat_url, json=chat_body, headers=headers)
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                return {
                    "status": "ok",
                    "elapsed_ms": round(elapsed, 1),
                    "message": f"连接成功 ({resp.status_code})",
                }

            return {
                "status": "error",
                "elapsed_ms": round(elapsed, 1),
                "message": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }
    except httpx.TimeoutException:
        return {"status": "error", "message": "连接超时（15秒）"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ═══════════════════════════════════════════════════════════════════
# 全局设置
# ═══════════════════════════════════════════════════════════════════

@router.get("/settings")
async def get_settings():
    cfg = get_config()
    sc = cfg.server_config
    return {
        "server": {
            "host": cfg.server_host,
            "port": cfg.server_port,
            "log_level": sc.get("log_level", "info"),
            "auto_start": sc.get("auto_start", False),
            "close_to_tray": sc.get("close_to_tray", True),
        },
        "config_path": str(cfg._config_path) if cfg._config_path else "",
    }


@router.put("/settings")
async def update_settings(data: dict):
    cfg = get_config()
    try:
        cfg.update_server(data)
    except ValueError as exc:
        return {"error": str(exc)}, 400
    return {"status": "ok", "message": "设置已保存，部分设置需重启后生效"}


# ═══════════════════════════════════════════════════════════════════
# Codex 配置管理
# ═══════════════════════════════════════════════════════════════════

@router.get("/codex/status")
async def codex_status():
    return _codex_mgr.get_status()


@router.post("/codex/apply")
async def codex_apply(data: dict):
    model = data.get("model", "")
    port = data.get("port", 8899)
    if not model:
        return {"error": "model 为必填项"}, 400

    _codex_mgr.backup_configs()
    ok = _codex_mgr.write_codex_config(model, int(port))
    return {"status": "ok" if ok else "error", "message": "配置已写入" if ok else "写入失败"}


@router.post("/codex/restore")
async def codex_restore():
    ok = _codex_mgr.restore_configs()
    return {"status": "ok" if ok else "error", "message": "配置已恢复" if ok else "恢复失败，可能没有备份"}


# ═══════════════════════════════════════════════════════════════════
# 服务端工具管理
# ═══════════════════════════════════════════════════════════════════

@router.get("/tools")
async def get_tools():
    cfg = get_config()
    tools_cfg = cfg.tools
    from .tools import TOOL_EXECUTORS
    tools = {}
    for name in TOOL_EXECUTORS:
        tools[name] = {
            "enabled": tools_cfg.get(name, {}).get("enabled", True),
        }
    return {"tools": tools}


@router.put("/tools")
async def update_tools(data: dict):
    cfg = get_config()
    cfg.update_tools(data)
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════
# 日志
# ═══════════════════════════════════════════════════════════════════

@router.get("/logs")
async def get_logs(limit: int = 100):
    stats = get_stats()
    return {"logs": stats.get_recent_logs(limit)}


@router.post("/logs/clear")
async def clear_logs():
    get_stats().clear_logs()
    return {"status": "ok"}


@router.websocket("/logs/stream")
async def logs_stream(websocket: WebSocket):
    await websocket.accept()

    queue: asyncio.Queue = asyncio.Queue()

    def on_log(entry: dict):
        try:
            queue.put_nowait(entry)
        except Exception:
            pass

    stats = get_stats()
    stats.add_listener(on_log)

    try:
        while True:
            entry = await queue.get()
            await websocket.send_json(entry)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        stats.remove_listener(on_log)


# ═══════════════════════════════════════════════════════════════════
# 配置导入导出
# ═══════════════════════════════════════════════════════════════════

@router.get("/config/export")
async def export_config():
    import yaml
    cfg = get_config()
    data = cfg.export_config()
    return {
        "yaml": yaml.dump(data, allow_unicode=True, default_flow_style=False),
        "config_path": str(cfg._config_path) if cfg._config_path else "",
    }


@router.post("/config/import")
async def import_config(data: dict):
    import yaml
    cfg = get_config()
    yaml_str = data.get("yaml", "")
    if not yaml_str:
        return {"error": "缺少 yaml 字段"}, 400
    try:
        new_data = yaml.safe_load(yaml_str)
        cfg.import_config(new_data)
        return {"status": "ok"}
    except Exception as exc:
        return {"error": str(exc)}, 400


@router.post("/shutdown")
async def shutdown():
    import sys

    def _do_shutdown():
        import time as _time
        _time.sleep(0.1)
        sys.exit(0)

    import threading
    threading.Thread(target=_do_shutdown, daemon=True).start()
    return {"status": "ok", "message": "正在关闭..."}


# ═══════════════════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════════════════

def _mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return key
    return key[:5] + "***" + key[-3:]


def _find_provider_for_target(target: str, providers: dict) -> str | None:
    for pname, pinfo in providers.items():
        if pinfo.get("adapter") == target or pname == target:
            return pname
    for pname in providers:
        if pname in target.lower():
            return pname
    return next(iter(providers), None) if providers else None
