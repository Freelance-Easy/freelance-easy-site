"""REVEAL (2026-10-17): on "/", nothing but the circle starts with a theme switch.

The circle's start budget is 50 ms (check_theme_reveal --max-start-ms 50; Daniel's "feel instant"). A view-transition
reveal already needs three frames: the old snapshot, the new snapshot, then the circle's first frame. At 35efe14 the flip
also started ~40 CSS transitions in the new view (header and rail link colours, the buttons' backgrounds and shadows, and
17 opacity transitions on the rail's tick marks, whose --nav-a0 differs per theme). The opacity ones run on the
compositor, and Chromium holds every main-thread animation started in the same frame (the circle included) until the
compositor reports their start: one frame late. The colour ones repaint the new view every frame under the circle. Both
pushed the start at 1440 past 50 ms in about half the runs (median 46-62 ms over 5 runs at load ~5; 390, with no rail,
stayed under). They are not needed for the circle's first frame: the circle reveals the new theme's final colours.

Deterministic: count the animations, other than the circle, that the switch started, sampled at the frame where the
circle appears, both directions, desktop and phone width. Read-only besides the toggle click.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

PROBE = r"""
async () => {
  const btn = document.querySelector('[data-theme-toggle]');
  btn.scrollIntoView({ block: 'nearest' });
  const isReveal = (a) => a.effect && a.effect.pseudoElement === '::view-transition-new(root)' &&
    a.effect.getKeyframes().some((k) => '--vt-r' in k);
  const name = (a) => {
    const t = a.effect && a.effect.target;
    const who = t ? t.tagName.toLowerCase() + (typeof t.className === 'string' && t.className.trim() ? '.' + t.className.trim().split(/\s+/)[0] : '') : '?';
    return `${a.constructor.name} ${who}${(a.effect && a.effect.pseudoElement) || ''} ${a.transitionProperty || a.animationName || ''}`;
  };
  const stale = new Set(document.getAnimations());
  const t0 = performance.now();
  btn.click();
  let out = null;
  await new Promise((done) => {
    const tick = () => {
      const fresh = document.getAnimations().filter((a) => !stale.has(a));
      const circle = fresh.find(isReveal);
      if (circle) out = { found: true, others: fresh.filter((a) => a !== circle).map(name) };
      if (out || performance.now() - t0 > 1500) done(); else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
  // let the reveal finish before the next leg
  await new Promise((done) => {
    const wait = () => (document.documentElement.classList.contains('vt-theme') ? setTimeout(wait, 30) : done());
    setTimeout(wait, 30);
  });
  return out || { found: false, others: [] };
}
"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
def test_only_the_circle_starts_with_the_switch(site_url, browser, width, height):
    ctx = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="no-preference")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(site_url + "/", wait_until="load")
        page.wait_for_function("() => window.__site && window.__site.TL", timeout=8000)
        page.wait_for_timeout(300)
        for leg in ("first", "back"):
            before = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            r = page.evaluate(PROBE)
            assert r["found"], f"{leg} @ {width}: no circle reveal"
            assert r["others"] == [], (
                f"{leg} @ {width} ({before} ->): the switch started {len(r['others'])} animations besides the circle, "
                f"each a frame's work under it (composited ones delay the circle's start by a frame): {r['others'][:12]}")
            page.wait_for_timeout(150)
        assert errors == [], errors
    finally:
        ctx.close()
