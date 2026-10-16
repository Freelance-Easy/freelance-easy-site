"""C4: the homepage story's URL + history (docs/interaction-contract.md v1: ICX-HIST.1-.9, ICX-JUMP.0-.5; decisions #18, #19,
#25), failing first: assets/story/story-url.js does not exist at 7f70d78 (C3 writes no history).

pushState / replaceState are spied from before the page's own scripts run (lib._INIT: window.__c2hist, each call carries the
engine state at the time of the write). Real wheel / key / click input drives the story. Ports: none (conftest's site_url).
Every assertion message starts with its ICX row id.
"""
from __future__ import annotations

import pathlib

import pytest
from playwright.sync_api import sync_playwright

import lib
from lib import BEATS, SLUGS, Cell, Story

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESK = Cell("desktop", 1440, 900, "dark")
DESK_LIGHT = Cell("desktop", 1440, 900, "light")
TABLET = Cell("tablet", 820, 1180, "dark")
PHONE = Cell("phone", 390, 664, "dark")
VIEWPORTS = [DESK, TABLET, PHONE]
SLACK = 0.5     # the same measured excess test_story_state.C5_SLACK carries (C5 removes it)


def allowance(distance: int) -> float:
    return lib.allowance(distance) + SLACK


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def open_page(browser, url: str, cell: Cell, theme: str | None = "dark"):
    """A page with the history spy installed, at `url` (a full URL), the engine up. Phone = touch + mobile."""
    phone = cell.width < 640
    ctx = browser.new_context(viewport={"width": cell.width, "height": cell.height}, reduced_motion="no-preference",
                              has_touch=phone, is_mobile=phone)
    if theme:
        ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{theme}')}}catch(e){{}}")
    ctx.add_init_script(lib._INIT)
    page = ctx.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_function("() => window.__site && window.__site.TL && window.FEStory && FEStory.destinations.length", timeout=10000)
    return ctx, page


def story_at(browser, site_url: str, path: str, cell: Cell, theme: str | None = None) -> Story:
    """A lib.Story (real input helpers) opened on `path`; the pinned mode of the cell (desktop / tablet)."""
    ctx = browser.new_context(viewport={"width": cell.width, "height": cell.height}, reduced_motion="no-preference")
    ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{theme or cell.theme}')}}catch(e){{}}")
    ctx.add_init_script(lib._INIT)
    page = ctx.new_page()
    page.goto(site_url + path, wait_until="load")
    page.wait_for_function("() => window.__site && window.__site.TL && window.FEStory", timeout=10000)
    m = page.evaluate("() => window.__site.map()")
    info = lib.Info(rest=lib._rest_times(m, cell.n_pinned), end_y=m["storyTop"] + m["scrollLen"], n=cell.n_pinned)
    st = Story(ctx, page, cell, info)
    page.mouse.move(cell.width / 2, cell.height / 2)
    return st


@pytest.fixture
def story(browser, site_url):
    st = story_at(browser, site_url, "/", DESK)
    res = st.wait_rest(12)
    assert res.status == "rest" and res.snap.index == 0, f"harness precondition: {res.snap.describe()}"
    yield st
    st.close()


def hash_now(page) -> str:
    return page.evaluate("() => location.hash")


def slug_state(page):
    return page.evaluate("() => (history.state || {}).story || null")


def state(page) -> dict:
    return page.evaluate("() => FEStory.state()")


def dests(page) -> list[dict]:
    return page.evaluate("() => FEStory.destinations")


def step_ok(res, idx: int, row: str) -> None:
    assert res.status == "rest" and res.snap.index == idx, (
        f"{row}: expected REST({BEATS[idx]}) within {res.elapsed:.1f}s, got {res.status}: {res.snap.describe()}")


# ----------------------------------------------------------------------------------------------------------- deep link

@pytest.mark.parametrize("cell", VIEWPORTS, ids=[c.name for c in VIEWPORTS])
def test_deep_link_each_destination(browser, site_url, cell: Cell):
    """ICX-JUMP.3 / ICX-HIST.3 / decisions #25: /#<slug> lands on that chapter (pinned rows: rendered is the target from the
    first frame; native rows: the page's own anchor scroll) and writes no history; then the URL follows the story: one
    step from the deep-linked chapter replaces it with the next chapter's slug (ICX-HIST.1)."""
    stepped = False
    for i, slug in enumerate(SLUGS):
        ctx, page = open_page(browser, f"{site_url}/#{slug}", cell)
        try:
            rows = dests(page)
            assert [r["slug"] for r in rows] == SLUGS, f"ICX-DEST: slugs {[r['slug'] for r in rows]}"
            row = rows[i]
            calls = page.evaluate("() => window.__c2hist.slice()")
            assert calls == [], f"ICX-HIST.3 ({cell.name} #{slug}): a deep link writes no history, saw {calls}"
            assert hash_now(page) == f"#{slug}", f"ICX-HIST.3 ({cell.name} #{slug}): the deep link's own URL stays, got {hash_now(page)!r}"
            if row["kind"] == "pinned":
                st = state(page)
                assert st["rendered"] == i and st["dest"] == i, f"ICX-JUMP.3 ({cell.name} #{slug}): rendered/dest {st['rendered']}/{st['dest']}, want {i}"
                if i > 0:
                    assert page.evaluate("() => window.scrollY") > 0, f"ICX-JUMP.3 ({cell.name} #{slug}): the page did not move to the chapter"
            else:
                page.wait_for_timeout(700)
                y = page.evaluate("() => window.scrollY")
                top = page.evaluate("(s) => document.getElementById(s).getBoundingClientRect().top", slug)
                at_end = page.evaluate("() => window.scrollY >= document.documentElement.scrollHeight - innerHeight - 2")
                assert y > 0 and (-4 <= top <= 140 or at_end), f"ICX-JUMP.3 ({cell.name} #{slug}): native anchor scroll left the section at {top:.0f}px (scrollY {y:.0f})"
            if not stepped and row["kind"] == "pinned" and i == 1:   # one deep link per viewport followed through a step
                stepped = True
                st0 = Story(ctx, page, cell, lib.Info(rest=[], end_y=0, n=0))
                length = page.evaluate("() => history.length")
                page.mouse.move(cell.width / 2, cell.height / 2)
                if cell.width >= 640:
                    page.wait_for_function("() => FEStory.state().phase === 'rest'", timeout=int(allowance(1) * 1000))
                    st0.wheel(100)
                else:
                    page.wait_for_function("() => FEStory.state().phase === 'rest'", timeout=int(allowance(1) * 1000))
                    page.evaluate("() => FEStory.goTo(2, {source: 'step'})")
                page.wait_for_function("() => FEStory.state().phase === 'rest' && FEStory.state().rendered === 2",
                                       timeout=int(allowance(2) * 1000))
                assert hash_now(page) == f"#{SLUGS[2]}" and slug_state(page) == SLUGS[2], (
                    f"ICX-HIST.1 ({cell.name}): a step after a deep link writes the next slug, got {hash_now(page)!r} / {slug_state(page)!r}")
                assert page.evaluate("() => history.length") == length, f"ICX-HIST.1 ({cell.name}): replaceState must not add an entry"
        finally:
            ctx.close()
    assert stepped


# ------------------------------------------------------------------------------------------------------------- steps

@pytest.mark.parametrize("cell", [DESK, DESK_LIGHT], ids=[c.id for c in (DESK, DESK_LIGHT)])
def test_steps_replace(browser, site_url, cell: Cell):
    """ICX-HIST.1/.5/.8: after EACH of 5 steps the URL is `#<slug of rendered>` (plain path for the first chapter),
    history.state records the slug and history.length is unchanged; one replaceState per step, no pushState."""
    st = story_at(browser, site_url, "/", cell)
    try:
        step_ok(st.wait_rest(12), 0, "harness precondition")
        length0 = st.page.evaluate("() => history.length")
        for i in range(1, 6):
            mark = st.hist_mark()
            st.wheel(100)
            res = st.wait_rest(allowance(1))
            step_ok(res, i, f"ICX-HIST.1 (step {i})")
            rendered = state(st.page)["rendered"]
            slug = dests(st.page)[rendered]["slug"]
            # the write follows the final landing by the quiet window (story-url.js QUIET); Your data rests 0.28 s after it
            st.page.wait_for_function("(s) => location.hash === '#' + s", arg=slug, timeout=1500)
            calls = st.hist()[0][mark[0]:]
            assert hash_now(st.page) == "#" + slug, f"ICX-HIST.1 (step {i}): location.hash {hash_now(st.page)!r}, want '#{slug}'"
            assert slug_state(st.page) == slug, f"ICX-HIST.1 (step {i}): history.state.story {slug_state(st.page)!r}, want {slug!r}"
            assert st.page.evaluate("() => history.length") == length0, f"ICX-HIST.1 (step {i}): history.length changed"
            assert [c[0] for c in calls] == ["replaceState"], f"ICX-HIST.1 (step {i}): one replaceState and no push, saw {calls}"
        # back to the first chapter: plain "/", no hash (ICX-HIST.5)
        for _ in range(5):
            st.wheel(-100)
            st.wait_rest(2.0)
        res = st.wait_rest(allowance(1))
        step_ok(res, 0, "ICX-HIST.5 (five back steps)")
        st.page.wait_for_function("() => location.hash === ''", timeout=2000)
        assert hash_now(st.page) == "" and "#" not in st.page.evaluate("() => location.href"), (
            f"ICX-HIST.5: the first chapter's URL is the plain path, got {st.page.evaluate('() => location.href')!r}")
        assert st.page.evaluate("() => history.length") == length0
    finally:
        st.close()


def test_pass_through_writes_nothing(story: Story):
    """ICX-HIST.1: a run of three quick steps writes once, at the final landing, and never a passed-through chapter."""
    mark = story.hist_mark()
    for _ in range(3):
        story.wheel(100)
        story.idle(300)
    step_ok(story.wait_rest(allowance(3)), 3, "ICX-HIST.1")
    calls = story.hist()[0][mark[0]:]
    assert [(c[0], c[1].split("#")[-1]) for c in calls] == [("replaceState", SLUGS[3])], f"ICX-HIST.1: got {calls}"


# ------------------------------------------------------------------------------------------------------------- jumps

def test_jump_pushes_back_returns(story: Story):
    """ICX-HIST.2/.3, ICX-JUMP.4: End = one pushState '#get-the-app' at its landing; Back = popstate -> the first chapter,
    Forward -> the last: both with no pushState/replaceState call at all."""
    page = story.page
    length0 = page.evaluate("() => history.length")
    mark = story.hist_mark()
    story.key("End")
    step_ok(story.wait_rest(allowance(1)), 8, "ICX-HIST.2 (End)")
    calls = story.hist()[0][mark[0]:]
    assert [c[0] for c in calls] == ["pushState"] and calls[0][1].endswith("#" + SLUGS[8]), f"ICX-HIST.2: End pushes one '#{SLUGS[8]}', saw {calls}"
    assert (calls[0][2] or {}).get("fe", {}).get("rendered") == 8, "ICX-HIST.2: the push happened before the final landing"
    assert page.evaluate("() => history.length") == length0 + 1, "ICX-HIST.2: exactly one new entry"
    assert slug_state(page) == SLUGS[8]

    mark = story.hist_mark()
    page.go_back()
    step_ok(story.wait_rest(allowance(1)), 0, "ICX-JUMP.4 (Back)")
    assert hash_now(page) == "", f"ICX-HIST.5: Back returns to the plain URL, got {hash_now(page)!r}"
    assert story.hist()[0][mark[0]:] == [], f"ICX-HIST.3: popstate must not write, saw {story.hist()[0][mark[0]:]}"
    assert page.evaluate("() => history.length") == length0 + 1

    page.go_forward()
    step_ok(story.wait_rest(allowance(1)), 8, "ICX-JUMP.4 (Forward)")
    assert hash_now(page) == "#" + SLUGS[8]
    assert story.hist()[0][mark[0]:] == [], f"ICX-HIST.3: popstate must not write, saw {story.hist()[0][mark[0]:]}"


def test_jump_run_extended_by_a_step_still_pushes_once(story: Story):
    """ICX-HIST.2: gestures that extend a jump's run keep one pushState at the final landing (Back undoes the whole run)."""
    page = story.page
    length0 = page.evaluate("() => history.length")
    mark = story.hist_mark()
    page.evaluate("() => FEStory.goTo(2, {source: 'jump'})")
    story.idle(30)          # inside the dip's fade-out: the cut moves, the run is still one run (ICX-DIP.2)
    story.wheel(100)
    step_ok(story.wait_rest(allowance(3)), 3, "ICX-HIST.2")
    calls = story.hist()[0][mark[0]:]
    assert [c[0] for c in calls] == ["pushState"] and calls[0][1].endswith("#" + SLUGS[3]), f"ICX-HIST.2: got {calls}"
    assert page.evaluate("() => history.length") == length0 + 1


# ---------------------------------------------------------------------------------------------------------------- init

def test_init_never_writes(browser, site_url):
    """ICX-HIST.3: a load with a chapter hash and a reload make no pushState/replaceState call; the reload lands on the
    finished frame (ICX-JUMP.3); a plain load writes nothing either."""
    st = story_at(browser, site_url, "/#dashboard", DESK)
    try:
        step_ok(st.wait_rest(allowance(1)), 3, "ICX-JUMP.3 (deep link plays, then rests)")
        assert st.hist()[0] == [], f"ICX-HIST.3: deep link wrote {st.hist()[0]}"
        assert hash_now(st.page) == "#dashboard"
        length = st.page.evaluate("() => history.length")
        st.page.reload(wait_until="load")
        st.page.wait_for_function("() => window.__site && window.__site.TL && window.FEStory", timeout=10000)
        res = st.wait_rest(4)
        step_ok(res, 3, "ICX-JUMP.3 (reload lands on the finished frame)")
        assert st.hist()[0] == [], f"ICX-HIST.3: reload wrote {st.hist()[0]}"
        assert st.page.evaluate("() => history.length") == length and hash_now(st.page) == "#dashboard"
    finally:
        st.close()
    plain = story_at(browser, site_url, "/", DESK)
    try:
        step_ok(plain.wait_rest(12), 0, "plain load")
        assert plain.hist()[0] == [], f"ICX-HIST.3: a plain load wrote {plain.hist()[0]}"
    finally:
        plain.close()


@pytest.mark.parametrize("key,idx,slug", [("top", 0, "new-invoice"), ("how", 1, "templates"), ("pricing", 6, "price"), ("download", 8, "get-the-app")])
def test_legacy_aliases(browser, site_url, key: str, idx: int, slug: str):
    """ICX-HIST.6 / decisions #19: #top #how #pricing #download land on their chapter, and ONE replaceState swaps the URL
    for the slug (plain path for #top); history.length is that of a plain load."""
    base_ctx, base = open_page(browser, site_url + "/", DESK)
    try:
        length = base.evaluate("() => history.length")
    finally:
        base_ctx.close()
    ctx, page = open_page(browser, f"{site_url}/#{key}", DESK)
    try:
        calls = page.evaluate("() => window.__c2hist.slice()")
        want = "/" if slug == "new-invoice" else f"/#{slug}"
        assert [c[0] for c in calls] == ["replaceState"] and calls[0][1] == want, f"ICX-HIST.6 (#{key}): want one replaceState '{want}', saw {calls}"
        assert hash_now(page) == ("" if slug == "new-invoice" else "#" + slug)
        assert page.evaluate("() => history.length") == length, f"ICX-HIST.6 (#{key}): history.length changed"
        page.wait_for_function(f"() => FEStory.state().rendered === {idx}", timeout=5000)
        assert page.evaluate("() => window.__c2hist.length") == 1, "ICX-HIST.6: the deep-link landing wrote again"
    finally:
        ctx.close()


def test_theme_hash_read_only(browser, site_url):
    """ICX-HIST.7/.4: #light is read on load (the stored theme is dark) and kept as is; the story starts on the first
    chapter; toggling the theme leaves URL, state and history.length unchanged and writes nothing."""
    st = story_at(browser, site_url, "/#light", DESK, theme="dark")
    try:
        step_ok(st.wait_rest(12), 0, "ICX-HIST.7 (the first chapter)")
        assert st.page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "light", "ICX-HIST.7: #light not read on load"
        assert st.hist()[0] == [] and hash_now(st.page) == "#light", f"ICX-HIST.7: home wrote {st.hist()[0]} / {hash_now(st.page)!r}"
        length = st.page.evaluate("() => history.length")
        st.page.click("[data-theme-toggle]")
        st.page.wait_for_timeout(1500)
        assert st.page.evaluate("() => document.documentElement.getAttribute('data-theme')") == "dark", "harness: the toggle did not flip the theme"
        assert hash_now(st.page) == "#light" and st.page.evaluate("() => history.length") == length, "ICX-HIST.4: the theme toggle touched the URL"
        assert st.hist()[0] == [], f"ICX-HIST.4: the theme toggle wrote {st.hist()[0]}"
    finally:
        st.close()


def test_no_grow_slug(story: Story):
    """The destination 'Dashboard' is `dashboard`: no slug, no written URL and no line of story-url.js carries 'grow'."""
    page = story.page
    assert not [s for s in SLUGS if "grow" in s] and not [d for d in dests(page) if "grow" in d["slug"]], "ICX-DEST: a slug contains 'grow'"
    story.key("End")
    step_ok(story.wait_rest(allowance(1)), 8, "ICX-HIST.2")
    story.wheel(-100)
    step_ok(story.wait_rest(allowance(1)), 7, "ICX-HIST.1")
    urls = [c[1] for c in story.hist()[0]]
    assert urls and not [u for u in urls if "grow" in u.lower()], f"ICX-HIST.5: a written URL carries 'grow': {urls}"
    src = (ROOT / "assets/story/story-url.js").read_text()
    assert "grow" not in src.lower(), "story-url.js mentions 'grow'"


# ---------------------------------------------------------------------------------------------------- hashchange, logo

@pytest.mark.parametrize("key,idx,slug", [("download", 8, "get-the-app"), ("pricing", 6, "price"), ("templates", 1, "templates")])
def test_hashchange_jumps(story: Story, key: str, idx: int, slug: str):
    """ICX-HIST.6 / ICX-JUMP: a same-page link (#download, #pricing, a slug) is a jump to its chapter: the browser's own
    entry is kept (history.length +1, not two), the script only replaces its URL with the slug (never a pushState); Back
    returns to the first chapter with no write."""
    page = story.page
    length0 = page.evaluate("() => history.length")
    mark = story.hist_mark()
    page.evaluate("(k) => { const a = document.createElement('a'); a.href = '#' + k; a.id = 'probe-link'; document.body.appendChild(a); a.click(); }", key)
    step_ok(story.wait_rest(allowance(1)), idx, f"ICX-JUMP (#{key})")
    calls = story.hist()[0][mark[0]:]
    assert all(c[0] == "replaceState" for c in calls), f"ICX-HIST.6 (#{key}): hashchange must not pushState (the browser added the entry), saw {calls}"
    assert hash_now(page) == "#" + slug, f"ICX-HIST.6 (#{key}): URL {hash_now(page)!r}, want '#{slug}'"
    assert page.evaluate("() => history.length") == length0 + 1, "ICX-HIST.6: one entry for the link, no more"
    assert slug_state(page) == slug
    mark = story.hist_mark()
    page.go_back()
    step_ok(story.wait_rest(allowance(1)), 0, "ICX-JUMP.4 (Back after a link)")
    assert hash_now(page) == "" and story.hist()[0][mark[0]:] == [], f"ICX-HIST.3: popstate wrote {story.hist()[0][mark[0]:]}"


def test_logo_jumps_home(story: Story):
    """B4 judge LOW / ICX-JUMP + ICX-HIST.2: the logo on '/' from a later chapter is a jump to the first chapter: no page
    load, one pushState to the plain path; a modifier click is left to the browser; at the first chapter it does nothing
    (ICX-JUMP.0: no write, no new entry)."""
    page = story.page
    page.evaluate("() => { window.__navs = 0; window.addEventListener('beforeunload', () => { window.__navs++; }); }")
    # zero distance first: nothing moves, nothing is written
    mark = story.hist_mark()
    length0 = page.evaluate("() => history.length")
    page.click("a.brand")
    page.wait_for_timeout(600)
    assert story.hist()[0][mark[0]:] == [] and page.evaluate("() => history.length") == length0, "ICX-JUMP.0: the logo at the first chapter wrote"
    # a modifier click is not intercepted
    seen = page.evaluate("""() => new Promise((res) => {
      const a = document.querySelector('a.brand'); let dp = null;
      window.addEventListener('click', (e) => { dp = e.defaultPrevented; e.preventDefault(); }, { once: true });
      a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, ctrlKey: true, button: 0 }));
      res(dp);
    })""")
    assert seen is False, "ICX-JUMP: a ctrl-click on the logo must be left to the browser"
    story.key("End")
    step_ok(story.wait_rest(allowance(1)), 8, "precondition: End")
    length1 = page.evaluate("() => history.length")
    mark = story.hist_mark()
    page.click("a.brand")
    step_ok(story.wait_rest(allowance(1)), 0, "ICX-JUMP (logo)")
    calls = story.hist()[0][mark[0]:]
    assert [c[0] for c in calls] == ["pushState"] and calls[0][1] == "/", f"ICX-HIST.2: the logo pushes the plain path once, saw {calls}"
    assert page.evaluate("() => history.length") == length1 + 1 and hash_now(page) == ""
    assert page.evaluate("() => window.__navs") == 0, "ICX-JUMP: the logo reloaded the page"


def test_legacy_link_to_the_current_chapter_is_normalised(browser, site_url):
    """ICX-HIST.6 (Sol C4-1 M): a #how link while the story already rests on Templates moves nothing, yet the entry the
    browser added gets the slug by replaceState (never a pushState); history.length +1 (the link's own entry)."""
    st = story_at(browser, site_url, "/#templates", DESK)
    try:
        step_ok(st.wait_rest(allowance(1)), 1, "precondition: deep link to Templates")
        length0 = st.page.evaluate("() => history.length")
        mark = st.hist_mark()
        st.page.evaluate("() => { const a = document.createElement('a'); a.href = '#how'; document.body.appendChild(a); a.click(); }")
        st.page.wait_for_function("() => location.hash === '#templates'", timeout=2000)
        calls = st.hist()[0][mark[0]:]
        assert [c[0] for c in calls] == ["replaceState"], f"ICX-HIST.6: got {calls}"
        assert st.page.evaluate("() => history.length") == length0 + 1
    finally:
        st.close()


def test_link_during_an_unfinished_jump_adds_one_entry(story: Story):
    """ICX-HIST.2/.6 (Sol C4-1 H): a hash link clicked while an explicit jump is still under way supersedes it: the
    browser's entry for the link is the only one added; the landing replaces its URL, no second pushState."""
    page = story.page
    length0 = page.evaluate("() => history.length")
    mark = story.hist_mark()
    page.evaluate("""() => { FEStory.goTo(5, {source: 'jump'});
      const a = document.createElement('a'); a.href = '#download'; document.body.appendChild(a); a.click(); }""")
    step_ok(story.wait_rest(allowance(3)), 8, "ICX-JUMP (link over a jump)")
    page.wait_for_function("() => location.hash === '#get-the-app'", timeout=2000)
    calls = story.hist()[0][mark[0]:]
    assert all(c[0] == "replaceState" for c in calls), f"ICX-HIST.6: a second entry was pushed: {calls}"
    assert page.evaluate("() => history.length") == length0 + 1


def test_back_right_after_a_jump_finds_its_entry(story: Story):
    """ICX-HIST.2 (Sol C4-1 M): the jump's pushState is written at its landing, so Back immediately after it returns to the
    first chapter instead of leaving the page."""
    page = story.page
    length0 = page.evaluate("() => history.length")
    story.key("End")
    page.wait_for_function(f"() => history.length === {length0 + 1}", timeout=3000)
    page.go_back()
    step_ok(story.wait_rest(allowance(1)), 0, "ICX-JUMP.4 (Back at once)")
    assert hash_now(page) == "" and page.evaluate("() => location.pathname") == "/"
