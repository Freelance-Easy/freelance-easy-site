/* Freelance Easy — the scroll-story homepage's download buttons (2026-10-08).
   The same behaviour as script.js on the other pages (which this page doesn't load: its theme toggle, demo loop and
   hero deck belong to the old homepage), kept in step with it by hand:
   - Platform: mac / win / mobile / other. Each download row ([data-dl]) gives the visitor's OS the filled button and
     the other OS the quiet link (Mac for an unknown desktop). html[data-os] picks the matching support line (site.css).
   - Links go to /dl/<os>/<campaign>; the campaign is ?utm_campaign only when it is on CAMPAIGNS, else the page's own
     label (body[data-campaign]). `_redirects` resolves the path to the GitHub asset. Without JS the HTML's plain
     /download/mac and /download/win stay.
   - Analytics (Plausible, cookieless, proxied through this domain; worker.js decides whether anything is sent): one
     event, "Download Click" {os, campaign, page, placement}. /privacy §3 lists it; nothing else is sent from here.
   - Phones and tablets: no installers. The filled button shares the page (or copies its link) and the note says
     there's no mobile app; the other OS's link is hidden.
   site.js moves each row's copy into the sticky story as it plays (the nodes move, they aren't cloned), so the
   listeners set here travel with them. */
(function () {
  "use strict";
  var root = document.documentElement;

  function track(name, props) {
    try {
      if (typeof window.plausible === "function") window.plausible(name, { props: props || {} });
    } catch (e) {}
  }

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

  // The ad flights' campaign labels (the same list as script.js). Add a flight's label to both before its ads run.
  var CAMPAIGNS = ["f1"];

  function campaignId() {
    var fromQuery = null;
    try {
      fromQuery = new URLSearchParams(location.search).get("utm_campaign");
    } catch (e) {}
    var wanted = String(fromQuery || "").toLowerCase();
    if (CAMPAIGNS.indexOf(wanted) >= 0) return wanted;
    var page = document.body.getAttribute("data-campaign") || "site";
    var clean = String(page).toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40);
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

  function share(statusEls) {
    var url = location.origin + location.pathname;
    function say(text) {
      statusEls.forEach(function (s) {
        s.textContent = text;
      });
    }
    function copyPageUrl() {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(
          function () {
            say("Link copied. Paste it into Notes or a message to yourself.");
          },
          function () {
            say("Couldn't copy the link. Copy this address: " + url);
          }
        );
      } else {
        say("Copy this address: " + url);
      }
    }
    if (typeof navigator.share === "function") {
      navigator
        .share({ title: "Freelance Easy", text: "Freelance Easy, an invoicing app for your computer.", url: url })
        .catch(function (err) {
          // Cancelling the share sheet is silent; a real failure falls back to the copy path.
          if (!err || err.name !== "AbortError") copyPageUrl();
        });
      return;
    }
    copyPageUrl();
  }

  function wire(block, os, campaign) {
    var placement = block.getAttribute("data-placement") || "";
    var primary = block.querySelector('[data-role="primary"]');
    var alt = block.querySelector('[data-role="alt"]');
    if (!primary || !alt) return;
    var statusEls = [].slice.call(document.querySelectorAll("[data-share-status]"));

    if (os === "mobile") {
      var label = primary.querySelector("[data-label]");
      if (label) label.textContent = typeof navigator.share === "function" ? "Share this page" : "Copy page link";
      var icon = primary.querySelector("[data-icon]");
      if (icon) icon.style.display = "none";
      primary.removeAttribute("href");
      primary.setAttribute("role", "button");
      primary.setAttribute("tabindex", "0");
      primary.addEventListener("click", function (e) {
        e.preventDefault();
        share(statusEls);
      });
      primary.addEventListener("keydown", function (e) {
        if (e.key === " " || e.key === "Spacebar") {
          e.preventDefault();
          share(statusEls);
        }
      });
      return;
    }

    var primOs = os === "win" ? "win" : "mac";
    var altOs = primOs === "mac" ? "win" : "mac";
    function setLink(a, targetOs) {
      a.setAttribute("data-platform", targetOs);
      a.setAttribute("href", "/dl/" + targetOs + "/" + campaign);
      var label = a.querySelector("[data-label]");
      if (label) label.textContent = "Download for " + NAMES[targetOs];
      var icon = a.querySelector("[data-icon]");
      if (icon) {
        icon.innerHTML = ICONS[targetOs];
        icon.setAttribute("data-icon", targetOs);
      }
    }
    setLink(primary, primOs);
    setLink(alt, altOs);
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
  }

  function init() {
    var os = detectPlatform();
    // site.css shows the matching support line from html[data-os] ("win", "mobile"; Mac's is the default)
    if (os === "win" || os === "mobile") root.setAttribute("data-os", os);
    else root.removeAttribute("data-os");
    document.body.setAttribute("data-os", os);
    var campaign = campaignId();
    document.body.setAttribute("data-campaign-resolved", campaign);
    document.querySelectorAll("[data-dl]").forEach(function (block) {
      wire(block, os, campaign);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
