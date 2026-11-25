"""Tests for FastAPI routes."""

import io

from fastapi.testclient import TestClient
from PIL import Image

from og_card_service.app import create_app
from og_card_service.github import RepoNotFoundError
from og_card_service.models import RepoMetadata


class _FakeGitHubClient:
    def __init__(self) -> None:
        self.calls = 0

    async def get_repo(
        self, owner: str, repo: str, *, refresh: bool = False
    ) -> RepoMetadata:
        self.calls += 1
        if owner == "missing":
            raise RepoNotFoundError(f"Repository '{owner}/{repo}' not found")
        return RepoMetadata(
            owner=owner,
            name=repo,
            description="Test repository description",
            stars=1234,
            forks=56,
            language="Python",
            license_name="MIT",
        )

    async def resolve_and_get_repo(
        self, repo_name: str, *, refresh: bool = False
    ) -> RepoMetadata:
        return await self.get_repo("tiangolo", repo_name, refresh=refresh)

    async def fetch_avatar_bytes(self, avatar_url: str | None) -> bytes | None:
        return None


def test_health_and_playground() -> None:
    app = create_app()
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        home = client.get("/")
        assert home.status_code == 200
        assert "GitHub Open Graph Card Service" in home.text


def test_custom_card_endpoint() -> None:
    app = create_app()
    with TestClient(app) as client:
        resp = client.get(
            "/v1/cards/custom",
            params={
                "owner": "acme",
                "repo": "widget",
                "description": "A clean custom card",
                "stars": 500,
                "forks": 20,
                "language": "Rust",
                "theme": "dracula",
            },
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert "ETag" in resp.headers
        img = Image.open(io.BytesIO(resp.content))
        assert img.size == (1200, 630)


def test_github_repo_endpoints_and_caching() -> None:
    app = create_app()
    with TestClient(app) as client:
        fake = _FakeGitHubClient()
        app.state.github = fake

        r1 = client.get("/github/tiangolo/fastapi.png?theme=midnight")
        assert r1.status_code == 200
        assert r1.headers["content-type"] == "image/png"
        assert Image.open(io.BytesIO(r1.content)).size == (1200, 630)

        # Second request hits image cache without re-rendering
        r2 = client.get("/github/tiangolo/fastapi?theme=midnight")
        assert r2.status_code == 200
        assert r1.content == r2.content

        # Short repo route
        r3 = client.get("/github/fastapi")
        assert r3.status_code == 200
        assert Image.open(io.BytesIO(r3.content)).size == (1200, 630)

        # 404 on missing repo
        r4 = client.get("/github/missing/nonexistent")
        assert r4.status_code == 404
