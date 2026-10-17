"""Footer sentence probe (C8; A10 judge's BINDING merge condition). Needs pillow: `uv run --with playwright --with pillow`.

"Clients, invoices and amounts in the demos, screenshots and tour are fictional." must be, on "/", "/tour/", "/pricing"
and "/privacy":
  - present once in the footer with that exact text, rendered at >= 15 px with opacity 1;
  - >= 4.5:1 on the RENDERED pixels: the text hidden (-webkit-text-fill-color), the element's box screenshot, the
    text colour against the worst pixel behind the words;
  - in view and not covered (elementFromPoint) once the page is scrolled to its end;
  in these layouts: calm-1440, calm-390 (prefers-reduced-motion, JS on), nojs-1440, nojs-390 (JS off); and on "/" with
  the pinned story (motion on, 1440 and 390x664) at the page end.
Usage: footnote_probe.py http://127.0.0.1:<port>
"""
from __future__ import annotations

import io
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from _common import Report, base_url, resolve, run_main  # noqa: E402

SENTENCE = "Clients, invoices and amounts in the demos, screenshots and tour are fictional."
SEL = 'footer [data-footnote="fictional"]'
PATHS = ["/", "/tour/", "/pricing", "/privacy"]
LAYOUTS = [("calm-1440", 1440, 900, True, True), ("calm-390", 390, 844, True, True),
           ("nojs-1440", 1440, 900, False, False), ("nojs-390", 390, 844, False, False),
           ("pinned-1440", 1440, 900, False, True), ("pinned-390", 390, 664, False, True)]   # name, w, h, reduced, js

INFO = """(sel) => { const e = document.querySelector(sel), r = e.getBoundingClientRect(), cs = getComputedStyle(e);
  const hit = document.elementFromPoint(r.left + Math.min(20, r.width / 2), r.top + r.height / 2);
  const m = cs.color.match(/[\\d.]+/g).map(Number);
  return { text: e.textContent.trim(), px: parseFloat(cs.fontSize), opacity: cs.opacity, color: m,
           box: { x: r.left, y: r.top, width: r.width, height: r.height },
           inView: r.top >= 0 && r.bottom <= innerHeight && r.width > 0, onTop: !!hit && e.contains(hit) }; }"""
HIDE = "(sel) => document.querySelector(sel).style.setProperty('-webkit-text-fill-color', 'transparent', 'important')"
SHOW = "(sel) => document.querySelector(sel).style.removeProperty('-webkit-text-fill-color')"


def lum(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def worst_ratio(page, info) -> float:
    from PIL import Image
    fg = [round(v) for v in info["color"][:3]]
    alpha = info["color"][3] if len(info["color"]) > 3 else 1.0
    page.evaluate(HIDE, SEL)
    try:
        png = page.screenshot(clip=info["box"], animations="allow", caret="hide")
    finally:
        page.evaluate(SHOW, SEL)
    img = Image.open(io.BytesIO(png)).convert("RGB")
    worst = 99.0
    for px in set(img.getdata()):
        over = tuple(alpha * f + (1 - alpha) * b for f, b in zip(fg, px))
        worst = min(worst, ratio(over, px))
    return worst


def main() -> int:
    base, rep = base_url(), Report("footnote")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for path in PATHS:
            url = resolve(base, path)
            for name, w, h, reduced, js in LAYOUTS:
                if name.startswith("pinned") and path != "/":
                    continue
                tag = f"{path} {name}"
                for theme in (("dark", "light") if js else ("dark",)):
                    ctx = browser.new_context(viewport={"width": w, "height": h}, java_script_enabled=js,
                                              reduced_motion="reduce" if reduced else "no-preference",
                                              color_scheme=theme)
                    ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{theme}')}}catch(e){{}}")
                    page = ctx.new_page()
                    try:
                        page.goto(url, wait_until="load")
                        where = f"{tag} {theme}" if js else tag
                        if page.locator(SEL).count() != 1:
                            rep.check(False, f"{where}: one footnote", page.locator(SEL).count())
                            continue
                        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
                        page.wait_for_timeout(900)
                        info = page.evaluate(INFO, SEL)
                        rep.check(info["text"] == SENTENCE and info["px"] >= 15 and info["opacity"] == "1",
                                  f"{where}: exact text, >= 15 px, opaque", [info["text"][:30], info["px"], info["opacity"]])
                        rep.check(info["inView"] and info["onTop"], f"{where}: in view and not covered at the page end",
                                  [info["inView"], info["onTop"]])
                        r = worst_ratio(page, info)
                        rep.check(r >= 4.5, f"{where}: {r:.2f}:1 on the rendered pixels (>= 4.5)", round(r, 2))
                    finally:
                        ctx.close()
        browser.close()
    return rep.finish()


if __name__ == "__main__":
    sys.exit(run_main(main))
