"""Tests for production FastAPI routes."""

import io

import httpx
from fastapi.testclient import TestClient
from PIL import Image

from og_card_service.app import create_app


def _mock_github(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "/repos/missing/" in url:
        return httpx.Response(404, json={"message": "Not Found"})
    if "/repos/ratelimit/" in url:
        return httpx.Response(403, json={"message": "API rate limit exceeded"})
    return httpx.Response(200, json={
        "name": "fastapi",
        "owner": {"login": "tiangolo"},
        "description": "FastAPI framework",
        "stargazers_count": 82450,
        "forks_count": 7120,
        "language": "Python",
        "license": {"spdx_id": "MIT"},
        "topics": ["python", "api"],
    })


def test_health() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_github_card_caching_etag_and_errors() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(_mock_github))

        r1 = client.get("/github/tiangolo/fastapi.png?theme=midnight")
        assert r1.status_code == 200
        assert r1.headers["content-type"] == "image/png"
        assert r1.headers["x-content-type-options"] == "nosniff"
        assert Image.open(io.BytesIO(r1.content)).size == (1200, 630)

        # Cache hit & ETag 304 Not Modified
        etag = r1.headers["etag"]
        r2 = client.get("/github/tiangolo/fastapi?theme=midnight", headers={"If-None-Match": etag})
        assert r2.status_code == 304

        assert client.get("/github/missing/repo").status_code == 404
        assert client.get("/github/ratelimit/repo").status_code == 503
        assert client.get("/github/bad$owner/repo").status_code == 422
