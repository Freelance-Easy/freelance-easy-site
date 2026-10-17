"""Dev-flag probe (C8): the opt-in URL flag stays opt-in; the content skip is the crossfade (FADEDEF).

  /?ci-tune          C7's overlay loads (#ci-tune present, tuning panel in view) and is INVISIBLE without the flag
                     (no #ci-tune, no request for checkpoint-tune.js);
  /                  (FADEDEF: ?ci-dip is gone) no held-frame element at rest; a Look content skip holds a frame (the
                     crossfade) and never sets `dip`; none left after the crossfade ends. A held frame is the inert clone
                     of `.stage-wrap` that holdFrame() adds after the stage (it lives 0.22 s).
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
            rep.check(page.evaluate(HELD) == 0, "/: no held-frame element at rest", page.evaluate(HELD))
            page.mouse.move(700, 450)
            page.keyboard.press("ArrowDown")
            # wait for the LANDING (rendered === dest === 1), not the step's start: dest flips at the seam's start, and a
            # second step during the seam extends the run instead of skipping content (main, 2026-10-17)
            page.wait_for_function("() => { const s = FEStory.state(); return s.dest === 1 && s.rendered === 1; }",
                                   timeout=8000)
            page.wait_for_timeout(1200)                          # into Templates' content (it runs ~5 s), then skip it
            page.evaluate("""() => { window.__held = 0; window.__dip = 0; new MutationObserver(() => { window.__held = Math.max(
              window.__held, document.querySelectorAll('.stage-wrap').length - 1); }).observe(document.body, { childList: true, subtree: true });
              const tick = () => { if (FEStory.state().dip) window.__dip++; if (window.__dip >= 0) requestAnimationFrame(tick); };
              requestAnimationFrame(tick); }""")
            still = page.evaluate("() => FEStory.state().phase")
            rep.check(still != "rest", "/: precondition, Templates' content is still playing", still)
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(1500)
            # FADEDEF (Daniel picked fade, 2026-10-17): decision #13's content skip is the crossfade by default
            rep.check(page.evaluate("() => window.__held") >= 1, "/: the content skip held a frame (the crossfade ran)",
                      page.evaluate("() => window.__held"))
            rep.check(page.evaluate("() => window.__dip") == 0, "/: the content skip never set dip (no dark frame)",
                      page.evaluate("() => window.__dip"))
            rep.check(page.evaluate(HELD) == 0, "/: no held-frame element after the crossfade ends", page.evaluate(HELD))
            rep.check(not errs, "/: steps and skips with no console/page error", errs[:3])
            rep.check(page.evaluate("() => FEStory.state().dest") >= 2, "/: the story moved on")
        finally:
            ctx.close()
        browser.close()
    return rep.finish()


if __name__ == "__main__":
    sys.exit(run_main(main))
