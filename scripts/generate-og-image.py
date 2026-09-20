"""Generate the OG image for the Freelance Easy landing page.

Output: assets/og-image.png at 1200×630, the standard OG/Twitter Card size.

Composition (v2.2 — matches the page: no pill, no serif headline):
    Top-left:    small wordmark "FREELANCE EASY" + accent bar
    Top-left:    plain kicker "A desktop invoicing app for Mac and Windows"
    Center-left: Montserrat Bold headline "Make your first invoice"
                 / "in 60 seconds"
    Below:       Lato Regular offer lines in muted color
    Top-right:   brand tile; bottom-right: freelance-easy.com

Why we don't include the dashboard chart that was in the original — it
overlapped the headline at thumbnail size. Visual quality at 200×104 (the
size most messaging apps render OG cards at) is the constraint that
matters; clean text > clever composition.

Run:
    venv/Scripts/python.exe scripts/generate-og-image.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
ASSETS = SITE_ROOT / "assets"
OUT_PATH = ASSETS / "og-image.png"
BRAND_TILE = ASSETS / "logo.png"

# Use the bundled fonts from the InvoiceGenerator project (canonical brand
# fonts: Montserrat, Lato, Playfair Display). They live alongside this site
# repo on disk; this script is run locally only.
# Resolve the sibling InvoiceGenerator checkout on either machine (Windows
# workstation or the Mac, where the workspace lives in Dropbox); override with
# FE_FONTS_DIR if the layout differs.
import os
_candidates = [
    Path(os.environ["FE_FONTS_DIR"]) if os.environ.get("FE_FONTS_DIR") else None,
    Path(__file__).resolve().parents[2] / "InvoiceGenerator" / "static" / "fonts",
    Path("C:/ClaudeCodeFiles/InvoiceGenerator/static/fonts"),
]
IG_FONTS = next((c for c in _candidates if c and c.exists()), _candidates[-1])
F_MONTSERRAT_BOLD = IG_FONTS / "Montserrat-Bold.ttf"
F_LATO_REGULAR = IG_FONTS / "Lato-Regular.ttf"
F_LATO_BOLD = IG_FONTS / "Lato-Bold.ttf"
F_PLAYFAIR_BOLD = IG_FONTS / "PlayfairDisplay-Bold.ttf"

# --------------------------------------------------------------------------
# Design tokens (match the live site)
# --------------------------------------------------------------------------

W, H = 1200, 630
BG = (13, 17, 23)              # #0d1117 — site surface color
BG_DARKER = (8, 10, 15)        # #080a0f — site bg-0
ACCENT = (44, 122, 123)        # #2c7a7b — site accent
ACCENT_BRIGHT = (66, 158, 159) # slightly brighter for highlight
TEXT_PRIMARY = (230, 232, 235) # #e6e8eb
TEXT_MUTED = (155, 160, 168)   # ~rgba(255,255,255,0.55)
TEXT_DIM = (105, 110, 118)     # bottom labels


def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _gradient_bg(img: Image.Image) -> None:
    """Subtle vertical gradient: slightly lighter at top, darker at bottom.

    Reads more like a designed surface than a flat fill at OG-card size.
    """
    pixels = img.load()
    if pixels is None:
        return
    top = (16, 21, 28)
    bot = BG_DARKER
    for y in range(H):
        t = y / (H - 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        for x in range(W):
            pixels[x, y] = (r, g, b)


def _draw_accent_bar(draw: ImageDraw.ImageDraw) -> None:
    """Short teal accent bar above the wordmark — anchors the composition."""
    x0, y0 = 80, 80
    x1, y1 = x0 + 56, y0 + 4
    draw.rectangle([x0, y0, x1, y1], fill=ACCENT_BRIGHT)


def _draw_wordmark(draw: ImageDraw.ImageDraw) -> None:
    font = _load_font(F_MONTSERRAT_BOLD, 22)
    # Use letter-spacing tracking by drawing each char with a tracked offset
    text = "FREELANCE EASY"
    x, y = 80, 100
    spacing = 4  # extra px between letters for tracked-out caps look
    for ch in text:
        draw.text((x, y), ch, font=font, fill=TEXT_PRIMARY)
        bbox = draw.textbbox((x, y), ch, font=font)
        x = bbox[2] + spacing


def _draw_kicker(draw: ImageDraw.ImageDraw) -> None:
    """Plain line below the wordmark — the same kicker the page uses."""
    font = _load_font(F_LATO_REGULAR, 22)
    draw.text((80, 150), "A desktop invoicing app for Mac and Windows", font=font, fill=TEXT_MUTED)


def _draw_headline(draw: ImageDraw.ImageDraw) -> None:
    """Two-line headline in the page's own heading face (Montserrat Bold); the
    serif italic stays in the wordmark, as on the page."""
    font = _load_font(F_MONTSERRAT_BOLD, 78)
    line1 = "Make your first invoice"
    line2 = "in 60 seconds"
    y = 236
    draw.text((80, y), line1, font=font, fill=TEXT_PRIMARY)
    bbox = draw.textbbox((80, y), line1, font=font)
    line_h = bbox[3] - bbox[1]
    draw.text((80, y + line_h + 14), line2, font=font, fill=TEXT_PRIMARY)


def _draw_subtitle(draw: ImageDraw.ImageDraw) -> None:
    font = _load_font(F_LATO_REGULAR, 28)
    line1 = "Your first invoice is free. No card, no time limit."
    line2 = "$5 a month or $50 a year when you need more."
    x, y = 80, 470
    draw.text((x, y), line1, font=font, fill=TEXT_MUTED)
    bbox = draw.textbbox((x, y), line1, font=font)
    draw.text((x, bbox[3] + 8), line2, font=font, fill=TEXT_MUTED)


def _draw_bottom_brand(draw: ImageDraw.ImageDraw) -> None:
    """Bottom-right: small 'freelance-easy.com' breadcrumb."""
    font = _load_font(F_LATO_REGULAR, 18)
    text = "freelance-easy.com"
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    x = W - 80 - w
    y = H - 80
    draw.text((x, y), text, font=font, fill=TEXT_DIM)


def _paste_brand_tile(img: Image.Image) -> None:
    """Brand FE tile in the top-right — replaces the prior traffic-light dots.

    Pulls from BRAND_TILE (the canonical 256x256 logo.png) and resizes for
    the OG card. Sized to feel like a logo lockup with the wordmark."""
    if not BRAND_TILE.exists():
        return  # silently skip if missing — keeps script resilient in CI
    tile = Image.open(BRAND_TILE).convert("RGBA")
    target = 132  # px on long edge
    tile = tile.resize((target, target), Image.LANCZOS)
    x = W - 80 - target
    y = 60
    img.paste(tile, (x, y), tile)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    _gradient_bg(img)
    draw = ImageDraw.Draw(img)

    _draw_accent_bar(draw)
    _draw_wordmark(draw)
    _draw_kicker(draw)
    _paste_brand_tile(img)
    _draw_headline(draw)
    _draw_subtitle(draw)
    _draw_bottom_brand(draw)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PATH, "PNG", optimize=True)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
