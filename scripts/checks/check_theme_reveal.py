#!/usr/bin/env python3
"""check_theme_reveal.py <url> [--toggle <sel>] [--width W ...] [--browser chromium|webkit]

Checks a page's FETheme circle reveal (A5; reused by A6, A7, A8 and C8). For each width (default 1440 and 390) it
loads <url> in a fresh profile and clicks the toggle twice, so both directions are covered, then once more under
prefers-reduced-motion. Each reveal must:
  - run one animation of --vt-r on ::view-transition-new(root) for 420 ms with cubic-bezier(.55,0,.25,1);
  - reach full radius 420 +/- 40 ms after it starts (measured on the document timeline);
  - be centred on the toggle's centre (+/- 1.5 px);
  - end at a radius that clears the farthest viewport corner plus the feather (22% of the radius, 48-220 px);
  - leave data-theme flipped and explicit, and clean up (no html.vt-theme, no --vt-x / --vt-y).
Under reduced motion the switch must be instant (flipped synchronously on click, no reveal animation).
Prints one line per check and "ALL PASS (N checks)"; exits 0 only if every check passes.

  uv run --with playwright python3 scripts/checks/check_theme_reveal.py http://127.0.0.1:8803/tests/fixtures/theme/
"""
from __future__ import annotations

import argparse
import math
import sys
import urllib.parse

DURATION_MS = 420
TOLERANCE_MS = 40
EASING = "cubic-bezier(0.55, 0, 0.25, 1)"
CENTRE_TOLERANCE_PX = 1.5
HEIGHTS = {1440: 900, 390: 844}
PRODUCTION_HOSTS = ("freelance-easy.com",)

# Clicks the toggle and follows the reveal frame by frame. Times are ms after the click (performance.now() and the
# document timeline share an origin).
PROBE_JS = r"""
async (sel) => {
  const root = document.documentElement;
  const btn = document.querySelector(sel);
  if (!btn) return { error: `no toggle matches ${sel}` };
  btn.scrollIntoView({ block: "nearest" });
  const r = btn.getBoundingClientRect();
  const out = {
    before: root.getAttribute("data-theme"), cx: r.left + r.width / 2, cy: r.top + r.height / 2,
    vw: innerWidth, vh: innerHeight, samples: [], found: false,
  };
  const isReveal = (a) => a.effect && a.effect.pseudoElement === "::view-transition-new(root)" &&
    a.effect.getKeyframes().some((k) => "--vt-r" in k);
  const stale = new Set(document.getAnimations());   // a finished fill-forwards reveal may linger: not this one
  const t0 = performance.now();
  btn.click();
  out.syncAfterClick = root.getAttribute("data-theme");
  out.vtClassAfterClick = root.classList.contains("vt-theme");
  let anim = null;
  await new Promise((done) => {
    const tick = () => {
      const now = performance.now() - t0;
      if (!anim) {
        anim = document.getAnimations().find((a) => !stale.has(a) && isReveal(a)) || null;
        if (anim) {
          out.found = true;
          const t = anim.effect.getTiming();
          out.duration = t.duration;
          out.easing = t.easing;
          const kf = anim.effect.getKeyframes();
          out.r0 = parseFloat(kf[0]["--vt-r"]);
          out.rEnd = parseFloat(kf[kf.length - 1]["--vt-r"]);
          out.vtX = parseFloat(root.style.getPropertyValue("--vt-x"));
          out.vtY = parseFloat(root.style.getPropertyValue("--vt-y"));
          out.count = document.getAnimations().filter((a) => isReveal(a) && a.playState !== "finished").length;
          anim.finished.then(() => { out.finishedAt = performance.now() - t0; }, () => { out.cancelled = true; });
        }
      }
      if (anim) {
        const ct = anim.effect.getComputedTiming();
        let rpx = null;
        try { rpx = parseFloat(getComputedStyle(root, "::view-transition-new(root)").getPropertyValue("--vt-r")); }
        catch (e) { rpx = null; }
        out.samples.push({ t: now, cur: anim.currentTime, progress: ct.progress,
                           rpx: Number.isFinite(rpx) ? rpx : null });
      }
      const settled = anim && (out.finishedAt !== undefined || out.cancelled) && !root.classList.contains("vt-theme");
      if (now > 2500 || settled || (!anim && now > 600)) done(); else requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
  await new Promise((done) => setTimeout(done, 50));
  out.after = root.getAttribute("data-theme");
  out.vtClassAfter = root.classList.contains("vt-theme");
  out.vtVarsAfter = root.style.getPropertyValue("--vt-x") + root.style.getPropertyValue("--vt-y");
  return out;
}
"""


def feather(r: float) -> float:
    return min(220.0, max(48.0, r * 0.22))


def start_ms(p: dict) -> float | None:
    """When the circle started growing, ms after the click: each frame's time minus the animation's currentTime."""
    xs = sorted(s["t"] - s["cur"] for s in p.get("samples", [])
                if s.get("cur") is not None and 0 < s["cur"] < DURATION_MS + TOLERANCE_MS)
    return xs[len(xs) // 2] if xs else None


def growing(p: dict) -> list[dict]:
    """The frames up to the first one at full radius (after that the pseudo-element is torn down)."""
    out = []
    for s in p.get("samples", []):
        out.append(s)
        if (s.get("progress") or 0) >= 1 or (s.get("rpx") is not None and s["rpx"] >= p["rEnd"] - 0.5):
            break
    return out


def growth_ms(p: dict) -> float | None:
    """Start of growth to the first frame at full radius, in wall-clock ms (rAF granularity)."""
    g, start = growing(p), start_ms(p)
    if not g or start is None:
        return None
    last = g[-1]
    if not ((last.get("progress") or 0) >= 1 or (last.get("rpx") is not None and last["rpx"] >= p["rEnd"] - 0.5)):
        return None
    return last["t"] - start


def reveal_failures(p: dict) -> list[str]:
    """Why a probe of a reveal fails the A5 contract; [] when it passes."""
    if p.get("error"):
        return [p["error"]]
    bad: list[str] = []
    flipped = {"dark": "light", "light": "dark"}.get(p["before"])
    if flipped is None:
        bad.append(f"data-theme before the click is {p['before']!r}, not dark/light")
    if not p["found"]:
        return bad + ["no --vt-r animation on ::view-transition-new(root) (no circle reveal)"]
    if p.get("count") != 1:
        bad.append(f"{p.get('count')} reveal animations at once, expected 1")
    if p.get("duration") != DURATION_MS:
        bad.append(f"animation duration {p.get('duration')} ms, expected {DURATION_MS}")
    if p.get("easing") != EASING:
        bad.append(f"easing {p.get('easing')!r}, expected {EASING!r}")
    took = growth_ms(p)
    if p.get("finishedAt") is None or took is None:
        bad.append("the reveal never reached full radius")
    elif abs(took - DURATION_MS) > TOLERANCE_MS:
        bad.append(f"full radius after {took:.0f} ms, expected {DURATION_MS}+/-{TOLERANCE_MS}")
    if abs(p["vtX"] - p["cx"]) > CENTRE_TOLERANCE_PX or abs(p["vtY"] - p["cy"]) > CENTRE_TOLERANCE_PX:
        bad.append(f"circle centre ({p['vtX']}, {p['vtY']}) is not the toggle centre ({p['cx']:.1f}, {p['cy']:.1f})")
    far = math.hypot(max(p["cx"], p["vw"] - p["cx"]), max(p["cy"], p["vh"] - p["cy"]))
    need = far + feather(far)
    if p["r0"] != 0:
        bad.append(f"the circle starts at {p['r0']} px, not 0")
    if not p["rEnd"] >= need:
        bad.append(f"end radius {p['rEnd']:.1f} px does not clear the far corner + feather ({need:.1f} px)")
    rs = [s["rpx"] for s in growing(p) if s["rpx"] is not None]
    if any(b < a - 0.5 for a, b in zip(rs, rs[1:])):
        bad.append("the radius shrank during the reveal")
    if p["after"] != flipped:
        bad.append(f"data-theme after the reveal is {p['after']!r}, expected {flipped!r}")
    if p["vtClassAfter"] or p["vtVarsAfter"]:
        bad.append("html.vt-theme or --vt-x/--vt-y left behind after the reveal")
    return bad


def instant_failures(p: dict) -> list[str]:
    """Why a probe under reduced motion (or without view transitions) is not an instant switch."""
    if p.get("error"):
        return [p["error"]]
    flipped = {"dark": "light", "light": "dark"}.get(p["before"])
    bad: list[str] = []
    if p["syncAfterClick"] != flipped:
        bad.append(f"data-theme right after the click is {p['syncAfterClick']!r}, expected {flipped!r} (not instant)")
    if p["found"] or p["vtClassAfterClick"]:
        bad.append("a circle reveal ran where the switch must be instant")
    if p["after"] != flipped:
        bad.append(f"data-theme afterwards is {p['after']!r}, expected {flipped!r}")
    return bad


def probe(page, toggle: str) -> dict:
    return page.evaluate(PROBE_JS, toggle)


def describe(p: dict) -> str:
    if not p.get("found"):
        return f"{p.get('before')}->{p.get('after')} instant"
    took, start = growth_ms(p) or float("nan"), start_ms(p) or float("nan")
    return (f"{p['before']}->{p['after']}: full radius {took:.0f} ms after start (start {start:.0f} ms after "
            f"click), centre ({p['vtX']:.1f}, {p['vtY']:.1f}), end r {p['rEnd']:.1f} px")


def run(url: str, toggle: str, widths: list[int], browser_name: str) -> int:
    from playwright.sync_api import sync_playwright

    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in PRODUCTION_HOSTS):
        print(f"refusing production host {host}; point this at a local or preview server", file=sys.stderr)
        return 2
    passed = failed = 0

    def report(name: str, bad: list[str], p: dict) -> None:
        nonlocal passed, failed
        if bad:
            failed += 1
            print(f"FAIL {name}: " + "; ".join(bad))
        else:
            passed += 1
            print(f"PASS {name}: {describe(p)}")

    with sync_playwright() as pw:
        browser = getattr(pw, browser_name).launch()
        try:
            for w in widths:
                vp = {"width": w, "height": HEIGHTS.get(w, 900)}
                for reduced in (False, True):
                    ctx = browser.new_context(viewport=vp, reduced_motion="reduce" if reduced else "no-preference")
                    page = ctx.new_page()
                    page.goto(url, wait_until="load")
                    page.wait_for_timeout(300)
                    if reduced:
                        p = probe(page, toggle)
                        report(f"{w}px reduced-motion", instant_failures(p), p)
                    else:
                        for leg in ("first", "back"):
                            p = probe(page, toggle)
                            report(f"{w}px reveal {leg}", reveal_failures(p), p)
                            page.wait_for_timeout(150)
                    ctx.close()
        finally:
            browser.close()
    if failed:
        print(f"FAILED ({failed} of {passed + failed} checks)")
        return 1
    print(f"ALL PASS ({passed} checks)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("--toggle", default="[data-theme-toggle]", help="CSS selector of the theme toggle")
    ap.add_argument("--width", type=int, action="append", help="viewport width (repeatable; default 1440 and 390)")
    ap.add_argument("--browser", default="chromium", choices=("chromium", "webkit"))
    a = ap.parse_args(argv)
    return run(a.url, a.toggle, a.width or [1440, 390], a.browser)


if __name__ == "__main__":
    sys.exit(main())
