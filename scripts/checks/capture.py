#!/usr/bin/env python3
"""Deterministic captures.

    capture.py <url> --widths 390,1024,1280,1440 --themes dark,light --out <dir>

Writes <dir>/<page>-<theme>-<width>.png (full page) for every width x theme.
Two runs against the same server produce byte-identical PNGs: motion is frozen
(prefers-reduced-motion: reduce, animation/transition/caret killed by an injected
stylesheet, videos paused at frame 0, smooth scrolling off), fonts and images are
awaited, the clock-free layout is captured at scroll 0, device scale factor 1.
Only 127.0.0.1/localhost is contacted. Exit 0 ok, 2 usage error.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

LOCAL = {"127.0.0.1", "localhost"}
FREEZE_CSS = """
*, *::before, *::after {
  animation: none !important; transition: none !important;
  caret-color: transparent !important; scroll-behavior: auto !important;
}
"""
SETTLE_JS = """async () => {
  if (document.fonts) await document.fonts.ready;
  await Promise.all(Array.from(document.images).map(i => i.decode ? i.decode().catch(() => null) : null));
  document.querySelectorAll('video').forEach(v => { v.pause(); try { v.currentTime = 0; } catch (e) {} });
  document.getAnimations().forEach(a => { try { a.cancel(); } catch (e) {} });
  window.scrollTo(0, 0);
}"""


def slug(url: str) -> str:
    path = urlparse(url).path.strip("/") or "home"
    return re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-")


def capture(url: str, widths: list[int], themes: list[str], out: Path) -> list[Path]:
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--font-render-hinting=none", "--disable-lcd-text"])
        try:
            for theme in themes:
                for w in widths:
                    ctx = browser.new_context(
                        viewport={"width": w, "height": 900}, device_scale_factor=1,
                        color_scheme=theme, reduced_motion="reduce", locale="en-US",
                        timezone_id="UTC")
                    ctx.route("**/*", lambda r: r.continue_()
                              if urlparse(r.request.url).hostname in LOCAL else r.abort())
                    ctx.add_init_script(
                        "try{localStorage.setItem('fe-theme'," + json.dumps(theme) + ")}catch(e){}")
                    page = ctx.new_page()
                    try:
                        page.goto(url, wait_until="load")
                        page.add_style_tag(content=FREEZE_CSS)
                        page.wait_for_timeout(500)
                        page.evaluate(SETTLE_JS)
                        page.wait_for_timeout(200)
                        f = out / f"{slug(url)}-{theme}-{w}.png"
                        page.screenshot(path=str(f), full_page=True, animations="disabled",
                                        caret="hide")
                        written.append(f)
                    finally:
                        ctx.close()
        finally:
            browser.close()
    return written


def main(argv: list[str]) -> int:
    args = argv[1:]
    url, out, widths, themes, bad = None, None, [390, 1024, 1280, 1440], ["dark", "light"], False
    i = 0
    try:
        while i < len(args):
            a = args[i]
            if a == "--widths":
                i += 1
                widths = [int(x) for x in args[i].split(",")]
            elif a == "--themes":
                i += 1
                themes = [x.strip() for x in args[i].split(",")]
            elif a == "--out":
                i += 1
                out = Path(args[i])
            elif not a.startswith("-") and url is None:
                url = a
            else:
                bad = True
            i += 1
    except (IndexError, ValueError):
        bad = True
    if (bad or not url or out is None or urlparse(url).hostname not in LOCAL
            or any(t not in ("dark", "light") for t in themes)):
        print("usage: capture.py <http://127.0.0.1:PORT/path> --widths 390,1024,1280,1440 "
              "--themes dark,light --out <dir>", file=sys.stderr)
        return 2
    for f in capture(url, widths, themes, out):
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
