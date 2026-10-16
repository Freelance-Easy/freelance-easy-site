"""C5b-test: the per-frame deadline guard in site.js rebuildFrame() is what keeps an old-palette scene out of the circle.

On a fast machine the chunked mounting finishes before the circle arrives, so the guard never fires and a plain
"nothing drew over the old scenes" test passes with the guard removed. Here the page is made to fall behind on purpose:
the CPU is throttled, and once the rebuild is in flight a long task blocks the main thread, so the next frame lands
(in animation time) after the circle could already have reached the stage. At that frame the guard must finish the
rebuild BEFORE the paint. The probe is a read-only observer plus the stall; it samples the circle's radius at the
frames that were drawn while the old scenes were still on the stage.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

PROBE = r"""
async (stallMs) => {
  const stg = document.querySelector('[data-stage=story]'), ovr = document.querySelector('.pin-over');
  const btn = document.querySelector('[data-theme-toggle]');
  const html = document.documentElement;
  const olds = [...stg.children].filter((e) => e.classList.contains('fx-root') && !e.classList.contains('fx-seam'));
  const br = btn.getBoundingClientRect();
  let x = br.left + br.width / 2, y = br.top + br.height / 2;
  const ease = (p) => {                       // cubic-bezier(.55,0,.25,1), solved by bisection (theme.js's reveal curve)
    let lo = 0, hi = 1, t = p;
    for (let i = 0; i < 40; i++) { t = (lo + hi) / 2; const bx = 3 * (1 - t) * (1 - t) * t * 0.55 + 3 * (1 - t) * t * t * 0.25 + t * t * t; if (bx < p) lo = t; else hi = t; }
    return 3 * (1 - t) * t * t * 1 + t * t * t;
  };
  // frames are judged in the ResizeObserver step: after every rAF callback (the site's guard included) and before the
  // paint, so what it sees is what that frame paints
  const probe = document.createElement('div');
  probe.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;pointer-events:none';
  document.body.appendChild(probe);
  const paints = [];
  let swapped = false, swapAt = -1, stalled = false, ticks = 0, t0 = 0;
  const ro = new ResizeObserver(() => { if (t0) paints.push({ t: performance.now() - t0, olds: olds.some((e) => e.isConnected) }); });
  ro.observe(probe);
  const mo = new MutationObserver(() => { if (!swapped && olds.some((e) => !e.isConnected)) { swapped = true; swapAt = performance.now() - t0; } });
  mo.observe(stg, { childList: true });
  t0 = performance.now();
  btn.click();
  const vx = parseFloat(html.style.getPropertyValue('--vt-x')), vy = parseFloat(html.style.getPropertyValue('--vt-y'));
  if (Number.isFinite(vx) && Number.isFinite(vy)) { x = vx; y = vy; }
  let dist = Infinity;
  for (const el of [stg, ...ovr.children]) {
    const b = el.getBoundingClientRect();
    if (b.width && b.height) dist = Math.min(dist, Math.hypot(Math.max(b.left - x, 0, x - b.right), Math.max(b.top - y, 0, y - b.bottom)));
  }
  const end = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)) + 222;
  let reach = 0;                                // ms after the click at which the circle's edge could first touch the stage / a card
  while (reach < 420 && ease(reach / 420) * end < dist) reach += 4;
  await new Promise((done) => {
    const tick = () => {
      ticks++;
      probe.style.width = (ticks % 2 ? 2 : 1) + 'px';                 // the ResizeObserver fires for this frame
      // the rebuild is in flight after the second frame: stall once, so the next frame arrives long after `reach`
      if (!stalled && !swapped && ticks === 3) {
        stalled = true;
        setTimeout(() => { const s = performance.now(); while (performance.now() - s < stallMs) { /* busy */ } }, 0);
      }
      if (performance.now() - t0 > 2500 || (swapped && !html.classList.contains('vt-theme'))) done();
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
  ro.disconnect(); mo.disconnect(); probe.remove();
  return { dist: Math.round(dist), reach, swapped, swapAt: Math.round(swapAt), stalled,
    paints: paints.map((p) => [Math.round(p.t), p.olds]),
    roots: stg.querySelectorAll(':scope > .fx-root:not(.fx-seam)').length };
}
"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.mark.parametrize("width,height", [(390, 664), (1440, 900)])
def test_deadline_guard_finishes_the_rebuild_before_a_late_frame_paints(site_url, browser, width, height):
    ctx = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="no-preference")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(site_url + "/#dark", wait_until="load")
        page.wait_for_function("() => window.__site && window.__site.TL", timeout=8000)
        page.wait_for_timeout(300)
        n = page.evaluate("() => document.querySelectorAll('[data-stage=story] > .fx-root:not(.fx-seam)').length")
        assert n > 0
        cdp = ctx.new_cdp_session(page)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 6})
        for leg in ("first", "back"):      # dark -> light, then light -> dark
            r = page.evaluate(PROBE, 300)
            where = f"{leg} @ {width}: {r}"
            assert r["stalled"], f"the stall never ran ({where})"
            assert r["swapped"], f"the scenes were never swapped ({where})"
            # a frame painted after the circle could have reached the stage (60 ms allowed for the rebuild's own start
            # after the click) must not show the old scenes: the guard finished the rebuild before that paint
            late = [p for p in r["paints"] if p[0] - 60 >= r["reach"]]
            assert late, f"no frame was painted after the circle's reach ({where})"
            bad = [p for p in late if p[1]]
            assert not bad, f"{leg}: frames at {[p[0] for p in bad]} ms painted the old scenes after the circle could reach the stage ({r['reach']} ms): {where}"
            assert r["roots"] == n, f"{leg}: {r['roots']} scene roots after the switch, expected {n}"
            page.wait_for_timeout(300)
        assert errors == [], errors
    finally:
        ctx.close()
