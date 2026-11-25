"""Domain models and request options."""

from enum import StrEnum

from pydantic import BaseModel, Field


class CardTheme(StrEnum):
    """Supported visual themes for rendered OG cards."""

    DARK = "dark"
    LIGHT = "light"
    MIDNIGHT = "midnight"
    DRACULA = "dracula"


class RepoMetadata(BaseModel):
    """Normalized GitHub repository metadata used for rendering."""

    owner: str
    name: str
    description: str = ""
    stars: int = Field(default=0, ge=0)
    forks: int = Field(default=0, ge=0)
    open_issues: int = Field(default=0, ge=0)
    language: str | None = None
    license_name: str | None = None
    avatar_url: str | None = None
    topics: list[str] = Field(default_factory=list)


class CardOptions(BaseModel):
    """Per-request rendering customization options."""

    theme: CardTheme = CardTheme.DARK
    show_owner: bool = True
    refresh: bool = False
