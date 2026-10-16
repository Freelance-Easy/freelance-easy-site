#!/usr/bin/env python3
"""The homepage story's step timing (C5, DEC-8; docs/interaction-contract.md ICX-STEP.2-.4).

For every step between two checkpoints (desktop 1440 and tablet 820, dark and light by default) it reports, in story
seconds (a step with no further input plays at 1x, ICX-STEP.6, so story seconds are wall seconds):

- transition: the gesture at REST(a) -> the end of the seam into b (b's entry);   ceiling 1.5 s (ICX-STEP.2)
- caption:    the gesture at REST(a) -> b's caption switches in;                   ceiling 0.7 s (ICX-STEP.3)
- content:    b's entry -> REST(b);                                                ceiling 5.0 s (ICX-STEP.4)
- the Ride (Grow -> Email) must stay 1.45 s +- 0.1 s.

A row over its ceiling is a FAIL unless it is a NAMED EXCEPTION below (each judged on frame strips, not by a number).

--activity also samples the stage frame by frame (window.__site.seekMaster at 60 fps of story time, a hash of every
inline style under the stage, field, band and overlay) and prints each segment's still spans >= 0.1 s: the dead time.
Exit 1 when any row fails.

  python3 scripts/checks/timing.py --url http://127.0.0.1:8813/
  python3 scripts/checks/timing.py --url 'http://127.0.0.1:8813/?pace=before' --activity
"""
from __future__ import annotations

import argparse
import json
import sys

LIMIT = {"transition": 1.5, "caption": 0.7, "content": 5.0}
RIDE = (1.45, 0.1)
# named exceptions, keyed by the INCOMING checkpoint (main's ruling 2026-10-15; contract ICX-STEP.2/.3)
EXCEPTIONS = {
    "transition": {
        "look": "Make->Look: the rest of Make's moving tail (the Create press, the PDF morph, the PDF press: 1.32 s dark, "
                "0.91 s light) plus the PDF->Look circle (1.26 s dark, untouched by DEC-8): no still frame left in it",
    },
    "caption": {
        "chase": "the Ride (1.39 s): 'Follow up in two clicks.' arrives once the band is the whole page (one clean colour "
                 "move, no text caught in it); earlier it would sit over the dive and the flood",
    },
    "content": {
        "chase": "Email (5.25 s): no typing; its still spans are cut 1.12 -> 0.34 s, and what is left is reading time: "
                 "'Email sent.' keeps a 0.20 s still hold (>= 0.5 s readable with its fades; main's ruling (b) 2026-10-16)",
    },
}
SIZES = {1440: (1440, 900), 820: (820, 1180), 390: (390, 664)}

# a hash of the stage's drawn state: every inline style under the stage, the field, the band and the overlay
SIG_JS = """
(([t0, t1, dt]) => {
  const roots = ['[data-stage=story]', '.stage-field', '.pin-band', '.pin-over', '.stage-shade']
    .map((s) => document.querySelector(s)).filter(Boolean);
  // (an element hidden by its own inline style, display none or opacity 0, is skipped with everything in it: a hand
  // still gliding under its finished fade is not motion anyone sees)
  const hidden = (st) => /display:\\s*none/.test(st) || /(^|;)\\s*opacity:\\s*0(\\.0+)?\\s*(;|$)/.test(st);
  const sig = () => {
    let h = 5381;
    const walk = (el) => {
      const st = el.getAttribute('style') || '';
      if (hidden(st)) { h = ((h * 33) ^ 48) >>> 0; return; }
      const s = st + (el.getAttribute('class') || '') + (el.children.length ? '' : el.textContent) + '|';
      for (let i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0;
      for (const c of el.children) walk(c);
    };
    for (const r of roots) walk(r);
    return h;
  };
  const out = [];
  for (let T = t0; T <= t1 + 1e-9; T += dt) { window.__site.seekMaster(T); out.push(sig()); }
  return out;
})
"""


def open_story(browser, url: str, width: int, theme: str):
    w, h = SIZES.get(width, (width, 900))
    touch = width < 640
    ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{theme}')}}catch(e){{}}")
    page = ctx.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_function("() => window.__site && window.__site.TL && window.__site.map().dests", timeout=15000)
    return ctx, page


def steps(m: dict) -> list[dict]:
    """One row per step a -> b between consecutive pinned checkpoints, from __site.map()."""
    pinned = [d for d in m["dests"] if d.get("kind") == "pinned"]
    rows = []
    for a, b in zip(pinned, pinned[1:]):
        sw = next((t for beat, t in m["switches"] if beat == b["beat"] and t >= a["rest"] - 1e-6), None)
        rows.append({
            "step": f"{a['beat']}->{b['beat']}", "to": b["beat"],
            "transition": round(b["entry"] - a["rest"], 3),
            "caption": None if sw is None else round(sw - a["rest"], 3),
            "content": round(b["rest"] - b["entry"], 3),
        })
    return rows


def verdicts(rows: list[dict]) -> list[str]:
    """Failures: a row over its ceiling with no named exception; the Ride outside 1.45 +- 0.1 s."""
    bad = []
    for r in rows:
        for k, lim in LIMIT.items():
            v = r[k]
            if v is None:
                bad.append(f"{r['step']}: no {k} switch found")
            elif v > lim + 1e-6 and r["to"] not in EXCEPTIONS[k]:
                bad.append(f"{r['step']}: {k} {v:.2f} s > {lim} s")
        if r["to"] == "chase" and abs(r["transition"] - (RIDE[0] + 0.02)) > RIDE[1]:
            bad.append(f"{r['step']}: the Ride {r['transition']:.2f} s, not {RIDE[0]} +- {RIDE[1]} s")
    return bad


def activity(page, t0: float, t1: float, fps: int = 60) -> list[int]:
    return page.evaluate(SIG_JS, [t0, t1, 1 / fps])


def still_spans(m: dict, sigs: list[int], fps: int = 60, min_s: float = 0.1) -> list[tuple[str, float, float]]:
    """(segment id, local start, local end) of every still span >= min_s (no stage change between frames)."""
    out = []
    for s in m["segs"]:
        i0, i1 = round(s["T0"] * fps), round(s["T1"] * fps)
        run0 = None
        for i in range(i0 + 1, min(i1, len(sigs) - 1) + 1):
            same = sigs[i] == sigs[i - 1]
            if same and run0 is None:
                run0 = i - 1
            if (not same or i == i1) and run0 is not None:
                end = i if same else i - 1
                if (end - run0) / fps >= min_s:
                    out.append((s["id"], round(run0 / fps - s["T0"], 3), round(end / fps - s["T0"], 3)))
                run0 = None
    return out


def moving_frames(page, m: dict, fps: int = 60) -> dict[str, int]:
    """Per segment: how many frames (1/fps of story, sampled from the segment's own start) differ from the frame before.
    Cutting still time leaves this count as it was; playing a move faster lowers it, slower raises it."""
    out = {}
    for s in m["segs"]:
        sig = activity(page, s["T0"], s["T1"], fps)
        out[s["id"]] = sum(1 for i in range(1, len(sig)) if sig[i] != sig[i - 1])
    return out


def run(url: str, widths: list[int], themes: list[str], browser_name: str, show_activity: bool, as_json: bool) -> int:
    from playwright.sync_api import sync_playwright
    fails, report = [], []
    with sync_playwright() as pw:
        browser = getattr(pw, browser_name).launch()
        try:
            for w in widths:
                for th in themes:
                    ctx, page = open_story(browser, url, w, th)
                    try:
                        m = page.evaluate("() => window.__site.map()")
                        rows = steps(m)
                        bad = verdicts(rows)
                        cell = {"width": w, "theme": th, "preset": m["preset"], "T1": m["T1"], "rows": rows, "fails": bad}
                        if show_activity:
                            cell["still"] = still_spans(m, activity(page, 0, m["T1"]))
                            cell["moving"] = moving_frames(page, m)
                            cell["segs"] = " ".join(f"{s['id']}:{s['T0']}-{s['T1']}" for s in m["segs"])
                        report.append(cell)
                        fails += [f"{w} {th}: {b}" for b in bad]
                    finally:
                        ctx.close()
        finally:
            browser.close()
    if as_json:
        print(json.dumps(report, indent=1))
    else:
        for c in report:
            print(f"== {c['width']} {c['theme']} ({c['preset']}, story {c['T1']:.2f} s)")
            print(f"   {'step':<14}{'transition':>11}{'caption':>9}{'content':>9}")
            for r in c["rows"]:
                flag = lambda k: ("*" if r[k] is not None and r[k] > LIMIT[k] and r["to"] in EXCEPTIONS[k] else " ")
                cap = "-" if r["caption"] is None else f"{r['caption']:.2f}"
                print(f"   {r['step']:<14}{r['transition']:>10.2f}{flag('transition')}{cap:>8}{flag('caption')}{r['content']:>8.2f}{flag('content')}")
            for s in c.get("still", []):
                print(f"   still  {s[0]:<12} {s[1]:.3f}-{s[2]:.3f} ({s[2] - s[1]:.2f} s)")
        print("named exceptions (*):")
        for k, ex in EXCEPTIONS.items():
            for b, why in ex.items():
                print(f"   {k} into {b}: {why}")
    print("FAIL" if fails else "PASS", f"({len(fails)} over budget)" if fails else "(every row within budget or a named exception)")
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--width", type=int, action="append", help="viewport width (repeatable; default 1440 and 820)")
    ap.add_argument("--theme", action="append", choices=("dark", "light"), help="default both")
    ap.add_argument("--browser", default="chromium", choices=("chromium", "webkit"))
    ap.add_argument("--activity", action="store_true", help="also print each segment's still spans >= 0.1 s")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    return run(a.url, a.width or [1440, 820], a.theme or ["dark", "light"], a.browser, a.activity, a.json)


if __name__ == "__main__":
    sys.exit(main())
