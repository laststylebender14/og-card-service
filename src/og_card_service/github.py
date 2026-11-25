"""Async GitHub API client with TTL caching."""

import httpx
from cachetools import TTLCache

from og_card_service.config import Settings
from og_card_service.models import RepoMetadata


class RepoNotFoundError(Exception):
    """Raised when a requested GitHub repository cannot be found."""


class GitHubUpstreamError(Exception):
    """Raised when GitHub API returns an unexpected error or rate limit."""


class GitHubClient:
    """Async client for fetching repository metadata and owner avatars."""

    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http
        self._settings = settings
        self._meta_cache: TTLCache[str, RepoMetadata] = TTLCache(
            maxsize=settings.max_cache_items,
            ttl=settings.metadata_cache_ttl_seconds,
        )
        self._resolve_cache: TTLCache[str, tuple[str, str]] = TTLCache(
            maxsize=settings.max_cache_items,
            ttl=settings.metadata_cache_ttl_seconds,
        )
        self._avatar_cache: TTLCache[str, bytes] = TTLCache(
            maxsize=settings.max_cache_items,
            ttl=settings.metadata_cache_ttl_seconds,
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "og-card-service/0.1.0",
        }
        if self._settings.github_token:
            headers["Authorization"] = f"Bearer {self._settings.github_token}"
        return headers

    async def get_repo(
        self, owner: str, repo: str, *, refresh: bool = False
    ) -> RepoMetadata:
        """Fetch repository metadata for ``owner/repo``."""
        cache_key = f"{owner.lower()}/{repo.lower()}"
        if not refresh and cache_key in self._meta_cache:
            return self._meta_cache[cache_key]

        url = f"{self._settings.github_api_base}/repos/{owner}/{repo}"
        try:
            resp = await self._http.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise GitHubUpstreamError(f"Failed to reach GitHub API: {exc}") from exc

        if resp.status_code == 404:
            raise RepoNotFoundError(f"Repository '{owner}/{repo}' not found")
        if resp.status_code >= 400:
            raise GitHubUpstreamError(
                f"GitHub API returned {resp.status_code} for '{owner}/{repo}'"
            )

        data = resp.json()
        license_info = data.get("license") or {}
        owner_info = data.get("owner") or {}

        metadata = RepoMetadata(
            owner=owner_info.get("login", owner),
            name=data.get("name", repo),
            description=data.get("description") or "",
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            open_issues=data.get("open_issues_count", 0),
            language=data.get("language"),
            license_name=license_info.get("spdx_id") or license_info.get("name"),
            avatar_url=owner_info.get("avatar_url"),
            topics=data.get("topics", [])[:4],
        )
        self._meta_cache[cache_key] = metadata
        return metadata

    async def resolve_and_get_repo(
        self, repo_name: str, *, refresh: bool = False
    ) -> RepoMetadata:
        """Resolve a bare ``repo_name`` via default owner or GitHub search."""
        if self._settings.default_github_owner:
            return await self.get_repo(
                self._settings.default_github_owner, repo_name, refresh=refresh
            )

        key = repo_name.lower()
        if not refresh and key in self._resolve_cache:
            owner, resolved_repo = self._resolve_cache[key]
            return await self.get_repo(owner, resolved_repo, refresh=refresh)

        url = f"{self._settings.github_api_base}/search/repositories"
        params = {"q": f"{repo_name} in:name", "sort": "stars", "per_page": 1}
        try:
            resp = await self._http.get(url, params=params, headers=self._headers())
        except httpx.HTTPError as exc:
            raise GitHubUpstreamError(f"Failed to search GitHub API: {exc}") from exc

        if resp.status_code >= 400:
            raise GitHubUpstreamError(
                f"GitHub search API returned {resp.status_code}"
            )

        items = resp.json().get("items") or []
        if not items:
            raise RepoNotFoundError(f"No repository found matching '{repo_name}'")

        top = items[0]
        owner = top["owner"]["login"]
        resolved_repo = top["name"]
        self._resolve_cache[key] = (owner, resolved_repo)
        return await self.get_repo(owner, resolved_repo, refresh=refresh)

    async def fetch_avatar_bytes(self, avatar_url: str | None) -> bytes | None:
        """Download and cache avatar image bytes, returning None on failure."""
        if not avatar_url:
            return None
        if avatar_url in self._avatar_cache:
            return self._avatar_cache[avatar_url]

        try:
            resp = await self._http.get(avatar_url)
            if resp.status_code == 200:
                self._avatar_cache[avatar_url] = resp.content
                return resp.content
        except httpx.HTTPError:
            return None
        return None
