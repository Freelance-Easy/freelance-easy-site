"""scripts/build-site.py: the generator that writes the eight root pages from src/ (B1).

The cutover fixtures are frozen and never edited:
  tests/fixtures/cutover/src/                 src/ as it was at the cutover
  tests/fixtures/cutover/expected/*.html      the eight root pages at the cut sha (652d12a)
  tests/fixtures/cutover/derive-audio-page.py the retired audio.html script, as it was at 652d12a
so later, authorised changes to src/ or the root pages never fail these tests.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "scripts" / "build-site.py"
CUTOVER = ROOT / "tests" / "fixtures" / "cutover"
OUTPUTS = sorted(
    f"{n}.html" for n in ("index", "install", "privacy", "terms", "404", "mac", "mac-audio", "audio")
)


def run_build(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(BUILD), *map(str, args)], capture_output=True, text=True)


def fixture_src(tmp_path: pathlib.Path) -> pathlib.Path:
    src = tmp_path / "src"
    shutil.copytree(CUTOVER / "src", src)
    return src


def test_cutover_fixture_byte_identical(tmp_path):
    out = tmp_path / "out"
    r = run_build("--src", CUTOVER / "src", "--out", out)
    assert r.returncode == 0, r.stdout + r.stderr
    built = sorted(p.name for p in out.iterdir())
    assert built == OUTPUTS
    assert sorted(p.name for p in (CUTOVER / "expected").iterdir()) == OUTPUTS
    for name in OUTPUTS:
        assert (out / name).read_bytes() == (CUTOVER / "expected" / name).read_bytes(), f"{name} drifted"


def test_check_fails_on_hand_edit(tmp_path):
    src, out = fixture_src(tmp_path), tmp_path / "out"
    assert run_build("--src", src, "--out", out).returncode == 0
    ok = run_build("--src", src, "--out", out, "--check")
    assert ok.returncode == 0, ok.stdout + ok.stderr

    # a hand edit to a generated page
    page = out / "terms.html"
    edited = page.read_bytes() + b"<!-- hand edit -->\n"
    page.write_bytes(edited)
    r = run_build("--src", src, "--out", out, "--check")
    assert r.returncode == 1
    assert "terms.html" in r.stdout and "index.html" not in r.stdout
    assert page.read_bytes() == edited, "--check must not write"

    # a src edit that was never regenerated (the footer partial feeds index.html only)
    assert run_build("--src", src, "--out", out).returncode == 0
    foot = src / "partials" / "footer.html"
    foot.write_bytes(foot.read_bytes().replace(b"Installation help", b"Install help", 1))
    r = run_build("--src", src, "--out", out, "--check")
    assert r.returncode == 1
    assert r.stdout.split("\n", 1)[1].split() == ["index.html"]

    # a missing output counts as drift
    assert run_build("--src", src, "--out", out).returncode == 0
    (out / "404.html").unlink()
    r = run_build("--src", src, "--out", out, "--check")
    assert r.returncode == 1 and "404.html" in r.stdout


def load_frozen_derive():
    spec = importlib.util.spec_from_file_location("frozen_derive", CUTOVER / "derive-audio-page.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_audio_matches_derive_rules(tmp_path):
    out = tmp_path / "out"
    assert run_build("--src", CUTOVER / "src", "--out", out).returncode == 0

    # the retired script, run on the generator's mac-audio.html, gives the generator's audio.html
    derive = load_frozen_derive()
    assert len(derive.SUBS) == 13
    derive.SRC, derive.DST = out / "mac-audio.html", tmp_path / "derived-audio.html"
    assert derive.main() == 0
    assert (out / "audio.html").read_bytes() == derive.DST.read_bytes()

    # a substitution that no longer matches stops the build
    src = fixture_src(tmp_path)
    page = src / "pages" / "mac-audio.html"
    clean = page.read_bytes()
    page.write_bytes(clean.replace(b"In US dollars, for one person, on your Mac.", b"In US dollars, for one person.", 1))
    r = run_build("--src", src, "--out", tmp_path / "out2")
    assert r.returncode == 1 and "expected exactly one match, found 0" in r.stderr
    assert not (tmp_path / "out2" / "audio.html").exists()

    # Mac-only wording that survives the substitutions stops the build (each leftover guard)
    for leftover, pattern in (
        (b"Runs on your Mac.", "on your Mac(?! or PC)"),
        (b"Mac-only", "Mac-only"),
        (b"data-single-platform", "single-platform"),
    ):
        page.write_bytes(clean.replace(b"  </body>", b"    <p>" + leftover + b"</p>\n  </body>", 1))
        r = run_build("--src", src, "--out", tmp_path / "out3")
        assert r.returncode == 1, leftover
        assert "Mac-only wording survived" in r.stderr and pattern in r.stderr


def test_assetsignore_covers_source_dirs():
    entries = {
        line.strip().strip("/")
        for line in (ROOT / ".assetsignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for d in ("src", "tests", "docs", "scratch", "scripts"):
        assert d in entries, f".assetsignore must list {d}/ so it is never uploaded as a public file"


def test_include_rules(tmp_path):
    src = fixture_src(tmp_path)
    (src / "partials" / "greet.html").write_bytes(b"  <p>{{ who }} \xe2\x80\x94 {{where}}</p>  \n")
    # 404.html stands in for any declared page (the generator builds a fixed list of pages)
    (src / "pages" / "404.html").write_bytes(
        b"<main>\n  <!-- #include partials/greet.html who=Daniel where=\"in Nashville\" -->\n</main>\n"
    )
    out = tmp_path / "out"
    r = run_build("--src", src, "--out", out)
    assert r.returncode == 0, r.stderr
    # partial bytes verbatim (trailing spaces kept), placeholders filled, the directive line replaced
    assert (out / "404.html").read_bytes() == "<main>\n  <p>Daniel — in Nashville</p>  \n</main>\n".encode()

    bad = {
        b"<!-- #include partials/greet.html who=Daniel -->\n": "needs where=",
        b"<!-- #include partials/greet.html who=a where=b extra=c -->\n": "no placeholder for extra",
        b"<p><!-- #include partials/greet.html who=a where=b --></p>\n": "alone on its line",
        b"<!-- #include partials/nope.html -->\n": "no such partial",
        b"<!-- #include partials/../../x.html -->\n": "leaves the source folder",
        b"<p>ok</p>\r\n": "carriage return",
    }
    for body, msg in bad.items():
        (src / "pages" / "404.html").write_bytes(body)
        r = run_build("--src", src, "--out", tmp_path / "bad")
        assert r.returncode == 1 and msg in r.stderr, (body, r.stderr)


def test_rejects_symlink_outside_src(tmp_path):
    outside = tmp_path / "outside.html"
    outside.write_bytes(b"<p>SECRET from outside src</p>\n")
    for rel in ("pages/404.html", "partials/footer.html"):
        src = tmp_path / f"src-{rel.split('/')[0]}"
        shutil.copytree(CUTOVER / "src", src)
        (src / rel).unlink()
        (src / rel).symlink_to(outside)
        out = tmp_path / f"out-{rel.split('/')[0]}"
        r = run_build("--src", src, "--out", out)
        assert r.returncode == 1, (rel, r.stdout, r.stderr)
        assert "symlink" in r.stderr, (rel, r.stderr)
        assert not out.exists() or not any(b"SECRET" in p.read_bytes() for p in out.iterdir()), rel
    # a symlinked page directory is refused too
    src = fixture_src(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    shutil.move(str(src / "pages"), elsewhere)
    (src / "pages").symlink_to(elsewhere, target_is_directory=True)
    r = run_build("--src", src, "--out", tmp_path / "out-dir")
    assert r.returncode == 1 and "symlink" in r.stderr, r.stderr


def test_check_fails_when_page_source_missing(tmp_path):
    src, out = fixture_src(tmp_path), tmp_path / "out"
    assert run_build("--src", src, "--out", out).returncode == 0
    # a deleted page source leaves a stale root page: build and --check both fail and name it
    (src / "pages" / "terms.html").unlink()
    for args in (("--check",), ()):
        r = run_build("--src", src, "--out", out, *args)
        assert r.returncode == 1, (args, r.stdout, r.stderr)
        assert "terms.html" in r.stdout + r.stderr, args
    # a page source with no declared output is refused as well
    shutil.copy(CUTOVER / "src" / "pages" / "terms.html", src / "pages" / "terms.html")
    (src / "pages" / "extra.html").write_bytes(b"<p>extra</p>\n")
    for args in (("--check",), ()):
        r = run_build("--src", src, "--out", out, *args)
        assert r.returncode == 1 and "extra.html" in r.stdout + r.stderr, (args, r.stderr)
    assert not (out / "extra.html").exists()


def test_placeholder_cannot_inject_include(tmp_path):
    src = fixture_src(tmp_path)
    (src / "partials" / "v.html").write_bytes(b"<p>{{v}}</p>\n")
    page = src / "pages" / "404.html"
    clean = page.read_bytes()
    for arg in (b'v="<!-- #include partials/footer.html -->"', b"v=#include", b'v="a <!-- b"'):
        page.write_bytes(clean.replace(b"  </body>", b"    <!-- #include partials/v.html " + arg + b" -->\n  </body>", 1))
        out = tmp_path / "out"
        r = run_build("--src", src, "--out", out)
        assert r.returncode == 1, (arg, r.stdout)
        assert "value for v" in r.stderr, (arg, r.stderr)
        assert not (out / "404.html").exists()


def test_site_url_serves_built_pages(site_url):
    assert site_url.startswith("http://127.0.0.1:")
    for path in ("/index.html", "/audio.html", "/mac.html"):
        with urllib.request.urlopen(site_url + path, timeout=10) as resp:
            assert resp.status == 200
            assert resp.read() == (ROOT / path.lstrip("/")).read_bytes()
