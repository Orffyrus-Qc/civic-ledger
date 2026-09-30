from __future__ import annotations

import logging
from typing import Any

import httpx

from . import config
from .privacy import redact_text
from .sources import is_allowed, source_kind

log = logging.getLogger("cpl.search")


async def searx_search(
    query: str,
    pages: int = 1,
    language: str = "en-CA",
    country: str | None = None,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    async with httpx.AsyncClient(
        timeout=config.HTTP_TIMEOUT,
        headers={"User-Agent": config.USER_AGENT},
        follow_redirects=True,
    ) as client:
        for page in range(1, pages + 1):
            try:
                resp = await client.get(
                    f"{config.SEARXNG_URL}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": language,
                        "pageno": page,
                        "safesearch": 1,
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
            except Exception as exc:
                log.warning("searx query failed %r: %s", query, exc)
                break
            for row in payload.get("results") or []:
                url = (row.get("url") or "").strip()
                if not url or not is_allowed(url, country):
                    continue
                hits.append(
                    {
                        "title": redact_text(row.get("title") or "")[:300],
                        "url": url,
                        "snippet": redact_text(row.get("content") or "")[:800],
                        "engine": ",".join(row.get("engines") or [])
                        or (row.get("engine") or "searxng"),
                        "kind": source_kind(url, country),
                        "query": query,
                        "country": country or "CA",
                    }
                )
    # de-dupe by url
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for hit in hits:
        if hit["url"] in seen:
            continue
        seen.add(hit["url"])
        unique.append(hit)
    return unique


async def fetch_text(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=config.HTTP_TIMEOUT,
        headers={"User-Agent": config.USER_AGENT},
        follow_redirects=True,
    ) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception as exc:
            log.info("fetch skipped %s: %s", url, exc)
            return ""
    ctype = resp.headers.get("content-type", "")
    if "html" not in ctype and "json" not in ctype and "text" not in ctype:
        return ""
    text = resp.text
    if "json" in ctype:
        return redact_text(text)[: config.FETCH_MAX_CHARS]
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "noscript"]):
            tag.decompose()
        body = " ".join(soup.get_text(" ", strip=True).split())
        return redact_text(body)[: config.FETCH_MAX_CHARS]
    except Exception:
        return redact_text(text)[: config.FETCH_MAX_CHARS]
