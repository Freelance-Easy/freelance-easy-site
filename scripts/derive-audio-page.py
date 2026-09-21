#!/usr/bin/env python3
"""Derive audio.html (Reddit; Mac + Windows) from mac-audio.html (Google ads; Mac only).

The two campaign pages are the same page with a different platform story, so
audio.html is generated rather than maintained by hand. Every substitution
below must match exactly once, or the script stops — a silent miss would ship
Mac-only wording on the two-platform page.

Usage (from the repo root):
  python3 scripts/derive-audio-page.py
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "mac-audio.html"
DST = ROOT / "audio.html"

WIN_NOTE = (
    '<div class="dl-support" data-support="win" hidden>'
    "For Windows 10 and 11, 64-bit. The installer isn't code-signed yet, so Windows shows a security warning "
    'the first time you open it. <a href="/install#windows">Installation help</a></div>'
)

SUBS: list[tuple[str, str]] = [
    (
        "<title>Freelance Easy for audio pros on Mac — make your first invoice in 60 seconds</title>",
        "<title>Freelance Easy for audio pros — make your first invoice in 60 seconds</title>",
    ),
    (
        "on your own Mac. Free for seven days, then $5 a month",
        "on your own Mac or PC. Free for seven days, then $5 a month",
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
    ("your files stay on your Mac either way.", "your files stay on your computer either way."),
    ("In US dollars, for one person, on your Mac.", "In US dollars, for one person, on your Mac or PC."),
    (
        "Checkout is handled by Stripe: card, Apple Pay or Link.",
        "Checkout is handled by Stripe: card, Apple Pay, Google Pay or Link.",
    ),
    ("invoices themselves stay on your Mac.", "invoices themselves stay on your computer."),
]


def main() -> int:
    html = SRC.read_text(encoding="utf-8")
    for old, new in SUBS:
        n = html.count(old)
        if n != 1:
            print(f"expected exactly one match, found {n}:\n  {old[:90]}", file=sys.stderr)
            return 1
        html = html.replace(old, new)
    # "Check which chip your Mac has" is the Mac visitor's note and stays on both
    # pages; "on your Mac or PC" is the two-platform wording this script writes.
    for leftover in (r"on your Mac(?! or PC)", r"Mac-only", r"single-platform"):
        if re.search(leftover, html):
            print(f"Mac-only wording survived: {leftover!r}", file=sys.stderr)
            return 1
    DST.write_text(html, encoding="utf-8")
    print("wrote", DST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
