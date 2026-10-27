"""B7: routes + the doc pages (install, privacy, terms, 404) on the shared shell.

Run: uv run --with pytest --with playwright python3 -m pytest tests/routes -q
The legal text must not change: the <main>...</main> bytes of privacy, terms and install are held to the cut
commit's (652d12a, branch (a), no A3; privacy v3 to its own commit, CUTS). The wrangler test is opt-in (FE_WRANGLER=1): it starts `wrangler dev` on
127.0.0.1 and never reaches freelance-easy.com or GitHub.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CUT = "652d12a"
# privacy v3 (2026-10-27) is held to its own commit; v2's <main> lives on in privacy-2026-10-11.html
CUTS = {"privacy": "5a62eb4"}
V2_ARCHIVE = "privacy-2026-10-11.html"
DOC =["install", "privacy", "terms", "404"]
LEGAL = ["install", "privacy", "terms"]
MAIN = re.compile(rb"<main\b.*?</main>", re.S)
# the app's version label ("Current version v0.3.2-beta" on install) is a routine release bump, not legal text: it is
# masked before the bytes are compared, so a release can bump it while every other byte stays held to CUT
VERSION = re.compile(rb"v\d+\.\d+\.\d+(?:-beta)?")
HEAD_SPAN = re.compile(r"[ \t]*<!-- fe-shell:head .*?<!-- /fe-shell:head -->\n", re.S)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("built")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build-site.py"), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def test_pricing_rule_and_sitemap():
    rules = [ln.split() for ln in (ROOT / "_redirects").read_text().splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    assert ["/pricing/", "/pricing", "301"] in rules
    # the existing rules are unchanged
    for rule in (["/privacy/", "/privacy", "301"], ["/terms/", "/terms", "301"], ["/mac/", "/mac", "301"],
                 ["/mac-audio/", "/mac-audio", "301"], ["/audio/", "/audio", "301"]):
        assert rule in rules
    assert any(r[0] == "/releases" and r[2] == "302" for r in rules)
    assert any(r[0] == "/download" and r[2] == "302" for r in rules)
    sitemap = (ROOT / "sitemap.xml").read_text()
    assert "<loc>https://freelance-easy.com/pricing</loc>" in sitemap


@pytest.mark.parametrize("name", LEGAL)
def test_legal_main_unchanged(built, name):
    cut = CUTS.get(name, CUT)
    now = MAIN.search((built / f"{name}.html").read_bytes())
    was = MAIN.search(subprocess.run(["git", "-C", str(ROOT), "show", f"{cut}:{name}.html"],
                                     capture_output=True, check=True).stdout)
    assert now and was
    assert VERSION.sub(b"vX", now.group(0)) == VERSION.sub(b"vX", was.group(0)), f"{name}: <main> bytes differ from {cut}"


def test_privacy_v2_archive_is_v2():
    """The dated v2 archive keeps the exact <main> users saw from 2026-10-11 (held to CUT)."""
    now = MAIN.search((ROOT / V2_ARCHIVE).read_bytes())
    was = MAIN.search(subprocess.run(["git", "-C", str(ROOT), "show", f"{CUT}:privacy.html"],
                                     capture_output=True, check=True).stdout)
    assert now and was
    assert VERSION.sub(b"vX", now.group(0)) == VERSION.sub(b"vX", was.group(0))


@pytest.mark.parametrize("name", DOC)
def test_doc_pages_on_shell(built, name):
    html = (built / f"{name}.html").read_text(encoding="utf-8")
    head = (ROOT / "src/partials/head.html").read_text()
    header = (ROOT / "src/partials/header.html").read_text().replace("{{dl_fallback}}", "/install")
    footer = (ROOT / "src/partials/footer.html").read_text().replace("{{dl_fallback}}", "/install")
    assert head in html and header in html and footer in html
    # a theme head identical to the homepage's
    home = (built / "index.html").read_text(encoding="utf-8")
    assert HEAD_SPAN.findall(html) == HEAD_SPAN.findall(home) and len(HEAD_SPAN.findall(html)) == 1
    # F8 explicit: data-theme on <html> in the markup
    assert re.search(r"<html\b[^>]*\bdata-theme=\"dark\"", html)
    # no ./script.js (CF-11); the content keeps styles.css
    assert not re.search(r"<script[^>]+src=\"(\./|/)?script\.js\"", html)
    assert re.search(r"<link[^>]+href=\"(\./|/)styles\.css\"", html)
    # the theme toggle works: FETheme, no hash policy
    assert 'FETheme.init({ hashPolicy: "none" })' in html
    # the bar's Download really downloads here too
    assert re.search(r"<script[^>]+src=\"/assets/story/download\.js\"", html)
    # the classic switch slot stays empty on doc pages (ICX-CLASSIC.4)
    assert re.search(r"<span class=\"fe-shell-slot\" data-classic-slot></span>", html)
    assert html.index("<header") < html.index("<main") < html.index("<footer")
    # the dated archives are untouched (outside src/)
    for arch in ("privacy-2026-09-29.html", "terms-2026-09-29.html"):
        assert "shell.css" not in (ROOT / arch).read_text(encoding="utf-8")


def test_font_preloaded(built):
    for name in DOC:
        assert 'rel="preload" href="/assets/story/fonts/Inter-Variable-latin.woff2"' in (built / f"{name}.html").read_text()


def test_dl_head_order(built):
    """dl-status.css comes with the header partial; the page's own sheet comes before the shell's overrides."""
    html = (built / "privacy.html").read_text(encoding="utf-8")
    assert html.count("/assets/story/dl-status.css") == 1


@pytest.mark.skipif(os.environ.get("FE_WRANGLER") != "1", reason="opt-in: FE_WRANGLER=1 starts wrangler dev")
def test_wrangler_routes():
    port = 8787
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
        s, h = head("/pricing/")
        assert s == 301 and h["location"].rstrip("/").endswith("/pricing") and not h["location"].endswith("/")
        for path in ("/privacy/", "/terms/"):
            assert head(path)[0] == 301
        assert head("/releases")[0] == 302
        assert head("/download")[0] == 302
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except Exception:
            proc.kill()


# ---- the fallback Download link (main's ruling: no fake #download target on the doc pages) ----------------------

PHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.0 Mobile/15E148 Safari/604.1")
FALLBACK_PAGES = [("/", "#download"), ("/install.html", "/install"), ("/privacy.html", "/install"),
                  ("/terms.html", "/install"), ("/404.html", "/install")]


@pytest.mark.parametrize("path,want", FALLBACK_PAGES)
@pytest.mark.parametrize("mode", ["nojs", "phone"])
def test_download_fallback_href(site_url, path, want, mode):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        kw = ({"java_script_enabled": False} if mode == "nojs"
              else {"user_agent": PHONE_UA, "is_mobile": True, "has_touch": True,
                    "viewport": {"width": 390, "height": 664}})
        ctx = b.new_context(**kw)
        page = ctx.new_page()
        page.goto(site_url + path, wait_until="load")
        page.wait_for_timeout(500)
        header = page.eval_on_selector(".site-header .nav-cta", "a => a.getAttribute('href')")
        footer = page.eval_on_selector(".site-footer .foot-links a:text-is('Download')", "a => a.getAttribute('href')")
        b.close()
    assert header == want and footer == want, (header, footer)
