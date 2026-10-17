"""Caption-at-rest sweep (C8; FUZZ's caption bug was found on desktop only).

At 820 (tablet) and 390x664 (phone), step FORWARD through every pinned checkpoint and then BACKWARD (real ArrowDown /
ArrowUp). At each rest the caption shown must be that checkpoint's own: FEStory.state().beat is the checkpoint, and in
the DOM exactly one `.captions .beat-copy` is not idle, it is `data-copy=<checkpoint>` (the phone's Your data caption is `yours-cap`), and it has text (ICX-CHECKPOINT.2:
no empty caption, no neighbour's). Usage: caption_probe.py http://127.0.0.1:<port>
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from _common import Report, SLUGS, base_url, open_story, walk, run_main  # noqa: E402

SHOWN = """() => [...document.querySelectorAll('.captions .beat-copy')].filter(e => !e.classList.contains('is-idle'))
  .map(e => [e.dataset.copy, e.textContent.trim().length])"""


def main() -> int:
    base, rep = base_url(), Report("caption")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for mode in ("tablet", "phone"):
            ctx, page, _ = open_story(browser, base, mode)
            try:
                def on_rest(direction, beat, st):
                    page.wait_for_timeout(150)                      # a caption's own fade settles
                    shown = page.evaluate(SHOWN)
                    rep.check(st["beat"] == beat and len(shown) == 1 and shown[0][0] in (beat, beat + "-cap") and shown[0][1] > 0,
                              f"{mode} {direction} {SLUGS[beat]}: its own caption shows", {"state": st["beat"], "dom": shown})

                first = page.evaluate(SHOWN)
                rep.check([s[0] for s in first] == ["make"] and first[0][1] > 0, f"{mode}: New invoice caption at the start", first)
                walk(page, mode, on_rest)
            finally:
                ctx.close()
        browser.close()
    return rep.finish()


if __name__ == "__main__":
    sys.exit(run_main(main))
