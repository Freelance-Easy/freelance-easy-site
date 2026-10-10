/* =====================================================================================================================
   The homepage's product moments, in the order of the essentials: Make -> Look -> Know -> Grow (the Ride) -> Chase ->
   Brand. Every state is the RELEASED app's markup (assets/kit.js, generated from InvoiceGenerator v0.3.0-beta) styled by
   the app's own CSS (assets/app.css, scoped under .fe-app); the morphs between states are motion, not UI.
   A scene = build(ctx) -> { DUR, seek(t), IN, OUT, leave(k), EVENTS }; ctx = { root, world, W, H, tall, dark }.
   ===================================================================================================================== */
(function () {
  "use strict";
  const { clamp, mix, E, P, spring, track, press, smooth, money0, rgba, mixC, cssC, solid, over, css, div, rectIn, skin,
    even, drawShape, drawInk, alphaAt, placeSt, swapText, Cursor, tipIn, vrect } = FX;
  const KIT = () => window.FE_SITE;
  const S = (FX.scenes = {});
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

  /* ---------------- shared helpers ---------------- */
  function addSt(parent, markup, zoom) {
    const st = div("fx-st", parent);
    st.style.zoom = zoom;
    st.innerHTML = markup;
    return st;
  }
  function stSize(st) {
    css(st, "display", "inline-block");
    css(st, "opacity", "1");
    css(st, "filter", "none");
    const b = vrect(st);
    return { cw: b.width, ch: b.height };
  }
  // geometry tracks: seq = [[t, R, f, z], ...] -> g(t) = {cx, cy, w, h, r, bw}
  function geom(seq) {
    const K = {};
    for (const p of ["cx", "cy", "w", "h", "r", "bw"]) K[p] = seq.map(([t, R, f, z]) => [t, R[p], f, z]);
    return (t) => ({ cx: track(t, K.cx), cy: track(t, K.cy), w: track(t, K.w), h: track(t, K.h), r: track(t, K.r),
      bw: Math.max(0, track(t, K.bw)) });
  }
  // a colour that rides the same springs: seq = [[t, rgba, f, z], ...]
  function colTrack(seq) {
    const ch = [0, 1, 2, 3].map((i) => seq.map(([t, c, f, z]) => [t, c[i], f, z]));
    return (t) => ch.map((k) => clamp(track(t, k), 0, 255));
  }
  // the content inside a shape: centred (or top-anchored) in the shape's current box
  function place(st, a, g, size, anchor, zoom) {
    const left = (g.w - size.cw) / 2, top = anchor === "top" ? 0 : (g.h - size.ch) / 2;
    placeSt(st, a, left, top, zoom);
  }
  // read a style with a temporary class (the app's real :hover / .active look, mirrored as .fe-hover by app.css)
  function withClass(el, cls, fn) {
    el.classList.add(cls);
    const v = fn(getComputedStyle(el));
    el.classList.remove(cls);
    return v;
  }
  const tok = (el, name) => getComputedStyle(el).getPropertyValue(name).trim();
  // fit the year-header row of a list table to its visible columns (the total sits under Amount)
  function fitYearHeader(table) {
    const ths = [...table.querySelectorAll("thead th")].filter((th) => getComputedStyle(th).display !== "none");
    const amountIdx = ths.findIndex((th) => /amount/i.test(th.textContent));
    for (const tr of table.querySelectorAll("tr.year-header")) {
      const tds = [...tr.children].filter((td) => getComputedStyle(td).display !== "none");
      if (amountIdx < 0 || tds.length < 3) continue;
      tds[0].colSpan = Math.max(1, amountIdx);
      tds[2].colSpan = Math.max(1, ths.length - amountIdx - 1);
    }
  }
  // the year row's total for a filtered view, as applyDashboardFilters recomputes it (sum of the visible year's rows).
  // A function replacement: a money string such as "$21,450.00" holds "$2", which a replacement STRING would read as a
  // capture-group reference.
  const withYearTotal = (html, v) => html.replace(/(<td class="text-right year-total">)[^<]*(<\/td>)/, (m, a, b) => a + FX.money(v) + b);
  // the long soft shadow on a real card that keeps its own skin (a satellite)
  const satShadow = (el, dark, h) => css(el, "box-shadow", `0 0 0 1px ${dark ? "rgba(255,255,255,0.06)" : "rgba(20,20,24,0.07)"}, ${FX.shadow(h, dark, 0.85)}`);
  // Look's paper at rest (the real PDF, a constant size: a page is a page) and its skin. site v2.2: Make's light
  // ending grows straight into it, so both pieces read it from here.
  function lookPaper(W, H, tall) {
    const PH = tall ? 664 : 832;
    return { cx: W / 2, cy: (tall ? 14 : 26) + PH / 2, w: Math.round((PH * 612) / 792), h: PH, r: 10, bw: 1 };
  }
  const paperSkin = (dark) => ({ fill: [255, 255, 255, 1], line: [20, 20, 24, 0.06], lineA: dark ? 0 : 1, dark, rimA: 0 });
  FX.helpers = { addSt, stSize, geom, colTrack, place, withClass, tok, fitYearHeader, lookPaper, paperSkin };

  /* =================================================================================================================
     01 MAKE (the hero): + New invoice -> client picker -> the client -> line items (filled) -> Balance Due ->
     Create Invoice -> the invoice as light paper. Dark: the app draws its preview dark, so the paper is the real PDF
     after a visible PDF press (AGENTS-BRIEF § 3). site v2.2: the paper is Look's own (Make no longer rests on a page of
     its own): dark ends at the PDF press and the Make -> Look seam opens Look's paper through the theme circle; light
     grows straight into Look's paper.
     ================================================================================================================= */
  S.make = {
    build(ctx) {
      const { world, W, H, tall, dark } = ctx;
      const k = KIT().make;
      const Z = tall
        ? { new: 2.7, pick: 1.95, rows: 1.36, sum: 1.62, create: 1.75, pdf: 2.9 }
        : { new: 3.3, pick: 2.45, rows: 1.56, sum: 2.05, create: 2.15, pdf: 3.5 };
      const CX = W / 2, CY = H / 2;
      const dd = div("fx-free d-dd", world);
      // site v2.1: the Create button is its own shape, under the card. It slides out from under the finished calculation
      // and waits there through the arrival's hold (the hand resting beside it); once pressed, the card and the button
      // become one shape again (dark: the invoice page's PDF button; light: the page itself).
      const pill = div("fx-shape", world);
      const pillInk = div("fx-ink", pill);
      const shape = div("fx-shape", world);
      const ink = div("fx-ink", shape);
      // site v2.2 (Daniel: "the pdf button can go straight to the template selecting part"): Make no longer rests on a
      // page of its own. Dark: it ends at the PDF press; the Make -> Look seam opens Look's paper from the press point
      // through the app's theme circle. Light: the card and the button grow straight into Look's paper (the real PDF, at
      // Look's own size and place), so the seam only brings the Theme page's tray in under it.
      const LP = lookPaper(W, H, tall), PAPER = paperSkin(dark);
      let pageImg = null;
      if (!dark) {
        pageImg = document.createElement("img");
        pageImg.src = "/assets/story/paper/INV1056-modern.svg";
        pageImg.alt = "";
        pageImg.className = "fx-bar-pdf";              // (absolute, unscaled: cropped by the growing page, never squashed)
        shape.appendChild(pageImg);
      }
      const ST = {};
      const add = (name, markup, sel, anchor = "center", parent = shape) => {
        const st = addSt(parent, markup, Z[name]);
        ST[name] = { st, box: st.querySelector(sel), anchor, z: Z[name] };
      };
      add("new", `<div id="invoices-page" class="redesigned d-new">${k.newBtn}</div>`, ".btn");
      add("pick", `<div id="invoice-form-page" class="redesigned d-pick">${k.picker}</div>`, ".custom-select-trigger");
      add("rows", `<div id="invoice-form-page" class="redesigned d-rows"><form id="invoice-form" class="card"><div class="card-pad">${k.rows}</div></form></div>`, "form.card", "top");
      add("sum", `<div id="invoice-form-page" class="redesigned d-total d-sum">${k.total}</div>`, ".total-row", "sum");
      add("create", `<div id="invoice-form-page" class="redesigned d-create">${k.create}</div>`, ".btn", "center", pill);
      if (dark) add("pdf", `<div id="invoice-detail" class="redesigned d-pdfbtn">${k.pdfBtn}</div>`, ".btn");
      // (phones, round C, Astra #4/#5: the line items and the total at fixed screen sizes, site.css; the Create button's
      // shadow is a control's: short and light)
      if (tall) { ST.rows.st.style.setProperty("--sz", String(Z.rows)); ST.sum.st.style.setProperty("--sz", String(Z.sum)); }
      const dsM = parseFloat(getComputedStyle(ctx.root).getPropertyValue("--demo-scale")) || 0.55;
      const LITE_PILL = tall ? { y: 3 / dsM, b: 10 / dsM } : null;
      // the picker: its own dropdown is drawn by dd (unfolds from under the field); the text slot swaps placeholder -> pick
      ST.pick.st.querySelector(".custom-select-dropdown")?.remove();
      const slot = ST.pick.st.querySelector(".custom-select-text");
      slot.innerHTML = `<span class="sw"><span class="sa">-- Select Client --</span><span class="sb">${esc(k.pick)}</span></span>`;
      const swA = slot.querySelector(".sa"), swB = slot.querySelector(".sb");
      dd.style.zoom = Z.pick;
      dd.innerHTML = `<div id="invoice-form-page" class="redesigned">${k.dropdown}</div>`;
      const opt = [...dd.querySelectorAll(".custom-select-option")].find((o) => o.textContent.trim() === k.pick);

      // ---- measure at rest: each state's own skin, then the shapes draw it
      for (const el of [shape, pill]) { css(el, "left", "0px"); css(el, "top", "0px"); css(el, "width", `${W}px`); css(el, "height", `${H}px`); }
      for (const s of Object.values(ST)) Object.assign(s, stSize(s.st));
      const sk = {};
      for (const [n, s] of Object.entries(ST)) { sk[n] = skin(s.box, s.z); s.box.classList.add("skinless"); }
      const hoverOpt = withClass(opt, "fe-hover", (cs) => rgba(cs.backgroundColor));
      const pillHover = withClass(ST.create.box, "fe-hover", (cs) => rgba(cs.backgroundColor));
      const padR = Math.round((parseFloat(getComputedStyle(ST.rows.st.querySelector(".card-pad")).paddingRight) || 20) * Z.rows);
      const ddR = rectIn(dd, ctx.root);
      const optR = rectIn(opt, ctx.root);
      for (const s of Object.values(ST)) css(s.st, "display", "none");
      const surf = solid(sk.rows.bg, dark ? [19, 22, 30, 1] : [255, 255, 255, 1]);
      const COL = {
        ink: solid(sk.new.bg, dark ? [58, 120, 170, 1] : [0, 0, 0, 1]),
        inkHover: solid(pillHover, null),
        surf,
        pick: solid(sk.pick.bg, surf),
        page: PAPER.fill,
        pdf: solid(sk.pdf ? sk.pdf.bg : null, dark ? [13, 17, 23, 1] : surf),
        line: sk.rows.bc[3] > 0.005 ? sk.rows.bc : dark ? [255, 255, 255, 0.07] : [20, 20, 24, 0.08],
      };
      if (!COL.inkHover) COL.inkHover = COL.ink;
      const gap = 6 * Z.pick;
      const pickTotal = sk.pick.h + gap + ddR.h;
      const pickCy = Math.round(CY - pickTotal / 2 + sk.pick.h / 2);
      const pill2 = (s) => s.h / 2;
      // the finished calculation: the two line items over Balance Due (dominant by size and weight, right-aligned under the
      // amounts, as in the app's form), with the Create button under the card; card and button centred together
      const sumPad = Math.round(padR * 0.9);
      const calcH = sk.rows.h + ST.sum.ch + sumPad;
      const gapP = tall ? 20 : 26;
      const groupH = calcH + gapP + sk.create.h;
      const calcCy = Math.round(CY - groupH / 2 + calcH / 2);
      const pillCy = Math.round(calcCy + calcH / 2 + gapP + sk.create.h / 2);
      const R = {
        new: { cx: CX, cy: CY, w: sk.new.w, h: sk.new.h, r: pill2(sk.new), bw: 0 },
        pick: { cx: CX, cy: pickCy, w: sk.pick.w, h: sk.pick.h, r: Math.min(sk.pick.r, sk.pick.h / 2), bw: Math.max(1, sk.pick.bw) },
        rows: { cx: CX, cy: CY, w: sk.rows.w, h: sk.rows.h, r: sk.rows.r, bw: Math.max(1, sk.rows.bw) },
        calc: { cx: CX, cy: calcCy, w: sk.rows.w, h: calcH, r: sk.rows.r, bw: Math.max(1, sk.rows.bw) },
        pill: { cx: CX, cy: pillCy, w: sk.create.w, h: sk.create.h, r: pill2(sk.create), bw: 0 },
        page: LP,                                        // (light: Look's own paper)
      };
      R.pill0 = { ...R.pill, cy: Math.round(calcCy + calcH / 2 - sk.create.h / 2 - 8) };   // tucked under the card's edge
      R.field = { ...R.pick, cy: CY };
      if (dark) R.pdf = { cx: CX, cy: CY, w: sk.pdf.w, h: sk.pdf.h, r: pill2(sk.pdf), bw: Math.max(1, sk.pdf.bw) };
      const dd0 = { x: Math.round(CX - ddR.w / 2), y: Math.round(pickCy + sk.pick.h / 2 + gap) };
      const optAt = [dd0.x + (optR.x - ddR.x) + optR.w * 0.62, dd0.y + (optR.y - ddR.y) + optR.h * 0.62];

      // ---- beats (120 BPM: every change on a beat or an 8th; test D's table, rows arrive filled together)
      const B = { pressNew: 0.55, morphPick: 0.59, unfold: 0.67, toOption: 0.66, pick: 1.1, fold: 1.16, swap: 1.16,
        center: 1.2, rest: 1.26, morphRows: 1.85, morphTotal: 2.6, pillIn: 3.0 };
      // the arrival's hold: the calculation, the button and the hand all settled (springs are exactly 1 by then)
      B.hold = +(B.pillIn + 0.6).toFixed(3);
      B.toCreate = +(B.hold + 0.04).toFixed(3);
      B.pressCreate = +(B.toCreate + 0.42).toFixed(3);
      let DUR;
      const MF = dark ? [2.8, 0.82] : [3.0, 0.9];
      if (dark) {
        B.morphPdf = +(B.pressCreate + 0.25).toFixed(3);
        B.toPdf = +(B.morphPdf + 0.02).toFixed(3);
        B.pressPdf = +(B.morphPdf + 0.55).toFixed(3);
        B.away = +(B.pressPdf + 0.11).toFixed(3);
        // the click: Make ends here; the seam opens Look's paper from the press point through the theme circle while
        // Make's tail plays on under it (the press releases, the hand leaves)
        B.handoff = +(B.pressPdf + 0.06).toFixed(3);
        DUR = B.handoff;
      } else {
        B.morphPage = +(B.pressCreate + 0.25).toFixed(3);
        B.away = +(B.morphPage - 0.12).toFixed(3);
        // the page grows straight into Look's paper; Make ends as it lands (~92 % there) and the seam brings the
        // Theme page's tray in while the page settles (exactly at rest at B.settle, where Look's own paper takes over)
        B.settle = +(B.morphPage + FX.settleTime(...MF) + 0.002).toFixed(3);
        B.handoff = +(B.morphPage + 0.2).toFixed(3);
        DUR = B.handoff;
      }
      B.merge = dark ? B.morphPdf : B.morphPage;            // the card and the button become one shape
      B.pillOff = +(B.merge + 0.5).toFixed(3);               // ...and the button's own shape is gone under it
      const mergeTo = dark ? R.pdf : R.page;
      const seq = [[0, R.new], [B.morphPick, R.pick, 2.6, 0.82], [B.center, R.field, 2.2, 0.9],
        [B.morphRows, R.rows, 2.4, 0.84], [B.morphTotal, R.calc, 2.4, 0.84], [B.merge, mergeTo, ...MF]];
      const fills = [[0, COL.surf], [B.morphPick, COL.pick, 2.6, 0.82], [B.morphRows, COL.surf, 2.4, 0.84]];
      fills.push([B.merge, dark ? COL.pdf : COL.page, ...MF]);
      const G = geom(seq), F = colTrack(fills);
      // (light: the page lands in Look's paper skin exactly, so Look's own paper can take over pixel for pixel)
      const LN = colTrack([[0, COL.line], ...(dark ? [] : [[B.merge, PAPER.line, ...MF]])]);
      const lineA = (t) => clamp(track(t, [[0, 0], [B.morphPick, 1, 2.6, 0.82]]));
      // the button: out from under the card, then (dark) into the merged shape on the same springs as the card, or
      // (light, site v2.2) back in under the card it came from, fading away whole as the page starts to grow
      const GP = geom([[0, R.pill0], [B.pillIn, R.pill, 2.8, 0.86], [B.merge, dark ? mergeTo : R.pill0, ...MF]]);
      const FP = colTrack([[0, COL.surf], [B.merge, dark ? COL.pdf : COL.page, ...MF]]);
      const lineAP = (t) => clamp(track(t, [[0, 0], [B.merge, dark ? 1 : 0.6, ...MF]]));
      // the line items step back once the total arrives: 100 -> 50 % (Daniel, 2026-10-06: "the text is a bit hard to
      // read" … "oh it was at 42% put it at 50% so it drops from 100 to 50%"; it was 42 %)
      const quiet = (t) => mix(1, 0.5, clamp(spring(t - B.morphTotal, 2.4, 0.84)));
      // light (site v2.2, Astra: the paper must never be empty): the calculation stays on the page while it grows (where
      // it was: the paper grows around it) and gives way to the real PDF, overlapping it by ~100 ms
      B.pdfIn = dark ? null : +(B.morphPage + 0.16).toFixed(3);
      // (phones, F1b, Astra F1: on a phone the two states overlapping read as the form drawn over the PDF) the
      // calculation leaves first: gone (its 0.1 s fade) 0.02 s before the PDF starts to show, both directions
      const calcOut = dark ? B.merge - 0.1 : tall ? +(B.pdfIn - 0.12).toFixed(3) : +(B.pdfIn + 0.03).toFixed(3);
      const SCHED = {
        new: [-1, B.pressNew + 0.02],
        pick: [B.morphPick + 0.2, B.morphRows - 0.1],
        rows: [B.morphRows + 0.16, calcOut],               // dark: the calculation leaves just before the merge
        sum: [B.morphTotal + 0.16, calcOut],
        // (light: the pressed button keeps its label and fades away whole, with its shape, as the page starts to grow)
        create: [B.pillIn + 0.14, dark ? B.pressCreate + 0.03 : 99],
        // dark: the button keeps its label (the theme circle reveals Look's paper over it, as the app's theme reveals
        // over the old screen)
        pdf: dark ? [B.morphPdf + 0.16, 99] : [99, 99],
      };
      const PRESS_AT = {};
      const tgt = (r, fx, fy) => [r.cx + (fx * r.w) / 2, r.cy + (fy * r.h) / 2];
      PRESS_AT.new = tgt(R.new, 0.42, 0.3);
      PRESS_AT.create = tgt(R.pill, 0.4, 0.32);
      if (dark) PRESS_AT.pdf = tgt(R.pdf, 0.3, 0.3);
      function inkState(t) {
        if (t < B.pressNew + 0.04) return { mode: "full", color: COL.ink };
        if (t < B.pressNew + 0.2) return { mode: "hole", k: P(t, B.pressNew + 0.04, 0.16, E.OPEN), at: "new", color: COL.ink };
        return { mode: "none" };                         // (dark: the paper arrives through the theme circle instead)
      }
      // the button's own colour: full until its press, then it opens from the press point (before anything grows)
      function pillInk0(t) {
        const to = B.pressCreate + 0.07;
        if (t < to || !dark) return { mode: "full" };   // (light: it keeps its colour; it fades away whole, see seek)
        if (t < to + 0.14) return { mode: "hole", k: P(t, to, 0.14, E.OPEN) };
        return { mode: "none" };
      }
      // ---- the cursor: in from the corner, presses, then rests beside where Create arrives (off the content), so the
      // arrival's hold is the finished calculation with the hand at Create; the first scroll presses it
      const cur = new Cursor(world, tall ? 40 : 36);
      const restAt = [R.pill.cx + R.pill.w / 2 + (tall ? 28 : 34), R.pill.cy - R.pill.h * 0.12];
      cur.keys = [[0, [W * 0.86, H * 1.02]], [0.02, PRESS_AT.new, 1.8, 0.95], [B.toOption, optAt, 2.2, 0.92],
        [B.rest, restAt, 1.6, 0.95], [B.toCreate, PRESS_AT.create, 2.2, 0.93]];
      if (dark) cur.keys.push([B.toPdf, PRESS_AT.pdf, 1.9, 0.93]);
      cur.keys.push([B.away, [W * 1.04, H * 1.06], 1.3, 1.0]);
      cur.presses = [B.pressNew, B.pick, B.pressCreate, ...(dark ? [B.pressPdf] : [])];
      cur.fade = [-1, B.away + 0.12];
      const tipOn = (t, r) => tipIn(cur, t, { x: r.cx - r.w / 2, y: r.cy - r.h / 2, w: r.w, h: r.h });

      function seek(t) {
        const g = G(t);
        const s = inkState(t);
        // the pill's real :hover while the hand rests on it
        let inkC = s.color || COL.ink;
        if (s.color === COL.ink && FX.gate.cursor > 0.5 && t < B.pressNew + 0.1 && tipOn(t, R.new)) inkC = COL.inkHover;
        const sq = (press(t, B.pressNew) + (dark ? press(t, B.pressPdf) : 0)) * (0.03 / 0.045);
        drawShape(shape, g, { fill: F(t), line: LN(t), lineA: lineA(t), dark, sq });
        // light: the real PDF arrives on the growing page (opacity only: no blur on the big page), at Look's own size,
        // centred and cropped by the page as it grows; at rest it is Look's paper exactly
        if (pageImg) {
          const pa = P(t, B.morphPage + 0.16, 0.16, E.DECEL);
          css(pageImg, "display", pa > 0.001 ? "block" : "none");
          css(pageImg, "opacity", pa >= 0.999 ? "1" : pa.toFixed(3));
          css(pageImg, "left", `${((g.w - LP.w) / 2).toFixed(2)}px`);
          css(pageImg, "top", `${((g.h - LP.h) / 2).toFixed(2)}px`);
          css(pageImg, "width", `${LP.w}px`);
          css(pageImg, "height", `${LP.h}px`);
        }
        let px = g.cx, py = g.cy;
        if (s.at) [px, py] = PRESS_AT[s.at];
        drawInk(ink, { mode: s.mode, k: s.k, x: g.w / 2 + (px - g.cx), y: g.h / 2 + (py - g.cy), w: g.w, h: g.h, color: inkC });
        // the Create button (its shadow arrives as it slides out, and leaves as it merges). light (site v2.2): once
        // pressed it is gone within 0.1 s of the page starting to grow, so no empty pill is left under it
        const gp = GP(t);
        const pOn = t >= B.pillIn && t < B.pillOff;
        const psh = P(t, B.pillIn, 0.16) * (1 - P(t, B.merge, 0.3));
        const pa0 = pOn ? (dark ? 1 : 1 - P(t, B.merge, 0.1, E.ACCEL)) : 0;
        drawShape(pill, gp, { fill: FP(t), line: COL.line, lineA: lineAP(t), dark, sq: press(t, B.pressCreate) * (0.03 / 0.045), sh: psh, alpha: pa0, lite: LITE_PILL });
        const ps = pillInk0(t);
        const pc = FX.gate.cursor > 0.5 && t > B.toCreate + 0.15 && t < B.pressCreate + 0.2 && tipOn(t, R.pill) ? COL.inkHover : COL.ink;
        drawInk(pillInk, { mode: pOn ? ps.mode : "none", k: ps.k, x: gp.w / 2 + (PRESS_AT.create[0] - gp.cx), y: gp.h / 2 + (PRESS_AT.create[1] - gp.cy), w: gp.w, h: gp.h, color: pc });
        // light: while the page grows, the calculation stays where it rested in its card (the paper grows around it)
        const pin = !dark && t >= B.merge, ox = (R.calc.cx - R.calc.w / 2) - (g.cx - g.w / 2), oy = (R.calc.cy - R.calc.h / 2) - (g.cy - g.h / 2);
        for (const [name, st] of Object.entries(ST)) {
          const a = alphaAt(t, SCHED[name][0], SCHED[name][1]);
          if (name === "sum") {
            if (pin) placeSt(st.st, a, ox + R.calc.w - st.cw - padR, oy + R.calc.h - st.ch - sumPad, st.z);
            else placeSt(st.st, a, g.w - st.cw - padR, g.h - st.ch - sumPad, st.z);
          } else if (name === "create") place(st.st, pOn ? a : 0, gp, st, "center", st.z);
          else if (name === "rows" && pin) placeSt(st.st, a, ox + (R.calc.w - st.cw) / 2, oy, st.z);
          else place(st.st, a, g, st, st.anchor, st.z);
          // the line items' step back (opacity only: their blur is their own in/out)
          if (name === "rows" && a > 0.001) css(st.st, "opacity", (a * quiet(t)).toFixed(3));
        }
        swapText(swA, swB, t, B.swap);
        // the list unfolds from under the field and folds back into it (clip + 8 px travel)
        const vis = P(t, B.unfold, 0.24, E.DECEL) * (1 - P(t, B.fold, 0.18, E.ACCEL));
        css(dd, "display", vis > 0.001 ? "block" : "none");
        css(dd, "left", `${(dd0.x / Z.pick).toFixed(2)}px`);
        css(dd, "top", `${(dd0.y / Z.pick).toFixed(2)}px`);
        css(dd, "clip-path", `inset(0 0 ${((1 - vis) * 100).toFixed(2)}% 0 round ${(12).toFixed(1)}px)`);
        css(dd, "transform", vis >= 1 ? "none" : `translateY(${(-8 * (1 - vis)).toFixed(2)}px)`);
        const hov = P(t, B.toOption + 0.3, 0.12) + 0.75 * press(t, B.pick);
        css(opt, "background", cssC(hoverOpt[3] > 0 ? hoverOpt : [0, 0, 0, 0.08], clamp(hov, 0, 1.75)));
        cur.draw(t);
      }
      const EVENTS = [
        { t: 0, what: "+ New invoice (the list's header button); the cursor glides in" },
        { t: B.pressNew, what: "press: + New invoice (its colour opens from the press point)" },
        { t: B.morphPick, what: "morph: the pill opens into the client picker; the list unfolds" },
        { t: B.pick, what: `press: ${k.pick}` },
        { t: B.fold, what: "fold: the list folds into the field; the placeholder hands over to the pick" },
        { t: B.center, what: "glide: the field to the centre; the hand rests where Create will be" },
        { t: B.morphRows, what: "morph: the field into the line items, filled (Project work, Revisions)" },
        { t: B.morphTotal, what: "the card grows Balance Due $1,500.00 under its rows (the rows step back; no count-up)" },
        { t: B.pillIn, what: "Create Invoice slides out from under the card, beside the resting hand" },
        { t: B.hold, what: "the arrival's hold: the finished calculation, the hand at Create" },
        { t: B.pressCreate, what: "press: Create Invoice (the button opens first)" },
        ...(dark ? [{ t: B.morphPdf, what: "the card and the button become the invoice page's PDF button (dark: the app draws its preview dark)" },
          { t: B.pressPdf, what: "press: PDF" },
          { t: DUR, what: "the hand-off (Make -> Look): Look's paper, the real PDF, opens from the press point through the app's theme circle; the Theme page's tray rises in as it lands" }]
          : [{ t: B.morphPage, what: "the card and the button grow straight into the invoice's real PDF (INV1056, Modern), at Look's own size and place" },
          { t: DUR, what: "the hand-off (Make -> Look): the Theme page's tray rises in under the page as it lands" }]),
      ];
      // the handles the Make -> Look seam drives: the hand (it plays on above the hand-off), the PDF press point (dark),
      // the moment the page is exactly at rest (light)
      const X = { shape, cur, pressAt: dark ? PRESS_AT.pdf : null, settle: dark ? null : B.settle, R: mergeTo };
      return { DUR, seek, EVENTS, B, label: "Make", HOLD: B.hold, END: DUR, X };
    },
  };

  /* =================================================================================================================
     02 LOOK: the Theme page's real style picker drives the invoice. Classic -> Modern -> Minimal -> Bold (one sliding
     indicator; the paper re-sets: old leaves, then new arrives); an accent preset inks the paper from the swatch; the
     persona's logo arrives. The paper is the REAL PDF (light in both themes; the Theme page's own previews are light too).
     ================================================================================================================= */
  S.look = {
    build(ctx) {
      const { world, W, H, tall, dark } = ctx;
      const k = KIT().look;
      const LP = lookPaper(W, H, tall);                  // the paper, in canvas units (Make's light ending lands on it)
      const PH = LP.h, PW = LP.w, PCX = LP.cx, PCY = LP.cy;
      // (site v2.2: the paper has a full-stage layer of its own, so the Make -> Look seam can open it through the theme
      // circle, shadow and all, while the tray arrives on its own move; the piece's own frame always leaves it unmasked)
      const wrapP = div("fx-free", world);
      css(wrapP, "width", `${W}px`);
      css(wrapP, "height", `${H}px`);
      const paper = div("fx-paper", wrapP);
      const IM = {};
      for (const n of ["classic", "modern", "minimal", "bold", "bold-brand", "bold-brand-logo"]) {
        const img = document.createElement("img");
        img.src = `/assets/story/paper/INV1056-${n}.svg`;
        img.alt = "";
        img.decoding = "async";
        paper.appendChild(img);
        IM[n] = img;
      }
      const shape = div("fx-shape", world);
      div("fx-ink", shape);
      // (picker zoom: the cards' sample text stays <= 5 CSS px on screen at the largest stage, 676 px; checked per frame)
      const Z = tall ? { picker: 0.665, presets: 1.32, pool: 1.75 } : { picker: 0.74, presets: 1.52, pool: 2.0 };
      const ST = {};
      const add = (name, markup, sel) => {
        const st = addSt(shape, markup, Z[name]);
        ST[name] = { st, box: st.querySelector(sel), z: Z[name] };
      };
      add("picker", `<div id="theme-page" class="redesigned d-theme"><div class="card picker-card"><div class="card-pad">${k.picker}</div></div></div>`, ".card");
      add("presets", `<div id="theme-page" class="redesigned d-theme"><div class="card"><div class="card-pad">${k.presets}</div></div></div>`, ".card");
      add("pool", `<div id="theme-page" class="redesigned d-theme"><div class="card"><div class="card-pad"><div class="logo-pool">${k.poolItem}</div></div></div></div>`, ".card");
      if (tall) ST.picker.st.style.setProperty("--sz", String(Z.picker));   // (phones: the template names at 12 screen px)
      if (tall) ST.presets.st.style.setProperty("--sz", String(Z.presets)); // (phones, round B2: 22 px swatches, 10 px gaps)
      const picker = ST.picker.st.querySelector(".style-picker");
      const cards = [...picker.querySelectorAll(".style-card")];
      cards.forEach((c) => c.classList.remove("active"));
      const ring = div("fx-ring", picker);
      const coral = [...ST.presets.st.querySelectorAll(".color-preset")].find((b) => (b.getAttribute("data-hex") || "").toLowerCase() === k.brand.toLowerCase());
      const poolItem = ST.pool.st.querySelector(".logo-pool-item");
      const useBtn = ST.pool.st.querySelector(".btn-pool-select");

      // ---- measure
      css(shape, "left", "0px"); css(shape, "top", "0px"); css(shape, "width", `${W}px`); css(shape, "height", `${H}px`);
      for (const s of Object.values(ST)) Object.assign(s, stSize(s.st));
      const sk = {};
      for (const [n, s] of Object.entries(ST)) { sk[n] = skin(s.box, s.z); s.box.classList.add("skinless"); }
      const pr = vrect(picker);
      const zp = Z.picker;
      const cardR = cards.map((c) => { const r = vrect(c); return { x: (r.left - pr.left) / zp, y: (r.top - pr.top) / zp, w: r.width / zp, h: r.height / zp }; });
      const radius = parseFloat(getComputedStyle(cards[0]).borderTopLeftRadius) || 10;
      const accent = rgba(tok(picker, "--accent")) , aring = rgba(tok(picker, "--accent-ring"));
      for (const s of Object.values(ST)) css(s.st, "display", "none");
      const surf = solid(sk.picker.bg, dark ? [19, 22, 30, 1] : [255, 255, 255, 1]);
      const line = sk.picker.bc[3] > 0.005 ? sk.picker.bc : dark ? [255, 255, 255, 0.07] : [20, 20, 24, 0.08];
      // (round B2, Astra pA #13: on phones at least 16 screen px between the control card and the stage's bottom edge)
      const dsL = parseFloat(getComputedStyle(ctx.root).getPropertyValue("--demo-scale")) || 0.55;
      const bottom = tall ? H - Math.max(30, Math.ceil(16 / dsL)) : H - 34;           // the control card floats over the paper's blank lower part (phones B1: 30, clear of the stage edge while it rises in)
      const RC = {};
      for (const n of ["picker", "presets", "pool"]) RC[n] = { cx: W / 2, cy: bottom - sk[n].h / 2, w: sk[n].w, h: sk[n].h, r: sk[n].r, bw: Math.max(1, sk[n].bw) };
      const B = { toBold: 0.78, pressBold: 1.28, morphPresets: 2.15, toCoral: 2.25, pressCoral: 2.77,
        morphPool: 3.83, toPool: 3.91, pressPool: 4.45, away: 4.58, poolExit: 4.86, poolDrop: 4.96 };
      const DUR = 6.26;
      RC.poolOut = { ...RC.pool, cy: H + RC.pool.h / 2 + 80 };
      const G = geom([[0, RC.picker], [B.morphPresets, RC.presets, 2.4, 0.84], [B.morphPool, RC.pool, 2.4, 0.84],
        [B.poolDrop, RC.poolOut, 6.0, 0.84]]);
      const SCHED = { picker: [0.12, B.morphPresets - 0.1], presets: [B.morphPresets + 0.16, B.morphPool - 0.1], pool: [B.morphPool + 0.16, B.poolExit] };
      // every cursor target is measured with its state placed exactly as it rests (canvas units, root unscaled)
      const at = (name, el, fx = 0.5, fy = 0.5) => {
        for (const s of Object.values(ST)) css(s.st, "display", "none");
        drawShape(shape, RC[name], { fill: surf, line, lineA: 1, dark });
        place(ST[name].st, 1, RC[name], ST[name], "center", ST[name].z);
        const r = rectIn(el, ctx.root);
        css(ST[name].st, "display", "none");
        return { x: r.x, y: r.y, w: r.w, h: r.h, p: [r.x + r.w * fx, r.y + r.h * fy] };
      };
      const cardAt = cards.map((c) => at("picker", c, 0.5, 0.42));
      const cardCanvas = (i) => cardAt[i].p;
      const coralT = at("presets", coral, 0.5, 0.55);
      const useT = at("pool", useBtn, 0.5, 0.55);
      const coralAt = coralT.p, useAt = useT.p;
      // the paper: which page is showing, swapped out-then-in at each press (M16, no blur on the big page)
      const SWAPS = [[B.pressBold, "modern", "bold"],
        [B.pressPool + 0.12, "bold-brand", "bold-brand-logo"]];
      const inkT0 = B.pressCoral + 0.06, inkDur = 0.62;
      // the ring: one indicator that slides card to card; each card's own active look rides the same spring
      const ACT = [[0, 1], [B.pressBold + 0.02, 3, 3.4, 0.9]];
      const actOf = (t, i) => clamp(track(t, ACT.map(([tt, v, f, z]) => [tt, v === i ? 1 : 0, f, z])));
      const RINGX = ACT.map(([tt, v, f, z]) => [tt, cardR[v].x, f, z]);
      const cur = new Cursor(world, tall ? 40 : 36);
      cur.keys = [[0, [W * 0.92, H * 1.04]], [B.toBold, cardCanvas(3), 2.3, 0.95], [B.toCoral, coralAt, 2.0, 0.94], [B.toPool, useAt, 2.0, 0.94],
        [B.away, [W * 1.05, H * 1.06], 1.3, 1.0]];
      cur.presses = [B.pressBold, B.pressCoral, B.pressPool];
      cur.fade = [-1, B.away + 0.14];
      const paperLook = paperSkin(dark);
      function pageAlpha(t, name) {
        // modern shows from the start; each swap: the old leaves (0.10 s), the new arrives 0.11 s later (0.16 s)
        let a = name === "modern" ? alphaAt(t, 0.05, 99) : 0;
        for (const [ts, from, to] of SWAPS) {
          if (name === from) a = Math.min(a, 1 - P(t, ts + 0.02, 0.1, E.ACCEL));
          if (name === to) a = Math.max(a, P(t, ts + 0.13, 0.16, E.DECEL));
        }
        // the accent: bold -> bold-brand by the ink (bold stays under it until the ink has covered the page)
        if (name === "bold" && t >= inkT0 + inkDur) a = 0;
        if (name === "bold-brand") {
          a = t >= inkT0 ? 1 : 0;
          for (const [ts, from] of SWAPS) if (from === "bold-brand") a = Math.min(a, 1 - P(t, ts + 0.02, 0.1, E.ACCEL));
        }
        return a;
      }
      function seek(t) {
        // the paper (constant size: a page is a page)
        css(wrapP, "-webkit-mask-image", "none");         // (the Make -> Look seam opens the paper through a circle)
        css(wrapP, "mask-image", "none");
        drawShape(paper, { cx: PCX, cy: PCY, w: PW, h: PH, r: 10, bw: 1 }, { ...paperLook, alpha: 1 });
        for (const [n, img] of Object.entries(IM)) {
          const a = pageAlpha(t, n);
          css(img, "opacity", a >= 0.999 ? "1" : a.toFixed(3));
          css(img, "display", a > 0.001 ? "block" : "none");
          const rise = n === "modern" || n === "bold-brand" ? 0 : 6 * (1 - a);
          css(img, "transform", rise > 0.01 && a < 1 ? `translateY(${rise.toFixed(2)}px)` : "none");
        }
        // the accent ink: a soft-edged circle from the swatch, recolouring the page (bold-brand over bold)
        const ik = P(t, inkT0, inkDur, E.OPEN);
        let mask = "none";
        if (t >= inkT0 && ik < 1) {
          const lx = coralAt[0] - (PCX - PW / 2), ly = coralAt[1] - (PCY - PH / 2);
          const far = Math.hypot(Math.max(lx, PW - lx), Math.max(ly, PH - ly));
          const fe = Math.max(4, 0.07 * Math.min(PW, PH));
          const rr = ik * (far + fe);
          mask = `radial-gradient(circle at ${lx.toFixed(1)}px ${ly.toFixed(1)}px, #000 ${Math.max(0, rr - fe).toFixed(1)}px, transparent ${rr.toFixed(1)}px)`;
        }
        css(IM["bold-brand"], "-webkit-mask-image", mask);
        css(IM["bold-brand"], "mask-image", mask);
        // the control card: picker -> presets -> pool (one shape; content leaves before each morph)
        const g = G(t);
        const sq = press(t, B.pressCoral) * 0 + 0;      // the card itself has no :active rule: it never squashes
        drawShape(shape, g, { fill: surf, line, lineA: 1, dark, sq, alpha: t >= B.poolDrop + 0.3 ? 0 : 1 });
        for (const [n, s] of Object.entries(ST)) place(s.st, alphaAt(t, SCHED[n][0], SCHED[n][1]), g, s, "center", s.z);
        // the style cards: the app's own active look (scale 1.03, full brightness; others dimmed .65), sliding ring.
        // (opacity and transform are written every frame: the Make -> Look seam brings the real cards in through them)
        for (let i = 0; i < cards.length; i++) {
          const a = actOf(t, i);
          css(cards[i], "opacity", "1");
          css(cards[i], "transform", a < 0.001 ? "none" : `scale(${(1 + 0.03 * a).toFixed(4)})`);
          css(cards[i], "filter", a > 0.999 ? "none" : `brightness(${(0.65 + 0.35 * a).toFixed(3)})`);
          const hovering = FX.gate.cursor > 0.5 && t > 0.2 && t < B.morphPresets && tipIn(cur, t, cardAt[i]);
          cards[i].classList.toggle("fe-hover", hovering && a < 0.5);
        }
        const rx = track(t, RINGX), cy0 = cardR[0].y, ch0 = cardR[0].h, cw0 = cardR[0].w;
        const sc = 1.03;
        css(ring, "left", `${(rx - (cw0 * (sc - 1)) / 2).toFixed(2)}px`);
        css(ring, "top", `${(cy0 - (ch0 * (sc - 1)) / 2).toFixed(2)}px`);
        css(ring, "width", `${(cw0 * sc).toFixed(2)}px`);
        css(ring, "height", `${(ch0 * sc).toFixed(2)}px`);
        css(ring, "border-radius", `${radius}px`);
        css(ring, "box-shadow", `0 0 0 1px ${cssC(accent)}, 0 0 0 4px ${cssC(aring)}`);
        css(ring, "opacity", "1");
        // the swatch's real :hover (scale 1.1) while the hand is on it; "Use this logo" -> the item turns .active
        coral.classList.toggle("fe-hover", FX.gate.cursor > 0.5 && t > B.toCoral + 0.25 && t < B.morphPool - 0.1);
        const used = t >= B.pressPool + 0.12;
        poolItem.classList.toggle("active", used);
        css(useBtn, "visibility", used ? "hidden" : "visible");
        useBtn.classList.toggle("fe-hover", FX.gate.cursor > 0.5 && !used && t > B.toPool + 0.3);
        cur.draw(t);
      }
      const IN = { cx: PCX, cy: PCY, w: PW, h: PH, r: 10, bw: 1, fill: [255, 255, 255, 1], line: [20, 20, 24, 0.06], rim: 0 };
      const OUT = { ...IN };
      function leave(kk) {
        // content leaves; the control card fades; the paper's page fades out of its frame (the seam takes the frame)
        const a = 1 - E.ACCEL(clamp(kk));
        for (const img of Object.values(IM)) if (img.style.display !== "none") css(img, "opacity", (a * (parseFloat(img.style.opacity) || 1)).toFixed(3));
        css(shape, "opacity", a.toFixed(3));
        cur.el.style.display = "none";
      }
      const EVENTS = [
        { t: 0, what: "the paper (the real PDF, Modern) + the Theme page's style picker" },
        { t: B.pressBold, what: "press: Bold; re-set" },
        { t: B.morphPresets, what: "morph: the card into the accent presets" },
        { t: B.pressCoral, what: `press: the ${k.brand} preset; its colour inks across the paper` },
        { t: B.morphPool, what: "morph: the card into the persona's logo (Uploaded Logos)" },
        { t: B.pressPool, what: "press: Use this logo; the paper re-sets with the logo" },
      ];
      // (open: the opening composition is complete, the paper, the picker's card and its cards all in; it holds still
      // until the hand sets off for Bold at B.toBold)
      const X = { paper, IM, R: { cx: PCX, cy: PCY, w: PW, h: PH, r: 10, bw: 1 }, look: paperLook, shape, RC,
        picker: ST.picker.st, surf, line, cards, ring, zp: Z.picker, wrapP, open: 0.3 };
      // the story's segment ends once the control card has dropped away and the hand has left (the branded page alone)
      return { DUR, seek, IN, OUT, leave, EVENTS, B, label: "Look", END: 5.45, X };
    },
  };

  /* =================================================================================================================
     03 KNOW: the invoice list's status filter (All Invoices · Outstanding · Overdue · Paid) flips through the real rows;
     one sliding indicator (the app's own .tab-ink); the card's height rides a spring; rows leave, then arrive.
     ================================================================================================================= */
  S.know = {
    build(ctx) {
      const { world, W, H, tall, dark } = ctx;
      const k = KIT().know;
      const Z = tall ? { tabs: 1.28, card: 1.62 } : { tabs: 1.12, card: 1.12 };
      const LIMIT = tall ? 3 : 6;
      const FILTERS = [
        { key: "all", match: () => true, cut: true },
        { key: "outstanding", match: (n) => k.status[n] === "outstanding" },
        { key: "overdue", match: (n) => k.status[n] === "overdue" },
        { key: "paid", match: (n) => k.status[n] === "paid", cut: true },
      ];
      const tabsEl = div("fx-free", world);
      tabsEl.style.zoom = Z.tabs;
      if (tall) tabsEl.style.setProperty("--sz", String(Z.tabs));         // (phones: the tabs at 12 screen px, site.css)
      tabsEl.innerHTML = `<div id="invoices-page" class="redesigned d-tabs">${k.tabs}</div>`;
      const tabs = [...tabsEl.querySelectorAll(".tab")];
      const inkEl = tabsEl.querySelector(".tab-ink");
      const shape = div("fx-shape", world);
      div("fx-ink", shape);
      const cls = tall ? "d-list no-actions no-date client-status" : "d-list no-actions";
      const ST = {};
      for (const f of FILTERS) {
        const rows = k.order.filter(f.match);
        const shown = rows.slice(0, f.cut ? LIMIT : rows.length);
        const yearTotal = rows.filter((n) => k.yearOf[n] === "2026").reduce((s, n) => s + k.totals[n], 0);
        const header = withYearTotal(k.years["2026"], yearTotal);
        const markup = `<div id="invoices-page" class="redesigned ${cls}"><div class="card"><div class="table-scroll"><table>${k.thead}<tbody>${header}${shown.map((n) => k.rows[n]).join("")}</tbody></table></div></div></div>`;
        const st = addSt(shape, markup, Z.card);
        ST[f.key] = { st, box: st.querySelector(".card"), z: Z.card, cut: !tall && f.cut && rows.length > shown.length, markup };
      }
      // measure
      css(shape, "left", "0px"); css(shape, "top", "0px"); css(shape, "width", `${W}px`); css(shape, "height", `${H}px`);
      for (const s of Object.values(ST)) { css(s.st, "display", "inline-block"); fitYearHeader(s.st.querySelector("table")); }
      for (const s of Object.values(ST)) Object.assign(s, stSize(s.st));
      const sk = {};
      for (const [n, s] of Object.entries(ST)) { sk[n] = skin(s.box, s.z); s.box.classList.add("skinless"); }
      // (phones, round B2: the tab rail and its underline span the card's own width, the tabs shared out across it)
      if (tall) {
        const rail = tabsEl.querySelector(".tabs");
        css(rail, "width", `${Math.max(...Object.values(sk).map((s) => s.w)) / Z.tabs}px`);
        css(rail, "justify-content", "space-between");
      }
      const tr = vrect(tabsEl.querySelector(".tabs"));
      const tabR = tabs.map((tb) => { const r = vrect(tb); return { x: (r.left - tr.left) / Z.tabs, w: r.width / Z.tabs, cx: r.left + r.width / 2, cy: r.top + r.height / 2 }; });
      const tabsW = tr.width, tabsH = tr.height;
      for (const s of Object.values(ST)) css(s.st, "display", "none");
      const surf = solid(sk.all.bg, dark ? [19, 22, 30, 1] : [255, 255, 255, 1]);
      const line = sk.all.bc[3] > 0.005 ? sk.all.bc : dark ? [255, 255, 255, 0.07] : [20, 20, 24, 0.08];
      // layout: tabs above the card, left edges aligned, the pair centred; the card's top stays put, its height springs
      const cardW = Math.max(...Object.values(sk).map((s) => s.w));
      const maxH = Math.max(...Object.values(sk).map((s) => s.h));
      const gapY = tall ? 18 : 22;
      const blockH = tabsH + gapY + maxH;
      const left = Math.round(W / 2 - Math.max(cardW, tabsW) / 2);
      const top = Math.round(H / 2 - blockH / 2);
      const cardTop = top + tabsH + gapY;
      const R = {};
      for (const [n, s] of Object.entries(sk)) R[n] = { cx: left + s.w / 2, cy: cardTop + s.h / 2, w: s.w, h: s.h, r: s.r, bw: Math.max(1, s.bw) };
      // site v2: the rows at rest, in canvas units (the Look -> Know seam lands the page on INV1056's row in All; the
      // Know -> Grow seam drops the visible Paid rows into the chart)
      const rowsAt = (n) => {
        for (const s of Object.values(ST)) css(s.st, "display", "none");
        drawShape(shape, R[n], { fill: surf, line, lineA: 1, dark });
        place(ST[n].st, 1, R[n], ST[n], "top", ST[n].z);
        const cardBottom = R[n].cy + R[n].h / 2;
        const out = [...ST[n].st.querySelectorAll("tbody tr:not(.year-header)")].map((tr) => {
          const r = rectIn(tr, ctx.root);
          return { cx: r.x + r.w / 2, cy: r.y + r.h / 2, w: r.w, h: r.h, r: 0, bw: 0, num: (tr.textContent.match(/INV\d+/) || [""])[0] };
        }).filter((r) => r.cy + r.h / 2 <= cardBottom - (ST[n].cut ? 40 : 0));
        css(ST[n].st, "display", "none");
        return out;
      };
      const rowsAll = rowsAt("all"), rowsPaid = rowsAt("paid");
      const B = { toOver: 0.71, pressOver: 1.21, toPaid: 2.46, pressPaid: 2.96, away: 3.14 };
      const DUR = 4.71;
      const ORDER = [["all", 0], ["overdue", B.pressOver], ["paid", B.pressPaid]];
      const G = geom(ORDER.map(([n, tt], i) => (i === 0 ? [0, R[n]] : [tt + 0.06, R[n], 2.4, 0.84])));
      const SCHED = { outstanding: [99, 99] };
      ORDER.forEach(([n, tt], i) => { SCHED[n] = [i === 0 ? 0.05 : tt + 0.16, i < ORDER.length - 1 ? ORDER[i + 1][1] + 0.02 : 99]; });
      const tabIndex = (n) => FILTERS.findIndex((f) => f.key === n);
      const INKX = ORDER.map(([n, tt], i) => [i === 0 ? 0 : tt + 0.03, tabR[tabIndex(n)].x, 3.4, 0.9]);
      const INKW = ORDER.map(([n, tt], i) => [i === 0 ? 0 : tt + 0.03, tabR[tabIndex(n)].w, 3.4, 0.9]);
      const tabAt = (i) => {
        const r = tabR[i];
        return [left + (r.x + r.w * 0.5) * Z.tabs, top + tabsH * 0.62];
      };
      const cur = new Cursor(world, tall ? 40 : 36);
      cur.keys = [[0, [W * 0.92, H * 1.04]], [B.toOver, tabAt(2), 2.3, 0.95],
        [B.toPaid, tabAt(3), 2.3, 0.95], [B.away, [W * 0.84, H * 0.96], 1.5, 1.0]];
      cur.presses = [B.pressOver, B.pressPaid];
      cur.fade = [-1, B.away + 0.2];
      function seek(t) {
        const g = G(t);
        drawShape(shape, g, { fill: surf, line, lineA: 1, dark });
        css(tabsEl, "left", `${(left / Z.tabs).toFixed(2)}px`);
        css(tabsEl, "top", `${(top / Z.tabs).toFixed(2)}px`);
        const ta = alphaAt(t, 0.02, 99);
        css(tabsEl, "opacity", ta >= 0.999 ? "1" : ta.toFixed(3));
        css(tabsEl, "display", ta > 0.001 ? "block" : "none");
        css(tabsEl, "transform", "none");                  // (a seam may move the tabs; the piece's own frame never does)
        for (const [n, s] of Object.entries(ST)) {
          const a = alphaAt(t, SCHED[n][0], SCHED[n][1]);
          place(s.st, a, g, s, "top", s.z);
          css(s.st, "-webkit-mask-image", s.cut ? "linear-gradient(to bottom, #000 calc(100% - 64px), transparent calc(100% - 6px))" : "none");
          css(s.st, "mask-image", s.cut ? "linear-gradient(to bottom, #000 calc(100% - 64px), transparent calc(100% - 6px))" : "none");
        }
        // the active tab: the app swaps its class at once; the ink slides (the app's own .tab-ink, translateX + scaleX)
        let on = 0;
        ORDER.forEach(([n, tt], i) => { if (i > 0 && t >= tt + 0.03) on = tabIndex(n); });
        tabs.forEach((tb, i) => { tb.classList.toggle("active", i === on); tb.classList.toggle("fe-hover", FX.gate.cursor > 0.5 && i !== on && tipIn(cur, t, { x: left + tabR[i].x * Z.tabs, y: top, w: tabR[i].w * Z.tabs, h: tabsH })); });
        css(inkEl, "transform", `translateX(${track(t, INKX).toFixed(2)}px) scaleX(${track(t, INKW).toFixed(2)})`);
        cur.draw(t);
      }
      const IN = { ...R.all, fill: surf, line };
      const OUT = { ...R.paid, fill: surf, line };
      function leave(kk) {
        const a = 1 - E.ACCEL(clamp(kk));
        for (const s of Object.values(ST)) if (s.st.style.display !== "none") css(s.st, "opacity", (a * parseFloat(s.st.style.opacity || "1")).toFixed(3));
        css(tabsEl, "opacity", a.toFixed(3));
        cur.el.style.display = "none";
      }
      const EVENTS = [
        { t: 0, what: `All Invoices (${k.counts.all}): the newest rows` },
        { t: B.pressOver, what: `press: Overdue (${k.counts.overdue})` },
        { t: B.pressPaid, what: `press: Paid (${k.counts.paid})` },
      ];
      const X = { shape, R, surf, line, tabsEl, zt: Z.tabs, ST, row1056: rowsAll.find((r) => r.num === "INV1056") || rowsAll[0],
        paidRows: rowsPaid, lastPaid: rowsPaid[rowsPaid.length - 1] };
      return { DUR, seek, IN, OUT, leave, EVENTS, B, label: "Know", END: 3.7, X };
    },
  };

  /* =================================================================================================================
     04 GROW: the dashboard as the app mounts it, art-directed. site v2.1: the chart comes first (the Know -> Grow seam
     grows the list's last row into the chart card, its labels arriving on the way); the bars rise at once, left to
     right in one quick wave (the first is a quarter up within ~0.1 s of the seam), this month landing last with the one
     accent bounce; then the KPIs arrive above it and count up (the app's own 900 ms easeOutCubic, 80 ms stagger) while
     the Collected YTD sparkline draws (sparkReveal).
     ================================================================================================================= */
  S.grow = {
    build(ctx) {
      const { world, W, H, tall, dark } = ctx;
      const k = KIT().grow;
      const Z = tall ? { kpis: 1.32, chart: 0.98 } : { kpis: 0.9, chart: 1.56 };
      const kpis = div("fx-free", world);
      kpis.style.zoom = Z.kpis;
      if (tall) kpis.style.setProperty("--sz", String(Z.kpis));           // (phones: KPI type at fixed screen px, site.css)
      kpis.innerHTML = `<div id="dashboard-page" class="redesigned d-kpis">${k.kpiRow}</div>`;
      const shape = div("fx-shape", world);
      div("fx-ink", shape);
      const uid = "g" + Math.random().toString(36).slice(2, 7);
      const chartMarkup = k.chart.replace(/id="(paidGrad|dueGrad)"/g, `id="$1-${uid}"`).replace(/url\(#(paidGrad|dueGrad)\)/g, `url(#$1-${uid})`);
      const st = addSt(shape, `<div id="dashboard-page" class="redesigned d-chart">${chartMarkup}</div>`, Z.chart);
      const box = st.querySelector(".chart-card");
      // wrap each bar's two segments so the stack rises from the baseline as one (transform-box: view-box)
      const groups = [...st.querySelectorAll(".bar-group")];
      const stacks = groups.map((gEl) => {
        const ns = "http://www.w3.org/2000/svg";
        const s = document.createElementNS(ns, "g");
        s.setAttribute("class", "bar-stack");
        const open = gEl.querySelector(".bar-open"), paid = gEl.querySelector(".bar-paid");
        gEl.insertBefore(s, gEl.firstChild);
        if (open) s.appendChild(open);
        if (paid) s.appendChild(paid);
        gEl.removeAttribute("style");
        return s;
      });
      // (phones, round C, Astra #9: the chart's baseline, drawn with the chart's labels, so its first frame is a chart
      // whose bars are still down rather than an empty card)
      if (tall && groups.length) {
        const svg = st.querySelector("svg");
        const rects = [...st.querySelectorAll(".bar-open, .bar-paid")];
        const num = (el, a) => parseFloat(el.getAttribute(a)) || 0;
        const y0 = Math.max(...rects.map((r) => num(r, "y") + num(r, "height")));
        const x0 = Math.min(...rects.map((r) => num(r, "x"))), x1 = Math.max(...rects.map((r) => num(r, "x") + num(r, "width")));
        if (svg && rects.length && isFinite(y0)) {
          const ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
          ln.setAttribute("class", "fx-baseline");
          for (const [a, v] of [["x1", x0], ["x2", x1], ["y1", y0], ["y2", y0]]) ln.setAttribute(a, String(v));
          groups[0].parentNode.insertBefore(ln, groups[0]);
        }
      }
      const kpiEls = [...kpis.querySelectorAll(".kpi")];
      const values = kpiEls.map((el) => el.querySelector(".kpi-value"));
      const targets = values.map((v) => parseFloat(v.getAttribute("data-target")) || 0);
      const sparks = kpiEls.map((el) => el.querySelector(".spark"));
      // measure
      css(shape, "left", "0px"); css(shape, "top", "0px"); css(shape, "width", `${W}px`); css(shape, "height", `${H}px`);
      const size = stSize(st);
      const sk = skin(box, Z.chart);
      box.classList.add("skinless");
      const kr = vrect(kpis);
      const kW = kr.width, kH = kr.height;
      const surf = solid(sk.bg, dark ? [19, 22, 30, 1] : [255, 255, 255, 1]);
      const line = sk.bc[3] > 0.005 ? sk.bc : dark ? [255, 255, 255, 0.07] : [20, 20, 24, 0.08];
      const gapY = tall ? 12 : 26;                       // (phones, round B1: 12, the larger KPI type needs the room)
      const blockH = kH + gapY + sk.h;
      const top = Math.round(H / 2 - blockH / 2);
      const RC = { cx: W / 2, cy: top + kH + gapY + sk.h / 2, w: sk.w, h: sk.h, r: sk.r, bw: Math.max(1, sk.bw) };
      const kLeft = Math.round(W / 2 - kW / 2);
      // the October bar (the tallest; all paid): where the Ride dives, and its colour where the dive ends
      place(st, 1, RC, size, "center", Z.chart);
      drawShape(shape, RC, { fill: surf, line, lineA: 1, dark });
      const octPaid = groups[groups.length - 1].querySelector(".bar-paid");
      const octR = rectIn(octPaid, ctx.root);
      const accent = rgba(tok(box, "--accent"));
      // (the chart's content is fully in by 0.21: the Know -> Grow seam hands over at B0 = 0.22, the bars still down)
      // (phones: the three KPI cards stack above the chart and fill most of the stage, so they arrive during the wave's
      // second half instead of after it: the stage's top is never left empty for long)
      const B = tall ? { content: 0.05, bars: 0.26, wave: 0.38, kpiIn: 0.44, count: 0.5, spark: 0.54 }
        : { content: 0.05, bars: 0.26, wave: 0.38, kpiIn: 0.66, count: 0.72, spark: 0.76 };
      const n = stacks.length;
      const barT = stacks.map((_, i) => B.bars + B.wave * Math.pow(i / (n - 1), 0.9));
      const DUR = 2.3;
      const kpiShadow = (el) => satShadow(el, dark, vrect(el).height);
      kpiEls.forEach(kpiShadow);
      function seek(t) {
        drawShape(shape, RC, { fill: surf, line, lineA: 1, dark });
        place(st, alphaAt(t, B.content, 99), RC, size, "center", Z.chart);
        css(kpis, "left", `${(kLeft / Z.kpis).toFixed(2)}px`);
        css(kpis, "top", `${(top / Z.kpis).toFixed(2)}px`);
        // (phones, Sol mobile #11: the KPI cards are in from the Know -> Grow seam's second half, which reveals them;
        // their values stay hidden until the count starts, then count up on the app's own clock)
        const ka = tall ? 1 : alphaAt(t, B.kpiIn, 99);
        css(kpis, "opacity", ka >= 0.999 ? "1" : ka.toFixed(3));
        css(kpis, "filter", ka >= 0.999 ? "none" : `blur(${((1 - ka) * 7).toFixed(2)}px)`);
        // the app's own odometer: 900 ms easeOutCubic from $0, 80 ms stagger (dashboard.html animateOdometers)
        values.forEach((v, i) => {
          const u = clamp((t - B.count - 0.08 * i) / 0.9);
          v.textContent = money0(targets[i] * E.CUBIC_OUT(u));
          // (phones, round C, Astra #9: the slots read "$0", the count's own start, from the first visible frame)
        });
        // the sparklines draw (style.css sparkReveal: a 700 ms wipe, cubic-bezier(.2,.7,.2,1))
        sparks.forEach((s, i) => {
          const u = P(t, B.spark + 0.08 * i, 0.7, FX.bezier(0.2, 0.7, 0.2, 1));
          css(s, "clip-path", u >= 1 ? "none" : `inset(0 ${((1 - u) * 100).toFixed(2)}% 0 0)`);
        });
        // the bars: one quick wave left to right; this month lands last with the one accent bounce
        stacks.forEach((s, i) => {
          const x = i / (n - 1);
          const kk = i === n - 1 ? spring(t - barT[i], 2.0, 0.76) : spring(t - barT[i], 3.0 + 0.6 * x, 0.86);
          css(s, "transform", kk >= 1 ? "none" : `scaleY(${Math.max(0, kk).toFixed(4)})`);
        });
      }
      const IN = { ...RC, fill: surf, line };
      const OUT = { ...RC, fill: surf, line };
      function leave(kk) {
        const a = 1 - E.ACCEL(clamp(kk));
        css(st, "opacity", a.toFixed(3));
        css(kpis, "opacity", a.toFixed(3));
      }
      const EVENTS = [
        { t: B.content, what: "the chart card's labels: Revenue, the twelve months, the axis (the bars still down)" },
        { t: B.bars, what: "the bars rise left to right in one quick wave" },
        { t: barT[n - 1], what: "October (the year's highest, all paid) lands last" },
        { t: B.count, what: `the KPIs arrive and count up (the app's 900 ms odometer): ${money0(targets[0])} Collected YTD` },
        { t: B.spark, what: "the Collected YTD sparkline draws (sparkReveal)" },
      ];
      const X = { shape, RC, surf, line, kpis, st, size, zc: Z.chart, kpiTop: top, kLeft, zk: Z.kpis };
      return { DUR, seek, IN, OUT, leave, EVENTS, B, octR, octColor: (fy) => over([accent[0], accent[1], accent[2], 0.95 - 0.4 * fy], surf), label: "Grow", END: DUR, X };
    },
  };

  /* =================================================================================================================
     THE RIDE (Grow -> Chase): the camera dives up the tallest bar until its colour fills the frame; that colour field
     becomes the next section's backdrop. Transform-only, one move, 0.86 s. Skipped under reduced motion.
     ================================================================================================================= */
  FX.ride = function (grow, rootEl, W, H) {
    // the path: the camera settles on October's bar near its base, then rides UP the bar (through its own gradient,
    // light at the base, deep at the top) while the zoom accelerates, until the bar's colour is the whole frame.
    // One curve (a quadratic Bezier through the base) so the turn never jolts; transform only.
    const b = grow.octR;
    const fy = 0.12;                                   // where the dive ends: just under the bar's rounded top
    const S1 = Math.max(W / b.w, H / (b.h * 0.24)) * 1.3;
    const P0 = [W / 2, H / 2], P1 = [b.x + b.w / 2, b.y + b.h * 0.92], P2 = [b.x + b.w / 2, b.y + b.h * fy];
    const DIVE = 0.84, DUR = 0.94;
    const glide = FX.bezier(0.42, 0, 0.22, 1);
    const color = grow.octColor(fy);
    function at(t) {
      const u = clamp(t / DIVE);
      const e = glide(u);
      const fx = (1 - e) * (1 - e) * P0[0] + 2 * e * (1 - e) * P1[0] + e * e * P2[0];
      const fyy = (1 - e) * (1 - e) * P0[1] + 2 * e * (1 - e) * P1[1] + e * e * P2[1];
      const s = Math.exp(Math.log(S1) * Math.pow(u, 2.3));   // slow, then the dive accelerates into the bar
      return { s, x: W / 2 - fx * s, y: H / 2 - fyy * s };
    }
    return { DUR, DIVE, color, seek(t) {
      const c = at(t);
      css(rootEl, "transform", t <= 0 ? "none" : `translate(${c.x.toFixed(2)}px, ${c.y.toFixed(2)}px) scale(${c.s.toFixed(4)})`);
    } };
  };

  /* =================================================================================================================
     05 CHASE (on the Ride's colour field): an overdue row -> its Email action -> the compose modal grows from the button
     -> Send -> "Email sent." -> later, on the dashboard, a visible mark-paid press: the status inks from the click, the
     word swaps, the totals update (the app's own applyDashboardDelta: 400 ms easeOutCubic).
     ================================================================================================================= */
  S.chase = {
    build(ctx) {
      const { world, W, H, tall, dark } = ctx;
      const k = KIT().chase;
      const Z = tall ? { list: 1.42, icon: 1.42, modal: 1.0, toast: 2.3, recent: 1.12, kpis: 1.12 }
        : { list: 1.1, icon: 1.1, modal: 1.18, toast: 2.6, recent: 1.08, kpis: 0.84 };
      // A: the list card (Overdue view: the year header + the chased row, with its row actions)
      const shapeA = div("fx-shape", world);
      div("fx-ink", shapeA);
      const listCls = tall ? "d-list no-date client-status" : "d-list no-date";
      const header = withYearTotal(KIT().know.years["2026"], k.total);
      const stA = addSt(shapeA, `<div id="invoices-page" class="redesigned ${listCls}"><div class="card"><div class="table-scroll"><table>${KIT().know.thead}<tbody>${header}${k.listRow}</tbody></table></div></div></div>`, Z.list);
      const boxA = stA.querySelector(".card");
      const rowA = stA.querySelector("tbody tr:not(.year-header)");
      const emailBtn = [...rowA.querySelectorAll(".icon-btn")].find((b) => /email/i.test(b.getAttribute("title") || ""));
      emailBtn.classList.add("fx-email");
      // B: one shape: the Email button -> the compose modal -> the toast -> the dashboard's Recent invoices card
      const shapeB = div("fx-shape", world);
      const inkB = div("fx-ink", shapeB);
      const stM = addSt(shapeB, `<div id="invoice-detail" class="redesigned d-compose">${k.compose}</div>`, Z.modal);
      const boxM = stM.querySelector(".email-compose-modal");
      for (const f of stM.querySelectorAll(".email-compose-field")) {
        const lab = f.querySelector("label");
        if (lab && /^(Cc|Bcc)$/.test(lab.textContent.trim())) f.classList.add("fx-hide");
      }
      const sendBtn = stM.querySelector("#email-compose-send-btn");
      const stT = addSt(shapeB, `<div class="redesigned d-toast">${k.toast}</div>`, Z.toast);
      const boxT = stT.querySelector(".flash");
      const stR = addSt(shapeB, `<div id="dashboard-page" class="redesigned d-recent${tall ? " fx-chase-recent" : ""}">${k.recentSent}</div>`, Z.recent);
      if (tall) stT.style.setProperty("--sz", String(Z.toast));           // (phones: "Email sent." at 14 screen px, 44 px tall)
      if (tall) {
        const rows = [...stR.querySelectorAll("tbody tr")];
        rows.forEach((tr, i) => { if (i >= 2 && !tr.textContent.includes(k.number)) tr.remove(); });
      }
      const boxR = stR.querySelector(".card");
      const rowR = [...stR.querySelectorAll("tbody tr")].find((tr) => tr.textContent.includes(k.number));
      // the mark-paid control: ONE real pill (button.status-toggle). The old word leaves first; at the pop's peak the
      // app swaps the class (and so the width) at once; the Paid tint inks from the press point; the new word arrives.
      const pill = rowR.querySelector(".status-toggle");
      const clsOld = pill.className, clsNew = clsOld.replace(/status-(overdue|outstanding)/, "status-paid");
      const oldWord = pill.textContent.trim();
      const newWord = (() => { const d = document.createElement("tbody"); d.innerHTML = k.rowPaid; return d.querySelector(".status-toggle").textContent.trim(); })();
      pill.innerHTML = `<span class="fx-pink"></span><span class="fx-w fx-old">${esc(oldWord)}</span><span class="fx-w fx-new">${esc(newWord)}</span>`;
      const pInk = pill.querySelector(".fx-pink"), wOld = pill.querySelector(".fx-old"), wNew = pill.querySelector(".fx-new");
      const cls0 = (el) => (el.getAttribute("class") || "").replace(/\b(fe-hover|fe-active)\b/g, "").replace(/\s+/g, " ").trim();
      const rowABase = cls0(rowA), emailBase = cls0(emailBtn), sendBase = cls0(sendBtn), rowRBase = cls0(rowR);
      // the KPI cards (the dashboard's real row): before -> after values computed per frame by the app's own tween
      const kp = div("fx-free", world);
      kp.style.zoom = Z.kpis;
      if (tall) { kp.style.setProperty("--sz", String(Z.kpis)); kp.classList.add("fx-chase-kpis"); }
      const kpiMarkup = `<div class="kpi-row">${k.kpiPaidBefore}${k.kpiDueBefore}${k.kpiOverdueBefore}</div>`;
      kp.innerHTML = `<div id="dashboard-page" class="redesigned d-kpis">${kpiMarkup}</div>`;
      const kpiCards = [...kp.querySelectorAll(".kpi")];
      const valPaid = kp.querySelector(".kpi-paid .kpi-value"), valOver = kp.querySelector(".kpi-overdue .kpi-value");
      const footOver = kp.querySelector(".kpi-overdue .kpi-foot");
      const footAfter = (() => { const d = document.createElement("div"); d.innerHTML = k.kpiOverdueAfter; return d.querySelector(".kpi-foot"); })();
      const footBeforeHTML = footOver ? footOver.innerHTML : "", footAfterHTML = footAfter ? footAfter.innerHTML : "";

      // ---- measure
      for (const sh of [shapeA, shapeB]) { css(sh, "left", "0px"); css(sh, "top", "0px"); css(sh, "width", `${W}px`); css(sh, "height", `${H}px`); }
      css(stA, "display", "inline-block");
      fitYearHeader(stA.querySelector("table"));
      const szA = stSize(stA), szM = stSize(stM), szT = stSize(stT), szR = stSize(stR);
      const skA = skin(boxA, Z.list), skM = skin(boxM, Z.modal), skT = skin(boxT, Z.toast), skR = skin(boxR, Z.recent);
      // where the Email button sits inside the list card, and the Send button inside the modal (canvas, centred)
      const aBox = vrect(boxA), eB = vrect(emailBtn), rB = vrect(rowA);
      const mBox = vrect(boxM), sB = vrect(sendBtn);
      // the pill before and after the swap (measured both ways, then put back): colours and the press point inside it
      css(wNew, "display", "none");
      const rBox = vrect(boxR), pB = vrect(pill), rowRB = vrect(rowR);
      const softOld = rgba(getComputedStyle(pill).backgroundColor);
      pill.className = clsNew; css(wOld, "display", "none"); css(wNew, "display", "inline");
      const pB2 = vrect(pill);
      const softNew = rgba(getComputedStyle(pill).backgroundColor);
      pill.className = clsOld; css(wOld, "display", "inline"); css(wNew, "display", "none");
      const kr = vrect(kp);
      const emailSkin = skin(emailBtn, Z.list);
      for (const el of [boxA, boxM, boxT, boxR]) el.classList.add("skinless");
      for (const s of [stA, stM, stT, stR]) css(s, "display", "none");
      const surfA = solid(skA.bg, dark ? [19, 22, 30, 1] : [255, 255, 255, 1]);
      const surfM = solid(skM.bg, surfA), surfT = solid(skT.bg, surfA), surfR = solid(skR.bg, surfA);
      const lineOf = (s) => (s.bc[3] > 0.005 ? s.bc : dark ? [255, 255, 255, 0.07] : [20, 20, 24, 0.08]);
      const CX = W / 2, CY = H / 2;
      const RA = { cx: CX, cy: CY, w: skA.w, h: skA.h, r: skA.r, bw: Math.max(1, skA.bw) };
      const emailAt = [RA.cx - skA.w / 2 + (eB.left - aBox.left) + eB.width / 2, RA.cy - skA.h / 2 + (eB.top - aBox.top) + eB.height / 2];
      const RI = { cx: emailAt[0], cy: emailAt[1], w: eB.width, h: eB.height, r: Math.max(4, emailSkin.r), bw: 0 };
      const RM = { cx: CX, cy: CY, w: skM.w, h: skM.h, r: skM.r, bw: Math.max(1, skM.bw) };
      const sendAt = [RM.cx - skM.w / 2 + (sB.left - mBox.left) + sB.width * 0.42, RM.cy - skM.h / 2 + (sB.top - mBox.top) + sB.height * 0.6];
      // (phones, Astra pA #2: after the Email press the overdue row stays; the modal opens over it, and "Email sent."
      // lands 14 screen px under it, the two one group centred in the stage, until the dashboard takes over)
      const ds = parseFloat(getComputedStyle(ctx.root).getPropertyValue("--demo-scale")) || 0.55;
      // (phones, round C, Astra #3: the group sits low, its bottom 40 screen px above the "Fictional data" row, which is
      // 8 px under the stage: the action next to its caption, not floating mid-field)
      const grpTop = Math.round(H - 32 / ds - (skA.h + 14 / ds + skT.h));
      // (phones, round C, Astra #13: the row card, the modal, the toast and the Recent card are small floating cards)
      const LITE = tall ? { y: 6 / ds, b: 18 / ds } : null;
      const RAt = tall ? { ...RA, cy: grpTop + skA.h / 2 } : RA;
      const RT = { cx: CX, cy: tall ? grpTop + skA.h + 14 / ds + skT.h / 2 : CY, w: skT.w, h: skT.h, r: skT.h / 2, bw: Math.max(1, skT.bw) };
      const gapY = tall ? 18 : 24;
      const blockH = kr.height + gapY + skR.h;
      const kTop = Math.round(H / 2 - blockH / 2);
      const RR = { cx: CX, cy: kTop + kr.height + gapY + skR.h / 2, w: skR.w, h: skR.h, r: skR.r, bw: Math.max(1, skR.bw) };
      const pillAt = [RR.cx - skR.w / 2 + (pB.left - rBox.left) + pB.width * 0.8, RR.cy - skR.h / 2 + (pB.top - rBox.top) + pB.height * 0.6];
      const rowRect = { x: RA.cx - skA.w / 2 + (rB.left - aBox.left), y: RA.cy - skA.h / 2 + (rB.top - aBox.top), w: rB.width, h: rB.height };
      const rowRRect = { x: RR.cx - skR.w / 2 + (rowRB.left - rBox.left), y: RR.cy - skR.h / 2 + (rowRB.top - rBox.top), w: rowRB.width, h: rowRB.height };
      const kLeft = Math.round(CX - kr.width / 2);
      kpiCards.forEach((el) => satShadow(el, dark, vrect(el).height));
      const B = { toRow: 0.22, toEmail: 0.62, pressEmail: 0.98, grow: 1.02, toSend: 1.74, pressSend: 2.3, morphToast: 2.44,
        morphDash: 3.68, toPill: 4.67, pressPill: 5.27, away: 5.59 };
      B.swapPill = +(B.pressPill + 0.12).toFixed(3);
      B.count = B.swapPill + 0.04;
      const DUR = 6.55;
      // (phones, Sol mobile P1 #4: the list card is whole and populated from local time 0, never an empty shell; it is
      // also what the Ride hands over to. Desktop keeps its arrival from 90 %.)
      const GA = tall ? geom([[0, RA], [0.0001, RA, 2.6, 0.86], [B.morphToast, RAt, 3.2, 0.88]]) : geom([[0, { ...RA, w: RA.w * 0.9, h: RA.h * 0.9 }], [0.0001, RA, 2.6, 0.86]]);
      const GB = geom([[0, RI], [B.grow, RM, 2.6, 0.86], [B.morphToast, RT, 3.2, 0.88], [B.morphDash, RR, 2.4, 0.84]]);
      const FB = colTrack([[0, surfA], [B.grow, surfM, 2.6, 0.86], [B.morphToast, surfT, 3.2, 0.88], [B.morphDash, surfR, 2.4, 0.84]]);
      // site v2.2 (Astra's review: "no empty shell"): the one shape always carries content. Each morph's outgoing content
      // leaves WITH the move (never before it) and the incoming content arrives during it, overlapping:
      // - the modal zooms out of the Email button with its content in it (scaled to fit, arriving at once);
      // - closing into the toast, the modal's content stays put, cropped by the shrinking shape, and fades over 160 ms;
      //   "Email sent." arrives in its last 60 ms;
      // - growing into the Recent card, the toast's words fade over 120 ms where they were; the card's content is
      //   revealed in place by the growing shape from 60 ms (before the toast's words have gone).
      const SCHED = { A: [tall ? -1 : 0.08] };          // (-1: in from the start; inOut treats a negative tin as already in)
      const M_IN = B.grow + 0.02, M_OUT = B.morphToast, M_OD = 0.16;
      const T_IN = B.morphToast + 0.1, T_OUT = B.morphDash, T_OD = 0.12;
      const R_IN = B.morphDash + 0.06;
      // a content's alpha: in over 0.16 s (DECEL), out over od (ACCEL)
      const inOut = (t, tin, tout, od) => Math.min(tin < 0 ? 1 : P(t, tin, 0.16, E.DECEL), 1 - P(t, tout, od, E.ACCEL));
      // a content box anchored at its own rest rect R while the shape g moves (the shape crops it; it is never squashed)
      const anchored = (st, a, g, R, size, z) => placeSt(st, a, g.w / 2 - size.cw / 2 + (R.cx - g.cx), g.h / 2 - size.ch / 2 + (R.cy - g.cy), z);
      const cur = new Cursor(world, tall ? 40 : 36);
      cur.keys = [[0, [W * 0.94, H * 1.04]], [B.toRow, [rowRect.x + rowRect.w * 0.56, rowRect.y + rowRect.h * 0.88], 1.8, 0.95],
        [B.toEmail, [emailAt[0] + eB.width * 0.12, emailAt[1] + eB.height * 0.18], 2.2, 0.93], [B.toSend, sendAt, 1.9, 0.93],
        [B.toPill, pillAt, 1.9, 0.93], [B.away, [W * 1.04, H * 1.06], 1.3, 1.0]];
      cur.presses = [B.pressEmail, B.pressSend, B.pressPill];
      cur.fade = [0.05, B.away + 0.14];
      // (phones, round B2, Astra pA #15: once Send is pressed and the toast shows, the hand leaves; it returns as it sets
      // off for the Paid pill. Scrubbing back brings it back: a pure function of t.)
      if (tall) cur.gaps = [[B.morphToast, B.toPill - 0.05]];
      // the press point in the new pill's own box (unzoomed px): the pill's right end stays put (the cell is right-aligned)
      const pressLocal = [((pB.left + pB.width * 0.8) - pB2.left) / Z.recent, (pB.height * 0.6) / Z.recent];
      const pW2 = pB2.width / Z.recent, pH2 = pB2.height / Z.recent;
      function seek(t) {
        // A: the list card, then (once its Email button is pressed) it fades away, content and card together
        const ga = GA(t);
        // the card arrives on the field (fades up as it grows from 90 %), and fades once its button has been pressed,
        // its content with it (site v2.2: never an empty card)
        // (phones: the card stays through the email and leaves as the dashboard grows, which carries the same row)
        const A_OUT = tall ? B.morphDash : B.pressEmail + 0.06, A_OD = tall ? 0.12 : 0.2;
        // (phones, round E: the open modal covered the row card's middle and left its edges cut on both sides; the row
        // steps aside while the modal is up, inside the grow and the close, and is back for "Email sent." under it)
        const cover = tall ? P(t, M_IN, 0.16, E.DECEL) * (1 - P(t, M_OUT + M_OD, 0.16, E.DECEL)) : 0;
        const aA = inOut(t, SCHED.A[0], A_OUT, A_OD) * (1 - cover);
        const skinA = Math.min(tall ? 1 : P(t, 0, 0.14, E.DECEL), 1 - P(t, A_OUT, A_OD, E.ACCEL)) * (1 - cover);
        drawShape(shapeA, ga, { fill: surfA, line: lineOf(skA), lineA: 1, dark, alpha: skinA <= 0.001 ? 0 : skinA, lite: LITE });
        place(stA, aA, ga, szA, "center", Z.list);
        const hand = FX.gate.cursor > 0.5, pr = FX.gate.press > 0.5;
        FX.flags(rowA, rowABase, [["fe-hover", hand && t > 0.5 && t < B.pressEmail + 0.06]]);
        FX.flags(emailBtn, emailBase, [["fe-hover", hand && t > B.toEmail + 0.25 && t < B.pressEmail + 0.06],
          ["fe-active", pr && t > B.pressEmail && t < B.pressEmail + 0.08]]);
        // B: grows from the button into the modal, shrinks into the toast, then grows into the Recent card
        const on = t >= B.grow - 0.02;
        const gb = GB(t);
        // (the modal has no :active rule: it never squashes; Send squashes in place through the app's own .btn:active)
        drawShape(shapeB, gb, { fill: FB(t), line: lineOf(t < B.morphToast ? skM : t < B.morphDash ? skT : skR), lineA: 1, dark, alpha: on ? 1 : 0, sh: on ? clamp((t - B.grow) / 0.15) : 0, lite: LITE });
        drawInk(inkB, { mode: "none" });
        // the modal's content: zooming out of the button with the shape (scaled to fit, centred), then (from the toast
        // morph) where it rests, cropped by the closing shape
        // (phones, round E: the screen-size text left no slack, so a crop cut words mid-letter; on phones the closing
        // modal's content shrinks with its shape as it grew with it, the toast's words have left as the Recent card
        // starts to grow, and the card's content grows with its shape: nothing is ever cut by a moving edge)
        const fit = (st, a, R, size, z) => {
          place(st, a, gb, size, "center", z);
          const k = Math.min(1, gb.w / R.w, gb.h / R.h);
          if (a > 0.001 && k < 0.9999) css(st, "transform", `scale(${Math.max(0.001, k).toFixed(5)})`);
        };
        const am = inOut(t, M_IN, M_OUT, tall ? T_IN - M_OUT : M_OD);   // (phones: gone as "Email sent." arrives)
        if (t < M_OUT || tall) fit(stM, am, RM, szM, Z.modal);
        else anchored(stM, am, gb, RM, szM, Z.modal);
        // the toast's words: centred in the closing shape (where the toast rests), then left where they are as the card
        // grows around them
        const at = inOut(t, T_IN, tall ? T_OUT - T_OD : T_OUT, T_OD);
        if (t < T_OUT) place(stT, at, gb, szT, "center", Z.toast);
        else anchored(stT, at, gb, RT, szT, Z.toast);
        // the Recent card's content: where it rests, revealed by the growing shape
        if (tall) fit(stR, inOut(t, R_IN, 99, 0.1), RR, szR, Z.recent);
        else anchored(stR, inOut(t, R_IN, 99, 0.1), gb, RR, szR, Z.recent);
        FX.flags(sendBtn, sendBase, [["fe-hover", hand && t > B.toSend + 0.3 && t < B.pressSend + 0.1],
          ["fe-active", pr && t > B.pressSend && t < B.pressSend + 0.08]]);
        // the KPI cards arrive above the Recent card (the dashboard's own order)
        const ka = alphaAt(t, B.morphDash + 0.26, 99);
        css(kp, "left", `${(kLeft / Z.kpis).toFixed(2)}px`);
        css(kp, "top", `${((kTop + 8 * (1 - ka)) / Z.kpis).toFixed(2)}px`);
        css(kp, "opacity", ka >= 0.999 ? "1" : ka.toFixed(3));
        css(kp, "display", ka > 0.001 ? "block" : "none");
        // the mark-paid press: the app's statusPop (scale to 1.18 at 40 % of 400 ms), its class swap at the peak;
        // the Paid tint inks from the press point, the word swaps (the old leaves first: two words never share a frame)
        const pu = (t - B.pressPill) / 0.4;
        let ps = 1;
        if (pu > 0 && pu < 1) ps = pu < 0.4 ? 1 + 0.18 * E.SMOOTH(pu / 0.4) : 1.18 - 0.18 * E.SMOOTH((pu - 0.4) / 0.6);
        ps = 1 + (ps - 1) * FX.gate.press;                // a pop played backwards would read as a glitch
        const hov = hand && t > B.toPill + 0.3 && t < B.pressPill;
        const sc = ps * (hov ? 1.05 : 1);                 // .status-toggle:hover is scale(1.05) in the app
        css(pill, "transform", sc === 1 ? "none" : `scale(${sc.toFixed(4)})`);
        FX.flags(rowR, rowRBase, [["fe-hover", hand && t > B.toPill + 0.2 && t < B.away]]);
        const swapped = t >= B.swapPill;
        pill.className = swapped ? clsNew : clsOld;
        const ik = P(t, B.swapPill, 0.2, E.OPEN);
        css(pill, "background", swapped && ik < 1 ? cssC(softOld) : "");
        css(pInk, "display", swapped && ik < 1 ? "block" : "none");
        css(pInk, "background", cssC(softNew));
        const far = Math.hypot(Math.max(pressLocal[0], pW2 - pressLocal[0]), Math.max(pressLocal[1], pH2 - pressLocal[1])) + 3;
        const rr = ik * far;
        const m = `radial-gradient(circle at ${pressLocal[0].toFixed(1)}px ${pressLocal[1].toFixed(1)}px, #000 ${Math.max(0, rr - 3).toFixed(1)}px, transparent ${rr.toFixed(1)}px)`;
        css(pInk, "-webkit-mask-image", m); css(pInk, "mask-image", m);
        const outA = 1 - P(t, B.pressPill + 0.02, 0.1, E.ACCEL);
        css(wOld, "display", swapped ? "none" : "inline");
        css(wOld, "opacity", outA.toFixed(3));
        css(wNew, "display", swapped ? "inline" : "none");
        const inA = P(t, B.swapPill + 0.11, 0.16, E.DECEL);
        css(wNew, "opacity", inA.toFixed(3));
        // the totals: the app's own applyDashboardDelta tween (400 ms easeOutCubic), values computed per frame
        const u = E.CUBIC_OUT(clamp((t - B.count) / 0.4));
        if (valPaid) valPaid.textContent = money0(mix(k.kpisBefore.collected, k.kpisAfter.collected, u));
        if (valOver) valOver.textContent = money0(mix(k.kpisBefore.overdue, k.kpisAfter.overdue, u));
        if (footOver) { const want = t >= B.count ? footAfterHTML : footBeforeHTML; if (footOver.innerHTML !== want) footOver.innerHTML = want; }
        cur.draw(t);
      }
      const IN = { ...RA, fill: surfA, line: lineOf(skA) };
      const OUT = { ...RR, fill: surfR, line: lineOf(skR) };
      function leave(kk) {
        const a = 1 - E.ACCEL(clamp(kk));
        for (const s of [stA, stM, stT, stR]) if (s.style.display !== "none") css(s, "opacity", (a * parseFloat(s.style.opacity || "1")).toFixed(3));
        css(kp, "opacity", (a * parseFloat(kp.style.opacity || "1")).toFixed(3));
        cur.el.style.display = "none";
      }
      const EVENTS = [
        { t: 0, what: `the Overdue row: ${k.number} ${k.client} ${FX.money(k.total)}` },
        { t: B.pressEmail, what: "press: the row's Email action (click 1)" },
        { t: B.grow, what: "the compose modal grows from the button (pre-filled: To, Subject, Message, the PDF)" },
        { t: B.pressSend, what: "press: Send (click 2)" },
        { t: B.morphToast, what: "the modal shrinks into the toast: Email sent." },
        { t: B.morphDash, what: "later, the dashboard: Recent invoices (the row carries the sent ring) + the KPIs" },
        { t: B.pressPill, what: "press: Overdue -> Paid (statusPop; the tint inks from the click; the word swaps)" },
        { t: B.count, what: `the totals update: Collected YTD ${money0(k.kpisBefore.collected)} -> ${money0(k.kpisAfter.collected)}, Overdue ${money0(k.kpisBefore.overdue)} -> ${money0(k.kpisAfter.overdue)}` },
      ];
      const X = { shapeB, inkB, RR, surfR, lineR: lineOf(skR), stR, szR, zR: Z.recent, kp };
      return { DUR, seek, IN, OUT, leave, EVENTS, B, label: "Chase", END: 6.05, X };
    },
  };

  /* =================================================================================================================
     06 YOURS (site v2): Settings -> Data storage, the released card that says where everything lives ("Your invoices,
     clients, settings, logos, and documents are saved in this folder."). The Chase -> Yours seam files the sent
     invoice into its folder icon. A short, self-contained beat: the story can drop it (Chase -> Price) without change.
     ================================================================================================================= */
  S.yours = {
    build(ctx) {
      const { world, W, H, tall, dark } = ctx;
      const k = KIT().yours;
      // (phones, F2: the phone story now shows this card under its own caption) a narrower card at a larger zoom, so its
      // words read at ~11-12 px on a ~300-340 px stage instead of ~7 px (site.css .fx-root.tall .d-settings .card)
      const Z = tall ? 1.8 : 1.3;
      const shape = div("fx-shape", world);
      div("fx-ink", shape);
      const st = addSt(shape, `<div id="settings-page" class="redesigned d-settings">${k.dataCard}</div>`, Z);
      const box = st.querySelector(".card");
      // (phones, F2b) the folder's path in full: the app's one-line input clips it at this card's width ("…/Freelanc"), so
      // the phone's picture shows the same value as text that wraps after a slash (site.css .fx-root.tall .path-val)
      const inp = tall && st.querySelector(".path-input input");
      if (inp) {
        const v = document.createElement("span");
        v.className = "path-val";
        inp.value.split("/").forEach((p, i) => { if (i) { v.append("/"); if (i > 1) v.append(document.createElement("wbr")); } v.append(p.replace(/ /g, " ")); });
        inp.replaceWith(v);
      }
      css(shape, "left", "0px"); css(shape, "top", "0px"); css(shape, "width", `${W}px`); css(shape, "height", `${H}px`);
      const size = stSize(st);
      const sk = skin(box, Z);
      box.classList.add("skinless");
      const surf = solid(sk.bg, dark ? [19, 22, 30, 1] : [255, 255, 255, 1]);
      const line = sk.bc[3] > 0.005 ? sk.bc : dark ? [255, 255, 255, 0.07] : [20, 20, 24, 0.08];
      const R = { cx: W / 2, cy: H / 2, w: sk.w, h: sk.h, r: sk.r, bw: Math.max(1, sk.bw) };
      drawShape(shape, R, { fill: surf, line, lineA: 1, dark });
      place(st, 1, R, size, "center", Z);
      const ic = rectIn(st.querySelector(".path-input .ic"), ctx.root);
      css(st, "display", "none");
      const DUR = 0.9;
      function seek(t) {
        drawShape(shape, R, { fill: surf, line, lineA: 1, dark });
        css(shape, "-webkit-mask-image", "none");          // (the Chase -> Yours seam reveals the card through a disc)
        css(shape, "mask-image", "none");
        place(st, alphaAt(t, 0.05, 99), R, size, "center", Z);
      }
      const X = { shape, R, surf, line, st, size, Z, folder: { cx: ic.x + ic.w / 2, cy: ic.y + ic.h / 2, w: ic.w, h: ic.h } };
      return { DUR, seek, EVENTS: [{ t: 0.05, what: "Settings -> Data storage: the folder that holds everything" }], B: {}, label: "Yours", START: 0.3, END: DUR, X };
    },
  };

  /* =================================================================================================================
     BRAND (the Resolve seam): the last shape, a light paper, resolves into the real Freelance Easy mark.
     ================================================================================================================= */
  S.brand = {
    build(ctx) {
      const { world, W, H, dark } = ctx;
      const shape = div("fx-shape", world);
      const ink = div("fx-ink", shape);
      const pimg = document.createElement("img");
      pimg.src = "/assets/story/paper/INV1056-modern.svg";
      pimg.alt = "";
      css(pimg, "position", "absolute"); css(pimg, "inset", "0"); css(pimg, "width", "100%"); css(pimg, "height", "100%");
      shape.appendChild(pimg);
      const mark = document.createElement("img");
      mark.src = "/assets/story/fe-mark.png";
      mark.alt = "";
      mark.className = "fx-mark";
      world.appendChild(mark);
      const MS = 128, mx = (W - MS) / 2, my = (H - MS) / 2;
      // the tile inside the mark's image (measured on assets/fe-mark.png: x 19-235, y 8-237 of 256)
      const tile = { cx: mx + ((19 + 235) / 2 / 256) * MS, cy: my + ((8 + 237) / 2 / 256) * MS, w: (216 / 256) * MS, h: (229 / 256) * MS, r: 28, bw: 0 };
      const ph = 112, pw = Math.round((ph * 612) / 792);
      const RP = { cx: W / 2, cy: H / 2, w: pw, h: ph, r: 10, bw: 1 };
      const B = { paperIn: 0.04, out: 0.6, morph: 0.68, seal: 0.9, markIn: 1.1 };
      const DUR = 1.7;
      const G = geom([[0, RP], [B.morph, tile, 2.4, 0.84]]);
      const tileC = [6, 10, 15, 1];
      function seek(t) {
        const g = G(t);
        const a = alphaAt(t, B.paperIn, B.out);
        const markA = P(t, B.markIn, 0.18, E.DECEL);
        drawShape(shape, g, { fill: [255, 255, 255, 1], line: [20, 20, 24, 0.08], lineA: 1 - P(t, B.morph, 0.2), dark, rimA: 0, alpha: markA >= 1 ? 0 : 1 });
        css(pimg, "opacity", a.toFixed(3));
        const sk = P(t, B.seal, 0.18, E.CLOSE);
        drawInk(ink, { mode: t < B.seal ? "none" : sk >= 1 ? "full" : "disc", k: sk, x: g.w / 2, y: g.h / 2, w: g.w, h: g.h, color: tileC });
        css(mark, "left", `${mx}px`);
        css(mark, "top", `${my}px`);
        css(mark, "opacity", markA >= 0.999 ? "1" : markA.toFixed(3));
        css(mark, "display", markA > 0.001 ? "block" : "none");
      }
      return { DUR, seek, EVENTS: [{ t: B.morph, what: "the paper resolves into the mark's tile" }, { t: B.markIn, what: "the real FE mark" }], B, label: "Brand" };
    },
  };

  /* =================================================================================================================
     THE MORPH SEAM (default): the outgoing piece's main shape springs into the incoming piece's first card.
     ================================================================================================================= */
  FX.morphSeam = function (layer, from, to, dark) {
    // the spring starts at the seam's t = 0 (the job has already let the outgoing content leave); 99.5 % there by 0.30 s
    const shape = div("fx-shape", layer);
    const DUR = 0.3;
    const G = geom([[0, from], [0.0001, to, 2.4, 0.84]]);
    const F = colTrack([[0, from.fill], [0.0001, to.fill, 2.4, 0.84]]);
    const L = colTrack([[0, from.line || to.line], [0.0001, to.line || from.line, 2.4, 0.84]]);
    const rim0 = from.rim == null ? 1 : from.rim, rim1 = to.rim == null ? 1 : to.rim;
    return {
      DUR, el: shape,
      seek(t) {
        const k = spring(t, 2.4, 0.84);
        drawShape(shape, G(t), { fill: F(t), line: L(t), lineA: 1, dark, rimA: mix(rim0, rim1, k) });
      },
      remove() { shape.remove(); },
    };
  };
})();
