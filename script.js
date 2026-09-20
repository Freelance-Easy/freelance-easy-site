/* Freelance Easy — landing page behaviour (v2.1, 2026-09)
   1. Theme toggle (dark default, persisted in localStorage).
   2. Platform detection — mac / win / mobile / other. Each download block
      ([data-dl]) gets one filled button for the visitor's OS and a plain link
      for the other; the matching compatibility text is shown. Phones get a
      share / copy-link handoff instead of installers.
   3. Campaign download paths — buttons link to /dl/<os>/<campaign>; the
      campaign id comes from ?utm_campaign (letters, digits, dashes) or the
      page's default. `_redirects` resolves the path to the GitHub asset.
   4. Analytics events (Plausible, cookieless, proxied through this domain):
      "Download Click", "Compatibility Help Opened", "Share To Computer".
      No personal data — which button, on which page, from which campaign.
   The no-JS state is the plain /download/<os> href already in the HTML. */

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

  // ---- Analytics (no-op until the script is configured) ----
  function track(name, props) {
    try {
      if (typeof window.plausible === "function") window.plausible(name, { props: props || {} });
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

  var ICONS = {
    mac: '<path d="M11.18 8.43c-.02-2.04 1.66-3.02 1.74-3.07-.95-1.39-2.43-1.58-2.95-1.6-1.26-.13-2.45.74-3.09.74-.65 0-1.63-.72-2.68-.7-1.38.02-2.65.8-3.36 2.04C-.6 8.4.43 12 1.85 13.97c.7.97 1.52 2.06 2.6 2.02 1.05-.04 1.45-.68 2.72-.68 1.27 0 1.62.68 2.73.66 1.13-.02 1.84-.99 2.53-1.97.8-1.13 1.13-2.23 1.15-2.29-.03-.01-2.2-.84-2.22-3.32-.02-2.07 1.69-3.07 1.77-3.12-.97-1.42-2.47-1.58-2.99-1.62zM9.27 2.42c.57-.7.96-1.66.85-2.62-.83.04-1.83.55-2.42 1.24-.53.62-1 1.6-.87 2.54.93.07 1.87-.46 2.44-1.16z"/>',
    win: '<path d="M0 2.4 6.5 1.5v6H0V2.4zM7.4 1.4 16 0v7.5H7.4V1.4zM0 8.5h6.5v6L0 13.6V8.5zM7.4 8.5H16V16l-8.6-1.4V8.5z"/>',
  };
  var NAMES = { mac: "Mac", win: "Windows" };

  // ---- Download blocks ----
  function wireDownloadBlock(block, os, campaign) {
    var placement = block.getAttribute("data-placement") || "";
    var primary = block.querySelector('[data-role="primary"]');
    var alt = block.querySelector('[data-role="alt"]');
    if (!primary || !alt) return;

    // The visitor's OS gets the filled button; the other becomes the plain link.
    // Mac stays primary for unknown desktops (the majority audience) — the link
    // for the other platform is always one click away.
    var primOs = os === "win" ? "win" : "mac";
    var altOs = primOs === "mac" ? "win" : "mac";
    var single = block.hasAttribute("data-single-platform"); // campaign pages: one platform only

    function setLink(a, targetOs, isPrimary) {
      a.setAttribute("data-platform", targetOs);
      a.setAttribute("href", "/dl/" + targetOs + "/" + campaign);
      var label = a.querySelector("[data-label]");
      if (label) label.textContent = isPrimary ? "Download for " + NAMES[targetOs] : NAMES[targetOs] + " download";
      var icon = a.querySelector("[data-icon]");
      if (icon) {
        icon.innerHTML = ICONS[targetOs];
        icon.setAttribute("data-icon", targetOs);
      }
    }
    setLink(primary, primOs, true);
    if (!single) setLink(alt, altOs, false);

    block.querySelectorAll("[data-support]").forEach(function (el) {
      el.hidden = el.getAttribute("data-support") !== primOs;
    });

    [primary, alt].forEach(function (a) {
      a.addEventListener("click", function () {
        track("Download Click", {
          os: a.getAttribute("data-platform"),
          campaign: campaign,
          page: pageId(),
          placement: placement,
        });
      });
    });

    block.querySelectorAll("[data-compat-help]").forEach(function (d) {
      d.addEventListener("toggle", function () {
        if (d.open) track("Compatibility Help Opened", { page: pageId(), placement: placement });
      });
    });

    // Phones: share or copy the page link; never a silent button.
    var shareBtn = block.querySelector("[data-share]");
    var status = block.querySelector("[data-share-status]");
    if (shareBtn) {
      var canShare = typeof navigator.share === "function";
      var label = shareBtn.querySelector("[data-label]");
      if (label) label.textContent = canShare ? "Share this page" : "Copy page link";
      shareBtn.addEventListener("click", function () {
        var url = location.origin + location.pathname;
        var done = function (how) {
          track("Share To Computer", { page: pageId(), placement: placement, how: how });
        };
        if (canShare) {
          navigator
            .share({ title: "Freelance Easy", text: "Invoicing app for freelancers — open this on your computer:", url: url })
            .then(function () { done("share"); })
            .catch(function () {});
          return;
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(url).then(
            function () {
              if (status) status.textContent = "Link copied. Open it on your computer to download the app.";
              done("copy");
            },
            function () {
              if (status) status.textContent = "Couldn't copy the link — it's " + url;
            }
          );
        } else if (status) {
          status.textContent = "Copy this address on your computer: " + url;
        }
      });
    }
  }

  function init() {
    bindToggle();
    var os = detectPlatform();
    document.body.setAttribute("data-os", os);
    var campaign = campaignId();
    document.body.setAttribute("data-campaign-resolved", campaign);
    document.querySelectorAll("[data-dl]").forEach(function (block) {
      wireDownloadBlock(block, os, campaign);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
