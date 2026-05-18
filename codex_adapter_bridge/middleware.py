"""中间件 —— 错误处理、请求日志、API Key 安全过滤"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .models import build_error_response

logger = logging.getLogger("codex-adapter-bridge")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """统一错误处理中间件 —— 对外隐藏内部错误细节"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.exception("未处理的异常: %s", exc)
            # Only expose the actual message for user errors, not internal details
            msg = str(exc)
            # Internal errors (import, attribute, etc.) get a generic message
            if _is_internal_error(exc):
                msg = "服务器内部错误，请查看代理日志获取详情"
            return JSONResponse(
                content=build_error_response(msg),
                status_code=500,
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件（不记录 API Key）"""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()

        if request.url.path == "/health":
            return await call_next(request)

        logger.info("→ %s %s", request.method, request.url.path)

        response = await call_next(request)

        elapsed = (time.monotonic() - start) * 1000
        logger.info(
            "← %s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response


class ApiKeyFilter(logging.Filter):
    """过滤日志中的 API Key 等敏感字段"""

    _SENSITIVE_KEYS = ("key", "token", "authorization", "secret", "password", "api_key", "credential")

    def filter(self, record: logging.LogRecord) -> bool:
        # Handle dict args (e.g., logging.info("msg", {"api_key": "sk-xxx"}))
        if record.args and isinstance(record.args, dict):
            record.args = {k: ("***" if self._is_sensitive(k) else v) for k, v in record.args.items()}
        # Handle tuple args (e.g., logging.info("key=%s", api_key))
        elif record.args and isinstance(record.args, tuple):
            record.args = tuple("***" if isinstance(a, str) and len(a) > 20 and any(s in str(a).lower() for s in ("sk-", "eyJ")) else a for a in record.args)
        return True

    @classmethod
    def _is_sensitive(cls, key: str) -> bool:
        return any(s in key.lower() for s in cls._SENSITIVE_KEYS)


_INTERNAL_ERROR_TYPES = (
    AttributeError, ImportError, NameError, SyntaxError,
    TypeError, MemoryError, SystemError, OSError,
)


def _is_internal_error(exc: Exception) -> bool:
    """用户错误（ValueError 等）应透传消息，内部错误应隐藏"""
    if isinstance(exc, ValueError):
        return False
    if isinstance(exc, _INTERNAL_ERROR_TYPES):
        return True
    return False
