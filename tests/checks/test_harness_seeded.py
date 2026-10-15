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

# Real F-rule failures the harness found at the base (66ce52b), beyond CF-11. Strict: the
# piece that fixes one must remove its line here.
BASE_FINDINGS = {
    ("/", "F7"): "base: CLS 0.0228 (>= 0.02) from div.fx-shape layout shifts at ~0.8-1.6 s",
    ("/terms", "F7"): "base: CLS 0.0227 (>= 0.02), one 45 ms shift of ul/p/h2 (font swap)",
    ("/404", "F8"): ("base: 404.html's head script sets data-theme only for light, so dark has "
                     "no attribute (same shape as CF-11 but not covered by it)"),
}


def _base_cases():
    for name in PAGES:
        for check in ("F5", "F7", "F8", "F10", "F11", "LINKS"):
            marks = []
            if check == "F8" and name in DOC_PAGES:
                marks.append(pytest.mark.xfail(strict=True, reason=(
                    "CF-11: script.js:34 removes data-theme for dark on the doc pages; "
                    "B7's ADOPT gate drops ./script.js there and flips this to pass")))
            reason = BASE_FINDINGS.get((name, check))
            if reason:
                marks.append(pytest.mark.xfail(strict=True, reason=reason))
            yield pytest.param(name, check, marks=marks, id=f"{name}-{check}")


@pytest.mark.parametrize("name,check", list(_base_cases()))
def test_passes_on_base(site_url, name, check):
    r = fidelity(site_url + PAGES[name], check)
    assert r.returncode == 0, r.stdout + r.stderr


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
