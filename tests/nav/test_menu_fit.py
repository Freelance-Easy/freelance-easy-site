"""PHONE: the menu sheet fits the visible phone viewport (Daniel's first iPhone session, 2026-10-17).

At iPhone 14 Safari with bars (390x664) the open sheet was 698 px tall in a 608 px box: no tap-outside area, Close
off-screen until the sheet was scrolled, and the Classic view switch sat on the bottom edge, where a "tap outside to
close" turned Classic on (and it persisted). At each real phone viewport (memory feedback-audit-real-viewports:
390x664, 375x548, 360x640, landscape 844x390), on "/" and /tour/, with the sheet open:

- test_sheet_fits_with_tap_out_zone: the sheet ends >= TAP_ZONE px above the visible viewport's bottom (bars showing),
  every point of that bottom zone is the sheet's dim area (a tap there closes it, never a control), and a tap in it
  closes the sheet without touching Classic.
- test_close_always_visible: Close is in view and is the element at its own centre (not clipped or covered).
- test_classic_not_at_the_edge: on "/", where the sheet holds the Classic row (390x664, 360x640), the row sits above
  the chapter list (never the sheet's last control), and the chapter list is complete (every destination, reachable).

Run: uv run --with pytest --with playwright python3 -m pytest tests/nav/test_menu_fit.py -q
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

BTN = "[data-menu-open]"
DLG = "#fe-menu"
TAP_ZONE = 48
SIZES = [(390, 664), (375, 548), (360, 640), (844, 390)]
PAGES = ["/", "/tour/"]

GEO = """() => {
  const d = document.querySelector('#fe-menu'), p = d.querySelector('.fe-menu-panel'), c = d.querySelector('[data-menu-close]');
  const vh = visualViewport.height, vw = visualViewport.width, r = (e) => { const b = e.getBoundingClientRect(); return [b.top, b.bottom, b.left, b.right]; };
  const zone = [];
  for (let y = vh - %d + 1; y < vh; y += 6) for (let x = 4; x < vw - 2; x += 24) {
    const e = document.elementFromPoint(x, y); if (e !== d) zone.push([Math.round(x), Math.round(y), e ? (e.className || e.tagName) + '' : null]); }
  const cr = r(c), hit = document.elementFromPoint((cr[2] + cr[3]) / 2, (cr[0] + cr[1]) / 2);
  return { vh, panel: r(p), close: cr, closeHit: hit === c || (hit && c.contains(hit)), zone };
}""" % TAP_ZONE


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _open_sheet(browser, site_url, path, w, h, theme="dark"):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True,
                              reduced_motion="no-preference")
    ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', '{theme}'); }} catch (e) {{}}")
    page = ctx.new_page()
    page.goto(site_url + path, wait_until="load")
    if path == "/":
        page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')",
                               timeout=15000)
    page.wait_for_timeout(300)
    page.tap(BTN)
    page.wait_for_function("(s) => document.querySelector(s).open", arg=DLG, timeout=3000)
    page.wait_for_timeout(200)
    return ctx, page


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("w,h", SIZES)
def test_sheet_fits_with_tap_out_zone(browser, site_url, path, w, h):
    ctx, page = _open_sheet(browser, site_url, path, w, h)
    try:
        g = page.evaluate(GEO)
        assert g["panel"][1] <= g["vh"] - TAP_ZONE + 0.5, \
            f"{w}x{h} {path}: the sheet ends at {g['panel'][1]:.0f} of a {g['vh']:.0f} px viewport: no {TAP_ZONE} px tap-out zone"
        assert not g["zone"], f"{w}x{h} {path}: points of the bottom {TAP_ZONE} px are not the dim area: {g['zone'][:6]}"
        pressed = page.evaluate("() => [...document.querySelectorAll('#fe-menu .classic-toggle')].map(b => b.getAttribute('aria-pressed'))")
        page.touchscreen.tap(w // 2, int(g["vh"]) - 12)
        page.wait_for_timeout(200)
        assert not page.evaluate("(s) => document.querySelector(s).open", DLG), f"{w}x{h} {path}: a tap at the bottom left the sheet open"
        assert page.evaluate("() => [...document.querySelectorAll('#fe-menu .classic-toggle')].map(b => b.getAttribute('aria-pressed'))") == pressed
        assert page.evaluate("() => localStorage.getItem('fe-classic')") is None, f"{w}x{h} {path}: a tap outside changed Classic"
    finally:
        ctx.close()


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("w,h", SIZES)
def test_close_always_visible(browser, site_url, path, w, h):
    ctx, page = _open_sheet(browser, site_url, path, w, h)
    try:
        g = page.evaluate(GEO)
        top, bottom = g["close"][0], g["close"][1]
        assert top >= 0 and bottom <= g["vh"] and g["closeHit"], f"{w}x{h} {path}: Close at {top:.0f}-{bottom:.0f} of {g['vh']:.0f}, hit={g['closeHit']}"
    finally:
        ctx.close()


@pytest.mark.parametrize("w,h", [(390, 664), (360, 640)])
def test_classic_not_at_the_edge(browser, site_url, w, h):
    ctx, page = _open_sheet(browser, site_url, "/", w, h)
    try:
        r = page.evaluate("""() => { const d = document.querySelector('#fe-menu'); const row = d.querySelector('.fe-menu-classic');
          const ch = d.querySelector('.fe-menu-chapters'); const vis = (e) => !!e && e.getClientRects().length > 0;
          return { row: vis(row), chapters: vis(ch), above: vis(row) && vis(ch) && !!(row.compareDocumentPosition(ch) & Node.DOCUMENT_POSITION_FOLLOWING)
                     && row.getBoundingClientRect().bottom <= ch.getBoundingClientRect().top + 0.5,
                   n: d.querySelectorAll('.fe-menu-chapters a[data-go]').length, want: FEStory.destinations.length }; }""")
        assert r["row"] and r["chapters"], f"{w}x{h}: the Classic row or the chapter list is not shown: {r}"
        assert r["above"], f"{w}x{h}: the Classic row is not above the chapter list (a stray tap at the sheet's end hits it)"
        assert r["n"] == r["want"], f"{w}x{h}: {r['n']} chapter rows, {r['want']} destinations"
        last = page.locator("#fe-menu .fe-menu-chapters a[data-go]").last
        last.scroll_into_view_if_needed()
        box, vh = last.bounding_box(), page.evaluate("() => visualViewport.height")
        assert box and box["y"] + box["height"] <= vh - TAP_ZONE + 0.5, f"{w}x{h}: the last chapter cannot be scrolled into the sheet: {box}"
    finally:
        ctx.close()
