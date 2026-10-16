"""A8: the homepage adopts the shared theme module (FETheme, hashPolicy "home").

The toggle never writes a hash; #dark / #light is still read on load and on hashchange; the story scenes rebuild with
the new palette on every switch, with and without View Transitions.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

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


ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECK = str(ROOT / "scripts" / "checks" / "check_theme_reveal.py")
SLOW = "/tests/fixtures/theme/index.html?seed=slow"


def run_check(url, *extra):
    return subprocess.run([sys.executable, CHECK, url, *extra], capture_output=True, text=True, timeout=240)


def test_reveal_check_passes_on_home(site_url):
    # C5b: the circle starts within 50 ms of the press in both directions (the check clicks twice: first and back),
    # now that the scenes rebuild after the circle starts instead of inside the view-transition update. Everything
    # else is unchanged: duration, easing, centre, no corner snap at 390 and 1440, instant under reduced motion.
    r = run_check(site_url + "/", "--max-start-ms", "50")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip().splitlines()[-1].startswith("ALL PASS"), r.stdout


def test_reveal_check_default_start_budget_is_still_50(site_url):
    r = run_check(site_url + SLOW, "--width", "390")
    assert r.returncode == 1 and "expected <= 50" in r.stdout, r.stdout + r.stderr
    r = run_check(site_url + SLOW, "--width", "390", "--max-start-ms", "80")
    assert r.returncode == 1 and "expected <= 80" in r.stdout, r.stdout + r.stderr


SWAP_PROBE = r"""
async () => {
  // C5b: the scenes rebuild after the circle starts; until the swap the OLD scenes are on the stage. Every frame before
  // the swap must keep the circle short of the stage and the cards over it (else a frame shows the old palette inside
  // the new theme). Samples the circle's radius each frame; the swap is when the old scene roots leave the stage.
  const stg = document.querySelector('[data-stage=story]'), ovr = document.querySelector('.pin-over');
  const btn = document.querySelector('[data-theme-toggle]');
  const olds = [...stg.children].filter((e) => e.classList.contains('fx-root') && !e.classList.contains('fx-seam'));
  const br = btn.getBoundingClientRect(), bx = br.left + br.width / 2, by = br.top + br.height / 2;
  let dist = Infinity;
  for (const el of [stg, ...ovr.children]) {
    const b = el.getBoundingClientRect();
    if (b.width && b.height) dist = Math.min(dist, Math.hypot(Math.max(b.left - bx, 0, bx - b.right), Math.max(b.top - by, 0, by - b.bottom)));
  }
  let swapped = false;
  const mo = new MutationObserver(() => { if (olds.some((e) => !e.isConnected)) swapped = true; });
  mo.observe(stg, { childList: true });
  const radii = [], t0 = performance.now();
  btn.click();
  await new Promise((done) => {
    const tick = () => {
      if (!swapped) {
        try {
          const r = parseFloat(getComputedStyle(document.documentElement, '::view-transition-new(root)').getPropertyValue('--vt-r'));
          if (Number.isFinite(r)) radii.push(Math.round(r));
        } catch (e) { /* no pseudo yet */ }
      }
      if (performance.now() - t0 > 1500 || (swapped && !document.documentElement.classList.contains('vt-theme'))) done();
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
  mo.disconnect();
  return { dist: Math.round(dist), swapped, radii, roots: stg.querySelectorAll(':scope > .fx-root:not(.fx-seam)').length };
}
"""


@pytest.mark.parametrize("width,height", [(390, 664), (1440, 900)])
def test_theme_rebuild_lands_before_the_circle_reaches_the_stage(site_url, browser, width, height):
    # a slow CPU (4x) makes the rebuild long enough to matter: the rest is done in one go before a frame could show
    # the circle over the old scenes
    ctx = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="no-preference")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(site_url + "/#dark", wait_until="load")
        page.wait_for_function("() => window.__site && window.__site.TL", timeout=8000)
        page.wait_for_timeout(300)
        n = page.evaluate("() => document.querySelectorAll('[data-stage=story] > .fx-root:not(.fx-seam)').length")
        cdp = ctx.new_cdp_session(page)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        for leg in ("first", "back"):
            r = page.evaluate(SWAP_PROBE)
            assert r["swapped"], f"{leg}: the scenes were never rebuilt"
            over = [x for x in r["radii"] if x >= r["dist"]]
            assert not over, f"{leg}: frames drew the circle at {over} px over the old scenes ({r['dist']} px away)"
            assert r["roots"] == n, f"{leg}: {r['roots']} scene roots on the stage after the switch, expected {n}"
            page.wait_for_timeout(200)
        assert errors == [], errors
    finally:
        ctx.close()


def test_double_press_flips_twice(site_url, browser):
    # two presses before the view-transition update applies are two flips (back where it started), as on the tours:
    # the homepage flips from FETheme.target() (the theme it is heading to), not from the not-yet-updated DOM
    ctx, page, errors = open_home(browser, site_url + "/#dark")
    try:
        start = theme(page)
        page.evaluate("""() => { const b = document.querySelector('[data-theme-toggle]'); b.click(); b.click(); }""")
        page.wait_for_function("() => !document.documentElement.classList.contains('vt-theme')", timeout=4000)
        page.wait_for_timeout(300)
        assert theme(page) == start
        assert page.evaluate("() => localStorage.getItem('fe-theme')") == start
        assert errors == [], errors
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
