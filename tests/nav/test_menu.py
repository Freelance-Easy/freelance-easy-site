"""B6: the phone/tablet menu sheet (src/partials/menu.html, assets/site/shell.{js,css}), per docs/interaction-contract.md.

- test_button_visible_rail_hidden: on "/" the bar's menu button shows wherever the chapter rail is hidden (390, 800) and
  is gone where the rail and the bar's links show (1024+); on the doc pages and /pricing it shows only where the bar has
  dropped How it works / Pricing (< 640).
- test_bar_fits: at 360 / 375 / 390, both themes, an iPhone ("Get it on Mac") and a desktop UA, on "/" and /pricing: one
  row, no overlap, nothing clipped or truncated, nothing past the viewport.
- test_dialog_focus_trap_esc_returns_focus: aria-expanded, Tab / Shift+Tab wrap inside the sheet, Escape and the Close
  control close it, focus returns to the button (opened as Safari does, with focus never on the button), the page and
  the story hold still under it, the bar's theme toggle still works with it open.
- test_tap_closes_and_lands: a chapter tap closes the sheet, then lands: a pinned chapter >= 2 away at rest, a native
  row by a native scroll to its section (ICX-JUMP.5); the menu itself never changes the hash.
- test_same_list_as_rail: the sheet's chapters and the rail's links are both FEStory.destinations, row for row, and the
  sheet marks the rail's aria-current chapter (read, never written: ICX-HL.5).
- test_site_links_on_every_shell_page / test_signin_flagged / test_axe_menu / test_nojs_button_hidden.

Run: uv run --with pytest --with playwright python3 -m pytest tests/nav/test_menu.py -q
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_spec = importlib.util.spec_from_file_location("run_axe", ROOT / "scripts" / "checks" / "run_axe.py")
run_axe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_axe)

IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "Version/18.0 Mobile/15E148 Safari/604.1")
SHELL_PAGES = ["/", "/install.html", "/privacy.html", "/terms.html", "/404.html", "/pricing.html"]
AD_PAGES = ["mac.html", "mac-audio.html", "audio.html"]
BTN = "[data-menu-open]"
DLG = "#fe-menu"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _open(browser, url, w=390, h=844, theme="dark", iphone=False, js=True):
    kw = {"viewport": {"width": w, "height": h}, "java_script_enabled": js}
    if iphone:
        kw.update(user_agent=IPHONE, is_mobile=True, has_touch=True)
    ctx = browser.new_context(**kw)
    ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', '{theme}'); }} catch (e) {{}}")
    page = ctx.new_page()
    errs: list[str] = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(url)
    if js and url.endswith("/"):                    # the story page: wait for the engine
        page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')",
                               timeout=10000)
    page.wait_for_timeout(300)
    page._b6_errs = errs  # type: ignore[attr-defined]
    return ctx, page


def _shown(page, sel):
    return page.evaluate("(s) => { const e = document.querySelector(s); if (!e) return false;"
                         " const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0"
                         " && getComputedStyle(e).visibility !== 'hidden'; }", sel)


def _is_open(page):
    return page.evaluate("(s) => document.querySelector(s).open", DLG)


def _rest(page, i, timeout=15000):
    page.wait_for_function(
        "(i) => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === i && s.dest === i; }",
        arg=i, timeout=timeout)
    page.wait_for_timeout(250)


# ---- where the button shows ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("width", [390, 800])
def test_button_visible_rail_hidden(site_url, browser, width):
    ctx, page = _open(browser, site_url + "/", w=width, h=900)
    try:
        assert not _shown(page, ".story-nav"), "the rail shows at this width"
        assert _shown(page, ".site-header [data-menu-slot] " + BTN), "no menu button in the bar's slot"
        assert page.get_attribute(BTN, "aria-expanded") == "false"
        assert page.get_attribute(BTN, "aria-controls") == "fe-menu"
        assert not page._b6_errs, page._b6_errs
    finally:
        ctx.close()


@pytest.mark.parametrize("width", [1024, 1280])
def test_button_hidden_where_rail_and_links_show(site_url, browser, width):
    ctx, page = _open(browser, site_url + "/", w=width, h=900)
    try:
        assert page.evaluate("() => { const n = document.querySelector('.story-nav'); return !n.hidden && getComputedStyle(n).display !== 'none'; }"), \
            "the rail is hidden at this width"  # (it draws in after the first arrival: visibility is B5's)
        assert _shown(page, '.site-header .nav > a[href="/tour/"]') and _shown(page, '.site-header .nav > a[href="/pricing"]')
        assert not _shown(page, BTN), "the menu button shows beside the rail"
    finally:
        ctx.close()


SHOWN = """() => [...document.querySelectorAll('.site-header .brand, .site-header .nav > a, .site-header .nav > button,'
  + ' .site-header .fe-menu-btn')].filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden')
  .map(e => e.matches('.brand') ? 'logo' : e.matches('[data-menu-open]') ? 'menu' : e.matches('[data-theme-toggle]') ? 'theme'
       : e.matches('[data-dl]') ? 'download' : e.textContent.trim())"""


@pytest.mark.parametrize("path", [p for p in SHELL_PAGES if p != "/"])
@pytest.mark.parametrize("width,want", [(390, True), (800, False), (1280, False)])
def test_button_on_doc_pages_only_where_links_drop(site_url, browser, path, width, want):
    ctx, page = _open(browser, site_url + path, w=width, h=900)
    try:
        shown = page.evaluate(SHOWN)
        if want:
            assert shown == ["logo", "download", "theme", "menu"], (path, shown)
        else:
            assert shown == ["logo", "How it works", "Pricing", "download", "theme"], (path, shown)
            assert page.evaluate("() => getComputedStyle(document.querySelector('[data-menu-slot]')).display") == "none"
    finally:
        ctx.close()


# ---- the bar still fits ----------------------------------------------------------------------------------------------

FIT = """() => {
  const sh = document.querySelector('.site-header .shell');
  const els = [...sh.querySelectorAll('.brand, .nav > a, .nav > button, .fe-menu-btn')]
    .filter(e => e.getClientRects().length && getComputedStyle(e).display !== 'none');
  return { vw: innerWidth, docw: document.documentElement.scrollWidth,
    items: els.map(e => { const b = e.getBoundingClientRect();
      const txt = e.querySelector('span') && e.classList.contains('brand') ? e.querySelector('span') : e;
      return { k: e.matches('.brand') ? 'brand' : e.matches('[data-menu-open]') ? 'menu'
               : e.matches('[data-theme-toggle]') ? 'theme' : e.matches('[data-dl]') ? 'download' : e.textContent.trim(),
               l: b.left, r: b.right, cy: b.top + b.height / 2, h: b.height,
               sw: txt.scrollWidth, cw: txt.clientWidth, label: e.textContent.trim() }; }) };
}"""


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("width", [360, 375, 390])
def test_bar_fits(site_url, browser, width, theme):
    for path in ["/", "/pricing.html"]:
        for iphone in (True, False):
            ctx, page = _open(browser, site_url + path, w=width, h=740, theme=theme, iphone=iphone)
            try:
                m = page.evaluate(FIT)
                where = f"{path} @{width} {theme} {'iphone' if iphone else 'desktop'}: {m}"
                keys = [i["k"] for i in m["items"]]
                assert keys == ["brand", "download", "theme", "menu"], where
                dl = m["items"][1]
                assert dl["label"] == ("Get it on Mac" if iphone else "Download"), where
                assert m["docw"] <= m["vw"], "the page is wider than the viewport: " + where
                cy = m["items"][0]["cy"]
                for a in m["items"]:
                    assert abs(a["cy"] - cy) <= 3, f"{a['k']} wrapped off the row: {where}"
                    assert a["h"] <= 44, f"{a['k']} grew to two lines: {where}"
                    if a["k"] in ("brand", "download"):          # (the icon buttons' 44 px ::after hit area is not text)
                        assert a["sw"] <= a["cw"] + 0.5, f"{a['k']} is clipped or truncated: {where}"
                    assert a["l"] >= 0 and a["r"] <= m["vw"], f"{a['k']} runs past the viewport: {where}"
                for a, b in zip(m["items"], m["items"][1:]):
                    assert a["r"] <= b["l"] + 0.5, f"{a['k']} overlaps {b['k']}: {where}"
            finally:
                ctx.close()


DESKTOP_UAS = {
    "mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "win": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
}

# every item of the bar, left to right, with its text's own box (Range) so a word spilling out of its box shows
SWEEP = """() => {
  const sh = document.querySelector('.site-header .shell');
  const els = [...sh.querySelectorAll('.brand, .nav > a, .nav > button, .dl-note, .fe-menu-btn')]
    .filter(e => e.getClientRects().length && getComputedStyle(e).display !== 'none' && getComputedStyle(e).visibility !== 'hidden');
  const items = els.map(e => { const b = e.getBoundingClientRect();
    let tl = b.left, tr = b.right;
    if (!e.matches('.fe-menu-btn, [data-theme-toggle]')) { const r = document.createRange(); r.selectNodeContents(e);
      const t = r.getBoundingClientRect(); tl = t.left; tr = t.right; }
    return { k: e.matches('.brand') ? 'brand' : e.matches('[data-menu-open]') ? 'menu' : e.matches('[data-theme-toggle]') ? 'theme'
      : e.matches('[data-dl]') ? 'download' : e.matches('.dl-note') ? 'note' : e.textContent.trim(),
      l: b.left, r: b.right, h: b.height, tl, tr, cy: b.top + b.height / 2 }; }).sort((a, b) => a.l - b.l);
  return { vw: innerWidth, docw: document.documentElement.scrollWidth, items };
}"""


def _sweep_problems(m):
    out = []
    if m["docw"] > m["vw"]:
        out.append("page wider than viewport")
    for a in m["items"]:
        if a["tl"] < a["l"] - 0.5 or a["tr"] > a["r"] + 0.5:
            out.append(f"{a['k']} text spills its box ({a['tl']:.0f}-{a['tr']:.0f} vs {a['l']:.0f}-{a['r']:.0f})")
        if a["h"] > 44:
            out.append(f"{a['k']} grew to {a['h']:.0f} px")
        if a["l"] < 0 or a["r"] > m["vw"]:
            out.append(f"{a['k']} runs past the viewport")
    for a, b in zip(m["items"], m["items"][1:]):
        if a["r"] > b["l"] + 0.5 or a["tr"] > b["tl"] + 0.5:
            out.append(f"{a['k']} overlaps {b['k']}")
    return out


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("os_", ["mac", "win"])
@pytest.mark.parametrize("path", ["/", "/pricing.html"])
def test_bar_sweep_600_to_1023(site_url, browser, path, os_, theme):
    """Every 8 px from 600 to 1023 (and 1023): no bar item clips, overlaps or truncates, on a Mac and a Windows desktop."""
    ctx = browser.new_context(viewport={"width": 1100, "height": 800}, user_agent=DESKTOP_UAS[os_])
    ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', '{theme}'); }} catch (e) {{}}")
    page = ctx.new_page()
    try:
        page.goto(site_url + path)
        if path == "/":
            page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')", timeout=10000)
        page.wait_for_timeout(500)
        bad = {}
        for w in list(range(600, 1024, 8)) + [1023]:
            page.set_viewport_size({"width": w, "height": 800})
            page.wait_for_timeout(60)
            probs = _sweep_problems(page.evaluate(SWEEP))
            if probs:
                bad[w] = probs
        assert not bad, f"{path} {os_} {theme}: {bad}"
    finally:
        ctx.close()


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("os_", ["mac", "win"])
@pytest.mark.parametrize("width", [640, 660, 672, 700])
def test_bar_fits_desktop_home(site_url, browser, width, os_, theme):
    ctx = browser.new_context(viewport={"width": width, "height": 800}, user_agent=DESKTOP_UAS[os_])
    ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', '{theme}'); }} catch (e) {{}}")
    page = ctx.new_page()
    try:
        page.goto(site_url + "/")
        page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')", timeout=10000)
        page.wait_for_timeout(500)
        m = page.evaluate(SWEEP)
        assert not _sweep_problems(m), (width, os_, theme, _sweep_problems(m), m)
        keys = [i["k"] for i in m["items"]]
        assert keys[0] == "brand" and "menu" in keys and keys[-1] == "menu" or "theme" in keys, keys
    finally:
        ctx.close()


@pytest.mark.parametrize("width", [360, 375])
def test_theme_and_menu_centres_40_apart(site_url, browser, width):
    ctx, page = _open(browser, site_url + "/", w=width, h=740, iphone=True)
    try:
        c = page.evaluate("() => ['[data-theme-toggle]', '[data-menu-open]'].map(s => { const b = document.querySelector(s).getBoundingClientRect(); return b.left + b.width / 2; })")
        assert c[1] - c[0] >= 40, c
    finally:
        ctx.close()


def test_sheet_marks_the_current_page(site_url, browser):
    ctx, page = _open(browser, site_url + "/pricing.html", w=390, h=844)
    try:
        cur = page.evaluate("() => [...document.querySelectorAll('#fe-menu .fe-menu-site a[aria-current]')].map(a => [a.textContent.trim(), a.getAttribute('aria-current'), a.classList.contains('is-current')])")
        assert cur == [["Pricing", "page", True]], cur
    finally:
        ctx.close()
    ctx, page = _open(browser, site_url + "/install.html", w=390, h=844)
    try:
        assert page.evaluate("() => document.querySelectorAll('#fe-menu .fe-menu-site a[aria-current]').length") == 0
    finally:
        ctx.close()


# ---- the dialog --------------------------------------------------------------------------------------------------------

FOCUS_IN = "(s) => !!document.activeElement && document.querySelector(s).contains(document.activeElement)"


def test_dialog_focus_trap_esc_returns_focus(site_url, browser):
    ctx, page = _open(browser, site_url + "/", w=390, h=844)
    try:
        _rest(page, 0)
        before = page.evaluate("() => ({ y: scrollY, s: JSON.stringify(FEStory.state()) })")
        # Safari never focuses a tapped button: open with focus on <body>, so only the sheet can bring it back
        page.evaluate("(s) => { document.activeElement && document.activeElement.blur(); document.querySelector(s).click(); }", BTN)
        assert _is_open(page) and page.get_attribute(BTN, "aria-expanded") == "true"
        assert page.evaluate(FOCUS_IN, DLG), "opening did not move focus into the sheet"
        n = page.evaluate("(s) => [...document.querySelector(s).querySelectorAll('a[href], button')]"
                          ".filter(e => e.getClientRects().length).length", DLG)
        assert n >= 4
        first = page.evaluate("() => document.activeElement.outerHTML")
        seen = set()
        for _ in range(n + 2):                      # all the way round and past the start
            page.keyboard.press("Tab")
            assert page.evaluate(FOCUS_IN, DLG), "Tab left the sheet"
            seen.add(page.evaluate("() => document.activeElement.outerHTML"))
        assert len(seen) == n, f"Tab did not visit every control once round: {len(seen)} of {n}"
        page.focus(DLG + " .fe-menu-panel a[href]")
        page.keyboard.press("Shift+Tab")
        assert page.evaluate(FOCUS_IN, DLG), "Shift+Tab left the sheet"
        assert page.evaluate("(s) => document.activeElement === document.querySelector(s + ' [data-menu-close]')", DLG), \
            "Shift+Tab from the first control did not wrap to the last"
        # the page and the story hold still under the open sheet; the bar's theme toggle still works
        page.mouse.move(195, 700)
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(500)
        page.keyboard.press("PageDown")
        page.wait_for_timeout(500)
        now = page.evaluate("() => ({ y: scrollY, s: JSON.stringify(FEStory.state()) })")
        assert now["y"] == before["y"], "the page scrolled under the open sheet"
        assert page.evaluate("() => getComputedStyle(document.documentElement).overflowY") == "hidden"
        assert page.evaluate("() => { const s = FEStory.state(); return s.rendered === 0 && s.dest === 0; }"), now
        t0 = page.get_attribute("html", "data-theme")
        page.click(".site-header [data-theme-toggle]")
        page.wait_for_timeout(700)
        assert page.get_attribute("html", "data-theme") != t0 and _is_open(page), "the theme toggle broke with the sheet open"
        # the click left focus on the bar's toggle: Tab and Shift+Tab come straight back into the sheet
        page.keyboard.press("Tab")
        assert page.evaluate(FOCUS_IN, DLG), "Tab escaped the sheet from the bar's theme toggle"
        page.focus(".site-header [data-theme-toggle]")
        page.keyboard.press("Shift+Tab")
        assert page.evaluate(FOCUS_IN, DLG), "Shift+Tab escaped the sheet from the bar's theme toggle"
        # Escape closes it and focus goes back to the button
        page.keyboard.press("Escape")
        assert not _is_open(page) and page.get_attribute(BTN, "aria-expanded") == "false"
        assert page.evaluate("(s) => document.activeElement === document.querySelector(s)", BTN), \
            "focus did not return to the menu button"
        assert page.evaluate("() => getComputedStyle(document.documentElement).overflowY") != "hidden"
        assert page.evaluate("() => [...document.body.children].every(e => !e.inert)")
        # the Close control does the same
        page.evaluate("(s) => { document.activeElement.blur(); document.querySelector(s).click(); }", BTN)
        assert _is_open(page)
        page.click(DLG + " [data-menu-close]")
        assert not _is_open(page)
        assert page.evaluate("(s) => document.activeElement === document.querySelector(s)", BTN)
        assert first  # noqa: the first focus target existed
        assert not page._b6_errs, page._b6_errs
    finally:
        ctx.close()


# ---- chapter taps ----------------------------------------------------------------------------------------------------

PICK = """(want) => {
  const d = FEStory.destinations, r = FEStory.state().rendered;
  if (want === 'pinned') { for (let i = d.length - 1; i >= 0; i--) if (d[i].kind === 'pinned' && Math.abs(i - r) >= 2) return i; }
  else { for (let i = 0; i < d.length; i++) if (d[i].kind === 'native') return i; }
  return -1;
}"""


@pytest.mark.parametrize("kind", ["pinned", "native"])
@pytest.mark.parametrize("width,height", [(390, 844), (800, 1000)])
def test_tap_closes_and_lands(site_url, browser, width, height, kind):
    ctx, page = _open(browser, site_url + "/", w=width, h=height)
    try:
        page.evaluate("() => { window.__b6hash = 0; addEventListener('hashchange', () => { __b6hash++; }); }")
        i = page.evaluate(PICK, kind)
        assert i >= 0, f"no {kind} row at {width}: {page.evaluate('() => FEStory.destinations.map(d => d.kind)')}"
        row = page.evaluate("(i) => FEStory.destinations[i]", i)
        page.click(BTN)
        assert _is_open(page)
        page.click(f'{DLG} .fe-menu-chapters a[data-go="{row["beat"]}"]')
        assert not _is_open(page), "the sheet stayed open after a chapter tap"
        assert page.evaluate("(s) => document.activeElement === document.querySelector(s)", BTN)
        if kind == "pinned":
            _rest(page, i)
        else:
            page.wait_for_function(
                """(a) => { const r = document.getElementById(a).getBoundingClientRect();
                   const hh = document.querySelector('.site-header').getBoundingClientRect().height;
                   return Math.abs(r.top - hh) <= 4; }""", arg=row["anchor"], timeout=8000)
            page.wait_for_timeout(400)
            assert page.evaluate("() => document.querySelector('.story-nav a[aria-current=\"location\"]').dataset.go") == row["beat"]
        assert page.evaluate("() => __b6hash") == 0, "the menu changed the hash itself"
        assert not page._b6_errs, page._b6_errs
    finally:
        ctx.close()


# ---- one source with the rail ------------------------------------------------------------------------------------------

LISTS = """(s) => ({
  dests: FEStory.destinations.map(d => [d.beat, d.name, '#' + d.anchor]),
  page: [...FEStory.destinations.filter(d => d.kind === 'pinned'), ...FEStory.destinations.filter(d => d.kind !== 'pinned')]
          .map(d => [d.beat, d.name, '#' + d.anchor]),
  rail: [...document.querySelectorAll('.story-nav a[data-go]')].map(a => [a.dataset.go, a.dataset.name, a.getAttribute('href')]),
  menu: [...document.querySelectorAll(s + ' .fe-menu-chapters a[data-go]')].map(a => [a.dataset.go,
          a.cloneNode(true).childNodes[0].textContent, a.getAttribute('href')]),
  cur: [...document.querySelectorAll(s + ' .fe-menu-chapters a.is-current')].map(a => a.dataset.go),
  railCur: (document.querySelector('.story-nav a[aria-current="location"]') || {}).dataset?.go || null,
  ariaInMenu: document.querySelectorAll(s + ' [aria-current]').length,
})"""


def _same_rows(got, width):
    """(SCRUB stage 1 / ICX-SCRUB.8) the sheet lists the chapters in PAGE order: the pinned story's rows, then the native
    sections after it. Where every native row already follows the pinned ones (the desktop, the 800 px tablet layout)
    that is the rail's own order, row for row; on a phone (< 640) Get the app (pinned) comes before Price and A note."""
    assert got["menu"] == got["page"], got
    assert sorted(got["menu"]) == sorted(got["dests"]) == sorted(got["rail"]), got
    if width >= 640:
        assert got["menu"] == got["dests"] == got["rail"], got
    else:
        assert [r[0] for r in got["menu"]][-3:] == ["end", "price", "note"], got


@pytest.mark.parametrize("width", [390, 800])
def test_same_list_as_rail(site_url, browser, width):
    ctx, page = _open(browser, site_url + "/", w=width, h=900)
    try:
        page.evaluate("() => FEStory.goTo(3, { source: 'jump' })")
        _rest(page, 3)
        page.click(BTN)
        got = page.evaluate(LISTS, DLG)
        assert len(got["dests"]) == 9
        _same_rows(got, width)
        assert got["cur"] == [got["railCur"]] == [got["dests"][3][0]], got
        assert got["ariaInMenu"] == 0, "the sheet wrote aria-current (rail.js is its only writer, ICX-HL.5)"
        page.keyboard.press("Escape")
        # a landing under the open sheet (a step still running when it opened) moves its current marker
        page.evaluate("(s) => { FEStory.goTo(4, { source: 'jump' }); document.querySelector(s).click(); }", BTN)
        assert _is_open(page)
        _rest(page, 4)
        got = page.evaluate(LISTS, DLG)
        assert got["cur"] == [got["railCur"]] == [got["dests"][4][0]], got
        page.keyboard.press("Escape")
        # a mode change re-reads the source: still row for row
        page.set_viewport_size({"width": 800 if width == 390 else 390, "height": 900})
        page.wait_for_timeout(900)
        page.click(BTN)
        got = page.evaluate(LISTS, DLG)
        _same_rows(got, 800 if width == 390 else 390)
    finally:
        ctx.close()
    src = (ROOT / "assets" / "site" / "shell.js").read_text()
    assert "FEStory.destinations" in src or "F.destinations" in src
    assert not re.search(r"aria-current", re.sub(r"//[^\n]*|/\*.*?\*/", "", src, flags=re.S)
                         .replace('a[aria-current="location"]', "")
                         .replace('setAttribute("aria-current", "page")', "")),  \
        "shell.js writes aria-current (only the sheet's own page link may: aria-current=page)"  # (chapters: ICX-HL.5)


# ---- every shell page --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("path", SHELL_PAGES)
def test_site_links_on_every_shell_page(site_url, browser, path):
    html = (ROOT / (path.strip("/") or "index.html")).read_text()
    assert html.count('id="fe-menu"') == 1 and html.count('class="fe-menu-btn"') == 1, path
    ctx, page = _open(browser, site_url + path, w=390, h=844)
    try:
        assert _shown(page, ".site-header [data-menu-slot] " + BTN), path
        page.click(BTN)
        assert _is_open(page)
        links = page.evaluate("""(s) => [...document.querySelectorAll(s + ' .fe-menu-site a')]
            .filter(a => a.getClientRects().length).map(a => [a.textContent.trim(), a.getAttribute('href')])""", DLG)
        assert links == [["How it works", "/tour/"], ["Pricing", "/pricing"]], (path, links)
        assert _shown(page, DLG + " .fe-menu-chapters") is (path == "/"), path
        page.keyboard.press("Escape")
    finally:
        ctx.close()
    if path == "/":                                 # at 800 the bar shows the links itself: the sheet holds the chapters
        ctx, page = _open(browser, site_url + "/", w=800, h=1000)
        try:
            page.click(BTN)
            assert not _shown(page, DLG + " .fe-menu-site") and _shown(page, DLG + " .fe-menu-chapters")
        finally:
            ctx.close()


def test_ad_pages_untouched():
    for name in AD_PAGES:
        html = (ROOT / name).read_text()
        assert "fe-menu" not in html and "data-menu-open" not in html, name


def test_signin_flagged(site_url, browser):
    ctx, page = _open(browser, site_url + "/pricing.html", w=390, h=844)
    try:
        a = page.evaluate("""(s) => { const a = document.querySelector(s + ' [data-flag="web-signup"]');
            return a && { hidden: a.hidden, href: a.getAttribute('href'), to: a.getAttribute('data-flag-href'), t: a.textContent.trim() }; }""", DLG)
        assert a == {"hidden": True, "href": None, "to": "/account", "t": "Sign in"}, a
    finally:
        ctx.close()
    # the flag on (shell.js served with web-signup true): shown with its href, exactly as the bar's
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    src = (ROOT / "assets" / "site" / "shell.js").read_text().replace('"web-signup": false', '"web-signup": true')
    ctx.route("**/assets/site/shell.js", lambda r: r.fulfill(status=200, content_type="text/javascript", body=src))
    page = ctx.new_page()
    try:
        page.goto(site_url + "/pricing.html")
        page.wait_for_timeout(300)
        page.click(BTN)
        got = page.evaluate("""(s) => [...document.querySelectorAll('[data-flag="web-signup"]')].map(a =>
            ({ inMenu: document.querySelector(s).contains(a), shown: a.getClientRects().length > 0, href: a.getAttribute('href') }))""", DLG)
        assert {"inMenu": True, "shown": True, "href": "/account"} in got, got
    finally:
        ctx.close()


# ---- axe and no JS -----------------------------------------------------------------------------------------------------

def _axe(page):
    page.add_script_tag(content=run_axe.axe_source())
    res = page.evaluate("axe.run(document, {resultTypes: ['violations']})")
    return [(v["id"], v["impact"], [n["target"] for n in v["nodes"][:3]])
            for v in res["violations"] if v.get("impact") in ("serious", "critical")]


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("path", ["/", "/pricing.html"])
def test_axe_menu(site_url, browser, path, theme):
    ctx, page = _open(browser, site_url + path, w=390, h=844, theme=theme)
    try:
        ctx.route("**/*", run_axe._local_only)
        closed = _axe(page)
        page.click(BTN)
        assert _is_open(page)
        page.wait_for_timeout(200)
        opened = _axe(page)
        assert not closed and not opened, {"closed": closed, "open": opened}
    finally:
        ctx.close()


def test_nojs_button_hidden(site_url, browser):
    ctx, page = _open(browser, site_url + "/", w=390, h=844, js=False)
    try:
        assert not _shown(page, BTN), "a dead menu button shows without JS"
    finally:
        ctx.close()
