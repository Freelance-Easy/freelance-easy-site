/* The shared shell (B2): one script every page loads from src/partials/head.html (deferred).
 *
 * The site switch for web-account UI. Contract: the web-account snapshot (children/E-web-account-contract.md § 6):
 *   data-flag="web-signup"   the bar's Sign in (B4) and the /pricing web path (PR-1)
 *   data-flag="web-billing"  the footer's Manage subscription (B2)
 * Flagged elements ship with the hidden attribute (so they stay hidden without JS) and are shown only when their
 * flag below is true. Web accounts are PAUSED (Daniel, 2026-10-15): both flags are off. This script makes no
 * network request; it never calls /web/* or api.freelance-easy.com.
 */
(function () {
  "use strict";
  var FLAGS = { "web-signup": false, "web-billing": false };

  function isOn(name) {
    return Object.prototype.hasOwnProperty.call(FLAGS, name) && FLAGS[name] === true;
  }

  function applyFlags(root) {
    var els = (root || document).querySelectorAll("[data-flag]");
    for (var i = 0; i < els.length; i++) {
      var on = isOn(els[i].getAttribute("data-flag"));
      // the flag guard: an element is shown only when its flag is on; unknown flags stay hidden
      els[i].hidden = !on;
      // a flagged link carries its target in data-flag-href (the page may not exist while the flag is off) and
      // becomes a real link only when shown
      var links = [els[i]].concat(Array.prototype.slice.call(els[i].querySelectorAll("[data-flag-href]")));
      for (var j = 0; j < links.length; j++) {
        var to = links[j].getAttribute("data-flag-href");
        if (to === null) continue;
        if (on) links[j].setAttribute("href", to);
        else links[j].removeAttribute("href");
      }
    }
  }

  /* ---------- (B6) the phone/tablet menu sheet (src/partials/menu.html) ----------
     A non-modal <dialog> under the bar, so the bar (its theme toggle, the menu button that now reads as a close) stays
     live; everything else in <body> is inert and the page cannot scroll while it is open. Focus is trapped in the
     sheet (Tab and Shift+Tab wrap); Escape, the sheet's Close, the menu button and a tap on the dim area close it, and
     focus goes back to the menu button. The chapter list renders from FEStory.destinations, the rail's own source
     (rail.js); the current chapter is read from the rail's aria-current, never written here (ICX-HL.5). A chapter tap
     closes the sheet first, then jumps exactly as a rail click: FEStoryURL.jump when C4 is present, else
     FEStory.goTo(slug, {source: "jump"}), which scrolls a native row natively (ICX-JUMP.5). Nothing here writes history. */
  function menu() {
    var dlg = document.getElementById("fe-menu");
    var btn = document.querySelector("[data-menu-open]");
    if (!dlg || !btn || dlg.getAttribute("data-wired")) return;
    dlg.setAttribute("data-wired", "1");
    var root = document.documentElement;
    var chapters = dlg.querySelector(".fe-menu-chapters"), list = chapters ? chapters.querySelector("ol") : null;
    var made = [];                                                  // body children this sheet made inert

    function story() { return document.querySelector(".story-nav") && window.FEStory ? window.FEStory : null; }

    function renderChapters() {
      var F = story();
      var rows = [];
      if (F) { try { rows = F.destinations || []; } catch (e) { rows = []; } }
      if (!list || !rows.length) { if (chapters) chapters.hidden = true; return; }
      var on = document.querySelector('.story-nav a[aria-current="location"]');
      var cur = on ? on.getAttribute("data-go") : null;            // the rail's state (rail.js owns it)
      while (list.firstChild) list.removeChild(list.firstChild);
      for (var i = 0; i < rows.length; i++) {
        var li = document.createElement("li"), a = document.createElement("a");
        a.setAttribute("href", "#" + rows[i].anchor);
        a.setAttribute("data-go", rows[i].beat);
        a.setAttribute("data-slug", rows[i].slug);
        a.textContent = rows[i].name;
        if (rows[i].beat === cur) {
          a.className = "is-current";
          var sr = document.createElement("span");
          sr.className = "fe-menu-sr";
          sr.textContent = " (current chapter)";                    // NEW COPY (screen-reader text)
          a.appendChild(sr);
        }
        li.appendChild(a);
        list.appendChild(li);
      }
      chapters.hidden = false;
    }

    function focusables() {
      var all = dlg.querySelectorAll("a[href], button:not([disabled])"), out = [];
      for (var i = 0; i < all.length; i++) if (all[i].getClientRects().length && !all[i].closest("[hidden]")) out.push(all[i]);
      return out;
    }

    function isOpen() { return dlg.open; }

    function open() {
      if (isOpen()) return;
      renderChapters();
      made = [];
      var kids = document.body.children;
      for (var i = 0; i < kids.length; i++) {
        var k = kids[i];
        if (k === dlg || k.classList.contains("site-header") || k.tagName === "SCRIPT" || k.inert) continue;
        k.inert = true;
        made.push(k);
      }
      root.classList.add("fe-menu-open");
      dlg.show();
      btn.setAttribute("aria-expanded", "true");
      btn.setAttribute("aria-label", "Close menu");                // NEW COPY (aria-label)
      var f = focusables();
      if (f.length) f[0].focus({ preventScroll: true });
    }

    // synchronous: a chapter jump that follows must find the page scrollable again
    function close(refocus) {
      if (!isOpen()) return;
      dlg.close();
      for (var i = 0; i < made.length; i++) made[i].inert = false;
      made = [];
      root.classList.remove("fe-menu-open");
      btn.setAttribute("aria-expanded", "false");
      btn.setAttribute("aria-label", "Menu");                      // NEW COPY (aria-label)
      if (refocus !== false) btn.focus({ preventScroll: true });    // focus returns to the menu button
    }

    btn.addEventListener("click", function () { if (isOpen()) close(); else open(); });
    dlg.addEventListener("click", function (e) {
      if (e.target === dlg || (e.target.closest && e.target.closest("[data-menu-close]"))) { close(); return; }
      var a = e.target.closest ? e.target.closest("a[data-go]") : null;
      if (!a || !list || !list.contains(a)) return;
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();                                           // the jump owns the move (and the history, C4)
      var slug = a.getAttribute("data-slug");
      close();
      var U = window.FEStoryURL, F = story();
      if (U && typeof U.jump === "function") U.jump(slug);
      else if (F) F.goTo(slug, { source: "jump" });
    });
    // the focus trap: Tab and Shift+Tab wrap inside the sheet
    dlg.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") return;
      var f = focusables();
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1], at = document.activeElement;
      if (e.shiftKey && (at === first || !dlg.contains(at))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (at === last || !dlg.contains(at))) { e.preventDefault(); first.focus(); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isOpen()) { e.preventDefault(); close(); }
    });
    // a link in the bar (the logo, Download, How it works) leaves or moves the page: the sheet closes first
    var bar = btn.closest(".site-header");
    if (bar) bar.addEventListener("click", function (e) {
      if (isOpen() && e.target.closest && e.target.closest("a[href]")) close(false);
    }, true);
    // a width where the button is gone (a rotation, a resize past the rail's breakpoint) closes the sheet
    window.addEventListener("resize", function () {
      if (isOpen() && !btn.getClientRects().length) close(false);
    });
  }

  window.FEShell = { flag: isOn, applyFlags: applyFlags };

  function ready() { applyFlags(); menu(); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ready);
  } else {
    ready();
  }
})();
