#!/usr/bin/env python3
"""Generate tests/fixtures/input/*.json from the models in LABELS.md (C1). Deterministic: no clock, no randomness.

Run: python3 tests/fixtures/input/gen_fixtures.py   (rewrites every fixture; `git diff` shows any change)
Expectations live only in LABELS.md; the fixtures carry the input streams and their DOM context, nothing else.
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
END_GAP = 120  # a tail ends when its next event would come > 120 ms after the last one

FINGER_60 = (3, 8, 16, 26, 34, 38)
FINGER_120 = (2, 4, 8, 13, 17, 19)
FINGER_2ND = (4, 12, 24, 38, 48, 52)
DRAG_208 = 14  # 4 px every 16 ms over 208 ms = events at 0..208


# ---------- frame models (float deltas per frame; sign carried by the caller) ----------
def flick_frames(t0, *, dt=16, finger=FINGER_60, peak=None, r=0.95, sign=1, until=None):
    """Finger phase then momentum peak*r^k, one float delta per frame, until it is negligible or `until`."""
    peak = finger[-1] if peak is None else peak
    out, t = [], t0
    for d in finger:
        if until is not None and t >= until:
            return out
        out.append((t, sign * float(d)))
        t += dt
    k = 1
    while True:
        d = peak * r ** k
        if d < 0.02 or (until is not None and t >= until):
            return out
        out.append((t, sign * d))
        t += dt
        k += 1


def decay_frames(t0, first, *, dt=16, r=0.95, sign=1):
    """A flick that opens on `first` px (D1 rows): first, first*r, first*r^2, ..."""
    out, t, k = [], t0, 0
    while True:
        d = first * r ** k
        if d < 0.02:
            return out
        out.append((t, sign * d))
        t += dt
        k += 1


def quantise(frames):
    """Whole-px events from float frames (fractions carry over, per sign); stop at the END_GAP rule."""
    events, carry, last_t, last_sign = [], 0.0, None, 0
    for t, d in frames:
        s = 1 if d > 0 else -1
        if s != last_sign:
            carry = 0.0
            last_sign = s
        carry += abs(d)
        if carry < 1:
            continue
        q = int(carry)
        if last_t is not None and t - last_t > END_GAP:
            break
        carry -= q
        events.append((t, s * q))
        last_t = t
    return events


def jank(frames, *, start=160, gaps=(96, 16, 16, 112, 16, 80, 16, 16)):
    """Coalesce frames from `start` on into deliveries after the cycling gaps (busy main thread)."""
    out = [(t, d) for t, d in frames if t < start]
    rest = [(t, d) for t, d in frames if t >= start]
    if not rest:
        return out
    deliver, i, j = out[-1][0] if out else start, 0, 0
    while j < len(rest):
        deliver += gaps[i % len(gaps)]
        i += 1
        s = 0.0
        while j < len(rest) and rest[j][0] <= deliver:
            s += rest[j][1]
            j += 1
        if s:
            out.append((deliver, s))
    return out


# ---------- event builders ----------
def wheel(t, dy, *, dx=0, mode=0, wdy=None, ctrl=False, meta=False, target="body", tag=None):
    ev = {"type": "wheel", "t": t, "deltaY": dy, "deltaX": dx, "deltaMode": mode,
          "wheelDeltaY": (-round(dy * 1.2) if wdy is None else wdy), "ctrlKey": ctrl, "metaKey": meta,
          "target": target}
    if tag:
        ev["tag"] = tag
    return ev


def wheels(pairs, **kw):
    return [wheel(t, d, **kw) for t, d in pairs]


def notch(t, sign=1, **kw):
    return wheel(t, 100 * sign, wdy=-120 * sign, **kw)


def ff_notch(t, sign=1, **kw):
    return wheel(t, 3 * sign, mode=1, wdy=-120 * sign, **kw)


def drag(t0, n=DRAG_208, px=4, dt=16):
    return [(t0 + i * dt, px) for i in range(n)]


def key(t, k, *, shift=False, ctrl=False, alt=False, meta=False, repeat=False, prevented=False, target="body"):
    return {"type": "keydown", "t": t, "key": k, "shiftKey": shift, "ctrlKey": ctrl, "altKey": alt,
            "metaKey": meta, "repeat": repeat, "defaultPrevented": prevented, "target": target}


def touch_seq(moves, *, x0=200, y0=600, dt=16, t0=0, end_after=8, fingers=1):
    """moves: list of (dx, dy_screen) cumulative offsets per move (screen y: negative = finger up = forward)."""
    def pts(dx, dy):
        return [{"x": x0 + dx + 40 * f, "y": y0 + dy} for f in range(fingers)]
    evs = [{"type": "touchstart", "t": t0, "touches": pts(0, 0), "target": "body"}]
    t = t0
    for dx, dy in moves:
        t += dt
        evs.append({"type": "touchmove", "t": t, "touches": pts(dx, dy), "target": "body"})
    evs.append({"type": "touchend", "t": t + end_after, "touches": [], "target": "body"})
    return evs


# ---------- DOM context ----------
BASE_NODES = {"html": {"tag": "HTML", "parent": None}, "body": {"tag": "BODY", "parent": "html"}}


def nodes(**extra):
    n = {k: dict(v) for k, v in BASE_NODES.items()}
    n.update(extra)
    return n


def fixture(name, events, *, env=None, dom=None):
    e = {"pinHeight": 800, "innerHeight": 800, "visualScale": 1, "enabled": True, "consumer": {"mode": "intercept"}}
    e.update(env or {})
    return {"name": name, "synthetic": True, "env": e, "nodes": dom or nodes(), "events": events}


def std_flick(t0=0, sign=1, **kw):
    return quantise(flick_frames(t0, sign=sign, **kw))


def build():
    F = {}

    # --- trackpad (smooth) ---
    F["tp-flick-60hz"] = fixture("tp-flick-60hz", wheels(std_flick()))
    F["tp-flick-120hz"] = fixture("tp-flick-120hz", wheels(quantise(flick_frames(0, dt=8, finger=FINGER_120, r=0.975))))
    F["tp-flick-up"] = fixture("tp-flick-up", wheels(std_flick(sign=-1)))
    F["tp-long-tail"] = fixture("tp-long-tail", wheels(std_flick(r=0.97)))
    F["tp-tail-jank-60hz"] = fixture("tp-tail-jank-60hz", wheels(quantise(jank(flick_frames(0)))))
    F["tp-tail-jank-120hz"] = fixture("tp-tail-jank-120hz", wheels(quantise(jank(
        flick_frames(0, dt=8, finger=FINGER_120, r=0.975)))))
    F["tp-brush"] = fixture("tp-brush", wheels([(0, 2), (16, 2), (32, 2)]))
    two = flick_frames(0, until=400) + flick_frames(400, finger=FINGER_2ND)
    F["tp-two-flicks-early"] = fixture("tp-two-flicks-early", wheels(quantise(two)))
    three = flick_frames(0, until=400) + flick_frames(400, finger=FINGER_2ND, until=800) + \
        flick_frames(800, finger=FINGER_2ND)
    F["tp-three-flicks"] = fixture("tp-three-flicks", wheels(quantise(three)))
    apart, t0 = [], 0
    for _ in range(3):
        f = std_flick(t0)
        apart += f
        t0 = f[-1][0] + 300
    F["tp-three-flicks-apart"] = fixture("tp-three-flicks-apart", wheels(apart))
    rev = flick_frames(0, until=400) + flick_frames(400, sign=-1)
    F["tp-reverse"] = fixture("tp-reverse", wheels(quantise(rev)))
    edge = quantise(flick_frames(0, until=400)) + [(400 + i * 16, d) for i, d in enumerate((-4, -4, -4, -2, -1, -1))]
    F["tp-reverse-edge-12"] = fixture("tp-reverse-edge-12", wheels(edge))
    jit = []
    slots = {800: -4, 816: -4, 832: -3}
    for t, d in flick_frames(0):
        jit.append((t, float(slots[t])) if t in slots else (t, d))
    F["tp-jitter-11"] = fixture("tp-jitter-11", wheels(quantise_mixed(jit, slots)))
    F["tp-drag-quiet-139"] = fixture("tp-drag-quiet-139", wheels(drag(0) + drag(208 + 139)))
    F["tp-drag-quiet-141"] = fixture("tp-drag-quiet-141", wheels(drag(0) + drag(208 + 141)))
    F["tp-sustained-drag"] = fixture("tp-sustained-drag", wheels(drag(0, n=125, px=20)))

    # --- mouse wheel (notch) ---
    F["mw-click"] = fixture("mw-click", [notch(0)])
    F["mw-click-firefox"] = fixture("mw-click-firefox", [ff_notch(0)])
    F["mw-click-up"] = fixture("mw-click-up", [notch(0, -1)])
    F["mw-burst"] = fixture("mw-burst", [notch(t) for t in (0, 50, 100, 150)])
    F["mw-three-clicks"] = fixture("mw-three-clicks", [notch(t) for t in (0, 400, 800)])
    F["mw-quiet-219"] = fixture("mw-quiet-219", [notch(0), notch(219)])
    F["mw-quiet-221"] = fixture("mw-quiet-221", [notch(0), notch(221)])
    F["mw-spin-sustained"] = fixture("mw-spin-sustained", [notch(t) for t in range(0, 2001, 40)])
    F["mw-reverse"] = fixture("mw-reverse", [notch(0), notch(150, -1)])

    # --- D1 ---
    for first in (60, 50, 49):
        name = f"d1-first-{first}"
        F[name] = fixture(name, wheels(quantise(decay_frames(0, first))))

    # --- class changes ---
    F["cls-notch-then-flick"] = fixture("cls-notch-then-flick", [notch(0)] + wheels(std_flick(300)))
    F["cls-drag-then-notch-200"] = fixture("cls-drag-then-notch-200", wheels(drag(0)) + [notch(208 + 200)])
    F["cls-notch-then-drag-180"] = fixture("cls-notch-then-drag-180", [notch(0)] + wheels(drag(180, n=20)))

    # --- bypass ---
    pinch = [wheel(i * 16, 3 if i < 15 else -3, wdy=0, ctrl=True) for i in range(30)]
    F["bp-ctrl-pinch"] = fixture("bp-ctrl-pinch", pinch)
    F["bp-ctrl-wheel"] = fixture("bp-ctrl-wheel", [notch(t, ctrl=True) for t in (0, 300, 600)])
    F["bp-meta-wheel"] = fixture("bp-meta-wheel", [notch(t, meta=True) for t in (0, 300, 600)])
    F["bp-pinch-then-flick"] = fixture("bp-pinch-then-flick", pinch + wheels(std_flick(pinch[-1]["t"] + 300), tag="flick"))
    F["bp-horizontal"] = fixture("bp-horizontal", [wheel(i * 16, 2, dx=20) for i in range(20)])
    F["bp-dialog-wheel"] = fixture("bp-dialog-wheel", wheels(std_flick(), target="p"),
                                   dom=nodes(dlg={"tag": "DIALOG", "parent": "body", "open": True},
                                             p={"tag": "P", "parent": "dlg"}))
    F["bp-textarea-wheel"] = fixture("bp-textarea-wheel", wheels(std_flick(), target="ta"),
                                     dom=nodes(ta={"tag": "TEXTAREA", "parent": "body"}))
    F["bp-editable-wheel"] = fixture("bp-editable-wheel", wheels(std_flick(), target="span"),
                                     dom=nodes(ed={"tag": "DIV", "parent": "body", "contenteditable": True},
                                               span={"tag": "SPAN", "parent": "ed"}))
    box = {"tag": "DIV", "parent": "body", "scroll": {"overflowY": "auto", "top": 0, "height": 1000, "client": 300}}
    F["bp-nested-can-scroll"] = fixture("bp-nested-can-scroll", wheels(std_flick(), target="p"),
                                        dom=nodes(box=box, p={"tag": "P", "parent": "box"}))
    box_end = {**box, "scroll": {**box["scroll"], "top": 700}}
    F["bp-nested-at-end"] = fixture("bp-nested-at-end", wheels(std_flick(), target="p"),
                                    dom=nodes(box=box_end, p={"tag": "P", "parent": "box"}))
    F["bp-consumer-pass"] = fixture("bp-consumer-pass", wheels(std_flick()), env={"consumer": {"mode": "pass"}})
    F["bp-consumer-takeover"] = fixture("bp-consumer-takeover", wheels(std_flick()),
                                        env={"consumer": {"mode": "takeover", "at": 200}})
    F["bp-disabled"] = fixture("bp-disabled", wheels(std_flick()) + [notch(3000)], env={"enabled": False})

    # --- keys ---
    for name, k, shift in (("key-arrowdown", "ArrowDown", False), ("key-arrowup", "ArrowUp", False),
                           ("key-pagedown", "PageDown", False), ("key-pageup", "PageUp", False),
                           ("key-space", " ", False), ("key-shift-space", " ", True),
                           ("key-home", "Home", False), ("key-end", "End", False)):
        F[name] = fixture(name, [key(0, k, shift=shift)])
    F["key-left-right"] = fixture("key-left-right", [key(0, "ArrowLeft"), key(500, "ArrowRight")])
    F["key-held-arrowdown"] = fixture("key-held-arrowdown", [key(0, "ArrowDown")] +
                                      [key(500 + 33 * i, "ArrowDown", repeat=True) for i in range(46)])
    F["key-three-presses"] = fixture("key-three-presses", [key(t, "ArrowDown") for t in (0, 100, 200)])
    F["key-in-fields"] = fixture(
        "key-in-fields", [key(i * 500, "ArrowDown", target=tg) for i, tg in enumerate(("inp", "ta", "sel", "span"))],
        dom=nodes(inp={"tag": "INPUT", "parent": "body"}, ta={"tag": "TEXTAREA", "parent": "body"},
                  sel={"tag": "SELECT", "parent": "body"}, ed={"tag": "DIV", "parent": "body", "contenteditable": True},
                  span={"tag": "SPAN", "parent": "ed"}))
    F["key-space-on-controls"] = fixture(
        "key-space-on-controls", [key(i * 500, " ", target=tg) for i, tg in enumerate(("a", "btn", "sum", "rb"))],
        dom=nodes(a={"tag": "A", "parent": "body"}, btn={"tag": "BUTTON", "parent": "body"},
                  sum={"tag": "SUMMARY", "parent": "body"}, rb={"tag": "DIV", "parent": "body", "role": "button"}))
    F["key-arrow-on-button"] = fixture("key-arrow-on-button", [key(0, "ArrowDown", target="btn")],
                                       dom=nodes(btn={"tag": "BUTTON", "parent": "body"}))
    F["key-modifiers"] = fixture("key-modifiers", [key(0, "ArrowDown", ctrl=True), key(500, "ArrowDown", alt=True),
                                                   key(1000, "ArrowDown", meta=True)])
    F["key-default-prevented"] = fixture("key-default-prevented", [key(0, "ArrowDown", prevented=True)])
    F["key-dialog-open"] = fixture("key-dialog-open", [key(0, "ArrowDown")],
                                   dom=nodes(dlg={"tag": "DIALOG", "parent": "body", "open": True}))
    F["key-consumer-pass"] = fixture("key-consumer-pass", [key(0, "ArrowDown")], env={"consumer": {"mode": "pass"}})

    # --- touch ---
    F["touch-swipe-up"] = fixture("touch-swipe-up", touch_seq([(0, -12 * i) for i in range(1, 11)]))
    F["touch-swipe-down"] = fixture("touch-swipe-down", touch_seq([(0, 12 * i) for i in range(1, 11)]))
    F["touch-long-drag"] = fixture("touch-long-drag", touch_seq([(0, -16 * i) for i in range(1, 26)]))
    F["touch-short-flick"] = fixture("touch-short-flick", touch_seq([(0, -10), (0, -20)]))
    F["touch-short-slow"] = fixture("touch-short-slow", touch_seq([(0, -2 * i) for i in range(1, 11)], dt=40))
    F["touch-horizontal"] = fixture("touch-horizontal", touch_seq([(12 * i, -i) for i in range(1, 11)]))
    F["touch-pinch"] = fixture("touch-pinch", touch_seq([(0, -12 * i) for i in range(1, 11)], fingers=2))
    sf = touch_seq([(0, -6)])[:-1]  # start + one 6 px move, no end yet
    sf.append({"type": "touchstart", "t": 24, "touches": [{"x": 200, "y": 594}, {"x": 240, "y": 594}], "target": "body"})
    for i in range(1, 11):
        y = 594 - 12 * i
        sf.append({"type": "touchmove", "t": 24 + 16 * i, "touches": [{"x": 200, "y": y}, {"x": 240, "y": y}],
                   "target": "body"})
    sf.append({"type": "touchend", "t": 24 + 16 * 10 + 8, "touches": [], "target": "body"})
    F["touch-second-finger"] = fixture("touch-second-finger", sf)
    sm = touch_seq([(0, -6)])[:-1]  # the second finger's touchstart is never seen (e.g. it landed elsewhere)
    for i in range(1, 11):
        y = 594 - 12 * i
        sm.append({"type": "touchmove", "t": 16 + 16 * i, "touches": [{"x": 200, "y": y}, {"x": 240, "y": y}],
                   "target": "body"})
    sm.append({"type": "touchend", "t": 16 + 16 * 10 + 8, "touches": [], "target": "body"})
    F["touch-second-finger-move"] = fixture("touch-second-finger-move", sm)
    # Sol C1-sol-1 repros (post-hoc rows in LABELS.md)
    F["tp-reverse-jitter-after"] = fixture("tp-reverse-jitter-after", wheels([(0, 20), (16, -12), (32, 1)]))
    F["bp-nested-reverse-up"] = fixture("bp-nested-reverse-up", [notch(0, target="p", tag="down"), notch(150, -1, target="p")],
                                        dom=nodes(box=box_end, p={"tag": "P", "parent": "box"}))
    trickle = [(0, 60)] + [(100 * i, round(1.0 - (i - 1) * 0.24 / 9, 4)) for i in range(1, 11)]
    F["d1-trickle"] = fixture("d1-trickle", wheels(trickle))
    tap = [{"type": "touchstart", "t": 0, "touches": [{"x": 200, "y": 600}], "target": "body"},
           {"type": "touchstart", "t": 20, "touches": [{"x": 200, "y": 600}, {"x": 240, "y": 600}], "target": "body"},
           {"type": "touchend", "t": 60, "touches": [{"x": 200, "y": 600}], "target": "body"}]
    for i in range(1, 11):
        tap.append({"type": "touchmove", "t": 60 + 16 * i, "touches": [{"x": 200, "y": 600 - 12 * i}], "target": "body"})
    tap.append({"type": "touchend", "t": 60 + 16 * 10 + 8, "touches": [], "target": "body"})
    F["touch-second-finger-tap"] = fixture("touch-second-finger-tap", tap)
    F["touch-zoomed"] = fixture("touch-zoomed", touch_seq([(0, -12 * i) for i in range(1, 11)]),
                                env={"visualScale": 1.5})
    return F


def quantise_mixed(frames, slots):
    """quantise(), but the jitter slots pass through exactly (they are whole px already)."""
    out, carry, last_t = [], 0.0, None
    for t, d in frames:
        if t in slots:
            out.append((t, int(d)))
            last_t = t
            continue
        carry += d
        if carry < 1:
            continue
        q = int(carry)
        if last_t is not None and t - last_t > END_GAP:
            break
        carry -= q
        out.append((t, q))
        last_t = t
    return out


def main():
    fx = build()
    for old in HERE.glob("*.json"):
        if old.stem not in fx:
            old.unlink()
    for name, data in sorted(fx.items()):
        (HERE / f"{name}.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    print(f"{len(fx)} fixtures")


if __name__ == "__main__":
    main()
