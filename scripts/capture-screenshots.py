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
  3. pip install playwright pillow && playwright install chromium

Usage:
  python scripts/capture-screenshots.py --out assets/screenshots \
      --profile "/path/to/InvoiceGenerator/.dev-profile"

Outputs (PNG; app shots at 2× device pixels, 1440×900 CSS px):
  dashboard-dark.png, dashboard-light.png,
  dashboard-attention-dark.png, dashboard-attention-light.png (phone detail:
    the "Needs attention" panel)

The other product images have their own scripts: the hero stack (one invoice
in the four templates, plus the four PDFs) is build-hero-collage.py; the
"Making an invoice" frames and the recording are capture-process.py.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1440, "height": 900}
PERSONA = {"display_name": "Jordan Reyes", "email": "jordan@example.com"}


def patch_session(profile: pathlib.Path) -> None:
    """Rewrite the dev session so the app shows the persona, not the mock user."""
    path = profile / "session.json"
    if not path.exists():
        print("no session.json in the dev profile — sign-in did not complete?", file=sys.stderr)
        return
    data = json.loads(path.read_text())
    data.update(PERSONA)
    path.write_text(json.dumps(data))


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

        browser.close()

    for name in (
        "dashboard-dark.png",
        "dashboard-light.png",
        "dashboard-attention-dark.png",
        "dashboard-attention-light.png",
    ):
        print("wrote", out / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
