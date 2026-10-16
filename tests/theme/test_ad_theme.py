"""A7: the ad pages (/mac, /mac-audio, /audio) switch theme through FETheme (A5); the dated doc archives keep script.js's own
theme path; the live doc pages moved to FETheme in B7 (CF-11).

- test_dark_is_explicit: dark is data-theme="dark" on load and after a switch back, never a removed attribute
  (script.js's applyTheme removed it, :34 at the base).
- test_mac_light_first: /mac opens light for a first visit (the ads are light, DEC-13), a stored choice wins, and the
  visit's light look carries to /mac-audio.
- test_loads_theme_module: each ad page loads assets/shared/theme.css and theme.js (FETheme).
- test_theme_color_follows: after a switch both theme-color metas carry the shown theme's colour.
- test_demo_follows_theme: a switch still points the making-an-invoice loop at the new theme's files.
- test_doc_pages_theme_unchanged: install, privacy, terms and the dated archives behave as at the base: no FETheme,
  light is data-theme="light", dark has no data-theme.
- test_no_grey_dip: going to dark, the area the circle has revealed is already the final dark (no colour fade inside).
- test_early_press_instant: a press before theme.css applies switches at once (no view transition); after, the circle.
The reveal itself (timing, mask, centre) is scripts/checks/check_theme_reveal.py's job.
"""
from __future__ import annotations

import struct
import zlib

import pytest
from playwright.sync_api import sync_playwright

AD_PAGES = ["mac", "mac-audio", "audio"]
DOC_PAGES = ["privacy-2026-09-29", "terms-2026-09-29"]   # the dated archives: untouched, script.js's own path
LIVE_DOC_PAGES = ["install", "privacy", "terms"]          # B7 (CF-11): on the shared shell, FETheme, explicit theme
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


@pytest.mark.parametrize("stored", [None, "dark", "light"])
@pytest.mark.parametrize("name", LIVE_DOC_PAGES)
def test_live_doc_pages_use_fetheme(browser, site_url, name, stored):
    ctx, page, errors, requests = open_page(browser, f"{site_url}/{name}.html", stored=stored)
    try:
        assert theme_attr(page) == ("light" if stored == "light" else "dark")
        assert page.evaluate("() => typeof window.FETheme") == "object"
        assert not [u for u in requests if u.endswith("/script.js") and "/js/" not in u]
        assert not errors, errors
    finally:
        ctx.close()


def pixel(page, x, y):
    """The RGB of one viewport pixel: a 1x1 PNG clip; with one pixel every PNG filter leaves the bytes raw."""
    png = page.screenshot(clip={"x": x, "y": y, "width": 1, "height": 1}, animations="allow")
    pos, data = 8, b""
    while pos < len(png):
        n = struct.unpack(">I", png[pos:pos + 4])[0]
        kind = png[pos + 4:pos + 8]
        if kind == b"IDAT":
            data += png[pos + 8:pos + 8 + n]
        pos += 12 + n
    raw = zlib.decompress(data)
    return tuple(raw[1:4])


# a background point well inside the circle's opaque core mid-reveal, near the toggle, clear of text
DIP_POINT = {1440: (1380, 120), 390: (370, 60)}


@pytest.mark.parametrize("width", [1440, 390])
def test_no_grey_dip(browser, site_url, width):
    """Going to dark, the area the circle has revealed is the final dark background at once (styles.css's 0.3 s
    colour transitions used to run inside the new snapshot: #272b33 -> #181c24 -> #13171f)."""
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 400 else 844},
                              reduced_motion="no-preference")
    page = ctx.new_page()
    try:
        page.goto(f"{site_url}/mac.html", wait_until="load")   # first visit: light
        page.evaluate("() => document.querySelectorAll('video').forEach((v) => v.pause())")
        page.wait_for_timeout(300)
        cdp = ctx.new_cdp_session(page)
        cdp.send("Animation.enable")
        cdp.send("Animation.setPlaybackRate", {"playbackRate": 0.1})   # the 420 ms reveal (and any fade) x10
        page.click("[data-theme-toggle]")
        page.wait_for_timeout(1800)
        assert page.evaluate("() => document.documentElement.classList.contains('vt-theme')"), "no reveal running"
        mid = pixel(page, *DIP_POINT[width])
        page.wait_for_timeout(6000)
        assert theme_attr(page) == "dark"
        final = pixel(page, *DIP_POINT[width])
        assert max(abs(a - b) for a, b in zip(mid, final)) <= 2, f"mid-reveal {mid} vs final dark {final}"
    finally:
        ctx.close()


VT_COUNT_JS = """() => { const o = document.startViewTransition; window.__vt = 0;
    if (o) document.startViewTransition = function () { window.__vt++; return o.apply(this, arguments); }; }"""


def test_early_press_instant(browser, site_url):
    """A press before the body-end theme.css applies switches at once (no view transition, so no UA cross-fade);
    once it has loaded, a press runs the circle."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
    page = ctx.new_page()
    held = []
    page.route("**/assets/shared/theme.css", lambda r: held.append(r))
    try:
        page.goto(f"{site_url}/mac.html", wait_until="commit")
        # script.js has run once theme.css's <link> exists (script.js adds it; at 76aa5d5 it followed script.js)
        page.wait_for_function("() => !!window.FETheme && !!document.querySelector('link[href$=\"/assets/shared/theme.css\"]')")
        page.wait_for_timeout(200)
        page.evaluate(VT_COUNT_JS)
        before = theme_attr(page)
        page.evaluate("() => document.querySelector('[data-theme-toggle]').click()")
        page.wait_for_timeout(200)
        assert page.evaluate("() => window.__vt") == 0, "an early press must not start a view transition"
        early = theme_attr(page)
        assert early != before and early in ("dark", "light"), (before, early)
        assert held, "theme.css was not requested"
        held[0].continue_()
        page.wait_for_load_state("load")
        page.wait_for_function("() => getComputedStyle(document.documentElement).getPropertyValue('--vt-r').trim() !== ''")
        page.evaluate("() => document.querySelector('[data-theme-toggle]').click()")
        page.wait_for_timeout(800)
        assert page.evaluate("() => window.__vt") == 1, "after theme.css loads a press runs the circle"
        assert theme_attr(page) == before
    finally:
        ctx.close()
