"""FLICKER2 (2026-10-17, Daniel: "still seing that flicker kinda when on a page then pausing for a few seconds then
scrolling again"). Measured: decision #13's content skip, a 220 ms dip through dark to the chapter's rest frame, when a
gesture comes with > CONTENT_FINISH_MAX of the content left (Look 0-4.35 s after landing, Email 0-4.68 s, ...).
?ci-dip=fade | seam are the prototypes for his A/B: the content's frame is held over the stage and crossfades away.

Requirement (main, 2026-10-17): no frame darker than the darker of the two pictures it blends between (stage luminance
per frame), exactly one step, rests on the next chapter, no FREE. Today's dip (no flag) fails the luminance check.
Run: uv run --with pytest --with playwright --with pillow python3 -m pytest tests/checkpoint/test_flicker2.py -q
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

import dipprobe

TOL = 0.02          # Y (0..1): JPEG + the moving cursor
BLEND_MS = {"fade": 220, "seam": 280}   # site.js XF_DUR; today's dip is darkest at 100 ms, inside both


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


# (theme, k, wait): Look 2 s after landing (2.9 s of content left); Email 3 s (2.2 s left; the Ride's exit seam
# follows). Light Look is not a case: today's dip there fades the white paper onto the light page, so luminance cannot
# tell it (measured: no frame darker); light Email can (the blue band).
CASES = [("dark", 1, 2.0), ("dark", 4, 3.0), ("light", 4, 3.0)]


@pytest.mark.parametrize("mode", ["fade", "seam"])
@pytest.mark.parametrize("theme,k,wait", CASES, ids=["dark-look", "dark-email", "light-email"])
def test_content_skip_never_darker(browser, site_url, mode, k, wait, theme):
    ctx, page = dipprobe.open_page(browser, f"{site_url}/?ci-dip={mode}", 1440, 900, theme)
    try:
        tr = dipprobe.run(page, k, wait)
    finally:
        ctx.close()
    blend = BLEND_MS[mode]
    low, floor = tr.window_min(0, blend), tr.floor(blend)
    assert low >= floor - TOL, (
        f"?ci-dip={mode} k={k}: a frame at Y={low:.3f} in the first {blend} ms, darker than the pictures it blends "
        f"(content {tr.pre_y:.3f}, rest {tr.rest_y:.3f}, after {tr.y_at(blend + 30):.3f}): it dipped")
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


def _to_content(browser, site_url, k=1):
    ctx, page = dipprobe.open_page(browser, f"{site_url}/?ci-dip=seam", 1440, 900, "dark")
    if k > 1:
        page.evaluate(f"() => FEStory.goTo({k - 1}, {{source: 'jump'}})")
        page.wait_for_function(f"() => {{ const s = FEStory.state(); return s.phase === 'rest' && s.rendered === {k - 1}; }}", timeout=20000)
        page.wait_for_timeout(900)
    page.evaluate(_WHEEL)
    page.wait_for_function(f"() => {{ const s = FEStory.state(); return s.rendered === {k} && s.step === 'content'; }}", timeout=15000)
    page.wait_for_timeout(600)
    return ctx, page


def test_held_frame_never_shows_through_a_dip(browser, site_url):
    """A jump inside the blend that dips at once: the held frame goes when the dip starts, so
    the dip never fades the stage under a bright copy of the old one."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_COUNT)
        page.evaluate(_WHEEL)
        page.wait_for_timeout(60)
        # inside the blend, back past the origin: a running seam never rushes or reverses there, it dips (decide)
        page.evaluate("() => FEStory.goTo(0, {source: 'jump'})")
        page.wait_for_function("() => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === 0 && s.dest === 0; }", timeout=20000)
        rec = page.evaluate("() => { const r = window.__hf; window.__hf = null; return r; }")
    finally:
        ctx.close()
    t0 = rec[0][0]
    dips = [r for r in rec if r[1] == "dip"]
    assert dips and dips[0][0] - t0 < 250, "harness: no dip inside the blend (the case needs one)"
    held = [r for r in dips if r[2] > 1]
    assert not held, f"{len(held)} dip frames with the held content frame still on the stage"
    assert rec[-1][2] == 1, "the held frame outlived the move"


def test_rebuild_mid_blend_drops_the_held_frame(browser, site_url):
    """A theme switch inside the blend rebuilds the story (resetEngine): the held frame goes with it at once."""
    ctx, page = _to_content(browser, site_url)
    try:
        page.evaluate(_WHEEL)
        page.wait_for_timeout(40)
        n0 = page.evaluate("() => document.querySelectorAll('.stage-wrap').length")
        page.evaluate("() => document.querySelector('[data-theme-toggle]').click()")
        page.wait_for_timeout(120)
        n1 = page.evaluate("() => document.querySelectorAll('.stage-wrap').length")
    finally:
        ctx.close()
    assert n0 == 2, f"harness: the blend's held frame was not up 40 ms in ({n0} stage-wraps)"
    assert n1 == 1, f"{n1} stage-wraps 120 ms after a rebuild mid-blend (the held frame outlived the rebuild)"
