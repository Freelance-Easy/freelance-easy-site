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
    // Each .cta-row contains [data-platform="win"] (real download) and
    // [data-platform="mac"] (a disabled "Coming soon" button — Mac build is
    // paused, 4-7 weeks). Mac users still see Windows as the primary CTA;
    // we just keep Mac visible so they know support is coming.
    var os = detectPlatform();
    document.querySelectorAll(".cta-row").forEach(function (row) {
      var win = row.querySelector('[data-platform="win"]');
      var mac = row.querySelector('[data-platform="mac"]');
      if (!win) return;

      // Windows is always the active primary while Mac is paused.
      win.classList.remove("btn-secondary");
      win.classList.add("btn-primary");
      if (win !== row.firstElementChild) {
        row.insertBefore(win, row.firstElementChild);
      }

      // On Mac, surface the Mac "coming soon" button right after Windows
      // so the user immediately sees their platform is acknowledged.
      if (os === "mac" && mac) {
        if (mac.previousElementSibling !== win) {
          row.insertBefore(mac, win.nextSibling);
        }
      }
    });

    // Set body data attr so CSS / future copy can react if needed.
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
