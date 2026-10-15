"""The homepage header's Download (A9): a real download in place on a Mac or a Windows PC, "send to computer" on a
phone, a status line with the requirement or the Windows warning and the install help. Local servers only
(tests/download/conftest.py): nothing reaches the live site or a release URL."""
from __future__ import annotations

import json

import pytest
from playwright.sync_api import sync_playwright

MAC_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
WIN_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
PHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
VISITORS = {"mac": (MAC_UA, "MacIntel"), "win": (WIN_UA, "Win32"), "phone": (PHONE_UA, "iPhone")}
CTA = ".site-header .nav-cta"
STATUS = '.site-header [data-dl-status][data-for="header"]'
NOTE = '.site-header [data-dl-note][data-for="header"]'


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def browser(pw):
    b = pw.chromium.launch()
    yield b
    b.close()


@pytest.fixture(scope="module")
def webkit(pw):
    try:
        b = pw.webkit.launch()
    except Exception as e:  # noqa: BLE001 - not installed here
        pytest.skip(f"webkit not installed: {e}")
    yield b
    b.close()


def _opener(browser, contexts):
    def open_(who: str, url: str, width: int = 1440, clock: bool = False):
        ua, platform = VISITORS[who]
        if who == "phone":
            ctx = browser.new_context(user_agent=ua, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, accept_downloads=True)
        else:
            ctx = browser.new_context(user_agent=ua, viewport={"width": width, "height": 900}, accept_downloads=True)
        ctx.add_init_script(f"Object.defineProperty(Navigator.prototype, 'platform', {{ get: () => {json.dumps(platform)} }});")
        ctx.add_init_script("window.__calls = []; window.plausible = function (n, o) { window.__calls.push([n, (o && o.props) || null]); };")
        contexts.append(ctx)
        page = ctx.new_page()
        if clock:
            page.clock.install()
        page.goto(url, wait_until="load")
        return page

    return open_


@pytest.fixture
def visit(browser):
    contexts = []
    yield _opener(browser, contexts)
    for ctx in contexts:
        ctx.close()


@pytest.fixture
def visit_webkit(webkit):
    contexts = []
    yield _opener(webkit, contexts)
    for ctx in contexts:
        ctx.close()


def _downloads_in_place(dl_site, visit, who: str, os_: str, filename: str):
    start = dl_site.url + "/"
    page = visit(who, start)
    before = len(dl_site.hits)
    with page.expect_download(timeout=5000) as info:
        page.locator(CTA).click()
    download = info.value
    assert download.suggested_filename == filename
    page.wait_for_timeout(300)
    assert page.url == start, "the page stays where it is"
    assert dl_site.hits[before:] == [f"/dl/{os_}/site"]
    assert page.evaluate("window.__calls") == [["Download Click", {"os": os_, "campaign": "site", "page": "home", "placement": "header"}]]


def test_mac_click_downloads_in_place(dl_site, visit):
    _downloads_in_place(dl_site, visit, "mac", "mac", "Freelance-Easy.dmg")


def test_win_click_downloads_in_place(dl_site, visit):
    # /dl/win/site is a 302 to the asset on another origin, as _redirects sends it to GitHub
    _downloads_in_place(dl_site, visit, "win", "win", "Freelance-Easy-Setup.exe")


def _stays_after_failure(dl_site, visit, who: str, os_: str):
    start = dl_site.url + "/"
    page = visit(who, start)
    before = len(dl_site.hits)
    page.locator(CTA).click()
    page.wait_for_timeout(800)
    assert dl_site.hits[before:] == [f"/dl/{os_}/site"], "the download was asked for"
    assert page.url == start, "an error answer never replaces the homepage"
    assert page.locator(CTA).is_visible(), "the header is still there"
    assert page.locator("[data-beat]").count() > 3, "the story is still there"
    assert page.locator(STATUS).is_visible(), "the status line and its install help are still there"


def test_failed_mac_download_stays_in_place(dl_site, visit):
    dl_site.mode["mac"] = "502"
    _stays_after_failure(dl_site, visit, "mac", "mac")


def test_failed_win_download_stays_in_place(dl_site, visit):
    dl_site.mode["win"] = "404"  # GitHub's 404 after the redirect
    _stays_after_failure(dl_site, visit, "win", "win")


def test_webkit_downloads_in_place_and_survives_a_502(dl_site, visit_webkit):
    """Playwright's WebKit (Safari's engine, not Safari): the hidden-frame download and the 502 case."""
    _downloads_in_place(dl_site, visit_webkit, "mac", "mac", "Freelance-Easy.dmg")
    dl_site.mode["mac"] = "502"
    _stays_after_failure(dl_site, visit_webkit, "mac", "mac")


def test_wire_is_idempotent(dl_site, visit):
    page = visit("mac", dl_site.url + "/")
    page.evaluate("FEDownload.wire(document.querySelector('.site-header .nav-cta'))")
    page.evaluate("FEDownload.wire(document.querySelector('.site-header .nav-cta'), {placement: 'header', platforms: ['mac']})")
    before = len(dl_site.hits)
    with page.expect_download(timeout=5000):
        page.locator(CTA).click()
    page.wait_for_timeout(300)
    assert len(page.evaluate("window.__calls")) == 1, "one click, one event"
    assert dl_site.hits[before:] == ["/dl/mac/site"], "one click, one request"


@pytest.mark.parametrize(
    "query, want",
    [("?utm_campaign=f1", "/dl/mac/f1"), ("?utm_campaign=F1&gclid=abc", "/dl/mac/f1"), ("?utm_campaign=nope", None), ("", None)],
)
def test_campaign_kept(dl_site, visit, query, want):
    page = visit("mac", dl_site.url + "/" + query)
    page_label = page.evaluate("document.body.getAttribute('data-campaign') || 'site'")
    href = page.locator(CTA).get_attribute("href")
    assert href == (want or f"/dl/mac/{page_label}")
    assert "?" not in href, "never a query string on /dl/ (_redirects)"


def test_phone_keeps_send_to_computer(dl_site, visit):
    page = visit("phone", dl_site.url + "/")
    cta = page.locator(CTA)
    assert cta.get_attribute("href") == "#download"
    assert cta.inner_text().strip() == "Get it on Mac"
    downloads = []
    page.on("download", lambda d: downloads.append(d))
    before = len(dl_site.hits)
    cta.click()
    page.wait_for_timeout(300)
    assert downloads == [] and dl_site.hits[before:] == [], "no file on a phone"
    assert page.evaluate("window.__calls") == []
    assert not page.locator(STATUS).is_visible()
    assert not page.locator(NOTE).is_visible()
    # the download block it jumps to still sends the page to the visitor's computer
    end = page.locator('[data-dl][data-placement="end"] [data-role="primary"]')
    assert end.inner_text().strip() == "Send to my Mac"
    assert end.get_attribute("role") == "button" and end.get_attribute("href") is None


@pytest.mark.parametrize(
    "who, note, words, link",
    [
        ("mac", "Apple Silicon Macs (M1 or later)", ["should start in a moment", "Apple Silicon Macs", "macOS 12 or later"], "/install#mac"),
        ("win", "Windows 10 and 11, 64-bit", ["should start in a moment", "Windows warns you", "code-signed"], "/install#windows"),
    ],
)
def test_status_line(dl_site, visit, who, note, words, link):
    page = visit(who, dl_site.url + "/")
    # before the click: the platform beside the button; the status line not yet
    assert page.locator(NOTE).is_visible()
    assert page.locator(NOTE).inner_text().strip() == note
    assert page.locator(CTA).get_attribute("aria-describedby") == page.locator(NOTE).get_attribute("id")
    status = page.locator(STATUS)
    assert not status.is_visible()
    with page.expect_download(timeout=5000):
        page.locator(CTA).click()
    assert status.is_visible()
    text = status.inner_text()
    for w in words:
        assert w in text
    assert status.locator(f'a[href="{link}"]').count() == 1
    assert not page.locator(NOTE).is_visible(), "the note steps aside while the status line says it"
    status.get_by_role("button", name="Close").click()
    page.wait_for_timeout(350)  # the 200 ms fade
    assert not status.is_visible()
    assert page.locator(NOTE).is_visible(), "the note is back"


def test_status_is_a_live_region_that_stays(dl_site, visit):
    page = visit("mac", dl_site.url + "/")
    box = page.locator(STATUS)
    # in the DOM, empty and not hidden before the click, so filling it is announced
    assert box.count() == 1
    assert box.get_attribute("role") == "status" and box.get_attribute("aria-live") == "polite"
    assert box.get_attribute("hidden") is None
    assert box.evaluate("b => b.childNodes.length") == 0
    with page.expect_download(timeout=5000):
        page.locator(CTA).click()
    assert box.get_attribute("hidden") is None and "should start" in box.inner_text()
    page.keyboard.press("Escape")
    page.wait_for_timeout(350)
    assert box.count() == 1 and box.get_attribute("hidden") is None
    assert box.evaluate("b => b.childNodes.length") == 0, "closed = emptied, not removed or hidden"


def test_status_closes_itself(dl_site, visit):
    # after ~12 s
    page = visit("mac", dl_site.url + "/", clock=True)
    with page.expect_download(timeout=5000):
        page.locator(CTA).click()
    page.mouse.move(10, 600)  # not hovering the card
    box = page.locator(STATUS)
    page.clock.run_for(11000)
    assert box.is_visible()
    page.clock.run_for(1500)
    assert not box.is_visible()
    # once the page scrolls a viewport
    page2 = visit("win", dl_site.url + "/")
    with page2.expect_download(timeout=5000):
        page2.locator(CTA).click()
    assert page2.locator(STATUS).is_visible()
    page2.evaluate("window.scrollBy(0, window.innerHeight + 40)")
    page2.wait_for_timeout(500)
    assert not page2.locator(STATUS).is_visible()


@pytest.mark.parametrize("width", [640, 800, 1024, 1440])
def test_note_beside_download_without_crowding(dl_site, visit, width):
    page = visit("mac", dl_site.url + "/", width=width)
    note, cta = page.locator(NOTE), page.locator(CTA)
    assert note.is_visible(), f"the requirement is in view beside Download at {width}"
    n, c = note.bounding_box(), cta.bounding_box()
    header = page.locator(".site-header").bounding_box()
    assert n["x"] + n["width"] <= c["x"] + 1, "the note sits left of the button"
    assert n["y"] >= header["y"] and n["y"] + n["height"] <= header["y"] + header["height"], "inside the header"
    tops = page.evaluate("[...document.querySelectorAll('.site-header .nav > *')].filter(e => e.offsetParent).map(e => Math.round(e.getBoundingClientRect().top + e.getBoundingClientRect().height / 2))")
    assert max(tops) - min(tops) <= 2, f"one row: {tops}"
    lines = page.evaluate("[...document.querySelectorAll('.site-header .nav a')].filter(e => e.offsetParent).map(e => e.getClientRects().length === 1 && e.getBoundingClientRect().height < 44)")
    assert all(lines), f"no nav link wraps at {width}: {lines}"
    # the status line covers the note without moving the nav
    before = page.locator(".site-header .nav a").first.bounding_box()
    page.route("**/dl/**", lambda r: r.abort())
    cta.click()
    assert page.locator(".site-header .nav a").first.bounding_box() == before
    brand = page.locator(".site-header .brand").bounding_box()
    nav = page.locator(".site-header .nav").bounding_box()
    assert brand["x"] + brand["width"] < nav["x"], "nothing overlaps the brand"
    assert page.evaluate("document.querySelector('.site-header .nav').scrollWidth <= document.querySelector('.site-header .nav').clientWidth + 1")


def test_platforms_option_mac_only(dl_site, visit):
    fixture = dl_site.url + "/tests/download/fixtures/mac-only.html"
    mac = visit("mac", fixture)
    assert mac.locator(CTA).get_attribute("href") == "/dl/mac/mac"
    win = visit("win", fixture)
    assert win.locator(CTA).get_attribute("href") == "#download", "a Mac-only Download never hands Windows a file"
    assert not win.locator(NOTE).is_visible()
    # the same through the JS option G1 uses
    assert win.evaluate("FEDownload.wire(document.getElementById('api-link'), {placement: 'x', platforms: ['mac']}), document.getElementById('api-link').getAttribute('href')") == "#download"
    assert mac.evaluate("FEDownload.wire(document.getElementById('api-link'), {placement: 'x', platforms: ['mac']}), document.getElementById('api-link').getAttribute('href')") == "/dl/mac/mac"
