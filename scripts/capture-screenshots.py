#!/usr/bin/env python3
"""Regenerate every product image on freelance-easy.com from the running DEV app.

Every screenshot on the site must come from the current build (the site's claims
lint), and none of them may show a real person's name or email — the demo profile
uses a fictional freelancer, and this script also rewrites the signed-in name in
the dev session so the app's sidebar shows the persona, not the mock test user.

Prerequisites (InvoiceGenerator's dev setup):
  1. The mock LicenseServer on :5001   — LicenseServer/run.py
  2. The RELEASED app in DEV mode on :50506 (a checkout at the release tag),
     with FE_DEV_PROFILE set to a throwaway profile seeded by
     scripts/seed-demo-profile.py: the fictional account the ads use (its
     docstring has the steps). Never the installed app on :50505 (real data):
     --app refuses that port.
  3. pip install playwright pillow && playwright install chromium

Usage:
  python scripts/capture-screenshots.py --out assets/screenshots \
      --profile /tmp/fe-demo-profile

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
import re
import sys

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1440, "height": 900}
PERSONA = {"display_name": "Jordan Wexcombe", "email": "jordan@example.com"}

# InvoiceGenerator serves dev/mock runs on 50506 (config.DEV_APP_PORT); 50505 is
# the installed app, with real data. --app must be a plain origin, never on 50505.
INSTALLED_APP_PORT = 50505
APP_ORIGIN = re.compile(r"https?://(?:[a-z0-9.-]+|\[[0-9a-f:.]+\])(?::(\d+))?/?", re.I)


def refuse_installed_app(ap: argparse.ArgumentParser, url: str) -> None:
    """Stop with an argparse error unless `url` is a plain http(s) origin off :50505."""
    m = APP_ORIGIN.fullmatch(url)
    if not m:
        ap.error(f"--app must be a plain origin like http://127.0.0.1:50506, got {url!r}")
    if m.group(1) and int(m.group(1)) == INSTALLED_APP_PORT:
        ap.error(
            f"refusing --app {url}: port {INSTALLED_APP_PORT} is the installed app, which holds real data. "
            "Run the dev app (InvoiceGenerator/rundev.command serves port 50506) and point --app there."
        )


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
    ap.add_argument("--app", default="http://127.0.0.1:50506")
    ap.add_argument("--out", default="assets/screenshots")
    ap.add_argument("--profile", required=True, help="the InvoiceGenerator .dev-profile directory")
    ap.add_argument("--user", default="Daniel (Google, active)", help="mock user label in the dev login dropdown")
    args = ap.parse_args()
    refuse_installed_app(ap, args.app)

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
        # The KPI figures count up from $0 on load (~1.1 s with the stagger) and
        # the bars and sparklines animate in: shoot only once each figure shows
        # its target and nothing is still moving.
        page.wait_for_function(
            """() => [...document.querySelectorAll('.kpi-value[data-target]')].every(el =>
                   el.textContent.replace(/[^0-9]/g, '') === String(Math.round(parseFloat(el.dataset.target))))
               && document.getAnimations().every(a => a.playState !== 'running'
                   || !isFinite(a.effect ? a.effect.getComputedTiming().endTime : Infinity))""",
            timeout=10000,
        )
        page.wait_for_timeout(200)
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
