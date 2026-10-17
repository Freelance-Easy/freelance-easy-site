"""Theme probe (C8; replaces the stale premium-pass site_theme_probe.py, which clicked the retired [data-set-theme] pill
on the :8821 prototype). It asserts the A5 theme contract on the live pages, from plain reads and one real click each:
  - data-theme is explicit ("dark" | "light") on load and after every switch, never absent (FETheme.init);
  - ONE [data-theme-toggle] button in the bar; a real click flips data-theme, stores it (localStorage fe-theme) and fires
    fe:themechange with the new theme (document and window);
  - the circle reveal cleans up: no html.vt-theme, no --vt-x/--vt-y left behind;
  - the toggle never writes the URL: location.hash and history.length unchanged (ICX-HIST.4);
  - on the homepage the story is undisturbed: still resting on the same checkpoint with the same dest;
  - reduced motion: the flip is synchronous (instant), no reveal.
Pages: "/" (1440 and 390) and "/tour/" (1440). Latency/duration of the circle is scripts/checks/check_theme_reveal.py's
(run by tests/theme). Usage: theme_probe.py http://127.0.0.1:<port>
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from _common import Report, base_url, run_main  # noqa: E402

TOGGLE = "[data-theme-toggle]"
WATCH = """() => { window.__tc = []; for (const t of [document, window]) t.addEventListener('fe:themechange',
  (e) => window.__tc.push(e.detail && e.detail.theme)); }"""
STATE = """() => ({ theme: document.documentElement.getAttribute('data-theme'), stored: localStorage.getItem('fe-theme'),
  vt: document.documentElement.classList.contains('vt-theme'),
  vars: [document.documentElement.style.getPropertyValue('--vt-x'), document.documentElement.style.getPropertyValue('--vt-y')],
  hash: location.hash, hist: history.length, ev: window.__tc || [],
  story: window.FEStory ? [FEStory.state().phase, FEStory.state().dest, FEStory.state().rendered] : null })"""

CELLS = [("/", 1440, 900, False), ("/", 390, 844, False), ("/tour/", 1440, 900, False), ("/", 1440, 900, True)]


def main() -> int:
    base, rep = base_url(), Report("theme")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for path, w, h, reduced in CELLS:
            tag = f"{path} {w}{' reduced-motion' if reduced else ''}"
            ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme="dark",
                                      reduced_motion="reduce" if reduced else "no-preference")
            page = ctx.new_page()
            try:
                page.goto(base + path, wait_until="load")
                if path == "/":
                    page.wait_for_function("() => window.FEStory && FEStory.state().phase === 'rest'", timeout=25000)
                page.evaluate(WATCH)
                rep.check(page.locator(TOGGLE).count() == 1, f"{tag}: exactly one theme toggle", page.locator(TOGGLE).count())
                before = page.evaluate(STATE)
                rep.check(before["theme"] in ("dark", "light"), f"{tag}: data-theme explicit on load", before["theme"])
                prev = before["theme"]
                for n in range(2):                                  # both directions
                    page.click(TOGGLE)
                    if reduced:
                        now = page.evaluate(STATE)                  # no wait: instant means synchronous
                    else:
                        page.wait_for_function("() => !document.documentElement.classList.contains('vt-theme')", timeout=3000)
                        now = page.evaluate(STATE)
                    want = "light" if prev == "dark" else "dark"
                    rep.check(now["theme"] == want, f"{tag}: click {n + 1} flips {prev} -> {want}", now["theme"])
                    rep.check(now["stored"] == want, f"{tag}: click {n + 1} stores fe-theme", now["stored"])
                    rep.check(now["ev"][-1:] == [want] * 1 and len(now["ev"]) == 2 * (n + 1),
                              f"{tag}: click {n + 1} fires fe:themechange on document and window", now["ev"])
                    if not reduced:
                        rep.check(not now["vt"] and now["vars"] == ["", ""], f"{tag}: click {n + 1} reveal cleaned up", now)
                    rep.check(now["hash"] == before["hash"] and now["hist"] == before["hist"],
                              f"{tag}: click {n + 1} writes no URL, no history", [now["hash"], now["hist"]])
                    rep.check(now["story"] == before["story"], f"{tag}: click {n + 1} leaves the story on its checkpoint",
                              [before["story"], now["story"]])
                    prev = want
            finally:
                ctx.close()
        browser.close()
    return rep.finish()


if __name__ == "__main__":
    sys.exit(run_main(main))
