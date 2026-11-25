"""Pillow-based 1200x630 Open Graph card renderer."""

import io
import math
import textwrap
from functools import lru_cache

from font_roboto import Roboto, RobotoBold
from numerize.numerize import numerize
from PIL import Image, ImageDraw, ImageFont, ImageOps

from og_card_service.models import LANG_COLORS, THEMES, CardTheme, RepoMetadata

W, H, M = 1200, 630, 40


@lru_cache(maxsize=16)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(RobotoBold if bold else Roboto, size)


def _avatar(
    raw: bytes | None, owner: str, accent: str, accent_soft: str, size: int = 88
) -> Image.Image:
    try:
        img = (
            ImageOps.fit(Image.open(io.BytesIO(raw)).convert("RGBA"), (size, size)) if raw else None
        )
    except Exception:
        img = None
    if img is None:
        img = Image.new("RGBA", (size, size), accent_soft)
        d = ImageDraw.Draw(img)
        ch, f = (owner[:1] or "?").upper(), _font(size // 2, bold=True)
        d.text(((size - f.getlength(ch)) / 2, size * 0.24), ch, fill=accent, font=f)
    mask = Image.new("L", (size * 2, size * 2), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 2 - 1, size * 2 - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask=mask.resize((size, size), Image.Resampling.LANCZOS))
    return out


def _draw_icons(draw: ImageDraw.ImageDraw, sx: float, fx: float, y: float, color: str) -> None:
    pts = [
        (
            sx + 9 + (10 if i % 2 == 0 else 4.2) * math.cos(math.radians(-90 + i * 36)),
            y + 14 + (10 if i % 2 == 0 else 4.2) * math.sin(math.radians(-90 + i * 36)),
        )
        for i in range(10)
    ]
    draw.polygon(pts, fill=color)
    lx, rx, mx, ty, my, by = fx + 5.5, fx + 16.5, fx + 11, y + 6, y + 14.4, y + 22
    draw.line([(lx, ty), (lx, my), (mx, my), (mx, by)], fill=color, width=2)
    draw.line([(rx, ty), (rx, my), (mx, my)], fill=color, width=2)
    for px, py in ((lx, ty), (rx, ty), (mx, by)):
        draw.ellipse((px - 2.6, py - 2.6, px + 2.6, py + 2.6), fill=color)


def render_card(
    repo: RepoMetadata,
    theme: CardTheme = CardTheme.DARK,
    show_owner: bool = True,
    avatar_bytes: bytes | None = None,
) -> bytes:
    """Render a 1200x630 PNG social preview card."""
    bg, card_bg, border, accent, accent_soft, text_pri, text_mut = THEMES[theme]
    canvas = Image.new("RGBA", (W, H), bg)
    draw = ImageDraw.Draw(canvas)

    for x in range(24, W, 32):
        for y in range(24, H, 32):
            draw.ellipse((x, y, x + 2, y + 2), fill=border)

    draw.rounded_rectangle([M, M, W - M, H - M], radius=24, fill=card_bg, outline=border, width=2)
    draw.rounded_rectangle([M + 28, M + 2, W - M - 28, M + 7], radius=3, fill=accent)

    px, py = 96, 98
    av = _avatar(avatar_bytes, repo.owner, accent, accent_soft)
    canvas.paste(av, (px, py), av)

    tx = px + 116
    prefix = f"{repo.owner} / " if show_owner else ""
    f_own = _font(34)
    own_w = f_own.getlength(prefix) if prefix else 0
    r_size = 46
    f_repo = _font(r_size, bold=True)
    while r_size > 26 and own_w + f_repo.getlength(repo.name) > (W - M - 56 - tx):
        r_size -= 2
        f_repo = _font(r_size, bold=True)

    if prefix:
        draw.text((tx, py + 24), prefix, fill=text_mut, font=f_own)
    draw.text((tx + own_w, py + 16 + (46 - r_size) // 2), repo.name, fill=text_pri, font=f_repo)

    desc = repo.description or "No repository description provided."
    lines = textwrap.wrap(desc, width=62, max_lines=3, placeholder="...")
    draw.multiline_text(
        (px, 228),
        "\n".join(lines),
        fill=text_pri if repo.description else text_mut,
        font=_font(29),
        spacing=12,
    )

    tx_pill, f_pill = px, _font(19)
    for topic in repo.topics[:4]:
        lbl = f"#{topic}"
        pw = f_pill.getlength(lbl) + 26
        if tx_pill + pw > W - px:
            break
        draw.rounded_rectangle([tx_pill, 398, tx_pill + pw, 432], radius=17, fill=accent_soft)
        draw.text((tx_pill + 13, 404), lbl, fill=accent, font=f_pill)
        tx_pill += pw + 12

    draw.line([(px, 472), (W - px, 472)], fill=border, width=1)
    fy, sx, f_stat = 502, float(px), _font(25)

    if repo.language:
        draw.ellipse([sx, fy + 7, sx + 15, fy + 22], fill=LANG_COLORS.get(repo.language, accent))
        sx += 25
        draw.text((sx, fy), repo.language, fill=text_pri, font=f_stat)
        sx += f_stat.getlength(repo.language) + 40

    star_txt, fork_txt = numerize(repo.stars, 1), numerize(repo.forks, 1)
    fx = sx + 26 + f_stat.getlength(star_txt) + 38
    _draw_icons(draw, sx, fx, fy, text_mut)
    draw.text((sx + 26, fy), star_txt, fill=text_mut, font=f_stat)
    draw.text((fx + 26, fy), fork_txt, fill=text_mut, font=f_stat)
    sx = fx + 26 + f_stat.getlength(fork_txt) + 40

    if repo.license_name and repo.license_name != "NOASSERTION":
        draw.text((sx, fy), repo.license_name, fill=text_mut, font=f_stat)

    f_brand = _font(22, bold=True)
    draw.text(
        (W - px - f_brand.getlength("github.com"), fy + 2),
        "github.com",
        fill=text_mut,
        font=f_brand,
    )

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
