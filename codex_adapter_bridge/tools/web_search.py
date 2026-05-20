"""DuckDuckGo Lite 搜索实现"""

from __future__ import annotations

import re

import httpx


async def execute_web_search(query: str) -> str:
    """执行 DuckDuckGo Lite 搜索，返回格式化结果"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            resp = await client.get(
                "https://lite.duckduckgo.com/lite/",
                params={"q": query},
                headers={"User-Agent": "CodexAdapter/1.0"},
            )
            if resp.status_code != 200:
                return f"搜索失败: HTTP {resp.status_code}"

            text = resp.text
            results: list[str] = []
            links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', text)
            snippets = re.findall(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', text, re.DOTALL)

            for i, (url, title) in enumerate(links[:5]):
                if 'duckduckgo.com' in url:
                    continue
                title_clean = re.sub(r'<[^>]+>', '', title).strip()
                snippet_clean = ""
                if i < len(snippets):
                    snippet_clean = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                results.append(f"{i+1}. {title_clean}\n   URL: {url}\n   {snippet_clean}")

            if results:
                return "搜索结果:\n\n" + "\n\n".join(results)
            return "未找到相关搜索结果"
    except Exception as e:
        return f"搜索异常: {str(e)}"
