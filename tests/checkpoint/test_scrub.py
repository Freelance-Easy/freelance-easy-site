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
  const A = window.__ann = [], live = document.querySelector('[data-story-live]');
  new MutationObserver(() => { if (live.textContent) A.push(live.textContent); })
    .observe(live, { childList: true, characterData: true, subtree: true });
}"""
PRICE_TOP = "() => document.getElementById('price').getBoundingClientRect().top"
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
    """Wait until the stage has caught up with the scroll (phase rest) and return the state. Two frames first: a scroll
    just made is read by the next frame's tick (before it, the phase is still the old rest)."""
    pg.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
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


# a slow continuous scroll from `from` to `to`: `slow` px/s inside the holds (and 10 px around them), `fast` px/s on the
# ramps, one scrollTo per frame, never a pause; resolves with performance.now() at its last scroll
_DRIVE = """(a) => new Promise((res) => {
  const m = __site.map(), holds = m.pieces.filter((p) => p.kind === 'hold').map((p) => [m.storyTop + p.s0 - 10, m.storyTop + p.s1 + 10]);
  let y = a.from, t = performance.now();
  const step = (now) => {
    const dt = Math.min(0.05, (now - t) / 1000); t = now;
    y = Math.min(a.to, y + (holds.some(([s0, s1]) => y >= s0 && y <= s1) ? a.slow : a.fast) * dt);
    scrollTo(0, Math.round(y));
    if (y >= a.to) return res(performance.now());
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
})"""
_LANDS = """() => { window.__lands = []; FEStory.onLand((p) => { if (p.final) __lands.push([performance.now(), p.slug]); }); }"""


def test_slow_continuous_drag_lands_only_when_it_stops(browser, site_url):
    """Sol SCRUB-1 HIGH 1 (ICX-SCRUB.5): a slow, continuous scroll across two holds (Templates, Invoices) lets the stage
    catch up with the scroll inside each hold, but the scroll never stopped: no landing, no announcement, no history write
    while it moves; once it stops inside the Dashboard hold, exactly one landing, one announcement and one replaceState."""
    ctx, pg = _open(browser, site_url, 390, 664)
    try:
        hold = pg.evaluate("() => { const m = __site.map(); const f = (b) => m.pieces.find((p) => p.kind === 'hold' && p.beat === b);"
                           " return { look: m.storyTop + f('look').s0, grow: m.storyTop + (f('grow').s0 + f('grow').s1) / 2 }; }")
        y0 = int(hold["look"]) - 130                  # on the ramp before Templates' hold
        pg.evaluate(f"() => scrollTo(0, {y0})")
        _still(pg, 20000)
        pg.wait_for_timeout(700)
        pg.evaluate(_LANDS)
        pg.evaluate("() => { window.__h.length = 0; window.__ann.length = 0; }")
        t_end = pg.evaluate(_DRIVE, {"from": y0, "to": round(hold["grow"]), "slow": 60, "fast": 700})
        early = [x for x in pg.evaluate("() => window.__lands") if x[0] < t_end]
        assert not early, f"a hold crossed while the scroll was still moving landed: {early}"
        assert pg.evaluate("() => window.__h") == [], f"the moving scroll wrote history: {pg.evaluate('() => window.__h')}"
        assert pg.evaluate("() => window.__ann") == [], f"the moving scroll announced: {pg.evaluate('() => window.__ann')}"
        s = _still(pg)
        pg.wait_for_timeout(800)                      # the landing's quiet window + story-url.js's QUIET window
        lands, H, ann = pg.evaluate("() => window.__lands"), pg.evaluate("() => window.__h"), pg.evaluate("() => window.__ann")
        assert s["rendered"] == 3 and s["dest"] == 3, f"did not land on Dashboard after it stopped: {s}"
        assert [x[1] for x in lands] == ["dashboard"], f"expected one landing once it stopped, got {lands}"
        assert H == [["replaceState", "/#dashboard"]], f"expected one replaceState once it stopped, got {H}"
        assert len(ann) == 1, f"expected one announcement once it stopped, got {ann}"
    finally:
        ctx.close()


def test_reentry_from_price_lands_the_last_hold(browser, site_url):
    """Sol SCRUB-1 HIGH 2 (ICX-HIST.8 for scrub): Price (native, URL /#price), then back up into the last pinned chapter's
    hold: one landing there, one replaceState with its URL, one announcement."""
    ctx, pg = _open(browser, site_url, 390, 664)
    try:
        _still(pg)
        pinned = [d["slug"] for d in pg.evaluate("() => FEStory.destinations") if d["kind"] == "pinned"]
        pg.evaluate("() => scrollTo(0, document.getElementById('price').getBoundingClientRect().top + scrollY - 64)")
        pg.wait_for_timeout(1200)
        assert pg.evaluate("() => location.hash") == "#price", "harness: the spy should have written /#price"
        assert pg.evaluate("() => FEStory.state().phase") == "released"
        pg.evaluate("() => { window.__h.length = 0; window.__ann.length = 0; }")
        pg.evaluate("() => scrollTo(0, __site.scrollFor('end'))")
        s = _still(pg)
        pg.wait_for_timeout(800)
        H, ann = pg.evaluate("() => window.__h"), pg.evaluate("() => window.__ann")
        assert s["rendered"] == 8 and s["beat"] == "end", f"the re-entry did not land on the last pinned: {s}"
        assert H == [["replaceState", "/#" + pinned[-1]]], f"the re-entry from Price: expected one replaceState, got {H}"
        assert pg.evaluate("() => location.hash") == "#" + pinned[-1]
        assert len(ann) == 1, f"the re-entry from Price: expected one announcement, got {ann}"
    finally:
        ctx.close()


def test_theme_switch_carries_a_menu_jump_to_price_through(browser, site_url):
    """Sol SCRUB-1 MEDIUM (ICX-JUMP.5, INT5-fix 3 for scrub): a theme switch while the menu's smooth jump to Price is under
    way rebuilds the story; the scroll still arrives at Price and the jump writes one pushState."""
    ctx, pg = _open(browser, site_url, 390, 664, path="/#dark")
    try:
        pg.evaluate("() => FEStory.goTo('look', {source: 'jump'})")
        _still(pg, 20000)
        pg.wait_for_timeout(800)
        theme0 = pg.evaluate("() => document.documentElement.getAttribute('data-theme')")
        pg.evaluate("() => { window.__h.length = 0; }")
        y0 = pg.evaluate("() => scrollY")
        pg.evaluate("() => FEStoryURL.jump('price')")
        pg.wait_for_timeout(250)                      # the smooth scroll is under way
        mid = pg.evaluate("() => scrollY")
        assert pg.evaluate(PRICE_TOP) > 300, "harness: the smooth scroll had already arrived"
        # a tap on the toggle: its touchstart (Sol SCRUB-2: a tap must not cancel the carry-through), then the click
        pg.evaluate("() => { const t = document.querySelector('[data-theme-toggle]');"
                    " t.dispatchEvent(new TouchEvent('touchstart', {bubbles: true, cancelable: true}));"
                    " t.dispatchEvent(new TouchEvent('touchend', {bubbles: true, cancelable: true})); t.click(); }")
        pg.wait_for_timeout(4000)
        top = pg.evaluate(PRICE_TOP)
        H = pg.evaluate("() => window.__h")
        assert pg.evaluate("() => document.documentElement.getAttribute('data-theme')") != theme0, "harness: the toggle never switched"
        assert mid > y0, "harness: the native scroll had not started"
        assert -4 <= top <= 200, f"the menu jump stopped mid-way after the theme switch (Price at {top:.0f}px); writes {H}"
        assert H == [["pushState", "/#price"]], f"one push for the jump, at its arrival; saw {H}"
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
