/* =====================================================================================================================
   The page (site v2.1): ONE story driven by scroll (vault "Motion House Style — One Shape (Light)" § 10).
   - One master timeline: Make -> [seam] -> Look -> [seam] -> Know -> [seam] -> Grow -> the Ride -> Chase -> [seam] ->
     Yours -> [seam] -> Price -> [seam] -> Brand. Every piece and seam is a pure function of its time, so scrolling back
     plays the story backwards (scrub, never replay).
   - Checkpoints (C3, docs/interaction-contract.md): one gesture = one page. A wheel gesture, swipe or step key plays the
     seam into the next checkpoint at its designed speed, then that chapter's content, and the story rests on its key
     frame; back is a 220 ms fade; far moves are one 220 ms dip. Scroll never scrubs the timeline. A tall track under a
     sticky pin holds one viewport per checkpoint; a foreign scroll (a scrollbar drag, an anchor) settles on the nearest.
     ONE rAF loop that sleeps when there is nothing to do.
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
  // (2026-10-12, Daniel: "one button, not a slider pill") one toggle, [data-theme-toggle], the audio pages' button; the
  // head script picks the first theme (#dark / #light, then fe-theme, then fe-theme-visit, else dark)
  const theme = () => (doc.getAttribute("data-theme") === "light" ? "light" : "dark");
  // BOTH theme-color metas (the dark- and light-scheme ones) follow the page theme, whatever the OS scheme is
  function syncSwitch() {
    const c = theme() === "dark" ? "#080a0f" : "#f3f3f0";
    for (const m of $$('meta[name="theme-color"]')) m.setAttribute("content", c);
  }
  // FETheme (assets/shared/theme.js, A5) owns the switch: data-theme, fe-theme, the #dark/#light read (home never writes
  // a hash) and the circle reveal. "fe:themechange" fires INSIDE the view-transition update; an instant switch (no
  // circle) rebuilds the scenes there, a circle reveal rebuilds them just after the circle starts (themeRebuild, C5b)
  document.addEventListener("fe:themechange", () => { syncSwitch(); themeRebuild(); });
  // the circle plays only where the story is in motion (not on short touch phones): to give those the circle too,
  // flip this one line to `{ from: b }` (A8 html.motion gate)
  const revealOpts = (b) => (motion() ? { from: b } : undefined);
  FETheme.init({ hashPolicy: "home", toggle: "[data-fe-no-auto-toggle]" });   // we bind the toggle ourselves, below
  document.addEventListener("click", (e) => {
    const b = e.target.closest && e.target.closest("[data-theme-toggle]");
    if (b) FETheme.set(FETheme.target() === "light" ? "dark" : "light", revealOpts(b));
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
  // (phones, F2b, Sol F2 #2) the offer copy rides the overlay's card, so it dips with it (a filter, which multiplies with
  // its own caption fade): no text ever outlives its card on a long jump
  const dipCopy = () => (TL && TL.p === "tall" && TL.offerSw && copy.end && copy.end.parentNode === capsEl ? copy.end : null);
  function setDip(a) {
    for (const el of [stageWrap, over]) if (el) { if (a >= 0.999) el.style.removeProperty("opacity"); else el.style.opacity = a.toFixed(3); }
    const c = dipCopy();
    if (c) { if (a >= 0.999) unDipCopy(); else c.style.filter = `opacity(${a.toFixed(3)})`; }
  }
  function unDipCopy() {
    const c = copy.end;
    if (!c || !c.style.filter) return;
    c.style.removeProperty("filter");
    if (c.getAttribute("style") === "") c.removeAttribute("style");
  }
  function clearDip() { for (const el of [stageWrap, over, band]) if (el) el.style.removeProperty("opacity"); unDipCopy(); dropXf(); }
  // FLICKER2 / FADEDEF (Daniel 2026-10-17: "when on a page then pausing for a few seconds then scrolling again" it
  // flickered; he picked the crossfade: "fade feels smoothest"): a gesture during a chapter's content with more than
  // CONTENT_FINISH_MAX left (decision #13) holds the content's frame as a still copy over the stage and crossfades it
  // onto the chapter's rest frame underneath, never through dark (no frame darker than the two pictures it blends);
  // the seam starts when the crossfade ends.
  const XF_DUR = 0.22;
  let xf = null;                                        // the held content frame: {t0, dur, el}
  function dropXf() { if (xf) { xf.el.remove(); xf = null; } }
  function holdFrame(t) {
    dropXf();
    const el = stageWrap.cloneNode(true);
    // ids stay (Sol FLICKER2-1 #1: id rules style the stage, e.g. Make's #invoice-form): the copy comes after the stage
    // in document order, so every id lookup still finds the live one, and it is inert and gone within XF_DUR
    for (const n of [el, ...el.querySelectorAll("[data-stage]")]) n.removeAttribute("data-stage");
    el.setAttribute("aria-hidden", "true");
    el.inert = true;
    Object.assign(el.style, { position: "absolute", left: `${stageWrap.offsetLeft}px`, top: `${stageWrap.offsetTop}px`,
      width: `${stageWrap.offsetWidth}px`, height: `${stageWrap.offsetHeight}px`, margin: "0", pointerEvents: "none" });
    stageWrap.after(el);
    xf = { t0: t, dur: XF_DUR, el };
  }
  function xfStep(now) {
    const a = 1 - (now - xf.t0) / xf.dur;
    if (a <= 0) dropXf(); else xf.el.style.opacity = a.toFixed(3);
  }
  // C5 (test_dip_fades_band) a dip whose cut turns the Ride's band on or off (a jump into or out of Email) fades the band
  // with the stage: left alone it flipped the whole pin's colour in one frame at the dark frame. A dip that stays inside
  // the band (or outside it) leaves the band put, as v2.1 asked. The band's state is the timeline's, at a story time.
  function bandOnAt(T) {
    if (!TL) return false;
    const sg = TL.segs[segAt(clamp(T, 0, TL.T1))];
    const G = sg.kind === "seam" && sg.seam.globals ? sg.seam.globals(T - sg.T0) : sg.G;
    return (G.band || 0) > 0;
  }
  function dipBand(a) {
    // (Sol C5-1 #3) the cut's own target, as cut() will take it: a skip stays on its origin's rest unless dest is >= 2 away
    const entry = dip.mode === "entry" || (dip.mode === "skip" && Math.abs(kD - kR) >= 2);
    const k = entry ? kD : dip.k;
    const to = bandOnAt(dip.cut ? shown : RE[k] ? RE[k][entry ? 0 : 1] : shown);
    if (dip.band0 !== to && a < 0.999) band.style.opacity = a.toFixed(3); else band.style.removeProperty("opacity");
  }
  const nav = $(".story-nav");
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
  // hero's own copy (real DOM, moved, never cloned) is the MAKE caption: an aria-hidden "01" and the h1, full size over
  // the full stage through all of Make. (F1c, Daniel 2026-10-10: "i want this button options and stuff to not be so
  // early in the website experience — prolly at the very end": the opening has no CTA block and no step-back; see
  // ctaEnd below.)
  // (F2, Daniel: "i like the your data but i also want it to end with a call to action") the phone story then goes on
  // Chase -> Yours (the folder card) -> the offer card: "yours" is an aria-hidden visual clone of the first trust item
  // (the section itself follows the pin), "end" is the End section's own copy, moved into the pin
  const TALL_BEATS = ["make", "look", "know", "grow", "chase", "yours", "end"];
  const TALL_PIN = [...PHONE_BEATS, "end"];
  // the captions under the stage (the caption budget): the offer card is centred in the full pin with the stage gone
  const CAP_EXCL = ["end"];
  // the end hold (story s): its length, and where the map's readable rest starts before the timeline's end. The map's
  // last frame is T1 + 0.01 (rendered as T1, a still), so the very end of the timeline is a scroll position too.
  // END_K: the shown time over which FX.story.endK goes 0 -> 1, from the end hold's start (T1 - 0.02) to T1 - 0.005,
  // halfway into the hold: it is exactly 1 well before the pin lets go, so a follower still settling by a hair never
  // leaves the section after the pin part-faded
  const END_HOLD = 0.06, END_REST = 0.02, END_K = 0.015;
  // the phone story's Make caption: the hero's own h1 with an aria-hidden chapter name ("New invoice") in front (removed whenever the phone
  // story is not running)
  let stepEl = null;
  function heroSplit(on) {
    const hc = copy.make;
    if (!hc) return;
    if (on) {
      if (!stepEl) {
        stepEl = document.createElement("span");
        stepEl.className = "step";
        stepEl.setAttribute("aria-hidden", "true");
        stepEl.textContent = "New invoice";
      }
      if (stepEl.parentNode !== hc) hc.insertBefore(stepEl, hc.firstChild);
    } else if (stepEl && stepEl.parentNode) stepEl.remove();
  }
  // (F1c, Daniel 2026-10-10: the CTA "at the very end") on a phone (the phone story, and the stacked page on a phone:
  // < 640 px, or a short touch screen such as a phone in landscape) the hero is the headline alone and everything that
  // asks for action is in the End copy, the offer card: the hero's sub line goes in under its headline, and the tour link
  // after its fine print, so the End's own CTA row, its trial line and its mobile note stay one adjacent block. The
  // hero's own CTA row, trial line and fine print leave the page (one Share/Copy button on the phone page). Real DOM,
  // moved, never cloned; everything goes back to its exact original place whenever this is off (laptops, tablets, no JS).
  let ctaParts = null;
  const calmPhone = () => doc.classList.contains("calm") && (window.innerWidth < 640 || shortTouch());
  function ctaEnd(on) {
    const hc = copy.make, ec = copy.end;
    if (!hc || !ec) return;
    if (on && !ctaParts) {
      const row = $(":scope > .cta-row", hc), tour = row && $(":scope > [data-tour-link]", row);
      const sub = $(":scope > .sub", hc), dis = $(":scope > .disclose.strong", hc), fine = $(":scope > .fine", hc);
      if (!row || !tour || !sub || !dis || !fine || !$(":scope > .cta-row", ec) || !$(":scope > .fine", ec)) return;
      // (in the order they leave; they come back in reverse, each before the node that followed it)
      ctaParts = [sub, tour, row, dis, fine].map((el) => ({ el, parent: el.parentNode, next: el.nextSibling }));
    }
    if (!ctaParts) return;
    const [sub, tour, ...rest] = ctaParts.map((p) => p.el);
    if (on) {
      const er = $(":scope > .cta-row", ec), ef = $(":scope > .fine", ec);
      if (sub.parentNode !== ec || sub.nextElementSibling !== er) ec.insertBefore(sub, er);
      if (tour.parentNode !== ec || tour.previousElementSibling !== ef) ec.insertBefore(tour, ef.nextSibling);
      for (const el of rest) if (el.parentNode) el.remove();
      return;
    }
    if (sub.parentNode === hc && tour.parentNode === ctaParts[1].parent && rest.every((el) => el.parentNode === hc)) return;
    for (let k = ctaParts.length - 1; k >= 0; k--) {
      const p = ctaParts[k];
      p.parent.insertBefore(p.el, p.next && p.next.parentNode === p.parent ? p.next : null);
    }
  }
  // each beat's copy lives in its home section (calm, no JS, the phone's late beats) or in the pin as a caption
  // (split: the phone story's hero split above)
  let lastPlace = null, ctaWait = null, ctaWaited = false;
  function placeCopies(inPin, split = false) {
    lastPlace = [inPin, split];
    // (F1c, Sol F1c #4) the calm phone page's hero is the headline alone too: its "01" as well, before the 02-05 below
    heroSplit(split ? inPin.includes("make") : !inPin.length && calmPhone());
    // (F1c: before the captions' tab order is set below, so the moved controls get the End copy's)
    // (Sol F1c #1, r2) the hero's download row leaves the page only once download.js has wired it (its DOMContentLoaded
    // init sets data-campaign-resolved): on any earlier start, resize or mode change it stays put, and one re-placement
    // runs after that init (plus a task), so the row a tablet or laptop puts back is always a wired one
    const toEnd = split ? inPin.includes("end") : !inPin.length && calmPhone();
    // (Sol F1c r3, r4) while it waits, html.cta-pending keeps that block hidden (site.css). The re-placement keeps the
    // reader exactly where they are: the timeline's own snapshot (refresh), or on the stacked page the first section
    // still on screen held at the same height. It waits once: if download.js never ran, the block is moved anyway (its
    // plain links still work) and nothing waits or hides again.
    if (toEnd && !ctaParts && !ctaWaited && !document.body.hasAttribute("data-campaign-resolved")) {
      doc.classList.add("cta-pending");
      // (no marker yet means download.js, a deferred script, has not run, so DOMContentLoaded is still to come even at
      // readyState "interactive"; the load event covers a download.js that never runs)
      if (!ctaWait) ctaWait = new Promise((r) => {
        const go = () => setTimeout(r, 0);
        if (document.readyState === "complete") { go(); return; }
        document.addEventListener("DOMContentLoaded", go, { once: true });
        window.addEventListener("load", go, { once: true });
      }).then(() => {
        ctaWaited = true;
        doc.classList.remove("cta-pending");
        if (TL) { refresh(); return; }
        const anchor = [...document.querySelectorAll("section")].find((s) => s.getBoundingClientRect().bottom > 0);
        const y0 = anchor ? anchor.getBoundingClientRect().top : 0;
        placeCopies(...lastPlace);
        if (anchor && window.scrollY > 0) window.scrollBy(0, anchor.getBoundingClientRect().top - y0);
      });
    } else {
      if (!toEnd) doc.classList.remove("cta-pending");  // (Sol F1c r5) a layout that keeps the block in place shows it
      ctaEnd(toEnd);
    }
    let moved = false;                                // once one caption moves in, the later ones follow it (story order)
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
      // (phones, F2b, Sol F2 #5) the phone story ends on the offer card, with no mark on the stage: no stage description
      if (want && split && b === "end") { if (sr) sr.remove(); sr = null; }
      else if (want && !sr) {
        sr = document.createElement("p");
        sr.className = "visually-hidden sr-stage";
        sr.textContent = STAGE_ARIA[b];
        c.appendChild(sr);
      }
      if (!want && sr) sr.remove();
      capActive(c, !want);                             // in the pin: idle until its beat is up; at home: ordinary
    }
    // (the phone story rode the headline's top: once it's back home, not even an empty style attribute is left)
    if (stepEl && !split && copy.make.getAttribute("style") === "") copy.make.removeAttribute("style");
    // (phones, F2) the Yours caption sits before the offer card's copy; the Yours section follows the pin (is-after-pin)
    const ending = split && inPin.includes("end") && copy.end && copy.end.parentNode === capsEl;
    const yc = ending ? yoursCapEl() : yoursCap;
    if (yc) {
      yc.classList.remove("is-on", "is-off", "is-idle");
      if (ending) { if (yc.parentNode !== capsEl || yc.nextSibling !== copy.end) capsEl.insertBefore(yc, copy.end); }
      else if (yc.parentNode) yc.remove();
    }
    if (home.yours) {
      home.yours.sec.classList.toggle("is-after-pin", !!ending);
      if (!ending) { home.yours.sec.style.removeProperty("--end-k"); if (home.yours.sec.getAttribute("style") === "") home.yours.sec.removeAttribute("style"); }
    }
  }
  // (phones, F2) the Yours caption: a visual clone of the first trust item's folder icon and title ("Your files stay
  // with you."), aria-hidden with nothing focusable; the real one is read in the Yours section after the pin. (Its body
  // line is longer than Chase's: it would become the caption budget and shrink the stage.)
  let yoursCap = null;
  function yoursCapEl() {
    if (yoursCap) return yoursCap;
    const li = copy.yours && $(".trust li", copy.yours);
    if (!li) return null;
    yoursCap = document.createElement("div");
    yoursCap.className = "beat-copy yours-cap";
    yoursCap.setAttribute("data-copy", "yours-cap");
    yoursCap.setAttribute("aria-hidden", "true");
    for (const s of [".ic", "h3"]) { const e = $(`:scope > ${s}`, li); if (e) yoursCap.appendChild(e.cloneNode(true)); }
    return yoursCap;
  }
  // the caption element a beat shows in the pin
  const capFor = (b) => (b === "yours" && yoursCap && yoursCap.parentNode === capsEl ? yoursCap
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
  // (R2: round B2's one-grid rule, captions on the stage's edges, is retired on phones for a wider stage; the captions
  // sit on the page's text column like every section below the story. F1: the story pins from the first frame, so the
  // Make caption is in the budget like every other caption.)
  const fitVars = ["--stage-w", "--stage-top"];
  // the caption budget: the tallest pinned caption among the phone beats, less any excluded (CAP_EXCL: the start
  // caption and the offer card, which are not under the full stage)
  function capBudget(exclude = []) {
    let h = 0;
    for (const b of TALL_BEATS) { if (exclude.includes(b)) continue; const c = capFor(b); if (c) h = Math.max(h, c.offsetHeight); }
    return h;
  }
  let fitCapH = -1;
  function fitPhone() {
    if (preset() !== "tall") { for (const v of fitVars) pin.style.removeProperty(v); fitCapH = -1; return; }
    const ph = pin.clientHeight, cw = stageCol.clientWidth;
    const safe = cssPx("env(safe-area-inset-bottom, 0px)");
    // (R2, Daniel 10-10 "make the bounds … a bit wider if the space feels cramped") the captions keep the full text
    // column (the page's 16 px gutters) instead of narrowing to the stage's edges: a narrower caption wrapped taller and
    // took that height from the stage (393 x 640: Chase's caption on 4 lines, a 301 px stage). At full width the
    // tallest caption is as short as it gets, so the stage is the widest the height allows, in one pass.
    const capH = capBudget(CAP_EXCL);   // (F2: the offer card is centred in the pin, outside the budget)
    const room = ph - safe - FIT_TOP - FIT_BOT - LABEL_ROW - LABEL_GAP - capH;
    const w = Math.max(120, Math.floor(Math.min(cw, (room * 5) / 6)));
    fitCapH = capH;
    const free = Math.max(0, ph - safe - ((w * 6) / 5 + LABEL_ROW + LABEL_GAP + capH));
    const top = Math.max(FIT_TOP, Math.round(free * 0.42));
    pin.style.setProperty("--stage-w", `${w}px`);
    pin.style.setProperty("--stage-top", `${top}px`);
  }
  // (F1) a caption that changes height on its own (late fonts; a share status line if its reserved line ever stopped
  // holding it) refits the stage when it changes the budget; the reserved status line means a share never does
  const capRO = "ResizeObserver" in window ? new ResizeObserver(() => { if (!capRaf) capRaf = requestAnimationFrame(capCheck); }) : null;
  let capRaf = 0, fitEndH = -1;
  const endCopyH = () => (copy.end && copy.end.parentNode === capsEl ? copy.end.offsetHeight : 0);
  function capCheck() {
    capRaf = 0;
    if (!TL || TL.p !== "tall" || fitCapH < 0) return;
    // (F2: the offer card is measured on the End copy's own box, so a change in its height re-lays the card too)
    if (capBudget(CAP_EXCL) === fitCapH && endCopyH() === fitEndH) return;
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
  let TL = null, OV = null, L = null;
  let ovCard = null, ovInk = null, ovMark = null;
  function clearStage() {
    for (const m of Object.values(mounts)) m.rootEl.remove();
    for (const k of Object.keys(mounts)) delete mounts[k];
    for (const l of $$(".fx-seam", stage)) l.remove();
    over.innerHTML = "";
    ovCard = ovInk = ovMark = null;
  }
  const mountNames = (isDesk, p) => (isDesk ? ["make", "look", "know", "grow", "chase", "yours"] : p === "tall" ? [...PHONE_BEATS, "yours"] : PHONE_BEATS);
  // pre: the scenes a theme rebuild already mounted in the new theme (themeRebuild), adopted when they were built for
  // this same stage (preset and scale); otherwise they go and the scenes mount here, as always
  function build(pre) {
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
    const names = mountNames(isDesk, p);
    // (Sol C5b-1 MEDIUM) the very same scenes, no more: a spare one would stay on the stage unregistered
    const fits = pre && pre.p === p && pre.s0 === s0 && pre.dark === dark && names.length === Object.keys(pre.m).length && names.every((n) => pre.m[n]);
    if (pre && !fits) for (const m of Object.values(pre.m)) m.rootEl.remove();
    for (const n of names) mounts[n] = fits ? pre.m[n] : mount(n, p, s0);
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
      // (phones) Make in two segments, to its arrival hold and on from it (the map's place ids, kept across F1c: the
      // start still and the stage's step-back for the hero's CTA block are gone with the block)
      scene("make", M.make, 0, M.make.inst.HOLD, GBASE);
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
      // C5 (DEC-8: cut dead time, never motion speed) Yours is still after its rest (START + 0.28) and Price after its
      // rest (T0 + 0.3): each now ends 0.02 s after its rest, so the next move starts on the gesture
      scene("yours", M.yours, M.yours.inst.START, FX.trim(false) ? M.yours.inst.START + 0.3 : M.yours.inst.END, GBASE);
      seam("yoursPrice", S.yoursPrice, M.yours, null);
      hold("price", FX.trim(false) ? 0.32 : 0.6, { ...GBASE, stage: 0, card: { from: "price", k: 1 } });
      seam("priceBrand", S.priceBrand, null, null);
      hold("brand", 1.0, { ...GBASE, stage: 0, mark: 1 });
    } else if (p === "tall") {
      // (phones, F2) Chase -> Yours (the Ride mirrored: the band draws back, the Recent card files into the Data storage
      // card), the folder card, then Yours -> Offer: the card leaves the stage and becomes the offer card in the full
      // pin (the End section's copy), and the story rests on it before the pin lets go
      seam("chaseYours", S.chaseYours, M.chase, M.yours);
      scene("yours", M.yours, M.yours.inst.START, M.yours.inst.END, GBASE);
      seam("yoursOffer", S.yoursOffer, M.yours, null);
      hold("end", END_HOLD, { ...GBASE, stage: 0, card: { from: "yours", to: "offer", k: 1 } });
    }
    // SCRUB (Daniel 2026-10-18, PHONE-options option 1): phones (and touch tablets) run the live site's scroll scrub, the
    // stage following the finger; desktop (and a fine-pointer tablet window) keeps the checkpoints. Decided per build.
    const scrubOn = p === "tall" || (SCRUB_TABLET && !isDesk && coarse.matches);
    TL = { segs, T1: T, HOLD: M.make.inst.HOLD, isDesk, p, W, H, dark, scrub: scrubOn };
    const seg = (id) => segs.find((s) => s.id === id);
    TL.seg = seg;
    // captions: the beat that starts at each switch time (the outgoing caption leaves, then the incoming arrives)
    // (the Ride: "Watch it add up." stays through the dive, leaves as the colour floods out, and "Follow up in two
    // clicks." arrives once the band is the whole page: one clean colour move, no text caught in it)
    const ride = seg("ride");
    // C5 (ICX-STEP.3, main 2026-10-16) wider stages: Look's caption arrives as Create's press lands (0.60 s after the
    // gesture at Make's hold), not 0.3 s into the hand-off (1.62 s dark): only the caption moves, no motion
    // (Sol C5-1 #1: a caption is ACTIVE 0.18 s after its switch, the 0.12 s hysteresis + the 0.06 s outgoing fade, so the
    // switch sits 0.04 s before the press: the caption is active 0.60 s after the gesture)
    const lookAt = p !== "tall" && FX.trim(false) ? seg("make").T0 + M.make.inst.B.pressCreate - 0.04 : seg("makeLook").T0 + 0.3;
    TL.switches = [["look", lookAt], ["know", seg("lookKnow").T0 + 0.22],
      ["grow", seg("knowGrow").T0 + 0.22], [null, ride.T0 + ride.seam.DIVE + 0.04], ["chase", ride.T1 - 0.08]];
    if (isDesk) {
      // (Chase -> Yours: the Chase caption leaves before the band draws back over it; Yours arrives once it's gone)
      // (and the overlay card never grows or shrinks under a caption: each side of it leaves first)
      TL.switches.push([null, seg("chaseYours").T0 + 0.06], ["yours", seg("chaseYours").T0 + 0.5],
        [null, seg("yoursPrice").T0 + 0.04], ["price", seg("yoursPrice").T0 + (seg("yoursPrice").seam.PRICE_IN ?? 0.5), 0.02],
        [null, seg("priceBrand").T0 + 0.04], ["note", seg("priceBrand").T0 + 0.4], ["end", seg("brand").T0 + 0.45]);
    } else if (p === "tall") {
      // (phones, F2: desktop's rules) Chase's caption leaves before the band draws back over it, Yours arrives once the
      // band is gone; the folder card never moves under a caption; the offer copy arrives once the card covers 98 % of
      // it (layout() measures that moment, TL.offerSw, on the real rects), with price's narrow 0.02 hysteresis
      const cy = seg("chaseYours"), yo = seg("yoursOffer");
      TL.offerSw = ["end", yo.T1, 0.02];
      // (F2d, Astra F2: a washed-out crossover) the Yours statement stays readable until the card lifts (LIFT), so a
      // readable element is up until the offer gives the eye its focal point
      TL.switches.push([null, cy.T0 + 0.06], ["yours", cy.T0 + 0.5], [null, yo.T0 + yo.seam.LIFT, 0.02], TL.offerSw);
    }
    TL.beats = ["make", ...TL.switches.map((s) => s[0])];
    // (A10, R5 A.2: G12 needs it where money adds up, not on Make's or Look's single invoice) "Fictional data" from the
    // START of Look -> Know (the first Know row is up 0.08 s into it, so the label is already there)...
    TL.labelData = seg("lookKnow").T0;
    // ...until the last money has left the stage (desktop, and the phone's own Chase -> Yours since F2)
    // (phones, F2d, Astra F2: the label retires WITH the dashboard it describes) the phone's Recent rows are gone at
    // chaseYours u 0.21 (SEAMS.chaseYours), so the label leaves at 0.24 instead of hanging under the card to 0.36
    // (A10: tablets have no Chase -> Yours; their pinned story ENDS on Chase's money, so their window ends on their own
    // timeline, at Chase's end, inclusive: the pin carries the labelled stage away; never an open-ended Infinity)
    const cyL = seg("chaseYours");
    TL.labelOff = cyL ? cyL.T0 + (p === "tall" ? 0.24 : 0.36) : seg("chase").T1;
    // (phones, F2d) from Chase -> Yours on, the stage's own box (its skin, its shade, the field in it) is gone: the band
    // and then the folder card are the one container on screen (site.css .pin.own)
    TL.ownAt = p === "tall" ? seg("chaseYours").T0 : Infinity;
    TL.late = isDesk ? seg("chaseYours").T0 + 0.3 : Infinity;
    // the page-level overlay (desktop, and phones since F2): the card that becomes the price card (phones: the offer
    // card), and (desktop) the real mark
    if (isDesk || p === "tall") {
      ovCard = div("ov-card", over);
      ovInk = div("fx-ink", ovCard);
    }
    if (isDesk) {
      ovMark = document.createElement("img");
      ovMark.src = "/assets/story/fe-mark.png";
      ovMark.alt = "";
      ovMark.className = "ov-mark";
      over.appendChild(ovMark);
    }
    // the Ride's colour (the October bar's own, near its top) is the band's and the field's
    const c = M.grow.inst.octColor(0.12);
    doc.style.setProperty("--ride", `rgb(${c.slice(0, 3).map(Math.round).join(",")})`);
    TL.ride = [c[0], c[1], c[2], 1];
    layout();
  }
  const beatAt = (T) => { let i = 0; for (const [, t] of TL.switches) if (T >= t) i++; return i; };
  const segAt = (T) => { const i = TL.segs.findIndex((s) => T <= s.T1 + 1e-9); return i < 0 ? TL.segs.length - 1 : i; };

  /* ---------------- layout: fit, the scroll map, every rect the frame path needs (measured here, never per frame) ---------------- */
  let storyTop = 0, kHero = 1, R0 = null, svhPx = 0, sizeW = 0, sizeH = 0;
  const CAP_GAP = 22;                                  // phones: the captions' clearance under the stage
  const YOURS_GAP = 36, OFFER_NEXT = 56, OFFER_RING = 8.5;               // (F2d) folder card -> its statement; offer card -> the next h2
  const LITE = (FX.PHONE_LITE = { y: 10, b: 28 });     // (F2d, Astra F2) the phone light theme: one soft card shadow
  function layout() {
    if (!TL) return;
    css(stageWrap, "transform", "none");
    if (TL.p === "tall") { label.style.removeProperty("transform"); if (copy.make) copy.make.style.removeProperty("top"); }
    const sw = stage.clientWidth, sh = stage.clientHeight, s = sw / TL.W;
    for (const m of Object.values(mounts)) { css(m.rootEl, "transform", `scale(${s.toFixed(5)})`); css(m.rootEl, "--demo-scale", String(s)); }
    for (const sg of TL.segs) if (sg.layer) { css(sg.layer, "transform", `scale(${s.toFixed(5)})`); css(sg.layer, "--demo-scale", String(s)); }
    const hh = header ? header.getBoundingClientRect().height : 64;
    storyTop = storyEl.getBoundingClientRect().top + window.scrollY - hh;
    const pr = pin.getBoundingClientRect(), wr = stageWrap.getBoundingClientRect();
    L = { sw, sh, s, hh, stageTop: wr.top - pr.top, stageH: wr.height, stageW: wr.width };
    // phones: the hero's copy sits under a smaller stage; every other caption under the full stage; both keep CAP_GAP
    // (phones < 640 px: the story pins from the first frame with the stage at full size; every caption sits under the
    // label row; the map's viewport is the pin's own stable 100svh, measured once per layout)
    sizeW = window.innerWidth; sizeH = window.innerHeight;
    svhPx = TL.p === "tall" ? cssPx("100svh") : 0;
    if (TL.p === "tall") {
      kHero = 1;
      L.capTop = Math.round(L.stageTop + L.stageH + LABEL_ROW + LABEL_GAP);
      pin.style.setProperty("--cap-top", `${L.capTop}px`);
      // (F2b) the Yours caption is one line (the folder icon and the title) under the caption budget's height: it sits
      // centred in the room between the stage and the pin's bottom margin, so the story's last chapter has no dead band
      // under it (the stage keeps its size; the caption only fades, never moves)
      if (yoursCap && yoursCap.parentNode === capsEl) {
        // (F2d, Astra F2: object and statement read as one composition) the caption sits YOURS_GAP under the folder card
        // itself (the stage's box is gone by then: .pin.own), not centred in the room under the stage
        const Y = mounts.yours && mounts.yours.inst.X.R;
        const bot = pr.height - cssPx("env(safe-area-inset-bottom, 0px)") - FIT_BOT;
        const cb = Y ? L.stageTop + (Y.cy + Y.h / 2) * s : L.stageTop + L.stageH;
        yoursCap.style.top = `${Math.round(Math.min(cb + YOURS_GAP, bot - yoursCap.offsetHeight))}px`;
      }
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
    } else if (TL.p === "tall" && ovCard && mounts.yours && copy.end && copy.end.parentNode === capsEl) OV = offerLayout(pr, wr);
    else OV = null;
    if (!OV || TL.isDesk) clearOfferVars();
    buildTrack();
    railMeasure();
    lastG = {};
    curSeg = -1;
  }

  // (phones, F2) the offer card: the End section's copy, centred in the full pin (its own padding is the card's), and the
  // overlay's two rects: the Data storage card where the stage shows it, and the offer card. Then the moment the copy
  // may arrive: the first u of Yours -> Offer from which the springing card covers >= 98 % of the copy's box (sampled
  // from the seam's own spring, so it holds at every phone size and in both themes).
  function clearOfferVars() {
    if (pin.style.getPropertyValue("--offer-top")) pin.style.removeProperty("--offer-top");
    const ys = home.yours && home.yours.sec;
    if (ys && ys.style.getPropertyValue("--offer-pull")) { ys.style.removeProperty("--offer-pull"); if (ys.getAttribute("style") === "") ys.removeAttribute("style"); }
    if (pin.style.clipPath) { pin.style.removeProperty("clip-path"); lastG.pinCut = ""; }
    for (const v of ["--offer-card-w", "--offer-card-h"]) if (storyEl.style.getPropertyValue(v)) storyEl.style.removeProperty(v);
    if (storyEl.getAttribute("style") === "") storyEl.removeAttribute("style");
  }
  function offerLayout(pr, wr) {
    const ec = copy.end, s = L.s;
    const safe = cssPx("env(safe-area-inset-bottom, 0px)");
    const eh = ec.offsetHeight;
    fitEndH = eh;
    const y = mounts.yours.inst.X;
    // (F2d, Astra F2: the storage card visibly becomes the offer card) the offer shares the folder card's centre, up to
    // where the old 46 % placement had it (a taller card is clamped to the pin's top margin)
    const ycy = (wr.top - pr.top) + y.R.cy * s;
    const top = Math.round(clamp(ycy - eh / 2, FIT_TOP, Math.max(FIT_TOP, (pr.height - safe - eh) * 0.46)));
    pin.style.setProperty("--offer-top", `${top}px`);
    // (F2d, Astra F2: ~190 px of empty page between the offer and the next heading as the pin lets go) the section after
    // the pin is drawn up under the pin's empty lower part, so its h2 is OFFER_NEXT under the card at release; the
    // release itself (storyEnd) does not move
    const ys = home.yours && home.yours.sec, h2 = ys && ys.querySelector("h2");
    if (h2) {
      const off = h2.getBoundingClientRect().top - ys.getBoundingClientRect().top;
      ys.style.setProperty("--offer-pull", `${Math.max(0, Math.round(pr.height - (top + eh) + off - OFFER_NEXT))}px`);
    }
    const orc = over.getBoundingClientRect(), er = ec.getBoundingClientRect();   // (the copy only fades: no transform)
    const cs = getComputedStyle(ec);
    const sx = wr.left - orc.left, sy = wr.top - orc.top;
    const probe = div("", over);
    probe.style.cssText = "position:absolute;width:0;height:0;background:var(--bg-1);border-color:var(--line-1);border-style:solid;border-width:0";
    const csP = getComputedStyle(probe);
    const fill = rgba(csP.backgroundColor), line = rgba(csP.borderTopColor);
    probe.remove();
    const ov = {
      yours: { g: { cx: sx + y.R.cx * s, cy: sy + y.R.cy * s, w: y.R.w * s, h: y.R.h * s, r: y.R.r * s, bw: 1 },
        look: { fill: y.surf, line: y.line, lineA: 1, dark: TL.dark } },
      offer: { g: { cx: er.left - orc.left + er.width / 2, cy: er.top - orc.top + er.height / 2, w: er.width, h: er.height, r: 24, bw: 1 },
        look: { fill, line, lineA: 1, dark: TL.dark } },
    };
    storyEl.style.setProperty("--offer-card-w", `${Math.round(er.width)}px`);
    storyEl.style.setProperty("--offer-card-h", `${Math.round(er.height)}px`);
    // the copy's box: the card less its padding
    const pl = parseFloat(cs.paddingLeft) || 0, pt = parseFloat(cs.paddingTop) || 0, pR = parseFloat(cs.paddingRight) || 0, pb = parseFloat(cs.paddingBottom) || 0;
    const bx = { l: er.left - orc.left + pl, t: er.top - orc.top + pt, r: er.right - orc.left - pR, b: er.bottom - orc.top - pb };
    const a = ov.yours.g, b = ov.offer.g, yo = TL.seg("yoursOffer"), sm = yo.seam;
    const cover = (k) => {
      const cx = mix(a.cx, b.cx, k), cy = mix(a.cy, b.cy, k), w = mix(a.w, b.w, k), h = mix(a.h, b.h, k);
      const ix = Math.min(bx.r, cx + w / 2) - Math.max(bx.l, cx - w / 2), iy = Math.min(bx.b, cy + h / 2) - Math.max(bx.t, cy - h / 2);
      return ix > 0 && iy > 0 ? (ix * iy) / ((bx.r - bx.l) * (bx.b - bx.t)) : 0;
    };
    // (R, Astra R #12: the tour button sat 1-5 px OUTSIDE the springing card as the copy arrived at 98 % cover) the copy
    // also waits until the card clears every side of it by OFFER_RING (or the side's own padding, if smaller)
    const ring = (k) => {
      const cx = mix(a.cx, b.cx, k), cy = mix(a.cy, b.cy, k), w = mix(a.w, b.w, k), h = mix(a.h, b.h, k);
      return (cx - w / 2) <= bx.l - Math.min(OFFER_RING, pl) + 0.5 && (cx + w / 2) >= bx.r + Math.min(OFFER_RING, pR) - 0.5
        && (cy - h / 2) <= bx.t - Math.min(OFFER_RING, pt) + 0.5 && (cy + h / 2) >= bx.b + Math.min(OFFER_RING, pb) - 0.5;
    };
    let uIn = sm.DUR;
    for (let u = sm.DUR; u >= sm.LIFT; u -= 0.005) { const k = sm.K(u); if (k == null || cover(k) < 0.98 || !ring(k)) break; uIn = u; }
    TL.offerIn = +uIn.toFixed(3);
    TL.offerSw[1] = yo.T0 + TL.offerIn;
    return ov;
  }

  /* ---------------- the destination table (ICX-DEST, docs/interaction-contract.md) and the pinned track ---------------- */
  // One row per beat, in BEATS order. A pinned row is a checkpoint: the story rests on its `rest` frame (story s) and a
  // move into it lands at its `entry` (its content start: the end of the seam into it). The track under the pin is one
  // BEAT_PX per checkpoint: checkpoint k sits at storyTop + k * BEAT_PX (ICX-SETTLE-7: BEAT_PX = round(100svh - header),
  // the pin's own height), and the pin lets go below the last one (storyEnd).
  const NAME = { make: "New invoice", look: "Templates", know: "Invoices", grow: "Dashboard", chase: "Email",
    yours: "Your data", price: "Price", note: "A note", end: "Get the app" };
  const SLUG = { make: "new-invoice", look: "templates", know: "invoices", grow: "dashboard", chase: "email",
    yours: "your-data", price: "price", note: "a-note", end: "get-the-app" };
  // legacy hashes (decisions #19): each keeps a tiny anchor of its own in index.html; C4 (story-url.js) owns the URL
  const LEGACY = { top: "make", how: "look", pricing: "price", download: "end" };
  // CP: the checkpoints of the current layout, in order (desktop all nine; tablets make…chase; phones make…chase, yours
  // and end, as shipped 10-10, decisions #21; calm / static: none). RE[k] = [entry, rest] of CP[k].
  let CP = [], RE = [], beatPx = 1, TRACK = null;
  function restEntry(b) {
    const seg = TL.seg;
    if (b === "make") return [0, TL.HOLD];
    if (b === "yours") return [seg("yours").T0, seg("yours").T0 + 0.28];
    if (b === "price") return [seg("price").T0, seg("price").T0 + 0.3];
    if (b === "note") return [seg("brand").T0, seg("brand").T0 + 0.2];
    if (b === "end") {
      if (TL.p === "tall") return [seg("end").T0, TL.T1 - END_REST];
      // (desktop: the note and the ending share the brand hold; the ending lands as its caption arrives)
      const sw = TL.switches.find((s) => s[0] === "end");
      return [sw[1], seg("brand").T1 - 0.05];
    }
    return [seg(b).T0, seg(b).T1 - 0.02];
  }
  function buildTrack() {
    CP = !TL ? [] : TL.isDesk ? BEATS.slice() : TL.p === "tall" ? TALL_BEATS.slice() : PHONE_BEATS.slice();
    RE = CP.map(restEntry);
    beatPx = Math.max(1, Math.round(pin.clientHeight));
    if (TL && TL.scrub) { buildMap(); TRACK = { L: MAP.L }; return; }   // SCRUB: the live scroll map is the track
    MAP = null;
    TRACK = { L: Math.max(0, CP.length - 1) * beatPx };
    css(track, "height", `${TRACK.L}px`);
    if (TL && TL.p === "tall" && TL.seg("end")) {
      endKv = -1;
      window.dispatchEvent(new Event("fx:layout"));
    }
  }
  // (SCRUB) a checkpoint's place is the middle of its hold on the map (the first: the story's top, as the live site's #top)
  const trackY = (k) => (MAP ? (k === 0 ? Math.max(0, Math.round(storyTop)) : scrollForBeat(CP[k])) : Math.round(storyTop) + k * beatPx);
  const storyEnd = () => (MAP ? storyTop + MAP.L : Math.round(storyTop) + (TRACK ? TRACK.L : 0));
  const nearestK = (y) => (MAP ? holdK(y) : clamp(Math.round((y - storyTop) / beatPx), 0, Math.max(0, CP.length - 1)));

  /* ---------------- SCRUB: the scroll map (ported from the live site, main 652d12a): plateaus at each checkpoint's rest
     frame, eased ramps between them; scroll drives the story, never the other way round ---------------- */
  // Touch tablets join the phones (SCRUB step 1: their holds are their checkpoints' rests on the current timeline, so the
  // map is the same mechanical one); false puts them back on the checkpoints in one line.
  const SCRUB_TABLET = true;
  let MAP = null;
  function buildMap() {
    // (phones, Daniel 10-10: "on phone id like you to have to scroll like 40% more … to slow down the animations") every
    // hold and ramp on the phone story is 1.4x the scroll; tablets keep their tuned 48 vh per second
    const vh = (TL.p === "tall" && svhPx > 0 ? svhPx : window.innerHeight) / 100 * (TL.p === "tall" ? 1.4 : 1);
    const seg = TL.seg;
    // the holds are the checkpoints' rest frames (restEntry: the same T as the live map's), one per CP row
    const LEN = { make: 10, look: 28, know: 26, grow: 14, chase: TL.isDesk ? 32 : 26, yours: 26, end: 40 };
    const holds = CP.map((b, k) => ({ beat: b, T: RE[k][1], len: LEN[b] }));
    const DRIFT = 0.03;
    // (v2.3b, Daniel: "each scroll makes the animation move less so it feels more natural and weighted": 48 vh per s)
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
    if (TL.p === "tall" && seg("end")) {
      endKv = -1;
      window.dispatchEvent(new Event("fx:layout"));
    }
  }
  // a ramp's progress with soft ends: zero slope at both ends, linear in the middle
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
  // the checkpoint whose hold is nearest the scroll position y
  function holdK(y) {
    const s = y - storyTop;
    let best = 0, bd = Infinity;
    for (const pc of MAP.pieces) {
      if (pc.kind !== "hold") continue;
      const d = s < pc.s0 ? pc.s0 - s : s > pc.s1 ? s - pc.s1 : 0;
      if (d < bd) { bd = d; best = Math.max(0, CP.indexOf(pc.beat)); }
    }
    return best;
  }
  // the hold the story time T sits in (its checkpoint index), or -1 on a ramp
  function holdAtT(T) {
    for (const pc of MAP.pieces) if (pc.kind === "hold" && T >= pc.T0 - 1e-4 && T <= pc.T1 + 1e-4) return Math.max(0, CP.indexOf(pc.beat));
    return -1;
  }
  function destinations() {
    return BEATS.map((b) => {
      const k = CP.indexOf(b);
      return { beat: b, name: NAME[b], slug: SLUG[b], anchor: SLUG[b], kind: k >= 0 ? "pinned" : "native",
        rest: k >= 0 ? +RE[k][1].toFixed(3) : null, entry: k >= 0 ? +RE[k][0].toFixed(3) : null };
    });
  }
  // (phones, F2; the contract F3 builds on) FX.story.endK(): how far the SHOWN time (the stage, never the scroll) has come
  // through the first half of the end hold, 0..1 (0 until T1 - 0.02, 1 from T1 - 0.005): the section after the
  // pin keys on it (its --end-k), so a scroll that outruns the stage never shows it early. endY(): the scroll position
  // where the story ends and the pin starts to leave (untransformed px). Events on window: fx:shown when endK changes,
  // fx:layout after each layout. Off phones (or with no phone ending) endK is 1.
  let endKv = -1;
  function setEndK(T) {
    const k = clamp((T - (TL.T1 - END_REST)) / END_K);
    if (k === endKv) return;
    endKv = k;
    if (home.yours) home.yours.sec.style.setProperty("--end-k", k >= 1 ? "1" : k.toFixed(3));
    window.dispatchEvent(new Event("fx:shown"));
  }
  FX.story = {
    endK: () => (TL && TL.p === "tall" && TL.seg("end") && endKv >= 0 ? endKv : 1),
    endY: () => (TL && TRACK ? storyEnd() : 0),
  };
  // readerY: the position as of the last scroll event, so a layout change above (a caption refit) has not moved it
  let readerY = 0;
  function keepPast(d) { const y = Math.round(storyEnd() + d); if (Math.abs(window.scrollY - y) >= 1) window.scrollTo(0, y); readerY = y; }
  // the header takes the band's colour while the band is the page; (phones, Astra pA #8) the phone story ends on Chase's
  // band, so once the reader is past the pinned story the header is back on its own surface (scrolling back restores it)
  let bandK = 0;
  function syncOnBand() {
    const onBand = bandK >= 0.6;
    if (lastG.onBand !== onBand) { lastG.onBand = onBand; doc.classList.toggle("on-band", onBand); }
    const past = !!(TL && TL.p === "tall" && TRACK && window.scrollY > storyEnd() + 1);
    if (lastG.past !== past) { lastG.past = past; doc.classList.toggle("past-band", past); }
    // (phones, F2d, Astra F2: the offer passed under the translucent header) as the pin lets go, everything in it is cut
    // at the header's lower edge: the pin's top has risen (scrollY - storyEnd) px above it, so that much is clipped
    // (measured: the pin's own top, read only from a few px before the release on, outside the pinned frames; the
    // computed storyEnd can differ from the sticky release by a px or two, which left a sliver under the header)
    const near = TL && TL.p === "tall" && TRACK && TL.seg("end") && window.scrollY > storyEnd() - 8;
    const cut = near ? (L.hh || 0) - pin.getBoundingClientRect().top : 0;
    const clip = cut > 0.5 ? `inset(${cut.toFixed(1)}px 0px 0px 0px)` : "";
    if (lastG.pinCut !== clip && (clip || pin.style.clipPath)) { lastG.pinCut = clip; if (clip) pin.style.clipPath = clip; else pin.style.removeProperty("clip-path"); }
  }
  window.addEventListener("scroll", () => { readerY = window.scrollY; if (TL && TRACK) syncOnBand(); }, { passive: true });
  // a saved place (segment id + local time) on the current timeline. (Sol F1 #3) Make is one scene on wider stages and
  // two segments on phones (make to HOLD, makeEnd): across 640 px, Make's own time carries over.
  function placeIn(id, u) {
    let sg = TL.seg(id);
    let moved = false;
    if (!sg && id === "makeEnd") { u = TL.HOLD + u; sg = TL.seg("make"); moved = true; }
    if (sg && sg.id === "make" && TL.p === "tall" && u > sg.T1 - sg.T0 + 1e-9) { u -= sg.T1 - sg.T0; sg = TL.seg("makeEnd"); moved = true; }
    return sg ? { sg, u, moved } : null;
  }

  /* ---------------- rendering one frame of the story at time T ---------------- */
  // Entering a segment resets every mount (hidden, at rest) once; after that only the segment's own participants are
  // touched each frame (a hidden mount is never sought: a seam seeks only what it shows, and every seek rewrites all
  // it shows, so re-entry is deterministic).
  let curSeg = -1, lastG = {};
  const setOnce = (key, el, prop, val) => { if (lastG[key] !== val) { lastG[key] = val; css(el, prop, val); } };
  function render(Tin) {
    const T = clamp(Tin, 0, TL.T1);
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
    // (the shown time itself; on the phone's last checkpoint at rest or released the story has arrived: the base's
    // scroll drifted it through its end hold to T1, so the section after the pin shows as the pin lets go)
    if (OV && OV.offer) setEndK(!MAP && CP[kR] === "end" && kR === CP.length - 1 && (phase === "rest" || phase === "released") ? TL.T1 : Tin);
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
    const kb = 1 - bk;
    if (G.bandTo && R0) {
      // (phones, F2d, Astra F2: "one container") the band gathers straight into a rect on the stage (canvas units: the
      // Data storage card), one silhouette from the page to the card, its corners the card's from a third of the way in,
      // its colour turning into the card's own (bandC, bandMix) so it lands on the card without a rim
      const s = L.s, k = clamp(G.bandK), r = G.bandTo;
      const x = (r.cx - r.w / 2) * s, y = (r.cy - r.h / 2) * s, w = r.w * s, h = r.h * s;
      const t = R0.t + y, l = R0.l + x, rr = R0.r + (L.sw - x - w), bb = R0.b + (L.sh - y - h);
      setOnce("bandD", band, "display", k < 1 ? "block" : "none");
      setOnce("bandC", band, "clip-path", k <= 0 ? "none"
        : `inset(${(t * k).toFixed(1)}px ${(rr * k).toFixed(1)}px ${(bb * k).toFixed(1)}px ${(l * k).toFixed(1)}px round ${((r.r || 3) * s * Math.min(1, k * 3)).toFixed(1)}px)`);
      const m = clamp(G.bandMix || 0), c = G.bandC;
      setOnce("bandBg", band, "background-color", !c || m <= 0 ? "" : FX.cssC(FX.mixC(TL.ride, c, m)));
    } else {
      setOnce("bandD", band, "display", bk > 0 ? "block" : "none");
      setOnce("bandC", band, "clip-path", bk <= 0 || bk >= 1 || !R0 ? "none"
        : `inset(${(R0.t * kb).toFixed(1)}px ${(R0.r * kb).toFixed(1)}px ${(R0.b * kb).toFixed(1)}px ${(R0.l * kb).toFixed(1)}px round ${(R0.rad * kb).toFixed(1)}px)`);
      setOnce("bandBg", band, "background-color", "");
    }
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
    // (full-field: the field is the whole stage, so the stage's own background takes its colour too: no edge fringe)
    const pinCls = "pin" + (f > 0.5 ? " on-field" : "") + (f >= 0.999 && !(G.fieldK > 0) ? " full-field" : "") + (T >= TL.late ? " is-late" : "") + (T >= TL.ownAt ? " own" : "");
    if (lastG.pinCls !== pinCls) { lastG.pinCls = pinCls; pin.setAttribute("class", pinCls); }
    // the header joins the band while the band is the page (syncOnBand)
    bandK = bk;
    syncOnBand();
    // the chapter rail takes the band's colours once the band's opening clip has covered its whole box (names included)
    if (railOn && R0) {
      if (!railBox && bk > 0 && bk < 1) railMeasure(true);
      const rb = railBox;
      const nb = bk >= 1 || (bk > 0 && !!rb && R0.l * kb <= rb.l && R0.t * kb <= rb.t && R0.r * kb <= rb.r && R0.b * kb <= rb.b);
      if (lastG.navBand !== nb) { lastG.navBand = nb; nav.classList.toggle("on-band", nb); }
    }
    // legal v-story (2026-10-08), narrowed by A10 (R5 A.2): "Fictional data", continuously, on [labelData, labelOff]
    // (both ends inclusive; the same frames in both directions, never faded or timed)
    const mode = T >= TL.labelData && T <= TL.labelOff ? "data" : "";
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
        lineA: mix(a.look.lineA, b.look.lineA, kc), dark: TL.dark, sq: 0, lite: TL.p === "tall" && !TL.dark ? LITE : undefined });
      const seal = c.seal || 0;
      drawInk(ovInk, { mode: seal <= 0 ? "none" : seal >= 1 ? "full" : "disc", k: seal, x: g.w / 2, y: g.h / 2, w: g.w, h: g.h, color: [6, 10, 15, 1] });
    }
    if (!ovMark) return;                               // (phones: the offer card only)
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
    // hysteresis only while the playhead moves: at rest the caption is the rest frame's own (ICX-CHECKPOINT.2). Chase,
    // Yours and Price rest within 0.12 s of a caption-less switch, so a seam played back past it rested with no caption.
    if (!instant && phase !== "rest" && capIdx >= 0 && Math.abs(i - capIdx) === 1) {
      // hysteresis: 0.12 s of story either side of a switch, or the switch's own width (the price copy rides its card,
      // so it uses 0.02: with 0.12 the card showed empty going forwards and the copy hung over it going back, ~0.3 s)
      const [, boundary, width = 0.12] = TL.switches[Math.max(i, capIdx) - 1];
      if (Math.abs(T - boundary) < width) i = capIdx;
    }
    // (phones, F2b, Sol F2 #1) the offer copy shows only while its card covers >= 98 % of it, which is from TL.offerSw[1]
    // on (layout() measures that moment): before it, the copy leaves at once in either direction, with no hysteresis and
    // no fade, so scrolling back never leaves it over a card that is shrinking away
    if (TL.offerSw && T < TL.offerSw[1]) {
      if (TL.beats[i] === "end") i = beatAt(T);
      const ec = copy.end;
      if (ec && ec.parentNode === capsEl && (ec.classList.contains("is-on") || ec.classList.contains("is-off"))) {
        ec.style.transition = "none";
        ec.classList.remove("is-on", "is-off");
        void ec.offsetWidth;
        ec.style.removeProperty("transition");
        if (ec.getAttribute("style") === "") ec.removeAttribute("style");
        capActive(ec, false);
      }
    }
    if (i === capIdx && !instant) return;
    capIdx = i;
    const b = TL.beats[i];                            // null: a beat with no caption (the Ride's flood)
    const next = capFor(b);
    clearTimeout(capTimer);
    // (phones, F2c) the offer copy never waits out an outgoing caption's 60 ms fade: a fling can step over the null
    // switch between the Yours caption and the copy (0.04 s of story), and by the time that fade ends the stage is gone
    // and the card is empty. The outgoing caption leaves at once (it sits under the card); the copy starts its own
    // 100 ms arrival now.
    if (next && next === copy.end && TL.offerSw) {
      for (const c of $$(".beat-copy.is-on, .beat-copy.is-off", capsEl)) {
        if (c === next) continue;
        c.style.transition = "none";
        c.classList.remove("is-on", "is-off");
        void c.offsetWidth;
        c.style.removeProperty("transition");
        if (c.getAttribute("style") === "") c.removeAttribute("style");
        capActive(c, false);
      }
    }
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
  }

  /* ---------------- the chapter rail (desktop): assets/story/rail.js owns it (B5, rail v3) ---------------- */
  // rail.js renders the rail from FEStory.destinations, shows or hides it, turns a click into FEStory.goTo and is the one
  // writer of its highlight and aria-current (ICX-HL.5). The engine keeps the two visual cues only it knows: .is-in (the
  // rail draws in once the arrival has handed over) and .on-band (the Ride's band has covered the rail's whole box).
  let railOn = false, railIn = false, railBox = null;
  // the rail's box inside the band's box (the band's clip insets are in that box: applyGlobals); measured lazily, since
  // rail.js may show the rail after this layout ran
  function railMeasure(now) {
    railOn = !!(nav && TL && TL.isDesk);
    railBox = null;
    if (!now || !railOn || nav.hidden) return;
    const r = nav.getBoundingClientRect(), br = band.getBoundingClientRect();
    if (!r.width || !br.width) return;
    railBox = { l: r.left - br.left, t: r.top - br.top, r: br.right - r.right, b: br.bottom - r.bottom };
  }
  function railReveal() {
    if (!railOn || railIn) return;
    railIn = true;
    nav.classList.add("is-in");                       // CSS draws the ticks and names in, top to bottom
  }
  function railTeardown() {
    railOn = false; railIn = false; railBox = null;
    if (nav) nav.classList.remove("is-in", "on-band");
  }

  /* ---------------- checkpoints (ICX v1, C3): one gesture = one page; seams and content play at their designed speed ---------------- */
  // docs/interaction-contract.md + docs/checkpoint-config.md v1. Input (assets/shared/checkpoint-input.js, C1) gives
  // ±1 steps and Home/End jumps; the engine keeps a signed dest. A step plays the seam into the next checkpoint at 1x,
  // lands there (rendered), plays its content at 1x and rests on its key frame. Back = a 220 ms fade to the previous rest.
  // Gestures during a move add ±1 (clamped to [first, last pinned]); a move whose rest cannot finish within 0.6 s
  // (rate ramp, never above 3x or a seam's own CAP) becomes one 220 ms dip; two dips are >= 600 ms apart. Every scene and
  // seam is the same pure function of story time as before: only the input model changed.
  // A foreign scroll inside the track (a scrollbar drag, find-in-page, an anchor) is FREE: the stage keeps its frame and
  // settles on the nearest checkpoint (ICX-SETTLE-1…9, from C0a's spike). History is C4's (story-url.js): this file
  // writes none; onLand/onDest carry what it needs.
  const CFG = Object.freeze({ DIP_OUT: 0.1, DIP_IN: 0.12, COOLDOWN: 0.6, RATE_MAX: 3, RUSH: 2.5, RUSH_MAX: 0.6,
    ABORT_RATE: 1.5, RATE_ACCEL: 12, CONTENT_FINISH_MAX: 0.6,
    ACK_TOL: 1.5, ACK_MS: 400, SCROLLEND_GRACE: 50, SETTLE_IDLE: 150, SETTLE_BACKSTOP: 700, REENTRY_STICKY_MS: 800,
    RESIZE_GRACE: 250, HOLD_MAX: 10000, ZOOM_SCALE: 1.01 });
  const EPS = 1e-4;
  const clock = () => performance.now() / 1000;
  // BT-2: feature-detect scrollend; ?noscrollend forces the idle path (Safari without scrollend)
  const HAS_SCROLLEND = "onscrollend" in window && !new URLSearchParams(location.search).has("noscrollend");
  let kR = 0, kD = 0, phase = "rest", run = null, dip = null, wait = 0, lastDipAt = -1e9, passK = -1;
  let shown = 0, raf = 0, lastNow = 0, held = false, lastDrawn = null, srcD = "init", initial = null;
  let free = null, ack = null, geomAt = -1e9, reentryUntil = -1e9, releasing = -1e9, swallow = -1, settles = 0;
  let barHeld = false, holdTimer = 0, classicPref = null, lastMode = null;
  let nativeSeq = 0, nativeStop = null;                // native anchor scrolls started (goTo) | the one stopNative cancelled: {seq, at}
  let native = null;                                    // a native row's smooth scroll in flight: null | {phase0, k, timer}
  const listeners = { dest: [], land: [], mode: [] };
  function emit(kind, p) { for (const fn of listeners[kind].slice()) { try { fn(p); } catch (e) { console.warn(e); } } }
  const bi = (k) => BEATS.indexOf(CP[k]);
  const payload = (k, source, extra) => ({ index: bi(k), beat: CP[k], slug: SLUG[CP[k]], source, ...extra });
  const last = () => CP.length - 1;

  // a seam may ask to be played no faster than its own CAP (the PDF -> Look reveal): a rush or a reversal honours it
  function capAt(T) {
    for (const sg of TL.segs) if (sg.seam && sg.seam.CAP && T >= sg.T0 - EPS && T <= sg.T1 + EPS) return Math.min(CFG.RATE_MAX, sg.seam.CAP);
    return CFG.RATE_MAX;
  }
  // ICX-SIGNED.5's T_c(R): the time the rest of a run takes from T to `to`, the rate ramping from r0 at RATE_ACCEL up to c
  // (integrated, so a CAP seam on the way counts)
  function runTime(T, to, r0, c) {
    const dir = to >= T ? 1 : -1, h = 1 / 480;
    let t = 0, r = r0, x = T;
    while ((to - x) * dir > EPS && t < 5) { x += dir * Math.min(r, capAt(x)) * h; r = Math.min(c, r + CFG.RATE_ACCEL * h); t += h; }
    return t;
  }
  // the rush cap c* = max(floor, the smallest c <= 3x that finishes within RUSH_MAX), or null (it dips instead)
  function rushCap(T, to, r0, floor) {
    if (runTime(T, to, r0, CFG.RATE_MAX) > CFG.RUSH_MAX) return null;
    let c = Math.max(1, r0);
    while (c < CFG.RATE_MAX && runTime(T, to, r0, c) > CFG.RUSH_MAX) c = Math.min(CFG.RATE_MAX, c + 0.05);
    return Math.max(floor, c);
  }

  /* -- scroll: our own scrolls are acknowledged by position (ICX-SETTLE-1) -- */
  function syncScroll(y) {
    const max = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    y = clamp(Math.round(y), 0, max);
    if (Math.abs(window.scrollY - y) <= 0.5) return;
    ack = { y, until: performance.now() + CFG.ACK_MS };
    window.scrollTo({ top: y, left: 0, behavior: "instant" });
    readerY = window.scrollY;
  }

  /* -- dest and landings: the only writers of kD and kR -- */
  function setDest(k, source) {
    k = clamp(k, 0, last());
    if (k === kD) return false;
    kD = k; srcD = source;
    emit("dest", payload(k, source));
    return true;
  }
  // a landing (Terms): rendered moves; final when it reaches dest (only a final landing plays content and rests)
  function land(k) {
    kR = k; passK = -1;
    syncScroll(trackY(k));
    if (kD === kR) announce(k);
    emit("land", payload(k, srcD, { final: kD === kR }));
  }
  // ICX-KEY.2 (C6): a polite live region says each FINAL landing's name (key, wheel, touch, rail, settle, popstate,
  // re-entry); pass-through landings and mid-move frames say nothing, and focus never moves (ICX-KEY.3)
  // (made at load, empty, so assistive tech knows the region before its first change)
  const liveEl = document.createElement("p");
  liveEl.className = "visually-hidden";
  liveEl.setAttribute("aria-live", "polite");
  liveEl.setAttribute("data-story-live", "");
  document.body.appendChild(liveEl);
  function announce(k) {
    const name = NAME[CP[k]] || "";
    if (liveEl.textContent === name) liveEl.textContent = "";   // the same name again is a new landing: say it again
    liveEl.textContent = name;
  }
  // the one way into REST (ICX-CHECKPOINT.2, ICX-REST): rendered == dest == k, the story on k's rest frame, scrollY on
  // k's track position. Everything that ends a move comes through here.
  function enforceRest(k) {
    run = null; wait = 0; passK = -1;
    if (k !== kR) { kD = k; land(k); }
    kD = kR = k;
    shown = RE[k][1];
    phase = "rest";
    syncScroll(trackY(k));
    wake();
  }
  function landAt(k) {                                  // instant (a mode flip keeps the place: restorePlace)
    if (MAP) { scrubPlace(trackY(k)); kR = kD = k; sPrev = k; return; }
    run = null; wait = 0; passK = -1; endFree();
    if (dip) { dip = null; clearDip(); }
    dropXf();                                           // (FADEDEF, judge FLICKER2 LOW) a jump never lets the held frame fade on
    kD = kR = k; shown = RE[k][1]; phase = "rest";
    syncScroll(trackY(k));
    lastDrawn = null; capIdx = -1;
    render(shown); updateCaptions(shown, true);
    wake();
  }

  /* -- the playhead: runs (1x seams and content; ramped rushes and reversals) and dips -- */
  function startRun(purpose, to, rate, cap, accel, t0) {
    run = { purpose, to, dir: to >= shown ? 1 : -1, rate, cap, accel };
    phase = "transition";
    wake(t0);
  }
  const contentRun = (t0) => startRun("content", RE[kR][1], 1, 1, false, t0);
  function cooling(t) {                                 // ICX-DIP.4: dest is kept; the decision is taken again at its end
    if (t - lastDipAt >= CFG.COOLDOWN - 1e-3) return false;
    wait = lastDipAt + CFG.COOLDOWN;
    if (phase === "rest") phase = "transition";
    wake();
    return true;
  }
  function startDip(k, mode, t0) {
    const t = t0 != null ? t0 : clock();
    if (cooling(t)) return;
    run = null; wait = 0; dropXf();
    dip = { t0: t, mode, k, cut: false, band0: bandOnAt(shown) };
    lastDipAt = t;
    phase = "dip";
    wake(t);
  }
  // The planner: from the running move (or a still frame) and the signed dest, what plays next. Called when dest changes,
  // at every landing, when content ends off dest, after a dip and when the cooldown ends.
  function decide(t0) {
    if (!CP.length || dip || wait || phase === "free" || phase === "released") return;
    const rs = RE[kR][1];
    if (run && run.purpose === "seam") {               // a forward seam kR -> kR + 1
      if (kD === kR + 1) return;
      if (kD > kR + 1) {                                // dest moved on: rush to the landing, or dip (ICX-SIGNED.4/.5)
        const c = rushCap(shown, run.to, run.rate, CFG.RUSH);
        if (c != null) { run.accel = true; run.cap = Math.max(run.cap, c); return; }
        return startDip(kD, "entry", t0);
      }
      if (kD === kR) {                                  // back to the origin: the seam plays backwards (ICX-SIGNED.2, ICX-BACK.3)
        const c = rushCap(shown, rs, CFG.ABORT_RATE, CFG.ABORT_RATE);
        if (c != null) { run = { purpose: "reverse", to: rs, dir: -1, rate: CFG.ABORT_RATE, cap: c, accel: true }; return; }
        return startDip(kR, "rest", t0);
      }
      return startDip(kD, "entry", t0);
    }
    if (run && run.purpose === "reverse") {             // back to REST(kR); further input is judged on arrival
      if (kD === kR + 1) { run = { purpose: "seam", to: RE[kR + 1][0], dir: 1, rate: 1, cap: 1, accel: false }; return; }
      if (kD > kR + 1) return startDip(kD, "entry", t0);
      return;
    }
    if (run && run.purpose === "content") {             // landed on kR, its content playing (ICX-STEP.7, ICX-BACK.2)
      if (kD === kR) return;
      if (kD > kR) {
        if (rs - shown <= CFG.CONTENT_FINISH_MAX + EPS) return;     // it finishes at 1x; decided again at its end
        return kD === kR + 1 ? skipContent(t0) : startDip(kD, "entry", t0);
      }
      return kD === kR - 1 ? startDip(kD, "rest", t0) : startDip(kD, "entry", t0);
    }
    // no run: on a still frame (at rest, after a dip or a cooldown, after FREE stopped a move)
    const atRest = Math.abs(shown - rs) <= 0.002;
    if (kD === kR) {
      if (atRest) return enforceRest(kR);
      if (shown < rs) return passK === kR ? skipContent(t0) : contentRun(t0);
      const c = rushCap(shown, rs, CFG.ABORT_RATE, CFG.ABORT_RATE);   // part-way into the next seam: back to rest
      if (c != null) return startRun("reverse", rs, CFG.ABORT_RATE, c, true, t0);
      return startDip(kR, "rest", t0);
    }
    if (kD === kR + 1) {
      if (atRest || shown > rs) return startRun("seam", RE[kR + 1][0], 1, 1, false, t0);   // ICX-STEP.1
      if (passK === kR || rs - shown > CFG.CONTENT_FINISH_MAX + EPS) return skipContent(t0);
      return contentRun(t0);                            // the rest of the content at 1x, then the seam (ICX-STEP.7)
    }
    if (kD === kR - 1) return startDip(kD, "rest", t0); // the back-fade (ICX-BACK.1/.2)
    return startDip(kD, "entry", t0);                   // distance >= 2 (ICX-DIP.1)
  }
  // decision #13's content skip (FLICKER2 "fade", the default since FADEDEF): the content's frame is held over the
  // stage, the stage cuts to kR's rest frame underneath (no landing: rendered stays, as the dip's cut) and the held
  // frame crossfades away; the seam starts when the crossfade ends (decide, at `wait`). It counts as a dip for the
  // cooldown (ICX-DIP.4) and re-syncs the scroll position the way the dip's cut does.
  // (FADEDEF r3, main's ruling) EVERY content skip is this crossfade: mid-content (decide's content run), a pass-through
  // landing in a multi-step run (arrive; ICX-SIGNED.6), and the still-frame skips (decide's no-run branch: passK, or
  // > CONTENT_FINISH_MAX left after FREE or a cooldown stopped the move). Inside the cooldown it waits it out like a dip
  // (cooling() sets `wait`; at its end decide() takes the no-run branch, where passK === kR routes back here), so a
  // run never stalls and the passed chapter's content never plays: no content run starts while passK === kR.
  function skipContent(t0) {
    const t = t0 != null ? t0 : clock();
    if (cooling(t)) return;
    holdFrame(t);
    xf.dipAt0 = lastDipAt;                              // an explicit jump inside the crossfade is not held by its cooldown
    run = null; wait = 0;
    lastDipAt = t;
    shown = RE[kR][1];
    passK = -1; syncScroll(trackY(kR));
    FX.gate.cursor = 1; FX.gate.press = 1;
    lastDrawn = null;
    render(shown); updateCaptions(shown, true);
    phase = "transition";
    wait = t + xf.dur;
    wake(t);
  }
  function arrive(r) {
    if (r.purpose === "seam") {
      land(kR + 1);
      if (kD === kR) { if (RE[kR][1] - shown > EPS) contentRun(); else enforceRest(kR); return; }
      passK = kR;                                       // a pass-through landing: its content never plays (ICX-SIGNED.6)
      phase = "transition";
      if (kD === kR + 1) return skipContent();         // FADEDEF r3: the pass-through's skip is the crossfade too
      return decide();
    }
    if (r.purpose === "reverse") land(kR);            // a reversed seam lands on its origin's rest frame (Terms; Sol C3-1 #3)
    if (kD === kR) return enforceRest(kR);
    phase = "transition";
    decide();
  }
  function runStep(dt) {
    const r = run;
    const x = shown + r.dir * Math.min(r.rate, capAt(shown)) * dt;
    if (r.accel) r.rate = Math.min(r.cap, r.rate + CFG.RATE_ACCEL * dt);
    if ((r.to - x) * r.dir <= EPS) { shown = r.to; run = null; arrive(r); }
    else shown = x;
  }
  // a dip: 100 ms out, the cut at the dark frame (dest as it stands then, ICX-DIP.2), 120 ms in
  function dipStep(now) {
    const u = now - dip.t0;
    if (u < CFG.DIP_OUT) { setDip(1 - u / CFG.DIP_OUT); dipBand(1 - u / CFG.DIP_OUT); return; }
    if (!dip.cut) cut();
    const a = Math.min(1, (u - CFG.DIP_OUT) / CFG.DIP_IN);
    setDip(a); dipBand(a);
    if (a >= 1) { const d = dip; dip = null; clearDip(); afterDip(d); }
  }
  function cut() {
    const d = dip;
    d.cut = true;
    // (ICX-STEP.7: a skip whose dest is >= 2 away by its dark frame is the dip to dest instead; Sol C3-1 #1)
    if (d.mode === "skip" && Math.abs(kD - kR) >= 2) d.mode = "entry";
    let k = d.k;
    if (d.mode === "entry") { k = kD; if (k === kR) d.mode = "rest"; }
    shown = d.mode === "entry" ? RE[k][0] : RE[k][1];
    // a cut is a landing (Terms), a skip excepted (no new landing: rendered stays); back on the origin counts too
    if (k !== kR || d.mode === "rest") land(k); else { passK = -1; syncScroll(trackY(kR)); }
    FX.gate.cursor = 1; FX.gate.press = 1;
    lastDrawn = null;
    render(shown); updateCaptions(shown, true);
  }
  function afterDip(d) {
    phase = "transition";
    if (d.mode === "entry") { contentRun(); if (kD !== kR) decide(); return; }
    if (kD === kR) return enforceRest(kR);
    decide();
  }

  /* -- input (C1's detector) -- */
  function onStep(dir, src, info) {
    if (!TL || !CP.length || held || MAP) return;      // (SCRUB: the detector is off; never reached)
    if (info && info.gesture != null && info.gesture === swallow) return;   // ICX-SETTLE-8: the rest of a crossing gesture
    // (the run's clock starts when the input is handled: an event's timeStamp can be older than its dispatch, and
    // counting that gap made the first frames of a 1x step run fast)
    const t0 = clock();
    if (phase === "released") return;
    if (phase === "free") {                            // ICX-SETTLE-5: counted from the beat the settle would have picked
      const b = settleTarget();
      endFree();
      syncScroll(trackY(kR));
      return jump(clamp(b + dir, 0, last()), "step", t0);
    }
    if (phase === "rest" && ((dir > 0 && kR === last()) || (dir < 0 && kR === 0))) return;
    if (!setDest(kD + dir, "step")) return;            // past the last pinned or the first: dropped (ICX-SIGNED.1)
    decide(t0);
  }
  // an explicit target (Home/End, the rail, a settle, C4's deep links and popstate): ICX-JUMP
  function jump(k, source, t0) {
    if (MAP) return scrubJump(k, source);
    if (native && source !== "settle" && source !== "step") stopNative();   // the latest explicit jump wins (C4-engine)
    if (phase === "released") reenter();
    if (phase === "free") { endFree(); syncScroll(trackY(kR)); }
    // (FADEDEF, judge FLICKER2 LOW) an explicit jump inside the content skip's crossfade removes the held frame at once
    // and ends the crossfade's wait: the stage is already on kR's rest frame, so the jump is planned from there now.
    // (main's ruling 2026-10-17, "feel instant") its own transition starts in this frame: the skip's cooldown holds
    // gesture steps only (as after a dip's cut, where the skip's dip became the jump), so it is undone for a jump
    if (xf) { lastDipAt = xf.dipAt0; dropXf(); wait = 0; }
    if (!dip && k === kR && kD === kR && (phase === "rest" || (run && run.purpose === "content"))) {
      if (phase === "rest") syncScroll(trackY(kR));   // ICX-JUMP.0: nothing moves, nothing replays
      return;
    }
    setDest(k, source);
    decide(t0);
  }
  function onJump(target, src, info) {
    if (!TL || !CP.length || held || MAP) return;
    const k = target === "first" ? 0 : last();
    // (INT5-fix 4; Sol INT-5) through story-url.js's jump path when it is there (as the rail and the menu): it saves the
    // departing offset BEFORE a re-entry from a native section moves the page, so Back returns to the reader's pixel
    const U = window.FEStoryURL;
    if (U && typeof U.jump === "function" && U.jump(SLUG[CP[k]])) return;
    jump(k, "jump");
  }
  // let the gesture pass natively (true) or intercept it: the edges (ICX-RELEASE, ICX-BACK.5), FREE's clamp (ICX-SETTLE-5),
  // the crossing from below (ICX-SETTLE-8), and overlays
  function isBypassed(ev, info) {
    if (!TL || !CP.length || !motion() || held) return true;
    if (doc.classList.contains("tq-locked") || document.querySelector("dialog[open]")) return true;
    if (info.jump) return false;                        // Home / End always jump (ICX-KEY.6)
    const y = window.scrollY, end = storyEnd();
    if (phase === "released" || y > end + 1) {
      if (info.source === "wheel" && info.dir < 0) {
        const dy = ev.deltaY * (ev.deltaMode === 1 ? 33.3 : ev.deltaMode === 2 ? window.innerHeight : 1);
        if (y + dy >= end) return true;                 // still below the pin: native
        reenter();                                      // the crossing event: prevented, REST(last), the rest swallowed
        reentered();
        swallow = info.gesture;
        return false;
      }
      return true;                                      // keys, touch and forward: native (then FREE / settle)
    }
    if (phase === "free") {
      const b = settleTarget();
      return (info.dir > 0 && b === last()) || (info.dir < 0 && b === 0);
    }
    // ICX-RELEASE.1; a touch "probe" (an in-slop move asked in both directions: a tap, a back-swipe start) is a pure
    // question and must not arm the release (judge C6 #1)
    if (phase === "rest" && info.dir > 0 && kR === last()) { if (info.phase !== "probe") releasing = clock(); return true; }
    if (phase === "rest" && info.dir < 0 && kR === 0) return true;                                // ICX-BACK.5
    return false;
  }
  const seq = window.FECheckpoint ? FECheckpoint.createSequence({ onStep, onJump, isBypassed, pinHeight: () => pin.clientHeight }) : null;
  if (seq) seq.attach(window);
  // SCRUB: the detector is off on a scrub build, so no wheel, touch or key is ever intercepted (native scroll drives it)
  const seqEnable = () => { if (seq) seq.setEnabled(!!(TL && motion() && CP.length && !MAP)); };

  /* -- FREE, RELEASED, settle (ICX-SETTLE-2…8) -- */
  function reenter() {
    endFree();
    run = null; wait = 0; passK = -1;
    if (dip) { dip = null; clearDip(); }
    dropXf();                                           // defensive, untested: only foreign() reaches here mid-crossfade, and it drops it first
    kR = kD = last(); shown = RE[kR][1]; phase = "rest";
    syncScroll(storyEnd());
    announce(kR);                                       // re-entry is a final landing on the last pinned (ICX-KEY.2)
    reentryUntil = clock() + CFG.REENTRY_STICKY_MS / 1000;
    lastDrawn = null;
    wake();
  }
  function setReleased() {
    endFree();
    run = null; wait = 0; passK = -1;
    if (dip) { dip = null; clearDip(); }
    dropXf();
    if (kR !== last() || Math.abs(shown - RE[last()][1]) > EPS) { kR = last(); shown = RE[kR][1]; lastDrawn = null; }
    kD = kR;
    phase = "released";
    wake();
  }
  function endFree() {
    if (!free) return;
    clearTimeout(free.timer); clearTimeout(free.backstop);
    free = null;
    if (phase === "free") phase = "transition";
  }
  // ICX-SETTLE-9 (C6-fix, judge C6 ruling b): a FREE episode that saw a pinch zoom (visualViewport.scale > ZOOM_SCALE)
  // never settles while zoomed (a settle scroll yanks the zoomed view, and "nearest" is wherever the zoom panned the
  // layout); on the zoom-out it settles once on the chapter it was landed on: a distance-0 re-alignment (ICX-SETTLE-4)
  const zoomed = () => { const v = window.visualViewport; return !!(v && v.scale > CFG.ZOOM_SCALE); };
  const settleTarget = () => (free && free.zoomed ? kR
    : free && free.from === "released" && !free.sawHold ? last() : nearestK(window.scrollY));
  function foreign(y) {
    const t = clock(), end = storyEnd();
    // a zoomed pan inside the pin may run past its end: still FREE (it re-aligns on kR at the zoom-out), never a release
    const zin = phase !== "released" && (zoomed() || !!(free && free.zoomed));
    if (!zin && (y > end + 1 || (t - releasing < 0.6 && kR === last() && y >= end - 1))) { if (phase !== "released") setReleased(); return; }
    if (!free) {
      free = { from: phase === "released" || t < reentryUntil ? "released" : "in", sawHold: barHeld, lastT: t, timer: 0, backstop: 0, preview: -1 };
      if (phase === "released") { kR = kD = last(); free.back = true; }   // a re-entry from below begins here
      run = null; wait = 0;                             // the stage keeps its frame; the settle plans afresh
      if (dip) { dip = null; clearDip(); }
      dropXf();                                         // (FADEDEF) a native scroll / goTo's native row drops the held frame at once
      phase = "free";
    }
    if (zoomed()) free.zoomed = true;
    free.lastT = t;
    const n = free.zoomed ? kR : nearestK(y);           // a zoomed episode previews the beat it will re-align on
    if (n !== free.preview) { free.preview = n; emit("dest", payload(n, "free", { preview: true })); }
    armSettle("scroll");
    wake();
  }
  function armSettle(trigger) {
    if (!free) return;
    clearTimeout(free.timer);
    if (trigger === "scrollend") { free.timer = setTimeout(() => settle("scrollend"), CFG.SCROLLEND_GRACE); return; }
    if (!HAS_SCROLLEND) free.timer = setTimeout(() => settle("idle"), CFG.SETTLE_IDLE);
    clearTimeout(free.backstop);
    free.backstop = setTimeout(() => settle("backstop"), CFG.SETTLE_BACKSTOP);
  }
  function settle(trigger) {
    if (!free || barHeld) return;                      // a scrollbar hold settles when it ends (ICX-SETTLE-6)
    const quiet = (clock() - free.lastT) * 1000;
    const need = trigger === "scrollend" ? CFG.SCROLLEND_GRACE : CFG.SETTLE_IDLE;
    if (zoomed()) { free.zoomed = true; return; }     // never while pinch-zoomed: the zoom-out settles (ICX-SETTLE-9)
    if (quiet < need - 1) { armSettle("scroll"); return; }
    const y = window.scrollY, from = free.from, sawHold = free.sawHold, back = !!free.back, zoom = !!free.zoomed, pv = free.preview;
    endFree();
    settles++;
    if (zoom) {                                         // the landed chapter, never the nearest
      if (pv !== kR) emit("dest", payload(kR, "free", { preview: true }));   // FREE's highlight back on it (ICX-HL.3)
      syncScroll(trackY(kR)); jump(kR, "settle"); return;
    }
    if (y > storyEnd() + 1) { setReleased(); return; }
    let b = nearestK(y);
    if (from === "released" && !sawHold) { b = last(); reentryUntil = clock() + CFG.REENTRY_STICKY_MS / 1000; }   // re-entry
    syncScroll(trackY(kR));
    jump(b, "settle");
    // a touch / momentum re-entry lands on REST(last) with no new landing (kR was already the last pinned): it is
    // still a final landing for ICX-KEY.2 (Sol C6-sol-1 #3); a sticky continuation of it says nothing again
    if (back && b === last() && kR === last() && kD === kR) { announce(kR); reentered(); }
  }
  // (INT5-fix 6; Astra INT-5) a re-entry from below is a final landing on the last pinned with no landing of its own (kR
  // already was the last pinned): story-url.js writes its URL like any FREE settle's (ICX-HIST.8), or the address kept
  // the native section's (#price) the reader came from. reentry: true marks it (a URL that already names it: no write)
  function reentered() { emit("land", payload(kR, "settle", { final: true, reentry: true })); }
  function onScroll() {
    if (!TL || !CP.length || held || !motion()) return;
    if (MAP) { wake(); return; }                        // SCRUB: the scroll is the input; no FREE, no settle
    const y = window.scrollY, t = performance.now();
    if (ack && t <= ack.until && Math.abs(y - ack.y) <= CFG.ACK_TOL) return;
    if (ack && t > ack.until) ack = null;
    if (t / 1000 - geomAt < CFG.RESIZE_GRACE / 1000 && phase !== "released" && phase !== "free" && y <= storyEnd() + 1) { syncScroll(trackY(kR)); return; }
    // the last frames of a native smooth scroll a later jump cancelled (stopNative) are its residue, not the reader's; only
    // while no NEWER native scroll has started (seq): a native jump issued inside the window is the latest target (Sol C4-engine 1)
    if (nativeStop && nativeStop.seq === nativeSeq && t / 1000 - nativeStop.at < CFG.RESIZE_GRACE / 1000 && phase !== "released" && phase !== "free") { syncScroll(trackY(kR)); return; }
    foreign(y);                                         // BT-1: FREE is entered here, synchronously in the scroll event
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("scrollend", () => { endNative(); if (HAS_SCROLLEND && free) armSettle("scrollend"); });

  /* -- a native row's smooth anchor scroll in flight (goTo, ICX-JUMP.5), and its cancel by a later explicit jump -- */
  // Main's ruling (C4 gap 3a): the latest explicit jump wins. A pinned jump issued while a native jump's smooth scroll is
  // still under way cancels that scroll (an instant scroll ends a smooth one), puts back the place the scroll left (its
  // FREE episode, or the release it caused, never happened) and then jumps from there: no settle undoes the dip, no stray
  // release at the native target.
  function startNative(aim) {
    if (native) clearTimeout(native.timer);
    native = { phase0: native ? native.phase0 : phase, k: native ? native.k : kR, aim, timer: setTimeout(endNative, 2500) };
  }
  function endNative() { if (native) { clearTimeout(native.timer); native = null; } }
  function stopNative() {
    const n = native;
    endNative();
    if (n.phase0 !== "released" && (phase === "free" || phase === "released")) {
      const pv = free ? free.preview : -1;
      endFree();
      run = null; wait = 0; passK = -1;
      if (dip) { dip = null; clearDip(); }
      if (kR !== n.k || Math.abs(shown - RE[n.k][1]) > EPS) lastDrawn = null;
      kR = kD = n.k; shown = RE[kR][1]; phase = "rest";
      if (pv >= 0 && pv !== kR) emit("dest", payload(kR, "free", { preview: true }));   // FREE's highlight back (ICX-HL.3)
    }
    const max = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    const y = clamp(Math.round(phase === "released" ? window.scrollY : trackY(kR)), 0, max);
    ack = { y, until: performance.now() + CFG.ACK_MS };
    window.scrollTo({ top: y, left: 0, behavior: "instant" });   // forced, even at the same y: it ends the smooth scroll
    readerY = window.scrollY;
    nativeStop = { seq: nativeSeq, at: clock() };       // the guard acts on this scroll's residue only
    wake();
  }
  // the zoom-out of a zoomed FREE episode: settle once, after the pinch's own last scrolls have gone quiet
  if (window.visualViewport) window.visualViewport.addEventListener("resize", () => {
    if (!free) return;
    if (zoomed()) { free.zoomed = true; return; }       // a pinch between FREE's scroll and its settle counts too
    if (!free.zoomed) return;
    free.lastT = clock();
    clearTimeout(free.timer);
    free.timer = setTimeout(() => settle("idle"), CFG.SETTLE_IDLE);
  });
  document.addEventListener("mousedown", (e) => {
    if (!(e.clientX >= doc.clientWidth || e.clientY >= doc.clientHeight)) return;
    barHeld = true;
    if (free) free.sawHold = true;
    clearTimeout(holdTimer);
    holdTimer = setTimeout(() => endHold(), CFG.HOLD_MAX);
  }, true);
  function endHold() {
    if (!barHeld) return;
    barHeld = false; clearTimeout(holdTimer);
    if (free) { free.lastT = clock() - CFG.SETTLE_IDLE / 1000; settle("hold"); }
  }
  window.addEventListener("mouseup", endHold, true);
  window.addEventListener("pointerup", endHold, true);
  window.addEventListener("mousemove", (e) => { if (barHeld && e.buttons === 0) endHold(); }, true);
  window.addEventListener("blur", endHold);
  // hidden tab: time stops (rAF stops; the first visible frame continues from the paused time, ICX-HIDDEN)
  let hiddenAt = -1;
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { hiddenAt = clock(); return; }
    const gone = hiddenAt >= 0 ? clock() - hiddenAt : 0;
    hiddenAt = -1;
    if (dip) dip.t0 += gone;                            // (Sol C3-1 #2) a dip resumes where it paused
    if (xf) xf.t0 += gone;                              // (Sol FLICKER2-1 #2) so does the content skip's crossfade
    if (sDip) sDip.t0 += gone;                          // (SCRUB) the scrub's dip and the arrival too
    if (sIntro) sIntro.t0 += gone;
    if (wait) wait += gone;
    lastDipAt += gone;
    lastNow = clock();
    wake();
  });

  /* ---------------- SCRUB: the follower (ported from the live site, main 652d12a): shown time chases the scroll's ---------------- */
  // v2.2/v2.3 (Daniel: "something smooth but responsive so u still feel like ur scrolling a website"; "id rather it smooth
  // and a bit draggy than super rushed"): the stage's speed aims at the gap (63 % of it every TAU), never faster than it
  // could still stop in, eased in and out (TV, ACC), never above 3x (VMAX; a seam's own CAP is eased into). Forward never
  // skips; only a one-frame JUMP (an explicit jump) or a long way back (REWIND, once the scroll paused) dips and lands.
  const TAU = 0.25, TV = 0.08, ACC = 9, VMAX = 3, A0 = 0.02, S_JUMP = 2.5, REWIND = 8, DIR_EPS = 0.015;
  function sCapAt(s, v, t) {
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
  function follow(e, v, dt, capOf = null) {
    for (let t = dt; t > 1e-9; ) {
      const h = Math.min(t, 1 / 240);
      t -= h;
      const a = Math.abs(e), dir = e > 0 ? -1 : 1;
      if (a < 1e-9) return [0, 0];
      const cap = capOf ? capOf(e, v) : VMAX;
      const sp = v * dir;
      if (sp > 0 && sp * sp >= 1.8 * ACC * a) v -= dir * Math.min(sp, ((sp * sp) / (2 * a)) * h);   // brakes onto the target
      else {
        const vg = dir * Math.min(cap, (a + A0) / TAU, Math.sqrt(2 * ACC * a));
        v += clamp((vg - v) / TV, -ACC, ACC) * h;
      }
      if (Math.abs(v) > cap) v = Math.sign(v) * Math.max(cap, Math.abs(v) - 3 * ACC * h);
      const e1 = e + v * h;
      if (Math.sign(e1) !== Math.sign(e)) return [0, 0];       // it never passes a still target
      e = e1;
    }
    return [e, v];
  }
  let sTarget = 0, sVel = 0, sIntro = null, sDip = null, sJump = null, sPrev = -1;
  let dirSign = 1, dirAnchor = 0, sMoved = 0, navJumpAt = -1;
  // where the target is, as its segment and local time (a rebuild or a resize changes the map, not the story)
  function targetPlace() { const sg = TL.segs[segAt(clamp(sTarget, 0, TL.T1))]; return { id: sg.id, u: sTarget - sg.T0 }; }
  // put the scroll position where the map gives that same segment-local time (the map is monotonic: bisection)
  function anchorScroll(tp) {
    const pl = tp && placeIn(tp.id, tp.u);
    if (!pl) return;
    const T = clamp(pl.sg.T0 + pl.u, 0, TL.T1);
    if (T <= mapScroll(0) + 1e-6) {
      if (pl.moved && Math.abs(window.scrollY - Math.round(storyTop)) >= 1) window.scrollTo(0, Math.max(0, Math.round(storyTop)));
      return;
    }
    let lo = 0, hi = storyTop + MAP.L;
    for (let k = 0; k < 40; k++) { const mid = (lo + hi) / 2; if (mapScroll(mid) < T) lo = mid; else hi = mid; }
    if (Math.abs(window.scrollY - hi) >= 1) window.scrollTo(0, Math.round(hi));
    readerY = window.scrollY;
  }
  const pastStory = () => (MAP && readerY > storyEnd() + 1 ? readerY - storyEnd() : null);
  // an explicit jump may dip forwards too; scrolling never does
  function navScrollTo(y) { navJumpAt = clock(); window.scrollTo(0, y); readerY = window.scrollY; wake(); }
  // the stage at scroll y at once (a mode flip, a restore): no move, no replay
  function scrubPlace(y) {
    if (Math.abs(window.scrollY - y) >= 1) window.scrollTo(0, Math.max(0, Math.round(y)));
    readerY = window.scrollY;
    sTarget = shown = mapScroll(window.scrollY); sVel = 0; sIntro = null; sJump = null;
    if (sDip) { sDip = null; clearDip(); }
    dirSign = 1; dirAnchor = sTarget;
    phase = window.scrollY > storyEnd() + 1 ? "released" : "rest";
    lastDrawn = null; capIdx = -1;
    render(shown); updateCaptions(shown, true);
    wake();
  }
  // an explicit jump to checkpoint k (the menu, the logo, a deep link's popstate, focus): dest now, the scroll to its hold,
  // the landing (one history write by story-url.js) once the stage has caught up there
  function scrubJump(k, source) {
    const y = trackY(k);
    if (phase === "rest" && kR === k && kD === k && Math.abs(window.scrollY - y) <= 1) return;   // ICX-JUMP.0
    sJump = { k, source };
    if (kD !== k) { kD = k; srcD = source; emit("dest", payload(k, source)); }
    navScrollTo(y);
  }
  // the landing glue (ICX-SCRUB): a final landing is the stage caught up with a still scroll inside checkpoint k's hold,
  // k not the one last landed (or an explicit jump's target): dest + one final onLand (story-url.js: one replaceState, a
  // jump's one pushState), one announcement. Holds the stage crosses while moving are previews only (ICX-HL.3).
  function scrubLand(y, moving) {
    if (y > storyEnd() + 1) {
      if (phase !== "released") { phase = "released"; sJump = null; kR = kD = last(); }
      return;
    }
    const k = holdAtT(shown);
    if (moving) {
      phase = "transition";
      if (k >= 0 && k !== sPrev) { sPrev = k; emit("dest", payload(k, "free", { preview: true })); }
      return;
    }
    phase = "rest";
    if (k < 0) return;                                  // still mid-ramp: rendered stays the last landed checkpoint
    const j = sJump && sJump.k === k ? sJump : null;
    if (k === kR && kD === k && !j) return;
    sJump = null; sPrev = k;
    const src = j ? j.source : "settle";
    if (kD !== k) { kD = k; srcD = src; emit("dest", payload(k, src)); }
    kR = k;
    announce(k);
    emit("land", payload(k, src, { final: true }));
  }
  function scrubTick() {
    const now = clock();
    const dt = clamp(now - lastNow, 0.0005, 0.05);
    lastNow = now;
    const y = window.scrollY;
    const tNew = mapScroll(y), step = Math.abs(tNew - sTarget);
    if (step > 1e-4) sMoved = now;
    // (a PageDown is a one-frame step of ~2.7 s: forwards that plays; a jump dips going back, or when asked for one)
    const jumped = step > S_JUMP && (tNew < sTarget || now - navJumpAt < 0.5);
    sTarget = tNew;
    let busy = false;
    if (sIntro) {
      // the arrival plays at natural speed to the hold frame; the first genuine scroll ends it
      const it = Math.min(TL.HOLD, (now - sIntro.t0) * sIntro.rate);
      shown = it;
      sVel = it < TL.HOLD ? sIntro.rate : 0;
      if (Math.abs(y - sIntro.y0) > 1) sIntro = null;
      else { busy = it < TL.HOLD; if (!busy) sIntro = null; }
    }
    if (!sIntro) {
      if (sDip) {
        const u = now - sDip.t0;
        if (u < CFG.DIP_OUT) { setDip(1 - u / CFG.DIP_OUT); scrubDipBand(1 - u / CFG.DIP_OUT); }
        else {
          if (!sDip.jumped) { shown = sTarget; sVel = 0; sDip.jumped = true; }
          const a = Math.min(1, (u - CFG.DIP_OUT) / CFG.DIP_IN);
          setDip(a); scrubDipBand(a);
          if (a >= 1) { sDip = null; clearDip(); }
        }
        busy = true;
      } else if (Math.abs(sTarget - shown) > S_JUMP && !(shown < TL.HOLD && sTarget <= TL.HOLD + 0.1) &&
          (jumped || (sTarget < shown && now - sMoved > 0.12 && shown - sTarget > REWIND))) {
        sDip = { t0: now, jumped: false, band0: bandOnAt(shown) };
        busy = true;
      } else {
        const [e, v] = follow(shown - sTarget, sVel, dt, (e1, v1) => sCapAt(sTarget + e1, v1, sTarget));
        shown = sTarget + e; sVel = v;
        if (Math.abs(e) < 0.0006 && Math.abs(v) < 0.006) { shown = sTarget; sVel = 0; } else busy = true;
      }
    }
    // the direction gate: hysteresis (DIR_EPS) on the target's movement; forwards restores the hand and the presses
    if (sIntro) { dirSign = 1; dirAnchor = sTarget; }
    else if (dirSign > 0) { if (sTarget < dirAnchor - DIR_EPS) { dirSign = -1; dirAnchor = sTarget; } else if (sTarget > dirAnchor) dirAnchor = sTarget; }
    else if (sTarget > dirAnchor + DIR_EPS) { dirSign = 1; dirAnchor = sTarget; } else if (sTarget < dirAnchor) dirAnchor = sTarget;
    const gTo = dirSign > 0 ? 1 : 0;
    FX.gate.press = gTo;
    const g0 = FX.gate.cursor;
    if (g0 !== gTo) { FX.gate.cursor = gTo > g0 ? Math.min(1, g0 + dt / 0.15) : Math.max(0, g0 - dt / 0.15); busy = true; }
    scrubLand(y, busy);
    if (window.__fxTrace) window.__fxTrace.push([now, shown, sTarget, phase, FX.gate.cursor]);   // test hook (off unless set)
    const key = `${shown.toFixed(5)}|${FX.gate.cursor.toFixed(3)}|${FX.gate.press}`;
    if (key !== lastDrawn) { lastDrawn = key; render(shown); }
    updateCaptions(shown, false);
    if (busy) raf = requestAnimationFrame(tick);
  }
  // C5's band rule for the scrub's dip: a cut that turns the Ride's band on or off fades the band with the stage
  function scrubDipBand(a) {
    const to = bandOnAt(sDip && sDip.jumped ? shown : sTarget);
    if (sDip && sDip.band0 !== to && a < 0.999) band.style.opacity = a.toFixed(3); else band.style.removeProperty("opacity");
  }

  /* ---------------- the loop: one rAF; sleeps when there is nothing to do ---------------- */
  function wake(t0) {
    if (!raf && TL && motion()) { lastNow = t0 != null ? Math.min(t0, clock()) : clock(); raf = requestAnimationFrame(tick); }
  }
  function tick() {
    raf = 0;
    if (!TL || held) return;
    if (MAP) return scrubTick();
    const now = clock();
    const dt = clamp(now - lastNow, 0, 0.1);
    lastNow = now;
    if (xf) xfStep(now);
    if (dip) dipStep(now);
    else if (run) runStep(dt);
    if (!dip && wait && now >= wait) { wait = 0; decide(); }
    // never stranded mid-move with nothing to play (ICX-REST.2)
    if (phase === "transition" && !run && !dip && !wait) decide();
    if (phase === "transition" && !run && !dip && !wait) enforceRest(kD);
    // BT-1 backstop: a foreign scroll seen on the frame even if its event is late
    if (ack && performance.now() > ack.until) ack = null;
    if (CP.length && !dip && !ack && phase !== "free" && phase !== "released" && Math.abs(window.scrollY - trackY(kR)) > CFG.ACK_TOL) foreign(window.scrollY);
    let busy = !!(run || dip || wait || xf);
    // the direction gate: the hand never walks backwards (it fades while the story runs back) and presses squash only
    // forwards; it comes back on the way to rest
    const gTo = run && run.dir < 0 ? 0 : 1;
    FX.gate.press = gTo;
    const g0 = FX.gate.cursor;
    if (g0 !== gTo) {
      FX.gate.cursor = gTo > g0 ? Math.min(1, g0 + dt / 0.15) : Math.max(0, g0 - dt / 0.15);
      busy = true;
    }
    if (window.__fxTrace) window.__fxTrace.push([now, shown, run ? run.to : shown, phase, FX.gate.cursor]);   // test hook (off unless set)
    const k = `${shown.toFixed(5)}|${FX.gate.cursor.toFixed(3)}|${FX.gate.press}`;
    if (k !== lastDrawn) { lastDrawn = k; render(shown); }
    updateCaptions(shown, false);
    if (railOn && !railIn && !(run && run.intro)) railReveal();   // the rail draws in once the arrival has handed over
    if (busy) raf = requestAnimationFrame(tick);
  }
  // story time between frames, for state(): the run's own clock (the shown frame is at most one frame behind it)
  function liveT() {
    if (!run || document.hidden) return shown;
    const x = shown + run.dir * Math.min(run.rate, capAt(shown)) * clamp(clock() - lastNow, 0, 0.1);
    return (run.to - x) * run.dir <= 0 ? run.to : x;
  }

  // focus that reaches an idle caption (a screen reader's cursor) brings that beat up, so focus is never invisible
  capsEl.addEventListener("focusin", (e) => {
    if (!TL || !motion()) return;
    const c = e.target.closest && e.target.closest(".beat-copy");
    if (!c || c.classList.contains("is-on")) return;
    const k = CP.indexOf(c.getAttribute("data-copy"));
    if (k >= 0) jump(k, "focus");                      // a focus landing replaces, never pushes (ICX-HIST, C4-engine)
  });

  /* ---------------- start, refresh (theme / layout / motion preference / late fonts), resize, teardown ---------------- */
  let layoutKey = "";
  const key = () => `${theme()}|${desktop() ? "desk" : "phone"}|${preset()}|${motion() ? "motion" : "calm"}`;
  const navType = () => { try { return performance.getEntriesByType("navigation")[0].type; } catch (e) { return "navigate"; } };
  function mode() {
    if (!motion()) return doc.classList.contains("calm") ? (classicPref === true ? "classic" : "calm") : "static";
    return !TL ? "static" : TL.isDesk ? "desktop" : TL.p === "tall" ? "phone" : "tablet";
  }
  function modeChanged() {
    const m = mode();
    if (m === lastMode) return;
    lastMode = m;
    emit("mode", { mode: m, destinations: destinations() });
  }
  function resetEngine() {
    cancelAnimationFrame(raf); raf = 0;
    endFree();
    // (INT-4, Sol HIGH / Astra MEDIUM) a rebuild mid-dip (a theme switch in its fade-in) drops the dip: its layers'
    // opacity goes back to rest with it, or the stage came to rest nearly invisible
    clearDip();
    run = null; dip = null; wait = 0; passK = -1; ack = null; swallow = -1;
    kR = kD = 0; phase = "rest";
    sDip = null; sIntro = null; sJump = null; sVel = 0; sPrev = -1;
  }
  function teardown() {
    // everything the story put on the page goes: the mounts, the page-level layers' styles, the global classes, the
    // dip, pending frames and timers (the stacked page must not inherit any of it)
    resetEngine();
    clearTimeout(capTimer);
    held = false;
    clearStage();
    TL = null; OV = null; L = null; TRACK = null; MAP = null; CP = []; RE = [];
    lastG = {}; curSeg = -1; lastDrawn = null; capIdx = -1;
    doc.classList.remove("on-band", "past-band");
    pin.setAttribute("class", "pin");
    pin.style.removeProperty("opacity");
    clearDip();
    pin.style.removeProperty("--cap-top");
    for (const v of fitVars) pin.style.removeProperty(v);
    clearOfferVars();
    fitCapH = -1; fitEndH = -1; endKv = -1;
    if (capRO) capRO.disconnect();
    for (const [el, props] of [[field, ["opacity", "clip-path"]], [shade, ["opacity"]], [band, ["display", "clip-path"]],
      [stageCol, ["opacity", "visibility"]], [stageWrap, ["transform"]], [track, ["height"]]]) for (const p of props) el.style.removeProperty(p);
    label.removeAttribute("data-mode");
    label.style.removeProperty("transform");
    FX.gate.cursor = 1; FX.gate.press = 1;
    railTeardown();
    placeCopies([]);
  }
  // the first landing (ICX-JUMP.3): a deep link plays its chapter's demo from its rest-entry, a reload or a history
  // visit lands on its rest frame, a fresh arrival at the top plays Make's arrival to its hold frame. No history.
  // (judge C3-1 #1) with scroll restoration manual, the reading place of a reload or a history visit with no chapter
  // hash is the engine's: saved on pagehide (the checkpoint in the pin, or the distance below it) and re-applied by
  // init() after layout. Per tab (sessionStorage), this page only; a new visit (navigate) never reads it.
  const PLACE_KEY = "fe-story-place";
  const entryK = () => { const s = history.state; return s && typeof s === "object" && s.k ? s.k : null; };   // story-url.js's entry key
  window.addEventListener("pagehide", () => {
    try {
      if (!TL || !CP.length || !motion()) { sessionStorage.removeItem(PLACE_KEY); return; }
      if (MAP) {                                        // (SCRUB) a reload keeps the pixel, as the live site did
        sessionStorage.setItem(PLACE_KEY, JSON.stringify({ y: Math.round(window.scrollY), w: window.innerWidth,
          path: location.pathname, cp: CP.join(), h: location.hash, k: entryK() }));
        return;
      }
      const below = phase === "released" || window.scrollY > storyEnd() + 1;
      const p = below ? { past: Math.round(window.scrollY - storyEnd()) } : { beat: CP[phase === "free" ? nearestK(window.scrollY) : kR] };
      p.path = location.pathname; p.cp = CP.join();
      p.h = location.hash; p.k = entryK();             // (INT5-fix 5) the entry left: its URL's chapter and its key
      sessionStorage.setItem(PLACE_KEY, JSON.stringify(p));
    } catch (e) { /* storage off: the page starts on its first chapter */ }
  });
  function savedPlace() {
    try { const p = JSON.parse(sessionStorage.getItem(PLACE_KEY) || "null"); sessionStorage.removeItem(PLACE_KEY); return p; } catch (e) { return null; }
  }
  // RELOAD: story-url.js keeps the reader's place inside a native section ({story, y, w, m}) in the entry's history.state and,
  // when the page is left, in sessionStorage "fe-story-held" (+ path and the entry's state key k). A reload or history visit
  // to that same chapter, in the same mode at the same width, comes back to that pixel, not the chapter's anchor (the
  // shipped site, with no chapter hashes, kept the pixel). A fresh deep link lands on the anchor. Same rule as story-url.js
  // heldY (calm / classic restore there); kept in both because this runs before the engine's first frame.
  function heldY(slug) {
    const nt = navType();
    if (nt !== "reload" && nt !== "back_forward") return null;
    const fits = (p) => !!p && p.story === slug && typeof p.y === "number" && p.w === window.innerWidth && p.m === mode();
    const s = history.state, k = s && typeof s === "object" && s.k ? s.k : null;
    let p = null;
    try { p = JSON.parse(sessionStorage.getItem("fe-story-held") || "null"); } catch (e) { p = null; }
    if (fits(p) && p.path === location.pathname && (p.k || null) === k) return Math.max(0, Math.round(p.y));
    if (s && typeof s === "object" && fits(s)) return Math.max(0, Math.round(s.y));
    return null;
  }
  function init() {
    // the engine owns the reading place: the browser's own scroll restoration on a reload or a history visit would land
    // after this one, read as a foreign scroll and settle elsewhere (not a history write: no entry, no URL change)
    try { if ("scrollRestoration" in history) history.scrollRestoration = "manual"; } catch (e) { /* ignore */ }
    let h = "";
    try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) { h = ""; }
    const b = LEGACY[h] || BEATS.find((x) => SLUG[x] === h) || null;
    const nt = navType();
    kR = kD = 0; shown = RE[0][1]; phase = "rest";
    const saved = savedPlace();                        // read once: savedPlace() removes the record
    if (MAP && (!b || CP.includes(b))) return scrubInit(b, nt, saved);
    if (b && CP.includes(b)) {
      const k = CP.indexOf(b);
      // (INT5-fix 5; Sol + Astra INT-5) a reload / history visit of the SAME entry the reader left below the story (scrolled
      // past it into the footer: the URL still names the chapter it was released from): that same distance past it, not
      // the chapter's rest frame. A fresh visit (navigate), another entry or another URL lands on the chapter.
      if (nt !== "navigate" && saved && saved.past != null && saved.cp === CP.join() && saved.path === location.pathname &&
          saved.h === location.hash && (saved.k || null) === entryK()) {
        phase = "released"; kR = kD = last(); shown = RE[kR][1];
        keepPast(Math.max(2, saved.past));
        initial = { index: bi(kR), source: "restored" };
        return;
      }
      kR = kD = k; srcD = "init";
      initial = { index: BEATS.indexOf(b), source: nt === "navigate" ? "init" : nt };
      syncScroll(trackY(k));
      if (nt === "navigate") { shown = RE[k][0]; contentRun(); if (k === 0) run.intro = true; }
      else shown = RE[k][1];
      emit("land", payload(k, "init", { final: true }));
      return;
    }
    if (b) {                                           // a native row in this layout: the anchor's own section
      const sec = document.getElementById(SLUG[b]);
      const held = heldY(SLUG[b]);                     // a reload / history visit inside it: the reader's pixel (RELOAD)
      if (held != null) window.scrollTo(0, held);
      else if (sec) window.scrollTo(0, Math.max(0, Math.round(sec.getBoundingClientRect().top + window.scrollY - (L ? L.hh : 0))));
      initial = { index: BEATS.indexOf(b), source: "native" };
      return;
    }
    if (saved && nt !== "navigate" && saved.path === location.pathname) {
      if (saved.past != null && saved.cp === CP.join()) {   // below the pin: the same distance past it
        phase = "released"; kR = kD = last(); shown = RE[kR][1];
        keepPast(Math.max(2, saved.past));
        initial = { index: bi(kR), source: "restored" };
        return;
      }
      if (saved.beat && CP.includes(saved.beat)) {          // in the pin: that checkpoint's rest frame
        kR = kD = CP.indexOf(saved.beat); shown = RE[kR][1];
        syncScroll(trackY(kR));
        initial = { index: bi(kR), source: "restored" };
        return;
      }
    }
    const y = window.scrollY;
    if (y < 4 && nt === "navigate") { shown = 0; contentRun(); run.intro = true; initial = { index: 0, source: "arrival" }; return; }
    if (y > storyEnd() + 1) { phase = "released"; kR = kD = last(); shown = RE[kR][1]; initial = { index: bi(kR), source: "restored" }; return; }
    kR = kD = nearestK(y); shown = RE[kR][1];
    syncScroll(trackY(kR));
    initial = { index: bi(kR), source: "restored" };
  }
  // (SCRUB) the first place: the reader's own pixel on a reload / history visit of the same entry at the same width (the
  // live site kept it); a deep link to a pinned row: its hold (ICX-SCRUB.6); a fresh arrival at the top: Make's arrival
  function scrubInit(b, nt, saved) {
    const k = b ? CP.indexOf(b) : -1;
    const same = !!saved && nt !== "navigate" && saved.path === location.pathname && saved.cp === CP.join() &&
      typeof saved.y === "number" && saved.w === window.innerWidth && saved.h === location.hash && (saved.k || null) === entryK();
    if (same) { window.scrollTo(0, Math.max(0, saved.y)); kR = holdK(window.scrollY); initial = { index: bi(kR), source: "restored" }; return; }
    if (k >= 0) {
      window.scrollTo(0, trackY(k));
      kR = kD = k;
      initial = { index: BEATS.indexOf(b), source: nt === "navigate" ? "init" : nt };
      emit("land", payload(k, "init", { final: true }));
      return;
    }
    if (window.scrollY < 4 && nt === "navigate") { sIntro = { t0: clock(), rate: 1, y0: window.scrollY }; shown = 0; kR = 0; initial = { index: 0, source: "arrival" }; return; }
    kR = holdK(window.scrollY);
    initial = { index: bi(kR), source: "restored" };
  }
  // the engine's state from the scroll position as it is now (k: the checkpoint already landed, else the nearest hold)
  function scrubSync(k) {
    readerY = window.scrollY;
    sTarget = mapScroll(readerY);
    if (!sIntro) { shown = sTarget; sVel = 0; } else sVel = sIntro.rate;
    dirSign = 1; dirAnchor = sTarget;
    const rel = readerY > storyEnd() + 1;
    kR = kD = rel ? last() : k != null && k >= 0 ? k : holdK(readerY);
    sPrev = kR;
    phase = rel ? "released" : sIntro ? "transition" : "rest";
  }
  function scrubStart(firstLoad, keep) {
    if (keep && keep.scrub && keep.cp === CP.join()) {
      // the same story time under the new map (a theme switch, late fonts, a refit): nothing moves; below the story, the
      // same distance past it
      if (keep.past != null) keepPast(keep.past); else if (!keep.intro) anchorScroll(keep.tp);
      sIntro = keep.intro;
      scrubSync(keep.kR);
      const pl = placeIn(keep.id, keep.u);
      if (pl) { shown = clamp(pl.sg.T0 + pl.u, pl.sg.T0, pl.sg.T1); sVel = keep.vel; }
      FX.gate.cursor = keep.cursor; dirSign = keep.dirSign;
      sJump = keep.jump;
      if (sJump) kD = sJump.k;
      if (phase !== "released" && Math.abs(shown - sTarget) > 1e-6) phase = "transition";
    } else {
      if (firstLoad) init();
      scrubSync(firstLoad ? kR : null);
    }
    FX.gate.press = dirSign > 0 ? 1 : 0;
  }
  // keep: a snapshot of where the story is (refresh), restored onto the rebuilt timeline when the checkpoints are the
  // same (a theme change, late fonts, a phone's caption refit). Across a layout change (a new destination table) the
  // reading place is restorePlace's job.
  function start(firstLoad, keep, pre) {
    dropRebuild(pre);                                   // any other (re)start supersedes a theme rebuild in flight
    // (INT5-fix 3; Astra INT-5) a native row's smooth scroll still in flight (the tablet menu's Price, then the theme
    // toggled): the reader asked to go there, so the rebuild carries it through to its target. The snapshot's place is
    // the scroll's mid-way FREE / release, and restoring it (an instant scroll) ended the smooth one at the pinned origin
    // while story-url.js's arrival still pushed the target's URL.
    const nat = native && typeof native.aim === "number" ? native : null;
    try {
      resetEngine();
      layoutKey = key();
      if (!motion()) {
        // (calm / static: the browser keeps the place itself, as it always did)
        try { if ("scrollRestoration" in history) history.scrollRestoration = "auto"; } catch (e) { /* ignore */ }
        teardown(); doc.classList.add("fx-ready"); seqEnable(); modeChanged(); return;
      }
      if (desktop()) placeCopies(BEATS);
      else if (preset() === "tall") placeCopies(TALL_PIN, true);
      else placeCopies(PHONE_BEATS);
      if (capRO) {
        capRO.disconnect();
        if (preset() === "tall") for (const b of TALL_BEATS) { const c = capFor(b); if (c) capRO.observe(c); }
      }
      build(pre);
      railMeasure();
      held = false;
      FX.gate.cursor = 1; FX.gate.press = 1;
      if (MAP) scrubStart(firstLoad, keep);
      else if (keep && keep.cp === CP.join()) {
        kR = Math.max(0, CP.indexOf(keep.beat)); kD = Math.max(0, CP.indexOf(keep.dest));
        const pl = placeIn(keep.id, keep.u);
        if (nat) {
          // the engine as the native jump had it (its origin's rest; released if it began below), the page left to the
          // scroll, which is asked again for the same target (smooth: it carries on from wherever it is now)
          kR = kD = nat.phase0 === "released" ? last() : nat.k; shown = RE[kR][1]; phase = nat.phase0 === "released" ? "released" : "rest";
          window.scrollTo({ top: nat.aim, behavior: "smooth" });
          startNative(nat.aim);
        } else if (keep.phase === "released") {
          phase = "released"; kR = kD = last(); shown = RE[kR][1];
          if (keep.past != null) keepPast(keep.past);
        } else if (keep.phase === "rest" || !pl) {
          shown = RE[kR][1]; phase = "rest"; kD = kR; syncScroll(trackY(kR));
        } else {
          shown = clamp(pl.sg.T0 + pl.u, 0, TL.T1); phase = "transition";   // the move carries on from the same frame
          syncScroll(trackY(kR));
          lastDipAt = -1e9;
          decide();
          // (INT-4) the arrival carries on as the arrival across a rebuild (a theme switch mid-arrival): the rail draws in
          // only once it hands over, as on the base
          if (keep.intro && run && run.purpose === "content" && kR === 0) run.intro = true;
        }
      } else if (firstLoad) init();
      else { kR = kD = 0; shown = RE[0][1]; }
      curSeg = -1; lastDrawn = null; capIdx = -1;
      render(shown);
      updateCaptions(shown, true);
      if (!(run && run.intro)) railReveal();            // an anchor, a reload or a rebuild: the rail is up at once
      doc.classList.add("fx-ready");
      seqEnable();
      modeChanged();
      wake();
    } catch (err) {
      doc.classList.remove("motion", "calm");
      if (pre) for (const m of Object.values(pre.m)) m.rootEl.remove();
      try { teardown(); } catch (e) { /* ignore */ }
      seqEnable();
      console.warn("The story fell back to its static layout:", err);
    }
  }
  function snapshot() {
    if (!TL || !CP.length) return null;
    if (MAP) {
      const sc = TL.segs[segAt(clamp(shown, 0, TL.T1))];
      return { cp: CP.join(), scrub: true, beat: CP[kR], dest: CP[kD], phase: phase === "released" ? "released" : "rest",
        id: sc.id, u: shown - sc.T0, vel: sVel, intro: sIntro ? { ...sIntro } : null, cursor: FX.gate.cursor, dirSign,
        tp: sIntro ? null : targetPlace(), past: pastStory(), kR, jump: sJump };
    }
    const sg = TL.segs[segAt(shown)];
    return { cp: CP.join(), beat: CP[kR], dest: CP[kD], phase, id: sg.id, u: shown - sg.T0, intro: !!(run && run.intro),
      past: phase === "released" ? readerY - storyEnd() : null };
  }
  function refresh() { start(false, snapshot()); }
  // C5b (the circle starts on the press, Daniel's "feel instant"): mounting the scenes is most of a rebuild (16-28 ms in
  // Chromium, 55-88 ms in WebKit, measured 2026-10-16), and inside the view-transition update it held the circle back by
  // that much. So a theme switch inside a circle reveal mounts the new theme's scenes AFTER the circle's first frame, a
  // few per task between frames, hidden beside the old ones, then swaps them in with the same refresh as before (the
  // story's place carried over). Until the swap the old scenes are still on the stage, outside the circle: before any
  // frame that could show the circle reaching the stage (or the overlay card), the rest is done at once, so no frame
  // shows a scene in the old palette inside the circle. An instant switch (no circle) rebuilds synchronously, as before.
  const RB_BUDGET = 8;                                // ms of mounting per task
  const RB_SLACK = 34;                                // ms: the next paint may come up to two frames after a task ends
  const revealEase = FX.bezier(0.55, 0, 0.25, 1);     // theme.js's reveal: 420 ms, cubic-bezier(.55,0,.25,1)
  let rb = null;                                      // the theme rebuild in flight
  function dropRebuild(keep) {
    if (!rb) return;
    const r = rb;
    rb = null;
    r.dead = true;
    cancelAnimationFrame(r.raf); clearTimeout(r.timer);
    if (r !== keep) for (const m of Object.values(r.m)) m.rootEl.remove();
  }
  const sameLayout = () => layoutKey.slice(layoutKey.indexOf("|")) === key().slice(key().indexOf("|"));
  function themeRebuild() {
    dropRebuild();
    if (!TL || !CP.length || !motion() || !doc.classList.contains("vt-theme") || !sameLayout()) { refresh(); return; }
    const r = (rb = { m: {}, t0: performance.now(), todo: null, touch: 0, raf: 0, timer: 0, frames: 0, dead: false });
    r.raf = requestAnimationFrame((ts) => rebuildFrame(r, ts));
  }
  // (Sol C5b-1 HIGH) a frame callback stays pending while the rebuild runs, so EVERY frame checks before it paints: if
  // the circle could reach the stage by this frame, the rest is done here, before the paint. The mounting itself runs in
  // tasks between frames, from the second frame on (the first is the new snapshot's capture, the second the circle's
  // first frame, where its start time is set: no work sits in front of either).
  function rebuildFrame(r, ts) {
    if (r.dead || r !== rb) return;
    if (++r.frames >= 2 && !r.todo && !rebuildPrep(r)) return;
    if (r.todo && (!doc.classList.contains("vt-theme") || Math.max(ts, performance.now()) + 4 - r.t0 >= r.touch)) { rebuildStep(r, true); return; }
    r.raf = requestAnimationFrame((t) => rebuildFrame(r, t));
    if (r.todo && !r.timer) r.timer = setTimeout(() => { r.timer = 0; rebuildStep(r, false); });
  }
  function rebuildPrep(r) {
    if (!TL || !motion() || !sameLayout()) { refresh(); return false; }
    const p = preset();
    Object.assign(r, { p, s0: stage.clientWidth / SIZE[p][0], dark: theme() === "dark", touch: circleReach() });
    r.todo = mountNames(desktop(), p).map((n) => () => { const m = mount(n, r.p, r.s0); m.show(false); r.m[n] = m; });
    return true;
  }
  // ms after the switch at which the circle's outer edge could first reach the stage or a card over it (an early bound:
  // t0 is before the circle's start, the end radius is theme.js's largest)
  function circleReach() {
    const x = parseFloat(doc.style.getPropertyValue("--vt-x")), y = parseFloat(doc.style.getPropertyValue("--vt-y"));
    if (!Number.isFinite(x) || !Number.isFinite(y)) return 0;
    const far = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)), end = far + 222;
    let d = Infinity;
    for (const el of [stage, ...over.children]) {
      const b = el.getBoundingClientRect();
      if (b.width && b.height) d = Math.min(d, Math.hypot(Math.max(b.left - x, 0, x - b.right), Math.max(b.top - y, 0, y - b.bottom)));
    }
    let ms = 0;
    while (ms < 420 && revealEase(ms / 420) * end < d) ms += 4;
    return ms;
  }
  // all: finish now (a frame that could show the circle on the stage, or the circle is gone). Otherwise mount for about
  // RB_BUDGET ms, and keep going when the circle could reach the stage within RB_SLACK (fewer last-moment stalls)
  function rebuildStep(r, all) {
    if (r.dead || r !== rb || !r.todo) return;
    const t = performance.now(), now = () => performance.now();
    while (r.todo.length) {
      r.todo.shift()();
      if (r.dead) return;
      const late = all || !doc.classList.contains("vt-theme") || now() + RB_SLACK - r.t0 >= r.touch;
      if (!late && r.todo.length && now() - t >= RB_BUDGET) return;      // the pending frame callback carries on
    }
    start(false, snapshot(), r);
  }
  // ICX-SETTLE-7: every resize re-measures at once (no debounce for the re-snap); the layout itself follows, debounced
  function onGeometry() {
    if (!TL || !CP.length || !motion() || MAP) return;  // (SCRUB: the debounced relayout re-anchors the map)
    const bp = Math.max(1, Math.round(pin.clientHeight));
    if (bp === beatPx) return;                          // 100svh did not move (a phone's bars): nothing to re-snap
    const past = phase === "released" ? readerY - storyEnd() : null;
    buildTrack();
    geomAt = clock();
    if (past != null) keepPast(past);
    else if (phase !== "free") syncScroll(trackY(kR));
  }
  let resizeT = 0;
  window.addEventListener("resize", () => {
    onGeometry();
    clearTimeout(resizeT);
    resizeT = setTimeout(() => {
      // a mode change (a rotation across the short-touch line, 640 or 1024 px) keeps the reader's place (ICX-DEST.4)
      const pl = readingPlace();
      noteView();
      if (syncMode() || key() !== layoutKey) { refresh(); restorePlace(pl); return; }
      if (!TL) return;
      // phones (Sol mobile P2): the browser's bars showing or hiding change the height only, by less than ~150 px. The
      // pin uses the stable 100svh, so there is nothing to re-lay; a width (orientation) or real height change re-lays.
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
    if (MAP) {                                          // (SCRUB) the same story time under the new map, or past it
      const tp = sIntro ? null : targetPlace(), pst = pastStory();
      layout();
      if (MAP) {
        if (pst != null) keepPast(pst); else anchorScroll(tp);
        sTarget = mapScroll(window.scrollY);
      }
      lastDrawn = null;
      render(shown);
      wake();
      return;
    }
    const past = phase === "released" ? readerY - storyEnd() : null;
    layout();
    geomAt = clock();
    // the story stays where it is: on its checkpoint's track position, or the same distance below the pin
    if (past != null) keepPast(past);
    else if (phase !== "free") syncScroll(trackY(kR));
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
  // motion, no calm class) stays there (a change of the motion preference sets the mode, as it always did).
  // K1's classic view (setClassic) overrides the reduced-motion query; a short touch screen is calm either way.
  function syncMode(force) {
    if (!force && !doc.classList.contains("motion") && !doc.classList.contains("calm")) return false;
    const rm = classicPref != null ? classicPref : mq.matches;
    const short = !rm && shortTouch(), calm = rm || short;
    doc.classList.toggle("short-touch", short);
    if (calm === doc.classList.contains("calm") && !calm === doc.classList.contains("motion")) return false;
    doc.classList.toggle("calm", calm); doc.classList.toggle("motion", !calm);
    return true;
  }
  // (Sol round D P2; K1-fix) a mode change keeps the reader's place: the checkpoint they are on, or the section they are
  // reading. Taken BEFORE the classes flip (the stacked sections appear at once), applied after the rebuild. "The section
  // they are reading" is the one the rail shows as current: the last whose top is at or above 40 % of the viewport
  // (rail.js SPY_LINE, ICX-HL.4; phones have no rail, so the rule is repeated here, not imported). The section under the
  // bar was one chapter behind whenever the next section's top sat between the bar and that line.
  // (K1-fix2) Only on a SAME-SIZE mode change (the Classic switch, a motion-preference flip). A size change (a rotation,
  // a resize) keeps the section under the bar: the browser re-lays the sections before the resize event while scrollY
  // still holds the old number, so a line farther down reads the wrong section then. viewW/viewH: the size at the last
  // resize the debounced handler saw (or at load).
  const READ_LINE = 0.4;
  let viewW = window.innerWidth, viewH = window.innerHeight;
  const noteView = () => { viewW = window.innerWidth; viewH = window.innerHeight; };
  function readingPlace() {
    if (TL && motion() && CP.length && phase !== "released" && window.scrollY <= storyEnd() + 1) {
      if (MAP) {                                        // (SCRUB) the beat whose caption is up (the last one that had one)
        let b = TL.beats[capIdx];
        for (let j = capIdx; !b && j >= 0; j--) b = TL.beats[j];
        return { beat: CP.includes(b) ? b : CP[holdK(window.scrollY)], inStory: true };
      }
      return { beat: CP[phase === "free" ? nearestK(window.scrollY) : kR], inStory: true };
    }
    const beatOf = (el) => (el.classList.contains("beat") ? el.dataset.beat : null);
    const els = document.querySelectorAll(".beat:not(.is-moved), .site-footer");
    if (window.innerWidth !== viewW || window.innerHeight !== viewH) {
      const hb = header ? header.getBoundingClientRect().bottom : 0;
      for (const el of els) {
        const r = el.getBoundingClientRect();
        if (r.height > 0 && r.top <= hb + 1 && r.bottom > hb + 1) return { el, off: r.top, beat: beatOf(el) };
      }
      return null;
    }
    const line = window.innerHeight * READ_LINE;
    let cur = null, top = 0;
    for (const el of els) {
      const r = el.getBoundingClientRect();
      if (r.height > 0 && r.top <= line) { cur = el; top = r.top; }
    }
    return cur ? { el: cur, off: top, beat: beatOf(cur) } : null;
  }
  function restorePlace(pl) {
    if (!pl) return;
    // a checkpoint in the new layout: land on its rest frame (no move, no replay)
    if (pl.beat && TL && motion() && CP.includes(pl.beat)) { landAt(CP.indexOf(pl.beat)); return; }
    const hb = header ? header.getBoundingClientRect().bottom : 0;
    let y = null;
    if (pl.el && pl.el.isConnected && pl.el.getBoundingClientRect().height > 0) y = window.scrollY + pl.el.getBoundingClientRect().top - pl.off;
    else if (pl.beat) {
      const sec = $(`.beat[data-beat="${pl.beat}"]`);
      const sr = sec ? sec.getBoundingClientRect() : null;
      // its top under the bar, or lower when the section is so short that the next one would cross the reading line
      // (then the rail, and the next visit's readingPlace, would name the next section)
      if (sr && sr.height > 0) y = window.scrollY + sr.top - Math.max(hb, window.innerHeight * READ_LINE - sr.height + 1);
    }
    if (y == null) return;
    window.scrollTo(0, Math.max(0, Math.round(y)));
    readerY = window.scrollY;
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

  /* ---------------- FEStory: the engine's contract (PLAN § C3; C4, B5, B6 and K1 consume it) ---------------- */
  // destinations: ICX-DEST rows {beat, name, slug, anchor, kind: "pinned"|"native", rest, entry} for the current mode.
  // mode: desktop | tablet | phone | calm | classic | static. rendered / dest: BEATS indexes. phase: rest | transition |
  // dip | free | released. state(): {phase, dest, rendered, T, trackY, beat, dip, step, settles, mode, scrollend}.
  // goTo(target, {source}): target = a BEATS index, beat id, slug or legacy hash; source step | jump | init | popstate
  // (a native row is a smooth anchor scroll, instant in calm, ICX-JUMP.5; opts.y, native rows only: scroll to that offset
  // instead of the anchor, story-url.js's Back to a held native place).
  // onDest(fn): fn({index, beat, slug, source, preview?}) whenever dest changes (the highlight, ICX-HL.1; source "free"
  //   with preview: true is FREE's nearest, ICX-HL.3).
  // onLand(fn): fn({index, beat, slug, source: step | jump | settle | init | popstate | focus, final}) at every landing; final =
  //   rendered == dest after it (only a final landing writes history, ICX-HIST; pass-through landings carry final: false).
  // onModeChange(fn): fn({mode, destinations}). setClassic(on): K1's hook (true = calm layout, false = the story, null =
  //   follow prefers-reduced-motion); it keeps the reading place. initial: how the first landing happened.
  function goTo(target, opts) {
    const source = (opts && opts.source) || "jump";
    const b = typeof target === "number" ? BEATS[target] : LEGACY[target] || BEATS.find((x) => x === target || SLUG[x] === target);
    if (!b) return false;
    if (!TL || !motion() || !CP.includes(b) || held) {
      const sec = document.getElementById(SLUG[b]);
      if (!sec) return false;
      const hh = header ? header.getBoundingClientRect().height : 0;
      const smooth = motion() && !mq.matches;
      // the latest explicit jump wins (C4-engine), the reverse of stopNative: a pinned run or dip still in flight is
      // cancelled now, before its cut or arrival can land and pin the page back (an instant scroll ends the smooth one).
      // The engine goes FREE here, exactly as the native scroll's first event would make it: no cut, no landing, no
      // announce, no history from the cancelled move; the dip's fade is cleared (clearDip) and the settle plans afresh.
      if (TL && motion() && CP.length && !held && !MAP && (run || dip || wait) && phase !== "free" && phase !== "released") foreign(window.scrollY);
      if (MAP) { sJump = null; navJumpAt = -1; }        // (SCRUB) a native row: the page's own scroll, the stage follows
      nativeSeq++;                                      // a new native scroll: a cancelled one's residue guard no longer applies
      // opts.y (RELOAD): Back to a native entry lands on the pixel the reader left (story-url.js), not the anchor
      const to = opts && typeof opts.y === "number" ? opts.y : sec.getBoundingClientRect().top + window.scrollY - hh;
      window.scrollTo({ top: Math.max(0, Math.round(to)), behavior: smooth ? "smooth" : "instant" });
      if (smooth && TL && motion() && CP.length && !held && !MAP) startNative(Math.max(0, Math.round(to)));
      return true;
    }
    jump(CP.indexOf(b), source);
    return true;
  }
  const on = (kind) => (fn) => { listeners[kind].push(fn); return () => { const i = listeners[kind].indexOf(fn); if (i >= 0) listeners[kind].splice(i, 1); }; };
  function state() {
    const has = CP.length > 0;
    return { phase, dest: has ? bi(kD) : null, rendered: has ? bi(kR) : null, T: +liveT().toFixed(4), trackY: has ? trackY(kD) : null,
      beat: TL ? TL.beats[capIdx] ?? null : null, dip: !!(dip || sDip), step: run ? run.purpose : null, settles, mode: mode(), scrollend: HAS_SCROLLEND };
  }
  window.FEStory = Object.freeze({
    get destinations() { return destinations(); },
    get mode() { return mode(); },
    get rendered() { return CP.length ? bi(kR) : null; },
    get dest() { return CP.length ? bi(kD) : null; },
    get phase() { return phase; },
    get initial() { return initial; },
    state, goTo,
    onDest: on("dest"), onLand: on("land"), onModeChange: on("mode"),
    setClassic(v) { classicPref = v == null ? null : !!v; const pl = readingPlace(); syncMode(true); refresh(); restorePlace(pl); },
    CONFIG: CFG,
  });

  /* ---------------- test hooks (headless checks): pure seeks of the master, the timeline, the engine's state ---------------- */
  window.__site = {
    mounts,
    get TL() { return TL; },
    seekMaster(T) {
      held = true; run = null; wait = 0; dip = null; sDip = null; sIntro = null; clearDip();
      shown = T;
      render(T);
      updateCaptions(T, true);
      railReveal();
      return T;
    },
    release() { held = false; wake(); },
    map() {
      return {
        T0: 0, T1: TL.T1, H: TL.HOLD, desktop: TL.isDesk, preset: TL.p, scrollLen: TRACK ? TRACK.L : 0, storyTop: Math.round(storyTop), beatPx,
        segs: TL.segs.map((s) => ({ id: s.id, kind: s.kind, T0: +s.T0.toFixed(3), T1: +s.T1.toFixed(3) })),
        beats: TL.beats, switches: TL.switches.map(([b, t, w]) => (w == null ? [b, +t.toFixed(3)] : [b, +t.toFixed(3), w])), dests: destinations(),
        // (SCRUB) the scroll map's pieces, in the live site's own format (652d12a __site.map)
        scrub: !!MAP, pieces: MAP ? MAP.pieces.map((p) => ({ kind: p.kind, beat: p.beat, s0: Math.round(p.s0), s1: Math.round(p.s1), T0: +p.T0.toFixed(3), T1: +p.T1.toFixed(3) })) : null,
      };
    },
    scrollFor(beat) { return MAP ? scrollForBeat(beat) : null; },
    state() {
      if (MAP) return { shown, target: sTarget, vel: sVel, beat: TL ? TL.beats[capIdx] : null, intro: !!sIntro, dip: !!sDip, gate: { ...FX.gate }, phase };
      return { shown: liveT(), target: run ? run.to : shown, vel: run ? run.dir * run.rate : 0, beat: TL ? TL.beats[capIdx] : null, intro: !!(run && run.intro), dip: !!dip, gate: { ...FX.gate }, phase };
    },
    pinEl() { return pin; },
    setGate(c, p) { FX.gate.cursor = c; FX.gate.press = p; lastDrawn = null; },
    refresh() { refresh(); },
  };
})();
