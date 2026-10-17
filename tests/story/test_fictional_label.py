"""A10: the homepage story's "Fictional data" disclosure (R5 ruling A.2/A.3; decisions-2026-10-15 #1).

One quiet label on the stage, only while the story's money is identifiable:
- on from the START of the Look -> Know seam (Sol: the first Know row is up 0.08 s into it) through Know, Grow,
  the Ride and Chase; off at chaseYours.T0 + 0.36 (desktop) / + 0.24 (phones, the Recent rows are gone at 0.21);
  the tablet story has no Chase -> Yours: its pinned timeline ends on Chase's money, so its window ends on its own
  timeline at chase.T1 (inclusive) instead of never (Infinity). No label on Make or Look (G12: a single invoice).
  The same frames in both scroll directions.
- size: >= 12.5 px at every width, rendered (after any stage zoom/transform), weight >= 500 (R5: what Sol cleared;
  never smaller, lighter or timed). (LABEL, 2026-10-17: the phone row under the stage was 12 px, under the floor.)
- contrast: >= 4.5:1 between the label's text colour and the WORST rendered pixel behind its words (the text hidden,
  the frame re-shot), on the stage, on the Ride's band and on the page, both themes. The crop is the words' own box,
  so whatever is under them is what gets measured: the stage's records and shadows where the label has no backing,
  the halo or chip where it has one (LABEL: plain text wherever that alone holds).
- calm / no-JS: the static Know, Grow and Chase figures keep their visible "Fictional data" caption (an adjacent
  caption counts, G12); the Make and Look captions and the trailing "Fictional data." in the three stage aria-labels
  (said twice next to the caption) are trimmed; the pinned story's screen-reader text (STAGE_ARIA) keeps it.

Run: uv run --with pytest --with playwright python3 -m pytest tests/story/test_fictional_label.py -q
"""
from __future__ import annotations

import struct
import zlib

import pytest
from playwright.sync_api import sync_playwright

MODES = {"desktop": (1440, 900), "tablet": (800, 1000), "phone": (390, 844)}
THEMES = ("dark", "light")
LABEL = ".stage-label"
EPS = 0.01          # never sample closer than this to a window edge (s of story time)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--font-render-hinting=none", "--disable-lcd-text"])
        yield b
        b.close()


def open_story(browser, site_url, mode, theme, *, reduced=False, js=True):
    w, h = MODES[mode]
    ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                              reduced_motion="reduce" if reduced else "no-preference", java_script_enabled=js)
    ctx.add_init_script("try{localStorage.setItem('fe-theme','" + theme + "')}catch(e){}")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site_url + "/", wait_until="load")
    if js and not reduced:
        page.wait_for_function("() => document.documentElement.classList.contains('fx-ready') && "
                               "window.__site && !!window.__site.TL", timeout=8000)
    page.wait_for_timeout(300)
    assert errors == [], errors
    return ctx, page


WINDOW_JS = """() => { const t = window.__site.TL, s = (id) => t.seg(id);
  return { lk: s('lookKnow').T0, chaseT1: s('chase').T1, cy: s('chaseYours') ? s('chaseYours').T0 : null,
    T1: t.T1, labelData: t.labelData, labelOff: t.labelOff, isDesk: t.isDesk, p: t.p,
    segs: t.segs.map((g) => [g.id, g.T0, g.T1]), ride: [s('ride').T0, s('ride').T1],
    know: s('know').T1, grow: s('grow').T1 }; }"""
SEEK_JS = """(T) => { window.__site.seekMaster(T); const l = document.querySelector('.stage-label');
  return { mode: l.getAttribute('data-mode'), op: getComputedStyle(l).opacity, text: l.innerText.trim() }; }"""


def window_for(mode, w):
    """The R5 window [on, off] for this mode, from the seams themselves (never from TL.labelData/labelOff)."""
    if mode == "desktop":
        assert w["isDesk"] and w["cy"] is not None
        return w["lk"], w["cy"] + 0.36
    if mode == "phone":
        assert w["p"] == "tall" and w["cy"] is not None
        return w["lk"], w["cy"] + 0.24
    assert not w["isDesk"] and w["p"] != "tall" and w["cy"] is None, "tablet: make..chase pinned, no Chase -> Yours"
    assert abs(w["T1"] - w["chaseT1"]) < 1e-9, "tablet: the pinned timeline ends on Chase"
    return w["lk"], w["chaseT1"]


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("mode", list(MODES))
def test_label_window(browser, site_url, mode, theme):
    ctx, page = open_story(browser, site_url, mode, theme)
    try:
        w = page.evaluate(WINDOW_JS)
        on, off = window_for(mode, w)
        # the window as the engine holds it: it opens at the seam's start and ends on this mode's own timeline
        assert abs(w["labelData"] - on) < 1e-6, ("labelData", w["labelData"], on)
        assert abs(w["labelOff"] - off) < 1e-6, ("labelOff", w["labelOff"], off, mode)
        assert off <= w["T1"] + 1e-9, ("the label window must end on this mode's timeline", off, w["T1"])
        ts = {0.0, w["T1"], on - EPS, on + 0.001, on + 0.08, off - EPS}
        if off + EPS <= w["T1"]:
            ts.add(off + EPS)
        for _id, t0, t1 in w["segs"]:
            ts.update({t0 + 0.004, (t0 + t1) / 2, t1 - 0.004})
        ts = sorted(t for t in ts if 0 <= t <= w["T1"] and not (abs(t - on) < 0.0009 or 0 < abs(t - off) < 0.004))
        bad = []
        for direction, seq in (("forward", ts), ("reverse", ts[::-1])):
            for t in seq:
                want = on <= t <= off
                got = page.evaluate(SEEK_JS, t)
                shown = got["mode"] == "data" and got["op"] == "1" and got["text"] == "Fictional data"
                hidden = got["mode"] != "data" and got["op"] == "0"
                if (want and not shown) or (not want and not hidden):
                    seg = next(s[0] for s in w["segs"] if s[1] <= t <= s[2] + 1e-9)
                    bad.append((direction, round(t, 3), seg, "want on" if want else "want off", got))
        assert not bad, bad[:12]
    finally:
        ctx.close()


@pytest.mark.parametrize("mode", list(MODES))
def test_label_size(browser, site_url, mode):
    ctx, page = open_story(browser, site_url, mode, "dark")
    try:
        w = page.evaluate(WINDOW_JS)
        page.evaluate(SEEK_JS, w["know"] - 0.02)
        px, weight = page.evaluate("() => { const cs = getComputedStyle(document.querySelector('.stage-label'));"
                                   " return [parseFloat(cs.fontSize), parseFloat(cs.fontWeight)]; }")
        assert px >= 12.5, (mode, px, 12.5)
        assert weight >= 500, (mode, weight)
    finally:
        ctx.close()


# the rendered size: the computed font size times any scale between the label and the screen (a stage zoom or
# transform), at the phone widths where the label has its own row under the stage (LABEL: that row was 12 px)
RENDERED_JS = """() => { const l = document.querySelector('.stage-label'), r = l.getBoundingClientRect();
  const ch = parseFloat(getComputedStyle(l).height);     // unrounded (offsetHeight rounds 20.25 to 20)
  return { fs: parseFloat(getComputedStyle(l).fontSize), scale: ch ? r.height / ch : 0,
    row: l.offsetHeight }; }"""


@pytest.mark.parametrize("width", [360, 390, 1024, 1440])
def test_label_rendered_size(browser, site_url, width):
    ctx = browser.new_context(viewport={"width": width, "height": 844 if width < 640 else 900}, device_scale_factor=1)
    ctx.add_init_script("try{localStorage.setItem('fe-theme','dark')}catch(e){}")
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        page.wait_for_function("() => document.documentElement.classList.contains('fx-ready') && "
                               "window.__site && !!window.__site.TL", timeout=8000)
        w = page.evaluate(WINDOW_JS)
        page.evaluate(SEEK_JS, w["know"] - 0.02)
        got = page.evaluate(RENDERED_JS)
        assert got["fs"] * got["scale"] >= 12.5 - 1e-6, (width, got)
        if width < 640:
            assert got["row"] == 20, ("the phone label row keeps its height, so the captions never move", got)
    finally:
        ctx.close()


FIELD_JS = """() => { const l = document.querySelector('.stage-label'), p = document.createElement('i');
  p.style.color = 'var(--ride-text)'; l.parentElement.appendChild(p);
  const want = getComputedStyle(p).color; p.remove();
  return { onField: !!l.closest('.pin.on-field'), color: getComputedStyle(l).color, want,
    chip: getComputedStyle(l).backgroundColor }; }"""


@pytest.mark.parametrize("theme", THEMES)
def test_label_field_palette(browser, site_url, theme):
    """On the Ride's field (desktop) the label takes the field's palette (LABEL: a broken comment once swallowed the
    rule, leaving the page's grey and chip on the teal; the contrast test cannot tell, both pass 4.5:1)."""
    ctx, page = open_story(browser, site_url, "desktop", theme)
    try:
        w = page.evaluate(WINDOW_JS)
        page.evaluate(SEEK_JS, w["chaseT1"] - 0.5)
        got = page.evaluate(FIELD_JS)
        assert got["onField"], got
        assert got["color"] == got["want"], (theme, got)
    finally:
        ctx.close()


# ---- contrast on the rendered pixels ----

def _png_pixels(png: bytes):
    """Decode an 8-bit RGB/RGBA PNG (Playwright's screenshots) to (width, height, rows of (r, g, b))."""
    pos, idat, width, height, ctype = 8, b"", 0, 0, 0
    while pos < len(png):
        n, kind = struct.unpack(">I4s", png[pos:pos + 8])
        body = png[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            width, height, depth, ctype = struct.unpack(">IIBB", body[:10])
            assert depth == 8 and ctype in (2, 6), (depth, ctype)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    bpp = 4 if ctype == 6 else 3
    raw, stride, rows, prev = zlib.decompress(idat), width * bpp, [], bytearray(width * bpp)
    for y in range(height):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x * bpp:x * bpp + 3]) for x in range(width)])
        prev = line
    return width, height, rows


def _lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (the words hidden with -webkit-text-fill-color, which no transition touches, so a running colour/background
# transition keeps running and is measured as it is; never `transition: none`, never animations="disabled")
HIDE_TEXT = """(sel) => { const l = document.querySelector(sel); l.dataset.keep = l.getAttribute('style') || '';
  l.style.setProperty('-webkit-text-fill-color', 'transparent', 'important'); }"""
SHOW_TEXT = """(sel) => { const l = document.querySelector(sel); const k = l.dataset.keep;
  if (k) l.setAttribute('style', k); else l.removeAttribute('style'); delete l.dataset.keep; }"""
TEXT_BOX = """(sel) => { const l = document.querySelector(sel), s = l.querySelector('span') || l, r = s.getBoundingClientRect();
  const m = getComputedStyle(s).color.match(/[\\d.]+/g).map(Number);
  return { x: r.left, y: r.top, w: r.width, h: r.height, color: m }; }"""
# any colour transition running on the label (a band entry/exit between two samples) is frozen at a fraction of its
# duration and measured there, at several fractions (an ease-out is most of the way at half time, so the crossing of
# the two palettes is early); a label with no transition has nothing to freeze
PAUSE_AT = """(k) => { const a = document.querySelector('.stage-label').getAnimations();
  for (const x of a) { x.pause(); const t = x.effect.getComputedTiming(); x.currentTime = (x.effect.getTiming().delay || 0) + t.duration * k; }
  return a.length; }"""
FRACTIONS = (0.02, 0.06, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75)
FINISH = "() => { for (const x of document.querySelector('.stage-label').getAnimations()) x.finish(); }"


def measure(page, sel):
    """(worst ratio, bg pixel, fg) of sel's text colour against every rendered pixel behind its words."""
    box = page.evaluate(TEXT_BOX, sel)
    fg = tuple(round(v) for v in box["color"][:3])
    alpha = box["color"][3] if len(box["color"]) > 3 else 1.0
    page.evaluate(HIDE_TEXT, sel)
    try:
        png = page.screenshot(clip={"x": box["x"], "y": box["y"], "width": box["w"], "height": box["h"]},
                              animations="allow", caret="hide")
    finally:
        page.evaluate(SHOW_TEXT, sel)
    _, _, rows = _png_pixels(png)

    def over(px):                                           # a translucent text colour lands on the pixel behind it
        return tuple(alpha * f + (1 - alpha) * b for f, b in zip(fg, px))
    worst = min((_ratio(over(px), px), px) for row in rows for px in row)
    return round(worst[0], 2), worst[1], fg + ((round(alpha, 2),) if alpha < 0.999 else ())


def grid_for(mode, w, step=0.25):
    """Every label-on frame at `step` s through the whole window (Know, Grow, the Ride, Chase, Chase -> Yours up to
    the off-point), in story order, so each band entry and exit happens between two samples."""
    on, off = window_for(mode, w)
    ts, t = [on + 0.001], on + step
    while t < off:
        ts.append(t)
        t += step
    ts.append(off - 0.005 if mode != "tablet" else w["T1"])
    return ts


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("mode", list(MODES))
def test_label_contrast(browser, site_url, mode, theme):
    ctx, page = open_story(browser, site_url, mode, theme)
    try:
        w = page.evaluate(WINDOW_JS)
        page.evaluate(SEEK_JS, w["lk"] - 0.05)              # settle off-window first, then walk forward
        page.wait_for_timeout(400)
        bad, worst, n = [], (99, None, None, None), 0
        for t in grid_for(mode, w):
            got = page.evaluate(SEEK_JS, t)
            assert got["mode"] == "data", (t, got)
            frozen = page.evaluate(PAUSE_AT, FRACTIONS[0])
            r, bg, fg = measure(page, LABEL)
            for k in FRACTIONS[1:] if frozen else ():
                page.evaluate(PAUSE_AT, k)
                r, bg, fg = min((r, bg, fg), measure(page, LABEL))
            page.evaluate(FINISH)
            n += 1
            worst = min(worst, (r, round(t, 3), bg, fg))
            if r < 4.5:
                seg = next(s[0] for s in w["segs"] if s[1] <= t <= s[2] + 1e-9)
                bad.append((round(t, 3), seg, r, "bg", bg, "fg", fg, "mid-transition" if frozen else "settled"))
        assert not bad, (mode, theme, f"{len(bad)}/{n} frames under 4.5:1", bad[:10])
        assert n >= 40, n
    finally:
        ctx.close()


# ---- the stacked (calm) and no-JS layouts ----

STATIC_JS = """() => [...document.querySelectorAll('figure.beat-static')].map((f) => {
  const st = f.querySelector('.stage[data-stage]'), cap = f.querySelector('figcaption');
  const r = cap ? cap.getBoundingClientRect() : null;
  return { beat: st ? st.getAttribute('data-stage') : null, aria: st ? st.getAttribute('aria-label') : '',
    cap: cap ? cap.textContent.trim() : null,
    capShown: !!(cap && r.width > 0 && r.height > 0 && getComputedStyle(cap).visibility !== 'hidden' &&
      getComputedStyle(cap).display !== 'none') }; })"""


@pytest.mark.parametrize("layout", ["calm-1440", "calm-390", "nojs-1440", "nojs-390"])
def test_calm_nojs_disclose(browser, site_url, layout):
    kind, width = layout.split("-")
    mode = "desktop" if width == "1440" else "phone"
    ctx, page = open_story(browser, site_url, mode, "dark", reduced=(kind == "calm"), js=(kind == "calm"))
    try:
        if kind == "calm":
            assert page.evaluate("() => document.documentElement.classList.contains('calm')")
        figs = {f["beat"]: f for f in page.evaluate(STATIC_JS)}
        for beat in ("know", "grow", "chase"):
            f = figs[beat]
            assert f["cap"] == "Fictional data" and f["capShown"], (layout, beat, f)       # the adjacent caption: G12
            assert "fictional data" not in f["aria"].lower(), (layout, beat, "said twice: caption + aria", f["aria"])
        assert "With email already configured" in figs["chase"]["aria"]                   # Sol: truthfulness
        for beat in ("make", "look"):                                                       # a single invoice: G12
            assert figs[beat]["cap"] is None, (layout, beat, figs[beat])
        assert "fictional client" in figs["make"]["aria"]                                   # R5: kept, invisible
    finally:
        ctx.close()


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("layout", ["calm-1440", "calm-390", "nojs-1440", "nojs-390"])
def test_calm_nojs_caption_contrast(browser, site_url, layout, theme):
    """The stacked layouts' "Fictional data" captions (the only visible disclosure there) are >= 4.5:1 on the rendered
    pixels behind them, both themes (fe:claims #3: the Chase caption on the Ride's teal measured 4.03-4.07 light)."""
    kind, width = layout.split("-")
    mode = "desktop" if width == "1440" else "phone"
    ctx, page = open_story(browser, site_url, mode, theme, reduced=(kind == "calm"), js=(kind == "calm"))
    try:
        bad, seen = [], {}
        for beat in ("know", "grow", "chase"):
            sel = f'figure:has(.stage[data-stage="{beat}"]) figcaption'
            page.evaluate("(s) => document.querySelector(s).scrollIntoView({ block: 'center' })", sel)
            page.wait_for_timeout(150)
            r, bg, fg = measure(page, sel)
            seen[beat] = (r, bg, fg)
            if r < 4.5:
                bad.append((beat, r, "bg", bg, "fg", fg))
        assert not bad, (layout, theme, bad, seen)
    finally:
        ctx.close()


def test_pinned_screen_reader_text_keeps_it(browser, site_url):
    """The pinned stage is aria-hidden and has no caption: its per-beat description (STAGE_ARIA) still says it."""
    ctx, page = open_story(browser, site_url, "desktop", "dark")
    try:
        texts = page.evaluate("() => Object.fromEntries(['know', 'grow', 'chase'].map((b) => {"
                              " const p = document.querySelector(`[data-copy=\"${b}\"] .sr-stage`);"
                              " return [b, p ? p.textContent : null]; }))")
        for beat, text in texts.items():
            assert text and text.rstrip().endswith("Fictional data."), (beat, text)
    finally:
        ctx.close()
