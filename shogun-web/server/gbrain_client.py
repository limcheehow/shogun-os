"""Shared HTTP client for gbrain MCP. Used by brain, docs, and dashboard endpoints."""
from __future__ import annotations

import logging
from typing import Any, List, Optional

import httpx
from config import get_config

logger = logging.getLogger(__name__)


async def gbrain_fetch_pages(
    source: str,
    *,
    limit: int = 200,
    slug_prefix: Optional[str] = None,
) -> List[dict[str, Any]]:
    """Fetch pages from gbrain for a given source, optionally filtered by slug prefix."""
    cfg = get_config()
    base = cfg.gbrain_base_url.rstrip("/")
    params = {"source_id": source, "limit": str(min(limit, 500))}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{base}/api/pages", params=params)
            if resp.status_code >= 400:
                logger.warning("gbrain /api/pages returned %s: %s", resp.status_code, resp.text[:300])
                return []
            payload = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("gbrain fetch pages error for %s: %s", source, exc)
        return []

    raw_pages: List[dict] = []
    if isinstance(payload, list):
        raw_pages = payload
    elif isinstance(payload, dict):
        raw_pages = payload.get("pages") or payload.get("data") or payload.get("results") or []

    if slug_prefix:
        raw_pages = [p for p in raw_pages if str(p.get("slug", "")).startswith(slug_prefix)]

    return raw_pages


async def gbrain_fetch_page(source: str, slug: str) -> Optional[dict[str, Any]]:
    """Fetch a single page from gbrain."""
    cfg = get_config()
    base = cfg.gbrain_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}/api/pages/{slug}", params={"source_id": source})
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            logger.warning("gbrain /api/pages/%s returned %s", slug, resp.status_code)
            return None
    except httpx.HTTPError as exc:
        logger.warning("gbrain fetch page error %s/%s: %s", source, slug, exc)
        return None


async def gbrain_search(
    source: str,
    query: str,
    limit: int = 20,
) -> List[dict[str, Any]]:
    """Search gbrain pages for a source."""
    cfg = get_config()
    base = cfg.gbrain_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base}/api/search",
                json={"query": query, "source_id": source, "limit": limit},
            )
            if resp.status_code >= 400:
                return []
            payload = resp.json()
            if isinstance(payload, list):
                return payload
            return payload.get("results") or payload.get("pages") or []
    except httpx.HTTPError as exc:
        logger.warning("gbrain search error for %s: %s", source, exc)
        return []