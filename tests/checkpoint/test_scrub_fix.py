"""SCRUB-fix (RELEASE Astra 1, 2026-10-18): the release review's three findings on the scrub engine, each red at 0a5e10a.

- test_jump_to_last_pinned_after_back_to_native_price (HIGH, ICX-HIST.2): Back returns to native Price (its `pop` is
  never consumed by a landing), then a menu jump to the last pinned chapter: one pushState with its URL, and Back
  from there returns to Price. Phone and touch tablet (scrub) and a mouse window at tablet width (checkpoint engine,
  native Price).
- test_tablet_resize_carries_a_price_jump (MEDIUM, ICX-JUMP.5 / ICX-SCRUB.5): a same-mode resize while the menu's smooth
  jump to Price runs carries the jump to Price, one pushState at its arrival; a resize across 1024 (a mode change) ends
  it with no write (ICX-HIST.1).
- test_theme_rebuild_keeps_the_pixel_at_every_hold (MEDIUM, ICX-SCRUB.7): a theme switch with the reader still inside
  any phone hold, the last (Get the app) included, keeps the scroll position within 1 px.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

from test_scrub import _LOG, PRICE_TOP, ST, _still  # noqa: F401  (the scrub helpers)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _open(browser, site_url, w, h, touch=True, path="/"):
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch,
                              reduced_motion="no-preference")
    pg = ctx.new_page()
    pg.goto(site_url + path, wait_until="load")
    pg.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready') && window.__site.TL",
                         timeout=15000)
    pg.evaluate(_LOG)
    return ctx, pg


def _rest(pg, timeout=20000):
    """Either engine at rest: the scrub build's caught-up stage, or the checkpoint engine's rest / released."""
    pg.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
    pg.wait_for_function("() => ['rest', 'released'].includes(FEStory.state().phase) && !__site.state().intro", timeout=timeout)
    return pg.evaluate(ST)


@pytest.mark.parametrize("vp", ["390x664-touch", "820x1180-touch", "900x800-mouse"])
def test_jump_to_last_pinned_after_back_to_native_price(browser, site_url, vp):
    size, kind = vp.split("-")
    w, h = map(int, size.split("x"))
    ctx, pg = _open(browser, site_url, w, h, touch=kind == "touch")
    try:
        scrub = pg.evaluate("() => __site.map().scrub")
        assert scrub is (kind == "touch"), f"harness: {vp} scrub={scrub}"
        rows = pg.evaluate("() => FEStory.destinations")
        pinned = [d["slug"] for d in rows if d["kind"] == "pinned"]
        native = [d["slug"] for d in rows if d["kind"] == "native"]
        assert "price" in native, f"harness: Price must be native at {vp}: {native}"
        after = native[native.index("price") + 1]          # the native row after Price (A note)
        pg.evaluate("() => FEStory.goTo('look', {source: 'jump'})")
        _rest(pg)
        pg.wait_for_timeout(800)
        # menu: Price (native, one push at its arrival), then the row after it; Back returns to native Price
        pg.evaluate("() => FEStoryURL.jump('price')")
        pg.wait_for_timeout(2200)
        assert pg.evaluate("() => location.hash") == "#price", "harness: the jump to Price did not arrive"
        pg.evaluate(f"() => FEStoryURL.jump('{after}')")
        pg.wait_for_timeout(2200)
        assert pg.evaluate("() => location.hash") == "#" + after, f"harness: the jump to {after} did not arrive"
        pg.evaluate("() => history.back()")
        pg.wait_for_timeout(1500)
        assert pg.evaluate("() => location.hash") == "#price", "harness: Back did not return to Price"
        assert abs(pg.evaluate(PRICE_TOP)) < 120, f"harness: Back did not scroll to Price ({pg.evaluate(PRICE_TOP):.0f})"
        assert pg.evaluate("() => FEStory.state().phase") == "released", "harness: Price should be below the story"
        pg.evaluate("() => { window.__h.length = 0; window.__dests = []; FEStory.onDest((p) => { if (!p.preview) __dests.push(p.slug); }); }")
        # the menu's last pinned chapter
        pg.evaluate(f"() => FEStoryURL.jump('{pinned[-1]}')")
        s = _rest(pg)
        pg.wait_for_timeout(900)
        H, dests = pg.evaluate("() => window.__h"), pg.evaluate("() => window.__dests")
        assert s["rendered"] == [d["slug"] for d in rows].index(pinned[-1]) and s["phase"] == "rest", f"{vp}: did not land on {pinned[-1]}: {s}"
        assert H == [["pushState", "/#" + pinned[-1]]], f"{vp}: the jump after Back: expected one pushState, got {H}"
        assert dests == [pinned[-1]], f"{vp}: the jump emitted no destination (or more than one): {dests}"
        assert pg.evaluate("() => location.hash") == "#" + pinned[-1]
        # Back undoes the jump: Price again
        pg.evaluate("() => { window.__h.length = 0; }")
        pg.evaluate("() => history.back()")
        pg.wait_for_timeout(1800)
        assert pg.evaluate("() => location.hash") == "#price", f"{vp}: Back skipped the jump"
        assert abs(pg.evaluate(PRICE_TOP)) < 120, f"{vp}: Back did not return to Price ({pg.evaluate(PRICE_TOP):.0f})"
        assert pg.evaluate("() => window.__h") == [], "popstate wrote history"
    finally:
        ctx.close()


@pytest.mark.parametrize("to", ["800x1180", "820x1000", "1100x1180"])
def test_tablet_resize_carries_a_price_jump(browser, site_url, to):
    ctx, pg = _open(browser, site_url, 820, 1180)
    try:
        assert pg.evaluate("() => __site.map().scrub") is True, "harness: a touch tablet is a scrub build"
        pg.evaluate("() => FEStory.goTo('look', {source: 'jump'})")
        _still(pg, 20000)
        pg.wait_for_timeout(800)
        pg.evaluate("() => { window.__h.length = 0; }")
        y0 = pg.evaluate("() => scrollY")
        pg.evaluate("() => FEStoryURL.jump('price')")
        pg.wait_for_timeout(200)                      # the smooth scroll is under way
        assert pg.evaluate(PRICE_TOP) > 300, "harness: the smooth scroll had already arrived"
        assert pg.evaluate("() => scrollY") > y0, "harness: the native scroll had not started"
        w, h = map(int, to.split("x"))
        pg.set_viewport_size({"width": w, "height": h})
        pg.wait_for_timeout(4000)
        top, H = pg.evaluate(PRICE_TOP), pg.evaluate("() => window.__h")
        if w < 1024:                                  # the same mode: the jump arrives, one push there
            assert pg.evaluate("() => __site.map().scrub") is True, "harness: still a scrub build"
            assert -4 <= top <= 200, f"the Price jump stopped mid-story after the resize (Price at {top:.0f}px); writes {H}"
            assert H == [["pushState", "/#price"]], f"one push for the jump, at its arrival; saw {H}"
        else:                                         # a mode change ends the jump with no write (ICX-HIST.1)
            assert pg.evaluate("() => __site.map().scrub") is False, "harness: >= 1024 is the checkpoint engine"
            assert ["pushState", "/#price"] not in H, f"a mode change must void the jump's write; saw {H}"
            if H:
                assert pg.evaluate("() => location.hash") != "#price" or -4 <= top <= 200, f"#price written away from Price ({top:.0f}px): {H}"
    finally:
        ctx.close()


def test_theme_rebuild_keeps_the_pixel_at_every_hold(browser, site_url):
    ctx, pg = _open(browser, site_url, 390, 664, path="/#dark")
    try:
        _still(pg, 20000)
        HOLDS = ("() => { const m = __site.map(); return m.pieces.filter((p) => p.kind === 'hold')"
                 ".map((p) => ({beat: p.beat, top: m.storyTop, s0: p.s0, s1: p.s1, end: FX.story.endY()})); }")
        bad = []
        for i in range(len(pg.evaluate(HOLDS))):
            for where in ("mid", "end"):
                hd = pg.evaluate(HOLDS)[i]                # the current theme's map
                y = hd["top"] + ((hd["s0"] + hd["s1"]) / 2 if where == "mid" else hd["s1"] - 4)
                y = min(y, hd["end"] - 2)                 # inside the pinned story (the last hold runs into the release)
                pg.evaluate(f"() => scrollTo(0, {round(y)})")
                s0 = _rest(pg)
                pg.wait_for_timeout(400)
                y0 = pg.evaluate("() => scrollY") - hd["top"] - hd["s0"]       # the reader's pixel inside the hold
                pg.evaluate("() => document.querySelector('[data-theme-toggle]').click()")
                pg.wait_for_timeout(2500)
                s1 = _rest(pg)
                h1 = pg.evaluate(HOLDS)[i]                # the new theme's map (dark and light ramps differ: live's too)
                y1 = pg.evaluate("() => scrollY") - h1["top"] - h1["s0"]
                if abs(y1 - y0) > 1 or s1["phase"] != s0["phase"]:
                    bad.append(f"{hd['beat']} {where}: {y0:.0f} -> {y1:.0f} px into the hold ({y1 - y0:+.0f} px; {s0['phase']} -> {s1['phase']})")
        assert not bad, "a theme rebuild moved the reader: " + "; ".join(bad)
    finally:
        ctx.close()
