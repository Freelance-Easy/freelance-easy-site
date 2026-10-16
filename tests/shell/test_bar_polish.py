"""BX: two pre-existing bar issues the B4 judge confirmed (qa/B4-judge-1.md).

1. The bar's resting text on the Ride's band reads >= 4.5:1 in both themes (it was 4.13:1 light, pixel-sampled).
2. A9's platform note ("Apple Silicon Macs (M1 or later)" / "Windows 10 and 11, 64-bit") fills in after load without
   shoving the nav: no layout shift of any bar box once the page has loaded.
"""
from __future__ import annotations

import collections
import re
import io
import pathlib
import sys

import pytest
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_bar import MAC_UA, browser, open_page, to_band  # noqa: E402,F401

WIN_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"


ON_BAND = "() => { const c = document.documentElement.classList; return c.contains('on-band') && !c.contains('past-band'); }"


def lum(rgb):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def rendered_contrast(page, selector):
    """The element's text colour against the pixels actually behind it (the most common colour in its box)."""
    el = page.locator(selector).first
    fg = el.evaluate("""e => { const c = getComputedStyle(e).color;
        const m = c.match(/[\\d.]+/g).map(Number);
        return c.startsWith('color(') ? m.slice(0, 3).map(v => v * 255) : m.slice(0, 3); }""")
    # hide the glyphs so only the backdrop is sampled
    tag = page.add_style_tag(content=selector + "{color:transparent !important}")
    shot = page.screenshot(clip=el.bounding_box())  # the viewport's pixels: the bar is sticky, never scrolled away
    tag.evaluate("e => e.remove()")
    img = Image.open(io.BytesIO(shot)).convert("RGB")
    bg = collections.Counter(img.getdata()).most_common(1)[0][0]
    return ratio(fg, bg), fg, bg


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("width", [1440, 800])
def test_bar_text_on_band_readable(site_url, browser, width, theme):
    ctx, page = open_page(browser, site_url + "/", width=width, theme=theme)
    try:
        to_band(page)
        page.add_style_tag(content="*, *::before, *::after { transition: none !important; }")  # no mid-fade samples
        worst = None
        for sel in (".site-header .brand span", ".site-header .nav a[href='/tour/']", ".site-header .nav a[href='/pricing']"):
            r, fg, bg = rendered_contrast(page, sel)
            # the sample only counts if the bar was on the band the whole time (the story keeps moving)
            assert page.evaluate(ON_BAND), "the bar left the Ride's band during the sample"
            worst = min(worst or (r, sel), (r, sel))
            assert r >= 4.5, (width, theme, sel, round(r, 2), fg, bg)
    finally:
        ctx.close()


SHIFTS = """new PerformanceObserver(l => { window.__navShifts = window.__navShifts || [];
  for (const e of l.getEntries()) for (const s of (e.sources || []))
    if (s.node && s.node.closest && s.node.closest('.site-header'))
      window.__navShifts.push(Math.round(e.startTime) + 'ms ' + s.node.nodeName + '.' + (s.node.className || '')
        + ' ' + Math.round(s.previousRect.x) + '->' + Math.round(s.currentRect.x)); })
  .observe({type: 'layout-shift', buffered: true}); window.__navShifts = window.__navShifts || [];"""


WIN_INIT = "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});"
LINUX_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"


@pytest.mark.parametrize("ua,text", [(MAC_UA, "M1 or later"), (WIN_UA, "64-bit")])
@pytest.mark.parametrize("width", [1440, 1024, 800, 640])
def test_note_fill_shifts_nothing(site_url, browser, width, ua, text):
    # the web fonts stay on their fallback: Inter's own swap-in (a separate, pre-existing 3-5 px nudge of every nav
    # label, not the note) is not what this test measures
    ctx, page = open_page(browser, site_url + "/", width=width, ua=ua, init=(WIN_INIT if ua == WIN_UA else "") + SHIFTS,
                          route=("**/*.woff2", lambda r: r.abort()))
    try:
        page.wait_for_timeout(600)
        note = page.locator(".site-header .dl-note")
        assert text in note.inner_text(), "the note still fills in for this platform"
        assert page.evaluate("() => window.__navShifts") == []
    finally:
        ctx.close()


@pytest.mark.parametrize("width", [1440, 800])
def test_note_placeholder_never_shows_wrong_text(site_url, browser, width):
    """Before the fill the reserved space is empty (no text, no wrong platform); a phone/other OS never gets a gap."""
    ctx, page = open_page(browser, site_url + "/", width=width, js=False)
    try:
        # without JS nothing marks a platform: the note keeps its [hidden] (display none), so no text shows or takes room
        assert page.locator(".site-header .dl-note").evaluate("e => getComputedStyle(e).display") == "none"
    finally:
        ctx.close()


def test_note_absent_below_640(site_url, browser):
    ctx, page = open_page(browser, site_url + "/", width=390)
    try:
        box = page.locator(".site-header .dl-note").bounding_box()
        assert box is None or box["width"] == 0, box
    finally:
        ctx.close()


@pytest.mark.parametrize("width", [1440, 800])
def test_no_room_held_for_an_os_without_a_note(site_url, browser, width):
    """Linux (no note is ever filled) keeps the bar exactly as before: the held room is not taken."""
    ctx, page = open_page(browser, site_url + "/", width=width, ua=LINUX_UA,
                          init="Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});")
    try:
        assert page.evaluate("() => document.documentElement.hasAttribute('data-dl-os')") is False
        assert page.locator(".site-header .dl-note").evaluate("e => getComputedStyle(e).display") == "none"
    finally:
        ctx.close()


def test_held_words_equal_the_filled_words():
    """The invisible words in the header markup are the words download.js fills in (same text, so the same width)."""
    root = pathlib.Path(__file__).resolve().parents[2]
    header = (root / "src" / "partials" / "header.html").read_text(encoding="utf-8")
    js = (root / "assets" / "story" / "download.js").read_text(encoding="utf-8")
    for os_ in ("mac", "win"):
        held = re.search(r'<span data-ph="%s">(.*?)</span></span>' % os_, header, re.S).group(0)
        held_parts = re.findall(r'<span class="dl-note-(?:part|sep)">(.*?)</span>', held)
        notes = re.search(r"\b%s: \[(.*?)\],\n" % os_, js, re.S).group(1)
        js_parts = re.findall(r'"([^"]*)"', notes)
        assert held_parts == js_parts, (os_, held_parts, js_parts)
