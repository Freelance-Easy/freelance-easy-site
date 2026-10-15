/* FETheme: the one theme switch for every page (A5, 2026-10-14).
   - data-theme on <html> is always "dark" or "light", never removed (styles.css keys light off [data-theme="light"]
     and dark off :root, so an explicit "dark" is safe there and in site.css).
   - The choice is remembered in localStorage "fe-theme" (shared by every page).
   - A switch from a control reveals the new theme through one soft-edged circle from the control's centre, with the
     app's numbers: 420 ms, cubic-bezier(.55,0,.25,1), a feather of 22% of the radius clamped to 48-220 px
     (theme.css holds the mask, this file the timing). Instant under prefers-reduced-motion or without
     document.startViewTransition.
   - "fe:themechange" ({detail:{theme}}) fires on document (it bubbles to window) only when the theme changes, inside
     the view-transition update, so a listener that repaints synchronously lands in the new snapshot.
   - Hash policy per page: "home" reads #dark / #light (on init and on hashchange) and never writes; "tour" reads the
     light/dark flag among & or , separated flags and, on a switch, rewrites only that flag (#light&reduced&email ->
     #dark&reduced&email; no flag, no write); "none" neither reads nor writes.
   API: FETheme.init({hashPolicy, toggle}), FETheme.set(theme, {from: el}), FETheme.get(). */
(function (w, d) {
  "use strict";
  if (w.FETheme) return;
  var KEY = "fe-theme";
  var DURATION = 420;
  var EASING = "cubic-bezier(.55,0,.25,1)";
  var FLAG = /(^|[&,])(light|dark)(?=[&,]|$)/g;
  var root = d.documentElement;
  var policy = "none";
  var started = false;
  var running = null;   // the reveal in flight, if any
  var want = null;      // the latest theme asked for (a toggle press mid-reveal flips from this, not the DOM)
  var seq = 0;          // bumped by every switch; a view-transition update callback applies only if still the latest

  function valid(t) { return t === "dark" || t === "light"; }
  function get() { return root.getAttribute("data-theme") === "light" ? "light" : "dark"; }

  function hashTheme() {
    var h = location.hash.slice(1);
    if (policy === "home") return valid(h) ? h : null;
    if (policy === "tour") {
      var f = h.split(/[&,]/);
      for (var i = f.length - 1; i >= 0; i--) if (valid(f[i])) return f[i];
    }
    return null;
  }
  function writeHash(t) {
    if (policy !== "tour") return;
    var h = location.hash.slice(1);
    var next = h.replace(FLAG, function (m, sep) { return sep + t; });
    if (next === h) return;       // no light/dark flag (nothing to keep in step) or already this theme
    try { history.replaceState(history.state, "", "#" + next); } catch (e) { /* file:// may refuse */ }
  }
  function remember(t) {
    try { w.localStorage.setItem(KEY, t); } catch (e) { /* storage blocked: this visit still flips */ }
  }

  // the only writer of data-theme: always an explicit "dark" or "light". The event fires only on a visible change
  // (a missing or odd data-theme already shows dark, so making it an explicit "dark" is not one).
  function apply(t) {
    var changed = get() !== t;
    root.setAttribute("data-theme", t);
    if (changed) d.dispatchEvent(new CustomEvent("fe:themechange", { bubbles: true, detail: { theme: t } }));
  }

  function canAnimate() {
    if (typeof d.startViewTransition !== "function") return false;
    try { return !w.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; }
  }

  function cleanup() {
    root.classList.remove("vt-theme");
    root.style.removeProperty("--vt-x");
    root.style.removeProperty("--vt-y");
  }

  function reveal(el, t) {
    var r = el.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
    var far = Math.hypot(Math.max(x, w.innerWidth - x), Math.max(y, w.innerHeight - y));
    // theme.css starts the feather at r - clamp(48px, 22% of r, 220px); the end radius puts that inner (fully opaque)
    // edge past the farthest corner, so the last frame before teardown is already the whole new theme (no snap)
    var end = Math.min(Math.max(far + 48, far / 0.78), far + 220) + 2;
    root.style.setProperty("--vt-x", x.toFixed(1) + "px");
    root.style.setProperty("--vt-y", y.toFixed(1) + "px");
    root.classList.add("vt-theme");
    var vt = null, mine = seq;
    try { vt = d.startViewTransition(function () { if (mine === seq) apply(t); }); } catch (e) { vt = null; }
    if (!vt) { cleanup(); apply(t); return; }
    running = vt;
    vt.ready.then(function () {
      vt.circle = root.animate({ "--vt-r": ["0px", end.toFixed(1) + "px"] },
        { duration: DURATION, easing: EASING, fill: "forwards", pseudoElement: "::view-transition-new(root)" });
    }).catch(function () { /* skipped or unsupported: the theme has still changed */ });
    vt.finished.catch(function () {}).then(function () {
      if (vt.circle) vt.circle.cancel();   // a finished fill-forwards animation would otherwise linger on <html>
      if (running === vt) { running = null; cleanup(); }
    });
  }

  function set(t, opts) {
    if (!valid(t)) return;
    var from = opts && opts.from;
    seq++;                        // any older reveal's update callback is now stale and will not apply
    want = t;
    remember(t);
    writeHash(t);
    if (running) {                 // a second switch mid-reveal: finish the first, then switch instantly
      var old = running;
      running = null;
      try { old.skipTransition(); } catch (e) { /* already finished */ }
      cleanup();
      apply(t);
      return;
    }
    if (root.getAttribute("data-theme") === t) return;
    if (from && typeof from.getBoundingClientRect === "function" && canAnimate()) { reveal(from, t); return; }
    apply(t);
  }

  function init(opts) {
    opts = opts || {};
    var p = opts.hashPolicy;
    policy = p === "home" || p === "tour" ? p : "none";
    apply(hashTheme() || get());   // makes a missing or odd data-theme explicit; a hash on load is not remembered
    if (started) return api;
    started = true;
    var sel = opts.toggle || "[data-theme-toggle]";
    d.addEventListener("click", function (e) {
      var b = e.target && e.target.closest ? e.target.closest(sel) : null;
      if (b) set((running ? want : get()) === "light" ? "dark" : "light", { from: b });
    });
    w.addEventListener("hashchange", function () {
      var h = hashTheme();
      if (h) set(h);
    });
    return api;
  }

  var api = { init: init, set: set, get: get };
  w.FETheme = api;
})(window, document);
