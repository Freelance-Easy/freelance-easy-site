"""Order probe (C8, the checkpoint rewrite of premium-pass order_probe.py).

The old probe counted scrub SEGMENTS played ("15/15, 0 dips") under fast wheel scrolls. The story is checkpoints now, so
this one walks every checkpoint instead, in every mode, with real key presses (ArrowDown / ArrowUp), and asserts the
contract's destination table (docs/interaction-contract.md § ICX-DEST) from FEStory.state() / onLand:
  - FEStory.mode is the mode asked for, and its pinned destinations are exactly the table's, in beat order, with the
    table's slugs (ICX-DEST.1/.2);
  - forward: each ArrowDown rests on the next checkpoint (phase "rest", rendered == dest == i, the caption's beat is
    that checkpoint's, scrollY within 1 px of trackY: ICX-CHECKPOINT.2), the URL is that slug's (plain "/" for the first,
    ICX-HIST.5) and history.length never grows for a step (ICX-HIST.1);
  - back: each ArrowUp rests on the previous one (ICX-BACK.1), same assertions;
  - onLand's FINAL landings, in order, are exactly the checkpoints walked (a step writes/announces only its final
    landing; no checkpoint is skipped, none is repeated: ICX-SIGNED.6), and the page logged no console error.
Modes: desktop 1440x900, tablet 820x1180, phone 390x664 (touch). Usage: order_probe.py http://127.0.0.1:<port>
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from _common import BEATS, MODES, PINNED, SLUGS, Report, base_url, open_story, walk, run_main  # noqa: E402


def main() -> int:
    base, rep = base_url(), Report("order")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for mode in MODES:
            ctx, page, errors = open_story(browser, base, mode)
            try:
                seq = PINNED[mode]
                got = page.evaluate("() => ({mode: FEStory.mode, dests: FEStory.destinations.filter(d => d.kind === 'pinned')"
                                    ".map(d => [d.beat, d.slug])})")
                rep.check(got["mode"] == mode, f"{mode}: FEStory.mode", got["mode"])
                rep.check(got["dests"] == [[b, SLUGS[b]] for b in seq], f"{mode}: pinned destinations = the table",
                          got["dests"])
                h0 = page.evaluate("() => history.length")
                first = page.evaluate("() => FEStory.state()")
                rep.check(first["rendered"] == first["dest"] == 0 and first["beat"] == "make",
                          f"{mode}: starts at rest on New invoice", first)
                page.evaluate("() => { window.__lands = []; }")

                def on_rest(direction, beat, st):
                    i = BEATS.index(beat)
                    where = f"{mode} {direction} {SLUGS[beat]}"
                    rep.check(st["phase"] == "rest" and st["rendered"] == st["dest"] == i,
                              f"{where}: rest, rendered == dest == {i}", st)
                    rep.check(st["beat"] == beat, f"{where}: caption beat is {beat}", st["beat"])
                    rep.check(st["trackY"] is not None and abs(page.evaluate("() => scrollY") - st["trackY"]) <= 1,
                              f"{where}: scrollY on the track position", st["trackY"])
                    want = "" if beat == "make" else "#" + SLUGS[beat]
                    # the write follows the landing by a moment on a back step (the dip's cut): poll, bounded
                    try:
                        page.wait_for_function("(w) => location.hash === w", arg=want, timeout=1500)
                    except Exception:
                        pass  # the check below reports it
                    loc = page.evaluate("() => [location.pathname, location.hash, history.length]")
                    rep.check(loc[1] == want and loc[2] == h0, f"{where}: URL {want or '/'} and history unchanged", loc)

                walked = walk(page, mode, on_rest)
                finals = page.evaluate("() => __lands.filter(l => l.final).map(l => l.beat)")
                rep.check(finals == walked, f"{mode}: final landings = the checkpoints walked, in order", finals)
                # a plain static server has no worker, so /js/script.js is a 404: that one request is not a page error
                errs = [e for e in errors if "404" not in e]
                rep.check(not errs, f"{mode}: no console error", errs[:3])
            finally:
                ctx.close()
        browser.close()
    return rep.finish()


if __name__ == "__main__":
    sys.exit(run_main(main))
