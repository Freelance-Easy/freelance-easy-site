/* Ported from React Bits GradualBlur (reactbits.dev), MIT + Commons Clause. */
/* Freelance Easy site-touches FINAL (P2, 2026-10-12; from B1's gb-camp). The strip itself is static CSS
   (gradual-blur.css); this file only does the one job CSS cannot, on a page without a header-height token
   (audio, mac-audio): --fx-hh on <html> = the sticky header's height, at load and whenever the header resizes.
   Nothing here runs per frame: no scroll listener, no rAF. */
(function () {
  "use strict";
  var d = document.documentElement;
  var header = document.querySelector("header.site-header");
  var top = document.querySelector(".fx-gb--top");

  if (top && header) {
    var setHH = function () { d.style.setProperty("--fx-hh", header.offsetHeight + "px"); };
    setHH();
    if ("ResizeObserver" in window) new ResizeObserver(setHH).observe(header);
  }
})();
