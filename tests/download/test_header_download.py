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
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def visit(browser):
    contexts = []

    def open_(who: str, url: str):
        ua, platform = VISITORS[who]
        if who == "phone":
            ctx = browser.new_context(user_agent=ua, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, accept_downloads=True)
        else:
            ctx = browser.new_context(user_agent=ua, viewport={"width": 1440, "height": 900}, accept_downloads=True)
        ctx.add_init_script(f"Object.defineProperty(Navigator.prototype, 'platform', {{ get: () => {json.dumps(platform)} }});")
        ctx.add_init_script("window.__calls = []; window.plausible = function (n, o) { window.__calls.push([n, (o && o.props) || null]); };")
        contexts.append(ctx)
        page = ctx.new_page()
        page.goto(url, wait_until="load")
        return page

    yield open_
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
    _downloads_in_place(dl_site, visit, "win", "win", "Freelance-Easy-Setup.exe")


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
        ("mac", "Apple Silicon Macs (M1 or later)", ["Apple Silicon Macs (M1 or later)", "macOS 12 or later"], "/install#mac"),
        ("win", "Windows 10 or 11, 64-bit", ["Windows 10 and 11, 64-bit", "security warning"], "/install#windows"),
    ],
)
def test_status_line(dl_site, visit, who, note, words, link):
    page = visit(who, dl_site.url + "/")
    # before the click: the platform beside the button; the status line not yet
    assert page.locator(NOTE).is_visible()
    assert page.locator(NOTE).inner_text().strip() == note
    status = page.locator(STATUS)
    assert not status.is_visible()
    with page.expect_download(timeout=5000):
        page.locator(CTA).click()
    assert status.is_visible()
    text = status.inner_text()
    for w in words:
        assert w in text
    assert status.locator(f'a[href="{link}"]').count() == 1
    status.get_by_role("button", name="Close").click()
    assert not status.is_visible()


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
