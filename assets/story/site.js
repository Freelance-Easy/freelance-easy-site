/* =====================================================================================================================
   The page (site v2.1): ONE story driven by scroll (vault "Motion House Style — One Shape (Light)" § 10).
   - One master timeline: Make -> [seam] -> Look -> [seam] -> Know -> [seam] -> Grow -> the Ride -> Chase -> [seam] ->
     Yours -> [seam] -> Price -> [seam] -> Brand. Every piece and seam is a pure function of its time, so scrolling back
     plays the story backwards (scrub, never replay).
   - Native scroll only. A tall track under a sticky pin; a piecewise map turns scroll into a target time, with soft
     holds (short plateaus, 10–40 vh, where scroll barely moves time) at each beat's readable frame.
   - The shown time chases the target like a smooth-scrolling page (v2.2): it eases in, speeds up with the gap (up to
     3x the designed pace; v2.3) and eases out, in ONE rAF loop that sleeps when there is nothing to do. Forward never skips;
     a one-frame jump (an anchor, a scrollbar grab) or a long way back dips the stage and lands.
   - Text never scrubs: each beat's copy is a caption that switches, with hysteresis, when its beat becomes active.
     Every caption stays in the accessibility tree, in order (the inactive ones are transparent and out of the tab
     order); the stage itself is decorative (aria-hidden, inert) and its description travels with each caption.
   - Arrival: the first beats autoplay to the hold frame (the finished calculation, the hand at Create); the first
     scroll takes over. Anchors, reloads and history visits never play it.
   - Reverse: the hand never walks backwards (it fades while time runs back) and presses only squash going forwards.
   - Desktop: captions left, stage right, the whole story. Phones/tablets: the stage pinned on top, captions under it
     (always >= 22 px clear of it), Make -> Chase; the late beats (Yours, Price, the note, the ending) are sections after.
   - Reduced motion / no JS: no scrub; the beats stack as sections, each with its static final frame.
   - The chapter rail (desktop, v2.2): one tick per checkpoint at the left edge. The current one is longest and fills as
     its scene plays; hover or focus opens it into an angled fan with the nearest one's name; a click lands on that
     checkpoint (the anchor path). It runs inside the same loop.
   ===================================================================================================================== */
(function () {
  "use strict";
  const doc = document.documentElement;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const { css, div, clamp, mix, E, P, rgba, drawShape, drawInk } = FX;

  /* ---------------- theme: dark by default (Daniel, 2026-10-05); #dark / #light; remembered (try/catch) ---------------- */
  const KEY = "fe-theme";
  const theme = () => (doc.getAttribute("data-theme") === "light" ? "light" : "dark");
  function syncSwitch() {
    for (const b of $$("[data-set-theme]")) b.setAttribute("aria-pressed", String(b.dataset.setTheme === theme()));
    const m = $('meta[name="theme-color"]');
    if (m) m.setAttribute("content", theme() === "dark" ? "#080a0f" : "#f3f3f0");
  }
  function setTheme(th, persist) {
    if (th !== "dark" && th !== "light") return;
    if (persist) { try { localStorage.setItem(KEY, th); } catch (e) { /* storage blocked: the hash still works */ } }
    if (th === theme()) { syncSwitch(); return; }
    doc.setAttribute("data-theme", th);
    syncSwitch();
    refresh();
  }
  // v2.1 (Daniel: "id like the same light and dark mode circle effect to be on the website and the app"): the switch
  // reveals the other theme through an expanding, soft-edged circle from the button, with the app's numbers: 420 ms,
  // cubic-bezier(.55,0,.25,1) (it eases in), a feather of ~22% of the radius (48–220 px). The old theme stays opaque
  // underneath (no dip, no grey). start() rebuilds the story synchronously, so the new snapshot is a finished frame.
  let themeVT = null;
  function themeReveal(btn, th) {
    if (th === theme() || themeVT || !document.startViewTransition || !motion() ||
        matchMedia("(prefers-reduced-motion: reduce)").matches) { setTheme(th, true); return; }
    const r = btn.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
    const far = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    const end = far + Math.min(220, Math.max(48, far * 0.22)) + 4;
    doc.style.setProperty("--vt-x", `${x.toFixed(1)}px`);
    doc.style.setProperty("--vt-y", `${y.toFixed(1)}px`);
    doc.classList.add("vt-theme");
    const vt = (themeVT = document.startViewTransition(() => setTheme(th, true)));
    vt.ready.then(() => doc.animate({ "--vt-r": ["0px", `${end.toFixed(1)}px`] },
      { duration: 420, easing: "cubic-bezier(.55,0,.25,1)", fill: "forwards", pseudoElement: "::view-transition-new(root)" }))
      .catch(() => { /* skipped or unsupported: the theme has still changed */ });
    vt.finished.catch(() => {}).then(() => {
      doc.classList.remove("vt-theme"); doc.style.removeProperty("--vt-x"); doc.style.removeProperty("--vt-y");
      if (themeVT === vt) themeVT = null;
    });
  }
  for (const b of $$("[data-set-theme]")) b.addEventListener("click", () => {
    themeReveal(b, b.dataset.setTheme);
    try { history.replaceState(null, "", "#" + b.dataset.setTheme); } catch (e) { /* file:// may refuse */ }
  });
  window.addEventListener("hashchange", () => {
    const h = location.hash.slice(1);
    if (h === "dark" || h === "light") setTheme(h, true);
  });
  syncSwitch();

  /* ---------------- header: clear at the very top, frosted once scrolled; the visitor's platform ---------------- */
  const header = $(".site-header");
  const sentinel = $("[data-header-sentinel]");
  if (header && sentinel && "IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => header.classList.toggle("is-stuck", !e.isIntersecting)).observe(sentinel);
  }
  try {
    const ua = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || navigator.userAgent;
    if (/win/i.test(ua)) doc.setAttribute("data-os", "win");
  } catch (e) { /* ignore */ }

  /* ---------------- modes and the DOM ---------------- */
  const motion = () => doc.classList.contains("motion");
  const desktop = () => window.innerWidth >= 1024;
  const preset = () => (window.innerWidth < 640 ? "tall" : "wide");
  const SIZE = { wide: [1000, 900], tall: [600, 720] };
  const storyEl = $("#story"), pin = $(".pin"), track = $(".track"), capsEl = $(".captions");
  const stageWrap = $(".stage-wrap"), stage = $("[data-stage=story]"), stageCol = $(".stage-col"), shade = $(".stage-shade");
  const field = $(".stage-field"), band = $(".pin-band"), over = $(".pin-over"), label = $(".stage-label");
  // v2.1 (Daniel: "in the middle of 05, the blue background like flickers"): a dip (a catch-up too long to glide)
  // fades only the stage and its overlay cards, never the pin. Fading the pin let the dark page flash through the
  // blue band mid-Chase on fast scrolls; the band and the captions now stay put while the stage blinks to its frame.
  function setDip(a) {
    for (const el of [stageWrap, over]) if (el) { if (a >= 0.999) el.style.removeProperty("opacity"); else el.style.opacity = a.toFixed(3); }
  }
  function clearDip() { for (const el of [stageWrap, over]) if (el) el.style.removeProperty("opacity"); }
  const nav = $(".story-nav"), navBtns = nav ? $$("button[data-go]", nav) : [], navTip = nav ? $(".nav-tip", nav) : null;
  const BEATS = ["make", "look", "know", "grow", "chase", "yours", "price", "note", "end"];
  const PHONE_BEATS = ["make", "look", "know", "grow", "chase"];
  const copy = {}, home = {};
  for (const b of BEATS) {
    const sec = $(`.beat[data-beat="${b}"]`);
    const c = sec && $(".beat-copy", sec);
    if (!c) continue;
    copy[b] = c;
    home[b] = { sec, parent: c.parentNode, next: c.nextElementSibling };
  }
  // what the (decorative, aria-hidden) stage shows during each beat: read with that beat's caption by screen readers
  const STAGE_ARIA = {
    make: "On the stage: making invoice INV1056 in Freelance Easy. New invoice, the client Halvard & Wren, two line items, Balance Due $1,500.00, Create Invoice, and the finished invoice. Real app, fictional client.",
    look: "On the stage: the Theme page's style picker sets the invoice's template, then an accent color and a logo; the invoice is the real PDF.",
    know: "On the stage: the invoice list filtered by status: All Invoices, Overdue and Paid. Fictional data.",
    // NEW COPY (legal v-story): the grow and chase descriptions, matching index.html's stage aria-labels
    grow: "On the stage: the dashboard. Revenue by month over the last twelve months, then Collected YTD $21,450, Outstanding $675 and Overdue $450. Fictional data.",
    chase: "On the stage: with email already configured, an overdue invoice is emailed from its row in two clicks, then manually marked paid on the dashboard. Collected YTD rises to $21,900 and Overdue falls to $0. Fictional data.",
    yours: "On the stage: Settings, Data storage. Your invoices, clients, settings, logos and documents are saved in a folder on your computer.",
    price: "On the stage: one price, $5 a month or $50 a year.",
    note: "On the stage: the Freelance Easy mark.",
    end: "On the stage: the Freelance Easy mark.",
  };
  // captions: ONE ordered accessible copy of every beat. The inactive ones stay readable (transparent, never hidden from
  // assistive tech) but leave the tab order; focus that lands in one anyway (a screen reader's cursor) brings its beat up.
  const FOCUSABLE = "a[href], button, input, select, textarea, summary, [tabindex]";
  function capActive(c, on) {
    c.classList.toggle("is-idle", !on);
    // (phones, F1) the start caption's controls (the hero's CTA) stay in the tab order while it's idle: Tab from the
    // header reaches them from the first frame, and the focus brings the start beat up (capsEl's focusin). (Sol F1 #2:
    // treated as active, so any tabindex an idle tablet caption saved on them is restored too.)
    if (c === startEl && c.parentNode === capsEl) on = true;
    for (const el of c.querySelectorAll(FOCUSABLE)) {
      if (!on) {
        if (!el.hasAttribute("data-ti")) el.setAttribute("data-ti", el.getAttribute("tabindex") ?? "");
        el.setAttribute("tabindex", "-1");
      } else if (el.hasAttribute("data-ti")) {
        const v = el.getAttribute("data-ti");
        if (v === "") el.removeAttribute("tabindex"); else el.setAttribute("tabindex", v);
        el.removeAttribute("data-ti");
      }
    }
  }
  // phones (< 640 px, motion; phase F1, Daniel 2026-10-10 "app first"): the story pins from the first frame and the
  // hero's own copy (real DOM, moved, never cloned) splits into two captions: MAKE = an aria-hidden "01", the h1 and the
  // sub line (on screen while Make arrives), and START = the hero's CTA row, the trial line and the fine print with the
  // mobile note (its own beat, the first thing the scroll reveals, one block so the disclosures stay beside the button).
  // Both are put back in the hero's exact original order whenever the phone story is not running.
  const TALL_BEATS = ["make", "start", "look", "know", "grow", "chase"];
  // the start still (story seconds): its length, the step-back [start, duration] inside it, the caption switch (once the
  // stage is small) and the readable frame (the map's start hold)
  const START_DUR = 0.5, STEP_IN = [0.04, 0.3], START_CAP = 0.36, START_HOLD = 0.42;
  let startEl = null, stepEl = null, heroParts = null;
  function heroSplit(on) {
    const hc = copy.make;
    if (!hc) return;
    if (on) {
      if (!heroParts) {
        heroParts = [".sub", ".cta-row", ".disclose.strong", ".fine"].map((s) => $(`:scope > ${s}`, hc)).filter(Boolean)
          .map((el) => ({ el, next: el.nextSibling }));
        startEl = document.createElement("div");
        startEl.className = "hero-copy beat-copy start-copy";
        startEl.setAttribute("data-copy", "start");
        stepEl = document.createElement("span");
        stepEl.className = "step";
        stepEl.setAttribute("aria-hidden", "true");
        stepEl.textContent = "01";
      }
      if (stepEl.parentNode !== hc) hc.insertBefore(stepEl, hc.firstChild);
      for (const p of heroParts) if (p.el.parentNode !== startEl) startEl.appendChild(p.el);
      return;
    }
    if (!heroParts) return;
    // (the parts go back in reverse, each before the node that followed it, so the hero's DOM is exactly as it was)
    for (let k = heroParts.length - 1; k >= 0; k--) {
      const p = heroParts[k];
      if (p.el.parentNode !== hc) hc.insertBefore(p.el, p.next && p.next.parentNode === hc ? p.next : null);
    }
    if (stepEl.parentNode) stepEl.remove();
    if (startEl.parentNode) { startEl.classList.remove("is-on", "is-off", "is-idle"); startEl.style.removeProperty("top"); startEl.remove(); }
  }
  // each beat's copy lives in its home section (calm, no JS, the phone's late beats) or in the pin as a caption
  // (split: the phone story's hero split above)
  function placeCopies(inPin, split = false) {
    heroSplit(split && inPin.includes("make"));
    let moved = false;                                 // once one caption moves in, the later ones follow it (story order)
    for (const b of BEATS) {
      const c = copy[b];
      if (!c) continue;
      const want = inPin.includes(b);
      const dest = want ? capsEl : null;
      if (dest && (c.parentNode !== dest || moved)) {
        dest.appendChild(c); home[b].sec.classList.add("is-moved");
        moved = true;
      }
      if (!dest && c.parentNode !== home[b].parent) {
        const nx = home[b].next && home[b].next.parentNode === home[b].parent ? home[b].next : null;
        home[b].parent.insertBefore(c, nx);
        home[b].sec.classList.remove("is-moved");
      }
      c.classList.remove("is-on", "is-off");
      c.removeAttribute("inert");
      c.removeAttribute("aria-hidden");
      c.style.removeProperty("top");
      let sr = c.querySelector(":scope > .sr-stage");
      if (want && !sr) {
        sr = document.createElement("p");
        sr.className = "visually-hidden sr-stage";
        sr.textContent = STAGE_ARIA[b];
        c.appendChild(sr);
      }
      if (!want && sr) sr.remove();
      capActive(c, !want);                             // in the pin: idle until its beat is up; at home: ordinary
    }
    // (the phone story rode the headline's top: once it's back home, not even an empty style attribute is left)
    if (heroParts && !split && copy.make.getAttribute("style") === "") copy.make.removeAttribute("style");
    if (startEl && startEl.parentNode !== capsEl && heroParts && heroParts[0].el.parentNode === startEl) {
      capsEl.insertBefore(startEl, copy.make.nextSibling);
    }
    if (startEl && startEl.parentNode === capsEl) { startEl.classList.remove("is-on", "is-off"); capActive(startEl, false); }
  }
  // the caption element a beat shows in the pin
  const capFor = (b) => (b === "start" ? (startEl && startEl.parentNode === capsEl ? startEl : null)
    : b && copy[b] && copy[b].parentNode === capsEl ? copy[b] : null);

  /* ---------------- phones: the stage, its label row and the captions, balanced in the pin ---------------- */
  // (Sol mobile P1 #3 / P2 #7) The pin is 100svh tall. Under the stage: an 8 px gap and the 20 px "Fictional data" row
  // (always reserved), 12 px, then the captions, budgeted at the LARGEST one so nothing moves between beats. The stage
  // stays 5:6 (its canvas is 600 x 720) and as wide as the gutters allow; the space left over is shared above and below
  // the block (a little more below), clear of the bottom safe-area inset.
  const LABEL_ROW = 28, LABEL_GAP = 12, FIT_TOP = 12, FIT_BOT = 16;
  // the label's spot in the stage (mounts and seam layers go before it); null (append) once it lives under the stage
  const labelRef = () => (label.parentNode === stage ? label : null);
  function cssPx(h) {
    const el = div("", document.body);
    el.style.cssText = `position:fixed;left:0;top:0;width:0;visibility:hidden;pointer-events:none;height:${h}`;
    const v = el.getBoundingClientRect().height;
    el.remove();
    return v;
  }
  // (round B2, Astra pA #11) ONE horizontal grid: when the height limits the stage (375 x 667), the captions (and so the
  // chapter number) take the stage's own left and right edges, as the label row does; the captions are measured at
  // that width, so the fit runs until it settles. (F1: the story pins from the first frame, so there is no intro to
  // line the stage up with; the Make and start captions are in the budget like every other caption.)
  const fitVars = ["--stage-w", "--stage-top", "--cap-inset"];
  // the caption budget: the tallest pinned caption among the phone beats, less any excluded (F2's offer card is not
  // under the stage, so it will pass ["end"])
  function capBudget(exclude = []) {
    let h = 0;
    for (const b of TALL_BEATS) { if (exclude.includes(b)) continue; const c = capFor(b); if (c) h = Math.max(h, c.offsetHeight); }
    return h;
  }
  let fitCapH = -1, fitStartH = -1;
  function fitPhone() {
    if (preset() !== "tall") { for (const v of fitVars) pin.style.removeProperty(v); fitCapH = -1; return; }
    const ph = pin.clientHeight, cw = stageCol.clientWidth;
    const safe = cssPx("env(safe-area-inset-bottom, 0px)");
    let w = cw, capH = 0;
    for (let k = 0; k < 4; k++) {
      pin.style.setProperty("--cap-inset", `${(cw - w) / 2}px`);
      capH = capBudget(["start"]);     // (F1: the start caption has its own room: the stage steps back for it)
      const room = ph - safe - FIT_TOP - FIT_BOT - LABEL_ROW - LABEL_GAP - capH;
      const nw = Math.max(120, Math.floor(Math.min(cw, (room * 5) / 6)));
      if (nw >= w) break;
      w = nw;
    }
    fitCapH = capBudget(["start"]);
    const free = Math.max(0, ph - safe - ((w * 6) / 5 + LABEL_ROW + LABEL_GAP + capH));
    const top = Math.max(FIT_TOP, Math.round(free * 0.42));
    pin.style.setProperty("--stage-w", `${w}px`);
    pin.style.setProperty("--stage-top", `${top}px`);
  }
  // (F1) a caption that changes height on its own (late fonts; a share status line if its reserved line ever stopped
  // holding it) refits the stage when it changes the budget; the reserved status line means a share never does
  const capRO = "ResizeObserver" in window ? new ResizeObserver(() => { if (!capRaf) capRaf = requestAnimationFrame(capCheck); }) : null;
  let capRaf = 0;
  function capCheck() {
    capRaf = 0;
    if (!TL || TL.p !== "tall" || fitCapH < 0) return;
    const sh = startEl && startEl.parentNode === capsEl ? startEl.offsetHeight : 0;
    if (capBudget(["start"]) === fitCapH && sh === fitStartH) return;
    relayoutChecked();
  }

  /* ---------------- mounts: one per piece, all on the ONE stage ---------------- */
  const mounts = {};
  function mount(name, p, s0) {
    const [W, H] = SIZE[p];
    const rootEl = div("fx-root stage-world" + (p === "tall" ? " tall" : ""));
    css(rootEl, "width", `${W}px`); css(rootEl, "height", `${H}px`);
    css(rootEl, "--demo-scale", String(s0));        // site.css's phone tables: text at 13.5 px on screen (measured with it)
    const cam = div("fx-free fx-cam", rootEl);
    css(cam, "width", `${W}px`); css(cam, "height", `${H}px`); css(cam, "transform-origin", "0 0");
    const world = div("fe-app", cam);
    stage.insertBefore(rootEl, labelRef());
    css(rootEl, "transform", "none");
    const inst = FX.scenes[name].build({ root: rootEl, world, W, H, tall: p === "tall", dark: theme() === "dark" });
    const m = { name, rootEl, cam, world, W, H, inst, p, vis: null };
    m.show = (on) => { if (m.vis !== on) { m.vis = on; css(rootEl, "display", on ? "block" : "none"); } };
    m.seek = (t) => { css(cam, "transform", "none"); inst.seek(t); };
    return m;
  }

  /* ---------------- the master timeline ---------------- */
  const GBASE = { field: 0, band: 0, stage: 1, card: null, mark: 0 };
  let TL = null, MAP = null, OV = null, L = null;
  let ovCard = null, ovInk = null, ovMark = null;
  function clearStage() {
    for (const m of Object.values(mounts)) m.rootEl.remove();
    for (const k of Object.keys(mounts)) delete mounts[k];
    for (const l of $$(".fx-seam", stage)) l.remove();
    over.innerHTML = "";
    ovCard = ovInk = ovMark = null;
  }
  function build() {
    clearStage();
    const p = preset(), [W, H] = SIZE[p];
    const isDesk = desktop();
    const dark = theme() === "dark";
    css(stageWrap, "transform", "none");
    // (Sol F1 #1) the phone step-back's ride on the label row never survives a rebuild (a phone -> tablet resize)
    label.style.removeProperty("transform");
    // phones: "Fictional data" leaves the clipped stage for its own row under it; everywhere else it is in the stage
    if (p === "tall") { if (label.parentNode !== stageCol) stageCol.appendChild(label); }
    else if (label.parentNode !== stage) stage.appendChild(label);
    fitPhone();
    const s0 = stage.clientWidth / W;
    const names = isDesk ? ["make", "look", "know", "grow", "chase", "yours"] : PHONE_BEATS;
    for (const n of names) mounts[n] = mount(n, p, s0);
    for (const m of Object.values(mounts)) m.show(false);
    const layer = () => {
      const l = div("fx-root stage-world fx-seam" + (p === "tall" ? " tall" : ""));
      css(l, "width", `${W}px`); css(l, "height", `${H}px`); css(l, "display", "none"); css(l, "--demo-scale", String(s0));
      stage.insertBefore(l, labelRef());
      return l;
    };
    const segs = [];
    let T = 0;
    const scene = (id, m, t0, t1, G) => { segs.push({ id, kind: "scene", m, t0, T0: T, T1: T + (t1 - t0), G }); T += t1 - t0; };
    // a still: a scene held on one of its frames for dur seconds of story (phones: the start beat, Make held at HOLD)
    const still = (id, m, t, dur, G) => { segs.push({ id, kind: "scene", still: true, m, t0: t, T0: T, T1: T + dur, G }); T += dur; };
    const seam = (id, make, A, B) => {
      const ctx = { A, B, layer: layer(), W, H, tall: p === "tall", dark };
      const sm = make(ctx);
      segs.push({ id, kind: "seam", seam: sm, layer: ctx.layer, parts: [A, B].filter(Boolean), T0: T, T1: T + sm.DUR, G: GBASE });
      T += sm.DUR;
      return sm;
    };
    const hold = (id, dur, G) => { segs.push({ id, kind: "hold", T0: T, T1: T + dur, G }); T += dur; };
    const M = mounts, S = FX.seams;
    if (p === "tall") {
      // (phones, F1 option A, main 2026-10-10) Make plays to its arrival hold; then the START still: the frame held
      // completely still while the stage steps back (STEP_IN) to make room for the hero's CTA block under it; then Make
      // finishes on the smaller stage, which grows back over Make -> Look as the tablet stage does
      scene("make", M.make, 0, M.make.inst.HOLD, GBASE);
      still("start", M.make, M.make.inst.HOLD, START_DUR, GBASE);
      scene("makeEnd", M.make, M.make.inst.HOLD, M.make.inst.END, GBASE);
    } else scene("make", M.make, 0, M.make.inst.END, GBASE);
    const ml = seam("makeLook", S.makeLook, M.make, M.look);
    scene("look", M.look, ml.B0 || 0, M.look.inst.END, GBASE);
    const lk = seam("lookKnow", S.lookKnow, M.look, M.know);
    scene("know", M.know, lk.B0 || 0, M.know.inst.END, GBASE);
    const kg = seam("knowGrow", S.knowGrow, M.know, M.grow);
    scene("grow", M.grow, kg.B0 || 0, M.grow.inst.END, GBASE);
    seam("ride", S.ride, M.grow, M.chase);
    scene("chase", M.chase, 0, M.chase.inst.END, { ...GBASE, field: 1, band: 1 });
    if (isDesk) {
      seam("chaseYours", S.chaseYours, M.chase, M.yours);
      scene("yours", M.yours, M.yours.inst.START, M.yours.inst.END, GBASE);
      seam("yoursPrice", S.yoursPrice, M.yours, null);
      hold("price", 0.6, { ...GBASE, stage: 0, card: { from: "price", k: 1 } });
      seam("priceBrand", S.priceBrand, null, null);
      hold("brand", 1.0, { ...GBASE, stage: 0, mark: 1 });
    }
    TL = { segs, T1: T, HOLD: M.make.inst.HOLD, isDesk, p, W, H, dark };
    const seg = (id) => segs.find((s) => s.id === id);
    TL.seg = seg;
    // captions: the beat that starts at each switch time (the outgoing caption leaves, then the incoming arrives)
    // (the Ride: "Watch it add up." stays through the dive, leaves as the colour floods out, and "Follow up in two
    // clicks." arrives once the band is the whole page: one clean colour move, no text caught in it)
    const ride = seg("ride");
    TL.switches = [["look", seg("makeLook").T0 + 0.3], ["know", seg("lookKnow").T0 + 0.22],
      ["grow", seg("knowGrow").T0 + 0.22], [null, ride.T0 + ride.seam.DIVE + 0.04], ["chase", ride.T1 - 0.08]];
    // (phones, F1) the start caption (the hero's CTA block) takes over from the headline just past the arrival's hold,
    // with a narrow hysteresis (the hold itself drifts 0.03 s, so the default 0.12 would hide it)
    // (the headline leaves once the stage has stepped back and the CTA block takes its place; the CTA block leaves as
    // Make -> Look begins, before the regrowing stage reaches it; Look arrives as before)
    if (p === "tall") {
      TL.switches.unshift(["start", seg("start").T0 + START_CAP, 0.01], [null, seg("makeLook").T0 + 0.02, 0.01]);
    }
    if (isDesk) {
      // (Chase -> Yours: the Chase caption leaves before the band draws back over it; Yours arrives once it's gone)
      // (and the overlay card never grows or shrinks under a caption: each side of it leaves first)
      TL.switches.push([null, seg("chaseYours").T0 + 0.06], ["yours", seg("chaseYours").T0 + 0.5],
        [null, seg("yoursPrice").T0 + 0.04], ["price", seg("yoursPrice").T0 + (seg("yoursPrice").seam.PRICE_IN ?? 0.5), 0.02],
        [null, seg("priceBrand").T0 + 0.04], ["note", seg("priceBrand").T0 + 0.4], ["end", seg("brand").T0 + 0.45]);
    }
    TL.beats = ["make", ...TL.switches.map((s) => s[0])];
    TL.labelData = seg("lookKnow").T0 + 0.14;          // "Fictional data" as the list (and its year total) arrives
    TL.labelOff = isDesk ? seg("chaseYours").T0 + 0.36 : Infinity;   // ...until the last money has left the stage
    TL.late = isDesk ? seg("chaseYours").T0 + 0.3 : Infinity;
    // the page-level overlay (desktop): the card that becomes the price card, and the real mark
    if (isDesk) {
      ovCard = div("ov-card", over);
      ovInk = div("fx-ink", ovCard);
      ovMark = document.createElement("img");
      ovMark.src = "/assets/story/fe-mark.png";
      ovMark.alt = "";
      ovMark.className = "ov-mark";
      over.appendChild(ovMark);
    }
    // the Ride's colour (the October bar's own, near its top) is the band's and the field's
    const c = M.grow.inst.octColor(0.12);
    doc.style.setProperty("--ride", `rgb(${c.slice(0, 3).map(Math.round).join(",")})`);
    layout();
  }
  const beatAt = (T) => { let i = 0; for (const [, t] of TL.switches) if (T >= t) i++; return i; };
  const segAt = (T) => { const i = TL.segs.findIndex((s) => T <= s.T1 + 1e-9); return i < 0 ? TL.segs.length - 1 : i; };

  /* ---------------- layout: fit, the scroll map, every rect the frame path needs (measured here, never per frame) ---------------- */
  let storyTop = 0, kHero = 1, R0 = null, svhPx = 0, sizeW = 0, sizeH = 0;
  const CAP_GAP = 22;                                  // phones: the captions' clearance under the stage
  function layout() {
    if (!TL) return;
    css(stageWrap, "transform", "none");
    if (TL.p === "tall") { label.style.removeProperty("transform"); if (copy.make) copy.make.style.removeProperty("top"); if (startEl) startEl.style.removeProperty("top"); }
    const sw = stage.clientWidth, sh = stage.clientHeight, s = sw / TL.W;
    for (const m of Object.values(mounts)) { css(m.rootEl, "transform", `scale(${s.toFixed(5)})`); css(m.rootEl, "--demo-scale", String(s)); }
    for (const sg of TL.segs) if (sg.layer) { css(sg.layer, "transform", `scale(${s.toFixed(5)})`); css(sg.layer, "--demo-scale", String(s)); }
    const hh = header ? header.getBoundingClientRect().height : 64;
    storyTop = storyEl.getBoundingClientRect().top + window.scrollY - hh;
    const pr = pin.getBoundingClientRect(), wr = stageWrap.getBoundingClientRect();
    L = { sw, sh, s, stageTop: wr.top - pr.top, stageH: wr.height, stageW: wr.width };
    // phones: the hero's copy sits under a smaller stage; every other caption under the full stage; both keep CAP_GAP
    // (phones < 640 px: the story pins from the first frame with the stage at full size; every caption sits under the
    // label row, the start caption under the stepped-back stage (TL.kStart); the map's viewport is the pin's own stable 100svh, measured once per layout)
    sizeW = window.innerWidth; sizeH = window.innerHeight;
    svhPx = TL.p === "tall" ? cssPx("100svh") : 0;
    if (TL.p === "tall") {
      kHero = 1;
      L.capTop = Math.round(L.stageTop + L.stageH + LABEL_ROW + LABEL_GAP);
      pin.style.setProperty("--cap-top", `${L.capTop}px`);
      // (F1) how far the stage steps back for the start caption: its whole block fits above the bottom margin (and the
      // safe-area inset), the stage's top edge staying where it is
      const sh0 = startEl && startEl.parentNode === capsEl ? startEl.offsetHeight : 0;
      fitStartH = sh0;
      const room = pr.height - cssPx("env(safe-area-inset-bottom, 0px)") - FIT_BOT - sh0 - L.capTop;
      TL.kStart = sh0 > 0 ? clamp(1 + room / L.stageH, 0.3, 1) : 1;
    } else if (!TL.isDesk) {
      const heroH = copy.make ? copy.make.offsetHeight : 0;
      kHero = clamp((pr.height - L.stageTop - CAP_GAP - heroH - 14) / L.stageH, 0.5, 1);
      pin.style.setProperty("--cap-top", `${Math.round(L.stageTop + L.stageH + CAP_GAP)}px`);
    } else {
      kHero = 1;
      pin.style.removeProperty("--cap-top");
      if (copy.make) copy.make.style.removeProperty("top");
    }
    // the band's clip starts on the stage (in the band's own box: the pin plus the header above it)
    const br = { left: pr.left, top: pr.top - hh, right: pr.right, bottom: pr.bottom };
    R0 = { t: wr.top - br.top, l: wr.left - br.left, r: br.right - wr.right, b: br.bottom - wr.bottom,
      rad: parseFloat(getComputedStyle(stage).borderTopLeftRadius) || 28 };
    // the overlay's rects (relative to .pin-over): the Yours card in the stage, the price card, the mark and its tile
    if (TL.isDesk) {
      const orc = over.getBoundingClientRect();
      const y = mounts.yours.inst.X;
      const sx = wr.left - orc.left, sy = wr.top - orc.top;
      const pc = copy.price;
      const t0 = pc.style.transform;
      pc.style.transform = "translateY(-50%)";
      const cr = $(".price-card", pc).getBoundingClientRect();
      pc.style.transform = t0;
      const MS = Math.round(clamp(wr.width * 0.24, 120, 176));
      const mark = { x: sx + wr.width / 2 - MS / 2, y: sy + wr.height / 2 - MS / 2, w: MS, h: MS };
      const dark = TL.dark;
      const probe = div("", over);
      probe.style.cssText = "position:absolute;width:0;height:0;background:var(--bg-1);border-color:var(--line-1);border-style:solid;border-width:0";
      const csP = getComputedStyle(probe);
      const priceFill = rgba(csP.backgroundColor), priceLine = rgba(csP.borderTopColor);
      probe.remove();
      OV = {
        yours: { g: { cx: sx + y.R.cx * s, cy: sy + y.R.cy * s, w: y.R.w * s, h: y.R.h * s, r: y.R.r * s, bw: 1 },
          look: { fill: y.surf, line: y.line, lineA: 1, dark } },
        price: { g: { cx: cr.left - orc.left + cr.width / 2, cy: cr.top - orc.top + cr.height / 2, w: cr.width, h: cr.height, r: 24, bw: 1 },
          look: { fill: priceFill, line: priceLine, lineA: 1, dark } },
        tile: { g: { cx: mark.x + ((19 + 235) / 2 / 256) * MS, cy: mark.y + ((8 + 237) / 2 / 256) * MS, w: (216 / 256) * MS, h: (229 / 256) * MS, r: MS * 0.2, bw: 0 },
          look: { fill: priceFill, line: priceLine, lineA: 0, dark } },
        mark,
      };
      css(ovMark, "left", `${mark.x.toFixed(1)}px`); css(ovMark, "top", `${mark.y.toFixed(1)}px`);
      css(ovMark, "width", `${MS}px`); css(ovMark, "height", `${MS}px`);
    } else OV = null;
    buildMap();
    navMeasure();
    lastG = {};
    curSeg = -1;
  }

  /* ---------------- the scroll map: plateaus at each beat's readable frame, eased ramps between them ---------------- */
  function buildMap() {
    const vh = (TL.p === "tall" && svhPx > 0 ? svhPx : window.innerHeight) / 100;
    const seg = TL.seg;
    // v2.1 (Daniel: "a bit more responsive"; less scroll between the finished graph and the Ride): shorter holds (the
    // captions are on screen through each ramp too, so a hold only needs to read as a pause), a near-immediate first
    // scroll at the top, and a little less scroll per second of story
    // (v2.2, Daniel: "the pdf button can go straight to the template selecting part": no hold on a finished page;
    // Make hands straight into Look)
    const holds = [
      { beat: "make", T: TL.HOLD, len: 10 },
      { beat: "look", T: seg("look").T1 - 0.02, len: 28 },
      { beat: "know", T: seg("know").T1 - 0.02, len: 26 },
      { beat: "grow", T: seg("grow").T1 - 0.02, len: 14 },
      { beat: "chase", T: seg("chase").T1 - 0.02, len: TL.isDesk ? 32 : 26 },
    ];
    // (phones, F1) the start hold: the first scroll's stop, the stage still on Make's arrival frame, the CTA block up
    if (TL.p === "tall") holds.splice(1, 0, { beat: "start", T: seg("start").T0 + START_HOLD, len: 30 });
    if (TL.isDesk) {
      holds.push({ beat: "yours", T: seg("yours").T0 + 0.28, len: 26 }, { beat: "price", T: seg("price").T0 + 0.3, len: 40 },
        { beat: "note", T: seg("brand").T0 + 0.2, len: 32 }, { beat: "end", T: seg("brand").T1 - 0.05, len: 40 });
    }
    const DRIFT = 0.03;
    // px of scroll per second of story time. v2.3 (Daniel: "have the page scroll like less sensitive so ppl have to
    // scroll more to activate more of the animation … rn its super fkn spazzy"): 32 vh for every second (was scenes 18,
    // seams 27), so an ordinary scroll plays the story near its designed pace instead of asking for 6x
    // (v2.3b, Daniel: "i also just want the page to be longer … each scroll makes the animation move less so it feels
    // more natural and weighted": 48 vh)
    const rate = () => 48 * vh;
    const pieces = [];
    let s = 0;
    holds.forEach((h, i) => {
      pieces.push({ kind: "hold", beat: h.beat, s0: s, s1: s + h.len * vh, T0: h.T, T1: h.T + DRIFT });
      s += h.len * vh;
      if (i === holds.length - 1) return;
      const Ta = h.T + DRIFT, Tb = holds[i + 1].T;
      const parts = [];
      for (const sg of TL.segs) {
        const a = Math.max(Ta, sg.T0), b = Math.min(Tb, sg.T1);
        if (b > a + 1e-6) parts.push({ Ta: a, Tb: b, len: (b - a) * rate(sg) });
      }
      const Lp = parts.reduce((x, q) => x + q.len, 0);
      const Lr = Math.max(8 * vh, Lp);
      pieces.push({ kind: "ramp", beat: holds[i + 1].beat, s0: s, s1: s + Lr, T0: Ta, T1: Tb, parts, Lp, ease: Math.min(0.3, (10 * vh) / Lr) });
      s += Lr;
    });
    MAP = { pieces, L: s, vh };
    css(track, "height", `${Math.round(s)}px`);
  }
  // a ramp's progress with soft ends: zero slope at both ends, linear in the middle (C1)
  function easeEnds(q, a) {
    if (a <= 0) return q;
    if (q < a) return (q * q) / (2 * a) / (1 - a);
    if (q > 1 - a) return 1 - ((1 - q) * (1 - q)) / (2 * a) / (1 - a);
    return (q - a / 2) / (1 - a);
  }
  function mapScroll(y) {
    const s = y - storyTop;
    const PC = MAP.pieces;
    if (s <= 0) return PC[0].T0;
    for (const pc of PC) {
      if (s > pc.s1) continue;
      const q = clamp((s - pc.s0) / (pc.s1 - pc.s0));
      if (pc.kind === "hold") return pc.T0 + (pc.T1 - pc.T0) * FX.smooth(0, 1, q);
      let x = easeEnds(q, pc.ease) * pc.Lp;
      for (const part of pc.parts) {
        if (x <= part.len) return part.Ta + (part.Tb - part.Ta) * (part.len > 0 ? x / part.len : 1);
        x -= part.len;
      }
      return pc.T1;
    }
    return PC[PC.length - 1].T1;
  }
  function scrollForBeat(beat) {
    const hs = MAP.pieces.filter((p) => p.kind === "hold" && p.beat === beat);
    if (!hs.length) return null;
    const h = hs[hs.length - 1];
    return Math.round(storyTop + (h.s0 + h.s1) / 2);
  }
  // where the target is, as its segment and local time (a rebuild or a resize changes the map, not the story)
  function targetPlace() { const sg = TL.segs[segAt(target)]; return { id: sg.id, u: target - sg.T0 }; }
  // put the scroll position where the new map gives that same segment-local time (the map is monotonic: bisection)
  // phones: how far below the pinned story the reader is (px past its end), or null while they are in it or above it.
  // readerY is the position as of the last scroll event, so a layout change above (a caption refit) has not moved it.
  let readerY = 0;
  const storyEnd = () => storyTop + MAP.L;
  function pastStory() { return TL && TL.p === "tall" && MAP && readerY > storyEnd() + 1 ? readerY - storyEnd() : null; }
  function keepPast(d) { const y = Math.round(storyEnd() + d); if (Math.abs(window.scrollY - y) >= 1) window.scrollTo(0, y); readerY = y; }
  // the header takes the band's colour while the band is the page; (phones, Astra pA #8) the phone story ends on Chase's
  // band, so once the reader is past the pinned story the header is back on its own surface (scrolling back restores it)
  let bandK = 0;
  function syncOnBand() {
    const onBand = bandK >= 0.6;
    if (lastG.onBand !== onBand) { lastG.onBand = onBand; doc.classList.toggle("on-band", onBand); }
    const past = !!(TL && TL.p === "tall" && MAP && window.scrollY > storyEnd() + 1);
    if (lastG.past !== past) { lastG.past = past; doc.classList.toggle("past-band", past); }
  }
  window.addEventListener("scroll", () => { readerY = window.scrollY; if (TL && MAP) syncOnBand(); }, { passive: true });
  // a saved place (segment id + local time) on the current timeline. (Sol F1 #3) Make is one scene on wider stages and
  // three segments on phones (make to HOLD, the start still, makeEnd): across 640 px, Make's own time carries over.
  function placeIn(id, u) {
    let sg = TL.seg(id);
    if (!sg && (id === "start" || id === "makeEnd")) { u = TL.HOLD + (id === "makeEnd" ? u : 0); sg = TL.seg("make"); }
    if (sg && sg.id === "make" && TL.p === "tall" && u > sg.T1 - sg.T0 + 1e-9) { u -= sg.T1 - sg.T0; sg = TL.seg("makeEnd"); }
    return sg ? { sg, u } : null;
  }
  function anchorScroll(tp) {
    const pl = tp && placeIn(tp.id, tp.u);
    if (!pl) return;
    const T = clamp(pl.sg.T0 + pl.u, 0, TL.T1);
    if (T <= mapScroll(0) + 1e-6) return;
    let lo = 0, hi = storyTop + MAP.L;
    for (let k = 0; k < 40; k++) { const mid = (lo + hi) / 2; if (mapScroll(mid) < T) lo = mid; else hi = mid; }
    if (Math.abs(window.scrollY - hi) >= 1) window.scrollTo(0, Math.round(hi));
  }

  /* ---------------- rendering one frame of the story at time T ---------------- */
  // Entering a segment resets every mount (hidden, at rest) once; after that only the segment's own participants are
  // touched each frame (a hidden mount is never sought: a seam seeks only what it shows, and every seek rewrites all
  // it shows, so re-entry is deterministic).
  let curSeg = -1, lastG = {};
  const setOnce = (key, el, prop, val) => { if (lastG[key] !== val) { lastG[key] = val; css(el, prop, val); } };
  function render(T) {
    T = clamp(T, 0, TL.T1);
    const i = segAt(T);
    const sg = TL.segs[i];
    if (i !== curSeg) {
      for (const m of Object.values(mounts)) { m.show(false); css(m.rootEl, "opacity", "1"); css(m.cam, "transform", "none"); }
      for (const s of TL.segs) if (s.layer) css(s.layer, "display", s === sg ? "block" : "none");
      curSeg = i;
    }
    let G = sg.G;
    if (sg.kind === "scene") {
      sg.m.show(true);
      sg.m.seek(sg.still ? sg.t0 : sg.t0 + (T - sg.T0));
    } else if (sg.kind === "seam") {
      const u = T - sg.T0;
      sg.seam.seek(u);
      if (sg.seam.globals) G = { ...GBASE, ...sg.seam.globals(u) };
    }
    applyGlobals(G, T);
  }
  function applyGlobals(G, T) {
    const f = G.field || 0;
    setOnce("field", field, "opacity", f >= 0.999 ? "1" : f.toFixed(3));
    setOnce("shade", shade, "opacity", (1 - f).toFixed(3));
    // the field can gather into a rect on the stage (canvas units -> stage px): Chase -> Yours, the Ride mirrored
    let fclip = "none";
    if (G.fieldTo && G.fieldK > 0 && R0) {
      const s = L.s, k = G.fieldK, r = G.fieldTo;
      const x = (r.cx - r.w / 2) * s, y = (r.cy - r.h / 2) * s, w = r.w * s, h = r.h * s;
      fclip = `inset(${(y * k).toFixed(1)}px ${((L.sw - x - w) * k).toFixed(1)}px ${((L.sh - y - h) * k).toFixed(1)}px ${(x * k).toFixed(1)}px round ${mix(R0.rad, (r.r || 3) * s, k).toFixed(1)}px)`;
    }
    setOnce("fieldClip", field, "clip-path", fclip);
    const bk = G.band || 0;
    setOnce("bandD", band, "display", bk > 0 ? "block" : "none");
    const kb = 1 - bk;
    setOnce("bandC", band, "clip-path", bk <= 0 || bk >= 1 || !R0 ? "none"
      : `inset(${(R0.t * kb).toFixed(1)}px ${(R0.r * kb).toFixed(1)}px ${(R0.b * kb).toFixed(1)}px ${(R0.l * kb).toFixed(1)}px round ${(R0.rad * kb).toFixed(1)}px)`);
    const so = G.stage == null ? 1 : G.stage;
    setOnce("stageOp", stageCol, "opacity", so >= 0.999 ? "1" : so.toFixed(3));
    setOnce("stageVis", stageCol, "visibility", so <= 0.001 ? "hidden" : "visible");
    // phones: the stage is smaller while the hero's copy is up, and grows to full size as Look begins; the hero's copy
    // rides down with the stage's bottom edge, CAP_GAP under it, so the growing stage never runs into it
    if (!TL.isDesk && TL.p !== "tall") {
      const sl = TL.seg("makeLook");
      const k = T <= sl.T0 ? kHero : mix(kHero, 1, P(T, sl.T0, sl.T1 - sl.T0, E.SMOOTH));
      setOnce("stageK", stageWrap, "transform", k >= 0.999 ? "none" : `scale(${k.toFixed(4)})`);
      if (copy.make) setOnce("heroTop", copy.make, "top", `${Math.round(L.stageTop + L.stageH * Math.min(1, k) + CAP_GAP)}px`);
    }
    // phones (F1 option A): the stage steps back during the start still (Make's frame held) so the hero's CTA block fits
    // under it, stays back while Make finishes, and grows back over Make -> Look as the tablet stage does. The label row
    // and the two hero captions ride the stage's bottom edge; the stage scales about its top centre.
    if (TL.p === "tall" && TL.kStart < 1) {
      const st = TL.seg("start"), sl = TL.seg("makeLook");
      const k = T <= sl.T0 ? mix(1, TL.kStart, P(T, st.T0 + STEP_IN[0], STEP_IN[1], E.SMOOTH))
        : mix(TL.kStart, 1, P(T, sl.T0, sl.T1 - sl.T0, E.SMOOTH));
      const full = k >= 0.9995, dy = L.stageH * (1 - k);
      setOnce("stageK", stageWrap, "transform", full ? "none" : `scale(${k.toFixed(4)})`);
      setOnce("labelK", label, "transform", full ? "none" : `translate(${(L.stageW * (1 - k) / 2).toFixed(2)}px, ${(-dy).toFixed(2)}px)`);
      const top = full ? "" : `${(L.capTop - dy).toFixed(2)}px`;
      if (copy.make) setOnce("heroTop", copy.make, "top", top);
      if (startEl) setOnce("startTop", startEl, "top", top);
    }
    // (full-field: the field is the whole stage, so the stage's own background takes its colour too: no edge fringe)
    const pinCls = "pin" + (f > 0.5 ? " on-field" : "") + (f >= 0.999 && !(G.fieldK > 0) ? " full-field" : "") + (T >= TL.late ? " is-late" : "");
    if (lastG.pinCls !== pinCls) { lastG.pinCls = pinCls; pin.setAttribute("class", pinCls); }
    // the header joins the band while the band is the page (syncOnBand)
    bandK = bk;
    syncOnBand();
    // the chapter rail takes the band's colours once the band's opening clip has passed it
    if (navOn && R0) {
      const nb = bk >= 1 || (bk > 0 && R0.l * kb < navCx && R0.t * kb < navCy);
      if (lastG.navBand !== nb) { lastG.navBand = nb; nav.classList.toggle("on-band", nb); }
    }
    // legal v-story (2026-10-08): "Fictional data", continuously, from the first frame until the last money has left
    // the stage (both directions); the old "The client is fictional." variant (and the switch at TL.labelData) is gone
    const mode = T >= TL.labelOff ? "" : "data";
    if (lastG.label !== mode) { lastG.label = mode; label.setAttribute("data-mode", mode); }
    if (OV && ovCard) drawOverlay(G);
  }
  function drawOverlay(G) {
    const c = G.card;
    if (!c) { setOnce("ovD", ovCard, "display", "none"); }
    else {
      lastG.ovD = "block";
      const a = OV[c.from], b = OV[c.to || (c.from === "yours" ? "price" : c.from)];
      const k = c.k;
      const g = { cx: mix(a.g.cx, b.g.cx, k), cy: mix(a.g.cy, b.g.cy, k), w: mix(a.g.w, b.g.w, k), h: mix(a.g.h, b.g.h, k),
        r: mix(a.g.r, b.g.r, clamp(k)), bw: 1 };
      const kc = clamp(k);
      drawShape(ovCard, g, { fill: FX.mixC(a.look.fill, b.look.fill, kc), line: FX.mixC(a.look.line, b.look.line, kc),
        lineA: mix(a.look.lineA, b.look.lineA, kc), dark: TL.dark, sq: 0 });
      const seal = c.seal || 0;
      drawInk(ovInk, { mode: seal <= 0 ? "none" : seal >= 1 ? "full" : "disc", k: seal, x: g.w / 2, y: g.h / 2, w: g.w, h: g.h, color: [6, 10, 15, 1] });
    }
    const m = G.mark || 0;
    setOnce("mkO", ovMark, "opacity", m >= 0.999 ? "1" : m.toFixed(3));
    setOnce("mkD", ovMark, "display", m > 0.001 ? "block" : "none");
  }

  /* ---------------- captions: switched by beat (hysteresis), never scrubbed ---------------- */
  // A switch: the outgoing leaves in 60 ms, then the incoming arrives in 100 ms (160 ms in all; never two at once).
  const CAP_OUT_MS = 60;
  let capIdx = -1, capTimer = 0;
  function updateCaptions(T, instant) {
    let i = beatAt(T);
    if (!instant && capIdx >= 0 && Math.abs(i - capIdx) === 1) {
      // hysteresis: 0.12 s of story either side of a switch, or the switch's own width (the price copy rides its card,
      // so it uses 0.02: with 0.12 the card showed empty going forwards and the copy hung over it going back, ~0.3 s)
      const [, boundary, width = 0.12] = TL.switches[Math.max(i, capIdx) - 1];
      if (Math.abs(T - boundary) < width) i = capIdx;
    }
    if (i === capIdx && !instant) return;
    capIdx = i;
    const b = TL.beats[i];                            // null: a beat with no caption (the Ride's flood)
    const next = capFor(b);                            // (phones: the hero is split into make + start)
    clearTimeout(capTimer);
    const cur = $$(".beat-copy.is-on", capsEl).filter((c) => c !== next);
    if (instant || !cur.length) {
      for (const c of $$(".beat-copy", capsEl)) { if (c !== next) { c.classList.remove("is-on", "is-off"); capActive(c, false); } }
      if (next) {
        if (instant) { next.style.transition = "none"; next.classList.add("is-on"); void next.offsetWidth; next.style.transition = ""; }
        else next.classList.add("is-on");
        next.classList.remove("is-off");
        capActive(next, true);
      }
    } else {
      for (const c of cur) { c.classList.remove("is-on"); c.classList.add("is-off"); capActive(c, false); }
      if (next) next.classList.remove("is-on", "is-off");
      capTimer = setTimeout(() => {
        for (const c of $$(".beat-copy.is-off", capsEl)) c.classList.remove("is-off");
        if (next) { next.classList.add("is-on"); capActive(next, true); }
      }, CAP_OUT_MS);
    }
    // the chapter rail follows the last beat that had a caption (through the Ride's flood, 04 stays current)
    let named = b;
    for (let j = i; !named && j >= 0; j--) named = TL.beats[j];
    navSetActive(named, instant);
  }

  /* ---------------- the chapter rail (desktop): checkpoints to see, follow and click ---------------- */
  // v2.2 (Daniel: "checkpoints that they could maybe like click on the left side of the screen … some kind of dynamic
  // animated scroller or animated bars … [Codex's] when you hover on it it expands into the more angled bars"). One tick
  // per checkpoint. At rest the current one is longest and fills as its scene plays (full on its readable frame), and
  // the long tick rolls on to the next as the next caption arrives. Hover (or keyboard focus) opens the rail like a
  // dock: the ticks swell around the pointer into an angled fan and the nearest one's name shows beside it. A click
  // lands on that checkpoint's readable frame through the anchor path (far away, the stage dips and lands). Lengths are
  // px, positions are in ticks; every move is a critically damped spring (closed form: the same at any frame rate).
  const NAV = { gap: 24, rest: [10, 20], open: [12, 44], fan: 3.4, doneA: 0.4,
    wP: 2 * Math.PI * 2.4, wH: 2 * Math.PI * 3.2, wY: 2 * Math.PI * 6, wTip: 2 * Math.PI * 7 };
  let navOn = false, navIn = false, navCP = [], navIdx = {}, navA = 0, navCx = 0, navCy = 0, navRoom = 44;
  let navP = 0, navPV = 0, navH = 0, navHV = 0, navY = 0, navYV = 0, navTipY = 0, navTipYV = 0;
  let navPtr = null, navFocus = -1, navTipK = -1, navTipO = "", navTipT = "";
  function spr(x, v, goal, w, dt) {
    const e = x - goal, k = Math.exp(-w * dt), c = v + w * e;
    return [goal + (e + c * dt) * k, (v - w * c * dt) * k];
  }
  // each checkpoint fills from the moment its caption arrives to its readable frame (its last hold in the map); Make
  // fills to its own end (the PDF press), since its only hold is the arrival's, mid-scene
  function navBuild() {
    if (!nav || !TL || !TL.isDesk) { navTeardown(); return; }
    navCP = []; navIdx = {};
    for (const btn of navBtns) {
      const b = btn.dataset.go;
      const sw = TL.switches.find((s) => s[0] === b);
      if (b !== "make" && !sw) continue;
      const hs = MAP.pieces.filter((p) => p.kind === "hold" && p.beat === b);
      const start = b === "make" ? 0 : sw[1];
      const end = b === "make" ? TL.seg("make").T1 - 0.02 : hs.length ? hs[hs.length - 1].T0 : start;
      const anchor = Math.max(end, start + 0.05);
      const tk = $(".tk", btn);
      tk.style.setProperty("--i", String(navCP.length));
      navIdx[b] = navCP.length;
      navCP.push({ b, btn, tk, f: $("b", tk), start, anchor, w: "", fw: "", fa: "", cls: "" });
    }
    nav.hidden = false;
    navOn = true;
    navMeasure();
  }
  // where the rail sits in the band's box (the band reaches it as its clip opens: applyGlobals), and how far the open
  // fan may reach before the captions (10 px clear: the narrow desktops get a shorter fan, never ticks over the text)
  function navMeasure() {
    if (!navOn) return;
    const r = $("ol", nav).getBoundingClientRect(), pr = pin.getBoundingClientRect();
    const hh = header ? header.getBoundingClientRect().height : 64;
    navCx = r.left + 16 - pr.left;
    navCy = r.top + r.height / 2 - (pr.top - hh);
    navRoom = clamp(capsEl.getBoundingClientRect().left - r.left - 10, NAV.rest[1] + 6, NAV.open[1]);
  }
  function navReveal() {
    if (!navOn || navIn) return;
    navIn = true;
    nav.classList.add("is-in");                       // CSS draws the ticks in, top to bottom
  }
  function navRove(k) { navCP.forEach((c, j) => c.btn.setAttribute("tabindex", j === k ? "0" : "-1")); }
  function navSetActive(b, force) {
    const k = navIdx[b];
    if (k == null || (k === navA && !force)) return;
    navA = k;
    navCP.forEach((c, j) => { if (j === k) c.btn.setAttribute("aria-current", "step"); else c.btn.removeAttribute("aria-current"); });
    if (!nav.contains(document.activeElement)) navRove(k);   // Tab lands on the current chapter
  }
  function navGo(b) {
    if (!TL || !motion()) return;
    const y = b === "make" ? 0 : scrollForBeat(b);
    if (y == null) return;
    navScrollTo(y);
  }
  // one frame of the rail at story time T; returns true while any of its springs is still moving
  function navTick(T, dt, instant) {
    if (!navOn || !navCP.length) return false;
    const n = navCP.length;
    const hGoal = navPtr != null || navFocus >= 0 ? 1 : 0;
    const yGoal = navFocus >= 0 ? navFocus : navPtr != null ? navPtr : navY;
    let busy = false;
    if (instant) {
      navP = navA; navPV = 0; navH = hGoal; navHV = 0; navY = yGoal; navYV = 0;
    } else {
      [navP, navPV] = spr(navP, navPV, navA, NAV.wP, dt);
      [navH, navHV] = spr(navH, navHV, hGoal, NAV.wH, dt);
      [navY, navYV] = spr(navY, navYV, yGoal, NAV.wY, dt);
      if (Math.abs(navP - navA) < 1e-3 && Math.abs(navPV) < 1e-2) { navP = navA; navPV = 0; } else busy = true;
      if (Math.abs(navH - hGoal) < 1e-3 && Math.abs(navHV) < 1e-2) { navH = hGoal; navHV = 0; } else busy = true;
      if (Math.abs(navY - yGoal) < 1e-3 && Math.abs(navYV) < 1e-2) { navY = yGoal; navYV = 0; } else busy = true;
    }
    const h = clamp(navH);
    const tipK = h > 0.02 ? Math.round(clamp(navY, 0, n - 1)) : -1;
    const [r0, r1] = NAV.rest, o0 = NAV.open[0], o1 = navRoom;
    let tipLen = 0;
    for (let j = 0; j < n; j++) {
      const c = navCP[j];
      const gR = Math.max(0, 1 - Math.abs(j - navP));                  // rest: the current tick (shared as it rolls on)
      const gO = Math.max(0, 1 - Math.abs(j - navY) / NAV.fan);        // open: the angled fan around the pointer
      const len = mix(r0 + (r1 - r0) * gR, o0 + (o1 - o0) * gO, h);
      const f = clamp((T - c.start) / (c.anchor - c.start));
      const w = `${len.toFixed(2)}px`, fw = `${(f * len).toFixed(2)}px`, fa = mix(NAV.doneA, 1, gR).toFixed(3);
      const cls = "tk" + (f > 0.002 && f < 0.998 ? " is-filling" : "") + (j === tipK ? " is-tip" : "");
      if (c.w !== w) { c.w = w; c.tk.style.width = w; }
      if (c.fw !== fw) { c.fw = fw; c.f.style.width = fw; }
      if (c.fa !== fa) { c.fa = fa; c.f.style.opacity = fa; }
      if (c.cls !== cls) { c.cls = cls; c.tk.className = cls; }
      if (j === tipK) tipLen = len;
    }
    // the name: a pill beside the tick under the pointer, gliding from tick to tick (it appears where it is)
    if (tipK < 0) navTipK = -1;
    else {
      if (tipK !== navTipK) {
        const c = navCP[tipK];
        $(".n", navTip).textContent = c.btn.dataset.n || "";
        $(".t", navTip).textContent = c.btn.dataset.name || "";
        if (navTipK < 0) { navTipY = tipK * NAV.gap; navTipYV = 0; }
        navTipK = tipK;
      }
      const goal = tipK * NAV.gap;
      if (instant) { navTipY = goal; navTipYV = 0; }
      else {
        [navTipY, navTipYV] = spr(navTipY, navTipYV, goal, NAV.wTip, dt);
        if (Math.abs(navTipY - goal) < 0.05 && Math.abs(navTipYV) < 0.5) { navTipY = goal; navTipYV = 0; } else busy = true;
      }
      const t = `translate3d(${(tipLen + 14).toFixed(1)}px, ${(navTipY + NAV.gap / 2 - 13).toFixed(1)}px, 0)`;
      if (navTipT !== t) { navTipT = t; navTip.style.transform = t; }
    }
    const o = (tipK < 0 ? 0 : h).toFixed(3);
    if (navTipO !== o) { navTipO = o; navTip.style.opacity = o; }
    return busy;
  }
  function navTeardown() {
    navOn = false; navIn = false; navPtr = null; navFocus = -1; navTipK = -1; navTipO = navTipT = "";
    if (!nav) return;
    nav.hidden = true;
    nav.classList.remove("is-in", "on-band");
    for (const c of navCP) {
      c.tk.removeAttribute("style"); c.tk.className = "tk"; c.f.removeAttribute("style");
      c.btn.removeAttribute("aria-current"); c.btn.setAttribute("tabindex", "-1");
    }
    navTip.removeAttribute("style");
    navCP = []; navIdx = {};
  }
  if (nav) {
    const btnAt = (e) => { const b = e.target.closest && e.target.closest("button[data-go]"); return b && navIdx[b.dataset.go] != null ? b : null; };
    nav.addEventListener("pointermove", (e) => {
      if (e.pointerType === "touch") return;          // touch: a tap is a click, never a hover
      const b = btnAt(e);
      if (!b) return;
      navPtr = clamp(navIdx[b.dataset.go] + (e.offsetY - NAV.gap / 2) / NAV.gap, 0, navCP.length - 1);
      wake();
    });
    nav.addEventListener("pointerleave", () => { navPtr = null; wake(); });
    nav.addEventListener("click", (e) => { const b = btnAt(e); if (b) navGo(b.dataset.go); });
    nav.addEventListener("focusin", (e) => {
      const b = btnAt(e);
      if (!b) return;
      navFocus = b.matches(":focus-visible") ? navIdx[b.dataset.go] : -1;
      navRove(navIdx[b.dataset.go]);
      wake();
    });
    nav.addEventListener("focusout", (e) => {
      if (nav.contains(e.relatedTarget)) return;
      navFocus = -1;
      navRove(navA);
      wake();
    });
    nav.addEventListener("keydown", (e) => {
      const b = btnAt(e);
      if (!b) return;
      const k = navIdx[b.dataset.go];
      const to = { ArrowDown: k + 1, ArrowRight: k + 1, ArrowUp: k - 1, ArrowLeft: k - 1, Home: 0, End: navCP.length - 1 }[e.key];
      if (to == null) return;
      e.preventDefault();
      navCP[clamp(to, 0, navCP.length - 1)].btn.focus({ preventScroll: true });   // the rail is pinned: never scroll
    });
  }

  /* ---------------- the follower: shown time chases the target (eases in, speeds up with the gap, eases out) ---------------- */
  // v2.2 (Daniel: "i can scroll faster than the animations so easily … more responsive to the scrolling, maybe like an
  // ease in then speed to where the scroll is? something smooth but responsive so u still feel like ur scrolling a
  // website"). v2.1b's stiff spring with a hard 1.8x cap let a quick scroll leave the stage crawling seconds behind.
  // Now the stage's speed aims at the gap: it closes ~63% of it every TAU (like a smooth-scrolling page), never faster
  // than it could still stop in (no overshoot), up to VMAX. The speed itself changes smoothly (over TV) and never by
  // more than ACC per second, so every start eases in, even from a hard flick, and every stop eases out. (v2.1b's
  // complaint, "wayyy too fast … spazzy", was v2's stiff spring starting at full speed on every wheel notch: the eased
  // speed is what keeps it calm.) Forward never skips; only a one-frame JUMP or a long way back (REWIND) dips and lands.
  // v2.3 (Daniel: "maybe we can try 3x … id rather it smooth and a bit draggy than super rushed … the 6x spazzyness"):
  // the ceiling is 3x, the chase a touch softer (TAU 0.2 -> 0.25) and its speed changes gentler (ACC 16 -> 9), and the
  // map asks for less speed in the first place (32 vh per story-second). Moving on to the next chapter eases up to the
  // ceiling and back down to the scroll's own pace.
  const TAU = 0.25, TV = 0.08, ACC = 9, VMAX = 3, A0 = 0.02, JUMP = 2.5, REWIND = 8, DIR_EPS = 0.015;
  // e = shown - target (the target held still over the step), v = d(shown)/dt; sub-steps of <= 1/240 s keep it the same
  // at any frame rate
  // a seam may ask to be played no faster than its own CAP (the PDF -> Look reveal, Daniel: "smoother and slower so it
  // feels more natural flow instead of speedy"): inside it the ceiling is CAP; ahead of it, in the direction the stage
  // is actually moving (its momentum, or the target's side when at rest), the ceiling is the speed that can still be
  // shed over the distance left (planned at 0.3 ACC, so the lagging speed still arrives at CAP), so it eases down into
  // it rather than braking at its edge. Evaluated at every sub-step (Sol: once per frame let it enter at ~1.67x).
  function capAt(s, v, t) {
    let cap = VMAX;
    if (!TL) return cap;
    const d = v > 0.02 ? 1 : v < -0.02 ? -1 : Math.sign(t - s);
    for (const sg of TL.segs) {
      const c = sg.seam && sg.seam.CAP;
      if (!c) continue;
      if (s >= sg.T0 && s <= sg.T1) cap = Math.min(cap, c);
      else if (d > 0 && sg.T0 > s) cap = Math.min(cap, Math.sqrt(c * c + 0.6 * ACC * (sg.T0 - s)));
      else if (d < 0 && sg.T1 < s) cap = Math.min(cap, Math.sqrt(c * c + 0.6 * ACC * (s - sg.T1)));
    }
    return cap;
  }
  // (capOf(e, v): the ceiling where the stage is now, e = shown - target; null = VMAX everywhere)
  function follow(e, v, dt, capOf = null) {
    for (let t = dt; t > 1e-9; ) {
      const h = Math.min(t, 1 / 240);
      t -= h;
      const a = Math.abs(e), dir = e > 0 ? -1 : 1;
      if (a < 1e-9) return [0, 0];                    // on the target: stop there (never coast past a still target)
      const cap = capOf ? capOf(e, v) : VMAX;
      const sp = v * dir;                             // speed toward the target
      if (sp > 0 && sp * sp >= 1.8 * ACC * a) {
        // inside the braking zone: a constant deceleration that stops exactly on the target (sp^2 / 2a stays constant
        // as it brakes), so every arrival eases to rest rather than snapping its last bit of speed away
        v -= dir * Math.min(sp, ((sp * sp) / (2 * a)) * h);
      } else {
        // the speed to be at: the gap over TAU (A0 makes the tail finish rather than creep), what it can still stop
        // in, and the ceiling; reached smoothly (TV) and never faster than ACC
        const vg = dir * Math.min(cap, (a + A0) / TAU, Math.sqrt(2 * ACC * a));
        v += clamp((vg - v) / TV, -ACC, ACC) * h;
      }
      // the ceiling holds on the actual speed too: anything over it is shed firmly (3 ACC), never in one snap
      if (Math.abs(v) > cap) v = Math.sign(v) * Math.max(cap, Math.abs(v) - 3 * ACC * h);
      const e1 = e + v * h;
      if (Math.sign(e1) !== Math.sign(e)) return [0, 0];       // it never passes a still target
      e = e1;
    }
    return [e, v];
  }

  /* ---------------- the loop: one rAF; sleeps when there is nothing to do ---------------- */
  let shown = 0, vel = 0, target = 0, raf = 0, lastNow = 0, intro = null, dip = null, held = false, gateTo = 1, lastDrawn = null;
  let dirSign = 1, dirAnchor = 0, lastTargetMove = 0, navJumpAt = -1;
  // an explicit jump (a nav link, a rail tick, focus reaching a caption) may dip forwards too; scrolling never does
  function navScrollTo(y) { navJumpAt = FX.now(); window.scrollTo(0, y); wake(); }
  function wake() {
    if (!raf && TL && motion()) { lastNow = FX.now(); raf = requestAnimationFrame(tick); }
  }
  function tick() {
    raf = 0;
    if (!TL || held) return;
    const now = FX.now();
    const dt = clamp(now - lastNow, 0.0005, 0.05);
    lastNow = now;
    // v2.1c (Daniel: "while scrolling it felt like it was skipping some scenes then when i scroll back i see them"):
    // ordinary scrolling NEVER skips. The stage plays every scene in order at up to the cap, even if it trails the
    // scroll for a moment. Only a one-frame jump (a nav anchor, a scrollbar grab) dips and lands.
    const tNew = mapScroll(window.scrollY), step = Math.abs(tNew - target);
    if (step > 1e-4) lastTargetMove = now;
    // (v2.3, Sol: a PageDown is a one-frame step of ~2.7 s; forwards that must play, not dip. A jump dips when it goes
    // back, or when the visitor asked for it: a link, a rail tick)
    const jumped = step > JUMP && (tNew < target || now - navJumpAt < 0.5);
    target = tNew;
    let busy = false;
    if (intro) {
      // the arrival plays at natural speed to the hold frame; the first genuine scroll ends it (the follower takes over
      // from the arrival's own time and speed)
      const it = Math.min(TL.HOLD, (now - intro.t0) * intro.rate);
      shown = it;
      vel = it < TL.HOLD ? intro.rate : 0;
      if (Math.abs(window.scrollY - intro.y0) > 1) intro = null;
      else { busy = it < TL.HOLD; if (!busy) intro = null; }
    }
    if (!intro) {
      if (dip) {
        const u = now - dip.t0;
        if (u < 0.1) setDip(1 - u / 0.1);
        else {
          if (!dip.jumped) { shown = target; vel = 0; dip.jumped = true; }
          const a = Math.min(1, (u - 0.1) / 0.1);
          setDip(a);
          if (a >= 1) { clearDip(); dip = null; }
        }
        busy = true;
      } else if (Math.abs(target - shown) > JUMP && !(shown < TL.HOLD && target <= TL.HOLD + 0.1) &&
          (jumped || (target < shown && now - lastTargetMove > 0.12 && shown - target > REWIND))) {
        // dip and land instead of gliding: (a) a one-frame jump (an anchor, a scrollbar grab), or (b) a LONG way back
        // (more than REWIND s of story, e.g. back to the top) once the scroll has paused. Forward never skips: every
        // scene plays, in order. (Except inside the arrival's own stretch: a scroll during the arrival fast-forwards
        // it to the hold.)
        dip = { t0: now, jumped: false };
        busy = true;
      } else {
        const [e, v] = follow(shown - target, vel, dt, (e1, v1) => capAt(target + e1, v1, target));
        shown = target + e; vel = v;
        if (Math.abs(e) < 0.0006 && Math.abs(v) < 0.006) { shown = target; vel = 0; } else busy = true;
      }
    }
    // the direction gate: symmetric hysteresis (DIR_EPS of story time either way) on the TARGET's movement, so a small
    // move can't strand it; going forwards it explicitly restores the hand and the presses
    if (intro) { dirSign = 1; dirAnchor = target; }
    else if (dirSign > 0) { if (target < dirAnchor - DIR_EPS) { dirSign = -1; dirAnchor = target; } else if (target > dirAnchor) dirAnchor = target; }
    else if (target > dirAnchor + DIR_EPS) { dirSign = 1; dirAnchor = target; } else if (target < dirAnchor) dirAnchor = target;
    gateTo = dirSign > 0 ? 1 : 0;
    FX.gate.press = gateTo;
    const g0 = FX.gate.cursor;
    if (g0 !== gateTo) {
      FX.gate.cursor = gateTo > g0 ? Math.min(1, g0 + dt / 0.15) : Math.max(0, g0 - dt / 0.15);
      busy = true;
    }
    if (window.__fxTrace) window.__fxTrace.push([now, shown, target, !!intro, FX.gate.cursor]);   // test hook (off unless set)
    const key = `${shown.toFixed(5)}|${FX.gate.cursor.toFixed(3)}|${FX.gate.press}`;
    if (key !== lastDrawn) { lastDrawn = key; render(shown); }
    updateCaptions(shown, false);
    if (navOn) {
      if (!intro && !navIn) navReveal();              // the rail draws in once the arrival has handed over
      if (navTick(shown, dt, false)) busy = true;
    }
    if (busy) raf = requestAnimationFrame(tick);
  }
  window.addEventListener("scroll", wake, { passive: true });

  /* ---------------- anchors: a jump lands on the beat's readable frame (the loop dips the stage if it's far) ---------------- */
  const ANCHOR = { top: "make", how: "look", pricing: "price", download: "end" };
  function jumpTo(id) {
    const beat = ANCHOR[id];
    const y = id === "top" ? 0 : scrollForBeat(beat);
    if (y == null) return false;
    navScrollTo(y);
    return true;
  }
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a || !TL || !motion()) return;
    const id = a.getAttribute("href").slice(1);
    if (!(id in ANCHOR) || !TL.beats.includes(ANCHOR[id])) return;   // not in the story (phones: a page section): native
    e.preventDefault();
    if (jumpTo(id)) { try { history.replaceState(null, "", "#" + id); } catch (err) { /* file:// */ } }
  });
  // focus that reaches an idle caption (a screen reader's cursor) brings that beat up, so focus is never invisible
  capsEl.addEventListener("focusin", (e) => {
    if (!TL || !motion()) return;
    const c = e.target.closest && e.target.closest(".beat-copy");
    if (!c || c.classList.contains("is-on")) return;
    const beat = c.getAttribute("data-copy");
    const y = beat === "make" ? 0 : scrollForBeat(beat);
    if (y != null) navScrollTo(y);
  });

  /* ---------------- start, refresh (theme / layout / motion preference / late fonts), resize, teardown ---------------- */
  let layoutKey = "";
  const key = () => `${theme()}|${desktop() ? "desk" : "phone"}|${preset()}|${motion() ? "motion" : "calm"}`;
  const navType = () => { try { return performance.getEntriesByType("navigation")[0].type; } catch (e) { return "navigate"; } };
  function teardown() {
    // everything the story put on the page goes: the mounts, the page-level layers' styles, the global classes, the
    // dip, pending frames and timers (the stacked page must not inherit any of it)
    cancelAnimationFrame(raf); raf = 0;
    clearTimeout(capTimer);
    intro = null; dip = null; held = false;
    clearStage();
    TL = null; MAP = null; OV = null; L = null;
    lastG = {}; curSeg = -1; lastDrawn = null; capIdx = -1;
    doc.classList.remove("on-band", "past-band");
    pin.setAttribute("class", "pin");
    pin.style.removeProperty("opacity");
    clearDip();
    pin.style.removeProperty("--cap-top");
    for (const v of fitVars) pin.style.removeProperty(v);
    fitCapH = -1;
    if (capRO) capRO.disconnect();
    for (const [el, props] of [[field, ["opacity", "clip-path"]], [shade, ["opacity"]], [band, ["display", "clip-path"]],
      [stageCol, ["opacity", "visibility"]], [stageWrap, ["transform"]], [track, ["height"]]]) for (const p of props) el.style.removeProperty(p);
    label.removeAttribute("data-mode");
    label.style.removeProperty("transform");
    FX.gate.cursor = 1; FX.gate.press = 1;
    navTeardown();
    placeCopies([]);
  }
  // keep: a snapshot of where the story is (refresh), restored onto the rebuilt timeline
  function start(firstLoad, keep) {
    try {
      cancelAnimationFrame(raf); raf = 0;
      layoutKey = key();
      if (!motion()) { teardown(); doc.classList.add("fx-ready"); return; }
      if (desktop()) placeCopies(BEATS);
      else if (preset() === "tall") placeCopies(PHONE_BEATS, true);
      else placeCopies(PHONE_BEATS);
      if (capRO) {
        capRO.disconnect();
        if (preset() === "tall") for (const b of TALL_BEATS) { const c = capFor(b); if (c) capRO.observe(c); }
      }
      build();
      navBuild();
      const h = location.hash.slice(1);
      const anchored = firstLoad && h in ANCHOR && TL.beats.includes(ANCHOR[h]);
      if (anchored) window.scrollTo(0, h === "top" ? 0 : scrollForBeat(ANCHOR[h]));
      else if (keep && keep.past != null && TL.p === "tall") keepPast(keep.past);   // (phones: below the story, stay there)
      else if (keep && !keep.intro) anchorScroll(keep.tp);      // the same story time under the new map: nothing moves
      target = mapScroll(window.scrollY);
      readerY = window.scrollY;
      held = false;
      if (dip) { dip = null; clearDip(); }
      intro = null; shown = target; vel = 0; dirSign = 1; FX.gate.cursor = 1;
      if (keep) {
        const pl = placeIn(keep.id, keep.u);
        if (pl) { shown = clamp(pl.sg.T0 + pl.u, pl.sg.T0, pl.sg.T1); vel = keep.vel; }
        intro = keep.intro;                            // still arriving: it carries on, on its own clock
        FX.gate.cursor = keep.cursor; dirSign = keep.dirSign;
      } else if (firstLoad && !anchored && window.scrollY < 4 && navType() === "navigate") {
        // a fresh arrival (not an anchor, a reload or a history visit: those land on their frame, never replaying)
        intro = { t0: FX.now(), rate: 1, y0: window.scrollY };
        shown = 0; vel = 1;
      }
      dirAnchor = target;
      gateTo = dirSign > 0 ? 1 : 0; FX.gate.press = gateTo;
      curSeg = -1; lastDrawn = null; capIdx = -1;
      render(shown);
      updateCaptions(shown, true);
      navTick(shown, 0, true);
      if (!intro) navReveal();                          // an anchor, a reload or a rebuild: the rail is up at once
      doc.classList.add("fx-ready");
      wake();
    } catch (err) {
      doc.classList.remove("motion", "calm");
      try { teardown(); } catch (e) { /* ignore */ }
      console.warn("The story fell back to its static layout:", err);
    }
  }
  function snapshot() {
    if (!TL) return null;
    const sg = TL.segs[segAt(shown)];
    return { id: sg.id, u: shown - sg.T0, vel, intro: intro ? { ...intro } : null, cursor: FX.gate.cursor, dirSign, tp: targetPlace(), past: pastStory() };
  }
  // a rebuild that keeps the story where it is: the same segment and local time, the follower's speed, the arrival
  // (if it's still playing) and the direction gate. The map is rebuilt; the scroll position is untouched.
  function refresh() { start(false, snapshot()); }
  let resizeT = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeT);
    resizeT = setTimeout(() => {
      // (round D: a rotation can cross the short-touch line; the reader keeps their place across it)
      const pl = readingPlace();
      if (syncMode()) { refresh(); restorePlace(pl); return; }
      if (key() !== layoutKey) { refresh(); return; }
      if (!TL) return;
      // phones (Sol mobile P2): the browser's bars showing or hiding change the height only, by less than ~150 px. The
      // pin and the map both use the stable 100svh, so there is nothing to re-lay or re-anchor; a width (orientation)
      // change or a real height change still lays out again.
      if (TL.p === "tall" && window.innerWidth === sizeW && Math.abs(window.innerHeight - sizeH) < 150) return;
      relayoutChecked();
    }, 140);
  });
  // (also a pinned caption's own resize, capCheck: it can fire before the window's debounced one, so it must refit the stage too)
  function relayoutChecked() {
    if (TL.p === "tall") fitPhone();
    const s0 = L ? L.s : 0;
    // phones: a new canvas scale changes the tables' compensated text (--demo-scale): remeasure the pieces too
    if (TL.p === "tall" && s0 && Math.abs(stage.clientWidth / TL.W - s0) > s0 * 0.004) { refresh(); return; }
    relayout();
  }
  function relayout() {
    const tp = intro ? null : targetPlace();
    const past = pastStory();
    layout();
    // the story stays where it is: the scroll position follows the new map (and the follower keeps its state)
    // (phones, Sol mobile pA P2: only a reader inside the pinned story is anchored to story time; one below it keeps
    // their place among the page's sections, the same distance past the story's end: no jump back into Chase)
    if (past != null) keepPast(past);
    else anchorScroll(tp);
    target = mapScroll(window.scrollY);
    lastDrawn = null;
    render(shown);
    wake();
  }
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  // (round D) a short touch screen gets the stacked beats, as reduced motion does (index.html's head script decides it
  // first, before the first paint; this is the same test). Touch only, so desktop windows never change. The small
  // viewport (100svh) ignores the browser bars showing and hiding, so only a rotation or a real resize flips it.
  const SHORT_TOUCH = 600;
  const coarse = window.matchMedia("(pointer: coarse)");
  const shortTouch = () => { try { return coarse.matches && (cssPx("100svh") || window.innerHeight) < SHORT_TOUCH; } catch (e) { return false; } };
  // true when the mode changed (the caller refreshes); on a resize, a page that fell back to its static layout (no
  // motion, no calm class) stays there (a change of the motion preference sets the mode, as it always did)
  function syncMode(force) {
    if (!force && !doc.classList.contains("motion") && !doc.classList.contains("calm")) return false;
    const short = !mq.matches && shortTouch(), calm = mq.matches || short;
    doc.classList.toggle("short-touch", short);
    if (calm === doc.classList.contains("calm") && !calm === doc.classList.contains("motion")) return false;
    doc.classList.toggle("calm", calm); doc.classList.toggle("motion", !calm);
    return true;
  }
  // (Sol round D P2) a mode change (motion <-> stacked: a rotation across the short-touch line, the motion preference)
  // keeps the reader's place: the story beat they were reading, or the section under the header. Taken BEFORE the
  // classes flip (the stacked sections appear at once), applied after the rebuild.
  function readingPlace() {
    const hb = header ? header.getBoundingClientRect().bottom : 0;
    if (TL && motion() && pastStory() == null && window.scrollY >= storyTop - 1) {
      const b = TL.beats[capIdx] || (window.scrollY < storyTop + 4 ? "make" : null);
      if (b) return { beat: b };
    }
    for (const el of document.querySelectorAll(".beat:not(.is-moved), .site-footer")) {
      const r = el.getBoundingClientRect();
      if (r.height > 0 && r.top <= hb + 1 && r.bottom > hb + 1) {
        const b = el.classList.contains("beat") ? el.dataset.beat : null;
        return b && PHONE_BEATS.includes(b) ? { beat: b } : { el, off: r.top };
      }
    }
    return null;
  }
  function restorePlace(pl) {
    if (!pl) return;
    const hb = header ? header.getBoundingClientRect().bottom : 0;
    let y = null;
    if (pl.el && pl.el.isConnected) y = window.scrollY + pl.el.getBoundingClientRect().top - pl.off;
    else if (pl.beat && TL && motion()) y = pl.beat === "make" ? 0 : scrollForBeat(pl.beat);
    else if (pl.beat) {
      // (F1: the phone story's start caption is the hero's own CTA block; stacked, that is the hero section)
      const sec = $(`.beat[data-beat="${pl.beat === "start" ? "make" : pl.beat}"]`);
      if (sec) y = window.scrollY + sec.getBoundingClientRect().top - hb;
    }
    if (y == null) return;
    y = Math.max(0, Math.round(y));
    window.scrollTo(0, y);
    readerY = window.scrollY;
    if (TL && motion()) {
      target = shown = mapScroll(window.scrollY); vel = 0; intro = null;
      lastDrawn = null; capIdx = -1;
      render(shown); updateCaptions(shown, true); navTick(shown, 0, true);
    }
  }
  const onMq = () => { const pl = readingPlace(); syncMode(true); refresh(); restorePlace(pl); };
  if (mq.addEventListener) mq.addEventListener("change", onMq);
  if (coarse.addEventListener) coarse.addEventListener("change", onMq);
  // the fonts measure every piece: wait for them (up to 1.8 s); if they land after that, remeasure in place
  const fontsLoaded = Promise.all(['400 14px "Inter"', '600 14px "Inter"', '700 14px "Inter"'].map((f) => document.fonts.load(f)))
    .then(() => document.fonts.ready);
  Promise.race([fontsLoaded.then(() => "fonts", () => "fonts"), new Promise((r) => setTimeout(() => r("timeout"), 1800))])
    .then((why) => {
      start(true);
      if (why === "timeout") fontsLoaded.then(() => { if (TL) refresh(); }, () => { /* no fonts: keep the fallback */ });
    });

  /* ---------------- test hooks (headless checks): pure seeks of the master, the map, the follower's state ---------------- */
  window.__site = {
    mounts,
    get TL() { return TL; },
    seekMaster(T) {
      held = true; intro = null; dip = null; clearDip();
      shown = target = T; vel = 0;
      render(T);
      updateCaptions(T, true);
      navReveal();
      navTick(T, 0, true);
      return T;
    },
    release() { held = false; wake(); },
    map() {
      return {
        T0: 0, T1: TL.T1, H: TL.HOLD, desktop: TL.isDesk, preset: TL.p, scrollLen: Math.round(MAP.L), storyTop: Math.round(storyTop),
        segs: TL.segs.map((s) => ({ id: s.id, kind: s.kind, T0: +s.T0.toFixed(3), T1: +s.T1.toFixed(3) })),
        beats: TL.beats, switches: TL.switches.map(([b, t]) => [b, +t.toFixed(3)]),
        pieces: MAP.pieces.map((p) => ({ kind: p.kind, beat: p.beat, s0: Math.round(p.s0), s1: Math.round(p.s1), T0: +p.T0.toFixed(3), T1: +p.T1.toFixed(3) })),
      };
    },
    scrollFor(beat) { return scrollForBeat(beat); },
    mapScroll(y) { return mapScroll(y); },
    state() { return { shown, target, vel, beat: TL ? TL.beats[capIdx] : null, intro: !!intro, dip: !!dip, gate: { ...FX.gate }, dirSign }; },
    pinEl() { return pin; },
    nav() {
      return { on: navOn, in: navIn, active: navA, beat: navCP[navA] ? navCP[navA].b : null, p: navP, h: navH, y: navY, tip: navTipK,
        band: !!(nav && nav.classList.contains("on-band")),
        ticks: navCP.map((c) => ({ b: c.b, w: parseFloat(c.w) || 0, f: parseFloat(c.fw) || 0, start: +c.start.toFixed(3), anchor: +c.anchor.toFixed(3) })) };
    },
    setGate(c, p) { FX.gate.cursor = c; FX.gate.press = p; gateTo = c; lastDrawn = null; },
    follow(e, v, dt) { return follow(e, v, dt); },
    refresh() { refresh(); },
  };
})();
