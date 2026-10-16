"""B4: the slim top bar on the homepage (DEC-1, decisions 2026-10-15 #7, #8, #23).

Site-level actions only: logo (/) · How it works (/tour/) · Pricing (/pricing) · Sign in (flagged web-signup, off) ·
Download (A9's control) · theme toggle · an empty [data-classic-slot] (K1) · an empty [data-menu-slot] (B6).
Sticky, never hides, 56 px at every width. No link in the bar jumps inside the story: the rail is the in-page menu
(B5). A9's Download keeps its own no-JS / phone fallback (#download, check-download-wiring.py's phone case); that is
A9's control, not a bar link, and with JS on a Mac or a Windows PC it is a real download (/dl/<os>/<campaign>).

Also here: the on-band hover of the Download pill (site.css `.nav a.nav-cta:hover`), readable (>= 4.5:1) on the
Ride's band in both themes.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
HEADER_SPAN = re.compile(r'<header class="site-header">.*?</header>\n', re.S)
MAC_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
HEIGHTS = {1440: 900, 1024: 768, 800: 900, 640: 800, 390: 844}
BAR_SELECTORS = ".site-header, .site-header .brand, .site-header .nav, .site-header .nav > *"

_spec = importlib.util.spec_from_file_location("fidelity", ROOT / "scripts" / "checks" / "fidelity.py")
fidelity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fidelity)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def open_page(browser, url, *, width=1440, theme="dark", js=True, route=None, ua=MAC_UA, init=None):
    ctx = browser.new_context(viewport={"width": width, "height": HEIGHTS.get(width, 900)}, color_scheme=theme,
                              java_script_enabled=js, user_agent=ua)
    ctx.add_init_script("try{localStorage.setItem('fe-theme','" + theme + "')}catch(e){}")
    if init:
        ctx.add_init_script(init)
    ctx.route("**/dl/**", lambda r: r.abort())  # never fetch a download
    if route:
        ctx.route(*route)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_timeout(500)
    assert errors == [], errors
    return ctx, page


def to_band(page):
    """Bring the story onto the Ride's band (html.on-band, not past it) with real wheel input. Since C3 the story moves
    by checkpoints (docs/interaction-contract.md): four wheel gestures from New invoice land on Email, where the band is
    the page. Each landing scrolls the page to its checkpoint's track position, so the bar is scrolled past too."""
    on = "() => { const c = document.documentElement.classList; return c.contains('on-band') && !c.contains('past-band'); }"
    vw = page.viewport_size
    page.mouse.move(vw["width"] / 2, vw["height"] * 0.6)
    page.wait_for_function("() => window.FEStory && FEStory.phase === 'rest'", timeout=15000)
    for _ in range(4):
        page.mouse.wheel(0, 100)
        page.wait_for_timeout(300)
    page.wait_for_function("() => { const s = FEStory.state(); return s.phase === 'rest' && s.beat === 'chase'; }", timeout=30000)
    page.wait_for_timeout(300)
    assert page.evaluate("() => scrollY") > 1000, "the wheel steps never scrolled the page"
    assert page.evaluate(on), "the story never put the header on the Ride's band"


def bar_items(page):
    """The bar's controls in document order: what each is, its target, and whether it shows."""
    return page.evaluate("""() => [...document.querySelectorAll(
        '.site-header .brand, .site-header .nav > a, .site-header .nav > button, .site-header [data-classic-slot],'
        + ' .site-header [data-menu-slot]')].map(e => ({
          key: e.matches('.brand') ? 'logo' : e.matches('[data-theme-toggle]') ? 'theme'
             : e.matches('[data-classic-slot]') ? 'classic-slot' : e.matches('[data-menu-slot]') ? 'menu-slot'
             : e.matches('[data-dl]') ? 'download' : e.matches('[data-flag="web-signup"]') ? 'signin'
             : e.textContent.trim(),
          href: e.getAttribute('href'), shown: !!e.offsetParent }))""")


# ---- order ---------------------------------------------------------------------------------------------------------

ORDER = ["logo", "How it works", "Pricing", "signin", "download", "theme", "classic-slot", "menu-slot"]


@pytest.mark.parametrize("width", [1440, 1024, 800, 640])
def test_item_order(site_url, browser, width):
    ctx, page = open_page(browser, site_url + "/", width=width)
    try:
        items = bar_items(page)
        assert [i["key"] for i in items] == ORDER, items
        by = {i["key"]: i for i in items}
        assert by["logo"]["href"] == "/" and by["How it works"]["href"] == "/tour/" and by["Pricing"]["href"] == "/pricing"
        assert by["download"]["href"].startswith("/dl/mac/"), by["download"]  # A9 on a Mac
        shown = [i["key"] for i in items if i["shown"]]
        # (B6) below the rail's 1024 px the menu button (its slot) shows at the bar's end; at 1024+ the slot takes no room.
        # (K1) the Classic switch fills its slot beside the theme toggle from 640 px (below, it is a row in B6's sheet)
        want = ["logo", "How it works", "Pricing", "download", "theme", "classic-slot"] + (["menu-slot"] if width < 1024 else [])
        assert shown == want, shown
        # "How it works" is a plain link to the full tour now (DEC-3), not the dialog's trigger
        assert page.locator(".site-header [data-tour-quick]").count() == 0
    finally:
        ctx.close()


def test_phone_bar(site_url, browser):
    """390: the logo, Download, the theme toggle and B6's menu button (the links moved into its sheet)."""
    ctx, page = open_page(browser, site_url + "/", width=390)
    try:
        items = bar_items(page)
        assert [i["key"] for i in items] == ORDER
        assert [i["key"] for i in items if i["shown"]] == ["logo", "download", "theme", "menu-slot"], items
    finally:
        ctx.close()


# ---- no in-story links ---------------------------------------------------------------------------------------------

def test_no_in_story_links(site_url, browser):
    span = HEADER_SPAN.findall((ROOT / "index.html").read_text(encoding="utf-8"))
    assert len(span) == 1
    hrefs = re.findall(r'<a\b[^>]*\bhref="([^"]*)"', span[0])
    # in the shipped bytes: no #how, #pricing or #top; the one #download is A9's Download fallback (no JS, phones)
    assert [h for h in hrefs if h.startswith("#")] == ["#download"], hrefs
    assert re.search(r'<a class="nav-cta" href="#download" data-dl\b', span[0]), "only A9's control keeps #download"
    for width in (1440, 800):
        ctx, page = open_page(browser, site_url + "/", width=width)
        try:
            live = page.evaluate("() => [...document.querySelectorAll('.site-header a[href]')].map(a => a.getAttribute('href'))")
            assert [h for h in live if h.startswith("#")] == [], live  # with JS on a Mac: none at all
        finally:
            ctx.close()


# ---- the web-signup flag -------------------------------------------------------------------------------------------

SIGNIN = '.site-header .nav > a[data-flag="web-signup"]'


def test_sign_in_hidden_without_flag(site_url, browser):
    """Web accounts are paused: Sign in ships hidden and inert (no href) with JS and without, at 1440 and 390."""
    for js in (True, False):
        for width in (1440, 390):
            ctx, page = open_page(browser, site_url + "/", width=width, js=js)
            try:
                link = page.locator(SIGNIN)
                assert link.count() == 1 and link.text_content().strip() == "Sign in"
                assert not link.is_visible() and link.get_attribute("href") is None, (js, width)
                assert link.get_attribute("data-flag-href") == "/account"
            finally:
                ctx.close()


def test_sign_in_shows_when_switch_on(site_url, browser):
    src = (ROOT / "assets" / "site" / "shell.js").read_text(encoding="utf-8")
    off = '"web-signup": false'
    assert src.count(off) == 1
    on = src.replace(off, '"web-signup": true')

    def serve(route):
        route.fulfill(status=200, content_type="application/javascript", body=on)

    ctx, page = open_page(browser, site_url + "/", route=("**/assets/site/shell.js", serve))
    try:
        assert page.locator(SIGNIN).is_visible() and page.locator(SIGNIN).get_attribute("href") == "/account"
        shown = [i["key"] for i in bar_items(page) if i["shown"]]
        assert shown == ["logo", "How it works", "Pricing", "signin", "download", "theme", "classic-slot"], shown
    finally:
        ctx.close()


# ---- 56 px, sticky, never hides ------------------------------------------------------------------------------------

BOX = """() => { const h = document.querySelector('.site-header'); const r = h.getBoundingClientRect(); const cs = getComputedStyle(h);
  const hit = document.elementFromPoint(innerWidth / 2, r.top + r.height / 2);
  return { top: r.top, h: r.height, pos: cs.position, vis: cs.visibility, op: cs.opacity, tf: cs.transform,
           onTop: !!hit && h.contains(hit), y: scrollY }; }"""


@pytest.mark.parametrize("width", [1440, 1024, 800, 640, 390])
def test_56px_sticky_never_hides(site_url, browser, width):
    ctx, page = open_page(browser, site_url + "/", width=width)
    try:
        seen = [page.evaluate(BOX)]
        for frac in (0.1, 0.35, 0.6, 0.85, 1.0):
            page.evaluate(f"() => window.scrollTo(0, document.documentElement.scrollHeight * {frac})")
            page.wait_for_timeout(500)
            seen.append(page.evaluate(BOX))
        page.evaluate("() => window.scrollBy(0, -400)")  # scrolling back up does not reveal a hidden bar: it never left
        page.wait_for_timeout(400)
        seen.append(page.evaluate(BOX))
        for s in seen:
            assert s["h"] == 56 and s["top"] == 0 and s["pos"] == "sticky", (width, s)
            assert s["vis"] == "visible" and s["op"] == "1" and s["tf"] == "none" and s["onTop"], (width, s)
        assert seen[-2]["y"] > 1000
    finally:
        ctx.close()


# ---- F7: no shift on theme toggle or scroll ------------------------------------------------------------------------

BAR_SHIFTS = """new PerformanceObserver(l => { window.__barShifts = window.__barShifts || [];
  for (const e of l.getEntries()) for (const s of (e.sources || []))
    if (s.node && s.node.closest && s.node.closest('.site-header'))
      window.__barShifts.push(Math.round(e.startTime) + 'ms ' + s.node.nodeName + '.' + s.node.className); })
  .observe({type: 'layout-shift', buffered: true}); window.__barShifts = window.__barShifts || [];"""


@pytest.mark.parametrize("width", [1440, 800, 390])
def test_bar_no_shift_theme_or_scroll(site_url, browser, width):
    """fidelity.py's F7 rect probe on the bar's boxes: identical across a theme toggle (the real button), across
    scrolling onto the Ride's band, and across a toggle on the band; and no layout shift comes from the bar."""
    ctx, page = open_page(browser, site_url + "/", width=width, init="(" + fidelity._CLS_JS + ")();" + BAR_SHIFTS)
    try:
        # geometry only: the label carries the class list, and the bar gains is-stuck once the page scrolls
        rects = lambda: [r[1:] for r in page.evaluate(fidelity._RECTS_JS, BAR_SELECTORS)]  # noqa: E731
        top = rects()
        assert len(top) >= 8
        # from here on: the load's own shifts (A9's note filling in at ~80 ms) are F7's CLS half, not this test's
        page.evaluate("() => { window.__barShifts = []; }")
        page.locator("[data-theme-toggle]").click()
        page.wait_for_timeout(900)
        assert rects() == top, "theme toggle"
        to_band(page)
        assert rects() == top, "scroll onto the band"
        page.locator("[data-theme-toggle]").click()
        page.wait_for_timeout(900)
        assert rects() == top, "theme toggle on the band"
        assert page.evaluate("() => window.__barShifts") == [], page.evaluate("() => window.__shifts")
    finally:
        ctx.close()


def test_fidelity_f7_bar_rects(site_url, browser):
    """fidelity.py's own F7 on `/`: its header/nav/toggle rects stay put across the theme switch (its CLS half is the
    base's known div.fx-shape finding, KNOWN_BASE_FAILS ("/", "F7"))."""
    ok, detail = fidelity.check_F7(browser, site_url + "/")
    assert not any("rects moved" in d for d in detail), detail


# ---- the slots and the menu stub -----------------------------------------------------------------------------------

@pytest.mark.parametrize("width", [1440, 390])
def test_slots_present(site_url, browser, width):
    ctx, page = open_page(browser, site_url + "/", width=width)
    try:
        for slot in ("[data-classic-slot]", "[data-menu-slot]"):
            el = page.locator(".site-header .nav > " + slot)
            assert el.count() == 1, slot
        # (K1) the slot holds the Classic switch and nothing else; it takes no room below 640 px, where the switch is a
        # row in B6's sheet (an empty slot still takes none: shell.css .fe-shell-slot:empty, checked on the doc pages by
        # tests/routes)
        classic = page.locator(".site-header .nav > [data-classic-slot]").evaluate("""e => ({
            only: e.children.length === 1 && e.children[0].matches('button.classic-toggle[data-classic-toggle]'),
            display: getComputedStyle(e).display })""")
        assert classic["only"], "something other than the Classic switch is in its slot"
        assert classic["display"] == ("none" if width < 640 else "flex"), classic
        # (B6) the menu slot holds the menu button and nothing else; it takes no room where the button is hidden (1440)
        menu = page.locator(".site-header .nav > [data-menu-slot]").evaluate("""e => ({
            only: e.childNodes.length === 1 && e.children.length === 1 && e.children[0].matches('button.fe-menu-btn[data-menu-open]'),
            display: getComputedStyle(e).display })""")
        assert menu["only"], "something other than the menu button is in the menu slot"
        assert menu["display"] == ("none" if width >= 1024 else "flex"), menu
        # K1's switch sits right beside the theme toggle
        assert page.evaluate("() => document.querySelector('.site-header [data-classic-slot]').previousElementSibling"
                             ".matches('[data-theme-toggle]')")
        # filled, the slot shows in line with the toggle
        if width >= 640:
            t = page.locator(".site-header [data-theme-toggle]").bounding_box()
            c = page.locator(".site-header .classic-toggle").bounding_box()
            assert c["x"] >= t["x"] + t["width"] and abs((c["y"] + c["height"] / 2) - (t["y"] + t["height"] / 2)) <= 2
    finally:
        ctx.close()


def test_menu_partial():
    """(B6) the phone/tablet menu partial is filled: the menu button and its sheet (tests/nav/test_menu.py covers it)."""
    part = re.sub(r"<!--.*?-->", "", (ROOT / "src" / "partials" / "menu.html").read_text(encoding="utf-8"), flags=re.S)
    assert part.count("data-menu-open") == 2 and '<dialog class="fe-menu" id="fe-menu"' in part


# ---- the on-band Download hover (site.css .nav a.nav-cta:hover) ----------------------------------------------------

CONTRAST = """(el) => {
  // computed colours come back as rgb()/rgba() (0-255) or, for color-mix(), as color(srgb r g b / a) (0-1)
  const rgba = (c) => { const m = c.match(/[\\d.]+/g).map(Number);
    return c.startsWith('color(') ? [m[0] * 255, m[1] * 255, m[2] * 255].concat(m.length > 3 ? [m[3]] : []) : m; };
  const lum = (m) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); };
  // composite the pill's fill over the first opaque background behind it (the header takes the band's colour)
  const layers = [];
  for (let n = el; n; n = n.parentElement) { const c = rgba(getComputedStyle(n).backgroundColor);
    layers.push(c); if (c.length < 4 || c[3] === 1) break; }
  const ride = (() => { const p = document.createElement('span'); p.style.color = 'var(--ride)'; document.body.appendChild(p);
    const c = getComputedStyle(p).color; p.remove(); return rgba(c); })();
  let bg = (layers[layers.length - 1].length < 4 || layers[layers.length - 1][3] === 1) ? layers.pop() : ride;
  for (const l of layers.reverse()) { const a = l.length < 4 ? 1 : l[3]; bg = bg.map((v, i) => l[i] * a + v * (1 - a)); }
  const fg = rgba(getComputedStyle(el).color);
  const a = lum(fg), b = lum(bg);
  return { fg: getComputedStyle(el).color, bg: 'rgb(' + bg.map(Math.round).join(',') + ')',
           ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) };
}"""


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("width", [1440, 800])
def test_on_band_download_hover_readable(site_url, browser, width, theme):
    ctx, page = open_page(browser, site_url + "/", width=width, theme=theme)
    try:
        to_band(page)
        cta = page.locator(".site-header .nav-cta")
        idle = cta.evaluate(CONTRAST)
        cta.hover()
        page.wait_for_timeout(400)
        hov = cta.evaluate(CONTRAST)
        assert hov["ratio"] >= 4.5, (width, theme, idle, hov)
        assert (hov["fg"], hov["bg"]) != (idle["fg"], idle["bg"]), "the hover still shows"
    finally:
        ctx.close()
