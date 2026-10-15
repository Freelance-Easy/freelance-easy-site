"""A8: the homepage adopts the shared theme module (FETheme, hashPolicy "home").

The toggle never writes a hash; #dark / #light is still read on load and on hashchange; the story scenes rebuild with
the new palette on every switch, with and without View Transitions.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

TOGGLE = "[data-theme-toggle]"
NO_VT = "Object.defineProperty(document, 'startViewTransition', {value: undefined, configurable: true});"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def open_home(browser, url, *, init_script=None, width=1440):
    ctx = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="no-preference")
    if init_script:
        ctx.add_init_script(init_script)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_function("() => window.__site && window.__site.TL", timeout=8000)
    page.wait_for_timeout(300)
    return ctx, page, errors


def theme(page):
    return page.evaluate("() => document.documentElement.getAttribute('data-theme')")


def press(page):
    page.locator(TOGGLE).first.click()
    page.wait_for_function("() => !document.documentElement.classList.contains('vt-theme')", timeout=4000)
    page.wait_for_timeout(150)


def checkpoint(page):
    """Pin the story at the first hold frame and describe the stage: its pixels and the scene elements' colours."""
    page.evaluate("() => { const s = window.__site; s.seekMaster(s.map().H); }")
    page.wait_for_timeout(250)
    png = page.locator("[data-stage=story]").screenshot()
    style = page.evaluate("""() => {
      const st = document.querySelector('[data-stage=story]');
      const out = [];
      for (const el of [st, ...st.querySelectorAll('*')].slice(0, 400)) {
        const c = getComputedStyle(el);
        out.push(c.backgroundColor + '|' + c.color + '|' + c.borderTopColor + '|' + c.boxShadow);
      }
      return out.join('\\n');
    }""")
    return png, style


def test_toggle_never_changes_hash(site_url, browser):
    ctx, page, errors = open_home(browser, site_url + "/")
    try:
        assert page.evaluate("() => location.hash") == ""
        first = theme(page)
        press(page)
        assert theme(page) != first
        assert page.evaluate("() => location.hash") == ""
        press(page)
        assert theme(page) == first
        assert page.evaluate("() => location.hash") == ""
        assert errors == [], errors
    finally:
        ctx.close()
    ctx, page, errors = open_home(browser, site_url + "/#dark")
    try:
        press(page)
        assert theme(page) == "light"
        assert page.evaluate("() => location.hash") == "#dark"   # read, never written
    finally:
        ctx.close()


def test_toggle_flips_once_and_both_theme_colors(site_url, browser):
    ctx, page, errors = open_home(browser, site_url + "/")
    try:
        before = theme(page)
        press(page)
        assert theme(page) != before, "one press must flip once (a leftover listener would flip it back)"
        want = "#f3f3f0" if theme(page) == "light" else "#080a0f"
        metas = page.evaluate("() => [...document.querySelectorAll('meta[name=theme-color]')].map(m => m.content)")
        assert len(metas) == 2 and metas == [want, want], metas
        press(page)    # back to the start: the light-scheme meta must follow too (it ships #f3f3f0)
        want = "#f3f3f0" if theme(page) == "light" else "#080a0f"
        metas = page.evaluate("() => [...document.querySelectorAll('meta[name=theme-color]')].map(m => m.content)")
        assert metas == [want, want], metas
        assert errors == [], errors
    finally:
        ctx.close()


@pytest.mark.parametrize("vt", [True, False], ids=["with-vt", "without-vt"])
def test_scene_palette_follows_theme(site_url, browser, vt):
    init = None if vt else NO_VT
    ctx, page, errors = open_home(browser, site_url + "/#dark", init_script=init)
    try:
        assert page.evaluate("() => typeof document.startViewTransition === 'function'") == vt
        dark = checkpoint(page)
        press(page)
        assert theme(page) == "light"
        light = checkpoint(page)
        assert light[0] != dark[0] and light[1] != dark[1], "the scenes kept the old theme's palette"
        press(page)
        assert theme(page) == "dark"
        assert checkpoint(page) == dark
        assert errors == [], errors
    finally:
        ctx.close()
    # and the rebuilt scenes equal a cold load in the new theme
    ctx, page, errors = open_home(browser, site_url + "/#light", init_script=init)
    try:
        assert checkpoint(page) == light
    finally:
        ctx.close()


def test_legacy_hash_read(site_url, browser):
    ctx, page, errors = open_home(browser, site_url + "/#light")
    try:
        assert theme(page) == "light"
        page.evaluate("() => { location.hash = '#dark'; }")
        page.wait_for_timeout(400)
        assert theme(page) == "dark"
        assert errors == [], errors
    finally:
        ctx.close()
