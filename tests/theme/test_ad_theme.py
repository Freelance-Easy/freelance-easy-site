"""A7: the ad pages (/mac, /mac-audio, /audio) switch theme through FETheme (A5); the doc pages keep script.js's own
theme path until B7 (CF-11).

- test_dark_is_explicit: dark is data-theme="dark" on load and after a switch back, never a removed attribute
  (script.js's applyTheme removed it, :34 at the base).
- test_mac_light_first: /mac opens light for a first visit (the ads are light, DEC-13), a stored choice wins, and the
  visit's light look carries to /mac-audio.
- test_loads_theme_module: each ad page loads assets/shared/theme.css and theme.js (FETheme).
- test_theme_color_follows: after a switch both theme-color metas carry the shown theme's colour.
- test_demo_follows_theme: a switch still points the making-an-invoice loop at the new theme's files.
- test_doc_pages_theme_unchanged: install, privacy, terms and the dated archives behave as at the base: no FETheme,
  light is data-theme="light", dark has no data-theme.
The reveal itself (timing, mask, centre) is scripts/checks/check_theme_reveal.py's job.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

AD_PAGES = ["mac", "mac-audio", "audio"]
DOC_PAGES = ["install", "privacy", "terms", "privacy-2026-09-29", "terms-2026-09-29"]
DARK, LIGHT = "#080a0f", "#f3f3f0"   # src/partials/campaign/head.html's theme-color metas


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def open_page(browser, url, *, stored=None, reduced=True):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                              reduced_motion="reduce" if reduced else "no-preference")
    if stored:
        ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', '{stored}'); }} catch (e) {{}}")
    page = ctx.new_page()
    errors, requests = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: requests.append(r.url))
    page.goto(url, wait_until="load")
    page.wait_for_timeout(150)
    return ctx, page, errors, requests


def theme_attr(page):
    return page.evaluate("() => document.documentElement.getAttribute('data-theme')")


def press(page):
    page.click("[data-theme-toggle]")
    page.wait_for_timeout(150)   # reduced motion: the switch is instant


def metas(page):
    return page.evaluate("""() => [...document.querySelectorAll('meta[name="theme-color"]')]
        .map((m) => m.getAttribute('content'))""")


@pytest.mark.parametrize("name", AD_PAGES)
def test_dark_is_explicit(browser, site_url, name):
    ctx, page, errors, _ = open_page(browser, f"{site_url}/{name}.html", stored="dark")
    try:
        assert theme_attr(page) == "dark", "a stored dark choice must be data-theme=\"dark\" on load"
        press(page)
        assert theme_attr(page) == "light"
        press(page)
        assert theme_attr(page) == "dark", "switching back to dark must set data-theme=\"dark\", not remove it"
        assert page.evaluate("() => localStorage.getItem('fe-theme')") == "dark"
        assert not errors, errors
    finally:
        ctx.close()


def test_mac_light_first(browser, site_url):
    ctx, page, errors, _ = open_page(browser, f"{site_url}/mac.html")
    try:
        assert theme_attr(page) == "light", "/mac must open light for a first visit"
        assert page.evaluate("() => sessionStorage.getItem('fe-theme-visit')") == "light"
        assert page.evaluate("() => localStorage.getItem('fe-theme')") is None, "a first visit stores no choice"
        hero = page.evaluate("""() => [...document.querySelectorAll('link[rel=preload][as=image]')]
            .map((l) => l.getAttribute('href'))""")
        assert "/assets/screenshots/mac-hero-light.webp" in hero
        # the visit's light look carries to the audio page (same tab, nothing stored)
        page.goto(f"{site_url}/mac-audio.html", wait_until="load")
        assert theme_attr(page) == "light"
        assert not errors, errors
    finally:
        ctx.close()
    for stored in ("dark", "light"):
        ctx, page, errors, _ = open_page(browser, f"{site_url}/mac.html", stored=stored)
        try:
            assert theme_attr(page) == stored, f"a stored {stored} choice must win on /mac"
        finally:
            ctx.close()


@pytest.mark.parametrize("name", AD_PAGES)
def test_loads_theme_module(browser, site_url, name):
    ctx, page, errors, requests = open_page(browser, f"{site_url}/{name}.html")
    try:
        assert page.evaluate("() => typeof window.FETheme === 'object' && !!window.FETheme.set")
        sheets = page.evaluate("() => [...document.styleSheets].map((s) => s.href || '')")
        assert any(s.endswith("/assets/shared/theme.css") for s in sheets), sheets
        assert not errors, errors
    finally:
        ctx.close()


@pytest.mark.parametrize("name", AD_PAGES)
def test_theme_color_follows(browser, site_url, name):
    ctx, page, errors, _ = open_page(browser, f"{site_url}/{name}.html", stored="dark")
    try:
        assert metas(page) == [DARK, LIGHT], "before any switch each meta keeps its own colour"
        press(page)
        assert metas(page) == [LIGHT, LIGHT]
        press(page)
        assert metas(page) == [DARK, DARK]
        assert not errors, errors
    finally:
        ctx.close()


@pytest.mark.parametrize("name", AD_PAGES)
def test_demo_follows_theme(browser, site_url, name):
    ctx, page, errors, _ = open_page(browser, f"{site_url}/{name}.html", stored="dark")
    demo = """() => { const v = document.querySelector('video[data-demo]');
        return [v.getAttribute('poster'), ...[...v.querySelectorAll('source')].map((s) => s.getAttribute('src'))]; }"""
    try:
        assert all("-dark" in u for u in page.evaluate(demo))
        press(page)
        assert all("-light" in u for u in page.evaluate(demo)), page.evaluate(demo)
        press(page)
        assert all("-dark" in u for u in page.evaluate(demo)), page.evaluate(demo)
        assert not errors, errors
    finally:
        ctx.close()


@pytest.mark.parametrize("stored", [None, "dark", "light"])
@pytest.mark.parametrize("name", DOC_PAGES)
def test_doc_pages_theme_unchanged(browser, site_url, name, stored):
    ctx, page, errors, requests = open_page(browser, f"{site_url}/{name}.html", stored=stored)
    try:
        assert theme_attr(page) == ("light" if stored == "light" else None)
        assert page.evaluate("() => typeof window.FETheme") == "undefined"
        assert not [u for u in requests if "/assets/shared/theme." in u]
        assert not errors, errors
    finally:
        ctx.close()
