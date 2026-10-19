"""C6: phones and touch per the interaction contract (docs/interaction-contract.md v1).

Real touch input through Chromium's input pipeline (CDP Input.synthesizeScrollGesture with gestureSourceType "touch":
touchstart / touchmove / touchend, and a real fling when preventFling is false), at the real phone viewports (memory
feedback-audit-real-viewports): iPhone 14 Safari ~390x664, SE ~375x548, Android ~360x640, iPad 820x1180, landscape
844x390, all hasTouch + isMobile (pointer: coarse).

- test_one_swipe_one_checkpoint: ICX-STEP / ICX-BACK: a flick and a slow drag, forward and back, each move exactly one
  checkpoint (never two), and nothing moves after the landing (no momentum leak). A short touch screen is calm
  (decisions #22): the swipe scrolls natively and nothing steps.
- test_flick_momentum_never_double_steps: a hard flick with a real fling steps once; at the checkpoint before the last
  pinned it steps onto "Get the app" and never releases (ICX-RELEASE.4); repeated flicks in a transition are clamped.
- test_first_chapter_scrolls_natively: ICX-BACK.5 / decisions #16: at REST(first) a back swipe is not prevented
  (pull-to-refresh); one checkpoint later it is.
- test_phone_release_reentry: ICX-RELEASE.1-.4, ICX-SETTLE-4/8 on touch: clamp at "Get the app", the next swipe releases
  into Price / A note, a swipe or fling back up from Price lands on REST(last pinned) and never on an earlier one, and
  the next back swipe is an ordinary step back.
- test_aria_live_no_focus_move: ICX-KEY.2 / .3: a polite live region announces each final landing's name (pass-through
  landings are not announced) and focus never moves.
- test_landscape_844x390: the shipped mode (a short touch screen: calm) behaves natively; a rotation keeps the place.
- test_swipe_no_long_task: no long task > 50 ms on a swipe at 4x CPU throttle.

SCRUB (stage 3, 2026-10-18; docs/interaction-contract.md ICX-SCRUB): phones (< 640) and touch tablets (640-1023, coarse)
are scrub builds now: the page scrolls natively under the finger and the story follows the scroll. The checkpoint-touch
claims (one swipe = one step, the clamp, the slop, a pinch's settle) moved to an iPad held sideways (1180x820, touch:
a checkpoint build, the one real touch device that still steps); the phone and 820-touch cells assert the scrub
contract instead (test_swipe_scrolls_and_the_story_follows, test_scrub_*, and the rewritten release / aria-live tests).
"""
from __future__ import annotations

import pytest
from playwright.sync_api import sync_playwright
from test_scrub import _still

BEATS = ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"]
STATE = "() => ({...FEStory.state(), y: Math.round(scrollY), end: __site.map().storyTop + __site.map().scrollLen, bp: __site.map().beatPx})"
ST = "() => ({...FEStory.state(), ...__site.state(), y: Math.round(scrollY), end: __site.map().storyTop + __site.map().scrollLen})"

VIEWPORTS = {
    "390x664": (390, 664, "phone"),
    "375x548": (375, 548, "calm"),
    "360x640": (360, 640, "phone"),
    "820x1180": (820, 1180, "tablet"),
    "1180x820": (1180, 820, "desktop"),     # an iPad held sideways: touch, >= 1024, a checkpoint build
}
SCRUB_VPS = ["390x664", "360x640", "820x1180"]

# every frame: [now, shown story time, scrollY, phase, dip] (ICX-SCRUB.3: the stage's speed, a dip)
_TRACE = """() => { const R = window.__tr = []; const rec = () => { if (window.__tr !== R) return; const s = __site.state();
  R.push([performance.now(), s.shown, Math.round(scrollY), FEStory.state().phase, !!s.dip]); requestAnimationFrame(rec); };
  requestAnimationFrame(rec); }"""
_TRACE_END = "() => { const r = window.__tr || []; window.__tr = null; return r; }"


def _no_skip(tr, what):
    """ICX-SCRUB.3: the stage never runs faster than 3x the wall clock (no skip forward or back) and never dips. The
    allowance (x1.5 + 10 ms of story) covers the recorder's frame timing against the engine's own."""
    fast = [(round(b[1] - a[1], 3), round(b[0] - a[0])) for a, b in zip(tr, tr[1:])
            if abs(b[1] - a[1]) > 3.0 * 1.5 * max(b[0] - a[0], 1.0) / 1000 + 0.01]
    assert not fast, f"{what}: the stage skipped (story s, ms) faster than 3x: {fast[:6]}"
    assert not any(r[4] for r in tr), f"{what}: the stage dipped"


def _hold_mid(page, beat):
    return page.evaluate("(b) => { const m = __site.map(); const h = m.pieces.find((p) => p.kind === 'hold' && p.beat === b);"
                         " return Math.round(m.storyTop + (h.s0 + h.s1) / 2); }", beat)

# logs: every dest change, landing and phase seen (rAF), and the touchmove events' defaultPrevented (a listener that
# runs after the story's own, on window, bubble phase)
_LOG = """() => {
  if (window.__c6) return;
  const L = window.__c6 = { dest: [], land: [], phases: [], ys: [], moves: [], rec: true };
  FEStory.onDest((p) => { if (!p.preview) L.dest.push([p.index, p.source]); });
  FEStory.onLand((p) => L.land.push([p.index, p.final, p.source]));
  window.addEventListener('touchmove', (e) => L.moves.push([e.cancelable, e.defaultPrevented]), { passive: true });
  const tick = () => { if (L.rec) { const s = FEStory.state(); if (L.phases[L.phases.length - 1] !== s.phase) L.phases.push(s.phase); L.ys.push(Math.round(scrollY)); } requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}"""
# diagnostics: every onStep the detector emits (direction, source, info), wrapped around C1's createSequence
_STEPS = """(() => { let v; Object.defineProperty(window, 'FECheckpoint', { configurable: true, get() { return v; }, set(api) {
  v = Object.freeze({ ...api, createSequence(o) { const os = o.onStep; o.onStep = (d, s, i) => {
    (window.__c6steps = window.__c6steps || []).push([d, s, i && i.trigger, Math.round(performance.now())]); return os(d, s, i); };
    return api.createSequence(o); } }); } }); })()"""
_MARK = "() => { window.__c6steps = []; const L = window.__c6; L.dest = []; L.land = []; L.phases = [FEStory.state().phase]; L.ys = []; L.moves = []; }"
_READ = "() => JSON.parse(JSON.stringify({...window.__c6, steps: window.__c6steps || []}))"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


class Phone:
    def __init__(self, browser, site_url, w, h, path="/", mobile=True):
        self.ctx = browser.new_context(viewport={"width": w, "height": h}, has_touch=True, is_mobile=mobile,
                                       reduced_motion="no-preference")
        self.ctx.add_init_script(_STEPS)
        self.page = self.ctx.new_page()
        self.page.goto(site_url + path, wait_until="load")
        self.page.wait_for_function("() => window.FEStory && document.documentElement.classList.contains('fx-ready') "
                                    "&& (window.__site.TL || FEStory.mode === 'calm')", timeout=10000)
        self.cdp = self.ctx.new_cdp_session(self.page)
        self.w, self.h = w, h

    def close(self):
        self.ctx.close()

    @property
    def mode(self):
        return self.page.evaluate("() => FEStory.mode")

    def st(self):
        return self.page.evaluate(STATE)

    def log(self):
        self.page.evaluate(_LOG)

    def mark(self):
        self.page.evaluate(_MARK)

    def read(self):
        return self.page.evaluate(_READ)

    def pinned(self):
        return self.page.evaluate("() => FEStory.destinations.filter(d => d.kind === 'pinned').map(d => BEATS_IDX(d.beat))"
                                  .replace("BEATS_IDX(d.beat)", "['make','look','know','grow','chase','yours','price','note','end'].indexOf(d.beat)"))

    # a forward swipe = the finger moves up (the page would scroll down): yDistance < 0
    def swipe(self, dist, speed, fling=False, y0=None):
        self.cdp.send("Input.synthesizeScrollGesture", {
            "x": self.w // 2, "y": int(y0 if y0 is not None else self.h * (0.75 if dist > 0 else 0.3)),
            "yDistance": -int(dist), "xDistance": 0, "speed": int(speed), "gestureSourceType": "touch",
            "preventFling": not fling})

    def flick(self, d=1, dist=160, fling=True):
        self.swipe(d * dist, 2400, fling=fling)

    def drag(self, d=1, dist=220):
        self.swipe(d * dist, 300)               # ~0.7 s, the finger lifted at rest (no fling)

    def finger_flick(self, d=1, offsets=(2, 5, 12, 28, 55, 95, 145, 200), ms=12):
        """A real finger's flick: it starts slowly (the first touchmoves inside the 8 px slop) and accelerates, then
        lifts at speed (~4 px/ms: Chromium's gesture detector flings it if nothing prevented the scroll)."""
        x, y0 = self.w // 2, int(self.h * (0.75 if d > 0 else 0.3))
        self.cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y0}]})
        for off in offsets:
            self.page.wait_for_timeout(ms)
            self.cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y0 - d * off}]})
        self.cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})

    def wait(self, pred, timeout=12000):
        try:
            self.page.wait_for_function(f"() => {{ const s = FEStory.state(); return {pred}; }}", timeout=timeout)
        except Exception as e:  # noqa: BLE001 - report the engine's state, not a bare timeout
            raise AssertionError(f"timed out waiting for {pred}: {self.st()} log={ {k: v for k, v in self.read().items() if k != 'ys'} if self.page.evaluate('() => !!window.__c6') else None}") from e
        return self.st()

    def rest_on(self, idx, timeout=12000):
        return self.wait(f"s.phase === 'rest' && s.rendered === {idx} && s.dest === {idx} && Math.abs(scrollY - s.trackY) <= 1 "
                         f"&& s.beat === '{BEATS[idx]}'", timeout)

    def goto_beat(self, beat):
        self.page.evaluate(f"() => FEStory.goTo('{beat}', {{source: 'jump'}})")
        return self.rest_on(BEATS.index(beat), 15000)


def _one_step(p: Phone, frm: int, to: int, what: str):
    """After a gesture from REST(frm): exactly one move, to REST(to), and nothing after it (momentum)."""
    p.rest_on(to)
    p.page.wait_for_timeout(900)                 # a fling or a late touch event would move it again here
    st, L = p.st(), p.read()
    dests = [d for d, _ in L["dest"]]
    assert dests == [to], f"{what}: from {BEATS[frm]} the dest went {[BEATS[d] for d in dests]}; one gesture = one step to {BEATS[to]}"
    assert st["phase"] == "rest" and st["rendered"] == to, f"{what}: moved again after landing: {st}"
    assert "free" not in L["phases"] and "released" not in L["phases"], f"{what}: native scroll leaked in: phases {L['phases']}"


# ------------------------------------------------------------------------------------------------- one swipe, one step
# (SCRUB stage 3) the checkpoint cells only: a short touch screen (calm) and an iPad held sideways (a checkpoint build);
# the phones and the 820 touch tablet scrub (test_swipe_scrolls_and_the_story_follows)
@pytest.mark.parametrize("vp", ["375x548", "1180x820"])
def test_one_swipe_one_checkpoint(browser, site_url, vp):
    w, h, want = VIEWPORTS[vp]
    p = Phone(browser, site_url, w, h)
    try:
        assert p.mode == want, f"{vp}: shipped mode is {p.mode!r}, expected {want!r}"
        if want == "calm":                       # decisions #22: the swipe is a page scroll, nothing steps
            y0 = p.page.evaluate("() => scrollY")
            p.flick(1, 200)
            p.page.wait_for_timeout(600)
            assert p.page.evaluate("() => scrollY") > y0 + 100, f"{vp}: calm page did not scroll natively"
            assert p.mode == "calm"
            return
        pins = p.pinned()
        p.rest_on(0)
        p.log()
        cases = [("flick forward", 1, p.flick), ("slow drag forward", 1, p.drag),
                 ("flick back", -1, p.flick), ("slow drag back", -1, p.drag)]
        k = 0
        for what, d, fn in cases:
            p.page.wait_for_timeout(300)
            p.mark()
            fn(d)
            _one_step(p, pins[k], pins[k + d], f"{vp} {what}")
            k += d
    finally:
        p.close()


@pytest.mark.parametrize("vp", SCRUB_VPS)
def test_swipe_scrolls_and_the_story_follows(browser, site_url, vp):
    """(SCRUB stage 3: replaces test_one_swipe_one_checkpoint and the phone half of the momentum test on the scrub builds,
    ICX-SCRUB.1/.3) a flick and a slow drag, forward and back, from Templates' hold: no touchmove is prevented, the page
    moves the finger's way (a flick's fling carries it well past the finger: the browser's own momentum), the story
    time moves the same way without a skip or a dip, and once the scroll stops nothing moves on (no momentum leak)."""
    w, h, want = VIEWPORTS[vp]
    p = Phone(browser, site_url, w, h)
    try:
        assert p.mode == want and p.page.evaluate("() => __site.map().scrub") is True, f"{vp}: not a scrub build"
        p.goto_beat("look")
        p.log()
        # each gesture starts mid-way down the ramp from Templates to Invoices (inside a hold the story time is all but
        # flat by design, ICX-SCRUB.2): a flick's fling and a drag both stay on that ramp
        ramp = p.page.evaluate("() => { const m = __site.map(); const r = m.pieces.find((p) => p.kind === 'ramp' && p.beat === 'know');"
                               " return Math.round(m.storyTop + (r.s0 + r.s1) / 2); }")
        cases = [("flick forward", 1, lambda: p.flick(1)), ("slow drag forward", 1, lambda: p.drag(1)),
                 ("flick back", -1, lambda: p.flick(-1)), ("slow drag back", -1, lambda: p.drag(-1))]
        for what, d, fn in cases:
            p.page.evaluate("(y) => scrollTo(0, y)", ramp)
            p.page.wait_for_timeout(300)
            s0 = _still(p.page, 15000)
            p.mark()
            p.page.evaluate(_TRACE)
            fn()
            s1 = _still(p.page, 15000)
            p.page.wait_for_timeout(900)              # a fling or a late touch event would move it again here
            s2, tr, L = p.page.evaluate(ST), p.page.evaluate(_TRACE_END), p.read()
            where = f"{vp} {what}"
            assert L["moves"], f"{where}: no touchmove reached the page"
            assert not any(m[1] for m in L["moves"]), f"{where}: touchmoves prevented {sum(1 for m in L['moves'] if m[1])}/{len(L['moves'])}"
            dy, dT = s1["y"] - s0["y"], s1["shown"] - s0["shown"]
            assert d * dy > 100, f"{where}: the page moved {dy} px"
            if "flick" in what:
                assert d * dy > 160 * 1.5, f"{where}: a 160 px flick moved the page only {dy} px (no fling: the momentum was cut)"
            assert d * dT > 0.1, f"{where}: the story did not follow the scroll ({s0['shown']:.3f} -> {s1['shown']:.3f})"
            assert s2["y"] == s1["y"] and abs(s2["shown"] - s1["shown"]) < 1e-3, f"{where}: moved on after it stopped: {s1} -> {s2}"
            assert "free" not in L["phases"] and not L["steps"], f"{where}: the checkpoint engine ran: {L['phases']} {L['steps']}"
            _no_skip(tr, where)
    finally:
        p.close()


# ------------------------------------------------------------------------------------------------- momentum
# (SCRUB stage 3) a checkpoint build with touch: an iPad held sideways. The phones' momentum is the browser's own
# (test_swipe_scrolls_and_the_story_follows: the fling carries the page, the stage follows without a skip).
def test_flick_momentum_never_double_steps(browser, site_url):
    p = Phone(browser, site_url, 1180, 820)
    try:
        assert p.mode == "desktop" and p.page.evaluate("() => __site.map().scrub") is False
        p.rest_on(0)
        p.log()
        # a finger's flick (slow start, fast lift) and a hard synthetic flick with its fling: each one step, forward
        # and back, and the fling never moves the page under the story
        for frm, to, fn in [(0, 1, lambda: p.finger_flick(1)), (1, 2, lambda: p.finger_flick(1)),
                            (2, 1, lambda: p.finger_flick(-1)), (1, 2, lambda: p.swipe(420, 5000, fling=True)),
                            # an easy flick: its first touchmove (~7 px) lands inside the slop, and the fling follows
                            (2, 3, lambda: p.swipe(200, 450, fling=True)), (3, 2, lambda: p.swipe(-200, 450, fling=True))]:
            p.page.wait_for_timeout(300)
            p.mark()
            fn()
            _one_step(p, frm, to, f"flick {BEATS[frm]} -> {BEATS[to]}")
        # at the checkpoint before the last pinned (A note here; Your data on the old phone) a flick lands on Get the app
        # and never releases
        pins = p.pinned()
        assert pins[-1] == 8, pins
        p.goto_beat(BEATS[pins[-2]])
        p.mark()
        p.finger_flick(1)
        # more flicks during the move are clamped (ICX-RELEASE.4); (SCRUB stage 3) at once, not 250 ms later: the
        # sideways iPad's step onto Get the app is shorter than the phone's was, and a flick after it has landed is a
        # release from REST(last), ICX-RELEASE.1
        p.finger_flick(1)
        p.swipe(420, 5000, fling=True)
        p.rest_on(8)
        p.page.wait_for_timeout(1500)
        st, L = p.st(), p.read()
        assert st["phase"] == "rest" and st["rendered"] == 8, f"after the clamp: {st}"
        assert "released" not in L["phases"] and "free" not in L["phases"], f"the flick's momentum leaked: phases {L['phases']}"
        assert max(L["ys"]) <= st["end"] + 1, f"the page scrolled past the pin during the clamp (max y {max(L['ys'])} > {st['end']})"
    finally:
        p.close()


# ------------------------------------------------------------------------------------------------- first chapter
def test_first_chapter_scrolls_natively_scrub(browser, site_url):
    """(SCRUB stage 3, ICX-SCRUB.1; the phone half of test_first_chapter_scrolls_natively) at the top a back swipe is never
    prevented (pull-to-refresh) and moves nothing; one chapter later (Templates) a back swipe is not prevented either:
    the page scrolls back and the story plays backwards, no dip."""
    p = Phone(browser, site_url, 390, 664)
    try:
        s0 = _still(p.page, 15000)
        assert s0["y"] == 0, s0
        p.log()
        p.mark()
        p.drag(-1, 160)
        p.page.wait_for_timeout(400)
        L = p.read()
        assert L["moves"], "no touchmove reached the page"
        assert not any(prevented for _, prevented in L["moves"]), (
            f"ICX-SCRUB.1: a back swipe at the first chapter was prevented (pull-to-refresh blocked): {L['moves'][:6]}")
        assert L["dest"] == [] and L["land"] == [] and p.page.evaluate(ST)["rendered"] == 0, f"a back swipe at the top moved the story: {L}"
        p.goto_beat("look")
        s0 = _still(p.page)
        p.mark()
        p.page.evaluate(_TRACE)
        p.drag(-1, 400)                           # out of Templates' (flat) hold onto the ramp from New invoice
        s1 = _still(p.page)
        tr, L = p.page.evaluate(_TRACE_END), p.read()
        assert L["moves"] and not any(prevented for _, prevented in L["moves"]), f"a back swipe at Templates was prevented: {L['moves'][:6]}"
        assert s1["y"] < s0["y"] - 100 and s1["shown"] < s0["shown"] - 0.1, f"the back swipe did not play back: {s0} -> {s1}"
        _no_skip(tr, "back swipe at Templates")
    finally:
        p.close()


# (SCRUB stage 3) the checkpoint half: an iPad held sideways
def test_first_chapter_scrolls_natively(browser, site_url):
    p = Phone(browser, site_url, 1180, 820)
    try:
        assert p.page.evaluate("() => __site.map().scrub") is False
        p.rest_on(0)
        p.log()
        p.mark()
        p.drag(-1, 160)
        p.page.wait_for_timeout(400)
        L = p.read()
        assert L["moves"], "no touchmove reached the page"
        assert not any(prevented for _, prevented in L["moves"]), (
            f"ICX-BACK.5: a back swipe at the first chapter was prevented (pull-to-refresh blocked): {L['moves'][:6]}")
        assert L["dest"] == [] and "dip" not in L["phases"], f"a back swipe at the first chapter moved the story: {L}"
        # control: one checkpoint later the same swipe is intercepted
        p.flick(1)
        p.rest_on(1)
        p.mark()
        p.drag(-1, 160)
        p.rest_on(0)
        assert any(prevented for _, prevented in p.read()["moves"]), "a back swipe at REST(look) was not intercepted"
    finally:
        p.close()


# ------------------------------------------------------------------------------------------------- release / re-entry
@pytest.mark.parametrize("vp", ["390x664", "360x640"])
def test_phone_release_reentry(browser, site_url, vp):
    """(SCRUB stage 3: the scrub form of ICX-RELEASE.1-.4 / ICX-HIST.8, ICX-SCRUB.1/.5) at Get the app's hold a forward
    flick is the browser's own release into Price (never prevented, nothing landed below the pin); native swipes carry
    the reader on to Price; dragging back up from below the pin into Get the app's hold is one landing there, announced,
    and never on an earlier chapter, no dip, from just below the pin and from further down; the next back flick plays the
    story backwards."""
    w, h, _ = VIEWPORTS[vp]
    p = Phone(browser, site_url, w, h)
    try:
        _still(p.page, 15000)
        assert p.pinned()[-1] == 8, "phone: the last pinned is Get the app (decisions #21)"
        p.log()
        p.goto_beat("end")
        p.page.wait_for_timeout(800)
        # a forward flick at the last pinned releases into Price / A note: the page's own scroll (ICX-SCRUB.1)
        p.mark()
        p.flick(1, 300)
        st = p.wait("s.phase === 'released'", 4000)
        p.page.wait_for_timeout(800)
        st, L = p.st(), p.read()
        assert st["y"] > st["end"] + 1, st
        assert L["moves"] and not any(m[1] for m in L["moves"]), f"the release flick was prevented: {L['moves'][:6]}"
        # below the pin it is the page: native swipes carry the reader on into Price; nothing lands
        vis = "(id) => { const r = document.getElementById(id).getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0; }"
        for _ in range(6):
            if p.page.evaluate(vis, "price"):
                break
            p.flick(1, 300)
            p.page.wait_for_timeout(700)
        st, L = p.st(), p.read()
        assert p.page.evaluate(vis, "price"), f"native swipes below the pin did not reach Price: {st}"
        assert st["phase"] == "released" and L["dest"] == [] and L["land"] == [] and not L["steps"], (
            f"a swipe below the pin moved the story: {st} {L['dest']} {L['land']}")
        # back up into the pin by the finger (drags, no fling), ending inside Get the app's hold: one landing there
        for what, down in [("drag from just below the pin", 0.5), ("drags from further down", 1.6)]:
            p.page.evaluate(f"() => window.scrollTo(0, __site.map().storyTop + __site.map().scrollLen + Math.round(innerHeight * {down}))")
            p.wait("s.phase === 'released'", 3000)
            p.page.wait_for_timeout(300)
            p.mark()
            p.page.evaluate("() => { document.querySelector('[data-story-live]').textContent = ''; }")
            p.page.evaluate(_TRACE)
            left = p.page.evaluate("() => scrollY") - _hold_mid(p.page, "end")
            while left > 8:
                chunk = min(left, int(h * 0.6))
                p.swipe(-chunk, 300, y0=int(h * 0.2))
                left = p.page.evaluate("() => scrollY") - _hold_mid(p.page, "end")
            st = _still(p.page, 8000)
            p.page.wait_for_timeout(1000)
            said = p.page.evaluate("() => document.querySelector('[data-story-live]').textContent")
            tr, L, st = p.page.evaluate(_TRACE_END), p.read(), p.page.evaluate(ST)
            assert said == "Get the app", f"ICX-KEY.2: the re-entry by {what} was not announced (live region {said!r})"
            assert st["phase"] == "rest" and st["rendered"] == 8 and st["beat"] == "end", f"re-entry by {what} did not land on Get the app: {st}"
            finals = [d for d, final, _ in L["land"] if final]
            assert finals == [8], f"re-entry by {what}: final landings {finals}; one, on Get the app, expected"
            touched = sorted({d for d, _, _ in L["land"]} | {d for d, _ in L["dest"]})
            assert set(touched) <= {8}, f"re-entry by {what} touched {[BEATS[i] for i in touched]}; only Get the app is allowed"
            assert not any(m[1] for m in L["moves"]), f"re-entry by {what}: a touchmove was prevented"
            _no_skip(tr, f"re-entry by {what}")
        # the next back flick plays the story backwards (ICX-SCRUB.3)
        s0 = _still(p.page)
        p.flick(-1)
        s1 = _still(p.page, 8000)
        assert s1["y"] < s0["y"] - 100 and s1["shown"] < s0["shown"] - 0.1, f"the back flick after the re-entry: {s0} -> {s1}"
    finally:
        p.close()


@pytest.mark.parametrize("vp", ["1180x820"])
def test_fling_reentry_checkpoint(browser, site_url, vp):
    """(SCRUB stage 3, Sol SCRUB-3 HIGH: the hard-fling half of the old phone re-entry test, ICX-RELEASE.2 / ICX-SETTLE-8,
    on a checkpoint build with touch, an iPad held sideways) from as far below the pin as the page goes, one hard flick
    whose fling runs up into the pin lands on REST(last pinned) and stays there: never an earlier checkpoint, announced,
    no dip, and the fling's tail does not walk it back after REENTRY_STICKY_MS; the next back swipe is an ordinary step
    back. (On a phone the fling is the browser's own and the stage follows it: test_phone_release_reentry.)"""
    w, h, want = VIEWPORTS[vp]
    p = Phone(browser, site_url, w, h)
    try:
        assert p.mode == want and p.page.evaluate("() => __site.map().scrub") is False
        p.rest_on(0)
        pins = p.pinned()
        last = pins[-1]
        name = p.page.evaluate(f"() => FEStory.destinations[{last}].name")
        p.log()
        p.goto_beat(BEATS[last])
        p.page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        p.wait("s.phase === 'released'", 3000)
        p.page.wait_for_timeout(300)
        p.mark()
        p.page.evaluate("() => { document.querySelector('[data-story-live]').textContent = ''; }")
        p.swipe(-500, 5000, fling=True, y0=100)
        p.rest_on(last, 8000)
        p.page.wait_for_timeout(1800)
        said = p.page.evaluate("() => document.querySelector('[data-story-live]').textContent")
        assert said == name, f"ICX-KEY.2: the re-entry by fling was not announced (live region {said!r})"
        st, L = p.st(), p.read()
        assert st["phase"] == "rest" and st["rendered"] == last, f"re-entry by fling did not stay on {name}: {st}"
        landed = sorted({d for d, _, _ in L["land"]} | {d for d, _ in L["dest"]})
        assert set(landed) <= {last}, f"re-entry by fling touched {[BEATS[i] for i in landed]}; only {name} is allowed"
        assert "dip" not in L["phases"], f"re-entry by fling played a dip: {L['phases']}"
        # the next back swipe is an ordinary step back (ICX-BACK)
        p.mark()
        p.flick(-1)
        p.rest_on(pins[-2])
    finally:
        p.close()


# ------------------------------------------------------------------------------------------------- aria-live
def test_aria_live_no_focus_move(browser, site_url):
    """(SCRUB stage 3: the scrub form, ICX-KEY.2/.3 + ICX-SCRUB.5) one polite live region; the scroll stopping in
    Templates' hold announces it once; one scroll on to Dashboard's hold carries the stage through Invoices' hold while it
    moves (not announced) and announces Dashboard once when it lands; nothing is announced while the stage moves; focus
    never moves."""
    p = Phone(browser, site_url, 390, 664)
    try:
        _still(p.page, 15000)
        regions = p.page.evaluate("() => [...document.querySelectorAll('[data-story-live]')].map(e => [e.getAttribute('aria-live'), e.getAttribute('role')])")
        assert len(regions) == 1 and regions[0][0] == "polite", f"ICX-KEY.2: one polite story live region expected, got {regions}"
        names = p.page.evaluate("() => Object.fromEntries(FEStory.destinations.map(d => [d.beat, d.name]))")
        p.page.evaluate("""() => {
            window.__c6said = [];
            const el = document.querySelector('[data-story-live]');
            new MutationObserver(() => { const t = el.textContent.trim(); if (t) window.__c6said.push([t, FEStory.state().phase, Math.round(scrollY)]); })
              .observe(el, { childList: true, characterData: true, subtree: true });
            const f = document.querySelector('[data-theme-toggle]') || document.querySelector('header a');
            f.focus(); window.__c6focus = f;
        }""")
        p.page.evaluate("(y) => scrollTo(0, y)", _hold_mid(p.page, "look"))
        s = _still(p.page, 15000)
        p.page.wait_for_timeout(500)
        assert s["rendered"] == 1, s
        p.page.evaluate(_TRACE)
        p.page.evaluate("(y) => scrollTo(0, y)", _hold_mid(p.page, "grow"))
        s = _still(p.page, 15000)
        p.page.wait_for_timeout(500)
        tr = p.page.evaluate(_TRACE_END)
        assert s["rendered"] == 3, s
        crossed = [r for r in tr if r[3] == "transition" and abs(r[1] - p.page.evaluate("() => FEStory.destinations[2].rest")) < 0.3]
        assert crossed, "harness: the stage never crossed Invoices' hold while moving"
        said = p.page.evaluate("() => window.__c6said")
        texts = [t for t, _, _ in said]
        assert texts == [names["look"], names["grow"]], f"ICX-KEY.2: expected Templates then Dashboard, each once; got {said}"
        assert all(ph == "rest" for _, ph, _ in said), f"announced while the stage moved: {said}"
        assert p.page.evaluate("() => document.activeElement === window.__c6focus"), "ICX-KEY.3: focus moved on a landing"
    finally:
        p.close()


# ------------------------------------------------------------------------------------------------- landscape
def test_landscape_844x390(browser, site_url):
    p = Phone(browser, site_url, 844, 390)
    try:
        assert p.mode == "calm", f"landscape 844x390 ships calm (a short touch screen); got {p.mode!r}"
        assert p.page.evaluate("() => document.documentElement.classList.contains('short-touch')")
        y0 = p.page.evaluate("() => scrollY")
        p.flick(1, 200)
        p.page.wait_for_timeout(600)
        assert p.page.evaluate("() => scrollY") > y0 + 100, "landscape: the swipe did not scroll the page"
    finally:
        p.close()
    # a rotation keeps the place (ICX-DEST.4): portrait REST(grow) -> landscape (calm, Dashboard in view) -> portrait
    p = Phone(browser, site_url, 390, 664)
    try:
        p.rest_on(0)
        p.goto_beat("grow")
        p.page.set_viewport_size({"width": 844, "height": 390})
        p.page.wait_for_timeout(700)
        assert p.mode == "calm"
        assert p.page.evaluate("""() => { const r = document.getElementById('dashboard').getBoundingClientRect();
            return r.top < innerHeight * 0.6 && r.bottom > 70; }"""), "rotation to landscape lost the place (Dashboard not in view)"
        p.page.set_viewport_size({"width": 390, "height": 664})
        p.page.wait_for_timeout(700)
        p.rest_on(3, 6000)
    finally:
        p.close()


# ------------------------------------------------------------------------------------------------- jank
def test_swipe_no_long_task(browser, site_url):
    p = Phone(browser, site_url, 390, 664)
    try:
        p.rest_on(0)
        p.page.wait_for_timeout(800)
        p.cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        p.page.evaluate("""() => { window.__c6lt = [];
            new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__c6lt.push([Math.round(e.startTime), Math.round(e.duration)]); })
              .observe({ type: 'longtask' }); }""")
        p.page.wait_for_timeout(300)
        t0 = p.page.evaluate("() => performance.now()")
        p.flick(1)
        p.page.wait_for_timeout(1200)
        p.flick(-1)
        p.page.wait_for_timeout(1200)
        lt = [x for x in p.page.evaluate("() => window.__c6lt") if x[0] >= t0]
        p.cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        assert not lt, f"long tasks (> 50 ms) on a swipe at 4x CPU throttle: {lt} (start ms, duration ms)"
    finally:
        p.close()


# ------------------------------------------------------------------------------------------------- pinch / sideways
_TOUCHLOG = """() => { window.__c6t = [];
  window.addEventListener('touchmove', (e) => window.__c6t.push([e.touches.length, e.defaultPrevented, e.cancelable]), { passive: true }); }"""


def test_pinch_never_prevented(browser, site_url):
    """ICX-BYPASS.2 (main's condition on C6's slop hold): once a second touch point is down, no touchmove is ever
    prevented, whether the first finger moved first (its in-slop move may be held) or not; a real pinch zooms."""
    p = Phone(browser, site_url, 390, 664)
    try:
        _still(p.page, 15000)
        p.goto_beat("look")                       # (SCRUB stage 3: a phone does not step; the menu's jump lands it)
        p.page.evaluate(_TOUCHLOG)
        t = lambda kind, pts: p.cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": pts})  # noqa: E731
        for lead in (0, 4):                       # no lead-in, and a 4 px in-slop first-finger move before the pinch
            t("touchStart", [{"x": 195, "y": 330, "id": 1}])
            if lead:
                p.page.wait_for_timeout(16)
                t("touchMove", [{"x": 195, "y": 330 - lead, "id": 1}])
            p.page.wait_for_timeout(16)
            t("touchStart", [{"x": 195, "y": 330 - lead, "id": 1}, {"x": 195, "y": 430, "id": 2}])
            for i in range(1, 9):
                p.page.wait_for_timeout(16)
                t("touchMove", [{"x": 195, "y": 330 - lead - 12 * i, "id": 1}, {"x": 195, "y": 430 + 12 * i, "id": 2}])
            t("touchEnd", [])
            p.page.wait_for_timeout(300)
        log = p.page.evaluate("() => window.__c6t")
        multi = [m for m in log if m[0] >= 2]
        assert multi, f"no two-finger touchmove reached the page: {log}"
        assert not any(prev for _, prev, _ in multi), f"a two-finger touchmove was prevented (pinch blocked): {multi}"
        # (not asserted: the pinch's own scroll of the layout viewport enters FREE and settles on the nearest chapter;
        # it does so at fa309c7 too: ICX-SETTLE-9's open zoom case, reported to main by C6)
        # a synthesized pinch really zooms the page (visualViewport.scale > 1)
        scale = p.page.evaluate("() => visualViewport.scale")   # the dispatched pinches may already have zoomed it
        if scale <= 1.2:
            p.cdp.send("Input.synthesizePinchGesture", {"x": 150, "y": 250, "scaleFactor": 2, "relativeSpeed": 800,
                                                         "gestureSourceType": "touch"})
            p.page.wait_for_timeout(400)
            scale = p.page.evaluate("() => visualViewport.scale")
        assert scale > 1.2, f"a touch pinch did not zoom the page (visualViewport.scale {scale})"
    finally:
        p.close()


_PINCH_REC = """() => { window.__pz = []; const rec = () => { const s = FEStory.state();
  window.__pz.push([s.phase, s.step, s.dip, s.rendered, s.dest, +visualViewport.scale.toFixed(2), Math.round(scrollY)]); requestAnimationFrame(rec); };
  requestAnimationFrame(rec); }"""


def _pinch(p):
    """A two-finger zoom-in pinch through the touch pipeline (Input.dispatchTouchEvent), the fingers diverging about
    y 380 (the judge's probe): Chromium zooms to scale 5 AND scrolls the layout viewport (608 -> 0 at Templates)."""
    t = lambda kind, pts: p.cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": pts})  # noqa: E731
    t("touchStart", [{"x": 195, "y": 330, "id": 1}])
    p.page.wait_for_timeout(16)
    t("touchStart", [{"x": 195, "y": 330, "id": 1}, {"x": 195, "y": 430, "id": 2}])
    for i in range(1, 9):
        p.page.wait_for_timeout(16)
        t("touchMove", [{"x": 195, "y": 330 - 12 * i, "id": 1}, {"x": 195, "y": 430 + 12 * i, "id": 2}])
    t("touchEnd", [])


# scrollY at the zoom-out: the first visualViewport resize back to scale <= 1.01, and SETTLE_IDLE (150 ms) later (when
# the zoom-out settle reads it)
_ZOOM_OUT_Y = """() => { window.__zo = []; const v = visualViewport; const on = () => { if (v.scale > 1.01 || window.__zo.length) return;
  window.__zo.push(Math.round(scrollY)); setTimeout(() => window.__zo.push(Math.round(scrollY)), 140); }; v.addEventListener('resize', on); }"""


def _unzoom(p):
    """Pinch back out to scale 1 (Input.synthesizePinchGesture)."""
    for _ in range(4):
        vv = p.page.evaluate("() => ({ s: visualViewport.scale, w: visualViewport.width, h: visualViewport.height })")
        if vv["s"] <= 1.01:
            break
        # (CDP's point is in the zoomed viewport's CSS px: its centre, or "Position out of bounds")
        p.cdp.send("Input.synthesizePinchGesture", {"x": int(vv["w"] / 2), "y": int(vv["h"] / 2), "relativeSpeed": 800,
                                                     "gestureSourceType": "touch", "scaleFactor": 1 / vv["s"]})
        p.page.wait_for_timeout(300)
    assert p.page.evaluate("() => visualViewport.scale") <= 1.01, "could not zoom back out"


def test_pinch_keeps_the_landed_chapter(browser, site_url):
    """Judge C6 ruling (b): a pinch at Templates that also scrolls the layout viewport must not settle while zoomed
    (a settle scroll yanks the zoomed view, and the nearest beat is wherever the zoom panned to). On zoom-out the story
    re-aligns ONCE on the chapter it was landed on (ICX-SETTLE-4 distance 0: no dip, no content replay, no dest
    change). A pure zoom with no layout scroll leaves the story alone (no settle at all).
    (SCRUB stage 3) The settle is the checkpoint engine's: an iPad held sideways (touch, a checkpoint build). A phone has
    no settle; its pinch is the browser's own and never prevented (test_pinch_never_prevented)."""
    p = Phone(browser, site_url, 1180, 820)
    try:
        assert p.page.evaluate("() => __site.map().scrub") is False
        p.rest_on(0)
        p.flick(1)
        p.rest_on(1)
        p.page.wait_for_timeout(400)
        p.log()
        p.mark()
        s0 = p.st()
        p.page.evaluate(_PINCH_REC)
        _pinch(p)                                  # zoom in at Templates (Chromium scrolls the layout viewport too)
        p.page.wait_for_timeout(1500)              # past SETTLE_BACKSTOP (700 ms): a settle would have run by now
        rec = p.page.evaluate("() => window.__pz")
        assert max(r[5] for r in rec) > 1.2, f"the pinch did not zoom the page: {rec[-1]}"
        assert any(abs(r[6] - s0["trackY"]) > 50 for r in rec if r[5] > 1.01), (
            f"the pinch did not scroll the layout viewport while zoomed (nothing to settle): {rec[-1]}")
        st, L = p.st(), p.read()
        assert "dip" not in L["phases"] and not any(r[2] for r in rec), f"a dip played while zoomed: {L['phases']}"
        assert L["dest"] == [] and all(r[3] == 1 for r in rec), f"the story left Templates while zoomed: dest {L['dest']}"
        assert st["settles"] == s0["settles"], f"a settle ran while zoomed ({s0['settles']} -> {st['settles']})"
        # zoom back out (the page-scale snaps to 1): one distance-0 re-alignment on Templates
        # Not vacuous (main's C6-fix re-check): the base bug needs the zoom-out to find the layout nearer another chapter.
        # The pinch's own layout scroll varies run to run (608 -> 0 here, less under load); if it left Templates
        # nearest, pan the layout to the top while still zoomed (the same foreign-scroll-while-zoomed path), then
        # require nearest != Templates when the scale comes back (as the zoom-out settle reads it, ~150 ms later).
        story_top, bp = s0["trackY"] - s0["bp"], s0["bp"]
        nearest = lambda y: max(0, min(8, round((y - story_top) / bp)))  # noqa: E731
        if nearest(p.page.evaluate("() => scrollY")) == 1:
            p.page.evaluate("() => window.scrollTo({ top: 0, behavior: 'instant' })")
            p.page.wait_for_timeout(1000)
        assert p.page.evaluate("() => visualViewport.scale") > 1.01 and p.st()["settles"] == s0["settles"], p.st()
        p.page.evaluate(_ZOOM_OUT_Y)
        _unzoom(p)
        p.page.wait_for_timeout(200)
        zo = p.page.evaluate("() => window.__zo")
        assert len(zo) == 2 and all(nearest(y) != 1 for y in zo), (
            f"vacuous: at the zoom-out the layout (y {zo}) was nearest Templates, so a nearest-settle would pass too")
        st = p.rest_on(1, 4000)
        p.page.wait_for_timeout(900)
        st, L = p.st(), p.read()
        rec = p.page.evaluate("() => window.__pz")
        assert st["phase"] == "rest" and st["rendered"] == 1 and abs(st["y"] - st["trackY"]) <= 1, f"not back on Templates: {st}"
        assert "dip" not in L["phases"] and not any(r[2] for r in rec), f"the zoom-out played a dip: {L['phases']}"
        assert L["dest"] == [] and L["land"] == [], f"the zoom-out moved the story: dest {L['dest']} land {L['land']}"
        assert not any(r[1] for r in rec), f"the zoom-out replayed content / ran a move: {sorted({r[1] for r in rec if r[1]})}"
        assert st["settles"] == s0["settles"] + 1, f"expected exactly one settle on zoom-out ({s0['settles']} -> {st['settles']})"
        # a pure zoom (no layout scroll) and back: the story is left alone, no settle at all
        s1 = p.st()
        p.mark()
        p.cdp.send("Input.synthesizePinchGesture", {"x": 195, "y": 332, "scaleFactor": 2, "relativeSpeed": 800,
                                                     "gestureSourceType": "touch"})
        p.page.wait_for_timeout(500)
        _unzoom(p)
        p.page.wait_for_timeout(1200)
        st, L = p.st(), p.read()
        assert st["phase"] == "rest" and st["rendered"] == 1 and L["dest"] == [] and "dip" not in L["phases"], st
        if st["y"] == s1["y"]:
            assert st["settles"] == s1["settles"], f"a pure zoom ran a settle ({s1['settles']} -> {st['settles']})"
    finally:
        p.close()


def test_probe_changes_nothing_at_end(browser, site_url):
    """Judge C6 #1: the touch adapter's in-slop "probe" asks isBypassed in both directions; a probe must change nothing.
    At REST(Get the app) a tiny back move (a sloppy tap / a back-swipe start, held inside the slop) used to stamp the
    release flag, so a scroll to the pin's end within 0.6 s was taken as a release. It must settle back instead."""
    p = Phone(browser, site_url, 390, 664)
    try:
        p.rest_on(0)
        p.goto_beat("end")
        p.page.wait_for_timeout(400)
        p.log()
        p.mark()
        p.swipe(-6, 200, y0=330)                   # a 6 px back move: every touchmove inside the slop (probes only)
        p.page.evaluate("() => { const s = FEStory.state(); window.scrollTo({ top: s.trackY - 1, behavior: 'instant' }); }")
        p.page.wait_for_timeout(1200)
        st, L = p.st(), p.read()
        assert L["moves"], "no in-slop touchmove reached the page (the probe never ran)"
        assert L["dest"] == [] and not L["steps"], f"the tap stepped the story: {L['dest']} {L['steps']}"
        assert "released" not in L["phases"], f"a probe armed the release: a 1 px scroll at Get the app released: {L['phases']}"
        assert st["phase"] == "rest" and st["rendered"] == 8, st
    finally:
        p.close()


def test_sheet_scrolls_natively(browser, site_url):
    """Judge C6 #3 with B6's menu sheet merged: mid-story at 390, a touch scroll inside the open sheet is never prevented,
    the sheet scrolls, and the story does not move."""
    p = Phone(browser, site_url, 390, 664)
    try:
        _still(p.page, 15000)
        p.goto_beat("look")                       # (SCRUB stage 3: a phone does not step; the menu's jump lands it)
        p.page.wait_for_timeout(400)
        y0 = p.page.evaluate("() => scrollY")
        p.page.click("[data-menu-open]")
        p.page.wait_for_function("() => document.querySelector('#fe-menu').open")
        p.page.wait_for_timeout(300)
        geo = p.page.evaluate("""() => { const d = document.querySelector('#fe-menu .fe-menu-scroll'); const r = d.getBoundingClientRect();
            return { sh: d.scrollHeight, ch: d.clientHeight, top: d.scrollTop, x: r.left + r.width / 2, y: r.top + r.height * 0.7 }; }""")
        assert geo["sh"] > geo["ch"] + 20, f"the sheet does not overflow at 390x664, nothing to scroll: {geo}"
        p.log()
        p.mark()
        p.swipe(160, 300, y0=geo["y"])             # a slow forward drag inside the sheet
        p.page.wait_for_timeout(600)
        L = p.read()
        after = p.page.evaluate("() => document.querySelector('#fe-menu .fe-menu-scroll').scrollTop")
        assert L["moves"], "no touchmove reached the page"
        assert not any(prev for _, prev in L["moves"]), f"a touch scroll inside the open sheet was prevented: {L['moves'][:6]}"
        want = min(40, geo["sh"] - geo["ch"]) - 1      # the list's own range (PHONE: the list scrolls inside the sheet, Close below it)
        assert after >= geo["top"] + want, f"the sheet did not scroll ({geo['top']} -> {after}, range {geo['sh'] - geo['ch']})"
        st = p.st()
        assert L["dest"] == [] and not L["steps"] and st["rendered"] == 1, f"the story moved under the sheet: {st} {L['dest']}"
        assert st["y"] == y0, f"the page scrolled under the sheet ({y0} -> {st['y']})"
    finally:
        p.close()


def test_horizontal_swipe_not_intercepted(browser, site_url):
    """A sideways swipe (fast or slow-starting) inside the story never steps and is never prevented."""
    p = Phone(browser, site_url, 390, 664)
    try:
        _still(p.page, 15000)
        p.goto_beat("look")                       # (SCRUB stage 3: a phone does not step; the menu's jump lands it)
        y0 = p.page.evaluate("() => scrollY")
        p.page.evaluate(_TOUCHLOG)
        for offs in ((12, 24, 36, 48, 60, 72), (2, 4, 7, 14, 30, 60, 100)):
            p.cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 60, "y": 330}]})
            for o in offs:
                p.page.wait_for_timeout(16)
                p.cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 60 + o * 2.5, "y": 330 - o * 0.1}]})
            p.cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            p.page.wait_for_timeout(300)
        log = p.page.evaluate("() => window.__c6t")
        assert log and not any(prev for _, prev, _ in log), f"a horizontal swipe was prevented: {log}"
        st = p.st()
        assert st["phase"] == "rest" and st["rendered"] == 1 and abs(st["y"] - y0) <= 30, f"a horizontal swipe moved the story: {st} (from y {y0})"
    finally:
        p.close()
