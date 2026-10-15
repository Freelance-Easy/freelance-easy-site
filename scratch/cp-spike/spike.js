/* C0a sticky-track feasibility spike (scratch only, never deployed).
 * The R1 §3.2 "A2" model in isolation: a sticky pin over a short native track (one pin height per beat), JS-owned
 * wheel/key/touch input, story time decoupled from scrollY, FREE settle for scroll sources we cannot intercept, and
 * RELEASED native scroll after the last beat. The probes in run_probes.py drive it through window.__cp.
 * Query: ?n=9 beats · ?tr=500&ct=700 (ms transition / content) · ?noscrollend (force the Safari idle fallback)
 *        · ?csszoom=1.25 (CSS zoom on the stage, the site's vrect trap) · any CFG key, e.g. ?SETTLE_IDLE=200
 */
(() => {
  "use strict";
  const Q = new URLSearchParams(location.search);
  const N = +(Q.get("n") || 9);
  const TR = +(Q.get("tr") || 500), CT = +(Q.get("ct") || 700);
  const NATIVE_SCROLLEND = "onscrollend" in window;
  const HAS_SCROLLEND = NATIVE_SCROLLEND && !Q.has("noscrollend");
  const NAMES = ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"];
  const CFG = {
    // R1 §3.4 detector (unchanged starting values)
    LINE_PX: 33.3, MIN_DELTA: 0.5, START_PX: 8, START_WIN: 120, QUIET_SMOOTH: 140, QUIET_NOTCH: 220,
    W_NOW: 50, W_PREV: 120, CONT_GAP: 45, TAIL_GATE: 0.6, RISE_RATIO: 1.8, V_RISE_MIN: 1000,
    MIN_STEP_MS: 250, REPEAT_MS: 850, SUSTAIN_K: 0.7, REVERSE_PX: 12, REVERSE_WIN: 80, KEY_REPEAT_MS: 420,
    SWIPE_MIN_PX: 36, SWIPE_FRAC: 0.05, SWIPE_VEL: 0.4, TOUCH_SLOP: 8, DIR_RATIO: 1.2,
    DIP_OUT: 100, DIP_IN: 120, DIP_COOLDOWN: 600, RUSH_LEFT: 600,
    // C0a settle rules (the ICX patch in docs/cp-spike-verdict.md)
    ACK_TOL: 1.5,        // px: a scroll event within this of the pending programmatic target is ours
    ACK_MS: 400,         // ms: how long a programmatic target stays pending
    SETTLE_IDLE: 150,    // ms of no scroll events = settle, where scrollend is missing (Safari) or as the grace
    SETTLE_BACKSTOP: 700,// ms: settle even if scrollend never arrives (scrollend supported)
    RESIZE_GRACE: 250,   // ms after a geometry change: foreign scroll events are re-snapped, never FREE
    HOLD_MAX: 10000,     // ms: a scrollbar hold with no mouseup ends after this
    SCROLLEND_GRACE: 50, // ms of no further scroll after a scrollend before settling (autoscroll fires many)
    REENTRY_STICKY_MS: 800, // ms after a settle from RELEASED: a new FREE episode still counts as re-entry (momentum
                            // that outlives our snap must not walk the story back from below)
  };
  for (const k of Object.keys(CFG)) if (Q.has(k)) CFG[k] = +Q.get(k);

  const $ = (s) => document.querySelector(s);
  const doc = document.documentElement, header = $(".hdr"), story = $("#story"), pin = $(".pin"), track = $(".track");
  const stage = $("#stage"), nameEl = $("#name"), phEl = $("#ph"), bar = $("#bar"), rail = $("#rail"), stEl = $("#st");
  const svhProbe = $("#svh");
  if (Q.has("csszoom")) stage.style.zoom = Q.get("csszoom");
  // ?classicbar: a styled (non-overlay) root scrollbar, the stand-in for a Windows classic scrollbar on a Mac proxy
  if (Q.has("classicbar")) { const st = document.createElement("style");
    st.textContent = "html::-webkit-scrollbar{width:15px;background:#222}html::-webkit-scrollbar-thumb{background:#888;border-radius:7px}";
    document.head.appendChild(st); }
  const now = () => performance.now();
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  // ---------- log (read by the probes) ----------
  const L = [];
  const C = { scroll: 0, acked: 0, foreign: 0, scrollend: 0, settles: 0, settleCancel: 0, steps: 0, lands: 0, dips: 0,
    wheel: 0, wheelPrevented: 0, wheelPassed: 0, resizeSnaps: 0, barDown: 0, barUp: 0, holdTimeouts: 0, touchSteps: 0 };
  const log = (ev, o) => { L.push(Object.assign({ t: +now().toFixed(1), ev, y: +window.scrollY.toFixed(2), ph: S.phase,
    r: S.rendered, d: S.dest }, o || {})); if (L.length > 4000) L.splice(0, 1000); };

  // ---------- geometry (offset chain + scrollY only: never getBoundingClientRect, the Safari CSS-zoom trap) ----------
  let G = {};
  function absTop(el) { let y = 0; for (let e = el; e; e = e.offsetParent) y += e.offsetTop; return y; }
  function measure() {
    const H = header.offsetHeight, svh = svhProbe.offsetHeight;
    const P = Math.max(1, Math.round(svh - H));                     // BEAT_PX = the pin height, integer CSS px
    pin.style.height = P + "px";
    track.style.height = (N - 1) * P + "px";
    const storyTop = absTop(story) - H;                              // the scrollY at which the pin sticks
    G = { H, svh, P, storyTop, storyEnd: storyTop + (N - 1) * P, iw: innerWidth, ih: innerHeight, at: now() };
    return G;
  }
  const yOf = (b) => G.storyTop + b * G.P;
  const maxScroll = () => doc.scrollHeight - innerHeight;
  const nearestBeat = (y = window.scrollY) => clamp(Math.round((y - G.storyTop) / G.P), 0, N - 1);

  // ---------- state ----------
  const S = { phase: "rest", rendered: 0, dest: 0, busy: false, run: null, timer: 0, lastDipAt: -1e9,
    ack: null, free: null, held: false, heldAt: 0, gest: null, touch: null, lastTouchEnd: -1e9, lastKeyStep: -1e9,
    lastWheelT: -1e9, geomAt: -1e9, reentryUntil: -1e9 };

  // ---------- programmatic scroll + acknowledgement (rule S1) ----------
  function syncScroll(y, why) {
    y = clamp(Math.round(y), 0, Math.max(0, maxScroll()));
    const cur = window.scrollY;
    if (Math.abs(cur - y) <= 0.5) { log("sync-noop", { to: y, why }); return; }   // no event will come: arm nothing
    S.ack = { y, until: now() + CFG.ACK_MS, why, events: 0 };
    window.scrollTo({ top: y, left: 0, behavior: "instant" });
    S.lastY = window.scrollY;
    log("sync", { to: y, why, syncY: +window.scrollY.toFixed(2) });
  }
  function onScroll() {
    C.scroll++;
    const y = window.scrollY, t = now();
    // the last position seen at the current viewport size (a rotation can move scrollY before "resize" fires: S7)
    if (innerWidth === G.iw && innerHeight === G.ih) S.lastY = y;
    if (S.ack && t <= S.ack.until && Math.abs(y - S.ack.y) <= CFG.ACK_TOL) {
      S.ack.events++; C.acked++; log("scroll-ack", { n: S.ack.events }); return;
    }
    if (S.ack && t > S.ack.until) S.ack = null;
    // a passed wheel/touch gesture or a key we let through: native scroll on purpose
    if (t - G.at < CFG.RESIZE_GRACE && S.phase !== "released" && S.phase !== "free" && y <= G.storyEnd + 1) {
      C.resizeSnaps++; log("scroll-resize-snap"); syncScroll(yOf(S.dest), "resize-grace"); return;
    }
    C.foreign++;
    foreign(y, t);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("scrollend", () => {
    C.scrollend++; log("scrollend", { native: true });
    if (HAS_SCROLLEND && S.free) armSettle("scrollend");
  });

  // ---------- FREE / RELEASED (rules S2–S6) ----------
  function foreign(y, t) {
    if (y > G.storyEnd + 1) {                                 // below the story: native page
      if (S.free) { clearSettle(); S.free = null; }
      if (S.phase !== "released") setReleased("foreign-below");
      return;
    }
    if (y < G.storyTop - 1) { if (S.free) { clearSettle(); S.free = null; } return; }  // above the story
    if (!S.free) {
      S.free = { since: t, from: t < S.reentryUntil ? "released" : S.phase, fromBeat: S.rendered, lastY: y, lastT: t,
        timer: 0, backstop: 0, sawHold: S.held };
      if (S.phase === "released") { S.rendered = N - 1; S.dest = N - 1; }
      S.phase = "free";
      log("free-enter", { from: S.free.from });
    }
    S.free.lastY = y; S.free.lastT = t;
    paintPreview(nearestBeat(y));
    armSettle("scroll");
  }
  function setReleased(why) {
    S.phase = "released"; S.rendered = N - 1; S.dest = N - 1; S.busy = false; clearTimeout(S.timer); S.run = null;
    log("released", { why }); paint();
  }
  function clearSettle() { if (!S.free) return; clearTimeout(S.free.timer); clearTimeout(S.free.backstop); }
  function armSettle(trigger) {
    if (!S.free) return;
    clearTimeout(S.free.timer);
    if (trigger === "scrollend") { S.free.timer = setTimeout(() => settle("scrollend"), CFG.SCROLLEND_GRACE); return; }
    if (!HAS_SCROLLEND) S.free.timer = setTimeout(() => settle("idle"), CFG.SETTLE_IDLE);
    clearTimeout(S.free.backstop);
    S.free.backstop = setTimeout(() => settle("backstop"), CFG.SETTLE_BACKSTOP);
  }
  function settle(trigger) {
    if (!S.free) return;
    if (S.held) { S.free.afterHold = true; log("settle-wait-hold", { trigger }); return; }
    const quiet = now() - S.free.lastT;
    const need = trigger === "scrollend" ? CFG.SCROLLEND_GRACE : CFG.SETTLE_IDLE;
    if (quiet < need - 1) { log("settle-defer", { trigger, quiet: +quiet.toFixed(1) }); armSettle("scroll"); return; }
    const y = window.scrollY;
    clearSettle();
    const from = S.free.from, sawHold = S.free.sawHold;
    S.free = null;
    C.settles++;
    if (y > G.storyEnd + 1) { setReleased("settle-below"); return; }
    let b = nearestBeat(y);
    if (from === "released" && !sawHold) { b = N - 1; S.reentryUntil = now() + CFG.REENTRY_STICKY_MS; }   // re-entry from below
    log("settle", { trigger, to: b, quiet: +quiet.toFixed(1) });
    S.phase = S.busy ? S.run.kind : "rest";
    goTo(b, "settle");
  }

  // ---------- scrollbar hold (rule S5) ----------
  document.addEventListener("mousedown", (e) => {
    const onBar = e.clientX >= doc.clientWidth || e.clientY >= doc.clientHeight;
    log("mousedown", { x: e.clientX, cw: doc.clientWidth, onBar, trusted: e.isTrusted });
    if (!onBar) return;
    C.barDown++; S.held = true; S.heldAt = now(); if (S.free) S.free.sawHold = true;
    clearTimeout(S.holdTimer); S.holdTimer = setTimeout(() => { C.holdTimeouts++; endHold("timeout"); }, CFG.HOLD_MAX);
  }, true);
  function endHold(why) {
    if (!S.held) return;
    S.held = false; clearTimeout(S.holdTimer); log("hold-end", { why });
    if (why === "mouseup") C.barUp++;
    if (S.free) { S.free.lastT = now() - CFG.SETTLE_IDLE; settle("hold-end"); }
  }
  window.addEventListener("mouseup", () => endHold("mouseup"), true);
  window.addEventListener("pointerup", () => endHold("mouseup"), true);
  window.addEventListener("mousemove", (e) => { if (S.held && e.buttons === 0) endHold("move-no-buttons"); }, true);
  window.addEventListener("blur", () => endHold("blur"));

  // ---------- the plan (ICX-lite: signed dest, dip ≥ 2, back = dip, rush) ----------
  function request(delta, src) {
    C.steps++;
    if (S.phase === "free") { const b0 = nearestBeat(); clearSettle(); C.settleCancel++; log("settle-cancel", { src, b0 });
      S.free = null; S.phase = S.busy ? S.run.kind : "rest"; S.dest = b0; }
    const before = S.dest;
    S.dest = clamp(S.dest + delta, 0, N - 1);
    log("step", { src, delta, from: before });
    if (S.dest === before) return;
    syncScroll(yOf(S.dest), "dest:" + src);
    if (!S.busy) next(); else rush();
    paint();
  }
  function goTo(b, src) {
    if (S.phase === "free") { clearSettle(); S.free = null; S.phase = S.busy ? S.run.kind : "rest"; }
    S.dest = clamp(b, 0, N - 1);
    log("goto", { src, to: S.dest });
    syncScroll(yOf(S.dest), "goto:" + src);
    if (!S.busy) next(); else rush();
    paint();
  }
  function next() {
    clearTimeout(S.timer);
    const d = S.dest - S.rendered;
    if (d === 0) return land();
    if (d === 1) return play();
    const wait = S.lastDipAt + CFG.DIP_COOLDOWN - now();
    if (wait > 0) { S.busy = true; S.phase = "wait"; S.run = { kind: "wait" }; S.timer = setTimeout(next, wait); return; }
    dip();
  }
  function play() {
    S.busy = true; S.phase = "play";
    S.run = { kind: "play", from: S.rendered, to: S.rendered + 1, t0: now(), dur: TR + CT };
    S.timer = setTimeout(() => { S.rendered = S.run.to; next(); }, S.run.dur);
    paint();
  }
  function rush() {
    if (!S.run || S.run.kind !== "play") return;
    const left = S.run.t0 + S.run.dur - now();
    if (left > CFG.RUSH_LEFT) { clearTimeout(S.timer); S.run.dur = now() - S.run.t0 + CFG.RUSH_LEFT;
      S.timer = setTimeout(() => { S.rendered = S.run.to; next(); }, CFG.RUSH_LEFT); }
  }
  function dip() {
    C.dips++; S.busy = true; S.phase = "dip"; S.lastDipAt = now();
    const fwd = S.dest > S.rendered;
    S.run = { kind: "dip", t0: now() };
    stage.classList.add("dark");
    S.timer = setTimeout(() => {                         // the dark frame: commit dest here
      S.rendered = S.dest; paint(); stage.classList.remove("dark");
      S.timer = setTimeout(() => {
        if (fwd && S.dest === S.rendered) { S.phase = "play"; S.run = { kind: "play", from: S.rendered, to: S.rendered, t0: now(), dur: CT };
          S.timer = setTimeout(next, CT); paint(); }
        else next();
      }, CFG.DIP_IN);
    }, CFG.DIP_OUT);
    paint();
  }
  function land() {
    S.busy = false; S.run = null; S.phase = "rest"; C.lands++;
    if (Math.abs(window.scrollY - yOf(S.rendered)) > CFG.ACK_TOL) syncScroll(yOf(S.rendered), "land-realign");
    log("land", { aligned: +(window.scrollY - yOf(S.rendered)).toFixed(2) });
    paint();
  }

  // ---------- wheel (R1 §3.4 detector; sticky per-gesture decision) ----------
  function canExit(dir) {
    if (S.phase !== "rest") return false;
    if (dir > 0) return S.rendered === N - 1 && S.dest === N - 1;
    return S.rendered === 0 && S.dest === 0 && window.scrollY <= G.storyTop + 1;
  }
  function decide(dir) {
    const y = window.scrollY;
    if (S.phase === "released" || y > G.storyEnd + 1) return dir < 0 ? "reentry" : "pass";
    if (y < G.storyTop - 1) return "pass";
    if (canExit(dir)) return "pass";
    return "intercept";
  }
  function onWheel(e) {
    C.wheel++;
    const mode = e.deltaMode;                                       // read deltaMode first (Firefox)
    const k = mode === 1 ? CFG.LINE_PX : mode === 2 ? innerHeight : 1;
    const dy = e.deltaY * k, dx = e.deltaX * k, t = e.timeStamp;
    if (e.ctrlKey) { log("wheel-bypass", { why: "ctrl", dy }); C.wheelPassed++; return; }
    if (Math.abs(dx) > Math.abs(dy)) { C.wheelPassed++; return; }
    const notchHint = mode === 1 || (Math.abs(e.wheelDeltaY || 0) >= 120 && e.wheelDeltaY % 120 === 0 && Math.abs(dy) >= 50)
      || (Math.abs(dy) >= 50 && t - S.lastWheelT > 30);
    let g = S.gest;
    if (!g || t - g.lastT > (g.notch ? CFG.QUIET_NOTCH : CFG.QUIET_SMOOTH)) {
      g = S.gest = { id: (g ? g.id : 0) + 1, notch: notchHint, decision: decide(Math.sign(dy)), lastT: t, t0: t, acc: 0,
        dir: 0, samples: [], peakV: 0, peakSince: 0, lastStepT: -1e9 };
      log("gesture", { id: g.id, notch: g.notch, decision: g.decision, dy });
    }
    g.lastT = t; S.lastWheelT = t;
    if (g.decision === "pass") { C.wheelPassed++; return; }
    if (g.decision === "reentry") {
      if (dy >= 0 || window.scrollY + dy >= G.storyEnd) { C.wheelPassed++; return; }   // still below: native
      e.preventDefault(); C.wheelPrevented++;
      g.decision = "swallow";
      if (S.free) { clearSettle(); S.free = null; }
      S.phase = "rest"; S.rendered = N - 1; S.dest = N - 1;
      syncScroll(G.storyEnd, "reentry-clamp"); log("reentry", {}); paint(); return;
    }
    e.preventDefault(); C.wheelPrevented++;
    if (g.decision === "swallow") return;
    const s = detect(g, t, dy);
    if (s) request(s, g.notch ? "wheel-notch" : "wheel");
  }
  function detect(g, t, dy) {
    const a = Math.abs(dy), s = Math.sign(dy);
    if (a < CFG.MIN_DELTA) return 0;
    g.samples.push({ t, a, s });
    while (g.samples.length && g.samples[0].t < t - CFG.W_NOW - CFG.W_PREV - 50) g.samples.shift();
    if (!g.dir) {
      if (g.notch) { g.dir = s; g.lastStepT = t; return s; }
      if (t - g.t0 > CFG.START_WIN) { g.t0 = t; g.acc = 0; }
      g.acc += a;
      if (g.acc >= CFG.START_PX) { g.dir = s; g.lastStepT = t; return s; }
      return 0;
    }
    if (s !== g.dir) {
      const back = g.samples.filter((p) => p.s === s && p.t > t - CFG.REVERSE_WIN).reduce((q, p) => q + p.a, 0);
      if (back >= CFG.REVERSE_PX) { g.dir = s; g.lastStepT = t; g.peakV = 0; g.peakSince = 0; return s; }
      return 0;
    }
    const sum = (lo, hi) => g.samples.filter((p) => p.s === s && p.t > lo && p.t <= hi).reduce((q, p) => q + p.a, 0);
    const vNow = sum(t - CFG.W_NOW, t) / CFG.W_NOW * 1000;
    const vPrev = sum(t - CFG.W_NOW - CFG.W_PREV, t - CFG.W_NOW) / CFG.W_PREV * 1000;
    g.peakV = Math.max(g.peakV, vNow); g.peakSince = Math.max(g.peakSince, vNow);
    const win = g.samples.filter((p) => p.t > t - CFG.W_NOW - CFG.W_PREV);
    let maxGap = 0; for (let i = 1; i < win.length; i++) maxGap = Math.max(maxGap, win[i].t - win[i - 1].t);
    const continuous = win.length > 2 && maxGap <= CFG.CONT_GAP;
    if (!g.notch && continuous && vPrev < CFG.TAIL_GATE * g.peakV && vNow > CFG.RISE_RATIO * vPrev
      && vNow > CFG.V_RISE_MIN && t - g.lastStepT >= CFG.MIN_STEP_MS) { g.lastStepT = t; g.peakV = vNow; g.peakSince = vNow; return s; }
    // (C0a D1) R1 had notch gestures "sustained" by any event; a smooth flick that opens with a >= 50 px delta is classed
    // notch for its whole gesture (ICX-CLASS), so its decaying tail stepped again at REPEAT_MS. Both kinds now need a
    // rate that is not decaying.
    const sustained = Q.has("r1notch") && g.notch ? true : vNow >= CFG.SUSTAIN_K * g.peakSince;
    if (t - g.lastStepT >= CFG.REPEAT_MS && sustained) { g.lastStepT = t; g.peakSince = vNow; return s; }
    return 0;
  }
  window.addEventListener("wheel", onWheel, { passive: false });

  // ---------- keyboard ----------
  const FIELD = /^(INPUT|TEXTAREA|SELECT)$/;
  window.addEventListener("keydown", (e) => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const tg = e.target;
    if (tg && (FIELD.test(tg.tagName) || tg.isContentEditable)) return;
    const k = e.key; let d = 0, jump = null;
    if (k === "ArrowDown" || k === "PageDown" || (k === " " && !e.shiftKey)) d = 1;
    else if (k === "ArrowUp" || k === "PageUp" || (k === " " && e.shiftKey)) d = -1;
    else if (k === "Home") jump = 0; else if (k === "End") jump = N - 1; else return;
    if (k === " " && tg && tg.closest && tg.closest("a,button,summary,[role=button]")) return;
    const y = window.scrollY;
    if (jump === null && (S.phase === "released" || y > G.storyEnd + 1)) { log("key-pass", { k, why: "below" }); return; }
    if (jump === N - 1 && canExit(1)) { log("key-pass", { k, why: "end-at-last" }); return; }
    if (d && canExit(d)) { log("key-pass", { k, why: "release" }); return; }
    e.preventDefault();
    if (e.repeat && now() - S.lastKeyStep < CFG.KEY_REPEAT_MS) return;
    S.lastKeyStep = now();
    if (jump !== null) {
      if (S.phase === "released") { S.phase = "rest"; }
      goTo(jump, "key");
    } else request(d, "key");
  });

  // ---------- touch ----------
  const swipePx = () => Math.max(CFG.SWIPE_MIN_PX, CFG.SWIPE_FRAC * G.P);
  story.addEventListener("touchstart", (e) => {
    if (e.touches.length > 1) { if (S.touch) S.touch.dead = true; log("touch-multi"); return; }
    const p = e.touches[0];
    S.touch = { x0: p.clientX, y0: p.clientY, t0: e.timeStamp, decided: null, stepped: false, dy: 0, dead: false };
  }, { passive: false });
  story.addEventListener("touchmove", (e) => {
    const T = S.touch; if (!T || T.dead) return;
    if (e.touches.length > 1) { T.dead = true; log("touch-multi"); return; }
    const p = e.touches[0], dx = p.clientX - T.x0, dy = T.y0 - p.clientY;   // dy > 0 = forward
    T.dy = dy;
    if (!T.decided) {
      if (Math.hypot(dx, dy) < CFG.TOUCH_SLOP) return;
      const vv = window.visualViewport;
      if (vv && vv.scale > 1.01) T.decided = "pass-zoomed";
      else if (Math.abs(dy) < CFG.DIR_RATIO * Math.abs(dx)) T.decided = "pass-horizontal";
      else if (S.phase === "released" || window.scrollY > G.storyEnd + 1) T.decided = "pass-below";
      else if (canExit(Math.sign(dy))) T.decided = "pass-exit";
      else T.decided = "intercept";
      log("touch-decide", { decided: T.decided, trusted: e.isTrusted });
    }
    if (T.decided !== "intercept") return;
    e.preventDefault();
    if (!T.stepped && Math.abs(dy) >= swipePx()) { T.stepped = true; C.touchSteps++; request(Math.sign(dy), "touch"); }
  }, { passive: false });
  const touchEnd = (e) => {
    const T = S.touch; S.lastTouchEnd = now(); if (!T) return;
    if (T.decided === "intercept" && !T.stepped && !T.dead && Math.abs(T.dy) >= 14 && Math.abs(T.dy) / Math.max(1, e.timeStamp - T.t0) >= CFG.SWIPE_VEL) {
      T.stepped = true; C.touchSteps++; request(Math.sign(T.dy), "touch-flick");
    }
    log("touch-end", { decided: T.decided, stepped: T.stepped }); S.touch = null;
  };
  story.addEventListener("touchend", touchEnd, { passive: true });
  story.addEventListener("touchcancel", touchEnd, { passive: true });

  // ---------- resize / rotation (rule S7) ----------
  function onGeometry(why) {
    const old = G, y = S.lastY != null ? S.lastY : window.scrollY;
    const wasBelow = y > old.storyEnd + 1, past = y - old.storyEnd;
    measure();
    const same = G.P === old.P && G.storyTop === old.storyTop;
    log("geometry", { why, P: G.P, oldP: old.P, svh: G.svh, iw: innerWidth, ih: innerHeight, same,
      rawY: +window.scrollY.toFixed(2), usedY: +y.toFixed(2) });
    if (same) { G.at = old.at; return; }                       // e.g. an iOS bar show/hide: 100svh did not move
    if (S.phase === "released" || wasBelow) { syncScroll(G.storyEnd + past, "resize-keep-below"); return; }
    if (S.phase === "free") { clearSettle(); S.free = null; S.phase = S.busy ? S.run.kind : "rest"; }
    syncScroll(yOf(S.dest), "resize");
    paint();
  }
  window.addEventListener("resize", () => onGeometry("resize"));
  if (window.visualViewport) visualViewport.addEventListener("resize", () => log("vv-resize", { scale: +visualViewport.scale.toFixed(3), h: +visualViewport.height.toFixed(1) }));

  // ---------- paint ----------
  for (let i = 0; i < N; i++) { const d = document.createElement("i"); d.title = NAMES[i] || "b" + i; rail.appendChild(d); }
  let pvBeat = -1;
  function paintPreview(b) { pvBeat = b; paint(); }
  function paint() {
    const r = S.rendered;
    stage.style.setProperty("--b", r);
    nameEl.textContent = NAMES[r] || "b" + r;
    phEl.textContent = S.phase + " → " + (NAMES[S.dest] || S.dest);
    [...rail.children].forEach((el, i) => { el.className = (i === r ? "cur " : "") + (i === S.dest ? "dest " : "")
      + (S.phase === "free" && i === pvBeat ? "pv" : ""); });
    stEl.textContent = `${S.phase} r${S.rendered} d${S.dest} y${Math.round(window.scrollY)} P${G.P} se:${HAS_SCROLLEND ? 1 : 0}`;
  }
  function tick() {
    if (S.run && S.run.kind === "play") bar.style.width = clamp((now() - S.run.t0) / S.run.dur, 0, 1) * 100 + "%";
    else bar.style.width = "0";
    requestAnimationFrame(tick);
  }

  // ---------- boot ----------
  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  measure();
  G.at = -1e9;                                                      // boot is not a geometry change (no resize grace)
  const hb = /^#b(\d)$/.exec(location.hash);
  if (hb) { S.rendered = S.dest = clamp(+hb[1], 0, N - 1); }
  window.scrollTo(0, yOf(S.rendered));
  S.lastY = window.scrollY;
  paint(); requestAnimationFrame(tick);
  log("boot", { P: G.P, svh: G.svh, nativeScrollend: NATIVE_SCROLLEND, hasScrollend: HAS_SCROLLEND });

  window.__cp = {
    N, CFG, L, C, TR, CT, nativeScrollend: NATIVE_SCROLLEND, hasScrollend: HAS_SCROLLEND,
    geom: () => Object.assign({}, G, { y: window.scrollY, max: maxScroll(), cw: doc.clientWidth, ch: doc.clientHeight,
      iw: innerWidth, ih: innerHeight, dpr: devicePixelRatio, vvScale: window.visualViewport ? visualViewport.scale : 1,
      sh: doc.scrollHeight, ys: Array.from({ length: N }, (_, i) => yOf(i)) }),
    state: () => ({ phase: S.phase, rendered: S.rendered, dest: S.dest, busy: S.busy, held: S.held, free: !!S.free,
      ack: S.ack ? { y: S.ack.y, events: S.ack.events } : null, gest: S.gest ? S.gest.decision : null, y: window.scrollY,
      aligned: +(window.scrollY - yOf(S.rendered)).toFixed(2) }),
    counters: () => Object.assign({}, C),
    mark: (ev, o) => log("mark:" + ev, o),
    goTo: (b) => goTo(b, "api"),
    yOf, nearestBeat,
    // the site's legacy-zoom probe (engine.js legacyZoom): true = getBoundingClientRect ignores CSS zoom (shipping Safari)
    legacyZoom: () => { const h = document.createElement("div"), c = document.createElement("div"), z = document.createElement("div"), i = document.createElement("div");
      h.style.cssText = "position:absolute;left:0;top:0;visibility:hidden"; c.style.cssText = "width:50px;height:10px"; z.style.cssText = "zoom:2";
      i.style.cssText = "width:50px;height:10px"; z.appendChild(i); h.append(c, z); document.body.appendChild(h);
      const r = i.getBoundingClientRect().width / c.getBoundingClientRect().width; h.remove(); return { ratio: r, legacy: r < 1.5 }; },
  };
})();
