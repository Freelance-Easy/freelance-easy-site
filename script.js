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
      restartDemos(syncDemoTheme(next));
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
        function copyPageUrl() {
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
        }
        if (canShare) {
          navigator
            .share({ title: "Freelance Easy", text: "Freelance Easy, an invoicing app for your computer.", url: url })
            .then(function () { done("share"); })
            .catch(function (err) {
              // Cancelling the share sheet is silent; a real failure falls back to the copy path.
              if (!err || err.name !== "AbortError") copyPageUrl();
            });
          return;
        }
        copyPageUrl();
      });
    }
  }

  // ---- The loop (silent, plays like a GIF, with a Pause button) ----
  // The recording exists in both app themes: …-dark.mp4 / …-light.mp4, the
  // same for the posters and the real-time files. The page's theme picks the
  // set before anything loads (the HTML carries the dark one, preload="none",
  // with native controls for no-JS). Here the native controls give way to the
  // caption's Pause / Play button and the loop starts, unless the visitor
  // prefers reduced motion (then it waits, with the native controls). Autoplay
  // refused (iOS Low Power Mode, a strict browser setting): the native controls
  // come back, so the poster is never a dead end. A visitor's pause survives a
  // theme switch.
  var motionQuery = null;
  var reduceMotion = false;
  try {
    motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    reduceMotion = motionQuery.matches;
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

  var demoPausedByVisitor = false;

  function wireDemo() {
    syncDemoTheme(currentTheme());
    var videos = document.querySelectorAll("video[data-demo]");
    var toggle = document.querySelector("[data-demo-toggle]");

    function reflect() {
      if (!toggle || !videos.length) return;
      var playing = !videos[0].paused;
      toggle.textContent = playing ? "Pause" : "Play";
      toggle.setAttribute("aria-pressed", String(!playing));
      toggle.setAttribute("aria-label", (playing ? "Pause" : "Play") + " the recording");
    }
    function start(v) {
      if (reduceMotion || demoPausedByVisitor) return;
      playDemo(v);
    }

    videos.forEach(function (v) {
      v.addEventListener("play", reflect);
      v.addEventListener("pause", reflect);
      if (reduceMotion) return; // poster + the native controls, plays on request
      v.controls = false;
      start(v);
    });
    if (toggle && !reduceMotion && videos.length) {
      toggle.hidden = false;
      toggle.addEventListener("click", function () {
        var v = videos[0];
        if (v.paused) {
          demoPausedByVisitor = false;
          playDemo(v);
        } else {
          demoPausedByVisitor = true;
          v.pause();
        }
      });
      reflect();
    }
    if (motionQuery) {
      var onChange = function (e) {
        reduceMotion = e.matches;
        videos.forEach(function (v) {
          if (reduceMotion) {
            v.pause();
            v.controls = true;
            if (toggle) toggle.hidden = true;
          } else {
            v.controls = false;
            if (toggle) toggle.hidden = false;
            start(v);
          }
        });
      };
      if (motionQuery.addEventListener) motionQuery.addEventListener("change", onChange);
      else if (motionQuery.addListener) motionQuery.addListener(onChange);
    }
  }
  function restartDemos(videos) {
    videos.forEach(function (v) {
      if (!reduceMotion && !demoPausedByVisitor) playDemo(v);
    });
  }

  // ---- The hero pile: bring a template to the front ----
  // Four real sheets (one <a> per template, see index.html) laid out by the
  // custom properties --x / --y (percent of the pile's width), --r (degrees)
  // and --z. The geometry mirrors scripts/build-hero-collage.py: a sheet behind
  // the front one rises by the band that holds its template's signature; the
  // slot it occupies sets its x offset and tilt. Picking a template (the names
  // under the pile, or a click on a sheet in the pile) re-arranges the values
  // and the sheets glide; the chosen one rides above the others on the way.
  // The front sheet is a link to its PDF. Without JS the caption's names are
  // plain links to the PDFs and the pile stays as the HTML laid it out.
  var TEMPLATES = ["modern", "bold", "classic", "minimal"];
  var TEMPLATE_NAMES = { modern: "Modern", bold: "Bold", classic: "Classic", minimal: "Minimal" };
  var PILE = {
    frontY: 56.098,
    band: { modern: 15.244, bold: 27.439, classic: 13.415, minimal: 13.415 },
    slotX: [0, 4.878, 9.756, 14.634],
    slotR: [0, 1.1, -1.3, 0.8],
  };
  var SHEET_ALT = {
    modern: "A session-day invoice for Westbrook Sound in the Modern template: an engineer day rate and a kit fee totalling $750, with a teal rule and totals box.",
    bold: "The same invoice in the Bold template: a navy 'Invoice #INV1045' title over a black rule, a navy table header and balance box.",
    classic: "The same invoice in the Classic template: a forest-green bar across the top and the name and job in a serif.",
    minimal: "The same invoice in the Minimal template: a centred grey INVOICE title and hairline rules.",
  };

  function wireStack() {
    var pile = document.querySelector("[data-stack]");
    if (!pile) return;
    var sheets = {};
    TEMPLATES.forEach(function (t) {
      sheets[t] = pile.querySelector('[data-sheet="' + t + '"]');
    });
    if (TEMPLATES.some(function (t) { return !sheets[t]; })) return;
    var picks = document.querySelectorAll("[data-pick]");
    var open = document.querySelector("[data-stack-open]");
    var current = "modern";
    var moving = null;
    var settleTimer = null;

    function pdfHref(t) {
      return "/assets/samples/invoice-" + t + ".pdf";
    }
    function arrange(front) {
      var order = [front].concat(TEMPLATES.filter(function (t) { return t !== front; }));
      var y = PILE.frontY;
      order.forEach(function (t, i) {
        var el = sheets[t];
        var img = el.querySelector("img");
        if (i > 0) y -= PILE.band[t];
        el.style.setProperty("--x", String(PILE.slotX[i]));
        el.style.setProperty("--y", y.toFixed(3));
        el.style.setProperty("--r", String(PILE.slotR[i]));
        el.style.setProperty("--z", String(TEMPLATES.length - i));
        el.classList.toggle("is-front", i === 0);
        if (i === 0) {
          el.removeAttribute("aria-hidden");
          el.removeAttribute("tabindex");
          el.setAttribute("aria-label", "Open the " + TEMPLATE_NAMES[t] + " invoice as a PDF");
          if (img) img.alt = SHEET_ALT[t];
        } else {
          el.setAttribute("aria-hidden", "true");
          el.setAttribute("tabindex", "-1");
          if (img) img.alt = "";
        }
      });
    }
    function mark(t) {
      picks.forEach(function (p) {
        p.setAttribute("aria-pressed", String(p.getAttribute("data-pick") === t));
      });
      if (open) {
        open.setAttribute("href", pdfHref(t));
        open.textContent = "Open the " + TEMPLATE_NAMES[t] + " PDF";
      }
    }
    function show(t) {
      if (t === current || TEMPLATES.indexOf(t) < 0) return;
      if (moving) moving.classList.remove("is-moving");
      moving = sheets[t];
      moving.classList.add("is-moving");
      clearTimeout(settleTimer);
      settleTimer = setTimeout(function () {
        if (moving) moving.classList.remove("is-moving");
        moving = null;
      }, 700);
      current = t;
      arrange(t);
      mark(t);
    }

    picks.forEach(function (p) {
      p.setAttribute("role", "button");
      p.addEventListener("click", function (e) {
        e.preventDefault();
        show(p.getAttribute("data-pick"));
      });
      p.addEventListener("keydown", function (e) {
        if (e.key === " " || e.key === "Spacebar") {
          e.preventDefault(); // a button answers to Space as well as Enter
          show(p.getAttribute("data-pick"));
        }
      });
    });
    TEMPLATES.forEach(function (t) {
      sheets[t].addEventListener("click", function (e) {
        if (t === current) return; // the front sheet is the link to its PDF
        e.preventDefault();
        show(t);
      });
    });
    if (open) open.hidden = false;
    arrange(current);
    mark(current);
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
