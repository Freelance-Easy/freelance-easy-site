"""TOUR (2026-10-17): /tour/ on the site's shell, with the chapters as rail-style navigation.

- The page is generated (src/pages/tour/index.html, declared in src/pages.txt) and carries the shared head, bar, menu
  sheet and footer byte for byte, the bar a direct child of <body>; classic.js wires the bar to the tour by data-page.
- The chapter list: the seven names, nothing else (no "01 / 07" counter anywhere in the stage), one aria-current, the
  current name brighter and a step bigger.
- No empty frame at load: the poster (a play button over the tour's last screen) is up from the first paint; the frame
  holds a real screen once ready. The first play or chapter pick takes the poster down; Space plays and pauses.
- Classic: no poster, no play button, each chapter its end state.
- The end: the end card (Watch again, Get the app) over the frame, and the page's Get the app section.
- axe: no serious or critical violation in the poster and the end states, both themes.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUILT = ROOT / "tour" / "index.html"
NAMES = ["Sign in", "Your name", "Dashboard", "Invoices", "New invoice", "Email", "Paid"]
ENDS = [8, 20, 28, 40, 62, 72, 80]
COUNTER = re.compile(r"\d+\s*/\s*\d+")
READY = "() => window.__tour && window.__tour.ready"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


run_axe = _load("run_axe", "scripts/checks/run_axe.py")


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _page(browser, site_url, w=1440, theme="dark", classic=None, wait_ready=True):
    ctx = browser.new_context(viewport={"width": w, "height": 900 if w > 600 else 844})
    ctx.route("**/dl/**", lambda r: r.abort())
    ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', '{theme}'); }} catch (e) {{}}")
    if classic is not None:
        ctx.add_init_script(f"try {{ localStorage.setItem('fe-classic', '{classic}'); }} catch (e) {{}}")
    page = ctx.new_page()
    page._errs = []
    page.on("pageerror", lambda e: page._errs.append(str(e)))
    page.goto(site_url + "/tour/", wait_until="domcontentloaded")
    if wait_ready:
        page.wait_for_function(READY, timeout=20000)
    return ctx, page


def _partial(name: str) -> str:
    return (ROOT / "src" / "partials" / name).read_text(encoding="utf-8").replace("{{dl_fallback}}", "/install")


def test_shell_present():
    html = BUILT.read_text(encoding="utf-8")
    for name in ("head.html", "header.html", "menu.html", "footer.html"):
        assert _partial(name) in html, name
    assert "tour/index.html" in [ln.strip() for ln in (ROOT / "src" / "pages.txt").read_text().splitlines()]
    assert (ROOT / "src" / "pages" / "tour" / "index.html").is_file()
    # the bar is a direct child of <body> (sticky; shell.js keeps body > .site-header live under the menu sheet)
    assert re.search(r'<body data-page="tour">\s*(<!--.*?-->\s*)*<header class="site-header">', html, re.S)
    assert html.count("<header") == 1 and html.count("<footer") == 1
    assert '<body data-page="tour">' in html
    assert html.index("<header") < html.index("<main") < html.index("<footer")


@pytest.mark.parametrize("w", [1440, 390])
def test_shell_rendered(site_url, browser, w):
    ctx, page = _page(browser, site_url, w=w)
    try:
        assert page.locator(".site-header").is_visible()
        assert page.locator(".site-header .brand").is_visible()
        assert page.locator("footer.site-footer").count() == 1
        # the bar's Classic switch is the tour's (classic.js: data-page="tour")
        assert page.locator(".site-header .classic-toggle").count() == 1
        assert page.locator(".back").count() == 0          # the old corner link is gone: the brand goes home
        assert not page._errs, page._errs
    finally:
        ctx.close()


@pytest.mark.parametrize("w", [1440, 820, 390])
def test_chapter_nav(site_url, browser, w):
    ctx, page = _page(browser, site_url, w=w)
    try:
        nav = page.locator("nav.tour-steps[aria-label='Tour chapters']")
        assert nav.count() == 1
        assert [t.strip() for t in nav.locator("button").all_inner_texts()] == NAMES
        # no counters anywhere in the stage: names only
        stage = page.inner_text(".tour-stage")
        assert not COUNTER.search(re.sub(r"\d+:\d\d / \d+:\d\d", "", stage)), stage
        assert page.locator("#caption-number").count() == 0
        for k in (3, 6, 0):
            page.evaluate("k => __tour.jump(k)", k)
            page.wait_for_timeout(500)   # the name eases to its current look (240 ms)
            cur = nav.locator("[aria-current]")
            assert cur.count() == 1 and cur.inner_text().strip() == NAMES[k], k
            assert page.inner_text("#caption-title").strip() == NAMES[k]
            st = page.evaluate("""k => { const b = [...document.querySelectorAll('[data-chapter]')];
                const cur = b[k], idle = b[(k + 1) % b.length];
                const s = el => getComputedStyle(el);
                return { cc: s(cur).color, ic: s(idle).color, cs: s(cur.querySelector('.nm')).scale,
                         is: s(idle.querySelector('.nm')).scale, cw: s(cur).fontWeight, iw: s(idle).fontWeight }; }""", k)
            assert st["cc"] != st["ic"], st                      # brighter
            assert float(st["cs"]) > 1 and st["is"] in ("none", "1"), st   # a step bigger
            # the current name is on screen (the row scrolls sideways on a phone)
            box, vw = cur.bounding_box(), page.viewport_size["width"]
            assert box["x"] >= 0 and box["x"] + box["width"] <= vw, (k, box)
        assert not page._errs, page._errs
    finally:
        ctx.close()


@pytest.mark.parametrize("w", [1440, 390])
def test_no_empty_frame_at_load(site_url, browser, w):
    ctx, page = _page(browser, site_url, w=w, wait_ready=False)
    try:
        # from the first paint: the poster's play button, visible and sized, over the frame
        btn = page.locator("#poster-play")
        assert btn.is_visible()
        box = btn.bounding_box()
        assert box["width"] >= 44 and box["height"] >= 44
        page.wait_for_function(READY, timeout=20000)
        page.wait_for_timeout(300)
        assert page.locator("#poster:not(.is-gone)").is_visible()
        # behind it, a real screen: the tour's last one (the updated dashboard), not an empty frame
        n = page.evaluate("() => document.getElementById('app-frame').contentDocument.querySelectorAll('#screen *').length")
        assert n > 50, n
        assert page.evaluate("() => !!document.getElementById('app-frame').contentDocument.querySelector('#screen .kpi-value')")
        st = page.evaluate("() => __tour.state()")
        assert st["t"] == 0 and st["chapter"] == 0 and not st["playing"], st
        assert page.inner_text("#time").strip() == "0:00 / 1:20"
        # the chapter row shows Sign in as current, in view (the poster's paint of the last screen must not move it)
        page.wait_for_timeout(600)
        row, cur = page.locator("#chapters").bounding_box(), page.locator("#chapters [aria-current]").bounding_box()
        assert page.inner_text("#chapters [aria-current]").strip() == "Sign in"
        assert cur["x"] >= row["x"] - 1 and cur["x"] + cur["width"] <= row["x"] + row["width"] + 1, (row, cur)
        # a click on the poster plays from Sign in and takes the poster down
        page.click("#poster-play")
        page.wait_for_function("() => __tour.state().playing && __tour.state().t > 0.2")
        assert page.locator("#poster.is-gone").count() == 1
        assert page.evaluate("() => !!document.getElementById('app-frame').contentDocument.querySelector('#screen #login-state, #screen #waiting-state')")
        assert not page._errs, page._errs
    finally:
        ctx.close()


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("w", [1440, 390])
def test_fictional_label_quiet(site_url, browser, w, theme):
    """(main CONTRACT 2026-10-17, Daniel) the frame's "Fictional data": the same words, always shown, plain --text-2 with
    no chip or backing, >= 12.5 px, not hidden from screen readers (contrast measured on pixels: TOUR report)."""
    ctx, page = _page(browser, site_url, w=w, theme=theme)
    try:
        for step in (None, 4):
            if step is not None:
                page.evaluate("k => __tour.jump(k)", step)
            el = page.locator(".frame-top .fictional")
            assert el.inner_text().strip() == "Fictional data" and el.is_visible()
            st = el.evaluate("""e => { const s = getComputedStyle(e), probe = document.createElement('span');
                probe.style.color = 'var(--text-2)'; document.body.appendChild(probe);
                const want = getComputedStyle(probe).color; probe.remove();
                return { c: s.color, want, fs: parseFloat(s.fontSize), bg: s.backgroundColor, op: s.opacity,
                         hidden: !!e.closest('[aria-hidden="true"]') }; }""")
            assert st["c"] == st["want"], st
            assert st["fs"] >= 12.5 and st["bg"] in ("rgba(0, 0, 0, 0)", "transparent") and st["op"] == "1", st
            assert not st["hidden"], st
    finally:
        ctx.close()


def test_space_plays(site_url, browser):
    ctx, page = _page(browser, site_url)
    try:
        page.locator("body").click(position={"x": 5, "y": 400})
        page.keyboard.press("Space")
        page.wait_for_function("() => __tour.state().playing")
        assert page.locator("#poster.is-gone").count() == 1
        assert page.get_attribute("#play", "aria-label") == "Pause tour"
        page.keyboard.press("Space")
        page.wait_for_function("() => !__tour.state().playing")
        assert page.get_attribute("#play", "aria-label") == "Play tour"
        # a chapter pick takes the poster down as well (on a fresh page)
        assert not page._errs, page._errs
    finally:
        ctx.close()


def test_bar_sticky_and_live_under_menu(site_url, browser):
    """(Sol TOUR-1) the bar stays at the top as the page scrolls, and stays live (not inert) while the menu sheet is open."""
    ctx, page = _page(browser, site_url, w=390)
    try:
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(200)
        box = page.locator(".site-header").bounding_box()
        assert abs(box["y"]) < 1 and page.locator(".site-header .brand").is_visible(), box
        page.click("[data-menu-open]")
        page.wait_for_selector("#fe-menu[open]")
        assert page.evaluate("() => !document.querySelector('.site-header').closest('[inert]')")
        page.click("[data-menu-open]")   # the bar's own button closes the sheet again
        page.wait_for_function("() => !document.querySelector('#fe-menu[open]')")
    finally:
        ctx.close()


def test_space_on_controls(site_url, browser):
    """(Sol TOUR-1) Space on a focused control is that control's (a chapter is picked, not playback toggled); with the
    menu sheet open, Space never starts the tour."""
    ctx, page = _page(browser, site_url)
    try:
        page.focus('[data-chapter="3"]')
        page.keyboard.press("Space")
        page.wait_for_timeout(200)
        st = page.evaluate("() => __tour.state()")
        assert st["chapter"] == 3 and not st["playing"], st
        page.set_viewport_size({"width": 390, "height": 844})
        page.click("[data-menu-open]")
        page.wait_for_selector("#fe-menu[open]")
        page.keyboard.press("Space")
        page.wait_for_timeout(200)
        assert not page.evaluate("() => __tour.state().playing")
    finally:
        ctx.close()


def test_chapter_pick_ends_poster(site_url, browser):
    ctx, page = _page(browser, site_url)
    try:
        page.click('[data-chapter="2"]')
        assert page.locator("#poster.is-gone").count() == 1
        assert page.evaluate("() => __tour.state().chapter") == 2
    finally:
        ctx.close()


def test_classic_end_states(site_url, browser):
    ctx, page = _page(browser, site_url, classic="1")
    try:
        assert page.get_attribute(".site-header .classic-toggle", "aria-pressed") == "true"
        assert page.locator("#poster.is-gone").count() == 1 and page.is_hidden("#play")
        for k in range(7):
            page.click(f'[data-chapter="{k}"]')
            st = page.evaluate("() => __tour.state()")
            assert st["chapter"] == k and not st["playing"] and abs(st["t"] - (ENDS[k] - 0.001)) < 1e-6, (k, st)
        page.keyboard.press("Space")
        page.wait_for_timeout(200)
        assert not page.evaluate("() => __tour.state().playing")
        assert page.is_hidden("#end-card")
    finally:
        ctx.close()


def _end(page):
    page.evaluate("() => { __tour.jump(6); __tour.play(); }")
    page.wait_for_function("() => __tour.state().t >= __tour.state().total", timeout=20000)
    page.wait_for_timeout(400)


def test_end_card_and_next_step(site_url, browser):
    ctx, page = _page(browser, site_url)
    try:
        _end(page)
        assert page.is_visible("#end-card") and page.is_hidden("#play")
        assert page.inner_text("#replay").strip() == "Watch again"
        link = page.locator("#end-card a")
        assert link.inner_text().strip() == "Get the app" and link.get_attribute("href") == "#get-the-app"
        end = page.locator("#get-the-app")
        assert end.locator("[data-dl] a[data-role='primary']").count() == 1
        assert end.locator("a[href='/pricing']").count() == 1
        page.click("#replay")
        page.wait_for_function("() => __tour.state().playing && __tour.state().t < 5")
        assert page.is_hidden("#end-card")
    finally:
        ctx.close()


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_axe_poster_and_end(site_url, browser, theme):
    found = []
    for w in (1440, 390):
        ctx, page = _page(browser, site_url, w=w, theme=theme)
        try:
            ctx.route("**/*", run_axe._local_only)
            page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
            page.add_script_tag(content=run_axe.axe_source())
            for state in ("poster", "end"):
                if state == "end":
                    _end(page)
                res = page.evaluate("axe.run(document, {resultTypes: ['violations']})")
                found += [(w, state, v["id"], [n["target"] for n in v["nodes"][:3]]) for v in res["violations"]
                          if v.get("impact") in ("serious", "critical")]
        finally:
            ctx.close()
    assert found == [], found
