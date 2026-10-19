"""WebKit smoke (C8; GATEFIX judge: the 640 bar had ~2.6 px spare in Chromium, Safari unverified).

Playwright WebKit at 600 / 640 / 680 / 800 / 1023 px on "/" and "/tour/":
  - the bar is one row: the brand and every visible nav item share one vertical band (centres within 8 px) and the header is
    one line tall (height <= 1.6 x its tallest item + 24 px);
  - `.site-header .nav` scrollWidth <= clientWidth + 1 (nothing overflows the nav);
  - nothing overlaps the brand TEXT box (`.site-header .brand span`): no other visible bar item intersects it;
  - the requirement note (`.dl-note`) is visible at >= 640 px (it is allowed to be absent below).
Usage: webkit_probe.py http://127.0.0.1:<port>   (needs `playwright install webkit`)
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from _common import Report, base_url, run_main  # noqa: E402

WIDTHS = [600, 640, 680, 800, 1023]
MEASURE = """() => {
  const hdr = document.querySelector('.site-header'), shell = hdr.querySelector('.shell') || hdr;
  const vis = (e) => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const nav = hdr.querySelector('.nav'), brandText = hdr.querySelector('.brand span');
  const box = (e) => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom }; };
  const items = [...hdr.querySelectorAll('.brand, .nav > *')].filter(vis);
  const flat = [...hdr.querySelectorAll('.brand img, .nav a, .nav button, .nav .dl-note')].filter(vis);
  const bt = box(brandText);
  const over = flat.filter((e) => !e.closest('.brand')).filter((e) => { const r = box(e);
    return r.l < bt.r - 0.5 && r.r > bt.l + 0.5 && r.t < bt.b - 0.5 && r.b > bt.t + 0.5; }).map((e) => e.className || e.tagName);
  const tops = items.map((e) => box(e)), tall = Math.max(...tops.map((r) => r.b - r.t));
  const note = hdr.querySelector('.dl-note');
  const cy = tops.map((r) => (r.t + r.b) / 2);
  return { hdrH: hdr.getBoundingClientRect().height, tall, spread: Math.max(...cy) - Math.min(...cy),
    navScroll: [nav.scrollWidth, nav.clientWidth], over, note: note ? vis(note) : null }; }"""


def main() -> int:
    base, rep = base_url(), Report("webkit")
    with sync_playwright() as pw:
        try:
            browser = pw.webkit.launch()
        except Exception as e:  # noqa: BLE001
            rep.check(False, "webkit launches", str(e).splitlines()[0])
            return rep.finish()
        for path in ("/", "/tour/"):
            for w in WIDTHS:
                ctx = browser.new_context(viewport={"width": w, "height": 800})
                page = ctx.new_page()
                try:
                    page.goto(base + path, wait_until="load")
                    page.wait_for_timeout(1200)                       # download.js fills the note after load
                    m = page.evaluate(MEASURE)
                    tag = f"{path} {w}"
                    rep.check(m["spread"] <= 8 and m["hdrH"] <= m["tall"] * 1.6 + 24,
                              f"{tag}: the bar is one row", {k: m[k] for k in ("hdrH", "tall", "spread")})
                    rep.check(m["navScroll"][0] <= m["navScroll"][1] + 1, f"{tag}: nav scrollWidth <= clientWidth + 1", m["navScroll"])
                    rep.check(not m["over"], f"{tag}: nothing over the brand text", m["over"])
                    if w >= 640:
                        rep.check(m["note"] is True, f"{tag}: the requirement note is visible", m["note"])
                finally:
                    ctx.close()
        browser.close()
    return rep.finish()


if __name__ == "__main__":
    sys.exit(run_main(main))
