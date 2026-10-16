"""A14 fidelity harness: each check fails on its seeded page and passes on the base pages.

Run: uv run --with pytest --with playwright python3 -m pytest tests/checks -q
The static test server (conftest `site_url`) has no clean URLs, so /install is /install.html.
"""
from __future__ import annotations

import filecmp
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKS = ROOT / "scripts" / "checks"
SEEDS = "/tests/fixtures/seeded"
PAGES = {"/": "/", "/install": "/install.html", "/privacy": "/privacy.html",
         "/terms": "/terms.html", "/404": "/404.html"}
DOC_PAGES = {"/install", "/privacy", "/terms"}


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECKS / script), *args],
                          capture_output=True, text=True, timeout=240)


def fidelity(url: str, check: str) -> subprocess.CompletedProcess:
    return run("fidelity.py", "--url", url, "--check", check)


# ------------------------------------------------ failing first: seeds ----

def test_F1_fails_on_seed():
    r = run("token_lint.py", str(ROOT / "tests/fixtures/seeded/f1.css"))
    assert r.returncode == 1, r.stdout + r.stderr
    for rule in ("raw-hex", "raw-colour-fn", "raw-duration"):
        assert rule in r.stdout


def test_F1_passes_on_tokens_and_fe_exempt():
    sys.path.insert(0, str(CHECKS))
    import token_lint
    assert token_lint.lint_text(".a { color: var(--app-fg); transition: opacity var(--app-dur); }") == []
    assert token_lint.lint_text(".a { color: #fff; }", "/x/assets/fe/app.css") == []
    assert token_lint.lint_text(".a { background: url(#frag); animation-duration: 0s; }") == []
    assert token_lint.lint_text("/* token-lint: allow */ .a { color: #fff; }") == []
    bad = token_lint.lint_text(":root {\n  --a: var(--app-x);\n  --b: 12px;\n"
                               "  /* SITE-ONLY */\n  --c: 3px;\n}", "site-tokens.css")
    assert [v["line"] for v in bad] == [3]


def test_F3_fails_on_seed(site_url):
    r = fidelity(f"{site_url}{SEEDS}/f3.html", "F3")
    assert r.returncode == 1 and "color-contrast" in r.stdout, r.stdout + r.stderr


def test_F5_fails_on_seed(site_url):
    r = fidelity(f"{site_url}{SEEDS}/f5.html", "F5")
    assert r.returncode == 1 and "third-party font" in r.stdout, r.stdout + r.stderr


def test_F7_fails_on_seed(site_url):
    r = fidelity(f"{site_url}{SEEDS}/f7.html", "F7")
    assert r.returncode == 1 and "CLS" in r.stdout and "rects moved" in r.stdout, r.stdout


def test_F8_fails_on_seed(site_url):
    r = fidelity(f"{site_url}{SEEDS}/f8.html", "F8")
    assert r.returncode == 1 and "data-theme='light'" in r.stdout, r.stdout


def test_F10_fails_on_seed(site_url):
    r = fidelity(f"{site_url}{SEEDS}/f10.html", "F10")
    assert r.returncode == 1 and "pulse" in r.stdout, r.stdout


def test_F11_fails_on_seed(site_url):
    r = fidelity(f"{site_url}{SEEDS}/f11.html", "F11")
    assert r.returncode == 1 and "scrollWidth" in r.stdout and "target" in r.stdout, r.stdout


def test_links_fails_on_seed_and_lists_external(site_url):
    r = fidelity(f"{site_url}{SEEDS}/links.html", "LINKS")
    assert r.returncode == 1
    assert "broken link" in r.stdout and "missing anchor #no-such-anchor" in r.stdout
    assert "external: https://example.com/never-fetched" in r.stdout


def test_axe_fails_on_seed(site_url):
    r = run("run_axe.py", f"{site_url}{SEEDS}/axe.html", "--theme", "dark")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "critical" in r.stdout and "button-name" in r.stdout


def test_axe_usage_and_non_local_refused():
    assert run("run_axe.py", "https://example.com", "--theme", "dark").returncode == 2
    assert run("fidelity.py", "--url", "https://example.com", "--check", "F8").returncode == 2


# ------------------------------------------------------- base pages -------

# Known F-rule failures at the base (66ce52b). (page, check) -> (reason, fragment that the
# FAIL line must contain). Strict and specific: a pass is a failure (XPASS), and so is any
# other failure (a crash, timeout or harness error is a real FAIL, not a known xfail).
CF11 = ("CF-11: script.js:34 removes data-theme for dark on the doc pages; B7's ADOPT gate "
        "drops ./script.js there and flips this to pass")
KNOWN_BASE_FAILS = {
    ("/install", "F8"): (CF11, "F8 FAIL [os=dark] data-theme=None"),
    ("/privacy", "F8"): (CF11, "F8 FAIL [os=dark] data-theme=None"),
    ("/terms", "F8"): (CF11, "F8 FAIL [os=dark] data-theme=None"),
    ("/404", "F8"): ("base: 404.html's head script sets data-theme only for light, so dark has "
                     "no attribute (CF-11's shape, not covered by it)",
                     "F8 FAIL [os=dark] data-theme=None"),
    ("/", "F7"): ("base: CLS 0.0228 (>= 0.02) from div.fx-shape shifts at ~0.8-1.6 s",
                  "F7 FAIL CLS 0.02"),
    ("/terms", "F7"): ("base: CLS 0.0227 (>= 0.02), one 45 ms shift of ul/p/h2 (font swap)",
                       "F7 FAIL CLS 0.02"),
    ("/", "LINKS"): ("pending PR-1: /pricing page", "broken link /pricing"),
}


def _base_cases():
    for name in PAGES:
        for check in ("F5", "F7", "F8", "F10", "F11", "LINKS"):
            yield pytest.param(name, check, id=f"{name}-{check}")


@pytest.mark.parametrize("name,check", list(_base_cases()))
def test_passes_on_base(site_url, name, check):
    r = fidelity(site_url + PAGES[name], check)
    known = KNOWN_BASE_FAILS.get((name, check))
    if known is None:
        assert r.returncode == 0, r.stdout + r.stderr
        return
    reason, fragment = known
    if r.returncode == 0:
        pytest.fail(f"XPASS(strict): {name} {check} now passes; remove it from KNOWN_BASE_FAILS "
                    f"({reason})")
    assert r.returncode == 1 and fragment in r.stdout and "harness error" not in r.stdout, (
        f"{name} {check} failed, but not as the known finding ({fragment!r}):\n"
        f"{r.stdout}{r.stderr}")
    pytest.xfail(reason)


# F1 on the base. Today's base CSS is not token-clean (M3 migrates it), so F1 on base pages is
# asserted to FAIL with a positive violation count; this cannot pass silently, and it flips the
# day a page really is clean (then move it out of this list).
@pytest.mark.parametrize("name", list(PAGES))
def test_F1_base_pages_report_known_violations(site_url, name):
    import json
    r = fidelity(site_url + PAGES[name], "F1")  # plain text first: must be a FAIL line
    assert r.returncode == 1 and "F1 FAIL" in r.stdout, r.stdout + r.stderr
    j = run("fidelity.py", "--url", site_url + PAGES[name], "--check", "F1", "--json")
    res = json.loads(j.stdout)["results"][0]
    assert res["count"] > 0 and not any("harness error" in d for d in res["details"])


def _lint_tree(root: pathlib.Path) -> list:
    sys.path.insert(0, str(CHECKS))
    import token_lint
    found = []
    for sub in ("assets/shared", "assets/site"):
        for f in sorted((root / sub).glob("**/*.css")) if (root / sub).is_dir() else []:
            found += token_lint.lint_text(f.read_text(), "/" + f.relative_to(root).as_posix())
    return found


def test_F1_assets_shared_and_site_clean_vacuous_while_dirs_missing():
    """assets/shared/** and assets/site/** must be token-clean. VACUOUS today: those dirs do not
    exist yet (M3 creates them); the test goes live the moment they do."""
    assert _lint_tree(ROOT) == []


def test_F1_shared_tree_lint_fails_on_seeded_raw_hex(tmp_path):
    d = tmp_path / "assets" / "shared"
    d.mkdir(parents=True)
    (d / "seed.css").write_text(".a { color: #ff00aa; }\n")
    (tmp_path / "assets" / "site").mkdir()
    (tmp_path / "assets" / "site" / "ok.css").write_text(".a { color: var(--app-fg); }\n")
    found = _lint_tree(tmp_path)
    assert [v["rule"] for v in found] == ["raw-hex"] and found[0]["file"].endswith("shared/seed.css")


def test_token_lint_reports_raw_fallback_inside_var():
    sys.path.insert(0, str(CHECKS))
    import token_lint
    v = token_lint.lint_text(".a { color: var(--app-fg, #fff); }")
    assert [x["rule"] for x in v] == ["raw-hex"]
    v = token_lint.lint_text(":root { --x: var(--app-fg, rgb(1,2,3)); }", "site-tokens.css")
    assert [x["rule"] for x in v] == ["raw-colour-fn"]
    assert token_lint.lint_text(":root { --x: var(--app-fg, var(--app-bg)); }", "site-tokens.css") == []


# ------------------------------------- stub server: redirects, 404s, empties, imports ------

STUB_PAGES = {
    "/page": "<!doctype html><html lang=en><title>p</title><body><main><h1>Stub</h1>"
             "<a href='/go'>go</a></main></body></html>",
    "/empty": "<!doctype html><html lang=en><title>e</title><body></body></html>",
    "/notfound": "<!doctype html><html lang=en><title>Not found</title><body><main><h1>Not found</h1>"
                 "<a href='/page'>home</a><button>ok</button></main></body></html>",
    "/css": "<!doctype html><html lang=en><title>c</title><link rel=stylesheet href='/a.css'>"
            "<body><main><h1 style='color:#ff00aa'>Styled</h1><a href='/page'>x</a></main></body></html>",
    "/routes": "<!doctype html><html lang=en><title>r</title><body><main><h1>Routes</h1>"
               "<a href='/dl/mac/site'>m</a><a href='/dl/win/site'>w</a>"
               "<a href='/download/win'>d</a><a href='/releases'>r</a>"
               "<a href='/page'>ordinary</a></main></body></html>",
    "/badroutes": "<!doctype html><html lang=en><title>b</title><body><main><h1>Bad routes</h1>"
                  "<a href='/download/linux'>l</a><a href='/dl/linux/site'>dl</a>"
                  "<a href='/releases/missing'>r</a><a href='/page'>ordinary</a></main></body></html>",
    "/a.css": "@import url('/b.css');\n.ok { color: var(--app-fg); }\n",
    "/b.css": ".imported { color: #123456; }\n",
}


@pytest.fixture(scope="module")
def stub_url():
    import http.server
    import threading
    hits: list[str] = []

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            hits.append(self.path)
            if self.path == "/go":
                self.send_response(302)
                self.send_header("Location", "http://example.invalid/never-fetched")
                self.end_headers()
                return
            if self.path == "/hop":  # a LOCAL redirect into a download route
                self.send_response(302)
                self.send_header("Location", "/dl/mac/site")
                self.end_headers()
                return
            body = STUB_PAGES.get(self.path)
            status = 200
            if self.path == "/notfound":
                status = 404
            if body is None:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(status)
            self.send_header("Content-Type", "text/css" if self.path.endswith(".css")
                             else "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", hits
    srv.shutdown()
    srv.server_close()


def test_links_refuse_redirect_to_external_host(stub_url):
    url, hits = stub_url
    r = fidelity(url + "/page", "LINKS")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "refusing redirect to non-local host: http://example.invalid/never-fetched" in r.stdout
    assert hits.count("/go") >= 1  # the local hop was made; the external target never was (no DNS, no fetch)


def test_links_never_request_download_routes(stub_url):
    url, hits = stub_url
    hits.clear()
    r = fidelity(url + "/routes", "LINKS")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "4 routed" in r.stdout, r.stdout
    bad = [h for h in hits if h.startswith(("/dl/", "/download")) or h == "/releases"]
    assert bad == [], f"download routes were requested: {bad}"


def test_links_undefined_download_routes_are_broken(stub_url):
    # a download-looking path with no _redirects/worker.js rule is a broken link, reported without a fetch
    url, hits = stub_url
    hits.clear()
    r = fidelity(url + "/badroutes", "LINKS")
    assert r.returncode == 1, r.stdout + r.stderr
    for p in ("/download/linux", "/dl/linux/site", "/releases/missing"):
        assert f"broken link {p}" in r.stdout, r.stdout
    bad = [h for h in hits if h.startswith(("/dl/", "/download", "/releases"))]
    assert bad == [], f"download routes were requested: {bad}"


def test_get_refuses_local_redirect_into_download_route(stub_url):
    url, hits = stub_url
    hits.clear()
    sys.path.insert(0, str(CHECKS))
    import fidelity as f
    with pytest.raises(f.Fail, match="refusing redirect to a download route"):
        f._get(url + "/hop")
    assert "/dl/mac/site" not in hits, hits


def test_get_refuses_download_routes():
    sys.path.insert(0, str(CHECKS))
    import fidelity as f
    for p in ("/dl/mac/site", "/download/win", "/download", "/releases"):
        with pytest.raises(f.Fail, match="refusing to fetch a download route"):
            f._get("http://127.0.0.1:1" + p)


@pytest.mark.parametrize("check", ["F1", "F3", "F5", "F7", "F8", "F10", "F11", "LINKS"])
def test_every_check_fails_on_non_2xx_document(stub_url, check):
    url, _ = stub_url
    r = fidelity(url + "/notfound", check)
    assert r.returncode == 1 and f"{check} FAIL main document status 404" in r.stdout, (
        r.stdout + r.stderr)


def test_axe_fails_on_non_2xx_document(stub_url):
    url, _ = stub_url
    r = run("run_axe.py", url + "/notfound", "--theme", "dark")
    assert r.returncode == 1 and "status 404" in r.stderr


@pytest.mark.parametrize("check", ["F1", "F3", "F5", "F7", "F8", "F10", "F11", "LINKS"])
def test_every_check_fails_on_empty_page(stub_url, check):
    url, _ = stub_url
    r = fidelity(url + "/empty", check)
    assert r.returncode == 1 and f"{check} FAIL nothing to check: empty document" in r.stdout, (
        r.stdout + r.stderr)


def test_F1_follows_imports_and_style_attributes(stub_url):
    url, _ = stub_url
    r = fidelity(url + "/css", "F1")
    assert r.returncode == 1
    assert "/b.css" in r.stdout, "the @import'ed stylesheet must be linted"
    assert "style attr" in r.stdout, "the style attribute must be linted"


def test_F7_layout_selectors_cover_story_nav():
    sys.path.insert(0, str(CHECKS))
    import fidelity as f
    assert ".story-nav" in f.LAYOUT_SELECTORS


def test_F8_runs_both_os_schemes_and_the_toggle(site_url):
    j = run("fidelity.py", "--url", site_url + "/", "--check", "F8", "--json")
    import json
    details = " ".join(json.loads(j.stdout)["results"][0]["details"])
    for tag in ("os=dark", "os=light", "toggled"):
        assert tag in details, details


@pytest.mark.parametrize("name", list(PAGES))
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_axe_passes_on_base(site_url, name, theme):
    r = run("run_axe.py", site_url + PAGES[name], "--theme", theme)
    assert r.returncode == 0, r.stdout + r.stderr


# ---------------------------------------------------------- capture --------

def test_capture_is_deterministic(site_url, tmp_path):
    outs = []
    for n in ("a", "b"):
        out = tmp_path / n
        r = run("capture.py", site_url + "/install.html", "--widths", "390,1280",
                "--themes", "dark,light", "--out", str(out))
        assert r.returncode == 0, r.stderr
        outs.append(out)
    names = sorted(p.name for p in outs[0].glob("*.png"))
    assert len(names) == 4
    for n in names:
        assert filecmp.cmp(outs[0] / n, outs[1] / n, shallow=False), f"{n} differs between runs"
