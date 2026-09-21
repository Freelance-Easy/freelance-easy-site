/* Freelance Easy — site Worker.
 *
 * Two jobs, nothing else:
 *   1. Serve the static site (everything under this folder) through the
 *      ASSETS binding, so `_redirects` and `_headers` keep working exactly as
 *      before this file existed.
 *   2. Proxy Plausible Analytics through our own domain — the script at
 *      /js/script.js and the event endpoint at /api/event. Plausible is
 *      cookieless and records no personal data; proxying is disclosed in
 *      /privacy ("served from our own domain"). Cookies are stripped before
 *      anything is forwarded (there are none on this site, but belt and braces).
 *
 * Until the Plausible site exists, SCRIPT_UPSTREAM is a placeholder and the
 * script route answers an empty script (a 200, cached briefly) — no console
 * error on any page, and no events are sent anywhere because the queue in the
 * page's snippet is never drained.
 */

const SCRIPT_PATH = "/js/script.js";
const EVENT_PATH = "/api/event";

// Plausible issues a per-site script (https://plausible.io/js/pa-<id>.js).
// Set this once the site is added in Plausible; keep "REPLACE_ME" until then.
const SCRIPT_UPSTREAM = "https://plausible.io/js/pa-REPLACE_ME.js";
const EVENT_UPSTREAM = "https://plausible.io/api/event";

async function proxyScript(request, ctx) {
  if (SCRIPT_UPSTREAM.includes("REPLACE_ME")) {
    return new Response("/* analytics not configured */\n", {
      status: 200,
      headers: {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "public, max-age=300",
      },
    });
  }
  const cache = caches.default;
  const cacheKey = new Request(new URL(request.url).origin + SCRIPT_PATH, {
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

async function proxyEvent(request) {
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
      return proxyScript(request, ctx);
    }
    if (url.pathname === EVENT_PATH && request.method === "POST") {
      return proxyEvent(request);
    }
    return env.ASSETS.fetch(request);
  },
};
