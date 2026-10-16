/* Checkpoint tuning overlay + recorder (C7). DEV TOOL: loaded only when the URL has ?ci-tune (the hook at the end of
 * checkpoint-input.js lazy-loads this file). Visitors never get it: no flag, no request, no panel.
 *
 * What it does, for Daniel's device-feel session:
 *   - lists every detector constant (FECheckpoint.DEFAULTS, docs/checkpoint-config.md v1) as an editable number;
 *   - runs a SHADOW detector with those values on the page's real input. The shadow never calls preventDefault
 *     (its events are read-only copies), so it cannot change how the page behaves; it only reports what the detector
 *     would have done with the values you typed (steps, trigger, class);
 *   - records the raw input in the tests/fixtures/input/*.json format (tests/checkpoint/run_detector.mjs reads it),
 *     so a real trackpad / mouse / phone session becomes a fixture.
 * No network, no storage (cookies, localStorage, sessionStorage): a recording leaves the page only through the
 * Export (a file download) or Copy buttons, which you press. Keys other than navigation keys are never recorded,
 * and node snapshots hold only tag, role, parent and scroll geometry (no text, ids or classes of the page).
 * Limits: a node's scroll geometry is snapshotted when first seen, and run_detector.mjs replays with DEFAULTS (the
 * tuned values travel in the file's "config" key for a runner that reads it; this tool does not edit the runner).
 * Window API for tests: window.__ciTune = { exportRecording(), startRecording(), stopRecording(), clear(), state() }.
 * Classic script; needs checkpoint-input.js loaded first (the hook guarantees it).
 */
(function (root) {
  "use strict";
  var FE = root.FECheckpoint, doc = root.document;
  if (!FE || !doc || root.__ciTune) return;

  var MAX_EVENTS = 6000;
  var NAV_KEYS = { ArrowUp: 1, ArrowDown: 1, ArrowLeft: 1, ArrowRight: 1, PageUp: 1, PageDown: 1, Home: 1, End: 1, " ": 1, Spacebar: 1 };
  var SCROLLABLE = { auto: 1, scroll: 1, overlay: 1 };
  var round = function (v) { return Math.round(v * 100) / 100; };

  var overrides = {}; // constants the tester changed
  var shadow = null;
  var recording = false;
  var events = [];
  var t0 = null;
  var nodeIds = null, nodes = null, nodeCount = 0;
  var steps = [], sampleCount = 0, lastSample = null;
  var panel, els = {};

  // ---------- recording ----------
  function resetRecording() { events = []; t0 = null; nodeIds = new Map(); nodes = {}; nodeCount = 0; }
  resetRecording();

  function inPanel(ev) {
    var p = typeof ev.composedPath === "function" ? ev.composedPath() : [];
    return p.indexOf(panel) !== -1;
  }

  function elementOf(n) {
    while (n && n.nodeType !== 1) n = n.parentNode;
    return n || doc.body;
  }

  function nodeId(el) {
    if (el === doc.documentElement) { snap(el, "html", null); return "html"; }
    if (el === doc.body) { snap(el, "body", "html"); return "body"; }
    if (nodeIds.has(el)) return nodeIds.get(el);
    var id = "n" + (++nodeCount);
    nodeIds.set(el, id);
    var parent = el.parentNode && el.parentNode.nodeType === 1 ? nodeId(el.parentNode) : "body";
    snap(el, id, parent);
    return id;
  }

  function snap(el, id, parent) {
    if (nodes[id]) return;
    if (id === "body") nodeId(doc.documentElement);
    var spec = { parent: parent, tag: el.tagName };
    var role = el.getAttribute && el.getAttribute("role");
    if (role) spec.role = role;
    var ce = el.getAttribute && el.getAttribute("contenteditable");
    if (ce !== null && ce !== undefined && ce !== "false") spec.contenteditable = true;
    if (el.tagName === "DIALOG" && el.open) spec.open = true;
    if (el !== doc.documentElement && el !== doc.body && el.scrollHeight > el.clientHeight + 1) {
      var oy = root.getComputedStyle(el).overflowY;
      if (SCROLLABLE[oy]) spec.scroll = { overflowY: oy, top: el.scrollTop, height: el.scrollHeight, client: el.clientHeight };
    }
    nodes[id] = spec;
  }

  function stamp(ev) {
    if (t0 === null) t0 = ev.timeStamp;
    return round(ev.timeStamp - t0);
  }

  function touchList(list) {
    var out = [];
    for (var i = 0; list && i < list.length; i++) out.push({ x: round(list[i].clientX), y: round(list[i].clientY) });
    return out;
  }

  function record(ev) {
    if (!recording || events.length >= MAX_EVENTS || inPanel(ev)) return;
    var type = ev.type, target = nodeId(elementOf(ev.target)), raw;
    if (type === "wheel") {
      raw = { type: "wheel", t: stamp(ev), target: target, deltaX: ev.deltaX, deltaY: ev.deltaY, deltaMode: ev.deltaMode,
        wheelDeltaY: ev.wheelDeltaY || 0, ctrlKey: ev.ctrlKey, metaKey: ev.metaKey };
    } else if (type === "keydown") {
      if (!NAV_KEYS[ev.key]) return; // never record typed text
      raw = { type: "keydown", t: stamp(ev), target: target, key: ev.key, repeat: ev.repeat, shiftKey: ev.shiftKey,
        ctrlKey: ev.ctrlKey, altKey: ev.altKey, metaKey: ev.metaKey, defaultPrevented: ev.defaultPrevented };
    } else {
      raw = { type: type, t: stamp(ev), target: target, touches: touchList(ev.touches) };
    }
    events.push(raw);
    paint();
  }

  function exportRecording() {
    nodeId(doc.documentElement); nodeId(doc.body);
    var open = doc.querySelectorAll("dialog[open]"); // the detector suppresses keys while any dialog is open
    for (var i = 0; i < open.length; i++) nodeId(open[i]);
    var vv = root.visualViewport;
    return {
      name: "rec-" + new Date().toISOString().slice(0, 16).replace(/[-:T]/g, ""),
      synthetic: false,
      env: { consumer: { mode: "intercept" }, enabled: true, innerHeight: root.innerHeight, pinHeight: root.innerHeight,
        visualScale: vv && vv.scale ? vv.scale : 1 },
      config: JSON.parse(JSON.stringify(overrides)),
      events: events.slice(),
      nodes: JSON.parse(JSON.stringify(nodes))
    };
  }

  // ---------- shadow detector: read-only copies of the page's input ----------
  function copyEvent(ev) {
    var c = {
      type: ev.type, timeStamp: ev.timeStamp, target: ev.target, cancelable: false, defaultPrevented: false,
      preventDefault: function () {}, composedPath: function () { return ev.composedPath(); }
    };
    var k, names = ["deltaX", "deltaY", "deltaMode", "wheelDeltaY", "ctrlKey", "metaKey", "shiftKey", "altKey", "key", "repeat"];
    for (var i = 0; i < names.length; i++) { k = names[i]; if (k in ev) c[k] = ev[k]; }
    if (ev.touches) { c.touches = ev.touches; c.changedTouches = ev.changedTouches; }
    return c;
  }

  function fakeTarget() {
    var map = [];
    return {
      document: doc,
      get innerHeight() { return root.innerHeight; },
      get visualViewport() { return root.visualViewport; },
      getComputedStyle: function (el) { return root.getComputedStyle(el); },
      addEventListener: function (type, fn) {
        var w = function (ev) { if (!inPanel(ev)) fn(copyEvent(ev)); };
        map.push([type, fn, w]);
        root.addEventListener(type, w, { passive: true, capture: true });
      },
      removeEventListener: function (type, fn) {
        for (var i = map.length - 1; i >= 0; i--) {
          if (map[i][0] === type && map[i][1] === fn) {
            root.removeEventListener(type, map[i][2], { capture: true });
            map.splice(i, 1);
          }
        }
      }
    };
  }

  function buildShadow() {
    if (shadow) shadow.detach();
    shadow = FE.createSequence({
      config: overrides,
      onStep: function (dir, src, info) {
        steps.unshift({ dir: dir, src: src, trigger: info.trigger, cls: info.cls || "", t: round(info.t) });
        if (steps.length > 12) steps.pop();
        paint();
      },
      onJump: function (target, src, info) {
        steps.unshift({ dir: 0, src: src, trigger: "jump " + target, cls: "", t: round(info.t) });
        if (steps.length > 12) steps.pop();
        paint();
      },
      onSample: function (s) { sampleCount++; lastSample = { dy: round(s.dy), cls: s.cls, gesture: s.gesture, decision: s.decision }; paint(); },
      pinHeight: function () { return root.innerHeight; }
    });
    shadow.attach(fakeTarget());
  }

  // ---------- panel ----------
  var CSS = [
    "#ci-tune{position:fixed;right:12px;bottom:12px;z-index:2147483000;width:300px;max-height:80vh;overflow:auto;",
    "font:12px/1.35 ui-monospace,Menlo,monospace;color:var(--text-0,CanvasText);background:var(--bg-3,Canvas);",
    "border:1px solid var(--line-2,GrayText);border-radius:8px;padding:10px;box-sizing:border-box}",
    "#ci-tune h2{font:inherit;font-weight:700;margin:0 0 6px}",
    "#ci-tune button{font:inherit;margin:0 4px 4px 0;padding:2px 8px;cursor:pointer}",
    "#ci-tune label{display:flex;justify-content:space-between;gap:8px;align-items:center;margin:2px 0}",
    "#ci-tune input{width:72px;font:inherit}",
    "#ci-tune .tuned{font-weight:700;color:var(--accent,Highlight)}",
    "#ci-tune pre{margin:4px 0;white-space:pre-wrap}"
  ].join("");

  function el(tag, props, kids) {
    var e = doc.createElement(tag), k;
    for (k in props || {}) e[k] = props[k];
    for (var i = 0; kids && i < kids.length; i++) e.appendChild(kids[i]);
    return e;
  }

  function buildPanel() {
    doc.head.appendChild(el("style", { textContent: CSS }));
    panel = el("div", { id: "ci-tune" });
    panel.setAttribute("data-ci-tune", "");
    // buttons give focus back to the page, so the next key press is the page's (and gets recorded)
    panel.addEventListener("click", function (e) { if (e.target && e.target.tagName === "BUTTON") e.target.blur(); });
    panel.appendChild(el("h2", { textContent: "checkpoint tune (dev) v" + FE.CONFIG_VERSION }));
    els.rec = el("button", { type: "button", textContent: "Record", onclick: function () { recording ? stopRecording() : startRecording(); } });
    els.clear = el("button", { type: "button", textContent: "Clear", onclick: function () { clear(); } });
    els.exp = el("button", { type: "button", textContent: "Export", onclick: download });
    els.copy = el("button", { type: "button", textContent: "Copy", onclick: copy });
    els.reset = el("button", { type: "button", textContent: "Reset values", onclick: function () { overrides = {}; syncInputs(); buildShadow(); paint(); } });
    panel.appendChild(el("div", {}, [els.rec, els.clear, els.exp, els.copy, els.reset]));
    els.status = el("pre", { id: "ci-tune-status" });
    els.steps = el("pre", { id: "ci-tune-steps" });
    panel.appendChild(els.status);
    panel.appendChild(els.steps);
    els.inputs = {};
    var d = FE.DEFAULTS;
    Object.keys(d).forEach(function (key) {
      var inp = el("input", { type: "number", step: "any", value: String(d[key]) });
      inp.setAttribute("data-key", key);
      inp.addEventListener("change", function () {
        var v = parseFloat(inp.value);
        if (isFinite(v) && v !== d[key]) overrides[key] = v; else delete overrides[key];
        buildShadow(); paint();
      });
      els.inputs[key] = inp;
      var lab = el("label", {}, [el("span", { textContent: key }), inp]);
      lab.firstChild.setAttribute("data-label", key);
      panel.appendChild(lab);
    });
    doc.body.appendChild(panel);
  }

  function syncInputs() {
    Object.keys(els.inputs).forEach(function (k) { els.inputs[k].value = String(k in overrides ? overrides[k] : FE.DEFAULTS[k]); });
  }

  function paint() {
    if (!panel) return;
    els.rec.textContent = recording ? "Stop" : "Record";
    els.status.textContent = (recording ? "REC " : "idle ") + events.length + " events" +
      (events.length >= MAX_EVENTS ? " (full)" : "") +
      "\nlast wheel: " + (lastSample ? lastSample.dy + " px " + lastSample.cls + " g" + lastSample.gesture + " " + lastSample.decision : "-") +
      "\nsamples: " + sampleCount;
    els.steps.textContent = steps.length ? steps.map(function (s) {
      return (s.dir > 0 ? "+1" : s.dir < 0 ? "-1" : " 0") + " " + s.src + " " + s.trigger + (s.cls ? " " + s.cls : "") + " @" + s.t;
    }).join("\n") : "steps: -";
    Object.keys(els.inputs).forEach(function (k) {
      els.inputs[k].parentNode.firstChild.className = k in overrides ? "tuned" : "";
    });
  }

  function startRecording() { recording = true; paint(); }
  function stopRecording() { recording = false; paint(); }
  function clear() { resetRecording(); steps = []; sampleCount = 0; lastSample = null; paint(); }

  function recordingText() { return JSON.stringify(exportRecording(), null, 1) + "\n"; }

  function download() { // the only way data leaves the page, with Copy: a local file, no request
    var rec = exportRecording();
    var url = root.URL.createObjectURL(new root.Blob([recordingText()], { type: "application/json" }));
    var a = el("a", { href: url, download: rec.name + ".json" });
    a.style.display = "none";
    doc.body.appendChild(a);
    a.click();
    doc.body.removeChild(a);
    root.setTimeout(function () { root.URL.revokeObjectURL(url); }, 1000);
  }

  function copy() {
    var text = recordingText();
    if (root.navigator && root.navigator.clipboard && root.navigator.clipboard.writeText) root.navigator.clipboard.writeText(text).catch(function () {});
  }

  // ---------- start ----------
  function start() {
    buildPanel();
    buildShadow();
    ["wheel", "keydown", "touchstart", "touchmove", "touchend", "touchcancel"].forEach(function (t) {
      root.addEventListener(t, record, { passive: true, capture: true });
    });
    paint();
  }

  root.__ciTune = {
    exportRecording: exportRecording, startRecording: startRecording, stopRecording: stopRecording, clear: clear,
    state: function () { return { recording: recording, events: events.length, overrides: JSON.parse(JSON.stringify(overrides)), steps: steps.slice() }; }
  };

  if (doc.body) start();
  else doc.addEventListener("DOMContentLoaded", start);
})(typeof globalThis !== "undefined" ? globalThis : this);
