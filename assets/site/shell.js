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

  window.FEShell = { flag: isOn, applyFlags: applyFlags };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { applyFlags(); });
  } else {
    applyFlags();
  }
})();
