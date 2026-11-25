"""Color palettes and GitHub language color mappings."""

from dataclasses import dataclass

from og_card_service.models import CardTheme

RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Color tokens for a card theme."""

    bg: RGB
    card_bg: RGB
    border: RGB
    accent: RGB
    accent_soft: RGB
    text_primary: RGB
    text_muted: RGB
    pill_bg: RGB


THEMES: dict[CardTheme, ThemePalette] = {
    CardTheme.DARK: ThemePalette(
        bg=(13, 17, 23),
        card_bg=(22, 27, 34),
        border=(48, 54, 61),
        accent=(88, 166, 255),
        accent_soft=(31, 45, 66),
        text_primary=(230, 237, 243),
        text_muted=(139, 148, 158),
        pill_bg=(33, 38, 45),
    ),
    CardTheme.LIGHT: ThemePalette(
        bg=(246, 248, 250),
        card_bg=(255, 255, 255),
        border=(208, 215, 222),
        accent=(9, 105, 218),
        accent_soft=(221, 244, 255),
        text_primary=(31, 35, 40),
        text_muted=(101, 109, 118),
        pill_bg=(239, 242, 245),
    ),
    CardTheme.MIDNIGHT: ThemePalette(
        bg=(10, 14, 28),
        card_bg=(17, 24, 46),
        border=(41, 56, 94),
        accent=(56, 189, 248),
        accent_soft=(23, 45, 79),
        text_primary=(241, 245, 249),
        text_muted=(148, 163, 184),
        pill_bg=(26, 36, 66),
    ),
    CardTheme.DRACULA: ThemePalette(
        bg=(25, 26, 33),
        card_bg=(40, 42, 54),
        border=(68, 71, 90),
        accent=(189, 147, 249),
        accent_soft=(68, 54, 92),
        text_primary=(248, 248, 242),
        text_muted=(154, 164, 200),
        pill_bg=(52, 55, 70),
    ),
}

LANGUAGE_COLORS: dict[str, RGB] = {
    "Python": (53, 114, 165),
    "TypeScript": (49, 120, 198),
    "JavaScript": (241, 224, 90),
    "Rust": (222, 165, 132),
    "Go": (0, 173, 216),
    "Java": (176, 114, 25),
    "C++": (243, 75, 125),
    "C": (85, 85, 85),
    "C#": (23, 134, 0),
    "Ruby": (112, 21, 22),
    "Swift": (240, 81, 56),
    "Kotlin": (169, 123, 255),
    "PHP": (79, 93, 149),
    "Shell": (137, 224, 81),
    "HTML": (227, 76, 38),
    "CSS": (86, 61, 124),
    "Dart": (0, 180, 171),
    "Elixir": (110, 74, 126),
    "Zig": (236, 145, 92),
}


def get_language_color(language: str | None, fallback: RGB) -> RGB:
    """Return the GitHub language badge color or a fallback."""
    if not language:
        return fallback
    return LANGUAGE_COLORS.get(language, fallback)
