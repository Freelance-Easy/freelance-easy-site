"""Shared plumbing for the M1 probes (C8). Every probe: `uv run --with playwright python3 <probe>.py <url>`.

Probes are read-only: they drive REAL input (keyboard, mouse) and read state through window.FEStory.state() /
onLand and plain DOM reads. They never write site state through evals (no goTo, no history calls).

A probe prints one `  ok|FAIL <what>` line per check and a last line `PROBE <name>: PASS (n checks)` or
`PROBE <name>: FAIL (k of n)`; it exits 0 only when every check passed. It never serves anything: the URL is given.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request

SLUGS = {"make": "new-invoice", "look": "templates", "know": "invoices", "grow": "dashboard", "chase": "email",
         "yours": "your-data", "price": "price", "note": "a-note", "end": "get-the-app"}
# docs/interaction-contract.md § ICX-DEST: the pinned set per mode, in beat order
PINNED = {
    "desktop": ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"],
    "tablet": ["make", "look", "know", "grow", "chase"],
    "phone": ["make", "look", "know", "grow", "chase", "yours", "end"],
}
# mode -> (width, height, touch): the three modes the contract names (tablet 820, phone 390x664)
MODES = {"desktop": (1440, 900, False), "tablet": (820, 1180, False), "phone": (390, 664, True)}

REST_JS = """() => { const F = window.FEStory; if (!F) return false; const s = F.state();
  return s.phase === 'rest' && s.rendered === s.dest; }"""


def base_url() -> str:
    if len(sys.argv) < 2 or not sys.argv[1].startswith("http"):
        sys.exit("usage: <probe>.py http://127.0.0.1:<port>")
    return sys.argv[1].rstrip("/")


def resolve(base: str, path: str) -> str:
    """A page URL on `base`: the clean path if the server has it, else path + .html (a plain static server)."""
    if path == "/" or path.endswith("/"):
        return base + path
    for cand in (path, path + ".html"):
        try:
            with urllib.request.urlopen(base + cand, timeout=10):
                return base + cand
        except urllib.error.HTTPError:
            continue
    return base + path


class Report:
    def __init__(self, name: str):
        self.name, self.n, self.bad = name, 0, 0

    def check(self, cond, what: str, detail=None) -> bool:
        self.n += 1
        if cond:
            print(f"  ok   {what}")
            return True
        self.bad += 1
        print(f"  FAIL {what}" + (f" -- {detail}" if detail is not None else ""))
        return False

    def finish(self) -> int:
        if self.bad:
            print(f"PROBE {self.name}: FAIL ({self.bad} of {self.n})")
            return 1
        print(f"PROBE {self.name}: PASS ({self.n} checks)")
        return 0


def story_context(browser, mode: str, *, theme: str = "dark"):
    w, h, touch = MODES[mode]
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch,
                              reduced_motion="no-preference")
    ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{theme}')}}catch(e){{}}")
    return ctx


def open_story(browser, base: str, mode: str, *, theme: str = "dark", path: str = "/"):
    """A fresh page on the homepage story, resting on its first checkpoint, with onLand recorded in window.__lands."""
    ctx = story_context(browser, mode, theme=theme)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(base + path, wait_until="load")
    try:
        page.wait_for_function("() => window.FEStory && window.FEStory.state().phase !== undefined", timeout=15000)
    except Exception:  # noqa: BLE001 - a scrub-era build has no FEStory: that is a FAIL line, not a traceback
        has = page.evaluate("() => ({ FEStory: typeof window.FEStory, site: typeof window.__site })")
        print(f"  FAIL {mode}: window.FEStory is absent (this build is not the checkpoint engine) -- {has}")
        print(f"PROBE {sys.argv[0].rsplit('/', 1)[-1].removesuffix('_probe.py')}: FAIL (build has no FEStory)")
        ctx.close()
        sys.exit(1)
    page.evaluate("""() => { window.__lands = [];
      FEStory.onLand((e) => { window.__lands.push({index: e.index, beat: e.beat, slug: e.slug, source: e.source, final: e.final}); }); }""")
    wait_rest(page, 25000)
    w, h, _ = MODES[mode]
    page.mouse.move(w / 2, h / 2)
    return ctx, page, errors


def wait_rest(page, timeout: int = 20000) -> None:
    page.wait_for_function(REST_JS, timeout=timeout, polling=50)


def step(page, key: str, dest: int, timeout: int = 20000) -> None:
    """One real key press, then wait until the engine's dest is `dest` and it is resting there."""
    page.keyboard.press(key)
    page.wait_for_function("(d) => window.FEStory.state().dest === d", arg=dest, timeout=5000, polling=25)
    wait_rest(page, timeout)


BEATS = ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"]


def scrub_step(page, beat: str, dest: int, timeout: int = 20000) -> None:
    """(SCRUB stage 3) a scrub build (a phone, a touch tablet) has no key steps: a key scrolls the page natively
    (ICX-SCRUB.1). The reader's scroll stops on the checkpoint's hold (its landing pixel, __site.scrollFor); wait until it
    has landed there (ICX-SCRUB.5)."""
    # (the engine's own jump pixel, site.js trackY: the first checkpoint's is the story's top)
    page.evaluate("(b) => window.scrollTo(0, b === 'make' ? Math.max(0, Math.round(__site.map().storyTop)) : __site.scrollFor(b))", beat)
    page.wait_for_function("(d) => window.FEStory.state().dest === d", arg=dest, timeout=8000, polling=25)
    wait_rest(page, timeout)


def walk(page, mode: str, on_rest) -> list[str]:
    """Step forward through every pinned checkpoint of `mode` with ArrowDown, then back with ArrowUp (a scrub build:
    scroll_step, the scroll stopping on each hold). After each rest calls on_rest(direction, beat, state) with
    FEStory.state(). Returns the beats walked, in order."""
    seq = PINNED[mode]
    scrub = page.evaluate("() => !!(window.__site && __site.map().scrub)")
    walked: list[str] = []
    for i in range(1, len(seq)):
        if scrub:
            scrub_step(page, seq[i], BEATS.index(seq[i]))
        else:
            step(page, "ArrowDown", BEATS.index(seq[i]))
        walked.append(seq[i])
        on_rest("fwd", seq[i], page.evaluate("() => FEStory.state()"))
    for i in range(len(seq) - 2, -1, -1):
        if scrub:
            scrub_step(page, seq[i], BEATS.index(seq[i]))
        else:
            step(page, "ArrowUp", BEATS.index(seq[i]))
        walked.append(seq[i])
        on_rest("back", seq[i], page.evaluate("() => FEStory.state()"))
    return walked


def run_main(main) -> int:
    """Run a probe's main(); an unexpected error (e.g. a selector the build lacks) is a FAIL line, not a bare traceback."""
    try:
        return main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        first = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
        print(f"  FAIL probe error -- {type(e).__name__}: {first}")
        print(f"PROBE {sys.argv[0].rsplit('/', 1)[-1].removesuffix('_probe.py')}: FAIL (error)")
        return 1
