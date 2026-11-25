# OG Card Service

> Generate `1200×630` Open Graph social preview PNG cards for any GitHub repository using **FastAPI** and **Pillow**.

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-PIL-blue)

---

## Quickstart

```bash
git clone https://github.com/laststylebender14/og-card-service.git
cd og-card-service
uv sync
uv run og-card-service
```

Or with Docker:

```bash
docker build -t og-card-service .
docker run -p 8000:8000 -e OG_GITHUB_TOKEN=ghp_xxx og-card-service
```

OpenAPI docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## API

| Endpoint | Response | Description |
| --- | --- | --- |
| `GET /github/{owner}/{repo}` | `image/png` | Render `1200×630` card (`.png` suffix optional) |
| `GET /health` | `application/json` | Liveness / readiness probe |

### Query Parameters

| Parameter | Default | Options |
| --- | --- | --- |
| `theme` | `dark` | `dark`, `light`, `midnight`, `dracula` |
| `show_owner` | `true` | `true`, `false` |
| `refresh` | `false` | `true` to bypass caches |

---

## Try It with `curl`

```bash
# Default dark theme
curl -sSf "http://localhost:8000/github/tiangolo/fastapi.png" -o fastapi.png

# Light theme
curl -sSf "http://localhost:8000/github/pallets/flask.png?theme=light" -o flask.png

# Midnight / Dracula themes (.png suffix is optional)
curl -sSf "http://localhost:8000/github/astral-sh/ruff?theme=midnight" -o ruff.png
curl -sSf "http://localhost:8000/github/pydantic/pydantic.png?theme=dracula" -o pydantic.png

# Health check
curl -sSf "http://localhost:8000/health"
```

---

## Embedding

```html
<meta property="og:image" content="https://your-domain.com/github/tiangolo/fastapi.png?theme=dark" />
<meta name="twitter:card" content="summary_large_image" />
```

```markdown
![fastapi](https://your-domain.com/github/tiangolo/fastapi.png?theme=midnight)
```

---

## Configuration (`OG_` env vars)

| Variable | Default | Description |
| --- | --- | --- |
| `OG_HOST` | `0.0.0.0` | Bind host |
| `OG_PORT` | `8000` | Bind port |
| `OG_LOG_LEVEL` | `info` | Uvicorn log level |
| `OG_GITHUB_TOKEN` | `None` | GitHub PAT for higher API rate limits |
| `OG_CACHE_TTL` | `900` | GitHub metadata cache TTL (seconds) |
| `OG_IMAGE_TTL` | `3600` | Rendered PNG cache TTL (seconds) |
| `OG_MAX_CACHE_ITEMS` | `512` | Max cached entries per cache |
| `OG_REQUEST_TIMEOUT` | `5.0` | Upstream HTTP timeout (seconds) |

---

## Development

```bash
uv run pytest -v
uv run ruff check .
```
