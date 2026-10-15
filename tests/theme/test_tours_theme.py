"""A6: the two tours (/tour/ and /tour/quick/) switch theme through FETheme (A5), and the app frame follows.

- test_inner_frame_follows: one press runs FETheme's circle, and on every frame of that reveal the iframe (the
  released app) already carries the new theme with its final colours, as does the page around it: no late fade
  (proto.js / quick.js used a 300 ms class fade in the frame; the pages have a 240 ms colour transition).
- test_compound_hash_kept: #light&reduced&<chapter> keeps every flag, in order, after a toggle (only the theme flag
  is rewritten) and the frame follows.
- test_reduced_instant: under reduced motion (the OS setting or the tour's #reduced flag) a press switches page and
  frame at once, with no circle.
The reveal itself (timing, mask, centre) is scripts/checks/check_theme_reveal.py's job.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

PAGES = ["/tour/", "/tour/quick/"]
PAUSE = {"/tour/": "window.__tour && window.__tour.pause()", "/tour/quick/": "window.__tourQuick && window.__tourQuick.pause()"}

# One press, followed frame by frame while the circle runs: the theme of the page and of the app frame, and the
# colours of the page body and the frame's elements (the same element objects at the end, so a re-rendered screen
# is never compared against itself)
PROBE_JS = r"""
async () => {
  const root = document.documentElement;
  const fdoc = document.getElementById("app-frame").contentDocument;
  const els = [document.body, document.querySelector(".frame-top"), fdoc.body,
               ...fdoc.querySelectorAll("#screen *")].filter(Boolean).slice(0, 400);
  const colours = (list) => list.map((el) => {
    if (!el.isConnected) return null;
    const s = el.ownerDocument.defaultView.getComputedStyle(el);
    return [s.backgroundColor, s.color, s.borderTopColor].join("|");
  });
  const isReveal = (a) => a.effect && a.effect.pseudoElement === "::view-transition-new(root)" &&
    a.effect.getKeyframes().some((k) => "--vt-r" in k);
  const out = { before: root.getAttribute("data-theme"), frames: [] };
  document.querySelector("[data-theme-toggle]").click();
  out.syncPage = root.getAttribute("data-theme");
  out.syncFrame = fdoc.documentElement.getAttribute("data-theme");
  const t0 = performance.now();
  let anim = null;
  await new Promise((done) => {
    const tick = () => {
      anim = anim || document.getAnimations().find(isReveal) || null;
      if (anim && anim.playState === "running") {
        out.frames.push({ page: root.getAttribute("data-theme"),
                          frame: fdoc.documentElement.getAttribute("data-theme"), colours: colours(els) });
      }
      const settled = anim && anim.playState !== "running" && !root.classList.contains("vt-theme");
      if (settled || performance.now() - t0 > 2000 || (!anim && performance.now() - t0 > 700)) done();
      else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
  out.found = !!anim;
  await new Promise((r) => setTimeout(r, 700));   // longer than any colour transition (the old 300 ms fade, 240 ms)
  out.after = root.getAttribute("data-theme");
  out.afterFrame = fdoc.documentElement.getAttribute("data-theme");
  out.final = colours(els);
  out.vtClass = root.classList.contains("vt-theme");
  return out;
}
"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def open_tour(browser, url, *, reduced=False, width=1440):
    ctx = browser.new_context(viewport={"width": width, "height": 900},
                              reduced_motion="reduce" if reduced else "no-preference")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    # the released app is in the frame once its first screen is installed
    page.wait_for_function("""() => { const f = document.getElementById('app-frame');
        const d = f && f.contentDocument; const s = d && d.getElementById('screen');
        return !!(s && s.children.length); }""", timeout=5000)
    page.wait_for_timeout(400)
    return ctx, page, errors


def themes(page):
    return page.evaluate("""() => [document.documentElement.getAttribute('data-theme'),
        document.getElementById('app-frame').contentDocument.documentElement.getAttribute('data-theme')]""")


@pytest.mark.parametrize("path", PAGES)
def test_inner_frame_follows(browser, site_url, path):
    ctx, page, errors = open_tour(browser, site_url + path)
    try:
        page.evaluate(PAUSE[path])   # a still screen, so any colour change is the theme's
        page.wait_for_timeout(100)
        for leg in ("first", "back"):
            p = page.evaluate(PROBE_JS)
            flipped = {"dark": "light", "light": "dark"}[p["before"]]
            assert p["found"], f"{leg}: no FETheme circle reveal on {path}"
            assert p["frames"], f"{leg}: the reveal ran no frames"
            for i, f in enumerate(p["frames"]):
                assert f["page"] == flipped and f["frame"] == flipped, \
                    f"{leg}: reveal frame {i}: page {f['page']!r}, app frame {f['frame']!r}, expected {flipped!r}"
                late = [k for k, (a, b) in enumerate(zip(f["colours"], p["final"])) if a and b and a != b]
                assert not late, (f"{leg}: reveal frame {i}: {len(late)} elements still fading "
                                  f"(first: #{late[0]} {f['colours'][late[0]]} -> {p['final'][late[0]]})")
            assert p["after"] == flipped and p["afterFrame"] == flipped and not p["vtClass"]
        assert errors == [], errors
    finally:
        ctx.close()


@pytest.mark.parametrize("path", PAGES)
def test_compound_hash_kept(browser, site_url, path):
    ctx, page, errors = open_tour(browser, site_url + path + "#light&reduced&email")
    try:
        assert themes(page) == ["light", "light"]
        for want, flag in (("dark", "#dark&reduced&email"), ("light", "#light&reduced&email")):
            page.click("[data-theme-toggle]")
            page.wait_for_function("() => !document.documentElement.classList.contains('vt-theme')", timeout=3000)
            page.wait_for_timeout(100)
            assert page.evaluate("() => location.hash") == flag
            assert themes(page) == [want, want]
            assert page.evaluate("() => localStorage.getItem('fe-theme')") == want
        assert errors == [], errors
    finally:
        ctx.close()


@pytest.mark.parametrize("how", ["os", "hash"])
@pytest.mark.parametrize("path", PAGES)
def test_reduced_instant(browser, site_url, path, how):
    url = site_url + path + ("#reduced" if how == "hash" else "")
    ctx, page, errors = open_tour(browser, url, reduced=how == "os")
    try:
        before = themes(page)[0]
        flipped = {"dark": "light", "light": "dark"}[before]
        p = page.evaluate("""() => {
            const fdoc = document.getElementById('app-frame').contentDocument;
            document.querySelector('[data-theme-toggle]').click();
            return { page: document.documentElement.getAttribute('data-theme'),
                     frame: fdoc.documentElement.getAttribute('data-theme'),
                     vt: document.documentElement.classList.contains('vt-theme'),
                     fading: fdoc.documentElement.classList.contains('theme-transitioning') }; }""")
        assert p == {"page": flipped, "frame": flipped, "vt": False, "fading": False}, p
        page.wait_for_timeout(100)
        assert page.evaluate("""() => document.getAnimations().some(a => a.effect &&
            String(a.effect.pseudoElement || '').startsWith('::view-transition'))""") is False
        assert errors == [], errors
    finally:
        ctx.close()
