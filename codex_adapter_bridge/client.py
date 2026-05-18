"""HTTP 客户端 —— 异步转发请求到国产模型 API"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import AsyncIterator

import httpx

from .adapters.base import BaseAdapter

logger = logging.getLogger("codex-adapter-bridge")

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
BACKOFF_BASE = 1.0
BACKOFF_MAX = 10.0


class UpstreamClient:
    """上游模型 API 异步客户端"""

    def __init__(self, adapter: BaseAdapter, api_key: str, timeout: float = 120.0, stream_timeout: float = 600.0):
        self.adapter = adapter
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None
        self._stream_client: httpx.AsyncClient | None = None
        self._timeout = timeout
        self._stream_timeout = stream_timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
        return self._client

    async def _get_stream_client(self) -> httpx.AsyncClient:
        if self._stream_client is None:
            self._stream_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=self._stream_timeout, write=30.0, pool=30.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
        return self._stream_client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._stream_client:
            await self._stream_client.aclose()
            self._stream_client = None

    async def chat_completion(self, chat_req: dict) -> dict:
        return await _with_retry(self._do_chat_completion, chat_req)

    async def _do_chat_completion(self, chat_req: dict) -> dict:
        client = await self._get_client()
        url = self.adapter.build_chat_url()
        headers = self.adapter.get_headers(self.api_key)

        response = await client.post(url, json=chat_req, headers=headers)
        if response.status_code >= 400:
            body = await response.aread()
            raise httpx.HTTPStatusError(
                f"Upstream {response.status_code}: {body.decode()[:500]}",
                request=response.request,
                response=response,
            )
        return response.json()

    async def chat_completion_stream(self, chat_req: dict) -> AsyncIterator[dict]:
        client = await self._get_stream_client()
        url = self.adapter.build_chat_url()
        headers = self.adapter.get_headers(self.api_key)
        chat_req["stream"] = True

        response = await _with_retry_for_stream(client, url, chat_req, headers)

        async with response:
            if response.status_code >= 400:
                body = await response.aread()
                raise httpx.HTTPStatusError(
                    f"Upstream {response.status_code}: {body.decode()[:500]}",
                    request=response.request,
                    response=response,
                )
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        yield chunk
                    except json.JSONDecodeError:
                        continue


async def _with_retry(fn, *args, **kwargs):
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await fn(*args, **kwargs)
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code not in RETRYABLE_STATUSES:
                raise
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
            last_exc = exc
        except Exception:
            raise

        if attempt < MAX_RETRIES:
            delay = min(BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 0.5), BACKOFF_MAX)
            logger.warning("Retry %d/%d after %.1fs: %s", attempt + 1, MAX_RETRIES, delay, last_exc)
            await asyncio.sleep(delay)
    raise last_exc


async def _with_retry_for_stream(client, url, chat_req, headers):
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await client.send(
                client.build_request("POST", url, json=chat_req, headers=headers),
                stream=True,
            )
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
            last_exc = exc
        except Exception:
            raise

        if attempt < MAX_RETRIES:
            delay = min(BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 0.5), BACKOFF_MAX)
            logger.warning("Stream retry %d/%d after %.1fs: %s", attempt + 1, MAX_RETRIES, delay, last_exc)
            await asyncio.sleep(delay)
    raise last_exc
