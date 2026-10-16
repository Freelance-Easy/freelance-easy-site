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
   - Phones and tablets: no installers. The filled button ("Send to my Mac") shares the page (or copies its link) and
     the note says the app runs on a Mac or Windows PC; the other OS's link is hidden. On a phone the End row adds two
     quiet links ("Copy link", "On Windows? Send it to your PC") and the header's Download reads "Get it on Mac".
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

  function pageUrl() {
    return location.origin + location.pathname;
  }

  function copyLink(statusEls) {
    var url = pageUrl();
    function say(text) {
      statusEls.forEach(function (s) {
        s.textContent = text;
      });
    }
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

  function share(statusEls) {
    if (typeof navigator.share === "function") {
      navigator
        .share({ title: "Freelance Easy", text: "Freelance Easy, an invoicing app for your computer.", url: pageUrl() })
        .catch(function (err) {
          // Cancelling the share sheet is silent; a real failure falls back to the copy path.
          if (!err || err.name !== "AbortError") copyLink(statusEls);
        });
      return;
    }
    copyLink(statusEls);
  }

  // (piece M, Daniel 2026-10-11) a phone: < 640 px, or a short touch screen such as a phone in landscape (site.css's
  // phone rules use the same query). Only the header's label follows it; the share button's words are every mobile
  // device's (an iPad can't install either).
  var PHONE_MQ = "(max-width: 639px), (pointer: coarse) and (max-height: 599px)";

  function headerLabel(a) {
    if (!a || !window.matchMedia) return;
    var mq = window.matchMedia(PHONE_MQ);
    function set() {
      var want = mq.matches ? "Get it on Mac" : "Download";
      if (a.textContent !== want) a.textContent = want;
    }
    set();
    if (mq.addEventListener) mq.addEventListener("change", set);
    else if (mq.addListener) mq.addListener(set);
  }

  // (A9) a single Download link (the homepage header's): a Mac or Windows visitor gets /dl/<os>/<campaign>, which the
  // site answers as an attachment (worker.js's Mac proxy; _redirects for Windows). A plain click loads it in a hidden
  // iframe, so the file downloads and the page never navigates: an error answer (a worker 502, GitHub's 404 after the
  // Windows redirect) lands in the hidden frame, not over the homepage (Sol A9-1). A modified click (new tab or window)
  // is the browser's own. The note beside the link keeps the platform next to it (R5); once clicked, the status line
  // under the header says the download should start, with the requirement or the Windows warning and the install
  // help, and the note steps aside while it shows. The status line closes itself (STATUS_MS, Escape, the story moving
  // a beat or the page a viewport, or its ×). Phones keep "send to computer": the link still jumps to the download
  // block, whose button shares the page, and on a phone it reads "Get it on Mac". An OS the placement doesn't offer
  // (Linux, or Windows on a Mac-only page) keeps the plain link. Options: placement, platforms (["mac"] for a Mac-only
  // page); without them, data-placement and data-platforms="mac,win" (the default). Wiring twice is a no-op.
  // The note in two parts: one line from 1024 px, stacked in two below (dl-status.css), so the nav never crowds.
  var NOTES = {
    mac: ["Apple Silicon Macs" /* NEW COPY */, " ", "(M1 or later)" /* NEW COPY */],
    win: ["Windows 10 and 11" /* NEW COPY */, ", ", "64-bit" /* NEW COPY */],
  };
  var STATUS = {
    mac: {
      text: "Your download should start in a moment. For Apple Silicon Macs with macOS 12 or later." /* NEW COPY */,
      href: "/install#mac",
    },
    win: {
      text: "Your download should start in a moment. Windows warns you the first time you open it: the installer isn't code-signed yet." /* NEW COPY */,
      href: "/install#windows",
    },
  };
  var STATUS_MS = 12000; // the status line's own close (Daniel's flip: 0 = stays until closed)
  var FADE_MS = 200;
  var HELP = "Install help" /* NEW COPY */;
  var CLOSE = "Close" /* NEW COPY (the close button's accessible name) */;

  function platformList(value) {
    var list = (Array.isArray(value) ? value : String(value || "mac,win").split(","))
      .map(function (s) {
        return String(s).trim().toLowerCase();
      })
      .filter(function (s) {
        return s === "mac" || s === "win";
      });
    return list.length ? list : ["mac", "win"];
  }

  function noteFor(placement) {
    return document.querySelector('[data-dl-note][data-for="' + placement + '"]');
  }

  // the hidden frame the downloads load in (one per page, reused)
  var frame = null;
  function downloadInPlace(url) {
    if (!frame) {
      frame = document.createElement("iframe");
      frame.hidden = true;
      frame.tabIndex = -1;
      frame.setAttribute("aria-hidden", "true");
      frame.setAttribute("data-dl-frame", "");
      document.body.appendChild(frame);
    }
    frame.src = url;
  }

  // the status line: its box stays in the DOM, empty and not hidden, as a polite live region; filling it announces it
  var open = null; // {box, note, stop}
  function closeStatus(fade) {
    if (!open) return;
    var o = open;
    open = null;
    o.stop();
    if (o.note) o.note.classList.remove("is-covered");
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fade || reduce) {
      o.box.textContent = "";
      return;
    }
    o.box.classList.add("is-leaving");
    setTimeout(function () {
      if (open && open.box === o.box) return; // shown again meanwhile
      o.box.classList.remove("is-leaving");
      o.box.textContent = "";
    }, FADE_MS);
  }

  function showStatus(os, placement) {
    var box = document.querySelector('[data-dl-status][data-for="' + placement + '"]');
    if (!box) return;
    closeStatus(false);
    box.classList.remove("is-leaving");
    var s = STATUS[os];
    var p = document.createElement("p");
    p.appendChild(document.createTextNode(s.text + " "));
    var help = document.createElement("a");
    help.href = s.href;
    help.textContent = HELP;
    p.appendChild(help);
    var close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", CLOSE);
    close.textContent = "×";
    close.addEventListener("click", function () {
      closeStatus(true);
    });
    box.textContent = "";
    box.setAttribute("data-os", os);
    box.appendChild(p);
    box.appendChild(close);
    // the note says the same thing: it steps aside while the status line shows (keeping its place, so the nav stays put)
    var note = noteFor(placement);
    if (note) note.classList.add("is-covered");

    var y0 = window.scrollY;
    var timer = 0;
    function arm(ms) {
      if (!STATUS_MS) return;
      timer = setTimeout(function () {
        // not while the visitor is reading it with the pointer or the keyboard
        if (box.contains(document.activeElement) || box.matches(":hover")) arm(4000);
        else closeStatus(true);
      }, ms);
    }
    function onKey(e) {
      if (e.key === "Escape" || e.key === "Esc") closeStatus(true);
    }
    function onScroll() {
      if (Math.abs(window.scrollY - y0) >= window.innerHeight) closeStatus(true);
    }
    // the story moving a beat: site.js marks the current chapter with aria-current
    var beat = window.MutationObserver
      ? new MutationObserver(function () {
          closeStatus(true);
        })
      : null;
    if (beat) beat.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["aria-current"] });
    document.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onScroll, { passive: true });
    arm(STATUS_MS);
    open = {
      box: box,
      note: note,
      stop: function () {
        clearTimeout(timer);
        if (beat) beat.disconnect();
        document.removeEventListener("keydown", onKey);
        window.removeEventListener("scroll", onScroll);
      },
    };
  }

  function wireLink(a, os, campaign, opts) {
    if (a.hasAttribute("data-dl-wired")) return; // FEDownload.wire on a [data-dl] link init already wired
    a.setAttribute("data-dl-wired", "");
    opts = opts || {};
    var placement = opts.placement || a.getAttribute("data-placement") || "header";
    var platforms = platformList(opts.platforms || a.getAttribute("data-platforms"));
    if (os === "mobile") {
      var held = noteFor(placement);
      if (held) held.setAttribute("data-dl-skip", "");
      headerLabel(a);
      return;
    }
    if (platforms.indexOf(os) < 0) {
      var spare = noteFor(placement);
      if (spare) spare.setAttribute("data-dl-skip", ""); // not filled: give back the room dl-status.css held for it
      return;
    }
    a.setAttribute("data-platform", os);
    a.setAttribute("href", "/dl/" + os + "/" + campaign);
    var note = noteFor(placement);
    if (note) {
      note.textContent = "";
      var parts = NOTES[os];
      [0, 1, 2].forEach(function (i) {
        var span = document.createElement("span");
        span.className = i === 1 ? "dl-note-sep" : "dl-note-part";
        span.textContent = parts[i];
        note.appendChild(span);
      });
      note.hidden = false;
      if (note.id) a.setAttribute("aria-describedby", note.id);
    }
    a.addEventListener("click", function (e) {
      track("Download Click", { os: os, campaign: campaign, page: pageId(), placement: placement });
      // a new tab or window (modifier or middle click) is the browser's own
      if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      downloadInPlace(a.getAttribute("href"));
      showStatus(os, placement);
    });
  }

  function wire(block, os, campaign) {
    if (block.tagName === "A") return wireLink(block, os, campaign);
    var placement = block.getAttribute("data-placement") || "";
    var primary = block.querySelector('[data-role="primary"]');
    var alt = block.querySelector('[data-role="alt"]');
    if (!primary || !alt) return;
    // each row's own status line, next to its button (Sol: the pricing row's result used to land in the hero's)
    var statusEls = [].slice.call(document.querySelectorAll('[data-share-status][data-for="' + placement + '"]'));

    if (os === "mobile") {
      var label = primary.querySelector("[data-label]");
      // (piece M, Daniel 2026-10-11: "Share this page" read like a social share) the button sends the page to the
      // visitor's own computer: the share sheet (AirDrop to their Mac is at its top on an iPhone), else the copy path
      if (label) label.textContent = "Send to my Mac";
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
        // a role="button" link: Enter and Space both activate it, as a native button would (an iPad with a keyboard)
        if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
          e.preventDefault();
          share(statusEls);
        }
      });
      // (piece M) the row's two quiet links (phones only, site.css): "Copy link" copies; "On Windows? Send it to your
      // PC" is the same share as the button. Native buttons: one tab stop each, Enter and Space built in.
      [].slice.call(document.querySelectorAll('[data-dl-copy][data-for="' + placement + '"]')).forEach(function (b) {
        b.addEventListener("click", function () {
          copyLink(statusEls);
        });
      });
      [].slice.call(document.querySelectorAll('[data-dl-send][data-for="' + placement + '"]')).forEach(function (b) {
        b.addEventListener("click", function () {
          share(statusEls);
        });
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
    // (piece M) the header's "Download" says where the app goes, on a phone only (it still jumps to the download block);
    // (A9) wireLink does it for a [data-dl] header link, this covers a header without one
    var cta = document.querySelector(".site-header .nav-cta");
    if (os === "mobile" && cta && !cta.hasAttribute("data-dl")) headerLabel(cta);
  }

  // (A9) for a page that wires its own link, e.g. a Mac-only page: FEDownload.wire(el, {placement, platforms: ["mac"]})
  window.FEDownload = {
    wire: function (el, opts) {
      if (el) wireLink(el, detectPlatform(), campaignId(), opts);
    },
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
