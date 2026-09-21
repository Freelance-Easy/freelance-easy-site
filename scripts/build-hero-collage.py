#!/usr/bin/env python3
"""Build the hero visual: one real invoice in the app's four templates, stacked.

Two stages, because they need different interpreters:

  render   — uses the InvoiceGenerator venv (reportlab + the app's own pdf_gen)
             against the DEV profile's data. Renders the hero invoice once per
             template with a restrained accent each, to assets/samples/invoice-<style>.pdf.
               InvoiceGenerator/venv/bin/python scripts/build-hero-collage.py render \
                   --app-dir ../InvoiceGenerator --profile ../InvoiceGenerator/.dev-profile

  compose  — uses a venv with pymupdf + pillow. Rasterises the top of each PDF and
             lays the four sheets as a fanned stack on a transparent canvas:
             assets/screenshots/invoice-stack-<front>.png, one per template in
             front, all the same size (and the per-style top crops).
               python scripts/build-hero-collage.py compose

No fake documents: every sheet is the app's real output for the same fictional
invoice (INV1045, Westbrook Sound). Styles and accents are listed in SHEETS.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent
SAMPLES = SITE / "assets" / "samples"
SHOTS = SITE / "assets" / "screenshots"

HERO_INVOICE_NUMBER = "INV1045"
USER_ID = "google_oauth_sub_daniel_001"  # the mock dev user whose profile holds the fictional data

# Front to back. Accents are muted and related: the sheets should read as one
# person's taste in four templates, not a colour chart.
SHEETS = [
    ("modern", "#2c7a7b"),   # the brand teal, front sheet
    ("bold", "#2b4a6f"),     # navy
    ("classic", "#2f5d50"),  # forest
    ("minimal", "#4a4f57"),  # graphite
]


# ----------------------------------------------------------------------------- render
def render(app_dir: pathlib.Path, profile: pathlib.Path) -> int:
    os.environ["INVOICEGEN_LICENSE_DEV_MODE"] = "1"
    os.environ["FE_DEV_PROFILE"] = str(profile)
    sys.path.insert(0, str(app_dir))
    os.chdir(app_dir)  # pdf_gen resolves its bundled fonts relative to the app

    import config  # noqa: E402  (the app's config; resolves the dev profile via the env above)
    import db  # noqa: E402

    config.set_current_user_id_override(USER_ID)
    config.ensure_user_data_dirs()
    db.init_db()

    from pdf_gen import generate_invoice_pdf  # noqa: E402

    invoices = {inv["invoice_number"]: inv for inv in db.get_invoices()}
    invoice = invoices[HERO_INVOICE_NUMBER]
    line_items = db.get_line_items(invoice["id"])
    client = db.get_client(invoice["client_id"]) if invoice["client_id"] else None
    base = dict(db.get_settings())

    SAMPLES.mkdir(parents=True, exist_ok=True)
    for style, accent in SHEETS:
        settings = dict(base)
        settings["invoice_style"] = style
        settings["accent_color"] = accent
        out = SAMPLES / f"invoice-{style}.pdf"
        generate_invoice_pdf(str(out), invoice, line_items, settings, client)  # type: ignore[arg-type]
        print("wrote", out, out.stat().st_size, "bytes")
    return 0


# ----------------------------------------------------------------------------- compose
CROP_H = 1470            # px at 3× — the same crop as the previous hero (top of the page through the totals)
SHEET_W = 1120           # each sheet's width on the canvas (page 1836 → 1120, so 1470 → 897 tall)
PAD = 28                 # canvas margin; the shadows need a little room

# Each sheet behind the front one rises by the band that holds that template's
# signature, so the reveal is per template, not a uniform step:
BAND = {
    "modern": 200,   # "INVOICE", the number and title, the teal rule
    "bold": 360,     # navy "Invoice #INV1045" title (~230px down) + the navy table header (~330px)
    "classic": 176,  # forest bar + the big name are the top 176px
    "minimal": 176,  # centred grey INVOICE title + names
}
# The slot a sheet occupies (front → back) sets its x offset and tilt: dx stays
# within the page's own right margin (~100px at this scale), so the strips on
# the right are blank paper edges, not sliced numbers; small alternating tilts
# so the pile reads as paper, not a grid.
SLOTS = [dict(dx=0, tilt=0.0), dict(dx=64, tilt=1.1), dict(dx=128, tilt=-1.3), dict(dx=192, tilt=0.8)]


def compose() -> int:
    """One stack per template in front (the page lets the visitor pick), all on
    the same canvas size so swapping them doesn't move the layout."""
    import pymupdf
    from PIL import Image, ImageFilter

    SHOTS.mkdir(parents=True, exist_ok=True)
    sheets: dict[str, Image.Image] = {}
    for style, _accent in SHEETS:
        doc = pymupdf.open(SAMPLES / f"invoice-{style}.pdf")
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        im = im.crop((0, 0, im.width, CROP_H))
        im.save(SHOTS / f"invoice-{style}.png", optimize=True)  # per-style crops: the phone image and the links
        scale = SHEET_W / im.width
        sheets[style] = im.resize((SHEET_W, round(im.height * scale)), Image.LANCZOS)

    styles = [s for s, _ in SHEETS]
    sheet_h = sheets["modern"].height
    # The front sheet sits at the same y in every variant: below the tallest
    # possible pile of bands (every template but the shortest-banded one).
    tallest = sum(sorted(BAND.values(), reverse=True)[: len(styles) - 1])
    front_y = PAD + tallest
    width = SLOTS[len(styles) - 1]["dx"] + SHEET_W + 2 * PAD + 30
    height = front_y + sheet_h + PAD + 30

    for front in styles:
        order = [front] + [s for s in styles if s != front]  # front → back, the rest in canonical order
        ys, y = {}, front_y
        for style in order:
            if style != front:
                y -= BAND[style]  # this sheet rises by the band it must keep visible
            ys[style] = y
        xs = {style: PAD + SLOTS[i]["dx"] for i, style in enumerate(order)}
        tilts = {style: SLOTS[i]["tilt"] for i, style in enumerate(order)}
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        for style in reversed(order):  # back to front
            im = sheets[style]
            framed = Image.new("RGBA", (im.width + 2, im.height + 2), (214, 214, 214, 255))  # hairline edge for the light theme
            framed.paste(im, (1, 1))
            rotated = framed.rotate(tilts[style], resample=Image.BICUBIC, expand=True)
            shadow = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
            shadow.putalpha(rotated.split()[3].point(lambda a: int(a * 0.26)))
            shadow = shadow.filter(ImageFilter.GaussianBlur(16))
            x, y = xs[style], ys[style]
            canvas.alpha_composite(shadow, (x - 4, y + 12))
            canvas.alpha_composite(rotated, (x, y))
        out = SHOTS / f"invoice-stack-{front}.png"
        canvas.save(out, optimize=True)
        print("wrote", out, canvas.size, out.stat().st_size // 1024, "KB")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--app-dir", required=True)
    r.add_argument("--profile", required=True)
    sub.add_parser("compose")
    args = ap.parse_args()
    if args.cmd == "render":
        return render(pathlib.Path(args.app_dir).resolve(), pathlib.Path(args.profile).resolve())
    return compose()


if __name__ == "__main__":
    raise SystemExit(main())
