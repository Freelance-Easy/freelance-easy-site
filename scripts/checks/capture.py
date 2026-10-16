#!/usr/bin/env python3
"""Deterministic captures.

    capture.py <url> --widths 390,1024,1280,1440 --themes dark,light --out <dir>

Writes <dir>/<page>-<theme>-<width>.png (full page) for every width x theme.
Two runs against the same server produce byte-identical PNGs: motion is frozen
(prefers-reduced-motion: reduce, animation/transition/caret killed by an injected
stylesheet, videos paused at frame 0, smooth scrolling off), fonts and images are
awaited, the clock-free layout is captured at scroll 0, device scale factor 1.
Only 127.0.0.1/localhost is contacted. Exit 0 ok, 1 capture failed (e.g. images still
pending after the bound), 2 usage error.

    --seek 0,6.5   story seconds: after load, window.__site.seekMaster(t) and a viewport
                   shot per time -> <page>-<theme>-<width>-t<sec>.png (repeatable / comma list)
    --motion       run with motion on (no reduced-motion); default stays reduced-motion.
                   --seek implies it: the reduced-motion layout has no story timeline.

Offscreen loading="lazy" images are forced eager and awaited with a bounded timeout
(IMAGE_WAIT_MS); anything still pending is named on stderr and the run exits 1.
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
IMAGE_WAIT_MS = 15000
SETTLE_JS = """async (bound) => {
  if (document.fonts) await document.fonts.ready;
  const imgs = Array.from(document.images);
  imgs.forEach(i => { if (i.loading === 'lazy') i.loading = 'eager'; });
  const pending = new Set(imgs.filter(i => (i.currentSrc || i.src || i.srcset) && !(i.complete && i.naturalWidth)));
  await Promise.race([
    Promise.all(imgs.map(i => (i.complete ? Promise.resolve() : new Promise(r => {
      i.addEventListener('load', r, {once: true}); i.addEventListener('error', r, {once: true}); }))
      .then(() => { if (i.complete && i.naturalWidth) pending.delete(i); }))),
    new Promise(r => setTimeout(r, bound))]);
  const stuck = Array.from(pending).filter(i => !(i.complete && i.naturalWidth)).map(i => i.currentSrc || i.src || i.srcset);
  if (stuck.length) return stuck;
  await Promise.race([Promise.all(imgs.map(i => i.decode ? i.decode().catch(() => null) : null)),
    new Promise(r => setTimeout(r, bound))]);
  document.querySelectorAll('video').forEach(v => { v.pause(); try { v.currentTime = 0; } catch (e) {} });
  document.getAnimations().forEach(a => { try { a.cancel(); } catch (e) {} });
  window.scrollTo(0, 0);
  return [];
}"""
SEEK_JS = """async (t) => {
  const s = window.__site;
  if (!s || !s.seekMaster) throw new Error('window.__site.seekMaster missing (no story on this page)');
  for (let n = 0; n < 100 && !s.TL; n++) await new Promise(r => setTimeout(r, 100));
  if (!s.TL) throw new Error('story timeline never built (is motion on? the reduced-motion layout has none)');
  s.seekMaster(t);
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  s.seekMaster(t);
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  return t;
}"""


class CaptureError(Exception):
    pass


def slug(url: str) -> str:
    path = urlparse(url).path.strip("/") or "home"
    return re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-")


def capture(url: str, widths: list[int], themes: list[str], out: Path,
            seeks: list[float] | None = None, motion: bool = False) -> list[Path]:
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
                        color_scheme=theme, reduced_motion="no-preference" if (motion or seeks) else "reduce", locale="en-US",
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
                        stuck = page.evaluate(SETTLE_JS, IMAGE_WAIT_MS)
                        if stuck:
                            raise CaptureError(
                                f"{len(stuck)} image(s) still pending after {IMAGE_WAIT_MS} ms: "
                                + ", ".join(stuck[:10]))
                        page.wait_for_timeout(200)
                        base = out / f"{slug(url)}-{theme}-{w}"
                        if not seeks:
                            f = Path(f"{base}.png")
                            page.screenshot(path=str(f), full_page=True, animations="disabled",
                                            caret="hide")
                            written.append(f)
                        for t in seeks or []:
                            page.evaluate(SEEK_JS, t)
                            f = Path(f"{base}-t{str(t).removesuffix('.0')}.png")
                            page.screenshot(path=str(f), animations="disabled", caret="hide")
                            written.append(f)
                    finally:
                        ctx.close()
        finally:
            browser.close()
    return written


def main(argv: list[str]) -> int:
    args = argv[1:]
    url, out, widths, themes, bad = None, None, [390, 1024, 1280, 1440], ["dark", "light"], False
    seeks: list[float] = []
    motion = False
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
            elif a == "--seek":
                i += 1
                seeks += [float(x) for x in args[i].split(",")]
            elif a == "--motion":
                motion = True
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
              "--themes dark,light [--seek 0,6.5] [--motion] --out <dir>", file=sys.stderr)
        return 2
    try:
        files = capture(url, widths, themes, out, seeks, motion)
    except Exception as e:  # never hang, never traceback: one message, non-zero
        print(f"capture failed: {e}", file=sys.stderr)
        return 1
    for f in files:
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
