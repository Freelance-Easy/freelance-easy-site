"""K1: the Classic view switch (decisions 2026-10-15 DEC-6, DEC-7, row 23; PLAN § K1).

A visible, persistent switch from the animated story to the calm, static layout and back, keeping the reader's place;
the site's global stop for autoplay (WCAG 2.2.2). Remembered per visitor in localStorage "fe-classic" ("1" Classic,
"0" the story); a reduced-motion visitor starts in Classic and may switch the story on. Where it lives:
  - "/" >= 1024 px: the bar's [data-classic-slot] beside the theme toggle (icon + "Classic");
  - "/" < 1024 px, wherever the bar shows B6's menu button: a row in the menu sheet (the phone bar has no room: the brand
    clipped by 4-19 px at 360-390; at 640-~727 the switch's 44 px pushed out the platform note, which stays beside
    Download at every width >= 640: GATEFIX, main's ruling 2026-10-17, PLAN.md Decision log);
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


def _toggle(page):
    """Press the Classic switch where the reader finds it: the bar's (>= 1024 px) or the menu sheet's row (< 1024 px;
    the sheet is opened for the press and closed after it, as a reader would)."""
    if page.is_visible(BAR_BTN):
        page.click(BAR_BTN)
        return
    page.click("[data-menu-open]")
    page.click(SHEET_BTN)
    page.click("[data-menu-open]")
    page.wait_for_function("() => !document.querySelector('#fe-menu').open")


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
        page.click("[data-menu-open]")                              # the sheet holds no switch either
        assert page.is_visible("#fe-menu .fe-menu-panel") and not page.is_visible(SHEET_BTN)
        page.click("[data-menu-open]")
        # turned upright (not short): the switch is back, in the sheet (< 640 px)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.click("[data-menu-open]")
        assert page.is_visible(SHEET_BTN)
        assert page.get_attribute(SHEET_BTN, "aria-pressed") == "true"
    finally:
        ctx.close()
    # a touch tablet whose window turns short: the bar's switch steps aside (and comes back)
    ctx, page = _open(browser, site_url, w=1024, h=760, ua="iphone", phone=True)
    try:
        assert page.is_visible(BAR_BTN)
        page.set_viewport_size({"width": 1024, "height": 500})
        page.wait_for_timeout(400)
        assert not page.is_visible(BAR_BTN), "the switch stayed where calm is automatic"
        page.set_viewport_size({"width": 1024, "height": 760})
        page.wait_for_timeout(400)
        assert page.is_visible(BAR_BTN)
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
    widths = [360, 375, 390] if ua == "iphone" else [360, 375, 390, 640, 700, 800, 1024, 1440]
    for w in widths:
        ctx, page = _open(browser, site_url, w=w, h=740 if w < 640 else 900, ua=ua, phone=ua == "iphone", theme=theme)
        try:
            m = page.evaluate(SWEEP)
            where = f"{ua} {theme} @{w}: {m}"
            assert not _problems(m), (_problems(m), where)
            keys = [i["k"] for i in m["items"]]
            if w < 1024:
                # below 1024 the bar has the menu button and the switch is the sheet's row (the phone bar is B6's,
                # unchanged; at 640-1023 the platform note keeps its place beside Download)
                if w < 640:
                    assert keys == ["brand", "download", "theme", "menu"], where
                else:
                    assert "classic" not in keys and keys[-1] == "menu" and "note" in keys, where
                assert not page.is_visible(BAR_BTN), where
                page.click("[data-menu-open]")
                assert page.is_visible(SHEET_BTN), where
                assert page.inner_text(SHEET_BTN).strip() == "Classic view"
                page.click(SHEET_BTN)
                page.wait_for_function("() => FEStory.mode === 'classic'")
                assert page.get_attribute(SHEET_BTN, "aria-pressed") == "true"
                assert page.evaluate("() => document.documentElement.classList.contains('calm')"), where
                assert _stored(page) == "1", where
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
    # every 8 px from 600 to 1023, every px from 640 to 680 and 696 to 732 (the old edges), on a Mac and a Windows desktop:
    # one row, nothing overlaps, the platform note beside Download from 640, the switch in the sheet (not the bar) < 1024
    ctx, page = _open(browser, site_url, w=1100, h=800, ua=ua, theme=theme)
    try:
        bad = {}
        for w in sorted(set(list(range(600, 1024, 8)) + list(range(640, 681)) + list(range(696, 733)) + [1023, 1024, 1440])):
            page.set_viewport_size({"width": w, "height": 800})
            page.wait_for_timeout(40)
            m = page.evaluate(SWEEP)
            probs = _problems(m)
            keys = [i["k"] for i in m["items"]]
            if "classic" not in keys and w >= 1024:
                probs.append("no classic switch in the bar")
            if "classic" in keys and w < 1024:
                probs.append("the classic switch is in the bar beside the menu button")
            if "note" not in keys and w >= 640:
                probs.append("no platform note beside Download")
            if probs:
                bad[w] = probs
        assert not bad, f"{ua} {theme}: {bad}"
    finally:
        ctx.close()


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("ua", ["mac", "win"])
def test_tour_bar_fits_with_classic(site_url, browser, ua, theme):
    """(TOUR r2, PLAN.md GATEFIX "same width = same place on every page") /tour/'s bar has the same items as "/" (links,
    the platform note, Download, theme, Classic), so it follows the same rule: below 1024 the menu button and the switch
    as the sheet's row, from 1024 the switch in the bar; one row, nothing over the brand, the note beside Download."""
    ctx, page = _open(browser, site_url, path="/tour/", w=1100, h=800, ua=ua, theme=theme)
    try:
        page.wait_for_function("() => window.__tour && window.__tour.ready", timeout=15000)
        bad = {}
        for w in sorted(set(list(range(600, 1024, 8)) + list(range(640, 681)) + list(range(696, 733)) + [820, 1023, 1024, 1440])):
            page.set_viewport_size({"width": w, "height": 800})
            page.wait_for_timeout(40)
            m = page.evaluate(SWEEP)
            probs = _problems(m)
            keys = [i["k"] for i in m["items"]]
            if w >= 1024 and ("classic" not in keys or "menu" in keys):
                probs.append("not the desktop bar (switch in the bar, no menu button)")
            if w < 1024 and ("classic" in keys or keys[-1] != "menu"):
                probs.append(f"the classic switch is in the bar or no menu button: {keys}")
            if "note" not in keys and w >= 640:
                probs.append("no platform note beside Download")
            if probs:
                bad[w] = probs
        assert not bad, f"{ua} {theme}: {bad}"
        # at 820 the switch is the sheet's row and works there
        page.set_viewport_size({"width": 820, "height": 800})
        page.wait_for_timeout(100)
        assert not page.is_visible(BAR_BTN)
        page.click("[data-menu-open]")
        assert page.is_visible(SHEET_BTN)
        assert page.inner_text(SHEET_BTN).strip() == "Classic view"
        page.click(SHEET_BTN)
        assert page.get_attribute(SHEET_BTN, "aria-pressed") == "true"
        assert page.evaluate("() => FEClassic.isOn()") and _stored(page) == "1"
        assert page.evaluate("() => document.querySelector('#fe-menu').open"), "the sheet closed under the switch"
    finally:
        ctx.close()


# ---- /tour/ ----------------------------------------------------------------------------------------------------------

def test_tour_stop(site_url, browser):
    ctx, page = _open(browser, site_url, path="/tour/", w=1440, h=900)
    try:
        page.wait_for_function("() => window.__tour && window.__tour.ready", timeout=15000)
        btn = ".site-header .classic-toggle"
        assert page.get_attribute(btn, "aria-pressed") == "false"
        assert page.inner_text(btn).strip() == "Classic"
        page.evaluate("() => __tour.jump(2)")
        t_start = page.evaluate("() => __tour.state().t")
        page.click("#play")
        page.wait_for_function("() => __tour.state().playing && __tour.state().t > %f + 0.3" % t_start)
        st = page.evaluate("""() => { document.querySelector('.site-header .classic-toggle').click(); return __tour.state(); }""")
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
    # (TOUR r2) a tablet at 820: as on "/", the bar has the menu button and the switch is the sheet's row
    ctx, page = _open(browser, site_url, path="/tour/", w=820, h=1180, ua="iphone", phone=True)
    try:
        page.wait_for_function("() => window.__tour && window.__tour.ready", timeout=15000)
        assert not page.is_visible(BAR_BTN) and page.is_visible("[data-menu-open]")
        page.click("[data-menu-open]")
        page.wait_for_selector(SHEET_BTN, state="visible")
    finally:
        ctx.close()
    # (Sol K1-1) on a tablet with the switch in the bar (>= 1024) the switch and the theme toggle do not overlap
    ctx, page = _open(browser, site_url, path="/tour/", w=1024, h=1366, ua="iphone", phone=True)
    try:
        t = page.locator(".site-header [data-theme-toggle]").bounding_box()
        c = page.locator(".site-header .classic-toggle").bounding_box()
        assert c["x"] >= t["x"] + t["width"], (t, c)
    finally:
        ctx.close()
    # (TOUR) the tour is on the shared bar: on a phone (< 640 px) the switch is the menu sheet's row, as on "/"
    ctx, page = _open(browser, site_url, path="/tour/", w=375, h=740, ua="iphone", phone=True)
    try:
        page.wait_for_function("() => window.__tour && window.__tour.ready", timeout=15000)
        assert not page.is_visible(".site-header .classic-toggle")
        page.click("[data-menu-open]")
        page.wait_for_selector(SHEET_BTN, state="visible")
        page.click(SHEET_BTN)
        assert page.get_attribute(SHEET_BTN, "aria-pressed") == "true" and _stored(page) == "1"
        assert page.evaluate("() => document.getElementById('app-frame').contentDocument.documentElement.dataset.motion") == "reduced"
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


# ---- the reading place at a section's edge (K1-fix; K1 judge finding 1) -------------------------------------------------
# readingPlace used to pick the section under the bar, so a section whose top sat a few px below the bar was one chapter
# BEHIND what the reader (and the rail) already showed. It now uses the rail's rule (ICX-HL.4): the last section whose
# top is at or above 40 % of the viewport.

CURRENT = """() => { const line = innerHeight * 0.4; let cur = null;
  for (const el of document.querySelectorAll('.beat:not(.is-moved), .site-footer')) {
    const r = el.getBoundingClientRect(); if (r.height > 0 && r.top <= line) cur = el; }
  return cur && cur.classList.contains('beat') ? cur.dataset.beat : null; }"""
RAIL_CURRENT = """() => { const a = document.querySelector('nav [aria-current="location"]'); if (!a) return null;
  const el = document.getElementById(a.getAttribute('href').slice(1)); if (!el) return null;
  const b = el.dataset.beat ? el : el.closest('[data-beat]'); return b ? b.dataset.beat : null; }"""
SCROLL_TO_TOP_AT = """([beat, at]) => { const el = document.querySelector(`.beat[data-beat="${beat}"]`);
  const y = scrollY + el.getBoundingClientRect().top - at; window.scrollTo({top: Math.max(0, y), behavior: 'instant'});
  return Math.round(el.getBoundingClientRect().top); }"""


def _landed(page, idx, where):
    """The story settled on destination idx (a rest frame), or fail naming where it landed instead."""
    try:
        _rest(page, idx, timeout=20000)
    except Exception:
        st = page.evaluate("() => { const s = FEStory.state(); return {phase: s.phase, rendered: s.rendered, dest: s.dest}; }")
        raise AssertionError(f"expected destination {idx}, the story is at {st}: {where}") from None


def _edge_positions(page):
    """px from the viewport top at which a section's top is put: 1-40 px below the bar, then 41-60 % down the viewport."""
    hb = page.evaluate("() => document.querySelector('.site-header').getBoundingClientRect().bottom")
    vh = page.evaluate("() => innerHeight")
    return [round(hb) + d for d in (1, 12, 40)] + [round(vh * p) for p in (0.41, 0.5, 0.6)]


@pytest.mark.parametrize("w,h", [(1440, 900), (820, 1100)], ids=["1440", "820"])
def test_place_kept_at_section_edges(site_url, browser, w, h):
    ctx, page = _open(browser, site_url, w=w, h=h)
    try:
        _toggle(page)
        page.wait_for_function("() => FEStory.mode === 'classic'")
        page.wait_for_timeout(150)
        dests = page.evaluate("FEStory.destinations")
        by_beat = {d["beat"]: k for k, d in enumerate(dests)}
        beats = page.evaluate("() => [...document.querySelectorAll('.beat:not(.is-moved)')].map(e => e.dataset.beat)")
        assert len(beats) >= 8, beats
        checked = 0
        for beat in beats:
            for at in _edge_positions(page):
                _toggle(page) if page.evaluate("FEStory.mode") != "classic" else None
                page.wait_for_function("() => FEStory.mode === 'classic'")
                page.evaluate(SCROLL_TO_TOP_AT, [beat, at])
                page.wait_for_timeout(120)
                cur = page.evaluate(CURRENT)
                if cur is None or cur not in by_beat:
                    continue                                    # the page top or the footer: no chapter to land on
                if w >= 1024:
                    assert page.evaluate(RAIL_CURRENT) == cur, ("the rail disagrees with the 40 % line", beat, at)
                # Classic -> story: lands on the chapter the reader was on (its rest frame)
                _toggle(page)
                page.wait_for_function("() => FEStory.mode !== 'classic'")
                page.wait_for_function("() => ['rest', 'released'].includes(FEStory.state().phase) && !FEStory.state().step",
                                       timeout=20000)
                page.wait_for_timeout(150)
                if page.evaluate("FEStory.state().phase") == "rest":
                    _landed(page, by_beat[cur], (beat, at, cur))
                else:                                          # a native section (the tablet's tail): the same one is current
                    assert page.evaluate(CURRENT) == cur, ("native section", beat, at, cur)
                checked += 1
        assert checked >= 30, checked
        assert not page._k1_errs, page._k1_errs
    finally:
        ctx.close()


@pytest.mark.parametrize("w,h", [(1440, 900), (820, 1100), (1440, 1200)],
                         ids=["1440", "820", "1440-tall"])
def test_story_to_classic_lands_on_chapter(site_url, browser, w, h):
    """The reverse: the chapter the story showed is the section the Classic page shows as current (not one behind)."""
    ctx, page = _open(browser, site_url, w=w, h=h)
    try:
        for k, d in enumerate(page.evaluate("FEStory.destinations")):
            idx = k
            page.evaluate("(b) => FEStory.goTo(b, {source: 'jump'})", d["beat"])
            page.wait_for_function("() => ['rest', 'released'].includes(FEStory.state().phase) && !FEStory.state().step",
                                   timeout=20000)
            page.wait_for_timeout(900)                          # a native section (tablet) is reached by a scroll
            pinned = page.evaluate("FEStory.state().phase") == "rest"
            before = None if pinned else page.evaluate(CURRENT)
            if pinned:
                _landed(page, idx, ("story", d["slug"]))
            _toggle(page)
            page.wait_for_function("() => FEStory.mode === 'classic'")
            page.wait_for_timeout(150)
            cur = page.evaluate(CURRENT)
            # (the last chapter on a tall window cannot be scrolled up to the line: the page has ended)
            at_end = page.evaluate("() => scrollY >= document.documentElement.scrollHeight - innerHeight - 1")
            assert at_end or cur == (d["beat"] if pinned else before), (d["slug"], d["beat"], cur, before)
            if w >= 1024:
                assert page.evaluate(RAIL_CURRENT) == cur
            _toggle(page)
            page.wait_for_function("() => FEStory.mode !== 'classic'")
            if pinned and not at_end:
                _landed(page, idx, ('back to the story', d['slug']))
    finally:
        ctx.close()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_classic_label_centred_on_icon(site_url, browser, theme):
    """(K1 judge LOW) at >= 1024 px the word "Classic" sits on the icon's centre line (it sat 0.75 px above)."""
    ctx, page = _open(browser, site_url, w=1440, h=900, theme=theme)
    try:
        m = page.evaluate("""() => { const b = document.querySelector('.site-header .classic-toggle'), br = b.getBoundingClientRect();
          const r = document.createRange(); r.selectNodeContents(b.querySelector('.classic-label')); const t = r.getBoundingClientRect();
          const i = b.querySelector('svg').getBoundingClientRect();
          return {btn: br.top + br.height / 2, text: t.top + t.height / 2, icon: i.top + i.height / 2}; }""")
        assert abs(m["text"] - m["icon"]) <= 0.3 and abs(m["btn"] - m["icon"]) <= 0.3, m
    finally:
        ctx.close()


# ---- a rotation keeps the place too (ICX-DEST.4): the layout re-flows before the resize event, so a size change reads the section under the bar (site.js readingPlace) ----

@pytest.mark.parametrize("beat", ["look", "grow"])
# (chase and yours land one checkpoint late on the base too: 910f8ad gives the same result, so they are not asserted here)
def test_rotation_round_trip_story(site_url, browser, beat):
    """portrait 390x664 story -> 844x390 (calm) -> portrait: back on the same checkpoint's rest frame."""
    ctx, page = _open(browser, site_url, w=390, h=664, ua="iphone", phone=True)
    try:
        dests = page.evaluate("FEStory.destinations")
        idx = next(k for k, d in enumerate(dests) if d["beat"] == beat)
        page.evaluate("(b) => FEStory.goTo(b, {source: 'jump'})", beat)
        _landed(page, idx, ("portrait", beat))
        page.set_viewport_size({"width": 844, "height": 390})
        page.wait_for_function("() => FEStory.mode === 'calm'", timeout=6000)
        page.wait_for_timeout(700)
        assert page.evaluate(CURRENT) == beat, ("landscape lost the place", beat)
        page.set_viewport_size({"width": 390, "height": 664})
        page.wait_for_timeout(700)
        _landed(page, idx, ("back in portrait", beat))
    finally:
        ctx.close()


@pytest.mark.parametrize("beat", ["look", "grow", "chase", "price"])
@pytest.mark.parametrize("w,h", [(375, 548), (390, 664)], ids=["375x548", "390x664-classic"])
def test_rotation_round_trip_stacked(site_url, browser, beat, w, h):
    """stacked sections (short touch screen / Classic): rotate to 844x390 and back, the chapter in view is the same one."""
    ctx, page = _open(browser, site_url, w=w, h=h, ua="iphone", phone=True, stored="1")
    try:
        page.wait_for_function("() => FEStory.mode === 'classic' || FEStory.mode === 'calm'")
        for at in (60, 90):                                     # the section's top just under the bar
            page.evaluate(SCROLL_TO_TOP_AT, [beat, at])
            page.wait_for_timeout(250)                          # let the scroll settle
            before = page.evaluate(CURRENT)
            assert before is not None
            page.set_viewport_size({"width": 844, "height": 390})
            page.wait_for_timeout(600)
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(600)
            assert page.evaluate(CURRENT) == before, (beat, at, before, page.evaluate(CURRENT))
    finally:
        ctx.close()
