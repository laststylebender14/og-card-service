"""Tests for the Pillow OG card renderer."""

import io

import pytest
from PIL import Image

from og_card_service.models import CardOptions, CardTheme, RepoMetadata
from og_card_service.renderer import CARD_HEIGHT, CARD_WIDTH, CardRenderer


@pytest.mark.parametrize("theme", list(CardTheme))
def test_render_produces_valid_1200x630_png(theme: CardTheme) -> None:
    renderer = CardRenderer()
    repo = RepoMetadata(
        owner="tiangolo",
        name="fastapi",
        description=(
            "FastAPI framework, high performance, easy to learn, fast to code, ready for production"
        ),
        stars=82450,
        forks=7120,
        language="Python",
        license_name="MIT",
        topics=["python", "api", "fastapi", "async"],
    )
    png_bytes = renderer.render(repo, CardOptions(theme=theme))

    img = Image.open(io.BytesIO(png_bytes))
    assert img.format == "PNG"
    assert img.size == (CARD_WIDTH, CARD_HEIGHT)


def test_render_handles_long_names_and_empty_description() -> None:
    renderer = CardRenderer()
    repo = RepoMetadata(
        owner="some-very-long-organization-name",
        name="an-extremely-long-repository-name-that-should-auto-scale-cleanly",
        description="",
        stars=42,
        forks=3,
    )
    png_bytes = renderer.render(repo, CardOptions(show_owner=True))
    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (CARD_WIDTH, CARD_HEIGHT)
