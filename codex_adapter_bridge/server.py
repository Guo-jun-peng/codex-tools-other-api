"""FastAPI 服务器 —— 应用工厂 + 中间件注册"""

from __future__ import annotations

import logging
import logging.handlers
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_config
from .adapters import get_registry
from .middleware import (
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware,
    ApiKeyFilter,
)
from .admin_api import router as admin_router
from .routes import register_routes

# Fix MIME types for Windows
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")

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
    register_routes(app)

    return app
