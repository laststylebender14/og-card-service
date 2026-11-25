"""FastAPI application, GitHub client, and routes."""

import asyncio
import hashlib
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
import uvicorn
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Path, Query, Response
from fastapi.responses import HTMLResponse

from og_card_service.models import CardTheme, RepoMetadata, Settings
from og_card_service.renderer import render_card

PNG_RESPONSE = {200: {"content": {"image/png": {}}, "description": "Rendered 1200x630 PNG card"}}

PLAYGROUND_HTML = """<!doctype html><html><body style="font-family:system-ui;background:#0d1117;
color:#e6edf3;max-width:900px;margin:2rem auto;padding:0 1rem">
<h2>GitHub OG Card Service</h2>
<input id=r value="tiangolo/fastapi"
 style="padding:8px;background:#161b22;color:#fff;border:1px solid #30363d;border-radius:6px">
<select id=t
 style="padding:8px;background:#161b22;color:#fff;border:1px solid #30363d;border-radius:6px">
<option>dark</option><option>light</option><option>midnight</option><option>dracula</option></select>
<button onclick="go()" style="padding:8px 14px;background:#238636;color:#fff;border:0;
border-radius:6px;cursor:pointer">Preview</button>
<img id=img style="width:100%;margin-top:1rem;border-radius:12px;border:1px solid #30363d">
<script>function go(){img.src=`/github/${r.value.trim()}.png?theme=${t.value}`}go()</script>
</body></html>"""


async def fetch_repo(app: FastAPI, owner: str | None, repo: str, refresh: bool) -> RepoMetadata:
    """Fetch GitHub repo metadata with TTL caching and optional search resolution."""
    settings: Settings = app.state.settings
    cache: TTLCache[str, RepoMetadata] = app.state.meta_cache
    http: httpx.AsyncClient = app.state.http
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "og-card-service"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    owner = owner or settings.default_github_owner
    key = f"{owner or '*'}/{repo}".lower()
    if not refresh and key in cache:
        return cache[key]

    try:
        if not owner:
            r = await http.get(
                "https://api.github.com/search/repositories",
                params={"q": f"{repo} in:name", "sort": "stars", "per_page": 1},
                headers=headers,
            )
            items = r.json().get("items") or [] if r.status_code < 400 else []
            if not items:
                raise HTTPException(404, f"Repository '{repo}' not found")
            owner, repo = items[0]["owner"]["login"], items[0]["name"]

        resp = await http.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"GitHub API error: {exc}") from exc

    if resp.status_code == 404:
        raise HTTPException(404, f"Repository '{owner}/{repo}' not found")
    if resp.status_code >= 400:
        raise HTTPException(502, f"GitHub API returned {resp.status_code}")

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


def _png(data: bytes, max_age: int) -> Response:
    etag = hashlib.sha256(data).hexdigest()[:16]
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": f"public, max-age={max_age}", "ETag": f'"{etag}"'},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as http:
            app.state.settings = cfg
            app.state.http = http
            app.state.meta_cache = TTLCache(maxsize=512, ttl=cfg.cache_ttl)
            app.state.img_cache = TTLCache(maxsize=512, ttl=cfg.image_ttl)
            yield

    app = FastAPI(
        title="OG Card Service",
        version="0.1.0",
        description="Generate 1200x630 Open Graph PNG cards for GitHub repositories.",
        lifespan=lifespan,
    )

    @app.get("/", response_class=HTMLResponse, tags=["Playground"], summary="Interactive preview")
    async def playground() -> str:
        return PLAYGROUND_HTML

    @app.get("/health", tags=["System"], summary="Health check")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/custom.png",
        tags=["Cards"],
        summary="Render a custom OG card",
        responses=PNG_RESPONSE,
    )
    async def custom_card(
        owner: Annotated[str, Query(description="Owner or org name")] = "acme",
        repo: Annotated[str, Query(description="Repository or project name")] = "awesome-project",
        description: Annotated[str, Query(description="Short project summary")] = "",
        stars: Annotated[int, Query(ge=0, description="Star count")] = 0,
        forks: Annotated[int, Query(ge=0, description="Fork count")] = 0,
        language: Annotated[str | None, Query(description="Primary language")] = None,
        theme: Annotated[CardTheme, Query(description="Visual card theme")] = CardTheme.DARK,
        show_owner: Annotated[bool, Query(description="Show owner/ prefix")] = True,
    ) -> Response:
        meta = RepoMetadata(
            owner=owner, name=repo, description=description,
            stars=stars, forks=forks, language=language,
        )
        return _png(await asyncio.to_thread(render_card, meta, theme, show_owner), 300)

    @app.get(
        "/inspect/github/{owner}/{repo}",
        response_model=RepoMetadata,
        tags=["GitHub"],
        summary="Inspect normalized GitHub metadata as JSON",
    )
    async def inspect_github(
        owner: Annotated[str, Path(description="GitHub username or organization")],
        repo: Annotated[str, Path(description="GitHub repository name")],
        refresh: Annotated[bool, Query(description="Bypass metadata cache")] = False,
    ) -> RepoMetadata:
        return await fetch_repo(app, owner, repo, refresh)

    async def _serve_github_card(
        owner: str | None, repo: str, theme: CardTheme, show_owner: bool, refresh: bool,
    ) -> Response:
        clean_repo = repo[:-4] if repo.lower().endswith(".png") else repo
        ckey = f"{owner or '*'}/{clean_repo}:{theme}:{show_owner}".lower()
        if not refresh and ckey in app.state.img_cache:
            return _png(app.state.img_cache[ckey], cfg.image_ttl)

        meta = await fetch_repo(app, owner, clean_repo, refresh)
        avatar = None
        if meta.avatar_url:
            r = await app.state.http.get(meta.avatar_url)
            avatar = r.content if r.status_code == 200 else None

        png = await asyncio.to_thread(render_card, meta, theme, show_owner, avatar)
        app.state.img_cache[ckey] = png
        return _png(png, cfg.image_ttl)

    @app.get(
        "/github/{owner}/{repo}",
        tags=["GitHub"],
        summary="Render OG card for owner/repo (.png optional)",
        responses=PNG_RESPONSE,
    )
    async def github_repo_card(
        owner: Annotated[str, Path(description="GitHub username or organization")],
        repo: Annotated[str, Path(description="Repository name (with optional .png suffix)")],
        theme: Annotated[CardTheme, Query(description="Visual card theme")] = CardTheme.DARK,
        show_owner: Annotated[bool, Query(description="Show owner/ prefix")] = True,
        refresh: Annotated[bool, Query(description="Bypass metadata and image caches")] = False,
    ) -> Response:
        return await _serve_github_card(owner, repo, theme, show_owner, refresh)

    @app.get(
        "/github/{repo}",
        tags=["GitHub"],
        summary="Render OG card by repo name (.png optional)",
        responses=PNG_RESPONSE,
    )
    async def github_short_card(
        repo: Annotated[str, Path(description="Repository name (with optional .png suffix)")],
        theme: Annotated[CardTheme, Query(description="Visual card theme")] = CardTheme.DARK,
        show_owner: Annotated[bool, Query(description="Show owner/ prefix")] = True,
        refresh: Annotated[bool, Query(description="Bypass metadata and image caches")] = False,
    ) -> Response:
        return await _serve_github_card(None, repo, theme, show_owner, refresh)

    return app


app = create_app()


def main() -> None:
    uvicorn.run("og_card_service.app:app", host="0.0.0.0", port=8000)
