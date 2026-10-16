"""PR-1: the interim /pricing page (src/pages/pricing.html).

How to buy, how to pay, the catches and the terms, on the shared shell. Money terms + legal copy (R3): every sentence
the page marks `<!-- NEW COPY -->` is logged with its source and ruling in docs/claims/pricing.md; banned phrases
(R5 C.1, G3, G6, G7, G8, G10) never appear; the JSON-LD prices equal the visible plan prices; the web path stays hidden
behind data-flag="web-signup" (children/E-web-account-contract.md § 6) while web accounts are paused.

Run: uv run --with pytest --with playwright python3 -m pytest tests/pages/test_pricing.py -q
The static test server (conftest `site_url`) has no clean URLs, so /pricing is /pricing.html.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "pages" / "pricing.html"
LEDGER = ROOT / "docs" / "claims" / "pricing.md"
PAGE = "/pricing.html"
HEIGHTS = {1440: 900, 390: 844}


def src() -> str:
    return SRC.read_text(encoding="utf-8")


def built() -> str:
    return (ROOT / "pricing.html").read_text(encoding="utf-8")


def clean(fragment: str) -> str:
    """Visible text of an HTML fragment: comments and tags dropped, entities decoded, whitespace collapsed."""
    fragment = re.sub(r"<!--.*?-->", "", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z$§\"'(])", text) if s]


def marked_blocks(source: str) -> list[str]:
    """The text of each element a `<!-- NEW COPY -->` marker stands in front of (a <meta> gives its content)."""
    out = []
    for m in re.finditer(r"<!-- NEW COPY -->\s*<(\w+)([^>]*)>", source):
        tag, attrs = m.group(1), m.group(2)
        if tag == "meta":
            out.append(clean(re.search(r'content="([^"]*)"', attrs).group(1)))
            continue
        end = re.compile(rf"</{tag}>").search(source, m.end())
        assert end, f"unclosed <{tag}> after a NEW COPY marker"
        out.append(clean(source[m.end():end.start()]))
    return out


class _MainText(HTMLParser):
    """Text blocks inside <main>, one per block element, skipping <script>/<style>."""

    BLOCKS = {"h1", "h2", "h3", "p", "li", "a", "span", "div", "section", "ol", "ul"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.skip = 0
        self.buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.depth += 1
        elif tag in ("script", "style"):
            self.skip += 1
        elif self.depth:
            self.buf.append(" ")

    def handle_endtag(self, tag):
        if tag == "main":
            self.depth -= 1
        elif tag in ("script", "style"):
            self.skip -= 1
        elif self.depth and tag in self.BLOCKS - {"a", "span"}:
            self.buf.append("\n")

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.buf.append(data)


def main_sentences(source: str) -> list[str]:
    p = _MainText()
    p.feed(re.sub(r"<!--.*?-->", "", source, flags=re.S))
    out = []
    for block in "".join(p.buf).split("\n"):
        out += sentences(re.sub(r"\s+", " ", block).strip())
    return [s for s in out if s]


def ledger_rows() -> dict[str, tuple[str, str]]:
    rows = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) == 4 and re.fullmatch(r"\d+[a-z]?", cells[0]):
            rows[cells[1]] = (cells[2], cells[3])
    return rows


def jsonld(page_html: str) -> dict:
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page_html, re.S)
    assert len(blocks) == 1, len(blocks)
    return json.loads(blocks[0])


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def open_page(browser, url, *, width=1440, js=True, route=None):
    ctx = browser.new_context(viewport={"width": width, "height": HEIGHTS.get(width, 900)}, java_script_enabled=js)
    if route:
        ctx.route(*route)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    resp = page.goto(url, wait_until="load")
    assert resp is not None and resp.status == 200, url
    page.wait_for_timeout(300)
    assert errors == [], errors
    return ctx, page


# ---- the sentence ledger -------------------------------------------------------------------------------------------

def test_every_sentence_logged(site_url):
    """Every NEW COPY sentence is a ledger row with a source and a ruling, and no sentence in <main> is unmarked."""
    source = src()
    marked = [s for block in marked_blocks(source) for s in sentences(block)]
    assert len(marked) >= 40, len(marked)
    rows = ledger_rows()
    missing = [s for s in marked if s not in rows]
    assert missing == [], f"NEW COPY sentences with no ledger row: {missing}"
    for s in marked:
        where, ruling = rows[s]
        assert where and ruling, s
    # nothing in <main> escapes the ledger: each sentence is marked, except this explicit list of shipped labels
    unmarked = [s for s in main_sentences(source) if s not in marked and s not in UNMARKED_OK]
    assert unmarked == [], f"sentences in <main> with no NEW COPY marker: {unmarked}"


# Shipped labels that may sit in <main> unmarked: the doc pages' back link (install.html) and A9's download labels
# (index.html; download.js rewrites them). Anything else in <main> carries NEW COPY and a ledger row.
UNMARKED_OK = frozenset({"← Back to Freelance Easy", "Download for Mac", "Download for Windows"})


# ---- banned phrases ------------------------------------------------------------------------------------------------

BANNED = ["one-click", "you're done", "effortless", "$5 total", "no extra fees", "nothing else to pay",
          "tax included", "all-in", "free forever", "no tiers", "no paywalls", "get paid faster", "cup of coffee",
          "$25", "on one computer", "never leaves your computer", "encrypted", "secure", "private", "can't see"]
COMPETITORS = ["freshbooks", "quickbooks", "wave", "xero", "zoho", "bonsai", "honeybook", "invoice ninja",
               "invoicely", "harvest", "square invoices", "paypal invoicing"]


def page_copy(page_html: str) -> str:
    """Everything a visitor or a crawler reads from this page's own copy: title, description, <main>, JSON-LD."""
    title = re.search(r"<title>(.*?)</title>", page_html, re.S).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)"', page_html).group(1)
    main = re.search(r"<main\b.*?</main>", page_html, re.S).group(0)
    return " ".join([clean(title), html.unescape(desc), clean(main), json.dumps(jsonld(page_html))]).lower()


def test_banned_phrases(site_url):
    text = page_copy(built())
    text = text.replace("’", "'")
    found = [p for p in BANNED if re.search(r"(?<![\w$])" + re.escape(p) + r"(?!\w)", text)]
    found += [c for c in COMPETITORS if re.search(r"\b" + re.escape(c) + r"\b", text)]
    assert found == [], found


# ---- JSON-LD -------------------------------------------------------------------------------------------------------

UNIT = {"MON": "month", "ANN": "year"}


def test_jsonld_matches_visible_prices(site_url, browser):
    """Product + Offers: each offer's price (and its unit spec) equals a visible plan card, one offer per card, USD,
    and no seller or claim the page doesn't make."""
    data = jsonld(built())
    assert data["@context"] == "https://schema.org" and data["@type"] == "Product"
    assert set(data) <= {"@context", "@type", "name", "url", "brand", "offers"}, set(data)
    offers = data["offers"]
    ld = set()
    for o in offers:
        assert o["@type"] == "Offer" and o["priceCurrency"] == "USD" and "seller" not in o
        spec = o["priceSpecification"]
        assert spec["price"] == o["price"] and spec["priceCurrency"] == "USD"
        ld.add((float(o["price"]), UNIT[spec["referenceQuantity"]["unitCode"]]))
    assert len(ld) == len(offers)

    ctx, page = open_page(browser, site_url + PAGE)
    try:
        cards = page.locator("main [data-price]")
        visible = set()
        for i in range(cards.count()):
            c = cards.nth(i)
            assert c.is_visible()
            amount = float(c.get_attribute("data-price"))
            assert c.inner_text().strip() == "$" + c.get_attribute("data-price")
            heading = c.evaluate("e => e.closest('h2').textContent.replace(/\\s+/g, ' ').trim()")
            assert heading == f"${c.get_attribute('data-price')} a {c.get_attribute('data-period')}", heading
            visible.add((amount, c.get_attribute("data-period")))
        main_text = page.locator("main").inner_text()
    finally:
        ctx.close()
    assert visible == ld, (visible, ld)

    # every other price the page states agrees: the meta description names exactly the offers' prices, and any amount
    # in the visible text is an offer price or the yearly plan's per-month figure (2026-10b: $50 / 12 = $4.17)
    def amounts(text):
        return {float(a) for a in re.findall(r"\$(\d+(?:\.\d+)?)", text)}

    prices = {p for p, _ in ld}
    desc = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', built()).group(1))
    assert amounts(desc) == prices, (desc, prices)
    per_month = {round(p / 12, 2) for p, unit in ld if unit == "year"}
    assert amounts(main_text) <= prices | per_month, (amounts(main_text), prices, per_month)


# ---- the web path --------------------------------------------------------------------------------------------------

WEB = 'main [data-flag="web-signup"]'


def test_web_path_hidden_without_flag(site_url, browser):
    """The web path is in <main>, flagged web-signup, and hidden with JS (the switch is off) and without JS; while off
    it is no link at all. Nothing on the page calls the web-account API."""
    for js in (True, False):
        for width in (1440, 390):
            seen = []
            ctx = browser.new_context(viewport={"width": width, "height": HEIGHTS[width]}, java_script_enabled=js)
            try:
                page = ctx.new_page()
                page.on("request", lambda r: seen.append(r.url))
                page.goto(site_url + PAGE, wait_until="load")
                page.wait_for_timeout(300)
                web = page.locator(WEB)
                assert web.count() == 1, (js, width)
                assert not web.is_visible(), (js, width)
                assert page.locator('a[href^="/start"], a[href^="/account"], a[href*="/web/"]').count() == 0, (js, width)
                assert web.locator("form, button, input").count() == 0
            finally:
                ctx.close()
            bad = [u for u in seen
                   if urlparse(u).path.startswith("/web/") or urlparse(u).hostname == "api.freelance-easy.com"]
            assert seen and bad == [], bad

    # the switch works: shell.js with web-signup on shows it as a link to /start
    shell = (ROOT / "assets" / "site" / "shell.js").read_text(encoding="utf-8")
    off = '"web-signup": false'
    assert shell.count(off) == 1
    on = shell.replace(off, '"web-signup": true')
    ctx, page = open_page(browser, site_url + PAGE, route=(
        "**/assets/site/shell.js", lambda r: r.fulfill(status=200, content_type="application/javascript", body=on)))
    try:
        assert page.locator(WEB).is_visible()
        assert page.locator(WEB + " a").get_attribute("href") == "/start"
    finally:
        ctx.close()


# ---- the page's own CSS, the sitemap, the shell ----------------------------------------------------------------

def test_inline_style_tokens(tmp_path):
    """The page's <style> block passes F1 (tokens only, no raw colours or durations)."""
    css = re.search(r"<style>(.*?)</style>", src(), re.S).group(1)
    f = tmp_path / "pricing-inline.css"
    f.write_text(css, encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "checks" / "token_lint.py"), str(f)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_single_column_layout(site_url, browser):
    """The doc column reads top to bottom at every width: no legacy rule (styles.css's homepage `.pricing` grid) turns
    <main> into columns. Every direct block starts at the column's left edge."""
    for width in (1440, 390):
        ctx, page = open_page(browser, site_url + PAGE, width=width)
        try:
            assert page.evaluate("() => getComputedStyle(document.querySelector('main')).display") == "block"
            blocks = "main > h1, main > p:not([hidden]), main > h2, main > .plan-grid"
            lefts = page.evaluate("(s) => [...document.querySelectorAll(s)]"
                                  ".map(e => Math.round(e.getBoundingClientRect().left))", blocks)
            assert len(set(lefts)) == 1, (width, lefts)
        finally:
            ctx.close()


IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/17.0 Mobile/15E148 Safari/604.1")


def test_phone_gets_no_installer_link(site_url, browser):
    """On a phone the download row offers only the hand-off to a computer (A9/piece M): no installer link (Sol PR-1)."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                              user_agent=IPHONE_UA)
    try:
        page = ctx.new_page()
        page.goto(site_url + PAGE, wait_until="load")
        page.wait_for_timeout(300)
        assert page.evaluate("() => document.documentElement.getAttribute('data-os')") == "mobile"
        row = page.locator('main [data-dl][data-placement="pricing-page"]')
        assert row.locator('[data-role="primary"]').is_visible()
        assert row.locator('[data-role="primary"] [data-label]').inner_text().strip() == "Send to my Mac"
        assert not row.locator('[data-role="alt"]').is_visible()
    finally:
        ctx.close()


def test_in_sitemap_and_on_the_shell(site_url):
    assert "<loc>https://freelance-easy.com/pricing</loc>" in (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    page_html = built()
    assert '<body data-page="pricing">' in page_html
    assert '<link rel="canonical" href="https://freelance-easy.com/pricing" />' in page_html
    head = (ROOT / "src" / "partials" / "head.html").read_text(encoding="utf-8")
    assert head in page_html
    assert page_html.count('<footer class="site-footer fe-shell-footer">') == 1
    assert 'data-dl data-placement="pricing-page"' in page_html
