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
 * visits never reach the statistics.
 */

const SCRIPT_PATH = "/js/script.js";
const EVENT_PATH = "/api/event";

// Plausible issues a per-site script (https://plausible.io/js/pa-<id>.js).
// Keep "REPLACE_ME" until the day analytics is switched on.
const SCRIPT_UPSTREAM = "https://plausible.io/js/pa-REPLACE_ME.js";
const EVENT_UPSTREAM = "https://plausible.io/api/event";

// The only hostnames whose visits are counted.
const COUNTED_HOSTS = new Set(["freelance-easy.com", "www.freelance-easy.com"]);

function counted(url) {
  return !SCRIPT_UPSTREAM.includes("REPLACE_ME") && COUNTED_HOSTS.has(url.hostname);
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
  if (!counted(url)) {
    // Dropped, not forwarded: analytics is off, or this isn't production.
    return new Response(null, { status: 202, headers: { "cache-control": "no-store" } });
  }
  const headers = new Headers();
  headers.set("content-type", request.headers.get("content-type") || "text/plain");
  headers.set("user-agent", request.headers.get("user-agent") || "");
  // Plausible derives country/visitor hash from the client IP and discards it;
  // without this header it would see Cloudflare's edge IP instead.
  const ip = request.headers.get("cf-connecting-ip");
  if (ip) headers.set("x-forwarded-for", ip);
  const upstream = await fetch(EVENT_UPSTREAM, {
    method: "POST",
    headers,
    body: request.body,
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
