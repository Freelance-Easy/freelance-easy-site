"""C5 (DEC-8, ICX-STEP.2-.4): the story's dead time is cut, its motion is not.

- every step's transition <= 1.5 s, gesture -> caption <= 0.7 s, content <= 5 s, except the NAMED exceptions in
  scripts/checks/timing.py (each pinned here at its own number), and the Ride 1.45 s +- 0.1 s;
- the timeline is C5's table on wider stages, the 10-10 table on phones, and `?pace=before` (Daniel's live A/B) is the
  base 67f6b3a's table exactly;
- test_no_motion_faster: every segment has as many moving frames (60 fps of story, a frame that differs from the one
  before) as on the base 67f6b3a, so no move plays faster or slower: only still frames were cut;
- test_dip_fades_band: a dip whose cut turns the Ride's band on fades it with the stage, never one frame's flip.
"""
from __future__ import annotations

import pathlib
import sys

import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "checks"))
import timing  # noqa: E402

WIDTH = {"desktop": 1440, "tablet": 820, "phone": 390}
CELLS = [("desktop", "dark"), ("desktop", "light"), ("tablet", "dark"), ("tablet", "light")]

# 67f6b3a (tests/story/test_segment_order.py's BASE, the 7ae00f7 timeline): what ?pace=before must play
BEFORE = {
    "dark": "make:0-4.92 makeLook:4.92-6.18 look:6.18-11.13 lookKnow:11.13-11.63 know:11.63-15.08 knowGrow:15.08-15.7 grow:15.7-17.46 ride:17.46-18.91 chase:18.91-24.96 chaseYours:24.96-25.86 yours:25.86-26.46 yoursPrice:26.46-27.71 price:27.71-28.31 priceBrand:28.31-29.61 brand:29.61-30.61",
    "light": "make:0-4.51 makeLook:4.51-5.27 look:5.27-10.22 lookKnow:10.22-10.72 know:10.72-14.17 knowGrow:14.17-14.79 grow:14.79-16.55 ride:16.55-18 chase:18-24.05 chaseYours:24.05-24.95 yours:24.95-25.55 yoursPrice:25.55-26.8 price:26.8-27.4 priceBrand:27.4-28.7 brand:28.7-29.7",
}
# C5: Email -0.78 s (three still spans), Yours -0.30, Yours->Price -0.49, Price -0.28, Price->Brand -0.43 (still tails)
AFTER = {
    "dark": "make:0-4.92 makeLook:4.92-6.18 look:6.18-11.13 lookKnow:11.13-11.63 know:11.63-15.08 knowGrow:15.08-15.7 grow:15.7-17.46 ride:17.46-18.91 chase:18.91-24.18 chaseYours:24.18-25.08 yours:25.08-25.38 yoursPrice:25.38-26.14 price:26.14-26.46 priceBrand:26.46-27.33 brand:27.33-28.33",
    "light": "make:0-4.51 makeLook:4.51-5.27 look:5.27-10.22 lookKnow:10.22-10.72 know:10.72-14.17 knowGrow:14.17-14.79 grow:14.79-16.55 ride:16.55-18 chase:18-23.27 chaseYours:23.27-24.17 yours:24.17-24.47 yoursPrice:24.47-25.23 price:25.23-25.55 priceBrand:25.55-26.42 brand:26.42-27.42",
}
TABLET_END = {"dark": "chase:18.91-24.18", "light": "chase:18-23.27"}
# phones keep the 10-10 timeline (PLAN Decision log 2026-10-15)
PHONE = {
    "dark": "make:0-3.6 makeEnd:3.6-4.92 makeLook:4.92-6.18 look:6.18-11.13 lookKnow:11.13-11.63 know:11.63-15.08 knowGrow:15.08-15.7 grow:15.7-17.46 ride:17.46-18.91 chase:18.91-24.96 chaseYours:24.96-25.86 yours:25.86-26.46 yoursOffer:26.46-27.71 end:27.71-27.77",
    "light": "make:0-3.6 makeEnd:3.6-4.51 makeLook:4.51-5.27 look:5.27-10.22 lookKnow:10.22-10.72 know:10.72-14.17 knowGrow:14.17-14.79 grow:14.79-16.55 ride:16.55-18 chase:18-24.05 chaseYours:24.05-24.95 yours:24.95-25.55 yoursOffer:25.55-26.8 end:26.8-26.86",
}
# moving frames per segment on the base 67f6b3a (timing.moving_frames, Chromium)
_WIDE = {"look": 238, "lookKnow": 24, "know": 152, "knowGrow": 37, "grow": 67, "ride": 85, "chase": 296,
         "chaseYours": 43, "yours": 1, "yoursPrice": 28, "price": 1, "priceBrand": 31, "brand": 1}
MOVING = {
    ("desktop", "dark"): {"make": 288, "makeLook": 74, **_WIDE},
    ("desktop", "light"): {"make": 263, "makeLook": 44, **_WIDE},
    ("phone", "dark"): {"make": 211, "makeEnd": 77, "makeLook": 74, "look": 238, "lookKnow": 24, "know": 150,
                        "knowGrow": 37, "grow": 57, "ride": 85, "chase": 304, "chaseYours": 43, "yours": 1,
                        "yoursOffer": 21, "end": 1},
}
FRAME_TOL = 2
# each named exception at its own number (+ 0.02 s): a drift past it is a new decision, not a pass
EXCEPTION_AT = {("transition", "look"): {"dark": 2.58, "light": 1.67}, ("caption", "chase"): 1.39, ("content", "chase"): 5.25}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _open(browser, site_url, layout, theme, query=""):
    return timing.open_story(browser, site_url + "/" + query, WIDTH[layout], theme)


def _segs(page) -> str:
    return page.evaluate("() => window.__site.map().segs.map(s => `${s.id}:${s.T0}-${s.T1}`).join(' ')")


@pytest.mark.parametrize("layout,theme", CELLS, ids=[f"{a}-{b}" for a, b in CELLS])
def test_budgets(browser, site_url, layout, theme):
    ctx, page = _open(browser, site_url, layout, theme)
    try:
        rows = timing.steps(page.evaluate("() => window.__site.map()"))
    finally:
        ctx.close()
    assert not timing.verdicts(rows), timing.verdicts(rows)
    for r in rows:
        for kind in timing.LIMIT:
            at = EXCEPTION_AT.get((kind, r["to"]))
            if at is not None and r[kind] > timing.LIMIT[kind]:
                lim = at[theme] if isinstance(at, dict) else at
                assert r[kind] <= lim + 0.02, f"{r['step']} {kind} {r[kind]:.2f} s: past its named exception ({lim} s)"


@pytest.mark.parametrize("layout,theme", CELLS + [("phone", "dark"), ("phone", "light")],
                         ids=[f"{a}-{b}" for a, b in CELLS + [("phone", "dark"), ("phone", "light")]])
def test_segments_equal_c5_table(browser, site_url, layout, theme):
    want = {"desktop": AFTER[theme], "phone": PHONE[theme],
            "tablet": AFTER[theme].split(" chaseYours")[0].rsplit(" ", 1)[0] + " " + TABLET_END[theme]}[layout]
    ctx, page = _open(browser, site_url, layout, theme)
    try:
        got = _segs(page)
    finally:
        ctx.close()
    assert got == want, f"timeline changed from C5's table:\n got  {got}\n want {want}"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_pace_before_is_the_base(browser, site_url, theme):
    """Daniel's live A/B: /?pace=before plays 67f6b3a's timeline exactly, and writes no storage."""
    ctx, page = _open(browser, site_url, "desktop", theme, "?pace=before")
    try:
        got = _segs(page)
        sw = page.evaluate("() => window.__site.map().switches.find(s => s[0] === 'look')[1]")
        keys = page.evaluate("() => Object.keys(localStorage).sort().join(',')")
    finally:
        ctx.close()
    assert got == BEFORE[theme]
    assert sw == round(float(BEFORE[theme].split("makeLook:")[1].split("-")[0]) + 0.3, 3), "the look caption is the base's"
    assert keys == "fe-theme", f"?pace=before wrote storage: {keys}"


@pytest.mark.parametrize("layout,theme", sorted(MOVING), ids=[f"{a}-{b}" for a, b in sorted(MOVING)])
def test_no_motion_faster(browser, site_url, layout, theme):
    """ICX-STEP.2: each segment's moving part keeps the base's duration (moving frames +- 2): cuts took still frames only."""
    ctx, page = _open(browser, site_url, layout, theme)
    try:
        got = timing.moving_frames(page, page.evaluate("() => window.__site.map()"))
    finally:
        ctx.close()
    base = MOVING[(layout, theme)]
    assert set(got) == set(base), f"segments differ: {sorted(got)} vs {sorted(base)}"
    off = {k: (got[k], base[k]) for k in base if abs(got[k] - base[k]) > FRAME_TOL}
    assert not off, f"moving frames (got, base 67f6b3a) changed: {off}"


def test_dip_fades_band(browser, site_url):
    """Tablet, Make -> End key -> one dip to Email: the band arrives faded with the stage, never at full in one frame."""
    ctx, page = _open(browser, site_url, "tablet", "dark")
    try:
        page.wait_for_function("() => window.__site.state().phase === 'rest'", timeout=20000)
        page.mouse.move(410, 400)
        page.evaluate("""() => { window.__dipRec = []; const band = document.querySelector('.pin-band');
          const sw = document.querySelector('.stage-wrap'); const t0 = performance.now();
          const f = () => { const cs = getComputedStyle(band);
            window.__dipRec.push([cs.display, +cs.opacity, +getComputedStyle(sw).opacity, window.__site.state().phase]);
            if (performance.now() - t0 < 700) requestAnimationFrame(f); }; requestAnimationFrame(f); }""")
        page.keyboard.press("End")
        page.wait_for_timeout(900)
        rec = page.evaluate("() => window.__dipRec")
    finally:
        ctx.close()
    assert any(r[3] == "dip" for r in rec), "no dip played"
    shown = [r for r in rec if r[0] != "none"]
    assert shown, "the band never came on"
    first = shown[0]
    assert first[3] == "dip" and first[1] <= 0.3, f"the band came on at opacity {first[1]} ({first[3]}): a one-frame flip"
    for d, a, s, ph in shown:
        if ph == "dip":
            assert a <= s + 0.05, f"band {a} ahead of the stage {s} during the dip"
