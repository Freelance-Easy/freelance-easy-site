#!/usr/bin/env python3
"""Build the hero visual: one real invoice in the app's four templates, stacked.

Two stages, because they need different interpreters:

  render   — uses the InvoiceGenerator venv (reportlab + the app's own pdf_gen)
             against the DEV profile's data. Renders the hero invoice once per
             template with a restrained accent each, to assets/samples/invoice-<style>.pdf.
               InvoiceGenerator/venv/bin/python scripts/build-hero-collage.py render \
                   --app-dir ../InvoiceGenerator --profile ../InvoiceGenerator/.dev-profile

  sheets   — uses a venv with pymupdf + pillow. Rasterises the top of each PDF to
             assets/screenshots/sheet-<style>.webp (1120 px wide, no edge or
             shadow: the page draws those). The page lays the four sheets as a
             deck with CSS transforms and animates the pull when the visitor
             brings one to the front; the deck's geometry lives in the HTML
             (the sheets' inline --x/--y/--s/--z), styles.css and script.js.
               python scripts/build-hero-collage.py sheets

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


# ----------------------------------------------------------------------------- sheets
CROP_H = 1470            # px at 3× — the top of the page through the totals
SHEET_W = 1120           # each sheet's width (page 1836 → 1120, so 1470 → 897 tall); 2× its size on the page

# This stage emits the four honest PDF rasters only. The deck's geometry
# (four fixed slots: x 0 / 4.878 / 9.756 / 14.634 % of the deck's width,
# y 36 / 24 / 12 / 0 %, scale 1 / .985 / .97 / .955, a 12 % band per sheet
# behind) lives in index.html / mac-audio.html (the sheets' inline custom
# properties), styles.css (.stack / .sheet) and script.js (DECK).


def sheets() -> int:
    """Raster the top of each template's PDF to a WebP sheet."""
    import pymupdf
    from PIL import Image

    SHOTS.mkdir(parents=True, exist_ok=True)
    for style, _accent in SHEETS:
        doc = pymupdf.open(SAMPLES / f"invoice-{style}.pdf")
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        im = im.crop((0, 0, im.width, CROP_H))
        scale = SHEET_W / im.width
        im = im.resize((SHEET_W, round(im.height * scale)), Image.LANCZOS)
        out = SHOTS / f"sheet-{style}.webp"
        im.save(out, "WEBP", quality=90, method=6)
        print("wrote", out, im.size, out.stat().st_size // 1024, "KB")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--app-dir", required=True)
    r.add_argument("--profile", required=True)
    sub.add_parser("sheets")
    args = ap.parse_args()
    if args.cmd == "render":
        return render(pathlib.Path(args.app_dir).resolve(), pathlib.Path(args.profile).resolve())
    return sheets()


if __name__ == "__main__":
    raise SystemExit(main())
