"""Production FastAPI service for GitHub Open Graph PNG cards."""

import asyncio
import hashlib
import logging
import weakref
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
import uvicorn
from cachetools import TTLCache
from fastapi import FastAPI, Header, HTTPException, Path, Query, Response

from og_card_service.models import CardTheme, RepoMetadata, Settings
from og_card_service.renderer import render_card

logger = logging.getLogger("og_card_service")
SLUG_PATTERN = r"^[A-Za-z0-9_.-]+$"
PNG_RESPONSE = {200: {"content": {"image/png": {}}, "description": "1200x630 PNG card"}}


async def _fetch_repo(app: FastAPI, owner: str, repo: str, refresh: bool) -> RepoMetadata:
    settings: Settings = app.state.settings
    cache: TTLCache[str, RepoMetadata] = app.state.meta_cache
    key = f"{owner}/{repo}".lower()
    if not refresh and key in cache:
        return cache[key]

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "og-card-service/0.1"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    try:
        resp = await app.state.http.get(
            f"https://api.github.com/repos/{owner}/{repo}", headers=headers
        )
    except httpx.HTTPError as exc:
        logger.warning("GitHub upstream error for %s/%s: %s", owner, repo, exc)
        raise HTTPException(502, "Upstream GitHub API unavailable") from exc

    if resp.status_code == 404:
        raise HTTPException(404, f"Repository '{owner}/{repo}' not found")
    if resp.status_code in (403, 429):
        logger.warning("GitHub rate limit hit (%s) for %s/%s", resp.status_code, owner, repo)
        raise HTTPException(503, "GitHub API rate limit exceeded")
    if resp.status_code >= 400:
        logger.error("GitHub API returned %s for %s/%s", resp.status_code, owner, repo)
        raise HTTPException(502, "Upstream GitHub API error")

    d = resp.json()
    lic = d.get("license") or {}
    meta = RepoMetadata(
        owner=d["owner"]["login"],
        name=d["name"],
        description=d.get("description") or "",
        stars=d.get("stargazers_count", 0),
        forks=d.get("forks_count", 0),
        language=d.get("language"),
        license_name=lic.get("spdx_id") or lic.get("name"),
        avatar_url=d["owner"].get("avatar_url"),
        topics=d.get("topics", [])[:4],
    )
    cache[key] = meta
    return meta


async def _fetch_avatar(http: httpx.AsyncClient, url: str | None) -> bytes | None:
    if not url:
        return None
    try:
        r = await http.get(url)
        return r.content if r.status_code == 200 else None
    except httpx.HTTPError:
        return None


def _png_response(data: bytes, max_age: int, if_none_match: str | None) -> Response:
    etag = f'"{hashlib.sha256(data).hexdigest()[:16]}"'
    headers = {
        "Cache-Control": f"public, max-age={max_age}, stale-while-revalidate=86400",
        "ETag": etag,
        "X-Content-Type-Options": "nosniff",
    }
    if if_none_match and etag in if_none_match:
        return Response(status_code=304, headers=headers)
    return Response(content=data, media_type="image/png", headers=headers)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
        async with httpx.AsyncClient(
            timeout=cfg.request_timeout, limits=limits, follow_redirects=True
        ) as http:
            app.state.settings = cfg
            app.state.http = http
            app.state.meta_cache = TTLCache(maxsize=cfg.max_cache_items, ttl=cfg.cache_ttl)
            app.state.img_cache = TTLCache(maxsize=cfg.max_cache_items, ttl=cfg.image_ttl)
            app.state.locks = weakref.WeakValueDictionary()
            yield

    app = FastAPI(
        title="OG Card Service",
        version="0.1.0",
        description="Production Open Graph PNG generator for GitHub repositories.",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["System"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/github/{owner}/{repo}", tags=["Cards"], responses=PNG_RESPONSE)
    async def github_card(
        owner: Annotated[str, Path(pattern=SLUG_PATTERN, max_length=64)],
        repo: Annotated[str, Path(pattern=SLUG_PATTERN, max_length=120)],
        theme: CardTheme = CardTheme.DARK,
        show_owner: Annotated[bool, Query()] = True,
        refresh: Annotated[bool, Query()] = False,
        if_none_match: Annotated[str | None, Header()] = None,
    ) -> Response:
        clean_repo = repo[:-4] if repo.lower().endswith(".png") else repo
        ckey = f"{owner}/{clean_repo}:{theme}:{show_owner}".lower()

        if not refresh and ckey in app.state.img_cache:
            return _png_response(app.state.img_cache[ckey], cfg.image_ttl, if_none_match)

        lock = app.state.locks.setdefault(ckey, asyncio.Lock())
        async with lock:
            if not refresh and ckey in app.state.img_cache:
                return _png_response(app.state.img_cache[ckey], cfg.image_ttl, if_none_match)

            meta = await _fetch_repo(app, owner, clean_repo, refresh)
            avatar = await _fetch_avatar(app.state.http, meta.avatar_url)
            png = await asyncio.to_thread(render_card, meta, theme, show_owner, avatar)
            app.state.img_cache[ckey] = png

        return _png_response(png, cfg.image_ttl, if_none_match)

    return app


app = create_app()


def main() -> None:
    cfg = Settings()
    uvicorn.run("og_card_service.app:app", host=cfg.host, port=cfg.port, log_level=cfg.log_level)
