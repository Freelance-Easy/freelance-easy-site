"""A theme switch mid-dip never leaves the stage dimmed (INT-4 Sol HIGH / Astra MEDIUM, qa/INT4-sol-1.md).

The theme switch rebuilds the story (fe:themechange -> refresh -> start from a snapshot). A rebuild during a dip (a
distance >= 2 dip, or the back-fade) used to drop the dip without restoring the stage's and the overlay's opacity, so
the story came to rest with the product stage nearly invisible (0.167 measured). At 1440, dark->light and light->dark,
the switch lands in the fade-out and in the fade-in; at rest both layers are back to their rest values (no inline
opacity, computed opacity 1).
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

LAYERS = """() => [document.querySelector('.stage-wrap'), document.querySelector('.pin-over')].map(e =>
  ({ inline: e.style.opacity, computed: getComputedStyle(e).opacity }))"""
# click the theme toggle from inside the page on the first frame of the asked part of the dip: "out" = the fade-out
# (before the cut), "in" = the fade-in (after the cut: the stage's opacity is rising again)
TOGGLE_IN_DIP = """(part) => new Promise((res, rej) => {
  const w = document.querySelector('.stage-wrap'), t0 = performance.now(); let cutAt = null, r0 = FEStory.state().rendered;
  const tick = () => {
    const s = FEStory.state(), op = parseFloat(w.style.opacity || '1');
    if (performance.now() - t0 > 3000) return rej(new Error('no dip seen: ' + JSON.stringify(s)));
    if (s.phase === 'dip') {
      if (cutAt == null && (s.rendered !== r0 || op < 0.05)) cutAt = performance.now();
      const ready = part === 'out' ? op < 0.9 && cutAt == null : cutAt != null && op > 0.05 && op < 0.95;
      if (ready) { document.querySelector('[data-theme-toggle]').click(); return res({ op, phase: s.phase }); }
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.mark.parametrize("part", ["out", "in"])
@pytest.mark.parametrize("move", ["dip", "back"])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_theme_switch_mid_dip_rests_with_full_stage(browser, site_url, theme, move, part):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
    ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{theme}')}}catch(e){{}}")
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        page.wait_for_function("() => window.FEStory && FEStory.phase === 'rest' && FEStory.rendered === 0", timeout=15000)
        page.mouse.move(720, 500)
        if move == "back":                               # REST(look), then one back gesture: the 220 ms back-fade
            page.evaluate("() => FEStory.goTo('look', {source: 'jump'})")
            page.wait_for_function("() => FEStory.phase === 'rest' && FEStory.rendered === 1", timeout=15000)
            page.wait_for_timeout(700)                   # past the dip cooldown
            page.evaluate("(p) => { window.__tog = (" + TOGGLE_IN_DIP + ")(p); window.__tog.catch(() => {}); }", part)
            page.mouse.wheel(0, -100)
        else:                                            # End from REST(make): one dip, distance 8
            page.evaluate("(p) => { window.__tog = (" + TOGGLE_IN_DIP + ")(p); window.__tog.catch(() => {}); }", part)
            page.keyboard.press("End")
        got = page.evaluate("() => window.__tog")
        want = 0 if move == "back" else 8
        page.wait_for_function(f"() => FEStory.phase === 'rest' && FEStory.rendered === {want}", timeout=15000)
        page.wait_for_timeout(300)
        assert page.evaluate("() => document.documentElement.getAttribute('data-theme')") != theme, "the toggle never switched"
        layers = page.evaluate(LAYERS)
        assert all(l["inline"] == "" and l["computed"] == "1" for l in layers), (
            f"theme switch in the dip's fade-{part} ({move}, {theme}, toggled at opacity {got['op']:.2f}): "
            f"at rest the stage / overlay are {layers}, not their rest values")
    finally:
        ctx.close()
