"""Generate the OG image for the Freelance Easy landing page.

Output: assets/og-image.png at 1200×630, the standard OG/Twitter Card size.

Composition:
    Top-left:    small wordmark "FREELANCE EASY" + accent bar
    Top-left:    "Closed beta · v0.2.1" pill below the wordmark
    Center-left: Playfair Display Italic headline "Invoicing should be"
                 / "the easy part."
    Below:       Lato Regular subtitle in muted color
    Bottom-right: small accent — three-dot indicator + tiny brand mark

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

# Use the bundled fonts from the InvoiceGenerator project (canonical brand
# fonts: Montserrat, Lato, Playfair Display). They live alongside this site
# repo on disk; this script is run locally only.
IG_FONTS = Path("C:/ClaudeCodeFiles/InvoiceGenerator/static/fonts")
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


def _draw_beta_pill(draw: ImageDraw.ImageDraw) -> None:
    """Small Closed Beta v0.2.1 pill below the wordmark."""
    font = _load_font(F_LATO_BOLD, 18)
    text = "Closed beta · v0.2.1"
    x, y = 80, 150
    pad_x, pad_y = 14, 7
    bbox = draw.textbbox((x, y), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    # Pill background — semi-transparent teal
    rect = [x - pad_x, y - pad_y, x + w + pad_x, y + h + pad_y]
    # Use a slightly muted teal (rgba alpha not supported on RGB; mix with bg)
    pill_bg = (18, 50, 52)
    draw.rounded_rectangle(rect, radius=20, fill=pill_bg, outline=ACCENT, width=1)
    draw.text((x, y), text, font=font, fill=ACCENT_BRIGHT)


def _draw_headline(draw: ImageDraw.ImageDraw) -> None:
    """Two-line italic headline. Playfair Display Bold (we don't have an italic
    .ttf in the bundled set, so Bold is used for headline weight — still reads
    as editorial vs the geometric sans body)."""
    font = _load_font(F_PLAYFAIR_BOLD, 86)
    line1 = "Invoicing should be"
    line2 = "the easy part."
    # Vertically center the headline block in the middle band of the canvas
    y = 240
    draw.text((80, y), line1, font=font, fill=TEXT_PRIMARY)
    bbox = draw.textbbox((80, y), line1, font=font)
    line_h = bbox[3] - bbox[1]
    draw.text((80, y + line_h + 8), line2, font=font, fill=TEXT_PRIMARY)


def _draw_subtitle(draw: ImageDraw.ImageDraw) -> None:
    font = _load_font(F_LATO_REGULAR, 28)
    line1 = "Native desktop invoicing for freelancers."
    line2 = "Local-first. Beautiful PDFs."
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


def _draw_corner_dots(draw: ImageDraw.ImageDraw) -> None:
    """Three small dots in the top-right — subtle macOS window-traffic-light
    homage that ties to the desktop-app positioning without being too cute."""
    cx_start = W - 80 - 3 * 14 - 2 * 8
    cy = 96
    r = 7
    colors = [(220, 90, 90), (220, 175, 80), (110, 200, 110)]
    for i, c in enumerate(colors):
        cx = cx_start + i * (2 * r + 8)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    _gradient_bg(img)
    draw = ImageDraw.Draw(img)

    _draw_accent_bar(draw)
    _draw_wordmark(draw)
    _draw_beta_pill(draw)
    _draw_corner_dots(draw)
    _draw_headline(draw)
    _draw_subtitle(draw)
    _draw_bottom_brand(draw)

    ASSETS.mkdir(parents=True, exist_ok=True)
    img.save(OUT_PATH, "PNG", optimize=True)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
