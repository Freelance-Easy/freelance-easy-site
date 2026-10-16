/* story-url.js (C4): the homepage story's URL + history, per docs/interaction-contract.md (ICX-HIST.1-.9, ICX-JUMP).
   The one owner of every history write the story makes. It listens to window.FEStory (assets/story/site.js, which writes
   none) and does nothing where FEStory is absent (this tag lives in the shared head partial, `defer`).

   - A step run or a FREE settle -> one replaceState at its FINAL landing (rendered == dest); passed-through landings write
     nothing (ICX-HIST.1/.8).
   - An explicit jump (rail, menu, Home/End, logo, caption focus) -> one pushState at its final landing; gestures that extend
     the run keep that one push (ICX-HIST.2).
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
  function stateFor(slug) {
    var s = history.state, o = {};
    if (s && typeof s === "object") for (var k in s) if (Object.prototype.hasOwnProperty.call(s, k)) o[k] = s[k];
    o.story = slug;
    return o;
  }
  function write(kind, slug) {
    var url = urlFor(slug);
    try {
      if (kind === "push") { if (url !== here()) history.pushState(stateFor(slug), "", url); }
      else history.replaceState(stateFor(slug), "", url);
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

  F.onDest(function (p) {
    if (!p || p.preview || p.source === "free") return;
    unqueue();
    if (p.source === "popstate") raise("pop");
    else if (p.source === "jump") raise(intent === "hash" ? "hash" : "push");
    else raise("replace");                         // step, settle
  });

  F.onLand(function (p) {
    if (!p || !p.final) return;                    // a pass-through landing writes nothing (ICX-HIST.1)
    unqueue();
    var kind = pending;
    pending = null;
    if (p.source === "init") return;               // load, reload, deep link: never a write (ICX-HIST.3)
    if (kind == null) kind = p.source === "jump" ? "push" : p.source === "popstate" ? "pop" : "replace";
    if (kind === "pop") return;
    if (kind === "push") { write("push", p.slug); return; }   // at the landing itself: Back must find the entry
    queued = { kind: "replace", slug: p.slug };
    quietTimer = setTimeout(flush, QUIET);
  });
  function flushOrDrop() { queued = null; clearTimeout(quietTimer); }   // Back arrived: the entry being left is not rewritten
  document.addEventListener("visibilitychange", function () { if (document.hidden) flush(); });
  window.addEventListener("pagehide", flush);

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
    if (ready) settled(function () { initializing = false; });
    else setTimeout(function () { waitInit(n + 1); }, 100);
  })(0);

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
      try { ok = F.goTo(slug, { source: "jump" }); } finally { intent = null; }
      if (kind === "hash" && ok) {
        // the link supersedes a jump still under way: the browser's own entry is the one for this run (no second push)
        if (there) { unqueue(); pending = null; write("replace", slug); }   // a legacy or odd hash still gets its slug
        else pending = "hash";
      }
      return ok;
    }
    var ok2 = F.goTo(slug, { source: "jump" });
    if (ok2) afterScroll(function () { write(kind === "push" ? "push" : "replace", slug); });
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
    if (cancelRestore) cancelRestore();
    cancelRestore = settled(function () { restoring = false; cancelRestore = null; });
    if (!slug) return;
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
