/* =====================================================================================================================
   The 25-second tour, in a dialog over the homepage (2026-10-06). Daniel: a "pretty quick animatic show of the app
   flow", opened from the hero ("Watch the 25-second tour", beside Download) and from the header's "How it works" ("i
   want them to see the app invoicing flow rather than just sent to a still part of the site"). The scroll story is
   untouched: this file never reads or writes its state.
   - Native <dialog> + showModal(): Esc, the top layer, and everything behind it inert (the chapter rail included).
   - The iframe (/tour/quick/#embed&<theme>) is created on open and removed on close: it restarts every
     time and loads nothing until it's asked for. It follows the page's theme (html[data-theme]) at open.
   - Scroll lock without moving the page: html.tq-locked only sets overflow hidden (+ a stable scrollbar gutter, so
     nothing shifts sideways); scrollY never changes, so site.js's follower sees no scroll event and no jump on close.
   - Focus returns to whatever opened it, with preventScroll (the header's links and the hero's caption both stay put).
   - Without JS (or <dialog>) the links do what their href says: the hero's opens the standalone tour, "How it works"
     goes to #how. A modified click (new tab / window) is left to the browser too.
   ===================================================================================================================== */
(() => {
  "use strict";
  const doc = document.documentElement;
  const dlg = document.getElementById("tour-quick");
  if (!dlg || typeof dlg.showModal !== "function") return;
  const slot = dlg.querySelector(".tq-frame");
  const SRC = "/tour/quick/";
  let opener = null, live = false;

  function open(el) {
    if (dlg.open) return;
    opener = el;
    live = true;
    const theme = doc.getAttribute("data-theme") === "light" ? "light" : "dark";
    const f = document.createElement("iframe");
    f.src = `${SRC}#embed&${theme}`;
    f.title = "Watch the 25-second tour";                // the button's (NEW COPY) words; no further copy
    f.setAttribute("loading", "eager");
    slot.replaceChildren(f);
    doc.classList.add("tq-locked");
    dlg.showModal();
  }
  // idempotent: the dialog's close event and a page leaving (pagehide) both land here, whichever comes first.
  // (Sol v2.4: no scroll restore here. The lock never moves the page, and after a resize or rotation site.js has
  // already re-mapped the scroll to keep the story's time, so restoring the opening scrollY would move it to another beat)
  function onClose() {
    if (!live) return;
    live = false;
    slot.replaceChildren();                                // the iframe goes: playback stops, nothing keeps running
    doc.classList.remove("tq-locked");
    if (opener && opener.isConnected) opener.focus({ preventScroll: true });
    opener = null;
  }
  dlg.addEventListener("close", onClose);
  // following "Full tour" (or any navigation) with the dialog open: close it now, synchronously, so a page restored
  // from the back/forward cache comes back unlocked with no dialog (the close event alone is queued, too late for it)
  window.addEventListener("pagehide", () => {
    if (dlg.open) dlg.close();
    onClose();
  });
  // a click on the backdrop (the dialog's own box is the full viewport; the tour sits in .tq-box) closes it
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  dlg.querySelector(".tq-close").addEventListener("click", () => dlg.close());
  // Esc with focus INSIDE the tour (after Tab, or a click on its Play) fires in the iframe's document, not here: the
  // tour posts { tourQuick: "close" } and only a message from this dialog's own iframe, on this page's own origin, is
  // taken (Sol v2.4: a frame that navigated elsewhere keeps its contentWindow; "null" === "null" covers file://)
  window.addEventListener("message", (e) => {
    const f = slot.firstElementChild;
    if (dlg.open && f && e.source === f.contentWindow && e.origin === location.origin && e.data && e.data.tourQuick === "close") dlg.close();
  });

  for (const el of document.querySelectorAll("[data-tour-quick]")) {
    el.setAttribute("aria-haspopup", "dialog");
    el.setAttribute("aria-controls", "tour-quick");
    // a listener on the link itself runs before site.js's document-level anchor handler; stopping it there keeps
    // "How it works" from also jumping the story to #how
    el.addEventListener("click", (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      e.stopPropagation();
      open(el);
    });
  }
})();
