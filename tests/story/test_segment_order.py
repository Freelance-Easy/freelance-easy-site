"""C3: the story's timeline is untouched by the checkpoint rebuild (PLAN § C3, "NEVER MAKE IT WORSE").

`__site.map().segs` (ids, order, and every segment's story-time bounds) must equal the base snapshot taken on 7ae00f7
(the scrub engine) for each layout and theme: C3 changed the input model only, so every scene and seam keeps its
duration and its place in the story.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright

# id:T0-T1 per layout and theme, measured on the base 7ae00f7 (Chromium, __site.map())
BASE = {
    ("desktop", "dark"): "make:0-4.92 makeLook:4.92-6.18 look:6.18-11.13 lookKnow:11.13-11.63 know:11.63-15.08 knowGrow:15.08-15.7 grow:15.7-17.46 ride:17.46-18.91 chase:18.91-24.96 chaseYours:24.96-25.86 yours:25.86-26.46 yoursPrice:26.46-27.71 price:27.71-28.31 priceBrand:28.31-29.61 brand:29.61-30.61",
    ("desktop", "light"): "make:0-4.51 makeLook:4.51-5.27 look:5.27-10.22 lookKnow:10.22-10.72 know:10.72-14.17 knowGrow:14.17-14.79 grow:14.79-16.55 ride:16.55-18 chase:18-24.05 chaseYours:24.05-24.95 yours:24.95-25.55 yoursPrice:25.55-26.8 price:26.8-27.4 priceBrand:27.4-28.7 brand:28.7-29.7",
    ("tablet", "dark"): "make:0-4.92 makeLook:4.92-6.18 look:6.18-11.13 lookKnow:11.13-11.63 know:11.63-15.08 knowGrow:15.08-15.7 grow:15.7-17.46 ride:17.46-18.91 chase:18.91-24.96",
    ("tablet", "light"): "make:0-4.51 makeLook:4.51-5.27 look:5.27-10.22 lookKnow:10.22-10.72 know:10.72-14.17 knowGrow:14.17-14.79 grow:14.79-16.55 ride:16.55-18 chase:18-24.05",
    ("phone", "dark"): "make:0-3.6 makeEnd:3.6-4.92 makeLook:4.92-6.18 look:6.18-11.13 lookKnow:11.13-11.63 know:11.63-15.08 knowGrow:15.08-15.7 grow:15.7-17.46 ride:17.46-18.91 chase:18.91-24.96 chaseYours:24.96-25.86 yours:25.86-26.46 yoursOffer:26.46-27.71 end:27.71-27.77",
    ("phone", "light"): "make:0-3.6 makeEnd:3.6-4.51 makeLook:4.51-5.27 look:5.27-10.22 lookKnow:10.22-10.72 know:10.72-14.17 knowGrow:14.17-14.79 grow:14.79-16.55 ride:16.55-18 chase:18-24.05 chaseYours:24.05-24.95 yours:24.95-25.55 yoursOffer:25.55-26.8 end:26.8-26.86",
}
SIZE = {"desktop": (1440, 900, False), "tablet": (820, 1180, False), "phone": (390, 664, True)}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.mark.parametrize("layout,theme", sorted(BASE), ids=[f"{a}-{b}" for a, b in sorted(BASE)])
def test_segments_equal_base(browser, site_url, layout, theme):
    w, h, touch = SIZE[layout]
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{theme}')}}catch(e){{}}")
    try:
        page = ctx.new_page()
        page.goto(site_url + "/?pace=before", wait_until="load")   # C5: the base timeline is the A/B flag's; C5's own table is tests/checkpoint/test_timing.py
        page.wait_for_function("() => window.__site && window.__site.TL", timeout=10000)
        got = page.evaluate("() => window.__site.map().segs.map(s => `${s.id}:${s.T0}-${s.T1}`).join(' ')")
        assert got == BASE[(layout, theme)], f"segment ids/order/bounds changed from the base 7ae00f7:\n got  {got}\n base {BASE[(layout, theme)]}"
    finally:
        ctx.close()
