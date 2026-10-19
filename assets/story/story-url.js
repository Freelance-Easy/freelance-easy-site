/* story-url.js (C4): the homepage story's URL + history, per docs/interaction-contract.md (ICX-HIST.1-.9, ICX-JUMP).
   The one owner of every history write the story makes. It listens to window.FEStory (assets/story/site.js, which writes
   none) and does nothing where FEStory is absent (this tag lives in the shared head partial, `defer`).

   - A step run or a FREE settle -> one replaceState at its FINAL landing (rendered == dest); passed-through landings write
     nothing (ICX-HIST.1/.8).
   - An explicit jump (rail, menu, Home/End, logo) -> one pushState at its final landing; gestures that extend
     the run keep that one push (ICX-HIST.2).
   - A focus landing (focus reaching an idle caption: Tab, a screen reader's cursor; source "focus") -> one replaceState at
     its final landing, like a step or a settle: keyboard traversal never stuffs Back with entries.
   - popstate -> FEStory.goTo(slug, {source: "popstate"}); never a write (ICX-HIST.3).
   - init / reload / deep link never write. One exception: a legacy hash (#top #how #pricing #download) is swapped for the
     chapter's own URL with one replaceState (ICX-HIST.6).
   - hashchange (a same-page #download / #how... link; the browser already added that entry) -> a jump to the chapter, then
     the entry's URL is normalised to the slug with replaceState (the length does not change).
   - The first chapter's URL is the plain path (no hash) (ICX-HIST.5). Theme hashes are never written (ICX-HIST.4/.7).
   - The logo on "/" is an ICX-JUMP to the first chapter (plain left click only).
   Native rows (tablet "Price", calm and classic): the page's own anchor scroll; the URL is written once the scroll arrives
   (ICX-JUMP.5). Scroll-spy inside native sections is the rail's (ICX-HIST.9), not this file's. */
(function () {
  "use strict";
  var F = window.FEStory;
  if (!F || typeof F.onLand !== "function" || typeof F.goTo !== "function") return;

  var FIRST = "new-invoice";
  var LEGACY = { top: "new-invoice", how: "templates", pricing: "price", download: "get-the-app" };
  var RANK = { pop: 0, replace: 1, hash: 2, push: 3 };

  function hashKey() { try { return decodeURIComponent(location.hash.slice(1)); } catch (e) { return ""; } }
  function rows() { try { return F.destinations || []; } catch (e) { return []; } }
  function rowOf(slug) { var r = rows(); for (var i = 0; i < r.length; i++) if (r[i].slug === slug) return r[i]; return null; }
  // a hash -> the chapter slug it names (legacy or current), else null
  function slugOf(key) { return LEGACY[key] || (rowOf(key) ? key : null); }
  function urlFor(slug) { return location.pathname + location.search + (slug === FIRST ? "" : "#" + slug); }
  function here() { return location.pathname + location.search + location.hash; }
  function copyState() {
    var s = history.state, o = {};
    if (s && typeof s === "object") for (var k in s) if (Object.prototype.hasOwnProperty.call(s, k)) o[k] = s[k];
    return o;
  }
  function stateFor(slug) { var o = copyState(); o.story = slug; return o; }
  // The entry a jump leaves is marked scrollRestoration "manual" (the mode is per entry): Back to it is the story's own
  // traversal (popstate -> goTo places the reader), never the browser's pixel restore. A native row's push is written at
  // its arrival, so "auto" would restore the ARRIVAL position over goTo's scroll (C4-engine: calm rail -> Templates ->
  // Back stayed on Templates). The new entry keeps the page's own mode (site.js: "auto" in calm / classic / static, so a
  // reload there keeps the exact pixel; "manual" in the story); popstate puts it back once its scroll has settled.
  function siteRestoration() { return ["calm", "classic", "static"].indexOf(F.mode) >= 0 ? "auto" : "manual"; }
  function setRestoration(m) { try { if ("scrollRestoration" in history && history.scrollRestoration !== m) history.scrollRestoration = m; } catch (e) { /* ignore */ } }
  // Back in a native mode (calm / classic / static) returns the reader to the exact pixel they left (main's ruling on Sol
  // C4-engine MEDIUM 3): before a push, the departing entry's state gets its scroll offset `y` (replaceState with no URL, so
  // the URL and history.length are untouched); popstate in a native mode restores it. `departY` is the offset where the jump
  // STARTED (a native row's push is written at its arrival, when scrollY is already the target's). The pinned modes save
  // nothing: the story's goTo places the reader there.
  // RELOAD: a reload carries the chapter URL the scroll-spy wrote (/#price), so the reader's place inside a native section
  // (any mode) or anywhere in calm / classic / static is kept: y (scrollY), w (innerWidth), m (FEStory.mode).
  //  - In the entry's state, with every chapter URL written for such a place (spy replace, a native jump's arrival, a settle).
  //  - In sessionStorage HELD when the page is left (pagehide, a hidden tab), since the reader may have scrolled on inside the
  //    section: a replaceState made in pagehide does not reach the reloaded entry (Chromium reloads the state it had before).
  //    The record names its entry by the state's key `k` (each written entry gets its own; a deep link's has none).
  // On load, when the URL's chapter is the one the record (same entry) or the state names, in the same mode at the same
  // width, that pixel is restored instead of the anchor landing: site.js's init in the story modes (heldY there reads the
  // same format), restoreHeld() below in calm / classic / static. Pinned rows keep ICX-JUMP.3 (nothing held); a fresh
  // deep link is a new entry and lands on the anchor; the load itself writes nothing (ICX-HIST.3).
  var HELD = "fe-story-held";
  function holdsPlace(slug) { var r = rowOf(slug); return siteRestoration() === "auto" || !!(r && r.kind === "native"); }
  function newKey() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }
  function entryKey() { var s = history.state; return s && typeof s === "object" && s.k ? s.k : null; }
  function mark(o, slug, y) {
    if (!o.k) o.k = newKey();
    delete o.y; delete o.w; delete o.m;
    if (holdsPlace(slug)) { o.y = Math.round(typeof y === "number" ? y : window.scrollY); o.w = window.innerWidth; o.m = F.mode; }
    return o;
  }
  // the chapter the URL names now: the plain path is the first chapter; a theme hash or a non-chapter id names none
  function urlSlug() { var k = hashKey(); return k === "" ? FIRST : slugOf(k); }
  // the held pixel for this entry's chapter `slug`, or null: the leave-time record first (newer), then the entry's state
  function heldY(slug) {
    var nav = null;
    try { nav = performance.getEntriesByType("navigation")[0].type; } catch (e) { nav = null; }
    if (nav !== "reload" && nav !== "back_forward") return null;   // a fresh visit (a deep link) lands on the anchor
    function fits(p) { return !!p && p.story === slug && typeof p.y === "number" && p.w === window.innerWidth && p.m === F.mode; }
    var p = null, s = history.state;
    try { p = JSON.parse(sessionStorage.getItem(HELD) || "null"); } catch (e) { p = null; }
    if (fits(p) && p.path === location.pathname && (p.k || null) === entryKey()) return Math.max(0, Math.round(p.y));
    if (s && typeof s === "object" && fits(s)) return Math.max(0, Math.round(s.y));
    return null;
  }

  function write(kind, slug, departY) {
    var url = urlFor(slug);
    try {
      if (kind === "push") {
        if (url !== here()) {
          var m = siteRestoration(), from = urlSlug();
          // the entry left keeps the reader's place when it holds one: anywhere in calm / classic, a native row in the
          // story modes (main's ruling on Sol RELOAD-1 HIGH 2: Back from a menu jump returns to the pixel, as the live site)
          if (m === "auto" || (from && holdsPlace(from))) {
            var cur = copyState();
            if (from && !cur.story) cur.story = from;
            cur.y = Math.round(typeof departY === "number" ? departY : window.scrollY);
            cur.w = window.innerWidth; cur.m = F.mode;
            history.replaceState(cur, "");
          }
          setRestoration("manual");
          var st = stateFor(slug);
          st.k = newKey();                             // a new entry: its own key (the copied one names the entry left)
          history.pushState(mark(st, slug), "", url);   // the arrival's place; refreshed when the reader leaves it
          setRestoration(m);
        }
      }
      else history.replaceState(mark(stateFor(slug), slug), "", url);
    } catch (e) { /* a sandboxed file:// page may refuse; the story still works */ }
  }

  /* ---- a legacy hash on load: one replaceState to the chapter's own URL (ICX-HIST.6) ---- */
  (function () {
    var s = LEGACY[hashKey()];
    if (s) write("replace", s);
  })();

  /* ---- the run in flight: what kind of write its final landing makes ---- */
  var pending = null;     // null | "pop" | "replace" | "hash" | "push"
  var intent = null;      // set only while this file calls goTo: "pop" | "hash" | "push"
  function raise(kind) { if (pending == null || RANK[kind] > RANK[pending]) pending = kind; }

  // A replaceState landing is written once no further dest change follows within QUIET ms: a dip lands (final) at its cut and
  // the gestures of a quick run (three steps 300 ms apart) arrive just after it, so the chapter they pass through is never
  // written (ICX-HIST.1, "a checkpoint passed through is never written"). A hidden tab flushes at once. A jump's pushState
  // is written at the landing itself, so Back right after it finds its entry (a later gesture replaces that entry's URL).
  var QUIET = 250;
  var queued = null, quietTimer = 0;
  function flush() {
    clearTimeout(quietTimer);
    var q = queued;
    queued = null;
    if (q) write(q.kind, q.slug);
  }
  function unqueue() {
    clearTimeout(quietTimer);
    if (queued) { pending = queued.kind; queued = null; }   // the run goes on: the same kind of write at its end
  }

  // where an explicit jump STARTED (its first dest event, before the story moves): a pinned jump's push is written at its
  // landing, when scrollY is already the target's; the entry it leaves keeps this offset (Back returns to it)
  var departY0 = null;
  F.onDest(function (p) {
    if (!p || p.preview || p.source === "free") return;
    if (p.source === "jump" && departY0 == null) departY0 = window.scrollY;
    unqueue();
    if (cancelArrival) { cancelArrival(); cancelArrival = null; }   // a pinned move supersedes a native jump still scrolling
    jumping = false;
    if (p.source === "popstate") raise("pop");
    else if (p.source === "jump") raise(intent === "hash" ? "hash" : "push");
    // focus reaching a caption: like a settle, it never STARTS a push (C4-engine). raise() keeps a higher pending kind, so a
    // focus landing that extends a run an explicit jump started keeps that run's one pushState: ICX-HIST.2 ("If gestures
    // extend the run after the jump, the run still writes one entry, with pushState, at its final landing, so Back undoes
    // the whole run"); main's ruling on Sol C4-engine HIGH 2 (test_focus_after_jump_keeps_one_push).
    else if (p.source === "focus") raise("replace");
    else raise("replace");                         // step, settle
  });

  F.onLand(function (p) {
    if (!p || !p.final) return;                    // a pass-through landing writes nothing (ICX-HIST.1)
    unqueue();
    var kind = pending, dy = departY0;
    pending = null; departY0 = null;
    if (p.source === "init") return;               // load, reload, deep link: never a write (ICX-HIST.3)
    if (kind == null) kind = p.source === "jump" ? "push" : p.source === "popstate" ? "pop" : "replace";
    // (INT5-fix round 2; Astra INT5-2) a Back onto a native row (its own scroll: no landing ever consumes its `pop`) leaves
    // `pop` pending; a re-entry is never Back's landing, so a stale `pop` does not silence it (ICX-HIST.8)
    if (p.reentry && kind === "pop") kind = "replace";
    if (kind === "pop") return;
    if (kind === "push") { write("push", p.slug, dy); return; }   // at the landing itself: Back must find the entry
    // (INT5-fix 6) a re-entry from below (the page scrolled back into the pinned story from a native section or the footer)
    // is a FREE settle's final landing (ICX-HIST.8): its chapter's URL, unless the URL already names it (distance 0)
    if (p.reentry && urlFor(p.slug) === here()) return;
    queued = { kind: "replace", slug: p.slug };
    quietTimer = setTimeout(flush, QUIET);
  });
  function flushOrDrop() { queued = null; clearTimeout(quietTimer); }   // Back arrived: the entry being left is not rewritten
  // (INT5-fix 1; Sol + Astra INT-5) a mode change (Classic on / off, a rotation across a layout line) rebuilds the story:
  // a pinned jump still in flight never lands, and a native jump's arrival would be written wherever the rebuild left the
  // page. Both are void, as in RACE's native-jump cancel: left set, the next ordinary step would push (ICX-HIST.1). A
  // landing still queued is a real one: written first.
  if (typeof F.onModeChange === "function") F.onModeChange(function () {
    flush(); pending = null; departY0 = null;
    if (cancelArrival) { cancelArrival(); cancelArrival = null; }
    jumping = false;
  });
  // RELOAD: leaving the page (a reload, another page, a hidden tab) records the current entry's place in HELD (no history
  // write). Not while the load's own scroll, a Back or a native jump is still settling: the record keeps what it had.
  function holdPlace() {
    if (initializing || restoring || jumping) return;
    var slug = urlSlug();
    try {
      if (!slug || !holdsPlace(slug)) { sessionStorage.removeItem(HELD); return; }
      sessionStorage.setItem(HELD, JSON.stringify({ path: location.pathname, story: slug, k: entryKey(),
        y: Math.round(window.scrollY), w: window.innerWidth, m: F.mode }));
    } catch (e) { /* storage off: the state's own y (or the anchor) */ }
  }
  function leave() { flush(); holdPlace(); }
  document.addEventListener("visibilitychange", function () { if (document.hidden) leave(); });
  window.addEventListener("pagehide", leave);

  /* ---- scroll settling: scrollend, or SETTLE_IDLE (160 ms with no scroll event) where scrollend is missing ---- */
  // settled(cb): cb once the page's scroll has settled (once, 2.5 s backstop); returns a cancel function
  function settled(cb) {
    var idle = 0, backstop = 0, done = false;
    function stop() {
      clearTimeout(idle); clearTimeout(backstop);
      window.removeEventListener("scroll", bump);
      window.removeEventListener("scrollend", fin);
    }
    function fin() { if (done) return; done = true; stop(); cb(); }
    function bump() { clearTimeout(idle); idle = setTimeout(fin, 160); }
    window.addEventListener("scroll", bump, { passive: true });
    window.addEventListener("scrollend", fin);
    backstop = setTimeout(fin, 2500);
    bump();
    return function () { done = true; stop(); };
  }

  // ICX-HIST.9's suppression flags (all this file's own): the scroll-spy (fe:spy) writes nothing while one is set
  var initializing = true;  // load, reload, deep link, legacy hash: until the scroll that load causes has settled
  var restoring = false;    // popstate: until the scroll it causes has settled
  var jumping = false;      // a native jump (ICX-JUMP.5): until its arrival, where the jump writes its own entry
  var cancelArrival = null, cancelRestore = null;
  (function waitInit(n) {
    var ready = document.readyState === "complete" && (F.initial || ["calm", "classic", "static"].indexOf(F.mode) >= 0 || n > 30);
    if (ready) { restoreHeld(); settled(function () { initializing = false; }); }
    else setTimeout(function () { waitInit(n + 1); }, 100);
  })(0);

  // RELOAD in calm / classic / static: the browser's own restoration ("auto") normally has the pixel already; where a
  // fragment scroll won over it, the held place is put back (instant, during `initializing`, so the spy writes nothing).
  // The story modes restore in site.js's init, before the engine's first frame.
  function restoreHeld() {
    if (siteRestoration() !== "auto") return;
    var slug = urlSlug(), y = slug ? heldY(slug) : null;
    if (y != null && Math.abs(window.scrollY - y) > 1) window.scrollTo({ top: y, left: 0, behavior: "instant" });
  }

  // a native scroll's arrival (calm, classic, tablet Price...): write once it has settled
  function afterScroll(fn) {
    if (cancelArrival) cancelArrival();
    jumping = true;
    cancelArrival = settled(function () { jumping = false; cancelArrival = null; fn(); });
  }

  // go to a chapter on behalf of a link: kind "push" (an explicit jump) or "hash" (the browser already added the entry)
  function jumpTo(slug, kind) {
    var row = rowOf(slug);
    if (!row) return false;
    if (row.kind === "pinned") {
      var idx = -1, all = rows();
      for (var i = 0; i < all.length; i++) if (all[i].slug === slug) idx = i;
      var before = F.state ? F.state() : null;
      var there = !!before && before.rendered === idx && before.dest === idx;     // ICX-JUMP.0: nothing will move
      intent = kind;
      var ok;
      departY0 = window.scrollY;                    // before goTo: from below the pin the engine moves the page at once
      try { ok = F.goTo(slug, { source: "jump" }); } finally { intent = null; }
      if (!ok) departY0 = null;
      if (ok) { if (cancelArrival) { cancelArrival(); cancelArrival = null; } jumping = false; }   // a same-chapter jump has no dest event
      // a run already heading for this chapter (a step in flight) has no new dest event: the explicit jump still owns it
      if (kind === "push" && ok && before && before.dest === idx && before.rendered !== idx) raise("push");
      if (kind === "hash" && ok) {
        // the link supersedes a jump still under way: the browser's own entry is the one for this run (no second push)
        if (there) { unqueue(); pending = null; write("replace", slug); }   // a legacy or odd hash still gets its slug
        else pending = "hash";
      }
      return ok;
    }
    var y0 = window.scrollY;                         // where the reader left from: Back in calm / classic returns here
    // the latest explicit jump wins (RACE; Sol RACE-1): a pinned move this native jump cancels never lands, so its pending
    // write kind is void here (left set, the next ordinary step would push); a landing still queued is the entry being left
    flush(); pending = null;
    var ok2 = F.goTo(slug, { source: "jump" });
    if (ok2) afterScroll(function () { write(kind === "push" ? "push" : "replace", slug, y0); });
    return ok2;
  }

  /* ---- a fragment navigation (a same-page link, location.hash = ...) also fires popstate; it is a jump, not a traversal ---- */
  var linkNav = false, linkTimer = 0;
  function markLink() { flush(); linkNav = true;  // a landing still queued belongs to the entry being left: write it first
    clearTimeout(linkTimer); linkTimer = setTimeout(function () { linkNav = false; }, 200); }
  if (window.navigation && typeof window.navigation.addEventListener === "function") {
    window.navigation.addEventListener("navigate", function (e) {
      if (e.navigationType === "push" && e.hashChange) markLink();
    });
  }
  // a plain left click on a same-page link whose hash names a chapter or a legacy alias (#download, #how...) is a jump to that
  // chapter, even when the hash already equals it (no hashchange then): the hidden footer link, the phone's header link
  window.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
    if (!a || (a.target && a.target !== "_self") || a.hasAttribute("download")) return;
    var u;
    try { u = new URL(a.href, location.href); } catch (err) { return; }
    if (u.origin !== location.origin || u.pathname !== location.pathname || u.search !== location.search || !u.hash) return;
    var key; try { key = decodeURIComponent(u.hash.slice(1)); } catch (err2) { return; }
    var slug = slugOf(key);
    if (slug) { flush(); e.preventDefault(); jumpTo(slug, "push"); return; }
    if (u.hash !== location.hash) markLink();          // another fragment (#dark, an id): the browser's own navigation
  });

  /* ---- popstate: the same visuals as a jump, never a write (ICX-JUMP.4, ICX-HIST.3) ---- */
  var popHref = null, popTimer = 0;
  window.addEventListener("popstate", function () {
    if (linkNav) return;                            // a fragment navigation: hashchange handles it
    popHref = location.href;
    clearTimeout(popTimer);
    popTimer = setTimeout(function () { popHref = null; }, 100);
    var key = hashKey();
    var slug = key === "" || key === "dark" || key === "light" ? FIRST : slugOf(key);
    flushOrDrop();
    pending = "pop";                                // whatever was under way is now Back's: no write for it (ICX-HIST.3)
    if (cancelArrival) { cancelArrival(); cancelArrival = null; }   // a native arrival write in flight is void
    jumping = false;
    restoring = true;
    // (SCRUB-fix 1; Astra RELEASE-1 HIGH) Back onto a row that is not pinned (Price, A note, an unknown hash) has no
    // landing to consume its `pop`: it ends with the popstate's own arrival, so a later jump's push is never silenced
    var popRow = slug ? rowOf(slug) : null, popPinned = !!(popRow && popRow.kind === "pinned");
    if (cancelRestore) cancelRestore();
    cancelRestore = settled(function () {
      restoring = false; cancelRestore = null; setRestoration(siteRestoration());
      if (!popPinned && pending === "pop") pending = null;
    });
    departY0 = null;
    if (!slug) return;
    var st = history.state, row = rowOf(slug);
    // a native mode: the exact pixel the reader left; in the story modes the same for a NATIVE row, when the entry's place
    // was kept for this chapter in this mode at this width (pinned rows keep ICX-JUMP.4: goTo below)
    var heldNative = !!(row && row.kind === "native" && st && st.story === slug && typeof st.y === "number" &&
      st.w === window.innerWidth && st.m === F.mode);
    if (heldNative && siteRestoration() !== "auto") {   // the story modes: the engine's own native scroll, to that pixel
      intent = "pop";
      try { F.goTo(slug, { source: "popstate", y: st.y }); } finally { intent = null; }
      return;
    }
    // (INT5-fix 2) only a place recorded for this chapter in this mode at this width (as RELOAD's reload path): an entry
    // written in the story modes, or at another width, lands on the chapter's anchor (goTo below)
    if (st && typeof st.y === "number" && siteRestoration() === "auto" && st.story === slug && st.m === F.mode &&
        st.w === window.innerWidth) {
      window.scrollTo({ top: st.y, left: 0, behavior: "instant" });
      return;
    }
    intent = "pop";
    try { F.goTo(slug, { source: "popstate" }); } finally { intent = null; }
  });

  /* ---- hashchange: a same-page #how / #download / #price link (ICX-HIST.6) ---- */
  window.addEventListener("hashchange", function () {
    linkNav = false;
    if (popHref && location.href === popHref) { popHref = null; return; }   // the popstate above already handled it
    var slug = slugOf(hashKey());
    if (!slug) return;                              // #dark / #light / an unknown hash: not a chapter
    jumpTo(slug, "hash");
  });

  /* ---- scroll-spy history (ICX-HIST.9): the nav module dispatches fe:spy; this file owns the write ---- */
  document.addEventListener("fe:spy", function (e) {
    var d = e && e.detail;
    if (!d || !d.slug || d.user === false || !rowOf(d.slug)) return;
    if (initializing || restoring || jumping) return;
    if (urlFor(d.slug) === here()) return;          // already this URL: the spy's echo after a jump / a Back writes nothing
    write("replace", d.slug);
  });

  /* ---- the explicit-jump entry point: rail, menu, logo (ICX-JUMP, ICX-HIST.2): one push at the landing / the arrival ---- */
  window.FEStoryURL = Object.freeze({
    jump: function (target) { var slug = slugOf(String(target)); return slug ? jumpTo(slug, "push") : false; },
  });

  /* ---- the logo on "/" is a jump to the first chapter (B4 judge LOW) ---- */
  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target && e.target.closest ? e.target.closest("a.brand") : null;
    if (!a || (a.target && a.target !== "_self") || a.hasAttribute("download")) return;
    var u;
    try { u = new URL(a.href, location.href); } catch (err) { return; }
    var home = function (p) { return p === "/" || p === "/index.html"; };
    if (u.origin !== location.origin || !home(u.pathname) || !home(location.pathname) || u.hash) return;
    if (!rowOf(FIRST)) return;
    e.preventDefault();
    jumpTo(FIRST, "push");
  });
})();
