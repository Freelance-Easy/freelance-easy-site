#!/usr/bin/env python3
"""Capture the invoice-creation flow from the running DEV app for the site's
"Making an invoice" section.

The script signs in as the mock user, rewrites the session to the fictional
persona, then makes a REAL invoice through the UI — new invoice, title, client,
two line items, a note, Create. Afterwards it deletes the invoice
(POST /invoices/<id>/delete) so the demo data set is unchanged.

--video (what the page uses since v2.3) records one dark-theme pass with a
drawn cursor and human typing speed (Playwright records no cursor of its own)
and writes the raw .webm plus the second offsets of the useful segment;
encode-process-video.py cuts the loop and the real-time file from it.

Without --video it captures a still at each stage, in both themes, plus
phone-width detail crops. The page stopped using those frames in v2.3 (the
loop replaced them); the stage is kept for a future still.

Prerequisites: the same as capture-screenshots.py (mock LicenseServer on :5001,
the app in DEV mode on :50505 with the fictional demo data, `playwright pillow`).

Usage:
  python scripts/capture-process.py --out assets/screenshots \
      --profile "/path/to/InvoiceGenerator/.dev-profile"
  python scripts/capture-process.py --video assets/video/raw \
      --profile "/path/to/InvoiceGenerator/.dev-profile"

Outputs (stills): create-1-details-{dark,light}.png, create-2-items-{dark,light}.png,
  create-3-preview-{dark,light}.png and the phone crops create-N-*-m-{dark,light}.png.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1440, "height": 900}
ITEMS_VIEWPORT = {"width": 1440, "height": 920}  # the new-invoice page is taller than the edit page (recurring row + Create button)
PERSONA = {"display_name": "Jordan Reyes", "email": "jordan@example.com"}

# The fictional job being invoiced. Different from the hero invoice (a session
# day for Westbrook Sound) so the page shows two real jobs, not one twice.
JOB = {
    "client": "Cedar Lane Records",
    "title": "Mix — 'Tall Grass' (single)",
    "items": [("Mix — 'Tall Grass'", "450"), ("Instrumental + TV mix", "75")],
    "note": "Thanks for the work — payment by bank transfer or Zelle within terms.",
}

CURSOR_JS = """
(() => {
  const c = document.createElement('div');
  c.id = '__cursor';
  c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:30px;pointer-events:none;z-index:2147483647;'
    + 'transform:translate(-3px,-2px);opacity:0;transition:opacity .2s';
  c.innerHTML = '<svg width="22" height="30" viewBox="0 0 22 30"><path d="M2 2 L2 24 L8 18 L12 27 L16 25 L12 16 L20 16 Z" fill="#fff" stroke="#000" stroke-width="1.5" stroke-linejoin="round"/></svg>';
  const add = () => document.body && document.body.appendChild(c);
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', add) : add();
  window.addEventListener('mousemove', e => { c.style.opacity = '1'; c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  window.addEventListener('mousedown', () => { c.style.transform = 'translate(-3px,-2px) scale(.85)'; }, true);
  window.addEventListener('mouseup', () => { c.style.transform = 'translate(-3px,-2px)'; }, true);
})();
"""


def patch_session(profile: pathlib.Path) -> None:
    path = profile / "session.json"
    data = json.loads(path.read_text())
    data.update(PERSONA)
    path.write_text(json.dumps(data))


def box(locator):
    b = locator.bounding_box()
    if b is None:
        raise RuntimeError("element has no box — is it rendered?")
    return b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"]


def crop_png(src: pathlib.Path, box_css, dst: pathlib.Path, pad: int = 12) -> None:
    from PIL import Image

    im = Image.open(src)
    w, h = im.size
    x0, y0, x1, y1 = box_css
    region = (max(0, int((x0 - pad) * 2)), max(0, int((y0 - pad) * 2)), min(w, int((x1 + pad) * 2)), min(h, int((y1 + pad) * 2)))
    im.crop(region).save(dst, optimize=True)


def scroll_editor_top(page) -> None:
    """Back to the top of the editor's own scroller (the window doesn't scroll)."""
    page.evaluate(
        """() => {
            const sp = document.querySelector('.main-wrap');
            if (sp) sp.scrollTop = 0; else window.scrollTo(0, 0);
        }"""
    )
    page.wait_for_timeout(250)


def scroll_editor_to(page, locator, top: int = 24) -> None:
    """Scroll the editor's own container so `locator` sits `top` px from the top."""
    locator.evaluate("el => el.scrollIntoView({block: 'start'})")
    locator.evaluate(
        """(el, top) => {
            const delta = el.getBoundingClientRect().top - top;
            let sp = el.parentElement;
            while (sp && sp !== document.body) {
                const s = getComputedStyle(sp);
                if (/(auto|scroll)/.test(s.overflowY) && sp.scrollHeight > sp.clientHeight) { sp.scrollTop += delta; return; }
                sp = sp.parentElement;
            }
            window.scrollBy(0, delta);
        }""",
        top,
    )
    page.wait_for_timeout(250)


class Flow:
    """Drives the real UI. `human=True` moves a drawn cursor and types at typing speed."""

    def __init__(self, page, app: str, human: bool) -> None:
        self.page = page
        self.app = app
        self.human = human
        self.marks: dict[str, float] = {}

    def mark(self, name: str) -> None:
        self.marks[name] = time.monotonic()

    def pause(self, ms: int) -> None:
        if self.human:
            self.page.wait_for_timeout(ms)

    def click(self, locator) -> None:
        if self.human:
            x0, y0, x1, y1 = box(locator)
            self.page.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=28)
            self.page.wait_for_timeout(180)
            self.page.mouse.down()
            self.page.wait_for_timeout(70)
            self.page.mouse.up()
            self.page.wait_for_timeout(220)
        else:
            locator.click()

    def type(self, locator, text: str, clear: bool = False) -> None:
        self.click(locator)
        if self.human:
            if clear:
                locator.press("Meta+a")
            locator.press_sequentially(text, delay=38)
            self.page.wait_for_timeout(250)
        else:
            locator.fill(text)  # fill() replaces whatever is there

    # --- the steps ---
    def open_new_invoice(self) -> None:
        p = self.page
        p.goto(f"{self.app}/invoices", wait_until="domcontentloaded")
        p.wait_for_timeout(700)
        self.mark("list")
        self.pause(900)
        self.click(p.get_by_role("link", name=re.compile(r"New invoice", re.I)).first)
        p.wait_for_url(re.compile(r"/invoices/new"), wait_until="domcontentloaded")
        p.wait_for_timeout(600)
        self.mark("editor")

    def fill_details(self) -> None:
        p = self.page
        self.type(p.locator("input[name=title]"), JOB["title"])
        # Payment terms and the client are custom selects: open the trigger, choose the row.
        terms = p.locator(".custom-select-wrap", has=p.locator("#payment-terms-select"))
        self.click(terms.locator(".custom-select-trigger"))
        p.wait_for_timeout(250)
        self.click(terms.locator(".custom-select-option", has_text=re.compile(r"^Net 30$")).first)
        p.wait_for_timeout(300)
        self.click(p.locator("#client-selector .custom-select-trigger"))
        p.wait_for_timeout(300)
        self.click(p.locator("#client-selector .custom-select-option", has_text=JOB["client"]).first)
        p.wait_for_timeout(500)
        self.pause(600)

    def fill_items(self) -> None:
        p = self.page
        heading = p.locator("h3.section-label", has_text=re.compile("line items", re.I)).first
        if self.human:
            # a visible scroll rather than a jump
            p.mouse.wheel(0, 640)
            p.wait_for_timeout(500)
        else:
            scroll_editor_to(p, heading)
        desc, rate = JOB["items"][0]
        self.type(p.locator("input[name=desc_0]"), desc)
        self.type(p.locator("input[name=rate_0]"), rate, clear=True)
        p.locator("input[name=rate_0]").press("Tab")  # blur → the app formats 450 as 450.00
        self.click(p.get_by_role("button", name=re.compile(r"Add Line Item", re.I)))
        p.wait_for_timeout(300)
        desc, rate = JOB["items"][1]
        self.type(p.locator("input[name=desc_1]"), desc)
        self.type(p.locator("input[name=rate_1]"), rate, clear=True)
        p.locator("input[name=rate_1]").press("Tab")
        self.pause(400)

    def fill_note(self) -> None:
        p = self.page
        notes = p.locator("textarea[name=notes]")
        if self.human:
            p.mouse.wheel(0, 500)
            p.wait_for_timeout(400)
        notes.evaluate("el => el.scrollIntoView({block: 'center'})")
        # The demo profile has this text as its default note, so the field is
        # usually pre-filled; only type it when it isn't.
        if notes.input_value().strip() != JOB["note"]:
            self.type(notes, JOB["note"], clear=True)
        self.pause(400)

    def create(self) -> int:
        p = self.page
        btn = p.get_by_role("button", name=re.compile(r"Create Invoice", re.I))
        btn.evaluate("el => el.scrollIntoView({block: 'center'})")
        p.wait_for_timeout(200)
        self.click(btn)
        p.wait_for_url(re.compile(r"/invoices/(\d+)$"), wait_until="domcontentloaded")
        p.wait_for_timeout(900)
        self.mark("preview")
        m = re.search(r"/invoices/(\d+)$", p.url)
        assert m, p.url
        if self.human:
            # rest on the PDF button, the natural next click
            x0, y0, x1, y1 = box(p.get_by_role("link", name="PDF"))
            p.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=30)
            p.wait_for_timeout(1800)
        self.mark("end")
        return int(m.group(1))


def main() -> int:
    ap = argparse.ArgumentParser()
    # localhost, not 127.0.0.1: the app redirects 127.0.0.1 → localhost to keep
    # its session cookie on one origin, and a redirected POST (the delete at the
    # end) would arrive as a GET.
    ap.add_argument("--app", default="http://localhost:50505")
    ap.add_argument("--out", default="assets/screenshots")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--user", default="Daniel (Google, active)")
    ap.add_argument("--video", default=None, help="directory for the raw .webm recording (video pass instead of stills)")
    ap.add_argument("--theme", choices=("dark", "light"), default="dark", help="app theme for the video pass (stills always do both)")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    profile = pathlib.Path(args.profile)
    video_dir = pathlib.Path(args.video) if args.video else None
    if video_dir:
        video_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx_kwargs = dict(viewport=VIEWPORT, device_scale_factor=2, color_scheme=args.theme)
        if video_dir:
            ctx_kwargs.update(record_video_dir=str(video_dir), record_video_size={"width": 1440, "height": 900}, device_scale_factor=1)
        ctx = browser.new_context(**ctx_kwargs)
        page = ctx.new_page()
        if video_dir:
            page.add_init_script(CURSOR_JS)
        t0 = time.monotonic()

        # --- mock sign-in (DEV mode only) ---
        page.goto(f"{args.app}/login", wait_until="networkidle")
        sel = page.locator("#test-user-select")
        if sel.count() == 0:
            print("no dev login dropdown — is the app running in DEV mode?", file=sys.stderr)
            return 2
        sel.select_option(label=args.user)
        page.get_by_role("button", name="Sign in with Google").click()
        page.wait_for_url(lambda u: not u.rstrip("/").endswith("/login"), wait_until="commit")
        patch_session(profile)
        page.goto(f"{args.app}/", wait_until="domcontentloaded")
        page.get_by_text("Recent invoices").wait_for(timeout=15000)
        assert PERSONA["display_name"] in page.content(), "persona not shown — session patch failed"
        # The app remembers its theme per user; start from the one this pass wants
        # (dark for stills, which then toggle to light for their second frame).
        is_light = page.locator("html[data-theme='light']").count() > 0
        if is_light != (args.theme == "light"):
            page.get_by_role("button", name="Toggle theme").click()
            page.wait_for_timeout(300)

        def toggle_theme() -> None:
            page.get_by_role("button", name="Toggle theme").click()
            page.wait_for_timeout(400)

        def both_themes(name: str, crop_box_fn=None) -> None:
            page.screenshot(path=str(out / f"{name}-dark.png"), type="png")
            if crop_box_fn:
                crop_png(out / f"{name}-dark.png", crop_box_fn(), out / f"{name}-m-dark.png")
            toggle_theme()
            page.screenshot(path=str(out / f"{name}-light.png"), type="png")
            if crop_box_fn:
                crop_png(out / f"{name}-light.png", crop_box_fn(), out / f"{name}-m-light.png")
            toggle_theme()

        flow = Flow(page, args.app, human=bool(video_dir))
        invoice_id = None
        try:
            flow.open_new_invoice()
            flow.fill_details()
            if not video_dir:
                # Frame 1: the top of the editor — tabs, number, title, date, terms, the client.
                scroll_editor_top(page)

                def details_crop():
                    label = box(page.locator("h3.section-label").first)
                    title = box(page.locator("input[name=title]"))
                    due = box(page.locator("#date-due-input"))
                    return (label[0], label[1], title[2], due[3])

                both_themes("create-1-details", details_crop)

            flow.fill_items()
            flow.fill_note()
            if not video_dir:
                # Frame 2: the line items, totals and note, at the shorter viewport.
                page.set_viewport_size(ITEMS_VIEWPORT)
                heading = page.locator("h3.section-label", has_text=re.compile("line items", re.I)).first
                scroll_editor_to(page, heading, top=24)

                def items_crop():
                    h = box(heading)
                    table = box(page.locator("table.line-items-table"))
                    qty = box(page.locator("table.line-items-table th.col-qty"))
                    return (table[0], h[1], qty[2] + 8, min(table[3] + 56, ITEMS_VIEWPORT["height"] - 8))

                both_themes("create-2-items", items_crop)
                page.set_viewport_size(VIEWPORT)

            invoice_id = flow.create()
            if not video_dir:
                # Frame 3: the finished invoice in the app, with PDF / Email Invoice.
                def preview_crop():
                    # The rendered invoice card, from its top through the date / due /
                    # balance strip, left 62% (INVOICE, number, title, the three boxes).
                    card = box(page.locator(".card.invoice-preview").first)
                    grid = page.locator(".modern-detail-grid")
                    strip = box(grid.first) if grid.count() else (card[0], card[1], card[2], card[1] + (card[3] - card[1]) * 0.4)
                    return (card[0], card[1], card[0] + (card[2] - card[0]) * 0.62, strip[3])

                both_themes("create-3-preview", preview_crop)
        finally:
            if invoice_id is not None:
                r = ctx.request.post(f"{args.app}/invoices/{invoice_id}/delete")
                print("deleted the captured invoice:", invoice_id, r.status)
            if video_dir:
                marks = {k: round(v - t0, 2) for k, v in flow.marks.items()}
                (video_dir / "marks.json").write_text(json.dumps(marks, indent=1))
                print("segment marks (s from recording start):", marks)
            page.close()
            ctx.close()
            browser.close()

    if video_dir:
        for f in sorted(video_dir.glob("*.webm")):
            print("raw recording:", f, f.stat().st_size // 1024, "KB")
    else:
        for f in sorted(out.glob("create-*.png")):
            print("wrote", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
