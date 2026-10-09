/* Generic timeline math adapted from ../app/fe-motion.js. No proposed app motion. */
(() => {
  'use strict';
  const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
  const tween = (t, start, duration) => clamp((t - start) / duration);
  const smooth = t => t * t * (3 - 2 * t);
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  // Designed cursor belongs to the player presentation, with a gentle curved glide.
  const glide = (from, to, t) => {
    const p = smooth(clamp(t)), arc = Math.sin(Math.PI * p) * .035;
    const dx = to.x - from.x, dy = to.y - from.y;
    return { x: from.x + dx * p - dy * arc, y: from.y + dy * p + dx * arc };
  };
  window.FM = { clamp, tween, smooth, wait, glide };
})();
