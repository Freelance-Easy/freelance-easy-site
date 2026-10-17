/* K1: the Classic view switch (decisions 2026-10-15 DEC-6, DEC-7, row 23).
 *
 * One button that turns the animated story off for a calm, static page, and back on. It is the site's global stop for
 * autoplay (WCAG 2.2.2): switching to Classic stops whatever is running at once. The choice is remembered per visitor in
 * localStorage "fe-classic" ("1" Classic, "0" the story); with no choice, a reduced-motion visitor starts in Classic and
 * may switch the story on. src/partials/head.html reads the same key before the first paint, so a remembered Classic
 * never shows a story frame first.
 *
 * "/"      the button fills the bar's [data-classic-slot] beside the theme toggle and drives FEStory.setClassic (site.js),
 *          which keeps the reading place. It is not shown where calm is automatic (a short touch screen, the same test
 *          as head.html and site.js): a dead control there. The stored choice is kept for larger screens.
 * /tour/   the button fills the bar's [data-classic-slot] (the bar sits in .tour-header) and, below 640 px, a menu-sheet row; proto.js listens for "fe:classicchange" and, in
 *          Classic, stops playback and shows each chapter's end state.
 * Focus never moves: the button keeps it. The button's state is aria-pressed.
 */
(function () {
  "use strict";
  var KEY = "fe-classic";
  var root = document.documentElement;
  var rm = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var coarse = window.matchMedia ? window.matchMedia("(pointer: coarse)") : null;

  function stored() {
    var v = null;
    try { v = localStorage.getItem(KEY); } catch (e) { v = null; }
    return v === "1" ? true : v === "0" ? false : null;
  }
  function store(on) {
    try { localStorage.setItem(KEY, on ? "1" : "0"); } catch (e) { /* storage off: the choice lasts this page */ }
  }
  var pref = stored();
  function isOn() { return pref != null ? pref : !!(rm && rm.matches); }

  // a short touch screen: under 600 px of small viewport (100svh) with a coarse pointer (head.html's and site.js's test)
  function shortTouch() {
    try {
      if (!coarse || !coarse.matches) return false;
      var pr = document.createElement("div");
      pr.style.cssText = "position:fixed;left:0;top:0;width:0;height:100svh;visibility:hidden;pointer-events:none";
      root.appendChild(pr);
      var sv = pr.getBoundingClientRect().height || window.innerHeight;
      root.removeChild(pr);
      return sv < 600;
    } catch (e) { return false; }
  }

  var ICON = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><rect x="2.5" y="2" width="11" height="12" rx="2" />' +
    '<path d="M5.5 5.5h5M5.5 8h5M5.5 10.5h3" /></svg>';

  function makeButton(slot) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "classic-toggle";
    b.setAttribute("data-classic-toggle", "");
    b.setAttribute("aria-label", "Classic view");                    // NEW COPY (aria-label)
    b.setAttribute("title", "Classic view");                         // NEW COPY (tooltip)
    b.innerHTML = ICON + '<span class="classic-label">Classic</span>'; // NEW COPY (bar label, >= 1024 px)
    slot.appendChild(b);
    return b;
  }

  // the phone sheet's row (< 640 px, where the bar has no room: shell.css): the same switch, its name as its words
  function makeSheetRow(panel) {
    var close = panel.querySelector("[data-menu-close]");
    var row = document.createElement("div");
    row.className = "fe-menu-classic";
    var b = document.createElement("button");
    b.type = "button";
    b.className = "classic-toggle";
    b.setAttribute("data-classic-toggle", "");
    b.innerHTML = ICON + '<span class="classic-label">Classic view</span><span class="classic-state" aria-hidden="true"></span>';
    row.appendChild(b);
    panel.insertBefore(row, close && close.parentNode === panel ? close : null);
    return b;
  }

  var btns = [], story = null, auto = false;
  var btn = null;
  function sync() {
    var on = isOn() ? "true" : "false", gone = auto && shortTouch();
    if (auto) root.classList.toggle("calm-auto", gone);
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute("aria-pressed", on);
      var row = btns[i].closest(".fe-menu-classic");
      (row || btns[i]).hidden = gone;
    }
  }
  function announce(on) {
    document.dispatchEvent(new CustomEvent("fe:classicchange", { detail: { on: on } }));
  }
  function toggle() {
    var on = !isOn();
    pref = on;
    store(on);
    // the stop: Classic tears the story down at once (no run, no frame loop), keeping the reading place
    if (story) story.setClassic(on);
    sync();
    announce(on);
  }

  function initHome(slot) {
    story = window.FEStory;
    // header.html made the bar's button as the parser passed (no shift on the first paint); no engine: no dead control
    var made = slot.querySelector("[data-classic-toggle]");
    if (!story || typeof story.setClassic !== "function") { if (made) slot.removeChild(made); return; }
    auto = true;
    btns.push(made || makeButton(slot));
    var panel = document.querySelector("#fe-menu .fe-menu-panel");
    if (panel) btns.push(makeSheetRow(panel));
    for (var i = 0; i < btns.length; i++) btns[i].addEventListener("click", toggle);
    // the remembered choice reaches the engine. head.html already set the classes before the first paint; Classic is
    // handed over now, before the engine's first start (cheap: the calm layout). The story chosen over reduced motion
    // waits for that start (a switch now would build the stage before the fonts land), then keeps its place.
    if (pref === true) story.setClassic(true);
    else if (pref === false && rm && rm.matches) {
      var off = story.onModeChange(function () { off(); Promise.resolve().then(function () { story.setClassic(false); }); });
    }
    // the motion preference changes mid-visit: site.js follows it unless the engine holds the choice; re-assert a
    // remembered story (Classic is always held)
    if (rm && rm.addEventListener) rm.addEventListener("change", function () {
      if (pref === false) story.setClassic(false);
      sync();
    });
    var later = function () { sync(); };
    window.addEventListener("resize", later);
    if (coarse && coarse.addEventListener) coarse.addEventListener("change", later);
    sync();
  }

  function initTour(slot) {
    btn = makeButton(slot);
    btns.push(btn);
    // (TOUR) the tour is on the shared bar now: below 640 px the bar has no room, so the switch is a sheet row there, as on "/"
    var panel = document.querySelector("#fe-menu .fe-menu-panel");
    if (panel) btns.push(makeSheetRow(panel));
    for (var i = 0; i < btns.length; i++) btns[i].addEventListener("click", toggle);
    if (rm && rm.addEventListener) rm.addEventListener("change", sync);
    sync();
  }

  // the tour's script asks for the effective state (proto.js)
  window.FEClassic = Object.freeze({ isOn: isOn, chosen: function () { return pref === true; } });

  function ready() {
    var slot = document.querySelector("[data-classic-slot]");
    if (!slot || slot.getAttribute("data-wired")) return;
    slot.setAttribute("data-wired", "1");
    if (document.body && document.body.getAttribute("data-page") === "home") initHome(slot);
    else if (slot.closest(".tour-header") || (document.body && document.body.getAttribute("data-page") === "tour")) initTour(slot);
  }
  // on "/" this runs in the tail, after the bar is parsed: at once, so Classic reaches the engine before its first start
  if (document.readyState !== "loading" || document.querySelector("[data-classic-slot]")) ready();
  else document.addEventListener("DOMContentLoaded", ready);
})();
