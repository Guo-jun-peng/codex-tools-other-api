"""路由子包 —— 汇总注册所有 API 端点"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from .health import router as health_router
from . import responses, chat
from .static import mount_spa


def register_routes(app: FastAPI) -> None:
    """直接将端点注册到 app 上"""
    # health router (these use decorator-based registration)
    app.include_router(health_router)

    # manual route registration for non-decorator endpoints
    app.add_api_route("/v1/responses", responses.responses_endpoint, methods=["POST"])
    app.add_api_route("/v1/chat/completions", chat.chat_completions_endpoint, methods=["POST"])

    # SPA static files
    mount_spa(app)
