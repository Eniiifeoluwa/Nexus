"""
Web Search Tool
───────────────
Wraps DuckDuckGo search (no API key required) with result normalisation,
retry logic, and a fallback stub for offline/test environments.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class WebSearchTool:
    """
    Search the web using DuckDuckGo.

    Returns a list of dicts:
        [{"title": str, "snippet": str, "url": str}, ...]
    """

    def __init__(self, max_results: int = 5, timeout: int = 10) -> None:
        self.max_results = max_results
        self.timeout = timeout

    def search(self, query: str, max_results: int | None = None) -> list[dict[str, str]]:
        n = max_results or self.max_results
        logger.debug("Web search: %r (n=%d)", query, n)
        try:
            return self._ddg_search(query, n)
        except Exception as exc:
            logger.warning("Web search failed: %s — returning empty results", exc)
            return []

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(2), reraise=False)
    def _ddg_search(self, query: str, n: int) -> list[dict[str, str]]:
        from duckduckgo_search import DDGS  # type: ignore

        results: list[dict[str, str]] = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=n):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                    }
                )
        return results
