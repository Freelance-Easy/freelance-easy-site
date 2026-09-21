/* Freelance Easy — landing page behaviour (v2.3, 2026-09)
   1. Theme toggle (dark default, persisted in localStorage). The product
      screenshots follow the theme in CSS (.shot-dark / .shot-light pairs).
      The making-an-invoice loop autoplays muted; see wireDemo for the
      reduced-motion and autoplay-refused fallbacks.
   2. Platform detection — mac / win / mobile / other. The download block
      ([data-dl]) gets one filled button for the visitor's OS and a plain link
      for the other; the matching compatibility text is shown. A block marked
      data-single-platform="mac" (the Mac campaign page) keeps its Mac button
      whatever the visitor runs. Phones get a share / copy-link handoff
      instead of installers.
   3. Campaign download paths — buttons link to /dl/<os>/<campaign>; the
      campaign id comes from ?utm_campaign (letters, digits, dashes) or the
      page's default. `_redirects` resolves the path to the GitHub asset.
   4. Analytics events (Plausible, cookieless, proxied through this domain):
      "Download Click", "Compatibility Help Opened", "Share To Computer".
      No personal data — which button, on which page, from which campaign.
   5. The hero stack's template picker (wireStack) and the header's scrolled
      hairline (wireHeader).
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
      syncDemoTheme(next).forEach(function (v) {
        if (!reduceMotion) playDemo(v);
      });
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
    // for the other platform is always one click away. A single-platform block
    // (the Mac campaign page) never changes its button; it only changes the
    // note, so a Windows visitor is told where the Windows download lives.
    var visitorOs = os === "win" ? "win" : "mac";
    var single = block.getAttribute("data-single-platform"); // "mac" on campaign pages, else null
    var primOs = single ? single : visitorOs;
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
    if (!single) setLink(alt, altOs);

    block.querySelectorAll("[data-support]").forEach(function (el) {
      el.hidden = el.getAttribute("data-support") !== visitorOs;
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
            .share({ title: "Freelance Easy", text: "Freelance Easy, an invoicing app for your computer.", url: url })
            .then(function () { done("share"); })
            .catch(function () {});
          return;
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(url).then(
            function () {
              if (status) status.textContent = "Link copied. Paste it into Notes or a message to yourself.";
              done("copy");
            },
            function () {
              if (status) status.textContent = "Couldn't copy the link. Copy this address: " + url;
            }
          );
        } else if (status) {
          status.textContent = "Copy this address: " + url;
        }
      });
    }
  }

  // ---- The loop (silent, autoplays like a GIF) ----
  // The recording exists in both app themes: …-dark.mp4 / …-light.mp4, the
  // same for the posters and the real-time files. The page's theme picks the
  // set (the HTML carries the dark one for no-JS).
  // Reduced motion: no autoplay; the poster stays and the controls appear, so
  // it plays only on request. Autoplay refused (iOS Low Power Mode, a strict
  // browser setting): same fallback, so the poster is never a dead end.
  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) {}

  function currentTheme() {
    return root.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function swapThemeIn(el, attr, theme) {
    var v = el.getAttribute(attr);
    if (!v) return false;
    var next = v.replace(/-(dark|light)(?=[-.])/, "-" + theme);
    if (next === v) return false;
    el.setAttribute(attr, next);
    return true;
  }

  function playDemo(v) {
    var p = v.play();
    if (p && typeof p.catch === "function") {
      p.catch(function (err) {
        if (!err || err.name !== "AbortError") v.controls = true;
      });
    }
  }

  // Point the loop (and the real-time link) at the theme's files; returns the
  // videos whose source changed, already reloaded.
  function syncDemoTheme(theme) {
    var changed = [];
    document.querySelectorAll("video[data-demo]").forEach(function (v) {
      var did = swapThemeIn(v, "poster", theme);
      v.querySelectorAll("source").forEach(function (s) {
        did = swapThemeIn(s, "src", theme) || did;
      });
      if (did) {
        v.load();
        changed.push(v);
      }
    });
    document.querySelectorAll("a[data-demo-realtime]").forEach(function (a) {
      swapThemeIn(a, "href", theme);
    });
    return changed;
  }

  function wireDemo() {
    syncDemoTheme(currentTheme());
    document.querySelectorAll("video[data-demo]").forEach(function (v) {
      if (reduceMotion) {
        v.removeAttribute("autoplay");
        v.pause();
        v.controls = true;
        return;
      }
      playDemo(v);
    });
  }

  // ---- The hero stack: bring a template to the front ----
  // One PNG per template in front (invoice-stack-<template>.png, all the same
  // size). Two image layers crossfade; the link under them opens the front
  // template's PDF. Without JS the caption's names are plain links to the PDFs.
  var TEMPLATES = ["modern", "bold", "classic", "minimal"];
  var TEMPLATE_NAMES = { modern: "Modern", bold: "Bold", classic: "Classic", minimal: "Minimal" };
  var STACK_ALT = {
    modern: "Four versions of the same invoice, stacked, the Modern template in front: a session-day invoice for Westbrook Sound with an engineer day rate and a kit fee totalling $750, with a teal rule and totals box; behind it the same invoice in the Bold, Classic and Minimal templates.",
    bold: "The same stack with the Bold template in front: a navy 'Invoice #INV1045' title over a black rule and a navy table header, the other three templates behind it.",
    classic: "The same stack with the Classic template in front: a forest-green bar across the top and the name and job in a serif, the other three templates behind it.",
    minimal: "The same stack with the Minimal template in front: a centred grey INVOICE title and hairline rules, the other three templates behind it.",
  };

  function wireStack() {
    var link = document.querySelector("[data-stack]");
    if (!link) return;
    var front = link.querySelector("[data-stack-img]");
    var ghost = link.querySelector("[data-stack-ghost]");
    var picks = document.querySelectorAll("[data-pick]");
    if (!front || !ghost || !picks.length) return;
    var current = "modern";
    var busy = false;

    function stackSrc(t) {
      return "/assets/screenshots/invoice-stack-" + t + ".png";
    }
    function pdfHref(t) {
      return "/assets/samples/invoice-" + t + ".pdf";
    }
    function mark(t) {
      picks.forEach(function (p) {
        p.setAttribute("aria-pressed", String(p.getAttribute("data-pick") === t));
      });
      link.setAttribute("href", pdfHref(t));
      link.setAttribute("aria-label", "Open the front invoice, the " + TEMPLATE_NAMES[t] + " template, as a PDF");
    }
    function show(t) {
      if (t === current || busy || TEMPLATES.indexOf(t) < 0) return;
      busy = true;
      ghost.onload = function () {
        ghost.alt = STACK_ALT[t];
        ghost.removeAttribute("aria-hidden");
        ghost.classList.add("is-front");
        front.classList.remove("is-front");
        front.setAttribute("aria-hidden", "true");
        front.alt = "";
        var was = front;
        front = ghost;
        ghost = was;
        current = t;
        busy = false;
        mark(t);
      };
      ghost.onerror = function () {
        busy = false;
      };
      ghost.src = stackSrc(t);
    }

    picks.forEach(function (p) {
      p.setAttribute("role", "button");
      p.addEventListener("click", function (e) {
        e.preventDefault();
        show(p.getAttribute("data-pick"));
      });
    });
    mark(current);
    var hint = document.querySelector("[data-stack-hint]");
    if (hint) hint.textContent = "Bring one to the front:";
    var after = document.querySelector("[data-stack-after]");
    if (after) after.hidden = false;

    // Fetch the other three stacks once the page is idle, so the first switch is instant.
    var idle = window.requestIdleCallback || function (f) { setTimeout(f, 1500); };
    idle(function () {
      TEMPLATES.forEach(function (t) {
        if (t !== current) new Image().src = stackSrc(t);
      });
    });
  }

  // ---- Header: a hairline once the page has scrolled under it ----
  function wireHeader() {
    var header = document.querySelector(".site-header");
    var sentinel = document.querySelector("[data-header-sentinel]");
    if (!header || !sentinel || !("IntersectionObserver" in window)) return;
    new IntersectionObserver(function (entries) {
      header.classList.toggle("is-stuck", !entries[0].isIntersecting);
    }).observe(sentinel);
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
    wireDemo();
    wireStack();
    wireHeader();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
