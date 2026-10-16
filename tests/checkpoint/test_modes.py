"""C3: the story's modes, release and re-entry, the settle path and the phone story (docs/interaction-contract.md v1).

- test_every_destination_reachable: every ICX-DEST row is reachable with the story on (a reload on /#<slug> lands on
  its rest frame, ICX-JUMP.3), in calm (reduced motion), with no JS, and in the 4 s fallback (site.js blocked, the head
  script drops `motion`): /#<slug> and the legacy hashes reach their sections (ICX-DEST.5).
- test_mode_flip_keeps_place: ICX-DEST.4 across 1024, 640 and calm on/off; focus never moves.
- test_release_and_reentry: ICX-RELEASE.1/.2 + ICX-SETTLE-8 (wheel crossing) + ICX-SETTLE-4 (re-entry by a foreign
  scroll from below lands on the last pinned, not the nearest).
- test_free_within_one_frame_under_load: BT-1 (ICX-SETTLE-2).
- test_scroll_stream_settles_once: BT-2 (ICX-SETTLE-3), the scrollend path and the ?noscrollend idle path.
- test_phone_story_steps_and_releases: the phone story as shipped 10-10 (7 checkpoints) on C1's touch input; a short
  touch screen stays calm (ICX-DEST.6).
"""
from __future__ import annotations

import time

import pytest
from playwright.sync_api import sync_playwright

BEATS = ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"]
SLUGS = ["new-invoice", "templates", "invoices", "dashboard", "email", "your-data", "price", "a-note", "get-the-app"]
LEGACY = {"top": "make", "how": "look", "pricing": "price", "download": "end"}
STATE = "() => ({...FEStory.state(), y: Math.round(scrollY), end: __site.map().storyTop + __site.map().scrollLen, bp: __site.map().beatPx})"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _ctx(browser, w=1440, h=900, **kw):
    return browser.new_context(viewport={"width": w, "height": h}, **kw)


def _ready(page):
    page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready') && (window.__site.TL || FEStory.mode === 'calm')", timeout=10000)


def _wait(page, pred: str, timeout=12000):
    try:
        page.wait_for_function(f"() => {{ const s = FEStory.state(); return {pred}; }}", timeout=timeout)
    except Exception as e:  # noqa: BLE001 - report the engine's state, not a bare timeout
        raise AssertionError(f"timed out waiting for {pred}: {page.evaluate(STATE)}") from e
    return page.evaluate(STATE)


def _rest_on(page, idx: int, timeout=12000):
    return _wait(page, f"s.phase === 'rest' && s.rendered === {idx} && s.dest === {idx} && Math.abs(scrollY - s.trackY) <= 1 && s.beat === '{BEATS[idx]}'", timeout)


def _section_in_view(page, sel: str) -> bool:
    box = page.locator(sel).first.bounding_box()
    vh = page.viewport_size["height"]
    if box is None or box["height"] <= 0:
        return False
    if box["y"] < vh * 0.5 and box["y"] + box["height"] > vh * 0.5:
        return True
    # a section near the page's end cannot scroll up to the header: at the bottom of the page, fully on screen counts
    at_end = page.evaluate("() => Math.ceil(scrollY + innerHeight) >= document.documentElement.scrollHeight - 1")
    return at_end and box["y"] >= 0 and box["y"] + box["height"] <= vh + 1


# ------------------------------------------------------------------------------------------------- reachable
@pytest.mark.parametrize("mode", ["motion", "motion-820", "calm", "nojs", "fallback4s"])
def test_every_destination_reachable(browser, site_url, mode):
    kw = {"reduced_motion": "reduce" if mode == "calm" else "no-preference"}
    if mode == "nojs":
        kw["java_script_enabled"] = False
    ctx = _ctx(browser, 820, 1180, **kw) if mode == "motion-820" else _ctx(browser, **kw)
    if mode == "fallback4s":
        ctx.route("**/assets/story/site.js", lambda r: r.abort())
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        if mode.startswith("motion"):
            _ready(page)
            kinds = page.evaluate("() => FEStory.destinations.map(d => d.kind)")
            for i, slug in enumerate(SLUGS):
                page.goto(f"{site_url}/#{slug}")
                page.reload(wait_until="load")
                _ready(page)
                if kinds[i] == "native":                 # a tablet's native row: its own section (ICX-JUMP.3)
                    page.wait_for_timeout(400)
                    assert _section_in_view(page, f"#{slug}"), f"{mode}: /#{slug} (native) did not land on its section"
                    assert page.evaluate("() => FEStory.phase") == "released"
                    continue
                st = _rest_on(page, i)
                assert st["T"] == pytest.approx(page.evaluate(f"() => FEStory.destinations[{i}].rest"), abs=0.002), st
            # and the engine's own jump (End) from the first checkpoint: one move to the last pinned
            page.keyboard.press("Home")
            _rest_on(page, 0)
            page.keyboard.press("End")
            _rest_on(page, kinds.index("native") - 1 if "native" in kinds else 8)
            return
        if mode == "fallback4s":
            page.wait_for_function("() => !document.documentElement.classList.contains('motion')", timeout=6000)
        if mode == "calm":
            _ready(page)
            assert page.evaluate("() => FEStory.mode") == "calm"
            assert all(d["kind"] == "native" for d in page.evaluate("() => FEStory.destinations"))
        for slug in SLUGS + list(LEGACY):
            page.goto(f"{site_url}/#{slug}")
            page.wait_for_timeout(150)
            target = f"#{slug}" if slug in SLUGS else f"#{SLUGS[BEATS.index(LEGACY[slug])]}"
            if slug == "top":                            # main#top: the page's top
                assert page.locator("main#top").count() == 1
                continue
            assert _section_in_view(page, target), f"{mode}: /#{slug} did not bring {target} into view"
    finally:
        ctx.close()


# ------------------------------------------------------------------------------------------------- mode flips
def test_mode_flip_keeps_place(browser, site_url):
    ctx = _ctx(browser)
    page = ctx.new_page()
    try:
        page.goto(f"{site_url}/#dashboard", wait_until="load")
        page.reload(wait_until="load")
        _ready(page)
        _rest_on(page, 3)
        page.evaluate("() => document.querySelector('[data-theme-toggle]').focus()")
        focus = "() => document.activeElement && document.activeElement.matches('[data-theme-toggle]')"
        for (w, h) in [(820, 1180), (600, 900), (1440, 900)]:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(400)
            _rest_on(page, 3)
            assert page.evaluate(focus), f"focus moved on the flip to {w}x{h}"
        page.emulate_media(reduced_motion="reduce")
        page.wait_for_timeout(400)
        assert page.evaluate("() => FEStory.mode") == "calm"
        assert _section_in_view(page, "#dashboard"), "calm on: the Dashboard section is not the one in view"
        assert page.evaluate(focus), "focus moved when calm turned on"
        page.emulate_media(reduced_motion="no-preference")
        page.wait_for_timeout(400)
        _rest_on(page, 3)
        assert page.evaluate(focus), "focus moved when calm turned off"
        # a native row on the tablet: desktop REST(price) -> 820 px shows the Price section -> back on REST(price)
        page.evaluate("() => FEStory.goTo('price', {source: 'jump'})")
        _rest_on(page, 6)
        page.set_viewport_size({"width": 820, "height": 1180})
        page.wait_for_timeout(500)
        assert _section_in_view(page, "#price"), "tablet: Price (native) is not the section in view"
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(500)
        _rest_on(page, 6)
    finally:
        ctx.close()


# ------------------------------------------------------------------------------------------------- release / re-entry
@pytest.mark.parametrize("size", [(1440, 900), (820, 1180)], ids=["desktop", "tablet"])
def test_release_and_reentry(browser, site_url, size):
    ctx = _ctx(browser, *size)
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        _ready(page)
        last = page.evaluate("() => FEStory.destinations.filter(d => d.kind === 'pinned').length") - 1
        idx = BEATS.index(["end", "chase"][size[0] < 1024])
        page.goto(f"{site_url}/#{SLUGS[idx]}")
        page.reload(wait_until="load")
        _ready(page)
        st = _rest_on(page, idx)
        assert last == (8 if size[0] >= 1024 else 4)
        page.mouse.move(size[0] / 2, size[1] / 2)
        page.mouse.wheel(0, 100)                         # ICX-RELEASE.1: not intercepted, the page scrolls natively
        st = _wait(page, "s.phase === 'released'", 3000)
        assert st["y"] > st["end"] + 1, st
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(300)
        # ICX-RELEASE.2 / ICX-SETTLE-8: wheel back up; the crossing event lands REST(last), never an earlier checkpoint
        seen = set()
        for _ in range(12):
            page.mouse.wheel(0, -120)
            page.wait_for_timeout(60)
            s = page.evaluate(STATE)
            if s["phase"] not in ("released",):
                seen.add(s["rendered"])
        st = _rest_on(page, idx, 4000)
        assert seen <= {idx}, f"re-entry touched checkpoints {sorted(seen)}; only the last pinned ({idx}) is allowed"
        page.wait_for_timeout(500)
        # the next back gesture is an ordinary ICX-BACK
        page.mouse.wheel(0, -100)
        _rest_on(page, idx - 1, 3000)
        # ICX-SETTLE-4: a foreign scroll from below into the track settles on the last pinned (re-entry), not the nearest
        page.evaluate("() => FEStory.goTo(%d, {source: 'jump'})" % idx)
        _rest_on(page, idx, 8000)
        page.mouse.wheel(0, 100)
        st = _wait(page, "s.phase === 'released'", 3000)
        page.evaluate("(y) => window.scrollTo(0, y)", st["end"] - int(2.4 * st["bp"]))
        st = _rest_on(page, idx, 8000)
    finally:
        ctx.close()


# ------------------------------------------------------------------------------------------------- BT-1
def test_free_within_one_frame_under_load(browser, site_url):
    ctx = _ctx(browser)
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        _ready(page)
        _rest_on(page, 0)
        # load: a 12 ms busy task every 16 ms on the main thread
        page.evaluate("() => { window.__load = setInterval(() => { const t = performance.now(); while (performance.now() - t < 12); }, 16); }")
        misses = []
        for n in range(10):
            k = (n % 3) + 2
            phase = page.evaluate("""(k) => new Promise((res) => {
                const y = __site.map().beatPx * k + 37;
                window.scrollTo(0, y);
                requestAnimationFrame(() => res(FEStory.state().phase));
            })""", k)
            if phase != "free":
                misses.append((n, phase))
            _wait(page, "s.phase === 'rest' || s.phase === 'dip' || s.phase === 'transition'", 4000)
            _wait(page, "s.phase === 'rest'", 15000)
        page.evaluate("() => clearInterval(window.__load)")
        assert not misses, f"BT-1: FREE was not entered within one frame of a foreign scrollTo: {misses}"
    finally:
        ctx.close()


# ------------------------------------------------------------------------------------------------- BT-2
@pytest.mark.parametrize("query", ["", "?noscrollend"], ids=["scrollend", "idle"])
def test_scroll_stream_settles_once(browser, site_url, query):
    ctx = _ctx(browser)
    page = ctx.new_page()
    try:
        page.goto(site_url + "/" + query, wait_until="load")
        _ready(page)
        _rest_on(page, 0)
        assert page.evaluate("() => FEStory.state().scrollend") == (query == ""), "BT-2: the settle path was not the one asked for"
        before = page.evaluate("() => FEStory.state().settles")
        # a 1 s stream of small foreign scrolls inside the track (a scrollbar drag / autoscroll)
        page.evaluate("""() => new Promise((res) => {
            let n = 0; const id = setInterval(() => { window.scrollBy(0, 40); if (++n >= 33) { clearInterval(id); res(); } }, 30);
        })""")
        page.wait_for_timeout(1200)
        st = _wait(page, "s.phase === 'rest'", 12000)
        after = page.evaluate("() => FEStory.state().settles")
        assert after - before == 1, f"BT-2 ({query or 'scrollend'}): a 1 s scroll stream gave {after - before} settles"
        near = round((33 * 40) / st["bp"])
        assert st["rendered"] == near, st
    finally:
        ctx.close()


# ------------------------------------------------------------------------------------------------- phones
def _swipe(cdp, x, y0, dy, steps=6, ms=100):
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y0}]})
    for i in range(1, steps + 1):
        time.sleep(ms / steps / 1000)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y0 - dy * i / steps}]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def test_phone_story_steps_and_releases(browser, site_url):
    ctx = _ctx(browser, 390, 664, has_touch=True, is_mobile=True)
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        _ready(page)
        assert page.evaluate("() => FEStory.mode") == "phone"
        pinned = page.evaluate("() => FEStory.destinations.filter(d => d.kind === 'pinned').map(d => d.beat)")
        assert pinned == ["make", "look", "know", "grow", "chase", "yours", "end"], pinned
        _rest_on(page, 0)
        cdp = ctx.new_cdp_session(page)
        for b in pinned[1:]:
            _swipe(cdp, 195, 500, 220)
            _rest_on(page, BEATS.index(b), 12000)
        # at the offer card (the last pinned) a swipe up is native: the page scrolls on into Price and A note
        _swipe(cdp, 195, 500, 300)
        st = _wait(page, "s.phase === 'released'", 4000)
        assert st["y"] > st["end"] + 1, st
        assert page.evaluate("() => FEStory.destinations.filter(d => d.kind === 'native').map(d => d.beat)") == ["price", "note"]
    finally:
        ctx.close()
    # a short touch screen stays calm (ICX-DEST.6, decisions #22)
    ctx = _ctx(browser, 375, 548, has_touch=True, is_mobile=True)
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        _ready(page)
        assert page.evaluate("() => FEStory.mode") == "calm"
    finally:
        ctx.close()


# ------------------------------------------------------------------------------------------------- reload keeps place
@pytest.mark.parametrize("case", ["desktop-footer", "tablet-price", "desktop-midpin"])
def test_reload_keeps_place(browser, site_url, case):
    """A reload with no chapter hash keeps the reader's place (judge C3-1 #1): below the pin (the footer on desktop, the
    tablet's native Price section) it comes back at the same offset; inside the pin it lands on the checkpoint's rest."""
    w, h = (820, 1180) if case.startswith("tablet") else (1440, 900)
    ctx = _ctx(browser, w, h)
    page = ctx.new_page()
    try:
        page.goto(site_url + "/", wait_until="load")
        _ready(page)
        _rest_on(page, 0)
        if case == "desktop-midpin":
            page.evaluate("() => FEStory.goTo('grow', {source: 'jump'})")
            _rest_on(page, 3)
            page.reload(wait_until="load")
            _ready(page)
            _rest_on(page, 3, 6000)
            return
        sel = ".site-footer" if case == "desktop-footer" else "#price"
        if case == "desktop-footer":
            page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        else:
            page.evaluate("(s) => window.scrollTo(0, document.querySelector(s).getBoundingClientRect().top + scrollY - 64)", sel)
        st = _wait(page, "s.phase === 'released'", 4000)
        page.wait_for_timeout(300)
        top0 = page.locator(sel).first.bounding_box()["y"]
        page.reload(wait_until="load")
        _ready(page)
        page.wait_for_timeout(600)
        top1 = page.locator(sel).first.bounding_box()["y"]
        st = page.evaluate(STATE)
        assert abs(top1 - top0) <= 2, f"{case}: reload moved {sel} from {top0:.0f} to {top1:.0f} ({st})"
        assert st["phase"] == "released", st
    finally:
        ctx.close()
