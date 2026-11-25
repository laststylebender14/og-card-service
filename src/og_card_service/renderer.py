"""Pillow-based Open Graph card rendering engine."""

import io
import math
from functools import lru_cache

from numerize.numerize import numerize
from PIL import Image, ImageDraw, ImageFont, ImageOps

from og_card_service.models import CardOptions, RepoMetadata
from og_card_service.themes import THEMES, ThemePalette, get_language_color

CARD_WIDTH = 1200
CARD_HEIGHT = 630
CARD_MARGIN = 40


@lru_cache(maxsize=32)
def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a clean sans-serif system font with cross-platform fallbacks."""
    candidates = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _text_width(font: ImageFont.FreeTypeFont | ImageFont.ImageFont, text: str) -> int:
    bbox = font.getbbox(text)
    return int(bbox[2] - bbox[0])


def _wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    max_lines: int = 3,
) -> list[str]:
    """Wrap text by rendered pixel width and truncate with ellipsis if needed."""
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current: list[str] = []
    consumed = 0

    for word in words:
        candidate = " ".join([*current, word])
        if _text_width(font, candidate) <= max_width or not current:
            current.append(word)
            consumed += 1
        else:
            lines.append(" ".join(current))
            if len(lines) == max_lines:
                break
            current = [word]
            consumed += 1

    if len(lines) < max_lines and current:
        lines.append(" ".join(current))

    if consumed < len(words) and lines:
        last = lines[-1]
        while last and _text_width(font, f"{last}...") > max_width:
            last = last[:-1].rstrip()
        lines[-1] = f"{last}..."

    return lines


def _draw_star_icon(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    radius: float,
    fill: tuple[int, int, int, int],
) -> None:
    """Draw a crisp 5-point star icon."""
    points: list[tuple[float, float]] = []
    inner_r = radius * 0.42
    for i in range(10):
        angle = math.radians(-90 + i * 36)
        r = radius if i % 2 == 0 else inner_r
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=fill)


def _draw_fork_icon(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    size: float,
    color: tuple[int, int, int, int],
) -> None:
    """Draw a clean Git fork vector icon."""
    r = 2.6
    left_x = x + size * 0.25
    right_x = x + size * 0.75
    mid_x = x + size * 0.5
    top_y = y + 3
    mid_y = y + size * 0.52
    bot_y = y + size - 3

    draw.line(
        [(left_x, top_y), (left_x, mid_y), (mid_x, mid_y), (mid_x, bot_y)],
        fill=color,
        width=2,
    )
    draw.line([(right_x, top_y), (right_x, mid_y), (mid_x, mid_y)], fill=color, width=2)
    for px, py in ((left_x, top_y), (right_x, top_y), (mid_x, bot_y)):
        draw.ellipse((px - r, py - r, px + r, py + r), fill=color)


def _build_avatar(
    avatar_bytes: bytes | None,
    owner: str,
    palette: ThemePalette,
    size: int = 88,
) -> Image.Image:
    """Create a circular anti-aliased avatar or a monogram fallback."""
    if avatar_bytes:
        try:
            img = ImageOps.fit(
                Image.open(io.BytesIO(avatar_bytes)).convert("RGBA"),
                (size, size),
                method=Image.Resampling.LANCZOS,
            )
        except Exception:
            img = None
    else:
        img = None

    if img is None:
        img = Image.new("RGBA", (size, size), (*palette.accent_soft, 255))
        draw = ImageDraw.Draw(img)
        initial = (owner[:1] or "?").upper()
        font = _load_font(size // 2, bold=True)
        w = _text_width(font, initial)
        draw.text(
            ((size - w) // 2, size // 4),
            initial,
            fill=(*palette.accent, 255),
            font=font,
        )

    mask = Image.new("L", (size * 2, size * 2), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size * 2 - 1, size * 2 - 1), fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask=mask)
    return out


class CardRenderer:
    """Renders GitHub Open Graph social preview PNG images."""

    def render(
        self,
        repo: RepoMetadata,
        options: CardOptions,
        avatar_bytes: bytes | None = None,
    ) -> bytes:
        """Render a 1200x630 PNG card for ``repo`` and return raw PNG bytes."""
        palette = THEMES[options.theme]
        canvas = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (*palette.bg, 255))
        draw = ImageDraw.Draw(canvas)

        # Subtle background dot pattern
        dot_color = (*palette.border, 90)
        for x in range(24, CARD_WIDTH, 32):
            for y in range(24, CARD_HEIGHT, 32):
                draw.ellipse((x, y, x + 2, y + 2), fill=dot_color)

        # Main card surface
        card_box = [
            CARD_MARGIN,
            CARD_MARGIN,
            CARD_WIDTH - CARD_MARGIN,
            CARD_HEIGHT - CARD_MARGIN,
        ]
        draw.rounded_rectangle(
            card_box,
            radius=24,
            fill=(*palette.card_bg, 255),
            outline=(*palette.border, 255),
            width=2,
        )

        # Top accent strip inside card (inset to respect rounded corners)
        draw.rounded_rectangle(
            [CARD_MARGIN + 28, CARD_MARGIN + 2, CARD_WIDTH - CARD_MARGIN - 28, CARD_MARGIN + 7],
            radius=3,
            fill=(*palette.accent, 255),
        )

        # Avatar
        pad_x = 96
        top_y = 98
        avatar = _build_avatar(avatar_bytes, repo.owner, palette, size=88)
        canvas.paste(avatar, (pad_x, top_y), avatar)

        # Owner / Repo Title
        title_x = pad_x + 116
        max_title_width = CARD_WIDTH - CARD_MARGIN - 56 - title_x
        owner_prefix = f"{repo.owner} / " if options.show_owner else ""

        font_owner = _load_font(34, bold=False)
        owner_w = _text_width(font_owner, owner_prefix) if owner_prefix else 0

        repo_font_size = 46
        font_repo = _load_font(repo_font_size, bold=True)
        while repo_font_size > 26 and (
            owner_w + _text_width(font_repo, repo.name) > max_title_width
        ):
            repo_font_size -= 2
            font_repo = _load_font(repo_font_size, bold=True)

        if owner_prefix:
            draw.text(
                (title_x, top_y + 24),
                owner_prefix,
                fill=(*palette.text_muted, 255),
                font=font_owner,
            )
        draw.text(
            (title_x + owner_w, top_y + 16 + (46 - repo_font_size) // 2),
            repo.name,
            fill=(*palette.text_primary, 255),
            font=font_repo,
        )

        # Description
        desc_y = 228
        if repo.description:
            font_desc = _load_font(29, bold=False)
            lines = _wrap_text(
                repo.description,
                font_desc,
                max_width=CARD_WIDTH - (pad_x * 2),
                max_lines=3,
            )
            for line in lines:
                draw.text((pad_x, desc_y), line, fill=(*palette.text_primary, 255), font=font_desc)
                desc_y += 42
        else:
            font_desc = _load_font(26, bold=False)
            draw.text(
                (pad_x, desc_y),
                "No repository description provided.",
                fill=(*palette.text_muted, 255),
                font=font_desc,
            )

        # Topic pills
        if repo.topics:
            pill_y = 398
            pill_x = pad_x
            font_pill = _load_font(19, bold=False)
            for topic in repo.topics[:4]:
                label = f"#{topic}"
                label_w = _text_width(font_pill, label)
                pill_w = label_w + 26
                if pill_x + pill_w > CARD_WIDTH - pad_x:
                    break
                draw.rounded_rectangle(
                    [pill_x, pill_y, pill_x + pill_w, pill_y + 34],
                    radius=17,
                    fill=(*palette.accent_soft, 255),
                )
                draw.text(
                    (pill_x + 13, pill_y + 6),
                    label,
                    fill=(*palette.accent, 255),
                    font=font_pill,
                )
                pill_x += pill_w + 12

        # Divider above footer
        footer_line_y = 472
        draw.line(
            [(pad_x, footer_line_y), (CARD_WIDTH - pad_x, footer_line_y)],
            fill=(*palette.border, 255),
            width=1,
        )

        # Footer stats
        footer_y = 502
        stat_x = pad_x
        font_stat = _load_font(25, bold=False)

        if repo.language:
            lang_color = get_language_color(repo.language, palette.accent)
            draw.ellipse(
                [stat_x, footer_y + 7, stat_x + 15, footer_y + 22],
                fill=(*lang_color, 255),
            )
            stat_x += 25
            draw.text(
                (stat_x, footer_y),
                repo.language,
                fill=(*palette.text_primary, 255),
                font=font_stat,
            )
            stat_x += _text_width(font_stat, repo.language) + 40

        _draw_star_icon(
            draw,
            cx=stat_x + 9,
            cy=footer_y + 14,
            radius=10,
            fill=(*palette.text_muted, 255),
        )
        stat_x += 26
        stars_label = numerize(repo.stars, 1)
        draw.text((stat_x, footer_y), stars_label, fill=(*palette.text_muted, 255), font=font_stat)
        stat_x += _text_width(font_stat, stars_label) + 38

        _draw_fork_icon(
            draw,
            x=stat_x,
            y=footer_y + 3,
            size=22,
            color=(*palette.text_muted, 255),
        )
        stat_x += 26
        forks_label = numerize(repo.forks, 1)
        draw.text((stat_x, footer_y), forks_label, fill=(*palette.text_muted, 255), font=font_stat)
        stat_x += _text_width(font_stat, forks_label) + 40

        if repo.license_name and repo.license_name != "NOASSERTION":
            draw.text(
                (stat_x, footer_y),
                repo.license_name,
                fill=(*palette.text_muted, 255),
                font=font_stat,
            )

        # Right-aligned github.com badge
        brand_text = "github.com"
        font_brand = _load_font(22, bold=True)
        brand_w = _text_width(font_brand, brand_text)
        draw.text(
            (CARD_WIDTH - pad_x - brand_w, footer_y + 2),
            brand_text,
            fill=(*palette.text_muted, 255),
            font=font_brand,
        )

        buffer = io.BytesIO()
        canvas.convert("RGB").save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
