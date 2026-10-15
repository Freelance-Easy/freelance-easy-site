"""A11: the tour pages' copy and meta (PLAN § A11, CF-13, R5 B.1).

- No standing "Example account ..." disclaimer anywhere in tour/ or src/; no "watch-only" in the two tour pages.
- The Email chapter's caption itself says email has to be set up first (R5 B.1: the qualifier moves to where the
  claim is made), in both caption-copy templates, marked NEW COPY, and it is what a visitor actually sees on screen
  when either tour reaches its Email chapter.
- /tour/ is the one tour: canonical + og meta on it; /tour/quick/ points its canonical at /tour/.
- The footer partial links to /tour/ exactly once.
"""
from __future__ import annotations

import pathlib
import re

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TOUR = ROOT / "tour" / "index.html"
QUICK = ROOT / "tour" / "quick" / "index.html"
FOOTER = ROOT / "src" / "partials" / "footer.html"

SIGNED = "once email is set up"   # the qualifier R5 B.1 requires on the Email chapter (wording signed by fe:claims)
EMAIL_INDEX = 5                    # the Email chapter in the caption list (the full tour's chapter 6 of 7)
CANONICAL = "https://freelance-easy.com/tour/"


def _text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _template(html: str) -> str:
    m = re.search(r'<template id="caption-copy">(.*?)</template>', html, re.S)
    assert m, "no <template id=\"caption-copy\">"
    return m.group(1)


def _meta(html: str, prop: str) -> str | None:
    m = re.search(r'<meta\s+property="%s"\s+content="([^"]*)"' % re.escape(prop), html)
    return m.group(1) if m else None


def _canonical(html: str) -> list[str]:
    return re.findall(r'<link\s+rel="canonical"\s+href="([^"]*)"', html)


def test_no_example_account():
    hits = []
    for base in (ROOT / "tour", ROOT / "src"):
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in {".html", ".js", ".css", ".json", ".txt", ".md"}:
                for n, line in enumerate(_text(p).splitlines(), 1):
                    if "example account" in line.lower():
                        hits.append(f"{p.relative_to(ROOT)}:{n}")
    assert not hits, f"'Example account' disclaimer still present: {hits}"


@pytest.mark.parametrize("page", [TOUR, QUICK], ids=["tour", "quick"])
def test_no_watch_only_in_markup(page):
    assert "watch-only" not in _text(page).lower()


@pytest.mark.parametrize("page", [TOUR, QUICK], ids=["tour", "quick"])
def test_email_caption_in_template(page):
    lines = [ln.strip() for ln in _template(_text(page)).splitlines() if "<p>" in ln]
    assert len(lines) == 7, lines
    email = lines[EMAIL_INDEX]
    assert email.startswith("<!-- NEW COPY --><p>"), email
    assert SIGNED in email, email


def test_templates_identical():
    # quick.js reads captions 3-7 of the full tour's list, verbatim: the two lists must not drift
    assert _template(_text(TOUR)) == _template(_text(QUICK))


def test_tour_canonical_and_og():
    html = _text(TOUR)
    assert _canonical(html) == [CANONICAL]
    assert _meta(html, "og:url") == CANONICAL
    for prop in ("og:title", "og:description"):
        assert (_meta(html, prop) or "").strip(), prop
    image = _meta(html, "og:image") or ""
    assert image.startswith("https://freelance-easy.com/"), image
    assert (ROOT / image.removeprefix("https://freelance-easy.com/")).is_file(), image


def test_quick_canonical_points_to_tour():
    assert _canonical(_text(QUICK)) == [CANONICAL]


def test_footer_links_tour_once():
    assert _text(FOOTER).count('href="/tour/"') == 1


# Seek each tour to its Email chapter, then read the caption the visitor sees (visible, rendered text).
SEEK = {
    "/tour/": (
        "() => window.__tour && window.__tour.ready",
        "() => { window.__tour.pause(); document.querySelector('[data-chapter=\"5\"]').click(); }",
        "() => window.__tour.state().chapter === 5",
    ),
    "/tour/quick/": (
        "() => window.__tourQuick && window.__tourQuick.ready",
        None,   # no seek API: it autoplays once; wait for the Email chapter (about 14 s in)
        "() => window.__tourQuick.timeline().chapters[window.__tourQuick.state().chapter].title === 'Email'",
    ),
}


@pytest.mark.parametrize("path", list(SEEK), ids=["tour", "quick"])
def test_email_caption_rendered(site_url, path):
    ready, seek, at_email = SEEK[path]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(site_url + path)
            page.wait_for_function(ready, timeout=15000)
            if seek:
                page.evaluate(seek)
            page.wait_for_function(at_email, timeout=40000)
            page.evaluate("() => (window.__tour || window.__tourQuick).pause()")
            caption = page.locator("#caption")
            caption.scroll_into_view_if_needed()
            assert caption.is_visible()
            box = caption.bounding_box()
            assert box and box["width"] > 0 and box["height"] > 0
            style = caption.evaluate(
                "el => { const s = getComputedStyle(el); return [s.visibility, s.opacity, s.color]; }")
            assert style[0] == "visible" and float(style[1]) > 0.5, style
            assert SIGNED in caption.inner_text(), caption.inner_text()
        finally:
            browser.close()
