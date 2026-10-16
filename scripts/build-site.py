#!/usr/bin/env python3
"""Build the eight root pages from src/ (stdlib only).

Layout:
  src/pages/<name>.html     one source per output page; written to <out>/<name>.html
  src/partials/**.html      shared spans, pulled in with an include line

The only template feature is the include line. A line that holds nothing but an
include directive (leading spaces allowed) is replaced by the partial's bytes; the
partial carries its own indentation and its trailing newline:

  <!-- #include partials/header.html -->
  <!-- #include partials/campaign/footer.html key=value other="two words" -->

Optional key=value pairs fill {{key}} placeholders in that partial. A placeholder
with no value, a value with no placeholder, a partial that includes another
partial, or an include directive anywhere other than on its own line all stop
the build. There is no other logic.

audio.html (Reddit; Mac + Windows) is derived from the built mac-audio.html (Google
ads; Mac only) by the substitutions below, ported verbatim from the retired
scripts/derive-audio-page.py: each one must match exactly once, and Mac-only
wording that survives them stops the build.

Usage (from the repo root):
  python3 scripts/build-site.py            build src/ into the repo root
  python3 scripts/build-site.py --check    rebuild in memory; exit 1 and list the
                                           committed outputs that differ
  --src <dir>  source folder (default: src/)    --out <dir>  output folder (default: repo root)
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

INCLUDE_LINE = re.compile(
    r"^[ \t]*<!-- #include (partials/[A-Za-z0-9_./-]+\.html)"
    r"((?: +[A-Za-z_][A-Za-z0-9_-]*=(?:\"[^\"]*\"|[^\s\"]+))*) -->\n?$"
)
INCLUDE_ANY = re.compile(r"<!--\s*#include\b")
VAR = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)=(?:\"([^\"]*)\"|([^\s\"]+))")
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_-]*)\s*\}\}")

# ---- audio.html: ported verbatim from scripts/derive-audio-page.py:22-82 (652d12a) ----
WIN_NOTE = (
    '<div class="dl-support" data-support="win" hidden>'
    "For Windows 10 and 11, 64-bit. The installer isn't code-signed yet, so Windows shows a security warning "
    'the first time you open it. <a href="/install#windows">Installation help</a></div>'
)

SUBS: list[tuple[str, str]] = [
    (
        "<title>Freelance Easy for audio pros on Mac — invoice your next client for $5 a month</title>",
        "<title>Freelance Easy for audio pros — invoice your next client for $5 a month</title>",
    ),
    (
        "on your own Mac. Every feature free for seven days, no card.",
        "on your own Mac or PC. Every feature free for seven days, no card.",
    ),
    (
        "<!-- Campaign landing page (Google ads, Mac-only). Not for search. -->",
        "<!-- Campaign landing page (Reddit; Mac + Windows). Not for search. -->",
    ),
    ('<body data-page="mac-audio" data-campaign="mac-audio">', '<body data-page="audio" data-campaign="audio">'),
    (
        "Invoicing for mix engineers, producers and studios, on your Mac.",
        "Invoicing for mix engineers, producers and studios, on Mac and Windows.",
    ),
    ("A desktop invoicing app for audio work, on your Mac: day rates", "A desktop invoicing app for audio work, on your Mac or PC: day rates"),
    ("live in a folder on\n              your own Mac, not on a web app's servers.", "live in a folder on\n              your own computer, not on a web app's servers."),
    ('<div class="dl" data-dl data-placement="hero" data-single-platform="mac">', '<div class="dl" data-dl data-placement="hero">'),
    (
        '<a class="dl-alt" data-role="alt" href="/"><span data-label>Need the Windows version?</span></a>',
        '<a class="dl-alt" data-platform="win" data-role="alt" href="/download/win"><span data-label>Download for Windows</span></a>',
    ),
    (
        '<div class="dl-support" data-support="win" hidden>This page is for the Mac version. <a href="/">The Windows download is on the main page.</a></div>',
        WIN_NOTE,
    ),
    (
        "There's no mobile app. Send yourself the link and open it on your Mac.",
        "There's no mobile app. Send yourself the link and open it on your Mac or PC.",
    ),
    ("In US dollars, for one person, on your Mac.", "In US dollars, for one person, on your Mac or PC."),
    (
        "Checkout is handled by Stripe: card, Apple Pay or Link.",
        "Checkout is handled by Stripe: card, Apple Pay, Google Pay or Link.",
    ),
]

# "Check your Mac's chip and macOS version" is the Mac visitor's note and stays on both
# pages; "on your Mac or PC" is the two-platform wording the substitutions write.
LEFTOVERS = (r"on your Mac(?! or PC)", r"Mac-only", r"single-platform")

DERIVED = {"audio.html": "mac-audio.html"}

# The generator owns a fixed list of outputs: every declared page needs src/pages/<name>, and a
# source with no declared output is refused, so a deleted or stray source never slips past --check.
# PAGES are the cutover's pages; a page added later is declared in <src>/pages.txt (one name per line,
# "#" comments), so the frozen cutover fixture, which has no pages.txt, still builds exactly its own.
PAGES = ("index.html", "install.html", "privacy.html", "terms.html", "404.html", "mac.html", "mac-audio.html")
ADDED_PAGES = "pages.txt"


class BuildError(Exception):
    pass


def read_text(path: pathlib.Path) -> str:
    # bytes in, bytes out: no newline translation and no trimming
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise BuildError(f"{path}: starts with a UTF-8 BOM")
    if b"\r" in data:
        raise BuildError(f"{path}: contains a carriage return (CRLF); sources use LF only")
    return data.decode("utf-8")


def source_file(src: pathlib.Path, path: pathlib.Path, where: str) -> pathlib.Path:
    """A source must be a regular file inside src/: no symlink anywhere below src/, and its
    strictly resolved path must stay inside the resolved src/ folder."""
    root = src.resolve(strict=True)
    try:
        rel = path.relative_to(src)
    except ValueError:
        raise BuildError(f"{where}: {path} is outside the source folder") from None
    if ".." in rel.parts:
        raise BuildError(f"{where}: include path leaves the source folder: {rel}")
    node = src
    for part in rel.parts:
        node = node / part
        if node.is_symlink():
            raise BuildError(f"{where}: {node} is a symlink; sources must be regular files inside {src}")
    if not path.is_file():
        raise BuildError(f"{where}: no such file: {rel}")
    resolved = path.resolve(strict=True)
    if root not in resolved.parents:
        raise BuildError(f"{where}: {rel} resolves outside the source folder")
    return resolved


def render_partial(src: pathlib.Path, rel: str, args: str, where: str) -> str:
    if ".." in pathlib.PurePosixPath(rel).parts:
        raise BuildError(f"{where}: include path leaves the source folder: {rel}")
    if not (src / rel).is_file() and not (src / rel).is_symlink():
        raise BuildError(f"{where}: no such partial: {rel}")
    path = source_file(src, src / rel, where)
    text = read_text(path)
    if INCLUDE_ANY.search(text):
        raise BuildError(f"{rel}: partials cannot include other partials")
    values: dict[str, str] = {}
    for m in VAR.finditer(args):
        key = m.group(1)
        if key in values:
            raise BuildError(f"{where}: {key} given twice")
        value = m.group(2) if m.group(2) is not None else m.group(3)
        # values are refused, not re-validated after substitution: a value can never carry a
        # comment or an include directive into the page
        if "<!--" in value or "-->" in value or "#include" in value:
            raise BuildError(f"{where}: the value for {key} may not contain '<!--', '-->' or '#include'")
        values[key] = value
    used: set[str] = set()

    def fill(m: re.Match) -> str:
        key = m.group(1)
        if key not in values:
            raise BuildError(f"{where}: {rel} needs {key}=..., which the include line does not give")
        used.add(key)
        return values[key]

    text = PLACEHOLDER.sub(fill, text)
    # values are checked one by one above; partial text and values can still combine into a directive
    if INCLUDE_ANY.search(text):
        raise BuildError(f"{where}: {rel} forms an include directive once its values are filled")
    unused = sorted(set(values) - used)
    if unused:
        raise BuildError(f"{where}: {rel} has no placeholder for {', '.join(unused)}")
    return text


def render_page(src: pathlib.Path, page: pathlib.Path) -> str:
    out: list[str] = []
    path = source_file(src, page, page.name)
    for n, line in enumerate(read_text(path).splitlines(keepends=True), 1):
        where = f"{page.name}:{n}"
        m = INCLUDE_LINE.match(line)
        if m:
            text = render_partial(src, m.group(1), m.group(2), where)
            if line.endswith("\n") and not text.endswith("\n"):
                raise BuildError(f"{where}: {m.group(1)} must end with a newline")
            out.append(text)
        elif INCLUDE_ANY.search(line):
            raise BuildError(
                f"{where}: an include directive must sit alone on its line, as <!-- #include partials/<name>.html -->"
            )
        else:
            out.append(line)
    return "".join(out)


def derive_audio(html: str) -> str:
    for old, new in SUBS:
        n = html.count(old)
        if n != 1:
            raise BuildError(f"audio.html: expected exactly one match, found {n}:\n  {old[:90]}")
        html = html.replace(old, new)
    for leftover in LEFTOVERS:
        if re.search(leftover, html):
            raise BuildError(f"audio.html: Mac-only wording survived: {leftover!r}")
    return html


def declared_pages(src: pathlib.Path) -> tuple[str, ...]:
    """PAGES plus the pages <src>/pages.txt adds."""
    path = src / ADDED_PAGES
    if not path.exists() and not path.is_symlink():
        return PAGES
    added: list[str] = []
    for n, line in enumerate(read_text(source_file(src, path, ADDED_PAGES)).splitlines(), 1):
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.html", name):
            raise BuildError(f"{ADDED_PAGES}:{n}: not a page name: {name!r}")
        if name in PAGES or name in DERIVED or name in added:
            raise BuildError(f"{ADDED_PAGES}:{n}: {name} is already declared")
        added.append(name)
    return PAGES + tuple(added)


def build(src: pathlib.Path) -> dict[str, bytes]:
    pages_dir = src / "pages"
    if not src.is_dir() or not pages_dir.is_dir():
        raise BuildError(f"no pages folder: {pages_dir}")
    if pages_dir.is_symlink():
        raise BuildError(f"{pages_dir} is a symlink; sources must be regular files inside {src}")
    pages = declared_pages(src)
    found = sorted(p.name for p in pages_dir.iterdir() if p.name.endswith(".html"))
    derived = sorted(set(found) & set(DERIVED))
    if derived:
        raise BuildError(f"{', '.join(derived)} is derived, not built from a source; remove it from {pages_dir}")
    missing = sorted(set(pages) - set(found))
    if missing:
        raise BuildError(f"declared pages with no source in {pages_dir}: {', '.join(missing)}")
    stray = sorted(set(found) - set(pages))
    if stray:
        raise BuildError(f"page sources with no declared output (add them to {src / ADDED_PAGES}): {', '.join(stray)}")
    html = {name: render_page(src, pages_dir / name) for name in pages}
    for name, base in DERIVED.items():
        html[name] = derive_audio(html[base])
    return {name: text.encode("utf-8") for name, text in html.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the root pages from src/.")
    ap.add_argument("--src", type=pathlib.Path, default=ROOT / "src", help="source folder (default: src/)")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT, help="output folder (default: the repo root)")
    ap.add_argument("--check", action="store_true", help="build in memory and list outputs that differ from --out")
    args = ap.parse_args(argv)
    try:
        outputs = build(args.src)
    except BuildError as e:
        print(f"build-site: {e}", file=sys.stderr)
        return 1
    if args.check:
        drifted = []
        for name, data in outputs.items():
            target = args.out / name
            if not target.is_file() or target.read_bytes() != data:
                drifted.append(name)
        if drifted:
            print("build-site --check: these outputs differ from src/ (edit src/, then run scripts/build-site.py):")
            for name in drifted:
                print(f"  {name}")
            return 1
        print(f"build-site --check: {len(outputs)} outputs match src/")
        return 0
    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        target = args.out / name
        if not target.is_file() or target.read_bytes() != data:
            target.write_bytes(data)
    print(f"build-site: {len(outputs)} pages built into {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
