"""C2: the story state harness's driver (tests/checkpoint/test_story_state.py uses it).

Drives REAL input (page.mouse.wheel, page.keyboard, window.scrollTo) into the homepage story through Playwright and
reads the engine's state. It never touches assets/shared/checkpoint-input.js (C1's module is not wired in yet).

State source, in this order:
  1. window.FEStory.state()   -- what C3 must expose. The harness assumes this shape (C3 may add fields):
        { phase: "rest" | "dip" | "free" | "released" | <anything else = moving>,
          dest: int,        // signed destination, index into BEATS (ICX terms: dest)
          rendered: int,    // last checkpoint fully landed (ICX terms: rendered)
          T: number,        // story time in seconds (alias: time)
          trackY: number,   // scrollY of the dest checkpoint's track position (ICX-CHECKPOINT.2: scrollY within 1 px)
          beat: string,     // the active caption's beat id, a BEATS entry (ICX-CHECKPOINT.2)
          dip: boolean }    // optional; phase == "dip" also counts
     "released" counts only with scrollY below the pinned track (ICX-REST.1).
  2. window.__site.state()    -- the base engine: { shown, target, vel, intro, dip, ... } (assets/story/site.js).
     The base has no gesture layer, no dest and no rendered; a wheel/key is scrubbed through mapScroll. The harness
     derives only what can honestly be derived: "rest" = the playhead is settled (shown == target, vel 0, no intro,
     no dip) exactly on a checkpoint rest frame from ICX-DEST's table.

Rest frames come from __site.map() (ICX-DEST "rest" column): make = HOLD, look/know/grow/chase = scene end - 0.02,
yours = scene start + 0.28, price = hold start + 0.3, note = brand start + 0.2, end = brand end - 0.05.
Pinned count per mode: desktop (>= 1024 px) 9, tablet (640-1023 px) 5.

Input model: one wheel event of 100 px = one notch gesture; gestures are spaced > QUIET_NOTCH (220 ms) apart.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from playwright.sync_api import Browser, Page

BEATS = ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"]
SLUGS = ["new-invoice", "templates", "invoices", "dashboard", "email", "your-data", "price", "a-note", "get-the-app"]
SEED = 20261015
REST_TOL = 0.015         # seconds of story time
RATE_CEILING = 3.0       # ICX-SIGNED.7
RATE_TOL = 1.05          # jitter allowance on the 3x ceiling (3.15x), measured over >= 100 ms windows


@dataclass(frozen=True)
class Cell:
    name: str
    width: int
    height: int
    theme: str

    @property
    def id(self) -> str:
        return f"{self.name}-{self.theme}"

    @property
    def n_pinned(self) -> int:
        return 9 if self.width >= 1024 else 5

    @property
    def last(self) -> int:
        return self.n_pinned - 1


CELLS = [
    Cell("desktop", 1440, 900, "dark"),
    Cell("desktop", 1440, 900, "light"),
    Cell("tablet", 820, 1180, "dark"),
    Cell("tablet", 820, 1180, "light"),
]

_INIT = """
(() => {
  window.__c2hist = [];
  for (const k of ['pushState', 'replaceState']) {
    const o = history[k];
    history[k] = function (s, t, u) { let st = null; try { st = window.__c2read(); } catch (e) { /* not ready */ } window.__c2hist.push([k, u == null ? null : String(u), st]); return o.apply(this, arguments); };
  }
  window.__c2read = () => {
    let fe = null;
    const F = window.FEStory;
    if (F) { const st = typeof F.state === 'function' ? F.state() : F.state; if (st) fe = JSON.parse(JSON.stringify(st)); }
    let site = null;
    if (window.__site && window.__site.state) { const s = window.__site.state(); site = { shown: s.shown, target: s.target, vel: s.vel, intro: s.intro, dip: s.dip }; }
    return { fe, site, y: window.scrollY, t: performance.now() };
  };
  window.__c2rec = null;
  window.__c2start = () => {
    window.__c2rec = [];
    const tick = () => { if (!window.__c2rec) return; if (window.__c2rec.length < 40000) window.__c2rec.push(window.__c2read()); requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  };
})();
"""


@dataclass
class Snap:
    src: str                 # "FEStory" or "__site"
    T: float
    y: float
    phase: str
    dest: int | None
    rendered: int | None
    dip: bool
    index: int | None        # the checkpoint the playhead is resting on, else None
    is_rest: bool
    released: bool
    t: float                 # performance.now() ms

    def describe(self) -> str:
        where = f"REST({BEATS[self.index]})" if self.index is not None else "not on a rest frame"
        eng = ("FEStory" if self.src == "FEStory" else "__site.state() only (no dest/rendered)")
        return (f"T={self.T:.3f} scrollY={self.y:.0f} phase={self.phase!r} dest={self.dest} rendered={self.rendered} "
                f"-> {where}; engine={eng}")


@dataclass
class Result:
    status: str              # rest | released | stalled | timeout
    snap: Snap
    elapsed: float


@dataclass
class Info:
    rest: list[float]
    end_y: float
    n: int


def _rest_times(m: dict, n: int) -> list[float]:
    segs = {s["id"]: s for s in m["segs"]}
    out = [m["H"]]
    for sid in ("look", "know", "grow", "chase"):
        out.append(round(segs[sid]["T1"] - 0.02, 3))
    if "yours" in segs:
        out.append(round(segs["yours"]["T0"] + 0.28, 3))
        out.append(round(segs["price"]["T0"] + 0.3, 3))
        out.append(round(segs["brand"]["T0"] + 0.2, 3))
        out.append(round(segs["brand"]["T1"] - 0.05, 3))
    return out[:n]


class Story:
    def __init__(self, ctx, page: Page, cell: Cell, info: Info):
        self.ctx, self.page, self.cell, self.info = ctx, page, cell, info

    # ---- open / close -------------------------------------------------------------------------------------------
    @classmethod
    def open(cls, browser: Browser, url: str, cell: Cell) -> "Story":
        ctx = browser.new_context(viewport={"width": cell.width, "height": cell.height}, reduced_motion="no-preference")
        ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{cell.theme}')}}catch(e){{}}")
        ctx.add_init_script(_INIT)
        page = ctx.new_page()
        page.goto(url, wait_until="load")
        page.wait_for_function("() => window.__site && window.__site.TL", timeout=10000)
        got = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert got == cell.theme, f"harness precondition: theme {cell.theme!r} not applied (data-theme={got!r})"
        m = page.evaluate("() => window.__site.map()")
        assert m["desktop"] == (cell.width >= 1024), f"harness precondition: unexpected mode for {cell.id}: {m['desktop']}"
        info = Info(rest=_rest_times(m, cell.n_pinned), end_y=m["storyTop"] + m["scrollLen"], n=cell.n_pinned)
        st = cls(ctx, page, cell, info)
        page.mouse.move(cell.width / 2, cell.height / 2)
        return st

    def close(self) -> None:
        self.ctx.close()

    # ---- state ---------------------------------------------------------------------------------------------------
    def derive(self, raw: dict) -> Snap:
        fe, site, y = raw["fe"], raw["site"], raw["y"]
        info = self.info
        below = y > info.end_y + 1
        if fe:
            T = float(fe.get("T", fe.get("time", 0.0)))
            phase = str(fe.get("phase"))
            dest, rendered = fe.get("dest"), fe.get("rendered")
            dip = bool(fe.get("dip")) or phase == "dip"
            # ICX-CHECKPOINT.2: rest = phase 'rest', rendered == dest, story time on the rest frame, scrollY within 1 px
            # of the track position (fe.trackY) and the checkpoint's caption active (fe.beat).
            ok = (phase == "rest" and rendered is not None and rendered == dest and 0 <= rendered < info.n
                  and abs(T - info.rest[rendered]) <= REST_TOL
                  and fe.get("trackY") is not None and abs(y - float(fe["trackY"])) <= 1
                  and fe.get("beat") == BEATS[rendered])
            released = below and phase == "released"   # ICX-REST.1: RELEASED = the phase AND scrollY below the pin
            return Snap("FEStory", T, y, phase, dest, rendered, dip, rendered if ok else None, ok, released, raw["t"])
        s = site or {"shown": 0.0, "target": 0.0, "vel": 0.0, "intro": False, "dip": False}
        T = float(s["shown"])
        near = next((i for i, r in enumerate(info.rest) if abs(T - r) <= REST_TOL), None)
        settled = (not s["intro"]) and (not s["dip"]) and abs(s["shown"] - s["target"]) < 1e-3 and abs(s["vel"]) < 1e-6
        ok = settled and near is not None
        phase = "rest" if ok else ("dip" if s["dip"] else ("intro" if s["intro"] else ("moving" if not settled else "mid-segment")))
        return Snap("__site", T, y, phase, None, None, bool(s["dip"]), near if ok else None, ok, below, raw["t"])

    def snap(self) -> Snap:
        return self.derive(self.page.evaluate("() => window.__c2read()"))

    def wait_rest(self, budget: float, stall_s: float = 1.2, min_wait: float = 0.6) -> Result:
        """Poll until the story is at rest on a checkpoint (or RELEASED below the pin). 'stalled' = nothing changed for
        stall_s while not at rest (ICX-REST.2); 'timeout' = still moving after the budget (ICX-REST.1)."""
        t0 = time.monotonic()
        first = self.snap()
        last_key, last_change, seen_motion = None, t0, False
        while True:
            s = self.snap()
            now = time.monotonic()
            if not s.is_rest or abs(s.T - first.T) > 0.01 or abs(s.y - first.y) > 1:
                seen_motion = True
            if s.released:
                return Result("released", s, now - t0)
            if s.is_rest and (seen_motion or now - t0 >= min_wait):
                return Result("rest", s, now - t0)
            key = (round(s.T, 4), round(s.y), s.phase)
            if key != last_key:
                last_key, last_change = key, now
            elif now - last_change >= stall_s and not s.is_rest:
                return Result("stalled", s, now - t0)
            if now - t0 >= budget:
                return Result("timeout", s, now - t0)
            self.page.wait_for_timeout(40)

    def to_checkpoint(self, idx: int) -> Result:
        """Precondition helper: move forward to REST(idx) by single wheel gestures (each waits for rest)."""
        res = self.wait_rest(allowance(1))
        for _ in range(idx):
            self.wheel(100)
            res = self.wait_rest(allowance(1))
        return res

    # ---- input ---------------------------------------------------------------------------------------------------
    def wheel(self, dy: float) -> None:
        self.page.mouse.wheel(0, dy)

    def key(self, k: str) -> None:
        self.page.keyboard.press(k)

    def scroll_to(self, y: float) -> None:
        self.page.evaluate("(y) => window.scrollTo(0, y)", y)

    def idle(self, ms: float) -> None:
        self.page.wait_for_timeout(ms)

    # ---- recorder / history --------------------------------------------------------------------------------------
    def rec_start(self) -> None:
        self.page.evaluate("() => window.__c2start()")

    def rec_stop(self) -> list[Snap]:
        raw = self.page.evaluate("() => { const r = window.__c2rec || []; window.__c2rec = null; return r; }")
        return [self.derive(r) for r in raw]

    def hist(self) -> tuple[list[list], int]:
        return (self.page.evaluate("() => window.__c2hist.slice()"), self.page.evaluate("() => history.length"))

    def hist_mark(self) -> tuple[int, int]:
        calls, n = self.hist()
        return len(calls), n


def allowance(distance: int) -> float:
    """ICX-REST.1: transition (<= 1.5 s per step) + content (<= 5 s) + 1 s of visible time."""
    return 1.5 * max(distance, 1) + 5 + 1


def dip_spans(frames: list[Snap]) -> list[tuple[float, float]]:
    """(start, end) in seconds of each contiguous run of dip frames."""
    spans, start, prev = [], None, None
    for f in frames:
        if f.dip and start is None:
            start = f.t
        if not f.dip and start is not None:
            spans.append((start / 1000, prev / 1000))
            start = None
        prev = f.t
    if start is not None:
        spans.append((start / 1000, prev / 1000))
    return spans


def max_rate(frames: list[Snap], window: float = 0.1) -> float:
    """Largest |dT/dt| over >= `window` s windows of frames, skipping any window that contains a dip frame (a cut is
    not playback) or a frame gap above 250 ms."""
    worst = 0.0
    for i, a in enumerate(frames):
        if a.dip:
            continue
        for j in range(i + 1, len(frames)):
            b = frames[j]
            if b.dip or (b.t - frames[j - 1].t) > 250:
                break
            dt = (b.t - a.t) / 1000
            if dt >= window:
                worst = max(worst, abs(b.T - a.T) / dt)
                break
    return worst


def rests_seen(frames: list[Snap]) -> set[int]:
    return {f.index for f in frames if f.index is not None}


def check_engine(snap: Snap, idx: int, row: str) -> None:
    """The contract's engine-state half: rendered == dest == idx and phase == 'rest' (ICX-CHECKPOINT.2)."""
    assert snap.src == "FEStory", (
        f"{row}: window.FEStory is absent; the base exposes only __site.state() (shown/target/vel) with no signed dest, "
        f"no rendered and no phase, so the contract's state cannot be read ({snap.describe()})")
    assert snap.phase == "rest" and snap.rendered == snap.dest == idx, (
        f"{row}: expected phase 'rest' with rendered == dest == {idx} ({BEATS[idx]}), got {snap.describe()}")


@dataclass
class Fuzz:
    """Seeded operation stream for the ICX-REST.1 fuzz. Operations: wheel (both directions, several sizes), keys
    (step keys, Home/End, ignored keys), foreign scrollTo inside the track, small resizes. Touch, rail clicks and
    popstate are not driven: the base has no rail, and the touch layer arrives with C3/C4."""
    cell: Cell
    rng: object
    log: list = field(default_factory=list)

    KEYS = ["ArrowDown", "ArrowUp", "PageDown", "PageUp", "Space", "Shift+Space", "Home", "End", "ArrowLeft"]

    def sequence(self, story: Story, forward_first: bool = False) -> list[str]:
        r = self.rng
        ops: list[str] = []
        for i in range(r.randint(2, 6)):
            x = r.random()
            if i == 0 and forward_first:
                k = r.choice(["wheel", "ArrowDown", "PageDown", "End", "Space"])
                if k == "wheel":
                    story.wheel(100)
                    ops.append("wheel(100)")
                else:
                    story.key(k)
                    ops.append(f"key({k})")
            elif x < 0.45:
                dy = r.choice([100, -100, 120, -120, 53, -53, 200, -200])
                story.wheel(dy)
                ops.append(f"wheel({dy})")
            elif x < 0.80:
                k = r.choice(self.KEYS)
                story.key(k)
                ops.append(f"key({k})")
            elif x < 0.92:
                y = r.randint(0, int(story.info.end_y))
                story.scroll_to(y)
                ops.append(f"scrollTo({y})")
            else:
                dw, dh = r.randint(-20, 20), r.randint(-30, 30)
                story.page.set_viewport_size({"width": self.cell.width + dw, "height": self.cell.height + dh})
                ops.append(f"resize({dw},{dh})")
            story.idle(r.choice([40, 90, 150, 260, 300, 420]))
        story.page.set_viewport_size({"width": self.cell.width, "height": self.cell.height})
        ops.append("resize(restore)")
        return ops
