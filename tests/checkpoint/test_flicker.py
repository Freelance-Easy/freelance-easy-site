"""FLICKER (2026-10-16, Daniel: "when switching between chapters, u kinda see the visualisation flicker for a second
before it moves again ... most notably when going from dashboard to email ... inconsistent").

What it was: ONE trackpad flick read as two gestures. A busy main thread (or browser) holds wheel events back and Chrome
coalesces them, so a still-moving inertia tail arrives with a gap in it (ev.timeStamp) and a burst after it:
  M1  a gap > QUIET_SMOOTH (140 ms) ended the gesture; the rest of the tail started a new one -> a second "start" step;
      its peak was seeded by the slow tail, so "repeat" could fire again every ~850 ms (Email -> Yours -> Price ...);
  M2  a short stall (40-45 ms, <= CONT_GAP) at 120 Hz: the coalesced burst passed the "rise" test -> a second step.
The second step lands while the Ride (or Email's content) plays -> ICX-DIP: the stage fades through dark and cuts on.
Fix: ICX-CLASS.4 (a gap inside a live tail keeps the gesture) and ICX-CLASS.5 (a held-back delta counts spread over
its gap), assets/shared/checkpoint-input.js; constants TAIL_LIVE, JOIN_MAX, SPREAD_MIN (docs/checkpoint-config.md).

Stall models (both deterministic): C = Chrome coalescing (the events inside the stall arrive as ONE event carrying their
summed deltas, stamped with the latest one's time); B = late delivery (each held event arrives after the stall, 1 ms
apart, with its own delta).
Run: uv run --with pytest --with playwright python3 -m pytest tests/checkpoint/test_flicker.py -q   (needs node)
"""
from __future__ import annotations

import json
import pathlib
import subprocess

import pytest
from playwright.sync_api import sync_playwright

from lib import CELLS, Story

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "input"
RUNNER = ROOT / "tests" / "checkpoint" / "replay_stream.mjs"
S0 = list(range(150, 1401, 50))          # 26 stall positions through the tail


def wheel(name: str) -> list[dict]:
    d = json.loads((FIX / f"{name}.json").read_text())
    return [{"t": e["t"], "deltaY": e["deltaY"], "deltaMode": e["deltaMode"], "wheelDeltaY": e["wheelDeltaY"]}
            for e in d["events"] if e["type"] == "wheel"]


def stalled(ev: list[dict], s0: int, S: int, model: str) -> list[dict]:
    held = [e for e in ev if s0 < e["t"] <= s0 + S]
    if not held:
        return ev
    pre = [e for e in ev if e["t"] <= s0]
    post = [e for e in ev if e["t"] > s0 + S]
    if model == "C":
        dy = sum(e["deltaY"] for e in held)
        return pre + [{"t": held[-1]["t"], "deltaY": dy, "deltaMode": 0, "wheelDeltaY": -round(dy * 1.2)}] + post
    late = [{**e, "t": s0 + S + i} for i, e in enumerate(held)]
    return pre + late + [{**e, "t": max(e["t"], s0 + S + len(held))} for e in post]


def replay(streams: list[list[dict]]) -> list[list[list]]:
    r = subprocess.run(["node", str(RUNNER)], input=json.dumps([{"events": s} for s in streams]),
                       capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# ---- the stall matrix (detector level) -------------------------------------------------------------------------------
# residue measured after the fix (cell -> the s0 that still double-steps); every other position steps exactly once
RESIDUE: dict = {}
# the jank fixtures are already coalesced streams: only model C stacks on them (model B would replay the time their
# summed events already cover a second time)
CELLS_M1 = ([(f, m, S) for f in ("tp-flick-60hz", "tp-flick-120hz", "tp-long-tail") for m in ("C", "B") for S in (150, 200, 300)]
            + [(f, "C", S) for f in ("tp-tail-jank-60hz", "tp-tail-jank-120hz") for S in (150, 200, 300)])
CELLS_M2 = [(f, m, S) for f in ("tp-flick-60hz", "tp-flick-120hz", "tp-long-tail") for m in ("C", "B") for S in (33, 40, 45)]


@pytest.mark.parametrize("fx,model,S", CELLS_M1 + CELLS_M2, ids=lambda v: str(v))
def test_one_flick_is_one_step_through_a_stall(fx, model, S):
    """ICX-CLASS.4/.5: a stall anywhere in a flick's tail never adds a step (<= 1 of 26 positions, named in RESIDUE)."""
    ev = wheel(fx)
    out = replay([stalled(ev, s0, S, model) for s0 in S0])
    bad = {s0: st for s0, st in zip(S0, out) if len(st) != 1}
    allowed = RESIDUE.get((fx, model, S), set())
    assert set(bad) <= allowed and len(bad) <= 1, (
        f"{fx} with a {S} ms stall (model {model}): {len(bad)}/26 positions stepped more than once, e.g. "
        f"{next(iter(bad.items()), None)} (s0 -> [sign, t, trigger] ...): the tail was read as a new gesture")


def test_second_flick_after_a_stall_still_steps():
    """A deliberate second flick ~300 ms after the first still steps (the rise test), stall-joined or not."""
    first = [e for e in wheel("tp-flick-60hz") if e["t"] <= 200]
    finger = [4, 12, 24, 38, 48, 52] + [round(52 * 0.95 ** k) for k in range(1, 30)]
    second = [{"t": 300 + 16 * i, "deltaY": d, "deltaMode": 0, "wheelDeltaY": -round(d * 1.2)} for i, d in enumerate(finger) if d]
    plain = first + second
    gap = [e for e in first if e["t"] <= 100] + second   # the first's tail held back 200 ms, then the second flick
    for name, s in (("plain", plain), ("after a 200 ms gap", gap)):
        st = replay([s])[0]
        assert [x[0] for x in st] == [1, 1], f"second flick {name}: steps {st} (want +1 +1)"


def test_slow_drag_after_a_finished_tail_steps():
    """TAIL_LIVE: a tail that died out on its own is over; a slow drag 300 ms after it is a new gesture and steps."""
    tail = wheel("tp-flick-60hz")
    end = tail[-1]["t"]
    drag = [{"t": end + 300 + 16 * i, "deltaY": 4, "deltaMode": 0, "wheelDeltaY": -5} for i in range(13)]
    assert [x[0] for x in replay([tail + drag])[0]] == [1, 1]


def test_fractional_tail_end_then_drag_steps():
    """Sol FLICKER-1 #3: a tail that fades out in sub-MIN_DELTA events is over; a slow drag 300 ms later steps."""
    tail = [e for e in wheel("tp-flick-60hz") if e["t"] <= 600]
    end = tail[-1]["t"]
    fade = [{"t": end + 16 * i, "deltaY": 0.3, "deltaMode": 0, "wheelDeltaY": 0} for i in range(1, 8)]
    drag = [{"t": fade[-1]["t"] + 300 + 16 * i, "deltaY": 4, "deltaMode": 0, "wheelDeltaY": -5} for i in range(13)]
    assert [x[0] for x in replay([tail + fade + drag])[0]] == [1, 1]


def test_pixel_mode_notches_unchanged():
    """Sol FLICKER-1 #2: mouse notches in pixel mode with no wheelDeltaY (0/100/400 ms) keep ca70450's steps."""
    ev = [{"t": t, "deltaY": 100, "deltaMode": 0, "wheelDeltaY": 0} for t in (0, 100, 400)]
    assert [x[0] for x in replay([ev])[0]] == [1, 1]


def test_gentle_second_flick_within_a_moving_tail_is_the_known_trade_off():
    """KNOWN TRADE-OFF (Sol FLICKER-2 #1, main's ruling 2026-10-17): tp-flick-60hz to 200 ms, then a gentle deliberate
    second flick (4/6/8/10/12 px at 16 ms from 500 ms, then decay) stepped twice on ca70450 and steps ONCE here: the
    tail was still moving when it stopped, so ICX-CLASS.4 joins the second flick to it, and at under V_RISE_MIN it is
    no rise. A gentle second flick within JOIN_MAX of a moving tail needs a firmer swipe (the firm one steps:
    test_second_flick_after_a_stall_still_steps). A missed step is gentler than the double step + dip Daniel saw; a
    re-acceleration step was tried and read partly coalesced tail deliveries as a flick (Sol FLICKER-3 #2,
    test_partly_coalesced_tail_delivery_is_one_step). Daniel tunes JOIN_MAX on devices. If this goes to [1, 1], check
    that test still passes before calling it fixed."""
    first = [e for e in wheel("tp-flick-60hz") if e["t"] <= 200]
    finger = [4, 6, 8, 10, 12] + [round(12 * 0.9 ** k) for k in range(1, 20)]
    second = [{"t": 500 + 16 * i, "deltaY": d, "deltaMode": 0, "wheelDeltaY": -round(d * 1.2)} for i, d in enumerate(finger) if d]
    assert [x[0] for x in replay([first + second])[0]] == [1]


def test_partly_coalesced_tail_delivery_is_one_step():
    """Sol FLICKER-3 #2: tp-flick-60hz to 800 ms, its held 800-1100 ms tail delivered as 3/7/9/24 px at 1100/1108/1116/
    1124 ms, then the rest of the tail: one flick, one step (growing batch sizes are not a new finger)."""
    ev = wheel("tp-flick-60hz")
    held = [(1100, 3), (1108, 7), (1116, 9), (1124, 24)]
    s = ([e for e in ev if e["t"] <= 800] + [{"t": t, "deltaY": d, "deltaMode": 0, "wheelDeltaY": -round(d * 1.2)} for t, d in held]
         + [e for e in ev if e["t"] > 1124])
    assert [x[0] for x in replay([s])[0]] == [1]


@pytest.mark.parametrize("fx", ["tp-flick-60hz", "tp-flick-120hz", "tp-long-tail"])
@pytest.mark.parametrize("model", ["C", "B"])
def test_stall_just_after_the_peak_is_one_step(fx, model):
    """Sol FLICKER-3 #1: a stall that begins just after the peak (s0 96-144 ms, 200 ms), while the 50 ms rate still
    equals its peak but the deltas already fall (38/36/34), joins: one step (the TAIL_DECAY share alone lags there)."""
    ev = wheel(fx)
    out = replay([stalled(ev, s0, 200, model) for s0 in range(96, 145, 8)])
    bad = {s0: st for s0, st in zip(range(96, 145, 8), out) if len(st) != 1}
    assert not bad, f"{fx} model {model}: {bad}"


def test_drag_still_speeding_up_then_quiet_is_not_a_tail():
    """ICX-CLASS.4 joins only a decaying stream: a frame-paced drag still speeding up (20 -> 40 px) when it went quiet
    is the hand stopping, not a tail; the hand moving again 300 ms later, gently (under V_RISE_MIN, so only a new
    gesture's start can step it), steps again, as on ca70450."""
    d1 = [{"t": 16 * i, "deltaY": 20 + 2 * i, "deltaMode": 0, "wheelDeltaY": -round((20 + 2 * i) * 1.2)} for i in range(11)]
    d2 = [{"t": 460 + 16 * i, "deltaY": 5, "deltaMode": 0, "wheelDeltaY": -6} for i in range(8)]
    assert [x[0] for x in replay([d1 + d2])[0]] == [1, 1]


H2_STREAMS = {
    # Sol FLICKER-2 #2 verbatim: a fast-spun wheel's notches are frame-paced but repeat one delta (and hold the rate)
    "spun-100": [(t, 100) for t in (0, 16, 32, 48, 400, 700)],
    # the same spin with two notches coalesced (100/200/100/100): the deltas vary and fall, but are multiples of one notch
    "spun-coalesced": [(0, 100), (16, 200), (32, 100), (48, 100), (400, 100), (700, 100)],
    # a spin that slows down (the rate decays like a tail), but every notch is the same 100 px
    "spun-slowing": [(t, 100) for t in (0, 16, 32, 60, 100, 150, 400, 700)],
}
H2_BASE = {"spun-100": 3, "spun-coalesced": 3, "spun-slowing": 3}   # steps on ca70450


@pytest.mark.parametrize("name", list(H2_STREAMS))
def test_spun_mouse_wheel_steps_as_before(name):
    """Sol FLICKER-2 #2: ICX-CLASS.4 joins only an inertia tail, never a run of mouse notches (deltas >= NOTCH_HINT_PX,
    multiples of one size). A mouse wheel's later clicks (pixel mode, wheelDeltaY -120 per notch) step exactly as on
    ca70450."""
    ev = [{"t": t, "deltaY": d, "deltaMode": 0, "wheelDeltaY": -round(d * 1.2)} for t, d in H2_STREAMS[name]]
    st = replay([ev])[0]
    assert len(st) == H2_BASE[name] and all(x[0] == 1 for x in st), f"{name}: steps {st}, want {H2_BASE[name]} x +1"


def test_mouse_notches_unchanged():
    """Notch sequences keep their labels. Known cost of ICX-CLASS.4 (Sol FLICKER-1 #1: a coalesced trackpad burst can
    carry a notch-like wheelDeltaY, so only deltaMode 1 is excluded): a pixel-mode mouse notch within JOIN_MAX of a
    trackpad tail still moving the same way joins that gesture and does not step."""
    got = replay([wheel("mw-three-clicks"), wheel("mw-quiet-221"), wheel("mw-quiet-219"), wheel("mw-burst"),
                  [e for e in wheel("tp-flick-60hz") if e["t"] <= 400]
                  + [{"t": 700, "deltaY": 100, "deltaMode": 0, "wheelDeltaY": -120}]])
    assert [[x[0] for x in s] for s in got] == [[1, 1, 1], [1, 1], [1], [1], [1]], got


# ---- the browser: Dashboard -> Email with replayed input (exact timestamps) --------------------------------------
_REC = r"""() => {
  const F = window.__flk = { rec: [], dest: [] };
  const st = document.querySelector('.stage-wrap'), ov = document.querySelector('.pin-over');
  FEStory.onDest(p => { if (F.rec) F.dest.push([Math.round(performance.now()), p.index, p.source, !!p.preview]); });
  const tick = () => { if (!F.rec) return; const s = FEStory.state();
    F.rec.push([Math.round(performance.now()), s.phase, s.dest, s.rendered, s.dip ? 1 : 0,
      +getComputedStyle(st).opacity, ov ? +getComputedStyle(ov).opacity : 1]);
    requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}"""
# the stream's events are dispatched on schedule with their timeStamp pinned to the stream's own clock, so the detector
# sees exactly the replayed times whatever the page's timers do
_PLAY = r"""(ev) => new Promise((done) => {
  const base = performance.now() + 30, x = innerWidth / 2, y = innerHeight / 2;
  let i = 0;
  const next = () => {
    while (i < ev.length && performance.now() >= base + ev[i].t) {
      const e = ev[i++];
      const w = new WheelEvent('wheel', { deltaY: e.deltaY, deltaMode: e.deltaMode, clientX: x, clientY: y, bubbles: true, cancelable: true });
      Object.defineProperty(w, 'timeStamp', { value: base + e.t });
      Object.defineProperty(w, 'wheelDeltaY', { value: e.wheelDeltaY });
      document.elementFromPoint(x, y).dispatchEvent(w);
    }
    if (i < ev.length) setTimeout(next, Math.max(0, base + ev[i].t - performance.now())); else done();
  };
  setTimeout(next, 30);
})"""
STREAMS = {
    "jank-tail+200ms-stall": lambda: stalled(wheel("tp-tail-jank-60hz"), 600, 200, "C"),   # M1
    "120hz+40ms-stall": lambda: stalled(wheel("tp-flick-120hz"), 250, 40, "C"),            # M2
}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.mark.parametrize("cell", [CELLS[0], CELLS[3]], ids=lambda c: c.id)
@pytest.mark.parametrize("stream", list(STREAMS))
def test_dashboard_to_email_one_flick_no_dip(browser, site_url, cell, stream):
    """One flick (with the page stalling in its tail): exactly one step, no dip frame, no faded stage, nothing more
    after it; it rests on the next chapter. Desktop: Dashboard -> Email (the Ride, where Daniel saw it). Tablet: Email
    is the last pinned there, so a second step from it is dropped (no dip); Invoices -> Dashboard is its case instead."""
    k0 = 3 if cell.n_pinned == 9 else 2
    st = Story.open(browser, site_url, cell)
    try:
        page = st.page
        page.evaluate("() => FEStory.goTo(%d, {source: 'jump'})" % k0)
        page.wait_for_function("() => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === %d && s.dest === %d; }" % (k0, k0), timeout=15000)
        page.wait_for_timeout(900)                        # past the dip cooldown
        page.evaluate(_REC)
        page.evaluate(_PLAY, STREAMS[stream]())
        page.wait_for_function("() => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === s.dest; }", timeout=15000)
        page.wait_for_timeout(1200)                       # anything more the tail would have done
        r = page.evaluate("() => { const F = window.__flk; const r = {rec: F.rec, dest: F.dest}; F.rec = null; return r; }")
    finally:
        st.close()
    rec, t0 = r["rec"], r["rec"][0][0]
    steps = [(d[0] - t0, d[1]) for d in r["dest"] if d[2] == "step" and not d[3]]
    dips = [(f[0] - t0, f[1], f[2], f[3]) for f in rec if f[4]]
    faded = [(f[0] - t0, f[5], f[6]) for f in rec if f[5] < 0.99 or f[6] < 0.99]
    assert [s[1] for s in steps] == [k0 + 1], f"{stream}: one flick stepped {steps} (ms, beat index): want one step to {k0 + 1}"
    assert not dips, f"{stream}: {len(dips)} dip frames, first {dips[:2]} (ms, phase, dest, rendered)"
    assert not faded, f"{stream}: stage/overlay faded on {len(faded)} frames, first {faded[:2]}"
    assert rec[-1][1:4] == ["rest", k0 + 1, k0 + 1], f"{stream}: ended {rec[-1][1:4]}, want rest on {k0 + 1}"
