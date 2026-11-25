"""Tests for FastAPI routes."""

import io

import httpx
from fastapi.testclient import TestClient
from PIL import Image

from og_card_service.app import create_app


def _mock_github(request: httpx.Request) -> httpx.Response:
    if "search/repositories" in str(request.url):
        return httpx.Response(
            200, json={"items": [{"owner": {"login": "tiangolo"}, "name": "fastapi"}]}
        )
    if "/repos/missing/" in str(request.url):
        return httpx.Response(404, json={"message": "Not Found"})
    return httpx.Response(
        200,
        json={
            "name": "fastapi",
            "owner": {"login": "tiangolo"},
            "description": "FastAPI framework",
            "stargazers_count": 82450,
            "forks_count": 7120,
            "language": "Python",
            "license": {"spdx_id": "MIT"},
            "topics": ["python", "api"],
        },
    )


def test_health_and_playground() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert "GitHub OG Card Service" in client.get("/").text


def test_custom_card_endpoint() -> None:
    with TestClient(create_app()) as client:
        resp = client.get(
            "/custom.png", params={"owner": "acme", "repo": "widget", "theme": "dracula"}
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert Image.open(io.BytesIO(resp.content)).size == (1200, 630)


def test_github_repo_endpoints_and_caching() -> None:
    app = create_app()
    with TestClient(app) as client:
        app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(_mock_github))

        inspect = client.get("/inspect/github/tiangolo/fastapi")
        assert inspect.status_code == 200
        assert inspect.json()["name"] == "fastapi"

        r1 = client.get("/github/tiangolo/fastapi.png?theme=midnight")
        assert r1.status_code == 200
        assert Image.open(io.BytesIO(r1.content)).size == (1200, 630)

        r2 = client.get("/github/tiangolo/fastapi?theme=midnight")
        assert r2.content == r1.content

        assert client.get("/github/fastapi").status_code == 200
        assert client.get("/github/missing/nonexistent").status_code == 404
