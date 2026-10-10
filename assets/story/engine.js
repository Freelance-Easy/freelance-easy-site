/* =====================================================================================================================
   FX — the house-style motion engine for the homepage prototype (vault "Motion House Style — One Shape (Light)").
   Ported from invoice-film/tests/common.js + proof.html + premium-pass/motion FM: springs are closed-form step
   responses (pure functions of t, exactly 1 at settle), several targets add up (track), colour arrives as a soft-edged
   ink circle (never a crossfade), text leaves before its morph and arrives after it, and a designed cursor presses every
   change. Every scene is a pure function of its own time t: seek(t) writes every managed style on every frame.
   The clock is document.timeline, so CDP Animation.setPlaybackRate slows a whole scene for frame strips.
   ===================================================================================================================== */
(function () {
  "use strict";
  const FX = (window.FX = {});
  // the direction gate (site v2): the page's loop sets cursor 0..1 (fades while scrubbing backwards) and press 0|1
  // (a press played backwards has no squash). 1/1 everywhere else, so every comp is still a pure function of t.
  FX.gate = { cursor: 1, press: 1 };
  // set class flags in a fixed order (class order never depends on the path taken to t)
  FX.flags = (el, base, on) => {
    let c = base || "";
    for (const [k, v] of on) if (v) c += (c ? " " : "") + k;
    if (el.getAttribute("class") !== c) el.setAttribute("class", c);
  };

  /* ---------------- maths ---------------- */
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const mix = (a, b, k) => a + (b - a) * k;
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const X = (s) => ((ax * s + bx) * s + cx) * s, Y = (s) => ((ay * s + by) * s + cy) * s;
    const dX = (s) => (3 * ax * s + 2 * bx) * s + cx;
    return (k) => {
      if (k <= 0) return 0;
      if (k >= 1) return 1;
      let s = k;
      for (let i = 0; i < 8; i++) {
        const e = X(s) - k, d = dX(s);
        if (Math.abs(e) < 1e-6) return Y(s);
        if (Math.abs(d) < 1e-6) break;
        s -= e / d;
      }
      let lo = 0, hi = 1;
      s = k;
      for (let i = 0; i < 40; i++) {
        const e = X(s) - k;
        if (Math.abs(e) < 1e-7) break;
        if (e > 0) hi = s; else lo = s;
        s = (lo + hi) / 2;
      }
      return Y(s);
    };
  }
  const E = {
    DECEL: bezier(0.05, 0.7, 0.1, 1),       // film.enter
    ACCEL: bezier(0.3, 0, 0.8, 0.15),       // film.exit
    GLIDE: bezier(0.65, 0, 0.35, 1),
    SMOOTH: bezier(0.25, 0.9, 0.25, 1),
    SETTLE: bezier(0.2, 0, 0, 1),
    OPEN: bezier(0.4, 0, 0.2, 1),           // the ink opening (proof.html)
    CLOSE: bezier(0.5, 0, 0.3, 1),          // the ink sealing
    THEME: bezier(0.55, 0, 0.25, 1),        // the app's theme circle: a gentle start, a quick middle, a soft landing
    CUBIC_OUT: (u) => 1 - Math.pow(1 - clamp(u), 3),   // the app's own easeOutCubic (animateOdometers, applyDashboardDelta)
  };
  const P = (t, t0, dur, ease = E.SMOOTH) => ease(clamp((t - t0) / dur));
  // closed-form spring step 0 -> 1 (f Hz, z damping); exactly 1 once the envelope is under 0.03 % (holds are still)
  function spring(t, f = 2.3, z = 0.86) {
    if (t <= 0) return 0;
    const w = 2 * Math.PI * f;
    if (z < 1) {
      const r = Math.sqrt(1 - z * z), ts = -Math.log(0.0003 * r) / (z * w);
      if (t >= ts) return 1;
      const wd = w * r;
      return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z / r) * Math.sin(wd * t));
    }
    const ts = 9.5 / w;
    if (t >= ts) return 1;
    return 1 - Math.exp(-w * t) * (1 + w * t);
  }
  // when spring(t, f, z) is exactly 1 (its hold is still from here on)
  const settleTime = (f = 2.3, z = 0.86) => (z < 1 ? -Math.log(0.0003 * Math.sqrt(1 - z * z)) / (z * 2 * Math.PI * f) : 9.5 / (2 * Math.PI * f));
  // a value with several targets: the sum of one spring per change (velocity stays continuous; still seekable)
  function track(t, keys, f = 2.3, z = 0.86) {
    let v = keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const k = keys[i];
      v += (k[1] - keys[i - 1][1]) * spring(t - k[0], k[2] || f, k[3] || z);
    }
    return v;
  }
  // a press: 0 -> 1 (down, 80 ms) -> 0 (released, 220 ms)
  function press(t, t0, down = 0.08, up = 0.22) {
    const d = t - t0;
    if (d <= 0 || d >= down + up) return 0;
    return d < down ? E.SMOOTH(d / down) : 1 - E.SETTLE((d - down) / up);
  }
  const smooth = (e0, e1, x) => { const u = clamp((x - e0) / (e1 - e0)); return u * u * (3 - 2 * u); };
  const money = (v) => (v < 0 ? "-$" : "$") + Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const money0 = (v) => "$" + Math.round(v).toLocaleString("en-US");
  Object.assign(FX, { clamp, mix, bezier, E, P, spring, settleTime, track, press, smooth, money, money0 });

  /* ---------------- colour ---------------- */
  function rgba(s) {
    const m = (s || "").match(/rgba?\(([^)]+)\)/);
    if (!m) {
      const h = (s || "").match(/^#([0-9a-f]{6})$/i);
      if (h) { const n = parseInt(h[1], 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1]; }
      return [0, 0, 0, 0];
    }
    const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  }
  const mixC = (a, b, k) => a.map((v, i) => v + (b[i] - v) * k);
  const cssC = (c, aMul = 1) => `rgba(${Math.round(c[0])},${Math.round(c[1])},${Math.round(c[2])},${(c[3] * aMul).toFixed(3)})`;
  const solid = (c, fb) => (c && c[3] > 0.01 ? [c[0], c[1], c[2], 1] : fb);
  // composite c (with alpha) over an opaque background
  const over = (c, bg) => [mix(bg[0], c[0], c[3]), mix(bg[1], c[1], c[3]), mix(bg[2], c[2], c[3]), 1];
  Object.assign(FX, { rgba, mixC, cssC, solid, over });

  /* ---------------- dom ---------------- */
  const css = (el, p, v) => el.style.setProperty(p, v);
  function div(cls, parent) {
    const d = document.createElement("div");
    if (cls) d.className = cls;
    if (parent) parent.appendChild(d);
    return d;
  }
  function frag(markup) {
    const d = document.createElement("div");
    d.innerHTML = markup.trim();
    return d.firstElementChild;
  }
  // THE VISUAL RECT of an element (phones, round E). The states are CSS-zoomed wrappers, and the shapes are sized from
  // their rects. Chromium and WebKit with evaluation-time zoom return getBoundingClientRect() as drawn (zoom applied);
  // shipping iOS WebKit returns it DIVIDED by the element's effective zoom, so every shape came out 1/zoom of its
  // content (the founder's iPhone, 2026-10-10: the Make card at 1/1.36, the Create pill at 1/1.75, Know's tabs pushed
  // off the card, Grow's KPIs past the stage). A zoom:2 probe tells the model once; on a legacy engine the rect is
  // scaled back by the element's own zoom product. Elsewhere it is the plain call (byte-identical frames). Every preset:
  // desktop and iPad Safari measure the same way. The probe runs once at startup; per frame it costs one test.
  let zoomLegacy = null;
  function legacyZoom() {
    if (zoomLegacy !== null) return zoomLegacy;
    const o = document.createElement("div"), i = document.createElement("div");
    o.style.cssText = "position:absolute;left:0;top:0;visibility:hidden;pointer-events:none;zoom:2";
    i.style.cssText = "width:50px;height:10px";
    o.appendChild(i);
    (document.body || document.documentElement).appendChild(o);
    const w = i.getBoundingClientRect().width;
    o.remove();
    zoomLegacy = w > 0 && w < 75;
    return zoomLegacy;
  }
  function vrect(el) {
    const r = el.getBoundingClientRect();
    if (!(zoomLegacy ?? legacyZoom())) return r;
    let z = 1;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const v = parseFloat(getComputedStyle(e).zoom); if (v > 0) z *= v; }
    if (Math.abs(z - 1) < 1e-6) return r;
    return { left: r.left * z, top: r.top * z, right: r.right * z, bottom: r.bottom * z, width: r.width * z, height: r.height * z,
      x: r.x * z, y: r.y * z };
  }
  // element rect in the scene's canvas units (the scene root is measured at scale 1)
  function rectIn(el, root) {
    const r = vrect(el), o = vrect(root);
    return { x: r.left - o.left, y: r.top - o.top, w: r.width, h: r.height, cx: r.left - o.left + r.width / 2,
      cy: r.top - o.top + r.height / 2 };
  }
  const even = (v) => 2 * Math.round(v / 2);
  // a real element's own skin, read from its computed style; zoom = the wrapper's CSS zoom (rects are zoomed already)
  function skin(el, zoom = 1) {
    const b = vrect(el), cs = getComputedStyle(el);
    return { w: even(b.width), h: even(b.height), r: parseFloat(cs.borderTopLeftRadius) * zoom,
      bw: parseFloat(cs.borderTopWidth) * zoom, bc: rgba(cs.borderTopColor), bg: rgba(cs.backgroundColor),
      color: rgba(cs.color) };
  }
  Object.assign(FX, { css, div, frag, rectIn, skin, even, vrect });
  if (document.body) legacyZoom();
  else document.addEventListener("DOMContentLoaded", legacyZoom, { once: true });

  /* ---------------- the shape: one surface whose skin rides springs ---------------- */
  // the long soft shadow that grows with the shape (house style § 2; dark: deeper, with a top rim and a light hairline)
  function shadow(h, dark, k = 1) {
    if (dark) {
      return `0 ${(2 + 0.004 * h).toFixed(2)}px ${(4 + 0.008 * h).toFixed(2)}px rgba(0,0,0,${(0.4 * k).toFixed(3)}), ` +
        `0 ${(10 + 0.04 * h).toFixed(1)}px ${(30 + 0.08 * h).toFixed(1)}px -8px rgba(0,0,0,${(0.55 * k).toFixed(3)}), ` +
        `0 ${(26 + 0.08 * h).toFixed(1)}px ${(70 + 0.16 * h).toFixed(1)}px -20px rgba(0,0,0,${(0.6 * k).toFixed(3)})`;
    }
    return `0 ${(1 + 0.002 * h).toFixed(2)}px ${(2 + 0.004 * h).toFixed(2)}px rgba(0,0,0,${(0.1 * k).toFixed(3)}), ` +
      `0 ${(6 + 0.03 * h).toFixed(1)}px ${(18 + 0.06 * h).toFixed(1)}px -6px rgba(0,0,0,${(0.22 * k).toFixed(3)}), ` +
      `0 ${(18 + 0.07 * h).toFixed(1)}px ${(48 + 0.14 * h).toFixed(1)}px -18px rgba(0,0,0,${(0.26 * k).toFixed(3)})`;
  }
  // (phones, round C, Astra #13) a small floating card or pill: one short, light shadow instead of the long one.
  // lite = {y, b} in canvas px (the scene converts its screen target with --demo-scale); k = the shadow strength
  function liteShadow(lite, dark, k = 1) {
    return `0 ${lite.y.toFixed(2)}px ${lite.b.toFixed(2)}px rgba(0,0,0,${((dark ? 0.32 : 0.1) * k).toFixed(3)})`;
  }
  // g = {cx, cy, w, h, r, bw}; look = {fill, line, lineA, dark, sq (press squash 0..1), sh (shadow strength), rimA, lite}
  function drawShape(el, g, look) {
    const { fill, line, dark } = look;
    const lineA = look.lineA == null ? 1 : look.lineA;
    const rimA = look.rimA == null ? lineA : look.rimA;
    const sq = 1 - 0.045 * (look.sq || 0) * FX.gate.press;   // no squash while the story plays backwards
    const rim = dark ? `, inset 0 1.5px 0 rgba(255,255,255,${(0.1 * rimA).toFixed(3)}), 0 0 0 1px rgba(160,190,240,${(0.07 * rimA).toFixed(3)})` : "";
    css(el, "left", `${(g.cx - g.w / 2).toFixed(2)}px`);
    css(el, "top", `${(g.cy - g.h / 2).toFixed(2)}px`);
    css(el, "width", `${Math.max(0, g.w).toFixed(2)}px`);
    css(el, "height", `${Math.max(0, g.h).toFixed(2)}px`);
    css(el, "background", cssC(fill));
    css(el, "border-radius", `${Math.max(0, Math.min(g.r, g.h / 2, g.w / 2)).toFixed(2)}px`);
    const shk = look.sh == null ? 1 : look.sh;
    const drop = look.lite ? liteShadow(look.lite, dark, shk) : shadow(g.h, dark, shk);
    css(el, "box-shadow", `inset 0 0 0 ${Math.max(0, g.bw).toFixed(2)}px ${cssC(line, lineA)}${rim}, ${drop}`);
    css(el, "transform", sq === 1 ? "none" : `scale(${sq.toFixed(5)})`);
    css(el, "opacity", look.alpha == null || look.alpha >= 0.999 ? "1" : look.alpha.toFixed(3));
    css(el, "display", look.alpha === 0 ? "none" : "block");
  }
  // the ink (M17): a colour layer under the content, shaped by a soft-edged radial mask.
  // s = {mode: none|full|hole|disc, k (0..1), x, y (in the shape's own box), w, h, color}
  function drawInk(ink, s) {
    // every managed property is written on every frame (a pure function of t: scrubbing back leaves nothing behind)
    css(ink, "display", s.mode === "none" ? "none" : "block");
    css(ink, "background", s.mode === "none" ? "transparent" : cssC(s.color));
    let mask = "none";
    if (s.mode === "hole" || s.mode === "disc") {
      const far = Math.hypot(Math.max(s.x, s.w - s.x), Math.max(s.y, s.h - s.y));
      const fe = Math.max(4, 0.07 * Math.min(s.w, s.h));
      const rr = s.k * (far + fe);
      const inside = s.mode === "hole" ? "transparent" : "#000", outside = s.mode === "hole" ? "#000" : "transparent";
      mask = `radial-gradient(circle at ${s.x.toFixed(1)}px ${s.y.toFixed(1)}px, ${inside} ${Math.max(0, rr - fe).toFixed(1)}px, ${outside} ${rr.toFixed(1)}px)`;
    }
    css(ink, "-webkit-mask-image", mask);
    css(ink, "mask-image", mask);
  }
  // THE THEME CIRCLE: the app's light/dark switch (premium-pass app: proto.js themeReveal + premium.css R21), as a pure
  // function of p (0..1, linear in time): a reveal through an expanding circle with a WIDE soft edge. The edge is 22 %
  // of the current radius, clamped to 48–220 SCREEN px (scale: canvas units -> screen px); the radius runs 0 -> the
  // farthest corner of the revealed area + the edge's own width (+2 px, as the app's), so it lands fully opaque; time
  // follows E.THEME. All lengths in and out are canvas units.
  const THEME = (FX.THEME = { dur: 0.46, k: 0.22, min: 48, max: 220 });
  // (ease: the theme switch's own E.THEME by default; the PDF -> Look reveal passes a slower, softer one)
  function themeCircle(p, far, scale, ease = E.THEME) {
    const s = scale > 0 ? scale : 1;
    const need = far * s + 2;                          // the inner (opaque) radius at the end, screen px
    const { k, min, max } = THEME;
    const end = need <= min / k - min ? need + min : need <= max / k - max ? need / (1 - k) : need + max;
    const r = ease(clamp(p)) * end;
    const fe = clamp(k * r, min, max);
    return { r: r / s, inner: Math.max(0, r - fe) / s, fe: fe / s };
  }
  // the circle as a mask on an element's own box (x, y, far in that box's units): "disc" shows the element inside the
  // circle (nothing at p <= 0, unmasked at p >= 1), "hole" hides it there (unmasked at p <= 0; the caller hides the
  // element at p >= 1). Both mask properties are written on every call (pure: scrubbing back closes the circle).
  function circleMask(el, mode, p, x, y, far, scale, ease) {
    let m = "none";
    if (mode === "disc" ? p < 1 : p > 0) {
      const c = themeCircle(p, far, scale, ease);
      const a = mode === "hole" ? "transparent" : "#000", b = mode === "hole" ? "#000" : "transparent";
      m = `radial-gradient(circle at ${x.toFixed(1)}px ${y.toFixed(1)}px, ${a} ${c.inner.toFixed(2)}px, ${b} ${c.r.toFixed(2)}px)`;
    }
    css(el, "-webkit-mask-image", m);
    css(el, "mask-image", m);
  }
  // THE BLOOM (site v2.4, Daniel: "feel like it comes out from the button rather than from the click … from the edgees of
  // the button or the center of the button"): the theme circle, born from a button. From the button's centre it opens as
  // an ellipse of the button's own proportions (hw, hh: its half-size), so it fills the button out to its edges first;
  // past them its extra width stays put while the radius grows, so it rounds into the circle. Its soft edge starts tight
  // (button scale, 0.3 of the radius) and widens into the theme circle's, which it is from there on: it lands exactly as
  // circleMask's "disc" (far from the centre, fully opaque, unmasked at p >= 1). Pure in p.
  function bloomMask(el, p, x, y, hw, hh, far, scale, ease = E.THEME) {
    let m = "none";
    if (p < 1) {
      const s = scale > 0 ? scale : 1;
      const need = far * s + 2;
      const { k, min, max } = THEME;
      const end = need <= min / k - min ? need + min : need <= max / k - max ? need / (1 - k) : need + max;
      const r = ease(clamp(p)) * end;                  // screen px, along the button's short axis
      if (r < 0.05) m = "linear-gradient(transparent, transparent)";
      else {
        const fe = clamp(k * r, Math.min(min, 0.3 * r), max);
        const H = hh * s, rx = r + Math.max(0, hw * s - H) * Math.min(1, r / H);
        m = `radial-gradient(${(rx / s).toFixed(2)}px ${(r / s).toFixed(2)}px at ${x.toFixed(1)}px ${y.toFixed(1)}px, #000 ${((100 * (r - fe)) / r).toFixed(2)}%, transparent 100%)`;
      }
    }
    css(el, "-webkit-mask-image", m);
    css(el, "mask-image", m);
  }
  // the farthest corner of any of the rects ({cx, cy, w, h}) from (x, y)
  const farFrom = (x, y, ...rs) => Math.max(0, ...rs.map((r) => Math.hypot(Math.max(x - (r.cx - r.w / 2), r.cx + r.w / 2 - x),
    Math.max(y - (r.cy - r.h / 2), r.cy + r.h / 2 - y))));
  // the stage's scale (canvas units -> screen px), as site.js lays it out on a mount's root or a seam's layer
  const stageScale = (el) => parseFloat(el && el.style.getPropertyValue("--demo-scale")) || 1;
  // content in/out (M16): arrives over 0.16 s from a 7 px blur after its morph starts; leaves in 0.10 s before the next
  function alphaAt(t, tin, tout) {
    const a = tin < 0 ? 1 : P(t, tin, 0.16, E.DECEL), b = 1 - P(t, tout, 0.1, E.ACCEL);
    return Math.min(a, b);
  }
  // place a zoomed state wrapper inside its shape: x, y in canvas units relative to the shape's box
  function placeSt(st, a, x, y, zoom) {
    css(st, "display", a > 0.001 ? "inline-block" : "none");
    css(st, "opacity", a >= 0.999 ? "1" : a.toFixed(3));
    css(st, "filter", a >= 0.999 ? "none" : `blur(${((1 - a) * 7).toFixed(2)}px)`);
    css(st, "left", `${(x / zoom).toFixed(2)}px`);
    css(st, "top", `${(y / zoom).toFixed(2)}px`);
    css(st, "transform", "none");                      // a seam may scale a state; the piece's own frame never does
  }
  // a text swap in one slot (M16): the old leaves (0.10 s, rising 0.45 em), the new arrives 0.11 s later (0.16 s)
  function swapText(oldEl, newEl, t, t0) {
    const a = P(t, t0, 0.1, E.ACCEL), b = P(t, t0 + 0.11, 0.16, E.DECEL);
    css(oldEl, "opacity", (1 - a).toFixed(3));
    css(oldEl, "transform", a <= 0 ? "none" : `translateY(${(-0.45 * a).toFixed(3)}em)`);
    css(oldEl, "visibility", a >= 1 ? "hidden" : "visible");
    css(newEl, "opacity", b.toFixed(3));
    css(newEl, "transform", b >= 1 ? "none" : `translateY(${(0.45 * (1 - b)).toFixed(3)}em)`);
    css(newEl, "visibility", b <= 0 ? "hidden" : "visible");
  }
  Object.assign(FX, { shadow, drawShape, drawInk, themeCircle, circleMask, bloomMask, farFrom, stageScale, alphaAt, placeSt, swapText });

  /* ---------------- the designed cursor ---------------- */
  const ARROW = "M3 3 L3 31.5 L10 25 L14.6 35.6 L19.3 33.6 L14.8 23.2 L24.2 23.2 Z";
  class Cursor {
    // keys: [[t, [x, y], f, z], ...] (the first is the start); presses: [t, ...]; size = width in canvas units
    constructor(parent, size = 36) {
      const ns = "http://www.w3.org/2000/svg";
      this.el = document.createElementNS(ns, "svg");
      this.el.setAttribute("viewBox", "0 0 28 40");
      this.el.setAttribute("class", "fx-cursor");
      this.el.setAttribute("aria-hidden", "true");
      const p = document.createElementNS(ns, "path");
      p.setAttribute("d", ARROW);
      p.setAttribute("fill", "#111");
      p.setAttribute("stroke", "#fff");
      p.setAttribute("stroke-width", "2.2");
      p.setAttribute("stroke-linejoin", "round");
      this.el.appendChild(p);
      parent.appendChild(this.el);
      this.size = size;
      css(this.el, "width", `${size}px`);
      css(this.el, "height", `${(size * 40) / 28}px`);
      this.tip = (3 * size) / 28;
      this.keys = [[0, [0, 0]]];
      this.presses = [];
      this.fade = null;   // [tIn, tOut]
    }
    at(t) {
      const K = this.keys;
      let x = K[0][1][0], y = K[0][1][1];
      for (let i = 1; i < K.length; i++) {
        const [t0, [tx, ty], f, z] = K[i], [px, py] = K[i - 1][1];
        const p = spring(t - t0, f || 2, z || 0.95), dx = tx - px, dy = ty - py;
        const arc = 0.08 * Math.sin(Math.PI * clamp(p));        // a slight arc, 8 % of the chord
        x += dx * p - dy * arc;
        y += dy * p + dx * arc;
      }
      return [x, y];
    }
    down(t) {
      let d = 0;
      for (const p of this.presses) d = Math.max(d, press(t, p));
      return d;
    }
    draw(t) {
      const [x, y] = this.at(t);
      const s = 1 - 0.14 * this.down(t) * FX.gate.press;
      css(this.el, "transform", `translate(${(x - this.tip).toFixed(2)}px, ${(y - this.tip).toFixed(2)}px) scale(${s.toFixed(4)})`);
      css(this.el, "transform-origin", `${this.tip}px ${this.tip}px`);
      let a = 1;
      if (this.fade) a = P(t, this.fade[0], 0.2, E.DECEL) * (1 - P(t, this.fade[1], 0.3, E.DECEL));
      // (phones, round B2: gaps [[tOut, tIn], ...]: hidden between two actions, with the same fade curves; unset elsewhere)
      if (this.gaps) for (const [g0, g1] of this.gaps) a *= 1 - (1 - P(t, g1, 0.2, E.DECEL)) * P(t, g0, 0.3, E.DECEL);
      // the hand never walks backwards: while the story reverses it fades out (FX.gate, driven by the page's loop)
      a *= FX.gate.cursor;
      css(this.el, "opacity", a >= 0.999 ? "1" : a.toFixed(3));
      css(this.el, "display", a <= 0.001 ? "none" : "block");
      return [x, y];
    }
  }
  FX.Cursor = Cursor;
  // is the cursor tip inside rect r (canvas units) at time t? (the app's real :hover follows the hand)
  FX.tipIn = (cur, t, r, pad = 0) => {
    const [x, y] = cur.at(t);
    return x >= r.x - pad && x <= r.x + r.w + pad && y >= r.y - pad && y <= r.y + r.h + pad;
  };

  /* ---------------- reduced motion, clock, director ---------------- */
  FX.reduced = () => document.documentElement.classList.contains("calm");
  FX.now = () => {
    const t = document.timeline && document.timeline.currentTime;
    return (t == null ? performance.now() : Number(t)) / 1000;
  };
  // One mover at a time: jobs run strictly in sequence. A job = {name, dur, seek(t), rate, before(), after()}.
  class Director {
    constructor() {
      this.queue = [];
      this.job = null;
      this.raf = 0;
      this.t0 = 0;
      this.tick = this.tick.bind(this);
      this.listeners = new Set();
    }
    run(job) {
      return new Promise((resolve) => {
        this.queue.push({ ...job, resolve });
        if (!this.job) this.next();
      });
    }
    clear() {                 // drop pending jobs (each still resolves, flagged skipped)
      const q = this.queue;
      this.queue = [];
      for (const j of q) j.resolve({ skipped: true });
    }
    finishNow() {             // jump the running job to its end (used when the visitor races ahead)
      if (this.job) { cancelAnimationFrame(this.raf); this.finish(); }
    }
    busy() { return !!this.job || this.queue.length > 0; }
    next() {
      this.job = this.queue.shift() || null;
      if (!this.job) { this.emit(); return; }
      const j = this.job;
      if (j.before) j.before();
      this.t0 = FX.now();
      j.t = 0;
      this.emit();
      if (!j.dur || j.dur <= 0) { this.finish(); return; }
      cancelAnimationFrame(this.raf);
      this.raf = requestAnimationFrame(this.tick);
    }
    tick() {
      const j = this.job;
      if (!j) return;
      const rate = j.rate || 1;
      const now = FX.now();
      j.t = Math.min(j.dur, j.t + Math.max(0, now - this.t0) * rate);
      this.t0 = now;
      j.seek(j.t);
      if (j.t >= j.dur) { this.finish(); return; }
      this.raf = requestAnimationFrame(this.tick);
    }
    finish() {
      const j = this.job;
      if (j) {
        j.seek(j.dur);
        if (j.after) j.after();
        j.resolve({ skipped: false });
      }
      this.job = null;
      this.next();
    }
    on(fn) { this.listeners.add(fn); }
    emit() { for (const fn of this.listeners) fn(this.job); }
  }
  FX.director = new Director();
})();
