"""Tests for the Pillow OG card renderer."""

import io

import pytest
from PIL import Image

from og_card_service.models import CardTheme, RepoMetadata
from og_card_service.renderer import render_card


@pytest.mark.parametrize("theme", list(CardTheme))
def test_render_produces_valid_1200x630_png(theme: CardTheme) -> None:
    repo = RepoMetadata(
        owner="tiangolo",
        name="fastapi",
        description="FastAPI framework, high performance, easy to learn, ready for production",
        stars=82450,
        forks=7120,
        language="Python",
        license_name="MIT",
        topics=["python", "api", "fastapi", "async"],
    )
    img = Image.open(io.BytesIO(render_card(repo, theme=theme)))
    assert img.format == "PNG"
    assert img.size == (1200, 630)


def test_render_handles_long_names_and_empty_description() -> None:
    repo = RepoMetadata(
        owner="some-very-long-organization-name",
        name="an-extremely-long-repository-name-that-should-auto-scale-cleanly",
        stars=42,
        forks=3,
    )
    img = Image.open(io.BytesIO(render_card(repo)))
    assert img.size == (1200, 630)
