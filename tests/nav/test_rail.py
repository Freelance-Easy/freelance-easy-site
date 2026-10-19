"""B5: the chapter rail v3 (assets/story/rail.js + rail.css, src/partials/rail.html), per docs/interaction-contract.md.

- test_aria_current_on_land: aria-current="location" moves at a landing (FEStory.onLand), never at dest (ICX-HL.2).
- test_highlight_follows_dest: the highlight is dest's the moment dest changes (ICX-HL.1).
- test_jump_no_intermediate_caption: a rail click >= 2 away shows no caption of the chapters between and lands within
  the dip time (ICX-JUMP.2).
- test_keyboard: Up / Down / Home / End move inside the rail without moving the story; Enter jumps (ICX-KEY.7).
- test_idle_contrast: idle names >= 4.5:1, pixel-measured, on the page and on the Ride band, both themes.
- test_names_always_visible: every name drawn, unclipped, clear of the captions and the stage at 1024/1280/1440.
- test_no_tip_fill_numerals: no .nav-tip, no is-filling, no digits, no progress semantics (ICX-NOPROG).
- test_nojs_anchors: without JS the rail is plain <a href="#slug"> anchors to the chapter sections (decisions #20);
  with JS it renders from FEStory.destinations and a click never changes the hash itself.
- test_scroll_spy_calm: calm / classic at >= 1024: the rail is fixed in the gutter, the highlight and aria-current
  follow the 40 % line (ICX-HL.4), and `fe:spy` fires at each change (ICX-HIST.9).
- test_free_nearest: a foreign scroll inside the track previews the nearest chapter (ICX-HL.3) and aria-current waits
  for the settle's landing.
- test_old_nav_code_gone: no navBuild / navTick / navGo / navSetActive left in assets/.

Run: uv run --with pytest --with playwright python3 -m pytest tests/nav/test_rail.py -q
"""
from __future__ import annotations

import base64
import pathlib
import re
import struct
import zlib
from html.parser import HTMLParser

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BEATS = ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"]
SLUGS = ["new-invoice", "templates", "invoices", "dashboard", "email", "your-data", "price", "a-note", "get-the-app"]
NAMES = ["New invoice", "Templates", "Invoices", "Dashboard", "Email", "Your data", "Price", "A note", "Get the app"]

REC = """() => {
  if (window.__rail) return;
  const cur = () => { const a = document.querySelector('.story-nav a[aria-current="location"]'); return a ? a.dataset.go : null; };
  const hl = () => { const a = document.querySelector('.story-nav a.is-hl'); return a ? a.dataset.go : null; };
  const nCur = () => document.querySelectorAll('.story-nav [aria-current]').length;
  window.__rail = { log: [], caps: [], spy: [], hash: 0, clickAt: null, cur, hl };
  FEStory.onDest((p) => __rail.log.push({ k: 'dest', beat: p.beat, preview: !!p.preview, cur: cur(), hl: hl(), n: nCur(), t: performance.now() }));
  FEStory.onLand((p) => __rail.log.push({ k: 'land', beat: p.beat, final: p.final, cur: cur(), hl: hl(), n: nCur(), t: performance.now() }));
  document.addEventListener('fe:spy', (e) => __rail.spy.push(e.detail.slug));
  window.addEventListener('hashchange', () => { __rail.hash++; });
  document.querySelector('.story-nav').addEventListener('click', () => { __rail.clickAt = performance.now(); }, true);
  const caps = document.querySelector('.captions');
  new MutationObserver((ms) => { for (const m of ms) { const el = m.target;
    if (el.classList && el.classList.contains('beat-copy') && el.classList.contains('is-on')) __rail.caps.push(el.getAttribute('data-copy')); } })
    .observe(caps, { subtree: true, attributes: true, attributeFilter: ['class'] });
}"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _open(browser, site_url, w=1280, h=800, theme="dark", **kw):
    ctx = browser.new_context(viewport={"width": w, "height": h}, **kw)
    ctx.add_init_script(f"try {{ localStorage.setItem('fe-theme', '{theme}'); }} catch (e) {{}}")
    page = ctx.new_page()
    errs: list[str] = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(f"{site_url}/#{theme}")
    page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready')", timeout=10000)
    page._b5_errs = errs  # type: ignore[attr-defined]
    return ctx, page


def _rest(page, i, timeout=15000):
    page.wait_for_function(
        "(i) => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === i && s.dest === i; }",
        arg=i, timeout=timeout)
    page.wait_for_timeout(250)


def _desk(browser, site_url, **kw):
    ctx, page = _open(browser, site_url, **kw)
    _rest(page, 0)
    page.wait_for_function("() => document.querySelector('.story-nav.is-in') && !document.querySelector('.story-nav').hidden")
    page.evaluate(REC)
    return ctx, page


def _click(page, beat):
    page.click(f".story-nav a[data-go='{beat}']")


def test_aria_current_on_land(browser, site_url):
    ctx, page = _desk(browser, site_url)
    try:
        assert page.evaluate("__rail.cur()") == "make"
        _click(page, "grow")                                       # distance 3: a dip
        _rest(page, 3)
        log = page.evaluate("__rail.log")
        dests = [e for e in log if e["k"] == "dest"]
        lands = [e for e in log if e["k"] == "land"]
        assert dests and dests[0]["beat"] == "grow", log
        assert dests[0]["cur"] == "make", f"aria-current moved at dest, not at the landing: {dests[0]}"
        assert lands and lands[-1]["beat"] == "grow" and lands[-1]["final"], log
        for e in lands:
            assert e["cur"] == e["beat"] and e["n"] == 1, e
        # a forward step (distance 1): during the seam aria-current stays on the chapter it left
        page.evaluate("__rail.log = []")
        _click(page, "chase")
        page.wait_for_timeout(120)
        mid = page.evaluate("({ phase: FEStory.phase, cur: __rail.cur(), hl: __rail.hl() })")
        if mid["phase"] != "rest":
            assert mid["cur"] == "grow" and mid["hl"] == "chase", mid
        _rest(page, 4)
        assert page.evaluate("__rail.cur()") == "chase"
        assert page.evaluate("document.querySelectorAll('.story-nav [aria-current]').length") == 1
        assert not page._b5_errs
    finally:
        ctx.close()


def test_highlight_follows_dest(browser, site_url):
    ctx, page = _desk(browser, site_url)
    try:
        page.mouse.move(700, 400)
        page.keyboard.press("ArrowDown")                           # the engine's own step input
        page.wait_for_timeout(260)
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(60)
        _click(page, "price")                                      # a jump on top of the run
        _rest(page, 6)
        dests = [e for e in page.evaluate("__rail.log") if e["k"] == "dest"]
        assert len(dests) >= 2, dests
        for e in dests:
            assert e["hl"] == e["beat"], f"highlight is not dest's at the dest change: {e}"
        assert page.evaluate("__rail.hl()") == "price"
    finally:
        ctx.close()


def test_jump_no_intermediate_caption(browser, site_url):
    ctx, page = _desk(browser, site_url)
    try:
        cfg = page.evaluate("FEStory.CONFIG")
        _click(page, "chase")                                      # distance 4
        _rest(page, 4)
        caps = page.evaluate("__rail.caps")
        between = {"look", "know", "grow"}
        assert not between & set(caps), f"captions of the chapters between were shown: {caps}"
        log = page.evaluate("__rail.log")
        t0 = page.evaluate("__rail.clickAt")
        land = next(e for e in log if e["k"] == "land" and e["final"])
        assert land["beat"] == "chase", log
        limit = (cfg["DIP_OUT"] + cfg["DIP_IN"]) * 1000 + 120
        assert land["t"] - t0 <= limit, f"landed {land['t'] - t0:.0f} ms after the click (dip budget {limit:.0f} ms)"
    finally:
        ctx.close()


def test_keyboard(browser, site_url):
    ctx, page = _desk(browser, site_url)
    try:
        focus = "() => document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.go : null"
        tabs = page.evaluate("[...document.querySelectorAll('.story-nav a')].map(a => a.getAttribute('tabindex'))")
        assert tabs.count("0") == 1 and tabs[0] == "0", tabs        # one tab stop: the current chapter
        page.focus(".story-nav a[aria-current='location']")
        y0 = page.evaluate("scrollY")
        for key, want in [("ArrowDown", "look"), ("ArrowDown", "know"), ("ArrowUp", "look"), ("End", "end"),
                          ("Home", "make"), ("ArrowUp", "make")]:
            page.keyboard.press(key)
            page.wait_for_timeout(80)
            assert page.evaluate(focus) == want, (key, want)
            st = page.evaluate("FEStory.state()")
            assert st["dest"] == 0 and st["rendered"] == 0, f"{key} inside the rail moved the story: {st}"
        assert page.evaluate("scrollY") == y0
        for _ in range(3):
            page.keyboard.press("ArrowDown")
        assert page.evaluate(focus) == "grow"
        page.keyboard.press("Enter")
        _rest(page, 3)
        assert page.evaluate(focus) == "grow", "focus left the rail"
        assert page.evaluate("__rail.cur()") == "grow"
        assert page.evaluate("__rail.hash") == 0, "the rail changed the hash itself (a second jump via hashchange)"
    finally:
        ctx.close()


# ---------------------------------------------------------------- pixels (no PIL: a tiny PNG reader)
def _png_rgb(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    i, idat, w = 8, b"", 0
    while i < len(data):
        ln, typ = struct.unpack(">I4s", data[i:i + 8])
        body = data[i + 8:i + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", body)
            assert depth == 8 and ctype in (2, 6) and inter == 0, (depth, ctype, inter)
            bpp = 3 if ctype == 2 else 4
        elif typ == b"IDAT":
            idat += body
        i += 12 + ln
    raw, stride, rows, prev = zlib.decompress(idat), w * bpp, [], bytearray(w * bpp)
    p = 0
    for _ in range(h):
        f, line = raw[p], bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b, c = prev[x], prev[x - bpp] if x >= bpp else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x:x + 3]) for x in range(0, stride, bpp)])
        prev = line
    return rows


def _lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _name_contrast(page, beat):
    box = page.evaluate("(b) => { const r = document.querySelector(`.story-nav a[data-go='${b}'] .nm`).getBoundingClientRect();"
                        " return { x: r.left - 3, y: r.top - 3, width: r.width + 6, height: r.height + 6 }; }", beat)
    px = [c for row in _png_rgb(page.screenshot(clip=box)) for c in row]
    counts: dict = {}
    for c in px:
        counts[c] = counts.get(c, 0) + 1
    bg = max(counts, key=counts.get)                               # the most common colour: what is behind the name
    return max(_ratio(c, bg) for c in px), bg


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_idle_contrast(browser, site_url, theme):
    ctx, page = _desk(browser, site_url, theme=theme, device_scale_factor=2)
    try:
        for where, idx, beat in [("page", 0, None), ("band", 4, "chase")]:
            if beat:
                _click(page, beat)
                _rest(page, idx)
                page.wait_for_timeout(400)                         # the colour transition
                assert page.evaluate("document.querySelector('.story-nav').classList.contains('on-band')"), "rail not on the band"
            page.mouse.move(900, 700)                              # no hover on the rail
            idle = page.evaluate("[...document.querySelectorAll('.story-nav a:not(.is-hl)')].map(a => a.dataset.go)")
            assert len(idle) == 8, idle
            _assert_idle(page, idle, f"{theme} pinned {where}")
    finally:
        ctx.close()


def _assert_idle(page, idle, label):
    worst = 99.0
    for b in idle:
        r, bg = _name_contrast(page, b)
        worst = min(worst, r)
        assert r >= 4.5, f"{label}: idle '{b}' is {r:.2f}:1 on {bg}"
    print(f"CONTRAST {label}: min {worst:.2f}:1 over {len(idle)} idle names")


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_idle_contrast_calm(browser, site_url, theme):
    """(judge B5-1 #1) calm / classic: the fixed rail scrolls over the Ride band section (#email); every idle name keeps
    >= 4.5:1 with the rail fully over the band and straddling its top edge (links over it take a.on-band)."""
    ctx, page = _open(browser, site_url, theme=theme, reduced_motion="reduce", device_scale_factor=2)
    try:
        page.wait_for_function("() => FEStory.mode === 'calm'")
        page.mouse.move(1200, 780)
        geo = page.evaluate("""() => { const n = document.querySelector('.story-nav').getBoundingClientRect();
          const e = document.getElementById('email').getBoundingClientRect();
          return { top: n.top, bottom: n.bottom, row: n.height / 9, eTop: e.top + scrollY, eH: e.height }; }""")
        assert geo["eH"] > geo["bottom"] - geo["top"] + 80, geo
        cases = [("band", geo["eTop"] - (geo["top"] - 40)),                       # band section covers the whole rail
                 ("straddle", geo["eTop"] - (geo["top"] + 5 * geo["row"] - 6))]  # its top edge cuts the sixth row
        for where, y in cases:
            page.evaluate("(y) => window.scrollTo(0, y)", round(y))
            page.wait_for_timeout(500)
            marks = page.evaluate("[...document.querySelectorAll('.story-nav a')].map(a => a.classList.contains('on-band'))")
            if where == "band":
                assert all(marks), marks
            else:
                assert any(marks) and not all(marks), marks
            idle = page.evaluate("[...document.querySelectorAll('.story-nav a:not(.is-hl)')].map(a => a.dataset.go)")
            assert len(idle) == 8, idle
            _assert_idle(page, idle, f"{theme} calm {where}")
    finally:
        ctx.close()


# c3a84e4's bar and footer: the brand's x, the controls' right gap, the footer's content edges (measured 2026-10-16;
# the story column's wider gutter must never reach them) — judge B5-1 #2
BASE_BAR = {
    ("story", 1024): (56.0, 30.7), ("story", 1280): (58.4, 58.4), ("story", 1440): (140.0, 140.0),
    ("calm", 1024): (30.7, 30.7), ("calm", 1280): (58.4, 58.4), ("calm", 1440): (140.0, 140.0),
}


@pytest.mark.parametrize("mode,w", list(BASE_BAR))
def test_bar_and_footer_keep_base_gutter(browser, site_url, mode, w):
    kw = {"reduced_motion": "reduce"} if mode == "calm" else {}
    ctx, page = _open(browser, site_url, w=w, **kw)
    try:
        page.wait_for_timeout(300)
        m = page.evaluate("""() => { const b = document.querySelector('.site-header .brand').getBoundingClientRect();
          const kids = [...document.querySelectorAll('.site-header .shell *')].map(e => e.getBoundingClientRect()).filter(r => r.width > 0);
          const fs = document.querySelector('footer .shell, .site-footer .shell'), fr = fs.getBoundingClientRect(), fc = getComputedStyle(fs);
          return { brand: b.left, right: innerWidth - Math.max(...kids.map(r => r.right)),
                   footL: fr.left + parseFloat(fc.paddingLeft), footR: innerWidth - fr.right + parseFloat(fc.paddingRight) }; }""")
        left, right = BASE_BAR[(mode, w)]
        for k, want in (("brand", left), ("right", right), ("footL", left), ("footR", right)):
            assert abs(m[k] - want) <= 0.6, f"{mode} {w}px: {k} {m[k]:.1f} != base {want}"
    finally:
        ctx.close()


@pytest.mark.parametrize("w", [1024, 1280, 1440])
def test_names_always_visible(browser, site_url, w):
    ctx, page = _desk(browser, site_url, w=w)
    try:
        page.mouse.move(w - 20, 790)                               # far from the rail: no hover needed
        page.wait_for_timeout(1000)                                # the draw-in (once, after the arrival)
        for idx, beat in [(0, None), (4, "chase"), (8, "end")]:
            if beat:
                _click(page, beat)
                _rest(page, idx)
            res = page.evaluate("""() => {
              const nav = document.querySelector('.story-nav');
              const names = [...nav.querySelectorAll('.nm')].map((n) => { const r = n.getBoundingClientRect();
                const c = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                return { t: n.textContent, l: r.left, r: r.right, top: r.top, b: r.bottom, w: r.width,
                  op: getComputedStyle(n).opacity, vis: getComputedStyle(nav).visibility, hit: !!(c && n.closest('a').contains(c)) }; });
              const lefts = [...document.querySelectorAll('.captions .beat-copy.is-on, .stage-wrap')]
                .map((e) => e.getBoundingClientRect()).filter((r) => r.width > 0).map((r) => r.left);
              return { names, clear: Math.min(...lefts), vw: innerWidth, vh: innerHeight };
            }""")
            names = res["names"]
            assert [n["t"] for n in names] == NAMES
            for i, n in enumerate(names):
                assert n["w"] > 20 and n["op"] == "1" and n["vis"] == "visible", (w, beat, n)
                assert n["l"] >= 0 and n["top"] >= 0 and n["b"] <= res["vh"], (w, beat, n)
                assert n["r"] + 12 <= res["clear"], f"{w}px: '{n['t']}' reaches {n['r']:.0f}, content starts at {res['clear']:.0f}"
                assert n["hit"], f"{w}px: '{n['t']}' is covered"
                if i:
                    assert n["top"] >= names[i - 1]["b"] - 0.5, (names[i - 1], n)
    finally:
        ctx.close()


def test_no_tip_fill_numerals(browser, site_url):
    ctx, page = _desk(browser, site_url)
    try:
        page.evaluate("""() => { window.__cls = []; new MutationObserver((ms) => { for (const m of ms) __cls.push(String(m.target.className && m.target.className.baseVal !== undefined ? m.target.className.baseVal : m.target.className)); })
          .observe(document.querySelector('.story-nav'), { subtree: true, attributes: true, attributeFilter: ['class', 'style'] }); }""")
        page.hover(".story-nav a[data-go='note']")
        _click(page, "yours")
        page.wait_for_timeout(150)
        widths1 = page.evaluate("[...document.querySelectorAll('.story-nav .tk')].map(t => getComputedStyle(t, '::before').width)")
        _rest(page, 5)
        page.mouse.move(900, 700)
        page.wait_for_timeout(400)
        widths2 = page.evaluate("[...document.querySelectorAll('.story-nav a:not(.is-hl) .tk')].map(t => getComputedStyle(t, '::before').width)")
        st = page.evaluate("""() => { const nav = document.querySelector('.story-nav');
          return { tip: document.querySelectorAll('.nav-tip').length, fill: document.querySelectorAll('.is-filling').length,
            text: nav.innerText + ' ' + [...nav.querySelectorAll('[aria-label],[title],[data-name]')].map(e => (e.getAttribute('aria-label') || '') + (e.getAttribute('title') || '') + (e.getAttribute('data-name') || '')).join(' '),
            datan: nav.querySelectorAll('[data-n]').length,
            prog: document.querySelectorAll('progress, [role=progressbar], [role=meter], [aria-valuenow]').length }; }""")
        assert st["tip"] == 0 and st["fill"] == 0, st
        assert not any("is-filling" in c or "is-tip" in c for c in page.evaluate("__cls")), "a fill or tip state was drawn"
        assert not re.search(r"\d", st["text"]), st["text"]
        assert st["datan"] == 0 and st["prog"] == 0, st
        assert len(set(widths2)) == 1, f"idle ticks differ in length (a fill or progress): {widths2}"
        assert widths1
    finally:
        ctx.close()


class _Rail(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.links: list[dict] = []
        self.buttons = 0
        self.ids: set[str] = set()
        self._nm = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        cls = (a.get("class") or "").split()
        if tag == "nav" and "story-nav" in cls:
            self.depth = 1
        elif self.depth:
            if tag == "a":
                self.links.append({"href": a.get("href"), "go": a.get("data-go"), "text": ""})
            elif tag == "button":
                self.buttons += 1
            elif tag == "span" and "nm" in cls:
                self._nm = True

    def handle_endtag(self, tag):
        if tag == "nav":
            self.depth = 0
        if tag == "span":
            self._nm = False

    def handle_data(self, data):
        if self._nm and self.links:
            self.links[-1]["text"] += data


def test_nojs_anchors(browser, site_url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, java_script_enabled=False)
    try:
        page = ctx.new_page()
        page.goto(site_url + "/")
        p = _Rail()
        p.feed(page.content())
        assert p.buttons == 0, "the rail still holds buttons (no-JS dead controls)"
        assert [l["href"] for l in p.links] == ["#" + s for s in SLUGS], p.links
        assert [l["text"] for l in p.links] == NAMES, p.links
        for s in SLUGS:
            assert s in p.ids, f"#{s} has no section"
    finally:
        ctx.close()
    ctx, page = _desk(browser, site_url)
    try:
        rows = page.evaluate("FEStory.destinations.map(r => ({ name: r.name, href: '#' + r.anchor, go: r.beat }))")
        got = page.evaluate("[...document.querySelectorAll('.story-nav a')].map(a => ({ name: a.querySelector('.nm').textContent, href: a.getAttribute('href'), go: a.dataset.go }))")
        assert got == rows, "the rail is not rendered from FEStory.destinations"
        h0 = page.evaluate("location.hash")
        _click(page, "know")
        _rest(page, 2)
        assert page.evaluate("__rail.hash") == 0, "the anchor's own navigation was not prevented"
        assert page.evaluate("location.hash") in (h0, "#invoices")   # (C4's pushState may write the slug; never via hashchange)
    finally:
        ctx.close()


@pytest.mark.parametrize("w,theme", [(1024, "dark"), (1440, "light")])
def test_scroll_spy_calm(browser, site_url, w, theme):
    ctx, page = _open(browser, site_url, w=w, theme=theme, reduced_motion="reduce")
    try:
        page.wait_for_function("() => FEStory.mode === 'calm'")
        page.wait_for_timeout(300)
        page.evaluate(REC.replace("const caps = document.querySelector('.captions');", "const caps = document.body;"))
        info = page.evaluate("""() => { const nav = document.querySelector('.story-nav'); const r = nav.getBoundingClientRect();
          const lefts = [...document.querySelectorAll('main .beat > .shell')].map((s) => s.getBoundingClientRect().left + parseFloat(getComputedStyle(s).paddingLeft));
          return { hidden: nav.hidden, fixed: getComputedStyle(nav).position, right: Math.max(...[...nav.querySelectorAll('.nm')].map(n => n.getBoundingClientRect().right)),
                   content: Math.min(...lefts), cur: __rail.cur() }; }""")
        assert not info["hidden"] and info["fixed"] == "fixed", info
        assert info["right"] + 16 <= info["content"], f"the rail crowds the content at {w}px: {info}"
        assert info["cur"] == "make", info
        vh = page.evaluate("innerHeight")
        maxy = page.evaluate("document.documentElement.scrollHeight - innerHeight")
        seen = []
        for i, s in enumerate(SLUGS[1:], start=1):
            top = page.evaluate("(s) => document.getElementById(s).getBoundingClientRect().top + scrollY", s)
            y = round(top - vh * 0.4 + 2)                          # its top just above the 40 % line
            if y > maxy:
                break                                              # the page cannot bring it that far up
            page.evaluate("(y) => window.scrollTo(0, y)", y)
            page.wait_for_timeout(120)
            got = page.evaluate("({ cur: __rail.cur(), hl: __rail.hl() })")
            assert got == {"cur": BEATS[i], "hl": BEATS[i]}, (s, got)
            page.evaluate("(y) => window.scrollTo(0, y)", y - 24)  # back below the line: the previous section
            page.wait_for_timeout(120)
            assert page.evaluate("__rail.cur()") == BEATS[i - 1], s
            page.evaluate("(y) => window.scrollTo(0, y)", y)
            page.wait_for_timeout(120)
            seen.append(BEATS[i])
        assert len(seen) >= 6, seen
        spy = page.evaluate("__rail.spy")
        assert spy and spy[-1] == SLUGS[BEATS.index(seen[-1])], spy
        assert all(spy[j] != spy[j + 1] for j in range(len(spy) - 1)), f"fe:spy fired without a change: {spy}"
        # a rail click in calm: a native anchor scroll to the section, no hash change from the rail itself
        _click(page, "know")
        page.wait_for_timeout(400)
        assert page.evaluate("__rail.cur()") == "know"
        assert page.evaluate("__rail.hash") == 0
        # classic (the story switched off by choice) keeps the same rail
        page.evaluate("FEStory.setClassic(true)")
        page.wait_for_timeout(200)
        assert page.evaluate("FEStory.mode") == "classic"
        assert not page.evaluate("document.querySelector('.story-nav').hidden")
        assert not page._b5_errs
    finally:
        ctx.close()


def test_calm_hides_when_narrow(browser, site_url):
    """main's condition for the calm rail: if the gutter cannot hold it, it hides instead of overlapping the content."""
    ctx, page = _open(browser, site_url, w=1024, reduced_motion="reduce")
    try:
        page.wait_for_function("() => FEStory.mode === 'calm'")
        page.wait_for_timeout(200)
        assert not page.evaluate("document.querySelector('.story-nav').hidden")
        page.add_style_tag(content=":root { --rail-room: 40px !important; }")  # a gutter too narrow for the names
        page.evaluate("window.dispatchEvent(new Event('resize'))")
        page.wait_for_timeout(200)
        assert page.evaluate("document.querySelector('.story-nav').hidden"), "the rail stayed over the content"
    finally:
        ctx.close()


def test_mode_return_resyncs(browser, site_url):
    """(Sol B5-1 MEDIUM) classic -> story keeps the reading place after the mode event; the rail follows that place."""
    ctx, page = _desk(browser, site_url)
    try:
        _click(page, "grow")
        _rest(page, 3)
        page.evaluate("FEStory.setClassic(true)")
        page.wait_for_timeout(300)
        page.evaluate("FEStory.setClassic(false)")
        page.wait_for_timeout(400)
        st = page.evaluate("({ r: FEStory.rendered, d: FEStory.dest, cur: __rail.cur(), hl: __rail.hl(), mode: FEStory.mode })")
        assert st["mode"] == "desktop", st
        assert st["cur"] == BEATS[st["r"]] and st["hl"] == BEATS[st["d"]], st
        assert st["cur"] == "grow", st
    finally:
        ctx.close()


def test_free_nearest(browser, site_url):
    ctx, page = _desk(browser, site_url)
    try:
        m = page.evaluate("__site.map()")
        page.evaluate("(y) => window.scrollTo({ top: y, behavior: 'instant' })", round(m["storyTop"] + 5 * m["beatPx"]))
        page.wait_for_function("() => __rail.log.some(e => e.k === 'dest' && e.preview)", timeout=3000)
        prev = next(e for e in page.evaluate("__rail.log") if e["k"] == "dest" and e["preview"])
        assert prev["beat"] == "yours" and prev["hl"] == "yours", prev
        assert prev["cur"] == "make", f"aria-current moved before the settle landed: {prev}"
        _rest(page, 5)
        assert page.evaluate("({ cur: __rail.cur(), hl: __rail.hl() })") == {"cur": "yours", "hl": "yours"}
    finally:
        ctx.close()


def test_old_nav_code_gone():
    hits = []
    for f in (ROOT / "assets").rglob("*.js"):
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            if re.search(r"navBuild|navTick|navGo|navSetActive", line):
                hits.append(f"{f.relative_to(ROOT)}:{i}")
    assert not hits, hits
    assert "nav-tip" not in (ROOT / "src" / "partials" / "rail.html").read_text()
