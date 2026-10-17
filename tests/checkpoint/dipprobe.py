"""FLICKER2 / FADEDEF: the content-interrupt probe (test_flicker2.py and the strip sheets use it).

One trial: land on chapter k by one notch from REST(k-1), wait `wait` s while k's content plays, one notch forward.
CDP screencast frames from the gesture -150 ms to +span ms; per frame the stage's mean luminance (Rec. 709 Y, 0..1,
over .stage-wrap's rect) and the engine state nearest to it. The rest frame's luminance is measured afterwards
(FEStory.goTo(k), at rest). Needs pillow.
"""
from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass, field

from PIL import Image, ImageStat

_REC = r"""() => {
  const M = window.__xp = { rec: [], land: [], dest: [] };
  FEStory.onLand(p => M.land.push([performance.now(), p.index, p.final, p.source]));
  FEStory.onDest(p => M.dest.push([performance.now(), p.index, p.source, !!p.preview]));
  const tick = () => { if (!M.rec) return; const s = FEStory.state();
    const op = parseFloat(getComputedStyle(document.querySelector('.stage-wrap')).opacity);
    M.rec.push([performance.now(), s.phase, s.dest, s.rendered, s.T, s.dip ? 1 : 0, op,
      document.querySelectorAll('.stage-wrap').length]); requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}"""
_NOTCH = r"""(at) => new Promise((done) => setTimeout(() => {
  const x = innerWidth / 2, y = innerHeight / 2;
  const w = new WheelEvent('wheel', { deltaY: 100, deltaMode: 0, clientX: x, clientY: y, bubbles: true, cancelable: true });
  Object.defineProperty(w, 'wheelDeltaY', { value: -120 });
  const t = performance.now(); document.elementFromPoint(x, y).dispatchEvent(w); done(t);
}, Math.max(0, at - performance.now())))"""
_RECT = "() => { const r = document.querySelector('.stage-wrap').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"
_REST = "(k) => { const s = FEStory.state(); return s.phase === 'rest' && s.rendered === k && s.dest === k; }"


@dataclass
class Trial:
    k: int
    at: float = 0.0                         # gesture time (performance.now ms)
    frames: list = field(default_factory=list)   # [(ms from gesture, Y, state row, jpeg bytes)]
    rest_y: float = 0.0
    pre_y: float = 0.0
    steps: list = field(default_factory=list)
    end: list = field(default_factory=list)
    free: bool = False
    dip_frames: int = 0                     # engine frames after the gesture with FEStory.state().dip set
    min_opacity: float = 1.0                # the live stage's lowest computed opacity after the gesture
    held_frames: int = 0                    # engine frames after the gesture with the held copy up (2 .stage-wrap)

    def window_min(self, lo: float = 0, hi: float = 400) -> float:
        return min(f[1] for f in self.frames if lo <= f[0] <= hi)

    def y_at(self, ms: float) -> float:
        return min(self.frames, key=lambda f: abs(f[0] - ms))[1]

    def floor(self) -> float:
        """The darker of the two pictures the crossfade blends: the content frame before the gesture and the rest frame
        (Sol FLICKER2-1 #3: never a frame from the transition under test)."""
        return min(self.pre_y, self.rest_y)


def _lum(jpeg: bytes, rect, scale) -> float:
    im = Image.open(io.BytesIO(jpeg)).convert("RGB")
    x, y, w, h = (round(v * scale) for v in rect)
    im = im.crop((x + 2, y + 2, x + w - 2, y + h - 2))
    r, g, b = (v / 255 for v in ImageStat.Stat(im).mean)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def run(page, k: int, wait: float, span: int = 1200, width: int = 1440) -> Trial:
    tr = Trial(k)
    if k == 0:                              # Make: its arrival (the intro) is its content; land = the load
        page.reload(wait_until="load")
        page.wait_for_function("() => window.FEStory && window.__site && window.__site.TL", timeout=15000)
    else:
        page.evaluate(f"() => FEStory.goTo({k - 1}, {{source: 'jump'}})")
        page.wait_for_function(_REST, arg=k - 1, timeout=20000)
        page.wait_for_timeout(900)
    page.evaluate(_REC)
    shots: list = []
    origin = page.evaluate("() => performance.timeOrigin")
    cdp = page.context.new_cdp_session(page)

    def on_frame(f):
        shots.append((f["metadata"]["timestamp"] * 1000 - origin, base64.b64decode(f["data"])))
        try:
            cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]})
        except Exception:  # noqa: BLE001 - the session may close first
            pass

    cdp.on("Page.screencastFrame", on_frame)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 80, "maxWidth": 720, "maxHeight": 720, "everyNthFrame": 1})
    if k == 0:
        t_land = page.evaluate("() => performance.now()")
    else:
        page.evaluate(_NOTCH, page.evaluate("() => performance.now() + 20"))
        page.wait_for_function(f"() => window.__xp.land.some(l => l[1] === {k} && l[2])", timeout=20000)
        t_land = page.evaluate(f"() => window.__xp.land.find(l => l[1] === {k} && l[2])[0]")
    tr.at = page.evaluate(_NOTCH, t_land + wait * 1000)
    page.wait_for_timeout(span + 150)
    cdp.send("Page.stopScreencast")
    page.wait_for_function(_REST, arg=k + 1, timeout=20000)
    page.wait_for_timeout(700)
    rec = page.evaluate("() => { const r = window.__xp; const o = {rec: r.rec, dest: r.dest}; r.rec = null; return o; }")
    tr.dest = [[round(d[0] - tr.at), d[1], d[2]] for d in rec["dest"]]
    tr.steps = [d[1] for d in rec["dest"] if d[0] >= tr.at - 1 and d[2] == "step"]
    tr.end = rec["rec"][-1][1:4]
    tr.free = any(r[1] in ("free", "released") for r in rec["rec"] if r[0] >= tr.at)
    after = [r for r in rec["rec"] if r[0] >= tr.at]
    tr.dip_frames = sum(1 for r in after if r[5])
    tr.min_opacity = min((r[6] for r in after), default=1.0)
    tr.held_frames = sum(1 for r in after if r[7] > 1)
    rect = page.evaluate(_RECT)
    vw = page.evaluate("() => innerWidth")
    for t, jpg in shots:
        if tr.at - 150 <= t <= tr.at + span:
            scale = Image.open(io.BytesIO(jpg)).size[0] / vw
            st = min(rec["rec"], key=lambda r: abs(r[0] - t))
            tr.frames.append((t - tr.at, _lum(jpg, rect, scale), st, jpg))
    pre = [f for f in tr.frames if f[0] < 0]
    tr.pre_y = pre[-1][1] if pre else tr.frames[0][1]
    # the rest frame of k, as the skip cuts to it
    page.evaluate(f"() => FEStory.goTo({k}, {{source: 'jump'}})")
    page.wait_for_function(_REST, arg=k, timeout=20000)
    page.wait_for_timeout(400)
    png = page.screenshot(type="jpeg", quality=80)
    sc = Image.open(io.BytesIO(png)).size[0] / vw
    tr.rest_y = _lum(png, rect, sc)
    cdp.detach()
    return tr


def open_page(browser, url: str, width: int, height: int, theme: str):
    ctx = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="no-preference")
    ctx.add_init_script(f"try{{localStorage.setItem('fe-theme','{theme}')}}catch(e){{}}")
    page = ctx.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_function("() => window.FEStory && window.__site && window.__site.TL", timeout=15000)
    page.mouse.move(width / 2, height / 2)
    page.wait_for_function(_REST, arg=0, timeout=20000)
    return ctx, page
