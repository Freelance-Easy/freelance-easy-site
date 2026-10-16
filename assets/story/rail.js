/* rail.js (B5): the homepage chapter rail v3, per docs/interaction-contract.md ICX-HL, ICX-JUMP, ICX-HIST.9, ICX-NOPROG.
   - Renders the rail from FEStory.destinations (the one source B6's menu shares) and re-renders on every mode change.
   - Desktop (>= 1024 px): with the story it sits in the pin's left gutter; in calm / classic it is fixed in the same
     gutter beside the stacked sections, and hides rather than overlap them if the gutter is too narrow.
   - The highlight (.is-hl) follows dest on input (FEStory.onDest, FREE's nearest included, ICX-HL.1/.3);
     aria-current="location" moves only at a landing (FEStory.onLand, pass-through landings included, ICX-HL.2).
     In native sections both follow the scroll-spy (ICX-HL.4: the last anchor whose top is at or above 40 % of the
     viewport). This file is the only writer of either (ICX-HL.5).
   - A click is a jump: the anchor's own navigation is prevented (the hash never changes from the rail, so nothing jumps
     twice) and the jump goes through story-url.js's FEStoryURL.jump (C4: it writes the history), else FEStory.goTo.
   - The scroll-spy runs in every mode that has native sections, rail visible or not, and dispatches `fe:spy`
     {detail: {slug}} on document at every current-section change; story-url.js decides whether that writes history.
     This file never calls pushState / replaceState.
   - Keyboard inside the rail: ArrowUp / ArrowDown move between chapters, Home / End to the first / last, Enter jumps
     (the link's own activation). One tab stop: the current chapter (roving tabindex).
   Without JS the rail's markup is plain <a href="#slug"> anchors (decisions #20). */
(function () {
  "use strict";
  var nav = document.querySelector(".story-nav");
  var F = window.FEStory;
  if (!nav || !F || typeof F.onDest !== "function") return;
  var doc = document.documentElement;
  var list = nav.querySelector("ol");
  var pinHome = nav.parentNode, pinNext = nav.nextSibling;       // where the rail lives with the story (the pin)
  var story = document.getElementById("story");
  var DESK = window.matchMedia("(min-width: 1024px)");
  var SPY_LINE = 0.4;                                             // ICX-HL.4 (decisions §C, was OPEN-17)
  var GAP_MIN = 16;                                               // calm: the rail's clearance to the content

  var rows = [], items = [], hl = -1, cur = -1, spyCur = -1, mode = null, io = null;

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function readRows() { try { return F.destinations || []; } catch (e) { return []; } }
  function hasPinned() { for (var i = 0; i < rows.length; i++) if (rows[i].kind === "pinned") return true; return false; }
  function hasNative() { for (var i = 0; i < rows.length; i++) if (rows[i].kind === "native") return true; return false; }

  /* ---- render: one link per destination row, in beat order (reuses the static markup's links) ---- */
  function render() {
    var links = list.querySelectorAll("a[data-go]");
    if (links.length > rows.length) for (var j = rows.length; j < links.length; j++) list.removeChild(links[j].parentNode);
    items = [];
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i], a = links[i];
      if (!a) {
        var li = document.createElement("li");
        a = document.createElement("a");
        var tk = document.createElement("span"); tk.className = "tk"; tk.setAttribute("aria-hidden", "true");
        var nm = document.createElement("span"); nm.className = "nm";
        a.appendChild(tk); a.appendChild(nm); li.appendChild(a); list.appendChild(li);
      }
      if (a.getAttribute("href") !== "#" + r.anchor) a.setAttribute("href", "#" + r.anchor);
      a.setAttribute("data-go", r.beat);
      a.setAttribute("data-name", r.name);
      var n = a.querySelector(".nm");
      if (n.textContent !== r.name) n.textContent = r.name;
      a.style.setProperty("--i", String(i));
      items.push({ a: a, row: r });
    }
  }

  /* ---- state: the highlight (dest) and aria-current (rendered) ---- */
  function setHL(i) {
    if (i == null || i < 0 || i >= items.length) i = -1;
    hl = i;
    for (var j = 0; j < items.length; j++) items[j].a.classList.toggle("is-hl", j === i);
  }
  function rove(k) {
    for (var j = 0; j < items.length; j++) items[j].a.setAttribute("tabindex", j === k ? "0" : "-1");
  }
  function setCur(i) {
    if (i == null || i < 0 || i >= items.length) i = -1;
    cur = i;
    for (var j = 0; j < items.length; j++) {
      if (j === i) items[j].a.setAttribute("aria-current", "location");
      else items[j].a.removeAttribute("aria-current");
    }
    if (!nav.contains(document.activeElement)) rove(i < 0 ? 0 : i);   // Tab lands on the current chapter
  }
  function fromEngine() {
    var s = null;
    try { s = F.state(); } catch (e) { s = null; }
    if (!s || s.rendered == null) return;
    setCur(s.rendered);
    setHL(s.dest == null ? s.rendered : s.dest);
  }

  /* ---- placement: in the pin with the story, fixed in the gutter in calm / classic, hidden below 1024 px ---- */
  function contentLeft() {
    var min = Infinity, secs = document.querySelectorAll("main .beat > .shell");
    for (var i = 0; i < secs.length; i++) {
      var el = secs[i], r = el.getBoundingClientRect();
      if (!r.width) continue;
      var pl = parseFloat(getComputedStyle(el).paddingLeft) || 0;
      min = Math.min(min, r.left + pl);
    }
    return min;
  }
  function place() {
    var desk = DESK.matches;
    var pinned = hasPinned();
    var show = desk && (pinned ? mode === "desktop" : mode === "calm" || mode === "classic");
    if (pinned || !show) {
      nav.classList.remove("is-fixed");
      doc.classList.remove("has-rail");
      if (nav.parentNode !== pinHome) pinHome.insertBefore(nav, pinNext && pinNext.parentNode === pinHome ? pinNext : pinHome.firstChild);
      nav.hidden = !show;
      bandWatch(false);
      return;
    }
    // calm / classic / static at >= 1024 px: beside the stacked sections
    if (story && story.parentNode && nav.parentNode !== story.parentNode) story.parentNode.insertBefore(nav, story);
    nav.classList.add("is-fixed");
    doc.classList.add("has-rail");
    nav.hidden = false;
    var r = nav.getBoundingClientRect();
    if (r.right + GAP_MIN > contentLeft()) {                       // too narrow: hide rather than overlap
      nav.hidden = true;
      doc.classList.remove("has-rail");
    }
    bandWatch(!nav.hidden);
  }

  /* ---- calm / classic: which links sit over the Ride's band section (the fixed rail straddles its edges) ---- */
  var bandSec = document.querySelector(".chapter--chase"), bandOn = false, bandRaf = 0;
  function bandMark() {
    bandRaf = 0;
    var fixed = nav.classList.contains("is-fixed") && !nav.hidden;
    var r = fixed && bandSec ? bandSec.getBoundingClientRect() : null, ons = [], i;
    for (i = 0; i < items.length; i++) {
      var on = false;
      if (r && r.height) {
        var lr = items[i].a.getBoundingClientRect(), c = lr.top + lr.height / 2;
        on = c >= r.top && c <= r.bottom;                         // the link's centre is over the band
      }
      ons.push(on);
    }
    // the ends of the run over the band feather the light theme's shade (rail.css), so it never reads as a panel
    for (i = 0; i < items.length; i++) {
      var a = items[i].a;
      a.classList.toggle("on-band", ons[i]);
      a.classList.toggle("band-first", ons[i] && !ons[i - 1]);
      a.classList.toggle("band-last", ons[i] && !ons[i + 1]);
    }
  }
  function bandSoon() { if (!bandRaf) bandRaf = requestAnimationFrame(bandMark); }
  function bandWatch(on) {
    if (on !== bandOn) {
      bandOn = on;
      if (on) window.addEventListener("scroll", bandSoon, { passive: true });
      else window.removeEventListener("scroll", bandSoon);
    }
    bandMark();
  }

  /* ---- the scroll-spy (ICX-HL.4, ICX-HIST.9): native sections only ---- */
  function spyCompute() {
    var line = window.innerHeight * SPY_LINE, k = -1;
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].kind !== "native") continue;
      var el = document.getElementById(rows[i].anchor);
      if (!el) continue;
      var r = el.getBoundingClientRect();
      if (!r.height && !r.width) continue;                         // not laid out in this mode
      if (r.top <= line) k = i;
    }
    return k;
  }
  var spyRaf = 0;
  function spy() {
    spyRaf = 0;
    if (!hasNative()) return;
    var k = spyCompute();
    if (k === spyCur) return;
    spyCur = k;
    if (k >= 0) {
      setHL(k); setCur(k);
      try { document.dispatchEvent(new CustomEvent("fe:spy", { detail: { slug: rows[k].slug } })); } catch (e) { /* old browser */ }
    } else if (hasPinned()) fromEngine();                          // back inside the pinned story: the engine's state
  }
  function spySoon() { if (!spyRaf) spyRaf = requestAnimationFrame(spy); }
  // a section's top crossing the 40 % line is an intersection change of the viewport's top 40 %. The margin is in px
  // from innerHeight (a % rootMargin is not reliably height-based), so it is rebuilt on every resize.
  var ioH = -1;
  function spyObserve() {
    if (!hasNative() || !("IntersectionObserver" in window)) return;
    var h = window.innerHeight;
    if (io && h === ioH) return;
    if (io) io.disconnect();
    ioH = h;
    io = new IntersectionObserver(spySoon, { rootMargin: "0px 0px -" + Math.round(h * (1 - SPY_LINE)) + "px 0px", threshold: [0, 1] });
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].kind !== "native") continue;
      var el = document.getElementById(rows[i].anchor);
      if (el) io.observe(el);
    }
  }
  function spyWatch() {
    if (io) { io.disconnect(); io = null; }
    window.removeEventListener("scroll", spySoon);
    spyCur = -2;                                                   // force the first computation to report
    if (!hasNative()) return;
    if ("IntersectionObserver" in window) spyObserve();
    else window.addEventListener("scroll", spySoon, { passive: true });
    spySoon();
  }

  /* ---- mode: re-render from the destination table ---- */
  function sync(m, dests) {
    mode = m;
    rows = dests || readRows();
    render();
    place();
    if (hasPinned()) {
      fromEngine();
      // a mode change keeps the reading place after this event (FEStory.setClassic -> restorePlace, a resize's re-snap),
      // and that landing emits nothing: read the engine again once it has settled the place
      requestAnimationFrame(function () { if (spyCur < 0 && hasPinned()) fromEngine(); });
    } else { setHL(-1); setCur(-1); }
    spyWatch();
  }

  F.onDest(function (p) {
    if (!p || spyCur >= 0) return;                                 // in a native section the spy leads
    setHL(p.index);                                                // ICX-HL.1 (and FREE's nearest, ICX-HL.3)
  });
  F.onLand(function (p) {
    if (!p || spyCur >= 0) return;
    setCur(p.index);                                               // ICX-HL.2: every landing, pass-through included
    if (p.final) setHL(p.index);
  });
  F.onModeChange(function (p) { sync(p && p.mode, p && p.destinations); });

  /* ---- input ---- */
  function itemOf(t) {
    var a = t && t.closest ? t.closest("a[data-go]") : null;
    if (!a || !nav.contains(a)) return -1;
    for (var i = 0; i < items.length; i++) if (items[i].a === a) return i;
    return -1;
  }
  nav.addEventListener("click", function (e) {
    var k = itemOf(e.target);
    if (k < 0 || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();                                            // the hash never changes from the rail itself
    var slug = items[k].row.slug;
    var U = window.FEStoryURL;
    if (U && typeof U.jump === "function") U.jump(slug);
    else F.goTo(slug, { source: "jump" });
  });
  nav.addEventListener("keydown", function (e) {
    var k = itemOf(e.target);
    if (k < 0 || e.altKey || e.ctrlKey || e.metaKey) return;
    var to = { ArrowDown: k + 1, ArrowUp: k - 1, Home: 0, End: items.length - 1 }[e.key];
    if (to == null) return;
    e.preventDefault();                                            // the engine ignores a prevented key (ICX-KEY.7)
    items[clamp(to, 0, items.length - 1)].a.focus({ preventScroll: true });
  });
  nav.addEventListener("focusin", function (e) { var k = itemOf(e.target); if (k >= 0) rove(k); });
  nav.addEventListener("focusout", function (e) { if (!nav.contains(e.relatedTarget)) rove(cur < 0 ? 0 : cur); });

  var placeRaf = 0;
  function placeSoon() {
    if (placeRaf) return;
    placeRaf = requestAnimationFrame(function () { placeRaf = 0; place(); spyObserve(); spySoon(); });
  }
  window.addEventListener("resize", placeSoon);
  if (DESK.addEventListener) DESK.addEventListener("change", placeSoon);

  sync(F.mode, readRows());
})();
