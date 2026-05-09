/* Freelance Easy — landing page interactions
   1. Theme toggle (dark default, persisted in localStorage)
   2. Platform detection — re-orders Windows/Mac download buttons so the
      user's OS is the primary CTA. The CTA labels and URLs are static in
      the HTML; we only swap their order. Falls back gracefully on Linux
      and unknowns ("See all downloads" remains visible). */

(function () {
  // ---- Theme ----
  var STORAGE_KEY = "fe-theme";
  var root = document.documentElement;

  function applyTheme(t) {
    if (t === "light") root.setAttribute("data-theme", "light");
    else root.removeAttribute("data-theme");
  }

  // Resolve initial theme: stored > system > dark default
  var stored = null;
  try {
    stored = localStorage.getItem(STORAGE_KEY);
  } catch (e) {}

  if (stored === "light" || stored === "dark") {
    applyTheme(stored);
  } else {
    applyTheme("dark");
  }

  function bindToggle() {
    var btn = document.querySelector("[data-theme-toggle]");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next =
        root.getAttribute("data-theme") === "light" ? "dark" : "light";
      applyTheme(next);
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (e) {}
    });
  }

  // ---- Platform detection ----
  function detectPlatform() {
    var ua = (navigator.userAgent || "").toLowerCase();
    var p = (navigator.platform || "").toLowerCase();
    if (/mac/.test(p) || /mac os x|macintosh/.test(ua)) return "mac";
    if (/win/.test(p) || /windows/.test(ua)) return "win";
    return "other";
  }

  function reorderCtas() {
    var os = detectPlatform();
    document.querySelectorAll(".cta-row").forEach(function (row) {
      var win = row.querySelector('[data-platform="win"]');
      var mac = row.querySelector('[data-platform="mac"]');
      if (!win || !mac) return;

      var primary = os === "mac" ? mac : win;
      var secondary = primary === win ? mac : win;

      primary.classList.remove("btn-secondary");
      primary.classList.add("btn-primary");
      secondary.classList.remove("btn-primary");
      secondary.classList.add("btn-secondary");

      if (primary !== row.firstElementChild) {
        row.insertBefore(primary, row.firstElementChild);
      }
      if (secondary.previousElementSibling !== primary) {
        row.insertBefore(secondary, primary.nextSibling);
      }
    });

    document.body.setAttribute("data-os", os);
  }

  // Run after DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      bindToggle();
      reorderCtas();
    });
  } else {
    bindToggle();
    reorderCtas();
  }
})();
