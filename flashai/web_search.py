"""
联网搜索：抓 DuckDuckGo HTML 搜索结果。

为什么不用 DDG 的 instant answer API：
- 那个接口对中文/小众 query 经常返回空，相关性差。
- 直接抓 html.duckduckgo.com/html 走的是无 JS 的搜索页，结构稳定。

返回结构化 list[dict]，供 agent 拼接到 prompt。
"""
from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import unquote, urlparse, parse_qs

import os
import requests

import config


_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
_ENDPOINT = "https://html.duckduckgo.com/html/"


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return html.unescape(text)


def _unwrap_ddg(href: str) -> str:
    """DDG 的外链是 //duckduckgo.com/l/?uddg=<encoded>，解开取真实 URL"""
    try:
        if "uddg=" in href:
            parsed = urlparse(href if href.startswith("http") else "https:" + href)
            qs = parse_qs(parsed.query)
            if "uddg" in qs:
                return unquote(qs["uddg"][0])
        return href
    except Exception:
        return href


def search(query: str, max_results: int | None = None) -> list[dict[str, Any]]:
    """
    返回 [{title, url, snippet}, ...]
    失败时返回空列表（不让搜索错误击穿整个 agent 调用）。
    """
    n = max_results or config.SEARCH_MAX_RESULTS
    try:
        resp = requests.post(
            _ENDPOINT,
            data={"q": query, "kl": "cn-zh"},
            headers={"User-Agent": _UA, "Referer": "https://duckduckgo.com/"},
            timeout=config.SEARCH_TIMEOUT,
            proxies=_proxies(),
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return [{"error": f"搜索失败: {e}"}]

    html_text = resp.text
    results: list[dict[str, Any]] = []

    # 抓 result__a 标题链接 + 紧跟的 result__snippet
    # 用非贪婪匹配，结果之间是独立的 <div class="result ...">
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'class="result__snippet"[^>]*>(.*?)</td>',
        re.IGNORECASE | re.DOTALL,
    )
    for href, title_html, snippet_html in pattern.findall(html_text):
        if len(results) >= n:
            break
        title = _clean(re.sub(r"<[^>]+>", "", title_html))
        snippet = _clean(re.sub(r"<[^>]+>", "", snippet_html))
        url = _unwrap_ddg(href)
        if not title:
            continue
        results.append({"title": title, "url": url, "snippet": snippet})

    return results


def format_for_prompt(query: str, results: list[dict[str, Any]]) -> str:
    """把搜索结果格式化成可塞进 system message 的文本块"""
    if not results:
        return ""
    if "error" in results[0]:
        return f"[联网搜索失败: {results[0]['error']}]"
    lines = [f"以下是关于 “{query}” 的联网搜索结果："]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   来源: {r['url']}")
    return "\n".join(lines)


def _proxies() -> dict[str, str] | None:
    p = (os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or "").strip()
    if not p:
        return None
    return {"http": p, "https": p}
