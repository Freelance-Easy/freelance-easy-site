"""B2: the shared shell. One theme + shell head (src/partials/head.html), one footer with a footnotes block
(src/partials/footer.html), assets/site/shell.css + shell.js.

The MODULE gate is `/` plus a doc-page fixture (tests/fixtures/shell/doc.html): the doc pages are B7's ADOPT gate,
/pricing is PR-1's and the ad pages are G1's. The web-account hooks follow the contract snapshot
(children/E-web-account-contract.md § 6): data-flag="web-billing" hides the footer's Manage subscription unless the
site switch (FLAGS in shell.js) turns it on; web accounts are paused, so it ships off.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = "/tests/fixtures/shell/doc.html"
HEAD_SPAN = re.compile(r"[ \t]*<!-- fe-shell:head .*?<!-- /fe-shell:head -->\n", re.S)
FOOTER_SPAN = re.compile(r'<footer class="site-footer fe-shell-footer">.*?</footer>\n', re.S)
FICTIONAL = "Clients, invoices and amounts in the demos, screenshots and tour are fictional."
HEIGHTS = {1440: 900, 800: 900, 390: 844}

_spec = importlib.util.spec_from_file_location("run_axe", ROOT / "scripts" / "checks" / "run_axe.py")
run_axe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_axe)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def built(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def open_page(browser, url, *, width=1440, theme="dark", reduced=False, js=True, route=None):
    ctx = browser.new_context(viewport={"width": width, "height": HEIGHTS.get(width, 900)}, color_scheme=theme,
                              reduced_motion="reduce" if reduced else "no-preference", java_script_enabled=js)
    ctx.add_init_script("try{localStorage.setItem('fe-theme','" + theme + "')}catch(e){}")
    if route:
        ctx.route(*route)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_timeout(400)
    assert errors == [], errors
    return ctx, page


def to_bottom(page):
    page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
    page.wait_for_timeout(600)


# ---- the head ------------------------------------------------------------------------------------------------------

def test_theme_head_identical(site_url):
    """`/` and the doc fixture emit the same theme + shell head bytes, and those bytes are head.html's."""
    partial = (ROOT / "src" / "partials" / "head.html").read_text(encoding="utf-8")
    spans = {}
    for name in ("index.html", FIXTURE.lstrip("/")):
        found = HEAD_SPAN.findall(built(name))
        assert len(found) == 1, (name, len(found))
        spans[name] = found[0]
    assert spans["index.html"] == spans[FIXTURE.lstrip("/")] == partial
    for tag in ('<link rel="stylesheet" href="/assets/shared/theme.css" />',
                '<script src="/assets/shared/theme.js"></script>',
                '<link rel="stylesheet" href="/assets/site/shell.css" />',
                '<script src="/assets/site/shell.js" defer></script>'):
        assert partial.count(tag) == 1, tag


def test_fixture_footer_mirrors_partial():
    """The fixture's footer is footer.html byte for byte, so the fixture tests the footer that ships."""
    partial = (ROOT / "src" / "partials" / "footer.html").read_text(encoding="utf-8")
    partial = partial.replace("{{dl_fallback}}", "#download")  # (B7) the placeholder; `/` and the fixture fill #download
    assert FOOTER_SPAN.findall(built(FIXTURE.lstrip("/"))) == [partial]
    assert FOOTER_SPAN.findall(built("index.html")) == [partial]


# ---- axe -----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("path", ["/", FIXTURE])
def test_axe_zero(site_url, browser, path, theme):
    found = []
    for width in (1440, 390):
        found += run_axe.run_axe(browser, site_url + path, theme, width)
    assert found == [], found


# ---- the web-billing flag ------------------------------------------------------------------------------------------

MANAGE = 'footer a[data-flag-href="/account"]'


@pytest.mark.parametrize("path", ["/", FIXTURE])
def test_manage_link_hidden_without_flag(site_url, browser, path):
    """Manage subscription is in the footer, flagged web-billing, and hidden: with JS (the site switch is off) and
    without JS (the hidden attribute), at 1440 and 390. While off it is no link at all (no href: /account does not
    exist yet). On the fixture, a flagged control the page styles display: inline-flex stays hidden too (shell.css)."""
    for js in (True, False):
        for width in (1440, 390):
            ctx, page = open_page(browser, site_url + path, width=width, js=js)
            try:
                link = page.locator(MANAGE)
                assert link.count() == 1
                assert link.text_content().strip() == "Manage subscription"
                assert link.evaluate("a => a.closest('[data-flag]').getAttribute('data-flag')") == "web-billing"
                assert page.locator('a[href="/account"]').count() == 0, (path, js, width)
                to_bottom(page)
                assert not link.is_visible(), (path, js, width)
                if path == FIXTURE:
                    assert not page.locator("a.fixture-flagged").is_visible(), (js, width)
                # shell.css's half of the guard: on `/` no other sheet hides [hidden] once a page gives the element
                # its own display (B4's Sign in will be a styled control)
                page.evaluate("""() => document.body.insertAdjacentHTML('beforeend',
                    '<a class="probe-flagged" data-flag="web-signup" hidden style="display:inline-flex">Sign in</a>')""")
                assert not page.locator("a.probe-flagged").is_visible(), (path, js, width)
            finally:
                ctx.close()


def test_manage_link_shows_when_switch_on(site_url, browser):
    """The switch works: shell.js with web-billing on shows the link (and leaves web-signup off)."""
    src = (ROOT / "assets" / "site" / "shell.js").read_text(encoding="utf-8")
    off = '"web-billing": false'
    assert src.count(off) == 1
    on = src.replace(off, '"web-billing": true')

    def serve(route):
        route.fulfill(status=200, content_type="application/javascript", body=on)

    for path in ("/", FIXTURE):
        ctx, page = open_page(browser, site_url + path, route=("**/assets/site/shell.js", serve))
        try:
            to_bottom(page)
            assert page.locator(MANAGE).is_visible(), path
            assert page.locator(MANAGE).get_attribute("href") == "/account", path
            assert page.evaluate("() => [FEShell.flag('web-billing'), FEShell.flag('web-signup')]") == [True, False]
            if path == FIXTURE:
                assert not page.locator("a.fixture-flagged").is_visible()
        finally:
            ctx.close()


def test_no_web_account_calls(site_url, browser):
    """B2 never calls the web-account API: no request to /web/* or to api.freelance-easy.com."""
    for path in ("/", FIXTURE):
        seen = []
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        try:
            page = ctx.new_page()
            page.on("request", lambda r: seen.append(r.url))
            page.goto(site_url + path, wait_until="load")
            to_bottom(page)
            page.wait_for_timeout(400)
        finally:
            ctx.close()
        bad = [u for u in seen if urlparse(u).path.startswith("/web/") or urlparse(u).hostname == "api.freelance-easy.com"]
        assert seen and bad == [], bad


# ---- A11's footer link ---------------------------------------------------------------------------------------------

def test_footer_tour_link_kept(site_url, browser):
    for width in (1440, 390):
        ctx, page = open_page(browser, site_url + "/", width=width)
        try:
            link = page.locator('footer a[href="/tour/"]')
            assert link.count() == 1
            to_bottom(page)
            assert link.is_visible() and link.inner_text().strip() == "Watch the tour", width
        finally:
            ctx.close()


# ---- the footnotes block -------------------------------------------------------------------------------------------

PROBE = """(el) => {
  const lum = (c) => { const m = c.match(/[\\d.]+/g).map(Number);
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(m[0]) + 0.7152 * f(m[1]) + 0.0722 * f(m[2]); };
  const opaque = (c) => { const m = c.match(/[\\d.]+/g); return m && (m.length < 4 || Number(m[3]) === 1); };
  let bg = null;
  for (let n = el; n; n = n.parentElement) { const c = getComputedStyle(n).backgroundColor; if (opaque(c)) { bg = c; break; } }
  if (!bg) { const p = document.createElement('span'); p.style.color = 'var(--bg-0)'; el.appendChild(p);
    bg = getComputedStyle(p).color; p.remove(); }
  const t2 = document.createElement('span'); t2.style.color = 'var(--text-2)'; el.parentElement.appendChild(t2);
  const text2 = getComputedStyle(t2).color; t2.remove();
  const cs = getComputedStyle(el); const r = el.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + Math.min(20, r.width / 2), r.top + r.height / 2);
  const a = lum(cs.color), b = lum(bg);
  return { text: el.textContent.trim(), px: parseFloat(cs.fontSize), color: cs.color, text2, bg,
           ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05), opacity: cs.opacity,
           inView: r.top >= 0 && r.bottom <= innerHeight && r.width > 0, onTop: !!hit && el.contains(hit) };
}"""


@pytest.mark.parametrize("mode", ["motion", "calm", "nojs"])
@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("path", ["/", FIXTURE])
def test_footnote_fictional(site_url, browser, path, theme, mode):
    """R5 A.2's footer sentence: visible in every mode (motion, calm, no JS) at 1440, 800 and 390, >= 15 px, the
    text-2 colour, >= 4.5:1 on its background. Without JS no script reads the stored theme, so the no-JS light case
    checks the page's own (dark) default."""
    for width in (1440, 800, 390):
        ctx, page = open_page(browser, site_url + path, width=width, theme=theme, reduced=(mode == "calm"),
                              js=(mode != "nojs"))
        try:
            note = page.locator('footer [data-footnote="fictional"]')
            assert note.count() == 1
            to_bottom(page)
            assert note.is_visible()
            p = note.evaluate(PROBE)
            where = (path, theme, mode, width, p)
            assert p["text"] == FICTIONAL, where
            assert p["px"] >= 15 and p["color"] == p["text2"] and p["opacity"] == "1", where
            assert p["ratio"] >= 4.5 and p["inView"] and p["onTop"], where
            if mode != "nojs":
                assert page.evaluate("() => document.documentElement.getAttribute('data-theme')") == theme
        finally:
            ctx.close()
