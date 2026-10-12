/* Ported from React Bits BorderGlow (reactbits.dev), MIT + Commons Clause. */
/* FINAL (P2, 2026-10-12; from B2's bg-price). Vanilla port of BorderGlow's edge light (see border-glow.css).
   A host is [data-fx="border-glow"] (the index price card's wrapper).
   - Pointer: only under (hover: hover) and (pointer: fine) and never under reduced motion. Events are delegated from the
     host's [data-dl] block (or the host itself); pointermove only stores coordinates, and one rAF per frame at most
     reads one getBoundingClientRect() and writes --edge-proximity and --cursor-angle on the host (React Bits' math).
     No scroll listeners, no rAF while the pointer is still; listeners are removed while the block is off screen.
   - B2's one-time sweep (?opt=sweep) and button hosts were not picked and are not in this file. */
(function () {
  "use strict";
  if (!window.matchMedia || !document.querySelectorAll) return;

  var mqPointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  var mqReduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  var PROPS = "--edge-proximity,--cursor-angle";

  function tracking() {
    return mqPointer.matches && !mqReduce.matches;
  }

  /* ---------- hosts ---------- */
  function tagHost(el) {
    el.classList.add("fx-glow", "fx-glow--card");
    el.setAttribute("data-fx", "border-glow");
    el.setAttribute("data-fx-props", PROPS);
  }
  function addEdge(host) {
    for (var c = host.lastElementChild; c; c = c.previousElementSibling) if (c.classList.contains("fx-glow-edge")) return;
    var s = document.createElement("span");
    s.className = "fx-glow-edge";
    s.setAttribute("aria-hidden", "true");
    host.appendChild(s);                                   // last child: download.js only rewrites [data-label]/[data-icon]
  }

  /* ---------- React Bits' edge proximity (0-100) and cursor angle ---------- */
  function measure(host, x, y) {
    var r = host.getBoundingClientRect();
    var cx = r.width / 2, cy = r.height / 2;
    var dx = x - r.left - cx, dy = y - r.top - cy;
    var kx = dx !== 0 ? cx / Math.abs(dx) : Infinity;
    var ky = dy !== 0 ? cy / Math.abs(dy) : Infinity;
    var edge = Math.min(Math.max(1 / Math.min(kx, ky), 0), 1);
    var deg = 0;
    if (dx !== 0 || dy !== 0) {
      deg = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
      if (deg < 0) deg += 360;
    }
    host.style.setProperty("--edge-proximity", (edge * 100).toFixed(3));
    host.style.setProperty("--cursor-angle", deg.toFixed(3) + "deg");
  }

  /* ---------- pointer tracking, delegated per block ---------- */
  var pend = null, raf = 0;
  function frame() {
    raf = 0;
    var p = pend;
    pend = null;
    if (!p || !p.host._fxIn || !tracking()) return;
    measure(p.host, p.x, p.y);
    p.host.classList.add("is-glow");
  }
  function queue(host, x, y) {
    pend = { host: host, x: x, y: y };
    if (!raf) raf = requestAnimationFrame(frame);
  }
  function hostOf(scope, t) {
    var h = t && t.closest ? t.closest('.fx-glow[data-fx="border-glow"]') : null;
    return h && scope.contains(h) ? h : null;
  }
  function onOver(e) {
    if (e.pointerType === "touch" || !tracking()) return;
    var h = hostOf(this, e.target);
    if (!h || (e.relatedTarget && h.contains(e.relatedTarget))) return;
    h._fxIn = true;
    queue(h, e.clientX, e.clientY);
  }
  function onMove(e) {
    if (e.pointerType === "touch" || !tracking()) return;
    var h = hostOf(this, e.target);
    if (h && h._fxIn) queue(h, e.clientX, e.clientY);
  }
  function onOut(e) {
    var h = hostOf(this, e.target);
    if (!h || (e.relatedTarget && h.contains(e.relatedTarget))) return;
    h._fxIn = false;
    h.classList.remove("is-glow");                         // the CSS fades it out (0.6 s), then hides it
  }

  var scopes = [];
  function bind(scope, on) {
    if (scope._fxBound === on) return;
    scope._fxBound = on;
    var m = on ? "addEventListener" : "removeEventListener";
    scope[m]("pointerover", onOver);
    scope[m]("pointermove", onMove, { passive: true });
    scope[m]("pointerout", onOut);
    if (!on) {
      var hs = scope.querySelectorAll(".fx-glow.is-glow");
      for (var i = 0; i < hs.length; i++) { hs[i]._fxIn = false; hs[i].classList.remove("is-glow"); }
      if (scope.matches(".fx-glow.is-glow")) { scope._fxIn = false; scope.classList.remove("is-glow"); }
    }
  }
  function syncAll() {
    for (var i = 0; i < scopes.length; i++) bind(scopes[i], !!scopes[i]._fxVis && tracking());
  }

  /* ---------- init ---------- */
  function init() {
    var hosts = document.querySelectorAll('[data-fx="border-glow"]');
    if (!hosts.length) return;
    var io = window.IntersectionObserver ? new IntersectionObserver(function (es) {
      for (var k = 0; k < es.length; k++) es[k].target._fxVis = es[k].isIntersecting;
      syncAll();
    }) : null;
    for (var h = 0; h < hosts.length; h++) {
      var host = hosts[h];
      if (!host.classList.contains("fx-glow")) tagHost(host);
      addEdge(host);
      var scope = host.closest("[data-dl]") || host;
      if (scopes.indexOf(scope) < 0) {
        scopes.push(scope);
        if (io) io.observe(scope); else scope._fxVis = true;
      }
    }
    syncAll();
    function onMq() { syncAll(); }
    if (mqPointer.addEventListener) { mqPointer.addEventListener("change", onMq); mqReduce.addEventListener("change", onMq); }
    else if (mqPointer.addListener) { mqPointer.addListener(onMq); mqReduce.addListener(onMq); }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
