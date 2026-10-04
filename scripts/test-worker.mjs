// Offline test of the site Worker's analytics switch and event contract.
// Loads worker.js twice (as shipped: off; and with a fake script id: on),
// mocks fetch/caches/ASSETS, and checks what would leave the site. Nothing
// touches the network. Run from the repo root: node scripts/test-worker.mjs
// (Node 20+). Expects the shipped worker.js to be OFF (REPLACE_ME): on the
// switch day, run it before putting the real id in.
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const SRC = process.argv[2] || fileURLToPath(new URL("../worker.js", import.meta.url));
const dir = mkdtempSync(join(tmpdir(), "fe-worker-"));
const src = readFileSync(SRC, "utf8");
writeFileSync(join(dir, "worker-off.mjs"), src);
writeFileSync(join(dir, "worker-on.mjs"), src.replace("pa-REPLACE_ME.js", "pa-TESTID123.js"));
assert.ok(src.includes("pa-REPLACE_ME.js"), "shipped worker must be OFF");

const upstream = [];
globalThis.fetch = async (url, init = {}) => {
  upstream.push({ url: String(url), init });
  return new Response("/* plausible script */", { status: 200 });
};
const cachePuts = [];
globalThis.caches = { default: { match: async () => undefined, put: async (k) => cachePuts.push(k.url) } };
const ctx = { waitUntil: () => {} };
const assets = [];
const env = { ASSETS: { fetch: async (r) => { assets.push(r.url); return new Response("asset"); } } };

function req(url, method = "GET", headers = {}, body = '{"n":"pageview","u":"https://freelance-easy.com/","d":"freelance-easy.com"}') {
  return new Request(url, { method, headers, body: method === "POST" ? body : undefined });
}
const PROD = "https://freelance-easy.com";
const PREVIEW = "https://feat-analytics-switch-freelance-easy-site.lively-breeze-6443.workers.dev";
const results = [];
async function check(label, worker, request, expect) {
  upstream.length = 0;
  const res = await worker.default.fetch(request, env, ctx);
  const body = await res.text();
  const got = { status: res.status, upstream: upstream.map((u) => u.url), body: body.slice(0, 30) };
  for (const [k, v] of Object.entries(expect)) assert.deepEqual(got[k], v, `${label}: ${k}`);
  results.push(`ok  ${label}  -> ${res.status} upstream=${JSON.stringify(got.upstream)}`);
  return { res, sent: upstream.slice() };
}

const off = await import(pathToFileURL(join(dir, "worker-off.mjs")).href);
const on = await import(pathToFileURL(join(dir, "worker-on.mjs")).href);
const hdrs = { cookie: "a=b", "cf-connecting-ip": "203.0.113.7", "user-agent": "UA", "content-type": "text/plain" };

await check("OFF prod script", off, req(PROD + "/js/script.js"), { status: 200, upstream: [] });
await check("OFF prod event", off, req(PROD + "/api/event", "POST", hdrs), { status: 202, upstream: [] });
await check("OFF preview event", off, req(PREVIEW + "/api/event", "POST", hdrs), { status: 202, upstream: [] });
await check("ON preview script", on, req(PREVIEW + "/js/script.js"), { status: 200, upstream: [] });
await check("ON preview event", on, req(PREVIEW + "/api/event", "POST", hdrs), { status: 202, upstream: [] });
await check("ON localhost event", on, req("http://localhost:8791/api/event", "POST", hdrs), { status: 202, upstream: [] });
await check("ON prod script", on, req(PROD + "/js/script.js"), { status: 200, upstream: ["https://plausible.io/js/pa-TESTID123.js"] });
await check("ON www script", on, req("https://www.freelance-easy.com/js/script.js"), { status: 200, upstream: ["https://plausible.io/js/pa-TESTID123.js"] });
const ev = await check("ON prod event", on, req(PROD + "/api/event", "POST", hdrs), { status: 200, upstream: ["https://plausible.io/api/event"] });
const fwd = ev.sent[0].init.headers;
assert.equal(fwd.get("cookie"), null, "cookie must not be forwarded");
assert.equal(fwd.get("x-forwarded-for"), "203.0.113.7");
assert.equal(fwd.get("user-agent"), "UA");
results.push("ok  ON prod event forwards x-forwarded-for + user-agent, no cookie");
// The event contract: only what /privacy lists is forwarded.
const E = PROD + "/api/event";
const dl = (p) => JSON.stringify({ n: "Download Click", u: PROD + "/mac", d: "freelance-easy.com", p });
await check("ON engagement forwarded (§3 lists it)", on, req(E, "POST", hdrs, JSON.stringify({ n: "engagement", sd: 80, e: 4000, u: PROD + "/", d: "freelance-easy.com", p: {} })), { status: 200, upstream: ["https://plausible.io/api/event"] });
await check("ON engagement with props dropped", on, req(E, "POST", hdrs, JSON.stringify({ n: "engagement", sd: 80, e: 4000, p: { who: "x" } })), { status: 202, upstream: [] });
await check("ON Download Click (4 props) forwarded", on, req(E, "POST", hdrs, dl({ os: "mac", campaign: "f1", page: "mac", placement: "hero" })), { status: 200, upstream: ["https://plausible.io/api/event"] });
await check("ON Download Click extra prop dropped", on, req(E, "POST", hdrs, dl({ os: "mac", campaign: "f1", page: "mac", placement: "hero", email: "x@y.z" })), { status: 202, upstream: [] });
await check("ON Download Click array props dropped", on, req(E, "POST", hdrs, dl(["os"])), { status: 202, upstream: [] });
await check("ON pageview with props dropped", on, req(E, "POST", hdrs, JSON.stringify({ n: "pageview", u: PROD + "/", p: { plan: "x" } })), { status: 202, upstream: [] });
await check("ON unknown event dropped", on, req(E, "POST", hdrs, JSON.stringify({ n: "Share To Computer", p: { how: "copy" } })), { status: 202, upstream: [] });
await check("ON outbound link event dropped", on, req(E, "POST", hdrs, JSON.stringify({ n: "Outbound Link: Click", p: { url: "https://x" } })), { status: 202, upstream: [] });
await check("ON malformed body dropped", on, req(E, "POST", hdrs, "not json"), { status: 202, upstream: [] });
await check("ON oversize body dropped", on, req(E, "POST", hdrs, JSON.stringify({ n: "pageview", pad: "x".repeat(9000) })), { status: 202, upstream: [] });
await check("ON 'name' key pageview forwarded", on, req(E, "POST", hdrs, JSON.stringify({ name: "pageview", url: PROD + "/", domain: "freelance-easy.com" })), { status: 200, upstream: ["https://plausible.io/api/event"] });
const fw = await check("ON forwarded body unchanged", on, req(E, "POST", hdrs, dl({ os: "win", campaign: "site", page: "home", placement: "hero" })), { status: 200 });
assert.equal(fw.sent[0].init.body, dl({ os: "win", campaign: "site", page: "home", placement: "hero" }));
results.push("ok  the forwarded body is byte-identical to what the page sent");
await check("ON prod GET event (not POST)", on, req(PROD + "/api/event"), { status: 200, upstream: [] });
await check("ON prod page", on, req(PROD + "/mac"), { status: 200, upstream: [] });
assert.ok(assets.includes(PROD + "/mac"), "pages go to ASSETS");
results.push("ok  pages and a GET to /api/event go to ASSETS");
console.log(results.join("\n"));
console.log("ALL PASS");
