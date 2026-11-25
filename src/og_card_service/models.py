"""Configuration, themes, and domain models."""

from enum import StrEnum

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class CardTheme(StrEnum):
    DARK = "dark"
    LIGHT = "light"
    MIDNIGHT = "midnight"
    DRACULA = "dracula"


# (bg, card_bg, border, accent, accent_soft, text_primary, text_muted)
THEMES: dict[CardTheme, tuple[str, str, str, str, str, str, str]] = {
    CardTheme.DARK: ("#0d1117", "#161b22", "#30363d", "#58a6ff", "#1f2d42", "#e6edf3", "#8b949e"),
    CardTheme.LIGHT: ("#f6f8fa", "#ffffff", "#d0d7de", "#0969da", "#ddf4ff", "#1f2328", "#656d76"),
    CardTheme.MIDNIGHT: (
        "#0a0e1c",
        "#11182e",
        "#29385e",
        "#38bdf8",
        "#172d4f",
        "#f1f5f9",
        "#94a3b8",
    ),
    CardTheme.DRACULA: (
        "#191a21",
        "#282a36",
        "#44475a",
        "#bd93f9",
        "#44365c",
        "#f8f8f2",
        "#9aa4c8",
    ),
}

LANG_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Rust": "#dea584",
    "Go": "#00ADD8",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "Ruby": "#701516",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OG_", env_file=".env", extra="ignore")
    github_token: str | None = None
    default_github_owner: str | None = None
    cache_ttl: int = 900
    image_ttl: int = 3600


class RepoMetadata(BaseModel):
    owner: str
    name: str
    description: str = ""
    stars: int = 0
    forks: int = 0
    language: str | None = None
    license_name: str | None = None
    avatar_url: str | None = None
    topics: list[str] = []
