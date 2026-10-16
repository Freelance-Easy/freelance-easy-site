"""C4-engine cross-piece checks (B5 + B6 judges): ONE rail click (1440) and ONE menu-sheet tap (390) each add exactly one
history entry, for a pinned row and for a native row, and Back returns the reader to where they were (ICX-HIST.2/.3,
ICX-JUMP.4/.5). The rail and the sheet both jump through story-url.js's FEStoryURL.jump; this file proves the whole
path from a real click.

pushState / replaceState are spied from before the page's scripts run. Never a real download link.

Run: uv run --with pytest --with playwright python3 -m pytest tests/nav/test_nav_history.py -q
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

SPY = """(() => { window.__h = [];
  for (const k of ['pushState', 'replaceState']) { const o = history[k];
    history[k] = function (s, t, u) { window.__h.push([k, u == null ? null : String(u)]); return o.apply(this, arguments); }; }
})();"""
REST = "(i) => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === i && s.dest === i; }"
PICK = """(want) => {
  const d = FEStory.destinations, r = FEStory.state().rendered ?? 0;
  if (want === 'pinned') { for (let i = d.length - 1; i >= 0; i--) if (d[i].kind === 'pinned' && Math.abs(i - r) >= 2) return i; }
  else { for (let i = 0; i < d.length; i++) if (d[i].kind === 'native' && i > 0) return i; }
  return -1;
}"""
AT_SECTION = """(a) => { const r = document.getElementById(a).getBoundingClientRect();
  const hh = document.querySelector('.site-header').getBoundingClientRect().height; return Math.abs(r.top - hh) <= 4; }"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _open(browser, site_url, w, h, reduce=False, phone=False):
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce" if reduce else "no-preference",
                              has_touch=phone, is_mobile=phone)
    ctx.add_init_script("try { localStorage.setItem('fe-theme', 'dark'); } catch (e) {}")
    ctx.add_init_script(SPY)
    page = ctx.new_page()
    errs: list[str] = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(site_url + "/", wait_until="load")
    page.wait_for_function("() => window.FEStory && window.FEStoryURL && document.documentElement.classList.contains('fx-ready')",
                           timeout=10000)
    if not reduce:
        page.wait_for_function(REST, arg=0, timeout=15000)
    page.wait_for_timeout(1300)        # past the load's own settle (story-url.js `initializing`)
    page._errs = errs  # type: ignore[attr-defined]
    return ctx, page


def _one_entry_then_back(page, row: dict, i: int, length0: int, start_y: float, pinned: bool, what: str) -> None:
    if pinned:
        page.wait_for_function(REST, arg=i, timeout=15000)
    else:
        page.wait_for_function(AT_SECTION, arg=row["anchor"], timeout=8000)
    page.wait_for_function("() => window.__h.length > 0", timeout=5000)
    page.wait_for_timeout(700)
    calls = page.evaluate("() => window.__h.slice()")
    assert calls == [["pushState", "/#" + row["slug"]]], f"ICX-HIST.2 ({what}): one pushState '#{row['slug']}', saw {calls}"
    assert page.evaluate("() => history.length") == length0 + 1, f"ICX-HIST.2 ({what}): not exactly one new entry"
    page.go_back()
    if pinned or page.evaluate("() => FEStory.mode") not in ("calm", "classic", "static"):
        page.wait_for_function(REST, arg=0, timeout=15000)
    try:
        page.wait_for_function("(y) => Math.abs(scrollY - y) <= 2", arg=start_y, timeout=8000)
    except Exception:
        got = page.evaluate("() => [scrollY, document.getElementById('new-invoice').getBoundingClientRect().top, FEStory.state()]")
        raise AssertionError(f"ICX-JUMP.4 ({what}): Back left the reader at {got}, not at scrollY {start_y}") from None
    page.wait_for_timeout(500)
    assert page.evaluate("() => location.hash") == "", f"ICX-HIST.5 ({what}): Back did not return to plain '/'"
    assert page.evaluate("() => window.__h.length") == len(calls), f"ICX-HIST.3 ({what}): Back wrote {page.evaluate('() => window.__h')}"
    assert page.evaluate("() => history.length") == length0 + 1
    assert not page._errs, page._errs


@pytest.mark.parametrize("kind", ["pinned", "native"])
def test_rail_click_one_entry(browser, site_url, kind):
    """B5 judge: one rail click at 1440 = one entry; Back = the first chapter, where the reader was. Pinned = the story;
    native = calm (reduced motion), where every row is a native section and the rail sits in the gutter."""
    ctx, page = _open(browser, site_url, 1440, 900, reduce=(kind == "native"))
    try:
        i = page.evaluate(PICK, kind)
        assert i >= 0, f"no {kind} row at 1440: {page.evaluate('() => FEStory.destinations.map(d => d.kind)')}"
        row = page.evaluate("(i) => FEStory.destinations[i]", i)
        page.wait_for_function("() => { const n = document.querySelector('.story-nav'); return n && !n.hidden; }", timeout=8000)
        length0, start_y = page.evaluate("() => history.length"), page.evaluate("() => scrollY")
        page.click(f".story-nav a[data-go='{row['beat']}']")
        _one_entry_then_back(page, row, i, length0, start_y, kind == "pinned", f"rail/{kind}/{row['slug']}")
    finally:
        ctx.close()


@pytest.mark.parametrize("kind", ["pinned", "native"])
def test_menu_tap_one_entry(browser, site_url, kind):
    """B6 judge: one menu-sheet tap at 390 = one entry; Back = the first chapter, where the reader was."""
    ctx, page = _open(browser, site_url, 390, 844, phone=True)
    try:
        i = page.evaluate(PICK, kind)
        assert i >= 0, f"no {kind} row at 390: {page.evaluate('() => FEStory.destinations.map(d => d.kind)')}"
        row = page.evaluate("(i) => FEStory.destinations[i]", i)
        length0, start_y = page.evaluate("() => history.length"), page.evaluate("() => scrollY")
        page.click("[data-menu-open]")
        page.wait_for_function("() => document.querySelector('#fe-menu').open", timeout=3000)
        page.click(f'#fe-menu .fe-menu-chapters a[data-go="{row["beat"]}"]')
        _one_entry_then_back(page, row, i, length0, start_y, kind == "pinned", f"menu/{kind}/{row['slug']}")
    finally:
        ctx.close()


# ---- reload keeps the reader's place (main's condition on the scrollRestoration change) ---------------------------------

CHAPTER = """() => { const s = FEStory.state(), d = FEStory.destinations;
  if (s.phase === 'rest' && s.rendered != null) return d[s.rendered].slug;
  const line = innerHeight * 0.4;
  for (const r of d) { const e = document.getElementById(r.anchor); if (!e) continue; const b = e.getBoundingClientRect();
    if (b.height > 0 && b.top <= line && b.bottom > line) return r.slug; }
  return null; }"""
MODES = {   # name: (width, height, reduced motion, fe-classic); calm = reduced motion with no choice (classic.js: Classic)
    "calm-1440": (1440, 900, True, None),
    "classic-1440": (1440, 900, False, "1"),
    "story-1440": (1440, 900, False, "0"),
    "story-390": (390, 844, False, "0"),
}
CASES = [(m, s, back) for m in MODES for s in ("price", "templates") for back in ((False, True) if m.split("-")[0] != "story" else (False,))]


@pytest.mark.parametrize("mode,slug,after_back", CASES, ids=[f"{m}-{s}{'-after-back' if b else ''}" for m, s, b in CASES])
def test_reload_keeps_place_calm_classic(browser, site_url, mode, slug, after_back):
    """Reload keeps the reader's place: scrolled a third of the way into Price / Templates, a reload lands on the same
    chapter; in calm / classic within a third of the viewport of the same pixel (the browser's own restore, which the
    jump's 'manual' entry mark must not take away), also after a rail jump and Back. The story modes land on the chapter
    (C3's own restore). The pixel delta is printed for the report."""
    w, h, reduce, classic = MODES[mode]
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce" if reduce else "no-preference",
                              has_touch=w < 640, is_mobile=w < 640)
    pref = f"localStorage.setItem('fe-classic', '{classic}');" if classic else ""
    ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', 'dark'); {pref} }} catch (e) {{}}")
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        page.wait_for_function("() => window.FEStory && window.FEStoryURL && document.documentElement.classList.contains('fx-ready')", timeout=10000)
        page.wait_for_timeout(2500)
        story = mode.startswith("story")
        got_mode = page.evaluate("() => FEStory.mode")
        assert got_mode in (("desktop", "phone") if story else ("calm", "classic")), f"harness: mode {got_mode}"
        if after_back:
            page.evaluate("() => FEStoryURL.jump('templates')")
            page.wait_for_function("() => location.hash === '#templates'", timeout=8000)
            page.wait_for_timeout(500)
            page.go_back()
            page.wait_for_timeout(1500)
        native = page.evaluate("(s) => FEStory.destinations.find(d => d.slug === s).kind", slug) == "native"
        if story:                            # the story: get there by a jump (the sections are not where the track is)
            page.evaluate("(s) => FEStoryURL.jump(s)", slug)
            if not native:
                page.wait_for_function(REST, arg=page.evaluate("(s) => FEStory.destinations.findIndex(d => d.slug === s)", slug), timeout=15000)
            page.wait_for_timeout(1500)
        y0 = page.evaluate("(a) => { const e = document.getElementById(a); const b = e.getBoundingClientRect();"
                           " return Math.round(scrollY + b.top + b.height / 3); }", slug)
        if not story or native:
            page.evaluate("(y) => window.scrollTo({top: y, behavior: 'instant'})", y0)
        page.wait_for_timeout(1500)          # any settle (story) has landed; a spy write has happened
        before = (page.evaluate("() => Math.round(scrollY)"), page.evaluate(CHAPTER))
        page.reload(wait_until="load")
        page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')", timeout=10000)
        page.wait_for_timeout(2500)
        after = (page.evaluate("() => Math.round(scrollY)"), page.evaluate(CHAPTER))
        delta = after[0] - before[0]
        print(f"\nRELOAD {mode} {slug}{' after-back' if after_back else ''}: before {before} after {after} delta {delta}px")
        assert after[1] == before[1], f"reload changed the chapter: before {before}, after {after}"
        if mode.split("-")[0] in ("calm", "classic"):
            assert abs(delta) <= h / 3, f"reload moved the reader {delta}px (before {before}, after {after})"
    finally:
        ctx.close()
