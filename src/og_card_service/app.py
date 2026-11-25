"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from cachetools import TTLCache
from fastapi import FastAPI

from og_card_service.config import Settings, get_settings
from og_card_service.github import GitHubClient
from og_card_service.renderer import CardRenderer
from og_card_service.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage shared HTTP client, caches, and renderer lifecycle."""
    settings: Settings = app.state.settings
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http_client:
        app.state.github = GitHubClient(http=http_client, settings=settings)
        app.state.renderer = CardRenderer()
        app.state.image_cache = TTLCache(
            maxsize=settings.max_cache_items,
            ttl=settings.image_cache_ttl_seconds,
        )
        yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        description="Dynamic Open Graph social preview card generator for GitHub repositories.",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.include_router(router)
    return app


app = create_app()
