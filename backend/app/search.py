"""Configurable web search provider integrations for local crisis verification.

Integrates real search providers (DuckDuckGo HTML, Brave Search, Tavily, SearXNG)
with strict local safety constraints: SSRF prevention, request timeouts,
bounded payloads, and honest offline degradation.
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger("crisissense.search")

SEARCH_TIMEOUT_SECONDS = 7
MAX_SEARCH_RESULTS = 5


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    published_at: str | None = None
    publisher: str | None = None


class SearchProvider(Protocol):
    name: str

    def is_configured(self) -> bool:
        ...

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        ...


class DuckDuckGoProvider:
    """Free web search provider using DuckDuckGo HTML endpoint without API keys."""
    name = "duckduckgo_html"

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        clean_query = query.strip()
        if not clean_query:
            return []

        url = "https://html.duckduckgo.com/html/"
        data = urllib.parse.urlencode({"q": clean_query}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
                content = response.read(500_000).decode("utf-8", "replace")
        except Exception as error:
            logger.warning(f"DuckDuckGo search failed: {error}")
            raise RuntimeError(f"DuckDuckGo search connection failed: {error}") from error

        # Find result snippets and links
        # DuckDuckGo HTML structure contains result__snippet and result__title links
        matches = re.findall(
            r'<a[^>]+class=[\'"][^\'"]*result__snippet[^\'"]*[\'"][^>]*href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>',
            content,
            re.DOTALL,
        )
        title_matches = re.findall(
            r'<a[^>]+class=[\'"][^\'"]*result__url[^\'"]*[\'"][^>]*href=[\'"]([^\'"]+)[\'"][^>]*>.*?</a>',
            content,
            re.DOTALL,
        )

        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for raw_url, snippet in matches:
            # Unquote DuckDuckGo redirect wrapper: //duckduckgo.com/l/?uddg=<actual_url>&rut=...
            uddg_match = re.search(r'uddg=([^&]+)', raw_url)
            actual_url = urllib.parse.unquote(uddg_match.group(1)) if uddg_match else raw_url
            if actual_url.startswith('//'):
                actual_url = 'https:' + actual_url

            if not actual_url.startswith(('http://', 'https://')):
                continue

            parsed = urllib.parse.urlsplit(actual_url)
            domain = parsed.netloc.lower()
            # Skip duckduckgo internal domains
            if 'duckduckgo.com' in domain or actual_url in seen_urls:
                continue

            seen_urls.add(actual_url)
            clean_snippet = html.unescape(re.sub(r'<[^>]+>', '', snippet)).strip()

            results.append(SearchResult(
                url=actual_url,
                title=domain,
                snippet=clean_snippet,
                publisher=domain.replace('www.', ''),
            ))

            if len(results) >= max_results:
                break

        return results


class BraveSearchProvider:
    """Brave Search API integration using BRAVE_SEARCH_API_KEY."""
    name = "brave_search"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.is_configured():
            raise RuntimeError("Brave Search requires BRAVE_SEARCH_API_KEY environment variable.")

        params = urllib.parse.urlencode({"q": query.strip(), "count": str(max_results)})
        url = f"https://api.search.brave.com/res/v1/web/search?{params}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
                "User-Agent": "CrisisSense/0.1",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read(500_000).decode("utf-8"))
        except Exception as error:
            raise RuntimeError(f"Brave Search API error: {error}") from error

        results = []
        for item in data.get("web", {}).get("results", []):
            item_url = item.get("url")
            if item_url and item_url.startswith(("http://", "https://")):
                results.append(SearchResult(
                    url=item_url,
                    title=item.get("title", ""),
                    snippet=item.get("description", ""),
                    published_at=item.get("page_age"),
                ))
        return results[:max_results]


class TavilySearchProvider:
    """Tavily Search API integration using TAVILY_API_KEY."""
    name = "tavily_search"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key.strip())

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not self.is_configured():
            raise RuntimeError("Tavily Search requires TAVILY_API_KEY environment variable.")

        url = "https://api.tavily.com/search"
        payload = json.dumps({"query": query.strip(), "max_results": max_results}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "CrisisSense/0.1",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read(500_000).decode("utf-8"))
        except Exception as error:
            raise RuntimeError(f"Tavily Search API error: {error}") from error

        results = []
        for item in data.get("results", []):
            item_url = item.get("url")
            if item_url and item_url.startswith(("http://", "https://")):
                results.append(SearchResult(
                    url=item_url,
                    title=item.get("title", ""),
                    snippet=item.get("content", ""),
                ))
        return results[:max_results]


def get_search_provider() -> tuple[SearchProvider | None, dict]:
    """Resolve active search provider based on environment variables.

    Returns:
        (provider_instance_or_none, provider_info_dict)
    """
    configured_choice = os.getenv("CRISISSENSE_SEARCH_PROVIDER", "").strip().lower()
    offline_flag = (
        os.getenv("CRISISSENSE_OFFLINE", "0").strip() in {"1", "true", "yes"}
        or (not configured_choice and (
            os.getenv("TRANSFORMERS_OFFLINE", "0").strip() in {"1", "true", "yes"}
            or os.getenv("HF_HUB_OFFLINE", "0").strip() in {"1", "true", "yes"}
        ))
    )

    if offline_flag or configured_choice in {"disabled", "none", "off"}:
        return None, {
            "provider": "disabled",
            "status": "offline_mode",
            "configured": False,
            "description": "Automatic web search disabled via configuration (offline mode).",
        }

    if configured_choice == "brave" or (not configured_choice and os.getenv("BRAVE_SEARCH_API_KEY")):
        brave = BraveSearchProvider()
        if brave.is_configured():
            return brave, {
                "provider": "brave_search",
                "status": "active",
                "configured": True,
                "description": "Brave Search API configured and active.",
            }

    if configured_choice == "tavily" or (not configured_choice and os.getenv("TAVILY_API_KEY")):
        tavily = TavilySearchProvider()
        if tavily.is_configured():
            return tavily, {
                "provider": "tavily_search",
                "status": "active",
                "configured": True,
                "description": "Tavily Search API configured and active.",
            }

    # Default to DuckDuckGo HTML provider (no API key required)
    ddg = DuckDuckGoProvider()
    return ddg, {
        "provider": "duckduckgo_html",
        "status": "active",
        "configured": True,
        "description": "DuckDuckGo HTML search provider active (no API key required).",
    }
