/* Checkpoint input (C1) — turns wheel, trackpad, key and touch input into discrete steps and jumps.
 *
 * Binding: docs/interaction-contract.md v1 (ICX-CLASS, ICX-BYPASS, ICX-KEY, ICX-SETTLE-8/9/D1) and
 * docs/checkpoint-config.md v1 (every constant below; CONFIG_VERSION is read from here and nowhere else).
 * The detector is R1 §3.4 with C0a's D1 fix. It knows nothing about checkpoints: it emits one onStep(±1) per
 * gesture (plus rise / sustained repeats, R1 §3.4) and onJump("first"|"last") for Home/End; the consumer (C3) keeps
 * the signed dest (ICX-SIGNED), the edges (release, ICX-BACK.5) and the settle rules.
 *
 * Classic script (no modules): sets window.FECheckpoint, like the FX global. Works in file:// and srcdoc frames.
 *
 *   var seq = FECheckpoint.createSequence({
 *     config,                     // optional overrides of DEFAULTS (unknown keys throw)
 *     onStep(dir, src, info),     // dir ±1; src "wheel"|"key"|"touch";
 *                                 // info {t, trigger: start|rise|repeat|reverse|key|key-repeat|swipe|flick, gesture?, cls?}
 *     onJump(target, src, info),  // target "first"|"last" (Home/End); src "key"; info {t, key, repeat}
 *     isBypassed(ev, info),       // optional; truthy = let this gesture / key / touch pass natively.
 *                                 // info {source, dir, phase: "start"|"continue"|"probe", gesture?, jump?}
 *                                 // ("probe": a touch still inside TOUCH_SLOP, asked in its tentative direction)
 *     onSample(rec),              // optional debug/tuning tap: every wheel event inside a gesture
 *     pinHeight()                 // optional; px of the pinned stage for SWIPE_PX (default innerHeight)
 *   });
 *   seq.attach(el)   // wheel + touch listeners on el (pass window for the story), keydown on el's window
 *   seq.setEnabled(bool)          // false: never preventDefault, never step (calm / classic, dialogs, …)
 *   seq.detach()
 *
 * Decisions are per gesture and sticky (R1 §3.4): a wheel gesture is classified (notch | smooth) and decided
 * (intercept | pass) on its first event and keeps both until it ends at its own quiet threshold (ICX-CLASS). An
 * intercepted gesture is never released mid-way (its tail must not leak into native scroll), except single events a
 * nested scroller, field or dialog under the pointer can still take in their direction. A gesture the consumer
 * passed is asked again on every event (phase "continue"); once isBypassed returns falsy, that event and the rest of
 * the gesture are prevented and swallowed: no steps (ICX-SETTLE-8's crossing from below).
 * Never intercepted (ICX-BYPASS): Ctrl/⌘+wheel and pinch, horizontal wheel (|dx| > |dy|), and wheel / key / touch
 * aimed inside an open dialog, a form field, [contenteditable], or a nested scroller that can still scroll that way.
 * Time is always ev.timeStamp (deterministic replay in tests/checkpoint/run_detector.mjs).
 */
(function (root) {
  "use strict";

  var CONFIG_VERSION = 1;

  // docs/checkpoint-config.md v1. tests/checkpoint/test_detector.py checks these against the doc.
  var DEFAULTS = Object.freeze({
    LINE_PX: 33.3, // deltaMode 1 -> px
    MIN_DELTA: 0.5, // px; smaller keeps a gesture alive but never steps
    START_PX: 8, // px summed within START_WIN to start a smooth gesture
    START_WIN: 120, // ms
    QUIET_SMOOTH: 140, // ms of quiet that ends a smooth gesture
    QUIET_NOTCH: 220, // ms of quiet that ends a notch gesture
    W_NOW: 50, // ms window for vNow
    W_PREV: 120, // ms window for vPrev (before W_NOW)
    CONT_GAP: 45, // ms: max gap for a "continuous" stream (rise test)
    TAIL_GATE: 0.6, // rise only once vPrev < TAIL_GATE * peak
    RISE_RATIO: 1.8, // rise: vNow > RISE_RATIO * vPrev
    V_RISE_MIN: 1000, // px/s: rise floor
    MIN_STEP_MS: 250, // ms between a step and a rise
    REPEAT_MS: 850, // ms between sustained repeats
    SUSTAIN_K: 0.7, // repeat only while vNow >= SUSTAIN_K * peakSinceStep (smooth AND notch: ICX-SETTLE-D1)
    JOIN_MAX: 600, // ms: the longest gap inside a still-moving inertia tail that keeps the gesture (ICX-CLASS.4)
    TAIL_LIVE: 20, // px/s: a tail at least this fast emits every frame, so a gap in it is not the hand (ICX-CLASS.4)
    SPREAD_MIN: 24, // ms: a smooth event later than this after the last one counts as spread over its gap (ICX-CLASS.5)
    BUNCH_MS: 4, // ms: events closer than this after a spread one are the same held-back delivery (ICX-CLASS.5)
    REVERSE_PX: 12, // px summed against the gesture's direction ...
    REVERSE_WIN: 80, // ... within this many ms -> a reverse step
    NOTCH_HINT_PX: 50, // notch hint: first delta >= this ...
    NOTCH_HINT_GAP: 30, // ... with no wheel event in the previous 30 ms
    KEY_REPEAT_MS: 420, // a held key (e.repeat) steps at most once per this
    TOUCH_SLOP: 8, // px before a touch is decided
    DIR_RATIO: 1.2, // vertical only if |dy| >= DIR_RATIO * |dx|
    SWIPE_MIN_PX: 36, // SWIPE_PX = max(SWIPE_MIN_PX, SWIPE_FRAC * pin height)
    SWIPE_FRAC: 0.05,
    SWIPE_VEL: 0.4, // px/ms at touchend ...
    SWIPE_END_MIN_PX: 14, // ... with |dy| >= this
    ZOOM_SCALE: 1.01 // visualViewport.scale above this: touches pan (ICX-SETTLE-9)
  });

  var FIELD_TAGS = { INPUT: 1, TEXTAREA: 1, SELECT: 1 };
  var CONTROL_TAGS = { A: 1, BUTTON: 1, SUMMARY: 1 };
  var SCROLLABLE = { auto: 1, scroll: 1, overlay: 1 };

  function sign(v) { return v > 0 ? 1 : v < 0 ? -1 : 0; }

  function mergeConfig(over) {
    var c = {}, k;
    for (k in DEFAULTS) c[k] = DEFAULTS[k];
    if (over) {
      for (k in over) {
        if (!Object.prototype.hasOwnProperty.call(DEFAULTS, k)) throw new Error("FECheckpoint: unknown config key " + k);
        c[k] = over[k];
      }
    }
    return Object.freeze(c);
  }

  function pathOf(ev) {
    var p = typeof ev.composedPath === "function" ? ev.composedPath() : null;
    if (p && p.length) return p;
    p = [];
    for (var n = ev.target; n; n = n.parentNode) p.push(n);
    return p;
  }

  function isOpenDialog(n) {
    return n.tagName === "DIALOG" && (n.open === true || (n.hasAttribute && n.hasAttribute("open")));
  }

  // ICX-BYPASS.3 / ICX-KEY.7: inside an open dialog, a form field or [contenteditable]
  function inFieldOrDialog(path) {
    for (var i = 0; i < path.length; i++) {
      var n = path[i];
      if (!n || n.nodeType !== 1) continue;
      if (FIELD_TAGS[n.tagName] || n.isContentEditable === true || isOpenDialog(n)) return true;
    }
    return false;
  }

  function onControl(path) {
    for (var i = 0; i < path.length; i++) {
      var n = path[i];
      if (!n || n.nodeType !== 1) continue;
      if (CONTROL_TAGS[n.tagName] || (n.getAttribute && n.getAttribute("role") === "button")) return true;
    }
    return false;
  }

  function createSequence(opts) {
    opts = opts || {};
    var C = mergeConfig(opts.config);
    var onStep = opts.onStep || function () {};
    var onJump = opts.onJump || function () {};
    var isBypassed = opts.isBypassed || null;
    var onSample = opts.onSample || null;

    var target = null, win = null, doc = null;
    var enabled = true;
    var g = null; // the current wheel gesture
    var gid = 0;
    var lastWheelT = -Infinity;
    var lastKeyStepT = -Infinity;
    var T = null; // the current touch

    // ICX-BYPASS.4: a nested scroll container (between the target and the page) that can still scroll in dir
    function nestedCanScroll(path, dir) {
      if (!dir) return false;
      var stopA = doc && doc.documentElement, stopB = doc && doc.body;
      for (var i = 0; i < path.length; i++) {
        var n = path[i];
        if (!n || n === target || n === stopA || n === stopB || n === doc || n === win) break;
        if (n.nodeType !== 1 || !(n.scrollHeight > n.clientHeight + 1)) continue;
        var view = (n.ownerDocument && n.ownerDocument.defaultView) || win;
        var oy = view && view.getComputedStyle ? view.getComputedStyle(n).overflowY : "visible";
        if (!SCROLLABLE[oy]) continue;
        if (dir > 0 ? n.scrollTop + n.clientHeight < n.scrollHeight - 1 : n.scrollTop > 0.5) return true;
      }
      return false;
    }

    function targetBypassed(ev, dir) {
      var path = pathOf(ev);
      return inFieldOrDialog(path) || nestedCanScroll(path, dir);
    }

    function consumerPasses(ev, info) {
      return !!(isBypassed && isBypassed(ev, info));
    }

    // ---------- wheel ----------
    function newGesture(ev, t, dy, prevWheelT) {
      var a = Math.abs(dy);
      var wdy = ev.wheelDeltaY || 0;
      var notch = ev.deltaMode === 1 ||
        (Math.abs(wdy) >= 120 && wdy % 120 === 0 && a >= C.NOTCH_HINT_PX) ||
        (a >= C.NOTCH_HINT_PX && t - prevWheelT > C.NOTCH_HINT_GAP);
      var dir = sign(dy);
      var ng = {
        id: ++gid, notch: notch, cls: notch ? "notch" : "smooth", decision: "intercept", lastT: t, winT0: t, acc: 0,
        dir: 0, dirT: -Infinity, samples: [], peakV: 0, peakSince: 0, lastStepT: -Infinity, vLast: 0, paced: 0
      };
      if (targetBypassed(ev, dir)) ng.decision = "pass";
      else if (consumerPasses(ev, { source: "wheel", dir: dir, phase: "start", gesture: ng.id })) ng.decision = "pass-consumer";
      return ng;
    }

    function step(s, src, info) { onStep(s, src, info); }

    // ICX-CLASS.4 (FLICKER): a gap inside a flick's still-moving inertia tail is the page or the browser not hearing
    // input (a busy main thread; Chrome holds and coalesces wheel events), never the hand going quiet: an inertia tail
    // has an event every frame while it moves. The gesture carries on (no new "start" step). Only a smooth flick
    // (peak >= V_RISE_MIN, frame-paced: >= 3 event gaps under SPREAD_MIN, which mouse notches never are) whose tail
    // still ran at >= TAIL_LIVE when the gap began, same direction, a gap <= JOIN_MAX, not a line-mode (deltaMode 1)
    // event. A new flick in the joined gesture still steps by the rise test
    // (ICX-CLASS.5 keeps the held-back burst itself from reading as one).
    function joinsTail(ev, t, dy) {
      if (!g.dir || g.decision !== "intercept" || sign(dy) !== g.dir) return false;
      if (t - g.lastT > C.JOIN_MAX || g.peakV < C.V_RISE_MIN || g.vLast < C.TAIL_LIVE || g.paced < 3) return false;
      return ev.deltaMode !== 1;
    }

    // R1 §3.4 core + C0a D1. Returns 0 or the step's sign (and sets g.trigger).
    function detect(t, dy) {
      var a = Math.abs(dy), s = sign(dy), i;
      if (t - g.prevT < C.SPREAD_MIN) g.paced++;
      // (a sub-MIN_DELTA tail event still says how slow the tail has become: Sol FLICKER-1 #3)
      if (a < C.MIN_DELTA) { if (s === g.dir) g.vLast = Math.min(g.vLast, a * 1000 / Math.max(1, t - g.prevT)); return 0; }
      // ICX-CLASS.5 (FLICKER): a smooth event that comes more than SPREAD_MIN after the last one may carry the summed
      // deltas of frames the page did not hear (Chrome coalesces wheel events while the main thread is busy); its delta
      // counts as spread evenly over that gap, so a held-back burst is not read as a new flick's rise
      // (held-back events delivered in a bunch, under BUNCH_MS apart, are one such delivery: they join that spread)
      var lq = g.samples.length ? g.samples[g.samples.length - 1] : null, last = lq ? lq.t : t;
      if (lq && lq.d && lq.s === s && t - last < C.BUNCH_MS) { lq.a += a; lq.d += t - last; lq.t = t; }
      else g.samples.push({ t: t, a: a, s: s, d: !g.notch && t - last > C.SPREAD_MIN ? t - last : 0 });
      var keep = t - C.W_NOW - C.W_PREV - C.REVERSE_WIN;
      while (g.samples.length && g.samples[0].t < keep) g.samples.shift();

      // rates in direction s (px/s, rate-independent) and the stream's continuity, including this sample
      var now = 0, prev = 0, lo = t - C.W_NOW, lo2 = lo - C.W_PREV, maxGap = 0, n = 0, lastIn = null;
      for (i = 0; i < g.samples.length; i++) {
        var q = g.samples[i];
        if (q.t > lo2) {
          if (lastIn !== null) maxGap = Math.max(maxGap, q.t - lastIn);
          lastIn = q.t; n++;
        }
        if (q.s !== s) continue;
        if (q.d) {
          now += q.a * Math.max(0, Math.min(q.t, t) - Math.max(q.t - q.d, lo)) / q.d;
          prev += q.a * Math.max(0, Math.min(q.t, lo) - Math.max(q.t - q.d, lo2)) / q.d;
        } else if (q.t > lo && q.t <= t) now += q.a;
        else if (q.t > lo2 && q.t <= lo) prev += q.a;
      }
      var vNow = now / C.W_NOW * 1000, vPrev = prev / C.W_PREV * 1000;

      // Every step that sets the direction seeds the peaks with the rate that caused it (Sol C1-sol-1 #3: an
      // opener left out of peakSince let a decaying trickle count as "sustained" and repeat, against D1).
      if (!g.dir) { // starting
        if (!g.notch) {
          if (t - g.winT0 > C.START_WIN) { g.winT0 = t; g.acc = 0; }
          g.acc += a;
          if (g.acc < C.START_PX) return 0;
        }
        g.dir = s; g.dirT = t; g.lastStepT = t; g.peakV = vNow; g.peakSince = vNow; g.trigger = "start";
        return s;
      }
      if (s !== g.dir) { // momentum never reverses: only REVERSE_PX against the direction within REVERSE_WIN does,
        // counting only samples since the direction was last set (Sol C1-sol-1 #1: older ones re-flipped on 1 px)
        var back = 0;
        for (i = 0; i < g.samples.length; i++) {
          var p = g.samples[i];
          if (p.s === s && p.t > t - C.REVERSE_WIN && p.t > g.dirT) back += p.a;
        }
        if (back >= C.REVERSE_PX) {
          g.dir = s; g.dirT = t; g.lastStepT = t; g.peakV = vNow; g.peakSince = vNow; g.trigger = "reverse";
          return s;
        }
        return 0;
      }
      g.vLast = vNow;
      g.peakV = Math.max(g.peakV, vNow);
      g.peakSince = Math.max(g.peakSince, vNow);
      var continuous = n > 2 && maxGap <= C.CONT_GAP;
      if (!g.notch && continuous && vPrev < C.TAIL_GATE * g.peakV && vNow > C.RISE_RATIO * vPrev &&
          vNow > C.V_RISE_MIN && t - g.lastStepT >= C.MIN_STEP_MS) {
        g.lastStepT = t; g.peakV = vNow; g.peakSince = vNow; g.trigger = "rise";
        return s;
      }
      // D1: notch gestures too need a rate that is not decaying (a >= 50 px smooth flick is classed notch)
      if (t - g.lastStepT >= C.REPEAT_MS && vNow >= C.SUSTAIN_K * g.peakSince) {
        g.lastStepT = t; g.peakSince = vNow; g.trigger = "repeat";
        return s;
      }
      return 0;
    }

    function onWheel(ev) {
      if (!enabled) return;
      var mode = ev.deltaMode; // read deltaMode before the deltas (Firefox)
      var k = mode === 1 ? C.LINE_PX : mode === 2 ? (win && win.innerHeight) || 800 : 1;
      var dy = ev.deltaY * k, dx = ev.deltaX * k, t = ev.timeStamp;
      var prevWheelT = lastWheelT;
      lastWheelT = t;
      if (ev.ctrlKey || ev.metaKey) return; // ICX-BYPASS.1 (pinch arrives as ctrl+wheel)
      if (Math.abs(dx) > Math.abs(dy)) return; // ICX-BYPASS.4 (horizontal, macOS back/forward)
      var live = g && t - g.lastT <= (g.notch ? C.QUIET_NOTCH : C.QUIET_SMOOTH);
      if (!live && g && joinsTail(ev, t, dy)) live = true;
      if (!live) {
        g = null;
        if (Math.abs(dy) < C.MIN_DELTA) return; // nothing to start
        g = newGesture(ev, t, dy, prevWheelT);
      }
      g.prevT = g.lastT; g.lastT = t;
      if (g.decision === "pass-consumer" &&
          !consumerPasses(ev, { source: "wheel", dir: sign(dy), phase: "continue", gesture: g.id })) {
        g.decision = "swallow"; // taken over mid-gesture (ICX-SETTLE-8): prevent the rest, step nothing
      }
      if (onSample) onSample({ source: "wheel", event: ev, t: t, dy: dy, gesture: g.id, cls: g.cls, decision: g.decision });
      if (g.decision === "pass" || g.decision === "pass-consumer") return;
      // An intercepted gesture is re-checked per event: an event a nested scroller (or field / dialog) under the
      // pointer can still take in its own direction is left to it, unprevented and unseen by the detector
      // (ICX-BYPASS.3/.4; Sol C1-sol-1 #2: reversing up at a scroller's bottom). A gesture passed at its start
      // stays passed (scroll latching: a scroller that reaches its end mid-gesture does not hand over the rest).
      if (g.decision === "intercept" && targetBypassed(ev, sign(dy))) return;
      if (ev.cancelable !== false) ev.preventDefault();
      if (g.decision === "swallow") return;
      var s = detect(t, dy);
      if (s) step(s, "wheel", { t: t, trigger: g.trigger, gesture: g.id, cls: g.cls });
    }

    // ---------- keys (ICX-KEY) ----------
    function onKey(ev) {
      if (!enabled) return;
      if (ev.defaultPrevented || ev.altKey || ev.ctrlKey || ev.metaKey) return;
      var k = ev.key, space = k === " " || k === "Spacebar", d = 0, jump = null;
      if (k === "ArrowDown" || k === "PageDown" || (space && !ev.shiftKey)) d = 1;
      else if (k === "ArrowUp" || k === "PageUp" || (space && ev.shiftKey)) d = -1;
      else if (k === "Home") jump = "first";
      else if (k === "End") jump = "last";
      else return; // ArrowLeft / ArrowRight and everything else: never intercepted
      var path = pathOf(ev);
      if (inFieldOrDialog(path)) return;
      if (space && onControl(path)) return;
      if (doc && doc.querySelector && doc.querySelector("dialog[open]")) return;
      var dir = d || (jump === "first" ? -1 : 1);
      if (consumerPasses(ev, { source: "key", dir: dir, jump: jump, phase: "start" })) return;
      ev.preventDefault();
      var t = ev.timeStamp;
      if (ev.repeat && t - lastKeyStepT < C.KEY_REPEAT_MS) return; // ICX-KEY.4
      lastKeyStepT = t;
      if (jump) onJump(jump, "key", { t: t, key: k, repeat: !!ev.repeat });
      else step(d, "key", { t: t, trigger: ev.repeat ? "key-repeat" : "key", key: k });
    }

    // ---------- touch (R1 §3.4; C6 finishes it on devices) ----------
    function swipePx() {
      var h = opts.pinHeight ? opts.pinHeight() : (win && win.innerHeight) || 0;
      return Math.max(C.SWIPE_MIN_PX, C.SWIPE_FRAC * h);
    }

    function onTouchStart(ev) {
      if (!enabled) return;
      if (ev.touches.length > 1) { // a second finger: pinch, never steps (ICX-BYPASS.2)
        if (T) T.dead = true;
        else T = { dead: true };
        return;
      }
      var p = ev.touches[0];
      T = { x0: p.clientX, y0: p.clientY, t0: ev.timeStamp, decided: null, stepped: false, dy: 0, dead: false, held: false };
    }

    // would a touch moving in dir pass natively? (dir 0: no direction yet -> only the direction-free reasons)
    function touchPasses(ev, dir, phase) {
      var vv = win && win.visualViewport;
      if (vv && vv.scale > C.ZOOM_SCALE) return true; // pinch-zoomed: pan (ICX-SETTLE-9)
      if (!dir) return inFieldOrDialog(pathOf(ev));
      return targetBypassed(ev, dir) || consumerPasses(ev, { source: "touch", dir: dir, phase: phase });
    }

    function onTouchMove(ev) {
      if (!enabled || !T || T.dead) return;
      if (ev.touches.length > 1) { T.dead = true; return; }
      var p = ev.touches[0], dx = p.clientX - T.x0, dy = T.y0 - p.clientY; // dy > 0 = forward (finger up)
      T.dy = dy;
      if (!T.decided) {
        if (Math.sqrt(dx * dx + dy * dy) < C.TOUCH_SLOP) {
          // C6 momentum guard: inside the slop the touch is held. The browser starts its own scroll (and, on lift,
          // its fling) from the first touchmove nobody prevents, and every later touchmove is then uncancelable, so
          // a slow start leaked into a native scroll + FREE + settle beside the step. A touch that would pass in
          // its tentative direction (the first chapter's pull-to-refresh, the release) is left alone: held when
          // neither direction passes, or (at an edge, where one does) when it has clearly started (>= 2 px) the
          // intercepted way; a sideways or 1 px lead-in at an edge is never held (Sol C6-sol-1 #1).
          // Only a vertical lead-in is held: a sideways lead-in is never touched (a horizontal swipe is not
          // intercepted). A touch whose held vertical lead-in then turns sideways is decided "flat" below: no step,
          // and its later moves stay prevented (nothing on the page scrolls sideways: overflow-x is clipped).
          // A second finger never gets here (the touch is dead): a pinch is never prevented.
          var vert = Math.abs(dy) > 0 && Math.abs(dy) >= C.DIR_RATIO * Math.abs(dx);
          var pf = vert && touchPasses(ev, 1, "probe"), pb = vert && touchPasses(ev, -1, "probe");
          var td = Math.abs(dy) >= 2 ? sign(dy) : 0;
          if (vert && ((!pf && !pb) || (pf !== pb && td && !(td > 0 ? pf : pb)))) {
            T.held = true;
            if (ev.cancelable !== false) ev.preventDefault();
          }
          return;
        }
        var dir = sign(dy);
        if (Math.abs(dy) < C.DIR_RATIO * Math.abs(dx)) T.decided = T.held ? "flat" : "pass"; // horizontal: no step
        else T.decided = touchPasses(ev, dir, "start") ? "pass" : "intercept";
      }
      if (T.decided === "flat") { if (ev.cancelable !== false) ev.preventDefault(); return; }
      if (T.decided !== "intercept") return;
      if (ev.cancelable !== false) ev.preventDefault();
      if (!T.stepped && Math.abs(dy) >= swipePx()) { // one touch = at most one step
        T.stepped = true;
        step(sign(dy), "touch", { t: ev.timeStamp, trigger: "swipe" });
      }
    }

    function onTouchEnd(ev) {
      if (!T) return;
      if (ev.touches && ev.touches.length) return; // a finger is still down
      var U = T;
      T = null;
      if (!enabled || U.dead || U.decided !== "intercept" || U.stepped) return;
      var ad = Math.abs(U.dy);
      if (ad >= C.SWIPE_END_MIN_PX && ad / Math.max(1, ev.timeStamp - U.t0) >= C.SWIPE_VEL) {
        step(sign(U.dy), "touch", { t: ev.timeStamp, trigger: "flick" });
      }
    }

    function onTouchCancel() { T = null; } // a cancelled touch never steps

    var L = [
      ["wheel", onWheel, { passive: false }, false],
      ["touchstart", onTouchStart, { passive: false }, false],
      ["touchmove", onTouchMove, { passive: false }, false],
      ["touchend", onTouchEnd, { passive: true }, false],
      ["touchcancel", onTouchCancel, { passive: true }, false],
      ["keydown", onKey, false, true] // on the window, bubble phase: the rail's own roving runs first (ICX-KEY.7)
    ];

    function reset() { g = null; T = null; }

    function attach(el) {
      if (target) detach();
      target = el;
      win = el && el.document ? el : (el && el.ownerDocument && el.ownerDocument.defaultView) || el;
      doc = (win && win.document) || (el && el.ownerDocument) || null;
      for (var i = 0; i < L.length; i++) (L[i][3] ? win : el).addEventListener(L[i][0], L[i][1], L[i][2]);
      reset();
    }

    function detach() {
      if (!target) return;
      for (var i = 0; i < L.length; i++) (L[i][3] ? win : target).removeEventListener(L[i][0], L[i][1], L[i][2]);
      target = win = doc = null;
      reset();
    }

    function setEnabled(on) {
      on = !!on;
      if (on !== enabled) reset();
      enabled = on;
    }

    return { attach: attach, detach: detach, setEnabled: setEnabled };
  }

  var api = Object.freeze({ CONFIG_VERSION: CONFIG_VERSION, DEFAULTS: DEFAULTS, createSequence: createSequence });
  root.FECheckpoint = api;

  // C7: dev only. ?ci-tune lazy-loads the tuning overlay next to this file; without the flag nothing is requested.
  var cs = root.document && root.document.currentScript;
  if (cs && cs.src && root.location && /[?&]ci-tune(?:[=&#]|$)/.test(root.location.search)) {
    var ts = root.document.createElement("script");
    ts.src = cs.src.replace(/checkpoint-input\.js(?:\?.*)?$/, "checkpoint-tune.js");
    root.document.head.appendChild(ts);
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
