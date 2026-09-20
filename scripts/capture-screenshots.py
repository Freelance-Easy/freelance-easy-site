#!/usr/bin/env python3
"""Capture the landing-page screenshots from a running Freelance Easy DEV app.

Every screenshot on freelance-easy.com must come from the current build (the
site's claims lint), so this script regenerates them from the app itself —
run it after each release that changes the UI.

Prerequisites (the InvoiceGenerator repo's dev setup):
  1. The mock LicenseServer on :5001   — LicenseServer/run.py
  2. The app in DEV mode on :50505     — InvoiceGenerator/rundev.command
     with the isolated .dev-profile seeded with demo data (fictional clients;
     never real customer data).
  3. pip install playwright && playwright install chromium

Usage:
  python scripts/capture-screenshots.py --out assets/screenshots
Options:
  --app  http://127.0.0.1:50505   (default)
  --user "Daniel (Google, active)" (mock user label in the dev login dropdown)

Outputs (PNG, 2× device pixels, 1440×900 CSS px viewport):
  dashboard-dark.png, dashboard-light.png
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1440, "height": 900}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default="http://127.0.0.1:50505")
    ap.add_argument("--out", default="assets/screenshots")
    ap.add_argument("--user", default="Daniel (Google, active)")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2, color_scheme="dark")
        page = ctx.new_page()

        # --- mock sign-in (DEV mode only; the dropdown does not exist in prod) ---
        page.goto(f"{args.app}/login", wait_until="networkidle")
        sel = page.locator("#test-user-select")
        if sel.count() == 0:
            print("no dev login dropdown — is the app running in DEV mode?", file=sys.stderr)
            return 2
        sel.select_option(label=args.user)
        page.get_by_role("button", name="Sign in with Google").click()
        # The dashboard polls /notifications every 30 s, so "networkidle" never
        # arrives there — wait for the page content instead.
        page.wait_for_url(lambda u: not u.rstrip("/").endswith("/login"), wait_until="commit")
        page.goto(f"{args.app}/", wait_until="domcontentloaded")
        page.get_by_text("Recent invoices").wait_for(timeout=15000)
        page.wait_for_timeout(800)  # let the chart animate in

        def shot(name: str) -> None:
            target = out / name
            page.screenshot(path=str(target), full_page=False, type="png")
            print("wrote", target)

        # Dark is the app default.
        if page.locator("html[data-theme='light']").count():
            page.get_by_role("button", name="Toggle theme").click()
            page.wait_for_timeout(400)
        shot("dashboard-dark.png")

        page.get_by_role("button", name="Toggle theme").click()
        page.wait_for_timeout(500)
        shot("dashboard-light.png")

        # Leave the app in dark mode for the next run.
        page.get_by_role("button", name="Toggle theme").click()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
