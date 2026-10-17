"""INT5-fix: the INT-5 gate's cross-piece history / navigation findings (qa/INT5-sol-1.md, qa/INT5-astra-1.md), each
failing first at f6481e2. pushState / replaceState are spied from before the page's own scripts run (lib._INIT:
window.__c2hist). Ports: none (conftest's site_url). Every assertion message starts with its finding number.

 1. Classic on / off before a jump lands: the jump's pending push is void (the next ordinary step replaces).
 2. Back in Classic restores a saved offset only when the entry's mode and width are the current ones.
 3. A theme switch during a tablet native jump carries the jump through to its target (and the URL is the target's).
 4. Home from a native section saves the departing pixel before the re-entry moves the page (Back returns to it).
 5. Reload after scrolling past the desktop story into the footer keeps the footer place (not #get-the-app's rest).
 6. A re-entry from a native section into the pinned story writes the last pinned chapter's URL (replaceState).
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

import lib
from lib import SLUGS, Cell

DESK = Cell("desktop", 1440, 900, "dark")
TABLET = Cell("tablet", 820, 1180, "dark")
PRICE_TOP = "() => document.getElementById('price').getBoundingClientRect().top"
INTO_PRICE = "() => window.scrollTo(0, document.getElementById('price').getBoundingClientRect().top + scrollY - 64 + 300)"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def open_page(browser, url: str, cell: Cell):
    ctx = browser.new_context(viewport={"width": cell.width, "height": cell.height}, reduced_motion="no-preference")
    ctx.add_init_script("try{localStorage.setItem('fe-theme','dark')}catch(e){}")
    ctx.add_init_script(lib._INIT)
    page = ctx.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_function("() => window.__site && window.__site.TL && window.FEStory && FEStory.destinations.length", timeout=10000)
    page.wait_for_timeout(1300)        # past the load's own settle (story-url.js's `initializing`)
    page.mouse.move(cell.width / 2, cell.height / 2)
    return ctx, page


def at_rest(page, idx: int, timeout: int = 12000) -> None:
    page.wait_for_function(f"() => {{ const s = FEStory.state(); return s.phase === 'rest' && s.rendered === {idx} && s.dest === {idx}; }}",
                           timeout=timeout)


def calls(page) -> list:
    return page.evaluate("() => window.__c2hist.slice()")


def into_price(page) -> float:
    """Tablet: 300 px into Price (a native row); the spy has written /#price. Returns Price's top."""
    assert page.evaluate("() => FEStory.destinations.find(d => d.slug === 'price').kind") == "native", "harness: price native"
    page.evaluate(INTO_PRICE)
    page.wait_for_timeout(900)
    assert page.evaluate("() => location.hash") == "#price", "harness: the spy should have written /#price"
    return page.evaluate(PRICE_TOP)


def test_1_classic_toggle_voids_a_pending_jump_push(browser, site_url):
    ctx, page = open_page(browser, site_url + "/", DESK)
    try:
        at_rest(page, 0)
        length0 = page.evaluate("() => history.length")
        # a far jump (a dip), then Classic on and off before it lands: the jump never lands
        page.evaluate("() => { FEStoryURL.jump('your-data'); FEStory.setClassic(true); FEStory.setClassic(false); }")
        page.wait_for_function("() => FEStory.state().phase === 'rest'", timeout=8000)
        page.wait_for_timeout(600)
        n0 = len(calls(page))
        r0 = page.evaluate("() => FEStory.state().rendered")
        page.evaluate("(k) => FEStory.goTo(k, {source: 'step'})", r0 + 1 if r0 < 8 else r0 - 1)
        page.wait_for_function("() => FEStory.state().phase === 'rest'", timeout=8000)
        page.wait_for_timeout(600)         # past story-url.js's QUIET window
        after = calls(page)
        assert all(c[0] == "replaceState" for c in after), f"1 (ICX-HIST.1): a push after Classic on/off: {after}"
        assert len(after) > n0, f"1: the step wrote nothing: {after}"
        assert page.evaluate("() => history.length") == length0, f"1 (ICX-HIST.1): history grew: {after}"
    finally:
        ctx.close()


def test_2_back_in_classic_ignores_another_modes_offset(browser, site_url):
    ctx, page = open_page(browser, site_url + "/", TABLET)
    try:
        into_price(page)                      # this entry's state: y in the tablet story layout
        page.evaluate("() => FEStoryURL.jump('new-invoice')")
        page.wait_for_function("() => location.hash === ''", timeout=12000)
        at_rest(page, 0)
        page.wait_for_timeout(400)
        page.evaluate("() => FEStory.setClassic(true)")
        page.wait_for_function("() => FEStory.mode === 'classic'", timeout=5000)
        page.wait_for_timeout(600)
        st = page.evaluate("() => history.state")
        page.evaluate("() => { window.__pops = []; addEventListener('popstate', () => __pops.push([location.hash, (history.state || {}).m])); history.back(); }")
        page.wait_for_function("() => window.__pops.length > 0", timeout=5000)
        page.wait_for_timeout(1500)
        top = page.evaluate(PRICE_TOP)
        pops, now = page.evaluate("() => window.__pops"), page.evaluate("() => location.hash")
        assert pops[0] == ["#price", "tablet"], f"harness: Back should reach the tablet #price entry, got {pops} (left {st})"
        assert now == "#price" and -4 <= top <= 200, (
            f"2: Back in Classic to a tablet entry landed #price at {top:.0f}px (URL now {now!r}), not its anchor")
    finally:
        ctx.close()


def test_3_theme_switch_carries_a_native_jump_through(browser, site_url):
    ctx, page = open_page(browser, site_url + "/", TABLET)
    try:
        at_rest(page, 0)
        length0 = page.evaluate("() => history.length")
        page.evaluate("() => FEStoryURL.jump('price')")
        page.wait_for_timeout(250)             # the smooth scroll is under way
        mid = page.evaluate("() => scrollY")
        page.evaluate("() => document.querySelector('[data-theme-toggle]').click()")
        page.wait_for_timeout(4000)            # past the native arrival's backstop (2.5 s) and any settle
        top = page.evaluate(PRICE_TOP)
        got = [(c[0], c[1]) for c in calls(page)]
        assert page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light", "harness: the toggle never switched"
        assert mid > 0, "harness: the native scroll had not started"
        assert -4 <= top <= 200, f"3: the native jump did not arrive (Price at {top:.0f}px, scrolled {mid}px when toggled); writes {got}"
        assert got == [("pushState", "/#price")], f"3 (ICX-JUMP.5): one push for the jump, at its arrival; saw {got}"
        assert page.evaluate("() => history.length") == length0 + 1
    finally:
        ctx.close()


def test_4_home_from_native_saves_the_departing_pixel(browser, site_url):
    ctx, page = open_page(browser, site_url + "/", TABLET)
    try:
        top0 = into_price(page)
        page.keyboard.press("Home")
        page.wait_for_function("() => location.hash === ''", timeout=12000)
        at_rest(page, 0)
        page.wait_for_timeout(400)
        page.evaluate("() => history.back()")
        page.wait_for_function("() => location.hash === '#price'", timeout=5000)
        page.wait_for_timeout(1500)
        top1 = page.evaluate(PRICE_TOP)
        assert abs(top1 - top0) <= 2, f"4: Back after Home moved #price from {top0:.0f} to {top1:.0f}px (the departing pixel was not saved)"
    finally:
        ctx.close()


def test_5_reload_below_the_desktop_story_keeps_the_footer(browser, site_url):
    ctx, page = open_page(browser, site_url + "/", DESK)
    try:
        page.evaluate("() => FEStoryURL.jump('get-the-app')")
        page.wait_for_function("() => location.hash === '#get-the-app'", timeout=15000)
        at_rest(page, 8, timeout=15000)
        page.wait_for_timeout(500)
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_function("() => FEStory.state().phase === 'released'", timeout=5000)
        page.wait_for_timeout(800)
        y0 = page.evaluate("() => scrollY")
        assert page.evaluate("() => location.hash") == "#get-the-app", "harness: the URL should still be #get-the-app"
        n = len(calls(page))
        page.reload(wait_until="load")
        page.wait_for_function("() => window.__site && window.__site.TL && window.FEStory", timeout=10000)
        page.wait_for_timeout(1500)
        y1 = page.evaluate("() => scrollY")
        s = page.evaluate("() => FEStory.state()")
        assert page.evaluate("() => window.__c2hist.slice()") == [], "5 (ICX-HIST.3): the reload wrote"
        assert abs(y1 - y0) <= 2 and s["phase"] == "released", f"5: the reload left the footer ({y0} -> {y1}, {s}); writes before {n}"
        # 6 (its distance-0 half, ICX-HIST.8): a re-entry whose URL already names the last pinned chapter writes nothing
        page.mouse.move(DESK.width / 2, DESK.height / 2)
        for _ in range(60):
            page.mouse.wheel(0, -120)
            page.wait_for_timeout(100)
            if page.evaluate("() => FEStory.state().phase === 'rest'"):
                break
        at_rest(page, 8, timeout=4000)
        page.wait_for_timeout(700)
        assert page.evaluate("() => window.__c2hist.slice()") == [], "6 (ICX-HIST.8): a re-entry onto the URL's own chapter wrote"
    finally:
        ctx.close()


def test_6_reentry_from_native_writes_the_last_pinned_url(browser, site_url):
    ctx, page = open_page(browser, site_url + "/", TABLET)
    try:
        pinned = [d["slug"] for d in page.evaluate("() => FEStory.destinations") if d["kind"] == "pinned"]
        last = SLUGS.index(pinned[-1])
        page.evaluate("() => window.scrollTo(0, document.getElementById('price').getBoundingClientRect().top + scrollY - 64)")
        page.wait_for_timeout(900)
        assert page.evaluate("() => location.hash") == "#price", "harness: the spy should have written /#price"
        length0 = page.evaluate("() => history.length")
        n0 = len(calls(page))
        for _ in range(40):
            page.mouse.wheel(0, -120)
            page.wait_for_timeout(120)
            if page.evaluate("() => FEStory.state().phase === 'rest'"):
                break
        at_rest(page, last, timeout=4000)
        page.wait_for_timeout(700)             # past story-url.js's QUIET window
        new = [(c[0], c[1]) for c in calls(page)[n0:]]
        assert page.evaluate("() => location.hash") == "#" + pinned[-1], f"6 (ICX-HIST.8): the re-entry left the URL at {page.evaluate('() => location.hash')!r}; writes {new}"
        assert new and all(c[0] == "replaceState" for c in new), f"6: a re-entry replaces; saw {new}"
        assert page.evaluate("() => history.length") == length0
    finally:
        ctx.close()
