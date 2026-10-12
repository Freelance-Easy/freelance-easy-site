/* Ported from React Bits FadeContent (reactbits.dev), MIT + Commons Clause. */
/* FINAL (P2, 2026-10-12; from B3's rv-camp, tuned per J1-rv): play-once picture reveal (audio.html,
   mac-audio.html). Vanilla, no GSAP. Runs at the end of <body>, before ./script.js. Contract:
   - Hides ONLY [data-fx="reveal"] figures whose top is below the viewport at init
     (.rv-wait; reveal.css applies it to the figure's media and lit pool, never its caption).
   - No IntersectionObserver, or prefers-reduced-motion: returns before hiding anything.
   - IntersectionObserver (threshold 0.15, rootMargin 0 0 -8% 0). On entry: .rv-wait off,
     .rv-in on (0.8 s, enter curve), then unobserve: once per element, forever.
   - First seen already past the top of the viewport (a jump past it): shown at once.
   - One mover: a figure entering within 0.5 s of the last start waits for that beat.
   - Reduce switching on mid-visit: every waiting figure shows at once.
   No scroll listeners, no rAF, no CSS custom properties (data-fx-props is empty). */
(function () {
  "use strict";

  if (!("IntersectionObserver" in window)) return;
  var mq = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  if (mq && mq.matches) return;

  var root = document.documentElement;
  var DUR = 800; // ms, matches reveal.css
  var BEAT = 500; // ms, one mover at a time
  var THRESHOLD = 0.15;

  var vh = window.innerHeight || root.clientHeight;
  var all = document.querySelectorAll('[data-fx="reveal"]');
  var waiting = [];
  for (var i = 0; i < all.length; i++) {
    if (all[i].getBoundingClientRect().top >= vh) {
      all[i].classList.add("rv-wait");
      waiting.push(all[i]);
    }
  }
  if (!waiting.length) return;

  var nextStart = 0;

  function showNow(el) {
    el.classList.remove("rv-wait");
  }

  function start(el) {
    if (!el.classList.contains("rv-wait")) return; // already shown (reduce switched on)
    var done = false;
    var timer = 0;
    function finish(e) {
      if (e && e.propertyName !== "opacity") return;
      if (done) return;
      done = true;
      el.removeEventListener("transitionend", finish);
      el.removeEventListener("transitioncancel", finish);
      clearTimeout(timer);
      el.classList.remove("rv-in"); // drops the transition and will-change
    }
    el.addEventListener("transitionend", finish);
    el.addEventListener("transitioncancel", finish);
    timer = setTimeout(finish, DUR + 250); // in case no transitionend arrives
    el.classList.add("rv-in");
    el.classList.remove("rv-wait");
  }

  function play(el) {
    var now = performance.now();
    var wait = Math.max(0, nextStart - now);
    nextStart = now + wait + BEAT;
    if (wait > 0) setTimeout(function () { start(el); }, wait);
    else start(el);
  }

  var io = new IntersectionObserver(
    function (entries) {
      for (var j = 0; j < entries.length; j++) {
        var e = entries[j];
        var el = e.target;
        if (e.boundingClientRect.top < 0) {
          // Past the viewport's top edge on first sight (anchor link, restored scroll,
          // a fast flick): shown at once, no dead frame, no late motion.
          io.unobserve(el);
          showNow(el);
        } else if (e.isIntersecting && e.intersectionRatio >= THRESHOLD - 0.001) {
          io.unobserve(el); // once, forever
          play(el);
        } else {
          // Below the fold and not yet seen: keep it waiting.
          el.classList.add("rv-wait");
        }
      }
    },
    // Spec: threshold 0.15, rootMargin 0 0 -8% 0. The top margin is extended far past
    // any page so that the whole region ABOVE the viewport is inside the root: a jump
    // straight from below the fold to past the top then flips the figure from "not
    // intersecting" to "fully intersecting" and fires this callback (with a 0 px top
    // margin it would cross no threshold and stay hidden). A figure below the fold never
    // touches the extended region, so entry from below triggers exactly as specified.
    { threshold: THRESHOLD, rootMargin: "1000000px 0px -8% 0px" }
  );

  for (var k = 0; k < waiting.length; k++) io.observe(waiting[k]);

  if (mq) {
    var onReduce = function (ev) {
      if (!ev.matches) return;
      io.disconnect();
      for (var m = 0; m < waiting.length; m++) {
        waiting[m].classList.remove("rv-wait", "rv-in");
      }
    };
    if (mq.addEventListener) mq.addEventListener("change", onReduce);
    else if (mq.addListener) mq.addListener(onReduce);
  }
})();
