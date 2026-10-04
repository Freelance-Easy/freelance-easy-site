/* Freelance Easy — site Worker.
 *
 * Two jobs, nothing else:
 *   1. Serve the static site (everything under this folder) through the
 *      ASSETS binding, so `_redirects` and `_headers` keep working exactly as
 *      before this file existed.
 *   2. Proxy Plausible Analytics through our own domain — the script at
 *      /js/script.js and the event endpoint at /api/event. Plausible is
 *      cookieless and records no personal data; proxying is disclosed in
 *      /privacy ("served through our own domain"). Only the headers Plausible
 *      needs are forwarded (no cookies; there are none on this site anyway).
 *
 * THE SWITCH is SCRIPT_UPSTREAM. While it holds "REPLACE_ME", analytics is
 * off: the script route answers an empty script (a 200, cached briefly, so no
 * page logs an error) and the event route drops anything sent to it, so
 * nothing leaves the site. Switching on = putting the site's own script URL
 * from Plausible (Site settings → General → Site installation) here, the same
 * day /privacy describes the analytics (legal v2). Even then, only the
 * production hostnames count: a branch preview (*.workers.dev) or a local
 * server gets the empty script and its events are dropped, so our own test
 * visits never reach the statistics. And only the events /privacy lists are
 * forwarded (FORWARDED_EVENTS: pageviews, Plausible's engagement event, and
 * Download Click with its four properties); anything else stops here.
 */

const SCRIPT_PATH = "/js/script.js";
const EVENT_PATH = "/api/event";

// Plausible issues a per-site script (https://plausible.io/js/pa-<id>.js).
// Keep "REPLACE_ME" until the day analytics is switched on.
const SCRIPT_UPSTREAM = "https://plausible.io/js/pa-REPLACE_ME.js";
const EVENT_UPSTREAM = "https://plausible.io/api/event";

// The only hostnames whose visits are counted, and the site's domain as
// Plausible knows it (the `d` its script sends).
const COUNTED_HOSTS = new Set(["freelance-easy.com", "www.freelance-easy.com"]);
const SITE_DOMAIN = "freelance-easy.com";

// The only events forwarded, with the only properties each may carry: what
// /privacy §3 lists (legal v2: the pages viewed, how long they stay open and
// how far they're scrolled, and which download button was clicked). Plausible's
// script sends "engagement" on its own (time on page, scroll depth). Anything
// else is dropped here. Adding an event or a property needs a §3 line first,
// then an entry here.
const FORWARDED_EVENTS = new Map([
  ["pageview", new Set()],
  ["engagement", new Set()],
  ["Download Click", new Set(["os", "campaign", "page", "placement"])],
]);
const MAX_EVENT_BYTES = 8192;

function counted(url) {
  return !SCRIPT_UPSTREAM.includes("REPLACE_ME") && COUNTED_HOSTS.has(url.hostname);
}

// At most `max` bytes of the body, decoded as strict UTF-8; null when it is
// larger (a declared Content-Length over the cap is refused before reading;
// an undeclared one is cut off at the cap), not UTF-8, or unreadable.
async function readCapped(request, max) {
  const declared = Number(request.headers.get("content-length"));
  if (Number.isFinite(declared) && declared > max) return null;
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > max) {
        await reader.cancel().catch(() => {});
        return null;
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(total);
    let at = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, at);
      at += chunk.byteLength;
    }
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (e) {
    return null;
  }
}

const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const isText = (v, max) => typeof v === "string" && v.length <= max;
const isCount = (v) => typeof v === "number" && Number.isFinite(v) && v >= 0;

// The event the page sent, in the browser format of Plausible's script
// ({n: name, u: page URL, d: domain, r: referrer, v: script version, p: props,
// and for engagement sd: scroll depth, e: time}), rebuilt from those known
// fields only; null to drop it. Plausible gets the rebuilt copy, never the
// raw body, so a field nobody listed here (a legacy property field such as
// `m`, `meta` or `props`, revenue `$`, anything new) can't reach it, and what
// it parses is exactly what was checked.
function rebuild(text) {
  let e;
  try {
    e = JSON.parse(text);
  } catch (err) {
    return null;
  }
  if (!isObject(e)) return null;
  const allowedProps = typeof e.n === "string" ? FORWARDED_EVENTS.get(e.n) : undefined;
  if (!allowedProps || e.d !== SITE_DOMAIN || !isText(e.u, 2048)) return null;
  let page;
  try {
    page = new URL(e.u);
  } catch (err) {
    return null;
  }
  if (!COUNTED_HOSTS.has(page.hostname)) return null;
  const out = { n: e.n, u: e.u, d: e.d };
  if (e.r !== undefined) {
    if (e.r !== null && !isText(e.r, 2048)) return null;
    out.r = e.r;
  }
  if (e.v !== undefined) {
    if (!isCount(e.v) && !isText(e.v, 32)) return null;
    out.v = e.v;
  }
  if (e.h !== undefined) {
    if (![0, 1, true, false].includes(e.h)) return null;
    out.h = e.h;
  }
  if (e.i !== undefined) {
    if (typeof e.i !== "boolean") return null;
    out.i = e.i;
  }
  if (e.n === "engagement") {
    if (!isCount(e.sd) || !isCount(e.e)) return null;
    out.sd = e.sd;
    out.e = e.e;
  }
  if (e.p !== undefined && e.p !== null) {
    if (!isObject(e.p)) return null;
    const keys = Object.keys(e.p);
    if (!keys.every((k) => allowedProps.has(k) && isText(e.p[k], 64))) return null;
    if (keys.length) out.p = Object.fromEntries(keys.map((k) => [k, e.p[k]]));
  }
  return out;
}

function dropped() {
  return new Response(null, { status: 202, headers: { "cache-control": "no-store" } });
}

async function proxyScript(request, ctx, url) {
  if (!counted(url)) {
    return new Response("/* analytics off here */\n", {
      status: 200,
      headers: {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "public, max-age=300",
      },
    });
  }
  const cache = caches.default;
  const cacheKey = new Request(url.origin + SCRIPT_PATH, {
    method: "GET",
  });
  let response = await cache.match(cacheKey);
  if (!response) {
    const upstream = await fetch(SCRIPT_UPSTREAM, {
      headers: { "user-agent": request.headers.get("user-agent") || "" },
      cf: { cacheTtl: 86400, cacheEverything: true },
    });
    response = new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "public, max-age=86400",
      },
    });
    if (upstream.ok) ctx.waitUntil(cache.put(cacheKey, response.clone()));
  }
  return response;
}

async function proxyEvent(request, url) {
  // Dropped, not forwarded: analytics is off, or this isn't production.
  if (!counted(url)) return dropped();
  // Only the content types Plausible's script sends, and the rebuilt event
  // goes on as text/plain, so Plausible reads the JSON this Worker checked
  // (a form-encoded body would be read as form fields instead).
  const type = (request.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
  if (type !== "text/plain" && type !== "application/json") return dropped();
  const text = await readCapped(request, MAX_EVENT_BYTES);
  const event = text === null ? null : rebuild(text);
  if (!event) return dropped();
  const body = JSON.stringify(event);
  const headers = new Headers();
  headers.set("content-type", "text/plain");
  headers.set("user-agent", request.headers.get("user-agent") || "");
  // Plausible derives country/visitor hash from the client IP and discards it;
  // without this header it would see Cloudflare's edge IP instead.
  const ip = request.headers.get("cf-connecting-ip");
  if (ip) headers.set("x-forwarded-for", ip);
  const upstream = await fetch(EVENT_UPSTREAM, {
    method: "POST",
    headers,
    body,
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "cache-control": "no-store" },
  });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === SCRIPT_PATH && request.method === "GET") {
      return proxyScript(request, ctx, url);
    }
    if (url.pathname === EVENT_PATH && request.method === "POST") {
      return proxyEvent(request, url);
    }
    return env.ASSETS.fetch(request);
  },
};
