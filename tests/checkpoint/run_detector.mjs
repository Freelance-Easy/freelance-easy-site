#!/usr/bin/env node
// C1: feed every tests/fixtures/input/*.json through assets/shared/checkpoint-input.js and print what it emitted.
//
//   node tests/checkpoint/run_detector.mjs            -> {"fixtures": {name: {steps, jumps, prevented, trace}}}
//   node tests/checkpoint/run_detector.mjs --config   -> {"CONFIG_VERSION": 1, "DEFAULTS": {...}}
//
// Deterministic: fixtures in sorted order, a fresh VM context (fresh module state) per fixture, time = the fixture's
// own ev.timeStamp, stable key order. Two runs give byte-identical output. The module is loaded the way a page loads
// it (a classic script that sets FECheckpoint on its global), and driven only through its public API:
// createSequence({config, onStep, onJump, isBypassed, onSample, pinHeight}) -> attach(el) / setEnabled / detach.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const MODULE = path.join(ROOT, "assets", "shared", "checkpoint-input.js");
const FIXTURES = path.join(ROOT, "tests", "fixtures", "input");

function load() {
  const src = fs.readFileSync(MODULE, "utf8");
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox, { filename: MODULE });
  if (!sandbox.FECheckpoint) throw new Error("checkpoint-input.js did not define FECheckpoint");
  return sandbox.FECheckpoint;
}

// ---------- a fake DOM: just enough for the module's checks, driven by the fixture's "nodes" ----------
function makeDom(fx) {
  const listeners = {};
  const view = {
    innerHeight: fx.env.innerHeight,
    visualViewport: { scale: fx.env.visualScale },
    getComputedStyle: (el) => ({ overflowY: (el._scroll && el._scroll.overflowY) || "visible" }),
    addEventListener(type, fn, opts) { (listeners[type] = listeners[type] || []).push({ fn, opts }); },
    removeEventListener(type, fn) { listeners[type] = (listeners[type] || []).filter((l) => l.fn !== fn); },
  };
  const doc = { nodeType: 9, defaultView: view };
  view.document = doc;
  const els = {};
  for (const id of Object.keys(fx.nodes).sort()) {
    const s = fx.nodes[id];
    els[id] = {
      nodeType: 1, id, tagName: s.tag, ownerDocument: doc, open: !!s.open, _spec: s, _scroll: s.scroll || null,
      scrollTop: s.scroll ? s.scroll.top : 0, scrollHeight: s.scroll ? s.scroll.height : 0,
      clientHeight: s.scroll ? s.scroll.client : 0,
      getAttribute(n) {
        if (n === "role") return s.role || null;
        if (n === "contenteditable") return s.contenteditable ? "true" : null;
        if (n === "open") return s.open ? "" : null;
        return null;
      },
      hasAttribute(n) { return this.getAttribute(n) !== null; },
    };
  }
  for (const id of Object.keys(els)) {
    const e = els[id];
    e.parentNode = e._spec.parent ? els[e._spec.parent] : doc;
  }
  for (const id of Object.keys(els)) {
    let ce = false;
    for (let n = els[id]; n && n.nodeType === 1; n = n.parentNode) if (n._spec.contenteditable) ce = true;
    els[id].isContentEditable = ce;
  }
  doc.documentElement = els.html;
  doc.body = els.body;
  doc.querySelector = (sel) => {
    if (sel !== "dialog[open]") throw new Error("fake DOM: unsupported selector " + sel);
    for (const id of Object.keys(els).sort()) if (els[id].tagName === "DIALOG" && els[id].open) return els[id];
    return null;
  };
  const dispatch = (ev) => { for (const l of (listeners[ev.type] || []).slice()) l.fn(ev); };
  return { view, doc, els, dispatch, listeners };
}

function makeEvent(raw, i, dom) {
  const target = dom.els[raw.target || "body"];
  const ev = {
    type: raw.type, timeStamp: raw.t, target, defaultPrevented: !!raw.defaultPrevented, _ours: false, _i: i,
    preventDefault() { this.defaultPrevented = true; this._ours = true; },
    composedPath() {
      const p = [];
      for (let n = target; n; n = n.parentNode) p.push(n);
      p.push(dom.view);
      return p;
    },
  };
  if (raw.type === "wheel") {
    Object.assign(ev, { deltaY: raw.deltaY, deltaX: raw.deltaX, deltaMode: raw.deltaMode, wheelDeltaY: raw.wheelDeltaY,
      ctrlKey: raw.ctrlKey, metaKey: raw.metaKey, shiftKey: false, altKey: false });
  } else if (raw.type === "keydown") {
    Object.assign(ev, { key: raw.key, shiftKey: raw.shiftKey, ctrlKey: raw.ctrlKey, altKey: raw.altKey,
      metaKey: raw.metaKey, repeat: raw.repeat });
  } else {
    const touches = raw.touches.map((p, k) => ({ clientX: p.x, clientY: p.y, identifier: k }));
    Object.assign(ev, { touches, changedTouches: touches });
  }
  return ev;
}

function runFixture(name) {
  const fx = JSON.parse(fs.readFileSync(path.join(FIXTURES, name + ".json"), "utf8"));
  const FE = load();
  const dom = makeDom(fx);
  const out = { steps: [], jumps: [], prevented: [], trace: [] };
  const c = fx.env.consumer;
  const seq = FE.createSequence({
    config: fx.config, // C7: a recording made with tuned thresholds replays with them (absent = DEFAULTS)
    onStep: (dir, src, info) => out.steps.push({ dir, src, t: info.t, trigger: info.trigger, gesture: info.gesture }),
    onJump: (target, src, info) => out.jumps.push({ target, src, t: info.t }),
    isBypassed: (ev) => (c.mode === "pass" ? true : c.mode === "takeover" ? ev.timeStamp < c.at : false),
    onSample: (s) => { if (s.source === "wheel") out.trace.push({ i: s.event._i, gesture: s.gesture, cls: s.cls }); },
    pinHeight: () => fx.env.pinHeight,
  });
  seq.attach(dom.view);
  if (!fx.env.enabled) seq.setEnabled(false);
  fx.events.forEach((raw, i) => {
    const ev = makeEvent(raw, i, dom);
    dom.dispatch(ev);
    if (ev._ours) out.prevented.push(i);
  });
  seq.detach();
  const left = Object.values(dom.listeners).reduce((n, l) => n + l.length, 0);
  if (left) throw new Error(name + ": detach() left " + left + " listeners");
  return out;
}

function stable(v) {
  if (Array.isArray(v)) return v.map(stable);
  if (v && typeof v === "object") return Object.fromEntries(Object.keys(v).sort().map((k) => [k, stable(v[k])]));
  return v;
}

if (process.argv.includes("--config")) {
  const FE = load();
  process.stdout.write(JSON.stringify(stable({ CONFIG_VERSION: FE.CONFIG_VERSION, DEFAULTS: FE.DEFAULTS })) + "\n");
} else {
  const names = fs.readdirSync(FIXTURES).filter((f) => f.endsWith(".json")).map((f) => f.slice(0, -5)).sort();
  const fixtures = {};
  for (const n of names) fixtures[n] = runFixture(n);
  process.stdout.write(JSON.stringify(stable({ fixtures })) + "\n");
}
