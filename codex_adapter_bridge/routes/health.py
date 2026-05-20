"""/health, /v1/models, /admin/reload-config 端点"""

from __future__ import annotations

from fastapi import APIRouter

from ..config import get_config, reload_config
from ..adapters import get_registry

router = APIRouter()


@router.get("/health")
async def health():
    reg = get_registry()
    cfg = get_config()
    return {
        "status": "ok",
        "adapters": reg.list(),
        "model_mapping": cfg.model_mapping,
    }


@router.get("/v1/models")
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


@router.post("/admin/reload-config")
async def admin_reload():
    reload_config()
    return {"status": "ok", "message": "配置已重新加载"}
