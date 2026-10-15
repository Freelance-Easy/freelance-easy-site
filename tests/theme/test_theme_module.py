"""A5: the shared theme module (assets/shared/theme.js + theme.css) on its fixture page.

The fixture (tests/fixtures/theme/index.html) takes ?policy=home|tour|none and ?bare=1 (no head script, so
FETheme.init meets a page without data-theme). The reveal probe lives in scripts/checks/check_theme_reveal.py, which
A6, A7, A8 and C8 reuse on real pages.
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOGGLE = "[data-theme-toggle]"

_spec = importlib.util.spec_from_file_location("check_theme_reveal", ROOT / "scripts" / "checks" / "check_theme_reveal.py")
ctr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctr)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def fixture_url(site_url):
    return f"{site_url}/tests/fixtures/theme/index.html"


def open_page(browser, url, *, width=1440, reduced=False, init_script=None):
    ctx = browser.new_context(viewport={"width": width, "height": ctr.HEIGHTS.get(width, 900)},
                              reduced_motion="reduce" if reduced else "no-preference")
    if init_script:
        ctx.add_init_script(init_script)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_function("() => !!window.FETheme", timeout=3000)
    page.wait_for_timeout(200)
    assert errors == [], errors
    return ctx, page


def settle(page):
    page.wait_for_function("() => !document.documentElement.classList.contains('vt-theme')", timeout=3000)
    page.wait_for_timeout(60)


def theme(page):
    return page.evaluate("() => document.documentElement.getAttribute('data-theme')")


def test_radius_probe_fixture(browser, fixture_url):
    for width in (1440, 390):
        ctx, page = open_page(browser, fixture_url, width=width)
        try:
            for leg in ("first", "back"):
                p = ctr.probe(page, TOGGLE)
                assert ctr.reveal_failures(p) == [], (width, leg, ctr.reveal_failures(p))
                took = ctr.growth_ms(p)
                assert 380 <= took <= 460, (width, leg, took)
                assert abs(p["vtX"] - p["cx"]) <= 1.5 and abs(p["vtY"] - p["cy"]) <= 1.5, (width, leg, p)
                settle(page)
        finally:
            ctx.close()


def test_reduced_motion_instant(browser, fixture_url):
    ctx, page = open_page(browser, fixture_url, reduced=True)
    try:
        for _ in range(2):
            p = ctr.probe(page, TOGGLE)
            assert ctr.instant_failures(p) == [], ctr.instant_failures(p)
        # FETheme.set with a source element is instant too
        assert page.evaluate("""() => { const b = document.querySelector('[data-theme-toggle]');
            FETheme.set(FETheme.get() === 'dark' ? 'light' : 'dark', { from: b });
            return [document.documentElement.getAttribute('data-theme'),
                    document.documentElement.classList.contains('vt-theme')]; }""") == ["light", False]
    finally:
        ctx.close()


def test_no_view_transitions_instant(browser, fixture_url):
    no_vt = "delete Document.prototype.startViewTransition; delete document.startViewTransition;"
    ctx, page = open_page(browser, fixture_url, init_script=no_vt)
    try:
        assert page.evaluate("() => typeof document.startViewTransition") == "undefined"
        for _ in range(2):
            p = ctr.probe(page, TOGGLE)
            assert ctr.instant_failures(p) == [], ctr.instant_failures(p)
    finally:
        ctx.close()


SPY = """
window.__removed = [];
const _rm = Element.prototype.removeAttribute;
Element.prototype.removeAttribute = function (name) {
  if (this === document.documentElement && String(name).toLowerCase() === "data-theme") window.__removed.push(name);
  return _rm.apply(this, arguments);
};
"""
WATCH = """() => { window.__old = [];
  new MutationObserver((ms) => ms.forEach((m) => window.__old.push(m.oldValue)))
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'], attributeOldValue: true }); }"""


def test_data_theme_always_explicit(browser, fixture_url):
    # a page with no head script (no data-theme at all) and one whose data-theme is odd: init makes both explicit
    ctx, page = open_page(browser, fixture_url + "?bare=1", init_script=SPY)
    try:
        assert theme(page) == "dark"
        page.evaluate(WATCH)
        seen = []
        for _ in range(3):
            page.click(TOGGLE)
            seen.append(theme(page))
            settle(page)
            seen.append(theme(page))
        for js in ("FETheme.set('dark')", "FETheme.set('light')", "FETheme.set('dark')", "FETheme.set('bogus')",
                   "FETheme.set(null)", "FETheme.set('')", "location.hash = '#light'", "location.hash = '#nope'",
                   "FETheme.init({hashPolicy: 'home'})"):
            page.evaluate(f"() => {{ {js}; }}")
            page.wait_for_timeout(30)
            seen.append(theme(page))
        page.wait_for_timeout(50)
        assert set(seen) <= {"dark", "light"}, seen
        assert "dark" in seen and "light" in seen, seen
        old = page.evaluate("() => window.__old")
        assert old and None not in old, f"data-theme was absent between switches: {old}"
        assert page.evaluate("() => window.__removed") == []
        page.evaluate("() => document.documentElement.setAttribute('data-theme', 'sepia')")
        page.evaluate("() => FETheme.init({hashPolicy: 'none'})")
        assert theme(page) == "dark"
    finally:
        ctx.close()


EVENTS = """() => { window.__ev = [];
  document.addEventListener('fe:themechange', (e) => window.__ev.push(
    ['document', e.detail.theme, document.documentElement.getAttribute('data-theme')]));
  window.addEventListener('fe:themechange', (e) => window.__ev.push(['window', e.detail.theme])); }"""


def test_fires_fe_themechange(browser, fixture_url):
    for reduced in (False, True):
        ctx, page = open_page(browser, fixture_url, reduced=reduced)
        try:
            page.evaluate(EVENTS)
            page.click(TOGGLE)
            settle(page)
            # fired once, with the new theme, after data-theme is set; it bubbles to window
            assert page.evaluate("() => window.__ev") == [["document", "light", "light"], ["window", "light"]]
            assert page.evaluate("() => [FETheme.get(), localStorage.getItem('fe-theme')]") == ["light", "light"]
            page.evaluate("() => FETheme.set('light')")         # no change, no event
            assert len(page.evaluate("() => window.__ev")) == 2
            page.evaluate("() => FETheme.set('dark')")
            page.evaluate("() => { location.hash = '#light'; }")  # home policy: a hash theme switches too
            page.wait_for_timeout(100)
            ev = [e[1] for e in page.evaluate("() => window.__ev") if e[0] == "document"]
            assert ev == ["light", "dark", "light"], ev
        finally:
            ctx.close()


def hash_of(page):
    return page.evaluate("() => location.hash")


def stored(page):
    return page.evaluate("() => localStorage.getItem('fe-theme')")


def test_hash_policy(browser, fixture_url):
    # home: reads #dark / #light (load and hashchange), never writes
    ctx, page = open_page(browser, fixture_url + "?policy=home&bare=1#light")
    try:
        assert theme(page) == "light" and stored(page) is None   # read on load, not remembered on load
        page.click(TOGGLE)
        settle(page)
        assert theme(page) == "dark" and hash_of(page) == "#light"
        page.evaluate("() => { location.hash = '#dark'; }")
        page.evaluate("() => { location.hash = '#light'; }")
        page.wait_for_timeout(100)
        assert theme(page) == "light" and stored(page) == "light"
    finally:
        ctx.close()
    ctx, page = open_page(browser, fixture_url + "?policy=home")
    try:
        page.click(TOGGLE)
        settle(page)
        assert theme(page) == "light" and hash_of(page) == ""
    finally:
        ctx.close()
    ctx, page = open_page(browser, fixture_url + "?policy=home&bare=1#light&reduced")
    try:
        assert theme(page) == "dark"            # home reads a bare #dark / #light only, as its head script does
    finally:
        ctx.close()

    # tour: reads the flag among others; a switch rewrites only that flag and keeps the rest
    ctx, page = open_page(browser, fixture_url + "?policy=tour&bare=1#light&reduced&email")
    try:
        assert theme(page) == "light"
        page.click(TOGGLE)
        settle(page)
        assert theme(page) == "dark" and hash_of(page) == "#dark&reduced&email"
        page.click(TOGGLE)
        settle(page)
        assert theme(page) == "light" and hash_of(page) == "#light&reduced&email"
        page.evaluate("() => { location.hash = '#embed&dark'; }")
        page.wait_for_timeout(100)
        assert theme(page) == "dark" and hash_of(page) == "#embed&dark"
    finally:
        ctx.close()
    ctx, page = open_page(browser, fixture_url + "?policy=tour#reduced&email")
    try:
        page.click(TOGGLE)
        settle(page)
        assert theme(page) == "light" and hash_of(page) == "#reduced&email"   # no flag: nothing added
    finally:
        ctx.close()

    # none: neither reads nor writes
    ctx, page = open_page(browser, fixture_url + "?policy=none&bare=1#light")
    try:
        assert theme(page) == "dark"
        page.click(TOGGLE)
        settle(page)
        page.click(TOGGLE)
        settle(page)
        assert theme(page) == "dark" and hash_of(page) == "#light"
        page.evaluate("() => FETheme.set('light')")
        page.evaluate("() => { location.hash = '#dark'; }")
        page.wait_for_timeout(100)
        assert theme(page) == "light" and hash_of(page) == "#dark"
    finally:
        ctx.close()


def test_check_theme_reveal_script(site_url, fixture_url):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "checks" / "check_theme_reveal.py"), fixture_url],
                       capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip().splitlines()[-1].startswith("ALL PASS"), r.stdout
