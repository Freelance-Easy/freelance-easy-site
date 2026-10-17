"""Dev-flag probe (C8): the two opt-in URL flags stay opt-in.

  /?ci-tune          C7's overlay loads (#ci-tune present, tuning panel in view) and is INVISIBLE without the flag
                     (no #ci-tune, no request for checkpoint-tune.js);
  /?ci-dip=fade|seam FLICKER2's prototypes load with no console error and no page error; the default "/" (and an unknown
                     value) has no held-frame element: FLICKER2 stays opt-in until Daniel picks. A held frame is the inert
                     clone of `.stage-wrap` that holdFrame() adds after the stage (it lives ~0.25 s, only with the flag).
Usage: flags_probe.py http://127.0.0.1:<port>
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from _common import Report, base_url, run_main  # noqa: E402

# the held frame (site.js holdFrame) is an inert clone of .stage-wrap inserted after the stage: more than one .stage-wrap
HELD = "() => document.querySelectorAll('.stage-wrap').length - 1"


def load(browser, url):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    errs, reqs = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" and "404" not in m.text else None)
    page.on("request", lambda r: reqs.append(r.url))
    page.goto(url, wait_until="load")
    page.wait_for_function("() => window.FEStory && FEStory.state().phase === 'rest'", timeout=25000)
    return ctx, page, errs, reqs


def main() -> int:
    base, rep = base_url(), Report("flags")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx, page, errs, reqs = load(browser, base + "/?ci-tune")
        try:
            page.wait_for_selector("#ci-tune", timeout=8000)
            rep.check(page.locator("#ci-tune").is_visible(), "/?ci-tune: the overlay loads and shows")
            rep.check(any("checkpoint-tune" in u for u in reqs), "/?ci-tune: checkpoint-tune.js was requested")
            rep.check(not errs, "/?ci-tune: no console/page error", errs[:3])
        finally:
            ctx.close()
        ctx, page, errs, reqs = load(browser, base + "/")
        try:
            page.wait_for_timeout(800)
            rep.check(page.locator("#ci-tune").count() == 0 and not any("checkpoint-tune" in u for u in reqs),
                      "/: no overlay and no request for it without the flag", [u for u in reqs if "tune" in u])
            rep.check(page.evaluate(HELD) == 0, "/: no held-frame element by default", page.evaluate(HELD))
            page.keyboard.press("ArrowDown")                      # mid-content skip would be the held frame's trigger
            page.wait_for_timeout(300)
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(500)
            rep.check(page.evaluate(HELD) == 0, "/: still none after two quick steps", page.evaluate(HELD))
        finally:
            ctx.close()
        for flag in ("fade", "seam"):
            ctx, page, errs, _ = load(browser, f"{base}/?ci-dip={flag}")
            try:
                page.mouse.move(700, 450)
                page.keyboard.press("ArrowDown")
                page.wait_for_function("() => FEStory.state().dest === 1", timeout=5000)
                page.wait_for_timeout(1200)                      # into Templates' content, then skip it with a step
                page.keyboard.press("ArrowDown")
                page.wait_for_timeout(1500)
                rep.check(not errs, f"/?ci-dip={flag}: loads and steps with no console/page error", errs[:3])
                rep.check(page.evaluate("() => FEStory.state().dest") >= 1, f"/?ci-dip={flag}: the story moved")
            finally:
                ctx.close()
        browser.close()
    return rep.finish()


if __name__ == "__main__":
    sys.exit(run_main(main))
