// Offline test of the site Worker's analytics switch and event contract.
// Loads worker.js twice (as shipped: off; and with a fake script id: on),
// mocks fetch/caches/ASSETS, and checks what would leave the site. Nothing
// touches the network. Run from the repo root (Node 20+):
//   node scripts/test-worker.mjs
//   node scripts/test-worker.mjs --payloads <captured.json> [--substitute-domain]
// The first form is the full suite; it expects the shipped worker.js to be
// OFF (REPLACE_ME), so on the switch day run it before putting the real id in.
// The second runs events captured from a real Plausible script
// (scripts/check-download-wiring.py --tracker) through the Worker, switched on
// (as it is, or with a test id while it's still off), as if they came from
// production, and fails if any is dropped. Each captured event is replayed
// with its own content type; its page URL moves to production (the capture
// ran on a preview) but its domain (d) is kept, unless --substitute-domain
// says the script was another site's (Plausible's own public one).
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const args = process.argv.slice(2);
const payloadsAt = args.indexOf("--payloads");
const payloadFile = payloadsAt >= 0 ? args[payloadsAt + 1] : null;
const substituteDomain = args.includes("--substitute-domain");
const SRC = args.find((a, i) => !a.startsWith("--") && (payloadsAt < 0 || i !== payloadsAt + 1)) || fileURLToPath(new URL("../worker.js", import.meta.url));
const dir = mkdtempSync(join(tmpdir(), "fe-worker-"));
const src = readFileSync(SRC, "utf8");
if (!payloadFile) assert.ok(src.includes("pa-REPLACE_ME.js"), "shipped worker must be OFF");
writeFileSync(join(dir, "worker-off.mjs"), src);
writeFileSync(join(dir, "worker-on.mjs"), src.replace("pa-REPLACE_ME.js", "pa-TESTID123.js"));

const upstream = [];
let github = null; // the GitHub Releases stand-in for the download tests
globalThis.fetch = async (url, init = {}) => {
  upstream.push({ url: String(url), init });
  if (github && String(url).startsWith("https://github.com/")) return github(String(url), init);
  return new Response("/* plausible */", { status: 200 });
};
// Cache API stand-in: "miss" (default: nothing stored), "store" (a real map), "throw".
let cacheMode = "miss";
const cacheStore = new Map();
globalThis.caches = {
  default: {
    match: async (req) => {
      if (cacheMode === "throw") throw new Error("cache down");
      if (cacheMode !== "store") return undefined;
      const hit = cacheStore.get(new Request(req).url);
      return hit ? hit.clone() : undefined;
    },
    put: async (req, res) => {
      if (cacheMode === "throw") throw new Error("cache down");
      if (cacheMode === "store") cacheStore.set(new Request(req).url, res.clone());
    },
  },
};
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
  return { status: res.status, headers: res.headers, body: await res.text(), sent: upstream.slice() };
}

// ---- --payloads: real tracker events must all pass -------------------------
if (payloadFile) {
  const payloads = JSON.parse(readFileSync(payloadFile, "utf8"));
  let failed = 0;
  for (const item of payloads) {
    const captured = typeof item === "string" ? { body: item, content_type: "text/plain" } : item;
    // As if sent from production: the page URL moves to our host.
    const p = JSON.parse(captured.body);
    const u = new URL(p.u);
    p.u = PROD + u.pathname + u.search;
    if (substituteDomain) p.d = "freelance-easy.com";
    const r = await run(on, post(E, JSON.stringify(p), { "content-type": captured.content_type || "" }));
    const ok = r.sent.length === 1;
    if (!ok) failed++;
    const fwd = ok ? JSON.parse(r.sent[0].init.body) : null;
    console.log(`${ok ? "ok  " : "DROP"} ${p.n}  (${captured.content_type})  sent keys: ${JSON.stringify(Object.keys(p))}  forwarded: ${JSON.stringify(fwd)}`);
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
// Sol third pass P1: what Plausible parses is the canonical URL that was checked.
const r4 = await check("ON backslash-userinfo URL sent canonical", on, post(E, pv({ u: "https://freelance-easy.com\\@evil.example/x" })), FWD);
assert.equal(JSON.parse(r4.sent[0].init.body).u, "https://freelance-easy.com/@evil.example/x");
results.push("ok  that URL goes on as https://freelance-easy.com/@evil.example/x (host checked = host sent)");
await check("ON URL with credentials dropped", on, post(E, pv({ u: "https://a:b@freelance-easy.com/" })), DROP);
await check("ON javascript: URL dropped", on, post(E, pv({ u: "javascript:alert(1)//freelance-easy.com" })), DROP);
await check("ON http URL accepted", on, post(E, pv({ u: "http://freelance-easy.com/mac" })), FWD);
// Sol third pass P2: a referrer never drops its event.
const longRef = "https://news.example/story?" + "q=1&".repeat(600);
const r5 = await check("ON long referrer kept (cut to origin + path)", on, post(E, pv({ r: longRef })), FWD);
assert.equal(JSON.parse(r5.sent[0].init.body).r, "https://news.example/story");
const r6 = await check("ON app referrer sent as null", on, post(E, pv({ r: "android-app://com.example" })), FWD);
assert.equal(JSON.parse(r6.sent[0].init.body).r, null);
results.push("ok  long and non-http referrers: event kept, referrer cut or nulled");
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

// The Mac download: the DMG itself as a 200 from this domain (worker.js macDownload).
const REL = "https://github.com/Freelance-Easy/InvoiceGenerator-releases/releases";
const LATEST = REL + "/latest/download/Freelance-Easy.dmg";
const VERSIONED = REL + "/download/v0.3.1-beta/Freelance-Easy.dmg";
const DMG_HEADERS = { "content-length": "8", etag: '"e1"', "last-modified": "Mon, 05 Oct 2026 23:26:16 GMT", "content-type": "application/octet-stream" };
function releases({ location = VERSIONED, asset } = {}) {
  return (url, init) => {
    if (url === LATEST) return new Response(null, { status: 302, headers: location ? { location } : {} });
    if (url === VERSIONED) return asset(init);
    return new Response("not found", { status: 404 });
  };
}
const goodAsset = (init) => {
  const range = new Headers(init.headers).get("range");
  if (range === "bytes=0-0") return new Response("D", { status: 206, headers: { ...DMG_HEADERS, "content-length": "1", "content-range": "bytes 0-0/154075165" } });
  if (range === "bytes=999999999-") return new Response("", { status: 416, headers: { "content-range": "bytes */154075165" } });
  return new Response(init.method === "HEAD" ? null : "DMGBYTES", { status: 200, headers: DMG_HEADERS });
};
const DL_OK = { status: 200, upstream: [LATEST, VERSIONED] };
const dlReq = (path, init = {}) => new Request(PROD + path, { headers: { "cf-connecting-ip": "203.0.113.7", "user-agent": "VisitorUA", cookie: "a=b", ...(init.headers || {}) }, method: init.method || "GET" });

github = releases({ asset: goodAsset });
const d1 = await check("DL /dl/mac/f1 streams the DMG as a 200", off, dlReq("/dl/mac/f1?utm_source=google&gclid=abc"), DL_OK);
assert.equal(d1.body, "DMGBYTES");
assert.equal(d1.headers.get("content-type"), "application/x-apple-diskimage");
assert.equal(d1.headers.get("content-disposition"), 'attachment; filename="Freelance-Easy.dmg"');
assert.equal(d1.headers.get("content-length"), "8");
assert.equal(d1.headers.get("etag"), '"e1"');
assert.equal(d1.headers.get("accept-ranges"), "bytes");
for (const s of d1.sent) {
  assert.ok(!/f1|gclid|utm_/.test(s.url), "no label or query string reaches GitHub");
}
// Exactly these headers go to GitHub: anything else (an IP header, a cookie, the visitor's UA) fails here.
assert.deepEqual([...new Headers(d1.sent[0].init.headers).keys()].sort(), ["user-agent"], "resolver sends only our user agent");
assert.deepEqual([...new Headers(d1.sent[1].init.headers).keys()].sort(), ["accept-encoding", "user-agent"], "asset fetch sends only our UA + identity");
assert.equal(new Headers(d1.sent[1].init.headers).get("user-agent"), "freelance-easy-site (download proxy)");
assert.equal(new Headers(d1.sent[1].init.headers).get("accept-encoding"), "identity");
assert.equal(d1.sent[0].init.redirect, "manual", "latest is resolved from GitHub's redirect, not followed");
assert.equal(d1.headers.get("cache-control"), "no-store, no-transform");
results.push("ok  only our UA (+ identity) reaches GitHub: no label, query, cookie, IP header or visitor UA; latest resolved to the tag");
await check("DL /download/mac streams the DMG", off, dlReq("/download/mac"), DL_OK);
await check("DL /dl/mac/site (homepage) streams the DMG", off, dlReq("/dl/mac/site"), DL_OK);
await check("DL works with analytics ON too", on, dlReq("/dl/mac/mac"), DL_OK);
const d2 = await check("DL HEAD: same headers, no body", off, dlReq("/dl/mac/f1", { method: "HEAD" }), DL_OK);
assert.equal(d2.body, "");
assert.equal(d2.headers.get("content-length"), "8");
assert.equal(d2.sent[1].init.method, "HEAD");
const d3 = await check("DL Range passes through as 206", off, dlReq("/dl/mac/f1", { headers: { range: "bytes=0-0" } }), { status: 206, upstream: [LATEST, VERSIONED] });
assert.equal(d3.headers.get("content-range"), "bytes 0-0/154075165");
assert.equal(new Headers(d3.sent[1].init.headers).get("range"), "bytes=0-0", "the Range header is forwarded");
const d3b = await check("DL If-Range is forwarded with Range", off, dlReq("/dl/mac/f1", { headers: { range: "bytes=0-0", "if-range": '"e1"' } }), { status: 206, upstream: [LATEST, VERSIONED] });
assert.equal(new Headers(d3b.sent[1].init.headers).get("if-range"), '"e1"', "the If-Range header is forwarded");
assert.deepEqual([...new Headers(d3b.sent[1].init.headers).keys()].sort(), ["accept-encoding", "if-range", "range", "user-agent"]);
const d4 = await check("DL unsatisfiable Range keeps 416", off, dlReq("/dl/mac/f1", { headers: { range: "bytes=999999999-" } }), { status: 416, upstream: [LATEST, VERSIONED] });
assert.equal(d4.headers.get("content-range"), "bytes */154075165");
for (const code of [404, 403, 500, 503]) {
  github = releases({ asset: () => new Response("<html>error</html>", { status: code }) });
  const r = await check(`DL upstream ${code} keeps its status`, off, dlReq("/dl/mac/f1"), { status: code, upstream: [LATEST, VERSIONED] });
  assert.notEqual(r.headers.get("content-type"), "application/x-apple-diskimage", "an error is never served as a .dmg");
  assert.equal(r.headers.get("content-disposition"), null);
}
github = releases({ location: null, asset: goodAsset });
await check("DL no tag from GitHub -> 502, no asset fetch", off, dlReq("/dl/mac/f1"), { status: 502, upstream: [LATEST] });
github = releases({ location: "https://evil.example/releases/download/../x/Freelance-Easy.dmg", asset: goodAsset });
await check("DL odd redirect target -> 502", off, dlReq("/dl/mac/f1"), { status: 502, upstream: [LATEST] });
// Sol P3: the redirect target must be exactly our repo's asset on github.com.
for (const loc of [
  "https://evil.example/Freelance-Easy/InvoiceGenerator-releases/releases/download/v0.3.1-beta/Freelance-Easy.dmg",
  "https://github.com/someone-else/repo/releases/download/v0.3.1-beta/Freelance-Easy.dmg",
  "http://github.com/Freelance-Easy/InvoiceGenerator-releases/releases/download/v0.3.1-beta/Freelance-Easy.dmg",
  VERSIONED + "?x=1",
]) {
  github = releases({ location: loc, asset: goodAsset });
  await check(`DL redirect to ${loc.slice(0, 40)}… refused -> 502`, off, dlReq("/dl/mac/f1"), { status: 502, upstream: [LATEST] });
}
github = releases({ location: "/Freelance-Easy/InvoiceGenerator-releases/releases/download/v0.3.1-beta/Freelance-Easy.dmg", asset: goodAsset });
await check("DL relative redirect on github.com accepted", off, dlReq("/dl/mac/f1"), DL_OK);
// Sol P2: the resolver's own error status is kept, and a tag is taken only from a redirect.
for (const code of [403, 404, 429, 500, 503]) {
  github = (url, init) => (url === LATEST ? new Response("err", { status: code, headers: { location: VERSIONED } }) : goodAsset(init));
  await check(`DL resolver ${code} keeps its status (no asset fetch)`, off, dlReq("/dl/mac/f1"), { status: code, upstream: [LATEST] });
}
github = (url, init) => (url === LATEST ? new Response(null, { status: 200, headers: { location: VERSIONED } }) : goodAsset(init));
await check("DL resolver 200 with a Location is not a redirect -> 502", off, dlReq("/dl/mac/f1"), { status: 502, upstream: [LATEST] });
github = releases({ asset: () => new Response("gz", { status: 200, headers: { ...DMG_HEADERS, "content-encoding": "gzip" } }) });
await check("DL an encoded upstream body is refused -> 502", off, dlReq("/dl/mac/f1"), { status: 502, upstream: [LATEST, VERSIONED] });
// Sol P2/P3: the tag cache is real (a hit skips the resolver) and a cache failure is a miss.
github = releases({ asset: goodAsset });
cacheMode = "store";
cacheStore.clear();
await check("DL cache: first request resolves and stores the tag", off, dlReq("/dl/mac/f1"), DL_OK);
await new Promise((r) => setTimeout(r, 0));
assert.equal(await cacheStore.get("https://freelance-easy.com/__internal/latest-mac-tag")?.clone().text(), "v0.3.1-beta", "the tag is cached");
assert.match(cacheStore.get("https://freelance-easy.com/__internal/latest-mac-tag").headers.get("cache-control"), /max-age=300/);
await check("DL cache: second request uses the cached tag", off, dlReq("/dl/mac/f1"), { status: 200, upstream: [VERSIONED] });
cacheMode = "throw";
await check("DL cache failure is a miss (still downloads)", off, dlReq("/dl/mac/f1"), DL_OK);
cacheMode = "miss";
results.push("ok  the tag cache stores and hits; a failing cache never blocks the download");
github = releases({ location: REL + "/download/../Freelance-Easy.dmg", asset: goodAsset });
await check("DL a '..' tag is refused -> 502", off, dlReq("/dl/mac/f1"), { status: 502, upstream: [LATEST] });
github = () => { throw new TypeError("network down"); };
await check("DL GitHub unreachable -> 502", off, dlReq("/dl/mac/f1"), { status: 502 });
github = releases({ asset: goodAsset });
const d5 = await check("DL POST -> 405", off, dlReq("/dl/mac/f1", { method: "POST" }), { status: 405, upstream: [] });
assert.equal(d5.headers.get("allow"), "GET, HEAD");
await check("DL /dl/win/x stays with the site's redirects", off, dlReq("/dl/win/site"), { status: 200, upstream: [] });
assert.ok(assets.includes(PROD + "/dl/win/site"), "/dl/win goes to ASSETS (_redirects)");
await check("DL /dl/macintosh is not a Mac download path", off, dlReq("/dl/macintosh"), { status: 200, upstream: [] });
github = null;

// Everything else goes to the site's files.
await check("ON prod GET /api/event", on, get(E), { status: 200, upstream: [] });
await check("ON prod page", on, get(PROD + "/mac"), { status: 200, upstream: [] });
assert.ok(assets.includes(PROD + "/mac"), "pages go to ASSETS");
results.push("ok  pages and a GET to /api/event go to the site's files");
console.log(results.join("\n"));
console.log(`ALL PASS (${results.length} checks)`);
