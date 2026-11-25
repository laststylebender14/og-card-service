"""HTTP routes for the OG card service."""

import asyncio
import hashlib
from typing import Annotated

from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse

from og_card_service.config import Settings
from og_card_service.github import GitHubClient, GitHubUpstreamError, RepoNotFoundError
from og_card_service.models import CardOptions, CardTheme, RepoMetadata
from og_card_service.renderer import CardRenderer

router = APIRouter()


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_github_client(request: Request) -> GitHubClient:
    return request.app.state.github


def get_renderer(request: Request) -> CardRenderer:
    return request.app.state.renderer


def get_image_cache(request: Request) -> TTLCache[str, bytes]:
    return request.app.state.image_cache


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
GitHubDep = Annotated[GitHubClient, Depends(get_github_client)]
RendererDep = Annotated[CardRenderer, Depends(get_renderer)]
ImageCacheDep = Annotated[TTLCache[str, bytes], Depends(get_image_cache)]


def _png_response(image_bytes: bytes, *, max_age: int = 3600) -> Response:
    etag = hashlib.sha256(image_bytes).hexdigest()[:16]
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": f"public, max-age={max_age}, stale-while-revalidate=86400",
            "ETag": f'"{etag}"',
        },
    )


def _strip_png_suffix(name: str) -> str:
    return name[:-4] if name.lower().endswith(".png") else name


async def _render_with_cache(
    *,
    cache_key: str,
    repo: RepoMetadata,
    options: CardOptions,
    github: GitHubClient,
    renderer: CardRenderer,
    image_cache: TTLCache[str, bytes],
) -> bytes:
    if not options.refresh and cache_key in image_cache:
        return image_cache[cache_key]

    avatar_bytes = await github.fetch_avatar_bytes(repo.avatar_url)
    png_bytes = await asyncio.to_thread(renderer.render, repo, options, avatar_bytes)
    image_cache[cache_key] = png_bytes
    return png_bytes


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness check endpoint."""
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse, tags=["playground"])
async def playground() -> str:
    """Minimal interactive playground for previewing OG cards."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OG Card Service</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; background: #0d1117; color: #e6edf3;
           max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
    p { color: #8b949e; }
    .controls { display: flex; gap: 0.75rem; flex-wrap: wrap; margin: 1.25rem 0; }
    input, select, button { padding: 0.55rem 0.85rem; border-radius: 8px; border: 1px solid #30363d;
                            background: #161b22; color: #e6edf3; font-size: 0.95rem; }
    button { background: #238636; border-color: #2ea043; cursor: pointer; font-weight: 600; }
    img { width: 100%; border-radius: 12px; border: 1px solid #30363d; margin-top: 1rem; }
    code { display: block; background: #161b22; padding: 0.75rem 1rem; border-radius: 8px;
           border: 1px solid #30363d; margin-top: 0.75rem; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>GitHub Open Graph Card Service</h1>
  <p>Generate 1200&times;630 social preview cards for any GitHub repository.</p>
  <div class="controls">
    <input id="repo" value="tiangolo/fastapi" placeholder="owner/repo or repo" />
    <select id="theme">
      <option value="dark">dark</option>
      <option value="light">light</option>
      <option value="midnight">midnight</option>
      <option value="dracula">dracula</option>
    </select>
    <button onclick="update()">Preview</button>
  </div>
  <code id="url"></code>
  <img id="preview" alt="OG Card Preview" />
  <script>
    function update() {
      const repo = document.getElementById('repo').value.trim().replace(/^\\/+/, '');
      const theme = document.getElementById('theme').value;
      const path = `/github/${repo}?theme=${encodeURIComponent(theme)}`;
      document.getElementById('url').textContent = window.location.origin + path;
      document.getElementById('preview').src = path;
    }
    update();
  </script>
</body>
</html>"""


@router.get("/v1/cards/custom", tags=["cards"])
async def custom_card(
    renderer: RendererDep,
    owner: Annotated[str, Query(min_length=1, max_length=64)] = "acme",
    repo: Annotated[str, Query(min_length=1, max_length=100)] = "awesome-project",
    description: Annotated[str, Query(max_length=400)] = "",
    stars: Annotated[int, Query(ge=0)] = 0,
    forks: Annotated[int, Query(ge=0)] = 0,
    language: Annotated[str | None, Query(max_length=40)] = None,
    theme: CardTheme = CardTheme.DARK,
    show_owner: bool = True,
) -> Response:
    """Render an OG card from explicit query parameters without calling GitHub."""
    metadata = RepoMetadata(
        owner=owner,
        name=repo,
        description=description,
        stars=stars,
        forks=forks,
        language=language,
    )
    options = CardOptions(theme=theme, show_owner=show_owner)
    png_bytes = await asyncio.to_thread(renderer.render, metadata, options, None)
    return _png_response(png_bytes, max_age=300)


@router.get("/v1/github/{owner}/{repo}", tags=["github"])
@router.get("/github/{owner}/{repo}", tags=["github"])
async def github_repo_card(
    owner: str,
    repo: str,
    github: GitHubDep,
    renderer: RendererDep,
    image_cache: ImageCacheDep,
    settings: SettingsDep,
    theme: CardTheme = CardTheme.DARK,
    show_owner: bool = True,
    refresh: bool = False,
) -> Response:
    """Generate an Open Graph PNG card for ``owner/repo``."""
    clean_repo = _strip_png_suffix(repo)
    options = CardOptions(theme=theme, show_owner=show_owner, refresh=refresh)
    cache_key = f"gh:{owner.lower()}/{clean_repo.lower()}:{theme}:{show_owner}"

    try:
        metadata = await github.get_repo(owner, clean_repo, refresh=refresh)
    except RepoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    png_bytes = await _render_with_cache(
        cache_key=cache_key,
        repo=metadata,
        options=options,
        github=github,
        renderer=renderer,
        image_cache=image_cache,
    )
    return _png_response(png_bytes, max_age=settings.image_cache_ttl_seconds)


@router.get("/v1/github/{repo}", tags=["github"])
@router.get("/github/{repo}", tags=["github"])
async def github_short_repo_card(
    repo: str,
    github: GitHubDep,
    renderer: RendererDep,
    image_cache: ImageCacheDep,
    settings: SettingsDep,
    theme: CardTheme = CardTheme.DARK,
    show_owner: bool = True,
    refresh: bool = False,
) -> Response:
    """Generate an Open Graph PNG card from a bare repository name."""
    clean_repo = _strip_png_suffix(repo)
    options = CardOptions(theme=theme, show_owner=show_owner, refresh=refresh)
    cache_key = f"gh-short:{clean_repo.lower()}:{theme}:{show_owner}"

    try:
        metadata = await github.resolve_and_get_repo(clean_repo, refresh=refresh)
    except RepoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except GitHubUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    png_bytes = await _render_with_cache(
        cache_key=cache_key,
        repo=metadata,
        options=options,
        github=github,
        renderer=renderer,
        image_cache=image_cache,
    )
    return _png_response(png_bytes, max_age=settings.image_cache_ttl_seconds)
