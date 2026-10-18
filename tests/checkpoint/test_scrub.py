"""SCRUB (Daniel 2026-10-18, PHONE-options option 1): phones (layout "tall", < 640) and touch tablets run the live site's
scroll scrub (docs/interaction-contract.md ICX-SCRUB): the page scrolls natively and the stage follows the scroll.

- test_no_input_intercepted: ICX-SCRUB.1, the guard: no touchmove and no wheel event is ever prevented, at a phone and
  a touch tablet, and the page moves under the finger (red on the checkpoint engine, 5953a65: every touchmove in the
  story was cancelled).
- test_slow_drag_follows_the_finger: ICX-SCRUB.2/.3: a slow 220 px drag moves the page about that far and the story
  about 0.41 s (the live site's measurement), and stops when the finger stops; a flick back plays backwards (no dip).
- test_history_one_replace_per_settled_hold: ICX-SCRUB.5: scrolling across a hold writes nothing; settling in a hold
  writes one replaceState with its URL; a menu jump writes one pushState and lands on the hold.
- test_map_matches_live: ICX-SCRUB.4: the phone's scroll map (__site.map().pieces) is the live site's (main 652d12a,
  tests/checkpoint/scrub_live_map.json) within 1 px, dark and light.
- test_desktop_keeps_checkpoints: a desktop window is not a scrub build.
"""
from __future__ import annotations

import json
import pathlib

import pytest
from playwright.sync_api import sync_playwright

LIVE = json.loads((pathlib.Path(__file__).parent / "scrub_live_map.json").read_text())

# every touchmove / wheel seen, with defaultPrevented, by a passive listener after the story's own (window, bubble)
_LOG = """() => {
  const L = window.__sc = { moves: [], wheels: [], trace: [] };
  addEventListener('touchmove', (e) => L.moves.push([e.cancelable, e.defaultPrevented]), { passive: true });
  addEventListener('wheel', (e) => L.wheels.push([e.cancelable, e.defaultPrevented]), { passive: true });
  const H = window.__h = [];
  for (const m of ['pushState', 'replaceState']) {
    const f = history[m].bind(history);
    history[m] = (s, t, u) => { if (u != null) H.push([m, String(u)]); return f(s, t, u); };
  }
}"""
ST = "() => ({...FEStory.state(), ...__site.state(), y: Math.round(scrollY)})"


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


def _still(pg, timeout=12000):
    """Wait until the stage has caught up with the scroll (phase rest) and return the state."""
    pg.wait_for_function("() => FEStory.state().phase === 'rest' && !__site.state().intro", timeout=timeout)
    return pg.evaluate(ST)


def _finger(pg, cdp, x, y0, offsets, ms=12):
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y0}]})
    for off in offsets:
        pg.wait_for_timeout(ms)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y0 - off}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


@pytest.mark.parametrize("vp", ["390x664", "360x640", "820x1180"])
def test_no_input_intercepted(browser, site_url, vp):
    w, h = map(int, vp.split("x"))
    ctx, pg = _open(browser, site_url, w, h)
    try:
        pg.evaluate("() => FEStory.goTo('look', {source: 'jump'})")
        s0 = _still(pg)
        cdp = pg.context.new_cdp_session(pg)
        # a slow drag up, a flick up, a flick back down: inside the story, all native
        _finger(pg, cdp, w // 2, int(h * 0.75), [3, 8, 20, 40, 70, 110, 150, 190, 220], ms=40)
        pg.wait_for_timeout(500)
        _finger(pg, cdp, w // 2, int(h * 0.75), [2, 5, 12, 28, 55, 95, 145, 200])
        pg.wait_for_timeout(1200)
        _finger(pg, cdp, w // 2, int(h * 0.3), [-2, -5, -12, -28, -55, -95, -145, -200])
        pg.wait_for_timeout(1200)
        for _ in range(6):
            pg.mouse.move(w // 2, h // 2)
            pg.mouse.wheel(0, 120)
            pg.wait_for_timeout(30)
        pg.wait_for_timeout(600)
        L = pg.evaluate("() => window.__sc")
        moved = pg.evaluate(ST)
        assert L["moves"], f"{vp}: no touchmove reached the page"
        assert not [m for m in L["moves"] if m[1]], f"{vp}: touchmoves prevented: {sum(1 for m in L['moves'] if m[1])}/{len(L['moves'])}"
        assert L["wheels"], f"{vp}: no wheel reached the page"
        assert not [m for m in L["wheels"] if m[1]], f"{vp}: wheels prevented: {sum(1 for m in L['wheels'] if m[1])}/{len(L['wheels'])}"
        assert moved["y"] != s0["y"], f"{vp}: the page never scrolled under the finger: {s0} -> {moved}"
        assert pg.evaluate("() => __site.map().scrub") is True, f"{vp}: a touch screen < 1024 must be a scrub build"
    finally:
        ctx.close()


def test_slow_drag_follows_the_finger(browser, site_url):
    ctx, pg = _open(browser, site_url, 390, 664)
    try:
        # at the end of Templates' hold (where the live measurement started: its map's hold s1 - 2)
        pg.evaluate("() => { const m = __site.map(); const h = m.pieces.find((p) => p.kind === 'hold' && p.beat === 'look'); scrollTo(0, m.storyTop + h.s1 - 2); }")
        s0 = _still(pg)
        cdp = pg.context.new_cdp_session(pg)
        # a slow 220 px drag (the live measurement's gesture: CDP touch at 300 px/s, no fling)
        cdp.send("Input.synthesizeScrollGesture", {"x": 195, "y": 500, "yDistance": -220, "xDistance": 0, "speed": 300,
                                                   "gestureSourceType": "touch", "preventFling": True})
        s1 = _still(pg)
        dy, dT = s1["y"] - s0["y"], s1["shown"] - s0["shown"]
        assert 180 <= dy <= 240, f"the page moved {dy} px for a 220 px drag (live: 215)"
        assert 0.25 <= dT <= 0.6, f"the story moved {dT:.3f} s for a 220 px drag (live: 0.41)"
        pg.wait_for_timeout(500)
        assert abs(pg.evaluate(ST)["shown"] - s1["shown"]) < 1e-3, "the story moved on after the finger stopped"
        # a flick back plays backwards: the shown time falls through intermediate frames, never a dip
        pg.evaluate("() => { window.__fxTrace = []; }")
        cdp.send("Input.synthesizeScrollGesture", {"x": 195, "y": 200, "yDistance": 160, "xDistance": 0, "speed": 2400,
                                                   "gestureSourceType": "touch", "preventFling": False})
        s2 = _still(pg)
        tr = pg.evaluate("() => window.__fxTrace.map((r) => r[1])")
        pg.evaluate("() => { window.__fxTrace = null; }")
        assert s2["shown"] < s1["shown"] - 0.3, f"a back flick did not play back: {s1['shown']:.3f} -> {s2['shown']:.3f}"
        distinct = {round(t, 2) for t in tr if s2["shown"] + 0.02 < t < s1["shown"] - 0.02}
        assert len(distinct) >= 5, f"the back flick cut instead of playing backwards ({len(distinct)} frames between)"
        assert not s2["dip"], "a back flick dipped"
    finally:
        ctx.close()


def test_history_one_replace_per_settled_hold(browser, site_url):
    ctx, pg = _open(browser, site_url, 390, 664)
    try:
        _still(pg)
        pg.evaluate("() => { window.__h.length = 0; }")
        # scroll straight to the Invoices hold (crossing Templates' hold on the way): the stage chases, passes Templates
        y = pg.evaluate("() => __site.scrollFor('know')")
        pg.evaluate(f"() => scrollTo(0, {y})")
        s = _still(pg, 20000)
        pg.wait_for_timeout(700)                      # story-url.js's QUIET window and more
        H = pg.evaluate("() => window.__h")
        assert s["rendered"] == 2 and s["dest"] == 2, f"did not land on Invoices: {s}"
        assert H == [["replaceState", "/#invoices"]], f"settling on Invoices: expected one replaceState, got {H}"
        assert pg.evaluate("() => document.querySelector('[data-story-live]').textContent") == "Invoices"
        # stopping mid-ramp writes nothing
        pg.evaluate("() => { window.__h.length = 0; }")
        pg.evaluate(f"() => scrollTo(0, {y} + Math.round(innerHeight * 0.6))")
        _still(pg)
        pg.wait_for_timeout(500)
        assert pg.evaluate("() => window.__h") == [], "a stop between holds wrote history"
        # a menu jump: one pushState, landing on the hold
        pg.evaluate("() => { window.__h.length = 0; }")
        pg.evaluate("() => FEStoryURL.jump('dashboard')")
        s = _still(pg, 20000)
        pg.wait_for_timeout(500)
        H = pg.evaluate("() => window.__h")
        assert s["rendered"] == 3 and abs(s["y"] - pg.evaluate("() => __site.scrollFor('grow')")) <= 1, f"jump: {s}"
        assert H == [["pushState", "/#dashboard"]], f"a menu jump: expected one pushState, got {H}"
    finally:
        ctx.close()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_map_matches_live(browser, site_url, theme):
    ctx, pg = _open(browser, site_url, 390, 664, path=f"/#{theme}")
    try:
        m = pg.evaluate("() => __site.map()")
        live = LIVE[theme]
        assert [(p["kind"], p["beat"]) for p in m["pieces"]] == [(p["kind"], p["beat"]) for p in live["pieces"]]
        for a, b in zip(m["pieces"], live["pieces"]):
            assert abs(a["s0"] - b["s0"]) <= 1 and abs(a["s1"] - b["s1"]) <= 1, f"{theme}: piece {a} vs live {b}"
            assert abs(a["T0"] - b["T0"]) <= 0.001 and abs(a["T1"] - b["T1"]) <= 0.001, f"{theme}: piece {a} vs live {b}"
        assert abs(m["scrollLen"] - live["scrollLen"]) <= 1
    finally:
        ctx.close()


def test_desktop_keeps_checkpoints(browser, site_url):
    ctx, pg = _open(browser, site_url, 1440, 900, touch=False)
    try:
        assert pg.evaluate("() => __site.map().scrub") is False
    finally:
        ctx.close()
