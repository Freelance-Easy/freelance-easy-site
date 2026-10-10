/* =====================================================================================================================
   The seams (site v2.1): every hand-off between two pieces is one continuous move that starts on the outgoing piece's
   last frame and ends on the incoming piece's first frame, exactly. Pure functions of u (seconds into the seam), forward
   and backward. A seam = { DUR, B0?, seek(u), globals(u)? }; B0 is the incoming piece's local time where the seam hands
   over (its content already in). seek() shows/hides its two mounts, seeks only the mounts it shows, and writes only
   properties the pieces' own seeks rewrite on every frame (or its own layer's elements), so leaving a seam leaves
   nothing behind. globals(u) drives the page-level layers (the Ride's colour field and band, the stage's opacity, the
   overlay card and the mark) through site.js.
   v2.1, from the two Sol reviews: no blank or dead frame in any join. Make -> Look brings the REAL template cards in
   (never above their own size); Look -> Know closes the page into INV1056's populated row while the list arrives around
   it; Know -> Grow grows the list's last row into the chart, labels on the way; Chase -> Yours carries the Recent card
   into the Data storage card, revealed from its folder icon. The Ride (the benchmark) is unchanged.
   v2.2 (Daniel): Make -> Look is the way into the template picker: no page rest, no step back. Dark opens Look's paper
   from the PDF press through the app's theme circle; light grows straight into it; the tray then rises in on its own.
   ===================================================================================================================== */
(function () {
  "use strict";
  const { clamp, E, P, spring, mixC, css, div, drawShape, bezier, placeSt } = FX;
  const { geom, addSt, place, fitYearHeader } = FX.helpers;
  const SEAMS = (FX.seams = {});
  const fadeOut = (u, u0, d) => 1 - P(u, u0, d, E.ACCEL);
  const op = (a) => (a >= 0.999 ? "1" : Math.max(0, a).toFixed(3));
  const shownAs = (el, a, disp = "block") => {
    css(el, "opacity", op(a));
    css(el, "display", a <= 0.001 ? "none" : disp);
  };
  // scale an element's current (already written) opacity: the piece's own seek wrote it this frame, so this is pure
  const dim = (el, k, disp) => {
    if (el.style.display === "none") return;          // the piece has it hidden this frame: nothing to dim
    const base = el.style.opacity === "" ? 1 : parseFloat(el.style.opacity);
    shownAs(el, base * k, disp || (el.style.display && el.style.display !== "none" ? el.style.display : "block"));
  };
  // the house ink's soft-edged circle (house style § 3) as a mask on an element's own box:
  // "disc" shows the element inside the circle, "hole" hides it inside the circle; k 0..1 grows the circle
  function inkMask(el, mode, k, x, y, w, h) {
    let m = "none";
    if (mode === "hole" ? k > 0 : k < 1) {
      const far = Math.hypot(Math.max(x, w - x), Math.max(y, h - y));
      const fe = Math.max(4, 0.07 * Math.min(w, h));
      const rr = clamp(k) * (far + fe);
      const a = mode === "hole" ? "transparent" : "#000", b = mode === "hole" ? "#000" : "transparent";
      m = `radial-gradient(circle at ${x.toFixed(1)}px ${y.toFixed(1)}px, ${a} ${Math.max(0, rr - fe).toFixed(1)}px, ${b} ${rr.toFixed(1)}px)`;
    }
    css(el, "-webkit-mask-image", m);
    css(el, "mask-image", m);
  }
  // the same circle stretched to the box (an ellipse through its corners), as a hole: a wide, short row opens from its
  // middle outwards and is gone everywhere at k = 1 (a circle would leave its two ends to the last)
  function ellipseHole(el, k) {
    let m = "none";
    if (k > 0) {
      const r1 = clamp(k) * 108, r0 = Math.max(0, r1 - 8);
      m = `radial-gradient(ellipse farthest-corner at 50% 50%, transparent ${r0.toFixed(1)}%, #000 ${r1.toFixed(1)}%)`;
    }
    css(el, "-webkit-mask-image", m);
    css(el, "mask-image", m);
  }
  // one row of a list state, cloned: the state's own markup at its own zoom (so its columns are the list's own),
  // skinless, clipped to the row (rowTop / rowBot: the row's edges inside the content box, canvas units). light: in the
  // app's light colours (site.css .fx-lightvars, app.css's own light block), so it reads on white in the dark theme too
  function rowClone(parent, S, rowTop, rowBot, light) {
    const inner = light ? `<div class="fx-lightvars">${S.markup}</div>` : S.markup;
    const st = addSt(parent, inner, S.z);
    const card = st.querySelector(".card");
    if (card) card.classList.add("skinless");
    const tb = st.querySelector("table");
    if (tb) fitYearHeader(tb);
    css(st, "clip-path", `inset(${(rowTop / S.z).toFixed(2)}px 0px ${((S.ch - rowBot) / S.z).toFixed(2)}px 0px)`);
    css(st, "display", "none");
    return st;
  }
  // where a top-anchored list state's content box sits at rest (canvas units): centred across the card, at its top
  const contentBox = (R, S) => ({ x: R.cx - R.w / 2 + (R.w - S.cw) / 2, y: R.cy - R.h / 2 });

  /* ---------------- Make -> Look: the hand-off straight into the template picker (site v2.2) ----------------
     Daniel: "the pdf button can go straight to the template selecting part", "the templates ... come in naturally and
     smoothly, i dont just wanna skip to it". No page rest, no step back: the seam IS the way into Look.
     - Make's tail plays on under it (A at END + u: the press releases, the page settles) and the hand is drawn on top of
       everything (the seam's own copy, Make's own keys), so it leaves exactly as it always did.
     - Dark: Look's paper (the real PDF, at its own size and place) opens from the PDF press point through the app's
       theme circle (FX.circleMask on Look's paper layer, shadow and all), over the PDF button. Light: Make's page has
       grown straight into Look's paper, so Look's own paper takes over once Make's springs are exactly at rest
       (pixel for pixel).
     - As the page lands, the Theme page's tray comes in on its own calm move (one rise with a fade, overlapping the
       end of the reveal); its four REAL template cards come with it and settle just behind it, Modern (the account's
       style) first, then its ring. The cards are never above their own size, so their sample text stays <= 5 CSS px on
       every frame (legal). The seam ends on Look's opening composition, still, before the hand sets off for Bold. */
  SEAMS.makeLook = function ({ A, B, layer, dark }) {
    const a = A.inst.X, b = B.inst.X;
    const A0 = A.inst.END;                             // Make's last frame: its tail plays on under the hand-off
    const B0 = Math.min(0.5, B.inst.B.toBold - 0.1);   // Look's opening composition (complete from b.open, still until
                                                       // the hand sets off for Bold)
    // v2.3 (Daniel: "can the pdf expand circle into 02 invoice templates be smoother and slower so it feels more natural
    // flow instead of speedy"): the circle takes 0.95 s (was the theme switch's 0.46) on the ink's own ease-in-out
    // (E.OPEN: a soft start and a soft landing, where the switch's E.THEME snaps through its middle); the tray and its
    // cards arrive a little later and settle more slowly to match; and the seam asks the follower to play it at no more
    // than CAP x its pace (site.js brakes into it), so even a quick scroll can't rush it
    const CD = 0.95, CEASE = E.OPEN;                   // dark: the circle, u 0 -> CD
    const SWAP = dark ? CD : Math.max(0, a.settle - A0);   // from here Look's own paper is the page (Make is hidden)
    // the tray: in at TS (as the page lands), rising RISE canvas units over TD; its fade is quicker (TA), so a dark
    // tray crossing the white page is grey only for a moment
    const TS = dark ? 0.6 : 0.1, TD = 0.62, TA = 0.3, RISE = 30;
    const order = [1, 0, 2, 3];                        // Modern (the account's style) first, then its neighbours
    // its cards come with it and settle just behind it: card i from CR below and 96 % of its own size, from
    // C0 + CS * order, over CSD (never above its own size)
    const C0 = TS + 0.06, CS = 0.05, CSD = 0.42, CR = 12;
    const RING = C0 + CSD;                             // Modern's ring once its card has settled
    const DUR = +(Math.max(SWAP, TS + TD, C0 + 3 * CS + CSD, RING + 0.16) + 0.02).toFixed(3);
    const CAP = 1.4;
    const app = div("fe-app", layer);
    const hand = new FX.Cursor(app, a.cur.size);       // Make's hand, above the hand-off (Look's mount is above Make's)
    hand.keys = a.cur.keys;
    hand.presses = a.cur.presses;
    hand.fade = a.cur.fade;
    // v2.4 (Daniel: "have the cirle that comes out from the pdf button feel like it comes out from the button rather than
    // from the click"): the reveal blooms from the PDF button itself (FX.bloomMask): from its centre, filling the button
    // to its edges, then swelling past them into the circle. The hand still presses where it pressed.
    const BTN = a.R || { cx: b.R.cx, cy: b.R.cy, w: 0, h: 0 };
    const P0 = [BTN.cx, BTN.cy];
    const far = FX.farFrom(P0[0], P0[1], b.R);         // the circle lands fully opaque on the paper's farthest corner
    return {
      DUR, B0, CAP,
      seek(u) {
        const aOn = u < SWAP;
        A.show(aOn);
        if (aOn) {
          A.seek(A0 + u);
          css(a.cur.el, "display", "none");            // (its hand is drawn above, by the seam)
        }
        hand.draw(A0 + u);
        const bOn = dark ? u > 0 : true;
        B.show(bOn);
        if (!bOn) return;
        B.seek(B0);
        if (dark) FX.bloomMask(b.wrapP, u / CD, P0[0], P0[1], BTN.w / 2, BTN.h / 2, far, FX.stageScale(layer), CEASE);
        else if (aOn) css(b.paper, "display", "none"); // (Make's page stands in for it until exactly at rest)
        // the tray: one calm rise with a fade (Look's seek wrote it in place this frame; the seam only offsets it)
        const ta = P(u, TS, TA, E.DECEL), tk = P(u, TS, TD, E.SETTLE);
        shownAs(b.shape, ta);
        css(b.shape, "transform", tk >= 0.9999 ? "none" : `translateY(${(RISE * (1 - tk)).toFixed(2)}px)`);
        // ...its cards settle in place (Look's seek wrote each card's own transform this frame: its active scale,
        // <= 1.03; the settle only ever multiplies it by <= 1)
        b.cards.forEach((card, i) => {
          const ks = P(u, C0 + CS * order.indexOf(i), CSD, E.SETTLE);
          const own = card.style.transform;
          const s0 = own && own !== "none" ? parseFloat(own.slice(6)) || 1 : 1;
          css(card, "transform", ks >= 0.9999 ? own || "none"
            : `translateY(${((CR * (1 - ks)) / b.zp).toFixed(2)}px) scale(${(s0 * (0.96 + 0.04 * ks)).toFixed(4)})`);
        });
        css(b.ring, "opacity", op(P(u, RING, 0.12)));
      },
    };
  };

  /* ---------------- Look -> Know: the branded page closes into its own row, populated, as the list arrives ----------------
     The page (the seam's own copy of it, above the list) closes into INV1056's row: its PDF leaves (cropped, never
     squashed) as it starts to close, and the row itself (number, client, amount, status: the list's own markup, in the
     app's light colours on the white page) rides it down. The list arrives around it (its card, header and neighbouring
     rows, then the tabs) before the page has finished closing; once it is a row in the list, the list's colour opens
     from its centre (dark: the dark row shows through; light: identical). The narrow bar lives ~0.1 s. */
  SEAMS.lookKnow = function ({ A, B, layer, dark }) {
    const a = A.inst.X, b = B.inst.X;
    const DUR = 0.5, B0 = 0.25;                         // ends on Know at t 0.25: the list and tabs fully in
    const row = b.row1056;
    const ROW = { cx: row.cx, cy: row.cy, w: row.w, h: row.h, r: 2, bw: 1 };
    const G = geom([[0, a.R], [0.03, ROW, 3.0, 0.9]]);
    const S = b.ST.all;
    const cb = contentBox(b.R.all, S);
    const rx = row.cx - cb.x, ry = row.cy - cb.y;      // the row's centre inside the list's content box
    const app = div("fe-app", layer);                   // (the app's styles apply inside)
    const bar = div("fx-shape fx-bar", app);
    const pdf = document.createElement("img");
    pdf.src = "/assets/story/paper/INV1056-bold-brand-logo.svg";
    pdf.alt = "";
    pdf.className = "fx-bar-pdf";
    bar.appendChild(pdf);
    const rowSt = rowClone(bar, S, ry - row.h / 2, ry + row.h / 2, dark);
    const SEAL = 0.3, SEALD = 0.09;
    return {
      DUR, B0,
      seek(u) {
        A.show(false);                                 // the bar is the page from u = 0 (Look's last frame is the page alone)
        const g = G(u);
        const k = P(u, SEAL, SEALD, E.OPEN);
        drawShape(bar, g, { ...a.look, sh: 1 - P(u, SEAL - 0.04, 0.05), alpha: k >= 1 ? 0 : 1 });
        ellipseHole(bar, k);
        const pa = fadeOut(u, 0.02, 0.1);
        css(pdf, "display", pa > 0.001 ? "block" : "none");
        css(pdf, "opacity", op(pa));
        css(pdf, "left", `${((g.w - a.R.w) / 2).toFixed(2)}px`);
        css(pdf, "top", `${((g.h - a.R.h) / 2).toFixed(2)}px`);
        css(pdf, "width", `${a.R.w.toFixed(2)}px`);
        css(pdf, "height", `${a.R.h.toFixed(2)}px`);
        placeSt(rowSt, P(u, 0.08, 0.14, E.DECEL), g.w / 2 - rx, g.h / 2 - ry, S.z);
        const bOn = u >= 0.12;
        B.show(bOn);
        if (!bOn) return;
        B.seek(B0);
        const la = P(u, 0.14, 0.2, E.DECEL);
        css(b.shape, "opacity", op(la));
        css(b.shape, "transform", la >= 0.9999 ? "none" : `translateY(${(14 * (1 - la)).toFixed(2)}px)`);
        const ta = P(u, 0.18, 0.2, E.DECEL);
        css(b.tabsEl, "opacity", op(ta));
        css(b.tabsEl, "display", ta > 0.001 ? "block" : "none");
        css(b.tabsEl, "transform", ta >= 0.9999 ? "none" : `translateY(${((10 * (1 - ta)) / b.zt).toFixed(2)}px)`);
      },
    };
  };

  /* ---------------- Know -> Grow: the list's last row grows into the chart, its labels arriving on the way ----------------
     The Paid list's other rows, its header and tabs leave; its last row lifts (Grow's own card, starting as that row:
     the list's colour, no shadow, the row's text above it) and grows into the chart card while the row's text gives way
     to the chart's real labels. The bars are still down at the hand-over and rise right after it (Grow's own wave). */
  SEAMS.knowGrow = function ({ A, B, layer, dark }) {
    const a = A.inst.X, b = B.inst.X;
    // Grow is held at t 0.22 (its labels in, the bars down) until the labels have arrived here (u = BARS), then its own
    // clock runs: its first bar starts 0.04 s later and is a quarter up ~0.1 s after the labels; the wave runs on into
    // Grow (the hand-over is Grow's t = B0, bars mid-rise)
    const DUR = 0.62, G0 = 0.22, BARS = 0.3, B0 = G0 + (DUR - BARS);
    const last = a.lastPaid;
    const ROW = { cx: last.cx, cy: last.cy, w: last.w, h: last.h, r: 0, bw: 0 };
    const GS = geom([[0, ROW], [0.05, b.RC, 2.8, 0.88]]);
    const kOf = (u) => clamp(spring(u - 0.05, 2.8, 0.88));
    const S = a.ST.paid;
    const cb = contentBox(a.R.paid, S);
    const app = div("fe-app", layer);
    const rowSt = rowClone(app, S, last.cy - last.h / 2 - cb.y, last.cy + last.h / 2 - cb.y, false);
    return {
      DUR, B0,
      seek(u) {
        const aOn = u < 0.2;
        A.show(aOn);
        if (aOn) {
          A.seek(A.inst.END);
          const ca = fadeOut(u, 0, 0.1);
          dim(S.st, ca, "inline-block");
          dim(a.tabsEl, ca, "block");
          css(a.shape, "opacity", op(fadeOut(u, 0.04, 0.14)));
        }
        placeSt(rowSt, fadeOut(u, 0.14, 0.1), cb.x, cb.y, S.z);
        B.show(true);
        B.seek(G0 + Math.max(0, u - BARS));
        const g = GS(u), k = kOf(u);
        drawShape(b.shape, g, { fill: mixC(a.surf, b.surf, k), line: b.line, lineA: k, dark, sh: P(u, 0.03, 0.16) });
        place(b.st, P(u, 0.16, 0.16, E.DECEL), g, b.size, "center", b.zc);
      },
    };
  };

  /* ---------------- Grow -> Chase: the Ride (the benchmark). The camera dives up October's bar until its colour is the
     whole stage (that field is the bar's own colour, so the hand-over is invisible), then the colour floods the page
     from the stage outwards and becomes Chase's band. Every step is a pure function of u, so it scrubs both ways.
     (v2.1: unchanged; a mount it has hidden is no longer seeked.) */
  SEAMS.ride = function ({ A, B, W, H, tall }) {
    const grow = A.inst;
    const bR = grow.octR;
    const fy = 0.12;
    const S1 = Math.max(W / bR.w, H / (bR.h * 0.24)) * 1.3;
    const P0 = [W / 2, H / 2], P1 = [bR.x + bR.w / 2, bR.y + bR.h * 0.92], P2 = [bR.x + bR.w / 2, bR.y + bR.h * fy];
    const DIVE = 0.84, FADE = 0.1, FLOOD0 = DIVE + 0.04, FLOOD = 0.52, DUR = FLOOD0 + FLOOD + 0.05;
    const glide = bezier(0.42, 0, 0.22, 1);
    const flood = bezier(0.5, 0, 0.18, 1);
    function cam(u) {
      const v = clamp(u / DIVE);
      const e = glide(v);
      const fx = (1 - e) * (1 - e) * P0[0] + 2 * e * (1 - e) * P1[0] + e * e * P2[0];
      const fyy = (1 - e) * (1 - e) * P0[1] + 2 * e * (1 - e) * P1[1] + e * e * P2[1];
      const s = Math.exp(Math.log(S1) * Math.pow(v, 2.3));
      return { s, x: W / 2 - fx * s, y: H / 2 - fyy * s };
    }
    return {
      DUR, DIVE,
      seek(u) {
        const aOn = u < DIVE + FADE;
        A.show(aOn);
        if (aOn) {
          A.seek(grow.END);
          const c = cam(u);
          css(A.cam, "transform", u <= 0 ? "none" : `translate(${c.x.toFixed(2)}px, ${c.y.toFixed(2)}px) scale(${c.s.toFixed(4)})`);
          const fade = 1 - clamp((u - DIVE) / FADE);
          css(A.rootEl, "opacity", fade >= 0.999 ? "1" : fade.toFixed(3));
        }
        const bOn = u >= DIVE;
        B.show(bOn);
        if (bOn) {
          B.seek(0);
          // (phones: Chase's opener is populated from its first frame, so it crossfades in over the dive's own FADE,
          // as the zoomed bar leaves, instead of appearing at once; desktop's opener is invisible at 0 and untouched)
          if (tall) { const a = clamp((u - DIVE) / FADE); css(B.rootEl, "opacity", a >= 0.999 ? "1" : a.toFixed(3)); }
        }
      },
      globals(u) {
        return { field: u >= DIVE - 0.0005 ? 1 : 0, band: u < FLOOD0 ? 0 : flood(clamp((u - FLOOD0) / FLOOD)) };
      },
    };
  };

  /* ---------------- Chase -> Yours: the paid invoices settle into the folder that holds them ----------------
     The dashboard's KPIs leave; the Recent invoices card (the completed invoice, paid) is carried forward, contracting
     with its content straight into the Data storage card's shape (about 2/3 of its size). Mid-contraction the Data
     storage card is revealed over it from its folder icon (the house ink's soft circle, 0.16 s: the outgoing and
     incoming content overlap that long, and the folder path is the first thing it shows). Meanwhile the band draws back
     into the stage (the Ride backwards) and the colour gathers into the card, gone behind it. Never an empty panel. */
  SEAMS.chaseYours = function ({ A, B, dark }) {
    const a = A.inst.X, b = B.inst.X;
    const DUR = 0.9;
    const Y = b.R;
    const G = geom([[0, a.RR], [0.04, Y, 2.4, 0.88]]);
    const D0 = 0.18, DD = 0.16;
    const outScale = (g) => Math.min(1, g.w / a.RR.w, g.h / a.RR.h);
    const inScale = (g) => Math.min(1, g.w / Y.w, g.h / Y.h);
    return {
      DUR,
      seek(u) {
        const g = G(u);
        const k = P(u, D0, DD, E.OPEN);
        const outOn = k < 1;
        A.show(outOn);
        if (outOn) {
          A.seek(A.inst.END);
          dim(a.kp, fadeOut(u, 0, 0.12), "block");
          drawShape(a.shapeB, g, { fill: a.surfR, line: a.lineR, lineA: 1, dark });
          const ks = outScale(g);
          css(a.stR, "left", `${((g.w - a.szR.cw) / 2 / a.zR).toFixed(2)}px`);
          css(a.stR, "top", `${((g.h - a.szR.ch) / 2 / a.zR).toFixed(2)}px`);
          css(a.stR, "transform", ks >= 0.9999 ? "none" : `scale(${ks.toFixed(5)})`);
        }
        const inOn = u >= D0;
        B.show(inOn);
        if (!inOn) return;
        B.seek(B.inst.START);
        drawShape(b.shape, g, { fill: b.surf, line: b.line, lineA: 1, dark });
        const ki = inScale(g);
        css(b.st, "left", `${((g.w - b.size.cw) / 2 / b.Z).toFixed(2)}px`);
        css(b.st, "top", `${((g.h - b.size.ch) / 2 / b.Z).toFixed(2)}px`);
        css(b.st, "transform", ki >= 0.9999 ? "none" : `scale(${ki.toFixed(5)})`);
        // the reveal: a soft circle from the folder icon (in the card's own box, the content scaled about its centre)
        const fx = g.w / 2 + (b.folder.cx - Y.cx) * ki, fy = g.h / 2 + (b.folder.cy - Y.cy) * ki;
        inkMask(b.shape, "disc", k, fx, fy, g.w, g.h);
      },
      globals(u) {
        // the Ride, mirrored: the band draws back into the stage once the Chase caption has left; the field then
        // gathers into the Data storage card and is gone behind it
        const fk = P(u, 0.3, 0.32, bezier(0.5, 0, 0.2, 1));
        return { field: u < 0.64 ? 1 : 0, fieldTo: Y, fieldK: fk, band: 1 - P(u, 0.08, 0.42, bezier(0.4, 0, 0.6, 1)) };
      },
    };
  };

  /* ---------------- Yours -> Price: the folder's card leaves the stage and becomes the price card ----------------
     Page-level (site.js draws the overlay card in the pin): the Data storage card's content leaves, the card is lifted
     out of the stage at its exact screen rect and springs to the price card's rect; the stage dims away behind it.
     site v2.2 (Astra: "pricing arrives as an empty slab"): the price copy (the caption, switched by site.js) arrives as
     soon as the card can hold it. PRICE_IN is that moment: the card's spring at ~92 %, where it covers 98 % of the
     copy's box (measured at 1440, both themes); the card goes on settling under readable copy. */
  SEAMS.yoursPrice = function ({ A }) {
    const a = A.inst.X;
    const DUR = 1.25, LIFT = 0.1;
    const PRICE_IN = +(LIFT + 0.19).toFixed(3);
    return {
      DUR, PRICE_IN,
      seek(u) {
        const aOn = u < LIFT;
        A.show(aOn);
        if (!aOn) return;
        A.seek(A.inst.END);
        dim(a.st, fadeOut(u, 0, 0.1), "inline-block");
      },
      globals(u) {
        return {
          stage: 1 - P(u, 0.12, 0.42, E.SMOOTH),
          card: u < LIFT ? null : { from: "yours", k: clamp(spring(u - LIFT, 2.8, 0.9)) },
        };
      },
    };
  };

  /* ---------------- Price -> Brand: the card resolves into the Freelance Easy mark ----------------
     House order (never ink and size at once): the card shrinks to the mark's tile, then the tile's colour seals it from
     the centre. v2.1: the real raster (assets/fe-mark.png, at its own rect, opacity only) starts arriving while the tile
     is still forming (it overlaps the tile's last 0.26 s), so the identity is there as the tile appears. */
  SEAMS.priceBrand = function () {
    const DUR = 1.3;
    return {
      DUR,
      seek() {},
      globals(u) {
        const seal = P(u, 0.74, 0.18, E.CLOSE);
        // v2.2 (lead): the raster now fades in over 0.30–0.56 s, while the card settles into the tile, so no blank
        // tile shows first (Sol's re-check saw one at 0.45–0.66 s). The card is at tile size when the mark is opaque.
        const mark = P(u, 0.30, 0.26, E.DECEL);
        return {
          stage: 0,
          card: mark >= 1 ? null : { from: "price", to: "tile", k: clamp(spring(u - 0.08, 2.4, 0.84)), seal: u < 0.74 ? 0 : seal },
          mark,
        };
      },
    };
  };
})();
