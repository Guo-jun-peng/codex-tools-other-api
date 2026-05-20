"""SPA 静态文件挂载"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

logger = logging.getLogger("codex-adapter-bridge")


def mount_spa(app: FastAPI) -> None:
    _dist = Path(__file__).resolve().parent.parent.parent / "desktop" / "dist"
    if not _dist.is_dir() or not (_dist / "index.html").exists():
        return

    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_dist / "index.html")

    logger.info("静态前端已挂载: %s", _dist)
