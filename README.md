# OG Card Service

> Generate crisp `1200×630` Open Graph social preview PNG cards for any GitHub repository using **FastAPI** and **Pillow**.

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-PIL-blue)
![uv](https://img.shields.io/badge/uv-managed-DE5FE9)

---

## Quickstart

```bash
git clone <your-repo-url>
cd og-card-service
uv sync
uv run og-card-service
```

Once running on `http://localhost:8000`:
- **Interactive Playground:** [http://localhost:8000](http://localhost:8000)
- **OpenAPI / Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Try It with `curl`

### 1. GitHub Repository Card (`owner/repo`)

```bash
# Default dark theme
curl -sSf "http://localhost:8000/github/tiangolo/fastapi.png" -o fastapi.png

# Light theme
curl -sSf "http://localhost:8000/github/pallets/flask.png?theme=light" -o flask.png

# Midnight theme (without .png suffix)
curl -sSf "http://localhost:8000/github/astral-sh/ruff?theme=midnight" -o ruff.png
```

### 2. Short Repo Lookup (auto-resolves top-starred match or `OG_DEFAULT_GITHUB_OWNER`)

```bash
curl -sSf "http://localhost:8000/github/fastapi.png?theme=dracula" -o fastapi-short.png
```

### 3. Custom Card (no GitHub API call)

```bash
curl -sSfG "http://localhost:8000/custom.png" \
  --data-urlencode "owner=acme" \
  --data-urlencode "repo=og-card-service" \
  --data-urlencode "description=Dynamic Open Graph social preview cards rendered with FastAPI and Pillow" \
  --data-urlencode "stars=1420" \
  --data-urlencode "forks=185" \
  --data-urlencode "language=Python" \
  --data-urlencode "theme=dracula" \
  -o custom.png
```

### 4. Inspect Normalized GitHub Metadata (JSON)

```bash
curl -sSf "http://localhost:8000/inspect/github/tiangolo/fastapi" | python3 -m json.tool
```

### 5. Health Check

```bash
curl -sSf "http://localhost:8000/health"
# {"status":"ok"}
```

---

## API Reference

| Endpoint | Response | Description |
| --- | --- | --- |
| `GET /github/{owner}/{repo}` | `image/png` | Render card for `owner/repo` (`.png` suffix optional) |
| `GET /github/{repo}` | `image/png` | Resolve repo by name via `OG_DEFAULT_GITHUB_OWNER` or GitHub search |
| `GET /custom.png` | `image/png` | Render card from query parameters |
| `GET /inspect/github/{owner}/{repo}` | `application/json` | Return normalized repository metadata |
| `GET /` | `text/html` | Interactive browser preview playground |
| `GET /health` | `application/json` | Liveness check |

### Query Parameters

| Parameter | Default | Values / Notes |
| --- | --- | --- |
| `theme` | `dark` | `dark`, `light`, `midnight`, `dracula` |
| `show_owner` | `true` | `true` or `false` (`owner /` prefix visibility) |
| `refresh` | `false` | `true` to bypass metadata & PNG caches |

---

## Embedding in HTML & Markdown

**HTML `<meta>` tag:**

```html
<meta property="og:image" content="https://your-domain.com/github/tiangolo/fastapi.png?theme=dark" />
<meta name="twitter:card" content="summary_large_image" />
```

**Markdown:**

```markdown
![fastapi](https://your-domain.com/github/tiangolo/fastapi.png?theme=midnight)
```

---

## Configuration

Configure via environment variables or a `.env` file:

| Variable | Default | Description |
| --- | --- | --- |
| `OG_GITHUB_TOKEN` | `None` | GitHub Personal Access Token for higher API rate limits |
| `OG_DEFAULT_GITHUB_OWNER` | `None` | Default owner/org for `/github/{repo}` |
| `OG_CACHE_TTL` | `900` | GitHub metadata cache TTL in seconds |
| `OG_IMAGE_TTL` | `3600` | Rendered PNG cache TTL in seconds |

---

## Development

```bash
uv run pytest -v
uv run ruff check .
```
