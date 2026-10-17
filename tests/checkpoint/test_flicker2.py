"""FLICKER2 / FADEDEF (2026-10-17, Daniel: "still seing that flicker kinda when on a page then pausing for a few seconds
then scrolling again"; then, of the A/B: "fade feels smoothest"). Decision #13's content skip (a gesture with
> CONTENT_FINISH_MAX of the content left: Look 0-4.35 s after landing, Email 0-4.68 s, ...) is the crossfade by default:
the content's frame is held over the stage and dissolves onto the chapter's rest frame, never through dark; then the
seam. Until FADEDEF it was a 220 ms dip through dark (?ci-dip=fade was the prototype).

Requirement (main, 2026-10-17; Sol FLICKER2-1 #3): no frame darker than the darker of the two pictures it blends (stage
luminance per frame against min(content, rest)); FEStory.state().dip never set and the stage never faded during the
skip (these see a dip on every chapter, which luminance cannot: light Look fades onto the page colour, dark Email onto
the band); exactly one step, rests on the next chapter, no FREE.
Run: uv run --with pytest --with playwright --with pillow python3 -m pytest tests/checkpoint/test_flicker2.py -q
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

import dipprobe

TOL = 0.02          # Y (0..1): JPEG + the moving cursor
BLEND_MS = 220      # site.js XF_DUR


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


# (theme, k, wait, width, height): Look 2 s after landing (2.9 s of content left); Email 3 s (2.2 s left; the Ride's exit
# seam follows); a phone (390 x 664, the real Safari viewport) on Look.
CASES = [("dark", 1, 2.0, 1440, 900), ("light", 1, 2.0, 1440, 900), ("dark", 4, 3.0, 1440, 900),
         ("light", 4, 3.0, 1440, 900), ("dark", 1, 2.0, 390, 664)]
IDS = ["dark-look", "light-look", "dark-email", "light-email", "phone-dark-look"]


@pytest.mark.parametrize("theme,k,wait,width,height", CASES, ids=IDS)
def test_content_skip_crossfades(browser, site_url, theme, k, wait, width, height):
    ctx, page = dipprobe.open_page(browser, f"{site_url}/", width, height, theme)
    try:
        tr = dipprobe.run(page, k, wait, width=width)
    finally:
        ctx.close()
    assert tr.dip_frames == 0, f"k={k}: FEStory.state().dip set on {tr.dip_frames} frames of a content skip (it dipped)"
    assert tr.min_opacity >= 0.999, f"k={k}: the stage faded to opacity {tr.min_opacity:.3f} during a content skip"
    assert tr.held_frames > 0, f"k={k}: no held content frame (no crossfade)"
    low, floor = tr.window_min(0, BLEND_MS), tr.floor()
    assert low >= floor - TOL, (
        f"k={k}: a frame at Y={low:.3f} in the first {BLEND_MS} ms, darker than the pictures it blends "
        f"(content {tr.pre_y:.3f}, rest {tr.rest_y:.3f})")
    assert tr.steps == [k + 1], f"steps {tr.steps}, want exactly [{k + 1}]"
    assert tr.end == ["rest", k + 1, k + 1], f"ended {tr.end}"
    assert not tr.free, "went FREE"


# ---- the held frame's lifetime --------------------------------------------------------------------------------------
_COUNT = r"""() => { const F = window.__hf = []; const tick = () => { if (!window.__hf) return; const s = FEStory.state();
  F.push([performance.now(), s.phase, document.querySelectorAll('.stage-wrap').length]); requestAnimationFrame(tick); };
  requestAnimationFrame(tick); }"""
_WHEEL = r"""() => { const x = innerWidth / 2, y = innerHeight / 2;
  const w = new WheelEvent('wheel', { deltaY: 100, deltaMode: 0, clientX: x, clientY: y, bubbles: true, cancelable: true });
  Object.defineProperty(w, 'wheelDeltaY', { value: -120 }); document.elementFromPoint(x, y).dispatchEvent(w); }"""
_HELD = "() => document.querySelectorAll('.stage-wrap').length"
_TWO_FRAMES = r"""() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => {
  const w = document.querySelectorAll('.stage-wrap'); r([w.length, w.length > 1 ? parseFloat(w[1].style.opacity) : null]); })))"""


def _to_content(browser, site_url, k=1):
    ctx, page = dipprobe.open_page(browser, f"{site_url}/", 1440, 900, "dark")
    if k > 1:
        page.evaluate(f"() => FEStory.goTo({k - 1}, {{source: 'jump'}})")
        page.wait_for_function(f"() => {{ const s = FEStory.state(); return s.phase === 'rest' && s.rendered === {k - 1}; }}", timeout=20000)
        page.wait_for_timeout(900)
    page.evaluate(_WHEEL)
    page.wait_for_function(f"() => {{ const s = FEStory.state(); return s.rendered === {k} && s.step === 'content'; }}", timeout=15000)
    page.wait_for_timeout(600)
    return ctx, page


def test_held_frame_never_shows_through_a_dip(browser, site_url):
    """A back jump inside the crossfade that dips: the held frame goes at once, so the dip never fades the stage under a
    bright copy of the old one."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_COUNT)
        page.evaluate(_WHEEL)
        page.wait_for_timeout(60)
        page.evaluate("() => FEStory.goTo(0, {source: 'jump'})")
        page.wait_for_function("() => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === 0 && s.dest === 0; }", timeout=20000)
        rec = page.evaluate("() => { const r = window.__hf; window.__hf = null; return r; }")
    finally:
        ctx.close()
    dips = [r for r in rec if r[1] == "dip"]
    assert dips, "harness: no dip after the back jump (the case needs one)"
    held = [r for r in dips if r[2] > 1]
    assert not held, f"{len(held)} dip frames with the held content frame still on the stage"
    assert rec[-1][2] == 1, "the held frame outlived the move"


def test_jump_mid_crossfade_drops_the_held_frame_at_once(browser, site_url):
    """(judge FLICKER2 LOW) a rail / menu / Home-End / popstate jump (all FEStory.goTo -> jump) inside the crossfade removes
    the held frame on its next frame, rather than letting it fade on for up to 220 ms over the new move."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_WHEEL)
        page.wait_for_timeout(40)
        n0 = page.evaluate(_HELD)
        page.evaluate("() => FEStory.goTo(4, {source: 'jump'})")
        n1, _ = page.evaluate(_TWO_FRAMES)
        page.wait_for_function("() => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === 4; }", timeout=20000)
    finally:
        ctx.close()
    assert n0 == 2, f"harness: the crossfade's held frame was not up 40 ms in ({n0} stage-wraps)"
    assert n1 == 1, f"{n1} stage-wraps two frames after a jump inside the crossfade (the held frame faded on)"


def test_foreign_scroll_mid_crossfade_drops_the_held_frame_at_once(browser, site_url):
    """A foreign scroll (a scrollbar drag, an anchor) inside the crossfade goes FREE: the held frame goes with it at once."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_WHEEL)
        page.wait_for_timeout(40)
        n0 = page.evaluate(_HELD)
        page.evaluate("() => window.scrollTo({ top: window.scrollY + 1500, behavior: 'instant' })")
        n1, _ = page.evaluate(_TWO_FRAMES)
        phase = page.evaluate("() => FEStory.state().phase")
    finally:
        ctx.close()
    assert n0 == 2, f"harness: the crossfade's held frame was not up 40 ms in ({n0} stage-wraps)"
    assert n1 == 1, f"{n1} stage-wraps two frames after a foreign scroll inside the crossfade (phase {phase})"


def test_content_skip_counts_for_the_dip_cooldown(browser, site_url):
    """(judge FLICKER2 LOW; ICX-DIP.4) the content skip counts as a dip for the cooldown of GESTURE steps: two back steps
    inside the crossfade fade back only once 0.6 s have passed since the skip, never two fades back to back."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_COUNT)
        page.evaluate(_WHEEL)
        page.wait_for_timeout(60)
        page.keyboard.press("ArrowUp")
        page.wait_for_timeout(30)
        page.keyboard.press("ArrowUp")
        assert page.evaluate("() => FEStory.state().dest") == 0, "harness: two back steps did not set dest 0"
        page.wait_for_function("() => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === 0; }", timeout=20000)
        rec = page.evaluate("() => { const r = window.__hf; window.__hf = null; return r; }")
    finally:
        ctx.close()
    held = [r[0] for r in rec if r[2] > 1]
    dips = [r[0] for r in rec if r[1] == "dip"]
    assert held and dips, "harness: the case needs a crossfade and then a dip"
    gap = dips[0] - held[0]
    assert gap >= 560, f"the back dip started {gap:.0f} ms after the content skip (cooldown 600 ms)"


_JUMP_NOW = r"""(k) => new Promise((r) => { FEStory.goTo(k, {source: 'jump'}); const s0 = FEStory.state().phase;
  requestAnimationFrame(() => r([s0, FEStory.state().phase, document.querySelectorAll('.stage-wrap').length])); })"""


@pytest.mark.parametrize("k", [4, 0], ids=["far-forward", "back"])
def test_jump_mid_crossfade_starts_at_once(browser, site_url, k):
    """(main's ruling 2026-10-17, "feel instant") a rail / menu / Home-End / popstate jump (FEStory.goTo, as rail.js
    calls it) ~100 ms into a Look skip's crossfade starts its own transition (the dip) in the same frame: the skip's
    cooldown holds gesture steps only."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_WHEEL)
        page.wait_for_timeout(100)
        n0 = page.evaluate(_HELD)
        p0, p1, n1 = page.evaluate(_JUMP_NOW, k)
        page.wait_for_function(f"() => {{ const s = FEStory.state(); return s.phase === 'rest' && s.rendered === {k}; }}", timeout=20000)
    finally:
        ctx.close()
    assert n0 == 2, f"harness: the crossfade's held frame was not up 100 ms in ({n0} stage-wraps)"
    assert p0 == "dip" and p1 == "dip", f"the jump's dip did not start at once: phase {p0} at the jump, {p1} a frame later"
    assert n1 == 1, "the held frame outlived the jump"


def test_release_mid_crossfade_drops_the_held_frame_at_once(browser, site_url):
    """A scroll past the story's end inside the crossfade releases the pin (setReleased): the held frame goes at once."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_WHEEL)
        page.wait_for_timeout(40)
        n0 = page.evaluate(_HELD)
        page.evaluate("() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' })")
        n1, _ = page.evaluate(_TWO_FRAMES)
        phase = page.evaluate("() => FEStory.state().phase")
    finally:
        ctx.close()
    assert n0 == 2, f"harness: the crossfade's held frame was not up 40 ms in ({n0} stage-wraps)"
    assert phase == "released", f"harness: the scroll did not release the pin (phase {phase})"
    assert n1 == 1, f"{n1} stage-wraps two frames after a release inside the crossfade"


def test_content_skip_resyncs_the_scroll(browser, site_url):
    """(judge FLICKER2 LOW) the skip re-syncs scrollY to the chapter's track position, as the dip's cut does: a 1 px
    drift inside the landing's acknowledged window (ICX-SETTLE-1) is put right by the skip."""
    ctx, page = dipprobe.open_page(browser, f"{site_url}/", 1440, 900, "dark")
    try:
        page.evaluate("() => { window.__drift = null; FEStory.onLand((p) => { if (p.index === 1 && p.final) {"
                      " window.scrollTo({ top: window.scrollY + 1, behavior: 'instant' }); window.__drift = window.scrollY; } }); }")
        page.evaluate(_WHEEL)
        page.wait_for_function("() => { const s = FEStory.state(); return s.rendered === 1 && s.step === 'content'; }", timeout=15000)
        page.wait_for_timeout(1000)
        before = page.evaluate("() => [window.scrollY, FEStory.state().trackY, FEStory.state().phase]")
        page.evaluate(_WHEEL)
        after = page.evaluate("() => new Promise((r) => requestAnimationFrame(() => r([window.scrollY, FEStory.state().trackY, document.querySelectorAll('.stage-wrap').length])))")
    finally:
        ctx.close()
    assert before[2] != "free" and abs(before[0] - before[1]) >= 0.5, f"harness: no drift survived into the content {before}"
    assert after[2] == 2, "harness: no crossfade"
    # state().trackY follows dest (now k + 1); the skip re-syncs to the rendered chapter's position, before[1]
    assert abs(after[0] - before[1]) < 0.5, f"scrollY {after[0]} vs Look's track {before[1]} after the skip: not re-synced"


_HIDE = r"""() => { window.__rafQ = []; window.__raf0 = window.requestAnimationFrame;
  window.requestAnimationFrame = (f) => { window.__rafQ.push(f); return 1; };   // a hidden tab runs no frames
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
  document.dispatchEvent(new Event('visibilitychange'));
  const w = document.querySelectorAll('.stage-wrap'); return w.length > 1 ? parseFloat(w[1].style.opacity) : null; }"""
_SHOW = r"""() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
  window.requestAnimationFrame = window.__raf0; document.dispatchEvent(new Event('visibilitychange'));
  const q = window.__rafQ; window.__rafQ = []; for (const f of q) requestAnimationFrame(f);
  return new Promise((r) => requestAnimationFrame(() => {             // the first visible frame (after the queued tick)
    const w = document.querySelectorAll('.stage-wrap'); r([w.length, w.length > 1 ? parseFloat(w[1].style.opacity) : null]); })); }"""


def test_hidden_tab_mid_crossfade_resumes_it(browser, site_url):
    """(Sol FLICKER2-1 #2, ICX-HIDDEN "time stops") a tab hidden inside the crossfade and shown again later continues the
    crossfade from where it paused: the held frame is still up, about as opaque as when the tab was hidden."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_WHEEL)
        page.wait_for_timeout(50)
        a0 = page.evaluate(_HIDE)
        page.wait_for_timeout(600)                     # longer than the whole crossfade
        n1, a1 = page.evaluate(_SHOW)
        page.wait_for_function("() => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === 2; }", timeout=20000)
        n2 = page.evaluate(_HELD)
    finally:
        ctx.close()
    assert a0 is not None and a0 > 0.3, f"harness: the held frame was not up when the tab hid (opacity {a0})"
    assert n1 == 2 and a1 is not None, "back from a hidden tab mid-crossfade, the held frame dropped at once (a cut)"
    assert a1 >= a0 - 0.2, f"the crossfade jumped ahead while hidden: opacity {a0:.2f} at hide, {a1:.2f} on the first visible frame"
    assert n2 == 1, "the held frame outlived the move"


def test_rebuild_mid_blend_drops_the_held_frame(browser, site_url):
    """A theme switch inside the crossfade rebuilds the story (resetEngine): the held frame goes with it at once."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_WHEEL)
        page.wait_for_timeout(40)
        n0 = page.evaluate(_HELD)
        page.evaluate("() => document.querySelector('[data-theme-toggle]').click()")
        page.wait_for_timeout(120)
        n1 = page.evaluate(_HELD)
    finally:
        ctx.close()
    assert n0 == 2, f"harness: the crossfade's held frame was not up 40 ms in ({n0} stage-wraps)"
    assert n1 == 1, f"{n1} stage-wraps 120 ms after a rebuild mid-blend (the held frame outlived the rebuild)"
