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
import hashlib
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
        "chase": "the Ride (1.57 s active): 'Follow up in two clicks.' arrives once the band is the whole page (one clean colour "
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

# the same hash at each story time in a list
SIG_AT_JS = SIG_JS.replace("(([t0, t1, dt]) =>", "((times) =>").replace(
    "for (let T = t0; T <= t1 + 1e-9; T += dt) { window.__site.seekMaster(T); out.push(sig()); }",
    "for (const T of times) { window.__site.seekMaster(T); out.push(sig()); }")
# Email's three cut still spans (scenes.js Chase: FX.cutTime), in the base's local seconds: [at, d]
CHASE_CUTS = [(1.655, 0.08), (3.16, 0.52), (4.49, 0.18)]


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
        # the caption is ACTIVE once its switch's hysteresis (0.12 s, or the switch's own width) and the outgoing
        # caption's 60 ms fade have passed (site.js updateCaptions; Sol C5-1 #1)
        sw = next((t + (w[0] if w else 0.12) + 0.06 for beat, t, *w in m["switches"] if beat == b["beat"] and t >= a["rest"] - 1e-6), None)
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


def base_time(seg_id: str, u: float, cut_len: float, base_len: float) -> float:
    """The base (?pace=before) local time that C5's local time u plays. C5's only mechanism is removing still time: a
    segment either keeps its start (the still tail is cut: identity) or, Chase, has CHASE_CUTS taken out of it, so a frame
    at or after a cut's start (in C5 time) is the base's frame d later."""
    if seg_id != "chase" or base_len - cut_len < 0.5:
        return u
    b, gone = u, 0.0
    for at, d in CHASE_CUTS:
        if u >= at - gone - 1e-9:
            b += d
        gone += d
    return b


def signature_diffs(page, base_page, m: dict, base_m: dict, fps: int = 60) -> list[str]:
    """Every frame of every segment must be the SAME picture as the base's frame at the same moment of the move: C5 at
    local u (u = k/fps from the segment's start) against ?pace=before at base_time(u), the cut still spans skipped.
    A faster, slower or re-eased move (also one overlapping another move) changes some frame's signature; a count of
    changed frames cannot see that. Also: what was cut must have been still in the base (a tail after the C5 segment's
    end, the spans inside Chase). Returns messages naming the segment and local time."""
    bad = []
    base = {s["id"]: s for s in base_m["segs"]}
    for s in m["segs"]:
        b = base.get(s["id"])
        if b is None:
            bad.append(f"{s['id']}: not in the base timeline")
            continue
        c_len, b_len = s["T1"] - s["T0"], b["T1"] - b["T0"]
        n = int(min(c_len, b_len + 0.02) * fps + 1e-6)
        us = [k / fps for k in range(n + 1)]
        got = page.evaluate(SIG_AT_JS, [s["T0"] + u for u in us])
        want = base_page.evaluate(SIG_AT_JS, [b["T0"] + base_time(s["id"], u, c_len, b_len) for u in us])
        diff = [us[k] for k in range(len(us)) if got[k] != want[k]]
        if diff:
            bad.append(f"{s['id']}: {len(diff)} of {len(us)} frames differ from the base (first at local {diff[0]:.3f} s, last {diff[-1]:.3f} s)")
        # what was cut must be still in the base
        spans = []
        if s["id"] == "chase" and b_len - c_len >= 0.5:
            spans = [(at, at + d) for at, d in CHASE_CUTS]
        elif b_len - c_len > 0.02:
            spans = [(c_len, b_len)]
        for a, z in spans:
            ts = [b["T0"] + a + (z - a) * i / 8 for i in range(1, 8)]  # (inside the span: its end frame is the next move's first)
            sg = base_page.evaluate(SIG_AT_JS, ts)
            if len(set(sg)) > 1:
                bad.append(f"{s['id']}: the base moves in the span {a:.2f}-{z:.2f} s that C5 cut: a move was removed")
    return bad


def segment_digests(page, m: dict, fps: int = 60) -> dict[str, str]:
    """Per segment: a digest of the stage signature at every 1/fps of its own time. Pinned from 67f6b3a (`?pace=before`,
    tests/checkpoint/base_signatures.json): a move that plays faster, slower or re-eased in code BOTH timelines share
    (which signature_diffs, `/` against the flag, cannot see) changes the digest."""
    out = {}
    for s in m["segs"]:
        n = int((s["T1"] - s["T0"]) * fps + 1e-6)
        sig = page.evaluate(SIG_AT_JS, [s["T0"] + k / fps for k in range(n + 1)])
        out[s["id"]] = hashlib.sha1(",".join(map(str, sig)).encode()).hexdigest()[:12]
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


def write_signatures(url: str, path: str, browser_name: str = "chromium") -> None:
    """Regenerate tests/checkpoint/base_signatures.json: segment_digests of `<url>?pace=before` at 1440, 820, 390, both
    themes (the cells test_base_motion_pinned reads). `url` is the site's base URL (any ?query is dropped)."""
    from playwright.sync_api import sync_playwright
    base = url.split("?")[0].split("#")[0].rstrip("/") + "/?pace=before"
    out = {}
    with sync_playwright() as pw:
        browser = getattr(pw, browser_name).launch()
        try:
            for lay, w in (("desktop", 1440), ("tablet", 820), ("phone", 390)):
                for th in ("dark", "light"):
                    ctx, page = open_story(browser, base, w, th)
                    try:
                        out[f"{lay}-{th}"] = segment_digests(page, page.evaluate("() => window.__site.map()"))
                    finally:
                        ctx.close()
        finally:
            browser.close()
    with open(path, "w") as f:
        f.write(json.dumps(out, indent=1) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", required=True)
    ap.add_argument("--width", type=int, action="append", help="viewport width (repeatable; default 1440 and 820)")
    ap.add_argument("--theme", action="append", choices=("dark", "light"), help="default both")
    ap.add_argument("--browser", default="chromium", choices=("chromium", "webkit"))
    ap.add_argument("--activity", action="store_true", help="also print each segment's still spans >= 0.1 s")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write-signatures", metavar="PATH", help="write the pinned base digests JSON (from <url>?pace=before) and exit")
    a = ap.parse_args(argv)
    if a.write_signatures:
        write_signatures(a.url, a.write_signatures, a.browser)
        return 0
    return run(a.url, a.width or [1440, 820], a.theme or ["dark", "light"], a.browser, a.activity, a.json)


if __name__ == "__main__":
    sys.exit(main())
