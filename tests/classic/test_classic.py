"""K1: the Classic view switch (decisions 2026-10-15 DEC-6, DEC-7, row 23; PLAN § K1).

A visible, persistent switch from the animated story to the calm, static layout and back, keeping the reader's place;
the site's global stop for autoplay (WCAG 2.2.2). Remembered per visitor in localStorage "fe-classic" ("1" Classic,
"0" the story); a reduced-motion visitor starts in Classic and may switch the story on. Where it lives:
  - "/" >= 640 px: the bar's [data-classic-slot] beside the theme toggle (icon + "Classic" from 1024, icon only below);
  - "/" < 640 px: a row in B6's menu sheet (the phone bar has no room: the brand clipped by 4-19 px at 360-390);
  - not shown where calm is automatic (a short touch screen); the stored choice is kept;
  - /tour/: the tour header beside the theme toggle; Classic stops playback and shows each chapter's end state.
src/partials/head.html reads the same key before the first paint.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run_axe = _load("run_axe", "scripts/checks/run_axe.py")
fidelity = _load("fidelity", "scripts/checks/fidelity.py")

UAS = {
    "mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "win": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "iphone": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
              "Version/18.0 Mobile/15E148 Safari/604.1",
}
BAR_BTN = ".site-header .classic-toggle"
SHEET_BTN = "#fe-menu .classic-toggle"
# the story's destinations at 1440 (FEStory.destinations, checked in the test)
DESTS = ["new-invoice", "templates", "invoices", "dashboard", "email", "your-data", "price", "a-note", "get-the-app"]
RUNNING = "() => document.getAnimations().filter(a => a.playState === 'running').length"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _ctx(browser, w=1440, h=900, theme="dark", ua="mac", stored=None, reduced=False, phone=False, init=None):
    kw = {"viewport": {"width": w, "height": h}, "user_agent": UAS[ua], "color_scheme": theme,
          "reduced_motion": "reduce" if reduced else "no-preference"}
    if phone:
        kw.update(is_mobile=True, has_touch=True)
    ctx = browser.new_context(**kw)
    ctx.route("**/dl/**", lambda r: r.abort())                        # never fetch a download
    ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', '{theme}'); }} catch (e) {{}}")
    if stored is not None:
        # only on the first document of the context: a reload must read what the page itself stored
        ctx.add_init_script("try { if (!sessionStorage.getItem('k1-seeded')) { localStorage.setItem('fe-classic', '"
                            + stored + "'); sessionStorage.setItem('k1-seeded', '1'); } } catch (e) {}")
    if init:
        ctx.add_init_script(init)
    return ctx


def _open(browser, site_url, path="/", **kw):
    ctx = _ctx(browser, **kw)
    page = ctx.new_page()
    errs: list[str] = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(site_url + path)
    if path == "/":
        page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')",
                               timeout=15000)
        page.wait_for_timeout(300)
    page._k1_errs = errs  # type: ignore[attr-defined]
    return ctx, page


def _rest(page, i, timeout=20000):
    page.wait_for_function(
        "(i) => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === i && s.dest === i && !s.step; }",
        arg=i, timeout=timeout)
    page.wait_for_timeout(200)


def _under_header(page):
    """The beat whose stacked section sits under the bar (site.js readingPlace's test)."""
    return page.evaluate("""() => { const hb = document.querySelector('.site-header').getBoundingClientRect().bottom;
      for (const el of document.querySelectorAll('.beat:not(.is-moved)')) { const r = el.getBoundingClientRect();
        if (r.height > 0 && r.top <= hb + 1 && r.bottom > hb + 1) return el.dataset.beat; } return null; }""")


def _stored(page):
    return page.evaluate("() => localStorage.getItem('fe-classic')")


# ---- the switch keeps the reading place, both ways --------------------------------------------------------------------

@pytest.mark.parametrize("slug", DESTS)
def test_toggle_both_ways_same_place(site_url, browser, slug):
    ctx, page = _open(browser, site_url, w=1440, h=900)
    try:
        dests = page.evaluate("FEStory.destinations")
        assert [d["slug"] for d in dests] == DESTS
        i = next(d for d in dests if d["slug"] == slug)
        k = page.evaluate("(s) => FEStory.destinations.findIndex(d => d.slug === s)", slug)
        beat = i["beat"]
        idx = page.evaluate("(b) => { FEStory.goTo(b, {source: 'jump'}); return FEStory.dest; }", beat)
        _rest(page, idx)
        # story -> Classic: the bar's button, the section of the same chapter under the bar
        page.click(BAR_BTN)
        page.wait_for_function("() => FEStory.mode === 'classic'")
        page.wait_for_timeout(150)
        assert page.get_attribute(BAR_BTN, "aria-pressed") == "true"
        assert _under_header(page) == beat, (slug, k, _under_header(page))
        # Classic -> story: lands on the same checkpoint's rest frame (no replay)
        page.click(BAR_BTN)
        page.wait_for_function("() => FEStory.mode === 'desktop'")
        _rest(page, idx)
        assert page.get_attribute(BAR_BTN, "aria-pressed") == "false"
        # focus never moves: it stays on the switch
        assert page.evaluate("() => document.activeElement && document.activeElement.matches('.site-header .classic-toggle')")
        assert not page._k1_errs, page._k1_errs
    finally:
        ctx.close()


# ---- remembered per visitor ------------------------------------------------------------------------------------------

def test_persists(site_url, browser):
    ctx, page = _open(browser, site_url)
    try:
        assert _stored(page) is None and page.evaluate("FEStory.mode") == "desktop"
        page.click(BAR_BTN)
        assert _stored(page) == "1"
        page.reload()
        page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')")
        assert page.evaluate("FEStory.mode") == "classic"
        assert page.get_attribute(BAR_BTN, "aria-pressed") == "true"
        page.click(BAR_BTN)
        assert _stored(page) == "0"
        page.reload()
        page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')")
        assert page.evaluate("FEStory.mode") == "desktop"
    finally:
        ctx.close()
    # a reduced-motion visitor starts in Classic and may switch the story on; the choice survives a reload and a resize
    ctx, page = _open(browser, site_url, reduced=True)
    try:
        assert page.evaluate("FEStory.mode") in ("calm", "classic")
        assert page.get_attribute(BAR_BTN, "aria-pressed") == "true"
        page.click(BAR_BTN)
        page.wait_for_function("() => FEStory.mode === 'desktop'")
        assert _stored(page) == "0"
        page.reload()
        page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')")
        page.wait_for_timeout(300)
        assert page.evaluate("FEStory.mode") == "desktop"
        assert page.evaluate("() => document.documentElement.classList.contains('motion')")
        page.set_viewport_size({"width": 1300, "height": 900})     # a resize re-reads the mode (site.js syncMode)
        page.wait_for_timeout(400)
        assert page.evaluate("FEStory.mode") == "desktop", "a resize reverted the visitor's choice"
        assert page.get_attribute(BAR_BTN, "aria-pressed") == "false"
    finally:
        ctx.close()


FIRST_FRAME = ("window.__k1fp = null; requestAnimationFrame(() => { window.__k1fp = "
               "document.documentElement.className; });")


def test_first_paint_is_classic(site_url, browser):
    """(main's condition 4) a remembered Classic is calm in the first painted frame: no story frame first."""
    ctx, page = _open(browser, site_url, stored="1", init=FIRST_FRAME)
    try:
        fp = page.evaluate("window.__k1fp")
        assert fp is not None and "calm" in fp.split() and "motion" not in fp.split(), fp
    finally:
        ctx.close()
    # and a story chosen over reduced motion is the story from the first frame
    ctx, page = _open(browser, site_url, stored="0", reduced=True, init=FIRST_FRAME)
    try:
        fp = page.evaluate("window.__k1fp")
        assert fp is not None and "motion" in fp.split() and "calm" not in fp.split(), fp
    finally:
        ctx.close()


@pytest.mark.parametrize("reduced", [False, True], ids=["motion-ok", "reduced"])
def test_story_choice_never_forces_motion_on_short_touch(site_url, browser, reduced):
    """(main's condition 2) a stored "0" never overrides the automatic calm of a short touch screen."""
    ctx, page = _open(browser, site_url, w=844, h=390, ua="iphone", phone=True, stored="0", reduced=reduced,
                      init=FIRST_FRAME)
    try:
        fp = page.evaluate("window.__k1fp")
        assert fp is not None and "motion" not in fp.split(), fp
        page.wait_for_timeout(400)
        cls = page.evaluate("document.documentElement.className").split()
        assert "calm" in cls and "motion" not in cls, cls
        assert page.evaluate("FEStory.mode") == "calm"
    finally:
        ctx.close()


# ---- the stop --------------------------------------------------------------------------------------------------------

def test_no_autoplay_in_classic(site_url, browser):
    """A remembered Classic on a fresh visit at the top: no arrival, no frame loop, no running animation."""
    ctx, page = _open(browser, site_url, stored="1")
    try:
        assert page.evaluate("FEStory.mode") == "classic"
        page.wait_for_timeout(1000)
        s = page.evaluate("FEStory.state()")
        assert s["step"] is None and s["phase"] == "rest", s
        assert page.evaluate(RUNNING) == 0
        assert page.evaluate("() => document.querySelector('.pin').children.length === 0 || !document.querySelector('.pin .mount, .pin canvas')")
        assert page.evaluate("() => scrollY") == 0, "the page moved by itself"
    finally:
        ctx.close()


def test_is_global_stop(site_url, browser):
    """(DEC-6) toggling while a content run plays stops it at once: in the same task as the click."""
    ctx, page = _open(browser, site_url)
    try:
        page.wait_for_function("() => FEStory.state().step === 'content'", timeout=5000)
        s = page.evaluate("""() => { document.querySelector('.site-header .classic-toggle').click();
          const s = FEStory.state(); return {mode: s.mode, step: s.step, phase: s.phase}; }""")
        assert s == {"mode": "classic", "step": None, "phase": "rest"}, s
        y0 = page.evaluate("() => scrollY")
        page.wait_for_timeout(800)
        assert page.evaluate(RUNNING) == 0
        assert page.evaluate("() => scrollY") == y0, "the story kept moving the page after the stop"
        assert page.evaluate("FEStory.state().step") is None
    finally:
        ctx.close()


def test_f10_parity(site_url, browser):
    """fidelity.py F10 (reduce -> 0 running animations after 1 s) holds on "/" and /tour/; Classic by choice matches it."""
    for path in ("/", "/tour/"):
        ok, ev = fidelity.check_F10(browser, site_url + path)
        assert ok, (path, ev)
    ctx, page = _open(browser, site_url, stored="1")
    try:
        page.wait_for_timeout(1000)
        assert page.evaluate(RUNNING) == 0
    finally:
        ctx.close()


# ---- where it lives --------------------------------------------------------------------------------------------------

def test_hidden_where_calm_is_automatic(site_url, browser):
    # a phone held sideways (short touch screen): calm is automatic, no switch anywhere; the stored choice is kept
    ctx, page = _open(browser, site_url, w=844, h=390, ua="iphone", phone=True, stored="1")
    try:
        assert page.evaluate("FEStory.mode") in ("calm", "classic")
        for sel in (BAR_BTN, SHEET_BTN):
            assert page.evaluate("(s) => { const b = document.querySelector(s); return !!b && b.getClientRects().length === 0; }", sel), sel
        assert page.evaluate("() => getComputedStyle(document.querySelector('.site-header [data-classic-slot]')).display") == "none"
        assert _stored(page) == "1"
        # turned upright (not short): the switch is back, in the sheet (< 640 px)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.click("[data-menu-open]")
        assert page.is_visible(SHEET_BTN)
        assert page.get_attribute(SHEET_BTN, "aria-pressed") == "true"
    finally:
        ctx.close()
    # a desktop browser, any height: always shown
    ctx, page = _open(browser, site_url, w=1024, h=500)
    try:
        assert page.is_visible(BAR_BTN)
    finally:
        ctx.close()


SWEEP = """() => {
  const sh = document.querySelector('.site-header .shell');
  const els = [...sh.querySelectorAll('.brand, .nav > a, .nav > button, .dl-note, .fe-menu-btn, .classic-toggle')]
    .filter(e => e.getClientRects().length && getComputedStyle(e).display !== 'none' && getComputedStyle(e).visibility !== 'hidden');
  const items = els.map(e => { const b = e.getBoundingClientRect();
    let tl = b.left, tr = b.right;
    if (!e.matches('.fe-menu-btn, [data-theme-toggle], .classic-toggle')) { const r = document.createRange(); r.selectNodeContents(e);
      const t = r.getBoundingClientRect(); tl = t.left; tr = t.right; }
    return { k: e.matches('.brand') ? 'brand' : e.matches('[data-menu-open]') ? 'menu' : e.matches('[data-theme-toggle]') ? 'theme'
      : e.matches('.classic-toggle') ? 'classic' : e.matches('[data-dl]') ? 'download' : e.matches('.dl-note') ? 'note' : e.textContent.trim(),
      l: b.left, r: b.right, h: b.height, tl, tr, cy: b.top + b.height / 2,
      sw: e.matches('.brand') ? e.querySelector('span').scrollWidth : 0, cw: e.matches('.brand') ? e.querySelector('span').clientWidth : 0 }; }).sort((a, b) => a.l - b.l);
  return { vw: innerWidth, docw: document.documentElement.scrollWidth, items };
}"""


def _problems(m):
    out = []
    if m["docw"] > m["vw"]:
        out.append("page wider than viewport")
    cy = m["items"][0]["cy"]
    for a in m["items"]:
        # (below 640 the bar is B6's, unchanged by K1: its brand is checked as B6's test_bar_fits does, by the name's
        # own scrollWidth; the text range of the logo + name pair overhangs by a glyph there on the base too)
        if a["k"] == "brand" and m["vw"] < 640:
            if a["sw"] > a["cw"] + 0.5:
                out.append("brand is clipped")
        elif a["tl"] < a["l"] - 0.5 or a["tr"] > a["r"] + 0.5:
            out.append(f"{a['k']} text spills its box")
        if a["h"] > 44:
            out.append(f"{a['k']} grew to {a['h']:.0f} px")
        if a["l"] < 0 or a["r"] > m["vw"]:
            out.append(f"{a['k']} runs past the viewport")
        if abs(a["cy"] - cy) > 3:
            out.append(f"{a['k']} wrapped off the row")
    for a, b in zip(m["items"], m["items"][1:]):
        if a["r"] > b["l"] + 0.5 or a["tr"] > b["tl"] + 0.5:
            out.append(f"{a['k']} overlaps {b['k']}")
    return out


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("ua", ["mac", "win", "iphone"])
def test_bar_fits_with_classic(site_url, browser, ua, theme):
    widths = [360, 375, 390] if ua == "iphone" else [360, 375, 390, 640, 700, 1024, 1440]
    for w in widths:
        ctx, page = _open(browser, site_url, w=w, h=740 if w < 640 else 900, ua=ua, phone=ua == "iphone", theme=theme)
        try:
            m = page.evaluate(SWEEP)
            where = f"{ua} {theme} @{w}: {m}"
            assert not _problems(m), (_problems(m), where)
            keys = [i["k"] for i in m["items"]]
            if w < 640:
                # the phone bar is B6's, unchanged; the switch is the sheet's row
                assert keys == ["brand", "download", "theme", "menu"], where
                page.click("[data-menu-open]")
                assert page.is_visible(SHEET_BTN), where
                assert page.inner_text(SHEET_BTN).strip() == "Classic view"
                page.click(SHEET_BTN)
                page.wait_for_function("() => FEStory.mode === 'classic'")
                assert page.get_attribute(SHEET_BTN, "aria-pressed") == "true"
                assert page.evaluate("() => document.querySelector('#fe-menu').open"), "the sheet closed under the switch"
            else:
                assert keys[keys.index("theme") + 1] == "classic", where
                label = page.inner_text(BAR_BTN).strip()
                assert label == ("Classic" if w >= 1024 else ""), (label, where)
                assert page.get_attribute(BAR_BTN, "aria-label") == "Classic view"
                assert page.get_attribute(BAR_BTN, "title") == "Classic view"
                assert not page.is_visible(SHEET_BTN)
        finally:
            ctx.close()
    if ua == "iphone":
        return
    # every 8 px from 600 to 1023, every px from 696 to 724 (the platform note's edge), on a Mac and a Windows desktop
    ctx, page = _open(browser, site_url, w=1100, h=800, ua=ua, theme=theme)
    try:
        bad = {}
        for w in sorted(set(list(range(600, 1024, 8)) + list(range(696, 725)) + [1023])):
            page.set_viewport_size({"width": w, "height": 800})
            page.wait_for_timeout(40)
            m = page.evaluate(SWEEP)
            probs = _problems(m)
            if "classic" not in [i["k"] for i in m["items"]] and w >= 640:
                probs.append("no classic switch in the bar")
            if probs:
                bad[w] = probs
        assert not bad, f"{ua} {theme}: {bad}"
    finally:
        ctx.close()


# ---- /tour/ ----------------------------------------------------------------------------------------------------------

def test_tour_stop(site_url, browser):
    ctx, page = _open(browser, site_url, path="/tour/", w=1440, h=900)
    try:
        page.wait_for_function("() => window.__tour && window.__tour.ready", timeout=15000)
        btn = ".tour-header .classic-toggle"
        assert page.get_attribute(btn, "aria-pressed") == "false"
        assert page.inner_text(btn).strip() == "Classic"
        page.evaluate("() => __tour.jump(2)")
        t_start = page.evaluate("() => __tour.state().t")
        page.click("#play")
        page.wait_for_function("() => __tour.state().playing && __tour.state().t > %f + 0.3" % t_start)
        st = page.evaluate("""() => { document.querySelector('.tour-header .classic-toggle').click(); return __tour.state(); }""")
        assert st["playing"] is False, st
        t_end = st["t"]
        assert st["chapter"] == 2 and t_end > t_start + 0.3, (t_start, st)   # chapter 2's end state, not its start
        page.wait_for_timeout(600)
        assert page.evaluate("() => __tour.state().t") == t_end, "the tour kept running after the stop"
        assert page.is_hidden("#play")
        assert page.evaluate("() => document.getElementById('app-frame').contentDocument.documentElement.dataset.motion") == "reduced"
        assert "Classic view" in page.inner_text("#player-note")
        assert _stored(page) == "1"
        # every chapter shows its end state; the stored choice survives a reload
        page.click('[data-chapter="4"]')
        s4 = page.evaluate("() => __tour.state()")
        assert s4["chapter"] == 4 and not s4["playing"]
        page.reload()
        page.wait_for_function("() => window.__tour && window.__tour.ready", timeout=15000)
        assert page.get_attribute(btn, "aria-pressed") == "true" and page.is_hidden("#play")
        # and back: the tour plays again
        page.click(btn)
        assert page.is_visible("#play") and _stored(page) == "0"
        # (Sol K1-1) Space on the focused switch presses the switch, not the tour's play/pause shortcut
        page.focus(btn)
        page.keyboard.press("Space")
        page.wait_for_timeout(200)
        assert page.get_attribute(btn, "aria-pressed") == "true" and not page.evaluate("() => __tour.state().playing")
        assert not page._k1_errs, page._k1_errs
    finally:
        ctx.close()
    # (Sol K1-1) on a phone the switch and the theme toggle do not overlap
    ctx, page = _open(browser, site_url, path="/tour/", w=375, h=740, ua="iphone", phone=True)
    try:
        t = page.locator(".tour-header [data-theme-toggle]").bounding_box()
        c = page.locator(".tour-header .classic-toggle").bounding_box()
        assert c["x"] >= t["x"] + t["width"], (t, c)
    finally:
        ctx.close()


# ---- axe, both states, both themes, "/" and /tour/ -------------------------------------------------------------------

@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("stored", ["0", "1"], ids=["story", "classic"])
@pytest.mark.parametrize("path", ["/", "/tour/"])
def test_axe_both_states(site_url, browser, path, stored, theme):
    found = []
    for w in (1440, 390):
        ctx = _ctx(browser, w=w, h=900, theme=theme, stored=stored)
        try:
            ctx.route("**/*", run_axe._local_only)
            page = ctx.new_page()
            page.goto(site_url + path, wait_until="load")
            page.wait_for_timeout(800)
            page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
            page.add_script_tag(content=run_axe.axe_source())
            res = page.evaluate("axe.run(document, {resultTypes: ['violations']})")
            found += [(w, v["id"], v["impact"], [n["target"] for n in v["nodes"][:3]]) for v in res["violations"]
                      if v.get("impact") in ("serious", "critical")]
        finally:
            ctx.close()
    assert found == [], found
