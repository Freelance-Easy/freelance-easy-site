"""B12: the homepage tour dialog is retired; the hero's tour link goes to the full tour (/tour/, DEC-2).

Run: uv run --with pytest --with playwright python3 -m pytest tests/routes/test_tour_dialog.py -q
The wrangler check is opt-in (FE_WRANGLER=1): it starts `wrangler dev` on 127.0.0.1:8829 and reaches nothing else.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_no_dialog_trigger():
    pat = re.compile(r"data-tour-quick|tour-modal")
    hits = [f"{f.relative_to(ROOT)}:{n}" for d in ("src", "assets") for f in (ROOT / d).rglob("*") if f.is_file()
            for n, ln in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1) if pat.search(ln)]
    assert hits == [], hits
    assert not (ROOT / "assets" / "story" / "tour-modal.js").exists()
    src = (ROOT / "src" / "pages" / "index.html").read_text(encoding="utf-8")
    assert "<dialog" not in src and "/tour/quick/" not in src


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def test_hero_links_full_tour(site_url, browser):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    try:
        page = ctx.new_page()
        page.goto(site_url + "/", wait_until="load")
        link = page.locator('[data-copy="make"] [data-tour-link]')
        assert link.count() == 1
        assert link.get_attribute("href") == "/tour/"
        assert " ".join(link.inner_text().split()) == "Watch the tour"
        assert page.locator("dialog").count() == 0
    finally:
        ctx.close()


def _place(page):
    return page.evaluate("""() => {
      const q = (s) => document.querySelector(s);
      const inEnd = (el) => !!el && !!el.closest('[data-copy="end"]');
      const hc = q('[data-copy="make"]');
      return {
        sub: inEnd(hc && hc.querySelector(':scope > .sub')) || inEnd(q('[data-copy="end"] .sub')),
        tour: inEnd(q('[data-tour-link]')),
        heroRow: !!(hc && hc.querySelector(':scope > .cta-row')),
        heroDisclose: !!(hc && hc.querySelector(':scope > .disclose.strong')),
        heroFine: !!(hc && hc.querySelector(':scope > .fine')),
        heroSub: !!(hc && hc.querySelector(':scope > .sub')),
        heroTour: !!(hc && hc.querySelector('[data-tour-link]')),
      };
    }""")


@pytest.mark.parametrize("size", ["390x844"])
def test_cta_end_still_moves(site_url, browser, size):
    w, h = (int(n) for n in size.split("x"))
    ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce", has_touch=True, is_mobile=True)
    try:
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route("**/dl/**", lambda r: r.abort())
        page.goto(site_url + "/", wait_until="load")
        page.wait_for_function("document.body.hasAttribute('data-campaign-resolved')", timeout=10000)
        page.wait_for_timeout(1200)
        on = _place(page)
        # on a phone the hero is the headline alone: sub line, tour link are in the end caption; row, disclosure, fine gone
        assert on["tour"] and on["sub"], on
        assert not (on["heroRow"] or on["heroDisclose"] or on["heroFine"] or on["heroSub"] or on["heroTour"]), on
        # and back where they were when the page stops being a phone
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(1500)
        off = _place(page)
        assert off["heroRow"] and off["heroDisclose"] and off["heroFine"] and off["heroSub"] and off["heroTour"], off
        assert not off["tour"], off
        assert errors == [], errors
    finally:
        ctx.close()


def _rules():
    return [ln.split() for ln in (ROOT / "_redirects").read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def test_quick_301_rules():
    rules = _rules()
    assert ["/tour/quick", "/tour/", "301"] in rules
    assert ["/tour/quick/*", "/tour/", "301"] in rules


@pytest.mark.skipif(os.environ.get("FE_WRANGLER") != "1", reason="opt-in: FE_WRANGLER=1 starts wrangler dev")
def test_quick_301_under_wrangler():
    port = 8829
    proc = subprocess.Popen(
        ["npx", "--yes", "wrangler@4.86.0", "dev", "--port", str(port), "--ip", "127.0.0.1",
         "--compatibility-date", "2026-05-03", "-c", str(ROOT / "wrangler.toml")],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(NoRedirect)

    def head(path):
        try:
            r = opener.open(urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="HEAD"), timeout=5)
            return r.status, r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.headers

    try:
        for _ in range(90):
            try:
                head("/")
                break
            except Exception:
                time.sleep(1)
        else:
            pytest.fail("wrangler dev did not come up")
        for path in ("/tour/quick/", "/tour/quick", "/tour/quick/quick.js"):
            s, h = head(path)
            assert s == 301, (path, s)
            assert re.sub(r"^https?://[^/]+", "", h["location"]) == "/tour/", (path, h["location"])
        assert head("/tour/")[0] == 200
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except Exception:
            proc.kill()
