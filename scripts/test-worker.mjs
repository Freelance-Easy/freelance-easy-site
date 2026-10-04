// Offline test of the site Worker's analytics switch and event contract.
// Loads worker.js twice (as shipped: off; and with a fake script id: on),
// mocks fetch/caches/ASSETS, and checks what would leave the site. Nothing
// touches the network. Run from the repo root (Node 20+):
//   node scripts/test-worker.mjs
//   node scripts/test-worker.mjs --payloads <captured.json>
// The second form runs events captured from Plausible's real browser script
// (scripts/check-download-wiring.py --tracker) through the Worker as if they
// came from production, and fails if any is dropped. Expects the shipped
// worker.js to be OFF (REPLACE_ME): on the switch day, run it before putting
// the real id in.
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const args = process.argv.slice(2);
const payloadsAt = args.indexOf("--payloads");
const payloadFile = payloadsAt >= 0 ? args[payloadsAt + 1] : null;
const SRC = args.find((a, i) => !a.startsWith("--") && i !== payloadsAt + 1) || fileURLToPath(new URL("../worker.js", import.meta.url));
const dir = mkdtempSync(join(tmpdir(), "fe-worker-"));
const src = readFileSync(SRC, "utf8");
assert.ok(src.includes("pa-REPLACE_ME.js"), "shipped worker must be OFF");
writeFileSync(join(dir, "worker-off.mjs"), src);
writeFileSync(join(dir, "worker-on.mjs"), src.replace("pa-REPLACE_ME.js", "pa-TESTID123.js"));

const upstream = [];
globalThis.fetch = async (url, init = {}) => {
  upstream.push({ url: String(url), init });
  return new Response("/* plausible */", { status: 200 });
};
globalThis.caches = { default: { match: async () => undefined, put: async () => {} } };
const ctx = { waitUntil: () => {} };
const assets = [];
const env = { ASSETS: { fetch: async (r) => { assets.push(r.url); return new Response("asset"); } } };
const off = await import(pathToFileURL(join(dir, "worker-off.mjs")).href);
const on = await import(pathToFileURL(join(dir, "worker-on.mjs")).href);

const PROD = "https://freelance-easy.com";
const PREVIEW = "https://feat-analytics-switch-freelance-easy-site.lively-breeze-6443.workers.dev";
const E = PROD + "/api/event";
const BASE_HEADERS = { "cf-connecting-ip": "203.0.113.7", "user-agent": "UA", "content-type": "text/plain;charset=UTF-8", cookie: "a=b" };

function post(url, body, headers = {}) {
  return new Request(url, { method: "POST", headers: { ...BASE_HEADERS, ...headers }, body });
}
function get(url) {
  return new Request(url);
}
async function run(worker, request) {
  upstream.length = 0;
  const res = await worker.default.fetch(request, env, ctx);
  return { status: res.status, body: await res.text(), sent: upstream.slice() };
}

// ---- --payloads: real tracker events must all pass -------------------------
if (payloadFile) {
  const payloads = JSON.parse(readFileSync(payloadFile, "utf8"));
  let failed = 0;
  for (const raw of payloads) {
    // As if sent from production: the page URL on our host, our domain.
    const p = JSON.parse(raw);
    const u = new URL(p.u);
    p.u = PROD + u.pathname + u.search;
    p.d = "freelance-easy.com";
    const r = await run(on, post(E, JSON.stringify(p)));
    const ok = r.sent.length === 1;
    if (!ok) failed++;
    const fwd = ok ? JSON.parse(r.sent[0].init.body) : null;
    console.log(`${ok ? "ok  " : "DROP"} ${p.n}  sent keys: ${JSON.stringify(Object.keys(p))}  forwarded: ${JSON.stringify(fwd)}`);
  }
  console.log(failed ? `${failed} of ${payloads.length} real events DROPPED` : `ALL ${payloads.length} real events forwarded`);
  process.exit(failed ? 1 : 0);
}

// ---- the contract ----------------------------------------------------------
const results = [];
async function check(label, worker, request, expect) {
  const r = await run(worker, request);
  if ("status" in expect) assert.equal(r.status, expect.status, `${label}: status`);
  if ("upstream" in expect) assert.deepEqual(r.sent.map((s) => s.url), expect.upstream, `${label}: upstream`);
  results.push(`ok  ${label}  -> ${r.status} upstream=${JSON.stringify(r.sent.map((s) => s.url))}`);
  return r;
}
const FWD = { status: 200, upstream: ["https://plausible.io/api/event"] };
const DROP = { status: 202, upstream: [] };
const pv = (extra = {}) => JSON.stringify({ n: "pageview", u: PROD + "/mac?utm_campaign=f1", d: "freelance-easy.com", r: null, v: 30, ...extra });
const dl = (p, extra = {}) => JSON.stringify({ n: "Download Click", u: PROD + "/mac", d: "freelance-easy.com", r: null, v: 30, p, ...extra });
const DLP = { os: "mac", campaign: "f1", page: "mac", placement: "hero" };

// The switch and the hosts.
await check("OFF prod script", off, get(PROD + "/js/script.js"), { status: 200, upstream: [] });
await check("OFF prod event", off, post(E, pv()), DROP);
await check("ON preview script", on, get(PREVIEW + "/js/script.js"), { status: 200, upstream: [] });
await check("ON preview event", on, post(PREVIEW + "/api/event", pv()), DROP);
await check("ON localhost event", on, post("http://localhost:8791/api/event", pv()), DROP);
await check("ON prod script", on, get(PROD + "/js/script.js"), { status: 200, upstream: ["https://plausible.io/js/pa-TESTID123.js"] });
await check("ON www script", on, get("https://www.freelance-easy.com/js/script.js"), { status: 200, upstream: ["https://plausible.io/js/pa-TESTID123.js"] });

// What is forwarded, and how.
const r1 = await check("ON pageview forwarded", on, post(E, pv()), FWD);
const h = r1.sent[0].init.headers;
assert.equal(h.get("cookie"), null, "no cookie forwarded");
assert.equal(h.get("x-forwarded-for"), "203.0.113.7");
assert.equal(h.get("user-agent"), "UA");
assert.equal(h.get("content-type"), "text/plain", "always text/plain upstream");
assert.equal(r1.sent[0].init.body, pv(), "canonical rebuilt body");
results.push("ok  forwarded: x-forwarded-for + user-agent, text/plain, no cookie, canonical body");
await check("ON engagement forwarded", on, post(E, JSON.stringify({ n: "engagement", sd: 80, d: "freelance-easy.com", u: PROD + "/", p: {}, e: 4000, v: 30 })), FWD);
const r2 = await check("ON Download Click forwarded", on, post(E, dl(DLP)), FWD);
assert.deepEqual(JSON.parse(r2.sent[0].init.body).p, DLP);
await check("ON application/json accepted", on, post(E, pv(), { "content-type": "application/json" }), FWD);

// Off-contract events and properties.
await check("ON engagement with props dropped", on, post(E, JSON.stringify({ n: "engagement", sd: 1, e: 1, d: "freelance-easy.com", u: PROD + "/", p: { who: "x" } })), DROP);
await check("ON Download Click extra prop dropped", on, post(E, dl({ ...DLP, email: "x@y.z" })), DROP);
await check("ON Download Click non-string prop dropped", on, post(E, dl({ ...DLP, os: { a: 1 } })), DROP);
await check("ON Download Click array props dropped", on, post(E, dl(["os"])), DROP);
await check("ON pageview with props dropped", on, post(E, pv({ p: { plan: "x" } })), DROP);
await check("ON __proto__ prop dropped", on, post(E, '{"n":"Download Click","u":"' + PROD + '/","d":"freelance-easy.com","p":{"__proto__":{"x":1}}}'), DROP);
await check("ON unknown event dropped", on, post(E, JSON.stringify({ n: "Share To Computer", u: PROD + "/", d: "freelance-easy.com" })), DROP);
await check("ON outbound link event dropped", on, post(E, JSON.stringify({ n: "Outbound Link: Click", u: PROD + "/", d: "freelance-easy.com", p: { url: "https://x" } })), DROP);
await check("ON 'name' instead of 'n' dropped", on, post(E, JSON.stringify({ name: "pageview", url: PROD + "/", domain: "freelance-easy.com" })), DROP);
await check("ON duplicate n (last wins: unknown) dropped", on, post(E, '{"n":"pageview","u":"' + PROD + '/","d":"freelance-easy.com","n":"Share To Computer"}'), DROP);
await check("ON other page host dropped", on, post(E, pv({ u: "https://evil.example/x" })), DROP);
await check("ON other domain dropped", on, post(E, pv({ d: "evil.example" })), DROP);
await check("ON revenue dropped from copy", on, post(E, dl(DLP, { $: { amount: 5 } })), FWD);
// Sol re-check P1: legacy property aliases never reach Plausible.
const r3 = await check("ON legacy m/meta/props aliases stripped", on, post(E, pv({ p: {}, m: { email: "x@y.z" }, meta: { email: "x@y.z" }, props: { email: "x@y.z" } })), FWD);
assert.ok(!/email|"m"|"meta"|"props"|"\$"/.test(r3.sent[0].init.body), "no alias or revenue in the forwarded copy");
results.push("ok  the forwarded copy carries no m/meta/props/$ field");
// Sol re-check P1: content types Plausible would read differently.
await check("ON form-urlencoded dropped", on, post(E, pv({ u: PROD + "/?&n=Share%20To%20Computer&p[email]=x" }), { "content-type": "application/x-www-form-urlencoded" }), DROP);
await check("ON multipart dropped", on, post(E, pv(), { "content-type": "multipart/form-data; boundary=x" }), DROP);
await check("ON missing content-type dropped", on, new Request(E, { method: "POST", body: new Blob([pv()]) }), DROP);
// Sol re-check P2: the size cap is in bytes and bounds reading.
await check("ON malformed body dropped", on, post(E, "not json"), DROP);
await check("ON unicode body over 8192 bytes dropped", on, post(E, pv({ r: "é".repeat(4500) })), DROP);
await check("ON invalid UTF-8 dropped", on, post(E, new Uint8Array([0x7b, 0xff, 0xfe, 0x7d])), DROP);
let pulled = 0;
const big = new ReadableStream({
  pull(c) {
    pulled++;
    if (pulled > 512) return c.close();
    c.enqueue(new Uint8Array(4096).fill(32));
  },
});
await check("ON streamed 2 MiB body dropped", on, new Request(E, { method: "POST", headers: { "content-type": "text/plain" }, body: big, duplex: "half" }), DROP);
assert.ok(pulled <= 4, `reading stopped at the cap (pulled ${pulled} chunks)`);
results.push(`ok  the streamed body was cut off after ${pulled} chunk(s), not read to the end`);

// Everything else goes to the site's files.
await check("ON prod GET /api/event", on, get(E), { status: 200, upstream: [] });
await check("ON prod page", on, get(PROD + "/mac"), { status: 200, upstream: [] });
assert.ok(assets.includes(PROD + "/mac"), "pages go to ASSETS");
results.push("ok  pages and a GET to /api/event go to the site's files");
console.log(results.join("\n"));
console.log(`ALL PASS (${results.length} checks)`);
