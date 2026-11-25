# OG Card Service

Dynamic Open Graph social preview card generator (`1200×630` PNG) for GitHub repositories, built with **FastAPI**, **Pillow**, and **httpx**.

## Features

- **Clean REST API**:
  - `GET /github/{owner}/{repo}` (or `/github/{owner}/{repo}.png`, `/v1/github/{owner}/{repo}`)
  - `GET /github/{repo}` — resolves via `OG_DEFAULT_GITHUB_OWNER` or top-starred GitHub repository search
  - `GET /v1/cards/custom` — render a card directly from query parameters
  - `GET /` — interactive browser preview playground
  - `GET /health` — liveness probe
- **Themes**: `dark` (default), `light`, `midnight`, `dracula` via `?theme=...`
- **Performance**: In-memory TTL caching for GitHub metadata, avatars, and rendered PNG bytes, plus `ETag` and `Cache-Control` HTTP headers.

## Quickstart

```bash
uv sync
uv run og-card-service
```

Then open [http://localhost:8000](http://localhost:8000) or fetch a card directly:

```bash
curl -o card.png "http://localhost:8000/github/tiangolo/fastapi?theme=dark"
```

## Configuration

Environment variables (prefix `OG_`):

| Variable | Default | Description |
| --- | --- | --- |
| `OG_HOST` | `0.0.0.0` | Bind host |
| `OG_PORT` | `8000` | Bind port |
| `OG_GITHUB_TOKEN` | `None` | Optional GitHub PAT for higher API rate limits |
| `OG_DEFAULT_GITHUB_OWNER` | `None` | Optional default owner for `/github/{repo}` |
| `OG_METADATA_CACHE_TTL_SECONDS` | `900` | GitHub metadata cache TTL |
| `OG_IMAGE_CACHE_TTL_SECONDS` | `3600` | Rendered PNG cache TTL |

## Development

```bash
uv run pytest
uv run ruff check .
```
