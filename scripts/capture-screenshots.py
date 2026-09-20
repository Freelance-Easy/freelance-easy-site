#!/usr/bin/env python3
"""Regenerate every product image on freelance-easy.com from the running DEV app.

Every screenshot on the site must come from the current build (the site's claims
lint), and none of them may show a real person's name or email — the demo profile
uses a fictional freelancer, and this script also rewrites the signed-in name in
the dev session so the app's sidebar shows the persona, not the mock test user.

Prerequisites (InvoiceGenerator's dev setup):
  1. The mock LicenseServer on :5001   — LicenseServer/run.py
  2. The app in DEV mode on :50505     — InvoiceGenerator/rundev.command
     with the isolated .dev-profile seeded with FICTIONAL demo data
     (clients, invoices, business name/email of the persona below).
  3. pip install playwright pymupdf && playwright install chromium

Usage:
  python scripts/capture-screenshots.py --out assets/screenshots \
      --profile "/path/to/InvoiceGenerator/.dev-profile"

Outputs (PNG; app shots at 2× device pixels, 1440×900 CSS px):
  dashboard-dark.png, dashboard-light.png,
  dashboard-attention-dark.png, dashboard-attention-light.png (phone detail:
    the "Needs attention" panel),
  invoice-day-rate.png (the hero: top of the hero invoice's rendered PDF),
  ../sample-invoice.pdf (the full PDF of the hero invoice, linked from its caption)

The "Making an invoice" frames and the recording come from capture-process.py,
which makes (and then deletes) a real invoice through the UI.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import pymupdf
from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1440, "height": 900}
PERSONA = {"display_name": "Jordan Reyes", "email": "jordan@example.com"}
HERO_INVOICE_NUMBER = "INV1045"   # "Kit fee + day rate — string session", balance due $750
SAMPLE_PDF_INVOICE_NUMBER = HERO_INVOICE_NUMBER  # the caption says "this invoice"; keep it true
HERO_CROP_HEIGHT = 1470  # px at 3× — keep in sync with the <img height> in the HTML


def patch_session(profile: pathlib.Path) -> None:
    """Rewrite the dev session so the app shows the persona, not the mock user."""
    path = profile / "session.json"
    if not path.exists():
        print("no session.json in the dev profile — sign-in did not complete?", file=sys.stderr)
        return
    data = json.loads(path.read_text())
    data.update(PERSONA)
    path.write_text(json.dumps(data))


def invoice_ids(page, app: str) -> dict[str, int]:
    page.goto(f"{app}/invoices", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    html = page.content()
    return {m.group(2): int(m.group(1)) for m in re.finditer(r'href="/invoices/(\d+)[^"]*"[^>]*>\s*(INV\d{4})', html)}


def viewport_box(locator) -> tuple[float, float, float, float]:
    b = locator.bounding_box()
    if b is None:
        raise RuntimeError("element has no box — is it rendered?")
    return b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"]


def crop_png(src: pathlib.Path, box_css: tuple[float, float, float, float], dst: pathlib.Path, pad: int = 12) -> None:
    """Crop a 2× screenshot to a CSS-pixel box (viewport coordinates) plus padding."""
    from PIL import Image

    im = Image.open(src)
    w, h = im.size
    x0, y0, x1, y1 = box_css
    region = (
        max(0, int((x0 - pad) * 2)),
        max(0, int((y0 - pad) * 2)),
        min(w, int((x1 + pad) * 2)),
        min(h, int((y1 + pad) * 2)),
    )
    im.crop(region).save(dst, optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default="http://127.0.0.1:50505")
    ap.add_argument("--out", default="assets/screenshots")
    ap.add_argument("--profile", required=True, help="the InvoiceGenerator .dev-profile directory")
    ap.add_argument("--user", default="Daniel (Google, active)", help="mock user label in the dev login dropdown")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    profile = pathlib.Path(args.profile)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2, color_scheme="dark")
        page = ctx.new_page()

        # --- mock sign-in (DEV mode only) ---
        page.goto(f"{args.app}/login", wait_until="networkidle")
        sel = page.locator("#test-user-select")
        if sel.count() == 0:
            print("no dev login dropdown — is the app running in DEV mode?", file=sys.stderr)
            return 2
        sel.select_option(label=args.user)
        page.get_by_role("button", name="Sign in with Google").click()
        page.wait_for_url(lambda u: not u.rstrip("/").endswith("/login"), wait_until="commit")
        patch_session(profile)

        def toggle_theme() -> None:
            page.get_by_role("button", name="Toggle theme").click()
            page.wait_for_timeout(400)

        def ensure_dark() -> None:
            if page.locator("html[data-theme='light']").count():
                toggle_theme()

        # --- dashboard, both themes, plus the phone detail (the attention panel) ---
        page.goto(f"{args.app}/", wait_until="domcontentloaded")
        page.get_by_text("Recent invoices").wait_for(timeout=15000)
        page.wait_for_timeout(800)
        ensure_dark()
        assert PERSONA["display_name"] in page.content(), "persona not shown — session patch failed"
        attention = viewport_box(page.locator("#attention-card"))
        page.screenshot(path=str(out / "dashboard-dark.png"), type="png")
        crop_png(out / "dashboard-dark.png", attention, out / "dashboard-attention-dark.png", pad=0)
        toggle_theme()
        page.screenshot(path=str(out / "dashboard-light.png"), type="png")
        crop_png(out / "dashboard-light.png", attention, out / "dashboard-attention-light.png", pad=0)
        toggle_theme()

        ids = invoice_ids(page, args.app)

        # --- the PDFs: hero crop + full sample ---
        hero_pdf = ctx.request.get(f"{args.app}/invoices/{ids[HERO_INVOICE_NUMBER]}/pdf").body()
        doc = pymupdf.open(stream=hero_pdf, filetype="pdf")
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=False)
        full = out / "_hero-full.png"
        pix.save(str(full))
        from PIL import Image  # Pillow comes with pymupdf's optional deps; pip install pillow if missing

        im = Image.open(full)
        w, _h = im.size
        # Top of the page through the totals box and the notes line (1836×1470 at 3×).
        im.crop((0, 0, w, HERO_CROP_HEIGHT)).save(out / "invoice-day-rate.png", optimize=True)
        full.unlink()

        sample_pdf = ctx.request.get(f"{args.app}/invoices/{ids[SAMPLE_PDF_INVOICE_NUMBER]}/pdf").body()
        (out.parent / "sample-invoice.pdf").write_bytes(sample_pdf)

        browser.close()

    for name in (
        "dashboard-dark.png",
        "dashboard-light.png",
        "dashboard-attention-dark.png",
        "dashboard-attention-light.png",
        "invoice-day-rate.png",
    ):
        print("wrote", out / name)
    print("wrote", out.parent / "sample-invoice.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
