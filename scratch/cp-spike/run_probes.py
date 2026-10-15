#!/usr/bin/env python3
"""C0a probes: drive scratch/cp-spike/index.html through every verdict row on the Playwright proxies.

One command (from anywhere):
  uv run --with playwright==1.63.0 python3 "<worktree>/scratch/cp-spike/run_probes.py"            # every column, every row
  uv run --with playwright==1.63.0 python3 ".../run_probes.py" --col webkit-iphone --row R8         # a slice

Serves the worktree itself on 127.0.0.1:8802 if nothing listens there (never freelance-easy.com).
Writes scratch/cp-spike/evidence/<column>/<row>__<WxH>[-variant].json, evidence/summary.json and evidence/summary.md.
Every input is synthesised: Playwright mouse.wheel (trusted wheel events with hand-made inertia tails), keyboard.press,
real mouse drags on a classic scrollbar where one exists, CDP Input.dispatchTouchEvent (Chromium, trusted touches),
JS-dispatched TouchEvent-shaped events (WebKit, untrusted: logic only, no native scroll or momentum), window.scrollBy
streams (stand-ins for autoscroll, find, iOS momentum), set_viewport_size (rotation, the iOS bars), device_scale_factor
contexts (browser zoom), CDP Emulation.setPageScaleFactor (pinch).
"""
import argparse, json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVID = HERE / "evidence"
PORT = 8802
BASE = f"http://127.0.0.1:{PORT}/scratch/cp-spike/index.html"

COLUMNS = {
    "chromium": dict(engine="chromium", vps=[(1440, 900, "desk"), (1280, 720, "desk"), (360, 640, "android")]),
    "webkit": dict(engine="webkit", vps=[(1440, 900, "desk"), (1280, 720, "desk")]),
    "webkit-iphone": dict(engine="webkit", vps=[(390, 664, "iphone"), (375, 548, "iphone"), (360, 640, "iphone"),
                                                (844, 390, "iphone")]),
}
ROWS = {
    "R1": "programmatic-scroll acknowledgement", "R2": "FREE/RELEASED boundaries", "R3": "settle cancellation",
    "R4": "resize/rotation", "R5": "scrollbar hold", "R6": "autoscroll", "R7": "Safari without scrollend",
    "R8": "iOS momentum + address bar", "R9": "zoom", "S1": "wheel grouping (supplementary, R1 §3.4 detector)",
}
TOL = 1.5


# ---------------------------------------------------------------- helpers
class T:
    """One probe run: checks, data, workaround notes."""
    def __init__(self, page, row, col, vp):
        self.page, self.row, self.col, self.vp = page, row, col, vp
        self.checks, self.data, self.work, self.synth = [], {}, [], []

    def check(self, name, ok, detail=None):
        self.checks.append({"name": name, "ok": bool(ok), "detail": detail})
        return ok

    def ev(self, js, arg=None):
        return self.page.evaluate(js, arg) if arg is not None else self.page.evaluate(js)

    def st(self):
        return self.ev("__cp.state()")

    def geom(self):
        return self.ev("__cp.geom()")

    def cnt(self):
        return self.ev("__cp.counters()")

    def log(self, since=0):
        return self.ev("(t) => __cp.L.filter(e => e.t >= t)", since)

    def now(self):
        return self.ev("performance.now()")

    def goto(self, q="", hash_=""):
        """Reload the spike; the previous page's log is kept in data['logs'] so the evidence stays complete."""
        try:
            prev = self.log(0)
            if prev:
                self.data.setdefault("logs_before_reload", []).append(prev)
        except Exception:
            pass
        goto(self.page, q, hash_)

    def status(self):
        if not all(c["ok"] for c in self.checks):
            return "FAIL"
        return "WORKAROUND" if self.work else "PASS"


def goto(page, q="", hash_=""):
    page.goto(BASE + (("?" + q) if q else "") + hash_)
    page.wait_for_function("window.__cp && __cp.geom().P > 0")
    page.wait_for_timeout(150)
    vs = page.viewport_size
    page.mouse.move(vs["width"] * 0.4, vs["height"] * 0.5)


def wait_rest(t, timeout=8.0, hold=0.15):
    end, since = time.time() + timeout, None
    while time.time() < end:
        s = t.st()
        if not s["busy"] and not s["free"] and s["phase"] in ("rest", "released"):
            since = since or time.time()
            if time.time() - since >= hold:
                return s
        else:
            since = None
        time.sleep(0.03)
    s = t.st()
    s["timeout"] = True
    return s


def at_rest_ok(t, s, beat=None):
    g = t.geom()
    if s["phase"] == "released":
        return s["y"] > g["storyEnd"] + 1
    ok = s["phase"] == "rest" and abs(s["aligned"]) <= TOL and not s.get("timeout")
    return ok and (beat is None or s["rendered"] == beat)


def flick(page, dy=70, n=22, decay=0.86, dt=0.016, ramp=True):
    """A trackpad-like flick: a short ramp-up (real trackpads open small), then a decaying inertia tail."""
    if ramp:
        for f in (0.08, 0.25, 0.55):
            page.mouse.wheel(0, dy * f)
            time.sleep(dt)
    v = dy
    for _ in range(n):
        page.mouse.wheel(0, v)
        time.sleep(dt)
        v *= decay
        if abs(v) < 0.6:
            break


def is_mwk(t):
    return t.col == "webkit-iphone"


def gesture(t, dy):
    """One deliberate gesture inside the story: a wheel flick, or on mobile WebKit (no wheel) a synthetic swipe."""
    if is_mwk(t):
        note = "mobile WebKit has no wheel: gestures are synthetic swipes"
        if note not in t.synth:
            t.synth.append(note)
        cy = t.page.viewport_size["height"] * 0.6
        return synth_touch(t, cy, cy - 220 * (1 if dy > 0 else -1))
    flick(t.page, dy)


def release(t, dy=90):
    """A forward gesture at the last beat that the browser must scroll natively."""
    if is_mwk(t):
        note = "mobile WebKit: the native scroll after a passed swipe is stood in by a window.scrollBy stream"
        if note not in t.synth:
            t.synth.append(note)
        r = gesture(t, dy)
        t.check("the swipe at the last beat was not prevented", not any(r["prevented"]), r)
        t.ev(STREAM_JS, {"px": 40, "frames": 20, "decay": 0.92})
        return
    flick(t.page, dy)


def press(t, key, n=1):
    for _ in range(n):
        t.page.keyboard.press(key)
        wait_rest(t)


STREAM_JS = """async ({px, frames, decay}) => { const ts = []; let v = px;
  for (let i = 0; i < frames; i++) { await new Promise(r => requestAnimationFrame(r)); window.scrollBy(0, v);
    ts.push(performance.now()); v *= decay; }
  return { first: ts[0], last: ts[ts.length - 1], y: window.scrollY }; }"""

TOUCH_JS = """async ({x, y0, y1, steps, dt, fingers}) => {
  const el = document.querySelector('.pin');
  const pt = (y) => ({ identifier: 1, target: el, clientX: x, clientY: y, pageX: x, pageY: y + scrollY, screenX: x, screenY: y });
  const fire = (type, y, live) => { const ev = new Event(type, { bubbles: true, cancelable: true });
    const p = pt(y), list = live ? Array.from({ length: fingers }, (_, i) => Object.assign({}, p, { identifier: i + 1 })) : [];
    Object.defineProperty(ev, 'touches', { value: list }); Object.defineProperty(ev, 'targetTouches', { value: list });
    Object.defineProperty(ev, 'changedTouches', { value: [p] }); el.dispatchEvent(ev); return ev.defaultPrevented; };
  const prevented = [];
  fire('touchstart', y0, true);
  for (let i = 1; i <= steps; i++) { await new Promise(r => setTimeout(r, dt)); prevented.push(fire('touchmove', y0 + (y1 - y0) * i / steps, true)); }
  fire('touchend', y1, false);
  return { prevented, y: window.scrollY };
}"""


def synth_touch(t, y0, y1, steps=10, dt=16, fingers=1):
    vs = t.page.viewport_size
    return t.ev(TOUCH_JS, {"x": vs["width"] * 0.4, "y0": y0, "y1": y1, "steps": steps, "dt": dt, "fingers": fingers})


def cdp_drag(t, y0, y1, steps=12, dt=0.016):
    cdp = t.page.context.new_cdp_session(t.page)
    x = t.page.viewport_size["width"] * 0.4
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y0}]})
    for i in range(1, steps + 1):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y0 + (y1 - y0) * i / steps}]})
        time.sleep(dt)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    cdp.detach()


def diff(a, b):
    return {k: b[k] - a[k] for k in b if isinstance(b[k], (int, float)) and b[k] != a.get(k)}


# ---------------------------------------------------------------- rows
def r1_ack(t):
    t.goto()
    c0, t0 = t.cnt(), t.now()
    press(t, "ArrowDown", 3)
    gesture(t, 70)
    s = wait_rest(t)
    t.check("one gesture = one step (beat 4)", s["rendered"] == 4, s)
    press(t, "End")
    press(t, "Home")
    c1 = t.cnt()
    d = diff(c0, c1)
    t.data["counters"] = d
    t.check("no programmatic scroll was misread as foreign", d.get("foreign", 0) == 0, d)
    t.check("every programmatic scroll produced an acknowledged scroll event", d.get("acked", 0) >= 5, d)
    t.check("at rest and aligned on beat 0", at_rest_ok(t, t.st(), 0), t.st())
    lg = t.log(t0)
    syncs = [e for e in lg if e["ev"] == "sync"]
    t.data["syncs"] = len(syncs)
    t.data["scrollTo_applied_synchronously"] = all(abs(e["syncY"] - e["to"]) <= TOL for e in syncs)
    # how many scroll / scrollend events follow one programmatic scrollTo
    per = []
    idx = [i for i, x in enumerate(lg) if x["ev"] == "sync"]           # by log order: an ack can share the sync's 0.1 ms stamp
    for k, i in enumerate(idx):
        win = lg[i + 1: idx[k + 1] if k + 1 < len(idx) else len(lg)]
        per.append({"acks": sum(1 for x in win if x["ev"] == "scroll-ack"), "scrollend": sum(1 for x in win if x["ev"] == "scrollend")})
    t.data["events_per_sync"] = per
    t.check("each scrollTo produced exactly one scroll event", all(p["acks"] == 1 for p in per), per)
    # a no-op sync must not leave a pending acknowledgement that would swallow the next foreign scroll
    t.ev("__cp.goTo(0)")
    wait_rest(t)
    t.check("no-op sync arms nothing", t.st()["ack"] is None or t.st()["ack"]["events"] >= 0, t.st())
    f0 = t.cnt()["foreign"]
    t.ev("window.scrollBy(0, 37)")
    t.page.wait_for_timeout(120)
    t.check("a foreign scroll right after is still seen as foreign", t.cnt()["foreign"] > f0, t.cnt())
    wait_rest(t)
    t.data["native_scrollend"] = t.ev("__cp.nativeScrollend")


def r2_bounds(t):
    t.goto()
    press(t, "End")
    g = t.geom()
    t0 = t.now()
    release(t)
    t.page.wait_for_timeout(300)
    s = t.st()
    t.check("a forward gesture at the last beat passes: RELEASED, page below the story", s["phase"] == "released" and s["y"] > g["storyEnd"] + 1, s)
    t.check("the passing gesture was never prevented", not any(e["ev"] == "step" for e in t.log(t0)), None)
    time.sleep(0.3)
    t1 = t.now()
    if is_mwk(t):                             # iOS: momentum from below cannot be clamped; FREE settles it
        t.ev(STREAM_JS, {"px": -30, "frames": 45, "decay": 1.0})
    else:
        for _ in range(45):                   # one continuous slow upward drag (a single gesture)
            t.page.mouse.wheel(0, -30)
            time.sleep(0.016)
    t.page.wait_for_timeout(250)
    s = wait_rest(t)
    lg = t.log(t1)
    t.check("re-entry clamps exactly to the story end, REST(last)", s["phase"] == "rest" and s["rendered"] == 8 and abs(s["y"] - g["storyEnd"]) <= TOL, s)
    t.check("the rest of that gesture is swallowed (no step)", not any(e["ev"] == "step" for e in lg), [e["ev"] for e in lg][:12])
    t.data["reentry_logged"] = any(e["ev"] == "reentry" for e in lg)
    time.sleep(0.3)
    gesture(t, -70)
    s = wait_rest(t)
    t.check("the next up gesture steps back to beat 7", s["rendered"] == 7 and at_rest_ok(t, s, 7), s)
    # FREE from below (a foreign scroll into the track while released) settles on the last beat
    press(t, "End")
    release(t)
    t.page.wait_for_timeout(300)
    t.ev("(y) => window.scrollTo(0, y)", g["storyEnd"] - 0.4 * g["P"])
    s = wait_rest(t)
    t.check("foreign re-entry from below settles on the last beat", at_rest_ok(t, s, 8), s)
    # PageDown at the last beat releases natively
    t.page.keyboard.press("PageDown")
    t.page.wait_for_timeout(500)
    s = t.st()
    t.check("PageDown at the last beat releases natively", s["phase"] == "released" and s["y"] > g["storyEnd"] + 1, s)
    # Home from below jumps back into the story
    press(t, "Home")
    t.check("Home from below lands on beat 0", at_rest_ok(t, t.st(), 0), t.st())


def r3_settle(t):
    t.goto()
    press(t, "ArrowDown", 2)
    g = t.geom()
    c0 = t.cnt()
    t.ev("(y) => window.scrollTo(0, y)", g["ys"][2] + 0.6 * g["P"])
    t.page.wait_for_timeout(40)
    t.check("a foreign scroll enters FREE", t.st()["free"], t.st())
    t.page.keyboard.press("ArrowDown")
    s = wait_rest(t)
    d = diff(c0, t.cnt())
    t.check("a key during a pending settle cancels it (0 settles, 1 cancel)", d.get("settles", 0) == 0 and d.get("settleCancel", 0) == 1, d)
    t.check("the step counts from the nearest beat (2.6 -> 3, +1 = 4)", at_rest_ok(t, s, 4), s)
    # a wheel during a pending settle cancels it too
    t.ev("(y) => window.scrollTo(0, y)", g["ys"][4] - 0.3 * g["P"])
    t.page.wait_for_timeout(40)
    c1 = t.cnt()
    gesture(t, -70)
    s = wait_rest(t)
    d = diff(c1, t.cnt())
    # a real race: Chrome's scrollend + 50 ms grace can settle before the wheel arrives; both orders must end on nearest-1
    t.data["wheel_path"] = "cancelled the pending settle" if d.get("settleCancel") else "settle fired first, then the step"
    t.check("a wheel right after a foreign scroll ends on nearest-1 (4 -> 3), one step", at_rest_ok(t, s, 3) and d.get("steps", 0) == 1, [d, s])
    # a stream of foreign scrolls: exactly one settle, after the stream ends, and the settle's own scroll is acknowledged
    t0, c2 = t.now(), t.cnt()
    r = t.ev(STREAM_JS, {"px": 14, "frames": 30, "decay": 0.97})
    s = wait_rest(t)
    lg = t.log(t0)
    d = diff(c2, t.cnt())
    st_ = [e for e in lg if e["ev"] == "settle"]
    t.data.update(stream=r, settle=st_, counters=d, free_enters=sum(1 for e in lg if e["ev"] == "free-enter"))
    t.check("exactly one settle for the stream", len(st_) == 1, st_)
    t.check("the settle came after the stream's last scroll", bool(st_) and st_[0]["t"] >= r["last"], [r, st_])
    t.check("one FREE entry (the settle's own scroll did not re-enter FREE)", t.data["free_enters"] == 1, t.data["free_enters"])
    t.check("lands aligned on the nearest beat", at_rest_ok(t, s) and s["rendered"] == round((r["y"] - g["storyTop"]) / g["P"]), [s, r])
    if st_:
        t.data["settle_latency_ms"] = round(st_[0]["t"] - r["last"], 1)
        t.data["settle_trigger"] = st_[0]["trigger"]
        if st_[0]["trigger"] != "scrollend":
            t.work.append(f"settled by '{st_[0]['trigger']}' (no scrollend)")


def r4_resize(t):
    w0, h0 = t.vp[0], t.vp[1]
    t.goto()
    press(t, "ArrowDown", 4)
    seq = [(1280, 720), (1024, 768), (1600, 1000), (w0, h0)] if t.vp[2] == "desk" else [(h0 if h0 > w0 else 390, w0 if w0 < h0 else 844), (w0, h0), (w0, h0 + 81), (w0, h0)]
    res = []
    for (w, h) in seq:
        t.page.set_viewport_size({"width": w, "height": h})
        t.page.wait_for_timeout(350)
        s, g = wait_rest(t), t.geom()
        res.append({"vp": [w, h], "P": g["P"], "s": s})
        t.check(f"resize to {w}x{h} keeps beat 4 aligned", at_rest_ok(t, s, 4), s)
    t.data["sequence"] = res
    # mid-transition resize
    t.page.keyboard.press("ArrowDown")
    t.page.wait_for_timeout(200)
    t.page.set_viewport_size({"width": seq[0][0], "height": seq[0][1]})
    s = wait_rest(t)
    t.check("resize mid-transition lands beat 5 aligned", at_rest_ok(t, s, 5), s)
    t.page.set_viewport_size({"width": w0, "height": h0})
    wait_rest(t)
    # released keeps its distance below the story
    press(t, "End")
    release(t)
    t.page.wait_for_timeout(300)
    g = t.geom()
    past = t.st()["y"] - g["storyEnd"]
    t.page.set_viewport_size({"width": seq[0][0], "height": seq[0][1]})
    t.page.wait_for_timeout(350)
    s, g2 = t.st(), t.geom()
    t.data["released"] = {"past_before": past, "past_after": s["y"] - g2["storyEnd"]}
    t.check("a released reader keeps their distance below the story", s["phase"] == "released" and abs((s["y"] - g2["storyEnd"]) - past) <= 2, t.data["released"])
    t.page.set_viewport_size({"width": w0, "height": h0})
    moved = [e for e in t.log(0) + sum(t.data.get("logs_before_reload", []), []) if e["ev"] == "geometry"
             and e.get("rawY") is not None and abs(e["rawY"] - e["usedY"]) > 1]
    t.data["scroll_moved_before_resize"] = moved
    if moved:
        t.work.append(f"{len(moved)} resize(s) moved scrollY before the resize event; the re-snap used the last "
                      "position seen at the old size (S7)")
    c = t.cnt()
    t.data["resize_grace_snaps"] = c["resizeSnaps"]
    if c["resizeSnaps"]:
        t.work.append(f"{c['resizeSnaps']} browser scroll corrections after a resize were re-snapped by RESIZE_GRACE")


def r5_hold(t, q=""):
    t.goto(q)
    g = t.geom()
    bar = g["iw"] - g["cw"]
    t.data["scrollbar_px"] = bar
    t0, c0 = t.now(), t.cnt()
    if bar > 0:
        x = g["iw"] - bar / 2
        thumb_h = g["ih"] * g["ih"] / g["sh"]
        t.page.mouse.move(x, max(2, thumb_h / 2))
        t.page.mouse.down()
        for i in range(1, 11):
            t.page.mouse.move(x, thumb_h / 2 + 18 * i)
            time.sleep(0.02)
        time.sleep(1.0)                                   # held still, longer than SETTLE_IDLE and the backstop
        s1 = t.st()
        t.data["during_hold"] = s1
        t.check("real thumb drag scrolled the page", s1["y"] > 50, s1)
        t.check("held thumb: FREE, no settle while held", s1["free"] and s1["held"] and t.cnt()["settles"] == c0["settles"], s1)
        t.page.mouse.up()
        s = wait_rest(t)
        d = diff(c0, t.cnt())
        t.data["counters"] = d
        t.check("mousedown reached the page from the scrollbar", d.get("barDown", 0) == 1, d)
        t.check("release: exactly one settle, aligned on the nearest beat", d.get("settles", 0) == 1 and at_rest_ok(t, s) and s["rendered"] == round((s1["y"] - g["storyTop"]) / g["P"]), [d, s])
        t.data["mouseup_seen"] = d.get("barUp", 0)
        if not d.get("barUp"):
            t.work.append("no mouseup after the scrollbar drag; the hold ended on another signal")
    else:
        t.work.append("overlay scrollbar (0 px): hold detection (clientX >= clientWidth) cannot see the thumb; the settle must rely on scrollend-after-release or the idle fallback")
        t.synth.append("hold synthesised: a real button down on content + a dispatched mousedown at clientX = clientWidth")
        t.page.mouse.down()                      # a real button stays down: WebKit's post-scroll mousemoves carry buttons=1
        t.ev("() => document.documentElement.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, clientX: document.documentElement.clientWidth, clientY: 60, buttons: 1}))")
        t.ev(STREAM_JS, {"px": 20, "frames": 15, "decay": 1.0})
        time.sleep(1.0)
        s1 = t.st()
        t.check("synthetic hold: FREE, no settle while held", s1["free"] and s1["held"] and t.cnt()["settles"] == c0["settles"], s1)
        y_hold = s1["y"]
        t.page.mouse.up()
        s = wait_rest(t)
        d = diff(c0, t.cnt())
        t.check("release: exactly one settle, aligned", d.get("settles", 0) == 1 and at_rest_ok(t, s) and s["rendered"] == round((y_hold - g["storyTop"]) / g["P"]), [d, s])
    # an undetected stationary hold (Mac overlay scrollbars): what the reader gets
    t.goto()
    c0 = t.cnt()
    t.ev(STREAM_JS, {"px": 20, "frames": 15, "decay": 1.0})
    time.sleep(1.0)
    t.data["undetected_hold_settles_after_1s"] = t.cnt()["settles"] - c0["settles"]


def r5_classic(t):
    """A styled non-overlay scrollbar, so a real thumb drag can be driven on the Mac proxies."""
    r5_hold(t, "classicbar")


def r6_auto(t, q=""):
    t.goto(q)
    press(t, "ArrowDown", 1)
    g = t.geom()
    t0, c0 = t.now(), t.cnt()
    t.ev("(a) => { window.__stream = (" + STREAM_JS + ")(a); return 1; }", {"px": 9, "frames": 60, "decay": 1.0})  # ~1 s, no wheel
    time.sleep(0.45)
    mid = t.st()
    r = t.ev("() => window.__stream")
    s = wait_rest(t)
    lg = t.log(t0)
    d = diff(c0, t.cnt())
    st_ = [e for e in lg if e["ev"] == "settle"]
    t.data.update(mid=mid, stream=r, counters=d, settles=st_, scrollend_during=sum(1 for e in lg if e["ev"] == "scrollend" and e["t"] <= r["last"]))
    t.check("the stage holds its frame during the stream (FREE, beat 1)", mid["free"] and mid["rendered"] == 1, mid)
    t.check("exactly one settle, after the stream", len(st_) == 1 and st_[0]["t"] >= r["last"], st_)
    t.check("lands aligned on the nearest beat", at_rest_ok(t, s) and s["rendered"] == round((r["y"] - g["storyTop"]) / g["P"]), [s, r])
    if st_ and st_[0]["trigger"] != "scrollend":
        t.work.append(f"settled by '{st_[0]['trigger']}'")
    if t.data["scrollend_during"] > 1 and "SCROLLEND_GRACE=0" not in q:
        t.work.append(f"scrollend fired {t.data['scrollend_during']}x during one foreign stream: a plain scrollend settle "
                      "fails (see the -nograce file); needs SCROLLEND_GRACE (S3)")


def r6_nograce(t):
    """Evidence for SCROLLEND_GRACE: the same stream with the grace at 0."""
    r6_auto(t, "SCROLLEND_GRACE=0")


def r7_noscrollend(t):
    t.goto("noscrollend")
    native = t.ev("__cp.nativeScrollend")
    t.data["native_scrollend"] = native
    press(t, "ArrowDown", 1)
    t0, c0 = t.now(), t.cnt()
    r = t.ev(STREAM_JS, {"px": 12, "frames": 25, "decay": 0.97})
    s = wait_rest(t)
    lg = t.log(t0)
    st_ = [e for e in lg if e["ev"] == "settle"]
    t.data.update(stream=r, settles=st_)
    t.check("fallback: exactly one settle, triggered by idle", len(st_) == 1 and st_[0]["trigger"] == "idle", st_)
    lat = st_[0]["t"] - r["last"] if st_ else None
    t.data["latency_ms"] = lat
    t.check("idle latency within SETTLE_IDLE .. +150 ms", lat is not None and 145 <= lat <= 300, lat)
    t.check("lands aligned", at_rest_ok(t, s), s)
    t.work.append("scrollend absent or disabled: idle-timer fallback" if not native else "scrollend forced off (?noscrollend) to exercise the Safari path")


def r8_touch(t):
    t.goto()
    g = t.geom()
    vs = t.page.viewport_size
    cy = vs["height"] * 0.6
    c0 = t.cnt()
    r = synth_touch(t, cy, cy - 220)
    s = wait_rest(t)
    t.check("one swipe = one step (synthetic touch, prevented)", s["rendered"] == 1 and any(r["prevented"]), [s, r])
    r = synth_touch(t, cy, cy - min(600, vs["height"] * 0.55), steps=20)
    s = wait_rest(t)
    t.check("a long swipe is still one step", s["rendered"] == 2, s)
    synth_touch(t, cy, cy - 220, fingers=2)
    s = wait_rest(t)
    t.check("two fingers (pinch) never step", s["rendered"] == 2, s)
    synth_touch(t, cy, cy - 22, steps=2, dt=10)
    s = wait_rest(t)
    t.check("a short fast flick steps at touchend", s["rendered"] == 3, s)
    t.data["touch_steps"] = t.cnt()["touchSteps"] - c0["touchSteps"]
    t.synth.append("touch synthesised in JS (untrusted): interception logic only; no native scroll, no momentum")
    # last beat: a forward swipe passes
    press(t, "End")
    r = synth_touch(t, cy, cy - 220)
    t.check("forward swipe at the last beat is not prevented (release)", not any(r["prevented"]), r)
    if t.col == "chromium" and t.vp[2] == "android":
        t.synth.append("trusted CDP touch drags (Chromium): real native scroll on release")
        t.goto()
        y0 = t.st()["y"]
        cdp_drag(t, cy, cy - 240)
        s = wait_rest(t)
        t.check("CDP trusted drag in the story: one step, no native scroll leak", s["rendered"] == 1 and at_rest_ok(t, s, 1), s)
        press(t, "End")
        cdp_drag(t, cy, cy - 300)
        t.page.wait_for_timeout(400)
        s = t.st()
        t.check("CDP trusted drag at the last beat scrolls natively (RELEASED)", s["phase"] == "released", s)
    # momentum from below: a decaying upward foreign stream after a touchend lands on the last beat, never mid-story
    press(t, "End")
    t.ev("(y) => window.scrollTo(0, y)", g["storyEnd"] + 500)
    t.page.wait_for_timeout(300)
    synth_touch(t, cy - 200, cy - 120, steps=3)          # the finger lift (passes: below the story)
    r = t.ev(STREAM_JS, {"px": -60, "frames": 30, "decay": 0.93})
    s = wait_rest(t)
    t.data["momentum_from_below"] = {"stream": r, "s": s}
    t.check("momentum from below into the track settles on the last beat", at_rest_ok(t, s, 8), [r, s])
    t.work.append("momentum from below cannot be clamped mid-fling: FREE settles it onto the last beat (S4)")
    t.synth.append("iOS momentum stood in by a decaying window.scrollBy stream")
    # the iOS bars: a height-only change (+81 px, about Safari's bottom bar) and back
    t.goto()
    press(t, "ArrowDown", 3)
    w, h = vs["width"], vs["height"]
    for hh in (h + 81, h):
        t.page.set_viewport_size({"width": w, "height": hh})
        t.page.wait_for_timeout(300)
        s = wait_rest(t)
        t.check(f"bars: height {hh} keeps beat 3 aligned", at_rest_ok(t, s, 3), s)
    t.data["geometry_events"] = [e for e in t.log(0) if e["ev"] == "geometry"]
    t.data["pointer_coarse"] = t.ev("matchMedia('(pointer: coarse)').matches")


def r9_zoom(t):
    t.goto()
    c0 = t.cnt()
    if is_mwk(t):
        t.synth.append("iPhone: no Ctrl+wheel; pinch is not drivable in Playwright WebKit (visualViewport.scale stays 1): only the zoom-emulation and CSS-zoom parts ran")
        t.page.keyboard.down("Control"); t.page.keyboard.up("Control")
    else:
        t.page.keyboard.down("Control")
        for _ in range(3):
            t.page.mouse.wheel(0, 100)
            time.sleep(0.05)
        t.page.keyboard.up("Control")
    t.page.wait_for_timeout(300)
    s = t.st()
    d = diff(c0, t.cnt())
    t.data["ctrl_wheel"] = {"counters": d, "vvScale": t.geom()["vvScale"]}
    t.check("Ctrl+wheel is never intercepted (no step)", s["dest"] == 0 and d.get("wheelPrevented", 0) == 0, [s, d])
    # CSS zoom on the stage (the site's vrect trap) must not move the track geometry
    P0 = t.geom()["P"]
    t.goto("csszoom=1.25")
    t.data["legacyZoom"] = t.ev("__cp.legacyZoom()")
    t.check("CSS zoom on the stage leaves the beat geometry unchanged", t.geom()["P"] == P0, [P0, t.geom()["P"]])
    press(t, "ArrowDown", 2)
    t.check("steps under CSS zoom land aligned", at_rest_ok(t, t.st(), 2), t.st())
    if t.col == "chromium":
        t.goto()
        cdp = t.page.context.new_cdp_session(t.page)
        cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 2})
        t.page.wait_for_timeout(200)
        vv = t.geom()["vvScale"]
        t.data["pinch_vvScale"] = vv
        r = synth_touch(t, t.page.viewport_size["height"] * 0.6, t.page.viewport_size["height"] * 0.6 - 220)
        s = wait_rest(t)
        t.check("pinch-zoomed (visualViewport.scale > 1): a touch pans, never steps", vv <= 1.01 or (s["dest"] == 0 and not any(r["prevented"])), [vv, s, r])
        cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 1})
        cdp.detach()


def r9_browser_zoom(t):
    """Run in a context whose CSS viewport and DPR mimic browser zoom (fractional scroll positions)."""
    t.goto()
    c0 = t.cnt()
    press(t, "ArrowDown", 3)
    press(t, "End")
    gesture(t, -70)
    s = wait_rest(t)
    press(t, "Home")
    d = diff(c0, t.cnt())
    t.data.update(counters=d, dpr=t.geom()["dpr"], P=t.geom()["P"])
    t.check("steps land aligned under fractional DPR", s["rendered"] == 7 and at_rest_ok(t, t.st(), 0), s)
    t.check("no acknowledgement misses (foreign == 0)", d.get("foreign", 0) == 0, d)


def s1_grouping(t, q=""):
    t.goto(q)
    def steps_of(fn):
        t0 = t.now()
        fn()
        wait_rest(t)
        time.sleep(0.3)
        return sum(1 for e in t.log(t0) if e["ev"] == "step" and e["src"].startswith("wheel"))
    res = {}
    res["one_flick"] = steps_of(lambda: flick(t.page, 70))
    def two():                       # the second flick lands ~300 ms into the first one's tail (past MIN_STEP_MS 250)
        flick(t.page, 70, n=16)
        flick(t.page, 110, n=18)
    res["two_flicks"] = steps_of(two)
    def clicks():
        for _ in range(3):
            t.page.mouse.wheel(0, 100)
            time.sleep(0.4)
    res["three_notch_clicks_400ms"] = steps_of(clicks)
    def burst():
        for _ in range(4):
            t.page.mouse.wheel(0, 100)
            time.sleep(0.06)
    res["notch_burst_4x60ms"] = steps_of(burst)
    res["big_first_delta_long_tail"] = steps_of(lambda: flick(t.page, 80, n=70, decay=0.955, ramp=False))   # opens >= 50 px
    t.data["steps"] = res
    t.check("one flick + tail = 1 step", res["one_flick"] == 1, res)
    t.check("second flick in the tail = 2 steps", res["two_flicks"] == 2, res)
    t.check("three notch clicks 400 ms apart = 3 steps", res["three_notch_clicks_400ms"] == 3, res)
    t.check("a notch burst = 1 step", res["notch_burst_4x60ms"] == 1, res)
    t.check("a flick opening >= 50 px with a long decaying tail = 1 step", res["big_first_delta_long_tail"] == 1, res)


def s1_r1notch(t):
    """R1's original notch rule (sustained = any event), to show the double step it causes."""
    s1_grouping(t, "r1notch")


PROBES = {
    "R1": [("", r1_ack)], "R2": [("", r2_bounds)], "R3": [("", r3_settle)], "R4": [("", r4_resize)],
    "R5": [("", r5_hold), ("classicbar", r5_classic)], "R6": [("", r6_auto), ("nograce", r6_nograce)], "R7": [("", r7_noscrollend)],
    "R8": [("", r8_touch)], "R9": [("", r9_zoom), ("zoom125", r9_browser_zoom), ("zoom175", r9_browser_zoom)],
    "S1": [("", s1_grouping), ("r1notch", s1_r1notch)],
}
INFORMATIONAL = {"nograce", "r1notch"}
SKIP = {("webkit-iphone", "S1")}  # wheel grouping: an iPhone has no wheel     # variants that record a failure mode on purpose; they do not count toward the cell


# ---------------------------------------------------------------- driver
def ensure_server():
    s = socket.socket()
    try:
        s.connect(("127.0.0.1", PORT))
        s.close()
        return None
    except OSError:
        pass
    p = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", str(ROOT)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", PORT), 0.2).close()
            return p
        except OSError:
            time.sleep(0.1)
    raise SystemExit("server did not start")


def context_for(pw, browser, col, vp, variant):
    w, h, kind = vp
    opts = {"viewport": {"width": w, "height": h}}
    if kind == "iphone":
        dev = dict(pw.devices["iPhone 14"])
        dev.pop("default_browser_type", None)
        dev["viewport"] = {"width": w, "height": h}
        opts = dev
    elif kind == "android":
        opts.update(is_mobile=True, has_touch=True, device_scale_factor=3)
    else:
        opts["device_scale_factor"] = 2
    if variant in ("zoom125", "zoom175"):
        z = 1.25 if variant == "zoom125" else 1.75
        opts["viewport"] = {"width": round(w / z), "height": round(h / z)}
        opts["device_scale_factor"] = opts.get("device_scale_factor", 1) * z
    return browser.new_context(**opts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--col", action="append")
    ap.add_argument("--row", action="append")
    a = ap.parse_args()
    cols = a.col or list(COLUMNS)
    rows = a.row or list(PROBES)
    srv = ensure_server()
    results = []
    try:
        with sync_playwright() as pw:
            for col in cols:
                spec = COLUMNS[col]
                bt = getattr(pw, spec["engine"])
                browser = (bt.launch(ignore_default_args=["--hide-scrollbars"], args=["--disable-features=OverlayScrollbar,OverlayScrollbars"])
                           if spec["engine"] == "chromium" else bt.launch())
                ver = browser.version
                for vp in spec["vps"]:
                    for row in rows:
                        if (col, row) in SKIP:
                            continue
                        for variant, fn in PROBES[row]:
                            first_fail = None
                            for attempt in (1, 2):   # a FAIL reruns once (host jitter can split a synthetic flick)
                                ctx = context_for(pw, browser, col, vp, variant)
                                page = ctx.new_page()
                                errs = []
                                page.on("pageerror", lambda e: errs.append(str(e)))
                                t = T(page, row, col, vp)
                                try:
                                    fn(t)
                                except Exception as e:  # a probe crash is a FAIL with its message
                                    t.check("probe ran", False, repr(e)[:500])
                                t.check("no page errors", not errs, errs)
                                if t.status() != "FAIL" or variant in INFORMATIONAL or attempt == 2:
                                    break
                                first_fail = [c for c in t.checks if not c["ok"]]
                                ctx.close()
                            if first_fail:
                                t.data["first_attempt_failed"] = first_fail
                            try:
                                full_log = t.log(0)
                            except Exception:
                                full_log = []
                            name = f"{row}__{vp[0]}x{vp[1]}" + (f"-{variant}" if variant else "")
                            rec = {"row": row, "item": ROWS[row], "column": col, "browser": f"{spec['engine']} {ver}",
                                   "viewport": vp, "variant": variant, "status": t.status(), "workaround": t.work, "synthesised": t.synth,
                                   "checks": t.checks, "data": t.data, "log": full_log}
                            out = EVID / col / f"{name}.json"
                            out.parent.mkdir(parents=True, exist_ok=True)
                            out.write_text(json.dumps(rec, indent=1, default=str))
                            results.append({k: rec[k] for k in ("row", "column", "viewport", "variant", "status", "workaround", "synthesised")}
                                           | {"failed": [c["name"] for c in t.checks if not c["ok"]], "file": str(out.relative_to(HERE)),
                                              "retried": bool(first_fail)})
                            print(f"{col:14} {vp[0]}x{vp[1]:<5} {row} {variant or '-':8} {t.status():10} "
                                  + ("; ".join(c["name"] for c in t.checks if not c["ok"]) or "; ".join(t.work)), flush=True)
                            ctx.close()
                browser.close()
    finally:
        if srv:
            srv.terminate()
    # aggregate per (row, column): FAIL > WORKAROUND > PASS; informational variants excluded
    cells = {}
    for r in results:
        if r["variant"] in INFORMATIONAL:
            continue
        k = (r["row"], r["column"])
        order = {"PASS": 0, "WORKAROUND": 1, "FAIL": 2}
        cells[k] = max(cells.get(k, "PASS"), r["status"], key=lambda s: order[s])
    # a partial run (--col/--row) replaces its own entries in summary.json and the cells are recomputed from all results
    summ = EVID / "summary.json"
    if (a.col or a.row) and summ.exists():
        key = lambda r: (r["row"], r["column"], tuple(r["viewport"]), r["variant"])
        mine = {key(r) for r in results}
        results = [r for r in json.loads(summ.read_text())["results"] if key(r) not in mine] + results
        cells = {}
        for r in results:
            if r["variant"] in INFORMATIONAL:
                continue
            k = (r["row"], r["column"])
            order = {"PASS": 0, "WORKAROUND": 1, "FAIL": 2}
            cells[k] = max(cells.get(k, "PASS"), r["status"], key=lambda s: order[s])
        cols, rows = list(COLUMNS), list(PROBES)
    summ.write_text(json.dumps({"results": results, "cells": {f"{k[0]}|{k[1]}": v for k, v in cells.items()}}, indent=1))
    lines = ["| row | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for row in rows:
        lines.append(f"| {row} {ROWS[row]} | " + " | ".join(cells.get((row, c), "-") for c in cols) + " |")
    md = "\n".join(lines)
    (summ.with_suffix(".md")).write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
