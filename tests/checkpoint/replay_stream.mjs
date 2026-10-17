#!/usr/bin/env node
// FLICKER: replay wheel streams through assets/shared/checkpoint-input.js and print the steps it emits.
//   echo '[{"events": [{"t": 0, "deltaY": 3}, ...]}, ...]' | node tests/checkpoint/replay_stream.mjs
//   -> [[[sign, t, trigger], ...], ...]   (one list of steps per stream, in order)
// Deterministic like run_detector.mjs: a fresh VM context per stream, time = each event's own t (ev.timeStamp).
// An event may carry wheelDeltaY and deltaMode; by default a trackpad's (deltaMode 0, wheelDeltaY = -1.2 * deltaY).
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const MODULE = path.join(ROOT, "assets", "shared", "checkpoint-input.js");
const SRC = fs.readFileSync(MODULE, "utf8");

function replay(events) {
  const sb = {};
  vm.createContext(sb);
  vm.runInContext(SRC, sb, { filename: MODULE });
  const steps = [], hs = {};
  const win = { addEventListener: (type, fn) => { hs[type] = fn; }, removeEventListener() {}, innerHeight: 800, document: null };
  const seq = sb.FECheckpoint.createSequence({ onStep: (s, src, info) => steps.push([s, Math.round(info.t), info.trigger]) });
  seq.attach(win);
  for (const e of events) {
    hs.wheel({ type: "wheel", deltaY: e.deltaY, deltaX: 0, deltaMode: e.deltaMode || 0,
      wheelDeltaY: e.wheelDeltaY != null ? e.wheelDeltaY : -Math.round(e.deltaY * 1.2), timeStamp: e.t,
      ctrlKey: false, metaKey: false, cancelable: true, preventDefault() {}, composedPath() { return []; }, target: null });
  }
  return steps;
}

const streams = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(streams.map((s) => replay(s.events))) + "\n");
