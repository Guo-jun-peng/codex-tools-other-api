"""服务端工具子包 —— 工具注册表 + 执行逻辑 + 代理循环"""

from __future__ import annotations

from .web_search import execute_web_search

TOOL_EXECUTORS = {
    "web_search": execute_web_search,
}
