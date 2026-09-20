/* Freelance Easy — landing page interactions (v2, 2026-09)
   1. Theme toggle (dark default, persisted in localStorage).
   2. Platform detection — mac / win / mobile / other. Re-orders the download
      buttons so the visitor's OS is the primary CTA, shows the Windows
      SmartScreen note only to Windows visitors, and swaps the primary CTA to
      "Send this page to my computer" on phones.
   3. Campaign download paths — buttons link to /dl/<os>/<campaign>; the
      campaign id comes from ?utm_campaign (letters, digits, dashes only) or the
      page's default. `_redirects` resolves the path to the GitHub asset.
   4. Analytics events (Plausible, cookieless, proxied through this domain):
      "Download Click", "Intel Notify", "Share To Computer". No personal data,
      no identifiers — just which button on which page.
   The no-JS fallback is the plain /download/<os> href already in the HTML. */

(function () {
  // ---- Theme ----
  var STORAGE_KEY = "fe-theme";
  var root = document.documentElement;

  function applyTheme(t) {
    if (t === "light") root.setAttribute("data-theme", "light");
    else root.removeAttribute("data-theme");
  }

  var stored = null;
  try {
    stored = localStorage.getItem(STORAGE_KEY);
  } catch (e) {}
  applyTheme(stored === "light" ? "light" : "dark");

  function bindToggle() {
    var btn = document.querySelector("[data-theme-toggle]");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      applyTheme(next);
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (e) {}
    });
  }

  // ---- Analytics (safe no-op when the script is not configured) ----
  function track(name, props) {
    try {
      if (typeof window.plausible === "function") {
        window.plausible(name, { props: props || {} });
      }
    } catch (e) {}
  }

  // ---- Platform detection ----
  function detectPlatform() {
    var ua = (navigator.userAgent || "").toLowerCase();
    var p = (navigator.platform || "").toLowerCase();
    var touch = navigator.maxTouchPoints > 1;
    if (/iphone|ipod|android.*mobile|windows phone/.test(ua)) return "mobile";
    if (/ipad/.test(ua) || (/mac/.test(p) && touch)) return "mobile"; // iPadOS reports as Mac
    if (/mac/.test(p) || /mac os x|macintosh/.test(ua)) return "mac";
    if (/win/.test(p) || /windows/.test(ua)) return "win";
    if (/android/.test(ua)) return "mobile";
    return "other";
  }

  // ---- Campaign id → /dl/<os>/<campaign> ----
  function campaignId() {
    var fromQuery = null;
    try {
      fromQuery = new URLSearchParams(location.search).get("utm_campaign");
    } catch (e) {}
    var raw = fromQuery || document.body.getAttribute("data-campaign") || "site";
    var clean = String(raw).toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40);
    return clean || "site";
  }

  function pageId() {
    return document.body.getAttribute("data-page") || "home";
  }

  function wireDownloadLinks(campaign) {
    document.querySelectorAll("a[data-platform]").forEach(function (a) {
      var os = a.getAttribute("data-platform");
      if (os !== "mac" && os !== "win") return;
      a.setAttribute("href", "/dl/" + os + "/" + campaign);
      a.addEventListener("click", function () {
        track("Download Click", { os: os, campaign: campaign, page: pageId() });
      });
    });
  }

  // ---- CTA ordering ----
  function reorderCtas(os) {
    document.querySelectorAll(".cta-row").forEach(function (row) {
      var win = row.querySelector('[data-platform="win"]');
      var mac = row.querySelector('[data-platform="mac"]');
      if (!win || !mac) return; // single-platform rows (the Mac campaign page) stay as authored

      var primary = os === "win" ? win : mac; // Mac is the default primary (majority audience)
      var secondary = primary === win ? mac : win;

      primary.classList.remove("btn-secondary");
      primary.classList.add("btn-primary");
      secondary.classList.remove("btn-primary");
      secondary.classList.add("btn-secondary");

      if (primary !== row.firstElementChild) row.insertBefore(primary, row.firstElementChild);
      if (secondary.previousElementSibling !== primary) row.insertBefore(secondary, primary.nextSibling);
    });
  }

  // ---- Intel Macs: no download, one honest sentence ----
  function bindIntel() {
    document.querySelectorAll("[data-intel]").forEach(function (link) {
      link.addEventListener("click", function (ev) {
        ev.preventDefault();
        document.querySelectorAll("[data-intel-note]").forEach(function (n) {
          n.hidden = false;
        });
        link.setAttribute("aria-expanded", "true");
        track("Intel Notify", { page: pageId() });
      });
    });
  }

  // ---- Phones: send the page to a computer ----
  function bindShare() {
    document.querySelectorAll("[data-share]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var url = location.origin + location.pathname;
        var done = function (how) {
          track("Share To Computer", { page: pageId(), how: how });
        };
        if (navigator.share) {
          navigator
            .share({ title: "Freelance Easy", text: "Invoicing app for freelancers — open this on your computer:", url: url })
            .then(function () { done("share"); })
            .catch(function () {});
          return;
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(url).then(function () {
            var note = btn.querySelector(".label .bot");
            if (note) note.textContent = "Link copied — paste it on your computer";
            done("copy");
          });
        }
      });
    });
  }

  function init() {
    bindToggle();
    var os = detectPlatform();
    document.body.setAttribute("data-os", os);
    var campaign = campaignId();
    document.body.setAttribute("data-campaign-resolved", campaign);
    wireDownloadLinks(campaign);
    reorderCtas(os);
    bindIntel();
    bindShare();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
